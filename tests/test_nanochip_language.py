"""Actual byte learning, checkpoint reuse, and provenance boundaries on tiny fixtures."""

from dataclasses import replace
import hashlib
import importlib.util
import json

import pytest

from nanochip.laboratory.contracts import Budget, CheckRequirement, ContractError, Task
from nanochip.laboratory.model_io import ModelIOContract
from nanochip.laboratory.models import language

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("torch") is None,
    reason="optional CPU PyTorch is not installed",
)


def contract():
    return ModelIOContract(
        "unit.architecture-text",
        1,
        "unit.status.v1",
        ("inspect_memory", "keep_reference"),
        128,
    )


def row(index, text="cache cache cache\n", *, split="train", **changes):
    digest = hashlib.sha256(f"language-fixture:{index}".encode()).hexdigest()
    return dict(
        record_id=f"language-{index}",
        group_id=f"source-{index}",
        split=split,
        original_split=split,
        input_text=text,
        source_sha256=digest,
        source_receipt=dict(path=f"fixture-{index}.json", sha256=digest),
        data_origin="constructed",
        label_origin="constructed unit fixture",
        **changes,
    )


@pytest.fixture(scope="module")
def checkpoint(tmp_path_factory):
    root = tmp_path_factory.mktemp("byte-lm") / "base"
    metadata = language.train(
        [row(0)],
        root,
        model_io_contract=contract(),
        max_steps=25,
        max_seconds=30,
        learning_rate=0.02,
        embedding_dim=4,
        hidden_dim=8,
    )
    return root, metadata


def test_pretraining_loss_covers_all_text_bytes_and_eos(checkpoint):
    path, evidence = checkpoint
    assert evidence["objective"] == "pretrain"
    assert evidence["loss_scope"] == "all text bytes and EOS"
    assert evidence["loss_tokens"] == len(row(0)["input_text"].encode()) + 1
    assert evidence["parameters_changed"]
    assert evidence["final_loss"] < evidence["initial_loss"]
    assert evidence["threads"] == 1
    assert evidence["steps_completed"] == 25
    tokenizer = json.loads((path / "tokenizer.json").read_text())
    assert tokenizer["vocab_size"] == 259
    assert "actions" not in tokenizer
    model = language.load_model(path, expected_model_io_contract=contract())
    a = model.predict("status=stall", model_io_contract=contract())
    b = language.load_model(path).predict("status=stall", model_io_contract=contract())
    assert a["continuation_log_probabilities"] == b["continuation_log_probabilities"]
    assert a["action"] in contract().actions


def test_supervised_adaptation_reuses_weights_and_scores_byte_continuations(
    checkpoint, tmp_path
):
    path, evidence = checkpoint
    sample = row(1, "status=stall\naction=", target_action="inspect_memory")
    adapted = language.train(
        [sample],
        tmp_path / "adapted",
        model_io_contract=contract(),
        objective="supervised",
        base_checkpoint=path,
        max_steps=3,
        max_seconds=30,
    )
    assert adapted["initial_parameter_sha256"] == evidence["final_parameter_sha256"]
    assert adapted["base_checkpoint_sha256"] == evidence["artifacts"]["checkpoint.pt"]
    assert adapted["loss_tokens"] == len(sample["target_action"].encode()) + 1
    assert adapted["parameters_changed"]
    model = language.load_model(tmp_path / "adapted")
    prediction = model.predict(sample["input_text"], model_io_contract=contract())
    torch = language._torch()
    for action in contract().actions:
        x, y = language._batch(
            [dict(input_text=sample["input_text"], target_action=action)],
            "supervised",
            torch,
        )
        with torch.no_grad():
            logits, _ = model.model(x)
            score = -float(
                torch.nn.functional.cross_entropy(
                    logits.flatten(0, 1),
                    y.flatten(),
                    ignore_index=-100,
                    reduction="sum",
                )
            )
        assert prediction["continuation_log_probabilities"][action] == pytest.approx(
            score
        )
    assert sum(prediction["action_probabilities"].values()) == pytest.approx(1)
    report = model.evaluate(
        [
            row(
                2,
                "status=unseen\naction=",
                split="test",
                target_action="keep_reference",
            )
        ],
        model_io_contract=contract(),
        objective="supervised",
    )
    assert report["loss_tokens"] > 1
    assert report["byte_next_token_nll"] > 0
    assert report["byte_perplexity"] > 1
    assert len(report["predictions"]) == 1
    assert report["training_majority_action"] == "inspect_memory"
    assert report["training_majority_action_accuracy"] == 0
    assert report["target_action_counts"] == {"keep_reference": 1}
    assert sum(report["predicted_action_counts"].values()) == 1
    assert report["per_action_accuracy"]["inspect_memory"] is None


def test_feedback_update_preserves_measured_origin_and_all_ancestors(
    checkpoint, tmp_path
):
    path, evidence = checkpoint
    measured = row(3, "area=12;checks=pass;action=", target_action="keep_reference")
    measured.update(
        data_origin="measured",
        original_split="development",
        label_origin="constructed test fixture of measured-feedback admission",
    )
    # This fixture verifies the update mechanism. It is not a real tool measurement.
    adapted = language.train(
        [measured],
        tmp_path / "feedback",
        model_io_contract=contract(),
        objective="supervised",
        base_checkpoint=path,
        max_steps=2,
        max_seconds=30,
    )
    assert adapted["data_origin_counts"] == {"measured": 1}
    assert {r["record_id"] for r in adapted["training_records"]} == {
        "language-0",
        "language-3",
    }
    assert adapted["initial_parameter_sha256"] == evidence["final_parameter_sha256"]
    decoder = language.load_model(tmp_path / "feedback")
    with pytest.raises(ContractError, match="overlaps training lineage"):
        decoder.evaluate(
            [dict(measured, split="dev")],
            model_io_contract=contract(),
            objective="supervised",
        )


@pytest.mark.parametrize(
    "key", ["record_id", "group_id", "source_sha256", "input_text", "receipt"]
)
def test_heldout_overlap_is_rejected_across_checkpoint_lineage(checkpoint, key):
    path, _ = checkpoint
    original = row(0)
    held = row(5, "independent text", split="test")
    if key == "receipt":
        held["source_receipt"] = original["source_receipt"]
    else:
        held[key] = original[key]
    with pytest.raises(ContractError, match="overlaps training lineage"):
        language.load_model(path).evaluate([held], model_io_contract=contract())


def test_final_test_and_representation_changes_cannot_update(checkpoint, tmp_path):
    path, _ = checkpoint
    held = row(5, split="test")
    with pytest.raises(ContractError, match="final test cannot be retagged"):
        language.train([held], tmp_path / "test", model_io_contract=contract())
    held["split"] = "train"
    with pytest.raises(ContractError, match="final test cannot be retagged"):
        language.train([held], tmp_path / "retagged", model_io_contract=contract())
    changed = replace(contract(), serializer_id="other")
    with pytest.raises(ContractError, match="contract mismatch"):
        language.train(
            [row(5)],
            tmp_path / "changed",
            model_io_contract=changed,
            base_checkpoint=path,
        )
    assert not (tmp_path / "changed").exists()


def test_rejects_input_drift_and_illegal_actions_before_inference(
    checkpoint, monkeypatch
):
    path, _ = checkpoint
    model = language.load_model(path)

    def forbidden(*args, **kwargs):
        pytest.fail("invalid input reached neural model")

    monkeypatch.setattr(model.model, "forward", forbidden)
    with pytest.raises(ContractError, match="contract mismatch"):
        model.predict("state", model_io_contract=replace(contract(), schema_version=2))
    with pytest.raises(ContractError, match="no truncation"):
        model.predict("é" * 65, model_io_contract=contract())
    with pytest.raises(ContractError, match="legal actions"):
        model.predict(
            "state", model_io_contract=contract(), allowed_actions=["invented"]
        )


def test_proposer_adapts_scoring_to_shared_harness(checkpoint):
    path, _ = checkpoint
    proposer = language.LanguageProposer(
        path,
        lambda task, history: task.specification["text"],
        model_io_contract=contract(),
    )
    task = Task(
        "language-case",
        ("inspect_memory",),
        (CheckRequirement("functional", "unit"),),
        specification={"text": "status=stall"},
    )
    assert proposer.propose(task, (), Budget(1, 1)).name == "inspect_memory"
    assert proposer.predictions[-1]["checkpoint_sha256"]
    assert proposer.propose(task, (), Budget(0, 1)) is None


def test_checkpoint_hashes_and_custom_model_identity(checkpoint, tmp_path):
    path, _ = checkpoint
    custom = tmp_path / "custom"
    language.train(
        [row(9)],
        custom,
        model_io_contract=contract(),
        max_steps=1,
        max_seconds=30,
        model_factory=language.build_model,
        architecture_id="student-byte-gru/v1",
        embedding_dim=4,
        hidden_dim=8,
    )
    with pytest.raises(ContractError, match="explicit model factory"):
        language.load_model(custom)
    assert (
        language.load_model(
            custom, model_factory=language.build_model
        ).model_io_contract
        == contract()
    )
    with (custom / "config.json").open("a") as stream:
        stream.write(" ")
    with pytest.raises(ContractError, match="content changed"):
        language.load_model(custom, model_factory=language.build_model)
