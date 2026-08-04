from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

import cli.arch2 as arch2_cli


runner = CliRunner()


def _profile(
    page: int,
    *,
    bottom_whitespace: float | None = 20.0,
    occupancy: float | None = 0.9,
    word_count: int = 220,
    has_figure: bool = False,
    has_table: bool = False,
    captions: tuple[str, ...] = (),
    starts_chapter: bool = False,
    major_unit_kind: str | None = None,
) -> arch2_cli.LayoutPageProfile:
    usable_bottom = 672.0
    content_bottom = (
        usable_bottom - bottom_whitespace if bottom_whitespace is not None else None
    )
    return arch2_cli.LayoutPageProfile(
        page=page,
        width=612.0,
        height=792.0,
        word_count=word_count,
        content_top=100.0 if content_bottom is not None else None,
        content_bottom=content_bottom,
        usable_bottom=usable_bottom,
        bottom_whitespace=bottom_whitespace,
        has_figure=has_figure,
        has_table=has_table,
        captions=captions,
        starts_chapter=starts_chapter,
        text_excerpt=f"Page {page} body text",
        content_occupancy=occupancy,
        major_unit_kind=major_unit_kind,
    )


def test_sparse_page_detector_reports_float_induced_underfill() -> None:
    profiles = [
        _profile(1, starts_chapter=True, major_unit_kind="chapter"),
        _profile(2, bottom_whitespace=180.0, occupancy=0.68),
        _profile(
            3,
            has_figure=True,
            captions=("Figure 1.2: Bounded methods serve a broader study",),
        ),
        _profile(4),
    ]

    findings = arch2_cli.sparse_page_findings(Path("book.pdf"), profiles=profiles)

    assert len(findings) == 1
    assert findings[0].severity == "error"
    assert findings[0].code == "float-induced-whitespace"
    assert findings[0].location.endswith(":page 2")
    assert "180pt" in findings[0].message
    assert "68% vertical content occupancy" in findings[0].message
    assert "page 3 contains Figure 1.2" in findings[0].message


def test_sparse_page_detector_reports_short_page_before_float() -> None:
    profiles = [
        _profile(1, starts_chapter=True, major_unit_kind="chapter"),
        _profile(
            2,
            bottom_whitespace=250.0,
            occupancy=0.48,
            word_count=52,
        ),
        _profile(
            3,
            has_figure=True,
            captions=("Figure 1.2: A float forced the page break",),
        ),
        _profile(4),
    ]

    findings = arch2_cli.sparse_page_findings(Path("book.pdf"), profiles=profiles)

    assert [finding.code for finding in findings] == ["float-induced-whitespace"]
    assert findings[0].location.endswith(":page 2")


def test_sparse_page_detector_exempts_intentional_short_pages() -> None:
    profiles = [
        _profile(1, bottom_whitespace=300.0, occupancy=0.4, word_count=40),
        _profile(
            2,
            bottom_whitespace=None,
            occupancy=None,
            word_count=0,
        ),
        _profile(
            3,
            bottom_whitespace=240.0,
            occupancy=0.5,
            major_unit_kind="part",
        ),
        _profile(
            4,
            bottom_whitespace=210.0,
            occupancy=0.58,
            starts_chapter=True,
            major_unit_kind="chapter",
        ),
        _profile(5, bottom_whitespace=190.0, occupancy=0.65),
        _profile(
            6,
            bottom_whitespace=220.0,
            occupancy=0.55,
            major_unit_kind="references",
        ),
        _profile(7, bottom_whitespace=230.0, occupancy=0.52),
        _profile(8),
    ]

    findings = arch2_cli.sparse_page_findings(Path("book.pdf"), profiles=profiles)

    assert findings == []


def test_sparse_page_detector_looks_past_blank_recto_verso_page() -> None:
    profiles = [
        _profile(1, starts_chapter=True, major_unit_kind="chapter"),
        _profile(2, bottom_whitespace=218.0, occupancy=0.56),
        _profile(
            3,
            bottom_whitespace=575.0,
            occupancy=0.012,
            word_count=4,
        ),
        _profile(4, major_unit_kind="appendix"),
        _profile(5),
    ]

    findings = arch2_cli.sparse_page_findings(Path("book.pdf"), profiles=profiles)

    assert findings == []


def test_sparse_page_detector_does_not_skip_sparse_part_opener() -> None:
    profiles = [
        _profile(1, starts_chapter=True, major_unit_kind="chapter"),
        _profile(2, bottom_whitespace=218.0, occupancy=0.56),
        _profile(
            3,
            bottom_whitespace=None,
            occupancy=None,
            word_count=0,
        ),
        _profile(
            4,
            bottom_whitespace=None,
            occupancy=None,
            word_count=5,
            major_unit_kind="part",
        ),
        _profile(5),
    ]

    findings = arch2_cli.sparse_page_findings(Path("book.pdf"), profiles=profiles)

    assert findings == []


def test_major_unit_detection_only_uses_opening_lines() -> None:
    opening = ["Running header", "References", "First entry"]
    late_heading = [
        "Running header",
        *[f"Body line {i}" for i in range(12)],
        "References",
    ]

    assert arch2_cli._pdf_major_unit_kind(opening) == "references"
    assert arch2_cli._pdf_major_unit_kind(late_heading) is None


def test_profile_geometry_ignores_low_sidenote_and_thin_rule() -> None:
    class Page:
        images: list[dict] = []
        curves: list[dict] = []
        rects = [{"x0": 130.0, "x1": 480.0, "top": 650.0, "bottom": 650.5}]

    words = [
        {"text": "Main", "x0": 140.0, "x1": 175.0, "top": 100.0, "bottom": 112.0},
        {"text": "ending", "x0": 140.0, "x1": 185.0, "top": 408.0, "bottom": 420.0},
        {"text": "sidenote", "x0": 25.0, "x1": 95.0, "top": 638.0, "bottom": 650.0},
    ]

    (
        main_words,
        objects,
        content_top,
        content_bottom,
    ) = arch2_cli._layout_profile_content_geometry(
        Page(),
        words,
        page_width=612.0,
        header_cutoff=90.0,
        footer_cutoff=672.0,
    )

    assert [word["text"] for word in main_words] == ["Main", "ending"]
    assert objects == []
    assert content_top == 100.0
    assert content_bottom == 420.0


def test_layout_findings_include_blocking_sparse_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profiles = [
        _profile(1, starts_chapter=True, major_unit_kind="chapter"),
        _profile(2, bottom_whitespace=185.0, occupancy=0.66),
        _profile(3, has_table=True, captions=("Table 1.1: Evidence",)),
        _profile(4),
    ]
    monkeypatch.setattr(arch2_cli, "scan_latex_logs", lambda: [])
    monkeypatch.setattr(
        arch2_cli,
        "scan_pdf_geometry",
        lambda _path, *, bottom_clearance: [],
    )
    monkeypatch.setattr(arch2_cli, "footnote_overflow_findings", lambda _path: [])
    monkeypatch.setattr(arch2_cli, "layout_page_profiles", lambda _path: profiles)

    findings = arch2_cli.layout_findings(Path("book.pdf"))

    assert [finding.code for finding in findings] == ["float-induced-whitespace"]
    assert findings[0].severity == "error"


def test_layout_scan_blocks_sparse_error_but_not_other_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        arch2_cli,
        "layout_findings",
        lambda *_args, **_kwargs: [
            arch2_cli.Finding("warning", "underfull-box", "book.log", "loose box"),
            arch2_cli.Finding(
                "error",
                "float-induced-whitespace",
                "book.pdf:page 2",
                "sparse page",
            ),
        ],
    )

    result = runner.invoke(arch2_cli.app, ["layout", "scan", "book.pdf"])

    assert result.exit_code == 1


def test_layout_scan_leaves_unrelated_warning_advisory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        arch2_cli,
        "layout_findings",
        lambda *_args, **_kwargs: [
            arch2_cli.Finding("warning", "underfull-box", "book.log", "loose box")
        ],
    )

    result = runner.invoke(arch2_cli.app, ["layout", "scan", "book.pdf"])

    assert result.exit_code == 0
