"""Execute a learned design action through the existing candidate harness."""

from dataclasses import asdict, replace
import inspect
import json
import math
from pathlib import Path
import shutil
import time

from . import dequant_probe, design_changes, design_learning, model_io
from .adapters import BLOCK_SCOPE, CORE_SCOPE, VerilatorBackend
from .contracts import Artifact, CheckRequirement, CheckResult, ContractError, Cost, RunReceipt, file_sha256
from .design_changes import DesignChangeMaterializer, design_change_task, run_design_checks
from .design_learning import design_input, design_proposer
from .models import sequence as sequence_model
from .models import proposer as model_proposer
from .evidence import JsonlRecorder
from .physical import flow
from .runner import run_campaign


PHYSICAL_CHECKS = (
    "gds_generated", "detailed_route_drc", "magic_drc", "klayout_drc", "physical_drc",
    "physical_lvs", "routed_timing", "electrical_constraints", "postroute_antenna",
)
CHECKPOINT_FILES = ("checkpoint.pt", "config.json", "tokenizer.json", "training.json")


def _write(path: Path, value):
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def _physical_inputs():
    return {"physical_config.json": flow.CONFIG,
            "physical_runner.py": Path(flow.__file__),
            "physical_coverage.tcl": Path(flow.__file__).with_name("coverage.tcl")}


class PhysicalDesignMaterializer:
    """Extend the ordinary candidate with pinned physical implementation inputs."""
    def __init__(self, transformer=None):
        self.transformer = transformer

    def materialize(self, task, action, workspace):
        candidate = DesignChangeMaterializer(transformer=self.transformer).materialize(task, action, workspace)
        artifacts = list(candidate.artifacts)
        for name, source in _physical_inputs().items():
            if file_sha256(source) != task.specification["physical_inputs"][name]:
                raise ContractError("Physical settings changed after task construction")
            shutil.copyfile(source, Path(candidate.root) / name)
            artifacts.append(Artifact.from_file(candidate.root, name))
        return replace(candidate, artifacts=tuple(artifacts))


class FunctionalPhysicalBackend:
    """Run functional checks first, then implement that exact same RTL snapshot.

    Failed checks remain failed; a successful process exit cannot accept them.
    Differential RTL simulation is distinct from RTL/netlist correspondence.
    """
    def __init__(self, check_timeout=120, physical_timeout=900, cores=1):
        self.check_timeout, self.physical_timeout, self.cores = check_timeout, physical_timeout, cores

    def evaluate(self, task, candidate):
        started = time.perf_counter()
        candidate.validate_files()
        if candidate.task_digest != task.digest or candidate.task_id != task.task_id:
            raise ContractError("Design candidate belongs to a different task")
        if task.specification["budgets"] != dict(check_timeout=self.check_timeout,
                                                  physical_timeout=self.physical_timeout, cores=self.cores):
            raise ContractError("Backend resource limits differ from frozen task")
        for name, source in _physical_inputs().items():
            manifested = {a.path:a.sha256 for a in candidate.artifacts}
            if (manifested.get(name) != task.specification["physical_inputs"][name]
                    or file_sha256(source) != manifested.get(name)):
                raise ContractError("Physical tool settings differ from manifested candidate")
        root = Path(candidate.root).parent
        source = Path(candidate.root) / "msh_deq.v"
        source_sha = file_sha256(source)
        functional = VerilatorBackend(self.check_timeout).evaluate(task, candidate)
        if functional.mode != "fresh":
            raise ContractError("Design execution requires fresh functional evidence")
        if file_sha256(Path(functional.output_root) / "candidate.v") != source_sha:
            raise ContractError("Functional execution used a different RTL candidate")
        _write(root / "functional-receipt.json", asdict(functional))
        checks = list(functional.checks)
        metrics = dict(functional.metrics)
        execution = functional.execution_status
        children = [functional]
        functional_pass = execution == "success" and any(
            c.name == "dequant_vectors" and c.scope == BLOCK_SCOPE and c.status == "pass"
            for c in functional.checks)
        differential = None
        if functional_pass:
            differential = run_design_checks(source, root / "differential", self.check_timeout)
            if (differential.get("mode") != "fresh" or differential["source_sha256"] != source_sha
                    or differential["reference_sha256"] != task.specification["source_sha256"]
                    or differential["checker_sha256"] != task.specification["transformer_sha256"]):
                raise ContractError("Differential checker used another candidate/reference/checker")
            completed_mismatch = (differential["status"] == "check_failed"
                and differential.get("simulation", {}).get("returncode") == 1
                and not differential.get("simulation", {}).get("timed_out", True))
            differential_status = "pass" if differential["ok"] else "fail" if completed_mismatch else "not_run"
            if not differential["ok"] and not completed_mismatch:
                execution = {"unavailable":"not_run", "timeout":"timeout"}.get(differential["status"], "error")
            checks.append(CheckResult("sequential_rtl_differential", differential_status,
                                      BLOCK_SCOPE, "Bounded valid-transaction differential simulation, not formal equivalence"))
        if functional_pass and differential["ok"]:
            # Independent adapters copy from this same immutable candidate.
            physical = flow.OpenRoadBackend(self.physical_timeout, self.cores).evaluate(task, candidate)
            if physical.mode != "fresh":
                raise ContractError("Design execution requires fresh physical evidence")
            _write(root / "physical-receipt.json", asdict(physical))
            physical_source = Path(physical.output_root) / "msh_deq.v"
            if file_sha256(physical_source) != source_sha:
                raise ContractError("Physical implementation used a different RTL candidate")
            children.append(physical)
            checks.extend(physical.checks)
            metrics.update(physical.metrics)
            execution = physical.execution_status
        candidate.validate_files()
        _write(root / "execution-link.json", dict(
            task_digest=task.digest, candidate_digest=candidate.digest, action=asdict(candidate.action),
            source_sha256=source_sha, functional_source_sha256=file_sha256(Path(functional.output_root) / "candidate.v"),
            physical_source_sha256=source_sha if len(children) == 2 else None,
            physical_run=len(children) == 2, rtl_netlist_correspondence="unresolved",
        ))
        artifacts = []
        for child in children:
            for item in child.output_artifacts:
                relative = item.resolve(child.output_root).relative_to(root)
                artifacts.append(Artifact(str(relative), item.sha256))
        if differential:
            for item in differential["output_artifacts"]:
                artifacts.append(Artifact("differential/" + item["path"], item["sha256"]))
            artifacts.append(Artifact.from_file(root, "differential/receipt.json"))
        artifacts += [Artifact.from_file(root, name) for name in
                      ("functional-receipt.json", "physical-receipt.json", "execution-link.json")
                      if (root / name).is_file()]
        return RunReceipt(task.task_id, candidate.digest, "fresh", execution,
                          "Nanochip functional and physical composition", "1",
                          checks=tuple(checks), metrics=metrics,
                          cost=Cost(time.perf_counter() - started), output_root=str(root),
                          output_artifacts=tuple(artifacts),
                          details="One exact RTL candidate; finite functional checks and physical results. Full core and RTL/netlist equivalence unresolved.")


def run_design_experiment(checkpoint: Path, output: Path, *, check_timeout=120,
                          physical_timeout=900, cores=1, materializer=None, transformer=None) -> dict:
    """Freeze inputs, decode once with both actions available, and execute it.

    A retained reference decision is reported as such, never replaced by a
    preferred change. The model chooses a supplied transformation; it does not
    author arbitrary RTL. Student materializers use the same checker/backend.
    """
    if (any(not math.isfinite(t) or t <= 0 for t in (check_timeout, physical_timeout))
            or type(cores) is not int or not 1 <= cores <= 8):
        raise ContractError("Use positive finite timeouts and 1..8 CPU cores")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    checkpoint = Path(checkpoint).resolve()
    shutil.copytree(checkpoint, output / "checkpoint")
    checkpoint_artifacts = {name:file_sha256(output / "checkpoint" / name) for name in CHECKPOINT_FILES}
    model_sources = {"sequence.py":Path(sequence_model.__file__),
                     "proposer.py":Path(model_proposer.__file__),
                     "model_io.py":Path(model_io.__file__),
                     "design_learning.py":Path(design_learning.__file__)}
    extension_path = Path(inspect.getsourcefile(transformer)).resolve() if transformer else None
    task = design_change_task()
    task = replace(task, max_proposals=1, max_attempts=1,
        required_checks=task.required_checks + (
            CheckRequirement("sequential_rtl_differential", BLOCK_SCOPE),
            *(CheckRequirement(name, BLOCK_SCOPE) for name in PHYSICAL_CHECKS),
            CheckRequirement("rtl_netlist_correspondence", BLOCK_SCOPE),
            CheckRequirement("workload_functional", CORE_SCOPE),
            CheckRequirement("checked_gds", CORE_SCOPE)),
        specification=dict(task.specification,
            checkpoint_sha256=file_sha256(output / "checkpoint/checkpoint.pt"),
            checkpoint_artifacts=checkpoint_artifacts,
            model_sources={name:file_sha256(path) for name,path in model_sources.items()},
            extension_sha256=file_sha256(extension_path) if extension_path else None,
            physical_inputs={name:file_sha256(path) for name,path in _physical_inputs().items()},
            image=flow.IMAGE, pdk_revision=flow.PDK_REVISION,
            budgets=dict(check_timeout=check_timeout, physical_timeout=physical_timeout, cores=cores)))
    _write(output / "task.json", asdict(task))
    code = output / "code"
    code.mkdir()
    for module in (Path(__file__), Path(design_changes.__file__), Path(design_learning.__file__), Path(dequant_probe.__file__)):
        shutil.copyfile(module, code / module.name)
    for name, module in model_sources.items():
        shutil.copyfile(module, code / name)
    if extension_path:
        shutil.copyfile(extension_path, code / "student_extension.py")
    _write(code / "manifest.json", [asdict(Artifact.from_file(code, path.name)) for path in sorted(code.iterdir())])
    proposer = design_proposer(output / "checkpoint")

    class RecordedProposer:
        def propose(self, task, history, budget):
            for name, digest in task.specification["checkpoint_artifacts"].items():
                if file_sha256(output / "checkpoint" / name) != digest:
                    raise ContractError("Checkpoint configuration, tokenizer, weights, or provenance changed")
            for name, path in model_sources.items():
                if file_sha256(path) != task.specification["model_sources"][name]:
                    raise ContractError("Model implementation changed after task construction")
            action = proposer.propose(task, history, budget)
            if proposer.predictions[-1]["checkpoint_sha256"] != task.specification["checkpoint_sha256"]:
                raise ContractError("Decoded action used a different checkpoint")
            _write(output / "proposal.json", dict(
                input_text=design_input(task), predictions=proposer.predictions,
                action=asdict(action) if action else None, both_actions_available=True,
                checkpoint_sha256=task.specification["checkpoint_sha256"],
                note="Decoded model action; supplied transformation library; no action substitution"))
            return action

    campaign = run_campaign(task, RecordedProposer(), materializer or PhysicalDesignMaterializer(transformer),
                            FunctionalPhysicalBackend(check_timeout, physical_timeout, cores),
                            output / "attempts", JsonlRecorder(output / "events.jsonl"))
    candidate_sources = [path for path in (output / "attempts").glob("attempt-*/candidate/msh_deq.v")
                         if any(o.candidate_digest for o in campaign.observations)]
    result = dict(schema_version=1, scope="one learned block-design proposal through actual tools",
                  campaign=asdict(campaign), predictions=proposer.predictions,
                  source_changed=any(file_sha256(path) != task.specification["source_sha256"] for path in candidate_sources),
                  complete_design_eligible=any(o.eligible for o in campaign.observations),
                  total_wall_seconds=time.perf_counter()-started,
                  limits=["Model chooses an authored transformation, not arbitrary RTL generation",
                          "Training provenance belongs to the loaded checkpoint; action selection alone establishes no physical benefit",
                          "Whole accelerator and exhaustive RTL/netlist equivalence remain unresolved"])
    _write(output / "design-experiment.json", result)
    return result
