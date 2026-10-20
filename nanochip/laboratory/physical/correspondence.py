"""Finite complete-workload checks of the exact final LVS netlist.

A passing result is scoped gate-level simulation, not formal equivalence.
The original mapped netlist, Liberty functions, PG normalization audit,
checker, program, memory image, tables, and all output dumps are retained.
"""

from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

from ..contracts import Artifact, CheckRequirement, ContractError, RunReceipt, Task, file_sha256
from ..teaching_core.backend import CHECKS, SCOPE
from . import flow

LIBERTY = "/foss/pdks/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
# SHA-256 of LIBERTY extracted from flow.IMAGE at flow.PDK_REVISION.
# This adapter commits to this bundle; cell_models.py remains library-generic.
LIBERTY_SHA256 = "8e78e14442062dba34d414fca6490b2f6b96038d4510d1438ca44fee31487135"
WORKLOAD_FILES = ("core.v", "core_tb.cpp", "rtl.py", "program.bin", "program.json", "tables.bin", "reference/image.bin",
                  "reference/goldens.npz", "reference/receipt.json", "task.json", "physical-config.json")
NUMERICAL_SOURCES = tuple("nanochip/kpu/" + name for name in (
    "reference/config.py", "reference/model.py", "reference/gen_weights.py", "reference/prng.py",
    "harness/memmap.py", "harness/scoring.py", "rtl/selfmodel/fxmodel.py", "rtl/selfmodel/fxluts.py"))
EXECUTION_FILES = {"core.v": "core.v", "core_tb.cpp": "core_tb.cpp", "program.bin": "program.bin",
                   "tables.bin": "tables.bin", "image.bin": "reference/image.bin"}


def _manifest(items, root, *, required=()):
    artifacts = {}
    for item in items:
        artifact = Artifact(**item)
        if artifact.path in artifacts:
            raise ContractError("Repeated artifact in evidence manifest")
        artifact.validate(root)
        artifacts[artifact.path] = artifact.sha256
    if not set(required) <= set(artifacts):
        raise ContractError("Required evidence artifacts are missing: " + str(sorted(set(required) - set(artifacts))))
    return artifacts


def _task_context(root, candidate=None):
    """Recover the frozen contract, never infer profiles from a successful run."""
    root = Path(root)
    raw = json.loads((root / "task.json").read_text())
    raw["required_checks"] = tuple(CheckRequirement(**check) for check in raw["required_checks"])
    task = Task(**raw)
    if candidate is not None:
        candidate.validate_files()
        _manifest([asdict(a) for a in candidate.artifacts], root, required=WORKLOAD_FILES)
        if candidate.task_id != task.task_id or candidate.task_digest != task.digest:
            raise ContractError("Candidate does not match its frozen task artifact")
    if not {(name, SCOPE) for name in CHECKS} <= {(check.name, check.scope) for check in task.required_checks}:
        raise ContractError("Frozen task omits complete-workload checks")
    profiles = task.specification.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise ContractError("Frozen task must declare nonempty workload/reset profiles")
    for profile in profiles:
        if (not isinstance(profile, dict) or set(profile) != {"latency", "stall_permille", "reset_seed", "jitter"}
                or any(type(value) is not int for value in profile.values())
                or profile["latency"] < 1 or not 0 <= profile["stall_permille"] < 1000
                or profile["reset_seed"] < 0 or profile["jitter"] < 0):
            raise ContractError("Malformed frozen memory/reset profile")
    if task.specification.get("physical"):
        declared = task.specification["physical"]
        if (declared.get("image") != flow.IMAGE or declared.get("pdk_revision") != flow.PDK_REVISION
                or json.loads((root / "physical-config.json").read_text()) != declared.get("configuration")):
            raise ContractError("Physical configuration/platform differs from frozen task")
    # Reference generation is bound to this workload, not a default seed/prompt.
    numerical = json.loads((root / "reference/receipt.json").read_text())
    if (numerical.get("schema") != "nanochip-teaching-core-reference/v0" or numerical.get("status") != "pass"
            or numerical.get("seed") != task.specification["seed"]
            or numerical.get("prompt_index") != task.specification["prompt_index"]
            or len(numerical.get("tokens", ())) != task.specification["token_count"]
            or (task.specification.get("tokens") is not None and numerical["tokens"] != task.specification["tokens"])):
        raise ContractError("Numerical reference belongs to another workload")
    if json.loads((root / "reference/contract.json").read_text()) != task.specification["target"]:
        raise ContractError("Numerical reference geometry/contract differs from frozen workload")
    _manifest(numerical["outputs"], root / "reference", required=("image.bin", "goldens.npz", "contract.json", "request.json"))
    frozen_sources = task.specification["source_artifacts"]
    recorded_sources = {item["path"] for item in numerical["source_artifacts"]}
    if not set(NUMERICAL_SOURCES) <= recorded_sources or len(recorded_sources) != len(numerical["source_artifacts"]):
        raise ContractError("Numerical reference lacks required source provenance")
    for artifact in numerical["source_artifacts"]:
        if frozen_sources.get(artifact["path"]) != artifact["sha256"]:
            raise ContractError("Numerical reference source differs from frozen task")
    for filename in ("core_tb.cpp", "rtl.py"):
        key = "nanochip/laboratory/teaching_core/" + filename
        if frozen_sources.get(key) != file_sha256(root / filename):
            raise ContractError("Workload checker differs from frozen task")
    program = json.loads((root / "program.json").read_text())
    if (program["configuration"] != task.specification["target"]["configuration"]
            or program["token_count"] != task.specification["token_count"]
            or program["program_sha256"] != file_sha256(root / "program.bin")
            or program["tables_sha256"] != file_sha256(root / "tables.bin")):
        raise ContractError("Program/table manifest differs from frozen workload")
    return task, profiles


def _validate_execution(raw, root, workload, profiles, *, gate_source=None):
    """Require actual runner-copied inputs and every task-declared profile."""
    if raw.get("status") != "completed" or raw.get("ok") is not True:
        raise ContractError("Complete fresh execution is required")
    inputs = _manifest(raw["inputs"], root, required=EXECUTION_FILES)
    for executed, original in EXECUTION_FILES.items():
        expected = gate_source if executed == "core.v" and gate_source is not None else file_sha256(Path(workload) / original)
        if inputs[executed] != expected:
            raise ContractError("Executed input differs from the candidate workload: " + executed)
    if raw.get("runner_sha256") != file_sha256(Path(workload) / "rtl.py"):
        raise ContractError("Executed runner differs from manifested workload checker")
    rows = raw.get("profiles", [])
    if [row.get("profile") for row in rows] != profiles:
        raise ContractError("Execution omitted or changed frozen task profiles")
    for row, expected in zip(rows, profiles):
        counters = row.get("result", {})
        if (type(row.get("returncode")) is not int or row["returncode"] != 0 or row.get("timed_out") is not False
                or counters.get("status") != "completed" or type(counters.get("protocol_errors")) is not int or counters["protocol_errors"] != 0
                or any(type(counters.get(key)) is not int or counters[key] < minimum for key, minimum in (("cycles", 1), ("read_beats", 1), ("write_beats", 1)))
                or any(type(counters.get(key)) is not int or counters[key] != expected[key] for key in ("latency", "stall_permille", "reset_seed"))):
            raise ContractError("A declared workload/reset/memory profile did not pass")
        Artifact.from_file(root, row["dump"]).validate(root)
    return inputs


def _physical_chain(root, workload):
    """Validate the producer's retained bytes before accepting final LVS/GDS."""
    root, workload = Path(root), Path(workload)
    producer = json.loads((root / "receipt.json").read_text())
    if (producer.get("schema") != "nanochip-physical/v1" or producer.get("status") != "completed"
            or type(producer.get("returncode")) is not int or producer["returncode"] != 0 or producer.get("image") != flow.IMAGE
            or producer.get("pdk") != "sky130A" or producer.get("pdk_revision") != flow.PDK_REVISION
            or producer.get("scope") != SCOPE or producer.get("design_name") != "nanochip_teaching_core"
            or producer.get("flow_stop_at") is not None):
        raise ContractError("Final physical producer platform/scope identity differs")
    artifacts = _manifest(producer["artifacts"], root, required=("core.v", "config.json", "source-manifest.json", "runner.py"))
    for name in ("core.v", "physical-config.json"):
        physical_name = "config.json" if name == "physical-config.json" else name
        if file_sha256(workload / name) != artifacts[physical_name]:
            raise ContractError("Physical source/configuration differs from candidate")
    if producer.get("config_sha256") != artifacts["config.json"] or producer.get("runner_sha256") != artifacts["runner.py"] or producer.get("source_manifest_sha256") != artifacts["source-manifest.json"]:
        raise ContractError("Physical producer input identity differs from retained files")
    sources = _manifest(producer["source_manifest"], root, required=("core.v",))
    if sources != {"core.v": artifacts["core.v"]} or json.loads((root / "source-manifest.json").read_text()) != producer["source_manifest"]:
        raise ContractError("Physical source manifest is not the selected core")
    _physical_provenance(root, workload, producer, artifacts)
    stages = sorted((root / "runs/physical").glob("*-netgen-lvs"))
    if len(stages) != 1:
        raise ContractError("A completed final LVS producer is required")
    stage = stages[0]
    state_path = stage / "state_in.json"
    state = json.loads(state_path.read_text())
    state_out = json.loads((stage / "state_out.json").read_text())
    count = state_out.get("metrics", {}).get("design__lvs_error__count")
    if type(count) not in (int, float) or count != 0 or not any(c.get("name") == "physical_lvs" and c.get("scope") == SCOPE and c.get("status") == "pass" for c in producer.get("checks", [])):
        raise ContractError("Final LVS did not pass against the layout")
    resolved = json.loads((stage / "config.json").read_text())
    if resolved.get("DESIGN_NAME") != "nanochip_teaching_core":
        raise ContractError("Final LVS top differs from selected core")
    netlist = root / flow._retained_relative(root, state["pnl"])
    lvs_gds = root / flow._retained_relative(root, state["gds"])
    spice = root / flow._retained_relative(root, state["spice"])
    gds = root / "runs/physical/final/gds/nanochip_teaching_core.gds"
    required = (state_path, stage / "state_out.json", stage / "config.json", netlist, lvs_gds, spice, gds)
    for path in required:
        relative = str(path.relative_to(root))
        if relative not in artifacts or file_sha256(path) != artifacts[relative]:
            raise ContractError("Final producer artifact is absent/stale: " + relative)
    if gds.stat().st_size == 0 or file_sha256(gds) != file_sha256(lvs_gds):
        raise ContractError("Final GDS differs from the LVS producer layout")
    return producer, stage, state_path, state, resolved, netlist, gds


def _physical_provenance(root, workload, producer, artifacts):
    """Keep a checkpoint continuation explicit and bind every imported view."""
    from .clock_flow import FLOW_FILES, PROFILE
    from .checkpoint import STRATEGY_KEYS
    profile = producer.get("flow_profile", "Classic")
    mode = producer.get("execution_mode", "legacy_unspecified")
    if profile not in ("Classic", "NanochipClockRepair") or mode not in ("legacy_unspecified", "fresh", "checkpoint_continuation"):
        raise ContractError("Unsupported physical producer profile/execution mode")
    config = json.loads((root / "config.json").read_text())
    if profile != ((config.get("meta") or {}).get("flow") or "Classic"):
        raise ContractError("Physical profile differs from selected configuration")
    frozen = json.loads((workload / "task.json").read_text())["specification"]["source_artifacts"]
    assets = producer.get("flow_assets", [])
    expected_assets = {"nanochip/laboratory/physical/" + name: "flow-assets/" + name for name in FLOW_FILES} if profile == PROFILE else {}
    if len(assets) != len(expected_assets) or {a["source_path"] for a in assets} != set(expected_assets):
        raise ContractError("Physical profile requires its exact complete frozen flow asset set")
    seen = set()
    for asset in assets:
        path, digest, source = asset["path"], asset["sha256"], asset["source_path"]
        if path in seen or path != expected_assets[source] or artifacts.get(path) != digest or frozen.get(source) != digest:
            raise ContractError("Physical flow asset differs from frozen task/producer artifacts")
        seen.add(path)
    if mode != "checkpoint_continuation":
        if producer.get("checkpoint") is not None:
            raise ContractError("Checkpoint evidence cannot be relabeled as a fresh/unspecified physical run")
        return
    if profile != PROFILE:
        raise ContractError("Checkpoint continuation requires the manifested clock-repair profile")
    link = producer["checkpoint"]
    manifest_path = link["manifest_path"]
    if artifacts.get(manifest_path) != link["manifest_sha256"]:
        raise ContractError("Checkpoint manifest is not linked to the physical producer")
    checkpoint = json.loads((root / manifest_path).read_text())
    if (checkpoint.get("schema") != "nanochip-physical-checkpoint/v1"
            or checkpoint.get("upstream_evidence_mode") != "reused_checkpoint"
            or checkpoint.get("start_at") != "Nanochip.ClockFanoutRepair"):
        raise ContractError("Unsupported physical checkpoint boundary")
    for prefix in ("parent_receipt", "parent_core", "parent_config", "original_state", "rewritten_state", "parent_cancellation"):
        if prefix == "parent_cancellation" and prefix + "_path" not in checkpoint:
            continue
        if artifacts.get(checkpoint[prefix + "_path"]) != checkpoint[prefix + "_sha256"]:
            raise ContractError("Checkpoint retained artifact changed: " + prefix)
    parent = json.loads((root / checkpoint["parent_receipt_path"]).read_text())
    if any(parent.get(key) != producer.get(key) for key in ("schema", "image", "pdk", "pdk_revision", "scope", "design_name")):
        raise ContractError("Checkpoint parent platform/scope differs")
    parent_artifacts = {a["path"]: a["sha256"] for a in parent["artifacts"]}
    if (len(parent_artifacts) != len(parent["artifacts"])
            or parent_artifacts.get("core.v") != checkpoint["parent_core_sha256"]
            or checkpoint["parent_core_sha256"] != artifacts["core.v"]
            or parent_artifacts.get("config.json") != checkpoint["parent_config_sha256"]
            or parent.get("config_sha256") != checkpoint["parent_config_sha256"]
            or parent_artifacts.get(checkpoint["parent_stage_state_path"]) != checkpoint["original_state_sha256"]):
        raise ContractError("Checkpoint parent source/configuration/state identity differs")
    parent_config = json.loads((root / checkpoint["parent_config_path"]).read_text())
    patch = checkpoint["config_patch"]
    if not isinstance(patch, dict) or not set(patch) <= STRATEGY_KEYS:
        raise ContractError("Checkpoint patch changes settings outside the declared continuation strategy")
    if "meta" in patch and patch["meta"] != {**(parent_config.get("meta") or {}), "flow": PROFILE}:
        raise ContractError("Checkpoint patch may change only the flow identity within metadata")
    if {**parent_config, **patch} != config:
        raise ContractError("Checkpoint configuration patch does not produce selected configuration")
    views = {}
    for view in checkpoint["copied_views"]:
        if (view["parent_path"] in views or parent_artifacts.get(view["parent_path"]) != view["sha256"]
                or artifacts.get(view["path"]) != view["sha256"]):
            raise ContractError("Imported checkpoint view differs from canceled parent artifacts")
        views[view["parent_path"]] = view["path"]

    def original_relative(value):
        if value.startswith("/work/"):
            return value[len("/work/"):]
        execution_root = parent.get("execution_root")
        if execution_root and value.startswith(execution_root.rstrip("/") + "/"):
            return value[len(execution_root.rstrip("/")) + 1:]
        if "/runs/physical/" in value:
            return "runs/physical/" + value.split("/runs/physical/", 1)[1]
        return value if value in parent_artifacts else None

    def same_state(before, after):
        if isinstance(before, dict):
            return isinstance(after, dict) and before.keys() == after.keys() and all(same_state(value, after[key]) for key, value in before.items())
        if isinstance(before, list):
            return isinstance(after, list) and len(before) == len(after) and all(same_state(a, b) for a, b in zip(before, after))
        relative = original_relative(before) if isinstance(before, str) else None
        if relative is not None:
            return relative in views and isinstance(after, str) and flow._retained_relative(root, after) == views[relative]
        return type(before) is type(after) and before == after

    original = json.loads((root / checkpoint["original_state_path"]).read_text())
    rewritten = json.loads((root / checkpoint["rewritten_state_path"]).read_text())
    if not same_state(original, rewritten):
        raise ContractError("Rewritten checkpoint state changes data/metrics or uses unbound imported views")


def _model_linkage(root, audit, netlist_sha256):
    """Link the compiled wrapper to this netlist/library, not another model run."""
    root = Path(root)
    if file_sha256(root / "standard-cells.lib") != LIBERTY_SHA256:
        raise ContractError("Functional Liberty differs from the exact pinned platform library")
    plan = json.loads((root / "model-plan.json").read_text())
    metadata_path = root / "models/model-metadata.json"
    metadata = json.loads(metadata_path.read_text())
    if (plan["model_metadata_sha256"] != file_sha256(metadata_path)
            or metadata["netlist_sha256"] != netlist_sha256
            or metadata["liberty_sha256"] != file_sha256(root / "standard-cells.lib")
            or metadata["script_sha256"] != file_sha256(root / "models/models.ys")
            or audit["audit_sha256"] != file_sha256(root / "models/model-audit.json")):
        raise ContractError("Normalized model is not linked to the actual final netlist/library")
    for field in ("script_path", "normalized_path", "simulation_source_path", "audit_path", "liberty_sha256", "netlist_sha256"):
        if plan[field] != metadata[field]:
            raise ContractError("Normalized model plan differs from its producer metadata")


def compare_gate_dumps(functional_root, functional_profiles, gate_root, gate_profiles):
    """Compare every declared profile, including the full external-memory dump."""
    if not functional_profiles or len(functional_profiles) != len(gate_profiles):
        raise ContractError("Every declared workload/reset/memory profile must execute")
    observations = []
    for expected, actual in zip(functional_profiles, gate_profiles):
        if expected["profile"] != actual["profile"]:
            raise ContractError("Gate-level profiles differ from functional evidence")
        if actual.get("result", {}).get("status") != "completed" or actual.get("returncode") != 0 or actual.get("timed_out"):
            raise ContractError("A gate-level workload did not complete")
        if actual["result"].get("protocol_errors") != 0:
            raise ContractError("Gate-level memory/command protocol check failed")
        reference = Path(functional_root) / expected["dump"]
        gate = Path(gate_root) / actual["dump"]
        observations.append({"profile": expected["profile"], "functional_dump_sha256": file_sha256(reference),
                             "gate_dump_sha256": file_sha256(gate), "byte_equal": reference.read_bytes() == gate.read_bytes(),
                             "gate_result": actual["result"]})
    return observations


def run_correspondence(physical_output, candidate, functional: RunReceipt, output, *, timeout_s=3600, cores=2, mode=None):
    """Require exact final powered netlist and fresh candidate-linked references."""
    if type(timeout_s) not in (int, float) or not math.isfinite(timeout_s) or timeout_s <= 0 or type(cores) is not int or not 1 <= cores <= 8:
        raise ValueError("Use positive finite gate-simulation bounds and 1..8 CPU cores")
    mode = flow._runtime_mode(mode)
    physical_output, output = Path(physical_output).resolve(strict=True), Path(output).resolve()
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.monotonic()
    result = {"schema": "nanochip-final-netlist-correspondence/v1", "method": "finite_gate_level_simulation", "status": "unresolved",
              "formal_status": "unproven", "eligible": False, "execution_mode": "fresh", "functional_evidence_mode": functional.mode, "scope": SCOPE, "image": flow.IMAGE,
              "runtime_mode": mode, "runtime_image_id": os.environ.get("NANOCHIP_RUNTIME_IMAGE_ID") if mode == "native" else None,
              "timeout_s": timeout_s, "cores": cores, "candidate_digest": candidate.digest,
              "task_id": candidate.task_id, "task_digest": candidate.task_digest, "physical_root": str(physical_output), "commands": [], "inputs": [],
              "boundary": "Exact final LVS netlist under the declared complete workload/reset/backpressure cases; ideal powered zero-delay digital cell models. No unbounded formal or timing-simulation claim."}
    name = "nanochip-gate-check-" + uuid.uuid4().hex[:12]
    try:
        candidate.validate_files()
        root = Path(candidate.root)
        task, profiles = _task_context(root, candidate)
        required = {(check, SCOPE) for check in CHECKS}
        passed = {(check.name, check.scope) for check in functional.checks if check.status == "pass"}
        if functional.mode != "fresh" or functional.execution_status != "success" or functional.task_id != candidate.task_id or functional.candidate_digest != candidate.digest or not required <= passed:
            raise ContractError("Fresh passing complete-workload evidence for this candidate is required")
        reference_root = Path(functional.output_root)
        _manifest([asdict(a) for a in functional.output_artifacts], reference_root,
                  required=("receipt.json", "checks.json", *EXECUTION_FILES))
        reference = json.loads((reference_root / "receipt.json").read_text())
        _validate_execution(reference, reference_root, root, profiles)
        reported = json.loads((reference_root / "checks.json").read_text())["checks"]
        if any(reported.get(name) != "pass" for name in CHECKS):
            raise ContractError("Retained functional checker did not pass all required checks")
        producer, stage, state_path, state, resolved, netlist, gds = _physical_chain(physical_output, root)
        result["workload_inputs"] = {"root": str(root), "artifacts": [asdict(Artifact.from_file(root, path)) for path in WORKLOAD_FILES]}
        result["functional_reference"] = {"root": str(reference_root), "artifacts": [asdict(artifact) for artifact in functional.output_artifacts],
                                            "run_receipt": asdict(functional)}
        result["physical_config_sha256"] = file_sha256(physical_output / "config.json")
        result["physical_receipt_sha256"] = file_sha256(physical_output / "receipt.json")
        result["physical_execution_mode"] = producer.get("execution_mode", "legacy_unspecified")
        result["physical_flow_profile"] = producer.get("flow_profile", "Classic")
        result["layout_artifact"] = asdict(Artifact.from_file(physical_output, str(gds.relative_to(physical_output))))
        result["physical_platform"] = {key: producer[key] for key in ("image", "pdk", "pdk_revision", "scope", "design_name")}
        physical = {}
        for key in ("FILL_CELL", "DECAP_CELL", "WELLTAP_CELL", "ENDCAP_CELL"):
            values = resolved.get(key) or []
            for master in values if isinstance(values, list) else [values]:
                physical[master] = []
        if resolved.get("DIODE_CELL"):
            master, pin = resolved["DIODE_CELL"].split("/")
            physical[master] = [pin]
        shutil.copyfile(netlist, output / "gate.v")
        result.update(netlist_path=str(netlist), netlist_sha256=file_sha256(netlist), producer_state_sha256=file_sha256(state_path), producer_state_path=str(state_path.relative_to(physical_output)),
                      functional_receipt_sha256=file_sha256(reference_root / "receipt.json"), profiles=profiles)
        for path in (netlist, state_path, stage / "config.json"):
            result["inputs"].append(asdict(Artifact.from_file(physical_output, str(path.relative_to(physical_output)))))
        copied = {"core_tb.cpp": root / "core_tb.cpp", "rtl-checker.py": root / "rtl.py", "program.bin": root / "program.bin",
                  "tables.bin": root / "tables.bin", "image.bin": root / "reference/image.bin", "model-checker.py": Path(__file__).with_name("cell_models.py")}
        for target, source in copied.items():
            shutil.copyfile(source, output / target)
            result["inputs"].append({"path": target, "sha256": file_sha256(output / target)})
        runroot = str(output) if mode == "native" else "/gate-check"
        # The driver imports only copied, hash-bound stdlib checkers.
        driver = '''import hashlib,importlib.util,json,pathlib,subprocess,time
root=pathlib.Path(__file__).resolve().parent
started=time.monotonic()
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
models=load("frozen_models",root/"model-checker.py")
rtl=load("frozen_rtl",root/"rtl-checker.py")
settings=json.loads((root/"settings.json").read_text())
if hashlib.sha256((root/"standard-cells.lib").read_bytes()).hexdigest()!=settings["liberty_sha256"]:
 raise ValueError("Functional Liberty differs from the exact pinned platform library")
plan=models.write_model_script(root/"standard-cells.lib",root/"gate.v",root/"models",top="nanochip_teaching_core",physical_only_cells=settings["physical"],power_ports=settings["power_ports"])
(root/"model-plan.json").write_text(json.dumps(plan,indent=2,sort_keys=True)+"\\n")
with (root/"normalization.log").open("w") as f:
 code=subprocess.run(["yosys","-Q","-T","-s",plan["script_path"]],stdout=f,stderr=subprocess.STDOUT,timeout=max(.01,settings["timeout_s"]-(time.monotonic()-started))).returncode
if code: raise SystemExit(code)
audit=models.validate_model_audit(plan)
(root/"model-audit-result.json").write_text(json.dumps(audit,indent=2,sort_keys=True)+"\\n")
r=rtl.run_rtl(audit["simulation_source_path"],root/"program.bin",root/"image.bin",root/"tables.bin",root/"execution",bench=root/"core_tb.cpp",timeout_s=max(.01,settings["timeout_s"]-(time.monotonic()-started)),profiles=tuple(settings["profiles"]),build_profile="mapped")
(root/"gate-result.json").write_text(json.dumps(r,indent=2,sort_keys=True)+"\\n")
raise SystemExit(0 if r["ok"] else 1)
'''
        (output / "driver.py").write_text(driver)
        power_ports = {resolved["VDD_PIN"]: 1, resolved["GND_PIN"]: 0}
        if len(power_ports) != 2:
            raise ContractError("Separate nominal supply and ground ports are required")
        result["nominal_power_ports"] = power_ports
        flow._json(output / "settings.json", {"physical": physical, "power_ports": power_ports, "profiles": result["profiles"], "timeout_s": timeout_s, "liberty_sha256": LIBERTY_SHA256})
        result["driver_sha256"] = file_sha256(output / "driver.py")
        if mode == "native":
            if os.environ.get("NANOCHIP_PHYSICAL_IMAGE") != flow.IMAGE or Path("/foss/pdks/sky130A").resolve() != Path(f"/foss/pdks/ciel/sky130/versions/{flow.PDK_REVISION}/sky130A"):
                raise ContractError("Native gate simulation requires the pinned tool-image/PDK identity")
            shutil.copyfile(LIBERTY, output / "standard-cells.lib")
            command = [sys.executable, str(output / "driver.py")]
        else:
            command = ["docker", "run", "--rm", "--pull=never", "--network", "none", "--cpus", str(cores), "--name", name,
                       "--entrypoint", "/bin/bash", "-v", f"{output}:/gate-check", flow.IMAGE, "-lc",
                       "set -e; cp " + LIBERTY + " /gate-check/standard-cells.lib; python3 /gate-check/driver.py"]
        result["commands"].append(command)
        with (output / "driver.log").open("w") as stream:
            code = flow._execute(command, stream, max(.01, timeout_s - (time.monotonic() - started)))
        result["returncode"] = code
        gate_receipt = output / "gate-result.json"
        if code == 0 and gate_receipt.is_file():
            gate = json.loads(gate_receipt.read_text())
            audit = json.loads((output / "model-audit-result.json").read_text())
            if not gate.get("ok") or audit.get("status") != "pass" or audit.get("functional_blackboxes") != 0:
                raise ContractError("Gate execution or functional model coverage did not pass")
            _model_linkage(output, audit, result["netlist_sha256"])
            _validate_execution(gate, output / "execution", root, profiles, gate_source=audit["simulation_source_sha256"])
            observations = compare_gate_dumps(reference_root, reference["profiles"], output / "execution", gate["profiles"])
            result.update(status="pass" if all(row["byte_equal"] for row in observations) else "fail",
                          eligible=all(row["byte_equal"] for row in observations), eligibility_scope="declared finite workload/netlist relation", observations=observations,
                          model_audit=audit, functional_model_sha256=file_sha256(output / "standard-cells.lib"))
        else:
            result["details"] = "Gate normalization/compilation/execution did not complete; inspect retained driver log"
        candidate.validate_files()
        _physical_chain(physical_output, root)
        for artifact in functional.output_artifacts:
            artifact.validate(functional.output_root)
    except subprocess.TimeoutExpired:
        if mode == "docker":
            subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        result.update(status="unresolved", execution_status="timeout", details="Bounded final-netlist simulation timed out; process tree/container killed")
    except (OSError, ValueError, TypeError, KeyError, ContractError) as exc:
        result.update(status="unresolved", details=str(exc))
    result["elapsed_s"] = time.monotonic() - started
    result["artifacts"] = [asdict(Artifact.from_file(output, str(path.relative_to(output)))) for path in sorted(output.rglob("*")) if path.is_file() and not path.is_symlink()]
    flow._json(output / "receipt.json", result)
    return result


def validate_correspondence(receipt_path, *, candidate=None, physical_output=None, functional_output=None) -> dict:
    """Read and recheck retained finite correspondence without rerunning P&R.

    Supply the actual held-out Candidate to require its identity and workload.
    Optional roots rebind container-produced artifacts to their host mounts.
    This validates the scoped relation; physical acceptance remains separate.
    """
    receipt_path = Path(receipt_path).resolve(strict=True)
    root = receipt_path.parent
    result = json.loads(receipt_path.read_text())
    if (result.get("schema") != "nanochip-final-netlist-correspondence/v1"
            or result.get("method") != "finite_gate_level_simulation"
            or result.get("scope") != SCOPE
            or result.get("status") != "pass" or result.get("eligible") is not True
            or result.get("formal_status") != "unproven" or result.get("execution_mode") != "fresh"
            or result.get("functional_evidence_mode") != "fresh"):
        raise ContractError("A completed scoped finite gate-level correspondence result is required")
    if result.get("image") != flow.IMAGE:
        raise ContractError("Mapped execution platform differs from the pinned image")
    _manifest(result["artifacts"], root, required=("gate.v", "gate-result.json", "model-audit-result.json", "model-plan.json", "standard-cells.lib",
                                                "models/model-metadata.json", "models/models.ys", "models/model-audit.json",
                                                "models/normalized.v", "models/simulation.v", "execution/receipt.json"))
    physical = Path(physical_output or result["physical_root"]).resolve(strict=True)
    reference = Path(functional_output or result["functional_reference"]["root"]).resolve(strict=True)
    workload = Path(candidate.root if candidate is not None else result["workload_inputs"]["root"]).resolve(strict=True)
    if candidate is not None:
        candidate.validate_files()
        if (candidate.digest != result["candidate_digest"] or candidate.task_id != result["task_id"]
                or candidate.task_digest != result["task_digest"]):
            raise ContractError("Mapped workload receipt belongs to another candidate/task")
    _manifest(result["workload_inputs"]["artifacts"], workload, required=WORKLOAD_FILES)
    task, profiles = _task_context(workload, candidate)
    if task.task_id != result["task_id"] or task.digest != result["task_digest"] or profiles != result["profiles"]:
        raise ContractError("Mapped receipt differs from the frozen task/profile contract")
    _manifest(result["functional_reference"]["artifacts"], reference, required=("receipt.json", "checks.json", *EXECUTION_FILES))
    reported = result["functional_reference"]["run_receipt"]
    required = {(name, SCOPE) for name in CHECKS}
    passed = {(check["name"], check["scope"]) for check in reported["checks"] if check["status"] == "pass"}
    if (reported["mode"] != "fresh" or reported["execution_status"] != "success" or reported["task_id"] != result["task_id"]
            or reported["candidate_digest"] != result["candidate_digest"] or not required <= passed
            or reported["output_artifacts"] != result["functional_reference"]["artifacts"]):
        raise ContractError("Fresh functional receipt is not bound to the mapped workload")
    producer, stage, state_path, state, resolved, netlist, gds = _physical_chain(physical, workload)
    if file_sha256(physical / "receipt.json") != result["physical_receipt_sha256"]:
        raise ContractError("Physical producer receipt changed")
    if file_sha256(physical / "config.json") != result["physical_config_sha256"] or file_sha256(workload / "physical-config.json") != result["physical_config_sha256"]:
        raise ContractError("Mapped workload physical configuration changed")
    if result["physical_platform"] != {key: producer[key] for key in ("image", "pdk", "pdk_revision", "scope", "design_name")}:
        raise ContractError("Physical producer platform linkage changed")
    if (result.get("physical_execution_mode", "legacy_unspecified") != producer.get("execution_mode", "legacy_unspecified")
            or result.get("physical_flow_profile", "Classic") != producer.get("flow_profile", "Classic")):
        raise ContractError("Physical producer execution/profile provenance changed")
    producer_artifact = Artifact(result["producer_state_path"], result["producer_state_sha256"])
    producer_artifact.validate(physical)
    if producer_artifact.resolve(physical) != state_path:
        raise ContractError("Final LVS producer state linkage changed")
    if file_sha256(netlist) != result["netlist_sha256"] or file_sha256(root / "gate.v") != result["netlist_sha256"]:
        raise ContractError("Final powered netlist linkage changed")
    if not isinstance(result.get("layout_artifact"), dict):
        raise ContractError("Final GDS artifact is mandatory")
    layout = Artifact(**result["layout_artifact"])
    layout.validate(physical)
    if layout.resolve(physical) != gds:
        raise ContractError("Final GDS linkage changed")
    if file_sha256(reference / "receipt.json") != result["functional_receipt_sha256"]:
        raise ContractError("Functional reference receipt changed")
    functional = json.loads((reference / "receipt.json").read_text())
    gate = json.loads((root / "gate-result.json").read_text())
    _validate_execution(functional, reference, workload, profiles)
    if any(json.loads((reference / "checks.json").read_text())["checks"].get(name) != "pass" for name in CHECKS):
        raise ContractError("Retained functional check did not pass")
    _validate_execution(gate, root / "execution", workload, profiles, gate_source=result["model_audit"]["simulation_source_sha256"])
    _model_linkage(root, result["model_audit"], result["netlist_sha256"])
    if gate != json.loads((root / "execution/receipt.json").read_text()):
        raise ContractError("Gate execution receipt differs from the retained runner output")
    observations = compare_gate_dumps(reference, functional["profiles"], root / "execution", gate["profiles"])
    if observations != result["observations"] or not all(row["byte_equal"] for row in observations):
        raise ContractError("Fresh mapped workload dump comparison no longer matches")
    if (result["model_audit"].get("status") != "pass" or result["model_audit"].get("functional_blackboxes") != 0
            or result["model_audit"] != json.loads((root / "model-audit-result.json").read_text())
            or file_sha256(root / "models/normalized.v") != result["model_audit"]["normalized_sha256"]
            or result["model_audit"].get("power_ports") != result["nominal_power_ports"]
            or result["model_audit"].get("power_rail_audit", {}).get("status") != "pass"
            or result["model_audit"].get("power_rail_audit", {}).get("unknown_or_crossed_rails") != 0
            or file_sha256(root / "models/simulation.v") != result["model_audit"]["simulation_source_sha256"]
            or file_sha256(root / "execution/core.v") != result["model_audit"]["simulation_source_sha256"]
            or file_sha256(root / "standard-cells.lib") != result["functional_model_sha256"]):
        raise ContractError("Functional model coverage or normalized netlist changed")
    return {"status": "pass", "scope": SCOPE, "method": result["method"], "formal_status": "unproven", "candidate_bound": candidate is not None,
            "candidate_digest": result["candidate_digest"], "task_id": result["task_id"], "task_digest": result["task_digest"],
            "netlist_sha256": result["netlist_sha256"], "physical_config_sha256": result["physical_config_sha256"],
            "physical_execution_mode": producer.get("execution_mode", "legacy_unspecified"), "physical_flow_profile": producer.get("flow_profile", "Classic"),
            "workload_inputs": result["workload_inputs"], "profiles": result["profiles"],
            "receipt_sha256": file_sha256(receipt_path), "physical_ok": json.loads((physical / "receipt.json").read_text()).get("ok") is True}
