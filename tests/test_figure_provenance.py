"""Evidence inventory checks must not mistake formatting or names for provenance."""

from pathlib import Path

import pytest

import data.validate_figure_provenance as provenance


@pytest.fixture
def figure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    monkeypatch.setattr(provenance, "ROOT", tmp_path)
    monkeypatch.setattr(provenance, "bibliography_keys", lambda: {"Primary2026"})
    monkeypatch.setattr(
        provenance, "recorded_receipt_paths", lambda: {"observations.csv"}
    )
    chapter = tmp_path / "chapter.qmd"
    chapter.write_text("")
    images = tmp_path / "images"
    images.mkdir()
    (images / "result.svg").write_text("<svg/>")
    return {"qmd": chapter, "stem": "result", "cell": None, "caption": "Result."}


def test_internal_cross_references_are_not_bibliographic_sources() -> None:
    assert (
        provenance.cited_sources("See @fig-result, @tbl-capacity and @eq-bound.")
        == set()
    )


def test_bibliography_key_is_a_source(figure: dict) -> None:
    assert provenance.cited_sources("Source [@Primary2026].") == {"Primary2026"}


def test_svg_does_not_implicitly_declare_a_conceptual_diagram(figure: dict) -> None:
    assert provenance.classify("fig-result", figure, {})[0] == "VIOLATION"
    assert (
        provenance.classify("fig-result", figure, {"evidence_class": "measured"})[0]
        == "VIOLATION"
    )


def test_csv_name_in_code_does_not_supply_missing_declared_input(figure: dict) -> None:
    figure["cell"] = 'filename = "missing.csv"'
    declaration = {"evidence_class": "measured", "data": ["missing.csv"]}
    verdict, detail, _ = provenance.classify("fig-result", figure, declaration)
    assert verdict == "VIOLATION"
    assert "missing" in detail


def test_internal_reference_cannot_support_transcribed_values(figure: dict) -> None:
    figure["caption"] = "Values from @tbl-capacity and @eq-bound."
    assert (
        provenance.classify("fig-result", figure, {"evidence_class": "transcribed"})[0]
        == "VIOLATION"
    )


def test_explicit_conceptual_figure_needs_no_empirical_source(figure: dict) -> None:
    verdict, detail, _ = provenance.classify(
        "fig-result", figure, {"evidence_class": "conceptual"}
    )
    assert verdict == "declared-conceptual"
    assert "not empirical observations" in detail


def test_transcribed_figure_can_name_actual_bibliographic_source(figure: dict) -> None:
    figure["caption"] = "Published values [@Primary2026]."
    assert (
        provenance.classify("fig-result", figure, {"evidence_class": "transcribed"})[0]
        == "declared-transcribed"
    )


def test_missing_or_unknown_source_is_rejected(figure: dict) -> None:
    declaration = {"evidence_class": "transcribed", "citations": ["Invented2026"]}
    assert provenance.classify("fig-result", figure, declaration)[0] == "VIOLATION"
    declaration = {"evidence_class": "conceptual", "generator": "missing.py"}
    assert provenance.classify("fig-result", figure, declaration)[0] == "VIOLATION"


def test_retained_data_path_establishes_inventory_only(figure: dict) -> None:
    (provenance.ROOT / "observations.csv").write_text("value\n1\n")
    declaration = {"evidence_class": "measured", "data": ["observations.csv"]}
    verdict, detail, _ = provenance.classify("fig-result", figure, declaration)
    assert verdict == "declared-measured"
    assert detail == "1 retained input(s)"
