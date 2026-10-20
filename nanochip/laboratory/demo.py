"""One cumulative CPU teaching run, composed from the laboratory components.

The diagnostic model learns from fresh, deliberately constructed RTL faults.
Its adaptation is a second supervised update, not a demonstrated RTL repair.
The separate design model selects one supplied source transformation. Finite
block checks and optional physical implementation measure that exact candidate;
neither a decoded action nor a GDS file establishes complete-chip correctness.
"""

from dataclasses import asdict, replace
import inspect
import json
import math
from pathlib import Path
import shutil
import time

from . import design_changes, design_learning, model_io
from .adapters import BLOCK_SCOPE, CORE_SCOPE, VerilatorBackend
from .contracts import Artifact, CheckRequirement, CheckResult, ContractError, Cost, RunReceipt, file_sha256
from .datasets.dequant_corpus import collect_corpus, load_corpus
from .design_experiment import CHECKPOINT_FILES, PHYSICAL_CHECKS, run_design_experiment
from .evidence import JsonlRecorder
from .experiments import diagnose, learning_study
from .models import proposer as model_proposer, sequence as sequence_model
from .runner import run_campaign


PROTOCOL = dict(seed=0, diagnostic_steps=300, adaptation_steps=150,
                design_seed=17, design_steps=360, training_seconds=60)
LIMITS = [
    "Tiny CPU byte-GRU structured-action models; no pretrained language model or arbitrary RTL generation",
    "Diagnostic labels are a disclosed teaching policy over constructed faults; adaptation uses development rows only",
    "Design labels are authored engineering preferences, not measured optimal-PPA labels",
    "One seed and related synthetic partitions; learning effects do not establish generalization or superiority",
    "Model chooses an authored transformation; retaining the reference is a valid unswapped model decision",
    "Numerical vectors and sequential RTL differential simulation are finite block checks, not formal equivalence",
    "Whole accelerator inference, RTL/netlist correspondence, and manufacturing signoff remain unresolved",
    "A generated GDS file does not establish physical closure or an accepted design",
]


def _write(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def _bound(path):
    path = Path(path).resolve()
    return dict(path=str(path), sha256=file_sha256(path))


def _checkpoint(path):
    return {name: file_sha256(Path(path) / name) for name in CHECKPOINT_FILES}


def _require_updates(result, steps):
    if result["steps_completed"] != steps or not result["parameters_changed"]:
        raise ContractError("Demo requires every predeclared parameter update; partial training is not a completed demo")


def _learn_diagnostics(manifest, output):
    """Train, update from development evidence, then evaluate frozen models."""
    rows = load_corpus(manifest)
    test = [row for row in rows if row["split"] == "test"]
    study = learning_study(manifest, output, train_seconds=PROTOCOL["training_seconds"],
                           adapt_seconds=PROTOCOL["training_seconds"])
    before, after = study["base_training"], study["adapted_training"]
    _require_updates(before, PROTOCOL["diagnostic_steps"])
    base_hashes = _checkpoint(output / "base")
    _require_updates(after, PROTOCOL["adaptation_steps"])
    if after["base_checkpoint_sha256"] != base_hashes["checkpoint.pt"]:
        raise ContractError("Adaptation did not load the declared base checkpoint")
    if after["initial_parameter_sha256"] != before["final_parameter_sha256"]:
        raise ContractError("Adaptation parameter lineage differs from the base model")
    frozen = dict(base=base_hashes, adapted=_checkpoint(output / "adapted"))
    evaluation = dict(base=study["base_evaluation"], adapted=study["adapted_evaluation"])
    report = dict(base_training=before, adapted_training=after, checkpoint_hashes=frozen,
                  evaluation=evaluation,
                  learning_effect=dict(
                      base_training_loss_change=before["final_loss"] - before["initial_loss"],
                      adaptation_training_loss_change=after["final_loss"] - after["initial_loss"],
                      held_out_accuracy_change=evaluation["adapted"]["exact_action_accuracy"]
                          - evaluation["base"]["exact_action_accuracy"],
                      interpretation="Observed one-run diagnostics; no learning-win or RTL-repair claim"),
                  saved_model_inference_record_id=test[0]["record_id"])
    _write(output / "report.json", report)
    return report


class FunctionalDesignBackend:
    """Compose the existing numerical and differential adapters without PDK work."""

    def __init__(self, timeout):
        self.timeout = timeout

    def evaluate(self, task, candidate):
        started = time.perf_counter()
        candidate.validate_files()
        if candidate.task_digest != task.digest or candidate.task_id != task.task_id:
            raise ContractError("Design candidate belongs to a different task")
        if task.specification["check_timeout"] != self.timeout:
            raise ContractError("Numerical/differential budget differs from the frozen task")
        root = Path(candidate.root).parent
        source = Path(candidate.root) / "msh_deq.v"
        source_sha = file_sha256(source)
        functional = VerilatorBackend(self.timeout).evaluate(task, candidate)
        if functional.mode != "fresh" or functional.candidate_digest != candidate.digest:
            raise ContractError("Numerical evidence is not fresh for the selected candidate")
        if file_sha256(Path(functional.output_root) / "candidate.v") != source_sha:
            raise ContractError("Numerical check executed a different RTL source")
        _write(root / "functional-receipt.json", asdict(functional))
        checks = list(functional.checks)
        artifacts = [Artifact(str(item.resolve(functional.output_root).relative_to(root)), item.sha256)
                     for item in functional.output_artifacts]
        execution = functional.execution_status
        differential = None
        # A completed numerical mismatch is still useful evidence. Run the
        # independent unchanged-RTL comparison when the simulator executed.
        if execution == "success":
            differential = design_changes.run_design_checks(source, root / "differential", self.timeout)
            if (differential["mode"] != "fresh" or differential["source_sha256"] != source_sha
                    or differential["reference_sha256"] != task.specification["source_sha256"]
                    or differential["checker_sha256"] != task.specification["transformer_sha256"]):
                raise ContractError("Differential evidence belongs to another source, reference, or checker")
            mismatch = (differential["status"] == "check_failed"
                        and differential.get("simulation", {}).get("returncode") == 1
                        and differential.get("simulation", {}).get("timed_out") is False)
            status = "pass" if differential["ok"] else "fail" if mismatch else "not_run"
            checks.append(CheckResult("sequential_rtl_differential", status, BLOCK_SCOPE,
                                      "Fresh bounded valid-transaction simulation; not formal equivalence"))
            if not differential["ok"] and not mismatch:
                execution = {"unavailable": "not_run", "timeout": "timeout"}.get(differential["status"], "error")
            artifacts += [Artifact("differential/" + item["path"], item["sha256"])
                          for item in differential["output_artifacts"]]
            artifacts.append(Artifact.from_file(root, "differential/receipt.json"))
        _write(root / "execution-link.json", dict(
            task_digest=task.digest, candidate_digest=candidate.digest, source_sha256=source_sha,
            functional_source_sha256=file_sha256(Path(functional.output_root) / "candidate.v"),
            differential_source_sha256=differential["source_sha256"] if differential else None,
            physical_run=False, rtl_netlist_correspondence="unresolved"))
        artifacts += [Artifact.from_file(root, name) for name in
                      ("functional-receipt.json", "execution-link.json")]
        candidate.validate_files()
        return RunReceipt(task.task_id, candidate.digest, "fresh", execution,
                          "Nanochip finite block check composition", "1", checks=tuple(checks),
                          metrics=functional.metrics, cost=Cost(time.perf_counter() - started),
                          output_root=str(root), output_artifacts=tuple(artifacts),
                          details="Exact selected RTL; finite block evidence; no physical run or complete-core acceptance")


def _functional_design(checkpoint, output, *, transformer, timeout):
    """Freeze a loaded-model proposal and use the ordinary campaign engine."""
    output.mkdir(parents=True)
    shutil.copytree(checkpoint, output / "checkpoint")
    checkpoint_hashes = _checkpoint(output / "checkpoint")
    model_sources = {Path(module.__file__).name: Path(module.__file__).resolve()
                     for module in (model_io, sequence_model, model_proposer, design_learning)}
    model_sources["demo.py"] = Path(__file__).resolve()
    source_hashes = {name: file_sha256(path) for name, path in model_sources.items()}
    code = output / "code"
    code.mkdir()
    for name, path in model_sources.items():
        shutil.copyfile(path, code / name)
    _write(code / "manifest.json", source_hashes)
    extension = Path(inspect.getsourcefile(transformer)).resolve() if transformer else None
    task = design_changes.design_change_task()
    task = replace(task, max_attempts=1, max_proposals=1,
        required_checks=task.required_checks + (
            CheckRequirement("sequential_rtl_differential", BLOCK_SCOPE),
            *(CheckRequirement(name, BLOCK_SCOPE) for name in PHYSICAL_CHECKS),
            CheckRequirement("rtl_netlist_correspondence", BLOCK_SCOPE),
            CheckRequirement("workload_functional", CORE_SCOPE),
            CheckRequirement("checked_gds", CORE_SCOPE)),
        specification=dict(task.specification, checkpoint_artifacts=checkpoint_hashes,
                           model_sources=source_hashes,
                           check_timeout=timeout,
                           extension_sha256=file_sha256(extension) if extension else None))
    _write(output / "task.json", asdict(task))
    proposer = design_learning.design_proposer(output / "checkpoint")

    class RecordedProposer:
        def propose(self, task, history, budget):
            if _checkpoint(output / "checkpoint") != checkpoint_hashes:
                raise ContractError("Saved checkpoint changed before design inference")
            if any(file_sha256(path) != source_hashes[name] for name, path in model_sources.items()):
                raise ContractError("Model implementation or serializer changed before design inference")
            action = proposer.propose(task, history, budget)
            if proposer.predictions[-1]["checkpoint_sha256"] != checkpoint_hashes["checkpoint.pt"]:
                raise ContractError("Proposal was decoded by another checkpoint")
            _write(output / "proposal.json", dict(
                input_text=design_learning.design_input(task), predictions=proposer.predictions,
                action=asdict(action) if action else None, both_actions_available=True,
                checkpoint_sha256=checkpoint_hashes["checkpoint.pt"],
                note="Saved model selects supplied action; no fallback or action substitution"))
            return action

    campaign = run_campaign(task, RecordedProposer(),
        design_changes.DesignChangeMaterializer(transformer=transformer), FunctionalDesignBackend(timeout),
        output / "attempts", JsonlRecorder(output / "events.jsonl"))
    if _checkpoint(output / "checkpoint") != checkpoint_hashes:
        raise ContractError("Saved checkpoint changed during design execution")
    if any(file_sha256(path) != source_hashes[name] for name, path in model_sources.items()):
        raise ContractError("Model implementation or serializer changed during design execution")
    result = dict(schema_version=1, scope="one learned block-design proposal through fresh finite RTL checks",
                  campaign=asdict(campaign), predictions=proposer.predictions,
                  complete_design_eligible=any(o.eligible for o in campaign.observations))
    _write(output / "design-experiment.json", result)
    return result


def _checks(execution):
    return [check for observation in execution["campaign"]["observations"]
            for check in observation["checks"]]


def _completed(execution, physical):
    observations = execution["campaign"]["observations"]
    if len(observations) != 1 or observations[0]["status"] != "success":
        return False
    required = {("dequant_vectors", BLOCK_SCOPE), ("sequential_rtl_differential", BLOCK_SCOPE)}
    if physical:
        required.update((name, BLOCK_SCOPE) for name in PHYSICAL_CHECKS)
    returned = {(c["name"], c["scope"]): c["status"] for c in _checks(execution)}
    return all(returned.get(key) == "pass" for key in required)


def _diagnostic_completed(diagnosis):
    observations = diagnosis["campaign"]["observations"]
    return (len(observations) == 1 and observations[0]["status"] == "success"
            and any(c["name"] == "diagnostic_request" and c["scope"] == "diagnostic:msh_deq"
                    and c["status"] == "pass" for c in observations[0]["checks"]))


def _markdown(report):
    lines = ["# Nanochip v0 teaching run", "", f"Run status: **{report['status']}**.", "",
             "Target: Kimi nano-KPU dequantizer block (`msh_deq`), not complete-model accelerator inference.", "",
             f"Selected action: `{report['design']['selected_action']}`. The saved model selects an authored RTL action.", "",
             "| Check | Scope | Status |", "| --- | --- | --- |"]
    lines += [f"| {c['name']} | {c['scope']} | {c['status']} |" for c in report["checks"]]
    lines += ["", "## Learning effects", "",
              "The diagnostic model receives fresh fault evidence, a supervised development-data update, and held-out evaluation.",
              "The design model learns constructed action preferences. These observations establish no learning or physical benefit.", ""]
    effect = report["diagnostics"]["learning_effect"]
    lines += [f"- {key}: `{value}`" for key, value in effect.items() if key != "interpretation"]
    lines += ["", "## Retained artifacts", ""]
    lines += [f"- [{name}]({value['path']}) (`{value['sha256']}`)" for name, value in report["artifacts"].items()]
    lines += ["", "## Limits", ""] + [f"- {item}" for item in report["limits"]]
    return "\n".join(lines) + "\n"


def run_demo(output: Path | str, *, physical=False, transformer=None, check_timeout=30,
             physical_timeout=900, cores=1) -> dict:
    """Run the one default teaching path; optional physical work uses its RTL.

    Outputs must be new. Contract/programming failures write ``failure.json``
    and propagate; engineering failures retain reports with ``engineering_failed``.
    No tool installation, network model calls, or silent student fallback occurs.
    """
    if (type(physical) is not bool
            or any(type(t) not in (int, float) or not math.isfinite(t) or t <= 0
                   for t in (check_timeout, physical_timeout))
            or type(cores) is not int or not 1 <= cores <= 8):
        raise ContractError("Use a boolean physical flag, positive finite timeouts, and 1..8 CPU cores")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    stage = "collection"
    _write(output / "protocol.json", dict(PROTOCOL, physical=physical, check_timeout=check_timeout,
        physical_timeout=physical_timeout, cores=cores, action_selection="one saved-model inference; both actions available"))
    try:
        collect_corpus(output / "diagnostics/corpus", timeout_s=check_timeout)
        manifest = output / "diagnostics/corpus/manifest.json"
        stage = "diagnostic_learning"
        learning = _learn_diagnostics(manifest, output / "diagnostics/learning")
        stage = "diagnostic_inference"
        diagnosis = diagnose(manifest, learning["saved_model_inference_record_id"],
            output / "diagnostics/inference", checkpoint=output / "diagnostics/learning/adapted")
        stage = "design_learning"
        design_manifest = design_learning.collect_design_examples(output / "design/corpus")
        design_training = design_learning.train_design_proposer(design_manifest, output / "design/learning",
            seed=PROTOCOL["design_seed"], max_steps=PROTOCOL["design_steps"],
            max_seconds=PROTOCOL["training_seconds"])
        _require_updates(design_training["training"], PROTOCOL["design_steps"])
        checkpoint = output / "design/learning/checkpoint"
        stage = "design_execution"
        if physical:
            execution = run_design_experiment(checkpoint, output / "design/execution", transformer=transformer,
                check_timeout=check_timeout, physical_timeout=physical_timeout, cores=cores)
        else:
            execution = _functional_design(checkpoint, output / "design/execution",
                                           transformer=transformer, timeout=check_timeout)
        checks = _checks(execution)
        predictions = execution["predictions"]
        selected_action = predictions[-1]["action"] if predictions else None
        artifacts = {"protocol": _bound(output / "protocol.json"),
                     "reference_rtl": _bound(design_changes.REFERENCE_SOURCE),
                     "diagnostic_dataset": _bound(manifest),
                     "diagnostic_training": _bound(output / "diagnostics/learning/report.json"),
                     "base_checkpoint": _bound(output / "diagnostics/learning/base/checkpoint.pt"),
                     "adapted_checkpoint": _bound(output / "diagnostics/learning/adapted/checkpoint.pt"),
                     "saved_model_diagnosis": _bound(output / "diagnostics/inference/diagnosis.json"),
                     "design_dataset": _bound(output / "design/corpus/manifest.json"),
                     "design_training": _bound(output / "design/learning/report.json"),
                     "design_checkpoint": _bound(checkpoint / "checkpoint.pt"),
                     "design_execution": _bound(output / "design/execution/design-experiment.json")}
        for path in sorted((output / "design/execution/attempts").glob("attempt-*/candidate/msh_deq.v")):
            artifacts["selected_candidate_rtl"] = _bound(path)
            artifacts["selected_candidate_diff"] = _bound(path.with_name("change.diff"))
        for name, relative in (("selected_proposal", "proposal.json"), ("design_task", "task.json"),
            ("execution_identity", "attempts/attempt-0001/execution-link.json"),
            ("numerical_receipt", "attempts/attempt-0001/functional-receipt.json"),
            ("differential_receipt", "attempts/attempt-0001/differential/receipt.json"),
            ("physical_receipt", "attempts/attempt-0001/physical-receipt.json")):
            path = output / "design/execution" / relative
            if path.is_file():
                artifacts[name] = _bound(path)
        for index, path in enumerate(sorted((output / "design/execution").rglob("*.gds"))):
            artifacts[f"generated_gds_{index}"] = _bound(path)
        diagnostic_ok = _diagnostic_completed(diagnosis)
        success = _completed(execution, physical) and diagnostic_ok
        report = dict(schema_version=1, success=success, status="completed" if success
                      else "engineering_failed", physical_requested=physical,
            target=dict(name="Kimi nano-KPU", upstream="https://github.com/MoonshotAI/nano-kpu", scope=BLOCK_SCOPE),
            diagnostics=dict(learning_effect=learning["learning_effect"],
                             saved_model_inference_record_id=learning["saved_model_inference_record_id"],
                             predictions=diagnosis["predictions"]),
            design=dict(selected_action=selected_action, arbitrary_rtl_generation=False,
                        source_changed="selected_candidate_rtl" in artifacts and
                            artifacts["selected_candidate_rtl"]["sha256"] != artifacts["reference_rtl"]["sha256"],
                        complete_design_eligible=execution["complete_design_eligible"]),
            checks=checks, artifacts=artifacts, limits=LIMITS,
            total_wall_seconds=time.perf_counter() - started)
        _write(output / "report.json", report)
        (output / "report.md").write_text(_markdown(report), encoding="utf-8")
        return report
    except Exception as exc:
        _write(output / "failure.json", dict(status="failed", stage=stage,
            error_type=type(exc).__name__, error=str(exc), total_wall_seconds=time.perf_counter() - started))
        raise
