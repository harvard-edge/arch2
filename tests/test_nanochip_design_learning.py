"""Check constructed semantic data, leakage boundaries, and actual model use."""

from collections import Counter
import importlib.util
import json

import pytest

from nanochip.laboratory.contracts import (
    Budget,
    CheckRequirement,
    ContractError,
    Task,
    file_sha256,
)
from nanochip.laboratory import design_learning as design
from nanochip.laboratory.models import load_model


def task_for(features, allowed=design.ACTIONS):
    return Task(
        "anonymous-design-test",
        tuple(allowed),
        (CheckRequirement("numerics", "constructed row transaction"),),
        specification={"design_features": features},
    )


@pytest.fixture
def corpus(tmp_path):
    return design.collect_design_examples(tmp_path / "corpus")


def test_semantic_corpus_partitions_and_disclosure(corpus):
    assert corpus["construction"] == "author_constructed_semantic_tasks"
    assert "not measured optimal PPA" in corpus["label_origin"]
    rows = corpus["records"]
    assert Counter(row["split"] for row in rows) == {"train": 32, "dev": 24, "test": 24}
    groups = {
        split: {row["group_id"] for row in rows if row["split"] == split}
        for split in ("train", "dev", "test")
    }
    assert not groups["train"] & (groups["dev"] | groups["test"])
    assert not groups["dev"] & groups["test"]
    assert len({row["input_text"] for row in rows}) == len(rows)
    assert all("n=256;" not in row["input_text"] for row in rows)
    for row in rows:
        assert all(action not in row["input_text"] for action in design.ACTIONS)
        assert all(
            action not in row["source_receipt"]["path"] for action in design.ACTIONS
        )
        assert len(row["input_text"].encode()) <= 128


def test_serializer_is_identity_free_and_uses_declared_facts(corpus):
    from pathlib import Path

    root = Path(corpus["manifest_path"]).parent
    first = json.loads(
        (root / corpus["records"][0]["source_receipt"]["path"]).read_text()
    )
    features = first["design_features"]
    expected = design.design_input(features)
    assert design.design_input(task_for(features)) == expected
    assert (
        design.design_input(
            first | {"target_action": "not-a-feature", "filename": "ignored"}
        )
        == expected
    )
    for key, replacement in (
        ("passes", 9),
        ("revisit", True),
        ("index_step", 3),
        ("reload_per_row", False),
        ("start_index", 1),
        ("access_order", "permuted"),
        ("row_values", 16),
    ):
        assert design.design_input(features | {key: replacement}) != expected
    with pytest.raises(ContractError, match="all declared"):
        design.design_input({})
    with pytest.raises(ContractError, match="four-bit"):
        design.design_input(features | {"quant_bits": 8})


def test_source_receipt_tamper_and_partition_reassignment_rejected(corpus, tmp_path):
    from pathlib import Path

    root = Path(corpus["manifest_path"]).parent
    source = root / corpus["records"][0]["source_receipt"]["path"]
    source.write_text(source.read_text() + " ")
    with pytest.raises(ContractError, match="content changed"):
        design.train_design_proposer(corpus, tmp_path / "bad")
    source.write_text(source.read_text()[:-1])
    corpus["records"][0]["split"] = "test"
    Path(corpus["manifest_path"]).write_text(json.dumps(corpus))
    with pytest.raises(ContractError, match="reassigned"):
        design.train_design_proposer(corpus, tmp_path / "bad-split")


@pytest.mark.skipif(
    importlib.util.find_spec("torch") is None, reason="optional CPU PyTorch unavailable"
)
def test_saved_model_is_actual_action_source_with_both_choices(
    corpus, tmp_path, monkeypatch
):
    from pathlib import Path

    report = design.train_design_proposer(
        corpus, tmp_path / "model", max_steps=45, max_seconds=20
    )
    assert report["training"]["parameters_changed"]
    assert report["training"]["final_loss"] < report["training"]["initial_loss"]
    assert report["training"]["device"] == "cpu"
    assert set(row["split"] for row in report["training"]["training_records"]) == {
        "train"
    }
    assert report["diagnostics"]["dev"]["record_count"] == 24
    assert report["diagnostics"]["test"]["record_count"] == 24
    for split in ("dev", "test"):
        assert report["diagnostics"][split]["majority_action"] == "retain_indexed_read"
        assert report["diagnostics"][split]["majority_action_accuracy"] == 0.875
    checkpoint = Path(report["checkpoint_dir"])
    assert file_sha256(checkpoint / "checkpoint.pt") == report["checkpoint_sha256"]
    first_source = (
        Path(corpus["manifest_path"]).parent
        / corpus["records"][0]["source_receipt"]["path"]
    )
    task = task_for(json.loads(first_source.read_text())["design_features"])

    def forbid_curator_at_inference(*args, **kwargs):
        raise AssertionError("Curator policy must never choose inference actions")

    monkeypatch.setattr(design, "_instructional_label", forbid_curator_at_inference)
    decoder = load_model(checkpoint, expected_model_io_contract=design.DESIGN_MODEL_IO)
    assert decoder.compatibility_mode == "bound"
    direct = decoder.predict(
        design.design_input(task), model_io_contract=design.DESIGN_MODEL_IO
    )
    proposer = design.design_proposer(checkpoint)
    action = proposer.propose(task, (), Budget(1, 1))
    assert action.name == direct["action"]
    assert (
        proposer.predictions[0]["action_probabilities"]
        == direct["action_probabilities"]
    )
    assert set(direct["action_probabilities"]) == set(design.ACTIONS)
    with pytest.raises(ContractError, match="both actions"):
        proposer.propose(
            task_for(task.specification["design_features"], (design.ACTIONS[0],)),
            (),
            Budget(1, 1),
        )
