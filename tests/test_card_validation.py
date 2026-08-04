from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from cli.card_migration import migrate_v1_1_to_v2_draft
from cli.arch2 import (
    CARD_SCHEMA_PATHS,
    CARD_SCHEMA_VERSION,
    ROOT,
    card_validation_findings,
)

VALID_CARD_DIR = ROOT / "examples" / "design-loop-cards"
INVALID_CARD_DIR = ROOT / "tests" / "fixtures" / "cards"


@pytest.mark.parametrize("schema_path", CARD_SCHEMA_PATHS.values())
def test_schema_is_valid_draft_2020_12(schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize(
    "filename",
    [
        "level-0-context.yaml",
        "level-1-auditable.yaml",
        "level-2-replayable.yaml",
        "level-3-independent.yaml",
        "redacted-level-0.yaml",
    ],
)
def test_legacy_v1_1_fixture_remains_valid_for_one_release(filename: str) -> None:
    path = VALID_CARD_DIR / filename
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["schema_version"] == "1.1"
    assert card_validation_findings(path) == []


def test_canonical_v2_fixture_validates_with_local_integrity_checks() -> None:
    path = VALID_CARD_DIR / "array-study-v2.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert CARD_SCHEMA_VERSION == "2.0"
    assert document["schema_version"] == CARD_SCHEMA_VERSION
    assert card_validation_findings(path) == []


def test_legacy_examples_preserve_one_case_as_levels_increase() -> None:
    cards = []
    for level, filename in enumerate(
        [
            "level-0-context.yaml",
            "level-1-auditable.yaml",
            "level-2-replayable.yaml",
            "level-3-independent.yaml",
        ]
    ):
        document = yaml.safe_load(
            (VALID_CARD_DIR / filename).read_text(encoding="utf-8")
        )
        card = document["design_loop_card"]
        assert card["conformance_level"] == level
        cards.append(card)

    for card in cards[1:]:
        for field in ("intent", "task", "design_space"):
            assert card[field] == cards[0][field]

    level_0_claim = cards[0]["intent"]["claim_boundary"]["claim"]
    assert "scopes the 16x16/32x8 comparison" in level_0_claim
    assert "evidence" not in level_0_claim.lower()
    assert (
        cards[3]["commitment_boundary"]["strongest_supported_claim"]
        == "Run one bounded RTL experiment for the 32x8 candidate."
    )

    def level_1_view(card: dict[str, object]) -> dict[str, object]:
        view = deepcopy(card)
        view.pop("card_id")
        view.pop("conformance_level")
        view.pop("rejection_authority", None)
        view.pop("commitment_boundary", None)
        view.pop("human_decision", None)
        view["representation"].pop("state_schema_id", None)
        view["environment"].pop("environment_id", None)
        view["method_role"]["actor_map"] = view["method_role"]["actor_map"][:1]
        for record in view["evidence"]["records"]:
            for key in ("evidence_id", "workload_id", "seed", "provenance"):
                record.pop(key, None)
        for trace in view["negative_traces"]:
            trace.pop("candidate_id", None)
        return view

    assert level_1_view(cards[1]) == level_1_view(cards[2])
    assert level_1_view(cards[2]) == level_1_view(cards[3])

    for record, packet_name in zip(
        cards[1]["evidence"]["records"],
        (
            "illustrative-array-summary-16x16.json",
            "illustrative-array-summary-32x8.json",
        ),
        strict=True,
    ):
        packet = json.loads(
            (VALID_CARD_DIR / "evidence" / packet_name).read_text(encoding="utf-8")
        )
        aggregate = packet["results"]["aggregate"]
        assert str(aggregate["estimated_cycles"]) in record["kind"]
        assert f'{aggregate["pe_utilization_percent"]:.6f}%' in record["kind"]


def test_start_path_separates_context_drafting_from_supported_profiles() -> None:
    start = (ROOT / "www" / "start.qmd").read_text(encoding="utf-8")
    assert "Draft the context profile in 30 minutes" in start
    assert "Complete profiles independently" in start
    assert "A partial profile must name its gaps." in start
    assert "Do not ask them to fabricate evidence" in start
    assert "/examples/design-loop-cards/array-study-v2.yaml" in start
    assert "old-card.v2-migration-draft.yaml" in start


def test_start_path_keeps_fixtures_labs_and_lighthouse_distinct() -> None:
    start = (ROOT / "www" / "start.qmd").read_text(encoding="utf-8")
    assert "Practice with executed evidence" in start
    assert "https://github.com/harvard-edge/arch2/tree/main/labs" in start
    assert "does not replace empirical lab work" in start
    assert "/book/chapters/08-running-the-loop/" in start
    assert "None substitutes for another." in start

    examples_readme = (VALID_CARD_DIR / "README.md").read_text(encoding="utf-8")
    assert "synthetic packets teach the schema" in examples_readme
    assert "https://github.com/harvard-edge/arch2/tree/main/labs" in examples_readme
    assert "do not replace empirical lab work" in examples_readme
    assert "Chapter 8 study" in examples_readme


def test_start_path_separates_profiles_from_evidence_and_commitment() -> None:
    start = (ROOT / "www" / "start.qmd").read_text(encoding="utf-8")
    for heading in ("Profile completeness", "Evidence fidelity", "Commitment"):
        assert f"<strong>{heading}</strong>" in start
    assert "A complete profile says that named bindings exist." in start
    assert "Schema validation proves structure and local bindings" in start
    assert "It does not prove that the workload is representative" in start
    assert "One profile never implies another." in start


@pytest.mark.skip(
    reason="appendix-b-design-loop-card was removed in 356e66f and the appendix set was\n    deliberately not rebuilt (card content moved to chapter 3). These assertions pin prose\n    that no longer exists anywhere in the book. Kept rather than deleted so the contract is\n    recoverable if that appendix ever returns; un-skip together with the content."
)
def test_appendix_b_distinguishes_fixture_lab_and_context_drafting() -> None:
    appendix = (
        ROOT / "book" / "appendices" / "appendix-b-design-loop-card" / "index.qmd"
    ).read_text(encoding="utf-8")
    assert "Synthetic card example" in appendix
    # Companion-labs assertions removed 2026-07-19: appendix-B dropped the labs
    # references in 33abd01f ("labs not ready"); restore with the content if labs return.
    assert "30-minute context workflow" in appendix
    assert "Draft and validate the study boundary" in appendix


@pytest.mark.skip(
    reason="appendix-b-design-loop-card was removed in 356e66f and the appendix set was\n    deliberately not rebuilt (card content moved to chapter 3). These assertions pin prose\n    that no longer exists anywhere in the book. Kept rather than deleted so the contract is\n    recoverable if that appendix ever returns; un-skip together with the content."
)
def test_appendix_b_does_not_treat_logs_or_crashes_as_proof() -> None:
    appendix = (
        ROOT / "book" / "appendices" / "appendix-b-design-loop-card" / "index.qmd"
    ).read_text(encoding="utf-8")
    normalized = re.sub(r"\s+", " ", appendix)
    assert "does not prove adequate exploration" in normalized
    assert "segfault or compile failure is an environment failure" in normalized
    assert "candidate-rejection check only when a predeclared rule" in normalized
    assert "simulator segfaults" not in appendix
    assert "enough to prove you explored the space" not in appendix


@pytest.mark.skip(
    reason="appendix-b-design-loop-card was removed in 356e66f and the appendix set was\n    deliberately not rebuilt (card content moved to chapter 3). These assertions pin prose\n    that no longer exists anywhere in the book. Kept rather than deleted so the contract is\n    recoverable if that appendix ever returns; un-skip together with the content."
)
def test_appendix_b_keeps_card_evidence_and_receipt_contained() -> None:
    appendix = (
        ROOT / "book" / "appendices" / "appendix-b-design-loop-card" / "index.qmd"
    ).read_text(encoding="utf-8")
    normalized = re.sub(r"\s+", " ", appendix)
    assert "compact summary and index" in normalized.lower()
    assert "detailed observations belong" in normalized.lower()
    assert "executable details in the replay package" in normalized
    assert "review rubric separates support from polish" in normalized.lower()
    assert "card acts as a shareable evidence ledger" not in normalized
    assert 'do not need separate "claim cards" or "evidence ledgers"' not in normalized


@pytest.mark.skip(
    reason="appendix-b-design-loop-card was removed in 356e66f and the appendix set was\n    deliberately not rebuilt (card content moved to chapter 3). These assertions pin prose\n    that no longer exists anywhere in the book. Kept rather than deleted so the contract is\n    recoverable if that appendix ever returns; un-skip together with the content."
)
def test_appendix_b_bounds_profile_and_replay_claims() -> None:
    appendix = (
        ROOT / "book" / "appendices" / "appendix-b-design-loop-card" / "index.qmd"
    ).read_text(encoding="utf-8")
    normalized = re.sub(r"\s+", " ", appendix)
    assert "profiles are non-ordinal" in normalized.lower()
    assert "A `partial` profile must list its missing bindings" in normalized
    assert "commands, an environment binding, inputs, outputs" in normalized
    assert "The command-line validator checks hashes for local" in normalized
    assert (
        "successful replay shows that the named replay package ran"
        in normalized.lower()
    )
    assert "broader reproducibility or transfer requires a separate evaluation" in (
        normalized.lower()
    )
    assert (
        "a tool crash should normally be recorded as an `environment_failure`"
        in normalized.lower()
    )
    assert "one profile never implies another" not in normalized.lower()
    # labs README link assertion removed 2026-07-19 with the "labs not ready" edit (33abd01f).


def test_legacy_v1_card_still_uses_v1_contract() -> None:
    assert card_validation_findings(INVALID_CARD_DIR / "valid-v1.0-legacy.yaml") == []


def test_explicit_legacy_contract_reports_its_own_version() -> None:
    findings = card_validation_findings(
        VALID_CARD_DIR / "level-0-context.yaml",
        schema_path=CARD_SCHEMA_PATHS["1.0"],
    )
    assert any("contract '1.0'" in finding.message for finding in findings)


def test_context_template_validates_without_claiming_other_profiles(
    tmp_path: Path,
) -> None:
    template_path = ROOT / "design-loop-card" / "template.yaml"
    document = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    card = document["design_loop_card"]
    assert set(card) == {
        "card_id",
        "profiles",
        "profile_gaps",
        "intent",
        "task",
        "design_space",
        "claims",
        "evidence",
        "failed_or_rejected",
        "gates",
        "decision_rights",
        "accountable_decision",
    }
    card["card_id"] = "starter-context-card"
    card["intent"]["objective"] = "Bound a first architecture experiment."
    card["intent"]["constraints"] = ["Hold the workload constant."]
    card["intent"]["non_goals"] = ["Authorize implementation."]
    card["design_space"]["legal"] = ["Compare two fixed candidates."]
    card["design_space"]["invalid"] = ["Change the workload."]
    card["design_space"]["deferred"] = ["Physical design."]
    card["task"]["kind"] = "bounded_experiment"
    card["task"]["description"] = "Compare two fixed candidates."
    claim = card["claims"][0]
    claim["claim_id"] = "claim-first-experiment"
    claim["statement"] = "One candidate may merit a bounded experiment."
    claim["baseline_or_comparator"] = "The fixed baseline candidate."
    claim["outcome"] = "Not tested."
    claim["scope"] = "The declared workload and two candidates."
    claim["non_claims"] = ["The candidate is implementation-ready."]
    decision = card["accountable_decision"]
    decision["holder_id"] = "architecture-owner"
    decision["action"] = "Decide whether to execute the experiment."
    decision["rationale"] = "The context is ready for review; evidence is pending."
    decision["claim_refs"] = ["claim-first-experiment"]
    decision["authorized_scope"] = "No execution is authorized by this draft."
    decision["reopen_conditions"] = ["Evidence becomes available."]

    completed = tmp_path / "context-card.yaml"
    completed.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    assert card_validation_findings(completed) == []


def test_start_workflow_uses_minimal_version_bounded_requirements() -> None:
    start = (ROOT / "www" / "start.qmd").read_text(encoding="utf-8")
    setup = """python3 -m venv .venv-card
.venv-card/bin/python -m pip install --upgrade pip==26.1.2
.venv-card/bin/python -m pip install -r requirements-card.txt
.venv-card/bin/python cli/arch2.py validate card my-card.yaml"""
    assert setup in start
    assert "pip install -r requirements-card.txt" in start
    assert "pip install -r requirements.txt" not in start
    assert ".venv-card/" in (ROOT / ".gitignore").read_text(encoding="utf-8")

    requirements = (ROOT / "requirements-card.txt").read_text(encoding="utf-8")
    for package in ("typer", "rich", "PyYAML", "jsonschema", "referencing"):
        line = next(
            line for line in requirements.splitlines() if line.startswith(package)
        )
        assert ">=" in line
        assert "<" in line


@pytest.mark.parametrize(
    ("filename", "message"),
    [
        ("invalid-level-1-missing-evidence.yaml", "level 1 requires 'evidence'"),
        ("invalid-level-3-dependent-gate.yaml", "True was expected"),
        ("invalid-top-level-claim.yaml", "use intent.claim_boundary.claim"),
        ("invalid-v2-claim-missing-comparator.yaml", "baseline_or_comparator"),
        ("invalid-v2-unknown-evidence-ref.yaml", "unknown evidence reference"),
        ("invalid-version.yaml", "unsupported schema version"),
    ],
)
def test_invalid_fixture_has_actionable_diagnostic(filename: str, message: str) -> None:
    findings = card_validation_findings(INVALID_CARD_DIR / filename)
    assert findings
    assert message in "\n".join(finding.message for finding in findings)


def test_cli_reports_success_and_failure() -> None:
    valid = subprocess.run(
        [
            sys.executable,
            str(ROOT / "cli" / "arch2.py"),
            "validate",
            "card",
            str(VALID_CARD_DIR / "array-study-v2.yaml"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert valid.returncode == 0, valid.stdout + valid.stderr
    assert "passed" in valid.stdout

    invalid = subprocess.run(
        [
            sys.executable,
            str(ROOT / "cli" / "arch2.py"),
            "validate",
            "card",
            str(INVALID_CARD_DIR / "invalid-top-level-claim.yaml"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert invalid.returncode == 1
    assert "intent.claim_boundary.claim" in re.sub(r"\s+", "", invalid.stdout)


def test_level_1_rejects_empty_load_bearing_content() -> None:
    findings = card_validation_findings(
        INVALID_CARD_DIR / "invalid-v1.1-empty-level-1.yaml"
    )
    locations = "\n".join(finding.location for finding in findings)
    for path in (
        "representation.reads",
        "representation.writes",
        "representation.uncertainties",
        "environment.actions",
        "environment.invalid_actions",
        "environment.observations",
        "method_role.actor_map",
        "feedback_budget.evaluations",
        "negative_traces",
    ):
        assert path in locations


@pytest.mark.parametrize(
    "path",
    [
        ("method_role", "actor_map", 0, "reads"),
        ("method_role", "actor_map", 0, "writes"),
        ("evidence", "records"),
    ],
)
def test_level_1_rejects_empty_nested_structures(
    tmp_path: Path, path: tuple[str | int, ...]
) -> None:
    document = yaml.safe_load(
        (VALID_CARD_DIR / "level-1-auditable.yaml").read_text(encoding="utf-8")
    )
    value = document["design_loop_card"]
    for part in path[:-1]:
        value = value[part]
    value[path[-1]] = []

    candidate = tmp_path / "empty-structure.yaml"
    candidate.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    findings = card_validation_findings(candidate)
    expected = "".join(
        f"[{part}]" if isinstance(part, int) else f".{part}" for part in path
    )
    assert any(expected in finding.location for finding in findings)


def test_level_2_requires_digest_and_replay_pointer() -> None:
    findings = card_validation_findings(
        INVALID_CARD_DIR / "invalid-v1.1-level-2-provenance.yaml"
    )
    messages = "\n".join(
        f"{finding.location} {finding.message}" for finding in findings
    )
    assert "parameter_hash" in messages
    assert "sha256:" in messages
    assert "source_uri" in messages


def _copy_v2_example(tmp_path: Path) -> Path:
    copied = tmp_path / "design-loop-cards"
    shutil.copytree(VALID_CARD_DIR, copied)
    return copied / "array-study-v2.yaml"


def test_v2_claims_ai_contribution_separately_from_architecture_outcome(
    tmp_path: Path,
) -> None:
    path = _copy_v2_example(tmp_path)
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["design_loop_card"]["claims"].append(
        {
            "claim_id": "claim-ai-contribution",
            "claim_type": "ai_contribution",
            "statement": "No AI method contributed to this illustrative result.",
            "baseline_or_comparator": "The same deterministic workflow without AI.",
            "outcome": "Both arms are identical because model_calls is zero.",
            "scope": "This constructed card example only.",
            "non_claims": ["AI is generally ineffective for architecture work."],
            "status": "null_result",
            "evidence_refs": [
                "illustrative-array-summary-16x16",
                "illustrative-array-summary-32x8",
            ],
        }
    )
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    assert card_validation_findings(path) == []


def test_v2_complete_decision_rights_require_all_six_actions(tmp_path: Path) -> None:
    path = _copy_v2_example(tmp_path)
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    rights = document["design_loop_card"]["decision_rights"]
    document["design_loop_card"]["decision_rights"] = [
        right for right in rights if right["action"] != "waive"
    ]
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    findings = card_validation_findings(path)
    assert findings
    assert any("decision_rights" in finding.location for finding in findings)


def test_v2_replay_profile_verifies_local_hashes(tmp_path: Path) -> None:
    path = _copy_v2_example(tmp_path)
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["design_loop_card"]["replay"]["environment_binding"]["sha256"] = (
        "sha256:" + "0" * 64
    )
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    findings = card_validation_findings(path)
    assert any(finding.code == "card-artifact-hash" for finding in findings)
    assert any("SHA-256 mismatch" in finding.message for finding in findings)


def test_v2_profiles_are_independent_not_cumulative(tmp_path: Path) -> None:
    path = _copy_v2_example(tmp_path)
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    card = document["design_loop_card"]
    card["profiles"]["replay"] = "not_claimed"
    card.pop("replay")
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    assert card_validation_findings(path) == []


def test_v1_1_migration_is_deterministic_and_does_not_invent_semantics() -> None:
    source = yaml.safe_load(
        (VALID_CARD_DIR / "level-3-independent.yaml").read_text(encoding="utf-8")
    )
    first = migrate_v1_1_to_v2_draft(source)
    second = migrate_v1_1_to_v2_draft(source)
    assert first == second
    assert first["status"] == "requires_author_input"
    assert "schema_version" not in first
    claim = first["mapped_design_loop_card"]["claims"][0]
    assert set(claim) == {"statement", "non_claims"}
    missing = {entry["target"] for entry in first["missing_semantics"]}
    assert "design_loop_card.claims[0].status" in missing
    assert "design_loop_card.profiles" in missing
    assert "design_loop_card.decision_rights" in missing
    assert "design_loop_card.replay" in missing


def test_migration_cli_writes_an_explicit_draft(tmp_path: Path) -> None:
    target = tmp_path / "migration-draft.yaml"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "cli" / "arch2.py"),
            "migrate",
            "card",
            str(VALID_CARD_DIR / "level-1-auditable.yaml"),
            "--output",
            str(target),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "requires author input" in completed.stdout
    draft = yaml.safe_load(target.read_text(encoding="utf-8"))
    assert draft["target_schema_version"] == "2.0"
    assert draft["status"] == "requires_author_input"
