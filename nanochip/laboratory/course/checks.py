"""Integration checks for the first cumulative student-built components."""

from __future__ import annotations

from dataclasses import asdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any, Callable, Mapping, Sequence

from ..contracts import (
    Action,
    Artifact,
    Budget,
    Candidate,
    CheckRequirement,
    CheckResult,
    ContractError,
    Cost,
    Metric,
    Observation,
    RunReceipt,
    Task,
    canonical_json,
    file_sha256,
)
from ..evidence import assess, JsonlRecorder
from ..runner import run_campaign
from .components import summarize_cost, validate_group_splits


def _write(path: Path, payload: Any) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(
            json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n"
        )


def _prepare_output(output: str | Path) -> Path:
    root = Path(output).resolve()
    if root.exists() and any(root.iterdir()):
        raise ContractError(f"Course run output must be new or empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _physical_acceptance_status(summary: Mapping[str, Any]) -> str:
    if summary.get("all_required_passed"):
        return "pass"
    if any(item.get("status") == "unresolved" for item in summary.get("checks", [])):
        return "unresolved"
    return "fail"


def validate_student_context(
    documents: Sequence[Mapping[str, Any]],
    returned: Sequence[Mapping[str, Any]],
    *,
    word_budget: int,
    byte_budget: int | None = None,
) -> tuple[dict, ...]:
    """Independently bind student retrieval excerpts to allowed source text."""
    if type(word_budget) is not int or word_budget < 0:
        raise ContractError("Context word budget must be a nonnegative integer")
    if byte_budget is not None and (type(byte_budget) is not int or byte_budget < 0):
        raise ContractError("Context byte budget must be a nonnegative integer")
    permitted = {}
    for source in documents:
        if not isinstance(source, Mapping):
            raise ContractError("Allowed context sources must be records")
        required = (
            "source_id",
            "partition",
            "text",
            "text_sha256",
            "source",
            "file_sha256",
        )
        if any(
            not isinstance(source.get(key), str) or not source[key] for key in required
        ):
            raise ContractError(
                "Allowed sources need content, partition, and file identities"
            )
        if source["partition"] not in ("train", "dev", "specification"):
            raise ContractError(
                "Final-test or undeclared sources cannot enter retrieval"
            )
        if (
            hashlib.sha256(source["text"].encode("utf-8")).hexdigest()
            != source["text_sha256"]
        ):
            raise ContractError(
                "Allowed source text no longer matches its content hash"
            )
        if source["source_id"] in permitted:
            raise ContractError("Allowed source identities must be unique")
        permitted[source["source_id"]] = source
    if not isinstance(returned, Sequence) or isinstance(returned, (str, bytes)):
        raise ContractError("Retriever must return a sequence of attributed excerpts")
    checked, total_words, total_bytes = [], 0, 0
    for excerpt in returned:
        if not isinstance(excerpt, Mapping):
            raise ContractError("Retrieved excerpts must be records")
        source = permitted.get(excerpt.get("source_id"))
        text = excerpt.get("text")
        if source is None:
            raise ContractError("Retriever returned a forged or unapproved source")
        if (
            excerpt.get("partition") != source["partition"]
            or excerpt.get("source") != source["source"]
            or excerpt.get("file_sha256") != source["file_sha256"]
        ):
            raise ContractError("Retriever changed source partition or file identity")
        if not isinstance(text, str) or not text.strip():
            raise ContractError("Retrieved excerpts must contain text")
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != excerpt.get(
            "text_sha256"
        ):
            raise ContractError(
                "Retrieved excerpt does not match its declared content hash"
            )
        normalize = lambda value: " ".join(value.split())
        if normalize(text) not in normalize(source["text"]):
            raise ContractError(
                "Retrieved excerpt content is not present in its allowed source"
            )
        total_words += len(text.split())
        total_bytes += len(source["source_id"].encode("utf-8")) + len(
            text.encode("utf-8")
        )
        checked.append(dict(excerpt))
    if total_words > word_budget:
        raise ContractError(
            "Retriever exceeded the independently checked context word budget"
        )
    if byte_budget is not None and total_bytes > byte_budget:
        raise ContractError(
            "Retriever exceeded the independently checked context byte budget"
        )
    return tuple(checked)


def summarize_campaign_receipt_cost(
    component, campaign_report: Mapping[str, Any]
) -> dict[str, Any]:
    """Use Lab 3's summarizer, then verify it against retained measured receipts."""
    if not callable(getattr(component, "summarize_cost", None)):
        raise ContractError("Lab 3 cost component must implement summarize_cost")
    receipts, independent_rows = [], []
    runs = tuple(campaign_report.get("development", ())) + tuple(
        campaign_report.get("final_test", ())
    )
    for run in runs:
        campaign = run.get("campaign", {})
        task_id = campaign.get("task_id")
        for observation in campaign.get("observations", ()):
            raw = observation.get("receipt")
            if raw is None:
                continue
            receipt = _decode_run_receipt(raw)
            if (
                receipt.task_id != task_id
                or receipt.candidate_digest != observation.get("candidate_digest")
                or receipt.mode != "fresh"
            ):
                raise ContractError(
                    "Lab 3 cost input is not the exact retained fresh campaign receipt"
                )
            for artifact in receipt.output_artifacts:
                artifact.validate(receipt.output_root or "")
            receipts.append(receipt)
            independent_rows.append(
                {
                    "task_id": receipt.task_id,
                    "candidate_digest": receipt.candidate_digest,
                    "mode": receipt.mode,
                    "execution_status": receipt.execution_status,
                    "wall_seconds": receipt.cost.wall_seconds,
                }
            )
    if not receipts:
        raise ContractError(
            "Lab 9 campaign retained no measured receipts for Lab 3 cost analysis"
        )
    result = component.summarize_cost(tuple(receipts))
    if not isinstance(result, Mapping) or result.get("rows") != independent_rows:
        raise ContractError(
            "Lab 3 cost rows differ from the retained candidate receipts"
        )
    expected_total = sum(item["wall_seconds"] for item in independent_rows)
    expected_fresh = sum(
        item["wall_seconds"] for item in independent_rows if item["mode"] == "fresh"
    )
    if (
        result.get("total_wall_seconds") != expected_total
        or result.get("fresh_wall_seconds") != expected_fresh
    ):
        raise ContractError(
            "Lab 3 reported cost totals differ from retained receipt values"
        )
    return dict(result)


def _decode_run_receipt(raw: Any) -> RunReceipt:
    """Rebuild nested typed evidence from the campaign's serialized receipt."""
    if isinstance(raw, RunReceipt):
        return raw
    if not isinstance(raw, Mapping):
        raise ContractError(
            "Campaign receipt must be a typed receipt or serialized mapping"
        )
    try:
        return RunReceipt(
            task_id=raw["task_id"],
            candidate_digest=raw["candidate_digest"],
            mode=raw["mode"],
            execution_status=raw["execution_status"],
            tool=raw["tool"],
            tool_version=raw["tool_version"],
            checks=tuple(
                item if isinstance(item, CheckResult) else CheckResult(**item)
                for item in raw.get("checks", ())
            ),
            metrics={
                name: item if isinstance(item, Metric) else Metric(**item)
                for name, item in raw.get("metrics", {}).items()
            },
            cost=raw.get("cost")
            if isinstance(raw.get("cost"), Cost)
            else Cost(**raw.get("cost", {})),
            details=raw.get("details", ""),
            output_root=raw.get("output_root"),
            output_artifacts=tuple(
                item if isinstance(item, Artifact) else Artifact(**item)
                for item in raw.get("output_artifacts", ())
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError(
            f"Campaign receipt is incomplete or malformed: {exc}"
        ) from exc


def _sum_attempt_cost(rows: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    keys = sorted(
        {
            key
            for row in rows
            for key, value in row.get("cost", {}).items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
    )
    return {
        key: sum(float(row.get("cost", {}).get(key, 0.0)) for row in rows)
        for key in keys
    }


def _comparison_inputs(campaign: Mapping[str, Any], candidate_budget: int):
    """Construct immutable per-arm facts from held-out campaign receipts."""
    comparison_cases = {row["case_id"]: row for row in campaign.get("comparison", ())}
    final_runs = tuple(campaign.get("final_test", ()))
    groups = sorted({row["group_id"] for row in comparison_cases.values()})
    method_names = ("adapted", "unadapted", "enumeration", "constant")
    inputs, expected = [], {}
    shared_cost = deepcopy(campaign.get("cost", {}))
    for method in method_names:
        case_inputs, expected_cases, all_receipts, method_runs = [], [], [], []
        for case_id, case in comparison_cases.items():
            runs = [
                row
                for row in final_runs
                if row.get("case_id") == case_id and row.get("arm") == method
            ]
            method_runs.extend(runs)
            observations = [
                observation
                for run in runs
                for observation in run.get("campaign", {}).get("observations", ())
            ]
            receipts = [
                _decode_run_receipt(item["receipt"])
                for item in observations
                if item.get("receipt")
            ]
            all_receipts.extend(receipts)
            arm_summary = case.get("arms", {}).get(method, {})
            case_cost = _sum_attempt_cost(runs)
            tool_cost = summarize_cost(tuple(receipts)) if receipts else None
            outcomes = [
                {
                    "case_id": case_id,
                    "group_id": case["group_id"],
                    "eligible": bool(item.get("eligible")),
                    "action": item.get("action"),
                    "status": item.get("status"),
                    "candidate_digest": item.get("candidate_digest"),
                    "receipt": receipt,
                }
                for item, receipt in zip(
                    observations,
                    [
                        _decode_run_receipt(item["receipt"])
                        if item.get("receipt")
                        else None
                        for item in observations
                    ],
                )
            ]
            case_input = {
                "case_id": case_id,
                "group_id": case["group_id"],
                "objective": deepcopy(case["objective"]),
                "candidate_budget": candidate_budget,
                "outcomes": outcomes,
                "best": deepcopy(arm_summary.get("best")),
                "attempt_cost": case_cost,
                "tool_receipt_cost": tool_cost,
            }
            case_inputs.append(case_input)
            expected_cases.append(
                {
                    "case_id": case_id,
                    "group_id": case["group_id"],
                    "objective": deepcopy(case["objective"]),
                    "candidate_budget": candidate_budget,
                    "outcome_count": len(observations),
                    "eligible_count": sum(
                        bool(item.get("eligible")) for item in observations
                    ),
                    "best": deepcopy(arm_summary.get("best")),
                    "attempt_cost": case_cost,
                    "tool_receipt_cost": tool_cost,
                }
            )
        attempt_cost = _sum_attempt_cost(method_runs)
        tool_cost = summarize_cost(tuple(all_receipts)) if all_receipts else None
        inputs.append(
            {
                "method": method,
                "groups": groups,
                "objective": deepcopy(campaign.get("objective")),
                "candidate_budget": candidate_budget,
                "cases": case_inputs,
                "attempt_cost": attempt_cost,
                "tool_receipt_cost": tool_cost,
            }
        )
        expected[method] = {
            "method": method,
            "groups": groups,
            "objective": deepcopy(campaign.get("objective")),
            "candidate_budget": candidate_budget,
            "outcome_count": sum(row["outcome_count"] for row in expected_cases),
            "eligible_count": sum(row["eligible_count"] for row in expected_cases),
            "cases": expected_cases,
            "attempt_cost": attempt_cost,
            "tool_receipt_cost": tool_cost,
        }
    return inputs, groups, expected, shared_cost


def _validate_comparison_result(
    result: Any,
    groups: Sequence[str],
    expected: Mapping[str, Any],
    campaign_cost: Mapping[str, Any],
) -> dict:
    if not isinstance(result, Mapping) or result.get("evaluation_groups") != list(
        groups
    ):
        raise ContractError(
            "Lab 9 comparison omitted or changed held-out evaluation groups"
        )
    if result.get("campaign_cost") != campaign_cost:
        raise ContractError(
            "Lab 9 comparison omitted or changed the single shared campaign cost ledger"
        )
    if result.get("cost_allocation") != {
        "campaign_cost": "shared_campaign_total_reported_once",
        "method_costs": "overlapping_breakdowns_not_additive",
    }:
        raise ContractError(
            "Lab 9 comparison must label shared and overlapping costs explicitly"
        )
    methods = result.get("methods")
    if not isinstance(methods, list) or len(methods) != len(expected):
        raise ContractError("Lab 9 comparison must retain all four matched methods")
    actual = {}
    for row in methods:
        if not isinstance(row, Mapping) or row.get("method") in actual:
            raise ContractError(
                "Lab 9 comparison methods must be distinct named records"
            )
        actual[row["method"]] = row
    if set(actual) != set(expected):
        raise ContractError("Lab 9 comparison omitted or added a held-out baseline")
    required = (
        "groups",
        "objective",
        "candidate_budget",
        "outcome_count",
        "eligible_count",
        "cases",
        "attempt_cost",
        "tool_receipt_cost",
    )
    for name, facts in expected.items():
        row = actual[name]
        if "shared_campaign_cost" in row or any(
            row.get(key) != facts[key] for key in required
        ):
            raise ContractError(
                f"Lab 9 comparison changed measured outcomes, bests, units, or costs for {name}"
            )
    return dict(result)


def _execute_student_comparison(
    component: Any,
    summaries: Sequence[Mapping[str, Any]],
    groups: Sequence[str],
    expected: Mapping[str, Any],
    campaign_cost: Mapping[str, Any],
) -> dict:
    student_input = deepcopy(summaries)
    immutable_input = deepcopy(student_input)
    result = component.compare_campaigns(
        student_input,
        evaluation_groups=list(groups),
        campaign_cost=deepcopy(campaign_cost),
    )
    if student_input != immutable_input:
        raise ContractError("Lab 9 comparison mutated its held-out evidence input")
    return _validate_comparison_result(result, groups, expected, campaign_cost)


def _adapted_winner_artifacts(
    campaign_root: str | Path,
    campaign_report: Mapping[str, Any],
    *,
    include_objects: bool = False,
) -> list[dict[str, Any]]:
    """Resolve each held-out adapted winner to its immutable retained candidate files."""
    root = Path(campaign_root).resolve(strict=True)
    report = campaign_report
    result = []
    summaries = report.get("comparison", [])
    for case in summaries:
        best = case.get("arms", {}).get("adapted", {}).get("best")
        if not best:
            continue
        case_id, expected_digest = case.get("case_id"), best.get("candidate_digest")
        runs = [
            item
            for item in report.get("final_test", ())
            if item.get("case_id") == case_id
            and item.get("arm") == "adapted"
            and any(
                observation.get("candidate_digest") == expected_digest
                for observation in item.get("campaign", {}).get("observations", ())
            )
        ]
        if len(runs) != 1:
            raise ContractError(
                f"Cannot uniquely resolve held-out adapted winner {case_id}"
            )
        run = runs[0]
        slot = root / "test" / case_id / "adapted" / f"slot-{run['slot']:03d}"
        event_path = slot / "events.jsonl"
        if not event_path.is_file():
            raise ContractError(
                f"Retained campaign slot is missing for adapted winner {case_id}"
            )
        events = [
            json.loads(line)
            for line in event_path.read_text(encoding="utf-8").splitlines()
            if line
        ]
        matches = [
            event
            for event in events
            if event.get("event") == "candidate"
            and event.get("candidate_digest") == expected_digest
        ]
        if len(matches) != 1:
            raise ContractError(
                f"Retained candidate event does not uniquely bind winner {case_id}"
            )
        value = matches[0]["candidate"]
        candidate = Candidate(
            value["candidate_id"],
            value["task_id"],
            value["root"],
            Action(**value["action"]),
            tuple(Artifact(**item) for item in value["artifacts"]),
            value.get("parent_id"),
            value.get("task_digest", ""),
        )
        candidate.validate_files()
        candidate_root = Path(candidate.root).resolve()
        if candidate.digest != expected_digest or not candidate_root.is_relative_to(
            root
        ):
            raise ContractError("Adapted winner candidate identity or location changed")
        task_raw = run["task"]
        task = Task(
            task_raw["task_id"],
            tuple(task_raw["allowed_actions"]),
            tuple(CheckRequirement(**item) for item in task_raw["required_checks"]),
            task_raw["max_proposals"],
            task_raw["max_attempts"],
            task_raw["specification"],
        )
        if candidate.task_digest != task.digest or candidate.task_id != task.task_id:
            raise ContractError(
                "Adapted winner candidate does not belong to its retained held-out task"
            )
        hashes = {
            name: file_sha256(candidate_root / name)
            for name in (
                "core.v",
                "physical-config.json",
                "program.bin",
                "tables.bin",
                "reference/image.bin",
                "reference/goldens.npz",
            )
        }
        winner = dict(
            case_id=case_id,
            task_digest=task.digest,
            candidate_digest=candidate.digest,
            action=candidate.action.name,
            core_sha256=hashes["core.v"],
            config_sha256=hashes["physical-config.json"],
            program_sha256=hashes["program.bin"],
            tables_sha256=hashes["tables.bin"],
            image_sha256=hashes["reference/image.bin"],
            golden_sha256=hashes["reference/goldens.npz"],
            token_count=task.specification.get("token_count"),
            candidate_root=str(candidate_root),
        )
        if include_objects:
            observation = next(
                item
                for item in run["campaign"]["observations"]
                if item.get("candidate_digest") == expected_digest
            )
            winner["_candidate"] = candidate
            winner["_functional_receipt"] = _decode_run_receipt(observation["receipt"])
        result.append(winner)
    return result


def _architect_review_template(
    *,
    comparison_artifact: Mapping[str, str],
    adapted_winners: Sequence[Mapping[str, Any]],
    physical_output: str | Path | None,
    physical_candidate_core: str | Path | None,
    physical_candidate_config: str | Path | None,
    mapped_receipt_path: str | Path | None,
    final_acceptance: Mapping[str, Any],
) -> dict[str, Any]:
    """Prepare a human disposition form without recording or inferring a review."""
    candidates = []
    for winner in adapted_winners:
        candidate_root = Path(winner["candidate_root"]).resolve()
        candidates.append(
            {
                "case_id": winner["case_id"],
                "task_digest": winner["task_digest"],
                "candidate_digest": winner["candidate_digest"],
                "action": winner["action"],
                "candidate_directory": str(candidate_root),
                "rtl": {
                    "path": str(candidate_root / "core.v"),
                    "sha256": winner["core_sha256"],
                },
                "physical_config": {
                    "path": str(candidate_root / "physical-config.json"),
                    "sha256": winner["config_sha256"],
                },
                "program_sha256": winner["program_sha256"],
                "tables_sha256": winner["tables_sha256"],
                "image_sha256": winner["image_sha256"],
                "golden_sha256": winner["golden_sha256"],
            }
        )
    physical_refs: dict[str, Any] = {}
    if physical_candidate_core is not None:
        core = Path(physical_candidate_core).resolve()
        physical_refs["lab8_checked_rtl"] = {
            "path": str(core),
            "sha256": file_sha256(core),
        }
    if physical_candidate_config is not None:
        config = Path(physical_candidate_config).resolve()
        physical_refs["lab8_checked_physical_config"] = {
            "path": str(config),
            "sha256": file_sha256(config),
        }
    if physical_output is not None:
        receipt = Path(physical_output).resolve() / "receipt.json"
        physical_refs["lab8_flow_receipt"] = {
            "path": str(receipt),
            "sha256": file_sha256(receipt) if receipt.is_file() else None,
        }
    if mapped_receipt_path is not None:
        proof = Path(mapped_receipt_path).resolve()
        physical_refs["fresh_mapped_workload_proof"] = {
            "path": str(proof),
            "sha256": file_sha256(proof) if proof.is_file() else None,
        }
    limitations = [
        "This is one descriptive campaign and does not establish statistical or causal superiority.",
        "Human disposition does not override required functional, physical, or correspondence checks.",
    ]
    if isinstance(final_acceptance.get("reasons"), list):
        limitations.extend(str(reason) for reason in final_acceptance["reasons"])
    proof_reference = physical_refs.get("fresh_mapped_workload_proof")
    if not isinstance(proof_reference, Mapping) or not proof_reference.get("sha256"):
        limitations.append(
            "No fresh mapped-workload proof artifact was retained for this evaluation."
        )
    return {
        "schema": "nanochip-course-architect-review/v1",
        "status": "pending_review",
        "disposition": None,
        "allowed_dispositions": ["accept", "revise", "reject"],
        "reviewer": {"name": None, "role": None, "reviewed_at_utc": None},
        "review_rationale": "",
        "revision_requests": [],
        "comparison_evidence": dict(comparison_artifact),
        "selected_candidate_evidence": candidates,
        "physical_evidence_references": physical_refs,
        "mechanical_acceptance_status": final_acceptance.get("status", "unresolved"),
        "residual_limitations": limitations,
        "scope": (
            "Architectural disposition only. A human reviewer must enter their own identity and rationale; "
            "this template does not constitute approval or alter mechanical lab completion."
        ),
        "review_instructions": (
            "Preserve this hash-bound template. Copy it outside the retained attempt, "
            "for example into the workspace reviews directory, and complete the copy. "
            "Keep the original evidence paths and hashes in that review."
        ),
    }


def run_lab01(
    splitter: Callable,
    records_path: str | Path,
    output: str | Path,
    *,
    seed: str,
    fractions: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Run the student's split builder on retained experiment records."""
    source = Path(records_path).resolve(strict=True)
    root = _prepare_output(output)
    rows = [
        json.loads(line)
        for line in source.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if not rows:
        raise ContractError("Lab 1 needs nonempty input records")
    for row in rows:
        receipt = row.get("source_receipt")
        source_hash = row.get("source_sha256")
        if not isinstance(receipt, Mapping) or not isinstance(source_hash, str):
            raise ContractError("Every row needs a source receipt and source hash")
        artifact = Artifact(**receipt)
        source_root = Path(row.get("source_root", source.parent)).resolve(strict=True)
        artifact.validate(source_root)
        source_path = artifact.resolve(source_root)
        if source_path.suffix == ".json":
            try:
                receipt_payload = json.loads(source_path.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                receipt_payload = {}
        else:
            receipt_payload = {}
        if receipt_payload.get("mode") == "fresh":
            if receipt_payload.get("candidate_sha256") != source_hash:
                raise ContractError(
                    "Source receipt does not bind a fresh run to the candidate hash"
                )
        elif row.get("data_origin") == "repository_documentation":
            text = row.get("input_text")
            text_hash = (
                hashlib.sha256(text.encode("utf-8")).hexdigest()
                if isinstance(text, str)
                else None
            )
            if (
                artifact.sha256 != source_hash
                or row.get("input_text_sha256") != text_hash
                or not row.get("attribution")
                or not row.get("license")
            ):
                raise ContractError(
                    "Documentation record lacks a content-bound attribution receipt"
                )
        else:
            raise ContractError(
                "Source receipt must bind a fresh run or an attributed source document"
            )
    before = deepcopy(rows)
    result = tuple(splitter(deepcopy(rows), seed=seed, fractions=fractions))
    if len(result) != len(rows):
        raise ContractError("Split builder must preserve every record")
    validate_group_splits(result)
    for original, split in zip(before, result):
        unchanged = {key: value for key, value in split.items() if key != "split"}
        original_content = {
            key: value for key, value in original.items() if key != "split"
        }
        if canonical_json(original_content) != canonical_json(unchanged):
            raise ContractError(
                "Split builder changed a record besides its split field"
            )
        source_split = original.get("original_split", "train")
        if source_split == "test" and split["split"] != "test":
            raise ContractError("A frozen final-test source group cannot be reassigned")
        if source_split in ("dev", "development") and split["split"] == "train":
            raise ContractError(
                "A frozen development source group cannot enter training"
            )
    retained_sources = root / "sources"
    retained_sources.mkdir()
    retained = []
    source_copies = {}
    for row in result:
        artifact = Artifact(**row["source_receipt"])
        old_root = Path(row.get("source_root", source.parent)).resolve()
        old_path = artifact.resolve(old_root)
        key = artifact.sha256
        if key not in source_copies:
            relative = f"{key}{old_path.suffix}"
            shutil.copyfile(old_path, retained_sources / relative)
            source_copies[key] = Artifact.from_file(root, f"sources/{relative}")
        retained.append(
            dict(row, source_receipt=asdict(source_copies[key]), source_root=str(root))
        )
    from ..datasets.characterize import profile_records

    characterization = profile_records(retained)
    characterization_path = root / "characterization.json"
    _write(characterization_path, characterization)
    record_path = root / "records.jsonl"
    with record_path.open("x", encoding="utf-8") as stream:
        for row in retained:
            stream.write(canonical_json(dict(row)) + "\n")
    counts = {
        name: sum(row["split"] == name for row in retained)
        for name in ("train", "dev", "test")
    }
    group_counts = {
        name: len({row["group_id"] for row in result if row["split"] == name})
        for name in ("train", "dev", "test")
    }
    retained_source = root / "input-records.jsonl"
    shutil.copyfile(source, retained_source)
    manifest = {
        "schema": "nanochip-course-split/v1",
        "source_records": {
            "path": retained_source.name,
            "sha256": file_sha256(retained_source),
        },
        "records": {"path": "records.jsonl", "sha256": file_sha256(record_path)},
        "characterization": {
            "path": characterization_path.name,
            "sha256": file_sha256(characterization_path),
        },
        "seed": seed,
        "fractions": dict(fractions or {"train": 0.6, "dev": 0.2, "test": 0.2}),
        "record_counts": counts,
        "group_counts": group_counts,
        "provenance": "Source artifacts were copied into this run; only split membership was assigned to records.",
    }
    _write(root / "split-manifest.json", manifest)
    return {
        "status": "pass",
        "output": str(root),
        "manifest": manifest,
        "characterization": characterization,
        "check": {"name": "grouped_split_preserves_records", "status": "pass"},
    }


def _oracle_pack(values: Sequence[int]) -> bytes:
    """Independent bit-position expression used only by the checker."""
    result = bytearray()
    for index in range(0, len(values), 2):
        result.append((values[index] & 15) | ((values[index + 1] & 15) << 4))
    return bytes(result)


def _oracle_unpack(packed: Sequence[int]) -> tuple[int, ...]:
    return tuple(
        value for byte in packed for value in ((byte >> 0) & 15, (byte >> 4) & 15)
    )


def run_lab02(
    pack: Callable,
    unpack: Callable,
    values: Sequence[int],
    output: str | Path,
    *,
    source_identity: str,
) -> dict[str, Any]:
    """Check an actual packed-weight conversion against an independent oracle."""
    root = _prepare_output(output)
    values = tuple(values)
    expected_bytes = _oracle_pack(values)
    encoded = pack(values)
    if isinstance(encoded, list):
        encoded = bytes(encoded)
    elif isinstance(encoded, tuple):
        encoded = bytes(encoded)
    if not isinstance(encoded, bytes) or encoded != expected_bytes:
        raise ContractError("Student packer changed the frozen int4 byte order")
    decoded = tuple(unpack(encoded))
    expected_values = _oracle_unpack(expected_bytes)
    if decoded != expected_values:
        raise ContractError(
            "Student unpacker disagrees with the independent nibble oracle"
        )
    payload = {
        "schema": "nanochip-course-int4-check/v1",
        "source_identity": source_identity,
        "input_values": list(values),
        "packed_hex": encoded.hex(),
        "decoded_values": list(decoded),
        "oracle": "independent low-nibble/high-nibble bit extraction",
        "scope": "int4 serialization vector; not a complete workload or RTL check",
    }
    _write(root / "int4-vectors.json", payload)
    return {
        "status": "pass",
        "output": str(root),
        "result": payload,
        "check": {"name": "int4_pack_unpack_matches_oracle", "status": "pass"},
    }


def run_lab03(
    adapter: Callable, task: Task, candidate: Candidate, output: str | Path
) -> dict[str, Any]:
    """Exercise receipt parsing and fail-closed scoped eligibility."""
    root = _prepare_output(output)
    base = dict(
        task_id=task.task_id,
        candidate_digest=candidate.digest,
        tool="course-receipt-fixture",
        tool_version="fixture-v1",
        cost={"wall_seconds": 1.0},
        output_root=None,
        output_artifacts=[],
    )
    cases = (
        (
            "passing_scoped_fixture",
            dict(
                base,
                mode="fixture",
                execution_status="success",
                checks=[
                    dict(
                        name=task.required_checks[0].name,
                        status="pass",
                        scope=task.required_checks[0].scope,
                    )
                ],
            ),
            False,
        ),
        (
            "tool_error",
            dict(base, mode="fixture", execution_status="error", checks=[]),
            False,
        ),
        (
            "wrong_scope",
            dict(
                base,
                mode="fixture",
                execution_status="success",
                checks=[
                    dict(
                        name=task.required_checks[0].name,
                        status="pass",
                        scope="wrong-scope",
                    )
                ],
            ),
            False,
        ),
    )
    outcomes = []
    for name, raw, expected_eligible in cases:
        receipt = adapter(raw, task, candidate)
        observation = assess(task, candidate, receipt)
        if observation.eligible is not expected_eligible:
            raise ContractError(f"Receipt adapter mishandled {name}")
        outcomes.append(
            {
                "case": name,
                "execution_status": receipt.execution_status,
                "mode": receipt.mode,
                "eligible": observation.eligible,
                "checks": [asdict(item) for item in observation.checks],
            }
        )
    _write(
        root / "receipt-contract-check.json",
        {
            "schema": "nanochip-course-receipt-check/v1",
            "scope": "constructed interface cases; not tool measurements",
            "cases": outcomes,
        },
    )
    return {
        "status": "pass",
        "output": str(root),
        "outcomes": outcomes,
        "check": {"name": "receipt_identity_and_fail_closed_states", "status": "pass"},
    }


def run_lab04(
    component,
    records_path: str | Path,
    model_io_contract: Mapping[str, Any],
    output: str | Path,
    *,
    budget: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Train from Lab 1's training partition and verify checkpoint reload."""
    from ..model_io import ModelIOContract
    from ..models import language

    root = _prepare_output(output)
    contract = ModelIOContract.from_dict(model_io_contract)
    rows = [
        json.loads(line)
        for line in Path(records_path).read_text(encoding="utf-8").splitlines()
        if line
    ]
    training = [row for row in rows if row.get("split") == "train"]
    if not training:
        raise ContractError("Lab 4 requires Lab 1 training records")
    checkpoint = root / "checkpoint"
    metadata = component.train(
        training, checkpoint, model_io_contract=contract, **dict(budget or {})
    )
    if not isinstance(metadata, Mapping) or not metadata.get("parameters_changed"):
        raise ContractError(
            "Training must retain a record showing actual parameter updates"
        )
    model = language.load_model(
        checkpoint,
        expected_model_io_contract=contract,
        model_factory=component.build_model,
    )
    if model.model_io_contract != contract:
        raise ContractError(
            "Reloaded checkpoint changed the declared model input contract"
        )
    report = {
        "schema": "nanochip-course-training-check/v1",
        "training_record_count": len(training),
        "checkpoint_sha256": model.checkpoint_sha256,
        "model_io_contract": contract.to_dict(),
        "parameters_changed": metadata["parameters_changed"],
        "parameter_count": metadata["parameter_count"],
        "scope": "checkpoint integrity and train-partition updates; no design benefit claim",
    }
    _write(root / "training-check.json", report)
    return {
        "status": "pass",
        "output": str(root),
        "report": report,
        "check": {
            "name": "checkpoint_reloads_with_declared_contract",
            "status": "pass",
        },
    }


def run_lab05(
    component,
    checkpoint: str | Path,
    model_io_contract: Mapping[str, Any],
    input_text: str | None,
    output: str | Path,
    *,
    documents: Sequence[Mapping[str, Any]] | None = None,
    context_limit: int = 24,
    model_factory=None,
    task: Task | None = None,
    materializer=None,
    backend=None,
    seed: int = 1,
    prompt_index: int = 0,
    tokens: list[int] | None = None,
    receipt_adapter=None,
) -> dict[str, Any]:
    """Retrieve context, infer an action, and run it through the complete core by default."""
    from ..context import with_context
    from ..model_io import ModelIOContract
    from ..models.language import load_model
    from ..teaching_core import TeachingCoreBackend, TeachingCoreMaterializer, make_task

    root = _prepare_output(output)
    io_contract = ModelIOContract.from_dict(model_io_contract)
    actual_target = task is None and materializer is None and backend is None
    if task is None:
        task = make_task(
            seed=seed, prompt_index=prompt_index, split="development", tokens=tokens
        )
    if not hasattr(component, "serialize"):
        raise ContractError("Lab 5 component must implement task serialization")
    serialized = component.serialize(task, ()) if input_text is None else input_text
    allowed_docs = deepcopy(tuple(documents or ()))
    student_docs = deepcopy(allowed_docs)
    selected_context = component.retrieve(serialized, student_docs, limit=context_limit)
    context = validate_student_context(
        allowed_docs, selected_context, word_budget=context_limit
    )
    enriched = with_context(serialized, context)
    model = load_model(
        checkpoint, expected_model_io_contract=io_contract, model_factory=model_factory
    )
    prediction = model.predict(enriched, model_io_contract=io_contract)
    action_name = component.parse_action(prediction["action"], io_contract.actions)
    if actual_target:
        materializer, backend = TeachingCoreMaterializer(), TeachingCoreBackend()
    elif task is None or materializer is None or backend is None:
        raise ContractError(
            "A test target requires task, materializer, and backend together"
        )
    if tuple(io_contract.actions) != tuple(task.allowed_actions):
        raise ContractError(
            "Model action contract must match the complete core's legal action set"
        )
    task = Task(
        task.task_id,
        task.allowed_actions,
        task.required_checks,
        max_proposals=1,
        max_attempts=1,
        specification=task.specification,
    )
    if receipt_adapter is not None:
        from .composition import ReceiptAdapterBackend

        backend = ReceiptAdapterBackend(backend, receipt_adapter)

    class Proposer:
        def propose(self, frozen_task, history, budget):
            return Action(action_name)

    events = JsonlRecorder(root / "events.jsonl")
    campaign = run_campaign(
        task, Proposer(), materializer, backend, root / "attempts", events
    )
    if not campaign.observations or campaign.observations[0].action.name != action_name:
        raise ContractError("Parsed student action did not reach the shared harness")
    observation = campaign.observations[0]
    if actual_target and not observation.eligible:
        raise ContractError("Complete-core numerical and protocol checks did not pass")
    if not actual_target and observation.eligible:
        raise ContractError("Fixture harness outcome cannot qualify as measured")
    report = {
        "schema": "nanochip-course-inference-check/v1",
        "action": action_name,
        "checkpoint_sha256": model.checkpoint_sha256,
        "model_io_contract_sha256": io_contract.digest,
        "model_input": {
            "text": enriched,
            "sha256": hashlib.sha256(enriched.encode("utf-8")).hexdigest(),
            "serializer_input": serialized,
            "retrieved_context": [dict(item) for item in context],
            "context_word_budget": context_limit,
        },
        "retrieved_sources": [item["source_id"] for item in context],
        "harness_campaign": asdict(campaign),
        "scope": (
            "fresh complete-core functional checks; no physical acceptance"
            if actual_target
            else "test-only fixture wiring; no measured result"
        ),
    }
    _write(root / "inference-check.json", report)
    return {
        "status": "pass",
        "output": str(root),
        "report": report,
        "check": {"name": "legal_action_reaches_shared_harness", "status": "pass"},
    }


def run_lab06(
    policy,
    output: str | Path,
    *,
    task: Task | None = None,
    materializer=None,
    backend=None,
    receipt_adapter=None,
) -> dict[str, Any]:
    """Run the search policy through either the real target or an interface fixture."""
    root = _prepare_output(output)
    actual_target = task is not None or materializer is not None or backend is not None
    if actual_target and (task is None or materializer is None or backend is None):
        raise ContractError("A real search run needs a task, materializer, and backend")
    if not actual_target:
        task = Task(
            "course-search-contract-v1",
            ("candidate_a", "candidate_b"),
            (CheckRequirement("candidate_identity", "fixture"),),
            max_proposals=3,
            max_attempts=2,
        )
    predictions = {}

    class CheckedMaterializer:
        def materialize(self, frozen_task, action, workspace):
            if actual_target:
                candidate = materializer.materialize(frozen_task, action, workspace)
                if not hasattr(policy, "predict"):
                    raise ContractError(
                        "A real search run requires the student's predictor"
                    )
                prediction = policy.predict(frozen_task, candidate)
                if not isinstance(prediction, Mapping) or not isinstance(
                    prediction.get("metrics"), Mapping
                ):
                    raise ContractError(
                        "Predictor must return metric estimates and uncertainty"
                    )
                estimates = prediction["metrics"]
                if "cycles" not in estimates:
                    raise ContractError("Core predictor must estimate cycles")
                for estimate in estimates.values():
                    if (
                        not isinstance(estimate, Mapping)
                        or type(estimate.get("value")) not in (int, float)
                        or type(estimate.get("uncertainty")) not in (int, float)
                        or estimate["uncertainty"] < 0
                        or not estimate.get("unit")
                    ):
                        raise ContractError(
                            "Predictions need a numeric value, unit, and nonnegative uncertainty"
                        )
                predictions[candidate.digest] = dict(prediction)
                return candidate
            candidate_root = Path(workspace) / "candidate"
            candidate_root.mkdir()
            file = candidate_root / "action.json"
            _write(file, {"action": action.name})
            return Candidate(
                action.name,
                frozen_task.task_id,
                str(candidate_root),
                action,
                (Artifact.from_file(candidate_root, "action.json"),),
                task_digest=frozen_task.digest,
            )

    class FixtureBackend:
        def evaluate(self, frozen_task, candidate):
            return RunReceipt(
                frozen_task.task_id,
                candidate.digest,
                "fixture",
                "success",
                "course-search-fixture",
                "fixture-v1",
                checks=(CheckResult("candidate_identity", "pass", "fixture"),),
                cost=Cost(0.0),
            )

    class Proposer:
        def propose(self, frozen_task, history, budget):
            proposals = tuple(Action(name) for name in frozen_task.allowed_actions)
            return policy.choose(frozen_task, proposals, history, budget)

    events = JsonlRecorder(root / "events.jsonl")
    run_backend = backend if actual_target else FixtureBackend()
    if receipt_adapter is not None and actual_target:
        from .composition import ReceiptAdapterBackend

        run_backend = ReceiptAdapterBackend(run_backend, receipt_adapter)
    campaign = run_campaign(
        task, Proposer(), CheckedMaterializer(), run_backend, root / "attempts", events
    )
    names = [item.action.name for item in campaign.observations if item.action]
    if len(set(names)) < 2:
        raise ContractError("Search must compare at least two distinct legal actions")
    if not actual_target and any(item.eligible for item in campaign.observations):
        raise ContractError("Fixture tool results cannot qualify as measured outcomes")
    prediction_rows = []
    if actual_target:
        for observation in campaign.observations:
            if observation.receipt is None:
                continue
            prediction = predictions[observation.candidate_digest]
            actual = observation.receipt.metrics.get("cycles")
            predicted = prediction["metrics"]["cycles"]
            if actual is None or predicted["unit"] != actual.unit:
                raise ContractError(
                    "Predicted and measured cycle metrics need matching units"
                )
            prediction_rows.append(
                {
                    "candidate_digest": observation.candidate_digest,
                    "action": observation.action.name,
                    "predicted_cycles": predicted["value"],
                    "actual_cycles": actual.value,
                    "uncertainty_cycles": predicted["uncertainty"],
                    "absolute_error_cycles": abs(predicted["value"] - actual.value),
                    "eligible": observation.eligible,
                }
            )
    result = {
        "schema": "nanochip-course-search-check/v1",
        "campaign": asdict(campaign),
        "predictions": prediction_rows,
        "scope": (
            "fresh full-core RTL measurements; not physical acceptance"
            if actual_target
            else "fixture interface exercise; no hardware measurements"
        ),
    }
    _write(root / "campaign.json", result)
    return {
        "status": "pass",
        "output": str(root),
        "campaign": result,
        "check": {"name": "feedback_changes_next_legal_action", "status": "pass"},
    }


def run_lab07(
    transform,
    task: Task,
    source_candidates: Mapping[str, Candidate],
    backend,
    output: str | Path,
    *,
    receipt_adapter=None,
) -> dict[str, Any]:
    """Transform Lab 6's exact candidates and rerun complete numerical checks."""
    import re

    root = _prepare_output(output)
    if receipt_adapter is not None:
        from .composition import ReceiptAdapterBackend

        backend = ReceiptAdapterBackend(backend, receipt_adapter)
    candidate_root = root / "design" / "candidate"
    candidate_root.mkdir(parents=True)
    results = []
    for action_name in task.allowed_actions:
        original = source_candidates.get(action_name)
        if original is None or original.task_digest != task.digest:
            raise ContractError(
                "Lab 7 needs each exact candidate produced by the current Lab 6 task"
            )
        original.validate_files()
        action_workspace = root / "design" / f"build-{action_name}"
        action_workspace.mkdir()
        action = Action(action_name)
        copied_root = action_workspace / "candidate"
        shutil.copytree(original.root, copied_root)
        candidate = Candidate(
            original.candidate_id,
            original.task_id,
            str(copied_root),
            original.action,
            original.artifacts,
            original.parent_id,
            original.task_digest,
        )
        source_path = Path(candidate.root) / "core.v"
        frozen_source = source_path.read_text(encoding="utf-8")
        baseline, count = re.subn(
            r"parameter integer MUL_BITS = \d+",
            "parameter integer MUL_BITS = 1",
            frozen_source,
        )
        if count != 1:
            raise ContractError(
                "Materialized core has no unique multiplier-width control"
            )
        transformed = transform(baseline, action)
        if not isinstance(transformed, str) or transformed != frozen_source:
            raise ContractError(
                "Student architecture transform differs from the frozen legal action"
            )
        source_path.write_text(transformed, encoding="utf-8")
        candidate.validate_files()
        receipt = backend.evaluate(task, candidate)
        observation = assess(task, candidate, receipt)
        if not observation.eligible:
            failed = [
                {"name": item.name, "status": item.status, "scope": item.scope}
                for item in observation.checks
                if item.status != "pass"
            ]
            raise ContractError(
                f"Full-core numerical/differential checks did not pass: {failed}"
            )
        destination = candidate_root / action_name
        shutil.copytree(candidate.root, destination)
        _write(
            destination / "candidate.json",
            {
                "candidate_id": candidate.candidate_id,
                "candidate_digest": candidate.digest,
                "task_digest": task.digest,
                "action": asdict(action),
                "core_sha256": file_sha256(source_path),
                "receipt": asdict(receipt),
                "observation": asdict(observation),
                "scope": "complete mathematical teaching-core RTL; physical acceptance remains separate",
            },
        )
        results.append(
            {
                "action": action_name,
                "candidate_digest": candidate.digest,
                "core_sha256": file_sha256(source_path),
                "eligible": observation.eligible,
                "checks": [
                    {"name": item.name, "status": item.status, "scope": item.scope}
                    for item in observation.checks
                ],
                "cycles": receipt.metrics.get("cycles").value
                if receipt.metrics.get("cycles")
                else None,
            }
        )
    if len(results) != len(task.allowed_actions):
        raise ContractError("Every frozen action must receive a complete RTL execution")
    summary = {
        "schema": "nanochip-course-architecture-check/v1",
        "task_digest": task.digest,
        "candidates": results,
        "scope": "complete mathematical teaching-core numerical and differential checks; no physical acceptance",
    }
    _write(root / "design" / "architecture-check.json", summary)
    return {
        "status": "pass",
        "output": str(root),
        "report": summary,
        "check": {
            "name": "full_core_numerical_and_differential_checks",
            "status": "pass",
        },
    }


def run_lab09(
    component,
    training_component,
    representation_component,
    records_path: str | Path,
    base_checkpoint: str | Path,
    model_io_contract: Mapping[str, Any],
    output: str | Path,
    *,
    search_component=None,
    architecture_component=None,
    physical_component=None,
    receipt_component=None,
    weight_component=None,
    physical_evidence: Mapping[str, Any] | None = None,
    physical_candidate_core: str | Path | None = None,
    physical_candidate_config: str | Path | None = None,
    physical_candidate_action: str | None = None,
    physical_receipt_sha256: str | None = None,
    physical_output: str | Path | None = None,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Continue Lab 4's checkpoint through measured development feedback and held-out tests."""
    from ..campaign import (
        CampaignCase,
        CampaignObjective,
        CampaignTarget,
        run_learning_campaign,
    )
    from .composition import CourseComposition, assess_reused_physical_acceptance
    from ..model_io import ModelIOContract
    from ..teaching_core import TeachingCoreBackend, TeachingCoreMaterializer, make_task

    root = _prepare_output(output)
    settings = dict(config or {})
    io_contract = ModelIOContract.from_dict(model_io_contract)
    if (
        search_component is None
        or architecture_component is None
        or weight_component is None
        or receipt_component is None
    ):
        raise ContractError(
            "Lab 9 requires active Lab 2, Lab 3, Lab 6, and Lab 7 components"
        )
    rows = [
        json.loads(line)
        for line in Path(records_path).read_text(encoding="utf-8").splitlines()
        if line
    ]
    training = [row for row in rows if row.get("split") == "train"]
    if not training:
        raise ContractError("Lab 9 requires the active Lab 1 training partition")
    if tuple(io_contract.actions) != ("serial_mul1", "serial_mul2"):
        raise ContractError(
            "Lab 9 model contract must match the complete core action vocabulary"
        )
    objective = CampaignObjective(
        "cycles", "accelerator:nanochip_teaching_core", True, "cycles"
    )
    cases = []
    for split, seed, prompt, tokens in settings.get(
        "cases",
        (
            ("dev", 17, 0, [1]),
            ("dev", 18, 1, [2, 3]),
            ("test", 101, 0, [4, 5, 6]),
            ("test", 102, 1, [7, 8, 9, 10]),
        ),
    ):
        task = make_task(
            seed=seed,
            prompt_index=prompt,
            split="development" if split == "dev" else "test",
            tokens=tokens,
        )
        task_spec = dict(task.specification, campaign_objective=asdict(objective))
        task = Task(
            task.task_id,
            task.allowed_actions,
            task.required_checks,
            max_proposals=task.max_proposals,
            max_attempts=task.max_attempts,
            specification=task_spec,
        )
        cases.append(
            CampaignCase(
                f"{split}-seed{seed}-prompt{prompt}",
                f"weights-seed{seed}-prompt{prompt}-tokens{len(tokens)}",
                split,
                task,
            )
        )

    composition = CourseComposition(
        training_component=training_component,
        representation_component=representation_component,
        search_component=search_component,
        architecture_component=architecture_component,
        weight_component=weight_component,
        base_materializer=TeachingCoreMaterializer(),
        model_io_contract=io_contract,
        base_checkpoint=base_checkpoint,
        physical_component=physical_component,
        receipt_component=receipt_component,
    )
    try:
        base_training = json.loads(
            (Path(base_checkpoint) / "training.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(
            "Lab 9 requires the retained Lab 4 training-lineage record"
        ) from exc
    lineage_rows = base_training.get("training_records")
    if not isinstance(lineage_rows, list) or not lineage_rows:
        raise ContractError(
            "Lab 9 cannot verify which records trained the Lab 4 checkpoint"
        )
    test_cases = [case for case in cases if case.split == "test"]
    test_groups = {case.group_id for case in test_cases}
    test_ids = {case.case_id for case in test_cases}
    test_inputs = {composition.serialize(case.task, (), ()) for case in test_cases}
    for row in lineage_rows:
        if (
            row.get("group_id") in test_groups
            or row.get("case_id") in test_ids
            or row.get("input_text") in test_inputs
        ):
            raise ContractError(
                "Lab 4 checkpoint training lineage overlaps a Lab 9 final-test input or group"
            )
    composition.training.seed = settings.get("seed", 17)
    composition.training.pretrain_steps = settings.get("pretrain_steps", 120)
    composition.training.adapt_steps = settings.get("adapt_steps", 80)
    composition.training.max_seconds = settings.get("training_seconds", 60)

    campaign_dir = root / "evaluation" / "campaign"
    campaign_dir.parent.mkdir()
    measured_backend = TeachingCoreBackend(
        timeout_s=settings.get("check_timeout", 180),
        max_cycles=settings.get("max_cycles", 300_000_000),
    )
    if receipt_component is not None:
        from .composition import ReceiptAdapterBackend

        measured_backend = ReceiptAdapterBackend(measured_backend, receipt_component)
    report = run_learning_campaign(
        campaign_dir,
        cases=cases,
        training_records=training,
        training_root=Path(records_path).resolve().parent,
        method=composition,
        target=CampaignTarget(
            composition.materializer, measured_backend, composition.serialize
        ),
        objective=objective,
        candidate_budget=settings.get("candidate_budget", 2),
        retriever=composition.retriever(),
        context_words=settings.get("context_words", 24),
    )
    receipt_cost = summarize_campaign_receipt_cost(receipt_component, report)
    final_test = report["final_test"]
    summaries, groups, expected_comparison, shared_campaign_cost = _comparison_inputs(
        report, settings.get("candidate_budget", 2)
    )
    comparison = _execute_student_comparison(
        component, summaries, groups, expected_comparison, shared_campaign_cost
    )
    comparison_path = root / "evaluation" / "comparison.json"
    _write(comparison_path, comparison)
    comparison_artifact = {
        "path": "comparison.json",
        "sha256": file_sha256(comparison_path),
    }
    winner_details = _adapted_winner_artifacts(
        campaign_dir, report, include_objects=True
    )
    adapted_winners = [
        {key: value for key, value in item.items() if not key.startswith("_")}
        for item in winner_details
    ]
    physical_summary = None
    final_acceptance = {
        "status": "pending_final_physical",
        "reasons": ["no candidate-linked Lab 8 physical receipt was supplied"],
    }
    if physical_evidence is not None:
        if (
            physical_component is None
            or physical_candidate_core is None
            or physical_candidate_config is None
        ):
            raise ContractError(
                "Lab 8 evidence needs its active interpreter and exact candidate source/config"
            )
        physical_summary = composition.interpret_physical(
            physical_evidence, physical_candidate_core
        )
        mapped_workload_receipt = None
        if physical_output is not None and adapted_winners:
            from ..physical.correspondence import (
                run_correspondence,
                validate_correspondence,
            )

            selected = max(
                winner_details,
                key=lambda item: (item.get("token_count") or -1, item["case_id"]),
            )
            if selected["core_sha256"] == physical_summary[
                "candidate_core_sha256"
            ] and selected["config_sha256"] == file_sha256(physical_candidate_config):
                proof_dir = root / "evaluation" / "mapped-netlist-workload"
                run_correspondence(
                    physical_output,
                    selected["_candidate"],
                    selected["_functional_receipt"],
                    proof_dir,
                    timeout_s=settings.get("correspondence_timeout", 3600),
                    cores=settings.get("cores", 2),
                    mode=settings.get("physical_mode"),
                )
                proof_path = proof_dir / "receipt.json"
                proof = validate_correspondence(
                    proof_path,
                    candidate=selected["_candidate"],
                    physical_output=physical_output,
                    functional_output=selected["_functional_receipt"].output_root,
                )
                mapped_workload_receipt = dict(
                    status=proof["status"],
                    mode="fresh",
                    case_id=selected["case_id"],
                    task_digest=proof["task_digest"],
                    candidate_digest=proof["candidate_digest"],
                    core_sha256=selected["core_sha256"],
                    config_sha256=proof["physical_config_sha256"],
                    program_sha256=selected["program_sha256"],
                    tables_sha256=selected["tables_sha256"],
                    image_sha256=selected["image_sha256"],
                    mapped_netlist_sha256=proof["netlist_sha256"],
                    functional_golden_sha256=selected["golden_sha256"],
                    receipt_sha256=proof["receipt_sha256"],
                    proof_path=str(proof_path),
                    profiles=proof["profiles"],
                    formal_status=proof["formal_status"],
                    physical_ok=proof["physical_ok"],
                )
        adapted_actions = {
            arm["best"]["action"]
            for case in report["comparison"]
            if (arm := case["arms"]["adapted"]).get("best")
        }
        final_acceptance = assess_reused_physical_acceptance(
            adapted_actions=sorted(adapted_actions),
            physical_action=physical_candidate_action,
            candidate_config=physical_candidate_config,
            raw_receipt=physical_evidence,
            interpreted=physical_summary,
            receipt_sha256=physical_receipt_sha256,
            adapted_winners=adapted_winners,
            mapped_workload_receipt=mapped_workload_receipt,
        )
    mapped_receipt_path = (
        root / "evaluation" / "mapped-netlist-workload" / "receipt.json"
    )
    review_template = _architect_review_template(
        comparison_artifact={
            **comparison_artifact,
            "path": str(comparison_path.resolve()),
        },
        adapted_winners=adapted_winners,
        physical_output=physical_output,
        physical_candidate_core=physical_candidate_core,
        physical_candidate_config=physical_candidate_config,
        mapped_receipt_path=mapped_receipt_path
        if mapped_receipt_path.is_file()
        else None,
        final_acceptance=final_acceptance,
    )
    review_path = root / "evaluation" / "architect-review.json"
    _write(review_path, review_template)
    decision = {
        "schema": "nanochip-course-evaluation/v1",
        "campaign": report,
        "comparison": comparison,
        "comparison_artifact": comparison_artifact,
        "architect_review_template": {
            "path": "architect-review.json",
            "sha256": file_sha256(review_path),
            "status": "pending_review",
        },
        "component_provenance": composition.provenance(),
        "retrieval_input_selection": composition.representation.last_context_selection,
        "validated_receipt_cost": receipt_cost,
        "adapted_heldout_winner_artifacts": adapted_winners,
        "lab8_physical_evidence": physical_summary,
        "final_capstone_acceptance": final_acceptance,
        "scope": "same held-out complete-core cases and candidate budgets; physical acceptance is separate",
        "interpretation": "One campaign is a descriptive result, not a causal or statistical superiority claim.",
    }
    _write(root / "evaluation" / "decision.json", decision)
    integration_status = "pass" if report["success"] else "fail"
    acceptance_status = (
        "pass"
        if final_acceptance["status"] == "accepted_by_reused_lab8_evidence"
        else "unresolved"
    )
    checks_out = [
        {"name": "heldout_comparison_and_cost_report", "status": integration_status},
        {
            "name": "final_physical_acceptance_for_adapted_winner",
            "status": acceptance_status,
            "details": "; ".join(final_acceptance["reasons"]),
        },
    ]
    return {
        "status": "pass" if report["success"] else "fail",
        "output": str(root),
        "report": decision,
        "check": {
            "name": "heldout_comparison_and_cost_report",
            "status": integration_status,
        },
        "checks": checks_out,
    }


def _physical_task_backend(
    *,
    seed: int,
    prompt_index: int,
    split: str,
    tokens,
    check_timeout: float,
    physical_timeout: float,
    correspondence_timeout: float,
    cores: int,
    mode: str | None,
):
    """Freeze identical physical/correspondence budgets into task and backend."""
    from ..physical.teaching import TeachingCorePhysicalBackend, make_physical_task

    task = make_physical_task(
        seed=seed,
        prompt_index=prompt_index,
        split=split,
        tokens=tokens,
        check_timeout=check_timeout,
        physical_timeout=physical_timeout,
        cores=cores,
        correspondence_timeout=correspondence_timeout,
    )
    backend = TeachingCorePhysicalBackend(
        check_timeout=check_timeout,
        physical_timeout=physical_timeout,
        cores=cores,
        correspondence_timeout=correspondence_timeout,
        mode=mode,
    )
    return task, backend


def run_lab08(
    component,
    candidate_root: str | Path,
    output: str | Path,
    *,
    weight_component,
    architecture_component,
    check_timeout: float = 180,
    timeout_s: float = 14400,
    correspondence_timeout: float = 3600,
    cores: int = 1,
    mode: str | None = None,
) -> dict[str, Any]:
    """Run full functional/physical acceptance, including mapped-netlist correspondence."""
    from ..contracts import Action
    from ..teaching_core import TeachingCoreMaterializer
    from .composition import ArchitectureMaterializer, WeightCodecMaterializer

    root = _prepare_output(output)
    prior = Path(candidate_root).resolve(strict=True)
    prior_core, prior_config = prior / "core.v", prior / "physical-config.json"
    if not prior_core.is_file() or not prior_config.is_file():
        raise ContractError(
            "Lab 8 requires Lab 7's retained core.v and physical configuration"
        )
    prior_task = json.loads((prior / "task.json").read_text(encoding="utf-8"))
    task_spec = prior_task["specification"]
    physical_task, backend = _physical_task_backend(
        seed=task_spec["seed"],
        prompt_index=task_spec["prompt_index"],
        split=task_spec["split"],
        tokens=task_spec.get("tokens"),
        check_timeout=check_timeout,
        physical_timeout=timeout_s,
        correspondence_timeout=correspondence_timeout,
        cores=cores,
        mode=mode,
    )
    action_raw = json.loads((prior / "candidate.json").read_text(encoding="utf-8"))[
        "action"
    ]
    action = Action(**action_raw)
    workspace = root / "physical-candidate"
    materializer = WeightCodecMaterializer(TeachingCoreMaterializer(), weight_component)
    materializer = ArchitectureMaterializer(materializer, architecture_component)
    candidate = materializer.materialize(physical_task, action, workspace)
    core, config = (
        Path(candidate.root) / "core.v",
        Path(candidate.root) / "physical-config.json",
    )
    expected_core_hash, expected_config_hash = file_sha256(prior_core), file_sha256(
        prior_config
    )
    if (
        file_sha256(core) != expected_core_hash
        or file_sha256(config) != expected_config_hash
    ):
        raise ContractError(
            "Lab 8 rebuilt a different Lab 7 candidate source or physical configuration"
        )
    receipt = backend.evaluate(physical_task, candidate)
    observation = assess(physical_task, candidate, receipt)
    flow_receipt_path = next(
        Path(candidate.root).parent.glob("physical-*/receipt.json"), None
    )
    if flow_receipt_path is None:
        raise ContractError(
            "Physical backend did not retain its underlying flow receipt"
        )
    flow_receipt = json.loads(flow_receipt_path.read_text(encoding="utf-8"))
    manifest = flow_receipt.get("source_manifest", [])
    if not any(
        item.get("path") == "core.v" and item.get("sha256") == expected_core_hash
        for item in manifest
    ):
        raise ContractError(
            "Underlying physical receipt does not bind the exact Lab 7 RTL source"
        )
    raw = {
        "schema": "nanochip-course-composite-physical-receipt/v1",
        "candidate_sha256": candidate.digest,
        "source_manifest": manifest,
        "config_sha256": file_sha256(config),
        "status": receipt.execution_status,
        "ok": observation.eligible,
        "checks": [asdict(item) for item in observation.checks],
        "physical_flow_receipt_sha256": file_sha256(flow_receipt_path),
        "physical_flow_status": flow_receipt.get("status"),
        "physical_flow_ok": flow_receipt.get("ok"),
        "task_digest": physical_task.digest,
        "candidate_digest": candidate.digest,
        "boundary": receipt.details,
        "mapped_netlist_workload_check": next(
            (
                dict(name=item.name, status=item.status, scope=item.scope)
                for item in observation.checks
                if item.name == "rtl_netlist_correspondence"
            ),
            None,
        ),
    }
    immutable_raw = deepcopy(raw)
    summary = component.summarize_physical_receipt(
        deepcopy(immutable_raw), candidate.digest
    )
    if raw != immutable_raw:
        raise ContractError("Lab 8 receipt interpreter mutated its source evidence")
    expected_checks = [asdict(item) for item in observation.checks]
    expected_pass = observation.eligible and all(
        item["status"] == "pass" for item in expected_checks
    )
    if (
        not isinstance(summary, Mapping)
        or summary.get("candidate_sha256") != candidate.digest
        or summary.get("checks") != expected_checks
        or summary.get("all_required_passed") is not expected_pass
    ):
        raise ContractError(
            "Lab 8 interpreter changed backend checks or their independently assessed result"
        )
    result = {
        "schema": "nanochip-course-physical-check/v1",
        "candidate_action": action.name,
        "candidate_core_sha256": expected_core_hash,
        "candidate_config_sha256": expected_config_hash,
        "physical_receipt_sha256": file_sha256(flow_receipt_path),
        "summary": summary,
        "source_manifest": manifest,
        "raw_receipt": raw,
        "functional_physical_receipt": asdict(receipt),
        "observation": asdict(observation),
        "physical_flow_receipt": flow_receipt,
        "scope": "complete-core physical plus fresh functional checks and explicit RTL/netlist correspondence",
        "boundary": receipt.details,
    }
    _write(root / "receipt-summary.json", result)
    status = _physical_acceptance_status(
        {"all_required_passed": expected_pass, "checks": expected_checks}
    )
    return {
        "status": status,
        "output": str(root),
        "report": result,
        "check": {"name": "physical_receipt_binds_checked_source", "status": status},
    }
