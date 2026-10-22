"""Constructed fixtures test mechanics only; they supply no research metrics."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from nanochip.laboratory.contracts import (
    Action,
    Budget,
    CheckRequirement,
    ContractError,
    Task,
)
from nanochip.laboratory.models import LearnedProposer, load_model, train
from nanochip.laboratory.models.sequence import ACTION_OFFSET, EOS


HAS_TORCH = importlib.util.find_spec("torch") is not None
requires_torch = pytest.mark.skipif(
    not HAS_TORCH, reason="optional CPU PyTorch is not installed"
)


def fixture_row(index, text, action, split="train"):
    digest = hashlib.sha256(f"constructed-unit-fixture-{index}".encode()).hexdigest()
    return dict(
        record_id=f"fixture-{index}",
        group_id=f"fixture-group-{index}",
        split=split,
        input_text=text,
        target_action=action,
        source_receipt={"path": f"unit-fixture-{index}.json", "sha256": digest},
        source_sha256=digest,
        label_origin="constructed unit fixture, no empirical performance claim",
    )


@pytest.fixture
def tiny_checkpoint(tmp_path):
    if not HAS_TORCH:
        pytest.skip("optional CPU PyTorch is not installed")
    rows = [
        fixture_row(0, "check=numerics; status=fail", "repair"),
        fixture_row(1, "check=numerics; status=pass", "stop"),
    ]
    metadata = train(
        rows,
        tmp_path / "base",
        seed=7,
        max_steps=45,
        max_seconds=15,
        action_vocabulary=("repair", "stop"),
        embedding_dim=8,
        hidden_dim=16,
    )
    return tmp_path / "base", metadata, rows


def test_core_import_does_not_import_optional_torch():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import nanochip.laboratory.models; assert 'torch' not in sys.modules",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=os.environ.copy(),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@requires_torch
def test_real_parameter_update_reload_and_masked_loss(tiny_checkpoint):
    path, evidence, rows = tiny_checkpoint
    assert evidence["parameters_changed"]
    assert evidence["initial_parameter_sha256"] != evidence["final_parameter_sha256"]
    assert evidence["steps_completed"] == 45
    assert evidence["final_loss"] < evidence["initial_loss"]
    assert evidence["threads"] <= 2
    assert evidence["input_truncation"] is False
    first, second = load_model(path), load_model(path)
    for row in rows:
        a, b = first.predict(row["input_text"]), second.predict(row["input_text"])
        assert a["token_ids"] == b["token_ids"]
        assert a["action_probabilities"] == b["action_probabilities"]
        assert a["action"] in ("repair", "stop")
        assert a["token_ids"][1] == EOS
    assert first.parse_tokens([ACTION_OFFSET, EOS]) == "repair"
    with pytest.raises(ContractError, match="exactly one action"):
        first.parse_tokens([ACTION_OFFSET, 0])
    with pytest.raises(ContractError, match="forbidden"):
        first.parse_tokens([ACTION_OFFSET, EOS], allowed_actions=["stop"])
    with pytest.raises(ContractError, match="nonempty subset"):
        first.predict("unknown", allowed_actions=["injected_action"])


@requires_torch
def test_training_rejects_final_test_and_input_truncation(tmp_path):
    with pytest.raises(ContractError, match="only explicitly assigned train"):
        train([fixture_row(2, "test", "repair", "test")], tmp_path / "no-test")
    row = fixture_row(2, "retagged test", "repair")
    row["original_split"] = "test"
    with pytest.raises(ContractError, match="Final-test"):
        train([row], tmp_path / "no-retagged-test")
    with pytest.raises(ContractError, match="no truncation"):
        train(
            [fixture_row(3, "oversized", "repair")],
            tmp_path / "no-truncation",
            max_input_bytes=2,
        )
    assert not (tmp_path / "no-test").exists()
    assert not (tmp_path / "no-truncation").exists()


@requires_torch
def test_adaptation_starts_same_checkpoint_and_retains_ancestry(
    tiny_checkpoint, tmp_path
):
    path, evidence, rows = tiny_checkpoint
    fresh = fixture_row(2, "new development observation", "repair")
    adapted = train(
        [fresh],
        tmp_path / "adapted",
        base_checkpoint=path,
        max_steps=3,
        max_seconds=15,
        seed=8,
    )
    assert adapted["base_checkpoint_sha256"] == evidence["artifacts"]["checkpoint.pt"]
    assert adapted["initial_parameter_sha256"] == evidence["final_parameter_sha256"]
    assert adapted["parameters_changed"]
    assert adapted["update_record_ids"] == [fresh["record_id"]]
    decoder = load_model(tmp_path / "adapted")
    old_train = dict(rows[0], split="dev")
    with pytest.raises(ContractError, match="overlaps training"):
        decoder.evaluate([old_train])
    held_out = fixture_row(3, "unseen observation and group", "repair", "test")
    report = decoder.evaluate([held_out])
    assert report["record_count"] == 1
    assert report["split"] == "test"
    assert 0 <= report["exact_action_accuracy"] <= 1
    assert report["constrained_valid_rate"] == 1


@requires_torch
def test_checkpoint_tampering_rejected(tiny_checkpoint):
    path, _, _ = tiny_checkpoint
    config = json.loads((path / "config.json").read_text())
    config["hidden_dim"] += 1
    (path / "config.json").write_text(json.dumps(config))
    with pytest.raises(ContractError, match="content changed"):
        load_model(path)


@requires_torch
def test_proposer_selects_only_checkpoint_legal_actions(tiny_checkpoint):
    path, _, _ = tiny_checkpoint
    proposer = LearnedProposer(path, lambda task, history: "new fixture observation")
    task = Task("unit-fixture", ("repair",), (CheckRequirement("check", "fixture"),))
    action = proposer.propose(task, (), Budget(1, 1))
    assert action is None or action == Action("repair")
    assert len(proposer.predictions) == 1
    assert proposer.propose(task, (), Budget(0, 1)) is None
