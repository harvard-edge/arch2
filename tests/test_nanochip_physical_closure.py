"""Repair diagnostics cannot promote partial or historical evidence to closure."""

import json
from pathlib import Path

import pytest

from nanochip.laboratory.contracts import ContractError, file_sha256
from nanochip.laboratory.physical.closure import (
    parse_antenna_report,
    parse_electrical_report,
    plan_retained_repair,
)


def test_antenna_plan_targets_failing_sink_not_every_pin_on_a_bad_net():
    raw = """Net: net1
  Pin: good/A (buf)
    Required ratio: 400 (Side area)
  Pin: bad/B (buf)
    Required ratio: 400 (Side area) (VIOLATED)
    Required ratio: 400 (Side area) (VIOLATED)
  Pin: diode/DIODE (diode)
    Required ratio: 2773 (Side area)
"""
    assert parse_antenna_report(raw) == [{"net": "net1", "pin": "bad/B"}]
    with pytest.raises(ContractError):
        parse_antenna_report("Required ratio: 400 (VIOLATED)")


def test_electrical_diagnostics_preserve_each_constraint_and_measurement():
    raw = """max slew
pin/A 0.750000 1.104613 -0.354613 (VIOLATED)
max fanout
clkbuf_0/X 10 16 -6 (VIOLATED)
max capacitance
clkbuf_0/X 0.2 0.287737 -0.087737 (VIOLATED)
"""
    rows = parse_electrical_report(raw)
    assert rows["max slew"] == [{"pin": "pin/A", "limit": 0.75, "observed": 1.104613}]
    assert rows["max capacitance"][0]["observed"] == 0.287737
    with pytest.raises(ContractError):
        parse_electrical_report("max slew\nbroken (VIOLATED)")


def test_plan_requires_final_reports_binds_inputs_and_never_grants_acceptance(tmp_path):
    source, output = tmp_path / "source", tmp_path / "plan"
    sta = source / "runs/physical/50-openroad-stapostpnr"
    route = source / "runs/physical/39-openroad-detailedrouting"
    ant = source / "runs/physical/41-openroad-checkantennas-1"
    for stage in (sta, route, ant):
        stage.mkdir(parents=True)
        (stage / "state_out.json").write_text('{"metrics":{}}')
    config = {
        "DESIGN_NAME": "msh_deq",
        "CLOCK_PERIOD": 100,
        "MAX_TRANSITION_CONSTRAINT": 0.75,
        "MAX_FANOUT_CONSTRAINT": 10,
        "MAX_CAPACITANCE_CONSTRAINT": 0.2,
        "STA_CORNERS": ["slow", "fast"],
    }
    (sta / "config.json").write_text(json.dumps(config))
    (ant / "reports").mkdir()
    (ant / "reports/antenna.rpt").write_text(
        "Net: net1\n Pin: bad/A (buf)\n Required: 400 (VIOLATED)\n"
    )
    for corner in config["STA_CORNERS"]:
        (sta / corner).mkdir()
        (sta / corner / "checks.rpt").write_text(
            "max fanout\nclkbuf_0/X 10 16 -6 (VIOLATED)\n"
        )
    plan = plan_retained_repair(source, output)
    assert plan["eligible"] is False
    assert plan["clock_driver_pins"] == ["clkbuf_0/X"]
    assert plan["constraints"] == {
        key: config[key] for key in config if key != "DESIGN_NAME"
    }
    assert all(
        file_sha256(source / item["path"]) == item["sha256"] for item in plan["inputs"]
    )
    with pytest.raises(FileExistsError):
        plan_retained_repair(source, output)
    (sta / "fast/checks.rpt").unlink()
    with pytest.raises(FileNotFoundError):
        plan_retained_repair(source, tmp_path / "missing-corner-plan")
    assert not (tmp_path / "missing-corner-plan").exists()
