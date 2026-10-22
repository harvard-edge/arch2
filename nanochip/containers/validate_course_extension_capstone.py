"""Run a Lab 9 sidecar from a completed retrieval-extension workspace.

The helper reuses a separately completed instructor Lab 8 physical result. It
does not change either course's progress log or rerun place and route. Lab 9
still performs its functional campaign and, for an exact RTL/config match,
runs a fresh held-out workload against the retained mapped netlist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Mapping

for _thread_variable in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[_thread_variable] = "1"

from nanochip.laboratory.contracts import ContractError, file_sha256
from nanochip.laboratory.course import course_status, load_student_component
from nanochip.laboratory.course import api as course_api
from nanochip.laboratory.course import checks


def _latest_events(workspace: Path) -> dict[int, dict[str, Any]]:
    path = workspace / "progress.jsonl"
    if not path.is_file():
        raise ContractError(f"Course progress log is missing: {path}")
    events: dict[int, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        event = json.loads(line)
        lab = event.get("lab")
        if type(lab) is not int:
            raise ContractError(
                "Course progress contains an event with no valid lab number"
            )
        events[lab] = event
    return events


def _require_current_labs(workspace: Path, through: int) -> dict[int, dict[str, Any]]:
    status = course_status(workspace)
    states = {row["lab"]: row["status"] for row in status["labs"]}
    _assert_lab_status_current(states, through)
    events = _latest_events(workspace)
    for number in range(1, through + 1):
        event = events.get(number)
        if not event or event.get("status") != "complete":
            raise ContractError(
                f"Workspace progress has no completed latest event for Lab {number}"
            )
    return events


def _assert_lab_status_current(states: Mapping[int, str], through: int) -> None:
    invalid = [
        number for number in range(1, through + 1) if states.get(number) != "complete"
    ]
    if invalid:
        details = ", ".join(
            f"Lab {number}={states.get(number, 'missing')}" for number in invalid
        )
        raise ContractError(
            f"Workspace does not have current completed Labs 1–{through}: {details}"
        )


def _require_instructor_components(events: Mapping[int, Mapping[str, Any]]) -> None:
    required = (2, 3, 6, 7)
    wrong = [
        number
        for number in required
        if events.get(number, {}).get("mode") != "instructor"
    ]
    if wrong:
        labs = ", ".join(str(number) for number in wrong)
        raise ContractError(
            f"This sidecar uses instructor reference implementations for Labs {labs}; "
            "complete those extension labs in instructor mode first"
        )


def _attempt_root(workspace: Path, event: Mapping[str, Any], lab: int) -> Path:
    outputs = event.get("outputs")
    if not isinstance(outputs, list):
        raise ContractError(f"Lab {lab} has no retained output list")
    paths = []
    for row in outputs:
        if not isinstance(row, Mapping) or not isinstance(row.get("path"), str):
            continue
        path = (workspace / row["path"]).resolve(strict=True)
        if path.is_relative_to(workspace) and path.name.startswith("attempt-"):
            paths.append(path)
    if len(paths) != 1:
        raise ContractError(
            f"Lab {lab} must retain exactly one in-workspace attempt directory"
        )
    return paths[0]


def _load_event_component(
    workspace: Path,
    lab: int,
    event: Mapping[str, Any],
    *,
    require_student: bool = False,
) -> ModuleType:
    mode = event.get("mode")
    if require_student and mode != "student":
        raise ContractError(
            f"The extension workspace must have executed its Lab {lab} student module"
        )
    if mode == "student":
        module = load_student_component(workspace, lab)
    elif mode == "instructor":
        module = course_api._load_reference(lab)
    else:
        raise ContractError(f"Lab {lab} event has no valid implementation mode")
    expected = event.get("implementation", {}).get("sha256")
    path = Path(module.__file__).resolve(strict=True)
    if (
        not isinstance(expected, str)
        or module.__loaded_source_sha256__ != expected
        or file_sha256(path) != expected
    ):
        raise ContractError(
            f"The loaded Lab {lab} source does not match its completed course event"
        )
    return module


def _verified_lab1_records(workspace: Path, event: Mapping[str, Any]) -> Path:
    attempt = _attempt_root(workspace, event, 1)
    manifest_path = attempt / "data/split-manifest.json"
    if not manifest_path.is_file():
        raise ContractError("The completed extension Lab 1 split manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    record_info = manifest.get("records", {})
    relpath, digest = record_info.get("path"), record_info.get("sha256")
    if not isinstance(relpath, str) or not isinstance(digest, str):
        raise ContractError("Lab 1 split manifest lacks its retained records receipt")
    records = (manifest_path.parent / relpath).resolve(strict=True)
    if not records.is_relative_to(attempt) or file_sha256(records) != digest:
        raise ContractError("Lab 1 records do not match the retained split manifest")
    return records


def _verified_lab4_checkpoint(
    workspace: Path, event: Mapping[str, Any]
) -> tuple[Path, dict]:
    attempt = _attempt_root(workspace, event, 4)
    check_paths = list(attempt.rglob("training-check.json"))
    if len(check_paths) != 1:
        raise ContractError("Lab 4 must retain one training-check.json")
    check_path = check_paths[0]
    check = json.loads(check_path.read_text(encoding="utf-8"))
    checkpoint = check_path.parent / "checkpoint"
    checkpoint_path = checkpoint / "checkpoint.pt"
    if (
        not checkpoint_path.is_file()
        or file_sha256(checkpoint_path) != check.get("checkpoint_sha256")
        or not (checkpoint / "training.json").is_file()
    ):
        raise ContractError(
            "Lab 4 checkpoint does not match its retained training check"
        )
    contract = check.get("model_io_contract")
    if not isinstance(contract, dict):
        raise ContractError("Lab 4 training check has no model input contract")
    return checkpoint, contract


def _find_receipt_by_hash(attempt: Path, digest: str) -> Path:
    if not isinstance(digest, str) or len(digest) != 64:
        raise ContractError("Expected a SHA-256 receipt identity")
    matches = [
        path
        for path in attempt.rglob("receipt.json")
        if path.is_file() and file_sha256(path) == digest
    ]
    if len(matches) != 1:
        raise ContractError(
            "Physical-flow receipt cannot be uniquely matched by its retained hash"
        )
    return matches[0]


def _mapped_proof_path(evaluation_output: Path) -> Path:
    return evaluation_output / "evaluation/mapped-netlist-workload/receipt.json"


def _lab8_physical_binding(
    instructor_workspace: Path, events: Mapping[int, Mapping[str, Any]]
):
    """Resolve and verify the exact Lab 8 receipt, RTL, config, and flow directory."""
    lab8_attempt = _attempt_root(instructor_workspace, events[8], 8)
    summaries = list(lab8_attempt.rglob("receipt-summary.json"))
    if len(summaries) != 1:
        raise ContractError("Instructor Lab 8 must retain one physical receipt summary")
    summary_path = summaries[0]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    flow_hash = summary.get("physical_receipt_sha256")
    if not isinstance(flow_hash, str) or len(flow_hash) != 64:
        raise ContractError("Lab 8 summary has no exact physical-flow receipt hash")
    flow_path = _find_receipt_by_hash(lab8_attempt, flow_hash)
    flow = json.loads(flow_path.read_text(encoding="utf-8"))
    raw = summary.get("raw_receipt")
    if not isinstance(raw, dict):
        raise ContractError("Lab 8 summary has no retained raw composite receipt")
    if raw.get("physical_flow_receipt_sha256") != flow_hash or summary.get(
        "physical_receipt_sha256"
    ) != file_sha256(flow_path):
        raise ContractError(
            "Lab 8 raw receipt and retained flow receipt hashes disagree"
        )

    lab7_attempt = _attempt_root(instructor_workspace, events[7], 7)
    expected_core = summary.get("candidate_core_sha256")
    expected_config = summary.get("candidate_config_sha256")
    if not isinstance(expected_core, str) or not isinstance(expected_config, str):
        raise ContractError(
            "Lab 8 summary lacks exact RTL and physical-configuration identities"
        )
    candidates = [
        path.parent
        for path in lab7_attempt.rglob("core.v")
        if path.is_file() and file_sha256(path) == expected_core
    ]
    if len(candidates) != 1:
        raise ContractError(
            "Lab 8 RTL does not uniquely match an exact retained Lab 7 candidate"
        )
    core = candidates[0] / "core.v"
    config = candidates[0] / "physical-config.json"
    candidate = json.loads(
        (candidates[0] / "candidate.json").read_text(encoding="utf-8")
    )
    action = candidate.get("action", {}).get("name")
    if (
        not config.is_file()
        or file_sha256(config) != expected_config
        or action != summary.get("candidate_action")
    ):
        raise ContractError(
            "Lab 8 action/configuration does not match the selected Lab 7 candidate"
        )

    summary_manifest = summary.get("source_manifest", [])
    raw_manifest = raw.get("source_manifest", [])
    flow_manifest = flow.get("source_manifest", [])
    if not any(
        row.get("path") == "core.v" and row.get("sha256") == expected_core
        for manifest in (summary_manifest, raw_manifest, flow_manifest)
        for row in manifest
        if isinstance(row, Mapping)
    ):
        raise ContractError("Lab 8 flow evidence does not bind the selected RTL hash")
    if raw.get("config_sha256") != expected_config or raw.get(
        "candidate_action"
    ) not in (None, action):
        raise ContractError(
            "Lab 8 composite receipt does not bind the selected config/action"
        )
    return {
        "summary_path": summary_path,
        "summary": summary,
        "physical_evidence": raw,
        "physical_receipt_sha256": flow_hash,
        "physical_output": flow_path.parent,
        "physical_candidate_core": core,
        "physical_candidate_config": config,
        "physical_candidate_action": action,
        "lab7_attempt": lab7_attempt,
        "physical_reuse": {
            "p_and_r_rerun": False,
            "retained_lab8_flow_reused": True,
            "retained_flow_receipt_sha256": flow_hash,
            "retained_physical_summary_sha256": file_sha256(summary_path),
            "fresh_correspondence_and_heldout_mapped_workload_contingent_on_exact_winner_hashes": True,
        },
    }


def _source_identity(module: ModuleType) -> dict[str, str]:
    path = Path(module.__file__).resolve(strict=True)
    loaded_hash = getattr(module, "__loaded_source_sha256__", None)
    if not isinstance(loaded_hash, str):
        raise ContractError(f"Loaded component has no source-byte identity: {path}")
    return {
        "path": str(path),
        "loaded_sha256": loaded_hash,
        "current_sha256": file_sha256(path),
    }


def _verify_output_path(
    output: Path, extension_workspace: Path, instructor_workspace: Path
) -> None:
    output = output.resolve()
    for workspace in (extension_workspace, instructor_workspace):
        if output == workspace or output.is_relative_to(workspace):
            raise ContractError("Sidecar output must be outside both course workspaces")
    if output.exists():
        raise ContractError(f"Sidecar output must be a new directory: {output}")


def run_extension_capstone(
    extension_workspace: str | Path,
    instructor_workspace: str | Path,
    output: str | Path,
    *,
    check_timeout: float = 180,
    correspondence_timeout: float = 3600,
    cores: int = 1,
    physical_mode: str | None = None,
) -> dict[str, Any]:
    extension = Path(extension_workspace).resolve(strict=True)
    instructor = Path(instructor_workspace).resolve(strict=True)
    sidecar = Path(output).resolve()
    if (
        not (extension / "course.json").is_file()
        or not (instructor / "course.json").is_file()
    ):
        raise ContractError(
            "Both inputs must be initialized Nanochip course workspaces"
        )
    extension_manifest = json.loads(
        (extension / "course.json").read_text(encoding="utf-8")
    )
    instructor_manifest = json.loads(
        (instructor / "course.json").read_text(encoding="utf-8")
    )
    if extension_manifest.get("mode") != "student":
        raise ContractError("Extension workspace must be initialized in student mode")
    if instructor_manifest.get("mode") != "instructor":
        raise ContractError(
            "Physical evidence workspace must be initialized in instructor mode"
        )
    _verify_output_path(sidecar, extension, instructor)

    extension_events = _require_current_labs(extension, 7)
    instructor_events = _require_current_labs(instructor, 8)
    _require_instructor_components(extension_events)
    if extension_events[5].get("mode") != "student":
        raise ContractError(
            "Extension workspace Lab 5 must be the active student retrieval implementation"
        )

    representation = _load_event_component(
        extension, 5, extension_events[5], require_student=True
    )
    training_component = _load_event_component(extension, 4, extension_events[4])
    records = _verified_lab1_records(extension, extension_events[1])
    checkpoint, model_contract = _verified_lab4_checkpoint(
        extension, extension_events[4]
    )
    physical = _lab8_physical_binding(instructor, instructor_events)

    reference_components = {
        number: course_api._load_reference(number) for number in (2, 3, 6, 7, 8, 9)
    }
    component_map = {
        "lab05_student_retrieval": representation,
        "lab04_active_training": training_component,
        **{
            f"lab{number:02d}_reference": module
            for number, module in reference_components.items()
        },
    }
    source_before = {
        name: _source_identity(module) for name, module in component_map.items()
    }
    changed_before = [
        name
        for name, source in source_before.items()
        if source["loaded_sha256"] != source["current_sha256"]
    ]
    if changed_before:
        raise ContractError(
            "A loaded component changed before the sidecar started: "
            + ", ".join(changed_before)
        )

    sidecar.mkdir(parents=True, exist_ok=False)
    preflight = {
        "schema": "nanochip-course-extension-capstone-preflight/v1",
        "extension_workspace": str(extension),
        "instructor_workspace": str(instructor),
        "extension_lab5_event_digest": extension_events[5]["run_digest"],
        "extension_lab5_source_sha256": representation.__loaded_source_sha256__,
        "extension_lab1_records_sha256": file_sha256(records),
        "extension_lab4_checkpoint_sha256": file_sha256(checkpoint / "checkpoint.pt"),
        "extension_lab4_model_io_contract": model_contract,
        "extension_completed_labs": [1, 2, 3, 4, 5, 6, 7],
        "extension_component_modes": {
            str(number): extension_events[number].get("mode") for number in range(1, 8)
        },
        "sidecar_component_scope": {
            "active_extension_components": [
                "Lab 4 implementation from extension event",
                "Lab 5 student retrieval implementation",
            ],
            "instructor_reference_components": [2, 3, 6, 7, 8, 9],
        },
        "instructor_lab8_event_digest": instructor_events[8]["run_digest"],
        "physical_reuse": physical["physical_reuse"],
        "components": source_before,
        "progress_mutation": "none; Lab 9 is written only to this separate sidecar",
    }
    (sidecar / "preflight.json").write_text(
        json.dumps(preflight, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    try:
        result = checks.run_lab09(
            reference_components[9],
            training_component,
            representation,
            records,
            checkpoint,
            model_contract,
            sidecar / "evaluation",
            search_component=reference_components[6],
            architecture_component=reference_components[7],
            weight_component=reference_components[2],
            physical_component=reference_components[8],
            receipt_component=reference_components[3],
            physical_evidence=physical["physical_evidence"],
            physical_candidate_core=physical["physical_candidate_core"],
            physical_candidate_config=physical["physical_candidate_config"],
            physical_candidate_action=physical["physical_candidate_action"],
            physical_receipt_sha256=physical["physical_receipt_sha256"],
            physical_output=physical["physical_output"],
            config={
                "check_timeout": check_timeout,
                "correspondence_timeout": correspondence_timeout,
                "cores": cores,
                "physical_mode": physical_mode,
            },
        )
    except Exception as exc:
        (sidecar / "failure.json").write_text(
            json.dumps(
                {
                    "schema": "nanochip-course-extension-capstone-failure/v1",
                    "exception": type(exc).__name__,
                    "message": str(exc),
                    "preflight_sha256": file_sha256(sidecar / "preflight.json"),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        raise

    source_after = {
        name: _source_identity(module) for name, module in component_map.items()
    }
    source_changed_during_run = [
        name
        for name, source in source_after.items()
        if source["loaded_sha256"] != source["current_sha256"]
    ]
    mapped_receipt_path = _mapped_proof_path(Path(result["output"]))
    mapped_receipt = None
    if mapped_receipt_path.is_file():
        mapped_receipt = {
            "path": str(mapped_receipt_path),
            "sha256": file_sha256(mapped_receipt_path),
            "status": json.loads(mapped_receipt_path.read_text(encoding="utf-8")).get(
                "status"
            ),
        }
    report = {
        "schema": "nanochip-course-extension-capstone-sidecar/v1",
        "status": result["status"]
        if not source_changed_during_run
        else "invalidated_source_changed_during_run",
        "extension_lab5_source_sha256": representation.__loaded_source_sha256__,
        "component_sources_before": source_before,
        "component_sources_after": source_after,
        "source_changed_during_run": source_changed_during_run,
        "physical_reuse": physical["physical_reuse"],
        "p_and_r_cost": "not incurred by this sidecar; it reuses the identified instructor Lab 8 flow",
        "fresh_mapped_workload": mapped_receipt,
        "course_progress_changed": False,
        "result": result,
    }
    report_path = sidecar / "sidecar-result.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("extension_workspace", type=Path)
    parser.add_argument("instructor_workspace", type=Path)
    parser.add_argument(
        "output", type=Path, help="new sidecar directory outside both course workspaces"
    )
    parser.add_argument("--check-timeout", type=float, default=180)
    parser.add_argument(
        "--correspondence-timeout",
        type=float,
        default=3600,
        help="Declared wall-clock budget for mapped correspondence, not a runtime guarantee",
    )
    parser.add_argument("--cores", type=int, default=1)
    parser.add_argument("--physical-mode", choices=("native", "docker"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = run_extension_capstone(
            args.extension_workspace,
            args.instructor_workspace,
            args.output,
            check_timeout=args.check_timeout,
            correspondence_timeout=args.correspondence_timeout,
            cores=args.cores,
            physical_mode=args.physical_mode,
        )
    except (ContractError, OSError, ValueError, StopIteration) as exc:
        print(
            json.dumps(
                {"status": "incomplete", "error": f"{type(exc).__name__}: {exc}"},
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    print(
        json.dumps(
            {
                "status": report["status"],
                "sidecar": str(args.output.resolve() / "sidecar-result.json"),
                "fresh_mapped_workload": report["fresh_mapped_workload"],
                "physical_reused": True,
                "progress_changed": False,
            },
            indent=2,
            default=str,
        )
    )
    if report["status"] == "invalidated_source_changed_during_run":
        return 1
    acceptance = report["result"].get("report", {}).get("final_capstone_acceptance", {})
    if acceptance.get("status") != "accepted_by_reused_lab8_evidence":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
