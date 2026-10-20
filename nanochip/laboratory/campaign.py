"""A measured design-learning campaign over explicit, replaceable components.

The existing runner owns proposal, candidate identity, execution, and assessment.
This module owns partitioning, measured-feedback admission, checkpoint lineage,
and a frozen comparison. Target-specific RTL and tool flows belong to adapters.
"""

from copy import deepcopy
from dataclasses import asdict, dataclass, replace
import hashlib
import inspect
import json
import math
from pathlib import Path
import shutil
import time
from typing import Any, Callable, Mapping, Protocol, Sequence

from .contracts import Action, Artifact, Candidate, ContractError, Observation, Task, canonical_json, file_sha256
from .evidence import JsonlRecorder
from .datasets.characterize import assess_input_support, fit_training_support, profile_records
from .interfaces import Backend, Materializer, Proposer
from .runner import run_campaign as execute_campaign


@dataclass(frozen=True)
class CampaignCase:
    case_id: str
    group_id: str
    split: str
    task: Task
    objective: "CampaignObjective | None" = None


@dataclass(frozen=True)
class CampaignObjective:
    metric: str
    scope: str
    minimize: bool = True
    unit: str | None = None

    def __post_init__(self):
        if not isinstance(self.unit, str) or not self.unit.strip():
            raise ContractError("Campaign objective requires an explicit measurement unit")


@dataclass(frozen=True)
class CampaignTarget:
    materializer: Materializer
    backend: Backend
    serialize: Callable[[Task, tuple[Observation, ...], Sequence[Mapping]], str]
    features: Callable[[Task], Mapping] | None = None
    numeric_features: tuple[str, ...] = ()
    categorical_features: tuple[str, ...] = ()


class CampaignMethod(Protocol):
    """Updates write a new checkpoint directory and return JSON metadata.

    Adaptation metadata must identify the preceding ``checkpoint.pt`` hash.
    The implementation may compose multiple phases, but must preserve that
    end-to-end lineage and retain the constituent phase receipts.
    """

    name: str

    def train(self, records: Sequence[Mapping], output: Path) -> Mapping: ...

    def adapt(self, records: Sequence[Mapping], base_checkpoint: Path, output: Path) -> Mapping: ...

    def proposer(self, checkpoint: Path, format_input: Callable) -> Proposer: ...


def _write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def _digest(value):
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _file(path: Path):
    return dict(path=str(path.resolve()), sha256=file_sha256(path))


def _checkpoint(root: Path):
    if not (root / "checkpoint.pt").is_file():
        raise ContractError("Method did not produce checkpoint.pt in its declared output")
    return {str(path.relative_to(root)): file_sha256(path)
            for path in sorted(root.rglob("*")) if path.is_file()}


def _unchanged(root, hashes):
    if _checkpoint(root) != hashes:
        raise ContractError("Frozen model checkpoint changed")


def _implementation_sources(method, target, retriever):
    values = [method, target.materializer, target.backend, target.serialize]
    if retriever is not None:
        values.append(retriever)
    paths = {Path(__file__).resolve()}
    paths.add(Path(inspect.getsourcefile(execute_campaign)).resolve())
    paths.add(Path(inspect.getsourcefile(profile_records)).resolve())
    if target.features is not None:
        values.append(target.features)
    for value in values:
        item = value if inspect.isfunction(value) or inspect.ismethod(value) else type(value)
        try:
            path = inspect.getsourcefile(item)
        except TypeError:
            path = None
        if path:
            paths.add(Path(path).resolve())
        if hasattr(value, "implementation_sources"):
            paths.update(Path(path).resolve() for path in value.implementation_sources())
    return {str(path): file_sha256(path) for path in sorted(paths)}


def _sources_unchanged(sources):
    if any(file_sha256(path) != digest for path, digest in sources.items()):
        raise ContractError("Campaign component implementation changed after protocol freeze")


def _snapshot_records(records, source_root, output):
    result, identities = [], set()
    for index, source in enumerate(records):
        row = deepcopy(dict(source))
        if (not row.get("record_id") or row["record_id"] in identities
                or not row.get("group_id") or row.get("split") != "train"
                or row.get("original_split", "train") == "test"):
            raise ContractError("Initial corpus needs unique, explicitly training-only records")
        identities.add(row["record_id"])
        artifact = Artifact(**row["source_receipt"])
        root = Path(row.get("source_root", source_root)).resolve()
        artifact.validate(root)
        relative = f"corpus/sources/{index:05d}-{Path(artifact.path).name}"
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact.resolve(root), destination)
        row["original_source_receipt"] = dict(root=str(root), **asdict(artifact))
        row["source_receipt"] = asdict(Artifact.from_file(output, relative))
        row["source_root"] = str(output)
        result.append(row)
    if not result:
        raise ContractError("Campaign requires an explicit initial training corpus")
    _write(output / "corpus/records.json", result)
    _write(output / "corpus/manifest.json", dict(schema_version=1,
        records=_file(output / "corpus/records.json"), count=len(result),
        role="initial training only; no final-test inputs or measurements"))
    return tuple(result)


def _validate_cases(cases, records, objective, candidate_budget):
    if type(candidate_budget) is not int or candidate_budget < 2:
        raise ContractError("Use at least two candidate slots per method and case")
    if not objective.metric or not objective.scope or type(objective.minimize) is not bool:
        raise ContractError("Objective needs a scoped metric and explicit direction")
    ids, groups, splits = set(), {}, set()
    actions = None
    for case in cases:
        if (not case.case_id or Path(case.case_id).name != case.case_id or case.case_id in (".", "..")
                or not case.group_id or case.case_id in ids
                or case.split not in ("dev", "test")):
            raise ContractError("Cases need unique identities and explicit dev/test partitions")
        ids.add(case.case_id)
        splits.add(case.split)
        selected_objective = case.objective or objective
        if (not selected_objective.metric or not selected_objective.scope
                or type(selected_objective.minimize) is not bool
                or selected_objective.unit is not None and not selected_objective.unit):
            raise ContractError("Case objective needs a scoped metric, direction, and optional unit")
        if case.group_id in groups and groups[case.group_id] != case.split:
            raise ContractError("Related case groups cross development and final test")
        groups[case.group_id] = case.split
        vocabulary = set(case.task.allowed_actions)
        if actions is not None and actions != vocabulary:
            raise ContractError("Campaign cases must share the declared action vocabulary")
        actions = vocabulary
    if splits != {"dev", "test"}:
        raise ContractError("Campaign needs both development and final-test cases")
    test_groups = {case.group_id for case in cases if case.split == "test"}
    test_ids = {case.case_id for case in cases if case.split == "test"}
    if any(row["group_id"] in test_groups or row.get("case_id") in test_ids for row in records):
        raise ContractError("Initial training data overlaps a final-test case/group")


def _knowledge_sources(records):
    return tuple(dict(source_id=row["record_id"], partition="train", kind="training_corpus",
        text=row["input_text"], text_sha256=_digest_text(row["input_text"]),
        source=str(Path(row["source_root"]) / row["source_receipt"]["path"]),
        file_sha256=row["source_receipt"]["sha256"]) for row in records)


def _digest_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _context(retriever, task, history, sources, words):
    if retriever is None:
        return ()
    permitted = {source["source_id"]: source for source in sources}
    returned = tuple(retriever.build(deepcopy(task), deepcopy(history), deepcopy(sources), words))
    # A replacement retriever can return excerpts, never a new/test source.
    for item in returned:
        source = permitted.get(item.get("source_id"))
        if (source is None or item.get("partition") != source["partition"]
                or item.get("text_sha256") != _digest_text(item.get("text", ""))
                or item.get("source") != source["source"]
                or item.get("file_sha256") != source["file_sha256"]
                or " ".join(item["text"].split()) not in " ".join(source["text"].split())):
            raise ContractError("Retriever returned undeclared, changed, or final-test evidence")
    if sum(len(item["text"].split()) for item in returned) > words:
        raise ContractError("Retriever exceeded its declared context word budget")
    return returned


class _Enumeration:
    """A declared conventional baseline with no learned or reference fallback."""

    def __init__(self, actions, index):
        self.actions, self.index = actions, index

    def propose(self, task, history, budget):
        return Action(self.actions[self.index % len(self.actions)])


def _attempt(case, arm, index, output, *, target, method, checkpoint, history,
             sources, retriever, context_words, protocol_hash, constant_action=None,
             forbidden_inputs=(), test_inputs=(), input_support=None):
    started = time.perf_counter()
    slot = output / case.split / case.case_id / arm / f"slot-{index:03d}"
    slot.mkdir(parents=True)
    hashes = _checkpoint(checkpoint) if checkpoint else None
    task = replace(case.task, max_proposals=1, max_attempts=1,
        specification=dict(case.task.specification, campaign_run=dict(
            case_id=case.case_id, group_id=case.group_id, split=case.split, arm=arm, slot=index,
            protocol_sha256=protocol_hash, checkpoint=hashes)))
    context = _context(retriever, task, tuple(history), sources, context_words)
    captured, assessments = [], []
    phase_cost = dict(proposal_wall_seconds=0.0, materialization_wall_seconds=0.0, backend_wall_seconds=0.0)

    def represent(task, inner_history):
        text = target.serialize(task, tuple(inner_history), context)
        if not isinstance(text, str) or not text:
            raise ContractError("Representation must return nonempty text")
        if (case.split == "test" and text in forbidden_inputs
                or case.split == "dev" and text in test_inputs):
            raise ContractError("Contextual represented input crosses training/development and final test")
        captured.append(text)
        if input_support is not None:
            features = target.features(deepcopy(task)) if target.features else {}
            assessments.append(dict(byte_support=assess_input_support(text, {}, input_support["byte_support"]),
                feature_support=assess_input_support(text, features, input_support["feature_support"])
                    if input_support["feature_support"] else None))
        return text

    proposer = (method.proposer(checkpoint, represent) if checkpoint else
                _Enumeration((constant_action,), 0) if arm == "constant" else _Enumeration(task.allowed_actions, index))

    class Recorded:
        def propose(self, task, inner_history, budget):
            if checkpoint:
                _unchanged(checkpoint, hashes)
            proposed = time.perf_counter()
            try:
                action = proposer.propose(task, deepcopy(tuple(history)) + inner_history, budget)
            finally:
                phase_cost["proposal_wall_seconds"] += time.perf_counter() - proposed
            if checkpoint:
                _unchanged(checkpoint, hashes)
            _write(slot / "proposal.json", dict(
                action=asdict(action) if action is not None else None, checkpoint=hashes,
                represented_inputs=captured, retrieved_sources=context,
                observed_input_support=assessments,
                predictions=getattr(proposer, "predictions", [])))
            return action

    class TimedMaterializer:
        def materialize(self, task, action, workspace):
            phase_started = time.perf_counter()
            try:
                return target.materializer.materialize(task, action, workspace)
            finally:
                phase_cost["materialization_wall_seconds"] += time.perf_counter() - phase_started

    class TimedBackend:
        def evaluate(self, task, candidate):
            phase_started = time.perf_counter()
            try:
                return target.backend.evaluate(task, candidate)
            finally:
                phase_cost["backend_wall_seconds"] += time.perf_counter() - phase_started

    result = execute_campaign(task, Recorded(), TimedMaterializer(), TimedBackend(),
                              slot / "attempts", JsonlRecorder(slot / "events.jsonl"))
    if checkpoint:
        _unchanged(checkpoint, hashes)
    summary = dict(case_id=case.case_id, case_group=case.group_id, split=case.split,
        arm=arm, slot=index, base_task_sha256=case.task.digest, task=asdict(task),
        checkpoint=hashes, campaign=asdict(result))
    summary["represented_inputs"] = captured
    summary["observed_input_support"] = assessments
    summary["cost"] = dict(phase_cost, attempt_wall_seconds=time.perf_counter() - started)
    summary["cost"]["loading_context_serialization_and_assessment_wall_seconds"] = (
        summary["cost"]["attempt_wall_seconds"] - sum(phase_cost.values()))
    _write(slot / "result.json", summary)
    return result.observations, summary, slot


def _value(observation, objective):
    if not observation.eligible or not observation.receipt:
        return None
    metric = observation.receipt.metrics.get(objective.metric)
    if (metric is None or metric.scope != objective.scope
            or objective.unit is not None and metric.unit != objective.unit):
        return None
    for artifact in observation.receipt.output_artifacts:
        artifact.validate(observation.receipt.output_root or "")
    return metric.value


def curate_feedback(case, observations, *, objective, input_text, output, campaign_root, features=None):
    """Retain all evidence; admit action labels only from measured feasibility.

    A preference label requires distinct feasible measured actions under this
    same case specification and a strict objective winner. A lone feasible
    action gets a feasibility label, never an optimality label. Ties abstain
    from preference; no missing check/metric turns into a positive example.
    """
    if case.split != "dev":
        raise ContractError("Final-test inputs or measurements cannot become training/RAG data")
    observations = tuple(observations)
    if any(item.receipt and (item.receipt.task_id != case.task.task_id or item.receipt.mode != "fresh"
                            or item.receipt.candidate_digest != item.candidate_digest)
           for item in observations):
        raise ContractError("Feedback contains another task's receipt or nonfresh measurements")
    payload = dict(schema_version=1, case_id=case.case_id, group_id=case.group_id,
        split="dev", task_sha256=case.task.digest, task=asdict(case.task),
        objective=asdict(objective), observations=[asdict(item) for item in observations])
    _write(output, payload)
    receipt = asdict(Artifact.from_file(campaign_root, str(output.relative_to(campaign_root))))
    common = dict(group_id=case.group_id, split="train", original_split="dev", case_id=case.case_id,
        source_root=str(campaign_root), source_sha256=receipt["sha256"], source_receipt=receipt,
        data_origin="measured", evidence_mode="fresh", label_origin="measured_campaign_prefix_v1")
    if features is not None:
        common["features"] = dict(features)
    # Language modeling of measured failures is distinct from an action label.
    records = [dict(common, record_id=f"{case.case_id}-{output.stem}-evidence", label_kind="measurement_text",
        input_text=input_text + "\nMEASURED TOOL EVIDENCE\n" + canonical_json(payload))]
    feasible = {}
    for item in observations:
        value = _value(item, objective)
        required = {(check.name, check.scope) for check in case.task.required_checks}
        passed = {(check.name, check.scope) for check in item.checks if check.status == "pass"}
        if (value is not None and item.action and item.status == "success"
                and item.receipt.execution_status == "success" and required <= passed):
            feasible.setdefault(item.action.name, []).append(value)
    kind, selected = None, None
    if len(feasible) == 1:
        kind, selected = "feasibility", next(iter(feasible))
    elif len(feasible) > 1:
        means = {action: sum(values) / len(values) for action, values in feasible.items()}
        ordered = sorted(feasible, key=lambda action: (means[action], action), reverse=not objective.minimize)
        if (max(feasible[ordered[0]]) < min(value for action in ordered[1:] for value in feasible[action])
                if objective.minimize else
                min(feasible[ordered[0]]) > max(value for action in ordered[1:] for value in feasible[action])):
            kind, selected = "preference", ordered[0]
    if selected:
        records.append(dict(common, record_id=f"{case.case_id}-{output.stem}-{kind}",
            label_kind=kind, input_text=input_text, target_action=selected,
            measured_objective=sum(feasible[selected]) / len(feasible[selected]), measured_actions=sorted(feasible),
            objective=asdict(objective), observed_values=feasible,
            interpretation="best strictly measured feasible prefix action" if kind == "preference"
                else "one observed feasible action; no optimality preference"))
    return tuple(records), dict(label_kind=kind, selected_action=selected,
        feasible_measured_actions=len(feasible), source_receipt=receipt,
        failure_records=sum(not item.eligible for item in observations))


def _validate_update(metadata, output, base_checkpoint=None):
    hashes = _checkpoint(output)
    if metadata.get("parameters_changed") is not True:
        raise ContractError("Method reports no actual parameter update")
    if base_checkpoint is not None:
        if metadata.get("base_checkpoint_sha256") != file_sha256(base_checkpoint / "checkpoint.pt"):
            raise ContractError("Adaptation did not continue from the preceding design checkpoint")
    return hashes


def _best(summaries, objective):
    measured = []
    for summary in summaries:
        for item in summary["campaign"]["observations"]:
            receipt = item.get("receipt")
            metric = receipt.get("metrics", {}).get(objective.metric) if receipt else None
            if (item["eligible"] and metric and metric["scope"] == objective.scope
                    and (objective.unit is None or metric["unit"] == objective.unit)):
                measured.append(dict(action=item["action"]["name"], value=metric["value"],
                                     unit=metric["unit"], scope=metric["scope"],
                                     candidate_digest=item["candidate_digest"]))
    if not measured:
        return None
    return sorted(measured, key=lambda item: (item["value"], item["action"]),
                  reverse=not objective.minimize)[0]


def _training_diagnostics(checkpoint, admitted, target):
    path = checkpoint / "training.json"
    metadata = json.loads(path.read_text()) if path.is_file() else {}
    rows = metadata.get("training_records", admitted)
    featured = [row for row in rows if "features" in row]
    return dict(profile=profile_records(rows), byte_support=fit_training_support(rows),
        feature_support=fit_training_support(featured, numeric_features=target.numeric_features,
            categorical_features=target.categorical_features) if featured and target.features else None,
        provenance="actual checkpoint training_records when supplied, otherwise admitted training rows"), rows


def _markdown(report):
    lines = ["# Nanochip measured learning campaign", "", f"Experiment execution: **{report['status']}**.", "",
        "Execution and design acceptance are separate. Each best result below passed its task's declared checks.", "",
        "| Held-out case | Objective | Method | Best action | Measured value |",
        "| --- | --- | --- | --- | --- |"]
    for case in report["comparison"]:
        for arm, outcome in case["arms"].items():
            best = outcome["best"]
            lines.append(f"| {case['case_id']} | {case['objective']['metric']} | {arm} | "
                + (f"{best['action']} | {best['value']} {best['unit']} |" if best else "unresolved | no feasible measured candidate |"))
    cost = report["cost"]
    lines += ["", "Training uses repository text followed by measured development feedback. Final-test inputs and measurements do not update weights or enter the retrieval corpus.", "",
        f"Total wall: {cost['total_wall_seconds']:.3f} s; input preparation: {cost['input_preparation_wall_seconds']:.3f} s; cold start before final test: {cost['cold_start_wall_seconds']:.3f} s.", "",
        "| Method | Held-out attempt wall (s) | Receipt tool time (s) |", "| --- | ---: | ---: |"]
    for arm, seconds in cost["final_test_attempt_wall_seconds"].items():
        lines.append(f"| {arm} | {seconds:.3f} | {cost['final_test_tool_seconds'][arm]:.3f} |")
    lines += ["", "Attempt wall includes model loading, proposal, representation, materialization, tools, and assessment. Receipt tool time is a narrower measurement. These values establish no total-cost advantage.", "",
        "Retained evidence: [protocol](protocol.json), [frozen evaluation](frozen-evaluation.json), [complete report](report.json), [training distributions](characterization/final-training.json).", "",
        "Measured ties and absent improvements remain valid outcomes; no learned-superiority claim is made.", ""]
    lines += [f"- {limit}" for limit in report["limits"]]
    return "\n".join(lines) + "\n"


def run_learning_campaign(output: Path | str, *, cases: Sequence[CampaignCase],
        training_records: Sequence[Mapping], training_root: Path | str,
        method: CampaignMethod, target: CampaignTarget, objective: CampaignObjective,
        candidate_budget: int = 2, retriever=None, context_words: int = 80,
        constant_action: str | None = None, input_preparation_wall_seconds: float = 0.0) -> dict:
    """Train, measure development proposals, adapt, then compare frozen methods.

    Every development round measures one learned and one enumeration candidate
    before curation. This shared acquisition cost is retained separately from
    matched held-out candidate budgets. All final-test methods start only after
    every parameter update, with the same permitted development knowledge.
    """
    cases = tuple(replace(case, objective=case.objective or objective,
        task=replace(case.task, specification=dict(deepcopy(case.task.specification),
            campaign_objective=asdict(case.objective or objective)))) for case in cases)
    training_records = tuple(training_records)
    _validate_cases(cases, training_records, objective, candidate_budget)
    constant_action = constant_action or cases[0].task.allowed_actions[-1]
    if constant_action not in cases[0].task.allowed_actions:
        raise ContractError("Constant baseline action must belong to the declared vocabulary")
    represented_cases = [(case, target.serialize(case.task, (), ())) for case in cases]
    if any(not isinstance(text, str) or not text for _, text in represented_cases):
        raise ContractError("Case representation must return nonempty text")
    test_inputs = {text for case, text in represented_cases if case.split == "test"}
    if any(text in test_inputs for case, text in represented_cases if case.split == "dev"):
        raise ContractError("Exact represented input crosses development and final-test partitions")
    if any(row["input_text"] in test_inputs for row in training_records):
        raise ContractError("Exact final-test represented input appears in initial training data")
    if type(context_words) is not int or context_words < 0:
        raise ContractError("Context word budget must be a nonnegative integer")
    if (type(input_preparation_wall_seconds) not in (int, float)
            or not math.isfinite(input_preparation_wall_seconds) or input_preparation_wall_seconds < 0):
        raise ContractError("Input preparation cost must be finite and nonnegative")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    started, stage = time.perf_counter(), "snapshot"
    try:
        records = _snapshot_records(training_records, training_root, output)
        implementations = _implementation_sources(method, target, retriever)
        for index, source in enumerate(implementations):
            destination = output / "code" / f"{index:03d}-{Path(source).name}"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        protocol = dict(schema_version=1, method=method.name,
            cases=[dict(case_id=c.case_id, group_id=c.group_id, split=c.split, task=asdict(c.task),
                        objective=asdict(c.objective or objective)) for c in cases],
            objective=asdict(objective), candidate_slots_per_method_case=candidate_budget,
            initial_corpus=_file(output / "corpus/records.json"), implementations=implementations,
            context_words=context_words, retrieval_enabled=retriever is not None,
            evaluation_arms=["adapted", "unadapted", "enumeration", "constant"],
            constant_action=constant_action, constant_policy="fixed before training and tool measurements",
            input_preparation_wall_seconds=input_preparation_wall_seconds,
            feedback="development learned+enumeration measured prefix; feasibility distinct from preference",
            final_test="no updates, no test inputs/outcomes in retrieval corpus; all checkpoints frozen first")
        _write(output / "protocol.json", protocol)
        protocol_hash = file_sha256(output / "protocol.json")
        _write(output / "protocol-sha256.json", dict(sha256=protocol_hash))
        knowledge = list(_knowledge_sources(records))

        def frozen():
            _sources_unchanged(implementations)
            if file_sha256(output / "protocol.json") != protocol_hash:
                raise ContractError("Frozen campaign protocol changed")
            if file_sha256(output / "corpus/records.json") != protocol["initial_corpus"]["sha256"]:
                raise ContractError("Frozen initial corpus changed")
            for row in records:
                Artifact(**row["source_receipt"]).validate(output)
            if any(case.task.digest != _digest(entry["task"]) for case, entry in zip(cases, protocol["cases"])):
                raise ContractError("Frozen campaign case specification changed")
            for source in knowledge:
                if file_sha256(source["source"]) != source["file_sha256"]:
                    raise ContractError("Permitted retrieval/training evidence changed")

        stage = "initial_training"
        base = output / "models/base"
        frozen()
        train_started = time.perf_counter()
        training = dict(method.train(deepcopy(records), base))
        training_wall = time.perf_counter() - train_started
        base_hashes = _validate_update(training, base)
        _write(output / "training.json", training)
        base_support, trained_rows = _training_diagnostics(base, records, target)
        _write(output / "characterization/initial-training.json", base_support)
        support = base_support
        forbidden_inputs = {row["input_text"] for row in trained_rows}
        current, updates, development = base, [], []
        all_feedback = []
        stage = "development"
        for case in (case for case in cases if case.split == "dev"):
            case_objective = case.objective or objective
            histories = {"learned": [], "enumeration": []}
            for index in range(candidate_budget):
                frozen()
                for arm in histories:
                    observations, summary, _ = _attempt(case, arm, index, output, target=target, method=method,
                        checkpoint=current if arm == "learned" else None, history=histories[arm],
                        sources=tuple(knowledge), retriever=retriever, context_words=context_words,
                        protocol_hash=protocol_hash, test_inputs=test_inputs, input_support=support)
                    histories[arm].extend(observations)
                    development.append(summary)
                    forbidden_inputs.update(summary["represented_inputs"])
                # The label prompt is the declared case representation without
                # held-out data; raw measurements remain separately sourced.
                feedback, curation = curate_feedback(case, histories["learned"] + histories["enumeration"],
                    objective=case_objective, input_text=target.serialize(case.task, (), ()),
                    output=output / "feedback" / case.case_id / f"round-{index:03d}.json", campaign_root=output,
                    features=target.features(deepcopy(case.task)) if target.features else None)
                all_feedback.extend(feedback)
                update_records = tuple(records) + tuple(all_feedback)
                if any(row["input_text"] in test_inputs for row in update_records):
                    raise ContractError("A designated development training input equals a final-test prompt")
                _write(output / "feedback" / case.case_id / f"round-{index:03d}-records.json", update_records)
                frozen()
                previous, previous_hashes = current, _checkpoint(current)
                current = output / "models" / f"update-{len(updates):03d}"
                update_started = time.perf_counter()
                metadata = dict(method.adapt(deepcopy(update_records), previous, current))
                update_wall = time.perf_counter() - update_started
                _validate_update(metadata, current, previous)
                _unchanged(previous, previous_hashes)
                _unchanged(base, base_hashes)
                support, trained_rows = _training_diagnostics(current, update_records, target)
                forbidden_inputs.update(row["input_text"] for row in trained_rows)
                _write(output / "characterization" / f"update-{len(updates):03d}.json", support)
                updates.append(dict(checkpoint=str(current), metadata=metadata, wall_seconds=update_wall,
                    curation=curation, update_record_ids=[row["record_id"] for row in update_records]))
                _write(output / "models" / f"update-{len(updates)-1:03d}-receipt.json", updates[-1])
                for row in feedback:
                    knowledge.append(dict(source_id=row["record_id"], partition="dev", kind=row["label_kind"],
                        text=row["input_text"], text_sha256=_digest_text(row["input_text"]),
                        source=str(output / row["source_receipt"]["path"]), file_sha256=row["source_receipt"]["sha256"]))
        frozen()
        final_hashes = _checkpoint(current)
        _write(output / "characterization/final-training.json", support)
        _write(output / "frozen-evaluation.json", dict(protocol_sha256=protocol_hash,
            base_checkpoint=str(base), base_hashes=base_hashes, adapted_checkpoint=str(current),
            adapted_hashes=final_hashes, development_knowledge_sha256=_digest(knowledge),
            updates_completed=len(updates)))
        cold_start_wall = time.perf_counter() - started + input_preparation_wall_seconds
        stage = "final_test"
        final, comparison = [], []
        for case in (case for case in cases if case.split == "test"):
            case_objective = case.objective or objective
            case_summaries = {}
            for arm, checkpoint in (("adapted", current), ("unadapted", base), ("enumeration", None), ("constant", None)):
                history, summaries = [], []
                for index in range(candidate_budget):
                    frozen()
                    _unchanged(base, base_hashes)
                    _unchanged(current, final_hashes)
                    observations, summary, _ = _attempt(case, arm, index, output, target=target, method=method,
                        checkpoint=checkpoint, history=history, sources=tuple(knowledge), retriever=retriever,
                        context_words=context_words, protocol_hash=protocol_hash, constant_action=constant_action,
                        forbidden_inputs=forbidden_inputs,
                        input_support=base_support if arm == "unadapted" else support)
                    history.extend(observations)
                    summaries.append(summary)
                    final.append(summary)
                best = _best(summaries, case_objective)
                case_summaries[arm] = dict(best=best,
                    outcome="feasible_measured" if best else "no_feasible_measured_candidate",
                    candidate_slots=candidate_budget,
                    attempts_used=sum(s["campaign"]["attempts_used"] for s in summaries),
                    proposals_used=sum(s["campaign"]["proposals_used"] for s in summaries))
            comparison.append(dict(case_id=case.case_id, group_id=case.group_id,
                                   objective=asdict(case_objective), arms=case_summaries))
        frozen()
        _unchanged(base, base_hashes)
        _unchanged(current, final_hashes)
        all_runs = development + final
        tool_seconds = lambda runs: sum(item["receipt"]["cost"]["wall_seconds"] for run in runs
            for item in run["campaign"]["observations"] if item.get("receipt"))
        completed = all(run["campaign"]["attempts_used"] == 1
            and len(run["campaign"]["observations"]) == 1
            and run["campaign"]["observations"][0]["status"] == "success" for run in all_runs)
        report = dict(schema_version=1, status="completed" if completed else "engineering_failed",
            success=completed, execution_completed=completed, method=method.name, protocol_sha256=protocol_hash,
            all_evaluation_arms_have_feasible_results=all(arm["best"] is not None for case in comparison for arm in case["arms"].values()),
            objective=asdict(objective), training=training, updates=updates,
            comparison=comparison, development=development, final_test=final,
            checkpoint_lineage=dict(base=str(base), adapted=str(current), base_hashes=base_hashes,
                                    adapted_hashes=final_hashes, base_unchanged=True),
            cost=dict(total_wall_seconds=time.perf_counter() - started + input_preparation_wall_seconds,
                input_preparation_wall_seconds=input_preparation_wall_seconds, cold_start_wall_seconds=cold_start_wall,
                initial_training_wall_seconds=training_wall,
                adaptation_wall_seconds=sum(update["wall_seconds"] for update in updates),
                shared_development_acquisition_tool_seconds=tool_seconds(development),
                shared_development_attempt_wall_seconds=sum(run["cost"]["attempt_wall_seconds"] for run in development),
                materialization_wall_seconds=sum(run["cost"]["materialization_wall_seconds"] for run in all_runs),
                final_test_attempt_wall_seconds={arm: sum(run["cost"]["attempt_wall_seconds"] for run in final if run["arm"] == arm)
                    for arm in ("adapted", "unadapted", "enumeration", "constant")},
                final_test_tool_seconds={arm: tool_seconds([r for r in final if r["arm"] == arm])
                                         for arm in ("adapted", "unadapted", "enumeration", "constant")},
                development_candidates=sum(r["campaign"]["attempts_used"] for r in development),
                final_test_candidates=sum(r["campaign"]["attempts_used"] for r in final)),
            limits=["Matched held-out candidate slots; training and shared development acquisition are additional cold-start costs",
                "Feasibility labels establish observed feasibility only; preference requires competing feasible measured actions",
                "Best measured prefix is not an exhaustive optimum or statistical superiority claim",
                "Objectives are compared within each case; unlike units are never aggregated as a speedup",
                "Check scope is declared by each task; complete-core/GDS acceptance requires every corresponding check",
                "No hidden reference fallback; invalid proposals and tool failures retain their own outcomes"])
        _write(output / "report.json", report)
        (output / "report.md").write_text(_markdown(report))
        return report
    except Exception as exc:
        _write(output / "failure.json", dict(status="failed", stage=stage,
            error_type=type(exc).__name__, error=str(exc), wall_seconds=time.perf_counter() - started))
        raise


class ByteLanguageMethod:
    """CPU byte-LM pretraining, supervised design learning, and measured updates.

    The contract and serializer are supplied by the target/course, with no
    registry or inferred representation conversion. Long raw measurements are
    split into declared bounded chunks for LM training, never silently truncated.
    """

    name = "byte_language_model"

    def __init__(self, model_io_contract, *, seed=0, pretrain_steps=120, supervised_steps=160,
                 adapt_steps=80, max_seconds=60):
        self.contract = model_io_contract
        self.seed, self.pretrain_steps = seed, pretrain_steps
        self.supervised_steps, self.adapt_steps = supervised_steps, adapt_steps
        self.max_seconds = max_seconds

    def _chunks(self, rows):
        result = []
        for row in rows:
            text, chunks, current = row["input_text"], [], ""
            for char in text:
                if len(char.encode()) > self.contract.max_input_bytes:
                    raise ContractError("A UTF-8 character exceeds the declared chunk byte envelope")
                if len((current + char).encode()) > self.contract.max_input_bytes:
                    chunks.append(current)
                    current = ""
                current += char
            if current:
                chunks.append(current)
            for index, text in enumerate(chunks):
                result.append(dict(row, input_text=text,
                    record_id=f"{row['record_id']}-chunk-{index}", chunk_parent_record_id=row["record_id"],
                    chunk_index=index, chunk_count=len(chunks)))
        return result

    def _update(self, records, output, base=None, adaptation=False):
        from .models import language
        docs = [row for row in records if "target_action" not in row]
        supervised = [row for row in records if "target_action" in row]
        phases, preceding = [], base
        for objective, rows in (("pretrain", self._chunks(docs)), ("supervised", supervised)):
            if not rows:
                continue
            final_phase = objective == "supervised" or not supervised
            destination = output if final_phase else output.with_name(output.name + "-pretrain")
            steps = self.adapt_steps if adaptation else self.pretrain_steps if objective == "pretrain" else self.supervised_steps
            metadata = language.train(rows, destination, model_io_contract=self.contract,
                objective=objective, base_checkpoint=preceding, seed=self.seed, max_steps=steps,
                max_seconds=self.max_seconds)
            if metadata["steps_completed"] != steps or not metadata["parameters_changed"]:
                raise ContractError("Byte-LM phase did not complete all declared parameter updates")
            phases.append(dict(objective=objective, checkpoint=str(destination), metadata=metadata,
                               checkpoint_sha256=file_sha256(destination / "checkpoint.pt")))
            preceding = destination
        if not phases:
            raise ContractError("Byte-LM update requires admitted text or supervised action records")
        return dict(phases=phases, parameters_changed=True,
            base_checkpoint_sha256=file_sha256(base / "checkpoint.pt") if base else None,
            initial_parameter_sha256=phases[0]["metadata"]["initial_parameter_sha256"],
            final_parameter_sha256=phases[-1]["metadata"]["final_parameter_sha256"],
            steps_completed=sum(phase["metadata"]["steps_completed"] for phase in phases))

    def train(self, records, output):
        return self._update(records, output)

    def adapt(self, records, base_checkpoint, output):
        return self._update(records, output, base_checkpoint, adaptation=True)

    def proposer(self, checkpoint, format_input):
        from .models.language import LanguageProposer
        return LanguageProposer(checkpoint, format_input, model_io_contract=self.contract)

    def implementation_sources(self):
        from .models import language
        from . import model_io
        return (language.__file__, model_io.__file__)


def teaching_core_input(task, history=(), context=()):
    """Declared known workload/intent facts, excluding goldens and tool outputs.

    Seeds and prompt prefixes identify the supplied workload, rather than an
    action label. Returned tool measurements enter the explicitly curated
    development corpus; held-out history never enters parameter updates.
    """
    from .context import with_context
    spec = task.specification
    config = spec["target"]["configuration"]
    facts = dict(model_width=config["d_model"], layers=config["n_layers"],
        experts=config["n_experts"], selected_experts=config["top_k"],
        token_count=spec["token_count"], weights_seed=spec["seed"],
        prompt_index=spec["prompt_index"], token_prefix=spec.get("tokens"),
        objective=spec["campaign_objective"])
    return with_context(canonical_json(facts), context)


def teaching_core_features(task):
    spec = task.specification
    return dict(token_count=spec["token_count"], weights_seed=spec["seed"],
                objective=spec["campaign_objective"]["metric"])


def validate_selected_design(report, output, *, backend, task_factory, materializer):
    """Fresh validation linked to the exact nominated parent design inputs.

    The physical task/checker may have a new manifest; the active RTL, physical
    configuration, microcode, tables, and runtime image must remain identical.
    A nomination failure never substitutes an authored reference candidate.
    """
    started = time.perf_counter()
    adapted = [run for run in report["final_test"] if run["arm"] == "adapted"]
    maximum = max((run["task"]["specification"]["token_count"] for run in adapted), default=None)
    # Nominate a case before inspecting its candidates. Lexical case identity
    # breaks equal-token-count ties, independent of result/observation order.
    cases = sorted({run["case_id"] for run in adapted
                    if run["task"]["specification"]["token_count"] == maximum})
    if not cases:
        result = dict(status="not_run", passed=False,
            details="No eligible adapted candidate at the maximum held-out token count; no fallback")
        _write(output / "selected-physical/report.json", result)
        return result
    case_id = cases[0]
    comparisons = [case for case in report.get("comparison", ()) if case["case_id"] == case_id]
    if len(comparisons) != 1:
        raise ContractError("Nominated maximum-workload case lacks one frozen comparison")
    comparison = comparisons[0]
    try:
        best = comparison["arms"]["adapted"]["best"]
        objective = CampaignObjective(**comparison["objective"])
    except (KeyError, TypeError) as exc:
        raise ContractError("Nominated case has a malformed adapted best or objective") from exc
    if best is None:
        result = dict(status="not_run", passed=False, case_id=case_id,
            details="The nominated maximum-workload case has no measured adapted best; no fallback")
        _write(output / "selected-physical/report.json", result)
        return result
    if (not isinstance(best, Mapping) or not isinstance(best.get("candidate_digest"), str)
            or any(key not in best for key in ("action", "value", "unit", "scope"))
            or type(best.get("value")) not in (int, float) or not math.isfinite(best["value"])
            or not isinstance(best.get("action"), str) or not best["action"]
            or type(objective.minimize) is not bool or not isinstance(objective.metric, str)
            or not objective.metric or not isinstance(objective.scope, str) or not objective.scope):
        raise ContractError("Nominated adapted best is malformed")
    runs = [run for run in adapted if run["case_id"] == case_id]
    if any(run["task"]["specification"]["token_count"] != maximum
           or run["task"]["specification"].get("campaign_objective") != asdict(objective) for run in runs):
        raise ContractError("Nominated case differs from its frozen workload/objective")
    measured_best = _best(runs, objective)
    if measured_best is None or any(best[key] != measured_best[key]
                                   for key in ("action", "value", "unit", "scope", "candidate_digest")):
        raise ContractError("Frozen adapted best does not match the best measured candidate")
    matches = [(run, item) for run in runs for item in run["campaign"]["observations"]
               if item.get("candidate_digest") == best["candidate_digest"]]
    if len(matches) != 1:
        raise ContractError("Nominated adapted best lacks one exact observation")
    run, observation = matches[0]
    receipt = observation.get("receipt")
    action = observation.get("action")
    if (observation.get("eligible") is not True or observation.get("status") != "success"
            or not receipt or receipt.get("mode") != "fresh" or receipt.get("execution_status") != "success"
            or receipt.get("candidate_digest") != best["candidate_digest"]
            or receipt.get("task_id") != run["task"]["task_id"]
            or not action or action.get("name") != best["action"]
            or action["name"] not in run["task"]["allowed_actions"]):
        raise ContractError("Nominated adapted best is not an eligible fresh observation/receipt")
    required = {(check["name"], check["scope"]) for check in run["task"]["required_checks"]}
    for checks in (observation.get("checks", ()), receipt.get("checks", ())):
        passed = {(check["name"], check["scope"]) for check in checks if check["status"] == "pass"}
        if not required <= passed:
            raise ContractError("Nominated adapted best lacks passing required checks")
    metric = receipt.get("metrics", {}).get(objective.metric)
    if (not metric or metric.get("value") != best["value"] or metric.get("unit") != objective.unit
            or metric.get("scope") != objective.scope):
        raise ContractError("Nominated adapted best differs from its measured objective")
    for artifact in receipt.get("output_artifacts", ()):
        Artifact(**artifact).validate(receipt.get("output_root") or "")
    parent_slot = output / "test" / run["case_id"] / "adapted" / f"slot-{run['slot']:03d}"
    event = next(event for event in (json.loads(line) for line in (parent_slot / "events.jsonl").read_text().splitlines())
                 if event["event"] == "candidate")
    value = event["candidate"]
    parent = Candidate(**dict(value, action=Action(**value["action"]),
                               artifacts=tuple(Artifact(**item) for item in value["artifacts"])))
    parent.validate_files()
    if (parent.digest != observation["candidate_digest"] or parent.digest != event["candidate_digest"]
            or asdict(parent.action) != action or parent.task_id != run["task"]["task_id"]
            or parent.task_digest != _digest(run["task"])):
        raise ContractError("Nominated parent differs from the measured adapted candidate")
    spec = run["task"]["specification"]
    task = task_factory(seed=spec["seed"], prompt_index=spec["prompt_index"], split="test", tokens=spec["tokens"])
    parent_inputs = {name: file_sha256(Path(parent.root) / name) for name in
        ("core.v", "physical-config.json", "program.bin", "tables.bin", "reference/image.bin")}
    task = replace(task, max_proposals=1, max_attempts=1, specification=dict(task.specification,
        nominated_parent=dict(candidate_digest=parent.digest, inputs=parent_inputs)))
    old_sources, new_sources = spec["source_artifacts"], task.specification["source_artifacts"]
    differences = {name: dict(parent=old_sources.get(name), physical=new_sources.get(name))
                   for name in sorted(set(old_sources) | set(new_sources)) if old_sources.get(name) != new_sources.get(name)}

    class Nominated:
        def propose(self, task, history, budget):
            return parent.action

    class Linked:
        def materialize(self, task, action, workspace):
            child = materializer.materialize(task, action, workspace)
            for name, expected in parent_inputs.items():
                if file_sha256(Path(child.root) / name) != expected:
                    raise ContractError("Physical candidate changed a nominated RTL/configuration/program/table/image input")
            _write(Path(child.root) / "parent-link.json", dict(parent_candidate_digest=parent.digest,
                parent_root=parent.root, exact_input_hashes=parent_inputs, task_checker_differences=differences))
            return replace(child, parent_id=parent.digest,
                artifacts=child.artifacts + (Artifact.from_file(child.root, "parent-link.json"),))

    physical = execute_campaign(task, Nominated(), Linked(), backend, output / "selected-physical/attempts",
                                JsonlRecorder(output / "selected-physical/events.jsonl"))
    parent.validate_files()
    passed = len(physical.observations) == 1 and physical.observations[0].eligible
    result = dict(status="passed" if passed else "engineering_failed", passed=passed,
        scope="selected-design physical validation, not all-arm physical comparison or PPA learning",
        parent_candidate_digest=parent.digest, parent_root=parent.root, exact_input_hashes=parent_inputs,
        nomination=dict(case_id=case_id, token_count=maximum, objective=asdict(objective), best=dict(best),
                        rule="maximum token count; lexical case tie break; frozen adapted measured best"),
        task_checker_differences=differences, task=asdict(task), campaign=asdict(physical),
        wall_seconds=time.perf_counter() - started,
        receipt_tool_seconds=sum(item.receipt.cost.wall_seconds for item in physical.observations if item.receipt))
    _write(output / "selected-physical/report.json", result)
    return result


def run_teaching_campaign(output: Path | str, *, candidate_budget=2,
        pretrain_steps=120, supervised_steps=160, adapt_steps=80, training_seconds=60,
        check_timeout=180, retriever=None, context_words=24, backend=None, task_factory=None,
        seed=17, test_seed=101, physical_mode="selected", physical_timeout=14400, cores=2,
        physical_backend=None, physical_task_factory=None, correspondence_timeout=3600) -> dict:
    """The complete teaching derivative through one connected measured loop.

    Initial data are attributed repository text, with no constructed preferred
    action labels. Development workloads have one/two tokens; frozen final
    workloads have three/four tokens, distinct weight seeds and prompt prefixes.
    The matched comparison performs complete RTL workload checks. By default,
    one nominated adapted maximum-workload candidate then receives fresh
    physical validation. ``physical_mode='functional'`` omits that stage;
    ``'every_candidate'`` explicitly adds physical checks to the learning study.
    """
    preparation_started = time.perf_counter()
    from .language_data import collect_language_corpus, load_language_corpus
    from .model_io import ModelIOContract
    from .teaching_core import make_task, TeachingCoreBackend, TeachingCoreMaterializer
    output = Path(output).resolve()
    if physical_mode not in ("functional", "selected", "every_candidate"):
        raise ContractError("Physical mode must be functional, selected, or every_candidate")
    if (type(correspondence_timeout) not in (int, float) or not math.isfinite(correspondence_timeout)
            or correspondence_timeout <= 0):
        raise ContractError("Use a positive finite correspondence timeout")
    if (type(seed) is not int or type(test_seed) is not int or min(seed, test_seed) < 0
            or len({seed, seed + 1, test_seed, test_seed + 1}) != 4):
        raise ContractError("Teaching campaign requires distinct nonnegative development and test weight seeds")
    if output.exists():
        raise ContractError("Teaching campaign output must be a new directory")
    # Corpus is a sibling input artifact, retained rather than regenerated
    # after training. The campaign separately snapshots its admitted train rows.
    corpus_root = output.with_name(output.name + "-language-corpus")
    corpus = collect_language_corpus(corpus_root, max_text_bytes=384)
    rows = [row for row in load_language_corpus(corpus) if row["split"] == "train"]
    objective = CampaignObjective("cycles", "accelerator:nanochip_teaching_core", True, "cycles")
    if physical_mode == "every_candidate":
        from functools import partial
        from .physical.teaching import make_physical_task, TeachingCorePhysicalBackend
        backend = backend or TeachingCorePhysicalBackend(check_timeout=check_timeout,
            physical_timeout=physical_timeout, cores=cores, correspondence_timeout=correspondence_timeout)
        task_factory = task_factory or partial(make_physical_task, check_timeout=check_timeout,
            physical_timeout=physical_timeout, cores=cores, correspondence_timeout=correspondence_timeout)
    factory = task_factory or make_task
    cases = tuple(CampaignCase(f"{split}-tokens-{count}", f"weights-{seed}-tokens-{count}", split,
        factory(seed=seed, prompt_index=prompt, split="development" if split == "dev" else "test", tokens=tokens))
        for split, seed, prompt, count, tokens in (
            ("dev", seed, 0, 1, [1]), ("dev", seed + 1, 1, 2, [2, 3]),
            ("test", test_seed, 0, 3, [4, 5, 6]), ("test", test_seed + 1, 1, 4, [7, 8, 9, 10])))
    contract = ModelIOContract("nanochip_teaching_core_workload", 1,
        "nanochip.teaching_core_input.v1", ("serial_mul1", "serial_mul2"), 768)
    method = ByteLanguageMethod(contract, seed=17, pretrain_steps=pretrain_steps,
        supervised_steps=supervised_steps, adapt_steps=adapt_steps, max_seconds=training_seconds)
    target = CampaignTarget(TeachingCoreMaterializer(), backend or TeachingCoreBackend(timeout_s=check_timeout),
        teaching_core_input, teaching_core_features, ("token_count", "weights_seed"), ("objective",))
    report = run_learning_campaign(output, cases=cases, training_records=rows, training_root=corpus_root,
        method=method, target=target, objective=objective, candidate_budget=candidate_budget,
        retriever=retriever, context_words=context_words, constant_action="serial_mul2",
        input_preparation_wall_seconds=time.perf_counter() - preparation_started)
    # Preserve the functional experiment before appending the independently
    # scoped selected-design physical result to the system-level report.
    _write(output / ("comparison-report.json" if physical_mode == "every_candidate" else "functional-report.json"), report)
    report["physical_mode"] = physical_mode
    if physical_mode == "selected":
        physical_started = time.perf_counter()
        try:
            from functools import partial
            from .physical.teaching import make_physical_task, TeachingCorePhysicalBackend
            physical = validate_selected_design(report, output,
                backend=physical_backend or TeachingCorePhysicalBackend(check_timeout=check_timeout,
                    physical_timeout=physical_timeout, cores=cores, correspondence_timeout=correspondence_timeout),
                task_factory=physical_task_factory or partial(make_physical_task, check_timeout=check_timeout,
                    physical_timeout=physical_timeout, cores=cores, correspondence_timeout=correspondence_timeout),
                materializer=TeachingCoreMaterializer())
        except Exception as exc:
            report.update(success=False, status="failed", selected_physical=dict(status="failed", passed=False,
                error_type=type(exc).__name__, error=str(exc)))
            _write(output / "selected-physical/failure.json", report["selected_physical"])
            (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
            (output / "report.md").write_text(_markdown(report) + "\nSelected physical validation failed; inspect selected-physical/failure.json.\n")
            raise
        report["selected_physical"] = physical
        report["success"] = report["execution_completed"] and physical["passed"]
        report["status"] = "completed" if report["success"] else "engineering_failed"
        report["cost"]["selected_physical_wall_seconds"] = time.perf_counter() - physical_started
        report["cost"]["selected_physical_receipt_tool_seconds"] = physical.get("receipt_tool_seconds", 0.0)
        report["cost"]["total_wall_seconds"] += report["cost"]["selected_physical_wall_seconds"]
    elif physical_mode == "every_candidate":
        report["success"] = report["execution_completed"] and report["all_evaluation_arms_have_feasible_results"]
        report["status"] = "completed" if report["success"] else "engineering_failed"
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    markdown = _markdown(report)
    if "selected_physical" in report:
        physical = report["selected_physical"]
        markdown += ("\nSelected-design physical validation: **" + physical["status"] + "**. "
            "[Exact parent/input linkage and every physical check](selected-physical/report.json). "
            "This stage does not establish PPA learning or physical equality across comparison arms.\n")
    (output / "report.md").write_text(markdown)
    return report


def main(argv=None):
    """Explicit system entry point; optional learning imports remain lazy."""
    import argparse
    parser = argparse.ArgumentParser(description="Train and adapt one design model from exact complete-core tool feedback")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--functional-only", action="store_true",
                        help="run exact complete-workload RTL checks; explicitly omit physical implementation")
    parser.add_argument("--physical-every-candidate", action="store_true",
                        help="expensive PPA study: run physical checks for every development and evaluation candidate")
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--test-seed", type=int, default=101)
    parser.add_argument("--candidate-budget", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=180, help="seconds per complete RTL candidate")
    parser.add_argument("--physical-timeout", type=float, default=14400,
                        help="engineering wall cap in seconds per full-core physical candidate; not a runtime promise")
    parser.add_argument("--correspondence-timeout", type=float, default=3600,
                        help="seconds for mapped-netlist correspondence compilation and checks")
    parser.add_argument("--cores", type=int, default=2)
    parser.add_argument("--pretrain-steps", type=int, default=120)
    parser.add_argument("--adapt-steps", type=int, default=80)
    parser.add_argument("--training-seconds", type=float, default=60)
    args = parser.parse_args(argv)
    if args.functional_only and args.physical_every_candidate:
        parser.error("--functional-only and --physical-every-candidate are mutually exclusive")
    physical_options = {}
    mode = "functional" if args.functional_only else "every_candidate" if args.physical_every_candidate else "selected"
    if mode == "every_candidate":
        from functools import partial
        from .physical.teaching import make_physical_task, TeachingCorePhysicalBackend
        physical_options = dict(backend=TeachingCorePhysicalBackend(check_timeout=args.timeout,
            physical_timeout=args.physical_timeout, cores=args.cores, correspondence_timeout=args.correspondence_timeout),
            task_factory=partial(make_physical_task, check_timeout=args.timeout,
                physical_timeout=args.physical_timeout, cores=args.cores, correspondence_timeout=args.correspondence_timeout))
    report = run_teaching_campaign(args.output, seed=args.seed, test_seed=args.test_seed,
        candidate_budget=args.candidate_budget, check_timeout=args.timeout,
        pretrain_steps=args.pretrain_steps, adapt_steps=args.adapt_steps, training_seconds=args.training_seconds,
        physical_mode=mode, physical_timeout=args.physical_timeout, cores=args.cores,
        correspondence_timeout=args.correspondence_timeout,
        **physical_options)
    execution = "completed" if report.get("execution_completed", report["success"]) else "engineering_failed"
    print(f"Experiment execution: {execution}")
    print(f"System validation: {report['status']}")
    print("Scope: complete teaching-derivative RTL workloads; physical implementation was explicitly omitted." if args.functional_only else
          "Scope: complete teaching derivative through the physical adapter; inspect every named check and correspondence result.")
    for case in report["comparison"]:
        print(f"{case['case_id']}: {case['objective']['metric']} ({case['objective']['scope']})")
        for arm, outcome in case["arms"].items():
            best = outcome["best"]
            print(f"  {arm}: {best['action']} = {best['value']} {best['unit']}" if best else
                  f"  {arm}: no feasible measured candidate")
    print("Executed experiment is separate from design acceptance; inspect selected physical checks, correspondence, and remaining boundaries.")
    print(f"Retained report: {Path(args.output).resolve() / 'report.json'}")
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
