"""Exact-candidate functional and physical composition for the teaching core."""

from copy import deepcopy
from dataclasses import asdict, replace
import json
import math
from pathlib import Path
import time
import uuid

from ..contracts import Artifact, CheckRequirement, CheckResult, ContractError, Cost, Metric, RunReceipt, file_sha256
from ..teaching_core.backend import CHECKS, ROOT, SCOPE, TeachingCoreBackend, _validate_sources, default_physical_config, make_task
from . import flow
from .correspondence import run_correspondence

PHYSICAL_CHECKS = ("gds_generated", "postroute_antenna", "detailed_route_drc", "magic_drc", "klayout_drc",
                   "physical_drc", "physical_lvs", "routed_timing", "electrical_constraints", "rtl_netlist_correspondence")
BOUNDARY = ("Complete mathematical teaching derivative with realized standard-cell storage and explicit external memory port. "
            "No upstream Kimi RTL/performance identity, external memory fabrication, manufacturing signoff, or tapeout claim.")
DEFAULT_CONFIG = default_physical_config()


def _validate_bounds(check_timeout, physical_timeout, cores, correspondence_timeout):
    for value in (check_timeout, physical_timeout, correspondence_timeout):
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError("Use positive finite functional, physical, and correspondence budgets")
    if type(cores) is not int or not 1 <= cores <= 8:
        raise ValueError("Use 1..8 CPU cores")


def make_physical_task(seed=1, prompt_index=0, split="development", tokens=None, *,
                       check_timeout=180, physical_timeout=14400, cores=2, correspondence_timeout=3600):
    """Freeze tool/configuration identity and require all checks at complete-core scope."""
    _validate_bounds(check_timeout, physical_timeout, cores, correspondence_timeout)
    task = make_task(seed, prompt_index, split, tokens)
    spec = deepcopy(dict(task.specification))
    package = Path(__file__).parent
    from .clock_flow import FLOW_FILES
    inputs = [package / name for name in dict.fromkeys(
        ("flow.py", "teaching.py", "coverage.tcl", "correspondence.py", "checkpoint.py", *FLOW_FILES))]
    spec["source_artifacts"].update({str(path.relative_to(ROOT)): file_sha256(path) for path in inputs})
    spec["physical"] = {"image": flow.IMAGE, "pdk_revision": flow.PDK_REVISION, "configuration": deepcopy(DEFAULT_CONFIG),
                        "check_timeout": check_timeout, "physical_timeout": physical_timeout, "cores": cores,
                        "correspondence_method": "finite_gate_level_simulation", "correspondence_timeout": correspondence_timeout}
    return replace(task, required_checks=task.required_checks + tuple(CheckRequirement(name, SCOPE) for name in PHYSICAL_CHECKS),
                   specification=spec)


class TeachingCorePhysicalBackend:
    """Run fresh complete-workload checks before physically implementing identical RTL."""

    def __init__(self, check_timeout=180, physical_timeout=14400, cores=2, correspondence_timeout=3600, mode=None):
        _validate_bounds(check_timeout, physical_timeout, cores, correspondence_timeout)
        self.check_timeout, self.physical_timeout, self.cores = check_timeout, physical_timeout, cores
        self.correspondence_timeout = correspondence_timeout
        self.mode = flow._runtime_mode(mode)

    def evaluate(self, task, candidate):
        started = time.monotonic()
        candidate.validate_files()
        if candidate.task_id != task.task_id or candidate.task_digest != task.digest:
            raise ContractError("Physical candidate belongs to a different frozen task")
        required_checks = {(check.name, check.scope) for check in task.required_checks}
        if not {(name, SCOPE) for name in PHYSICAL_CHECKS} <= required_checks:
            raise ContractError("Physical task must require every complete-core physical check")
        expected = {"image": flow.IMAGE, "pdk_revision": flow.PDK_REVISION, "configuration": DEFAULT_CONFIG,
                    "check_timeout": self.check_timeout, "physical_timeout": self.physical_timeout, "cores": self.cores,
                    "correspondence_method": "finite_gate_level_simulation", "correspondence_timeout": self.correspondence_timeout}
        if task.specification.get("physical") != expected:
            raise ContractError("Physical tool/configuration/budgets differ from the frozen task")
        source = Path(candidate.root) / "core.v"
        config = Path(candidate.root) / "physical-config.json"
        manifest = {artifact.path: artifact.sha256 for artifact in candidate.artifacts}
        if manifest.get("core.v") != file_sha256(source) or manifest.get("physical-config.json") != file_sha256(config):
            raise ContractError("Physical inputs are not the manifested candidate inputs")
        if json.loads(config.read_text()) != DEFAULT_CONFIG:
            raise ContractError("Candidate physical configuration differs from frozen task")
        functional = TeachingCoreBackend(timeout_s=self.check_timeout).evaluate(task, candidate)
        if functional.mode != "fresh" or functional.candidate_digest != candidate.digest:
            raise ContractError("Fresh functional evidence for this exact candidate is required")
        if file_sha256(Path(functional.output_root) / "core.v") != manifest["core.v"]:
            raise ContractError("Functional evidence used another RTL source")
        root = Path(candidate.root).parent
        flow._json(root / "functional-receipt.json", asdict(functional))
        checks, metrics = list(functional.checks), dict(functional.metrics)
        required = {(name, SCOPE) for name in CHECKS}
        successful = {(check.name, check.scope) for check in checks if check.status == "pass"}
        physical = correspondence = None
        execution = functional.execution_status
        if execution == "success" and required <= successful:
            output = root / ("physical-" + uuid.uuid4().hex[:12])
            physical = flow.run_physical_design({"core.v": source}, output, config=config, scope=SCOPE,
                                               boundary=BOUNDARY, timeout_s=self.physical_timeout, cores=self.cores,
                                               mode=self.mode)
            if file_sha256(output / "core.v") != manifest["core.v"] or physical.get("config_sha256") != manifest["physical-config.json"]:
                raise ContractError("Physical implementation used another candidate/configuration")
            checks.extend(CheckResult(**item) for item in physical["checks"])
            proof_output = root / ("correspondence-" + uuid.uuid4().hex[:12])
            correspondence = run_correspondence(output, candidate, functional, proof_output,
                                                timeout_s=self.correspondence_timeout, cores=self.cores, mode=self.mode)
            checks.append(CheckResult("rtl_netlist_correspondence", correspondence["status"], SCOPE,
                                      json.dumps({"method": correspondence["method"], "formal_status": correspondence["formal_status"],
                                                  "details": correspondence.get("details", correspondence["boundary"])}, sort_keys=True)))
            postroute = physical.get("stages", {}).get("openroad-stapostpnr", {}).get("metrics", {})
            for name, key, unit in (("postroute_instance_area", "design__instance__area", "um2"),
                                     ("postroute_setup_worst_slack", "timing__setup__ws", "ns"),
                                     ("postroute_hold_worst_slack", "timing__hold__ws", "ns")):
                if flow._number(postroute.get(key)):
                    metrics[name] = Metric(postroute[key], unit, SCOPE)
            execution = {"completed": "success", "timeout": "timeout", "unavailable": "not_run"}.get(physical["status"], "error")
        else:
            checks.extend(CheckResult(name, "not_run", SCOPE, "Physical execution requires all fresh complete-workload checks to pass") for name in PHYSICAL_CHECKS)
        candidate.validate_files()
        _validate_sources(task)
        flow._json(root / "execution-link.json", {"task_digest": task.digest, "candidate_digest": candidate.digest,
                  "candidate_source_sha256": manifest["core.v"], "functional_source_sha256": file_sha256(Path(functional.output_root) / "core.v"),
                  "physical_source_sha256": manifest["core.v"] if physical else None,
                  "physical_config_sha256": manifest["physical-config.json"], "physical_execution": physical is not None,
                  "correspondence_method": correspondence["method"] if correspondence else None,
                  "formal_status": "unproven", "boundary": BOUNDARY})
        artifacts = []
        for artifact in functional.output_artifacts:
            relative = artifact.resolve(functional.output_root).relative_to(root)
            artifacts.append(Artifact(str(relative), artifact.sha256))
        if physical:
            physical_root = output.relative_to(root)
            artifacts.extend(Artifact(str(physical_root / artifact["path"]), artifact["sha256"]) for artifact in physical["artifacts"])
            artifacts.append(Artifact.from_file(root, str(physical_root / "receipt.json")))
        if correspondence:
            proof_root = proof_output.relative_to(root)
            artifacts.extend(Artifact(str(proof_root / artifact["path"]), artifact["sha256"]) for artifact in correspondence["artifacts"])
            artifacts.append(Artifact.from_file(root, str(proof_root / "receipt.json")))
        artifacts.extend(Artifact.from_file(root, name) for name in ("functional-receipt.json", "execution-link.json"))
        return RunReceipt(task.task_id, candidate.digest, "fresh", execution, "Nanochip complete-core functional/physical composition", "1",
                          checks=tuple(checks), metrics=metrics, cost=Cost(time.monotonic() - started), details=BOUNDARY,
                          output_root=str(root), output_artifacts=tuple(artifacts))
