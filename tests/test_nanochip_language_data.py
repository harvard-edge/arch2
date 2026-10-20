"""Repository text has file-group splits; engineering labels keep their origin."""

import json

import pytest

from nanochip.laboratory.contracts import ContractError
from nanochip.laboratory import language_data
from nanochip.laboratory.design_learning import collect_design_examples


def test_document_corpus_is_attributed_grouped_and_reconstructs_source(tmp_path):
    root = tmp_path / "text"
    manifest = language_data.collect_language_corpus(root, max_text_bytes=96)
    rows = language_data.load_language_corpus(manifest)
    groups = {}
    for row in rows:
        groups.setdefault(row["group_id"], set()).add(row["split"])
        assert len(row["input_text"].encode()) <= 96
        assert row["data_origin"] == "repository_documentation"
        assert row["attribution"] and row["license"] == "Apache-2.0"
    assert all(len(splits) == 1 for splits in groups.values())
    assert {row["split"] for row in rows} == {"train", "dev", "test"}
    for name in language_data.DOCUMENT_SPLITS:
        text = "".join(row["input_text"] for row in rows if row["group_id"] == f"document:{name}")
        assert text == (root / "sources" / name).read_text()


def test_reassigned_text_and_tampered_source_fail(tmp_path):
    root = tmp_path / "text"
    manifest = language_data.collect_language_corpus(root)
    path = root / "manifest.json"
    changed = json.loads(path.read_text())
    changed["records"][0]["split"] = "test"
    path.write_text(json.dumps(changed))
    with pytest.raises(ContractError, match="frozen partitions"):
        language_data.load_language_corpus(path)
    path.write_text(json.dumps(manifest))
    with (root / "sources/architecture.md").open("a") as stream:
        stream.write("changed")
    with pytest.raises(ContractError, match="content changed"):
        language_data.load_language_corpus(path)


def test_constructed_architecture_rows_are_not_reported_as_measurements(tmp_path):
    manifest = collect_design_examples(tmp_path / "design")
    rows = language_data.architecture_examples(manifest)
    assert all(row["data_origin"] == "constructed" for row in rows)
    assert all("not measured optimal PPA" in row["label_origin"] for row in rows)
    assert all(row["source_root"] == str(tmp_path / "design") for row in rows)
    assert {row["split"] for row in rows} == {"train", "dev", "test"}


def test_measured_feedback_helper_calls_strict_evidence_loader(tmp_path, monkeypatch):
    from nanochip.laboratory import design_feedback_data
    def reject(path):
        raise ContractError("invalid measured source bundle")
    monkeypatch.setattr(design_feedback_data, "load_feedback", reject)
    with pytest.raises(ContractError, match="invalid measured source bundle"):
        language_data.measured_feedback_examples(tmp_path / "invalid.json")
