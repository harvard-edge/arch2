"""Constructed evidence tests; none of these fixtures are hardware results."""
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path

import pytest

from nanochip.laboratory.physical import correspondence
from nanochip.laboratory.contracts import (
    Action,
    Artifact,
    Candidate,
    CheckRequirement,
    CheckResult,
    ContractError,
    RunReceipt,
    Task,
    file_sha256,
)
from nanochip.laboratory.physical import flow
from nanochip.laboratory.physical.correspondence import (
    SCOPE,
    CHECKS,
    WORKLOAD_FILES,
    EXECUTION_FILES,
    NUMERICAL_SOURCES,
    compare_gate_dumps,
    validate_correspondence,
)


@pytest.fixture(autouse=True)
def constructed_library_identity(monkeypatch):
    """Only this constructed fixture substitutes its explicitly fake library."""
    monkeypatch.setattr(
        correspondence,
        "LIBERTY_SHA256",
        hashlib.sha256(b"constructed Liberty").hexdigest(),
    )


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) if isinstance(value, (dict, list)) else value)


def manifest(root):
    return [
        asdict(Artifact.from_file(root, str(p.relative_to(root))))
        for p in sorted(root.rglob("*"))
        if p.is_file()
    ]


def test_every_declared_profile_and_protocol_result_must_match(tmp_path):
    for root in (tmp_path / "functional", tmp_path / "gate"):
        root.mkdir()
        (root / "dump.bin").write_bytes(b"fixture")
    profile = {"latency": 1, "stall_permille": 0, "reset_seed": 0, "jitter": 0}
    expected = [{"profile": profile, "dump": "dump.bin"}]
    actual = [
        {
            "profile": profile,
            "dump": "dump.bin",
            "returncode": 0,
            "timed_out": False,
            "result": {"status": "completed", "protocol_errors": 0},
        }
    ]
    assert compare_gate_dumps(
        tmp_path / "functional", expected, tmp_path / "gate", actual
    )[0]["byte_equal"]
    (tmp_path / "gate/dump.bin").write_bytes(b"wrong fixture")
    assert not compare_gate_dumps(
        tmp_path / "functional", expected, tmp_path / "gate", actual
    )[0]["byte_equal"]
    with pytest.raises(ContractError, match="Every declared"):
        compare_gate_dumps(tmp_path / "functional", expected, tmp_path / "gate", [])
    actual[0]["result"]["protocol_errors"] = 1
    with pytest.raises(ContractError, match="protocol"):
        compare_gate_dumps(tmp_path / "functional", expected, tmp_path / "gate", actual)


def fixture(tmp_path):
    c, p, f, q = [
        tmp_path / name for name in ("candidate", "physical", "functional", "proof")
    ]
    for name in WORKLOAD_FILES:
        if name not in ("task.json", "reference/receipt.json"):
            write(c / name, "constructed " + name)
    write(c / "physical-config.json", {"DESIGN_NAME": "nanochip_teaching_core"})
    task = Task(
        "task-fixture",
        ("fixture",),
        tuple(CheckRequirement(name, SCOPE) for name in CHECKS),
        specification={
            "seed": 1,
            "prompt_index": 0,
            "token_count": 1,
            "tokens": [3],
            "target": {"configuration": {"fixture": True}},
            "profiles": [
                {"latency": 24, "stall_permille": 0, "reset_seed": 0, "jitter": 12},
                {"latency": 48, "stall_permille": 50, "reset_seed": 19, "jitter": 24},
            ],
            "source_artifacts": {
                **{
                    "nanochip/laboratory/teaching_core/" + name: file_sha256(c / name)
                    for name in ("core_tb.cpp", "rtl.py")
                },
                **{name: "0" * 64 for name in NUMERICAL_SOURCES},
            },
        },
    )
    write(c / "task.json", asdict(task))
    for name in ("contract.json", "request.json"):
        write(c / "reference" / name, {})
    write(c / "reference/contract.json", task.specification["target"])
    write(
        c / "program.json",
        {
            "configuration": task.specification["target"]["configuration"],
            "token_count": 1,
            "program_sha256": file_sha256(c / "program.bin"),
            "tables_sha256": file_sha256(c / "tables.bin"),
        },
    )
    numerical = {
        "schema": "nanochip-teaching-core-reference/v0",
        "status": "pass",
        "seed": 1,
        "prompt_index": 0,
        "tokens": [3],
        "outputs": manifest(c / "reference"),
        "source_artifacts": [
            {"path": name, "sha256": "0" * 64} for name in NUMERICAL_SOURCES
        ],
    }
    write(c / "reference/receipt.json", numerical)
    candidate = Candidate(
        "fixture",
        task.task_id,
        str(c),
        Action("fixture"),
        tuple(Artifact(**a) for a in manifest(c)),
        task_digest=task.digest,
    )
    profiles = task.specification["profiles"]
    rows = []
    for index, profile in enumerate(profiles):
        row = {
            "profile": profile,
            "dump": f"dump-{index}.bin",
            "returncode": 0,
            "timed_out": False,
            "result": {
                "status": "completed",
                "protocol_errors": 0,
                "cycles": 7,
                "read_beats": 3,
                "write_beats": 1,
                **profile,
            },
        }
        rows.append(row)
        write(f / row["dump"], "constructed complete output image")
        write(q / "execution" / row["dump"], "constructed complete output image")
    for executed, original in EXECUTION_FILES.items():
        write(f / executed, (c / original).read_text())
        write(
            q / "execution" / executed,
            "constructed wrapper"
            if executed == "core.v"
            else (c / original).read_text(),
        )
    functional_raw = {
        "status": "completed",
        "ok": True,
        "profiles": rows,
        "inputs": [asdict(Artifact.from_file(f, name)) for name in EXECUTION_FILES],
        "runner_sha256": file_sha256(c / "rtl.py"),
    }
    write(f / "receipt.json", functional_raw)
    write(f / "checks.json", {"checks": {name: "pass" for name in CHECKS}})
    functional = RunReceipt(
        task.task_id,
        candidate.digest,
        "fresh",
        "success",
        "constructed fixture",
        "fixture",
        checks=tuple(CheckResult(name, "pass", SCOPE) for name in CHECKS),
        output_root=str(f),
        output_artifacts=tuple(Artifact(**a) for a in manifest(f)),
    )
    write(p / "core.v", (c / "core.v").read_text())
    write(p / "config.json", (c / "physical-config.json").read_text())
    write(p / "runner.py", "constructed physical runner")
    sources = [asdict(Artifact.from_file(p, "core.v"))]
    write(p / "source-manifest.json", sources)
    netlist = "runs/physical/final.v"
    stream = "runs/physical/52-magic-streamout/core.gds"
    gds = "runs/physical/final/gds/nanochip_teaching_core.gds"
    spice = "runs/physical/extracted.spice"
    for name, text in (
        (netlist, "constructed netlist"),
        (stream, "constructed GDS"),
        (gds, "constructed GDS"),
        (spice, "constructed SPICE"),
    ):
        write(p / name, text)
    stage = "runs/physical/64-netgen-lvs"
    producer_path = stage + "/state_in.json"
    write(
        p / producer_path,
        {
            "pnl": "/work/" + netlist,
            "gds": "/work/" + stream,
            "spice": "/work/" + spice,
        },
    )
    write(p / stage / "state_out.json", {"metrics": {"design__lvs_error__count": 0}})
    write(p / stage / "config.json", {"DESIGN_NAME": "nanochip_teaching_core"})
    physical = {
        "schema": "nanochip-physical/v1",
        "status": "completed",
        "returncode": 0,
        "ok": False,
        "image": flow.IMAGE,
        "pdk": "sky130A",
        "pdk_revision": flow.PDK_REVISION,
        "scope": SCOPE,
        "design_name": "nanochip_teaching_core",
        "flow_stop_at": None,
        "config_sha256": file_sha256(p / "config.json"),
        "runner_sha256": file_sha256(p / "runner.py"),
        "source_manifest": sources,
        "source_manifest_sha256": file_sha256(p / "source-manifest.json"),
        "checks": [{"name": "physical_lvs", "status": "pass", "scope": SCOPE}],
        "artifacts": manifest(p),
    }
    write(p / "receipt.json", physical)
    write(q / "gate.v", "constructed netlist")
    write(q / "models/normalized.v", "constructed normalized")
    write(q / "models/simulation.v", "constructed wrapper")
    write(q / "standard-cells.lib", "constructed Liberty")
    gate = {
        "status": "completed",
        "ok": True,
        "profiles": rows,
        "inputs": [
            asdict(Artifact.from_file(q / "execution", name))
            for name in EXECUTION_FILES
        ],
        "runner_sha256": file_sha256(c / "rtl.py"),
    }
    write(q / "gate-result.json", gate)
    write(q / "execution/receipt.json", gate)
    write(q / "models/model-audit.json", {"constructed": True})
    write(q / "models/models.ys", "constructed model recipe")
    metadata = {
        "netlist_sha256": file_sha256(q / "gate.v"),
        "liberty_sha256": file_sha256(q / "standard-cells.lib"),
        "script_sha256": file_sha256(q / "models/models.ys"),
        **{
            key: str(q / "models" / name)
            for key, name in (
                ("script_path", "models.ys"),
                ("normalized_path", "normalized.v"),
                ("simulation_source_path", "simulation.v"),
                ("audit_path", "model-audit.json"),
            )
        },
    }
    write(q / "models/model-metadata.json", metadata)
    write(
        q / "model-plan.json",
        {
            **metadata,
            "model_metadata_sha256": file_sha256(q / "models/model-metadata.json"),
        },
    )
    audit = {
        "status": "pass",
        "functional_blackboxes": 0,
        "normalized_sha256": file_sha256(q / "models/normalized.v"),
        "audit_sha256": file_sha256(q / "models/model-audit.json"),
        "power_ports": {"VPWR": 1, "VGND": 0},
        "power_rail_audit": {"status": "pass", "unknown_or_crossed_rails": 0},
        "simulation_source_sha256": file_sha256(q / "models/simulation.v"),
    }
    write(q / "model-audit-result.json", audit)
    receipt = {
        "schema": "nanochip-final-netlist-correspondence/v1",
        "scope": SCOPE,
        "method": "finite_gate_level_simulation",
        "formal_status": "unproven",
        "status": "pass",
        "eligible": True,
        "execution_mode": "fresh",
        "functional_evidence_mode": "fresh",
        "image": flow.IMAGE,
        "candidate_digest": candidate.digest,
        "task_id": candidate.task_id,
        "task_digest": candidate.task_digest,
        "physical_root": str(p),
        "physical_receipt_sha256": file_sha256(p / "receipt.json"),
        "physical_config_sha256": file_sha256(p / "config.json"),
        "producer_state_path": producer_path,
        "producer_state_sha256": file_sha256(p / producer_path),
        "netlist_sha256": file_sha256(q / "gate.v"),
        "workload_inputs": {
            "root": str(c),
            "artifacts": [asdict(a) for a in candidate.artifacts],
        },
        "functional_reference": {
            "root": str(f),
            "artifacts": [asdict(a) for a in functional.output_artifacts],
            "run_receipt": asdict(functional),
        },
        "functional_receipt_sha256": file_sha256(f / "receipt.json"),
        "profiles": profiles,
        "layout_artifact": asdict(Artifact.from_file(p, gds)),
        "nominal_power_ports": {"VPWR": 1, "VGND": 0},
        "model_audit": audit,
        "physical_platform": {
            key: physical[key]
            for key in ("image", "pdk", "pdk_revision", "scope", "design_name")
        },
        "functional_model_sha256": file_sha256(q / "standard-cells.lib"),
        "observations": compare_gate_dumps(f, rows, q / "execution", rows),
        "artifacts": manifest(q),
    }
    write(q / "receipt.json", receipt)
    return candidate, p, f, q


def test_read_only_validator_binds_candidate_and_keeps_physical_acceptance_separate(
    tmp_path,
):
    c, p, f, q = fixture(tmp_path)
    result = validate_correspondence(q / "receipt.json", candidate=c)
    assert result["status"] == "pass" and result["candidate_bound"]
    assert result["physical_ok"] is False and result["formal_status"] == "unproven"
    with pytest.raises(ContractError, match="another candidate"):
        validate_correspondence(
            q / "receipt.json", candidate=replace(c, task_id="another-task")
        )


@pytest.mark.parametrize(
    "target",
    [
        "runs/physical/final.v",
        "core.v",
        "runs/physical/final/gds/nanochip_teaching_core.gds",
        "runs/physical/64-netgen-lvs/state_in.json",
    ],
)
def test_stale_or_missing_physical_artifacts_are_rejected(tmp_path, target):
    c, p, f, q = fixture(tmp_path)
    (p / target).write_text("changed after physical producer")
    with pytest.raises(ContractError):
        validate_correspondence(q / "receipt.json", candidate=c)


def rehash_proof(q, receipt):
    receipt["artifacts"] = [a for a in manifest(q) if a["path"] != "receipt.json"]
    write(q / "receipt.json", receipt)


@pytest.mark.parametrize(
    "name", ["program.bin", "tables.bin", "image.bin", "core_tb.cpp"]
)
def test_actual_gate_inputs_cannot_be_replaced_or_relabelled(tmp_path, name):
    c, p, f, q = fixture(tmp_path)
    (q / "execution" / name).write_text("different executed input")
    raw = json.loads((q / "gate-result.json").read_text())
    for item in raw["inputs"]:
        if item["path"] == name:
            item["sha256"] = file_sha256(q / "execution" / name)
    write(q / "gate-result.json", raw)
    write(q / "execution/receipt.json", raw)
    receipt = json.loads((q / "receipt.json").read_text())
    rehash_proof(q, receipt)
    with pytest.raises(ContractError, match="Executed input differs"):
        validate_correspondence(q / "receipt.json", candidate=c)


def test_frozen_profiles_cannot_be_dropped_even_if_both_runs_match(tmp_path):
    c, p, f, q = fixture(tmp_path)
    raw = json.loads((q / "gate-result.json").read_text())
    raw["profiles"] = raw["profiles"][:1]
    write(q / "gate-result.json", raw)
    write(q / "execution/receipt.json", raw)
    receipt = json.loads((q / "receipt.json").read_text())
    rehash_proof(q, receipt)
    with pytest.raises(ContractError, match="frozen task profiles"):
        validate_correspondence(q / "receipt.json", candidate=c)


def test_same_bytes_from_another_layout_cannot_be_relabelled_as_final(tmp_path):
    c, p, f, q = fixture(tmp_path)
    receipt = json.loads((q / "receipt.json").read_text())
    receipt["layout_artifact"] = None
    write(q / "receipt.json", receipt)
    with pytest.raises((ContractError, TypeError)):
        validate_correspondence(q / "receipt.json", candidate=c)


def test_default_seed_reference_cannot_stand_in_for_new_workload(tmp_path):
    c, p, f, q = fixture(tmp_path)
    numerical = json.loads((Path(c.root) / "reference/receipt.json").read_text())
    numerical["seed"] = 999
    write(Path(c.root) / "reference/receipt.json", numerical)
    # Rebind artifact hashes so the test reaches workload semantics, not merely byte integrity.
    c = replace(c, artifacts=tuple(Artifact(**a) for a in manifest(Path(c.root))))
    receipt = json.loads((q / "receipt.json").read_text())
    receipt["candidate_digest"] = c.digest
    receipt["workload_inputs"]["artifacts"] = [asdict(a) for a in c.artifacts]
    write(q / "receipt.json", receipt)
    with pytest.raises(ContractError, match="another workload"):
        validate_correspondence(q / "receipt.json", candidate=c)


def test_read_only_validator_rejects_another_hardware_scope(tmp_path):
    c, p, f, q = fixture(tmp_path)
    receipt = json.loads((q / "receipt.json").read_text())
    receipt["scope"] = "accelerator:another_top"
    write(q / "receipt.json", receipt)
    with pytest.raises(ContractError, match="scoped finite"):
        validate_correspondence(q / "receipt.json", candidate=c)


def test_rehashed_model_from_another_netlist_is_rejected(tmp_path):
    c, p, f, q = fixture(tmp_path)
    metadata = json.loads((q / "models/model-metadata.json").read_text())
    metadata["netlist_sha256"] = "f" * 64
    write(q / "models/model-metadata.json", metadata)
    plan = json.loads((q / "model-plan.json").read_text())
    plan["netlist_sha256"] = metadata["netlist_sha256"]
    plan["model_metadata_sha256"] = file_sha256(q / "models/model-metadata.json")
    write(q / "model-plan.json", plan)
    rehash_proof(q, json.loads((q / "receipt.json").read_text()))
    with pytest.raises(ContractError, match="actual final netlist/library"):
        validate_correspondence(q / "receipt.json", candidate=c)


def test_rehashed_final_gds_must_still_match_lvs_layout(tmp_path):
    c, p, f, q = fixture(tmp_path)
    (p / "runs/physical/final/gds/nanochip_teaching_core.gds").write_text(
        "another layout"
    )
    physical = json.loads((p / "receipt.json").read_text())
    physical["artifacts"] = [a for a in manifest(p) if a["path"] != "receipt.json"]
    write(p / "receipt.json", physical)
    receipt = json.loads((q / "receipt.json").read_text())
    receipt["physical_receipt_sha256"] = file_sha256(p / "receipt.json")
    receipt["layout_artifact"] = asdict(
        Artifact.from_file(p, "runs/physical/final/gds/nanochip_teaching_core.gds")
    )
    write(q / "receipt.json", receipt)
    with pytest.raises(ContractError, match="differs from the LVS producer layout"):
        validate_correspondence(q / "receipt.json", candidate=c)


def test_gate_runner_identity_cannot_be_relabelled(tmp_path):
    c, p, f, q = fixture(tmp_path)
    raw = json.loads((q / "gate-result.json").read_text())
    raw["runner_sha256"] = "f" * 64
    write(q / "gate-result.json", raw)
    write(q / "execution/receipt.json", raw)
    rehash_proof(q, json.loads((q / "receipt.json").read_text()))
    with pytest.raises(ContractError, match="runner differs"):
        validate_correspondence(q / "receipt.json", candidate=c)


def test_rehashed_other_liberty_cannot_claim_pinned_platform(tmp_path):
    c, p, f, q = fixture(tmp_path)
    (q / "standard-cells.lib").write_text("another functional library")
    metadata = json.loads((q / "models/model-metadata.json").read_text())
    metadata["liberty_sha256"] = file_sha256(q / "standard-cells.lib")
    write(q / "models/model-metadata.json", metadata)
    plan = json.loads((q / "model-plan.json").read_text())
    plan["liberty_sha256"] = metadata["liberty_sha256"]
    plan["model_metadata_sha256"] = file_sha256(q / "models/model-metadata.json")
    write(q / "model-plan.json", plan)
    receipt = json.loads((q / "receipt.json").read_text())
    receipt["functional_model_sha256"] = metadata["liberty_sha256"]
    rehash_proof(q, receipt)
    with pytest.raises(ContractError, match="exact pinned platform library"):
        validate_correspondence(q / "receipt.json", candidate=c)


def checkpoint_fixture(tmp_path):
    """Constructed continuation metadata; this never represents a resumed flow."""
    c, p, f, q = fixture(tmp_path)
    workload = Path(c.root)
    config = {
        "CLOCK_PERIOD": 100,
        "NANOCHIP_CLOCK_BRANCH_SIZE": 8,
        "meta": {"flow": "NanochipClockRepair"},
    }
    write(workload / "physical-config.json", config)
    write(p / "config.json", config)
    write(p / "checkpoint/parent/core.v", (p / "core.v").read_text())
    write(
        p / "checkpoint/parent/config.json",
        {"CLOCK_PERIOD": 100, "NANOCHIP_CLOCK_BRANCH_SIZE": 4},
    )
    original = {"pnl": "/work/runs/physical/final.v", "metrics": {"example": 7}}
    write(p / "checkpoint/original-state.json", original)
    write(
        p / "checkpoint/views/runs/physical/final.v",
        (p / "runs/physical/final.v").read_text(),
    )
    write(
        p / "checkpoint/state.json",
        {**original, "pnl": "/work/checkpoint/views/runs/physical/final.v"},
    )
    parent = json.loads((p / "receipt.json").read_text())
    parent.update(
        status="cancelled",
        returncode=143,
        execution_mode="fresh",
        flow_profile="Classic",
        config_sha256=file_sha256(p / "checkpoint/parent/config.json"),
    )
    parent["artifacts"] = [
        {"path": "core.v", "sha256": file_sha256(p / "core.v")},
        {"path": "config.json", "sha256": parent["config_sha256"]},
        {
            "path": "runs/physical/final.v",
            "sha256": file_sha256(p / "runs/physical/final.v"),
        },
        {
            "path": "runs/physical/42-openroad-globalplacement/state_out.json",
            "sha256": file_sha256(p / "checkpoint/original-state.json"),
        },
    ]
    write(p / "checkpoint/parent/receipt.json", parent)
    task = json.loads((workload / "task.json").read_text())
    assets = []
    from nanochip.laboratory.physical.clock_flow import FLOW_FILES

    for name in FLOW_FILES:
        asset_path = "flow-assets/" + name
        source_path = "nanochip/laboratory/physical/" + name
        write(p / asset_path, "constructed custom flow " + name)
        digest = file_sha256(p / asset_path)
        task["specification"]["source_artifacts"][source_path] = digest
        assets.append(
            {"path": asset_path, "sha256": digest, "source_path": source_path}
        )
    write(workload / "task.json", task)
    checkpoint = {
        "schema": "nanochip-physical-checkpoint/v1",
        "upstream_evidence_mode": "reused_checkpoint",
        "start_at": "Nanochip.ClockFanoutRepair",
        "parent_stage_state_path": "runs/physical/42-openroad-globalplacement/state_out.json",
        "config_patch": {
            "NANOCHIP_CLOCK_BRANCH_SIZE": 8,
            "meta": {"flow": "NanochipClockRepair"},
        },
        "copied_views": [
            {
                "path": "checkpoint/views/runs/physical/final.v",
                "parent_path": "runs/physical/final.v",
                "sha256": file_sha256(p / "runs/physical/final.v"),
            }
        ],
    }
    for prefix, path in (
        ("parent_receipt", "checkpoint/parent/receipt.json"),
        ("parent_core", "checkpoint/parent/core.v"),
        ("parent_config", "checkpoint/parent/config.json"),
        ("original_state", "checkpoint/original-state.json"),
        ("rewritten_state", "checkpoint/state.json"),
    ):
        checkpoint[prefix + "_path"] = path
        checkpoint[prefix + "_sha256"] = file_sha256(p / path)
    write(p / "checkpoint/checkpoint.json", checkpoint)
    producer = json.loads((p / "receipt.json").read_text())
    producer.update(
        execution_mode="checkpoint_continuation",
        flow_profile="NanochipClockRepair",
        flow_assets=assets,
        checkpoint={
            "manifest_path": "checkpoint/checkpoint.json",
            "manifest_sha256": file_sha256(p / "checkpoint/checkpoint.json"),
        },
    )
    return p, workload, producer, checkpoint


@pytest.mark.parametrize(
    "mutation",
    [
        None,
        "view",
        "metrics",
        "config_patch",
        "flow_asset",
        "fresh_label",
        "missing_asset",
        "duplicate_asset",
        "profile",
        "geometry_patch",
        "metadata_patch",
    ],
)
def test_checkpoint_imports_and_profile_assets_are_explicitly_bound(tmp_path, mutation):
    p, workload, producer, checkpoint = checkpoint_fixture(tmp_path)
    if mutation == "view":
        checkpoint["copied_views"][0]["sha256"] = "f" * 64
    elif mutation == "metrics":
        rewritten = json.loads((p / "checkpoint/state.json").read_text())
        rewritten["metrics"]["example"] = 0
        write(p / "checkpoint/state.json", rewritten)
        checkpoint["rewritten_state_sha256"] = file_sha256(p / "checkpoint/state.json")
    elif mutation == "config_patch":
        checkpoint["config_patch"] = {}
    elif mutation == "flow_asset":
        producer["flow_assets"][0]["source_path"] = "not-frozen.py"
    elif mutation == "fresh_label":
        producer["execution_mode"] = "fresh"
    elif mutation == "missing_asset":
        producer["flow_assets"].pop()
    elif mutation == "duplicate_asset":
        producer["flow_assets"][1] = producer["flow_assets"][0]
    elif mutation == "profile":
        producer["flow_profile"] = "Classic"
    elif mutation in ("geometry_patch", "metadata_patch"):
        key, value = (
            ("CLOCK_PERIOD", 200)
            if mutation == "geometry_patch"
            else ("meta", {"flow": "NanochipClockRepair", "version": "changed"})
        )
        checkpoint["config_patch"][key] = value
        config = json.loads((p / "config.json").read_text())
        config[key] = value
        write(p / "config.json", config)
    write(p / "checkpoint/checkpoint.json", checkpoint)
    producer["checkpoint"]["manifest_sha256"] = file_sha256(
        p / "checkpoint/checkpoint.json"
    )
    artifacts = {a["path"]: a["sha256"] for a in manifest(p)}
    if mutation is None:
        correspondence._physical_provenance(p, workload, producer, artifacts)
    else:
        with pytest.raises(ContractError):
            correspondence._physical_provenance(p, workload, producer, artifacts)


@pytest.mark.parametrize(
    "settings",
    [
        {"NANOCHIP_CLOCK_WORKING_PIN_CAPACITANCE": 0.06},
        {"NANOCHIP_CLOCK_BRANCH_CELL": "sky130_fd_sc_hd__clkbuf_8"},
    ],
)
def test_checkpoint_clock_optimization_settings_are_bound(tmp_path, settings):
    p, workload, producer, checkpoint = checkpoint_fixture(tmp_path)
    checkpoint["config_patch"].update(settings)
    config = json.loads((p / "config.json").read_text())
    config.update(settings)
    write(p / "config.json", config)
    write(p / "checkpoint/checkpoint.json", checkpoint)
    producer["checkpoint"]["manifest_sha256"] = file_sha256(
        p / "checkpoint/checkpoint.json"
    )
    correspondence._physical_provenance(
        p, workload, producer, {a["path"]: a["sha256"] for a in manifest(p)}
    )
