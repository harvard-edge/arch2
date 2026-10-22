"""Run the complete orchestration against an explicitly synthetic process tool."""

from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys

import pytest

from nanochip.laboratory import campaign
from nanochip.laboratory.context import KeywordContext
from nanochip.laboratory.contracts import (
    Action,
    Artifact,
    Candidate,
    CheckRequirement,
    CheckResult,
    ContractError,
    Cost,
    Metric,
    Observation,
    RunReceipt,
    Task,
    file_sha256,
)


SCOPE = "fixture:synthetic_process_not_rtl"
OBJECTIVE = campaign.CampaignObjective("cycles", SCOPE, unit="cycles")


def serialize(task, history, context):
    # Deliberately excludes identity, split, labels, and future tool results.
    return (
        "toy workload="
        + str(task.specification["workload"])
        + "\n"
        + " ".join(s["text"] for s in context)
    )


class Materializer:
    def materialize(self, task, action, workspace):
        root = workspace / "candidate"
        root.mkdir()
        (root / "input.json").write_text(
            json.dumps(
                dict(action=action.name, workload=task.specification["workload"])
            )
        )
        return Candidate(
            action.name,
            task.task_id,
            str(root),
            action,
            (Artifact.from_file(root, "input.json"),),
            task_digest=task.digest,
        )


class ProcessTool:
    """An actual subprocess with synthetic metrics; never an RTL stand-in claim."""

    def __init__(self, timeline, *, fail_fast=False, wrong_candidate=False):
        self.timeline, self.calls = timeline, []
        self.fail_fast, self.wrong_candidate = fail_fast, wrong_candidate

    def evaluate(self, task, candidate):
        self.timeline.append(("tool", task.specification["campaign_run"]["split"]))
        self.calls.append(candidate.action.name)
        candidate.validate_files()
        output = Path(candidate.root).parent / "tool"
        output.mkdir()
        source = Path(candidate.root) / "input.json"
        # This subprocess exercises real execution/artifact/failure handling.
        code = "import json,sys; r=json.load(open(sys.argv[1])); print(json.dumps({'cycles': {'slow':9,'fast':3}[r['action']]})); sys.exit(1 if sys.argv[2]=='yes' and r['action']=='fast' else 0)"
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                code,
                str(source),
                "yes" if self.fail_fast else "no",
            ],
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
        (output / "stdout.json").write_text(completed.stdout)
        (output / "stderr.log").write_text(completed.stderr)
        metric = json.loads(completed.stdout)["cycles"]
        return RunReceipt(
            task.task_id,
            "different candidate" if self.wrong_candidate else candidate.digest,
            "fresh",
            "error" if completed.returncode else "success",
            "synthetic Python fixture",
            sys.version,
            checks=(
                CheckResult(
                    "compute", "not_run" if completed.returncode else "pass", SCOPE
                ),
            ),
            metrics={"cycles": Metric(metric, "cycles", SCOPE)},
            cost=Cost(0.01),
            output_root=str(output),
            output_artifacts=tuple(
                Artifact.from_file(output, name)
                for name in ("stdout.json", "stderr.log")
            ),
        )


class Method:
    """Fixture update counter, explicitly not a learned model."""

    name = "synthetic_update_fixture"

    def __init__(self, timeline):
        self.timeline, self.updates = timeline, []

    def _save(self, output, version):
        output.mkdir(parents=True)
        (output / "checkpoint.pt").write_text(json.dumps(dict(version=version)))
        (output / "config.json").write_text(json.dumps(dict(fixture=True)))

    def train(self, records, output):
        self.timeline.append(("train", "train"))
        self._save(output, 0)
        return dict(parameters_changed=True, fixture=True)

    def adapt(self, records, base_checkpoint, output):
        self.timeline.append(("adapt", "dev"))
        self.updates.append(records)
        previous = json.loads((base_checkpoint / "checkpoint.pt").read_text())[
            "version"
        ]
        self._save(output, previous + 1)
        return dict(
            parameters_changed=True,
            base_checkpoint_sha256=file_sha256(base_checkpoint / "checkpoint.pt"),
        )

    def proposer(self, checkpoint, format_input):
        version = json.loads((checkpoint / "checkpoint.pt").read_text())["version"]

        class Proposer:
            def propose(self, task, history, budget):
                format_input(task, history)
                return Action("fast" if version else "slow")

        return Proposer()


def setup(tmp_path, *, fail_fast=False, wrong_candidate=False):
    source = tmp_path / "source.json"
    source.write_text(json.dumps(dict(text="toy fixture training text")))
    rows = [
        dict(
            record_id="train-doc",
            group_id="train-doc",
            split="train",
            original_split="train",
            input_text="toy fixture training text",
            source_sha256=file_sha256(source),
            source_receipt=dict(path=source.name, sha256=file_sha256(source)),
            data_origin="constructed",
            label_origin="synthetic orchestration test",
        )
    ]
    cases = [
        campaign.CampaignCase(
            f"case-{split}",
            f"group-{split}",
            split,
            Task(
                f"task-{split}",
                ("slow", "fast"),
                (CheckRequirement("compute", SCOPE),),
                specification=dict(workload=index),
            ),
        )
        for index, split in enumerate(("dev", "test"))
    ]
    timeline = []
    method = Method(timeline)
    backend = ProcessTool(
        timeline, fail_fast=fail_fast, wrong_candidate=wrong_candidate
    )
    target = campaign.CampaignTarget(Materializer(), backend, serialize)
    return (
        dict(
            cases=cases,
            training_records=rows,
            training_root=tmp_path,
            method=method,
            target=target,
            objective=OBJECTIVE,
        ),
        timeline,
    )


def test_complete_measured_loop_freezes_before_matched_heldout_comparison(tmp_path):
    kwargs, timeline = setup(tmp_path)
    report = campaign.run_learning_campaign(
        tmp_path / "run", retriever=KeywordContext(), **kwargs
    )
    assert report["success"] is True
    assert len(report["updates"]) == 2
    assert [update["curation"]["label_kind"] for update in report["updates"]] == [
        "feasibility",
        "preference",
    ]
    assert [update["curation"]["selected_action"] for update in report["updates"]] == [
        "slow",
        "fast",
    ]
    test_start = next(
        index for index, event in enumerate(timeline) if event == ("tool", "test")
    )
    assert not any(event[0] in ("train", "adapt") for event in timeline[test_start:])
    for rows in kwargs["method"].updates:
        assert all(
            row["original_split"] != "test" and row["group_id"] != "group-test"
            for row in rows
        )
    arms = report["comparison"][0]["arms"]
    assert {arm["candidate_slots"] for arm in arms.values()} == {2}
    assert {arm["attempts_used"] for arm in arms.values()} == {2}
    assert arms["adapted"]["best"]["value"] == arms["enumeration"]["best"]["value"]
    assert arms["unadapted"]["best"]["value"] > arms["adapted"]["best"]["value"]
    assert report["cost"]["development_candidates"] == 2 * 2
    assert report["cost"]["final_test_candidates"] == 4 * 2
    assert report["checkpoint_lineage"]["base_unchanged"] is True
    assert (tmp_path / "run/frozen-evaluation.json").exists()
    # Every tool result, including the conventional arm, stays inspectable.
    assert len(list((tmp_path / "run").rglob("stdout.json"))) == (2 + 4) * 2


def test_per_case_objective_override_is_frozen_and_compared_only_within_case(tmp_path):
    kwargs, _ = setup(tmp_path)
    case = kwargs["cases"][1]
    kwargs["cases"][1] = replace(
        case, objective=campaign.CampaignObjective("cycles", SCOPE, False, "cycles")
    )
    report = campaign.run_learning_campaign(tmp_path / "run", **kwargs)
    comparison = report["comparison"][0]
    assert comparison["objective"]["minimize"] is False
    assert comparison["objective"]["unit"] == "cycles"
    assert comparison["arms"]["enumeration"]["best"]["action"] == "slow"
    protocol = json.loads((tmp_path / "run/protocol.json").read_text())
    assert protocol["cases"][1]["objective"] == comparison["objective"]


def test_missing_requested_metric_keeps_explicit_no_measured_candidate_outcome(
    tmp_path,
):
    kwargs, _ = setup(tmp_path)
    kwargs["cases"][1] = replace(
        kwargs["cases"][1],
        objective=campaign.CampaignObjective("physical_area", SCOPE, True, "um^2"),
    )
    report = campaign.run_learning_campaign(tmp_path / "run", **kwargs)
    assert all(
        arm["outcome"] == "no_feasible_measured_candidate" and arm["best"] is None
        for arm in report["comparison"][0]["arms"].values()
    )


def test_failed_tool_receipts_are_retained_without_feasible_preference_labels(tmp_path):
    kwargs, _ = setup(tmp_path, fail_fast=True)
    report = campaign.run_learning_campaign(tmp_path / "run", **kwargs)
    assert report["status"] == "engineering_failed" and report["success"] is False
    assert report["comparison"][0]["arms"]["adapted"]["best"] is None
    assert report["comparison"][0]["arms"]["enumeration"]["best"]["action"] == "slow"
    assert all(
        update["curation"]["label_kind"] == "feasibility"
        for update in report["updates"]
    )
    labels = [row for row in kwargs["method"].updates[-1] if row.get("target_action")]
    assert {row["target_action"] for row in labels} == {"slow"}
    assert list((tmp_path / "run").rglob("stderr.log"))


def test_receipt_identity_failure_stops_before_adaptation_or_fallback(tmp_path):
    kwargs, _ = setup(tmp_path, wrong_candidate=True)
    with pytest.raises(ContractError, match="different candidate"):
        campaign.run_learning_campaign(tmp_path / "run", **kwargs)
    assert kwargs["method"].updates == []
    assert kwargs["target"].backend.calls == ["slow"]
    failure = json.loads((tmp_path / "run/failure.json").read_text())
    assert failure["stage"] == "development"
    assert not (tmp_path / "run/report.json").exists()


@pytest.mark.parametrize("leak", ["original_split", "group_id", "case_id"])
def test_heldout_training_overlap_is_rejected_before_any_update(tmp_path, leak):
    kwargs, timeline = setup(tmp_path)
    row = kwargs["training_records"][0]
    row[leak] = {
        "original_split": "test",
        "group_id": "group-test",
        "case_id": "case-test",
    }[leak]
    with pytest.raises(ContractError, match="test|training-only"):
        campaign.run_learning_campaign(tmp_path / "run", **kwargs)
    assert timeline == []


def test_cross_partition_case_family_is_rejected(tmp_path):
    kwargs, _ = setup(tmp_path)
    kwargs["cases"][1] = replace(kwargs["cases"][1], group_id="group-dev")
    with pytest.raises(ContractError, match="groups cross"):
        campaign.run_learning_campaign(tmp_path / "run", **kwargs)


def test_case_identity_cannot_escape_its_output_directory(tmp_path):
    kwargs, _ = setup(tmp_path)
    kwargs["cases"][0] = replace(kwargs["cases"][0], case_id="../escape")
    with pytest.raises(ContractError, match="identities"):
        campaign.run_learning_campaign(tmp_path / "run", **kwargs)


def test_retrieval_cannot_inject_final_test_evidence(tmp_path):
    kwargs, _ = setup(tmp_path)

    class BadRetriever:
        def build(self, task, history, sources, budget):
            return [
                dict(
                    source_id="test-source",
                    partition="test",
                    text="secret outcomes",
                    text_sha256=campaign._digest_text("secret outcomes"),
                )
            ]

    with pytest.raises(ContractError, match="final-test evidence"):
        campaign.run_learning_campaign(
            tmp_path / "run", retriever=BadRetriever(), **kwargs
        )
    assert kwargs["target"].backend.calls == []


def test_adaptation_must_continue_same_model_checkpoint(tmp_path):
    kwargs, _ = setup(tmp_path)
    original = kwargs["method"].adapt

    def reinitialized(records, base, output):
        metadata = original(records, base, output)
        metadata["base_checkpoint_sha256"] = "0" * 64
        return metadata

    kwargs["method"].adapt = reinitialized
    with pytest.raises(ContractError, match="preceding design checkpoint"):
        campaign.run_learning_campaign(tmp_path / "run", **kwargs)
    assert not (tmp_path / "run/frozen-evaluation.json").exists()


def test_invalid_model_action_has_no_reference_fallback_or_extra_budget(tmp_path):
    kwargs, _ = setup(tmp_path)

    class Invalid:
        def propose(self, task, history, budget):
            return Action("not_a_legal_design")

    kwargs["method"].proposer = lambda checkpoint, format_input: Invalid()
    report = campaign.run_learning_campaign(tmp_path / "run", **kwargs)
    assert report["success"] is False
    arms = report["comparison"][0]["arms"]
    assert arms["adapted"]["attempts_used"] == arms["unadapted"]["attempts_used"] == 0
    assert arms["enumeration"]["attempts_used"] == 2
    assert kwargs["target"].backend.calls == [
        "slow",
        "fast",
        "slow",
        "fast",
        "fast",
        "fast",
    ]


def observation(
    case, action, value, *, eligible=True, check_status="pass", metric_scope=SCOPE
):
    receipt = RunReceipt(
        case.task.task_id,
        action,
        "fresh",
        "success",
        "synthetic curation fixture",
        "1",
        checks=(CheckResult("compute", check_status, SCOPE),),
        metrics={"cycles": Metric(value, "cycles", metric_scope)},
    )
    return Observation(
        Action(action), action, action, "success", receipt.checks, eligible, receipt
    )


@pytest.mark.parametrize(
    "values,kind,selected",
    [
        ([("slow", 9)], "feasibility", "slow"),
        ([("slow", 9), ("slow", 3)], "feasibility", "slow"),
        ([("slow", 9), ("fast", 3)], "preference", "fast"),
        ([("slow", 3), ("fast", 3)], None, None),
    ],
)
def test_curation_distinguishes_feasibility_preference_and_ties(
    tmp_path, values, kind, selected
):
    kwargs, _ = setup(tmp_path)
    case = kwargs["cases"][0]
    rows, summary = campaign.curate_feedback(
        case,
        [observation(case, *value) for value in values],
        objective=OBJECTIVE,
        input_text="toy workload",
        output=tmp_path / "feedback.json",
        campaign_root=tmp_path,
    )
    assert summary["label_kind"] == kind and summary["selected_action"] == selected
    assert (
        rows[0]["label_kind"] == "measurement_text" and "target_action" not in rows[0]
    )
    assert len(rows) == (2 if selected else 1)


@pytest.mark.parametrize(
    "changes",
    [dict(eligible=False), dict(check_status="fail"), dict(metric_scope="wrong:scope")],
)
def test_missing_or_failed_scoped_evidence_cannot_become_positive_labels(
    tmp_path, changes
):
    kwargs, _ = setup(tmp_path)
    case = kwargs["cases"][0]
    rows, summary = campaign.curate_feedback(
        case,
        [observation(case, "fast", 3, **changes)],
        objective=OBJECTIVE,
        input_text="toy workload",
        output=tmp_path / "feedback.json",
        campaign_root=tmp_path,
    )
    assert summary["label_kind"] is None
    assert all("target_action" not in row for row in rows)


def test_final_test_is_never_curated_even_if_it_passes(tmp_path):
    kwargs, _ = setup(tmp_path)
    case = kwargs["cases"][1]
    with pytest.raises(ContractError, match="cannot become training/RAG"):
        campaign.curate_feedback(
            case,
            [observation(case, "fast", 3)],
            objective=OBJECTIVE,
            input_text="toy workload",
            output=tmp_path / "feedback.json",
            campaign_root=tmp_path,
        )
    assert not (tmp_path / "feedback.json").exists()


def test_actual_byte_lm_continues_same_weights_through_measured_tool_loop(tmp_path):
    pytest.importorskip("torch")
    from nanochip.laboratory.model_io import ModelIOContract
    from nanochip.laboratory.models.language import load_model

    kwargs, _ = setup(tmp_path)
    contract = ModelIOContract(
        "synthetic_campaign", 1, "test.serialize.v1", ("slow", "fast"), 256
    )
    # Disclosed constructed instruction rows supplement the initial text corpus.
    docs = kwargs["training_records"]
    for index, action in enumerate(contract.actions):
        docs.append(
            dict(
                docs[0],
                record_id=f"instruction-{index}",
                group_id=f"instruction-{index}",
                input_text=f"toy workload={index + 10}\n",
                target_action=action,
            )
        )
    kwargs["method"] = campaign.ByteLanguageMethod(
        contract, pretrain_steps=2, supervised_steps=2, adapt_steps=1, max_seconds=30
    )
    report = campaign.run_learning_campaign(tmp_path / "run", **kwargs)
    assert report["success"] is True
    assert [phase["objective"] for phase in report["training"]["phases"]] == [
        "pretrain",
        "supervised",
    ]
    base = load_model(
        report["checkpoint_lineage"]["base"], expected_model_io_contract=contract
    )
    adapted = load_model(
        report["checkpoint_lineage"]["adapted"], expected_model_io_contract=contract
    )
    assert (
        base.metadata["final_parameter_sha256"]
        != adapted.metadata["final_parameter_sha256"]
    )
    assert all(
        row["original_split"] != "test" for row in adapted.metadata["training_records"]
    )
    assert any(
        row["data_origin"] == "measured" for row in adapted.metadata["training_records"]
    )
    assert adapted.config["architecture"] == "byte-gru-lm/v1"


def test_exact_heldout_prompt_is_rejected_even_with_different_declared_group(tmp_path):
    kwargs, timeline = setup(tmp_path)
    kwargs["training_records"][0]["input_text"] = serialize(
        kwargs["cases"][1].task, (), ()
    )
    with pytest.raises(ContractError, match="Exact final-test represented input"):
        campaign.run_learning_campaign(tmp_path / "run", **kwargs)
    assert timeline == []


def test_component_import_does_not_eagerly_import_torch():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import nanochip.laboratory.campaign; print('torch' in sys.modules)",
        ],
        text=True,
        capture_output=True,
        check=True,
        timeout=5,
    )
    assert result.stdout.strip() == "False"


def test_cli_default_requests_one_selected_design_physical_validation(
    tmp_path, monkeypatch
):
    calls = []

    def fixture(output, **kwargs):
        calls.append(kwargs)
        return dict(status="completed", success=True, comparison=[])

    monkeypatch.setattr(campaign, "run_teaching_campaign", fixture)
    assert campaign.main(["--output", str(tmp_path / "run"), "--cores", "1"]) == 0
    assert calls[0]["physical_mode"] == "selected" and calls[0]["cores"] == 1
    assert calls[0]["physical_timeout"] == 14400
    assert calls[0]["correspondence_timeout"] == 3600
    assert "backend" not in calls[0]


def test_cli_physical_every_candidate_is_explicit_and_has_matched_budgets(
    tmp_path, monkeypatch
):
    from nanochip.laboratory.physical.teaching import TeachingCorePhysicalBackend

    calls = []

    def fixture(output, **kwargs):
        calls.append(kwargs)
        return dict(status="completed", success=True, comparison=[])

    monkeypatch.setattr(campaign, "run_teaching_campaign", fixture)
    assert (
        campaign.main(
            [
                "--physical-every-candidate",
                "--output",
                str(tmp_path / "run"),
                "--cores",
                "1",
            ]
        )
        == 0
    )
    assert calls[0]["physical_mode"] == "every_candidate"
    assert isinstance(calls[0]["backend"], TeachingCorePhysicalBackend)
    assert calls[0]["backend"].cores == 1
    assert calls[0]["backend"].physical_timeout == 14400
    assert calls[0]["backend"].correspondence_timeout == 3600
    assert calls[0]["task_factory"].keywords == dict(
        check_timeout=180, physical_timeout=14400, cores=1, correspondence_timeout=3600
    )


@pytest.mark.parametrize("mode", ["selected", "every_candidate"])
def test_cli_forwards_custom_physical_and_correspondence_budgets_without_changing_checks(
    tmp_path, monkeypatch, mode
):
    calls = []

    def fixture(output, **kwargs):
        calls.append(kwargs)
        return dict(status="completed", success=True, comparison=[])

    monkeypatch.setattr(campaign, "run_teaching_campaign", fixture)
    args = [
        "--output",
        str(tmp_path / "run"),
        "--physical-timeout",
        "12345",
        "--correspondence-timeout",
        "750",
    ]
    if mode == "every_candidate":
        args.append("--physical-every-candidate")
    assert campaign.main(args) == 0
    assert calls[0]["correspondence_timeout"] == 750
    assert calls[0]["physical_timeout"] == 12345
    if mode == "every_candidate":
        assert calls[0]["backend"].physical_timeout == 12345
        assert calls[0]["task_factory"].keywords["physical_timeout"] == 12345
        assert calls[0]["backend"].correspondence_timeout == 750
        assert calls[0]["task_factory"].keywords["correspondence_timeout"] == 750


@pytest.mark.parametrize("mode", ["selected", "every_candidate"])
def test_teaching_api_uses_same_correspondence_budget_for_task_and_backend(
    tmp_path, monkeypatch, mode
):
    from nanochip.laboratory import language_data

    calls = []
    monkeypatch.setattr(language_data, "collect_language_corpus", lambda *a, **k: {})
    monkeypatch.setattr(
        language_data, "load_language_corpus", lambda *a, **k: [dict(split="train")]
    )
    monkeypatch.setattr(
        campaign, "_markdown", lambda report: "synthetic forwarding fixture\n"
    )

    def learning(output, **kwargs):
        output.mkdir()
        if mode == "every_candidate":
            calls.append(
                (
                    kwargs["target"].backend,
                    kwargs["cases"][0].task.specification["physical"],
                )
            )
        return dict(
            success=True,
            execution_completed=True,
            status="completed",
            comparison=[],
            all_evaluation_arms_have_feasible_results=True,
            cost=dict(total_wall_seconds=0.0),
        )

    def selected(report, output, **kwargs):
        calls.append(
            (
                kwargs["backend"],
                kwargs["task_factory"](seed=7).specification["physical"],
            )
        )
        return dict(status="passed", passed=True, receipt_tool_seconds=0.0)

    monkeypatch.setattr(campaign, "run_learning_campaign", learning)
    monkeypatch.setattr(campaign, "validate_selected_design", selected)
    result = campaign.run_teaching_campaign(
        tmp_path / "run", physical_mode=mode, correspondence_timeout=750
    )
    assert result["success"] is True
    assert len(calls) == 1
    assert (
        calls[0][0].correspondence_timeout
        == calls[0][1]["correspondence_timeout"]
        == 750
    )
    assert calls[0][0].physical_timeout == calls[0][1]["physical_timeout"] == 14400


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan"), True])
def test_invalid_correspondence_budget_rejected_before_collection_or_training(
    tmp_path, timeout
):
    with pytest.raises(ContractError, match="positive finite correspondence timeout"):
        campaign.run_teaching_campaign(tmp_path / "run", correspondence_timeout=timeout)
    assert not (tmp_path / "run").exists()
    assert not (tmp_path / "run-language-corpus").exists()


def test_cli_separates_execution_from_acceptance_and_reports_ties(
    tmp_path, monkeypatch, capsys
):
    arguments = []

    def fixture(output, **kwargs):
        arguments.append((output, kwargs))
        return dict(
            status="completed",
            success=True,
            comparison=[
                dict(
                    case_id="heldout",
                    objective=asdict(OBJECTIVE),
                    arms={
                        arm: dict(best=dict(action="fast", value=3, unit="cycles"))
                        for arm in ("adapted", "unadapted", "enumeration", "constant")
                    },
                )
            ],
        )

    from dataclasses import asdict

    monkeypatch.setattr(campaign, "run_teaching_campaign", fixture)
    assert campaign.main(["--functional-only", "--output", str(tmp_path / "run")]) == 0
    output = capsys.readouterr().out
    assert "Experiment execution: completed" in output
    assert "constant: fast = 3 cycles" in output
    assert "separate from design acceptance" in output
    assert "physical implementation was explicitly omitted" in output
    assert arguments[0][1]["candidate_budget"] == 2


def test_core_representation_contains_only_known_facts_and_declared_objective():
    task = Task(
        "synthetic-representation",
        ("serial_mul1", "serial_mul2"),
        (CheckRequirement("unused", SCOPE),),
        specification=dict(
            target=dict(
                configuration=dict(d_model=8, n_layers=2, n_experts=4, top_k=2)
            ),
            token_count=4,
            seed=101,
            prompt_index=0,
            tokens=[1, 2, 3, 4],
            campaign_objective=dict(
                metric="cycles",
                scope="accelerator:nanochip_teaching_core",
                minimize=True,
            ),
            exact_goldens="MUST_NOT_ENTER_INPUT",
            observed_cycles=12345,
            source_artifacts={"path": "MUST_NOT_ENTER_INPUT"},
        ),
    )
    text = campaign.teaching_core_input(task)
    assert "MUST_NOT_ENTER_INPUT" not in text and "observed_cycles" not in text
    assert '"token_count":4' in text and '"weights_seed":101' in text
    assert '"token_prefix":[1,2,3,4]' in text and '"objective"' in text


def test_dev_test_exact_prompt_collision_is_rejected_before_work(tmp_path):
    kwargs, timeline = setup(tmp_path)
    case = kwargs["cases"][1]
    kwargs["cases"][1] = replace(
        case, task=replace(case.task, specification=dict(workload=0))
    )
    with pytest.raises(ContractError, match="crosses development and final-test"):
        campaign.run_learning_campaign(tmp_path / "run", **kwargs)
    assert timeline == [] and not (tmp_path / "run").exists()


def test_contextual_final_prompt_cannot_equal_an_admitted_training_input(tmp_path):
    kwargs, _ = setup(tmp_path)

    class Retriever:
        def build(self, task, history, sources, budget):
            return [dict(sources[0])]

    def contextual(task, history, context):
        if task.specification.get("campaign_run", {}).get("split") == "test":
            return context[0]["text"]
        return serialize(task, history, context)

    kwargs["target"] = replace(kwargs["target"], serialize=contextual)
    with pytest.raises(ContractError, match="Contextual represented input"):
        campaign.run_learning_campaign(
            tmp_path / "run", retriever=Retriever(), **kwargs
        )
    assert len(kwargs["target"].backend.calls) == 2 * 2


def test_undeclared_units_are_rejected_and_wrong_units_never_become_preference(
    tmp_path,
):
    with pytest.raises(ContractError, match="explicit measurement unit"):
        campaign.CampaignObjective("cycles", SCOPE)
    kwargs, _ = setup(tmp_path)
    case = kwargs["cases"][0]
    wrong = observation(case, "fast", 3)
    wrong = replace(
        wrong,
        receipt=replace(wrong.receipt, metrics={"cycles": Metric(3, "seconds", SCOPE)}),
    )
    rows, summary = campaign.curate_feedback(
        case,
        [observation(case, "slow", 9), wrong],
        objective=OBJECTIVE,
        input_text="toy workload",
        output=tmp_path / "feedback.json",
        campaign_root=tmp_path,
    )
    assert (
        summary["label_kind"] == "feasibility" and summary["selected_action"] == "slow"
    )
    assert not any(row.get("label_kind") == "preference" for row in rows)


def test_distributions_support_and_stage_costs_are_retained(tmp_path):
    kwargs, _ = setup(tmp_path)
    kwargs["target"] = replace(
        kwargs["target"],
        features=lambda task: dict(workload=task.specification["workload"]),
        numeric_features=("workload",),
    )
    report = campaign.run_learning_campaign(
        tmp_path / "run", input_preparation_wall_seconds=0.25, **kwargs
    )
    assert (
        report["execution_completed"] is True
        and report["all_evaluation_arms_have_feasible_results"] is True
    )
    assert report["cost"]["input_preparation_wall_seconds"] == 0.25
    assert report["cost"]["materialization_wall_seconds"] > 0
    assert set(report["cost"]["final_test_attempt_wall_seconds"]) == {
        "adapted",
        "unadapted",
        "enumeration",
        "constant",
    }
    assert all(
        summary["cost"]["attempt_wall_seconds"]
        >= summary["cost"]["materialization_wall_seconds"]
        for summary in report["development"] + report["final_test"]
    )
    assessments = report["final_test"][0]["observed_input_support"]
    assert assessments[0]["feature_support"]["within_observed_support"] is False
    assert any(
        reason["code"] == "numeric_outside_training_range"
        for reason in assessments[0]["feature_support"]["reasons"]
    )
    profile = json.loads(
        (tmp_path / "run/characterization/final-training.json").read_text()
    )
    assert profile["profile"]["data_origin_counts"]["measured"] > 0
    markdown = (tmp_path / "run/report.md").read_text()
    assert "Receipt tool time" in markdown and "no total-cost advantage" in markdown


def selected_fixture(tmp_path, *, correspondence="pass", alter_program=False):
    from dataclasses import asdict

    slot = tmp_path / "test/heldout/adapted/slot-000"
    root = slot / "attempts/attempt-0001/candidate"
    root.mkdir(parents=True)
    names = (
        "core.v",
        "physical-config.json",
        "program.bin",
        "tables.bin",
        "reference/image.bin",
    )
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic exact input: " + name)
    task = Task(
        "selected-fixture",
        ("serial_mul1", "serial_mul2"),
        (CheckRequirement("compute", SCOPE),),
        specification=dict(
            seed=17,
            prompt_index=0,
            tokens=[1, 2, 3, 4],
            token_count=4,
            source_artifacts={"checker.py": "a" * 64},
            campaign_objective=asdict(OBJECTIVE),
        ),
    )
    candidate = Candidate(
        "serial_mul2",
        task.task_id,
        str(root),
        Action("serial_mul2"),
        tuple(Artifact.from_file(root, name) for name in names),
        task_digest=task.digest,
    )
    event = dict(
        event="candidate",
        candidate=asdict(candidate),
        candidate_digest=candidate.digest,
    )
    (slot / "events.jsonl").write_text(json.dumps(event) + "\n")
    check = CheckResult("compute", "pass", SCOPE)
    receipt = RunReceipt(
        task.task_id,
        candidate.digest,
        "fresh",
        "success",
        "synthetic parent fixture",
        "1",
        checks=(check,),
        metrics={"cycles": Metric(3, "cycles", SCOPE)},
    )
    parent_observation = Observation(
        candidate.action,
        candidate.candidate_id,
        candidate.digest,
        "success",
        (check,),
        True,
        receipt,
    )
    best = dict(
        action="serial_mul2",
        value=3,
        unit="cycles",
        scope=SCOPE,
        candidate_digest=candidate.digest,
    )
    report = dict(
        final_test=[
            dict(
                arm="adapted",
                case_id="heldout",
                slot=0,
                task=asdict(task),
                campaign=dict(observations=[asdict(parent_observation)]),
            )
        ],
        comparison=[
            dict(
                case_id="heldout",
                objective=asdict(OBJECTIVE),
                arms=dict(adapted=dict(best=best)),
            )
        ],
    )

    def factory(**kwargs):
        return replace(
            task,
            required_checks=task.required_checks
            + (CheckRequirement("rtl_netlist_correspondence", SCOPE),),
            specification=dict(
                task.specification, source_artifacts={"checker.py": "b" * 64}
            ),
        )

    class Copier:
        def materialize(self, task, action, workspace):
            import shutil

            child = workspace / "candidate"
            shutil.copytree(root, child)
            if alter_program:
                (child / "program.bin").write_text("changed program")
            return Candidate(
                action.name,
                task.task_id,
                str(child),
                action,
                tuple(Artifact.from_file(child, name) for name in names),
                task_digest=task.digest,
            )

    class PhysicalFixture:
        def __init__(self):
            self.calls = 0

        def evaluate(self, task, candidate):
            self.calls += 1
            assert candidate.parent_id == event["candidate_digest"]
            return RunReceipt(
                task.task_id,
                candidate.digest,
                "fresh",
                "success",
                "synthetic selected physical fixture",
                "1",
                checks=(
                    CheckResult("compute", "pass", SCOPE),
                    CheckResult("rtl_netlist_correspondence", correspondence, SCOPE),
                ),
            )

    return report, factory, Copier(), PhysicalFixture(), candidate


@pytest.mark.parametrize(
    "status,passed", [("pass", True), ("unresolved", False), ("fail", False)]
)
def test_selected_physical_validation_requires_correspondence_and_exact_parent_link(
    tmp_path, status, passed
):
    report, factory, materializer, backend, parent = selected_fixture(
        tmp_path, correspondence=status
    )
    result = campaign.validate_selected_design(
        report,
        tmp_path,
        task_factory=factory,
        materializer=materializer,
        backend=backend,
    )
    assert result["passed"] is passed and backend.calls == 1
    assert result["parent_candidate_digest"] == parent.digest
    assert result["exact_input_hashes"]["core.v"] == file_sha256(
        Path(parent.root) / "core.v"
    )
    assert result["task_checker_differences"] == {
        "checker.py": dict(parent="a" * 64, physical="b" * 64)
    }
    link = json.loads(
        (
            tmp_path
            / "selected-physical/attempts/attempt-0001/candidate/parent-link.json"
        ).read_text()
    )
    assert link["parent_candidate_digest"] == parent.digest


def test_selected_physical_validation_cannot_replace_program_or_fallback(tmp_path):
    report, factory, materializer, backend, _ = selected_fixture(
        tmp_path, alter_program=True
    )
    with pytest.raises(ContractError, match="nominated RTL/configuration/program"):
        campaign.validate_selected_design(
            report,
            tmp_path,
            task_factory=factory,
            materializer=materializer,
            backend=backend,
        )
    assert backend.calls == 0


def test_missing_eligible_maximum_workload_nominee_never_uses_reference(tmp_path):
    report, factory, materializer, backend, _ = selected_fixture(tmp_path)
    report["final_test"][0]["campaign"]["observations"][0]["eligible"] = False
    report["comparison"][0]["arms"]["adapted"]["best"] = None
    result = campaign.validate_selected_design(
        report,
        tmp_path,
        task_factory=factory,
        materializer=materializer,
        backend=backend,
    )
    assert result["status"] == "not_run" and result["passed"] is False
    assert backend.calls == 0
    assert not (tmp_path / "selected-physical/attempts").exists()


def test_selected_design_nominates_best_adapted_slot_instead_of_first_eligible(
    tmp_path,
):
    from copy import deepcopy
    from dataclasses import asdict
    import shutil

    report, factory, _, backend, original = selected_fixture(tmp_path)
    slow_root = Path(original.root)
    fast_slot = tmp_path / "test/heldout/adapted/slot-001"
    fast_root = fast_slot / "attempts/attempt-0001/candidate"
    shutil.copytree(slow_root, fast_root)
    fast = replace(original, root=str(fast_root))
    (fast_slot / "events.jsonl").write_text(
        json.dumps(
            dict(
                event="candidate", candidate=asdict(fast), candidate_digest=fast.digest
            )
        )
        + "\n"
    )
    fast_run = deepcopy(report["final_test"][0])
    fast_run["slot"] = 1
    (slow_root / "core.v").write_text("synthetic slower RTL")
    slow = replace(
        original,
        candidate_id="serial_mul1",
        action=Action("serial_mul1"),
        artifacts=tuple(
            Artifact.from_file(slow_root, item.path) for item in original.artifacts
        ),
    )
    slow_run = report["final_test"][0]
    slow_observation = slow_run["campaign"]["observations"][0]
    slow_observation.update(
        action=asdict(slow.action),
        candidate_id=slow.candidate_id,
        candidate_digest=slow.digest,
    )
    slow_observation["receipt"].update(candidate_digest=slow.digest)
    slow_observation["receipt"]["metrics"]["cycles"]["value"] = 9
    (slow_root.parents[2] / "events.jsonl").write_text(
        json.dumps(
            dict(
                event="candidate", candidate=asdict(slow), candidate_digest=slow.digest
            )
        )
        + "\n"
    )
    report["final_test"].append(fast_run)

    class CopyBest:
        def materialize(self, task, action, workspace):
            child = workspace / "candidate"
            shutil.copytree(fast_root, child)
            assert action == Action("serial_mul2")
            return replace(
                fast, root=str(child), task_id=task.task_id, task_digest=task.digest
            )

    result = campaign.validate_selected_design(
        report, tmp_path, task_factory=factory, materializer=CopyBest(), backend=backend
    )
    assert result["passed"] is True
    assert result["parent_root"] == str(fast_root)
    assert result["nomination"]["best"]["action"] == "serial_mul2"
    assert result["nomination"]["best"]["value"] == 3
    assert result["exact_input_hashes"]["core.v"] == file_sha256(fast_root / "core.v")
    assert result["exact_input_hashes"]["core.v"] != file_sha256(slow_root / "core.v")


@pytest.mark.parametrize(
    "malformed",
    [
        "unknown_digest",
        "wrong_value",
        "wrong_action",
        "wrong_unit",
        "ineligible",
        "missing_receipt",
        "cached_receipt",
        "wrong_receipt_digest",
        "failed_required_check",
    ],
)
def test_selected_design_rejects_malformed_frozen_best_without_backend_or_fallback(
    tmp_path, malformed
):
    report, factory, materializer, backend, _ = selected_fixture(tmp_path)
    best = report["comparison"][0]["arms"]["adapted"]["best"]
    observation = report["final_test"][0]["campaign"]["observations"][0]
    if malformed == "unknown_digest":
        best["candidate_digest"] = "0" * 64
    elif malformed == "wrong_value":
        best["value"] = 1
    elif malformed == "wrong_action":
        best["action"] = "serial_mul1"
    elif malformed == "wrong_unit":
        best["unit"] = "seconds"
    elif malformed == "ineligible":
        observation["eligible"] = False
    elif malformed == "missing_receipt":
        observation["receipt"] = None
    elif malformed == "cached_receipt":
        observation["receipt"]["mode"] = "cached"
    elif malformed == "wrong_receipt_digest":
        observation["receipt"]["candidate_digest"] = "0" * 64
    else:
        observation["receipt"]["checks"][0]["status"] = "fail"
    with pytest.raises(ContractError, match="adapted best"):
        campaign.validate_selected_design(
            report,
            tmp_path,
            task_factory=factory,
            materializer=materializer,
            backend=backend,
        )
    assert backend.calls == 0
    assert not (tmp_path / "selected-physical/attempts").exists()
