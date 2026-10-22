from pathlib import Path
import json
import hashlib

import pytest

from nanochip.laboratory.contracts import (
    Action,
    Artifact,
    Candidate,
    CheckRequirement,
    ContractError,
    CheckResult,
    Cost,
    Metric,
    RunReceipt,
    Task,
    file_sha256,
)
from nanochip.laboratory.course.composition import (
    ArchitectureMaterializer,
    ReceiptAdapterBackend,
    RepresentationAdapter,
    SearchPolicyAdapter,
    WeightCodecMaterializer,
    assess_reused_physical_acceptance,
    interpret_physical_receipt,
)


class _Trainer:
    def build_model(self, *args, **kwargs):
        return object()


class _Representation:
    def serialize(self, task, history):
        return f"{task.task_id}:{len(history)}"

    def retrieve(self, query, documents, limit):
        return list(documents[:1])

    def parse_action(self, text, actions):
        return text


class _Search:
    def predict(self, task, candidate):
        return {
            "metrics": {"cycles": {"value": 12, "unit": "cycles", "uncertainty": 2}}
        }

    def choose(self, task, proposals, history, budget):
        return proposals[-1]


class _Learner:
    def propose(self, task, history, budget):
        return Action(task.allowed_actions[0])


def _task():
    return Task(
        "composition-test",
        ("a", "b"),
        (CheckRequirement("identity", "test-scope"),),
        specification={"case": 1},
    )


def test_lab5_adapter_uses_student_serializer_and_bounds_retrieval():
    adapter = RepresentationAdapter(_Representation())
    task = _task()
    text = "trusted source text"
    docs = tuple(
        {
            "source_id": f"doc-{i}",
            "partition": "train",
            "text": text,
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "source": f"source-{i}",
            "file_sha256": f"{i:064x}",
        }
        for i in range(2)
    )
    assert adapter.serialize(task) == "composition-test:0"
    assert adapter.retrieve(task, (), docs, 3) == (docs[0],)

    class Leaky(_Representation):
        def retrieve(self, query, documents, limit):
            return ({"source_id": "not-permitted"},)

    with pytest.raises(ContractError, match="forged or unapproved"):
        RepresentationAdapter(Leaky()).retrieve(task, (), docs, 1)

    class Mutated(_Representation):
        def retrieve(self, query, documents, limit):
            item = dict(documents[0], text="forged text", text_sha256="0" * 64)
            return (item,)

    with pytest.raises(ContractError, match="content hash"):
        RepresentationAdapter(Mutated()).retrieve(task, (), docs, 20)

    class OverBudget(_Representation):
        def retrieve(self, query, documents, limit):
            return (documents[0],)

    long_source = "one two three four five"
    long_document = dict(
        docs[0],
        text=long_source,
        text_sha256=hashlib.sha256(long_source.encode()).hexdigest(),
    )
    with pytest.raises(ContractError, match="word budget"):
        RepresentationAdapter(OverBudget()).retrieve(task, (), (long_document,), 3)


def test_capstone_context_selection_fits_exact_composed_utf8_envelope():
    from nanochip.laboratory.model_io import ModelIOContract

    task = _task()
    contract = ModelIOContract("test", 1, "serializer-v1", ("a", "b"), 180)
    text = "λ" * 120
    docs = (
        {
            "source_id": "x" * 200,
            "partition": "train",
            "text": text,
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "source": "source",
            "file_sha256": "1" * 64,
        },
        {
            "source_id": "short",
            "partition": "train",
            "text": "measured cycles",
            "text_sha256": hashlib.sha256(b"measured cycles").hexdigest(),
            "source": "source2",
            "file_sha256": "2" * 64,
        },
    )

    class Retrieved(_Representation):
        def retrieve(self, query, documents, limit):
            return tuple(documents)

    adapter = RepresentationAdapter(Retrieved(), contract)
    selected = adapter.retrieve(task, (), docs, 20)
    composed = adapter.serialize(task, (), selected)
    assert len(composed.encode("utf-8")) <= contract.max_input_bytes
    assert [item["source_id"] for item in selected] == ["short"]
    assert (
        adapter.last_context_selection["omitted"][0]["reason"]
        == "complete_composed_input_exceeds_model_byte_envelope"
    )
    assert selected[0]["selection"] == "included_in_model_input"


def test_lab6_policy_wraps_learned_proposal_and_validates_predictions(tmp_path):
    adapter = SearchPolicyAdapter(_Search())
    chosen = adapter.proposer(_Learner(), _Representation().parse_action).propose(
        _task(), (), object()
    )
    assert chosen == Action("b")

    root = tmp_path / "candidate"
    root.mkdir()
    (root / "core.v").write_text("module core; endmodule\n")
    candidate = Candidate(
        "b",
        "composition-test",
        str(root),
        Action("b"),
        (Artifact.from_file(root, "core.v"),),
        task_digest=_task().digest,
    )
    assert (
        adapter.observe_candidate(_task(), candidate)["metrics"]["cycles"]["value"]
        == 12
    )
    assert candidate.digest in adapter.predictions

    class Bad(_Search):
        def choose(self, task, proposals, history, budget):
            return Action("illegal")

    with pytest.raises(ContractError, match="legal action"):
        SearchPolicyAdapter(Bad()).proposer(
            _Learner(), _Representation().parse_action
        ).propose(_task(), (), object())


def test_lab7_transform_is_applied_to_candidate_and_rehashes_artifacts(tmp_path):
    class Base:
        def materialize(self, task, action, workspace):
            root = Path(workspace) / "candidate"
            root.mkdir(parents=True)
            (root / "core.v").write_text("// baseline\n")
            (root / "task.json").write_text(task.task_id)
            return Candidate(
                action.name,
                task.task_id,
                str(root),
                action,
                tuple(
                    Artifact.from_file(root, name) for name in ("core.v", "task.json")
                ),
                task_digest=task.digest,
            )

    class Architecture:
        def transform(self, source, action):
            return source + f"// lab7:{action.name}\n"

    task = _task()
    result = ArchitectureMaterializer(Base(), Architecture()).materialize(
        task, Action("a"), tmp_path / "work"
    )
    assert Path(result.root, "core.v").read_text().endswith("// lab7:a\n")
    result.validate_files()
    assert result.digest != ""
    assert next(
        item for item in result.artifacts if item.path == "core.v"
    ).sha256 == file_sha256(Path(result.root, "core.v"))


def test_lab2_codec_rechecks_every_q4_tensor_in_fresh_candidate_image(tmp_path):
    from nanochip.laboratory.course.reference import lab02_representation
    from nanochip.laboratory.teaching_core import TeachingCoreMaterializer, make_task

    task = make_task(seed=13, prompt_index=0)
    codec = WeightCodecMaterializer(TeachingCoreMaterializer(), lab02_representation)
    candidate = codec.materialize(task, Action("serial_mul1"), tmp_path / "slot")
    candidate.validate_files()
    evidence = json.loads((tmp_path / "slot/lab2-weight-codec.json").read_text())
    assert evidence["task_digest"] == task.digest
    assert evidence["candidate_digest_after_codec"] == candidate.digest
    assert (
        evidence["source_weight_image_sha256"]
        == evidence["materialized_weight_image_sha256"]
    )
    assert all(
        row["oracle_match"] and row["unpack_match"] for row in evidence["tensors"]
    )
    assert any(row["tensor"] == "emb.q" for row in evidence["tensors"])


def test_lab8_interpreter_binds_receipt_to_exact_candidate_source(tmp_path):
    from nanochip.laboratory.course.reference.lab08_physical import (
        summarize_physical_receipt,
    )

    core = tmp_path / "core.v"
    core.write_text("module core; endmodule\n")
    digest = file_sha256(core)
    raw = {
        "candidate_sha256": "manifest-digest",
        "source_manifest": [{"path": "core.v", "sha256": digest}],
        "status": "completed",
        "ok": True,
        "receipt_sha256": "receipt-id",
        "checks": [{"name": "timing", "status": "pass", "scope": "core"}],
    }
    result = interpret_physical_receipt(
        type(
            "C",
            (),
            {"summarize_physical_receipt": staticmethod(summarize_physical_receipt)},
        ),
        raw,
        core,
    )
    assert result["candidate_core_sha256"] == digest
    assert result["physical_candidate_sha256"] == "manifest-digest"
    assert result["interpreted_checks"]["all_required_passed"] is True
    raw["source_manifest"][0]["sha256"] = "0" * 64
    with pytest.raises(ContractError):
        interpret_physical_receipt(
            type(
                "C",
                (),
                {
                    "summarize_physical_receipt": staticmethod(
                        summarize_physical_receipt
                    )
                },
            ),
            raw,
            core,
        )

    failed_raw = {
        "candidate_sha256": "manifest-digest",
        "source_manifest": [{"path": "core.v", "sha256": digest}],
        "status": "success",
        "ok": False,
        "checks": [{"name": "timing", "status": "fail", "scope": "core"}],
    }

    class LyingPhysical:
        @staticmethod
        def summarize_physical_receipt(raw, candidate_sha256):
            return {
                "candidate_sha256": candidate_sha256,
                "checks": raw["checks"],
                "all_required_passed": True,
            }

    with pytest.raises(ContractError, match="changed named checks"):
        interpret_physical_receipt(LyingPhysical, failed_raw, core)


def test_lab9_reuses_physical_evidence_only_for_same_action_config_and_netlist_check(
    tmp_path,
):
    config = tmp_path / "physical-config.json"
    config.write_text('{"clock": 100}\n')
    winner = {
        "case_id": "heldout-a",
        "task_digest": "task",
        "candidate_digest": "candidate",
        "action": "serial_mul2",
        "core_sha256": "core-hash",
        "config_sha256": file_sha256(config),
        "program_sha256": "program",
        "tables_sha256": "tables",
        "image_sha256": "image",
    }
    raw = {"config_sha256": file_sha256(config)}
    interpreted = {
        "candidate_core_sha256": "core-hash",
        "interpreted_checks": {"all_required_passed": True},
    }
    mapped = {
        "case_id": "heldout-a",
        "status": "pass",
        "mode": "fresh",
        "mapped_netlist_sha256": "netlist",
        "functional_golden_sha256": "golden",
        "receipt_sha256": "mapped-receipt",
        **{
            key: winner[key]
            for key in (
                "task_digest",
                "candidate_digest",
                "core_sha256",
                "config_sha256",
                "program_sha256",
                "tables_sha256",
                "image_sha256",
            )
        },
    }
    accepted = assess_reused_physical_acceptance(
        adapted_actions=("serial_mul2",),
        physical_action="serial_mul2",
        candidate_config=config,
        raw_receipt=raw,
        interpreted=interpreted,
        receipt_sha256="receipt-hash",
        adapted_winners=(winner,),
        mapped_workload_receipt=mapped,
    )
    assert accepted["status"] == "accepted_by_reused_lab8_evidence"
    assert accepted["checks"]["same_physical_config"] is True
    mismatched = assess_reused_physical_acceptance(
        adapted_actions=("serial_mul1",),
        physical_action="serial_mul2",
        candidate_config=config,
        raw_receipt=raw,
        interpreted=interpreted,
        receipt_sha256="receipt-hash",
        adapted_winners=(winner,),
        mapped_workload_receipt=mapped,
    )
    assert mismatched["status"] == "pending_final_physical"
    changed_rtl = dict(winner, core_sha256="other-core")
    mismatch_rtl = assess_reused_physical_acceptance(
        adapted_actions=("serial_mul2",),
        physical_action="serial_mul2",
        candidate_config=config,
        raw_receipt=raw,
        interpreted=interpreted,
        receipt_sha256="receipt-hash",
        adapted_winners=(changed_rtl,),
        mapped_workload_receipt=mapped,
    )
    assert mismatch_rtl["checks"]["same_winner_core"] is False
    assert mismatch_rtl["status"] == "pending_final_physical"
    unresolved = dict(raw)
    pending = assess_reused_physical_acceptance(
        adapted_actions=("serial_mul2",),
        physical_action="serial_mul2",
        candidate_config=config,
        raw_receipt=unresolved,
        interpreted=interpreted,
        receipt_sha256="receipt-hash",
        adapted_winners=(winner,),
        mapped_workload_receipt=None,
    )
    assert pending["checks"]["fresh_mapped_netlist_workload_pass"] is False


def test_lab3_receipt_adapter_cannot_change_backend_evidence_in_place(tmp_path):
    task = _task()
    root = tmp_path / "candidate"
    root.mkdir()
    (root / "core.v").write_text("module core; endmodule\n")
    candidate = Candidate(
        "a",
        task.task_id,
        str(root),
        Action("a"),
        (Artifact.from_file(root, "core.v"),),
        task_digest=task.digest,
    )
    raw = RunReceipt(
        task.task_id,
        candidate.digest,
        "fresh",
        "error",
        "backend",
        "1",
        checks=(CheckResult("identity", "fail", "test-scope"),),
        metrics={"cycles": Metric(3, "cycles", "test-scope")},
        cost=Cost(0.25),
    )

    class Backend:
        def evaluate(self, task, candidate):
            return raw

    class LyingParser:
        def adapt_receipt(self, value, task, candidate):
            value["execution_status"] = "success"
            value["checks"][0]["status"] = "pass"
            return RunReceipt(
                value["task_id"],
                value["candidate_digest"],
                value["mode"],
                value["execution_status"],
                value["tool"],
                value["tool_version"],
                tuple(CheckResult(**item) for item in value["checks"]),
                {key: Metric(**item) for key, item in value["metrics"].items()},
                Cost(**value["cost"]),
                value["details"],
                value["output_root"],
                (),
            )

    with pytest.raises(ContractError, match="changed backend evidence"):
        ReceiptAdapterBackend(Backend(), LyingParser()).evaluate(task, candidate)


def test_course_training_adaptation_segments_measurement_text_without_loss(tmp_path):
    from nanochip.laboratory.model_io import ModelIOContract
    from nanochip.laboratory.course.composition import TrainingAdapter

    contract = ModelIOContract("test", 1, "serializer-v1", ("a", "b"), 64)
    base = tmp_path / "base"
    base.mkdir()
    (base / "checkpoint.pt").write_bytes(b"base")
    prior_record = {"record_id": "prior", "input_text": "prior source"}
    (base / "training.json").write_text(
        json.dumps(
            {
                "final_parameter_sha256": "base-params",
                "training_records": [prior_record],
            }
        )
    )
    calls = []

    class Trainer:
        def build_model(self, *args, **kwargs):
            return object()

        def train(self, records, output, **kwargs):
            rows = list(records)
            calls.append((kwargs["objective"], rows))
            output.mkdir(parents=True, exist_ok=True)
            (output / "checkpoint.pt").write_bytes(b"updated")
            previous = json.loads(
                (kwargs["base_checkpoint"] / "training.json").read_text()
            )
            metadata = {
                "parameters_changed": True,
                "steps_completed": 1,
                "base_checkpoint_sha256": file_sha256(
                    kwargs["base_checkpoint"] / "checkpoint.pt"
                ),
                "initial_parameter_sha256": previous["final_parameter_sha256"],
                "final_parameter_sha256": "updated-params",
                "training_records": previous["training_records"] + rows,
            }
            (output / "training.json").write_text(json.dumps(metadata))
            return metadata

    adapter = TrainingAdapter(Trainer(), contract, base_checkpoint=base)
    long_text = "λ" * 80
    rows = (
        {"record_id": "measurement", "input_text": long_text},
        {"record_id": "label", "input_text": "prompt", "target_action": "a"},
    )
    result = adapter.adapt(rows, base, tmp_path / "adapted")
    chunks = calls[0][1]
    assert all(
        len(row["input_text"].encode("utf-8")) <= contract.max_input_bytes
        for row in chunks
    )
    assert "".join(row["input_text"] for row in chunks) == long_text
    assert all(
        row["source_receipt"] if "source_receipt" in row else True for row in chunks
    )
    assert result["text_segmentation"]["segmented_record_count"] == len(chunks)


def test_reference_lab5_serializer_compacts_history_within_contract(tmp_path):
    from nanochip.laboratory.course.reference.lab05_inference import serialize
    from nanochip.laboratory.model_io import ModelIOContract
    from nanochip.laboratory.teaching_core.backend import make_task, ACTIONS
    from nanochip.laboratory.contracts import Observation

    task = make_task(seed=17, prompt_index=0, split="development", tokens=[1])
    task = Task(
        task.task_id,
        task.allowed_actions,
        task.required_checks,
        task.max_proposals,
        task.max_attempts,
        dict(
            task.specification,
            campaign_objective={
                "metric": "cycles",
                "scope": "accelerator:nanochip_teaching_core",
                "minimize": True,
                "unit": "cycles",
            },
        ),
    )
    history = []
    for index in range(12):
        action = Action(ACTIONS[index % len(ACTIONS)])
        receipt = RunReceipt(
            task.task_id,
            f"{index:064x}",
            "fresh",
            "success",
            "sim",
            "1",
            checks=tuple(
                CheckResult(
                    name,
                    "fail" if index == 11 and name == "exact_argmax" else "pass",
                    "accelerator:nanochip_teaching_core",
                )
                for name in (
                    "exact_integer_logits",
                    "exact_argmax",
                    "float_numerical",
                    "protocol",
                    "runtime_program",
                    "reset_latency_independence",
                )
            ),
            metrics={
                "cycles": Metric(
                    float(100 + index), "cycles", "accelerator:nanochip_teaching_core"
                )
            },
            cost=Cost(1.0),
        )
        history.append(
            Observation(
                action,
                action.name,
                receipt.candidate_digest,
                "success",
                receipt.checks,
                True,
                receipt=receipt,
            )
        )
    text = serialize(task, history)
    assert any(row[-1] for row in json.loads(text)["h"])
    contract = ModelIOContract(
        "nanochip_teaching_core_workload",
        1,
        "nanochip.course.task_json.v3",
        tuple(ACTIONS),
        768,
    )
    contract.validate_text(text)


def test_lab9_comparison_must_retain_all_matched_measurements_and_costs():
    from copy import deepcopy
    from nanochip.laboratory.course.checks import _execute_student_comparison
    from nanochip.laboratory.course.reference.lab09_evaluate import compare_campaigns

    group = "heldout-group"
    objective = {
        "metric": "cycles",
        "scope": "accelerator:nanochip_teaching_core",
        "minimize": True,
        "unit": "cycles",
    }
    best = {
        "action": "serial_mul2",
        "candidate_digest": "a" * 64,
        "scope": objective["scope"],
        "unit": "cycles",
        "value": 123,
    }
    case = {
        "case_id": "case-1",
        "group_id": group,
        "objective": objective,
        "candidate_budget": 2,
        "outcomes": [{"eligible": True, "receipt": None}],
        "best": best,
        "attempt_cost": {"attempt_wall_seconds": 3.0},
        "tool_receipt_cost": None,
    }
    methods = ("adapted", "unadapted", "enumeration", "constant")
    summaries = [
        {
            "method": name,
            "groups": [group],
            "objective": objective,
            "candidate_budget": 2,
            "cases": [deepcopy(case)],
            "attempt_cost": {"attempt_wall_seconds": 3.0},
            "tool_receipt_cost": None,
        }
        for name in methods
    ]
    campaign_cost = {"initial_training_wall_seconds": 5.0}
    expected_case = {
        "case_id": "case-1",
        "group_id": group,
        "objective": objective,
        "candidate_budget": 2,
        "outcome_count": 1,
        "eligible_count": 1,
        "best": best,
        "attempt_cost": {"attempt_wall_seconds": 3.0},
        "tool_receipt_cost": None,
    }
    expected = {
        name: {
            "method": name,
            "groups": [group],
            "objective": objective,
            "candidate_budget": 2,
            "outcome_count": 1,
            "eligible_count": 1,
            "cases": [deepcopy(expected_case)],
            "attempt_cost": {"attempt_wall_seconds": 3.0},
            "tool_receipt_cost": None,
        }
        for name in methods
    }
    good = compare_campaigns(
        summaries, evaluation_groups=[group], campaign_cost=campaign_cost
    )
    assert _execute_student_comparison(
        type(
            "Good",
            (),
            {"compare_campaigns": staticmethod(lambda *_args, **_kwargs: good)},
        )(),
        summaries,
        [group],
        expected,
        campaign_cost,
    )

    bad_results = [{}]
    missing_method = deepcopy(good)
    missing_method["methods"] = [
        row for row in missing_method["methods"] if row["method"] != "constant"
    ]
    bad_results.append(missing_method)
    wrong_unit = deepcopy(good)
    wrong_unit["methods"][0]["cases"][0]["best"]["unit"] = "ns"
    bad_results.append(wrong_unit)
    wrong_best = deepcopy(good)
    wrong_best["methods"][0]["cases"][0]["best"]["candidate_digest"] = "b" * 64
    bad_results.append(wrong_best)
    promoted_cost = deepcopy(good)
    promoted_cost["methods"][0]["attempt_cost"]["attempt_wall_seconds"] = 30.0
    bad_results.append(promoted_cost)
    changed_campaign_cost = deepcopy(good)
    changed_campaign_cost["campaign_cost"]["initial_training_wall_seconds"] = 30.0
    bad_results.append(changed_campaign_cost)
    additive_cost_claim = deepcopy(good)
    additive_cost_claim["cost_allocation"][
        "method_costs"
    ] = "additive_to_campaign_total"
    bad_results.append(additive_cost_claim)
    for bad in bad_results:
        with pytest.raises(ContractError):
            _execute_student_comparison(
                type(
                    "Bad",
                    (),
                    {
                        "compare_campaigns": staticmethod(
                            lambda *_args, result=bad, **_kwargs: result
                        )
                    },
                )(),
                summaries,
                [group],
                expected,
                campaign_cost,
            )

    class Mutating:
        @staticmethod
        def compare_campaigns(rows, **kwargs):
            rows[0]["cases"][0]["best"]["value"] = 999999
            return good

    with pytest.raises(ContractError, match="mutated"):
        _execute_student_comparison(
            Mutating(), summaries, [group], expected, campaign_cost
        )


def test_lab9_comparison_inputs_keep_per_case_units_counts_and_all_arm_costs():
    from nanochip.laboratory.course.checks import (
        _comparison_inputs,
        _execute_student_comparison,
    )
    from nanochip.laboratory.course.reference.lab09_evaluate import compare_campaigns

    objective = {
        "metric": "cycles",
        "scope": "accelerator:nanochip_teaching_core",
        "minimize": True,
        "unit": "cycles",
    }
    arms = ("adapted", "unadapted", "enumeration", "constant")
    case = {
        "case_id": "heldout-case",
        "group_id": "heldout-group",
        "objective": objective,
        "arms": {
            name: {
                "best": {
                    "action": "serial_mul2",
                    "candidate_digest": name,
                    "scope": objective["scope"],
                    "unit": "cycles",
                    "value": 10,
                }
            }
            for name in arms
        },
    }
    final_test = [
        {
            "case_id": case["case_id"],
            "case_group": case["group_id"],
            "arm": name,
            "campaign": {
                "observations": [
                    {
                        "eligible": True,
                        "action": "serial_mul2",
                        "status": "success",
                        "candidate_digest": name,
                    }
                ]
            },
            "cost": {"attempt_wall_seconds": 2.0, "proposal_wall_seconds": 0.1},
        }
        for name in arms
    ]
    campaign = {
        "comparison": [case],
        "final_test": final_test,
        "objective": objective,
        "cost": {"initial_training_wall_seconds": 5.0},
    }
    summaries, groups, expected, campaign_cost = _comparison_inputs(
        campaign, candidate_budget=2
    )
    assert groups == ["heldout-group"]
    assert len(summaries) == 4
    for item in summaries:
        assert item["objective"]["unit"] == "cycles"
        assert item["candidate_budget"] == 2
        assert item["cases"][0]["group_id"] == "heldout-group"
        assert item["cases"][0]["outcomes"][0]["eligible"] is True
        assert item["attempt_cost"] == {
            "attempt_wall_seconds": 2.0,
            "proposal_wall_seconds": 0.1,
        }
    result = compare_campaigns(
        summaries, evaluation_groups=groups, campaign_cost=campaign_cost
    )
    _execute_student_comparison(
        type(
            "Student",
            (),
            {"compare_campaigns": staticmethod(lambda *_args, **_kwargs: result)},
        )(),
        summaries,
        groups,
        expected,
        campaign_cost,
    )
