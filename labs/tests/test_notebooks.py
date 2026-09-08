from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

NOTEBOOKS = [
    Path("notebooks/lab_01_prompt_to_card.py"),
    Path("notebooks/lab_02_scissors_gap.py"),
    Path("notebooks/lab_03_score_a_claim.py"),
    Path("notebooks/lab_04_represent_and_replay.py"),
    Path("notebooks/lab_05_environment_contract.py"),
    Path("examples/scale_proxy_mirage/lab.py"),
    Path("notebooks/lab_07_earned_trust.py"),
    Path("notebooks/lab_08_run_the_loop.py"),
    Path("notebooks/lab_09_same_loop_different_costs.py"),
    Path("notebooks/lab_10_own_the_commitment.py"),
]

RECEIPT_NOTEBOOKS = [
    Path("examples/scale_proxy_mirage/lab.py"),
    Path("notebooks/lab_08_run_the_loop.py"),
    Path("notebooks/lab_09_same_loop_different_costs.py"),
]

CANONICAL_CARD_FIELDS = [
    "Intent",
    "Task",
    "Design space",
    "Representation",
    "Environment",
    "Method role",
    "Feedback budget",
    "Evidence",
    "Failed runs / rejected alternatives",
    "Rejection authority",
    "Commitment boundary / would overturn",
    "Decision and owner",
]

HIDDEN_DEFAULT_STATE = {
    "archive_ready",
    "artifact_ready",
    "decision_complete",
    "evidence_revealed",
    "prediction_snapshot",
    "reflection_form",
    "warmup_unlocked",
}


def _source(notebook: Path) -> str:
    return (Path(__file__).resolve().parents[1] / notebook).read_text()


def test_one_activity_exists_for_each_chapter() -> None:
    assert len(NOTEBOOKS) == 10
    assert len(set(NOTEBOOKS)) == 10


def test_marimo_notebooks_import() -> None:
    labs_root = Path(__file__).resolve().parents[1]
    for index, notebook in enumerate(NOTEBOOKS):
        path = labs_root / notebook
        spec = importlib.util.spec_from_file_location(f"arch2_notebook_{index}", path)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert module.app is not None


@pytest.mark.parametrize(("lab_index", "notebook"), list(enumerate(NOTEBOOKS, start=1)))
def test_activity_map_and_heading_name_one_chapter(
    lab_index: int, notebook: Path
) -> None:
    source = _source(notebook)
    heading = next(
        line.strip()
        for line in source.splitlines()
        if line.strip().startswith("# Lab ")
    )
    activity_map = (
        Path(__file__).resolve().parents[1] / "notebooks/README.md"
    ).read_text()

    import re

    match = re.search(r"Chapter (\d+)", heading)
    assert match is not None
    chapter_num = match.group(1)

    map_line = next(
        line
        for line in activity_map.splitlines()
        if line.startswith(f"| [{lab_index:02d}]")
        or line.startswith(f"| [**{lab_index:02d}**]")
    )

    assert heading.startswith(f"# Lab {lab_index:02d} ")
    assert f"| Ch{chapter_num}," in map_line


@pytest.mark.parametrize("notebook", NOTEBOOKS)
def test_default_graph_hides_downstream_activity_state(notebook: Path) -> None:
    path = Path(__file__).resolve().parents[1] / notebook
    spec = importlib.util.spec_from_file_location(f"default_{path.stem}", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    _, definitions = module.app.run()

    assert HIDDEN_DEFAULT_STATE.isdisjoint(set(definitions))


@pytest.mark.parametrize("notebook", NOTEBOOKS)
def test_each_activity_enforces_the_shared_learning_progression(
    notebook: Path,
) -> None:
    source = _source(notebook)

    assert "warmup_unlocked" in source
    assert "prediction_snapshot" in source
    assert '"confidence"' in source
    assert '"reason"' in source
    assert "mo.stop(" in source
    assert "reflection_form" in source
    assert "Record reflection" in source


@pytest.mark.parametrize("notebook", RECEIPT_NOTEBOOKS)
def test_receipt_activities_keep_human_decisions_explicit(notebook: Path) -> None:
    source = _source(notebook)

    assert "record_human_decision" in source
    assert "validate_receipt" in source
    assert '"selected_candidate_id"' in source
    assert '"governing_objective"' in source
    assert '"would_overturn"' in source
    assert "mo.download(" in source
    assert "gate_survivor" not in source
    assert "min_latency_us" not in source


@pytest.mark.parametrize(
    ("notebook", "activity_id"),
    [
        (Path("notebooks/lab_08_run_the_loop.py"), "lab_08_run_the_loop"),
        (
            Path("notebooks/lab_09_same_loop_different_costs.py"),
            "lab_09_same_loop_different_costs",
        ),
    ],
)
def test_reused_simulator_receipts_bind_the_chapter_activity(
    notebook: Path, activity_id: str
) -> None:
    source = _source(notebook)

    assert "attach_activity_record" in source
    assert f'"activity_id": "{activity_id}"' in source
    assert "archive.writestr(" not in source


def test_sourced_public_record_fixture_uses_the_canonical_card() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    fixture = json.loads(
        (repo_root / "labs/fixtures/alphachip_public_record_card.json").read_text()
    )
    fields = fixture["card_fields"]

    assert [entry["field"] for entry in fields] == CANONICAL_CARD_FIELDS
    assert "fixed teaching snapshot" in fixture["source"]["snapshot_note"]
    assert "Absent or partial does not imply" in fixture["interpretation_boundary"]

    bibliography = (repo_root / "book/references/references.bib").read_text()
    citation_keys = {
        citation for entry in fields for citation in entry.get("citations", [])
    }
    assert citation_keys
    for citation_key in citation_keys:
        assert f"{{{citation_key}," in bibliography


def test_prompt_bootstrap_does_not_claim_canonical_completion() -> None:
    source = Path("notebooks/lab_01_prompt_to_card.py").read_text()

    assert "Four-field bootstrap complete" in source
    assert "not a complete canonical design-loop card" in source
    assert "Card complete" not in source
    assert '"activity_id": "lab_01_prompt_to_card"' in source
    assert "mo.download(" in source


def test_proxy_lab_persists_explicit_learner_decision() -> None:
    source = Path("examples/scale_proxy_mirage/lab.py").read_text()

    assert "record_human_decision" in source
    assert "render_objective_summary" in source
    assert "render_receipt_validation" in source
    assert '"selected_candidate_id": decision_snapshot["choice"]' in source
    assert '"governing_objective": decision_snapshot["objective"]' in source
    assert 'decision_snapshot["rationale"]' in source
    assert "Rationale (optional)" not in source
    assert "prediction_snapshot = dict(prediction_form.value)" in source
    assert "archive_download = mo.download" in source
    assert "gate_survivor" not in source
    assert "SCALE-Sim v2" not in source


def test_scissors_gap_separates_queue_load_from_search_effort() -> None:
    source = Path("notebooks/lab_02_scissors_gap.py").read_text()

    assert "offered_load = proposal_rate / adjudication_capacity" in source
    assert "queue_growth = max(0.0, proposal_rate - adjudication_capacity)" in source
    assert "trusted_throughput = min(proposal_rate, adjudication_capacity)" in source
    assert "evaluations_to_target" in source
    assert "generated candidates wait behind" not in source
    assert "Only raising" not in source
    assert "this book's remedy buys them little" not in source
    assert "return (warmup_unlocked,)" in source
    assert "return prediction_locked, prediction_snapshot" in source
    assert "return (investment_committed,)" in source
    assert '"activity_id": "lab_02_scissors_gap"' in source
    assert "mo.download(" in source
