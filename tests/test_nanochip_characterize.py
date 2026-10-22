"""Distribution diagnostics are descriptive; held-out values never fit support."""

from copy import deepcopy
import hashlib
import json

import pytest

from nanochip.laboratory.contracts import ContractError
from nanochip.laboratory.datasets.characterize import (
    assess_input_support,
    fit_training_support,
    profile_records,
)


def row(index, text="cache", split="train", label="inspect", **changes):
    source = hashlib.sha256(str(index).encode()).hexdigest()
    return dict(
        record_id=f"record-{index}",
        group_id=f"group-{index}",
        split=split,
        original_split=split,
        input_text=text,
        target_action=label,
        source_sha256=source,
        source_receipt=dict(path=f"{index}.json", sha256=source),
        data_origin="constructed",
        **changes,
    )


def test_profile_lengths_counts_and_frozen_training_majority():
    rows = [
        row(0, "é", label="inspect"),
        row(1, "abcd", label="keep"),
        row(2, "longer", label="inspect"),
        row(3, "x", split="test", label="keep"),
    ]
    profile = profile_records(rows)
    assert profile["input_bytes"]["total"] == sum(
        len(r["input_text"].encode()) for r in rows
    )
    assert profile["input_bytes"]["min"] == 1
    assert profile["input_bytes"]["max"] == 6
    assert profile["input_bytes"]["median"] == 3
    assert profile["split_counts"] == {"test": 1, "train": 3}
    assert profile["label_counts"] == {"inspect": 2, "keep": 2}
    assert profile["data_origin_counts"] == {"constructed": 4}
    baseline = profile["training_majority_baseline"]
    assert baseline["action"] == "inspect"
    assert baseline["by_split"]["train"]["constant_action_accuracy"] == pytest.approx(
        2 / 3
    )
    assert baseline["by_split"]["test"]["constant_action_accuracy"] == 0
    assert all(not values for values in profile["cross_partition_leakage"].values())
    assert json.loads(json.dumps(profile)) == profile


def test_profile_exposes_duplicate_inputs_group_source_and_receipt_leakage():
    a = row(0, "same", label="inspect")
    b = row(1, "same", split="test", label="keep")
    b.update(
        group_id=a["group_id"],
        source_sha256=a["source_sha256"],
        source_receipt=a["source_receipt"],
    )
    profile = profile_records([a, b, dict(a)])
    assert profile["exact_record_duplicates"][0]["count"] == 2
    assert profile["duplicate_record_ids"][0]["identity"] == a["record_id"]
    assert profile["exact_input_duplicates"][0]["count"] == 3
    for name in ("groups", "sources", "source_receipts", "exact_inputs"):
        assert profile["cross_partition_leakage"][name][0]["splits"] == [
            "test",
            "train",
        ]
    assert profile["conflicting_input_labels"][0]["labels"] == ["inspect", "keep"]


def test_unlabeled_text_and_empty_profile_do_not_invent_baseline_or_receipt_validation():
    sample = row(0)
    sample.pop("target_action")
    sample["source_receipt"]["path"] = "/file-that-does-not-exist"
    profile = profile_records([sample])
    assert profile["missing_label_count"] == 1
    assert profile["training_majority_baseline"]["action"] is None
    assert "not opened or validated" in profile["validation"]
    empty = profile_records([])
    assert empty["record_count"] == 0
    assert empty["input_bytes"]["min"] is None


def test_only_training_inputs_fit_explicit_feature_support():
    records = [
        row(0, "abcd", features={"lanes": 4, "mode": "serial", "signed": True}),
        row(1, "ééé", features={"lanes": 8, "mode": "parallel", "signed": False}),
        row(
            2,
            "x" * 100,
            split="dev",
            features={"lanes": 1000, "mode": "future", "signed": 7},
        ),
        # Even malformed held-out features/text cannot influence the fit.
        dict(split="test", input_text=None, features="malformed"),
    ]
    support = fit_training_support(
        records, numeric_features=("lanes",), categorical_features=("mode", "signed")
    )
    assert support["training_record_ids"] == ["record-0", "record-1"]
    assert support["numeric_features"]["lanes"] == {"min": 4, "max": 8}
    assert support["input_bytes"]["min"] == 4
    assert support["input_bytes"]["max"] == 6
    assert support["categorical_features"]["mode"] == ["parallel", "serial"]
    result = assess_input_support(
        "aaaaa", {"lanes": 6, "mode": "serial", "signed": True}, support
    )
    assert result["within_observed_support"] is True
    assert result["reasons"] == []
    assert "not confidence" in result["interpretation"]
    assert json.loads(json.dumps(support)) == support


def test_support_returns_concrete_reasons_for_new_input():
    support = fit_training_support(
        [row(0, "abcd", features={"lanes": 4, "mode": "serial", "signed": True})],
        numeric_features=("lanes",),
        categorical_features=("mode", "signed"),
    )
    result = assess_input_support(
        "ééé", {"lanes": 8, "mode": "parallel", "extra": "not checked"}, support
    )
    assert result["within_observed_support"] is False
    assert {r["code"] for r in result["reasons"]} == {
        "byte_length_outside_training_range",
        "numeric_outside_training_range",
        "unseen_category",
        "missing_declared_feature",
    }
    assert result["unchecked_feature_names"] == ["extra"]
    assert result["input_bytes"] == 6
    # Boolean True and integer 1 are different explicitly declared categories.
    typed = assess_input_support(
        "abcd", {"lanes": 4, "mode": "serial", "signed": 1}, support
    )
    assert [r["code"] for r in typed["reasons"]] == ["unseen_category"]
    invalid = assess_input_support(
        "abcd", {"lanes": True, "mode": [], "signed": True}, support
    )
    assert {r["code"] for r in invalid["reasons"]} == {
        "invalid_numeric_feature",
        "invalid_categorical_feature",
    }


def test_no_training_or_reassigned_final_test_cannot_fit_support():
    with pytest.raises(ContractError, match="designated training"):
        fit_training_support([row(0, split="test")])
    leaked = row(0)
    leaked["original_split"] = "test"
    with pytest.raises(ContractError, match="Final-test"):
        fit_training_support([leaked])
    profile = profile_records([leaked])
    assert profile["retagged_final_test_record_ids"] == ["record-0"]
    assert profile["training_majority_baseline"]["action"] is None


def test_feature_declarations_and_support_identity_are_checked():
    sample = row(0, features={"lanes": 4})
    with pytest.raises(ContractError, match="one declared type"):
        fit_training_support(
            [sample], numeric_features=("lanes",), categorical_features=("lanes",)
        )
    with pytest.raises(ContractError, match="lacks declared feature"):
        fit_training_support([sample], numeric_features=("missing",))
    sample["features"]["lanes"] = float("nan")
    with pytest.raises(ContractError, match="finite and nonboolean"):
        fit_training_support([sample], numeric_features=("lanes",))
    support = fit_training_support([row(0)])
    changed = deepcopy(support)
    changed["input_bytes"]["max"] = 100
    with pytest.raises(ContractError, match="content changed"):
        assess_input_support("abcd", {}, changed)


def test_byte_only_support_needs_no_hidden_feature_extraction():
    support = fit_training_support([row(0, "abc"), row(1, "abcd")])
    assert support["numeric_features"] == {}
    assert support["categorical_features"] == {}
    assert assess_input_support("abc", {}, support)["within_observed_support"]
    assert not assess_input_support("a", {}, support)["within_observed_support"]
