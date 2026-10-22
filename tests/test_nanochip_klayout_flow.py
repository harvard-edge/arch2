"""Preserve DRC settings while correcting the pinned deck's argument names."""

import hashlib
import json
import subprocess

import pytest

from nanochip.laboratory.physical import klayout_flow


@pytest.fixture
def deck(tmp_path, monkeypatch):
    path = tmp_path / "rules.drc"
    path.write_text("source($input, $top_cell)\n$thr ? threads($thr) : threads(4)\n")
    monkeypatch.setattr(
        klayout_flow, "DRC_DECK_SHA256", hashlib.sha256(path.read_bytes()).hexdigest()
    )
    return path


def native_command(deck):
    values = {
        "input": "/work/a path/layout=v1.gds",
        "topcell": "core",
        "report": "/work/report.xml",
        "feol": "true",
        "beol": "true",
        "floating_metal": "true",
        "offgrid": "true",
        "seal": "false",
        "threads": "2",
    }
    command = ["klayout", "-b", "-zz", "-r", str(deck)]
    for key, value in values.items():
        command.extend(["-rd", key + "=" + value])
    return command


def test_exact_names_change_without_losing_any_requested_values(deck):
    original = native_command(deck)
    unchanged = original.copy()
    result, receipt = klayout_flow.adapt_sky130_drc_command(
        original, runset=deck, top="core"
    )
    expected = original.copy()
    for old, new in (
        ("topcell=core", "top_cell=core"),
        ("floating_metal=true", "floating_met=true"),
        ("threads=2", "thr=2"),
    ):
        expected[expected.index(old)] = new
    assert original == unchanged
    assert result == expected
    assert receipt["rule_values"]["floating_metal"] == "true"
    assert receipt["threads"] == 2


@pytest.mark.parametrize(
    "damage",
    [
        "missing",
        "duplicate",
        "already_mapped",
        "unknown",
        "top",
        "zero_threads",
        "fractional_threads",
        "truncated",
    ],
)
def test_ambiguous_or_changed_native_arguments_fail_before_execution(deck, damage):
    command = native_command(deck)
    if damage == "missing":
        command = command[:-2]
    elif damage == "duplicate":
        command += ["-rd", "threads=3"]
    elif damage == "already_mapped":
        command[-1] = "thr=2"
    elif damage == "unknown":
        command += ["-rd", "sram_exclude=true"]
    elif damage == "top":
        command[command.index("topcell=core")] = "topcell=other"
    elif damage == "zero_threads":
        command[-1] = "threads=0"
    elif damage == "fractional_threads":
        command[-1] = "threads=1.5"
    elif damage == "truncated":
        command += ["-rd"]
    with pytest.raises(ValueError):
        klayout_flow.adapt_sky130_drc_command(command, runset=deck, top="core")


def test_different_or_changed_deck_cannot_inherit_compatibility(deck, tmp_path):
    command = native_command(deck)
    other = tmp_path / "other.drc"
    other.write_bytes(deck.read_bytes())
    with pytest.raises(ValueError, match="configured DRC deck"):
        klayout_flow.adapt_sky130_drc_command(command, runset=other, top="core")
    deck.write_text("changed rules\n")
    with pytest.raises(ValueError, match="deck identity"):
        klayout_flow.adapt_sky130_drc_command(command, runset=deck, top="core")


class NativePatternDRC:
    def __init__(self, deck, *, fail=False):
        self.step_dir = str(deck.parent)
        self.config = {"KLAYOUT_DRC_RUNSET": str(deck), "DESIGN_NAME": "core"}
        self.command = native_command(deck)
        self.fail = fail

    def run_subprocess(self, command, *, check):
        assert check is True
        self.executed = command
        if self.fail:
            raise subprocess.CalledProcessError(1, command)
        return {"returncode": 0}

    def run_sky130(self, state_in, **kwargs):
        self.run_subprocess(self.command, check=False)
        # Nonzero native DRC metrics must survive a successful process exit.
        return {"klayout__drc_error__count": 7}


def test_wrapper_preserves_native_metric_and_records_actual_arguments(deck):
    wrapped = klayout_flow.build_klayout_drc_step(
        NativePatternDRC, step_error=RuntimeError
    )
    step = wrapped(deck)
    assert step.run_sky130(None) == {"klayout__drc_error__count": 7}
    receipt = json.loads(
        (deck.parent / "nanochip-klayout-drc-arguments.json").read_text()
    )
    assert receipt["status"] == "subprocess_completed"
    assert receipt["adapted_command"] == step.executed
    assert "thr=2" in step.executed
    assert "floating_met=true" in step.executed


def test_failed_producer_does_not_return_metrics(deck):
    wrapped = klayout_flow.build_klayout_drc_step(
        NativePatternDRC, step_error=RuntimeError
    )
    with pytest.raises(subprocess.CalledProcessError):
        wrapped(deck, fail=True).run_sky130(None)
    receipt = json.loads(
        (deck.parent / "nanochip-klayout-drc-arguments.json").read_text()
    )
    assert receipt["status"] == "error"
    assert receipt["returncode"] == 1
