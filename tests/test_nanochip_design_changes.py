"""Actual RTL transformation, source binding, differential and scalar checks."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from nanochip.laboratory import dequant_probe
from nanochip.laboratory.adapters import VerilatorBackend
from nanochip.laboratory.contracts import Action, ContractError, file_sha256
from nanochip.laboratory.design_changes import (
    DESIGN_ACTIONS,
    REFERENCE_SHA256,
    REFERENCE_SOURCE,
    DesignChangeMaterializer,
    apply_design_change,
    design_change_task,
    run_design_checks,
    validate_action_conformance,
)
from nanochip.laboratory.exercises.design import check_design


def test_actions_are_exact_source_pinned_and_diff_is_complete(tmp_path):
    original = REFERENCE_SOURCE.read_text()
    assert hashlib.sha256(original.encode()).hexdigest() == REFERENCE_SHA256
    assert apply_design_change(original, DESIGN_ACTIONS[0]) == original
    transformed = apply_design_change(original, DESIGN_ACTIONS[1])
    assert "qrow_v[8*w_j +: 8]" not in transformed
    assert "wire [3:0]  w_nib = qrow_v[3:0];" in transformed
    assert transformed.count("qrow_v <= {4'b0, qrow_v[1023:4]};") == 1
    # Intake is preserved verbatim, including its original variable byte demux.
    assert "qrow_v[8*pos[6:0] +: 8] <= beat_r[7:0];" in transformed
    for name in DESIGN_ACTIONS:
        candidate = DesignChangeMaterializer().materialize(
            design_change_task(), Action(name), tmp_path / name
        )
        candidate.validate_files()
        root = Path(candidate.root)
        assert (root / "reference.v").read_text() == original
        assert (root / "msh_deq.v").read_text() == apply_design_change(original, name)
        diff = (root / "change.diff").read_text()
        assert bool(diff) == (name == "stream_quantized_row")
        if diff:
            assert "-    wire [6:0]  w_j" in diff
            assert "+                qrow_v <= {4'b0, qrow_v[1023:4]};" in diff
        saved_task = json.loads((root / "task.json").read_text())
        assert saved_task["specification"]["transformer_sha256"] == file_sha256(
            root / "design_changes.py"
        )


@pytest.mark.parametrize(
    "change", [lambda s: s + "\n", lambda s: s.replace("wire [6:0]", "wire [7:0]")]
)
def test_unreviewed_source_cannot_be_transformed(change):
    with pytest.raises(ContractError, match="source hash"):
        apply_design_change(
            change(REFERENCE_SOURCE.read_text()), "stream_quantized_row"
        )


def test_unknown_actions_and_materializer_drift_cannot_execute(tmp_path):
    source = tmp_path / "source.v"
    shutil.copyfile(REFERENCE_SOURCE, source)
    task = design_change_task(source)
    source.write_text(source.read_text() + "\n")
    with pytest.raises(ContractError, match="changed after task"):
        DesignChangeMaterializer(source).materialize(
            task, Action(DESIGN_ACTIONS[1]), tmp_path / "drift"
        )
    with pytest.raises(ContractError, match="Unknown design action"):
        apply_design_change(REFERENCE_SOURCE.read_text(), "guess")
    with pytest.raises(ContractError, match="without parameters"):
        DesignChangeMaterializer().materialize(
            task, Action(DESIGN_ACTIONS[1], {"shift": 5}), tmp_path / "parameters"
        )
    restricted = replace(design_change_task(), allowed_actions=(DESIGN_ACTIONS[0],))
    with pytest.raises(ContractError, match="two named actions"):
        DesignChangeMaterializer().materialize(
            restricted, Action(DESIGN_ACTIONS[1]), tmp_path / "restricted"
        )


@pytest.mark.parametrize(
    "suffix", ["", "\n// I changed the design\n", "\n/* qrow_v <= qrow_v >> 4; */\n"]
)
def test_stream_action_rejects_unchanged_hardware_including_comment_only_edits(suffix):
    original = REFERENCE_SOURCE.read_text()
    with pytest.raises(ContractError, match="must change hardware"):
        validate_action_conformance(original, original + suffix, "stream_quantized_row")


@pytest.mark.parametrize(
    "shift",
    ["{4'b0, qrow_v[1023:4]}", "qrow_v >> 4", "qrow_v >> 4'd4", "qrow_v >> 32'd4"],
)
@pytest.mark.parametrize("keep_unused", [False, True])
def test_conformance_accepts_admitted_stream_spellings_and_unused_declarations(
    shift, keep_unused
):
    original = REFERENCE_SOURCE.read_text()
    changed = apply_design_change(original, "stream_quantized_row")
    changed = changed.replace("{4'b0, qrow_v[1023:4]}", shift)
    if keep_unused:
        changed = changed.replace(
            "    // Consume staged nibbles",
            "    wire [6:0] w_j = wr_i[7:1];\n"
            "    wire [7:0] w_qb = qrow_v[8*w_j +: 8];\n    // Consume staged nibbles",
        )
    changed = changed.replace("w_nib =", "w_nib /* read // literal comment */ =")
    validate_action_conformance(original, changed, "stream_quantized_row")


@pytest.mark.parametrize(
    "mutation",
    [
        lambda s: s.replace("qrow_v[3:0]", "qrow_v[7:4]"),
        lambda s: s.replace("qrow_v <=", "qrow_v ="),
        lambda s: s.replace("{4'b0, qrow_v[1023:4]}", "qrow_v >> 1'd4"),
        lambda s: s.replace("if (state == S_WR) begin", "if (state == S_Q) begin"),
        lambda s: s.replace("wire [3:0]  w_nib", "wi re [3:0]  w_nib"),
        lambda s: s.replace("w_nib = qrow_v[3:0]", "w_nib = qrow_v[3:0] ^ 4'b1"),
    ],
)
def test_conformance_rejects_wrong_read_shift_assignment_state_or_extra_hardware(
    mutation,
):
    original = REFERENCE_SOURCE.read_text()
    changed = mutation(apply_design_change(original, "stream_quantized_row"))
    with pytest.raises(ContractError, match="requires the admitted low-nibble read"):
        validate_action_conformance(original, changed, "stream_quantized_row")


def _noop_transformer(source, action):
    return source


def _comment_transformer(source, action):
    return (
        source
        if action == "retain_indexed_read"
        else source + "\n// stream_quantized_row implemented\n"
    )


def _always_stream_transformer(source, action):
    return apply_design_change(source, "stream_quantized_row")


def _bad_retain_transformer(source, action):
    return (
        source + "\n// retain\n"
        if action == "retain_indexed_read"
        else apply_design_change(source, action)
    )


@pytest.mark.parametrize(
    "transformer,message",
    [
        (_noop_transformer, "must change hardware"),
        (_comment_transformer, "must change hardware"),
        (_always_stream_transformer, "exact original source"),
        (_bad_retain_transformer, "exact original source"),
    ],
)
def test_exercise_rejects_invalid_either_branch_before_any_simulation(
    tmp_path, monkeypatch, transformer, message
):
    def forbidden(*args, **kwargs):
        pytest.fail(
            "structurally invalid exercise must not launch expensive simulation"
        )

    monkeypatch.setattr(
        "nanochip.laboratory.exercises.design.VerilatorBackend.evaluate", forbidden
    )
    monkeypatch.setattr(
        "nanochip.laboratory.exercises.design.run_design_checks", forbidden
    )
    with pytest.raises(ContractError, match=message):
        check_design(tmp_path / "exercise", transformer=transformer)


def test_materializer_rejects_comment_only_student_transformer(tmp_path):
    task = design_change_task()
    task = replace(
        task,
        specification=dict(
            task.specification, extension_sha256=file_sha256(Path(__file__))
        ),
    )
    with pytest.raises(ContractError, match="must change hardware"):
        DesignChangeMaterializer(transformer=_comment_transformer).materialize(
            task, Action("stream_quantized_row"), tmp_path / "workspace"
        )
    assert not (tmp_path / "workspace/candidate").exists()


def test_exercise_checks_both_correct_branches_before_tools(tmp_path, monkeypatch):
    from nanochip.laboratory.contracts import CheckResult, RunReceipt

    calls = []
    output = tmp_path / "exercise"

    def transformer(source, action):
        calls.append(action)
        return apply_design_change(source, action)

    def functional(task, candidate):
        assert calls == ["retain_indexed_read", "stream_quantized_row"]
        assert (
            output / "retain/candidate/msh_deq.v"
        ).read_text() == REFERENCE_SOURCE.read_text()
        return RunReceipt(
            task.task_id,
            candidate.digest,
            "fixture",
            "success",
            "fake-tool",
            "fixture",
            checks=(CheckResult("dequant_vectors", "pass", "block:msh_deq"),),
        )

    monkeypatch.setattr(
        "nanochip.laboratory.exercises.design.VerilatorBackend.evaluate",
        lambda self, task, candidate: functional(task, candidate),
    )
    monkeypatch.setattr(
        "nanochip.laboratory.exercises.design.run_design_checks",
        lambda *args: {"ok": True},
    )
    result = check_design(output, transformer=transformer)
    assert result["ok"]
    assert result["action_conformance"] == {
        "retain_indexed_read": "pass",
        "stream_quantized_row": "pass",
    }
    assert result["reference_candidate"]["action"]["name"] == "retain_indexed_read"


@pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator unavailable")
def test_real_rtl_passes_independent_integer_oracle_and_original_rtl_miter(tmp_path):
    task = design_change_task()
    candidate = DesignChangeMaterializer().materialize(
        task, Action(DESIGN_ACTIONS[1]), tmp_path
    )
    functional = VerilatorBackend().evaluate(task, candidate)
    assert functional.execution_status == "success"
    assert functional.checks[0].status == "pass"
    assert functional.metrics["lanes_checked"].value == 1740
    assert functional.metrics["mismatches"].value == 0
    result = run_design_checks(
        Path(candidate.root) / "msh_deq.v", tmp_path / "equivalence"
    )
    assert result["ok"] and result["status"] == "passed"
    assert result["checks"]["jobs_completed"] == 409
    assert result["checks"]["resets"] == 15
    assert result["checks"]["cycles_checked"] > 80000
    assert result["checks"]["stream_stall_cycles"] > 0
    assert result["source_sha256"] == file_sha256(Path(candidate.root) / "msh_deq.v")
    assert result["reference_sha256"] == REFERENCE_SHA256
    assert "Not exhaustive equivalence" in result["limits"]
    assert json.loads((tmp_path / "equivalence/receipt.json").read_text()) == result
    assert {a["path"] for a in result["output_artifacts"]} >= {
        "reference.v",
        "candidate.v",
        "miter.v",
        "stress.cpp",
        "checker.py",
        "simulation.log",
    }


@pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator unavailable")
def test_real_differential_checker_rejects_wrong_shift(tmp_path):
    broken = tmp_path / "wrong_shift.v"
    source = apply_design_change(REFERENCE_SOURCE.read_text(), DESIGN_ACTIONS[1])
    broken.write_text(
        source.replace("{4'b0, qrow_v[1023:4]}", "{8'b0, qrow_v[1023:8]}")
    )
    result = run_design_checks(broken, tmp_path / "bad")
    assert not result["ok"] and result["status"] == "check_failed"
    assert result["build"]["returncode"] == 0
    assert result["simulation"]["returncode"] == 1
    assert "RTL mismatch" in (tmp_path / "bad/simulation.log").read_text()


def test_unavailable_tool_never_passes_and_cannot_reuse_prior_result(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "nanochip.laboratory.design_changes.shutil.which", lambda _: None
    )
    result = run_design_checks(REFERENCE_SOURCE, tmp_path / "missing")
    assert not result["ok"] and result["status"] == "unavailable"
    assert "simulation" not in result
    with pytest.raises(ValueError, match="must be empty"):
        run_design_checks(REFERENCE_SOURCE, tmp_path / "missing")


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan")])
def test_invalid_time_bounds_rejected_before_writing(timeout, tmp_path):
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="finite and positive"):
        run_design_checks(REFERENCE_SOURCE, output, timeout)
    assert not output.exists()


@pytest.mark.skipif(shutil.which("yosys") is None, reason="Yosys unavailable")
def test_yosys_proves_local_nibble_extraction_law_for_all_rows_and_positions(tmp_path):
    """Local combinational theorem only; no sequential-equivalence claim."""
    theorem = tmp_path / "extraction.v"
    theorem.write_text(
        """module extraction(input [1023:0] row, input [7:0] index, output equal);
wire [7:0] qb = row[8*index[7:1] +: 8];
wire [3:0] old_nibble = index[0] ? qb[7:4] : qb[3:0];
wire [1023:0] remaining = row >> {index, 2'b00};
assign equal = old_nibble == remaining[3:0];
endmodule
"""
    )
    result = dequant_probe._run(
        [
            shutil.which("yosys"),
            "-p",
            "read_verilog extraction.v; prep -top extraction; sat -verify -prove equal 1 -show-inputs",
        ],
        tmp_path,
        tmp_path / "yosys.log",
        60,
    )
    assert result["returncode"] == 0 and not result["timed_out"]
    assert "SUCCESS" in (tmp_path / "yosys.log").read_text()
