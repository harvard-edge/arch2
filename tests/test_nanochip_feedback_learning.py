"""CPU-only adaptation mechanics; feedback here is an explicitly synthetic fixture.

These tests do not run EDA or manufacture measured evidence. Production
admission is owned by design_feedback_data.load_feedback and its own tests.
"""

from collections import Counter
import copy
import importlib.util
import json
from pathlib import Path
import shutil

import pytest

from nanochip.laboratory import design_learning as design
from nanochip.laboratory import design_feedback_learning as learning
from nanochip.laboratory.contracts import ContractError, file_sha256
from nanochip.laboratory.models import load_model


def _fixture_loader(path):
    """Only test fixtures bypass production raw-tool evidence admission."""
    path = Path(path)
    value = json.loads(path.read_text())
    receipt = value["records"][0]["source_receipt"]
    if file_sha256(path.parent / receipt["path"]) != receipt["sha256"]:
        raise ContractError("Synthetic fixture source changed")
    return value


@pytest.fixture(scope="module")
def adapted_case(tmp_path_factory):
    if importlib.util.find_spec("torch") is None:
        pytest.skip("optional CPU PyTorch unavailable")
    root = tmp_path_factory.mktemp("feedback-learning-fixture")
    corpus = design.collect_design_examples(root / "corpus")
    base_report = design.train_design_proposer(
        corpus, root / "initial", max_steps=3, max_seconds=20
    )
    base = Path(base_report["checkpoint_dir"])
    before = {name: file_sha256(base / name) for name in learning.CHECKPOINT_FILES}
    features = dict(
        row_values=256,
        quant_bits=4,
        reload_per_row=True,
        access_order="ascending",
        index_step=1,
        start_index=0,
        passes=1,
        revisit=False,
    )
    feedback_root = root / "synthetic-feedback"
    feedback_root.mkdir()
    evidence = feedback_root / "evidence.json"
    evidence.write_text(
        json.dumps(
            dict(construction="synthetic unit-test evidence; no physical measurement")
        )
    )
    digest = file_sha256(evidence)
    row = dict(
        record_id="synthetic-feedback-case",
        group_id="synthetic-feedback-group",
        split="train",
        original_split="development",
        input_text=design.design_input(features),
        target_action=design.ACTIONS[1],
        source_sha256=digest,
        source_receipt=dict(path="evidence.json", sha256=digest),
        label_origin="synthetic test fixture preference; not measured",
    )
    feedback = dict(
        records=[row],
        target_features=features,
        selected_action=row["target_action"],
        source_files=[],
        copied_evidence=[],
    )
    manifest = feedback_root / "manifest.json"
    manifest.write_text(json.dumps(feedback))
    calls = []
    actual_train = learning.train
    actual_predict = learning.sequence.TinyActionDecoder.predict

    def observed_train(rows, destination, **kwargs):
        protocol_path = Path(destination).parent / "protocol.json"
        assert protocol_path.is_file()
        assert protocol_path.with_suffix(".sha256").read_text().strip() == file_sha256(
            protocol_path
        )
        assert not (Path(destination).parent / "report.json").exists()
        calls.append(
            dict(
                rows=copy.deepcopy(rows),
                destination=str(destination),
                kwargs=kwargs,
                protocol_hash=file_sha256(protocol_path),
            )
        )
        return actual_train(rows, destination, **kwargs)

    def no_target_prediction(self, text, **kwargs):
        assert (
            text != row["input_text"]
        ), "Adaptation must not inspect physical target predictions"
        return actual_predict(self, text, **kwargs)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(learning, "load_feedback", _fixture_loader)
        patch.setattr(learning, "train", observed_train)
        patch.setattr(
            learning.sequence.TinyActionDecoder, "predict", no_target_prediction
        )
        report = learning._adapt_from_feedback(
            base,
            Path(corpus["manifest_path"]),
            manifest,
            root / "adaptation",
            protocol=learning._protocol(max_steps=2),
        )
    return dict(
        root=root,
        corpus=corpus,
        base=base,
        before=before,
        manifest=manifest,
        report=report,
        calls=calls,
    )


def test_public_protocol_has_no_tuning_or_target_selection(tmp_path, monkeypatch):
    received = []

    def capture(*args, protocol):
        received.append(protocol)
        return {}

    monkeypatch.setattr(learning, "_adapt_from_feedback", capture)
    learning.adapt_from_feedback(
        tmp_path / "base", tmp_path / "corpus", tmp_path / "feedback", tmp_path / "out"
    )
    assert received == [learning._protocol()]
    protocol = received[0]
    assert (
        protocol["seed"],
        protocol["max_steps"],
        protocol["max_seconds"],
        protocol["learning_rate"],
        protocol["batch_size"],
    ) == (19, 120, 30.0, 0.001, 16)
    assert protocol["order"] == ["control", "adapted"]
    assert not protocol["test_protocol"]


def test_train_only_replay_and_one_feedback_case(adapted_case):
    report, calls = adapted_case["report"], adapted_case["calls"]
    assert len(calls) == 2
    for call in calls:
        rows = call["rows"]
        assert len(rows) == 64
        assert {row["split"] for row in rows} == {"train"}
        assert Counter(row["target_action"] for row in rows[:56]) == dict.fromkeys(
            design.ACTIONS, 28
        )
        assert (
            len({row.get("sampling_replica_of", row["record_id"]) for row in rows[:56]})
            == 32
        )
        assert len({row["sampling_replica_of"] for row in rows[56:]}) == 1
        assert {row["adaptation_replica"] for row in rows[56:]} == set(range(8))
        assert all(Path(row["source_receipt"]["path"]).is_file() for row in rows)
    assert report["update_counts"] == dict(
        original_train_rows=32,
        replay_rows=56,
        measured_examples=1,
        feedback_replicas=8,
        rows_per_update=64,
    )
    assert "not acceptance" in report["scope"]


def test_matched_control_changes_only_label_source(adapted_case):
    control, feedback = (call["rows"] for call in adapted_case["calls"])
    assert control[:56] == feedback[:56]
    provenance_and_label = {
        "target_action",
        "label_origin",
        "source_sha256",
        "source_receipt",
    }
    for left, right in zip(control[56:], feedback[56:]):
        assert left["target_action"] == design.ACTIONS[0]
        assert right["target_action"] == design.ACTIONS[1]
        assert {
            key: value for key, value in left.items() if key not in provenance_and_label
        } == {
            key: value
            for key, value in right.items()
            if key not in provenance_and_label
        }
        source = json.loads(Path(left["source_receipt"]["path"]).read_text())
        assert source["label_origin"] == design.LABEL_ORIGIN
        assert "no measured" in source["scope"]


def test_frozen_lineage_equal_updates_and_original_bytes(adapted_case):
    report = adapted_case["report"]
    assert [Path(call["destination"]).name for call in adapted_case["calls"]] == [
        "control",
        "adapted",
    ]
    assert {call["protocol_hash"] for call in adapted_case["calls"]} == {
        report["protocol_sha256"]
    }
    assert file_sha256(report["protocol_path"]) == report["protocol_sha256"]
    assert {
        name: file_sha256(adapted_case["base"] / name)
        for name in learning.CHECKPOINT_FILES
    } == adapted_case["before"]
    assert report["checkpoint_hashes"]["base"] == adapted_case["before"]
    initial = report["lineage"]["base_parameter_sha256"]
    for name in ("control", "adapted"):
        result = report["training"][name]
        assert result["initial_parameter_sha256"] == initial
        assert result["parameters_changed"]
        assert result["steps_completed"] == 2
        assert load_model(report["checkpoints"][name]).actions == list(design.ACTIONS)
    assert len(report["protocol"]["batch_record_ids"]) == 2
    assert all(len(batch) == 16 for batch in report["protocol"]["batch_record_ids"])


def test_regression_diagnostics_compare_all_three_frozen_models(adapted_case):
    diagnostics = adapted_case["report"]["diagnostics"]
    assert set(diagnostics) == {"base", "control", "adapted"}
    for result in diagnostics.values():
        for split in ("dev", "test"):
            assert result[split]["record_count"] == 24
            assert sum(result[split]["class_counts"].values()) == 24
            assert set(result[split]["per_action_correct_counts"]) == set(
                design.ACTIONS
            )
            assert "not new physical generalization" in result[split]["interpretation"]


def test_existing_output_and_tampered_sources_are_rejected(
    adapted_case, tmp_path, monkeypatch
):
    case = adapted_case
    monkeypatch.setattr(learning, "load_feedback", _fixture_loader)
    with pytest.raises(ContractError, match="new directory"):
        learning.adapt_from_feedback(
            case["base"],
            Path(case["corpus"]["manifest_path"]),
            case["manifest"],
            case["root"],
        )
    copied_corpus = tmp_path / "corpus"
    shutil.copytree(Path(case["corpus"]["manifest_path"]).parent, copied_corpus)
    source = copied_corpus / case["corpus"]["records"][0]["source_receipt"]["path"]
    source.write_text(source.read_text() + " ")
    with pytest.raises(ContractError, match="content changed"):
        learning.adapt_from_feedback(
            case["base"],
            copied_corpus / "manifest.json",
            case["manifest"],
            tmp_path / "bad-corpus",
        )
    copied_feedback = tmp_path / "feedback"
    shutil.copytree(case["manifest"].parent, copied_feedback)
    (copied_feedback / "evidence.json").write_text("tampered")
    with pytest.raises(ContractError, match="source changed"):
        learning.adapt_from_feedback(
            case["base"],
            Path(case["corpus"]["manifest_path"]),
            copied_feedback / "manifest.json",
            tmp_path / "bad-feedback",
        )
    assert not (tmp_path / "bad-corpus").exists()
    assert not (tmp_path / "bad-feedback").exists()
