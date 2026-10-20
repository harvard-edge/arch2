"""Programmatic course execution API; root CLI aliases may wrap these calls."""

from __future__ import annotations

import importlib
import hashlib
import json
import os
from types import ModuleType
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Mapping

from ..contracts import Action, Artifact, Candidate, ContractError, canonical_json, file_sha256
from . import checks
from .registry import get_lab
from .workspace import (
    course_status,
    init_workspace,
    load_student_component,
    record_lab_result,
)


class LabExecutionError(RuntimeError):
    """A lab did not pass; its failed attempt remains in the workspace."""

    def __init__(self, message: str, *, event: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.event = dict(event) if event is not None else None


def _load_reference(lab_number: int):
    lab = get_lab(lab_number)
    path = Path(__file__).with_name("reference") / lab.student_file
    if not path.is_file():
        raise ContractError(f"Instructor recovery implementation is not ready for Lab {lab_number}")
    module_name = "nanochip.laboratory.course.reference.lab%02d_%s" % (lab_number,
        {1: "data", 2: "representation", 3: "harness", 5: "inference",
         6: "search", 7: "architecture", 8: "physical", 9: "evaluate"}.get(lab_number, "train"))
    module = ModuleType(module_name)
    module.__file__ = str(path)
    module.__package__ = "nanochip.laboratory.course.reference"
    try:
        source = path.read_bytes()
        exec(compile(source, str(path), "exec"), module.__dict__)
    except Exception as exc:
        raise ContractError(f"Instructor implementation failed to load: {exc}") from exc
    module.__loaded_source_sha256__ = hashlib.sha256(source).hexdigest()
    return module


def _next_attempt(root: Path, lab_number: int) -> Path:
    parent = root / "runs" / f"lab{lab_number:02d}"
    parent.mkdir(parents=True, exist_ok=True)
    index = 1
    while True:
        target = parent / f"attempt-{index:03d}"
        try:
            target.mkdir()
            return target
        except FileExistsError:
            index += 1


def _write_durable_json(path: Path, value: Mapping[str, Any]) -> None:
    """Write a small attempt receipt before execution can be interrupted."""
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _lab9_campaign_config(values: Mapping[str, Any]) -> dict[str, Any]:
    """Merge declared CLI resource limits over optional campaign-specific settings."""
    result = dict(values.get("campaign_config") or {})
    # Explicit course-run controls win for matching resource keys; absent
    # controls preserve campaign_config values before supplying defaults.
    overrides = {
        "timeout_s": "check_timeout",
        "correspondence_timeout": "correspondence_timeout",
        "cores": "cores",
        "physical_mode": "physical_mode",
    }
    for input_key, setting_key in overrides.items():
        if input_key in values:
            result[setting_key] = values[input_key]
    for key, default in (("check_timeout", 180), ("correspondence_timeout", 3600),
                         ("cores", 1), ("physical_mode", None)):
        result.setdefault(key, default)
    return result


def _latest_events(root: Path) -> dict[int, dict[str, Any]]:
    manifest = json.loads((root / "course.json").read_text(encoding="utf-8"))
    path = root / manifest["progress_path"]
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line:
            event = json.loads(line)
            result[event["lab"]] = event
    return result


def _candidates_from_lab6(root: Path, event: Mapping[str, Any]) -> dict[str, Candidate]:
    outputs = event.get("outputs", [])
    if len(outputs) != 1:
        raise ContractError("Lab 6 must retain exactly one candidate-search attempt")
    search_root = root / outputs[0]["path"] / "search"
    events_path = search_root / "events.jsonl"
    candidates = {}
    for line in events_path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("event") != "candidate":
            continue
        value = row["candidate"]
        candidate_root = Path(value["root"]).resolve(strict=True)
        if not candidate_root.is_relative_to(search_root.resolve()):
            raise ContractError("Lab 6 candidate root escapes its retained search attempt")
        candidate = Candidate(value["candidate_id"], value["task_id"], str(candidate_root),
                              Action(**value["action"]),
                              tuple(Artifact(**item) for item in value["artifacts"]),
                              value.get("parent_id"), value.get("task_digest", ""))
        candidate.validate_files()
        if candidate.digest != row.get("candidate_digest") or candidate.action.name in candidates:
            raise ContractError("Lab 6 candidate identity is duplicate or changed")
        candidates[candidate.action.name] = candidate
    return candidates


def run_lab(
    workspace: str | Path,
    lab_number: int,
    *,
    mode: str = "student",
    inputs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one lab component and retain its implementation, inputs, and checks.

    Run records bind each lab to its student (or explicit instructor) code and
    the retained upstream artifacts that were active when it ran.
    """
    lab = get_lab(lab_number)
    values = dict(inputs or {})
    root = Path(workspace).resolve()
    status = course_status(root)
    states = {item["lab"]: item["status"] for item in status["labs"]}
    for upstream in lab.upstream:
        if states.get(upstream) != "complete":
            raise ContractError(f"Lab {lab_number} requires current passing Lab {upstream} artifacts")
    component = load_student_component(root, lab_number) if mode == "student" else _load_reference(lab_number)
    component_source = Path(component.__file__).resolve()
    executed_implementation = {
        "path": component_source.relative_to(root).as_posix() if mode == "student"
                else str(component_source),
        "sha256": component.__loaded_source_sha256__,
    }
    run_inputs: dict[str, str] = {}
    latest = _latest_events(root)
    for upstream in lab.upstream:
        event = latest[upstream]
        run_inputs[f"lab{upstream:02d}"] = event["run_digest"]
    for name in ("records_path",):
        if name in values:
            path = Path(values[name]).resolve(strict=True)
            run_inputs[f"external_{name}"] = file_sha256(path)
    attempt = _next_attempt(root, lab_number)
    start_record = {
        "schema": "nanochip-course-attempt-start/v1",
        "lab": lab_number,
        "mode": mode,
        "attempt": attempt.name,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "implementation": executed_implementation,
        "inputs": run_inputs,
    }
    _write_durable_json(attempt / "start.json", start_record)
    result = None
    error = None
    interrupted_error: KeyboardInterrupt | None = None
    try:
        if lab_number == 1:
            records_path = values.get("records_path")
            if records_path is None:
                from ..language_data import collect_language_corpus
                corpus_root = attempt / "source-corpus"
                manifest = collect_language_corpus(corpus_root)
                records_path = attempt / "source-records.jsonl"
                with Path(records_path).open("x", encoding="utf-8") as stream:
                    for row in manifest["records"]:
                        stream.write(canonical_json(row) + "\n")
                run_inputs["generated_corpus_manifest"] = file_sha256(corpus_root / "manifest.json")
            output = attempt / "data"
            result = checks.run_lab01(component.split_records, records_path, output,
                                      seed=values.get("seed", "nanochip-course-v1"),
                                      fractions=values.get("fractions"))
            result["output"] = str(attempt)
        elif lab_number == 2:
            from ..teaching_core.fixtures import build_fixture
            fixture_root = attempt / "fixture"
            build_fixture(fixture_root, seed=values.get("seed", 1),
                          prompt_index=values.get("prompt_index", 0),
                          timeout_s=values.get("fixture_timeout_s", 120))
            image = (fixture_root / "image.bin").read_bytes()
            import struct
            _magic, _version, *_prefix, tensor_count, descriptor_addr = struct.unpack_from("<24I", image)
            values_nibbles = None
            for index in range(tensor_count):
                _name_hash, address, nbytes, _aux = struct.unpack_from("<IIII", image, descriptor_addr + 16 * index)
                # The first packed q4 tensor is the real embedding matrix in the upstream image.
                if nbytes and address > descriptor_addr and index == 0:
                    values_nibbles = tuple(nibble for byte in image[address:address + nbytes]
                                           for nibble in (byte & 15, byte >> 4))
                    break
            if not values_nibbles:
                raise ContractError("Teaching-core fixture contains no packed weight bytes")
            run_inputs["weight_image_sha256"] = file_sha256(fixture_root / "image.bin")
            run_inputs["weight_fixture_receipt_sha256"] = file_sha256(fixture_root / "receipt.json")
            result = checks.run_lab02(component.pack_int4, component.unpack_int4, values_nibbles,
                                      attempt / "representation",
                                      source_identity=run_inputs["weight_image_sha256"])
            result["output"] = str(attempt)
        elif lab_number == 3:
            if all(key in values for key in ("task", "candidate")):
                task, candidate = values["task"], values["candidate"]
            else:
                from ..teaching_core import TeachingCoreMaterializer, make_task
                task = make_task(seed=values.get("seed", 1), prompt_index=values.get("prompt_index", 0),
                                 split="development", tokens=values.get("tokens"))
                candidate = TeachingCoreMaterializer().materialize(task, Action("serial_mul1"),
                                                                    attempt / "baseline-candidate")
            result = checks.run_lab03(component.adapt_receipt, task, candidate, attempt / "harness")
            result["output"] = str(attempt)
        elif lab_number == 4:
            records_path = values.get("records_path")
            if records_path is None:
                upstream_dir = root / latest[1]["outputs"][0]["path"]
                matches = list(upstream_dir.rglob("records.jsonl"))
                if len(matches) != 1:
                    raise ContractError("Lab 4 needs a unique retained Lab 1 records.jsonl")
                records_path = matches[0]
            model_io_contract = values.get("model_io_contract")
            if model_io_contract is None:
                from ..model_io import ModelIOContract
                from ..teaching_core.backend import ACTIONS
                model_io_contract = ModelIOContract("nanochip_teaching_core_workload", 1,
                    "nanochip.course.task_json.v3", ACTIONS, 768).to_dict()
            result = checks.run_lab04(component, records_path, model_io_contract,
                                      attempt / "learning", budget=values.get("budget"))
        elif lab_number == 5:
            checkpoint = values.get("checkpoint")
            upstream_dir = root / latest[4]["outputs"][0]["path"]
            if checkpoint is None:
                matches = list(upstream_dir.rglob("checkpoint.pt"))
                if len(matches) != 1:
                    raise ContractError("Lab 5 needs a unique retained Lab 4 checkpoint")
                checkpoint = matches[0].parent
            training_checks = list(upstream_dir.rglob("training-check.json"))
            if len(training_checks) != 1:
                raise ContractError("Lab 5 needs Lab 4's retained model input contract")
            retained_contract = json.loads(training_checks[0].read_text())["model_io_contract"]
            model_io_contract = values.get("model_io_contract", retained_contract)
            if model_io_contract != retained_contract:
                raise ContractError("Lab 5 input contract must match the active Lab 4 checkpoint")
            documents = values.get("documents")
            if documents is None:
                from ..context import specification_sources
                documents = specification_sources()
            model_component = (load_student_component(root, 4) if latest[4]["mode"] == "student"
                               else _load_reference(4))
            receipt_component = (load_student_component(root, 3) if latest[3]["mode"] == "student"
                                 else _load_reference(3))
            result = checks.run_lab05(component, checkpoint, model_io_contract,
                                      None, attempt / "inference",
                                      documents=documents,
                                      context_limit=values.get("context_limit", 24),
                                      model_factory=model_component.build_model,
                                      seed=values.get("seed", 1),
                                      prompt_index=values.get("prompt_index", 0),
                                      tokens=values.get("tokens"),
                                      receipt_adapter=receipt_component)
        elif lab_number == 6:
            from ..teaching_core import TeachingCoreBackend, TeachingCoreMaterializer, make_task
            task = make_task(seed=values.get("seed", 1), prompt_index=values.get("prompt_index", 0),
                             split="development", tokens=values.get("tokens"))
            receipt_component = (load_student_component(root, 3) if latest[3]["mode"] == "student"
                                 else _load_reference(3))
            result = checks.run_lab06(component, attempt / "search", task=task,
                                      materializer=TeachingCoreMaterializer(),
                                      backend=TeachingCoreBackend(
                                          timeout_s=values.get("timeout_s", 180),
                                          max_cycles=values.get("max_cycles", 300_000_000)),
                                      receipt_adapter=receipt_component)
        elif lab_number == 7:
            from ..teaching_core import TeachingCoreBackend, make_task
            task = make_task(seed=values.get("seed", 1), prompt_index=values.get("prompt_index", 0),
                             split="development", tokens=values.get("tokens"))
            candidates = _candidates_from_lab6(root, latest[6])
            receipt_component = (load_student_component(root, 3) if latest[3]["mode"] == "student"
                                 else _load_reference(3))
            result = checks.run_lab07(component.transform, task, candidates,
                                      TeachingCoreBackend(
                                          timeout_s=values.get("timeout_s", 180),
                                          max_cycles=values.get("max_cycles", 300_000_000)),
                                      attempt, receipt_adapter=receipt_component)
        elif lab_number == 8:
            upstream7 = root / latest[7]["outputs"][0]["path"]
            candidates = sorted((upstream7 / "design" / "candidate").iterdir())
            if len(candidates) != 2:
                raise ContractError("Lab 8 needs both complete-core checked candidates from Lab 7")
            def measured_cycles(path):
                receipt = json.loads((path / "candidate.json").read_text(encoding="utf-8"))["receipt"]
                metric = receipt.get("metrics", {}).get("cycles")
                if not isinstance(metric, Mapping) or not isinstance(metric.get("value"), (int, float)):
                    raise ContractError("Lab 7 candidate lacks a measured cycle receipt")
                return metric["value"]
            selected = min(candidates, key=measured_cycles)
            weight_component = (load_student_component(root, 2) if latest[2]["mode"] == "student"
                                else _load_reference(2))
            architecture_component = (load_student_component(root, 7) if latest[7]["mode"] == "student"
                                       else _load_reference(7))
            result = checks.run_lab08(component, selected, attempt / "physical",
                weight_component=weight_component, architecture_component=architecture_component,
                check_timeout=values.get("timeout_s", 180),
                timeout_s=values.get("physical_timeout_s", 14400),
                correspondence_timeout=values.get("correspondence_timeout", 3600),
                cores=values.get("cores", 1),
                mode=values.get("physical_mode"))
            result["output"] = str(attempt)
        elif lab_number == 9:
            upstream1 = root / latest[1]["outputs"][0]["path"]
            upstream4 = root / latest[4]["outputs"][0]["path"]
            records = next(upstream1.rglob("records.jsonl"))
            checkpoint = next(upstream4.rglob("checkpoint.pt")).parent
            contract_path = next(upstream4.rglob("training-check.json"))
            model_contract = json.loads(contract_path.read_text())["model_io_contract"]
            training_component = (load_student_component(root, 4) if latest[4]["mode"] == "student"
                                 else _load_reference(4))
            representation_component = (load_student_component(root, 5) if latest[5]["mode"] == "student"
                                         else _load_reference(5))
            search_component = (load_student_component(root, 6) if latest[6]["mode"] == "student"
                                else _load_reference(6))
            weight_component = (load_student_component(root, 2) if latest[2]["mode"] == "student"
                                else _load_reference(2))
            architecture_component = (load_student_component(root, 7) if latest[7]["mode"] == "student"
                                       else _load_reference(7))
            physical_component = (load_student_component(root, 8) if latest[8]["mode"] == "student"
                                  else _load_reference(8))
            receipt_component = (load_student_component(root, 3) if latest[3]["mode"] == "student"
                                 else _load_reference(3))
            lab8_root = root / latest[8]["outputs"][0]["path"]
            physical_summary_path = next(lab8_root.rglob("receipt-summary.json"))
            physical_summary = json.loads(physical_summary_path.read_text(encoding="utf-8"))
            retained_flow_hash = physical_summary.get("physical_receipt_sha256")
            flow_receipts = [path for path in lab8_root.rglob("receipt.json")
                             if path.is_file() and file_sha256(path) == retained_flow_hash]
            if not retained_flow_hash or len(flow_receipts) != 1:
                raise ContractError("Lab 8's retained physical-flow receipt cannot be uniquely verified by hash")
            verified_flow_receipt_sha256 = file_sha256(flow_receipts[0])
            selected_core_hash = physical_summary["candidate_core_sha256"]
            lab7_root = root / latest[7]["outputs"][0]["path"]
            candidate_roots = list((lab7_root / "design" / "candidate").iterdir())
            physical_candidate_core = next(path / "core.v" for path in candidate_roots
                                           if file_sha256(path / "core.v") == selected_core_hash)
            result = checks.run_lab09(component, training_component, representation_component,
                records, checkpoint, model_contract, attempt / "evaluation",
                search_component=search_component,
                architecture_component=architecture_component,
                weight_component=weight_component,
                physical_component=physical_component,
                receipt_component=receipt_component,
                physical_evidence=physical_summary["raw_receipt"],
                physical_candidate_core=physical_candidate_core,
                physical_candidate_config=physical_candidate_core.parent / "physical-config.json",
                physical_candidate_action=physical_candidate_core.parent.name,
                physical_receipt_sha256=verified_flow_receipt_sha256,
                physical_output=flow_receipts[0].parent,
                config=_lab9_campaign_config(values))
            result["output"] = str(attempt)
        else:
            raise ContractError(f"Lab {lab_number} is not connected to a downstream check yet")
    except KeyboardInterrupt as exc:
        interrupted_error = exc
        error = "KeyboardInterrupt: course lab interrupted"
        _write_durable_json(attempt / "interruption.json", {
            "schema": "nanochip-course-attempt-interruption/v1",
            "lab": lab_number,
            "attempt": attempt.name,
            "exception": type(exc).__name__,
            "message": str(exc),
            "implementation": executed_implementation,
            "inputs": run_inputs,
            "start_record_sha256": file_sha256(attempt / "start.json"),
        })
        result = {"status": "fail", "output": str(attempt), "error": error}
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        failure_path = attempt / "failure.json"
        with failure_path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps({"lab": lab_number, "error": error}, indent=2) + "\n")
        result = {"status": "fail", "output": str(attempt), "error": error}

    if file_sha256(component_source) != executed_implementation["sha256"]:
        error = error or "Component source changed while its lab run was executing"
        result["error"] = error
        result["status"] = "fail"

    outputs = [attempt]
    checks_result = result.get("checks", [result.get("check", {"name": "lab_execution", "status": "fail"})])
    if error:
        checks_result = [{"name": lab.integration_check, "status": "fail", "details": error}]
    event = record_lab_result(root, lab_number, mode=mode, outputs=outputs,
                              checks=checks_result, inputs=run_inputs,
                              details=result.get("error", ""),
                              executed_implementation=executed_implementation)
    if interrupted_error is not None:
        raise interrupted_error.with_traceback(interrupted_error.__traceback__)
    if error or event["status"] != "complete":
        raise LabExecutionError(f"Lab {lab_number} did not pass: {error or result}", event=event)
    return event


def initialize_and_run_demo(workspace: str | Path, *, mode: str = "instructor") -> list[dict[str, Any]]:
    """Initialize a workspace and run its automatic data, weight, and harness labs."""
    root = Path(workspace)
    init_workspace(root, mode=mode)
    return [run_lab(root, number, mode=mode) for number in (1, 2, 3)]
