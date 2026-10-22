"""Compose the laboratory components without a second execution framework."""

from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
import shutil
import time

from .contracts import (
    Action,
    Artifact,
    Candidate,
    CheckRequirement,
    CheckResult,
    ContractError,
    Cost,
    RunReceipt,
    Task,
    file_sha256,
)
from .context import KeywordContext, specification_sources, with_context
from .datasets.dequant_corpus import (
    ACTIONS,
    load_corpus,
    serialize_observation,
    teaching_action,
)
from .evidence import JsonlRecorder
from .model_io import ModelIOContract
from .runner import run_campaign


def _write(path: Path, value) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def _contextualize(rows, mode: str):
    if mode not in ("none", "keyword"):
        raise ContractError("Unknown context provider")
    sources = specification_sources() if mode == "keyword" else ()
    retriever = KeywordContext()
    output = []
    for row in rows:
        context = (
            retriever.retrieve(row["input_text"], sources, max_words=48)
            if sources
            else ()
        )
        output.append(
            dict(
                row,
                input_text=with_context(row["input_text"], context),
                retrieved_sources=list(context),
            )
        )
    return tuple(output)


def diagnostic_model_io(context: str) -> ModelIOContract:
    """Retrieval changes the represented input and needs a compatible model."""
    if context not in ("none", "keyword"):
        raise ContractError("Unknown context provider")
    return ModelIOContract(
        "dequant_diagnostic_observation",
        1,
        f"nanochip.serialize_observation.context_{context}.v1",
        tuple(ACTIONS),
        2048,
    )


def learning_study(
    manifest: Path,
    output: Path,
    *,
    context: str = "none",
    train_seconds: float = 30,
    adapt_seconds: float = 15,
) -> dict:
    """A predeclared diagnostic study, with final test evaluated after updates.

    This proves training/checkpoint/inference composition. It does not measure
    architectural optimization or turn diagnostic requests into repairs.
    """
    from .models import load_model, train

    started = time.perf_counter()
    rows = _contextualize(load_corpus(manifest), context)
    input_contract = diagnostic_model_io(context)
    initial = [row for row in rows if row["split"] == "train"]
    development = [
        dict(row, original_split="dev", split="train")
        for row in rows
        if row["split"] == "dev"
    ]
    final_test = [row for row in rows if row["split"] == "test"]
    if not initial or not development or not final_test:
        raise ContractError(
            "Study needs distinct train, development, and final-test records"
        )
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    protocol = dict(
        schema_version=1,
        corpus_manifest=str(Path(manifest).resolve()),
        corpus_sha256=file_sha256(manifest),
        context=context,
        seed=0,
        initial_steps=300,
        adaptation_steps=150,
        train_seconds=train_seconds,
        adapt_seconds=adapt_seconds,
        actions=list(ACTIONS),
        model_io_contract=input_contract.to_dict(),
        initial_record_ids=[row["record_id"] for row in initial],
        adaptation_record_ids=[row["record_id"] for row in development],
        test_record_ids=[row["record_id"] for row in final_test],
        label_scope="imitation of disclosed diagnostic teaching policy",
    )
    _write(output / "protocol.json", protocol)
    _write(
        output / "adaptation-view.json",
        dict(
            origin="explicit new training view of development data; final test excluded",
            records=development,
        ),
    )
    before = train(
        initial,
        output / "base",
        seed=0,
        max_steps=300,
        max_seconds=train_seconds,
        action_vocabulary=ACTIONS,
        model_io_contract=input_contract,
    )
    after = train(
        development,
        output / "adapted",
        seed=0,
        max_steps=150,
        max_seconds=adapt_seconds,
        action_vocabulary=ACTIONS,
        base_checkpoint=output / "base",
    )
    # Both parameter-update phases finish before either checkpoint sees final test.
    base_model, adapted_model = load_model(output / "base"), load_model(
        output / "adapted"
    )
    base_evaluation = base_model.evaluate(final_test, model_io_contract=input_contract)
    adapted_evaluation = adapted_model.evaluate(
        final_test, model_io_contract=input_contract
    )
    counts = Counter(row["target_action"] for row in initial)
    majority = sorted(counts, key=lambda action: (-counts[action], action))[0]
    report = dict(
        schema_version=1,
        protocol=protocol,
        base_training=before,
        adapted_training=after,
        base_evaluation=base_evaluation,
        adapted_evaluation=adapted_evaluation,
        majority_baseline=dict(
            action=majority,
            accuracy=sum(row["target_action"] == majority for row in final_test)
            / len(final_test),
        ),
        teacher_policy=dict(
            label_agreement=1.0,
            interpretation="Labels are defined by this rule; agreement is not an independent quality metric",
        ),
        total_wall_seconds=time.perf_counter() - started,
        limits=[
            "One small constructed corpus and one seed; no statistical superiority claim",
            "Held-out mutation templates share one design and vector suite",
            "No accepted/pass cases in final test",
            "Actual recurrent action-decoder training, not general language-model pretraining",
            "No RTL repair, architecture performance improvement, or GDS claim from this study",
        ],
    )
    _write(output / "study.json", report)
    return report


class _DiagnosticMaterializer:
    def __init__(self, corpus_root: Path, row: dict):
        self.corpus_root, self.row = corpus_root, row

    def materialize(self, task, action, workspace):
        if action.parameters or action.name not in ACTIONS:
            raise ContractError("Diagnostic actions accept no hidden repair parameters")
        source_receipt = Artifact(**self.row["source_receipt"])
        source_receipt.validate(self.corpus_root)
        for artifact in self.row.get("evidence_artifacts", []):
            Artifact(**artifact).validate(self.corpus_root)
        source_root = source_receipt.resolve(self.corpus_root).parent
        root = workspace / "candidate"
        root.mkdir()
        for name in ("candidate.v", "receipt.json", "build.log", "simulation.log"):
            if (source_root / name).exists():
                shutil.copyfile(source_root / name, root / name)
        if file_sha256(root / "candidate.v") != self.row["source_sha256"]:
            raise ContractError(
                "Diagnostic snapshot no longer matches the source record"
            )
        (root / "observation.json").write_text(self.row["input_text"], encoding="utf-8")
        (root / "request.json").write_text(json.dumps(asdict(action)), encoding="utf-8")
        return Candidate(
            self.row["record_id"],
            task.task_id,
            str(root),
            action,
            tuple(
                Artifact.from_file(root, path.name) for path in sorted(root.iterdir())
            ),
            task_digest=task.digest,
        )


class DiagnosticBackend:
    """Execute exactly the decoded inspection; never silently apply a repair.

    The tool reads previously measured artifacts. Fresh execution refers to
    this inspection only, not to a new RTL simulation or physical run.
    """

    def evaluate(self, task, candidate):
        started = time.perf_counter()
        candidate.validate_files()
        if candidate.task_id != task.task_id or candidate.task_digest != task.digest:
            raise ContractError("Diagnostic candidate belongs to another task")
        root = Path(candidate.root)
        observed_text = (root / "observation.json").read_text()
        receipt = json.loads((root / "receipt.json").read_text())
        logs = {
            name: (root / name).read_text() if (root / name).exists() else ""
            for name in ("simulation.log", "build.log")
        }
        if (
            observed_text
            != serialize_observation(receipt, logs["simulation.log"], logs["build.log"])
            or file_sha256(root / "candidate.v") != receipt["candidate_sha256"]
        ):
            raise ContractError(
                "Diagnostic input does not match the retained RTL evidence"
            )
        observation = json.loads(observed_text)
        checks = observation["checks"]
        action = candidate.action.name
        if action == "inspect_numerics":
            selected = dict(
                mismatches=checks["mismatches"],
                lanes_checked=checks["lanes_checked"],
                first_mismatches=observation["first_mismatches"],
            )
        elif action == "inspect_protocol":
            selected = {
                key: checks[key]
                for key in (
                    "protocol_error",
                    "rows_completed",
                    "cycles",
                    "stream_stall_cycles",
                )
            }
        elif action == "inspect_build":
            selected = {
                key: observation[key]
                for key in (
                    "status",
                    "build_returncode",
                    "compiler_diagnostics",
                    "timed_out",
                )
            }
        elif action == "accept_block":
            selected = dict(
                finite_block_probe_passed=observation["status"] == "passed"
                and receipt.get("ok") is True,
                complete_design_accepted=False,
            )
        else:
            raise ContractError("Unknown diagnostic action")
        allowed_acceptance = (
            action != "accept_block" or selected["finite_block_probe_passed"]
        )
        result = dict(
            action=action,
            selected_evidence=selected,
            candidate_digest=candidate.digest,
            source_receipt_sha256=file_sha256(root / "receipt.json"),
            execution="fresh diagnostic inspection of retained RTL evidence",
            rtl_modified=False,
            rtl_simulation_rerun=False,
            physical_flow_run=False,
        )
        output = root.parent / "diagnostic"
        output.mkdir()
        _write(output / "diagnostic.json", result)
        candidate.validate_files()
        return RunReceipt(
            task.task_id,
            candidate.digest,
            "fresh",
            "success",
            "Nanochip diagnostic reader",
            "1",
            checks=(
                CheckResult(
                    "diagnostic_request",
                    "pass" if allowed_acceptance else "fail",
                    "diagnostic:msh_deq",
                    "The selected inspection executed; this is not a repair",
                ),
            ),
            cost=Cost(time.perf_counter() - started),
            output_root=str(output),
            output_artifacts=(Artifact.from_file(output, "diagnostic.json"),),
            details="Prior RTL evidence was inspected. No fresh simulation or physical implementation.",
        )


def diagnose(
    manifest: Path,
    record_id: str,
    output: Path,
    *,
    checkpoint: Path | None = None,
    context: str = "none",
) -> dict:
    rows = load_corpus(manifest)
    row = next((row for row in rows if row["record_id"] == record_id), None)
    if row is None:
        raise ContractError("Record identity is absent from the validated corpus")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    contextual = _contextualize([row], context)[0]
    task = Task(
        "nanochip-diagnostic-v1",
        ACTIONS,
        (
            CheckRequirement("diagnostic_request", "diagnostic:msh_deq"),
            CheckRequirement("workload_functional", "accelerator:msh_chip_top"),
            CheckRequirement("checked_gds", "accelerator:msh_chip_top"),
        ),
        max_attempts=1,
        max_proposals=1,
        specification=dict(
            source_sha256=row["source_sha256"],
            source_receipt=row["source_receipt"],
            observation_text=contextual["input_text"],
            retrieved_sources=contextual["retrieved_sources"],
        ),
    )
    if checkpoint is not None:
        from .models import LearnedProposer, load_model

        recorded = load_model(checkpoint).model_io_contract
        proposer = LearnedProposer(
            checkpoint,
            lambda task, history: task.specification["observation_text"],
            model_io_contract=diagnostic_model_io(context)
            if recorded is not None
            else None,
        )
    else:

        class RuleProposer:
            def propose(self, task, history, budget):
                receipt = Artifact(**row["source_receipt"]).resolve(
                    Path(manifest).parent
                )
                return Action(teaching_action(json.loads(receipt.read_text())))

        proposer = RuleProposer()
    campaign = run_campaign(
        task,
        proposer,
        _DiagnosticMaterializer(Path(manifest).parent, row),
        DiagnosticBackend(),
        output / "attempts",
        JsonlRecorder(output / "events.jsonl"),
    )
    result = dict(
        schema_version=1,
        policy="learned" if checkpoint is not None else "rule",
        context=context,
        retrieved_sources=contextual["retrieved_sources"],
        predictions=getattr(proposer, "predictions", []),
        campaign=asdict(campaign),
        scope="diagnostic action execution on retained evidence; no repair or GDS claim",
    )
    _write(output / "diagnosis.json", result)
    return result
