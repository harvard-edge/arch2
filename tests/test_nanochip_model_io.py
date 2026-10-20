"""Representation changes must be declared before a checkpoint can act on them.

These tiny constructed examples verify composition, not model quality.
"""

from dataclasses import replace
import hashlib
import importlib.util
import json
import shutil

import pytest

from nanochip.laboratory.contracts import Budget, CheckRequirement, ContractError, Task, file_sha256
from nanochip.laboratory.model_io import ModelIOContract
from nanochip.laboratory.models import LearnedProposer, load_model, train
from nanochip.laboratory.models import sequence


requires_torch = pytest.mark.skipif(importlib.util.find_spec("torch") is None,
                                     reason="optional CPU PyTorch is not installed")


def contract(**changes):
    return replace(ModelIOContract("unit.observation", 1, "unit.serialize.v1",
                                   ("inspect", "stop"), 64), **changes)


def row(index, text, action="inspect", split="train"):
    digest = hashlib.sha256(f"constructed-model-io-{index}".encode()).hexdigest()
    return dict(record_id=f"io-{index}", group_id=f"io-group-{index}", split=split,
                input_text=text, target_action=action, source_sha256=digest,
                source_receipt={"path": f"io-{index}.json", "sha256": digest},
                label_origin="constructed unit fixture")


@pytest.fixture(scope="module")
def bound_checkpoint(tmp_path_factory):
    if importlib.util.find_spec("torch") is None:
        pytest.skip("optional CPU PyTorch is not installed")
    path = tmp_path_factory.mktemp("model-io") / "checkpoint"
    metadata = train([row(0, "status=fail"), row(1, "status=pass", "stop")], path,
                     model_io_contract=contract(), max_steps=3, max_seconds=30,
                     embedding_dim=4, hidden_dim=8)
    return path, metadata


def test_contract_roundtrip_and_utf8_byte_budget():
    declared = contract(max_input_bytes=4)
    assert ModelIOContract.from_dict(json.loads(json.dumps(declared.to_dict()))) == declared
    assert declared.digest == ModelIOContract.from_dict(declared.to_dict()).digest
    assert declared.validate_text("éé") == b"\xc3\xa9\xc3\xa9"
    with pytest.raises(ContractError, match="no truncation"):
        declared.validate_text("ééa")
    with pytest.raises(ContractError, match="return text"):
        declared.validate_text(b"bytes")
    with pytest.raises(ContractError, match="valid UTF-8"):
        declared.validate_text("\ud800")


@pytest.mark.parametrize("change", [dict(overflow="truncate"), dict(encoding="ascii"),
    dict(schema_version=True), dict(schema_version=0), dict(max_input_bytes=True),
    dict(actions=("inspect", "inspect")), dict(serializer_id=" ")])
def test_invalid_contract_is_rejected(change):
    with pytest.raises(ContractError):
        contract(**change)


@requires_torch
def test_bound_training_reload_and_prediction_identity(bound_checkpoint):
    path, metadata = bound_checkpoint
    declared = contract()
    assert metadata["parameters_changed"]
    assert metadata["compatibility_mode"] == "bound"
    assert metadata["model_io_contract_sha256"] == declared.digest
    assert metadata["input_truncation"] is False
    config = json.loads((path / "config.json").read_text())
    assert config["model_io_contract"] == declared.to_dict()
    assert metadata["artifacts"]["config.json"] == file_sha256(path / "config.json")
    first = load_model(path, expected_model_io_contract=declared)
    second = load_model(path)
    assert second.model_io_contract == declared
    a = first.predict("status=fail", model_io_contract=declared)
    b = second.predict("status=fail", model_io_contract=declared)
    assert a["token_ids"] == b["token_ids"]
    assert a["action_probabilities"] == b["action_probabilities"]
    assert a["model_io_contract_sha256"] == declared.digest


@pytest.mark.parametrize("change", [dict(schema_id="other"), dict(schema_version=2),
    dict(serializer_id="unit.serialize.v2"), dict(actions=("stop", "inspect")),
    dict(max_input_bytes=63)])
@requires_torch
def test_load_rejects_every_representation_mismatch_before_model_load(bound_checkpoint, monkeypatch, change):
    path, _ = bound_checkpoint
    def forbidden(*args, **kwargs):
        pytest.fail("incompatible model must not be constructed")
    monkeypatch.setattr(sequence, "build_model", forbidden)
    with pytest.raises(ContractError, match="contract mismatch"):
        load_model(path, expected_model_io_contract=contract(**change))


@requires_torch
def test_missing_contract_and_oversized_input_never_reach_model(bound_checkpoint, monkeypatch):
    path, _ = bound_checkpoint
    decoder = load_model(path)
    def forbidden(*args, **kwargs):
        pytest.fail("invalid model input reached neural inference")
    monkeypatch.setattr(decoder.model, "forward", forbidden)
    for declaration in (None, contract(schema_version=2)):
        with pytest.raises(ContractError, match="contract mismatch"):
            decoder.predict("status=fail", model_io_contract=declaration)
    with pytest.raises(ContractError, match="no truncation"):
        decoder.predict("é" * 33, model_io_contract=contract())
    with pytest.raises(ContractError, match="contract mismatch"):
        LearnedProposer(path, lambda task, history: "status=fail")


@requires_torch
def test_training_rejects_conflicting_declarations_before_updates(tmp_path):
    for index, options in enumerate((dict(max_input_bytes=65),
                                     dict(action_vocabulary=("stop", "inspect")))):
        destination = tmp_path / f"bad-{index}"
        with pytest.raises(ContractError, match="differs from the model input contract"):
            train([row(0, "status=fail")], destination, model_io_contract=contract(), **options)
        assert not destination.exists()
    with pytest.raises(ContractError, match="no truncation"):
        train([row(0, "é" * 33)], tmp_path / "oversize", model_io_contract=contract())
    assert not (tmp_path / "oversize").exists()


@requires_torch
def test_adaptation_inherits_contract_and_cannot_reinterpret(bound_checkpoint, tmp_path):
    path, evidence = bound_checkpoint
    inherited = train([row(2, "status=unknown")], tmp_path / "adapted", base_checkpoint=path,
                      max_steps=2, max_seconds=30)
    assert inherited["initial_parameter_sha256"] == evidence["final_parameter_sha256"]
    decoder = load_model(tmp_path / "adapted", expected_model_io_contract=contract())
    assert decoder.model_io_contract == contract()
    assert inherited["model_io_contract_sha256"] == evidence["model_io_contract_sha256"]
    for index, options in enumerate((dict(model_io_contract=contract(serializer_id="other")),
                                     dict(max_input_bytes=65),
                                     dict(action_vocabulary=("inspect",)))):
        destination = tmp_path / f"reinterpreted-{index}"
        with pytest.raises(ContractError):
            train([row(2, "status=unknown")], destination, base_checkpoint=path, **options)
        assert not destination.exists()


@requires_torch
def test_bound_evaluation_requires_declaration_before_loss(bound_checkpoint, monkeypatch):
    path, _ = bound_checkpoint
    decoder = load_model(path)
    held_out = [row(3, "status=unseen", split="test")]
    def forbidden(*args, **kwargs):
        pytest.fail("missing declaration must not reach loss/inference")
    with monkeypatch.context() as patch:
        patch.setattr(decoder.model, "forward", forbidden)
        with pytest.raises(ContractError, match="contract mismatch"):
            decoder.evaluate(held_out)
    result = decoder.evaluate(held_out, model_io_contract=contract())
    assert result["model_io_contract_sha256"] == contract().digest
    assert result["predictions"][0]["compatibility_mode"] == "bound"


@requires_torch
def test_student_serializer_uses_same_bytes_in_training_and_inference(tmp_path, monkeypatch):
    # A student's declared replacement needs no registry or runtime rewrite.
    declared = contract(schema_version=2, serializer_id="student.status.v2")
    def student_serializer(task, history):
        return f"result:{task.specification['status']}"
    task = Task("student", ("inspect", "stop"), (CheckRequirement("functional", "unit"),),
                specification={"status": "échec"})
    text = student_serializer(task, ())
    captured = []
    original = sequence._encode_input
    def capture(value, limit):
        encoded = original(value, limit)
        captured.append((value.encode("utf-8"), encoded))
        return encoded
    monkeypatch.setattr(sequence, "_encode_input", capture)
    path = tmp_path / "student"
    train([row(4, text)], path, model_io_contract=declared,
          max_steps=2, max_seconds=30, embedding_dim=4, hidden_dim=8)
    training_bytes, training_tokens = captured[-1]
    proposer = LearnedProposer(path, student_serializer, model_io_contract=declared)
    proposer.propose(task, (), Budget(1, 1))
    assert captured[-1] == (training_bytes, training_tokens)
    assert training_bytes == b"result:\xc3\xa9chec"
    assert proposer.predictions[0]["model_io_contract_sha256"] == declared.digest


@requires_torch
def test_legacy_loading_is_explicit_and_cannot_claim_new_contract(tmp_path):
    path = tmp_path / "legacy"
    train([row(0, "status=fail")], path, max_steps=2, max_seconds=30,
          embedding_dim=4, hidden_dim=8)
    # Existing checkpoints lack the new explicit metadata; they remain loadable.
    metadata = json.loads((path / "training.json").read_text())
    metadata.pop("compatibility_mode")
    metadata.pop("model_io_contract_sha256")
    (path / "training.json").write_text(json.dumps(metadata))
    decoder = load_model(path)
    assert decoder.model_io_contract is None
    assert decoder.compatibility_mode == "legacy_unbound"
    assert decoder.predict("status=fail")["compatibility_mode"] == "legacy_unbound"
    with pytest.raises(ContractError, match="Legacy unbound"):
        load_model(path, expected_model_io_contract=contract())
    with pytest.raises(ContractError, match="Legacy unbound"):
        decoder.predict("status=fail", model_io_contract=contract())
    with pytest.raises(ContractError, match="cannot acquire"):
        train([row(1, "new")], tmp_path / "retrofit", base_checkpoint=path,
              model_io_contract=contract())


@requires_torch
def test_saved_contract_cannot_drift_from_tokenizer(bound_checkpoint, tmp_path):
    path, _ = bound_checkpoint
    changed = tmp_path / "changed"
    shutil.copytree(path, changed)
    config_path = changed / "config.json"
    config = json.loads(config_path.read_text())
    config["model_io_contract"]["actions"].reverse()
    config_path.write_text(json.dumps(config))
    # Even a rewritten manifest does not make inconsistent contract/token IDs valid.
    metadata_path = changed / "training.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["artifacts"]["config.json"] = file_sha256(config_path)
    metadata["model_io_contract_sha256"] = ModelIOContract.from_dict(config["model_io_contract"]).digest
    metadata_path.write_text(json.dumps(metadata))
    with pytest.raises(ContractError, match="differs from saved"):
        load_model(changed)
