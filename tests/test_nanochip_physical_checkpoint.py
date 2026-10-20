"""Constructed checkpoint provenance guards; never physical closure evidence."""

from dataclasses import asdict
import json
from pathlib import Path

import pytest

from nanochip.laboratory.contracts import Artifact, ContractError
from nanochip.laboratory.physical import flow
from nanochip.laboratory.physical.checkpoint import prepare_cts_checkpoint
from nanochip.laboratory.physical.clock_flow import FLOW_FILES, PROFILE


def fixture(tmp_path):
    parent, child = tmp_path / "parent", tmp_path / "child"
    stage = parent / "runs/physical/30-openroad-cts"
    stage.mkdir(parents=True)
    child.mkdir()
    config = {"DESIGN_NAME": "nanochip_teaching_core", "VERILOG_FILES": ["dir::core.v"], "CLOCK_PORT": "clk", "CLOCK_PERIOD": 100, "SYNTH_STRATEGY": "AREA 3"}
    for root in (parent, child):
        (root / "core.v").write_text("constructed source fixture")
    (parent / "config.json").write_text(json.dumps(config))
    (child / "config.json").write_text(json.dumps({**config, "meta": {"flow": PROFILE}, "NANOCHIP_CLOCK_BRANCH_SIZE": 8}))
    for name in ("fixture.odb", "fixture.sdc"):
        (stage / name).write_text("constructed view fixture")
    state = {"odb": "/work/runs/physical/30-openroad-cts/fixture.odb", "sdc": "/work/runs/physical/30-openroad-cts/fixture.sdc", "metrics": {"fixture_metric": 7}}
    (stage / "state_out.json").write_text(json.dumps(state))
    artifacts = [asdict(Artifact.from_file(parent, str(p.relative_to(parent)))) for p in parent.rglob("*") if p.is_file()]
    receipt = {"image": flow.IMAGE, "pdk_revision": flow.PDK_REVISION, "design_name": config["DESIGN_NAME"],
               "scope": "accelerator:nanochip_teaching_core", "artifacts": artifacts,
               "source_manifest": [asdict(Artifact.from_file(parent, "core.v"))], "status": "error", "ok": False}
    (parent / "receipt.json").write_text(json.dumps(receipt))
    return parent, child


def prepare(parent, child):
    return prepare_cts_checkpoint(parent, child, runtime_root="/work", image=flow.IMAGE, pdk_revision=flow.PDK_REVISION)


def test_checkpoint_copies_exact_bound_views_and_marks_upstream_reuse(tmp_path):
    parent, child = fixture(tmp_path)
    result = prepare(parent, child)
    manifest = json.loads((child / result["manifest_path"]).read_text())
    state = json.loads((child / manifest["rewritten_state_path"]).read_text())
    assert manifest["upstream_evidence_mode"] == "reused_checkpoint"
    assert state["metrics"] == {"fixture_metric": 7}
    assert state["odb"] == "/work/checkpoint/views/runs/physical/30-openroad-cts/fixture.odb"
    assert all((child / item["path"]).read_bytes() == (parent / item["parent_path"]).read_bytes() for item in manifest["copied_views"])


def test_checkpoint_rejects_clock_or_source_changes(tmp_path):
    parent, child = fixture(tmp_path)
    config = json.loads((child / "config.json").read_text())
    config["CLOCK_PERIOD"] = 200
    (child / "config.json").write_text(json.dumps(config))
    with pytest.raises(ContractError, match="acceptance configuration"):
        prepare(parent, child)


def test_checkpoint_rejects_a_changed_parent_view(tmp_path):
    parent, child = fixture(tmp_path)
    (parent / "runs/physical/30-openroad-cts/fixture.odb").write_text("changed view")
    with pytest.raises(ContractError):
        prepare(parent, child)


def test_custom_profile_assets_are_separate_from_rtl_manifest(tmp_path, monkeypatch):
    source = tmp_path / "core.v"
    source.write_text("constructed RTL fixture")
    monkeypatch.setattr(flow.shutil, "which", lambda _: None)
    result = flow.run_physical_design({"core.v": source}, tmp_path / "run",
        config={"DESIGN_NAME": "nanochip_teaching_core", "VERILOG_FILES": ["dir::core.v"], "meta": {"flow": PROFILE}},
        scope="accelerator:nanochip_teaching_core", boundary="constructed dispatch fixture", mode="docker")
    assert result["status"] == "unavailable" and not result["ok"]
    assert [row["path"] for row in result["source_manifest"]] == ["core.v"]
    assert {row["path"] for row in result["flow_assets"]} == {"flow-assets/" + name for name in FLOW_FILES}
    assert all(row["source_path"] == "nanochip/laboratory/physical/" + Path(row["path"]).name for row in result["flow_assets"])
