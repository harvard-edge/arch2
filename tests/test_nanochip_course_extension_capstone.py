import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from nanochip.laboratory.contracts import ContractError, file_sha256


def _helper():
    path = Path(__file__).resolve().parents[1] / "nanochip/containers/validate_course_extension_capstone.py"
    spec = importlib.util.spec_from_file_location("nanochip_course_extension_capstone", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_capstone_admission_rejects_stale_extension_lab(tmp_path):
    helper = _helper()
    states = {number: "complete" for number in range(1, 8)}
    states[6] = "stale"
    with pytest.raises(ContractError, match="Lab 6=stale"):
        helper._assert_lab_status_current(states, 7)


def test_capstone_admission_rejects_missing_instructor_lab8(tmp_path):
    helper = _helper()
    with pytest.raises(ContractError, match="Labs 1–8"):
        helper._assert_lab_status_current({number: "complete" for number in range(1, 8)}, 8)


def test_capstone_requires_instructor_mode_for_reference_only_extension_labs():
    helper = _helper()
    events = {number: {"mode": "instructor"} for number in range(1, 8)}
    events[6] = {"mode": "student"}
    with pytest.raises(ContractError, match="Labs 6"):
        helper._require_instructor_components(events)


def test_capstone_cli_uses_physical_runtime_modes_and_nested_proof_path():
    helper = _helper()
    args = helper._parser().parse_args(["extension", "instructor", "sidecar", "--physical-mode", "native"])
    assert args.physical_mode == "native"
    with pytest.raises(SystemExit):
        helper._parser().parse_args(["extension", "instructor", "sidecar", "--physical-mode", "strict"])
    assert helper._mapped_proof_path(Path("/new/sidecar/evaluation")) == Path(
        "/new/sidecar/evaluation/evaluation/mapped-netlist-workload/receipt.json")
    assert helper._parser().parse_args(["extension", "instructor", "sidecar"]).correspondence_timeout == 3600


def test_capstone_output_must_be_new_and_outside_course_workspaces(tmp_path):
    helper = _helper()
    extension = tmp_path / "extension"
    instructor = tmp_path / "instructor"
    extension.mkdir()
    instructor.mkdir()
    with pytest.raises(ContractError, match="outside both course workspaces"):
        helper._verify_output_path(extension / "sidecar", extension, instructor)
    existing = tmp_path / "already-used"
    existing.mkdir()
    with pytest.raises(ContractError, match="must be a new directory"):
        helper._verify_output_path(existing, extension, instructor)


def test_capstone_requires_exact_retained_physical_receipt_hash(tmp_path):
    helper = _helper()
    attempt = tmp_path / "attempt-008"
    attempt.mkdir()
    receipt = attempt / "physical-0001/receipt.json"
    receipt.parent.mkdir()
    receipt.write_text('{"status":"pass"}\n')
    digest = file_sha256(receipt)
    assert helper._find_receipt_by_hash(attempt, digest) == receipt
    with pytest.raises(ContractError, match="uniquely matched"):
        helper._find_receipt_by_hash(attempt, hashlib.sha256(b"other").hexdigest())


def test_capstone_binds_lab8_receipt_to_exact_lab7_rtl_and_config(tmp_path):
    helper = _helper()
    instructor = tmp_path / "instructor"
    lab7 = instructor / "runs/lab07/attempt-001"
    lab8 = instructor / "runs/lab08/attempt-001"
    candidate = lab7 / "design/candidate/serial_mul2"
    candidate.mkdir(parents=True)
    lab8.mkdir(parents=True)
    core = candidate / "core.v"
    config = candidate / "physical-config.json"
    core.write_text("module core; endmodule\n")
    config.write_text('{"platform":"fixture"}\n')
    (candidate / "candidate.json").write_text(json.dumps({"action": {"name": "serial_mul2"}}))

    core_hash, config_hash = file_sha256(core), file_sha256(config)
    flow_path = lab8 / "physical-0001/receipt.json"
    flow_path.parent.mkdir()
    manifest = [{"path": "core.v", "sha256": core_hash}]
    flow_path.write_text(json.dumps({"status": "pass", "source_manifest": manifest}) + "\n")
    flow_hash = file_sha256(flow_path)
    raw = {"physical_flow_receipt_sha256": flow_hash,
           "config_sha256": config_hash,
           "candidate_action": "serial_mul2",
           "source_manifest": manifest}
    summary = {"physical_receipt_sha256": flow_hash,
               "candidate_core_sha256": core_hash,
               "candidate_config_sha256": config_hash,
               "candidate_action": "serial_mul2",
               "source_manifest": manifest,
               "raw_receipt": raw}
    (lab8 / "physical/receipt-summary.json").parent.mkdir()
    (lab8 / "physical/receipt-summary.json").write_text(json.dumps(summary) + "\n")
    events = {
        7: {"outputs": [{"path": "runs/lab07/attempt-001"}]},
        8: {"outputs": [{"path": "runs/lab08/attempt-001"}]},
    }
    binding = helper._lab8_physical_binding(instructor.resolve(), events)
    assert binding["physical_candidate_core"] == core
    assert binding["physical_candidate_config"] == config
    assert binding["physical_receipt_sha256"] == flow_hash
    assert binding["physical_reuse"]["p_and_r_rerun"] is False

    summary["physical_receipt_sha256"] = hashlib.sha256(b"wrong receipt").hexdigest()
    (lab8 / "physical/receipt-summary.json").write_text(json.dumps(summary) + "\n")
    with pytest.raises(ContractError, match="uniquely matched"):
        helper._lab8_physical_binding(instructor.resolve(), events)
