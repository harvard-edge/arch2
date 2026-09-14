"""Book-integrity contract: structure, rendered-output, and Springer delivery checks.

Each test pins one rule the CLI enforces so a broken manuscript cannot pass
quietly: heading structure, chapter closers, float order, table cells, page
references, unused images, PDF fonts and metadata, EPUB accessibility metadata,
HTML alt attributes, and the Springer delivery report.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
import yaml

import cli.arch2 as arch2_cli

ALT = "Line chart of training compute rising from 2010 to 2026 on a logarithmic axis."


def _write(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _codes(findings: list[arch2_cli.Finding]) -> list[str]:
    return [finding.code for finding in findings]


def _chapter(tmp_path: Path, body: str) -> Path:
    return _write(tmp_path / "chapters" / "03-lifecycle" / "03-lifecycle.qmd", body)


CLOSER = "## Open Questions\n\nText.\n\n## Summary\n\nText.\n"


def test_heading_level_skip_and_end_punctuation(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "a.qmd",
        "---\ntitle: x\n# not a heading\n---\n\n# Chapter\n\n### Skipped {#sec-x}\n\n## Fine\n\n## Ends badly.\n",
    )

    assert _codes(arch2_cli.heading_findings(path)) == [
        "heading-level-skip",
        "heading-end-punctuation",
    ]


def test_headings_inside_code_fences_are_ignored(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "a.qmd", "# Chapter\n\n```python\n#### comment.\n```\n\n## Section\n"
    )
    assert arch2_cli.heading_findings(path) == []


def test_chapter_must_close_with_open_questions_then_summary(tmp_path: Path) -> None:
    good = _chapter(tmp_path, "# Chapter\n\n## Body\n\n" + CLOSER)
    assert arch2_cli.chapter_closer_findings(good) == []

    bad = _chapter(tmp_path, "# Chapter\n\n## Common Pitfalls\n\n## Summary\n")
    assert _codes(arch2_cli.chapter_closer_findings(bad)) == ["chapter-closer"]

    not_a_chapter = _write(
        tmp_path / "frontmatter" / "preface.qmd", "# Preface\n\n## Body\n"
    )
    assert arch2_cli.chapter_closer_findings(not_a_chapter) == []


def test_figure_mentioned_only_after_it_appears_is_flagged(tmp_path: Path) -> None:
    late = _write(
        tmp_path / "late.qmd",
        f'![**Lead.** Body.](images/fig-a){{#fig-a fig-alt="{ALT}"}}\n\nAs @fig-a shows.\n',
    )
    assert _codes(arch2_cli.float_order_findings(late)) == ["float-mentioned-late"]

    early = _write(
        tmp_path / "early.qmd",
        f'The trend in @fig-a matters.\n\n![**Lead.** Body.](images/fig-a){{#fig-a fig-alt="{ALT}"}}\n\nAgain @fig-a.\n',
    )
    assert arch2_cli.float_order_findings(early) == []

    chunk = _write(
        tmp_path / "chunk.qmd",
        "```{python}\n#| label: fig-b\nprint(1)\n```\n\nLater @fig-b.\n",
    )
    assert _codes(arch2_cli.float_order_findings(chunk)) == ["float-mentioned-late"]


def test_page_number_reference_is_rejected_but_citation_locator_is_not(
    tmp_path: Path,
) -> None:
    path = _write(
        tmp_path / "a.qmd",
        "> Quoted line [@Conway1981MPCAdventures, p. 2]\n\nThe proof is on page 12.\n",
    )
    findings = arch2_cli.structural_reference_findings(path)
    assert [(f.code, f.location.rsplit(":", 1)[1]) for f in findings] == [
        ("page-number-reference", "3")
    ]


def test_empty_table_cell_is_rejected(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "a.qmd",
        "| A | B |\n| --- | ---: |\n| x |  |\n| y | 2 |\n",
    )
    assert _codes(
        [f for f in arch2_cli.table_findings(path) if f.code == "table-empty-cell"]
    ) == ["table-empty-cell"]


def test_unused_image_is_a_warning(tmp_path: Path) -> None:
    images = tmp_path / "chapters" / "01-x" / "images"
    _write(images / "used-plot.svg", "<svg/>")
    _write(images / "stray-photo.png", "png")

    findings = arch2_cli.unused_image_findings(
        tmp_path, corpus="![caption](images/used-plot)"
    )

    assert [(f.severity, f.code, Path(f.location).name) for f in findings] == [
        ("warning", "image-unreferenced", "stray-photo.png")
    ]


def _pdf(tmp_path: Path, *, title: str, author: str, lang: str | None) -> Path:
    from pypdf import PdfWriter
    from pypdf.generic import NameObject, TextStringObject

    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_metadata({"/Title": title, "/Author": author})
    if lang:
        writer._root_object[NameObject("/Lang")] = TextStringObject(lang)
    path = tmp_path / "book.pdf"
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def test_pdf_metadata_and_language_are_required(tmp_path: Path) -> None:
    config, _ = arch2_cli._load_quarto_config()
    title = config["book"]["title"]
    author = config["book"]["author"]

    good = _pdf(tmp_path, title=title, author=author, lang="en-US")
    assert arch2_cli.pdf_findings(good) == []

    bad = _pdf(tmp_path, title="Draft", author="", lang=None)
    assert _codes(arch2_cli.pdf_findings(bad)) == [
        "pdf-metadata-title",
        "pdf-metadata-author",
        "pdf-language",
    ]


def _epub(tmp_path: Path, meta: str) -> Path:
    opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:language>en-US</dc:language>{meta}
  </metadata>
</package>
"""
    path = tmp_path / "book.epub"
    with zipfile.ZipFile(path, "w") as epub:
        epub.writestr("EPUB/content.opf", opf)
        epub.writestr(
            "EPUB/text/ch001.xhtml",
            '<html xmlns="http://www.w3.org/1999/xhtml"><body><p>Text</p></body></html>',
        )
    return path


def test_epub_requires_accessibility_metadata(tmp_path: Path) -> None:
    bare = _epub(tmp_path, "")
    assert "epub-accessibility-metadata" in _codes(arch2_cli.epub_findings(bare))

    complete = _epub(
        tmp_path,
        "".join(
            f'<meta property="{name}">value</meta>'
            for name in arch2_cli.EPUB_ACCESSIBILITY_PROPERTIES
        ),
    )
    assert "epub-accessibility-metadata" not in _codes(
        arch2_cli.epub_findings(complete)
    )


def test_book_config_declares_epub_accessibility_metadata() -> None:
    config = yaml.safe_load(
        (arch2_cli.BOOK_DIR / "_quarto.yml").read_text(encoding="utf-8")
    )
    epub = config["format"]["epub"]
    for key in (
        "accessModes",
        "accessModeSufficient",
        "accessibilityFeatures",
        "accessibilityHazards",
        "accessibilitySummary",
    ):
        assert epub.get(key), key
    assert "alternativeText" in epub["accessibilityFeatures"]


def test_html_image_without_alt_is_rejected(tmp_path: Path) -> None:
    index = _write(tmp_path / "index.html", '<div class="arch2-release-meta"></div>')
    _write(tmp_path / "chapters" / "a.html", '<p><img src="figure.svg"></p>')
    _write(tmp_path / "chapters" / "b.html", '<p><img src="icon.svg" alt=""></p>')

    findings = [f for f in arch2_cli.html_findings(index) if f.code == "html-image-alt"]

    assert [Path(f.location).name for f in findings] == ["a.html"]


def test_orcid_badge_gets_an_accessible_name(tmp_path: Path) -> None:
    # Quarto's author template links ORCID through a bare <img>; the build
    # repairs it so the alt-text check can stay strict.
    page = _write(
        tmp_path / "chapters" / "a.html",
        '<a href="https://orcid.org/0000" class="quarto-title-author-orcid"> '
        '<img src="data:image/png;base64,AAAA"></a>'
        '<a class="quarto-title-author-orcid"><img src="x.png" alt="kept"></a>',
    )

    assert arch2_cli.normalize_html_orcid_icons(tmp_path) == 1
    text = page.read_text(encoding="utf-8")
    assert '<img alt="ORCID iD" src="data:image/png;base64,AAAA">' in text
    assert 'alt="kept"' in text and text.count("alt=") == 2
    assert arch2_cli.normalize_html_orcid_icons(tmp_path) == 0


def test_image_pixel_width_reads_png_and_jpeg_headers(tmp_path: Path) -> None:
    png = tmp_path / "a.png"
    png.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\x0dIHDR"
        + (2400).to_bytes(4, "big")
        + b"\x00" * 8
    )
    jpeg = tmp_path / "a.jpg"
    jpeg.write_bytes(
        b"\xff\xd8"
        + b"\xff\xe0\x00\x04\x00\x00"
        + b"\xff\xc0\x00\x11\x08"
        + (600).to_bytes(2, "big")
        + (1800).to_bytes(2, "big")
        + b"\x00" * 12
    )

    assert arch2_cli.image_pixel_width(png) == 2400
    assert arch2_cli.image_pixel_width(jpeg) == 1800


def test_raster_artwork_below_springer_floor_is_flagged(tmp_path: Path) -> None:
    chapter = _write(
        tmp_path / "chapters" / "05-methods" / "05-methods.qmd",
        f'![**Lead.** Body.](images/plot.png){{#fig-plot fig-alt="{ALT}"}}\n',
    )
    png = chapter.parent / "images" / "plot.png"
    png.parent.mkdir(parents=True)
    png.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\x0dIHDR"
        + (1500).to_bytes(4, "big")
        + b"\x00" * 8
    )
    images = arch2_cli.figure_image_records(chapter)

    line_art = arch2_cli.artwork_resolution_findings(images)
    assert _codes(line_art) == ["delivery-artwork-resolution"]

    photo = arch2_cli.artwork_resolution_findings(
        images, {"figures": {"fig-plot": {"artwork": "photo"}}}
    )
    assert photo == []


def test_chapter_metadata_requires_abstract_and_keywords(tmp_path: Path) -> None:
    chapter = _chapter(tmp_path, "# Chapter\n")
    config = tmp_path / "springer-delivery.yml"

    assert _codes(arch2_cli.springer_chapter_metadata_findings(config, [chapter])) == [
        "delivery-chapter-metadata"
    ]

    config.write_text(
        yaml.safe_dump(
            {
                "chapters": {
                    "03-lifecycle": {
                        "abstract": "A standalone abstract. " * 5,
                        "keywords": ["design loop", "evaluation", "life cycle"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    assert arch2_cli.springer_chapter_metadata_findings(config, [chapter]) == []

    config.write_text(
        yaml.safe_dump(
            {
                "chapters": {
                    "03-lifecycle": {"abstract": "See @sec-x.", "keywords": ["one"]}
                }
            }
        ),
        encoding="utf-8",
    )
    assert _codes(arch2_cli.springer_chapter_metadata_findings(config, [chapter])) == [
        "delivery-abstract-standalone",
        "delivery-keywords-count",
    ]


def test_chapter_reference_lists_are_required(tmp_path: Path) -> None:
    with_refs = _chapter(tmp_path, "# Chapter\n\n## References\n\n::: {#refs}\n:::\n")
    assert arch2_cli.chapter_reference_list_findings([with_refs]) == []

    without = _write(tmp_path / "chapters" / "04-x" / "04-x.qmd", "# Chapter\n")
    assert _codes(arch2_cli.chapter_reference_list_findings([without])) == [
        "delivery-chapter-references"
    ]


def test_permissions_ledger_blocks_uncleared_material(tmp_path: Path) -> None:
    source = _write(
        tmp_path / "a.qmd",
        f'![**Lead.** Body.](images/fig-a){{#fig-a fig-alt="{ALT}"}}\n\n'
        f'![**Lead.** Body.](images/fig-b){{#fig-b fig-alt="{ALT.replace("Line", "Bar")}"}}\n',
    )
    images = arch2_cli.figure_image_records(source)
    ledger = tmp_path / "permissions.yml"

    assert _codes(arch2_cli.permissions_ledger_findings(ledger, images)) == [
        "delivery-permissions"
    ]

    ledger.write_text(
        yaml.safe_dump(
            {
                "figures": {
                    "fig-a": {"origin": "original", "color_in_print": False},
                    "fig-b": {
                        "origin": "third-party",
                        "source": "Vendor press kit",
                        "license": "All Rights Reserved",
                        "permission": "requested",
                        "color_in_print": True,
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    assert _codes(arch2_cli.permissions_ledger_findings(ledger, images)) == [
        "delivery-permissions-uncleared"
    ]


def test_manuscript_structure_meets_the_contract() -> None:
    findings = arch2_cli._filter_suppressed(arch2_cli.structure_findings())
    errors = [f"{f.code} {f.location}" for f in findings if f.severity == "error"]
    assert errors == []


@pytest.mark.parametrize(
    "command",
    [("validate", "structure"), ("verify", "pdf"), ("check", "delivery")],
)
def test_integrity_commands_are_registered(command: tuple[str, str]) -> None:
    from typer.testing import CliRunner

    result = CliRunner().invoke(arch2_cli.app, [command[0], "--help"])
    assert command[1] in result.output
