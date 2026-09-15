"""Alt-text contract for the Springer Nature accessibility requirement.

Springer Nature requires alt text for every figure and image, delivered as an
Excel file and carried into the PDF through SNmono's \\Description macro. These
tests pin the source parser, each alt-text rule, the PDF hook, the render-time
reconciliation, and the spreadsheet writer.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pytest

import cli.arch2 as arch2_cli

GOOD_ALT = (
    "Line chart of training compute rising from 2010 to 2026 on a logarithmic axis."
)
SECOND_ALT = "Flow diagram in which a request passes through a wrapper to a tool."


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "chapter.qmd"
    path.write_text(body, encoding="utf-8")
    return path


def _codes(path: Path) -> set[str]:
    return {finding.code for finding in arch2_cli.alt_text_findings([path])}


def _figure(
    alt: str,
    caption: str = "**Compute grows quickly.** Notable models over time",
    label: str = "fig-a",
) -> str:
    return f'![{caption}](images/{label}){{#{label} width="100%" fig-alt="{alt}"}}\n'


def test_parser_sees_a_figure_whose_caption_cites_a_source(tmp_path: Path) -> None:
    # The regex this parser replaced stopped at the first "]", so a caption
    # carrying [@Key] hid its figure; 20 of 60 book figures went unchecked.
    path = _write(
        tmp_path,
        '![**Lead.** Data from [@Key2024].](images/fig-a){#fig-a width="100%"}\n',
    )

    assert [image.label for image in arch2_cli.figure_image_records(path)] == ["fig-a"]
    assert "figure-alt" in _codes(path)


def test_parser_reads_attributes_split_across_lines(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        f'![**Lead.** Body [@Key].](images/fig-a){{#fig-a width="100%"\nfig-alt="{GOOD_ALT}"}}\n',
    )

    (image,) = arch2_cli.figure_image_records(path)
    assert image.alt == GOOD_ALT
    assert image.alt_line == 2
    assert _codes(path) == set()


def test_unlabeled_image_needs_alt_text(tmp_path: Path) -> None:
    assert "figure-alt" in _codes(_write(tmp_path, "![](images/ch01-cover-map.svg)\n"))


def test_code_cell_figure_reads_block_scalar_alt(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "```{python}\n"
        "#| label: fig-a\n"
        "#| fig-cap: |\n"
        "#|   **Lead.** Body.\n"
        "#| fig-alt: |\n"
        "#|   Line chart of training compute rising from 2010\n"
        "#|   to 2026 on a logarithmic axis.\n"
        "print(1)\n"
        "```\n",
    )

    (image,) = arch2_cli.figure_image_records(path)
    assert image.kind == "chunk"
    assert image.alt == GOOD_ALT
    assert _codes(path) == set()


def test_images_inside_code_fences_are_not_figures(tmp_path: Path) -> None:
    path = _write(tmp_path, "```markdown\n![](images/example.svg)\n```\n")
    assert arch2_cli.figure_image_records(path) == []


@pytest.mark.parametrize(
    ("alt", "code"),
    [
        (
            "Line chart of training compute rising from 2010 to 2026",
            "alt-text-full-stop",
        ),
        (
            "Line chart of **training compute** rising from 2010 to 2026.",
            "alt-text-markup",
        ),
        (
            "Line chart of training compute rising to 58% by 2026.",
            "alt-text-read-aloud",
        ),
        (
            "Line chart of training compute rising 3.8x from 2010 to 2026.",
            "alt-text-read-aloud",
        ),
        (
            "Training compute rises from 2010 to 2026 on a logarithmic axis.",
            "alt-text-image-type",
        ),
        (
            "Image of a line chart of training compute rising over time.",
            "alt-text-redundant-prefix",
        ),
        ("TODO line chart of training compute over time.", "alt-text-placeholder"),
        ("Line chart of compute.", "alt-text-too-short"),
        ("Line chart of training compute; compare @fig-other.", "figure-alt-reference"),
    ],
)
def test_alt_text_rule_fires(tmp_path: Path, alt: str, code: str) -> None:
    assert code in _codes(_write(tmp_path, _figure(alt)))


def test_well_formed_alt_text_passes(tmp_path: Path) -> None:
    assert _codes(_write(tmp_path, _figure(GOOD_ALT))) == set()


def test_alt_text_must_not_repeat_the_caption(tmp_path: Path) -> None:
    caption = (
        "**Compute grows quickly.** Line chart of training compute rising from 2010 "
        "to 2026 on a logarithmic axis"
    )
    assert "alt-text-echoes-caption" in _codes(
        _write(tmp_path, _figure(GOOD_ALT, caption))
    )


def test_duplicate_alt_text_is_rejected(tmp_path: Path) -> None:
    body = _figure(GOOD_ALT) + "\n" + _figure(GOOD_ALT, label="fig-b")
    assert "alt-text-duplicate" in _codes(_write(tmp_path, body))


def test_missing_full_stop_is_a_deterministic_repair(tmp_path: Path) -> None:
    path = _write(tmp_path, _figure(GOOD_ALT.rstrip(".")))

    (finding,) = [
        finding
        for finding in arch2_cli.alt_text_findings([path])
        if finding.code == "alt-text-full-stop"
    ]
    assert finding.fixable
    line = path.read_text(encoding="utf-8").splitlines()[0]
    repaired = arch2_cli.apply_line_edits(line, [(finding.span, finding.replacement)])
    assert f'fig-alt="{GOOD_ALT}"' in repaired


def test_pdf_build_routes_alt_text_to_springer_description() -> None:
    header = (arch2_cli.BOOK_DIR / "tex" / "springer-header.tex").read_text(
        encoding="utf-8"
    )
    springer_class = (arch2_cli.BOOK_DIR / "SNmono.cls").read_text(encoding="utf-8")

    assert arch2_cli.ALT_TEXT_DESCRIPTION_HOOK in header
    assert arch2_cli.SNMONO_DESCRIPTION_MACRO in springer_class
    assert arch2_cli.alt_text_wiring_findings() == []


def test_render_check_reconciles_description_texts(tmp_path: Path) -> None:
    source = _write(
        tmp_path, _figure(GOOD_ALT) + "\n" + _figure(SECOND_ALT, label="fig-b")
    )
    images = arch2_cli.figure_image_records(source)
    recorded = tmp_path / "DescriptionTexts.txt"

    recorded.write_text(
        f"1 (Fig. 1.1) - {GOOD_ALT}\n2 (Fig. 1.2) - {SECOND_ALT}\n", encoding="utf-8"
    )
    assert arch2_cli.description_texts_findings(recorded, images) == []

    recorded.write_text(f"1 (Fig. 1.1) - {GOOD_ALT}\n", encoding="utf-8")
    codes = {f.code for f in arch2_cli.description_texts_findings(recorded, images)}
    assert "alt-text-pdf-count" in codes

    recorded.write_text(
        f"1 (Fig. 1.1) - Something else entirely.\n2 (Fig. 1.1) - {SECOND_ALT}\n",
        encoding="utf-8",
    )
    codes = {f.code for f in arch2_cli.description_texts_findings(recorded, images)}
    assert {"alt-text-pdf-mismatch", "alt-text-pdf-duplicate"} <= codes


def test_render_check_rejects_latex_escapes_in_descriptions(tmp_path: Path) -> None:
    # Pandoc escapes an apostrophe as \textquotesingle{}; the letters-only match
    # would pass it, so the escape itself must fail the check.
    alt = "Loop diagram of a placement policy's actions and the floorplan state."
    source = _write(tmp_path, _figure(alt))
    recorded = tmp_path / "DescriptionTexts.txt"
    recorded.write_text(
        "1 (Fig. 1.1) - Loop diagram of a placement policy\\textquotesingle {}s "
        "actions and the floorplan state.\n",
        encoding="utf-8",
    )

    findings = arch2_cli.description_texts_findings(
        recorded, arch2_cli.figure_image_records(source)
    )

    assert [finding.code for finding in findings] == ["alt-text-pdf-escape"]


def test_pdf_build_keeps_description_texts_past_scratch_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The build deletes DescriptionTexts.txt with the other LaTeX byproducts, so
    # it must copy the file out first, and never leave a stale copy behind.
    latex_output = tmp_path / "book" / "DescriptionTexts.txt"
    preserved = tmp_path / "_build" / "springer" / "DescriptionTexts.txt"
    latex_output.parent.mkdir(parents=True)
    monkeypatch.setattr(arch2_cli, "LATEX_DESCRIPTION_TEXTS_PATH", latex_output)
    monkeypatch.setattr(arch2_cli, "DESCRIPTION_TEXTS_PATH", preserved)

    latex_output.write_text(f"1 (Fig. 1.1) - {GOOD_ALT}\n", encoding="utf-8")
    arch2_cli.preserve_description_texts()
    assert preserved.read_text(encoding="utf-8") == f"1 (Fig. 1.1) - {GOOD_ALT}\n"

    latex_output.unlink()
    arch2_cli.preserve_description_texts()
    assert not preserved.exists()
    assert "DescriptionTexts.txt" in arch2_cli._LATEX_SCRATCH_PATTERNS


def test_missing_description_texts_is_reported(tmp_path: Path) -> None:
    findings = arch2_cli.description_texts_findings(
        tmp_path / "DescriptionTexts.txt", []
    )
    assert [finding.code for finding in findings] == ["alt-text-pdf-missing"]


def test_export_sheets_number_figures_per_chapter(tmp_path: Path) -> None:
    chapter = tmp_path / "chapters" / "03-lifecycle"
    chapter.mkdir(parents=True)
    source = chapter / "03-lifecycle.qmd"
    source.write_text(
        '![](images/ch03-cover-map.svg){fig-alt="Chapter overview diagram of six activities."}\n\n'
        + _figure(GOOD_ALT, caption="**AI-assisted EDA tools need checks.** Body")
        + "\n"
        + _figure(SECOND_ALT, label="fig-b"),
        encoding="utf-8",
    )

    sheets = arch2_cli.alt_text_export_sheets(
        arch2_cli.figure_image_records(source), None
    )

    assert [name for name, _ in sheets] == ["All images", "Chapter 3"]
    rows = sheets[1][1]
    assert [row[1] for row in rows[1:]] == [
        "unnumbered (chapter opening)",
        "3.1",
        "3.2",
    ]
    assert [row[2] for row in rows[1:]] == ["", "fig3_1", "fig3_2"]
    # The headline keeps its case; acronyms must survive into the workbook.
    assert rows[2][5] == "AI-assisted EDA tools need checks."


def test_xlsx_writer_produces_a_well_formed_workbook(tmp_path: Path) -> None:
    out = tmp_path / "alt.xlsx"
    arch2_cli.write_xlsx(
        out,
        [
            (
                "All images",
                [["Figure", "Alt text", "Words"], ["1.1", "Chart <a> & b.", 4]],
            ),
            ("Chapter 1", [["Figure"], ["1.1"]]),
        ],
    )

    with zipfile.ZipFile(out) as archive:
        names = set(archive.namelist())
        for name in names:
            ElementTree.fromstring(archive.read(name))
        workbook = archive.read("xl/workbook.xml").decode()
        sheet = archive.read("xl/worksheets/sheet1.xml").decode()

    assert {
        "[Content_Types].xml",
        "_rels/.rels",
        "xl/workbook.xml",
        "xl/_rels/workbook.xml.rels",
        "xl/styles.xml",
        "xl/worksheets/sheet1.xml",
        "xl/worksheets/sheet2.xml",
    } <= names
    assert 'name="All images"' in workbook and 'name="Chapter 1"' in workbook
    assert "Chart &lt;a&gt; &amp; b." in sheet
    assert "<v>4</v>" in sheet


def test_figure_that_draws_a_table_is_flagged(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "```{python}\n"
        "#| label: fig-a\n"
        f'#| fig-alt: "{GOOD_ALT}"\n'
        "fig, ax = plt.subplots()\n"
        "ax.table(cellText=[[1]])\n"
        "```\n",
    )

    findings = arch2_cli.alt_text_findings([path])

    assert [(f.severity, f.code) for f in findings] == [
        ("warning", "figure-renders-table")
    ]


def test_manuscript_alt_text_meets_the_contract() -> None:
    findings = arch2_cli._filter_suppressed(arch2_cli.alt_text_findings())
    errors = [f"{f.code} {f.location}" for f in findings if f.severity == "error"]
    assert errors == []
