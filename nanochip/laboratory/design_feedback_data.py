"""Freeze a measured exploration preference from two existing tool bundles.

This collector never runs a physical flow. A smaller postroute cell area earns
an exploration preference only when both designs pass the same bounded RTL
checks and have identical failed physical check families. It does not establish
optimal PPA, full-core correctness, or acceptance of either design.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import shutil
from typing import Any

from . import design_changes
from .contracts import (
    Action,
    Artifact,
    Candidate,
    ContractError,
    canonical_json,
    file_sha256,
)
from .design_learning import design_input
from .physical import flow

LABEL_ORIGIN = "measured_area_exploration_preference_with_failed_checks"
SCHEMA = "nanochip-measured-design-feedback/v1"
BOUNDARY = (
    "One development case reused for adaptation; two measured designs only. "
    "Area preference within identical failed physical check families; no optimal-PPA, "
    "held-out generalization, full-core correctness, manufacturing, or acceptance claim."
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def _read(path: Path) -> Any:
    try:

        def reject(token):
            raise ContractError(f"Nonfinite JSON constant in {path}: {token}")

        return json.loads(path.read_text(), parse_constant=reject)
    except (OSError, ValueError) as exc:
        raise ContractError(f"Unavailable or invalid evidence: {path}: {exc}") from exc


def _write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def _finite(value: Any, name: str, *, positive=False) -> float:
    _require(
        type(value) in (int, float) and math.isfinite(value),
        f"Finite numeric {name} required",
    )
    _require(not positive or value > 0, f"Positive {name} required")
    return value


def derive_preference(candidates: list[dict]) -> str:
    """Choose smaller area only inside one matched, completed failure envelope."""
    _require(len(candidates) == 2, "Exactly two measured candidates are required")
    _require(
        len({c["action"] for c in candidates}) == 2,
        "Distinct candidate actions required",
    )
    for candidate in candidates:
        _require(
            candidate.get("functional_passed") is True,
            "Both functional checks must pass",
        )
        _require(
            candidate.get("physical_completed") is True,
            "Both physical flows must complete",
        )
        _require(
            candidate.get("required_physical_passed") is True,
            "Routed timing and DRC/LVS must pass",
        )
        _finite(
            candidate.get("postroute_instance_area"), "postroute area", positive=True
        )
        for key in ("postroute_setup_worst_slack", "postroute_hold_worst_slack"):
            _finite(candidate.get(key), key)
    failures = [sorted(c.get("failed_check_families", [])) for c in candidates]
    _require(
        bool(failures[0]) and failures[0] == failures[1],
        "Identical nonempty failed physical check families required",
    )
    _require(
        candidates[0]["configuration"] == candidates[1]["configuration"],
        "Physical configurations must match",
    )
    areas = [c["postroute_instance_area"] for c in candidates]
    _require(
        areas[0] != areas[1], "No area improvement; abstaining from an artificial label"
    )
    return candidates[areas.index(min(areas))]["action"]


class _Evidence:
    def __init__(self):
        self.files: dict[str, str] = {}
        self.minimal: set[Path] = set()

    def file(self, path: Path, expected: str | None = None, *, copy=False) -> str:
        path = path.resolve()
        try:
            digest = self.files.get(str(path))
            if digest is None:
                digest = file_sha256(path)
                self.files[str(path)] = digest
        except OSError as exc:
            raise ContractError(f"Missing evidence file: {path}") from exc
        _require(
            expected is None or digest == expected, f"Evidence hash mismatch: {path}"
        )
        if copy:
            self.minimal.add(path)
        return digest

    def read(self, path: Path, *, copy=True):
        self.file(path, copy=copy)
        return _read(path)

    def artifacts(self, root: Path, items: list[dict]) -> None:
        _require(
            isinstance(items, list) and bool(items),
            "Nonempty artifact manifest required",
        )
        _require(
            len({a["path"] for a in items}) == len(items), "Duplicate artifact paths"
        )
        for item in items:
            artifact = Artifact(**item)
            self.file(artifact.resolve(root), artifact.sha256)


def _functional(
    e: _Evidence, root: Path, source_hash: str, *, differential=False
) -> dict:
    receipt = e.read(root / "receipt.json")
    _require(
        receipt.get("mode") == "fresh"
        and receipt.get("ok") is True
        and receipt.get("status") == "passed",
        "Fresh passing functional receipt required",
    )
    for key in ("version_probe", "build", "simulation"):
        part = receipt.get(key, {})
        _require(
            part.get("returncode") == 0 and part.get("timed_out") is False,
            f"Functional {key} must complete successfully",
        )
    e.file(root / "candidate.v", source_hash, copy=True)
    _require(
        receipt.get("candidate_sha256") == source_hash,
        "Functional source identity mismatch",
    )
    if receipt.get("output_artifacts"):
        e.artifacts(root, receipt["output_artifacts"])
    for name in receipt.get("generated_files", []):
        target = Path(name).resolve()
        _require(
            target.is_relative_to(root.resolve()),
            "Functional artifact escapes output root",
        )
        e.file(target)
    fields = {
        "bench_sha256": "stress.cpp" if differential else "dequant_tb.cpp",
        "binary_sha256": "obj/equivalence_probe"
        if differential
        else "obj/dequant_probe",
    }
    if differential:
        fields |= {
            "reference_sha256": "reference.v",
            "miter_sha256": "miter.v",
            "checker_sha256": "checker.py",
        }
    else:
        fields |= {
            "vectors_sha256": "vectors.json",
            "vector_text_sha256": "vectors.txt",
        }
    for key, name in fields.items():
        _require(key in receipt, f"Missing functional identity: {key}")
        e.file(root / name, receipt[key], copy=name != fields["binary_sha256"])
    raw = (root / "simulation.log").read_text()
    e.file(root / "simulation.log", copy=True)
    prefix = "EQUIVALENCE_JSON " if differential else "PROBE_JSON "
    summaries = [
        json.loads(line[len(prefix) :])
        for line in raw.splitlines()
        if line.startswith(prefix)
    ]
    _require(
        len(summaries) == 1 and summaries[0] == receipt.get("checks"),
        "Functional summary differs from raw log",
    )
    checks = summaries[0]
    if differential:
        _require(
            receipt.get("reference_sha256") == design_changes.REFERENCE_SHA256,
            "Differential reference identity mismatch",
        )
        original = (root / "reference.v").read_text()
        candidate = (root / "candidate.v").read_text()
        _require(
            (root / "miter.v").read_text()
            == design_changes._equivalence_miter(original, candidate),
            "Differential miter differs from unchanged comparison contract",
        )
        _require(
            (root / "stress.cpp").read_text() == design_changes._STRESS_BENCH,
            "Differential stress bench changed",
        )
        _require(
            checks.get("jobs_completed") == 409 and checks.get("resets") == 15,
            "Complete declared differential cases required",
        )
        counters = ("valid_writes", "stream_stall_cycles", "cycles_checked")
    else:
        _require(
            checks.get("mismatches") == 0 and checks.get("protocol_error") == "",
            "Integer oracle checks failed",
        )
        counters = ("rows_completed", "lanes_checked", "stream_stall_cycles")
    _require(checks.get("ok") is True, "Functional raw check failed")
    for key in counters:
        _finite(checks.get(key), key, positive=True)
    return receipt


def _physical(e: _Evidence, root: Path, source_hash: str) -> dict:
    receipt = e.read(root / "receipt.json")
    _require(
        receipt.get("status") == "completed" and receipt.get("returncode") == 0,
        "Completed successful physical execution required",
    )
    _require(
        receipt.get("candidate_sha256") == source_hash,
        "Physical source identity mismatch",
    )
    e.artifacts(root, receipt.get("artifacts"))
    for name, key in (
        ("msh_deq.v", "candidate_sha256"),
        ("config.json", "config_sha256"),
        ("runner.py", "runner_sha256"),
    ):
        e.file(root / name, receipt.get(key), copy=True)
    e.file(root / "image.json", copy=True)
    config = {
        key: receipt.get(key)
        for key in (
            "config_sha256",
            "image",
            "pdk",
            "pdk_revision",
            "runner_sha256",
            "cores",
            "host_architecture",
        )
    }
    config["coverage_script_sha256"] = e.file(root / "coverage.tcl", copy=True)
    _require(
        all(value is not None for value in config.values()),
        "Physical configuration identity incomplete",
    )
    _require(
        type(config["cores"]) is int and config["cores"] > 0,
        "Physical CPU limit missing",
    )
    _require(
        config["image"] == flow.IMAGE and config["pdk_revision"] == flow.PDK_REVISION,
        "Physical image or PDK identity mismatch",
    )
    commands = [c for c in receipt.get("commands", []) if "run" in c and "--cpus" in c]
    _require(len(commands) == 1, "One physical execution command required")
    command = commands[0]
    _require(
        command[command.index("--cpus") + 1] == str(config["cores"])
        and config["image"] in command
        and config["pdk_revision"] in command[-1],
        "Physical command differs from declared image, PDK, or CPU limit",
    )
    # Recompute checks from each executing stage, including explicit corner coverage.
    checks, stages = flow.collect_checks(root)
    _require(
        checks == receipt.get("checks"),
        "Physical checks differ from raw retained states",
    )
    for stage in stages.values():
        e.file(root / stage["path"], copy=True)
    timing = stages.get("openroad-stapostpnr", {})
    _require(bool(timing), "Postroute timing state required")
    e.file((root / timing["path"]).parent / "config.json", copy=True)
    e.file(root / "coverage-receipt.json", copy=True)
    e.file(root / "coverage.tcl", copy=True)
    coverage = e.read(root / "coverage-receipt.json")
    e.artifacts(root, coverage.get("input_artifacts"))
    for corner in coverage.get("corners", []):
        e.file(root / corner["log"], corner["log_sha256"], copy=True)
        e.file(root / corner["environment"], corner["environment_sha256"], copy=True)
    required = {
        "gds_generated",
        "routed_timing",
        "detailed_route_drc",
        "magic_drc",
        "klayout_drc",
        "physical_drc",
        "physical_lvs",
    }
    status = {c["name"]: c["status"] for c in checks}
    _require(
        all(status.get(name) == "pass" for name in required),
        "Routed timing and DRC/LVS must pass",
    )
    _require(
        all(c["status"] in ("pass", "fail") for c in checks),
        "Unresolved physical check",
    )
    metrics = timing["metrics"]
    extracted = {
        "postroute_instance_area": metrics.get("design__instance__area"),
        "postroute_setup_worst_slack": metrics.get("timing__setup__ws"),
        "postroute_hold_worst_slack": metrics.get("timing__hold__ws"),
    }
    for key, value in extracted.items():
        _finite(value, key, positive=key == "postroute_instance_area")
    raw_failures = {
        key: value
        for stage in stages.values()
        for key, value in stage["metrics"].items()
        if (key.endswith("__count") or key == "route__drc_errors")
        and type(value) in (int, float)
        and math.isfinite(value)
        and value > 0
    }
    return dict(
        physical_completed=True,
        required_physical_passed=True,
        configuration=config,
        checks=checks,
        failed_check_families=sorted(
            c["name"] for c in checks if c["status"] == "fail"
        ),
        raw_failures=raw_failures,
        **extracted,
    )


def _inspect(
    baseline: Path, candidate: Path, baseline_differential: Path
) -> tuple[dict, _Evidence]:
    e = _Evidence()
    task = e.read(candidate / "task.json")
    proposal = e.read(candidate / "proposal.json")
    experiment = e.read(candidate / "design-experiment.json")
    events_path = candidate / "events.jsonl"
    e.file(events_path, copy=True)
    events = [json.loads(line) for line in events_path.read_text().splitlines()]
    _require(
        [v["event"] for v in events]
        == [
            "campaign_started",
            "proposal",
            "candidate",
            "observation",
            "campaign_finished",
        ],
        "Exactly one completed candidate campaign required",
    )
    _require(events[0]["task"] == task, "Task/event linkage mismatch")
    specification = task["specification"]
    reference_hash = specification["source_sha256"]
    _require(
        reference_hash == design_changes.REFERENCE_SHA256,
        "Unsupported original RTL source",
    )
    original_path = baseline / "source.v"
    e.file(original_path, reference_hash, copy=True)
    original = original_path.read_text()
    item = events[2]["candidate"]
    item_root = Path(item["root"]).resolve()
    _require(
        item_root == (candidate / "attempts/attempt-0001/candidate").resolve(),
        "Candidate root linkage mismatch",
    )
    e.artifacts(item_root, item["artifacts"])
    obj = Candidate(
        item["candidate_id"],
        item["task_id"],
        str(item_root),
        Action(**item["action"]),
        tuple(Artifact(**a) for a in item["artifacts"]),
        item.get("parent_id"),
        item["task_digest"],
    )
    task_digest = hashlib.sha256(canonical_json(task).encode()).hexdigest()
    _require(
        obj.task_digest == task_digest and obj.task_id == task["task_id"],
        "Candidate/task identity mismatch",
    )
    _require(obj.digest == events[2]["candidate_digest"], "Candidate digest mismatch")
    action = item["action"]
    _require(
        action == proposal.get("action") == events[1]["action"],
        "Proposal/action linkage mismatch",
    )
    _require(
        action["name"] in task["allowed_actions"] and not action["parameters"],
        "Unsupported candidate action",
    )
    _require(
        proposal.get("input_text") == design_input(specification),
        "Proposal input serialization mismatch",
    )
    e.file(item_root / "reference.v", reference_hash, copy=True)
    changed_path = item_root / "msh_deq.v"
    changed_hash = e.file(changed_path, copy=True)
    _require(
        changed_path.read_text()
        == design_changes.apply_design_change(original, action["name"]),
        "Candidate differs from exact named RTL transformation",
    )
    _require(e.read(item_root / "task.json") == task, "Materialized task mismatch")
    attempt = item_root.parent
    link = e.read(attempt / "execution-link.json")
    _require(
        link.get("task_digest") == task_digest
        and link.get("candidate_digest") == obj.digest
        and link.get("action") == action
        and link.get("physical_run") is True,
        "Execution linkage mismatch",
    )
    _require(
        all(
            link.get(key) == changed_hash
            for key in (
                "source_sha256",
                "functional_source_sha256",
                "physical_source_sha256",
            )
        ),
        "Cross-tool source mismatch",
    )
    observation = events[3]["observation"]
    _require(
        observation.get("candidate_digest") == obj.digest
        and observation.get("action") == action
        and observation.get("status") == "success",
        "Observation linkage mismatch",
    )
    campaign = events[4]["campaign"]
    _require(
        campaign == experiment.get("campaign")
        and campaign["observations"] == [observation]
        and campaign["task_id"] == task["task_id"],
        "Completed campaign linkage mismatch",
    )
    _require(
        experiment.get("complete_design_eligible") is False,
        "Unexpected full design acceptance",
    )
    for name in ("functional-receipt.json", "physical-receipt.json"):
        wrapper = e.read(attempt / name)
        _require(
            wrapper.get("candidate_digest") == obj.digest
            and wrapper.get("task_id") == task["task_id"]
            and wrapper.get("mode") == "fresh"
            and wrapper.get("execution_status") == "success",
            "Fresh execution wrapper linkage mismatch",
        )
        e.artifacts(Path(wrapper["output_root"]), wrapper["output_artifacts"])
    baseline_functional = _functional(e, baseline / "functional", reference_hash)
    candidate_functional = _functional(e, attempt / "tool", changed_hash)
    for key in (
        "bench_sha256",
        "probe_sha256",
        "vectors_sha256",
        "vector_text_sha256",
        "tool_version",
    ):
        _require(
            baseline_functional.get(key) == candidate_functional.get(key),
            "Integer reference test configuration mismatch",
        )
    for key in ("bench_sha256", "probe_sha256"):
        _require(
            candidate_functional.get(key) == specification[key],
            "Functional task reference mismatch",
        )
    baseline_diff = _functional(
        e, baseline_differential, reference_hash, differential=True
    )
    candidate_diff = _functional(
        e, attempt / "differential", changed_hash, differential=True
    )
    _require(
        baseline_diff["bench_sha256"] == candidate_diff["bench_sha256"]
        and baseline_diff["tool_version"] == candidate_diff["tool_version"],
        "Differential configuration mismatch",
    )
    physical_dirs = list(attempt.glob("physical-*/receipt.json"))
    _require(len(physical_dirs) == 1, "Exactly one physical candidate bundle required")
    rows = [
        dict(
            action="retain_indexed_read",
            source_sha256=reference_hash,
            functional_passed=True,
            **_physical(e, baseline / "physical", reference_hash),
        ),
        dict(
            action=action["name"],
            source_sha256=changed_hash,
            functional_passed=True,
            **_physical(e, physical_dirs[0].parent, changed_hash),
        ),
    ]
    for row in rows:
        conf = row["configuration"]
        _require(
            conf["cores"] == specification["budgets"]["cores"]
            and conf["image"] == specification["image"]
            and conf["pdk_revision"] == specification["pdk_revision"],
            "Task physical configuration mismatch",
        )
        for name, key in [
            ("physical_config.json", "config_sha256"),
            ("physical_runner.py", "runner_sha256"),
            ("physical_coverage.tcl", "coverage_script_sha256"),
        ]:
            _require(
                conf[key] == specification["physical_inputs"][name],
                "Task physical input identity mismatch",
            )
    selected = derive_preference(rows)
    return (
        dict(
            task=task,
            input_text=design_input(specification),
            target_features=specification["design_features"],
            candidates=rows,
            selected_action=selected,
            accepted=False,
            label_origin=LABEL_ORIGIN,
            boundary=BOUNDARY,
        ),
        e,
    )


def _record(evidence: dict, digest: str) -> dict:
    return dict(
        record_id="feedback-dequant256-v1",
        group_id="physical-dequant256-v1",
        split="train",
        original_split="development",
        input_text=evidence["input_text"],
        target_action=evidence["selected_action"],
        source_sha256=digest,
        source_receipt=dict(path="evidence.json", sha256=digest),
        label_origin=LABEL_ORIGIN,
    )


def collect_feedback(baseline_dir: Path, candidate_dir: Path, output: Path) -> dict:
    """Validate existing bundles, run only missing baseline RTL differential, freeze evidence."""
    baseline, candidate, output = (
        Path(baseline_dir).resolve(),
        Path(candidate_dir).resolve(),
        Path(output).resolve(),
    )
    _require(not output.exists(), "Feedback output must be a new path")
    _require(
        not output.is_relative_to(baseline) and not output.is_relative_to(candidate),
        "Do not write inside source bundles",
    )
    output.mkdir(parents=True)
    baseline_diff = output / "baseline-differential"
    # The baseline predates the differential harness; add that one check locally.
    design_changes.run_design_checks(baseline / "source.v", baseline_diff)
    evidence, inspected = _inspect(baseline, candidate, baseline_diff)
    code_hash = file_sha256(Path(__file__))
    source_files = [
        dict(path=path, sha256=digest)
        for path, digest in sorted(inspected.files.items())
    ]
    evidence.update(
        schema=SCHEMA,
        baseline_dir=str(baseline),
        candidate_dir=str(candidate),
        baseline_differential=str(baseline_diff),
        source_files=source_files,
        collector_sha256=code_hash,
    )
    _write(output / "evidence.json", evidence)
    digest = file_sha256(output / "evidence.json")
    copies = []
    for index, path in enumerate(sorted(inspected.minimal)):
        destination = output / "raw" / f"{index:04d}-{path.name}"
        destination.parent.mkdir(exist_ok=True)
        shutil.copyfile(path, destination)
        copies.append(
            dict(
                path=str(destination.relative_to(output)),
                sha256=file_sha256(destination),
                source=str(path),
            )
        )
    manifest = dict(
        schema=SCHEMA,
        case_count=1,
        records=[_record(evidence, digest)],
        target_features=evidence["target_features"],
        input_text=evidence["input_text"],
        selected_action=evidence["selected_action"],
        candidates=evidence["candidates"],
        accepted=False,
        label_origin=LABEL_ORIGIN,
        boundary=BOUNDARY,
        collector_sha256=code_hash,
        evidence_snapshot=dict(path="evidence.json", sha256=digest),
        source_files=source_files,
        copied_evidence=copies,
    )
    _write(output / "manifest.json", manifest)
    return load_feedback(output / "manifest.json")


def load_feedback(manifest: Path) -> dict:
    """Verify frozen bytes, original bundles, raw checks, serialization, and derived label."""
    manifest = Path(manifest).resolve()
    root = manifest.parent
    data = _read(manifest)
    _require(
        data.get("schema") == SCHEMA and data.get("case_count") == 1,
        "Feedback schema mismatch",
    )
    _require(
        data.get("collector_sha256") == file_sha256(Path(__file__)),
        "Feedback collector code changed",
    )
    snapshot = Artifact(**data["evidence_snapshot"])
    snapshot.validate(root)
    evidence = _read(snapshot.resolve(root))
    _require(
        data.get("source_files") == evidence.get("source_files"),
        "Source provenance mismatch",
    )
    for item in evidence["source_files"]:
        try:
            _require(
                file_sha256(item["path"]) == item["sha256"],
                f"Source evidence changed: {item['path']}",
            )
        except OSError as exc:
            raise ContractError(f"Missing source evidence: {item['path']}") from exc
    sources = {item["path"]: item["sha256"] for item in evidence["source_files"]}
    _require(bool(data.get("copied_evidence")), "Copied evidence missing")
    for item in data["copied_evidence"]:
        Artifact(item["path"], item["sha256"]).validate(root)
        _require(
            sources.get(item["source"]) == item["sha256"],
            "Copied evidence source hash mismatch",
        )
    derived, inspected = _inspect(
        Path(evidence["baseline_dir"]),
        Path(evidence["candidate_dir"]),
        Path(evidence["baseline_differential"]),
    )
    for key, value in derived.items():
        _require(
            evidence.get(key) == value,
            f"Frozen evidence differs from raw derivation: {key}",
        )
    expected_sources = [
        dict(path=path, sha256=digest)
        for path, digest in sorted(inspected.files.items())
    ]
    _require(
        expected_sources == evidence["source_files"], "Evidence source manifest changed"
    )
    _require(
        {str(p) for p in inspected.minimal}
        == {item["source"] for item in data["copied_evidence"]},
        "Minimal copied evidence set changed",
    )
    for key in (
        "target_features",
        "input_text",
        "selected_action",
        "candidates",
        "accepted",
        "label_origin",
        "boundary",
        "collector_sha256",
    ):
        _require(
            data.get(key) == evidence.get(key),
            f"Feedback manifest differs from evidence: {key}",
        )
    _require(
        data.get("records") == [_record(derived, snapshot.sha256)],
        "Feedback record label or serialization changed",
    )
    return data
