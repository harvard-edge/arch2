"""Diagnostic integration checks use explicitly constructed test evidence."""

from dataclasses import asdict
import json
from pathlib import Path

import pytest

from nanochip.laboratory import __main__ as cli
from nanochip.laboratory.contracts import (
    Action,
    Artifact,
    CheckRequirement,
    ContractError,
    Task,
    file_sha256,
)
from nanochip.laboratory.datasets.dequant_corpus import ACTIONS, serialize_observation
from nanochip.laboratory.experiments import DiagnosticBackend, _DiagnosticMaterializer


def diagnostic_candidate(tmp_path, action):
    source = tmp_path / "source"
    source.mkdir()
    (source / "candidate.v").write_text(
        "// Constructed unit-test source, never compiled\n"
    )
    receipt = dict(
        mode="fixture",
        status="check_failed",
        ok=False,
        candidate_sha256=file_sha256(source / "candidate.v"),
        build=dict(returncode=0),
        simulation=dict(returncode=1),
        checks=dict(
            mismatches=3,
            lanes_checked=8,
            rows_completed=2,
            protocol_error="",
            cycles=80,
            stream_stall_cycles=4,
        ),
    )
    (source / "receipt.json").write_text(json.dumps(receipt))
    (source / "simulation.log").write_text(
        "mismatch row=0 lane=1 expected=42 observed=21\n"
    )
    text = serialize_observation(receipt, (source / "simulation.log").read_text())
    row = dict(
        record_id="fixture-0",
        source_sha256=receipt["candidate_sha256"],
        source_receipt=asdict(Artifact.from_file(tmp_path, "source/receipt.json")),
        input_text=text,
    )
    task = Task(
        "fixture-diagnostic",
        ACTIONS,
        (CheckRequirement("diagnostic_request", "diagnostic:msh_deq"),),
    )
    work = tmp_path / "work"
    work.mkdir()
    candidate = _DiagnosticMaterializer(tmp_path, row).materialize(
        task, Action(action), work
    )
    return task, candidate, row


@pytest.mark.parametrize(
    "action, evidence_key",
    [
        ("inspect_numerics", "mismatches"),
        ("inspect_protocol", "protocol_error"),
        ("inspect_build", "build_returncode"),
    ],
)
def test_decoded_action_selects_exact_diagnostic_without_repair(
    tmp_path, action, evidence_key
):
    task, candidate, row = diagnostic_candidate(tmp_path, action)
    result = DiagnosticBackend().evaluate(task, candidate)
    payload = json.loads((Path(result.output_root) / "diagnostic.json").read_text())
    assert payload["action"] == action
    assert evidence_key in payload["selected_evidence"]
    assert payload["rtl_modified"] is False
    assert payload["rtl_simulation_rerun"] is False
    assert payload["physical_flow_run"] is False
    assert file_sha256(Path(candidate.root) / "candidate.v") == row["source_sha256"]
    assert result.checks[0].status == "pass"


def test_accept_request_cannot_accept_a_failed_block(tmp_path):
    task, candidate, _ = diagnostic_candidate(tmp_path, "accept_block")
    result = DiagnosticBackend().evaluate(task, candidate)
    assert result.execution_status == "success"
    assert result.checks[0].status == "fail"


def test_backend_rejects_changed_evidence(tmp_path):
    task, candidate, _ = diagnostic_candidate(tmp_path, "inspect_build")
    (Path(candidate.root) / "receipt.json").write_text("{}")
    with pytest.raises(ContractError, match="changed"):
        DiagnosticBackend().evaluate(task, candidate)


def test_cli_failed_acceptance_returns_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "nanochip.laboratory.experiments.diagnose",
        lambda *args, **kwargs: dict(
            policy="fixture",
            scope="unit-test fixture",
            campaign=dict(
                observations=[
                    dict(
                        action=dict(name="accept_block"),
                        status="success",
                        checks=[dict(name="diagnostic_request", status="fail")],
                    )
                ]
            ),
        ),
    )
    assert (
        cli.main(
            [
                "diagnose",
                "--corpus",
                "unused",
                "--record",
                "fixture",
                "--output",
                str(tmp_path),
            ]
        )
        == 1
    )
