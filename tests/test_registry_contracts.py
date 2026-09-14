from __future__ import annotations

import datetime as dt
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import pytest
import yaml

from tools.render_awesome import OUTPUT_PATH, render
from tools.validate_registries import (
    ROOT,
    TOOL_DIR,
    WORKSHOP_DIR,
    WORKSHOP_SCHEMA,
    TOOL_SCHEMA,
    _schema_errors,
    _semantic_errors,
    validate,
)


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


class _FragmentAuditParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.attributes: list[tuple[str, str | None]] = []
        self.tags: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        self.attributes.extend(attrs)


def test_registry_contracts_and_generated_indexes_are_current() -> None:
    assert validate() == []


def test_every_tool_exposes_availability_and_verification_date() -> None:
    for path in TOOL_DIR.glob("*.yml"):
        tool = _load(path)
        assert tool["artifact_availability"]
        assert tool["last_verified"]


def test_unverified_tool_uses_explicit_null_date(tmp_path: Path) -> None:
    tool = {
        "title": "Unverified test",
        "url": "https://example.com/tool",
        "artifact_type": "Tool",
        "categories": ["Simulation"],
        "description": "A fixture for the unverified state.",
        "fit_note": "Exercises availability validation.",
        "artifact_availability": "unverified",
    }
    path = tmp_path / "unverified.yml"
    path.write_text(yaml.safe_dump(tool), encoding="utf-8")
    assert _schema_errors(path, TOOL_SCHEMA) == []

    tool["last_verified"] = "2026-07-10"
    path.write_text(yaml.safe_dump(tool), encoding="utf-8")
    assert _schema_errors(path, TOOL_SCHEMA)


def test_apollo_uses_reachable_authoritative_paper_record() -> None:
    apollo = _load(TOOL_DIR / "apollo.yml")
    assert apollo["url"] == "https://arxiv.org/abs/2102.01723"
    assert apollo["artifact_availability"] == "paper_only"


def test_archived_workshops_do_not_retain_submission_links() -> None:
    workshops = [_load(path) for path in WORKSHOP_DIR.glob("*.yml")]
    assert workshops
    for item in workshops:
        if item.get("status") == "archived":
            assert "submission_url" not in item


def test_expired_active_workshop_is_rejected(tmp_path: Path) -> None:
    workshop = {
        "title": "Expired test",
        "url": "https://example.com/event",
        "venue": "Test",
        "when": "2000",
        "event_start": "2000-01-01",
        "event_end": "2000-01-02",
        "status": "active",
        "last_verified": dt.date.today().isoformat(),
        "description": "Expired active fixture.",
        "categories": ["Architecture 2.0"],
    }
    path = tmp_path / "expired.yml"
    path.write_text(yaml.safe_dump(workshop), encoding="utf-8")
    errors = _semantic_errors([], [path])
    assert any("active workshop ended" in error for error in errors)


def test_archived_workshop_cannot_retain_submission_link(tmp_path: Path) -> None:
    workshop = {
        "title": "Archived test",
        "url": "https://example.com/event",
        "venue": "Test",
        "when": "2000",
        "event_end": "2000-01-02",
        "status": "archived",
        "last_verified": "2026-07-10",
        "description": "Archived fixture.",
        "categories": ["Architecture 2.0"],
        "submission_url": "https://example.com/closed",
    }
    path = tmp_path / "archived.yml"
    path.write_text(yaml.safe_dump(workshop), encoding="utf-8")
    assert _schema_errors(path, WORKSHOP_SCHEMA)


def test_awesome_is_generated_from_registry() -> None:
    assert OUTPUT_PATH.read_text(encoding="utf-8") == render()


@pytest.mark.skipif(shutil.which("quarto") is None, reason="Quarto is not installed")
def test_tool_template_escapes_untrusted_registry_text_and_links(
    tmp_path: Path,
) -> None:
    template_source = ROOT / "tools" / "_tool-card.ejs.md"
    template = template_source.read_text(encoding="utf-8")
    assert "<%-" not in template

    (tmp_path / "_tool-card.ejs.md").write_text(template, encoding="utf-8")
    (tmp_path / "_quarto.yml").write_text(
        "project:\n  type: website\n  output-dir: _site\nformat: html\n",
        encoding="utf-8",
    )
    (tmp_path / "index.qmd").write_text(
        """---
title: Tool escaping test
listing:
  - id: tool-registry
    contents: tools.yml
    template: _tool-card.ejs.md
    fields: [title, url, description, authors, institution, submitted_by, artifact_availability, last_verified, categories, tags]
    field-required: [title, url, description, artifact_availability, categories]
---

:::{#tool-registry}
:::
""",
        encoding="utf-8",
    )
    payloads = [
        {
            "title": 'Bad"><script>alert("title")</script>',
            "url": 'https://example.com/tool/" autofocus onfocus="alert(1)',
            "description": "<img src=x onerror=alert(2)>",
            "authors": "<b onmouseover=alert(3)>Injected author</b>",
            "institution": "<svg onload=alert(4)>",
            "submitted_by": "<iframe srcdoc='<script>alert(5)</script>'>",
            "artifact_availability": 'runnable" onclick="alert(6)',
            "last_verified": "2026-07-10</span><script>alert(7)</script>",
            "categories": ['Simulation"><img src=x onerror=alert(8)>'],
            "tags": ['tag"><svg onload=alert(9)>'],
        },
        {
            "title": "Unsafe scheme",
            "url": "javascript:alert(10)",
            "description": "Scheme should be rejected.",
            "artifact_availability": "source_available",
            "categories": ["Simulation"],
            "tags": [],
        },
    ]
    (tmp_path / "tools.yml").write_text(
        yaml.safe_dump(payloads, sort_keys=False), encoding="utf-8"
    )

    rendered = subprocess.run(
        ["quarto", "render"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert rendered.returncode == 0, rendered.stdout + rendered.stderr
    html = (tmp_path / "_site" / "index.html").read_text(encoding="utf-8")
    card_fragments = [
        f'<article class="tool-card {fragment.split("</article>", 1)[0]}</article>'
        for fragment in html.split('<article class="tool-card ')[1:]
    ]
    assert len(card_fragments) == 2

    audit = _FragmentAuditParser()
    audit.feed("".join(card_fragments))
    assert not {"script", "img", "svg", "iframe", "b"}.intersection(audit.tags)
    assert not any(name.startswith("on") for name, _ in audit.attributes)
    assert not any(name in {"autofocus", "srcdoc"} for name, _ in audit.attributes)

    hrefs = [value for name, value in audit.attributes if name == "href"]
    assert len(hrefs) == 2
    assert hrefs[1] == "#"
    assert urlparse(hrefs[0] or "").scheme == "https"
    assert "autofocus" in (hrefs[0] or "")
    open_labels = [
        value
        for name, value in audit.attributes
        if name == "aria-label" and (value or "").startswith("Open Bad")
    ]
    assert open_labels == ['Open Bad"><script>alert("title")</script>']
    assert 'href="javascript:' not in html
    assert "availability-runnable&quot;" not in html
    assert "availability-unverified" in html
    for escaped in (
        "&lt;script&gt;",
        "&lt;img",
        "&lt;b",
        "&lt;svg",
        "&lt;iframe",
    ):
        assert escaped in html


@pytest.mark.skipif(shutil.which("quarto") is None, reason="Quarto is not installed")
def test_workshop_template_escapes_untrusted_registry_text(tmp_path: Path) -> None:
    template_source = ROOT / "www" / "_workshop-card.ejs.md"
    template = template_source.read_text(encoding="utf-8")
    assert "<%-" not in template

    (tmp_path / "_workshop-card.ejs.md").write_text(template, encoding="utf-8")
    (tmp_path / "_quarto.yml").write_text(
        "project:\n  type: website\n  output-dir: _site\nformat: html\n",
        encoding="utf-8",
    )
    (tmp_path / "index.qmd").write_text(
        """---
title: Workshop escaping test
listing:
  - id: workshop-registry
    contents: workshops.yml
    template: _workshop-card.ejs.md
    fields: [title, description, venue, when, status, last_verified, location, organizers, history, categories]
    field-required: [title, url, description, venue, status, categories]
---

:::{#workshop-registry}
:::
""",
        encoding="utf-8",
    )
    payload = {
        "title": 'Bad"><script>alert("title")</script>',
        "url": 'https://example.com/workshop/" onmouseover="alert(2)',
        "venue": 'Venue" onmouseover="alert(1)',
        "when": "2026",
        "status": "archived",
        "last_verified": "2026-07-10",
        "description": "<img src=x onerror=alert(1)>",
        "location": "<b>Injected location</b>",
        "organizers": "<script>alert('organizer')</script>",
        "categories": ["Architecture 2.0"],
        "history": [
            {
                "label": "<em>Injected label</em>",
                "when": "2025",
                "url": 'https://example.com/history/" onmouseover="alert(3)',
                "note": "<svg onload=alert(1)>",
            }
        ],
    }
    (tmp_path / "workshops.yml").write_text(
        yaml.safe_dump([payload], sort_keys=False), encoding="utf-8"
    )

    rendered = subprocess.run(
        ["quarto", "render"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert rendered.returncode == 0, rendered.stdout + rendered.stderr
    html = (tmp_path / "_site" / "index.html").read_text(encoding="utf-8")
    for unsafe in (
        '<script>alert("title")',
        "<script>alert('organizer')",
        "<img src=x onerror=alert(1)>",
        "<b>Injected location</b>",
        "<em>Injected label</em>",
        "<svg onload=alert(1)>",
    ):
        assert unsafe not in html
    for escaped in ("&lt;script&gt;", "&lt;img", "&lt;b&gt;", "&lt;em&gt;", "&lt;svg"):
        assert escaped in html
    assert 'Bad"&gt;&lt;script&gt;' in html
    assert 'onmouseover="alert(2)' not in html
    assert 'onmouseover="alert(3)' not in html
    assert "https://example.com/workshop/%22%20onmouseover=%22alert(2)" in html
    assert "https://example.com/history/%22%20onmouseover=%22alert(3)" in html
