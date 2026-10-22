"""The block probe must execute candidate RTL and retain failed evidence."""

import hashlib
import json
from pathlib import Path
import shutil

import pytest

from nanochip.laboratory.dequant_probe import run_probe


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "nanochip/kpu/rtl/msh_deq.v"
FAULT = ROOT / "nanochip/trajectories/variants/msh_deq_bad_shift.v"


@pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator unavailable")
def test_actual_rtl_distinguishes_known_fault_and_retains_artifacts(tmp_path):
    good = run_probe(BASELINE, tmp_path / "baseline")
    bad = run_probe(FAULT, tmp_path / "fault")
    assert good["ok"] and good["status"] == "passed"
    assert good["checks"]["mismatches"] == 0
    assert good["checks"]["stream_stall_cycles"] > 0
    assert good["checks"]["producer_bubble_cycles"] > 0
    assert not bad["ok"] and bad["status"] == "check_failed"
    assert bad["checks"]["mismatches"] > 0
    assert bad["checks"]["lanes_checked"] == good["checks"]["lanes_checked"]
    assert bad["candidate_sha256"] != good["candidate_sha256"]
    assert bad["vectors_sha256"] == good["vectors_sha256"]
    for name, result in [("baseline", good), ("fault", bad)]:
        saved = json.loads((tmp_path / name / "receipt.json").read_text())
        assert saved == result
        assert (
            result["candidate_sha256"]
            == hashlib.sha256(
                (tmp_path / name / "candidate.v").read_bytes()
            ).hexdigest()
        )
        assert result["build"]["returncode"] == 0
        assert result["simulation"]["elapsed_s"] > 0
        assert (tmp_path / name / "simulation.log").is_file()


def test_missing_tool_cannot_pass_or_reuse_output(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "nanochip.laboratory.dequant_probe.shutil.which", lambda _: None
    )
    output = tmp_path / "missing"
    result = run_probe(BASELINE, output)
    assert not result["ok"] and result["status"] == "unavailable"
    assert "build" not in result
    assert (output / "receipt.json").is_file()
    with pytest.raises(ValueError, match="must be empty"):
        run_probe(BASELINE, output)


@pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator unavailable")
def test_compile_error_cannot_produce_measurement(tmp_path):
    source = tmp_path / "invalid.v"
    source.write_text("this is deliberately invalid Verilog\n")
    result = run_probe(source, tmp_path / "failed")
    assert not result["ok"] and result["status"] == "build_failed"
    assert result["build"]["returncode"] != 0
    assert "checks" not in result
    assert "simulation" not in result
