"""Run a bounded, reproducible Lab 5 student-hook composition smoke.

The smoke initializes a student workspace, uses a small instructor foundation
checkpoint, compares reference and student retrieval on one frozen development
task, then validates both selected actions through fresh complete-core checks.
It claims no learning benefit and performs no physical-design run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

# Keep any numerical libraries used by the installed runtime on one CPU thread.
for _thread_variable in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[_thread_variable] = "1"

from nanochip.laboratory.contracts import file_sha256
from nanochip.laboratory.course import course_status, init_workspace, run_lab
from nanochip.laboratory.course.checks import validate_student_context
from nanochip.laboratory.context import specification_sources


_STUDENT_SPLITTER = """
import hashlib

def split_records(records, *, seed, fractions=None):
    ratios = dict(fractions or {"train": 0.6, "dev": 0.2, "test": 0.2})
    groups = {}
    originals = {}
    for row in records:
        group = row["group_id"]
        groups.setdefault(group, []).append(row)
        originals.setdefault(group, row.get("original_split", "train"))
    movable = [group for group in groups if originals[group] == "train"]
    ordered = sorted(movable,
        key=lambda group: hashlib.sha256(f"{seed}\\0{group}".encode()).digest())
    cuts = (ratios["train"], ratios["train"] + ratios["dev"])
    assignment = {group: ("dev" if originals[group] == "development" else originals[group])
                  for group in groups if originals[group] in ("dev", "development", "test")}
    for rank, group in enumerate(ordered):
        position = (rank + 0.5) / len(ordered)
        assignment[group] = "train" if position < cuts[0] else "dev" if position < cuts[1] else "test"
    for missing in ("train", "dev", "test"):
        if missing not in assignment.values():
            counts = {part: list(assignment.values()).count(part) for part in ("train", "dev", "test")}
            donor = max((assignment[group] for group in ordered), key=lambda part: counts[part])
            moved = next(group for group in reversed(ordered) if assignment[group] == donor)
            assignment[moved] = missing
    return [dict(row, split=assignment[row["group_id"]]) for row in records]
""".lstrip()


_STUDENT_INFERENCE = """
import hashlib
import json
import re

def serialize(task, history):
    spec = task.specification
    config = spec["target"]["configuration"]
    check_names = tuple(requirement.name for requirement in task.required_checks)
    observations = {}
    for item in history:
        if item.action is None or item.action.name not in task.allowed_actions:
            raise ValueError("history contains no legal action identity")
        metric = item.receipt.metrics.get("cycles") if item.receipt else None
        failed_mask = sum(1 << check_names.index(check.name) for check in item.checks
                          if check.status != "pass" and check.name in check_names)
        action_index = task.allowed_actions.index(item.action.name)
        previous = observations.get(action_index, [0, 0, None, 0])
        observations[action_index] = [previous[0] + 1,
            previous[1] + int(bool(item.eligible)),
            int(metric.value) if metric else None, failed_mask]
    value = {"schema": "nanochip.course.task_json/v3",
             "w": [config["d_model"], config["n_layers"], config["n_experts"], config["top_k"]],
             "x": [spec["token_count"], spec["seed"], spec["prompt_index"], spec.get("tokens")],
             "a": list(task.allowed_actions),
             "h": [[index, *observations[index]] for index in sorted(observations)]}
    return json.dumps(value, sort_keys=True, separators=(",", ":"))

def retrieve(query, documents, *, limit):
    # A transparent query expansion selects a short, attributed quantization excerpt.
    terms = set(re.findall(r"[a-z][a-z0-9_]+",
                           (query + " int4 packed embedding quantization").lower()))
    ranked = []
    for source in documents:
        if source.get("partition") not in ("train", "dev", "specification"):
            raise ValueError("disallowed retrieval partition")
        source_terms = set(re.findall(r"[a-z][a-z0-9_]+", source["text"].lower()))
        overlap = len(terms & source_terms)
        if overlap:
            ranked.append((overlap, source["source_id"], source))
    if not ranked or limit <= 0:
        return ()
    _, _, source = sorted(ranked, key=lambda row: (-row[0], row[1]))[0]
    sentence_match = re.search(r"[^.!?]+[.!?]", source["text"])
    sentence = sentence_match.group(0).replace("**", "").strip() if sentence_match else ""
    sentence_words = sentence.split()
    if sentence_words and len(sentence_words) <= limit:
        excerpt = " ".join(sentence_words)
        selection = "first_complete_sentence"
    else:
        excerpt = " ".join(source["text"].replace("**", "").split()[:limit])
        selection = "bounded_prefix"
    return (dict(source, text=excerpt, retrieval_selection=selection,
                 retrieval_word_limit=limit, retrieved_words=len(excerpt.split()),
                 text_sha256=hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
                 full_text_sha256=source["text_sha256"]),)

def parse_action(text, allowed_actions):
    if not isinstance(text, str) or not text.strip() or "\\n" in text or "\\r" in text:
        raise ValueError("expected one action name")
    action = text.strip()
    if action not in tuple(allowed_actions):
        raise ValueError("action is outside the declared interface")
    return action
""".lstrip()


def _summary(report: dict[str, Any], path: Path) -> dict[str, Any]:
    observation = report["harness_campaign"]["observations"][0]
    receipt = observation["receipt"]
    output_root = Path(receipt["output_root"])
    core = next(row for row in receipt["output_artifacts"] if row["path"] == "core.v")
    core_path = output_root / core["path"]
    contexts = report["model_input"]["retrieved_context"]
    checks = [
        {"name": row["name"], "scope": row["scope"], "status": row["status"]}
        for row in receipt["checks"]
    ]
    return {
        "report": str(path),
        "action": observation["action"]["name"],
        "eligible": observation["eligible"],
        "task_id": report["harness_campaign"]["task_id"],
        "checkpoint_sha256": report["checkpoint_sha256"],
        "model_input_sha256": report["model_input"]["sha256"],
        "model_input_bytes": len(report["model_input"]["text"].encode("utf-8")),
        "context_word_budget": report["model_input"]["context_word_budget"],
        "context_words": sum(len(row["text"].split()) for row in contexts),
        "contexts": [
            {
                key: row[key]
                for key in (
                    "source_id",
                    "partition",
                    "source",
                    "file_sha256",
                    "text_sha256",
                    "text",
                )
            }
            for row in contexts
        ],
        "candidate_digest": observation["candidate_digest"],
        "candidate_core_sha256": core["sha256"],
        "candidate_core_hash_verified": file_sha256(core_path) == core["sha256"],
        "receipt_mode": receipt["mode"],
        "checks": checks,
        "all_core_checks_pass": all(
            row["scope"] == "accelerator:nanochip_teaching_core"
            and row["status"] == "pass"
            for row in checks
        ),
        "cycles": receipt["metrics"]["cycles"]["value"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "workspace",
        type=Path,
        help="new output directory for this smoke; it must not already exist",
    )
    args = parser.parse_args(argv)
    root = args.workspace.resolve()
    init_workspace(root, mode="student")
    (root / "labs/lab01_data.py").write_text(_STUDENT_SPLITTER, encoding="utf-8")

    events = []
    events.append(run_lab(root, 1, mode="student"))
    events.append(run_lab(root, 2, mode="instructor"))
    events.append(run_lab(root, 3, mode="instructor"))
    events.append(
        run_lab(
            root,
            4,
            mode="instructor",
            inputs={"budget": {"max_steps": 3, "max_seconds": 30, "seed": 91}},
        )
    )
    model_inputs = {"seed": 23, "prompt_index": 0, "tokens": [7], "context_limit": 24}
    baseline_event = run_lab(root, 5, mode="instructor", inputs=model_inputs)
    events.append(baseline_event)
    baseline_path = (
        root / baseline_event["outputs"][0]["path"] / "inference/inference-check.json"
    )
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))

    (root / "labs/lab05_inference.py").write_text(_STUDENT_INFERENCE, encoding="utf-8")
    student_event = run_lab(root, 5, mode="student", inputs=model_inputs)
    events.append(student_event)
    student_path = (
        root / student_event["outputs"][0]["path"] / "inference/inference-check.json"
    )
    student = json.loads(student_path.read_text(encoding="utf-8"))

    baseline_summary = _summary(baseline, baseline_path)
    student_summary = _summary(student, student_path)
    verified_context = validate_student_context(
        specification_sources(),
        student["model_input"]["retrieved_context"],
        word_budget=24,
    )
    comparisons = {
        "student_hook_executed": student_event["mode"] == "student",
        "same_development_task": baseline_summary["task_id"]
        == student_summary["task_id"]
        and "development" in student_summary["task_id"],
        "same_checkpoint": baseline_summary["checkpoint_sha256"]
        == student_summary["checkpoint_sha256"],
        "recorded_model_input_changed": baseline_summary["model_input_sha256"]
        != student_summary["model_input_sha256"],
        "retrieval_attribution_revalidated": len(verified_context) == 1
        and verified_context[0]["source_id"]
        == student_summary["contexts"][0]["source_id"],
        "within_word_and_byte_budgets": student_summary["context_words"] <= 24
        and student_summary["model_input_bytes"] <= 768,
        "exact_rtl_source_hash_matches_receipt": student_summary[
            "candidate_core_hash_verified"
        ],
        "fresh_complete_core_checks_pass": student_summary["receipt_mode"] == "fresh"
        and student_summary["all_core_checks_pass"]
        and student_summary["eligible"],
        "no_physical_run": True,
    }
    if not all(comparisons.values()):
        raise RuntimeError(
            f"Student extension smoke failed its independent summary: {comparisons}"
        )
    receipt = {
        "schema": "nanochip-course-student-extension-evidence/v1",
        "workspace": str(root),
        "component_hashes": {
            "lab01_data.py": events[0]["implementation"]["sha256"],
            "lab05_inference.py": student_event["implementation"]["sha256"],
        },
        "event_digests": [
            {
                "lab": event["lab"],
                "mode": event["mode"],
                "status": event["status"],
                "run_digest": event["run_digest"],
            }
            for event in events
        ],
        "reference": baseline_summary,
        "student_extension": student_summary,
        "comparisons": comparisons,
        "interpretation": "The workspace-defined retrieval policy changed the recorded model input and passed it through the saved model, parser, materializer, and fresh complete-core harness. Both runs used the same development task and checkpoint. This demonstrates component composition and evidence lineage; it does not establish a learning benefit or a human usability result.",
    }
    path = root / "extension-comparison.json"
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "pass",
                "workspace": str(root),
                "receipt": str(path),
                "comparisons": comparisons,
                "reference_action": baseline_summary["action"],
                "student_action": student_summary["action"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
