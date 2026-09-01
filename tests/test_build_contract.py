from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

import cli.arch2 as arch2_cli


runner = CliRunner()


def _write_part_manifest_fixture(tmp_path) -> Path:
    book = tmp_path / "book"
    files = (
        "index.qmd",
        "contents/frontmatter/preface.qmd",
        "contents/frontmatter/acknowledgments.qmd",
        "contents/frontmatter/about-the-author.qmd",
        "contents/frontmatter/disclosure.qmd",
        "contents/parts/part-i.qmd",
        "contents/chapters/01-one.qmd",
        "contents/backmatter/appendix-a.qmd",
    )
    for relative in files:
        path = book / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if relative == "index.qmd":
            path.write_text(
                "{{< include contents/frontmatter/preface.qmd >}}\n",
                encoding="utf-8",
            )
        else:
            path.write_text(f"# {path.stem}\n", encoding="utf-8")

    (book / "_quarto.yml").write_text(
        "book:\n"
        "  chapters:\n"
        "    - index.qmd\n"
        "    - contents/frontmatter/acknowledgments.qmd\n"
        "    - contents/frontmatter/about-the-author.qmd\n"
        "    - contents/frontmatter/disclosure.qmd\n"
        "    - ---\n"
        "    - part: contents/parts/part-i.qmd\n"
        "      chapters:\n"
        "        - contents/chapters/01-one.qmd\n"
        "  appendices:\n"
        "    - contents/backmatter/appendix-a.qmd\n",
        encoding="utf-8",
    )
    return book


def _point_cli_at_book(monkeypatch: pytest.MonkeyPatch, root: Path, book: Path) -> None:
    monkeypatch.setattr(arch2_cli, "ROOT", root)
    monkeypatch.setattr(arch2_cli, "BOOK_DIR", book)
    monkeypatch.setattr(
        arch2_cli,
        "CONTENT_ROOTS",
        (
            book / "contents" / "chapters",
            book / "contents" / "parts",
            book / "contents" / "backmatter",
        ),
    )
    monkeypatch.setattr(
        arch2_cli,
        "BOOK_PREFACE_SOURCE",
        book / "contents" / "frontmatter" / "preface.qmd",
    )
    monkeypatch.setattr(
        arch2_cli,
        "BOOK_INCLUDE_ONLY_SOURCES",
        (book / "contents" / "frontmatter" / "preface.qmd",),
    )
    monkeypatch.setattr(
        arch2_cli,
        "BOOK_FRONTMATTER",
        (
            book / "index.qmd",
            book / "contents" / "frontmatter" / "foreword.qmd",
            book / "contents" / "frontmatter" / "acknowledgments.qmd",
            book / "contents" / "frontmatter" / "about-the-author.qmd",
            book / "contents" / "frontmatter" / "disclosure.qmd",
        ),
    )


def test_manifest_includes_qmd_backed_part_opener(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    book = _write_part_manifest_fixture(tmp_path)
    _point_cli_at_book(monkeypatch, tmp_path, book)

    findings = arch2_cli.manifest_findings()

    assert not [finding for finding in findings if finding.code == "orphan-qmd"]
    assert (
        book / "contents" / "parts" / "part-i.qmd"
    ).resolve() in arch2_cli._manifest_qmd_entries(arch2_cli._load_quarto_config()[0])


def test_book_order_places_part_opener_before_its_chapter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    book = _write_part_manifest_fixture(tmp_path)
    _point_cli_at_book(monkeypatch, tmp_path, book)

    ordered = [
        path.relative_to(book).as_posix() for path in arch2_cli.book_ordered_qmd_files()
    ]

    assert ordered == [
        "index.qmd",
        "contents/frontmatter/acknowledgments.qmd",
        "contents/frontmatter/about-the-author.qmd",
        "contents/frontmatter/disclosure.qmd",
        "contents/parts/part-i.qmd",
        "contents/chapters/01-one.qmd",
        "contents/backmatter/appendix-a.qmd",
        "contents/frontmatter/preface.qmd",
    ]


def test_release_render_restores_version_source(tmp_path) -> None:
    version_tex = tmp_path / "version.tex"
    original = "\\def\\ArchTwoReleaseVersion{Development build}\n"
    version_tex.write_text(original)

    with arch2_cli._temporary_version_tex(version_tex, "Release v1.2.3+gabcdef1"):
        assert version_tex.read_text() == (
            "\\def\\ArchTwoReleaseVersion{Release v1.2.3+gabcdef1}\n"
        )

    assert version_tex.read_text() == original


def test_tool_subsite_rewrites_all_root_navigation_targets() -> None:
    build_script = (
        arch2_cli.ROOT / ".github" / "scripts" / "build_site.sh"
    ).read_text()
    for target in (
        "about",
        "start",
        "readings",
        "workshops",
        "submit",
        "submit-resource",
        "submit-workshop",
    ):
        assert (
            f's#href="\\./{target}\\.html"#href="../{target}.html"#g;' in build_script
        )
    assert "assembled tool pages retain root-relative navigation links" in build_script


def test_local_build_guide_activates_its_documented_environment() -> None:
    guide = (arch2_cli.ROOT / "CONTRIBUTING.md").read_text()
    activation = guide.index("source .venv/bin/activate")
    build = guide.index("SKIP_BOOK=1 .github/scripts/build_site.sh")
    assert activation < build
    assert "Quarto 1.9.36" in guide[:build]


def test_site_build_does_not_bypass_generated_asset_cleanliness() -> None:
    build_script = (
        arch2_cli.ROOT / ".github" / "scripts" / "build_site.sh"
    ).read_text()

    assert "ARCH2_SKIP_ASSET_DRIFT=1 ./arch2" not in build_script
    assert "./arch2 render --no-layout" in build_script


def test_html_title_strip_uses_release_language() -> None:
    title_enhancement = (
        arch2_cli.ROOT / "book" / "_includes" / "author-link.html"
    ).read_text()

    assert "arch2-release-meta" in title_enhancement
    assert "Development build" in title_enhancement
    assert "'Release ' + displayVersion" in title_enhancement
    assert "Preview" not in title_enhancement


def test_build_help_matches_standard_artifact_contract() -> None:
    result = runner.invoke(arch2_cli.app, ["build", "--help"])
    assert result.exit_code == 0, result.output
    assert "Defaults to HTML + PDF + EPUB" in result.output
    assert "arch2 check standard" in result.output


def test_footnote_source_check_accepts_reference_style(tmp_path) -> None:
    chapter = tmp_path / "chapter.qmd"
    chapter.write_text(
        "An optional term.[^fn-example-c03]\n\n"
        "[^fn-example-c03]: **Example term**: A compact optional gloss.\n"
    )

    assert arch2_cli.footnote_source_findings([chapter]) == []


def test_footnote_source_check_rejects_inline_and_malformed_notes(tmp_path) -> None:
    chapter = tmp_path / "chapter.qmd"
    chapter.write_text(
        "Inline note.^[This should be referenced.]\n\n"
        "[^example]: **Example term:** The colon is inside the bold span.\n"
    )

    codes = {finding.code for finding in arch2_cli.footnote_source_findings([chapter])}
    assert codes == {"inline-footnote", "footnote-id", "footnote-term-head"}


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        ([], "all"),
        (["--all"], "all"),
        (["--html", "--pdf", "--epub"], "all"),
        (["--pdf"], "pdf"),
        (["--html", "--pdf"], "html,pdf"),
    ],
)
def test_build_selects_coherent_format_set(
    monkeypatch: pytest.MonkeyPatch, args: list[str], expected: str
) -> None:
    calls: list[str] = []

    def fake_render(to: str, **_: object) -> None:
        calls.append(to)

    monkeypatch.setattr(arch2_cli, "_render_one", fake_render)
    result = runner.invoke(arch2_cli.app, ["build", *args])
    assert result.exit_code == 0, result.output
    assert calls == [expected]


def test_abbreviations_findings_empty_on_repository() -> None:
    findings = arch2_cli.abbreviations_findings()
    assert findings == [], f"Found abbreviation issues: {[f.message for f in findings]}"


@pytest.mark.parametrize(
    ("prose", "abbr", "expected"),
    [
        # The expansion stops at the acronym's own words, and does not run
        # backwards into whatever preceded them.
        ("chips and Google Tensor Processing Unit", "TPU", "Tensor Processing Unit"),
        (
            "Each integrated domain-specific architecture",
            "DSA",
            "domain-specific architecture",
        ),
        ("a plain frames per second", "FPS", "frames per second"),
        (
            "a destructive complementary metal-oxide-semiconductor",
            "CMOS",
            "complementary metal-oxide-semiconductor",
        ),
        (
            "aspect-ratio limits and minimum static noise margins",
            "SNM",
            "static noise margins",
        ),
        # Function words inside an expansion are skipped, not counted.
        (
            "whether Pareto rankings survive dynamic voltage and frequency scaling",
            "DVFS",
            "dynamic voltage and frequency scaling",
        ),
        (
            "scored with Holistic Evaluation of Language Models",
            "HELM",
            "Holistic Evaluation of Language Models",
        ),
        # An all-caps or numeric tail contributes all of its characters.
        (
            "processes that prohibit uploading Graphic Database System II",
            "GDSII",
            "Graphic Database System II",
        ),
        (
            "lowered through the Flexible Intermediate Representation for RTL",
            "FIRRTL",
            "Flexible Intermediate Representation for RTL",
        ),
        (
            "the bus speaks Advanced eXtensible Interface 5",
            "AXI5",
            "Advanced eXtensible Interface 5",
        ),
        # Parentheticals that are not expansions yield nothing to register.
        ("governed by International Organization for Standardization", "ISO", None),
        ("demonstrated by the historic Pentium floating-point division", "FDIV", None),
        ("quantized to 8-bit integer", "INT8", None),
        ("as reported by prior work", "AI", None),
    ],
)
def test_prose_expansion_matches_only_the_acronyms_own_words(
    prose, abbr, expected
) -> None:
    assert arch2_cli._match_prose_expansion(prose, abbr) == expected


def test_unregistered_abbreviation_reports_the_real_expansion(tmp_path) -> None:
    """A registry suggestion must be pasteable, not padded with stray prose."""
    chapter = tmp_path / "chapter.qmd"
    chapter.write_text(
        "Modern accelerators and Google Zonal Tensor Unit (ZTU) parts diverge.\n",
        encoding="utf-8",
    )
    findings = arch2_cli.abbreviations_findings([chapter])
    unregistered = [f for f in findings if f.code == "unregistered-abbreviation"]
    assert len(unregistered) == 1
    assert "'ZTU' is expanded as 'Zonal Tensor Unit'" in unregistered[0].message
    assert "and Google" not in unregistered[0].message


def test_expansion_may_span_a_comma(tmp_path) -> None:
    """Comma-separated expansions are real abbreviations, not invisible ones."""
    chapter = tmp_path / "chapter.qmd"
    chapter.write_text(
        "The kernel uses a bespoke, unregistered wide instruction, multiple lanes (WIML) form.\n",
        encoding="utf-8",
    )
    findings = arch2_cli.abbreviations_findings([chapter])
    unregistered = [f for f in findings if f.code == "unregistered-abbreviation"]
    assert len(unregistered) == 1
    assert (
        "'WIML' is expanded as 'wide instruction, multiple lanes'"
        in unregistered[0].message
    )


def test_abbreviations_findings_catches_unexpanded_and_overcapitalized(
    tmp_path,
) -> None:
    chapter = tmp_path / "chapter.qmd"
    chapter.write_text(
        "First mention of RTL without definition.\n"
        "And Process Design Kit (PDK) with overcapitalized expansion.\n",
        encoding="utf-8",
    )
    findings = arch2_cli.abbreviations_findings([chapter])
    codes = {f.code for f in findings}
    assert "unexpanded-abbreviation" in codes
    assert "overcapitalized-expansion" in codes


def test_abbreviations_cli_command() -> None:
    result = runner.invoke(arch2_cli.app, ["check", "abbreviations"])
    assert result.exit_code == 0, result.output
    assert "passed abbreviations & acronyms" in result.output


def test_glossary_findings_empty_on_repository() -> None:
    findings = arch2_cli.glossary_findings()
    assert findings == [], f"Found glossary issues: {[f.message for f in findings]}"


def test_glossary_findings_detects_drift(tmp_path, monkeypatch) -> None:
    fake_qmd = tmp_path / "apdx-d-glossary.qmd"
    fake_qmd.write_text("Stale content\n", encoding="utf-8")
    monkeypatch.setattr(arch2_cli, "GLOSSARY_PATH", fake_qmd)
    findings = arch2_cli.glossary_findings()
    codes = {f.code for f in findings}
    assert "glossary-drift" in codes


def test_glossary_cli_commands() -> None:
    # Test check glossary
    check_res = runner.invoke(arch2_cli.app, ["check", "glossary"])
    assert check_res.exit_code == 0, check_res.output
    assert "passed glossary & acronym catalog" in check_res.output

    # Test generate glossary
    gen_res = runner.invoke(arch2_cli.app, ["generate", "glossary"])
    assert gen_res.exit_code == 0, gen_res.output
    assert "generated" in gen_res.output


def test_abbreviations_detects_unregistered_terms(tmp_path: Path) -> None:
    chapter = tmp_path / "01-sample.qmd"
    chapter.write_text(
        "# Sample\n\nWe introduce low-density parity-check (LDPC) codes for memory protection.\n",
        encoding="utf-8",
    )
    findings = arch2_cli.abbreviations_findings([chapter])
    unregistered = [f for f in findings if f.code == "unregistered-abbreviation"]
    assert len(unregistered) == 1
    assert unregistered[0].severity == "warning"
    assert "LDPC" in unregistered[0].message
    assert "CMOS_ABBREVIATIONS" in unregistered[0].message
    assert "./arch2 generate glossary" in unregistered[0].message
