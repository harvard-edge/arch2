"""Starter adapter checks; mocked results are explicitly test data."""

import json
from pathlib import Path
import subprocess
import sys

from nanochip.laboratory.adapters import (
    BLOCK_SCOPE,
    DequantMaterializer,
    ReferenceProposer,
    VerilatorBackend,
    starter_task,
)
from nanochip.laboratory.contracts import (
    Action,
    Budget,
    CheckResult,
    Observation,
    file_sha256,
)


def test_reference_policy_uses_observed_failure_not_turn_number():
    proposer = ReferenceProposer()
    task = starter_task()
    budget = Budget(2, 1)
    good = Observation(
        Action("teaching_fault"),
        "c",
        "digest",
        "success",
        (CheckResult("dequant_vectors", "pass", BLOCK_SCOPE),),
    )
    bad = Observation(
        Action("teaching_fault"),
        "c",
        "digest",
        "success",
        (CheckResult("dequant_vectors", "fail", BLOCK_SCOPE),),
    )
    assert proposer.propose(task, (good,), budget) is None
    assert proposer.propose(task, (bad,), budget).name == "reference"


def test_crash_after_summary_is_an_execution_error(tmp_path, monkeypatch):
    task = starter_task()
    candidate = DequantMaterializer().materialize(task, Action("reference"), tmp_path)

    def crashed_probe(source, output, timeout, *, bench_path):
        output.mkdir()
        for name in (
            "receipt.json",
            "candidate.v",
            "dequant_tb.cpp",
            "vectors.json",
            "vectors.txt",
        ):
            (output / name).write_text("unit-test-output")
        return dict(
            status="check_failed",
            ok=False,
            candidate_sha256=file_sha256(source),
            bench_sha256=file_sha256(bench_path),
            probe_sha256=file_sha256(Path(candidate.root) / "probe.py"),
            checks=dict(ok=False, rows_completed=1, lanes_checked=4, mismatches=1),
            simulation=dict(returncode=-11, timed_out=False),
            total_elapsed_s=0.01,
        )

    monkeypatch.setattr(
        "nanochip.laboratory.adapters.dequant_probe.run_probe", crashed_probe
    )
    receipt = VerilatorBackend().evaluate(task, candidate)
    assert receipt.execution_status == "error"
    assert receipt.checks[0].status == "not_run"


def test_core_cli_requires_no_site_packages():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-S", "-m", "nanochip.laboratory", "labs"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, result.stderr
    assert "9. Evaluate and improve the system" in result.stdout
