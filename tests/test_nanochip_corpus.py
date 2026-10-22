"""Corpus observations omit construction identities and bind back to evidence."""

import json
from pathlib import Path
import shutil

import pytest

from nanochip.laboratory.contracts import ContractError, file_sha256
from nanochip.laboratory.datasets.dequant_corpus import (
    ACTIONS,
    CASES,
    DEFAULT_SOURCE,
    INPUT_SCHEMA,
    LABEL_ORIGIN,
    construct_candidate,
    load_corpus,
    serialize_observation,
    teaching_action,
)
from nanochip.laboratory.dequant_probe import run_probe


def test_templates_are_unique_copies_and_leave_reference_untouched():
    before = DEFAULT_SOURCE.read_bytes()
    candidates = [construct_candidate(before.decode(), case) for case in CASES]
    assert len(set(candidates)) == len(CASES) == 15
    assert DEFAULT_SOURCE.read_bytes() == before
    assert {case.split for case in CASES} == {"train", "dev", "test"}
    assert len({case.template for case in CASES}) == len(CASES)
    with pytest.raises(ContractError, match="anchor"):
        construct_candidate("unrelated source", CASES[1])


def test_anonymous_observation_is_allowlisted_and_contains_only_current_result():
    receipt = {
        "status": "check_failed",
        "ok": False,
        "source_origin": "/private/target_inspect_numerics/output_shift.v",
        "candidate_sha256": "secret-fault-name",
        "future_action": "accept_block",
        "build": {"returncode": 0},
        "simulation": {"returncode": 1},
        "checks": {"mismatches": 4, "protocol_error": "", "future_verdict": "fixed"},
    }
    encoded = serialize_observation(
        receipt,
        "mismatch row=0 lane=1 expected=42 observed=21\nsecret path\n",
        "/private/output_shift.v: syntax error near target_action",
    )
    decoded = json.loads(encoded)
    assert decoded["schema"] == INPUT_SCHEMA
    assert decoded["compiler_diagnostics"] == ["syntax_error"]
    assert decoded["first_mismatches"] == [
        {"row": 0, "lane": 1, "expected": 42, "observed": 21}
    ]
    assert len(encoded.encode()) < 2048
    for forbidden in (
        "private",
        "output_shift",
        "secret",
        "future",
        "target_action",
        *ACTIONS,
    ):
        assert forbidden not in encoded
    assert serialize_observation(
        {**receipt, "future_action": "anything"}
    ) == serialize_observation(receipt)


@pytest.mark.parametrize(
    "receipt, action",
    [
        ({"ok": True, "status": "passed"}, "accept_block"),
        ({"status": "build_failed"}, "inspect_build"),
        ({"status": "unavailable"}, "inspect_build"),
        ({"status": "check_failed", "checks": {"mismatches": 8}}, "inspect_numerics"),
        (
            {
                "status": "check_failed",
                "checks": {"mismatches": 8, "protocol_error": "timeout"},
            },
            "inspect_protocol",
        ),
    ],
)
def test_policy_labels_are_diagnostic_decisions(receipt, action):
    assert teaching_action(receipt) == action


def _single_record_manifest(root, receipt):
    row = {
        "record_id": "case-0",
        "group_id": "template-0",
        "split": "train",
        "input_text": serialize_observation(receipt),
        "target_action": teaching_action(receipt),
        "source_receipt": {
            "path": "probe/receipt.json",
            "sha256": file_sha256(root / "probe/receipt.json"),
        },
        "source_sha256": receipt["candidate_sha256"],
        "label_origin": LABEL_ORIGIN,
    }
    (root / "records.jsonl").write_text(json.dumps(row) + "\n")
    manifest = {
        "schema_version": 1,
        "actions": list(ACTIONS),
        "records": {
            "path": "records.jsonl",
            "sha256": file_sha256(root / "records.jsonl"),
        },
    }
    (root / "manifest.json").write_text(json.dumps(manifest))
    return row, manifest


def test_loader_retains_failed_execution_and_rejects_tampered_snapshot(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "nanochip.laboratory.dequant_probe.shutil.which", lambda _: None
    )
    receipt = run_probe(DEFAULT_SOURCE, tmp_path / "probe")
    _single_record_manifest(tmp_path, receipt)
    rows = load_corpus(tmp_path / "manifest.json")
    assert rows[0]["target_action"] == "inspect_build"
    (tmp_path / "probe/candidate.v").write_text("changed")
    with pytest.raises(ContractError, match="snapshot changed"):
        load_corpus(tmp_path / "manifest.json")


def test_loader_rejects_cross_split_duplicate_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "nanochip.laboratory.dequant_probe.shutil.which", lambda _: None
    )
    receipt = run_probe(DEFAULT_SOURCE, tmp_path / "probe")
    row, manifest = _single_record_manifest(tmp_path, receipt)
    duplicate = {**row, "record_id": "case-1", "split": "test"}
    (tmp_path / "records.jsonl").write_text(
        json.dumps(row) + "\n" + json.dumps(duplicate) + "\n"
    )
    manifest["records"]["sha256"] = file_sha256(tmp_path / "records.jsonl")
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ContractError, match="crosses"):
        load_corpus(tmp_path / "manifest.json")


@pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator unavailable")
def test_constructed_numerical_and_protocol_faults_execute_as_distinct_diagnostics(
    tmp_path,
):
    source = DEFAULT_SOURCE.read_text()
    for index, expected in ((1, "inspect_numerics"), (3, "inspect_protocol")):
        candidate = tmp_path / f"candidate-{index}.v"
        candidate.write_text(construct_candidate(source, CASES[index]))
        receipt = run_probe(candidate, tmp_path / f"probe-{index}")
        assert receipt["mode"] == "fresh"
        assert receipt["build"]["returncode"] == 0
        assert receipt["simulation"]["elapsed_s"] > 0
        assert teaching_action(receipt) == expected
