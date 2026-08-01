from __future__ import annotations

import pytest
from typer.testing import CliRunner

import cli.arch2 as arch2_cli


runner = CliRunner()


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
