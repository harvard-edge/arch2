#!/usr/bin/env python3
"""Arch2 command-line interface for the Architecture 2.0 Synthesis Lecture."""

from __future__ import annotations

import json
import hashlib
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
import html as html_lib
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Iterator
from urllib.parse import unquote, urlsplit

import typer
from rich.console import Console
from rich.table import Table

try:
    from cli.card_migration import migrate_v1_1_to_v2_draft
except ModuleNotFoundError:  # Support direct execution as python cli/arch2.py.
    from card_migration import migrate_v1_1_to_v2_draft

ROOT = Path(__file__).resolve().parents[1]
BOOK_DIR = ROOT / "book"
BUILD_DIR = BOOK_DIR / "_build"
PDF_PATH = BUILD_DIR / "Architecture-2.0.pdf"
HTML_PATH = BUILD_DIR / "index.html"
EPUB_PATH = BUILD_DIR / "Architecture-2.0.epub"
EPUBCHECK_VERSION = "5.3.0"
LOG_DIR = BUILD_DIR / "logs"
DEFAULT_REVIEW_WORKBENCH = ROOT.parent.parent / "PaperReviewWorkbench"
LOOP_DIR = ROOT / ".arch2" / "reviews" / "loop"
DEFAULT_GEMINI_MODEL = "gemini-3.1-pro-preview"
CARD_SCHEMA_VERSION = "2.0"
CARD_SCHEMA_PATHS = {
    "1.0": ROOT / "schemas" / "design-loop-card.v1.schema.json",
    "1.1": ROOT / "schemas" / "design-loop-card.v1.1.schema.json",
    "2.0": ROOT / "schemas" / "design-loop-card.v2.schema.json",
}
CARD_SCHEMA_PATH = CARD_SCHEMA_PATHS[CARD_SCHEMA_VERSION]

DEFAULT_LOOP_CONCEPTS = (
    "Architecture 2.0",
    "design loop",
    "design-loop card",
    "feedback budget",
    "fidelity ladder",
    "rejection authority",
    "world model",
    "environment",
    "method role",
    "commitment boundary",
    "lighthouse prompt",
)

DISCLOSURE_GATED_CONCEPTS = (
    "design-loop card",
    "feedback budget",
    "fidelity ladder",
    "rejection authority",
    "world model",
    "method role",
    "commitment boundary",
    "lighthouse prompt",
)

console = Console()

app = typer.Typer(
    name="arch2",
    help="Compiler-style build and audit driver for the Architecture 2.0 lecture.",
    no_args_is_help=True,
)
check_app = typer.Typer(
    help="Run composed manuscript quality gates.", no_args_is_help=True
)
validate_app = typer.Typer(
    help="Validate source files without requiring a render.", no_args_is_help=True
)
migrate_app = typer.Typer(
    help="Create explicit migration drafts for versioned artifacts.",
    no_args_is_help=True,
)
verify_app = typer.Typer(
    help="Verify rendered artifacts against manuscript sources.", no_args_is_help=True
)
layout_app = typer.Typer(
    help="Scan PDF, LaTeX, and visual layout signals.", no_args_is_help=True
)
review_app = typer.Typer(
    help="Open the Arch2 local review/commenting bench.", no_args_is_help=True
)
loop_app = typer.Typer(
    help="Run self-improving manuscript review loops.", no_args_is_help=True
)
generate_app = typer.Typer(
    help="Generate derived assets, schemas, and backmatter appendices.",
    no_args_is_help=True,
)


class FindingFormat(str, Enum):
    """How findings are rendered.

    ``table`` is for a human at a terminal. ``json`` and ``ndjson`` are for a
    program or an agent applying the repairs; both keep every path intact,
    which the Rich table cannot promise once a column has to wrap.
    """

    table = "table"
    json = "json"
    ndjson = "ndjson"


# Set once by the root callback and read by the emitter. Findings are produced
# deep inside the check functions, and threading a format argument through
# every run_*_check signature would touch far more code than the choice is
# worth.
_finding_format = FindingFormat.table


@app.callback()
def main(
    output_format: FindingFormat = typer.Option(
        FindingFormat.table,
        "--format",
        "-f",
        help="Finding output format. Use json or ndjson for machine repair.",
    ),
) -> None:
    """Compiler-style build and audit driver for the Architecture 2.0 lecture."""
    global _finding_format
    _finding_format = output_format


app.add_typer(check_app, name="check")
app.add_typer(validate_app, name="validate")
app.add_typer(generate_app, name="generate")
app.add_typer(migrate_app, name="migrate")
app.add_typer(verify_app, name="verify")
app.add_typer(layout_app, name="layout")
app.add_typer(review_app, name="review")
app.add_typer(loop_app, name="loop")


@dataclass(frozen=True)
class Finding:
    """One rule violation.

    The first four attributes are what a human reads. The last three are what a
    machine needs to repair the violation without re-deriving it: ``span`` is
    the exact source substring at fault, ``replacement`` is what it should
    become, and ``context`` is the unwrapped source line the span sits in.

    A rule that can fill ``span`` and ``replacement`` describes a deterministic
    edit, which is the same property that makes it safe to gate on. A rule that
    can offer neither is asking for a judgment call and generally belongs at
    warning severity.
    """

    severity: str
    code: str
    location: str
    message: str
    span: str | None = None
    replacement: str | None = None
    context: str | None = None

    @property
    def fixable(self) -> bool:
        """True when the finding carries a deterministic edit."""
        return self.span is not None and self.replacement is not None

    def as_record(self) -> dict[str, Any]:
        """Render as a flat record with the file path and line split out.

        ``location`` is a display string and not always a file position; a
        citation-reuse finding locates a BibTeX key, not a line. Splitting is
        therefore best-effort, and ``path``/``line`` stay absent when the
        location is not ``file:line``.
        """
        record: dict[str, Any] = {
            "severity": self.severity,
            "code": self.code,
            "location": self.location,
            "message": self.message,
            "fixable": self.fixable,
        }
        match = re.match(r"^(?P<path>.+?):(?P<line>\d+)$", self.location)
        if match:
            record["path"] = match.group("path")
            record["line"] = int(match.group("line"))
        for key in ("span", "replacement", "context"):
            value = getattr(self, key)
            if value is not None:
                record[key] = value
        return record


@dataclass(frozen=True)
class LayoutPageProfile:
    page: int
    width: float
    height: float
    word_count: int
    content_top: float | None
    content_bottom: float | None
    usable_bottom: float
    bottom_whitespace: float | None
    has_figure: bool
    has_table: bool
    captions: tuple[str, ...]
    starts_chapter: bool
    text_excerpt: str
    content_occupancy: float | None = None
    major_unit_kind: str | None = None


@dataclass(frozen=True)
class LayoutRepairItem:
    id: str
    severity: str
    code: str
    location: str
    evidence: str
    likely_cause: str
    suggested_action: str
    source_hints: tuple[str, ...]


@dataclass(frozen=True)
class ManuscriptLabel:
    path: Path
    line: int
    label: str
    kind: str


@dataclass(frozen=True)
class CitationOccurrence:
    path: Path
    line: int
    context: str


@dataclass(frozen=True)
class DefinitionOccurrence:
    path: Path
    line: int
    term: str
    context: str


@dataclass(frozen=True)
class SvgShape:
    kind: str
    x: float
    y: float
    width: float
    height: float

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def cx(self) -> float:
        return self.x + self.width / 2.0

    @property
    def cy(self) -> float:
        return self.y + self.height / 2.0

    @property
    def radius(self) -> float:
        return self.width / 2.0

    def contains_point(self, x: float, y: float) -> bool:
        if self.kind == "rect":
            return (
                self.x <= x <= self.x + self.width
                and self.y <= y <= self.y + self.height
            )
        dx = x - self.cx
        dy = y - self.cy
        return (dx * dx + dy * dy) <= self.radius * self.radius


@dataclass(frozen=True)
class SvgTextLabel:
    x: float
    y: float
    text: str
    font_size: float
    anchor: str

    @property
    def estimated_width(self) -> float:
        return sum(svg_character_width(ch, self.font_size) for ch in self.text)

    @property
    def left(self) -> float:
        width = self.estimated_width
        if self.anchor == "middle":
            return self.x - width / 2.0
        if self.anchor == "end":
            return self.x - width
        return self.x

    @property
    def right(self) -> float:
        return self.left + self.estimated_width

    @property
    def top(self) -> float:
        return self.y - self.font_size * 0.85

    @property
    def bottom(self) -> float:
        return self.y + self.font_size * 0.25


@dataclass(frozen=True)
class SvgBounds:
    kind: str
    left: float
    top: float
    right: float
    bottom: float
    label: str = ""


OVERFULL_HBOX_RE = re.compile(
    r"Overfull \\hbox \((?P<pts>[0-9.]+)pt too wide\)(?P<context>[^\n]*)"
)
OVERFULL_VBOX_RE = re.compile(
    r"Overfull \\vbox \((?P<pts>[0-9.]+)pt too high\)(?P<context>[^\n]*)"
)
UNDERFULL_RE = re.compile(r"Underfull \\(?:h|v)box (?P<context>[^\n]*)")
UNRESOLVED_REF_RE = re.compile(
    r"(?:Reference|Citation) `?([^'\n]+)'? on page .* undefined", re.I
)
PDF_CAPTION_LINE_RE = re.compile(r"\b(?P<kind>Figure|Table)\s*[A-Z]?\d+(?:\.\d+)?:")
PDF_CHAPTER_START_RE = re.compile(r"^Chapter\s+\d+\b", re.I)
PDF_MAJOR_UNIT_LINE_RE = re.compile(
    r"^(?P<kind>Chapter|Appendix|Part|References)(?:\s+(?:[A-Z]|\d+|[IVXLC]+))?$",
    re.I,
)
LAYOUT_USABLE_TOP = 90.0
LAYOUT_FOOTER_BAND = 120.0
LAYOUT_MAIN_COLUMN_LEFT_RATIO = 0.20
LAYOUT_MAIN_COLUMN_RIGHT_RATIO = 0.80
LAYOUT_MIN_VECTOR_DIMENSION = 4.0
LAYOUT_MIN_VECTOR_AREA = 64.0
LAYOUT_MAJOR_UNIT_OPENING_LINES = 12
DEFAULT_SPARSE_CLEARANCE = 170.0
DEFAULT_MAX_CONTENT_OCCUPANCY = 0.72
DEFAULT_SPARSE_MIN_BODY_WORDS = 80
CONTENT_ROOTS = (
    BOOK_DIR / "contents" / "chapters",
    BOOK_DIR / "contents" / "parts",
    BOOK_DIR / "contents" / "backmatter",
)
# Thin root index.qmd includes the sole preface body (not listed separately in
# book.chapters). See docs/REPO-LAYOUT.md.
BOOK_PREFACE_SOURCE = BOOK_DIR / "contents" / "frontmatter" / "preface.qmd"
BOOK_FRONTMATTER = (
    BOOK_DIR / "index.qmd",
    BOOK_DIR / "contents" / "frontmatter" / "foreword.qmd",
    BOOK_DIR / "contents" / "frontmatter" / "acknowledgments.qmd",
    BOOK_DIR / "contents" / "frontmatter" / "about-the-author.qmd",
    BOOK_DIR / "contents" / "frontmatter" / "disclosure.qmd",
)
BOOK_INCLUDE_ONLY_SOURCES = (BOOK_PREFACE_SOURCE,)
CANONICAL_CROSSREF_PREFIXES = ("fig", "tbl", "eq", "sec", "lst", "pri")
REQUIRED_REFERENCED_LABEL_PREFIXES = ("fig-", "tbl-", "eq-", "lst-")
CANONICAL_BIBLIOGRAPHY = BOOK_DIR / "references" / "references.bib"
CANONICAL_CSL = BOOK_DIR / "csl" / "chicago-author-date.csl"
CROSSREF_PREFIX_PATTERN = "|".join(CANONICAL_CROSSREF_PREFIXES)
GENERATED_ASSET_SUFFIXES = (".pdf", ".svg", ".png", ".jpg", ".jpeg")
QUARTO_LABEL_RE = re.compile(
    rf"\{{[^}}\n]*#(?P<label>(?:{CROSSREF_PREFIX_PATTERN})-[A-Za-z0-9_-]+)(?=[\s}}])[^}}]*\}}"
)
LATEX_LABEL_RE = re.compile(
    r"\\label\{(?P<label>(?:fig|tab|eq|sec|lst):[A-Za-z0-9:_-]+)\}"
)
QUARTO_REF_RE = re.compile(
    rf"(?<![#\w])@(?P<label>(?:{CROSSREF_PREFIX_PATTERN})-[A-Za-z0-9_-]+)\b"
)
LATEX_REF_RE = re.compile(
    r"\\(?:auto|[cC]|eq)?ref\{(?P<label>(?:fig|tab|eq|sec|lst):[A-Za-z0-9:_-]+)\}"
)
RAW_STRUCTURE_REF_RE = re.compile(
    r"\b(?:"
    r"(?:[Cc]hapters?|[Cc]h\.)\s*\d+(?:\.\d+)?(?:\s*(?:-|and|,)\s*\d+(?:\.\d+)?)*"
    r"|(?:[Aa]ppendix|[Aa]ppendices|[Aa]pp\.)\s+[A-Z](?:\s*(?:-|and|,)\s*[A-Z])*"
    r"|(?:[Tt]ables?|[Tt]ab\.)\s*\d+(?:\.\d+)?"
    r"|(?:[Ff]igures?|[Ff]ig\.)\s*\d+(?:\.\d+)?"
    r"|(?:[Ss]ections?|[Ss]ec\.)\s*\d+(?:\.\d+)?"
    r"|(?:[Ee]quations?|[Ee]qs?\.)\s*\d+(?:\.\d+)?"
    r"|(?:[Ll]istings?|[Ll]st\.)\s*\d+(?:\.\d+)?"
    r")\b"
)
CHAP_LABEL_OR_REF_RE = re.compile(
    r"(?<![\w#])@chap-[A-Za-z0-9_-]+\b|#chap-[A-Za-z0-9_-]+\b"
)
# A raw LaTeX \ref against a Quarto-style hyphen label. Quarto owns these
# labels, so \ref does not resolve them and the PDF prints a bare "??" while
# the HTML silently drops the link. The colon form (\ref{fig:x}) is a genuine
# LaTeX label and is handled by LATEX_REF_RE, not banned here.
LATEX_SECTION_REF_RE = re.compile(
    rf"\\(?:auto|[cC]|eq)?ref\{{(?:{CROSSREF_PREFIX_PATTERN}|chap)-[A-Za-z0-9_-]+\}}"
)
# Deictic structure references: prose that points at a neighbouring chapter,
# section, or float by position rather than by label. These survive an edit
# that reorders the book and then quietly lie to the reader, which is the same
# failure the hard-coded-number ban exists to prevent. Only flagged when the
# line carries no cross-reference of its own; "the next chapter
# (@sec-loop-patterns-across-stack)" names its target and is fine.
DEICTIC_STRUCTURE_RE = re.compile(
    r"\b(?:"
    r"(?:the|this|that|a)\s+(?:next|previous|last|preceding|following|prior|earlier|later)\s+"
    # "part" is deliberately absent. Quarto emits no @part-* reference, so a
    # part opener saying "the preceding part" has no cross-reference to migrate
    # to. Same reason Part I / Part 2 stays out of RAW_STRUCTURE_REF_RE.
    r"(?:chapter|section|subsection|appendix)"
    r"|(?:chapter|section|appendix)\s+that\s+follows"
    r"|(?:the\s+)?(?:table|figure|listing|equation|diagram|plot)\s+(?:above|below)"
    r"|(?:above|below)\s+(?:table|figure|listing|equation)"
    r")\b",
    re.IGNORECASE,
)
ANY_CROSSREF_RE = re.compile(
    rf"(?<![#\w])@(?:{CROSSREF_PREFIX_PATTERN}|chap)-[A-Za-z0-9_-]+\b"
)
TABLE_ENV_RE = re.compile(
    r"\\begin\{(?P<env>table\*?)\}(?P<option>\[[^\]]+\])?"
    r"(?P<body>.*?)\\end\{(?P=env)\}",
    re.DOTALL,
)
ARRAYSTRETCH_RE = re.compile(r"\\renewcommand\{\\arraystretch\}\{(?P<value>[0-9.]+)\}")
TABCOLSEP_RE = re.compile(r"\\setlength\{\\tabcolsep\}\{(?P<value>[0-9.]+)\s*pt\}")
MARKDOWN_FIGURE_RE = re.compile(
    r"!\[[^\]]*\]\((?P<target>[^)\s]+)(?:\s+\"[^\"]*\")?\)"
    r"\{#(?P<label>fig-[A-Za-z0-9_-]+)(?=[\s}])[^}]*\}"
)
MARKDOWN_FIGURE_ATTR_RE = re.compile(
    r"!\[[^\]]*\]\((?P<target>[^)\s]+)(?:\s+\"[^\"]*\")?\)\{(?P<attrs>[^}]*#(?P<label>fig-[A-Za-z0-9_-]+)[^}]*)\}"
)
EXECUTABLE_FIGURE_RE = re.compile(
    r"^\s*#\|\s*label:\s*(?P<label>fig-[A-Za-z0-9_-]+)\s*$",
    re.MULTILINE,
)
CHUNK_START_RE = re.compile(r"^\s*```\{(?P<engine>[^}]*)\}\s*$")
CHUNK_LABEL_RE = re.compile(
    rf"^\s*#\|\s*label:\s*(?P<label>(?:{CROSSREF_PREFIX_PATTERN})-[A-Za-z0-9_-]+)\s*$",
    re.MULTILINE,
)
CHUNK_FIG_ALT_RE = re.compile(r"^\s*#\|\s*fig-alt:\s*(?P<alt>.+?)\s*$")
# Quarto expands @refs in prose but NOT inside alt text, so one written there
# survives into the rendered alt attribute verbatim. That fails the build's
# html-unresolved-reference check a full CI cycle later, and a screen reader
# reads the raw label aloud. Catch it in the source instead.
ALT_TEXT_REF_RE = re.compile(r"@(?:sec|fig|tbl|eq|lst|chap)-[A-Za-z0-9_-]+")
CHUNK_FIG_POS_RE = re.compile(r"^\s*#\|\s*fig-pos:\s*(?P<pos>.+?)\s*$")
CITE_RE = re.compile(r"(?<![\w@])@(?P<key>[A-Za-z0-9:_-]+)")
DEFINITION_RE = re.compile(
    r"^\s*>\s*\*\*(?P<term>[^*\n.][^*\n]{1,90}?)\.\*\*", re.MULTILINE
)
STYLE_RE = re.compile(r"\.(?P<class>[A-Za-z0-9_-]+)\s*\{(?P<body>[^}]*)\}", re.DOTALL)
FONT_SIZE_RE = re.compile(r"font-size\s*:\s*(?P<size>[0-9.]+)px")
SVG_FONT_FAMILY_RE = re.compile(
    r"font-family\s*(?::|=)\s*['\"]?(?P<family>[^;\"'}]+)", re.I
)
TRANSLATE_RE = re.compile(
    r"translate\(\s*(?P<x>-?[0-9.]+)(?:[,\s]+(?P<y>-?[0-9.]+))?\s*\)"
)
MIN_ARRAYSTRETCH = 1.2
MIN_TABCOLSEP_PT = 2.5
MIN_RECT_PADDING = 4.0
MIN_CIRCLE_PADDING = 8.0
CONTENT_SVG_FONT_STACK = ("Arial", "Helvetica", "sans-serif")
DEFAULT_FONT_SIZE = 12.0


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _run(
    cmd: list[str],
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        env=merged_env,
        text=True,
        capture_output=capture,
    )


def _record_log(name: str, text: str) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = LOG_DIR / f"{name}-{stamp}.log"
    target.write_text(text, encoding="utf-8")
    (LOG_DIR / f"{name}-latest.log").write_text(text, encoding="utf-8")
    return target


def _emit_findings(findings: Iterable[Finding], *, title: str) -> None:
    rows = _filter_suppressed(findings)
    if _finding_format is not FindingFormat.table:
        _emit_findings_machine(rows, title=title)
        return
    if not rows:
        console.print(f"[green]passed[/green] {title}")
        return

    table = Table(title=title, show_lines=False)
    table.add_column("Severity", style="bold")
    table.add_column("Code")
    table.add_column("Location", overflow="fold")
    table.add_column("Message", overflow="fold")
    for finding in rows:
        style = "red" if finding.severity == "error" else "yellow"
        table.add_row(
            f"[{style}]{finding.severity}[/{style}]",
            finding.code,
            finding.location,
            finding.message,
        )
    console.print(table)


SUPPRESSION_RE = re.compile(
    r"<!--\s*arch2-allow:\s*(?P<code>[a-z][a-z0-9-]*)\s*(?P<reason>[^>]*?)\s*-->"
)


def suppression_map(path: Path) -> dict[int, set[str]]:
    """Map line numbers to the rule codes deliberately allowed on them.

    A directive covers the line it sits on. When it sits alone on its own line
    it covers the next non-blank line instead, which is the only way to exempt
    something inside a construct that cannot hold a trailing comment.

    The reason is required and is not parsed. Its job is to survive in the
    source so the next reader learns why the exception exists rather than
    finding a bare override and deleting it.
    """
    allowed: dict[int, set[str]] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return allowed
    for index, line in enumerate(lines, start=1):
        match = SUPPRESSION_RE.search(line)
        if not match or not match.group("reason"):
            continue
        target = index
        if SUPPRESSION_RE.sub("", line).strip() == "":
            for offset in range(index, len(lines)):
                if lines[offset].strip():
                    target = offset + 1
                    break
        allowed.setdefault(target, set()).add(match.group("code"))
    return allowed


_suppression_cache: dict[str, dict[int, set[str]]] = {}


def _is_suppressed(finding: Finding) -> bool:
    match = re.match(r"^(?P<path>.+?):(?P<line>\d+)$", finding.location)
    if not match:
        return False
    relative = match.group("path")
    if relative not in _suppression_cache:
        _suppression_cache[relative] = suppression_map(ROOT / relative)
    return finding.code in _suppression_cache[relative].get(
        int(match.group("line")), set()
    )


def _filter_suppressed(findings: Iterable[Finding]) -> list[Finding]:
    return [finding for finding in findings if not _is_suppressed(finding)]


def suppression_hygiene_findings(paths: list[Path] | None = None) -> list[Finding]:
    """Reject an arch2-allow directive that states no reason.

    A bare override is how a ruleset quietly stops meaning anything. Requiring
    a reason keeps the cost of an exception slightly above the cost of the fix.
    """
    findings: list[Finding] = []
    for path in paths if paths is not None else content_qmd_files():
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"<!--\s*arch2-allow:[^>]*-->", text):
            parsed = SUPPRESSION_RE.fullmatch(match.group(0))
            if parsed and parsed.group("reason"):
                continue
            findings.append(
                Finding(
                    "error",
                    "arch2-allow-missing-reason",
                    f"{_relative(path)}:{line_number(text, match.start())}",
                    "arch2-allow needs a reason: <!-- arch2-allow: code why this "
                    "case is deliberate -->",
                    span=match.group(0),
                    context=match.group(0),
                )
            )
    return findings


def _emit_findings_machine(findings: list[Finding], *, title: str) -> None:
    """Write findings as JSON or NDJSON on stdout.

    Printed with the plain builtin rather than the Rich console. Rich wraps to
    the terminal width, and a wrapped path is a broken path once something
    downstream tries to open it.
    """
    records = [finding.as_record() for finding in findings]
    if _finding_format is FindingFormat.ndjson:
        for record in records:
            print(json.dumps({"gate": title, **record}))
        return
    fixable = sum(1 for record in records if record["fixable"])
    print(
        json.dumps(
            {
                "gate": title,
                "summary": {
                    "total": len(records),
                    "errors": sum(1 for r in records if r["severity"] == "error"),
                    "warnings": sum(1 for r in records if r["severity"] == "warning"),
                    "fixable": fixable,
                    "codes": sorted({r["code"] for r in records}),
                },
                "findings": records,
            },
            indent=2,
        )
    )


def _exit_if_failed(proc: subprocess.CompletedProcess[str], label: str) -> None:
    if proc.returncode == 0:
        console.print(f"[green]passed[/green] {label}")
        return
    console.print(f"[red]failed[/red] {label}")
    if proc.stdout:
        console.print(proc.stdout)
    if proc.stderr:
        console.print(proc.stderr)
    raise typer.Exit(proc.returncode)


def _exit_on_findings(
    findings: list[Finding], *, title: str, fail_on_warning: bool = False
) -> None:
    remaining = _filter_suppressed(findings)
    _emit_findings(remaining, title=title)
    if any(
        finding.severity == "error"
        or (fail_on_warning and finding.severity == "warning")
        for finding in remaining
    ):
        raise typer.Exit(1)


def _card_json_path(parts: Iterable[object]) -> str:
    path = "$"
    for part in parts:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}"
    return path


def _card_schema_message(
    error: object, card: object, *, expected_version: str | None = None
) -> str:
    message = str(getattr(error, "message", "invalid card"))
    validator = getattr(error, "validator", None)
    absolute_path = list(getattr(error, "absolute_path", []))

    if absolute_path == ["schema_version"] and validator == "const":
        return f"schema version does not match contract '{expected_version}'"

    if validator == "additionalProperties" and "'claim'" in message:
        return "unexpected top-level card field 'claim'; use intent.claim_boundary.claim and intent.claim_boundary.non_claim"

    if validator == "required" and isinstance(card, dict):
        loop_card = card.get("design_loop_card")
        level = (
            loop_card.get("conformance_level") if isinstance(loop_card, dict) else None
        )
        missing_match = re.search(r"'([^']+)' is a required property", message)
        if missing_match and isinstance(level, int):
            return (
                f"conformance level {level} requires "
                f"'{missing_match.group(1)}' at {_card_json_path(absolute_path)}"
            )

    return message


def _card_v2_semantic_findings(card: dict[str, Any], card_path: Path) -> list[Finding]:
    """Check v2 relationships and local integrity bindings JSON Schema cannot express."""
    findings: list[Finding] = []
    location = _relative(card_path)
    loop_card = card["design_loop_card"]

    def add(code: str, json_path: str, message: str) -> None:
        findings.append(Finding("error", code, f"{location}:{json_path}", message))

    def indexed_ids(
        records: list[dict[str, Any]], key: str, json_path: str
    ) -> set[str]:
        identifiers: set[str] = set()
        for index, record in enumerate(records):
            identifier = record[key]
            if identifier in identifiers:
                add(
                    "card-duplicate-id",
                    f"{json_path}[{index}].{key}",
                    f"duplicate {key} {identifier!r}",
                )
            identifiers.add(identifier)
        return identifiers

    evidence_records = loop_card["evidence"]["records"]
    claims = loop_card["claims"]
    gates = loop_card["gates"]
    rejected = loop_card["failed_or_rejected"]
    evidence_ids = indexed_ids(
        evidence_records, "evidence_id", "$.design_loop_card.evidence.records"
    )
    claim_ids = indexed_ids(claims, "claim_id", "$.design_loop_card.claims")
    gate_ids = indexed_ids(gates, "gate_id", "$.design_loop_card.gates")
    indexed_ids(rejected, "record_id", "$.design_loop_card.failed_or_rejected")

    def check_refs(
        refs: list[str], known: set[str], json_path: str, label: str
    ) -> None:
        for index, reference in enumerate(refs):
            if reference not in known:
                add(
                    "card-unknown-reference",
                    f"{json_path}[{index}]",
                    f"unknown {label} reference {reference!r}",
                )

    for index, claim in enumerate(claims):
        check_refs(
            claim["evidence_refs"],
            evidence_ids,
            f"$.design_loop_card.claims[{index}].evidence_refs",
            "evidence",
        )
    for index, gate in enumerate(gates):
        check_refs(
            gate["evidence_refs"],
            evidence_ids,
            f"$.design_loop_card.gates[{index}].evidence_refs",
            "evidence",
        )
    for index, record in enumerate(rejected):
        check_refs(
            record["evidence_refs"],
            evidence_ids,
            f"$.design_loop_card.failed_or_rejected[{index}].evidence_refs",
            "evidence",
        )
        gate_ref = record.get("gate_ref")
        if gate_ref is not None and gate_ref not in gate_ids:
            add(
                "card-unknown-reference",
                f"$.design_loop_card.failed_or_rejected[{index}].gate_ref",
                f"unknown gate reference {gate_ref!r}",
            )

    recommendation = loop_card.get("recommendation")
    if recommendation:
        check_refs(
            recommendation["claim_refs"],
            claim_ids,
            "$.design_loop_card.recommendation.claim_refs",
            "claim",
        )
    decision_record = loop_card["accountable_decision"]
    check_refs(
        decision_record["claim_refs"],
        claim_ids,
        "$.design_loop_card.accountable_decision.claim_refs",
        "claim",
    )
    review = loop_card.get("independent_review")
    if review:
        check_refs(
            review["claim_refs"],
            claim_ids,
            "$.design_loop_card.independent_review.claim_refs",
            "claim",
        )
        check_refs(
            review["evidence_refs"],
            evidence_ids,
            "$.design_loop_card.independent_review.evidence_refs",
            "evidence",
        )

    rights = {
        (right["holder_id"], right["action"]) for right in loop_card["decision_rights"]
    }
    if loop_card["profiles"]["decision_rights"] == "complete":
        for index, gate in enumerate(gates):
            if (gate["authority_id"], "reject") not in rights:
                add(
                    "card-decision-right",
                    f"$.design_loop_card.gates[{index}].authority_id",
                    "gate authority must hold a declared reject right",
                )
            waiver = gate["waiver_rule"]
            if waiver["allowed"] and (waiver["authority_id"], "waive") not in rights:
                add(
                    "card-decision-right",
                    f"$.design_loop_card.gates[{index}].waiver_rule.authority_id",
                    "waiver authority must hold a declared waive right",
                )
        if (
            recommendation
            and (recommendation["recommender_id"], "recommend") not in rights
        ):
            add(
                "card-decision-right",
                "$.design_loop_card.recommendation.recommender_id",
                "recommender must hold a declared recommend right",
            )
        if (decision_record["holder_id"], "commit") not in rights:
            add(
                "card-decision-right",
                "$.design_loop_card.accountable_decision.holder_id",
                "decision holder must hold a declared commit right",
            )

    def verify_local_artifact(raw_uri: str, digest: str, json_path: str) -> None:
        parsed = urlsplit(raw_uri)
        if parsed.scheme or parsed.netloc:
            return
        if parsed.query or parsed.fragment:
            add(
                "card-artifact-uri",
                json_path,
                "local artifact URI must not contain a query or fragment",
            )
            return
        base = card_path.parent.resolve()
        target = (base / unquote(parsed.path)).resolve()
        try:
            target.relative_to(base)
        except ValueError:
            add(
                "card-artifact-escape",
                json_path,
                "local artifact URI escapes the card directory",
            )
            return
        if not target.is_file():
            add(
                "card-artifact-missing",
                json_path,
                f"local artifact does not exist: {raw_uri}",
            )
            return
        observed = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
        if observed != digest:
            add(
                "card-artifact-hash",
                json_path,
                f"SHA-256 mismatch for {raw_uri!r}: declared {digest}, observed {observed}",
            )

    for record_index, record in enumerate(evidence_records):
        for collection in ("inputs", "outputs"):
            for artifact_index, artifact in enumerate(record[collection]):
                sha256 = artifact["integrity"].get("sha256")
                if sha256:
                    verify_local_artifact(
                        artifact["uri"],
                        sha256,
                        (
                            "$.design_loop_card.evidence.records"
                            f"[{record_index}].{collection}[{artifact_index}].uri"
                        ),
                    )

    replay = loop_card.get("replay")
    if replay:
        replay_artifacts = [("environment_binding", replay["environment_binding"])]
        replay_artifacts.extend(
            (f"inputs[{index}]", artifact)
            for index, artifact in enumerate(replay["inputs"])
        )
        replay_artifacts.extend(
            (f"outputs[{index}]", artifact)
            for index, artifact in enumerate(replay["outputs"])
        )
        for suffix, artifact in replay_artifacts:
            verify_local_artifact(
                artifact["uri"],
                artifact["sha256"],
                f"$.design_loop_card.replay.{suffix}.uri",
            )

    return findings


def card_validation_findings(
    card_path: Path,
    *,
    schema_path: Path | None = None,
) -> list[Finding]:
    """Validate a YAML or JSON card against the canonical versioned contract."""
    location = _relative(card_path)
    if not card_path.exists():
        return [Finding("error", "card-missing", location, "card file does not exist")]

    try:
        if card_path.suffix.lower() == ".json":
            card = json.loads(card_path.read_text(encoding="utf-8"))
        elif card_path.suffix.lower() in {".yaml", ".yml"}:
            try:
                import yaml
            except ImportError:
                return [
                    Finding(
                        "error",
                        "missing-yaml",
                        "python",
                        "PyYAML is required to validate YAML design-loop cards",
                    )
                ]
            card = yaml.safe_load(card_path.read_text(encoding="utf-8"))
        else:
            return [
                Finding(
                    "error",
                    "card-file-type",
                    location,
                    "design-loop cards must use a .yaml, .yml, or .json extension",
                )
            ]
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [Finding("error", "card-parse", location, str(exc))]
    except Exception as exc:
        # PyYAML's parser exception is intentionally caught without importing it
        # at module load time, so JSON validation does not require PyYAML.
        return [Finding("error", "card-parse", location, str(exc))]

    if not isinstance(card, dict):
        return [
            Finding(
                "error",
                "card-document-type",
                location,
                "card document must be a mapping/object",
            )
        ]

    declared_version = card.get("schema_version")
    if schema_path is None:
        if (
            not isinstance(declared_version, str)
            or declared_version not in CARD_SCHEMA_PATHS
        ):
            supported = ", ".join(f"'{version}'" for version in CARD_SCHEMA_PATHS)
            return [
                Finding(
                    "error",
                    "card-schema-version",
                    f"{location}:$.schema_version",
                    f"unsupported schema version {declared_version!r}; supported versions are {supported}",
                )
            ]
        schema_path = CARD_SCHEMA_PATHS[declared_version]

    if not schema_path.exists():
        return [
            Finding(
                "error",
                "card-schema-missing",
                _relative(schema_path),
                "canonical design-loop card schema does not exist",
            )
        ]

    try:
        from jsonschema import Draft202012Validator, FormatChecker
        from jsonschema.exceptions import SchemaError
        from referencing import Registry, Resource
    except ImportError:
        return [
            Finding(
                "error",
                "missing-jsonschema",
                "python",
                "jsonschema is required to validate design-loop cards",
            )
        ]

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, UnicodeError, json.JSONDecodeError, SchemaError) as exc:
        return [
            Finding(
                "error",
                "card-schema-invalid",
                _relative(schema_path),
                str(exc),
            )
        ]

    registry = Registry()
    known_schema_paths = set(CARD_SCHEMA_PATHS.values()) | {schema_path}
    for known_path in known_schema_paths:
        if not known_path.exists():
            continue
        known_schema = json.loads(known_path.read_text(encoding="utf-8"))
        schema_id = known_schema.get("$id")
        if schema_id:
            registry = registry.with_resource(
                schema_id, Resource.from_contents(known_schema)
            )

    validator = Draft202012Validator(
        schema, registry=registry, format_checker=FormatChecker()
    )
    expected_version = (
        schema.get("properties", {}).get("schema_version", {}).get("const")
    )
    errors = sorted(
        validator.iter_errors(card),
        key=lambda error: (
            list(error.absolute_path),
            list(error.absolute_schema_path),
            error.message,
        ),
    )
    findings = [
        Finding(
            "error",
            "card-schema",
            f"{location}:{_card_json_path(error.absolute_path)}",
            _card_schema_message(error, card, expected_version=expected_version),
        )
        for error in errors
    ]
    if not findings and declared_version == "2.0":
        findings.extend(_card_v2_semantic_findings(card, card_path))
    return findings


def run_card_check(card_path: Path) -> None:
    findings = card_validation_findings(card_path)
    if not findings:
        console.print(
            f"[green]passed[/green] design-loop card ({_relative(card_path)})"
        )
        return
    for finding in findings:
        console.print(
            f"{finding.severity} [{finding.code}] {finding.location}: {finding.message}",
            markup=False,
            soft_wrap=True,
        )
    raise typer.Exit(1)


def content_qmd_files() -> list[Path]:
    paths: list[Path] = [path for path in BOOK_FRONTMATTER if path.exists()]
    for path in BOOK_INCLUDE_ONLY_SOURCES:
        if path.exists() and path.resolve() not in {p.resolve() for p in paths}:
            paths.append(path)
    for content_root in CONTENT_ROOTS:
        if content_root.exists():
            paths.extend(content_root.rglob("*.qmd"))
    return sorted(paths)


def book_ordered_qmd_files() -> list[Path]:
    """Return content files in the order declared by Quarto's book manifest."""
    manifest = BOOK_DIR / "_quarto.yml"
    content_paths = {path.resolve() for path in content_qmd_files()}
    if not manifest.exists():
        return sorted(content_paths)

    config, findings = _load_quarto_config()
    if findings:
        return sorted(content_paths)

    ordered = [path for path in _manifest_qmd_entries(config) if path in content_paths]

    ordered_set = set(ordered)
    ordered.extend(sorted(content_paths - ordered_set))
    return ordered


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def label_kind(label: str) -> str:
    if label.startswith(("fig-", "fig:")):
        return "figure"
    if label.startswith(("tbl-", "tab:")):
        return "table"
    if label.startswith(("eq-", "eq:")):
        return "equation"
    if label.startswith(("sec-", "sec:")):
        return "section"
    if label.startswith(("lst-", "lst:")):
        return "listing"
    if label.startswith("pri-"):
        return "principle"
    return "label"


def collect_labels(path: Path) -> list[ManuscriptLabel]:
    text = path.read_text(encoding="utf-8")
    labels: list[ManuscriptLabel] = []

    for match in QUARTO_LABEL_RE.finditer(text):
        label = match.group("label")
        labels.append(
            ManuscriptLabel(
                path, line_number(text, match.start()), label, label_kind(label)
            )
        )

    for match in LATEX_LABEL_RE.finditer(text):
        label = match.group("label")
        labels.append(
            ManuscriptLabel(
                path, line_number(text, match.start()), label, label_kind(label)
            )
        )

    for match in CHUNK_LABEL_RE.finditer(text):
        label = match.group("label")
        labels.append(
            ManuscriptLabel(
                path, line_number(text, match.start()), label, label_kind(label)
            )
        )

    return labels


def collect_refs(paths: list[Path]) -> set[str]:
    refs: set[str] = set()
    for path in paths:
        for _, line in manuscript_source_lines(path):
            refs.update(match.group("label") for match in QUARTO_REF_RE.finditer(line))
            refs.update(match.group("label") for match in LATEX_REF_RE.finditer(line))
    return refs


def equivalent_ref_labels(label: str) -> set[str]:
    if label.startswith("tab:"):
        return {label, f"tbl-{label[4:]}"}
    if label.startswith("tbl-"):
        return {label, f"tab:{label[4:]}"}
    if label.startswith("fig:"):
        return {label, f"fig-{label[4:]}"}
    if label.startswith("fig-"):
        return {label, f"fig:{label[4:]}"}
    if label.startswith("eq:"):
        return {label, f"eq-{label[3:]}"}
    if label.startswith("eq-"):
        return {label, f"eq:{label[3:]}"}
    if label.startswith("sec:"):
        return {label, f"sec-{label[4:]}"}
    if label.startswith("sec-"):
        return {label, f"sec:{label[4:]}"}
    if label.startswith("lst:"):
        return {label, f"lst-{label[4:]}"}
    if label.startswith("lst-"):
        return {label, f"lst:{label[4:]}"}
    return {label}


def undefined_ref_findings(paths: list[Path]) -> list[Finding]:
    labels: set[str] = set()
    for path in paths:
        for label in collect_labels(path):
            labels.update(equivalent_ref_labels(label.label))

    findings: list[Finding] = []
    for path in paths:
        for line_number_value, line in manuscript_source_lines(path):
            for regex in (QUARTO_REF_RE, LATEX_REF_RE):
                for match in regex.finditer(line):
                    ref = match.group("label")
                    if not (equivalent_ref_labels(ref) & labels):
                        findings.append(
                            Finding(
                                "error",
                                "undefined-crossref",
                                f"{_relative(path)}:{line_number_value}",
                                f"cross-reference target '{ref}' is not defined",
                            )
                        )
    return findings


def unreferenced_label_findings(
    targets: list[Path], all_paths: list[Path]
) -> list[Finding]:
    refs = collect_refs(all_paths)
    findings: list[Finding] = []

    for path in targets:
        for label in collect_labels(path):
            if not label.label.startswith(REQUIRED_REFERENCED_LABEL_PREFIXES):
                continue
            if not (equivalent_ref_labels(label.label) & refs):
                findings.append(
                    Finding(
                        "error",
                        "unreferenced-label",
                        f"{_relative(label.path)}:{label.line}",
                        f"unreferenced {label.kind} label '{label.label}'",
                    )
                )

    return findings


def table_findings(path: Path) -> list[Finding]:
    text = path.read_text(encoding="utf-8")
    findings: list[Finding] = []

    for index, row in enumerate(text.splitlines(), start=1):
        if row.lstrip().startswith("|") and ("\\(" in row or "\\)" in row):
            findings.append(
                Finding(
                    "error",
                    "pipe-table-math",
                    f"{_relative(path)}:{index}",
                    r"pipe-table rows should use $...$ inline math, not \(...\), so HTML and PDF render consistently",
                )
            )

    for match in TABLE_ENV_RE.finditer(text):
        line = line_number(text, match.start())
        location = f"{_relative(path)}:{line}"
        option = match.group("option") or ""
        body = match.group("body")
        findings.append(
            Finding(
                "error",
                "raw-latex-table",
                location,
                "raw LaTeX tables are PDF-only; use a Quarto-native table with a #tbl-* label so HTML and PDF both render and cross-reference it",
            )
        )

        if not option:
            findings.append(
                Finding(
                    "error",
                    "table-placement",
                    location,
                    r"raw LaTeX table has no placement option; use \begin{table}[H]",
                )
            )
        elif option != "[H]":
            findings.append(
                Finding(
                    "error",
                    "table-placement",
                    location,
                    f"raw LaTeX table placement {option} allows floating; use [H]",
                )
            )

        if "\\caption" not in body:
            findings.append(
                Finding(
                    "error",
                    "table-caption",
                    location,
                    "raw LaTeX table is missing a caption",
                )
            )
        if "\\label{tab:" not in body:
            findings.append(
                Finding(
                    "error",
                    "table-label",
                    location,
                    "raw LaTeX table is missing a tab: label",
                )
            )
        for spacing_match in ARRAYSTRETCH_RE.finditer(body):
            value = float(spacing_match.group("value"))
            if value < MIN_ARRAYSTRETCH:
                findings.append(
                    Finding(
                        "error",
                        "table-spacing",
                        f"{_relative(path)}:{line_number(text, match.start('body') + spacing_match.start())}",
                        f"raw LaTeX table sets \\arraystretch to {value:g}; use at least {MIN_ARRAYSTRETCH:g}",
                    )
                )
        for spacing_match in TABCOLSEP_RE.finditer(body):
            value = float(spacing_match.group("value"))
            if value < MIN_TABCOLSEP_PT:
                findings.append(
                    Finding(
                        "error",
                        "table-spacing",
                        f"{_relative(path)}:{line_number(text, match.start('body') + spacing_match.start())}",
                        f"raw LaTeX table sets \\tabcolsep to {value:g}pt; use at least {MIN_TABCOLSEP_PT:g}pt or split the table",
                    )
                )

    return findings


def manuscript_source_lines(path: Path) -> Iterable[tuple[int, str]]:
    in_fence = False
    for line_number_value, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        yield line_number_value, line


def structural_reference_findings(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    # @chap-* is deliberately absent from the guidance. CHAP_LABEL_OR_REF_RE
    # rejects it, because Quarto resolves a chapter through its section label
    # and renders @sec-* against a chapter H1 as the chapter reference. Naming
    # @chap-* here would advise the one form this rule refuses.
    message = "use top-level cross-references (@sec-*, @fig-*, @tbl-*, @lst-*, @eq-*) instead of hard-coded chapter, section, appendix, figure, table, listing, or equation numbers"

    for line_number_value, line in manuscript_source_lines(path):
        if CHAP_LABEL_OR_REF_RE.search(line) or LATEX_SECTION_REF_RE.search(line):
            findings.append(
                Finding(
                    "error",
                    "raw-structure-reference",
                    f"{_relative(path)}:{line_number_value}",
                    message,
                )
            )
            continue
        line_prose_only = re.sub(r"\[@[^\]]+\]", "", line)
        if RAW_STRUCTURE_REF_RE.search(line_prose_only):
            findings.append(
                Finding(
                    "error",
                    "raw-structure-reference",
                    f"{_relative(path)}:{line_number_value}",
                    message,
                )
            )

    return findings


ANCHOR_SUFFIX_RE = re.compile(r"\s*\{#.*")


def only_child_section_findings(path: Path) -> list[Finding]:
    """Flag a section whose subdivision produced exactly one subsection.

    A lone subsection is not a division. It promises the reader a set and then
    delivers one member, and in the table of contents it shows up as a single
    indented entry under its parent with no sibling to justify the indent.
    Either the subsection is the parent's remaining content, in which case the
    heading should be removed or promoted, or a sibling is missing.

    Reported without a replacement because the resolution is an authorial
    choice between promoting, deleting, and splitting.
    """
    headings = [
        (number, len(match.group(1)), match.group(2).strip())
        for number, line in manuscript_source_lines(path)
        for match in [re.match(r"^(#{2,4})\s+(.*)$", line)]
        if match
    ]
    findings: list[Finding] = []
    for index, (number, level, title) in enumerate(headings):
        children = []
        for _, other_level, other_title in headings[index + 1 :]:
            if other_level <= level:
                break
            if other_level == level + 1:
                children.append(other_title)
        if len(children) == 1:
            # Computed outside the f-strings below: a backslash inside an
            # f-string expression is a SyntaxError before Python 3.12, and CI
            # runs 3.10 and 3.11.
            parent_title = ANCHOR_SUFFIX_RE.sub("", title)
            child_title = ANCHOR_SUFFIX_RE.sub("", children[0])
            findings.append(
                Finding(
                    "error",
                    "only-child-section",
                    f"{_relative(path)}:{number}",
                    f'"{parent_title}" has exactly one subsection '
                    f'("{child_title}"); promote it, fold it into the parent, '
                    "or give it a sibling",
                    context=("#" * level) + " " + title,
                )
            )
    return findings


FOOTNOTE_BEFORE_PUNCT_RE = re.compile(
    r"(?P<marker>\[\^[A-Za-z0-9_-]+\])(?P<punct>[.,;:!?])(?!\S)"
)


def footnote_punctuation_findings(path: Path) -> list[Finding]:
    """Flag footnote markers that sit inside trailing punctuation.

    House style puts the marker after the punctuation ("text.[^fn]"), not
    before it ("text[^fn]."). The fix is a pure transposition of two adjacent
    tokens, so each finding carries the exact span and its replacement and can
    be applied without reading the sentence.

    A definition line ("[^fn]: body") is not a marker and is excluded by
    requiring the punctuation to be followed by whitespace or end of line.
    """
    findings: list[Finding] = []
    for line_number_value, line in manuscript_source_lines(path):
        if line.lstrip().startswith("[^"):
            continue
        for match in FOOTNOTE_BEFORE_PUNCT_RE.finditer(line):
            marker, punct = match.group("marker"), match.group("punct")
            findings.append(
                Finding(
                    "error",
                    "footnote-inside-punctuation",
                    f"{_relative(path)}:{line_number_value}",
                    f'footnote marker precedes "{punct}"; house style puts the '
                    f"marker after trailing punctuation",
                    span=match.group(0),
                    replacement=f"{punct}{marker}",
                    context=line.rstrip(),
                )
            )
    return findings


def deictic_reference_findings(path: Path) -> list[Finding]:
    """Flag prose that points at a chapter, section, or float by position.

    "In the next chapter" and "the table above" are hard-coded structure
    references wearing a different coat. They read as harmless because they
    carry no number, but they break under exactly the same edit: reorder two
    chapters, or let a float land on the previous page, and the sentence now
    misdirects the reader with nothing in the build to catch it.

    A line that already carries a cross-reference is exempt. "In the next
    chapter (@sec-loop-patterns-across-stack), we ask..." names its target, so
    the deictic phrase is prose colour rather than the only pointer, and it
    survives a reorder.
    """
    findings: list[Finding] = []
    for line_number_value, line in manuscript_source_lines(path):
        if ANY_CROSSREF_RE.search(line):
            continue
        match = DEICTIC_STRUCTURE_RE.search(re.sub(r"\[@[^\]]+\]", "", line))
        if match:
            findings.append(
                Finding(
                    "error",
                    "deictic-structure-reference",
                    f"{_relative(path)}:{line_number_value}",
                    f'"{match.group(0)}" points at structure by position; name the '
                    "target with a cross-reference (@sec-*, @fig-*, @tbl-*, @lst-*) "
                    "so it survives a reorder",
                )
            )
    return findings


XHTML_VOID_RE = re.compile(
    r"<(br|img|hr|input|meta|link|source|col|area|embed|wbr)((?:\s[^>]*?)?)(?<!/)>",
    re.IGNORECASE,
)


def xhtml_void_tag_findings(path: Path) -> list[Finding]:
    """Reject unclosed void tags, which are valid HTML but break the EPUB.

    EPUB content is XHTML, so every element must close. A raw ``<br>`` renders
    fine in HTML and then fails EPUB generation with a mismatched-tag parse
    error naming a line in a built artifact, which is a long way from the
    manuscript line that caused it. Checked here so the failure names the
    source file instead.
    """
    findings: list[Finding] = []
    text = path.read_text(encoding="utf-8")
    for match in XHTML_VOID_RE.finditer(text):
        tag = match.group(1).lower()
        findings.append(
            Finding(
                "error",
                "xhtml-unclosed-void-tag",
                f"{_relative(path)}:{line_number(text, match.start())}",
                f"<{tag}> is not closed; EPUB content is XHTML and will fail to "
                f"parse. Write <{tag}/>",
            )
        )
    return findings


def svg_wellformed_findings() -> list[Finding]:
    """Reject SVG assets that are not well-formed XML.

    The PDF build shells out to rsvg-convert, which parses every SVG as XML and
    aborts the whole render when one fails. The usual cause is a bare ``&`` in a
    CSS comment inside a ``<style>`` block, which XML reads as the start of an
    entity reference. Wrapping the block in ``<![CDATA[ ... ]]>`` fixes it and
    keeps the next one from happening. Checked here so a malformed asset fails
    at commit time rather than eight minutes into a render.
    """
    import xml.etree.ElementTree as ElementTree

    findings: list[Finding] = []
    for svg_path in sorted((ROOT / "book").rglob("*.svg")):
        try:
            ElementTree.parse(svg_path)
        except ElementTree.ParseError as exc:
            findings.append(
                Finding(
                    "error",
                    "svg-malformed",
                    f"{_relative(svg_path)}:{exc.position[0]}",
                    f"SVG is not well-formed XML ({exc.msg}); rsvg-convert will abort the "
                    "PDF build. A bare '&', '<', or '>' inside a <style> block is the usual "
                    "cause, so wrap the block in <![CDATA[ ... ]]>",
                )
            )
    return findings


def figure_path_findings(path: Path) -> list[Finding]:
    text = path.read_text(encoding="utf-8")
    findings: list[Finding] = []

    for match in MARKDOWN_FIGURE_RE.finditer(text):
        target = match.group("target")
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
            continue

        line = line_number(text, match.start())
        location = f"{_relative(path)}:{line}"
        resolved = (path.parent / target).resolve()
        try:
            resolved.relative_to(ROOT)
        except ValueError:
            findings.append(
                Finding(
                    "error",
                    "figure-path",
                    location,
                    f"figure '{match.group('label')}' points outside the repo: {target}",
                )
            )
            continue

        exists = resolved.exists()
        if not exists and not resolved.suffix:
            exists = any(
                resolved.with_suffix(suffix).exists()
                for suffix in (".pdf", ".svg", ".png", ".jpg", ".jpeg")
            )

        if not exists:
            findings.append(
                Finding(
                    "error",
                    "figure-path",
                    location,
                    f"figure '{match.group('label')}' target does not exist: {target}",
                )
            )

    return findings


def figure_source_findings(path: Path) -> list[Finding]:
    text = path.read_text(encoding="utf-8")
    findings: list[Finding] = []

    for match in MARKDOWN_FIGURE_ATTR_RE.finditer(text):
        line = line_number(text, match.start())
        attrs = match.group("attrs")
        label = match.group("label")
        location = f"{_relative(path)}:{line}"
        if re.search(r"\bfig-pos\s*=", attrs):
            findings.append(
                Finding(
                    "error",
                    "figure-placement-override",
                    location,
                    f"figure '{label}' uses fig-pos; let Quarto/LaTeX place figures unless a rendered defect requires an override",
                )
            )
        alt_match = re.search(r"\bfig-alt\s*=\s*\"([^\"]+)\"", attrs)
        if not alt_match or len(alt_match.group(1).strip()) < 12:
            findings.append(
                Finding(
                    "error",
                    "figure-alt",
                    location,
                    f"figure '{label}' is missing meaningful fig-alt text",
                )
            )
        elif ALT_TEXT_REF_RE.search(alt_match.group(1)):
            findings.append(
                Finding(
                    "error",
                    "figure-alt-reference",
                    location,
                    f"figure '{label}' has a cross-reference marker in its fig-alt text; "
                    "Quarto does not expand @refs there, so it reaches the rendered HTML "
                    "verbatim and a screen reader announces the raw label. Describe the "
                    "target in words instead",
                )
            )

    in_chunk = False
    chunk_label: str | None = None
    chunk_label_line = 0
    chunk_has_alt = False
    for index, line in enumerate(text.splitlines(), start=1):
        if not in_chunk and CHUNK_START_RE.match(line):
            in_chunk = True
            chunk_label = None
            chunk_label_line = index
            chunk_has_alt = False
            continue
        if not in_chunk:
            continue
        if line.strip().startswith("```"):
            if chunk_label and not chunk_has_alt:
                findings.append(
                    Finding(
                        "error",
                        "figure-alt",
                        f"{_relative(path)}:{chunk_label_line}",
                        f"generated figure '{chunk_label}' is missing a fig-alt chunk option",
                    )
                )
            in_chunk = False
            chunk_label = None
            continue
        label_match = CHUNK_LABEL_RE.match(line)
        if label_match:
            chunk_label = label_match.group("label")
            chunk_label_line = index
            continue
        alt_match = CHUNK_FIG_ALT_RE.match(line)
        if alt_match and alt_match.group("alt").strip().strip('"'):
            chunk_has_alt = True
            if ALT_TEXT_REF_RE.search(alt_match.group("alt")):
                findings.append(
                    Finding(
                        "error",
                        "figure-alt-reference",
                        f"{_relative(path)}:{index}",
                        f"generated figure '{chunk_label or 'unlabeled'}' has a cross-reference "
                        "marker in its fig-alt text; Quarto does not expand @refs there, so it "
                        "reaches the rendered HTML verbatim and a screen reader announces the "
                        "raw label. Describe the target in words instead",
                    )
                )
            continue
        pos_match = CHUNK_FIG_POS_RE.match(line)
        if pos_match and chunk_label:
            findings.append(
                Finding(
                    "error",
                    "figure-placement-override",
                    f"{_relative(path)}:{index}",
                    f"generated figure '{chunk_label}' uses fig-pos; let Quarto/LaTeX place figures unless a rendered defect requires an override",
                )
            )

    return findings


def manuscript_integrity_findings() -> list[Finding]:
    all_paths = content_qmd_files()
    findings: list[Finding] = []
    findings.extend(undefined_ref_findings(all_paths))
    findings.extend(suppression_hygiene_findings(all_paths))
    findings.extend(unreferenced_label_findings(all_paths, all_paths))
    findings.extend(svg_wellformed_findings())
    for path in all_paths:
        findings.extend(xhtml_void_tag_findings(path))
        findings.extend(figure_path_findings(path))
        findings.extend(figure_source_findings(path))
        findings.extend(table_findings(path))
        findings.extend(structural_reference_findings(path))
        findings.extend(deictic_reference_findings(path))
        findings.extend(only_child_section_findings(path))
    return sorted(
        findings, key=lambda finding: (finding.location, finding.code, finding.message)
    )


def is_crossref_key(key: str) -> bool:
    return key.startswith(
        tuple(f"{prefix}-" for prefix in CANONICAL_CROSSREF_PREFIXES)
        + ("fig:", "tab:", "eq:", "sec:", "lst:")
    )


def citation_chapter_name(path: Path) -> str:
    try:
        rel = path.relative_to(BOOK_DIR)
    except ValueError:
        rel = path.relative_to(ROOT)
    parts = rel.parts
    if len(parts) >= 3 and parts[0] == "contents":
        if parts[1] in {"chapters", "backmatter", "frontmatter", "parts"}:
            return parts[2]
    if len(parts) >= 2 and parts[0] in {"chapters", "backmatter", "frontmatter"}:
        return parts[1]
    return str(rel)


def collect_citation_occurrences(
    paths: list[Path],
) -> dict[str, list[CitationOccurrence]]:
    hits: dict[str, list[CitationOccurrence]] = {}
    for path in paths:
        for line, text in manuscript_source_lines(path):
            for match in CITE_RE.finditer(text):
                key = match.group("key").rstrip(".,;:]})")
                if is_crossref_key(key):
                    continue
                hits.setdefault(key, []).append(
                    CitationOccurrence(path, line, text.strip())
                )
    return hits


def citation_reuse_findings(
    *, min_total: int = 4, min_chapters: int = 2, show_context: bool = False
) -> list[Finding]:
    rows: list[Finding] = []
    hits = collect_citation_occurrences(content_qmd_files())
    for key, occurrences in hits.items():
        chapters = sorted({citation_chapter_name(hit.path) for hit in occurrences})
        if len(occurrences) >= min_total or len(chapters) >= min_chapters:
            message = f"{len(occurrences)} uses across {len(chapters)} chapter(s): {' | '.join(chapters)}"
            rows.append(Finding("warning", "citation-reuse", key, message))
            if show_context:
                for occurrence in occurrences:
                    rows.append(
                        Finding(
                            "warning",
                            "citation-reuse-context",
                            f"{_relative(occurrence.path)}:{occurrence.line}",
                            occurrence.context,
                        )
                    )
    return sorted(rows, key=lambda finding: (finding.code, finding.location))


def bibliography_entry_keys(bib_path: Path = CANONICAL_BIBLIOGRAPHY) -> set[str]:
    if not bib_path.exists():
        return set()
    text = bib_path.read_text(encoding="utf-8")
    return {
        match.group("key")
        for match in re.finditer(r"@\w+\s*\{\s*(?P<key>[^,\s]+)", text)
    }


def citation_resolution_findings(
    paths: list[Path] | None = None,
    bib_path: Path = CANONICAL_BIBLIOGRAPHY,
) -> list[Finding]:
    targets = paths if paths is not None else content_qmd_files()
    keys = bibliography_entry_keys(bib_path)
    findings: list[Finding] = []
    if not bib_path.exists():
        return [
            Finding(
                "error",
                "missing-bibliography",
                _relative(bib_path),
                "canonical bibliography file is missing",
            )
        ]
    for key, occurrences in collect_citation_occurrences(targets).items():
        if key in keys:
            continue
        for occurrence in occurrences:
            findings.append(
                Finding(
                    "error",
                    "undefined-citation",
                    f"{_relative(occurrence.path)}:{occurrence.line}",
                    f"citation key '@{key}' is not defined in {_relative(bib_path)}",
                )
            )
    return sorted(findings, key=lambda finding: (finding.location, finding.message))


def bibliography_style_findings() -> list[Finding]:
    findings: list[Finding] = []
    quarto_path = BOOK_DIR / "_quarto.yml"
    if not quarto_path.exists():
        return [
            Finding(
                "error",
                "missing-quarto-config",
                _relative(quarto_path),
                "book configuration is missing",
            )
        ]

    try:
        import yaml
    except ImportError:
        findings.append(
            Finding(
                "error",
                "missing-yaml",
                "python",
                "PyYAML is required for bibliography style validation",
            )
        )
        return findings

    try:
        config = yaml.safe_load(quarto_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        findings.append(
            Finding(
                "error",
                "invalid-quarto-yaml",
                _relative(quarto_path),
                str(exc),
            )
        )
        return findings

    bibliography = config.get("bibliography")
    if bibliography != ["references/references.bib"]:
        findings.append(
            Finding(
                "error",
                "bibliography-style",
                _relative(quarto_path),
                "use the canonical bibliography list: references/references.bib",
            )
        )
    if config.get("csl") != "csl/chicago-author-date.csl":
        findings.append(
            Finding(
                "error",
                "bibliography-style",
                _relative(quarto_path),
                "use the canonical HTML/EPUB CSL file: csl/chicago-author-date.csl",
            )
        )
    pdf_config = (config.get("format") or {}).get("pdf") or {}
    if pdf_config.get("biblio-style") != "spbasic":
        findings.append(
            Finding(
                "error",
                "bibliography-style",
                _relative(quarto_path),
                "PDF output should use the Springer spbasic bibliography style",
            )
        )
    if pdf_config.get("cite-method") != "natbib":
        findings.append(
            Finding(
                "error",
                "bibliography-style",
                _relative(quarto_path),
                "PDF output should use natbib citations",
            )
        )

    for path, code, message in (
        (
            CANONICAL_BIBLIOGRAPHY,
            "missing-bibliography",
            "canonical bibliography file is missing",
        ),
        (
            CANONICAL_CSL,
            "missing-csl",
            "canonical CSL style file is missing",
        ),
    ):
        if not path.exists():
            findings.append(Finding("error", code, _relative(path), message))

    if not CANONICAL_BIBLIOGRAPHY.exists():
        return findings

    bib_text = CANONICAL_BIBLIOGRAPHY.read_text(encoding="utf-8")
    key_matches = list(re.finditer(r"@(?P<type>\w+)\s*\{\s*(?P<key>[^,\s]+)", bib_text))
    seen: dict[str, int] = {}
    for match in key_matches:
        key = match.group("key")
        line = line_number(bib_text, match.start())
        if key in seen:
            findings.append(
                Finding(
                    "error",
                    "duplicate-bib-key",
                    f"{_relative(CANONICAL_BIBLIOGRAPHY)}:{line}",
                    f"duplicate bibliography key '{key}' first appears on line {seen[key]}",
                )
            )
        seen[key] = line

    try:
        from pybtex.database.input import bibtex

        bibliography_data = bibtex.Parser().parse_file(str(CANONICAL_BIBLIOGRAPHY))
    except Exception as exc:
        findings.append(
            Finding(
                "error",
                "invalid-bibliography",
                _relative(CANONICAL_BIBLIOGRAPHY),
                f"BibTeX parser failed: {exc}",
            )
        )
        return findings

    required_fields_by_type = {
        "article": ("title", "year", "journal"),
        "book": ("title", "year", "publisher"),
        "inproceedings": ("title", "year", "booktitle"),
        "techreport": ("title", "year", "institution"),
        "phdthesis": ("title", "year", "school"),
        "mastersthesis": ("title", "year", "school"),
        "misc": ("title", "year"),
    }
    key_lines = {
        match.group("key"): line_number(bib_text, match.start())
        for match in key_matches
    }
    for key, entry in bibliography_data.entries.items():
        entry_type = entry.type.lower()
        fields = {field.lower(): value for field, value in entry.fields.items()}
        line = key_lines.get(key, 1)
        location = f"{_relative(CANONICAL_BIBLIOGRAPHY)}:{line}"
        required_fields = required_fields_by_type.get(entry_type, ("title", "year"))
        missing = [field for field in required_fields if not fields.get(field)]
        if missing:
            findings.append(
                Finding(
                    "error",
                    "incomplete-bib-entry",
                    location,
                    f"{key} is missing required field(s): {', '.join(missing)}",
                )
            )
        has_identity = bool(
            entry.persons.get("author")
            or entry.persons.get("editor")
            or fields.get("organization")
            or fields.get("key")
        )
        if not has_identity:
            findings.append(
                Finding(
                    "error",
                    "incomplete-bib-entry",
                    location,
                    f"{key} needs author, editor, organization, or key metadata",
                )
            )
        if entry_type == "misc" and not any(
            fields.get(field)
            for field in ("doi", "url", "howpublished", "note", "organization")
        ):
            findings.append(
                Finding(
                    "warning",
                    "thin-bib-entry",
                    location,
                    f"{key} is a misc entry without DOI, URL, organization, howpublished, or note",
                )
            )

    return sorted(
        findings, key=lambda finding: (finding.severity, finding.location, finding.code)
    )


def bibliography_findings() -> list[Finding]:
    findings = bibliography_style_findings()
    findings.extend(citation_resolution_findings())
    return sorted(
        findings, key=lambda finding: (finding.location, finding.code, finding.message)
    )


def _load_quarto_config() -> tuple[dict, list[Finding]]:
    quarto_path = BOOK_DIR / "_quarto.yml"
    if not quarto_path.exists():
        return {}, [
            Finding(
                "error",
                "missing-quarto-config",
                _relative(quarto_path),
                "book configuration is missing",
            )
        ]
    try:
        import yaml
    except ImportError:
        return {}, [
            Finding(
                "error",
                "missing-yaml",
                "python",
                "PyYAML is required for Quarto manifest validation",
            )
        ]
    try:
        return yaml.safe_load(quarto_path.read_text(encoding="utf-8")) or {}, []
    except yaml.YAMLError as exc:
        return {}, [
            Finding(
                "error",
                "invalid-quarto-yaml",
                _relative(quarto_path),
                str(exc),
            )
        ]


def _flatten_manifest_items(items: list) -> list[str]:
    """Flatten Quarto chapter items, including QMD-backed part openers."""
    flat: list[str] = []
    for item in items:
        if isinstance(item, str):
            flat.append(item)
            continue
        if not isinstance(item, dict):
            continue

        file_path = item.get("file") or item.get("href")
        if isinstance(file_path, str):
            flat.append(file_path)

        part = item.get("part")
        if isinstance(part, str) and part.endswith(".qmd"):
            flat.append(part)

        chapters = item.get("chapters")
        if isinstance(chapters, list):
            flat.extend(_flatten_manifest_items(chapters))
    return flat


def _extract_qmds(items: list) -> list[Path]:
    return [
        (BOOK_DIR / item).resolve()
        for item in _flatten_manifest_items(items)
        if item.strip() != "---" and item.endswith(".qmd")
    ]


def _manifest_qmd_entries(config: dict) -> list[Path]:
    book_config = config.get("book") or {}
    entries: list[Path] = []
    for section in ("chapters", "appendices"):
        raw_items = book_config.get(section) or []
        if isinstance(raw_items, list):
            entries.extend(_extract_qmds(raw_items))
    return entries


def _book_qmd_files() -> list[Path]:
    files: list[Path] = []
    for path in BOOK_DIR.rglob("*.qmd"):
        if any(part in {"_build", "_freeze"} for part in path.parts):
            continue
        files.append(path.resolve())
    return sorted(files)


def manifest_findings() -> list[Finding]:
    config, findings = _load_quarto_config()
    if findings:
        return findings

    quarto_path = BOOK_DIR / "_quarto.yml"
    book_config = config.get("book") or {}
    if not isinstance(book_config, dict):
        return [
            Finding(
                "error",
                "book-manifest",
                _relative(quarto_path),
                "Quarto config is missing the book section",
            )
        ]

    entries = _manifest_qmd_entries(config)
    entry_set = set(entries)
    actual_qmds = set(_book_qmd_files())

    seen: dict[Path, int] = {}
    for index, entry in enumerate(entries, start=1):
        if entry in seen:
            findings.append(
                Finding(
                    "error",
                    "duplicate-manifest-entry",
                    _relative(quarto_path),
                    f"{_relative(entry)} appears more than once in the book manifest",
                )
            )
        seen[entry] = index
        if not entry.exists():
            findings.append(
                Finding(
                    "error",
                    "missing-manifest-entry",
                    _relative(quarto_path),
                    f"manifest entry does not exist: {_relative(entry)}",
                )
            )

    # A finalized foreword may be added before the acknowledgments, and the AI
    # disclosure page trails the author bio; neither is required front matter.
    optional_frontmatter = {
        "contents/frontmatter/foreword.qmd",
        "contents/frontmatter/disclosure.qmd",
    }
    optional_paths = {
        *(BOOK_DIR / name for name in optional_frontmatter),
        *BOOK_INCLUDE_ONLY_SOURCES,
    }
    for path in sorted(actual_qmds - entry_set - optional_paths):
        findings.append(
            Finding(
                "error",
                "orphan-qmd",
                _relative(path),
                "QMD file is not included in book.chapters or book.appendices",
            )
        )

    chapter_items = _flatten_manifest_items(book_config.get("chapters") or [])
    chapter_qmds = [
        item
        for item in chapter_items
        if isinstance(item, str) and item.endswith(".qmd")
    ]
    expected_frontmatter = [
        "index.qmd",
        "contents/frontmatter/foreword.qmd",
        "contents/frontmatter/acknowledgments.qmd",
        "contents/frontmatter/about-the-author.qmd",
        "contents/frontmatter/disclosure.qmd",
    ]
    present_frontmatter = [
        name
        for name in expected_frontmatter
        if name not in optional_frontmatter or name in chapter_qmds
    ]
    if chapter_qmds[: len(present_frontmatter)] != present_frontmatter:
        findings.append(
            Finding(
                "error",
                "frontmatter-order",
                _relative(quarto_path),
                "front matter should begin with index (includes preface), then "
                "contents/frontmatter/foreword (when included), acknowledgments, "
                "and about-the-author",
            )
        )
    if len(chapter_items) > len(present_frontmatter):
        separator_index = len(present_frontmatter)
        if chapter_items[separator_index] != "---":
            findings.append(
                Finding(
                    "warning",
                    "frontmatter-separator",
                    _relative(quarto_path),
                    "book.chapters should separate front matter from numbered chapters with ---",
                )
            )

    return sorted(
        findings, key=lambda finding: (finding.location, finding.code, finding.message)
    )


UNRESOLVED_RENDERED_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "quarto-unresolved-ref",
        re.compile(r"class=[\"'][^\"']*quarto-unresolved-ref", re.I),
        "Quarto unresolved-reference markup appears in rendered output",
    ),
    (
        "raw-crossref-token",
        re.compile(rf"(?<![#\w])@(?:{CROSSREF_PREFIX_PATTERN}|chap)-[A-Za-z0-9_-]+\b"),
        "raw Quarto cross-reference token appears in rendered output",
    ),
    (
        "raw-citation-token",
        re.compile(r"\[@[A-Za-z0-9:_-]+(?:[;,\s]+@[A-Za-z0-9:_-]+)*\]"),
        "raw citation token appears in rendered output",
    ),
    (
        "broken-numbered-ref",
        re.compile(
            r"\b(?:Chapter|Section|Figure|Table|Listing|Equation)\s+\?+\b",
            re.I,
        ),
        "numbered reference rendered as a question mark",
    ),
    (
        "generic-unresolved-marker",
        re.compile(r"(?<!\?)\?\?(?!\?)|\?\?\?"),
        "generic unresolved marker appears in rendered output",
    ),
    (
        "target-prefixed-question",
        re.compile(r"\?(?:sec|fig|tbl|eq|lst|chap)-[A-Za-z0-9_-]+"),
        "target-prefixed unresolved marker appears in rendered output",
    ),
    (
        "citation-question-marker",
        re.compile(r"\bCitation\?", re.I),
        "citation rendered as an unresolved question marker",
    ),
)


def _visible_html_text(text: str) -> str:
    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", text)
    text = re.sub(r"(?is)<(pre|code|samp|kbd)\b.*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return html_lib.unescape(text)


def _snippet(text: str, start: int, end: int, *, radius: int = 80) -> str:
    return _compact_text(text[max(0, start - radius) : end + radius], limit=180)


HTML_RAW_UNRESOLVED_CODES = {
    "quarto-unresolved-ref",
    "raw-crossref-token",
    "target-prefixed-question",
}


def _scan_rendered_text(
    text: str, *, location: str, include_codes: set[str] | None = None
) -> list[Finding]:
    findings: list[Finding] = []
    for code, pattern, message in UNRESOLVED_RENDERED_PATTERNS:
        if include_codes is not None and code not in include_codes:
            continue
        match = pattern.search(text)
        if not match:
            continue
        findings.append(
            Finding(
                "error",
                code,
                location,
                f"{message}: {_snippet(text, match.start(), match.end())}",
            )
        )
    return findings


def pdf_unresolved_findings(pdf_path: Path = PDF_PATH) -> list[Finding]:
    if not pdf_path.exists():
        return [
            Finding(
                "error",
                "missing-pdf",
                _relative(pdf_path),
                "rendered PDF does not exist",
            )
        ]
    try:
        from pypdf import PdfReader
    except ImportError:
        return [
            Finding(
                "error",
                "missing-pypdf",
                "python",
                "pypdf is required for rendered unresolved-token scanning",
            )
        ]

    logging.getLogger("pypdf").setLevel(logging.ERROR)
    findings: list[Finding] = []
    reader = PdfReader(str(pdf_path))
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        findings.extend(
            _scan_rendered_text(
                text, location=f"{_relative(pdf_path)}:page {page_number}"
            )
        )
    return findings


def html_unresolved_findings(html_root: Path = BUILD_DIR) -> list[Finding]:
    if not html_root.exists():
        return [
            Finding(
                "error",
                "missing-html",
                _relative(html_root),
                "rendered HTML output does not exist",
            )
        ]

    findings: list[Finding] = []
    html_files = sorted(html_root.rglob("*.html"))
    if not html_files:
        return [
            Finding(
                "error",
                "missing-html",
                _relative(html_root),
                "rendered HTML output contains no HTML files",
            )
        ]
    for page_path in html_files:
        page_text = page_path.read_text(encoding="utf-8", errors="replace")
        findings.extend(
            _scan_rendered_text(
                page_text,
                location=_relative(page_path),
                include_codes=HTML_RAW_UNRESOLVED_CODES,
            )
        )
        visible_text = _visible_html_text(page_text)
        findings.extend(
            _scan_rendered_text(visible_text, location=f"{_relative(page_path)}:text")
        )
    return findings


def epub_unresolved_findings(epub_path: Path = EPUB_PATH) -> list[Finding]:
    if not epub_path.exists():
        return [
            Finding(
                "error",
                "missing-epub",
                _relative(epub_path),
                "rendered EPUB does not exist",
            )
        ]
    findings: list[Finding] = []
    try:
        with zipfile.ZipFile(epub_path) as epub:
            names = [
                name
                for name in epub.namelist()
                if name.endswith((".html", ".xhtml")) and not name.endswith("nav.xhtml")
            ]
            for name in names:
                text = epub.read(name).decode("utf-8", errors="replace")
                findings.extend(
                    _scan_rendered_text(
                        text,
                        location=f"{_relative(epub_path)}:{name}",
                        include_codes=HTML_RAW_UNRESOLVED_CODES,
                    )
                )
                findings.extend(
                    _scan_rendered_text(
                        _visible_html_text(text),
                        location=f"{_relative(epub_path)}:{name}:text",
                    )
                )
    except zipfile.BadZipFile:
        return [
            Finding(
                "error",
                "invalid-epub",
                _relative(epub_path),
                "EPUB is not a readable zip package",
            )
        ]
    return findings


def rendered_unresolved_findings(
    *,
    pdf: Path = PDF_PATH,
    html_root: Path = BUILD_DIR,
    epub: Path = EPUB_PATH,
    formats: Iterable[str] | None = None,
) -> list[Finding]:
    format_set = set(formats or _RENDER_FORMATS)
    findings: list[Finding] = []
    if "pdf" in format_set:
        findings.extend(pdf_unresolved_findings(pdf))
    if "html" in format_set:
        findings.extend(html_unresolved_findings(html_root))
    if "epub" in format_set:
        findings.extend(epub_unresolved_findings(epub))
    return sorted(
        findings, key=lambda finding: (finding.location, finding.code, finding.message)
    )


def _pdf_rendered_pages(pdf_path: Path, prefix: Path) -> list[Path] | None:
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        return None
    proc = subprocess.run(
        [pdftoppm, "-r", "144", "-png", str(pdf_path), str(prefix)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    return sorted(prefix.parent.glob(f"{prefix.name}-*.png"))


def _pdf_visual_matches_head(path_text: str, current_path: Path) -> bool | None:
    old_blob = subprocess.run(
        ["git", "show", f"HEAD:{path_text}"],
        cwd=str(ROOT),
        capture_output=True,
    )
    if old_blob.returncode != 0:
        return None
    (ROOT / "tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="arch2-asset-", dir=str(ROOT / "tmp")
    ) as tmp:
        tmp_dir = Path(tmp)
        old_pdf = tmp_dir / "old.pdf"
        old_pdf.write_bytes(old_blob.stdout)
        old_pages = _pdf_rendered_pages(old_pdf, tmp_dir / "old")
        new_pages = _pdf_rendered_pages(current_path, tmp_dir / "new")
        if old_pages is None or new_pages is None:
            return None
        if len(old_pages) != len(new_pages):
            return False
        return all(
            old_page.read_bytes() == new_page.read_bytes()
            for old_page, new_page in zip(old_pages, new_pages)
        )


def generated_asset_findings() -> list[Finding]:
    proc = _run(
        [
            "git",
            "status",
            "--porcelain",
            "--untracked-files=no",
            "--",
            "book/contents/chapters",
            "book/contents/backmatter",
        ],
        capture=True,
    )
    if proc.returncode != 0:
        return [
            Finding(
                "error",
                "git-status",
                "git",
                (proc.stderr or proc.stdout or "git status failed").strip(),
            )
        ]

    findings: list[Finding] = []
    for raw_line in proc.stdout.splitlines():
        if len(raw_line) < 4:
            continue
        status = raw_line[:2]
        path_text = raw_line[3:]
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1]
        path = Path(path_text)
        if "images" not in path.parts:
            continue
        if path.suffix.lower() not in GENERATED_ASSET_SUFFIXES:
            continue
        if path.suffix.lower() in {".svg", ".pdf", ".png"} and status.strip() == "M":
            current_path = ROOT / path
            continue
        findings.append(
            Finding(
                "error",
                "generated-asset-drift",
                path_text,
                f"tracked generated asset is dirty after render ({status.strip() or 'modified'}); commit the refreshed asset or fix nondeterministic generation",
            )
        )
    return findings


def normalize_definition_term(term: str) -> str:
    return re.sub(r"\s+", " ", term.strip().lower())


def definition_matches_concept(definition_term: str, concept: str) -> bool:
    definition_key = normalize_definition_term(definition_term)
    concept_key = normalize_definition_term(concept)
    return definition_key == concept_key or concept_key in definition_key


def has_preview_marker(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in (
            "preview",
            "defined in chapter",
            "defined later",
            "introduced later",
            "chapter 7",
            "chapter 4",
            "chapter 5",
        )
    )


def is_disclosure_prose_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if stripped.startswith(("#", "```", ":::", "!", "|")):
        return False
    if stripped.startswith(">"):
        return False
    if stripped.startswith("\\abstract"):
        return False
    return True


def collect_definition_occurrences(
    paths: list[Path],
) -> dict[str, list[DefinitionOccurrence]]:
    hits: dict[str, list[DefinitionOccurrence]] = {}
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for match in DEFINITION_RE.finditer(text):
            term = " ".join(match.group("term").split())
            key = normalize_definition_term(term)
            context = text.splitlines()[line_number(text, match.start()) - 1].strip()
            hits.setdefault(key, []).append(
                DefinitionOccurrence(
                    path, line_number(text, match.start()), term, context
                )
            )
    return hits


def concept_findings(*, min_uses: int = 3) -> list[Finding]:
    paths = content_qmd_files()
    findings: list[Finding] = []

    for key, occurrences in collect_definition_occurrences(paths).items():
        definition_files = sorted(
            {_relative(occurrence.path) for occurrence in occurrences}
        )
        if len(definition_files) > 1:
            locations = ", ".join(
                f"{_relative(occurrence.path)}:{occurrence.line}"
                for occurrence in occurrences
            )
            findings.append(
                Finding(
                    "error",
                    "duplicate-definition",
                    key,
                    f"definition appears in multiple files: {locations}",
                )
            )

    for concept in DEFAULT_LOOP_CONCEPTS:
        occurrences = _concept_occurrences(concept, paths)
        if 0 < len(occurrences) < min_uses:
            first_path, first_line, _ = occurrences[0]
            findings.append(
                Finding(
                    "warning",
                    "concept-underuse",
                    f"{_relative(first_path)}:{first_line}",
                    f"'{concept}' appears {len(occurrences)} time(s); either deepen/reuse it or avoid a one-off coined term",
                )
            )

    return sorted(
        findings,
        key=lambda finding: (
            finding.severity,
            finding.code,
            finding.location,
            finding.message,
        ),
    )


def disclosure_findings(
    *,
    concepts: tuple[str, ...] = DISCLOSURE_GATED_CONCEPTS,
    min_uses_without_definition: int = 3,
) -> list[Finding]:
    paths = book_ordered_qmd_files()
    path_order = {path.resolve(): index for index, path in enumerate(paths)}
    definitions = collect_definition_occurrences(paths)
    all_definitions = [
        occurrence for occurrences in definitions.values() for occurrence in occurrences
    ]
    findings: list[Finding] = []

    for concept in concepts:
        hits = [
            occurrence
            for occurrence in _concept_occurrences(concept, paths)
            if is_disclosure_prose_line(occurrence[2])
        ]
        if not hits:
            continue

        matching_definitions = [
            occurrence
            for occurrence in all_definitions
            if definition_matches_concept(occurrence.term, concept)
        ]
        if not matching_definitions:
            if len(hits) >= min_uses_without_definition:
                first_path, first_line, _ = hits[0]
                findings.append(
                    Finding(
                        "warning",
                        "missing-concept-definition",
                        f"{_relative(first_path)}:{first_line}",
                        f"'{concept}' appears {len(hits)} time(s) but has no quote-style owner definition block",
                    )
                )
            continue

        owner = min(
            matching_definitions,
            key=lambda occurrence: (
                path_order.get(occurrence.path.resolve(), 10_000),
                occurrence.line,
            ),
        )
        owner_key = (path_order.get(owner.path.resolve(), 10_000), owner.line)
        for hit_path, hit_line, context in hits:
            if hit_path.resolve() == owner.path.resolve():
                continue
            hit_key = (path_order.get(hit_path.resolve(), 10_000), hit_line)
            if hit_key >= owner_key:
                continue
            if has_preview_marker(context):
                continue
            findings.append(
                Finding(
                    "warning",
                    "premature-concept-use",
                    f"{_relative(hit_path)}:{hit_line}",
                    f"'{concept}' appears before its owner definition at {_relative(owner.path)}:{owner.line}",
                )
            )
            break

    return sorted(
        findings, key=lambda finding: (finding.code, finding.location, finding.message)
    )


def count_qmd_figures(content_root: Path = BOOK_DIR) -> int:
    labels: set[str] = set()
    for path in sorted(content_root.rglob("*.qmd")):
        text = path.read_text(encoding="utf-8")
        labels.update(
            match.group("label") for match in MARKDOWN_FIGURE_RE.finditer(text)
        )
        labels.update(
            match.group("label") for match in EXECUTABLE_FIGURE_RE.finditer(text)
        )
    return len(labels)


def count_pdf_visual_xobjects(pdf_path: Path) -> tuple[int, list[tuple[int, int]]]:
    try:
        from pypdf import PdfReader
    except ImportError:
        return (-1, [])

    logging.getLogger("pypdf").setLevel(logging.ERROR)
    reader = PdfReader(str(pdf_path))
    total = 0
    pages: list[tuple[int, int]] = []

    for page_number, page in enumerate(reader.pages, start=1):
        resources = page.get("/Resources") or {}
        xobjects = resources.get("/XObject") if resources else None
        page_total = 0
        if xobjects:
            for obj in xobjects.get_object().values():
                subtype = obj.get_object().get("/Subtype")
                if subtype in {"/Form", "/Image"}:
                    total += 1
                    page_total += 1
        if page_total:
            pages.append((page_number, page_total))

    return total, pages


def pdf_figure_findings(pdf_path: Path = PDF_PATH) -> list[Finding]:
    if not pdf_path.exists():
        return [
            Finding(
                "error",
                "missing-pdf",
                _relative(pdf_path),
                "rendered PDF does not exist",
            )
        ]

    expected = count_qmd_figures()
    actual, pages = count_pdf_visual_xobjects(pdf_path)
    if actual < 0:
        return [
            Finding(
                "error",
                "missing-pypdf",
                "python",
                "pypdf is required for PDF figure verification",
            )
        ]
    if actual < expected:
        return [
            Finding(
                "error",
                "pdf-figures",
                _relative(pdf_path),
                f"PDF has {actual} visual XObjects, but authored QMD references {expected} figures; pages: {pages}",
            )
        ]
    return []


def html_findings(html_path: Path = HTML_PATH) -> list[Finding]:
    if not html_path.exists():
        return [
            Finding(
                "error",
                "missing-html",
                _relative(html_path),
                "rendered HTML index does not exist",
            )
        ]

    text = html_path.read_text(encoding="utf-8", errors="replace")
    findings: list[Finding] = []
    if "arch2-release-meta" not in text:
        findings.append(
            Finding(
                "error",
                "html-release-meta",
                _relative(html_path),
                "HTML is missing the release/date metadata strip",
            )
        )

    html_files = sorted(html_path.parent.rglob("*.html"))
    for page_path in html_files:
        page_text = page_path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"<img[^>]+src=[\"'][^\"']+\.pdf", page_text, re.I):
            findings.append(
                Finding(
                    "error",
                    "html-pdf-figure",
                    _relative(page_path),
                    "HTML contains a PDF image reference; use SVG/PNG for browser figures",
                )
            )
        for pattern in (
            r"class=[\"'][^\"']*quarto-unresolved-ref",
            r"\?(?:sec|fig|tbl|eq)-[A-Za-z0-9_-]+",
            r"@(?:sec|chap|fig|tbl|eq)-[A-Za-z0-9_-]+",
            r"\?\?\?",
        ):
            if re.search(pattern, page_text):
                findings.append(
                    Finding(
                        "error",
                        "html-unresolved-reference",
                        _relative(page_path),
                        "HTML contains an unresolved reference marker; use Quarto-native labels and @refs",
                    )
                )
                break
    return findings


def normalize_html_hub_links(html_root: Path = BUILD_DIR) -> int:
    """Restore canonical root links that Quarto rewrites inside the book."""
    pattern = re.compile(r'href="[^"]*"(?=\s+data-arch2-href="(?P<href>/[^"]+)")')
    changed = 0
    for page_path in sorted(html_root.rglob("*.html")):
        text = page_path.read_text(encoding="utf-8")
        normalized, count = pattern.subn(
            lambda match: f'href="{match.group("href")}"', text
        )
        if count:
            page_path.write_text(normalized, encoding="utf-8")
            changed += count
    return changed


def _epub_visible_text(payload: bytes) -> str:
    """Extract XHTML text while excluding literal examples and executable content."""
    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        return ""

    chunks: list[str] = []
    excluded = {"code", "kbd", "pre", "samp", "script", "style"}

    def visit(element: ET.Element, suppressed: bool = False) -> None:
        local_name = element.tag.rsplit("}", 1)[-1]
        current_suppressed = suppressed or local_name in excluded
        if not current_suppressed and element.text:
            chunks.append(element.text)
        for child in element:
            visit(child, current_suppressed)
            if not current_suppressed and child.tail:
                chunks.append(child.tail)

    visit(root)
    return "\n".join(chunks)


def epub_findings(epub_path: Path = EPUB_PATH) -> list[Finding]:
    if not epub_path.exists():
        return [
            Finding(
                "error",
                "missing-epub",
                _relative(epub_path),
                "rendered EPUB does not exist",
            )
        ]

    findings: list[Finding] = []
    try:
        with zipfile.ZipFile(epub_path) as epub:
            names = epub.namelist()
            opf_names = [name for name in names if name.endswith(".opf")]
            if not opf_names:
                findings.append(
                    Finding(
                        "error",
                        "epub-metadata",
                        _relative(epub_path),
                        "EPUB contains no OPF package metadata",
                    )
                )
            else:
                try:
                    opf_root = ET.fromstring(epub.read(opf_names[0]))
                except ET.ParseError:
                    findings.append(
                        Finding(
                            "error",
                            "epub-metadata",
                            f"{_relative(epub_path)}:{opf_names[0]}",
                            "EPUB package metadata is not well-formed XML",
                        )
                    )
                else:
                    languages = [
                        (element.text or "").strip()
                        for element in opf_root.findall(
                            ".//{http://purl.org/dc/elements/1.1/}language"
                        )
                    ]
                    invalid_languages = {
                        value for value in languages if value.upper() in {"C", "POSIX"}
                    }
                    if not languages or any(not value for value in languages):
                        findings.append(
                            Finding(
                                "error",
                                "epub-language",
                                f"{_relative(epub_path)}:{opf_names[0]}",
                                "EPUB package metadata must declare a publication language",
                            )
                        )
                    elif invalid_languages:
                        findings.append(
                            Finding(
                                "error",
                                "epub-language",
                                f"{_relative(epub_path)}:{opf_names[0]}",
                                "EPUB publication language cannot use a process locale such as C or POSIX",
                            )
                        )
            html_names = [name for name in names if name.endswith((".html", ".xhtml"))]
            if not html_names:
                findings.append(
                    Finding(
                        "error",
                        "epub-content",
                        _relative(epub_path),
                        "EPUB contains no HTML/XHTML content files",
                    )
                )
                return findings

            content_payloads = [
                epub.read(name) for name in html_names if not name.endswith("nav.xhtml")
            ]
            combined = "\n".join(
                payload.decode("utf-8", errors="replace")
                for payload in content_payloads
            )
            visible_text = "\n".join(
                _epub_visible_text(payload) for payload in content_payloads
            )
    except zipfile.BadZipFile:
        return [
            Finding(
                "error",
                "invalid-epub",
                _relative(epub_path),
                "EPUB is not a readable zip package",
            )
        ]

    if "callout-learning-objectives" not in combined:
        findings.append(
            Finding(
                "warning",
                "epub-custom-callouts",
                _relative(epub_path),
                "EPUB is missing Arch2 custom callout markup",
            )
        )

    if re.search(r"(?m)^\s*:::\s*(?:\{[^}\n]*\})?\s*$", visible_text):
        findings.append(
            Finding(
                "error",
                "epub-literal-fenced-div",
                _relative(epub_path),
                "EPUB contains a literal fenced-Div marker; check source block spacing",
            )
        )

    for pattern in (
        r"class=[\"'][^\"']*quarto-unresolved-ref",
        r"\?(?:sec|fig|tbl|eq)-[A-Za-z0-9_-]+",
        r"@(?:sec|chap|fig|tbl|eq)-[A-Za-z0-9_-]+",
        r"\?\?\?",
    ):
        if re.search(pattern, combined):
            findings.append(
                Finding(
                    "error",
                    "epub-unresolved-reference",
                    _relative(epub_path),
                    "EPUB contains an unresolved reference marker; use Quarto-native labels and @refs",
                )
            )
            break

    return findings


def normalize_epub_xhtml(epub_path: Path = EPUB_PATH) -> int:
    """Normalize Quarto XHTML attributes that are invalid in EPUB."""
    original_mode = epub_path.stat().st_mode & 0o777
    xhtml_namespace = "http://www.w3.org/1999/xhtml"
    ET.register_namespace("", xhtml_namespace)
    ET.register_namespace("epub", "http://www.idpf.org/2007/ops")
    ET.register_namespace("m", "http://www.w3.org/1998/Math/MathML")
    ET.register_namespace("svg", "http://www.w3.org/2000/svg")

    with zipfile.ZipFile(epub_path, "r") as source:
        entries = [(info, source.read(info.filename)) for info in source.infolist()]

    changed = 0
    normalized: list[tuple[zipfile.ZipInfo, bytes]] = []
    for info, payload in entries:
        if not info.filename.endswith((".html", ".xhtml")):
            normalized.append((info, payload))
            continue

        root = ET.fromstring(payload)
        document_changed = False
        for element in root.iter():
            for attribute in list(element.attrib):
                if not attribute.startswith("data-") or attribute == attribute.lower():
                    continue
                normalized_attribute = attribute.lower()
                if normalized_attribute not in element.attrib:
                    element.attrib[normalized_attribute] = element.attrib[attribute]
                del element.attrib[attribute]
                changed += 1
                document_changed = True
        for wrapper in root.iter():
            if wrapper.tag.endswith("}div") or wrapper.tag == "div":
                if "alt" in wrapper.attrib:
                    del wrapper.attrib["alt"]
                    changed += 1
                    document_changed = True
        if document_changed:
            payload = ET.tostring(
                root,
                encoding="utf-8",
                xml_declaration=True,
                short_empty_elements=True,
            )
        normalized.append((info, payload))

    if not changed:
        return 0

    with tempfile.NamedTemporaryFile(
        prefix=f".{epub_path.name}.", suffix=".tmp", dir=epub_path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
    try:
        with zipfile.ZipFile(temporary, "w") as target:
            for info, payload in normalized:
                target.writestr(info, payload)
        temporary.chmod(original_mode)
        temporary.replace(epub_path)
    finally:
        temporary.unlink(missing_ok=True)
    return changed


def _has_required_epubcheck_version(output: str) -> bool:
    expected = f"EPUBCheck v{EPUBCHECK_VERSION}"
    return expected in {line.strip() for line in output.splitlines()}


def run_epubcheck(epub_path: Path = EPUB_PATH) -> None:
    executable = shutil.which("epubcheck")
    if executable is None:
        _exit_on_findings(
            [
                Finding(
                    "error",
                    "missing-epubcheck",
                    _relative(epub_path),
                    f"EPUBCheck {EPUBCHECK_VERSION} is required for EPUB publication",
                )
            ],
            title="EPUBCheck",
        )
        return

    version_proc = _run([executable, "--version"], capture=True)
    version_output = (version_proc.stdout or "") + (version_proc.stderr or "")
    if version_proc.returncode != 0 or not _has_required_epubcheck_version(
        version_output
    ):
        _exit_on_findings(
            [
                Finding(
                    "error",
                    "epubcheck-version",
                    executable,
                    f"EPUBCheck {EPUBCHECK_VERSION} is required; found {version_output.strip() or 'an unreadable version'}",
                )
            ],
            title="EPUBCheck",
        )

    proc = _run([executable, str(epub_path), "--failonwarnings"], capture=True)
    transcript = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    log_path = _record_log("epubcheck", transcript)
    if proc.returncode != 0:
        console.print(f"[red]failed[/red] EPUBCheck transcript: {_relative(log_path)}")
        console.print(transcript[-6000:])
        raise typer.Exit(proc.returncode)
    console.print(f"[green]passed[/green] EPUBCheck {EPUBCHECK_VERSION}")
    console.print(f"[dim]transcript: {_relative(log_path)}[/dim]")


def strip_namespace(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_float(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    match = re.match(r"\s*(-?[0-9.]+)", value)
    return float(match.group(1)) if match else default


def parse_translate(transform: str | None) -> tuple[float, float]:
    if not transform:
        return (0.0, 0.0)
    total_x = 0.0
    total_y = 0.0
    for match in TRANSLATE_RE.finditer(transform):
        total_x += float(match.group("x"))
        total_y += float(match.group("y") or 0.0)
    return (total_x, total_y)


def svg_text_content(element: Any) -> str:
    return " ".join("".join(element.itertext()).split())


def parse_class_font_sizes(root: Any) -> dict[str, float]:
    css = "\n".join(
        element.text or ""
        for element in root.iter()
        if strip_namespace(element.tag) == "style"
    )
    sizes: dict[str, float] = {}
    for match in STYLE_RE.finditer(css):
        size_match = FONT_SIZE_RE.search(match.group("body"))
        if size_match:
            sizes[match.group("class")] = float(size_match.group("size"))
    return sizes


def font_size_for(element: Any, class_sizes: dict[str, float]) -> float:
    style = element.attrib.get("style", "")
    inline = FONT_SIZE_RE.search(style)
    if inline:
        return float(inline.group("size"))

    for class_name in element.attrib.get("class", "").split():
        if class_name in class_sizes:
            return class_sizes[class_name]
    return DEFAULT_FONT_SIZE


def svg_character_width(ch: str, font_size: float) -> float:
    if ch.isspace():
        return font_size * 0.30
    if ch in ".,:;'/|!":
        return font_size * 0.24
    if ch in "-+()[]{}":
        return font_size * 0.34
    if ch in "MW@%":
        return font_size * 0.78
    if ch.isupper():
        return font_size * 0.60
    return font_size * 0.52


def walk_with_translate(
    element: Any,
    inherited: tuple[float, float] = (0.0, 0.0),
) -> Iterable[tuple[Any, tuple[float, float]]]:
    own = parse_translate(element.attrib.get("transform"))
    current = (inherited[0] + own[0], inherited[1] + own[1])
    yield element, current
    for child in element:
        yield from walk_with_translate(child, current)


def collect_svg_shapes(root: Any) -> list[SvgShape]:
    shapes: list[SvgShape] = []
    for element, offset in walk_with_translate(root):
        tag = strip_namespace(element.tag)
        ox, oy = offset
        if tag == "rect":
            raw_width = element.attrib.get("width")
            raw_height = element.attrib.get("height")
            if "%" in (raw_width or "") or "%" in (raw_height or ""):
                continue
            width = parse_float(raw_width)
            height = parse_float(raw_height)
            if width <= 0 or height <= 0:
                continue
            shapes.append(
                SvgShape(
                    "rect",
                    parse_float(element.attrib.get("x")) + ox,
                    parse_float(element.attrib.get("y")) + oy,
                    width,
                    height,
                )
            )
        elif tag == "circle":
            radius = parse_float(element.attrib.get("r"))
            if radius <= 0:
                continue
            cx = parse_float(element.attrib.get("cx")) + ox
            cy = parse_float(element.attrib.get("cy")) + oy
            shapes.append(
                SvgShape("circle", cx - radius, cy - radius, radius * 2.0, radius * 2.0)
            )
    return shapes


def collect_svg_labels(root: Any, class_sizes: dict[str, float]) -> list[SvgTextLabel]:
    labels: list[SvgTextLabel] = []
    for element, offset in walk_with_translate(root):
        if strip_namespace(element.tag) != "text":
            continue
        text = svg_text_content(element)
        if not text:
            continue
        labels.append(
            SvgTextLabel(
                x=parse_float(element.attrib.get("x")) + offset[0],
                y=parse_float(element.attrib.get("y")) + offset[1],
                text=text,
                font_size=font_size_for(element, class_sizes),
                anchor=element.attrib.get("text-anchor", "start"),
            )
        )
    return labels


def parse_viewbox(root: Any) -> tuple[float, float, float, float] | None:
    raw = root.attrib.get("viewBox")
    if not raw:
        width = parse_float(root.attrib.get("width"))
        height = parse_float(root.attrib.get("height"))
        if width <= 0 or height <= 0:
            return None
        return (0.0, 0.0, width, height)
    parts = raw.replace(",", " ").split()
    if len(parts) != 4:
        return None
    try:
        x, y, width, height = (float(part) for part in parts)
    except ValueError:
        return None
    if width <= 0 or height <= 0:
        return None
    return (x, y, width, height)


def collect_svg_bounds(root: Any, class_sizes: dict[str, float]) -> list[SvgBounds]:
    bounds: list[SvgBounds] = []
    for element, offset in walk_with_translate(root):
        tag = strip_namespace(element.tag)
        ox, oy = offset
        if tag == "rect":
            raw_width = element.attrib.get("width")
            raw_height = element.attrib.get("height")
            if "%" in (raw_width or "") or "%" in (raw_height or ""):
                continue
            width = parse_float(raw_width)
            height = parse_float(raw_height)
            if width <= 0 or height <= 0:
                continue
            x = parse_float(element.attrib.get("x")) + ox
            y = parse_float(element.attrib.get("y")) + oy
            bounds.append(SvgBounds("rect", x, y, x + width, y + height))
        elif tag == "circle":
            radius = parse_float(element.attrib.get("r"))
            if radius <= 0:
                continue
            cx = parse_float(element.attrib.get("cx")) + ox
            cy = parse_float(element.attrib.get("cy")) + oy
            bounds.append(
                SvgBounds("circle", cx - radius, cy - radius, cx + radius, cy + radius)
            )
        elif tag == "ellipse":
            rx = parse_float(element.attrib.get("rx"))
            ry = parse_float(element.attrib.get("ry"))
            if rx <= 0 or ry <= 0:
                continue
            cx = parse_float(element.attrib.get("cx")) + ox
            cy = parse_float(element.attrib.get("cy")) + oy
            bounds.append(SvgBounds("ellipse", cx - rx, cy - ry, cx + rx, cy + ry))
        elif tag == "line":
            x1 = parse_float(element.attrib.get("x1")) + ox
            y1 = parse_float(element.attrib.get("y1")) + oy
            x2 = parse_float(element.attrib.get("x2")) + ox
            y2 = parse_float(element.attrib.get("y2")) + oy
            bounds.append(
                SvgBounds("line", min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
            )
        elif tag == "text":
            text = svg_text_content(element)
            if not text:
                continue
            label = SvgTextLabel(
                x=parse_float(element.attrib.get("x")) + ox,
                y=parse_float(element.attrib.get("y")) + oy,
                text=text,
                font_size=font_size_for(element, class_sizes),
                anchor=element.attrib.get("text-anchor", "start"),
            )
            bounds.append(
                SvgBounds(
                    "text", label.left, label.top, label.right, label.bottom, label.text
                )
            )
    return bounds


def svg_viewbox_findings(
    path: Path, root: Any, class_sizes: dict[str, float]
) -> list[Finding]:
    viewbox = parse_viewbox(root)
    if viewbox is None:
        return []
    x, y, width, height = viewbox
    left = x
    top = y
    right = x + width
    bottom = y + height
    tolerance = 1.5

    findings: list[Finding] = []
    for bounds in collect_svg_bounds(root, class_sizes):
        if (
            bounds.left < left - tolerance
            or bounds.right > right + tolerance
            or bounds.top < top - tolerance
            or bounds.bottom > bottom + tolerance
        ):
            label = f" '{bounds.label}'" if bounds.label else ""
            findings.append(
                Finding(
                    "error",
                    "svg-viewbox",
                    _relative(path),
                    f"{bounds.kind}{label} extends outside the declared viewBox",
                )
            )
    return findings


def svg_shape_margin(label: SvgTextLabel, shape: SvgShape) -> float:
    left_margin = label.left - shape.x
    right_margin = shape.x + shape.width - label.right
    top_margin = label.top - shape.y
    bottom_margin = shape.y + shape.height - label.bottom
    return min(left_margin, right_margin, top_margin, bottom_margin)


def containing_svg_shape(
    label: SvgTextLabel, shapes: list[SvgShape]
) -> SvgShape | None:
    candidates = [shape for shape in shapes if shape.contains_point(label.x, label.y)]
    if not candidates:
        return None

    rects = [shape for shape in candidates if shape.kind == "rect"]
    if rects:
        return min(rects, key=lambda shape: shape.area)

    return max(candidates, key=lambda shape: svg_shape_margin(label, shape))


def svg_label_findings(
    path: Path, label: SvgTextLabel, shape: SvgShape
) -> list[Finding]:
    findings: list[Finding] = []
    location = _relative(path)
    if shape.kind == "rect":
        padding = max(MIN_RECT_PADDING, label.font_size * 0.25)
        available_width = shape.width - 2.0 * padding
        available_height = shape.height - 2.0 * padding

        if label.estimated_width > available_width:
            findings.append(
                Finding(
                    "error",
                    "svg-text-fit",
                    location,
                    f"text '{label.text}' estimates {label.estimated_width:.1f}px wide inside a {shape.width:.1f}px rectangle",
                )
            )
        if label.font_size * 1.1 > available_height:
            findings.append(
                Finding(
                    "error",
                    "svg-text-fit",
                    location,
                    f"text '{label.text}' has too little vertical room",
                )
            )
        if (
            label.left < shape.x + padding
            or label.right > shape.x + shape.width - padding
        ):
            findings.append(
                Finding(
                    "error",
                    "svg-text-fit",
                    location,
                    f"text '{label.text}' is too close to or crosses a rectangle boundary",
                )
            )
        if (
            label.top < shape.y + padding
            or label.bottom > shape.y + shape.height - padding
        ):
            findings.append(
                Finding(
                    "error",
                    "svg-text-fit",
                    location,
                    f"text '{label.text}' is too close to or crosses a rectangle top/bottom boundary",
                )
            )
    else:
        padding = max(MIN_CIRCLE_PADDING, label.font_size * 0.45)
        margin = svg_shape_margin(label, shape)
        if margin < padding:
            findings.append(
                Finding(
                    "error",
                    "svg-text-fit",
                    location,
                    f"text '{label.text}' has only {margin:.1f}px margin inside a circle",
                )
            )
    return findings


def normalize_svg_font_stack(value: str) -> tuple[str, ...]:
    return tuple(part.strip().strip("'\"") for part in value.split(",") if part.strip())


def svg_font_family_findings(path: Path) -> list[Finding]:
    text = path.read_text(encoding="utf-8", errors="replace")
    stacks = {
        normalize_svg_font_stack(match.group("family"))
        for match in SVG_FONT_FAMILY_RE.finditer(text)
    }
    location = _relative(path)
    if not stacks:
        return [
            Finding(
                "error",
                "svg-font-family",
                location,
                "content figure must declare the shared Arial, Helvetica, "
                "sans-serif font stack",
            )
        ]

    unexpected = sorted(stack for stack in stacks if stack != CONTENT_SVG_FONT_STACK)
    if not unexpected:
        return []
    rendered = "; ".join(", ".join(stack) for stack in unexpected)
    return [
        Finding(
            "error",
            "svg-font-family",
            location,
            f"content figure uses a noncanonical font stack: {rendered}",
        )
    ]


def is_content_svg(path: Path) -> bool:
    resolved = path.resolve()
    return any(resolved.is_relative_to(root.resolve()) for root in CONTENT_ROOTS)


def svg_text_findings_for_file(path: Path) -> list[Finding]:
    from defusedxml import ElementTree as safe_et
    from defusedxml.common import DefusedXmlException

    try:
        root = safe_et.parse(path).getroot()
    except (safe_et.ParseError, DefusedXmlException) as exc:
        return [
            Finding(
                "error", "svg-parse", _relative(path), f"could not parse SVG: {exc}"
            )
        ]

    class_sizes = parse_class_font_sizes(root)
    shapes = collect_svg_shapes(root)
    labels = collect_svg_labels(root, class_sizes)

    findings: list[Finding] = []
    if is_content_svg(path):
        findings.extend(svg_font_family_findings(path))
    findings.extend(svg_viewbox_findings(path, root, class_sizes))
    for label in labels:
        shape = containing_svg_shape(label, shapes)
        if shape is None:
            continue
        findings.extend(svg_label_findings(path, label, shape))
    return findings


def svg_paths(inputs: list[Path] | None = None) -> list[Path]:
    candidates = inputs or list(CONTENT_ROOTS)
    paths: list[Path] = []
    for raw_path in candidates:
        path = raw_path if raw_path.is_absolute() else ROOT / raw_path
        if path.is_dir():
            paths.extend(sorted(path.rglob("*.svg")))
        elif path.suffix.lower() == ".svg":
            paths.append(path)
    return sorted(set(path.resolve() for path in paths))


def svg_text_findings(inputs: list[Path] | None = None) -> list[Finding]:
    findings: list[Finding] = []
    for path in svg_paths(inputs):
        findings.extend(svg_text_findings_for_file(path))
    return findings


def latex_logs() -> list[Path]:
    pdf_mtime = PDF_PATH.stat().st_mtime if PDF_PATH.exists() else 0.0
    logs = [
        path
        for path in sorted(BOOK_DIR.glob("*.log"))
        if not pdf_mtime or path.stat().st_mtime >= pdf_mtime - 300
    ]
    latest = LOG_DIR / "render-latest.log"
    if latest.exists():
        logs.append(latest)
    return logs


def generated_tex() -> Path | None:
    candidates = sorted(
        [*BOOK_DIR.glob("*.tex"), *BUILD_DIR.glob("*.tex")],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def scan_latex_text(text: str, *, location: str) -> list[Finding]:
    findings: list[Finding] = []
    for match in OVERFULL_HBOX_RE.finditer(text):
        findings.append(
            Finding(
                "error",
                "overfull-hbox",
                location,
                f"{match.group('pts')}pt too wide {match.group('context').strip()}",
            )
        )
    for match in OVERFULL_VBOX_RE.finditer(text):
        findings.append(
            Finding(
                "error",
                "overfull-vbox",
                location,
                f"{match.group('pts')}pt too high {match.group('context').strip()}",
            )
        )
    for match in UNDERFULL_RE.finditer(text):
        findings.append(
            Finding(
                "warning",
                "underfull-box",
                location,
                match.group("context").strip() or "underfull TeX box",
            )
        )
    for match in UNRESOLVED_REF_RE.finditer(text):
        findings.append(
            Finding(
                "error",
                "undefined-reference",
                location,
                f"undefined reference or citation: {match.group(1)}",
            )
        )
    return findings


def scan_latex_logs() -> list[Finding]:
    findings: list[Finding] = []
    for log_path in latex_logs():
        findings.extend(
            scan_latex_text(
                log_path.read_text(encoding="utf-8", errors="replace"),
                location=_relative(log_path),
            )
        )
    return findings


def _is_page_number(text: str) -> bool:
    return bool(re.fullmatch(r"\d+|[ivxlcdm]+", text.strip(), re.I))


def _compact_text(text: str, *, limit: int | None = None) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if limit is not None and len(compact) > limit:
        return compact[: limit - 1].rstrip() + "..."
    return compact


def _extract_pdf_words(page) -> list[dict]:
    try:
        return (
            page.extract_words(x_tolerance=1, y_tolerance=3, keep_blank_chars=False)
            or []
        )
    except TypeError:
        return page.extract_words() or []


def _word_lines(words: list[dict], *, y_tolerance: float = 4.0) -> list[str]:
    lines: list[tuple[float, list[dict]]] = []
    for word in sorted(
        words,
        key=lambda item: (
            float(item.get("top", 0.0)),
            float(item.get("x0", 0.0)),
        ),
    ):
        top = float(word.get("top", 0.0))
        if lines and abs(top - lines[-1][0]) <= y_tolerance:
            lines[-1][1].append(word)
            continue
        lines.append((top, [word]))
    return [
        _compact_text(
            " ".join(
                str(word.get("text", ""))
                for word in sorted(
                    line_words, key=lambda item: float(item.get("x0", 0.0))
                )
            )
        )
        for _, line_words in lines
    ]


def _pdf_caption_snippets(text: str) -> tuple[str, ...]:
    snippets: list[str] = []
    for line in text.splitlines():
        compact = _compact_text(line, limit=220)
        if PDF_CAPTION_LINE_RE.search(compact):
            snippets.append(compact)
    return tuple(snippets)


def _pdf_caption_snippets_from_lines(lines: list[str]) -> tuple[str, ...]:
    snippets: list[str] = []
    for index, line in enumerate(lines):
        if not PDF_CAPTION_LINE_RE.search(line):
            continue
        snippet = line
        for continuation in lines[index + 1 : index + 3]:
            if PDF_CAPTION_LINE_RE.search(continuation):
                break
            snippet = f"{snippet} {continuation}"
            if len(snippet) >= 220:
                break
        snippets.append(_compact_text(snippet, limit=220))
    return tuple(snippets)


def _caption_kinds(captions: tuple[str, ...]) -> set[str]:
    kinds: set[str] = set()
    for caption in captions:
        match = PDF_CAPTION_LINE_RE.search(caption)
        if match:
            kinds.add(match.group("kind").lower())
    return kinds


def _layout_source_hints(profile: LayoutPageProfile) -> tuple[str, ...]:
    hints: list[str] = [f"inspect rendered PDF page {profile.page}"]
    for caption in profile.captions[:2]:
        hints.append(f"search source for caption: {caption}")
    if not profile.captions and profile.text_excerpt:
        hints.append(f"search source for excerpt: {profile.text_excerpt}")
    return tuple(hints)


def _in_layout_main_column(item: dict, *, page_width: float) -> bool:
    x0 = float(item.get("x0", 0.0) or 0.0)
    x1 = float(item.get("x1", x0) or x0)
    midpoint = (min(x0, x1) + max(x0, x1)) / 2.0
    return (
        page_width * LAYOUT_MAIN_COLUMN_LEFT_RATIO
        <= midpoint
        <= page_width * LAYOUT_MAIN_COLUMN_RIGHT_RATIO
    )


def _is_meaningful_layout_object(
    obj: dict,
    *,
    collection_name: str,
    page_width: float,
    header_cutoff: float,
    footer_cutoff: float,
) -> bool:
    if not _in_layout_main_column(obj, page_width=page_width):
        return False
    x0 = float(obj.get("x0", 0.0) or 0.0)
    x1 = float(obj.get("x1", x0) or x0)
    top = float(obj.get("top", 0.0) or 0.0)
    bottom = float(obj.get("bottom", top) or top)
    width = abs(x1 - x0)
    height = abs(bottom - top)
    if top < header_cutoff or top > footer_cutoff:
        return False
    if collection_name == "images":
        return (
            width >= LAYOUT_MIN_VECTOR_DIMENSION
            and height >= LAYOUT_MIN_VECTOR_DIMENSION
        )
    return (
        width >= LAYOUT_MIN_VECTOR_DIMENSION
        and height >= LAYOUT_MIN_VECTOR_DIMENSION
        and width * height >= LAYOUT_MIN_VECTOR_AREA
    )


def _layout_profile_content_geometry(
    page,
    body_words: list[dict],
    *,
    page_width: float,
    header_cutoff: float,
    footer_cutoff: float,
) -> tuple[list[dict], list[tuple[str, dict]], float | None, float | None]:
    main_words = [
        word
        for word in body_words
        if _in_layout_main_column(word, page_width=page_width)
    ]
    objects: list[tuple[str, dict]] = []
    for collection_name in ("images", "rects", "curves"):
        for obj in getattr(page, collection_name, []) or []:
            if _is_meaningful_layout_object(
                obj,
                collection_name=collection_name,
                page_width=page_width,
                header_cutoff=header_cutoff,
                footer_cutoff=footer_cutoff,
            ):
                objects.append((collection_name, obj))

    content_tops = [float(word.get("top", 0.0)) for word in main_words]
    content_bottoms = [float(word.get("bottom", 0.0)) for word in main_words]
    for _, obj in objects:
        content_tops.append(max(header_cutoff, float(obj.get("top", 0.0) or 0.0)))
        content_bottoms.append(min(footer_cutoff, float(obj.get("bottom", 0.0) or 0.0)))
    return (
        main_words,
        objects,
        min(content_tops) if content_tops else None,
        max(content_bottoms) if content_bottoms else None,
    )


def _pdf_major_unit_kind(lines: list[str]) -> str | None:
    for line in lines[:LAYOUT_MAJOR_UNIT_OPENING_LINES]:
        match = PDF_MAJOR_UNIT_LINE_RE.fullmatch(_compact_text(line))
        if match:
            return match.group("kind").lower()
    return None


def _starts_major_unit(profile: LayoutPageProfile) -> bool:
    return (
        bool(profile.major_unit_kind)
        or profile.starts_chapter
        or bool(re.match(r"^(Appendix\b|References\b)", profile.text_excerpt, re.I))
    )


def _profile_occupancy(profile: LayoutPageProfile) -> float | None:
    if profile.content_occupancy is not None:
        return profile.content_occupancy
    if profile.content_top is None or profile.content_bottom is None:
        return None
    usable_height = profile.usable_bottom - LAYOUT_USABLE_TOP
    if usable_height <= 0:
        return None
    content_height = max(
        0.0,
        min(profile.content_bottom, profile.usable_bottom)
        - max(profile.content_top, LAYOUT_USABLE_TOP),
    )
    return min(1.0, content_height / usable_height)


def _is_layout_interstitial(profile: LayoutPageProfile) -> bool:
    occupancy = _profile_occupancy(profile)
    return (
        not _starts_major_unit(profile)
        and not (profile.has_figure or profile.has_table)
        and profile.word_count <= 12
        and (occupancy is None or occupancy <= 0.08)
    )


def layout_page_profiles(pdf_path: Path) -> list[LayoutPageProfile]:
    try:
        import pdfplumber
    except ImportError:
        return []
    if not pdf_path.exists():
        return []

    profiles: list[LayoutPageProfile] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            width = float(page.width)
            height = float(page.height)
            header_cutoff = LAYOUT_USABLE_TOP
            footer_cutoff = height - LAYOUT_FOOTER_BAND
            usable_bottom = footer_cutoff
            text = page.extract_text() or ""

            words = _extract_pdf_words(page)
            body_words = []
            for word in words:
                word_text = str(word.get("text", "")).strip()
                if not word_text or _is_page_number(word_text):
                    continue
                top = float(word.get("top", 0.0))
                bottom = float(word.get("bottom", 0.0))
                if top < header_cutoff or bottom > footer_cutoff:
                    continue
                body_words.append(word)

            (
                main_words,
                profile_objects,
                content_top,
                content_bottom,
            ) = _layout_profile_content_geometry(
                page,
                body_words,
                page_width=width,
                header_cutoff=header_cutoff,
                footer_cutoff=footer_cutoff,
            )
            body_lines = _word_lines(main_words)
            captions = _pdf_caption_snippets_from_lines(body_lines)
            if not captions:
                captions = _pdf_caption_snippets(text)
            major_unit_kind = _pdf_major_unit_kind(body_lines)
            starts_chapter = major_unit_kind == "chapter" or bool(
                PDF_CHAPTER_START_RE.search(text.strip())
            )

            bottom_whitespace = (
                max(0.0, usable_bottom - content_bottom)
                if content_bottom is not None
                else None
            )
            usable_height = usable_bottom - header_cutoff
            content_occupancy = (
                max(
                    0.0,
                    min(content_bottom, usable_bottom)
                    - max(content_top, header_cutoff),
                )
                / usable_height
                if content_top is not None
                and content_bottom is not None
                and usable_height > 0
                else None
            )
            caption_kinds = _caption_kinds(captions)
            has_table = "table" in caption_kinds
            has_figure = (
                any(
                    collection_name == "images"
                    for collection_name, _ in profile_objects
                )
                or "figure" in caption_kinds
            )
            profiles.append(
                LayoutPageProfile(
                    page=page_index,
                    width=round(width, 1),
                    height=round(height, 1),
                    word_count=len(main_words),
                    content_top=(
                        round(content_top, 1) if content_top is not None else None
                    ),
                    content_bottom=(
                        round(content_bottom, 1) if content_bottom is not None else None
                    ),
                    usable_bottom=round(usable_bottom, 1),
                    bottom_whitespace=(
                        round(bottom_whitespace, 1)
                        if bottom_whitespace is not None
                        else None
                    ),
                    has_figure=has_figure,
                    has_table=has_table,
                    captions=captions,
                    starts_chapter=starts_chapter,
                    text_excerpt=_compact_text(" ".join(body_lines), limit=220)
                    or _compact_text(text, limit=220),
                    content_occupancy=(
                        round(min(1.0, content_occupancy), 3)
                        if content_occupancy is not None
                        else None
                    ),
                    major_unit_kind=major_unit_kind,
                )
            )
    return profiles


def scan_pdf_geometry(
    pdf_path: Path,
    *,
    bottom_clearance: float = 72.0,
    bleed_tolerance: float = 1.0,
    max_findings: int = 80,
) -> list[Finding]:
    try:
        import pdfplumber
    except ImportError:
        return [
            Finding(
                "error",
                "missing-pdfplumber",
                "python",
                "pdfplumber is required for PDF geometry scanning",
            )
        ]

    if not pdf_path.exists():
        return [
            Finding(
                "error",
                "missing-pdf",
                _relative(pdf_path),
                "rendered PDF does not exist",
            )
        ]

    findings: list[Finding] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            width = float(page.width)
            height = float(page.height)
            page_loc = f"{_relative(pdf_path)}:page {page_index}"

            for char in page.chars:
                text = str(char.get("text", "")).strip()
                if not text:
                    continue
                x0 = float(char.get("x0", 0.0))
                x1 = float(char.get("x1", 0.0))
                top = float(char.get("top", 0.0))
                bottom = float(char.get("bottom", 0.0))
                if (
                    x0 < -bleed_tolerance
                    or x1 > width + bleed_tolerance
                    or top < -bleed_tolerance
                    or bottom > height + bleed_tolerance
                ):
                    findings.append(
                        Finding(
                            "error",
                            "physical-bleed",
                            page_loc,
                            f"text extends outside page bounds: {text!r}",
                        )
                    )
                    break

            try:
                words = (
                    page.extract_words(
                        x_tolerance=1, y_tolerance=3, keep_blank_chars=False
                    )
                    or []
                )
            except TypeError:
                words = page.extract_words() or []
            crowded_words = [
                word
                for word in words
                if float(word.get("bottom", 0.0)) > height - bottom_clearance
                and not _is_page_number(str(word.get("text", "")))
            ]
            if crowded_words:
                snippet = " ".join(
                    str(word.get("text", "")) for word in crowded_words[:8]
                )
                findings.append(
                    Finding(
                        "warning",
                        "bottom-crowding",
                        page_loc,
                        f"content sits within {bottom_clearance:g}pt of page bottom: {snippet}",
                    )
                )

            for collection_name in ("images", "rects", "curves", "lines"):
                for obj in getattr(page, collection_name, []) or []:
                    x0 = float(obj.get("x0", 0.0) or 0.0)
                    x1 = float(obj.get("x1", 0.0) or 0.0)
                    top = float(obj.get("top", 0.0) or 0.0)
                    bottom = float(obj.get("bottom", 0.0) or 0.0)
                    if (
                        x0 < -bleed_tolerance
                        or x1 > width + bleed_tolerance
                        or top < -bleed_tolerance
                        or bottom > height + bleed_tolerance
                    ):
                        findings.append(
                            Finding(
                                "error",
                                "physical-bleed",
                                page_loc,
                                f"{collection_name[:-1]} object extends outside page bounds",
                            )
                        )
                        break
                    if (
                        bottom > height - bottom_clearance
                        and collection_name != "lines"
                    ):
                        findings.append(
                            Finding(
                                "warning",
                                "bottom-crowding",
                                page_loc,
                                f"{collection_name[:-1]} object sits within {bottom_clearance:g}pt of page bottom",
                            )
                        )
                        break

            if len(findings) >= max_findings:
                findings.append(
                    Finding(
                        "warning",
                        "truncated-report",
                        _relative(pdf_path),
                        f"stopped after {max_findings} findings",
                    )
                )
                return findings

    return findings


def footnote_overflow_findings(
    pdf_path: Path,
    *,
    bottom_band: float = 42.0,
    max_findings: int = 80,
) -> list[Finding]:
    """Flag margin footnotes/sidenotes that run off (or into) the page bottom.

    With ``reference-location: margin`` the Springer build stacks footnotes as
    sidenotes in the outer margin. When a page carries several long notes the
    stack runs past the bottom of the text block and the last note clips off the
    page (see the Bayesian-optimization note on page 52). The generic
    ``physical-bleed`` check catches the clipped glyph but cannot say it is a
    footnote; this check isolates small-font text in the *outer margin* (so the
    running footer and body prose are excluded) and reports the offending note's
    text, which is the actionable signal for shortening or rebalancing it.
    """
    try:
        import pdfplumber
    except ImportError:
        return [
            Finding(
                "error",
                "missing-pdfplumber",
                "python",
                "pdfplumber is required for PDF geometry scanning",
            )
        ]
    if not pdf_path.exists():
        return [
            Finding(
                "error",
                "missing-pdf",
                _relative(pdf_path),
                "rendered PDF does not exist",
            )
        ]

    from collections import Counter

    findings: list[Finding] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            height = float(page.height)
            chars = [c for c in page.chars if str(c.get("text", "")).strip()]
            if not chars:
                continue
            # Modal glyph size is the body text; notes/sidenotes set smaller.
            sizes = Counter(round(float(c.get("size", 0.0)), 1) for c in chars)
            body_size = sizes.most_common(1)[0][0]
            if body_size <= 0:
                continue
            body_chars = [
                c for c in chars if round(float(c.get("size", 0.0)), 1) == body_size
            ]
            if not body_chars:
                continue
            block_x0 = min(float(c.get("x0", 0.0)) for c in body_chars)
            block_x1 = max(float(c.get("x1", 0.0)) for c in body_chars)

            # Margin text: noticeably smaller than body AND outside the text block.
            margin_chars = [
                c
                for c in chars
                if round(float(c.get("size", 0.0)), 1) <= body_size * 0.9
                and (
                    float(c.get("x1", 0.0)) < block_x0 - 2.0
                    or float(c.get("x0", 0.0)) > block_x1 + 2.0
                )
            ]
            overflow = [
                c
                for c in margin_chars
                if float(c.get("bottom", 0.0)) > height - bottom_band
            ]
            if not overflow:
                continue

            lowest = max(float(c.get("bottom", 0.0)) for c in overflow)
            line = [
                c for c in overflow if abs(float(c.get("bottom", 0.0)) - lowest) < 6.0
            ]
            snippet = "".join(
                c.get("text", "")
                for c in sorted(line, key=lambda c: float(c.get("x0", 0.0)))
            )[:70].strip()
            off_page = lowest > height + 1.0
            findings.append(
                Finding(
                    "error" if off_page else "warning",
                    "footnote-overflow",
                    f"{_relative(pdf_path)}:page {page_index}",
                    (
                        f"margin footnote/sidenote {'clips off the page bottom' if off_page else 'reaches the page bottom'}; "
                        f"shorten or rebalance the note: {snippet!r}"
                    ),
                )
            )
            if len(findings) >= max_findings:
                break
    return findings


def sparse_page_findings(
    pdf_path: Path,
    *,
    sparse_clearance: float = DEFAULT_SPARSE_CLEARANCE,
    max_content_occupancy: float = DEFAULT_MAX_CONTENT_OCCUPANCY,
    min_body_words: int = DEFAULT_SPARSE_MIN_BODY_WORDS,
    profiles: list[LayoutPageProfile] | None = None,
) -> list[Finding]:
    """Find unexpectedly underfilled body pages in a rendered PDF.

    The detector requires both a large absolute gap and low vertical occupancy,
    then exempts front matter, major-unit openings and endings, blank pages,
    reference pages, and the document's final page. Remaining findings block
    the rendered-manuscript gate until the spread is rebalanced or exempted.
    """
    page_profiles = profiles if profiles is not None else layout_page_profiles(pdf_path)
    if not page_profiles:
        return []

    first_body_page = min(
        (
            profile.page
            for profile in page_profiles
            if profile.starts_chapter
            or profile.major_unit_kind in {"chapter", "appendix", "part"}
        ),
        default=page_profiles[0].page,
    )
    reference_pages: set[int] = set()
    in_references = False
    for profile in page_profiles:
        if profile.major_unit_kind == "references":
            in_references = True
        elif profile.major_unit_kind in {"chapter", "appendix", "part"}:
            in_references = False
        if in_references:
            reference_pages.add(profile.page)

    findings: list[Finding] = []
    for index, profile in enumerate(page_profiles):
        next_index = index + 1
        while next_index < len(page_profiles) and _is_layout_interstitial(
            page_profiles[next_index]
        ):
            next_index += 1
        next_profile = (
            page_profiles[next_index] if next_index < len(page_profiles) else None
        )
        if profile.page < first_body_page:
            continue
        if _starts_major_unit(profile) or profile.page in reference_pages:
            continue
        if next_profile is None or _starts_major_unit(next_profile):
            continue
        if profile.bottom_whitespace is None or profile.content_bottom is None:
            continue

        occupancy = _profile_occupancy(profile)
        if occupancy is None:
            continue
        if profile.bottom_whitespace < sparse_clearance:
            continue
        if occupancy > max_content_occupancy:
            continue
        next_has_float = next_profile.has_figure or next_profile.has_table
        if profile.word_count < min_body_words and not (
            profile.has_figure or profile.has_table or next_has_float
        ):
            continue

        if next_has_float:
            code = "float-induced-whitespace"
            next_content = (
                next_profile.captions[0]
                if next_profile.captions
                else "figure or table content"
            )
            context = (
                f"; page {next_profile.page} contains "
                f"{_compact_text(next_content, limit=120)}"
            )
        elif profile.has_figure or profile.has_table:
            code = "sparse-float-page"
            context = ""
        else:
            code = "large-bottom-whitespace"
            context = ""

        findings.append(
            Finding(
                "error",
                code,
                f"{_relative(pdf_path)}:page {profile.page}",
                (
                    f"content ends {profile.bottom_whitespace:g}pt above the usable "
                    f"page bottom ({occupancy:.0%} vertical content occupancy)"
                    f"{context}; inspect this spread for an avoidable page break"
                ),
            )
        )
    return findings


def layout_findings(
    pdf_path: Path,
    *,
    bottom_clearance: float = 72.0,
    include_sparse_pages: bool = True,
) -> list[Finding]:
    findings = scan_latex_logs()
    findings.extend(scan_pdf_geometry(pdf_path, bottom_clearance=bottom_clearance))
    findings.extend(footnote_overflow_findings(pdf_path))
    if include_sparse_pages:
        findings.extend(sparse_page_findings(pdf_path))
    return findings


def _repair_item_for_finding(
    index: int,
    finding: Finding,
    *,
    profile: LayoutPageProfile | None = None,
) -> LayoutRepairItem:
    guidance = {
        "overfull-hbox": (
            "A line, caption, table cell, or margin note exceeds the TeX measure.",
            "Find the local source near the cited log context, then shorten the phrase, split the table/caption, resize the figure, or introduce a better break point.",
        ),
        "overfull-vbox": (
            "A vertical box is taller than the available page area.",
            "Inspect the nearby float, callout, table, or footnote stack; reduce height, split it, or move neighboring prose so the page builder has a legal break.",
        ),
        "underfull-box": (
            "TeX had to stretch or loosen a line/page more than usual.",
            "Check the rendered page before editing. If the looseness is visible, rebalance the paragraph, move a nearby sentence, or adjust the float placement.",
        ),
        "physical-bleed": (
            "Rendered content extends outside the physical PDF page bounds.",
            "Treat this as a blocking layout bug. Resize or split the offending content so no glyph or object crosses the page box.",
        ),
        "bottom-crowding": (
            "Content is too close to the footer or page bottom.",
            "Move a sentence, shrink or split the nearby object, or add a better page break so the bottom margin breathes.",
        ),
        "footnote-overflow": (
            "A margin footnote or sidenote stack is too deep for the page.",
            "Shorten the note, move the note trigger, split the note, or move adjacent prose so the sidenote stack stays within the page.",
        ),
        "undefined-reference": (
            "A rendered cross-reference or citation did not resolve.",
            "Fix the label, citation key, or source order before doing visual layout polish.",
        ),
        "float-induced-whitespace": (
            "A figure or table likely moved to the next page after this page's prose ended.",
            "Inspect the spread, then move explanatory prose or the float, reduce the float height, or keep the break only when it improves the reading sequence.",
        ),
        "sparse-float-page": (
            "A page containing a figure or table has substantial unused vertical space.",
            "Check whether the float can be resized, paired with its setup prose, or moved to avoid an isolated visual island.",
        ),
        "large-bottom-whitespace": (
            "The page builder ended a regular content page much earlier than the usable text block.",
            "Inspect nearby headings, callouts, footnotes, and floats, then rebalance a short paragraph or nearby object if the spread reads unevenly.",
        ),
    }
    likely_cause, suggested_action = guidance.get(
        finding.code,
        (
            "The raw layout scan found a rendered artifact issue.",
            "Inspect the rendered page and the nearby source before choosing a repair.",
        ),
    )
    return LayoutRepairItem(
        id=f"L{index:03d}",
        severity=finding.severity,
        code=finding.code,
        location=finding.location,
        evidence=finding.message,
        likely_cause=likely_cause,
        suggested_action=suggested_action,
        source_hints=(
            _layout_source_hints(profile)
            if profile is not None
            else (f"start from {finding.location}",)
        ),
    )


def layout_repair_items(
    pdf_path: Path,
    *,
    bottom_clearance: float = 72.0,
    sparse_clearance: float = DEFAULT_SPARSE_CLEARANCE,
    min_body_words: int = DEFAULT_SPARSE_MIN_BODY_WORDS,
    max_items: int = 80,
    profiles: list[LayoutPageProfile] | None = None,
) -> list[LayoutRepairItem]:
    page_profiles = profiles if profiles is not None else layout_page_profiles(pdf_path)
    profiles_by_page = {profile.page: profile for profile in page_profiles}
    findings = layout_findings(
        pdf_path,
        bottom_clearance=bottom_clearance,
        include_sparse_pages=False,
    )
    findings.extend(
        sparse_page_findings(
            pdf_path,
            sparse_clearance=sparse_clearance,
            min_body_words=min_body_words,
            profiles=page_profiles,
        )
    )

    items: list[LayoutRepairItem] = []
    for finding in findings:
        page_match = re.search(r":page\s+(\d+)$", finding.location)
        profile = profiles_by_page.get(int(page_match.group(1))) if page_match else None
        items.append(
            _repair_item_for_finding(
                len(items) + 1,
                finding,
                profile=profile,
            )
        )
        if len(items) >= max_items:
            break

    return items


def layout_repair_packet(
    pdf_path: Path,
    *,
    bottom_clearance: float = 72.0,
    sparse_clearance: float = DEFAULT_SPARSE_CLEARANCE,
    min_body_words: int = DEFAULT_SPARSE_MIN_BODY_WORDS,
    max_items: int = 80,
) -> dict:
    from collections import Counter

    profiles = layout_page_profiles(pdf_path)
    items = layout_repair_items(
        pdf_path,
        bottom_clearance=bottom_clearance,
        sparse_clearance=sparse_clearance,
        min_body_words=min_body_words,
        max_items=max_items,
        profiles=profiles,
    )
    affected_pages: set[int] = set()
    for item in items:
        for match in re.finditer(r"page\s+(\d+)", f"{item.location} {item.evidence}"):
            page = int(match.group(1))
            affected_pages.add(page)
            affected_pages.add(page - 1)
            affected_pages.add(page + 1)
    affected_pages = {page for page in affected_pages if page > 0}

    severity_counts = Counter(item.severity for item in items)
    code_counts = Counter(item.code for item in items)
    return {
        "pdf": _relative(pdf_path),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "thresholds": {
            "bottom_clearance_pt": bottom_clearance,
            "sparse_clearance_pt": sparse_clearance,
            "max_content_occupancy": DEFAULT_MAX_CONTENT_OCCUPANCY,
            "min_body_words": min_body_words,
        },
        "summary": {
            "item_count": len(items),
            "by_severity": dict(sorted(severity_counts.items())),
            "by_code": dict(sorted(code_counts.items())),
        },
        "recommended_commands": {
            "hard_scan": "./arch2 layout scan --json tmp/pdfs/layout-scan.json",
            "repair_packet": "./arch2 layout doctor --markdown tmp/pdfs/layout-repair-packet.md --json tmp/pdfs/layout-repair-packet.json",
            "figure_contact_sheet": "./arch2 layout contact-sheet figures",
            "table_contact_sheet": "./arch2 layout contact-sheet tables",
        },
        "items": [asdict(item) for item in items],
        "page_profiles": [
            asdict(profile) for profile in profiles if profile.page in affected_pages
        ],
    }


def render_layout_repair_markdown(packet: dict) -> str:
    lines = [
        "# Arch2 layout repair packet",
        "",
        f"PDF: `{packet['pdf']}`",
        f"Generated: `{packet['generated_at']}`",
        "",
        "## Summary",
        "",
        f"- Items: {packet['summary']['item_count']}",
        f"- By severity: `{packet['summary']['by_severity']}`",
        f"- By code: `{packet['summary']['by_code']}`",
        "",
        "## Workflow",
        "",
        "1. Start with `error` items; they are structural layout failures.",
        "2. Review `warning` items visually in the PDF spread before editing.",
        "3. Intentional title, opening, closing, blank, and reference pages are excluded from sparse-page warnings.",
        "4. After edits, rebuild the PDF and rerun `arch2 layout scan` and `arch2 layout doctor`.",
        "",
        "## Findings",
        "",
    ]
    if not packet["items"]:
        lines.append("No layout repair candidates were found.")
    for item in packet["items"]:
        lines.extend(
            [
                f"### {item['id']} {item['code']} ({item['severity']})",
                "",
                f"- Location: `{item['location']}`",
                f"- Evidence: {item['evidence']}",
                f"- Likely cause: {item['likely_cause']}",
                f"- Suggested action: {item['suggested_action']}",
            ]
        )
        if item["source_hints"]:
            lines.append("- Source hints:")
            for hint in item["source_hints"]:
                lines.append(f"  - {hint}")
        lines.append("")

    if packet["page_profiles"]:
        lines.extend(["## Page Profiles", ""])
        for profile in packet["page_profiles"]:
            lines.append(
                f"- Page {profile['page']}: words={profile['word_count']}, "
                f"bottom_whitespace={profile['bottom_whitespace']}, "
                f"content_occupancy={profile['content_occupancy']}, "
                f"figure={profile['has_figure']}, table={profile['has_table']}"
            )
            if profile["captions"]:
                for caption in profile["captions"][:2]:
                    lines.append(f"  - {caption}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _emit_layout_repair_items(items: list[LayoutRepairItem]) -> None:
    if not items:
        console.print("[green]passed[/green] layout doctor")
        return
    table = Table(title="layout doctor", show_lines=False)
    table.add_column("ID", style="bold")
    table.add_column("Severity")
    table.add_column("Code")
    table.add_column("Location")
    table.add_column("Action")
    for item in items:
        style = "red" if item.severity == "error" else "yellow"
        if item.severity == "info":
            style = "cyan"
        table.add_row(
            item.id,
            f"[{style}]{item.severity}[/{style}]",
            item.code,
            item.location,
            _compact_text(item.suggested_action, limit=92),
        )
    console.print(table)


def run_layout_check(
    *, bottom_clearance: float = 72.0, fail_on_warning: bool = False
) -> None:
    findings = layout_findings(PDF_PATH, bottom_clearance=bottom_clearance)
    _exit_on_findings(findings, title="layout audit", fail_on_warning=fail_on_warning)


def run_refs_check() -> None:
    _exit_on_findings(manuscript_integrity_findings(), title="references")


def run_manifest_check() -> None:
    _exit_on_findings(manifest_findings(), title="book manifest")


def run_figures_check(pdf: Path = PDF_PATH) -> None:
    _exit_on_findings(pdf_figure_findings(pdf), title="PDF figures")


def footnote_in_table_findings(paths: list[Path] | None = None) -> list[Finding]:
    """Flag footnote markers inside Markdown table cells.

    A footnote whose marker sits in a table cell breaks the Springer PDF build:
    with ``reference-location: margin`` Quarto turns the footnote into a margin
    sidenote, and inside a longtable cell the sidenote text leaks inline with an
    unbalanced brace (LaTeX "Extra }, or forgotten \\endgroup"). Footnotes must
    live in body prose, never in a table cell. Catches both inline ``^[...]`` and
    reference ``[^id]`` markers; a ``[^id]:`` definition at column 0 is not a
    table row and is correctly ignored.
    """
    targets = paths if paths is not None else content_qmd_files()
    marker = re.compile(r"\^\[|\[\^[A-Za-z0-9_-]+\]")
    findings: list[Finding] = []
    for path in targets:
        in_fence = False
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            stripped = line.lstrip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = not in_fence
                continue
            if in_fence or not stripped.startswith("|"):
                continue
            if marker.search(line):
                findings.append(
                    Finding(
                        "error",
                        "footnote-in-table",
                        f"{_relative(path)}:{lineno}",
                        "footnote marker inside a table cell breaks the margin PDF build; move the note to body prose",
                    )
                )
    return findings


def footnote_source_findings(paths: list[Path] | None = None) -> list[Finding]:
    """Flag footnote source forms that violate the manuscript contract.

    Reference-style notes keep definitions inspectable beside the paragraph
    that uses them. The source convention also gives every note a book-unique
    identifier and a visible defined-term head. This check is deliberately
    mechanical. It does not decide whether material belongs in a footnote.
    """
    targets = paths if paths is not None else content_qmd_files()
    inline_marker = re.compile(r"\^\[")
    definition = re.compile(r"^\[\^([A-Za-z0-9_-]+)\]:\s*(.*)$")
    identifier = re.compile(r"^fn-[a-z0-9]+(?:-[a-z0-9]+)*-c\d{2}(?:-\d+)?$")
    term_head = re.compile(r"^\*\*[^*]+\*\*:(?:\s+\S.*)?$")
    findings: list[Finding] = []
    for path in targets:
        in_fence = False
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            stripped = line.lstrip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            if inline_marker.search(line):
                findings.append(
                    Finding(
                        "error",
                        "inline-footnote",
                        f"{_relative(path)}:{lineno}",
                        "inline Pandoc footnote found; use a named reference-style footnote beside the paragraph",
                    )
                )
            match = definition.match(stripped)
            if not match:
                continue
            note_id, body = match.groups()
            if not identifier.fullmatch(note_id):
                findings.append(
                    Finding(
                        "error",
                        "footnote-id",
                        f"{_relative(path)}:{lineno}",
                        f'footnote id "{note_id}" must use fn-<topic>-cNN with an optional numeric suffix',
                    )
                )
            if not term_head.match(body):
                findings.append(
                    Finding(
                        "error",
                        "footnote-term-head",
                        f"{_relative(path)}:{lineno}",
                        "footnote definition must begin with a bold term or origin label followed by a colon outside the bold span",
                    )
                )
    return findings


STRIPPED_VOCABULARY: dict[str, str] = {
    "flywheel": "compounding loop",
    "guardrail": "constraint",
    "ladder": "fidelity spectrum",
    "ledger": "record",
    "moat": "advantage",
    "onboarding": "setup",
    "rung": "tier",
    "scaffold": "harness",
    "scaffolding": "harness",
}

# "By spring, ..." is a date, not the banned construction. Kept deliberately
# short: every other -ing word after a sentence-initial "By" is a gerund.
BY_GERUND_EXEMPT = frozenset({"spring", "morning", "evening"})


def find_markdown_figures(text: str) -> list[dict[str, Any]]:
    """Parse markdown figures handling balanced brackets inside captions."""
    results: list[dict[str, Any]] = []
    i = 0
    while i < len(text):
        if text[i : i + 2] == "![":
            start_pos = i
            depth = 1
            j = i + 2
            while j < len(text) and depth > 0:
                if text[j] == "[":
                    depth += 1
                elif text[j] == "]":
                    depth -= 1
                j += 1
            if depth == 0:
                caption = text[i + 2 : j - 1]
                rest = text[j:]
                m = re.match(
                    r"^\((?P<path>[^)]+)\)\{#(?P<id>fig-[a-z0-9-]+)(?P<attrs>[^}]*)\}",
                    rest,
                )
                if m:
                    results.append(
                        {
                            "caption": caption.strip(),
                            "path": m.group("path"),
                            "id": m.group("id"),
                            "attrs": m.group("attrs"),
                            "start": start_pos,
                        }
                    )
                    i = j + m.end()
                    continue
        i += 1
    return results


def caption_findings(paths: list[Path] | None = None) -> list[Finding]:
    """Validate figure captions against the 3-Layer Pedagogical standard.

    Project caption contract:
    1. Every figure caption must open with a bold headline (e.g. ![**Headline.** ...]).
    2. Captions must be concise (<= 750 characters / ~90 words max) to fit page budget.
    """
    targets = paths if paths is not None else content_qmd_files()
    findings: list[Finding] = []
    for path in targets:
        content = path.read_text(encoding="utf-8")
        figs = find_markdown_figures(content)
        for f in figs:
            caption = f["caption"]
            fig_id = f["id"]
            start_pos = f["start"]
            lineno = content[:start_pos].count("\n") + 1

            if not (caption.startswith("**") and ("**" in caption[2:])):
                findings.append(
                    Finding(
                        "error",
                        "caption-bold-headline",
                        f"{_relative(path)}:{lineno}",
                        f"figure caption '{fig_id}' must begin with a bold headline lead '![**Headline.** ...]'",
                    )
                )

            if len(caption) > 750:
                findings.append(
                    Finding(
                        "error",
                        "caption-length",
                        f"{_relative(path)}:{lineno}",
                        f"figure caption '{fig_id}' is too long ({len(caption)} chars > 750 chars max); streamline to 3-5 lines",
                    )
                )
    return findings


def prose_style_findings(paths: list[Path] | None = None) -> list[Finding]:
    """Flag mechanical prose-style regressions that a manual sweep cannot hold.

    Five classes in the project prose and emphasis contract are prone to silent
    reintroduction whenever a passage is rewritten.

    Stripped vocabulary. An earlier sweep replaced a set of process metaphors
    with plainer terms, but nothing enforced the result, so survivors persisted
    in the front matter and appendix A until a register audit found them. Figure
    anchors and image paths are stripped before matching, because an anchor name
    is not reader-visible prose; rename those deliberately, not under this check.

    Em-dashes. Banned in running prose. The only sanctioned use is an epigraph or
    signature attribution, which always opens its line with the dash.

    "By <gerund>" sentence openers. Banned since the rule file was written, swept
    by hand more than once, and back in three chapters by 2026-07-26. The shape
    buries the actor in a participial phrase and reads as machine-generated, which
    is the same defect the active-voice rule exists to catch. Only the gerund form
    is matched, so "By contrast" and "By 2030" stay legal.

    Non-breaking SI units. A number and its unit must not be split across a line,
    which in this Quarto source means ``3\\ W`` rather than ``3 W``. A 2026-07-27
    sweep found the manuscript almost evenly divided, 26 compliant against 85 not,
    because nothing checked it and the defect is invisible until the PDF breaks a
    line in the wrong place. Fenced blocks are already skipped, which is what keeps
    the check off matplotlib labels and Python f-strings where a plain space is
    correct. Image definitions and ``fig-alt`` text are skipped too, since alt text
    is read aloud rather than typeset.

    Inline term bold. Bold marks a structural slot, never a term. ``emphasis.md``
    carried the opposite carve-out until 2026-07-27, letting a load-bearing term
    take one bold at its canonical definition; a sweep found 39 such spans against
    808 structural ones and retired the rule. Only mid-line bold is flagged. Table
    rows, list and numbered-list labels, footnote term heads, caption leads,
    blockquote labels, and callout fences are skipped, and so is a line-initial
    bold, because whether that opener is a legal callout label or the
    dressed-up-list anti-pattern depends on the enclosing block rather than the
    line.

    ``gate`` and ``cadence`` are deliberately absent. Both carry heavy literal
    architecture senses (gate delay, clock gating, gate-level netlist), so a
    pattern broad enough to catch the process metaphor would bury real findings
    in noise. Those two stay a reading judgment.
    """
    targets = paths if paths is not None else content_qmd_files()
    anchors = re.compile(
        r"\]\([^)]*\)"  # image and link targets, which carry asset filenames
        r"|[@{#]*(?:fig|tbl|sec|lst|eq)-[a-z0-9-]+"  # cross-reference anchors
        r"|\S+\.(?:svg|png|pdf|jpe?g)"  # bare asset paths
    )
    vocabulary = re.compile(
        r"\b(" + "|".join(sorted(STRIPPED_VOCABULARY)) + r")s?\b", re.IGNORECASE
    )
    # Sentence-initial, allowing for the list bullets, blockquote marks, and bold
    # callout labels that can sit in front of the first word of a sentence.
    # An adverb may sit between "By" and the gerund ("By systematically stepping
    # through..."), which evaded the original pattern and hid a live instance.
    by_gerund = re.compile(r"(?:^|[.!?]\s+|\*\*\s+)By\s+(?:\w+ly\s+)?(\w+ing)\b")
    line_opener = re.compile(r"^(?:[-*+>]\s+|\d+\.\s+|\*\*)+")
    raw_tilde = re.compile(r"(?<![a-zA-Z0-9_\`\$\~])~\s*(\d+[\w\.\,]*)")
    spatial_float = re.compile(
        r"\b(?:figure|table|listing|chart|diagram)\s+(?:below|above)\b"
        r"|\b(?:below|above)\s+in\s+@(fig|tbl|lst)\b"
        r"|\b(?:as\s+shown\s+below)\b",
        re.IGNORECASE,
    )
    bare_si_unit = re.compile(
        r"(?<![\\\w])(\d+(?:\.\d+)?) "
        r"(W|nm|mm|GHz|MHz|Hz|kB|MB|GB|TB|ms|ns|ps|pJ|nJ|mW|mV|V|\u00b0C)\b"
    )
    # Every line shape that owns a legal bold, plus the line-initial label the
    # regex cannot adjudicate. Anything left is running prose.
    structural_bold = re.compile(
        r"^(?:\|"  # table row or header
        r"|:\s+\*\*"  # table caption lead
        r"|!\[\*\*"  # figure caption lead
        r"|\[\^[\w-]+\]:\s*\*\*"  # footnote term head
        r"|[-*+]\s+\*\*"  # list label
        r"|\d+\.\s+\*\*"  # numbered-list label
        r"|>"  # blockquote label
        r"|:::"  # callout fence and its title attribute
        r"|\*\*)"  # line-initial label
    )
    inline_bold = re.compile(r"\*\*(.+?)\*\*")
    findings: list[Finding] = []
    for path in targets:
        in_fence = False
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            stripped = line.lstrip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            prose = anchors.sub("", line)
            for match in vocabulary.finditer(prose):
                replacement = STRIPPED_VOCABULARY[match.group(1).lower()]
                findings.append(
                    Finding(
                        "error",
                        "stripped-vocabulary",
                        f"{_relative(path)}:{lineno}",
                        f'"{match.group(0)}" was stripped from the manuscript '
                        f'vocabulary; use "{replacement}" or plainer wording',
                    )
                )
            # Pandoc renders "---" as an em-dash, so the literal form is a prose
            # em-dash too and was previously unchecked. Table separator rows and
            # YAML/thematic-break lines are excluded before the test, since those
            # legitimately consist of dashes.
            dash_prose = prose
            if dash_prose.lstrip().startswith("|") or dash_prose.strip(" -:|") == "":
                dash_prose = ""
            has_em_dash = "\u2014" in dash_prose or re.search(
                r"(?<!-)---(?!-)", dash_prose
            )
            if has_em_dash and not prose.lstrip("> ").startswith("\u2014"):
                findings.append(
                    Finding(
                        "error",
                        "em-dash",
                        f"{_relative(path)}:{lineno}",
                        "em-dash in running prose; recast with a period, comma, "
                        "or colon (attribution lines are the only exemption)",
                    )
                )
            if re.search(r"\b(et\s+al\.)", prose, re.IGNORECASE):
                findings.append(
                    Finding(
                        "error",
                        "explicit-et-al",
                        f"{_relative(path)}:{lineno}",
                        'explicit "et al." in running prose is non-standard; use proper Quarto citations [@key] or @key instead of typing "et al."',
                    )
                )
            tilde_match = raw_tilde.search(prose)
            if (
                tilde_match
                and "http" not in prose
                and "git" not in prose
                and not stripped.startswith("#")
            ):
                findings.append(
                    Finding(
                        "error",
                        "raw-tilde-approximation",
                        f"{_relative(path)}:{lineno}",
                        f'raw tilde "{tilde_match.group(0)}" in running prose; use "about {tilde_match.group(1)}" or "$\\approx {tilde_match.group(1)}$" per CMOS',
                    )
                )
            spatial_match = spatial_float.search(prose)
            if spatial_match:
                findings.append(
                    Finding(
                        "error",
                        "spatial-float-reference",
                        f"{_relative(path)}:{lineno}",
                        f'deictic spatial float reference "{spatial_match.group(0)}" is non-standard; cite the float anchor directly (e.g. @fig-slug or @tbl-slug) without relative spatial adjectives (CMOS §§ 3.9, 3.83)',
                    )
                )
            for match in by_gerund.finditer(line_opener.sub("", prose)):
                if match.group(1).lower() in BY_GERUND_EXEMPT:
                    continue
                findings.append(
                    Finding(
                        "error",
                        "by-gerund-opener",
                        f"{_relative(path)}:{lineno}",
                        f'"By {match.group(1)}" opens a sentence; name the actor '
                        "and give it a verb instead of a participial phrase",
                    )
                )
            if not stripped.startswith("![") and "fig-alt" not in line:
                for match in bare_si_unit.finditer(prose):
                    findings.append(
                        Finding(
                            "error",
                            "si-unit-spacing",
                            f"{_relative(path)}:{lineno}",
                            f'"{match.group(0)}" splits a number from its unit; '
                            f"write {match.group(1)}\\ {match.group(2)} so the "
                            "PDF cannot break the line between them",
                            span=match.group(0),
                            replacement=f"{match.group(1)}\\ {match.group(2)}",
                            context=line.rstrip(),
                        )
                    )
            body = prose.strip()
            if not structural_bold.match(body):
                for match in inline_bold.finditer(body):
                    if match.start() == 0:
                        continue
                    findings.append(
                        Finding(
                            "error",
                            "inline-term-bold",
                            f"{_relative(path)}:{lineno}",
                            f'"{match.group(1)}" is bolded mid-sentence; bold '
                            "marks a structural label, so italicize a coinage "
                            "and leave ordinary vocabulary plain",
                        )
                    )
    return findings


GLOSSARY_DOMAINS: list[tuple[str, str, str, str]] = [
    (
        "hardware",
        "Hardware Architecture and Microarchitecture",
        "tbl-glossary-hardware",
        "sec-glossary-hardware",
    ),
    (
        "physical",
        "Physical Design, Manufacturing and Signoff",
        "tbl-glossary-physical",
        "sec-glossary-physical",
    ),
    (
        "compilers",
        "EDA, Compilers and Intermediate Representations",
        "tbl-glossary-compilers",
        "sec-glossary-compilers",
    ),
    (
        "verification",
        "Verification, Power and Standards",
        "tbl-glossary-verification",
        "sec-glossary-verification",
    ),
    (
        "interconnects",
        "Bus Protocols and Interconnect Interfaces",
        "tbl-glossary-interconnects",
        "sec-glossary-interconnects",
    ),
    ("ai", "AI, Modeling and Design Automation", "tbl-glossary-ai", "sec-glossary-ai"),
]

# Canonical technical abbreviations registry (CMOS Chapter 10 style contract)
# Format: (canonical_expansion, is_proper_noun, phonetic_article, domain_key, engineering_definition, regex_pattern, exempt_first_mention)
CMOS_ABBREVIATIONS: dict[str, tuple[str, bool, str, str, str, str, bool]] = {
    # Hardware Architecture & Microarchitecture
    "ABI": (
        "application binary interface",
        False,
        "an",
        "hardware",
        "The low-level binary interface between software programs and the operating system or hardware register state.",
        r"application binary interface",
        True,
    ),
    "AMX": (
        "Advanced Matrix Extensions",
        True,
        "an",
        "hardware",
        "A proprietary matrix acceleration instruction set extension developed by Intel for high-throughput tensor arithmetic.",
        r"Advanced\ Matrix\ Extensions",
        True,
    ),
    "ASIC": (
        "application-specific integrated circuit",
        False,
        "an",
        "hardware",
        "A custom-manufactured integrated circuit tailored to execute a specific computing workload with maximal energy and area efficiency.",
        r"application-specific integrated circuit",
        False,
    ),
    "CPU": (
        "central processing unit",
        False,
        "a",
        "hardware",
        "The primary general-purpose execution engine that sequences and executes instruction streams in a computer system.",
        r"central processing unit",
        True,
    ),
    "DDR": (
        "double data rate",
        False,
        "a",
        "hardware",
        "A memory bus protocol that transfers data on both the rising and falling edges of the clock cycle.",
        r"double\ data\ rate",
        True,
    ),
    "DMA": (
        "direct memory access",
        False,
        "a",
        "hardware",
        "A hardware feature allowing peripheral devices or accelerators to transfer data directly to and from main memory without processor intervention.",
        r"direct memory access",
        True,
    ),
    "DSA": (
        "domain-specific architecture",
        False,
        "a",
        "hardware",
        "A customized processor or compute engine engineered specifically to maximize execution efficiency for a targeted family of workloads.",
        r"domain[- ]specific architecture",
        False,
    ),
    "DVFS": (
        "dynamic voltage and frequency scaling",
        False,
        "a",
        "hardware",
        "A power management technique that dynamically adjusts operating voltage and clock frequency to balance performance against thermal dissipation.",
        r"dynamic\ voltage\ and\ frequency\ scaling",
        True,
    ),
    "FIFO": (
        "first-in, first-out",
        False,
        "a",
        "hardware",
        "A queue data structure or buffer hardware where the earliest stored data elements are retrieved first.",
        r"first-in,?\s+first-out",
        False,
    ),
    "FPS": (
        "frames per second",
        False,
        "an",
        "hardware",
        "A frame-rate unit for real-time rendering and perception pipelines, used to state a display or sensor deadline.",
        r"frames per second",
        False,
    ),
    "FPGA": (
        "field-programmable gate array",
        False,
        "an",
        "hardware",
        "A reconfigurable integrated circuit containing programmable logic blocks and routing channels configured post-fabrication.",
        r"field-programmable gate array",
        False,
    ),
    "GDDR5": (
        "Graphics Double Data Rate 5",
        True,
        "a",
        "hardware",
        "A high-bandwidth synchronous graphics random-access memory interface standard tailored for parallel data-intensive computing.",
        r"Graphics\ Double\ Data\ Rate\ 5",
        False,
    ),
    "GEMM": (
        "general matrix multiply",
        False,
        "a",
        "hardware",
        "The canonical linear algebra compute kernel forming the computational core of deep neural network acceleration.",
        r"general(?:ized)? matrix multiply|general matrix multiplication",
        False,
    ),
    "GPU": (
        "graphics processing unit",
        False,
        "a",
        "hardware",
        "A massively parallel processor optimized for high-throughput rasterization, linear algebra, and tensor operations.",
        r"graphics processing unit",
        True,
    ),
    "HBM": (
        "High Bandwidth Memory",
        True,
        "an",
        "hardware",
        "A high-speed 3D-stacked DRAM memory architecture providing massive memory bandwidth through wide through-silicon via (TSV) interconnects.",
        r"High\ Bandwidth\ Memory",
        False,
    ),
    "HDL": (
        "hardware description language",
        False,
        "an",
        "hardware",
        "A specialized formal language (such as SystemVerilog or VHDL) used to model the structure, behavior, and timing of digital electronic circuits.",
        r"hardware description language",
        True,
    ),
    "HPC": (
        "high-performance computing",
        False,
        "an",
        "hardware",
        "The practice of aggregating computing power to perform complex calculations at massively parallel scales.",
        r"high[- ]performance computing",
        True,
    ),
    "IPC": (
        "instructions per cycle",
        False,
        "an",
        "hardware",
        "A standard microarchitectural throughput metric measuring the average number of instructions executed per clock cycle.",
        r"instructions? per cycle",
        True,
    ),
    "ISA": (
        "instruction set architecture",
        False,
        "an",
        "hardware",
        "The abstract model and boundary defining instructions, registers, addressing modes, and memory consistency for a processor.",
        r"instruction[- ]set architecture",
        False,
    ),
    "KGD": (
        "known-good die",
        False,
        "a",
        "hardware",
        "A bare semiconductor die or chiplet that has been comprehensively tested and verified to meet functional and electrical specifications prior to multi-die package assembly.",
        r"known[- ]good[- ]die",
        True,
    ),
    "MSHR": (
        "miss status holding register",
        False,
        "an",
        "hardware",
        "A specialized hardware buffer in non-blocking caches tracking in-flight memory requests to allow cache lookups to continue during outstanding misses.",
        r"miss status holding register",
        True,
    ),
    "NoC": (
        "network-on-chip",
        False,
        "a",
        "hardware",
        "An on-die packet-switched communication subsystem connecting processing elements, caches, and memory controllers.",
        r"network[- ]on[- ]chip",
        False,
    ),
    "NPU": (
        "neural processing unit",
        False,
        "an",
        "hardware",
        "A specialized hardware accelerator designed specifically for accelerating tensor operations and deep neural network workloads.",
        r"neural processing unit",
        False,
    ),
    "NUMA": (
        "non-uniform memory access",
        False,
        "a",
        "hardware",
        "A multiprocessing system architecture where memory access latency varies depending on the physical proximity of the memory module to the requesting processor core.",
        r"non[- ]uniform memory access",
        True,
    ),
    "PE": (
        "processing element",
        False,
        "a",
        "hardware",
        "An individual arithmetic compute node or execution unit within a systolic array or parallel accelerator matrix.",
        r"processing[- ]element",
        True,
    ),
    "RISC": (
        "reduced instruction set computer",
        False,
        "a",
        "hardware",
        "A processor design philosophy based on simplified instructions that execute in a single cycle with load-store memory access.",
        r"reduced instruction set computer",
        True,
    ),
    "ROB": (
        "reorder buffer",
        False,
        "an",
        "hardware",
        "A circular FIFO buffer in out-of-order execution processors tracking in-flight speculative instructions to ensure in-order retirement and precise exceptions.",
        r"reorder buffer",
        False,
    ),
    "RTL": (
        "register-transfer level",
        False,
        "an",
        "hardware",
        "A digital design modeling abstraction describing synchronous signal and data transfers between hardware registers through combinational logic.",
        r"register-transfer[- ]level",
        False,
    ),
    "SoC": (
        "system-on-chip",
        False,
        "an",
        "hardware",
        "An integrated circuit consolidating an entire electronic or computing system onto a single semiconductor die.",
        r"system[- ]on[- ]chip",
        False,
    ),
    "SRAM": (
        "static random-access memory",
        False,
        "an",
        "hardware",
        "Fast, volatile semiconductor memory using bistable latching circuitry used for on-chip caches and scratchpads.",
        r"static random[- ]access memory",
        False,
    ),
    "TCM": (
        "tightly coupled memory",
        False,
        "a",
        "hardware",
        "Fast, deterministic on-chip static RAM mapped directly into the processor core's memory map with zero wait states.",
        r"tightly[- ]coupled memory",
        True,
    ),
    "TDP": (
        "thermal design power",
        False,
        "a",
        "hardware",
        "The maximum sustained power consumption that a cooling system is engineered to dissipate under worst-case operational workloads.",
        r"thermal design power",
        False,
    ),
    "TLB": (
        "translation lookaside buffer",
        False,
        "a",
        "hardware",
        "A dedicated hardware cache that stores recent virtual-to-physical address translations to accelerate memory access.",
        r"translation lookaside buffer",
        False,
    ),
    "TPU": (
        "Tensor Processing Unit",
        True,
        "a",
        "hardware",
        "A custom-developed application-specific integrated circuit engineered by Google specifically for accelerating machine learning training and inference workloads.",
        r"Tensor\ Processing\ Unit",
        False,
    ),
    "TSO": (
        "Total Store Order",
        True,
        "a",
        "hardware",
        "A hardware memory consistency model guaranteeing that store operations from a given thread appear in program order to all processors.",
        r"Total Store Order",
        True,
    ),
    "WSC": (
        "warehouse-scale computing",
        False,
        "a",
        "hardware",
        "Massive datacenter computing systems engineered as a unified, coordinated warehouse of compute nodes, storage, and networking.",
        r"warehouse[- ]scale computing",
        True,
    ),
    # Physical Design, Manufacturing & Signoff
    "BSPDN": (
        "backside power delivery network",
        False,
        "a",
        "physical",
        "A 3D semiconductor manufacturing technology that moves the power distribution metal grid to the backside of the silicon wafer to reduce IR-drop and routing congestion.",
        r"backside power delivery network",
        True,
    ),
    "DEF": (
        "Design Exchange Format",
        True,
        "a",
        "physical",
        "An open ASCII representation format for transferring physical layout, placement, and routing data between EDA physical design tools.",
        r"Design\ Exchange\ Format",
        True,
    ),
    "DRC": (
        "design rule check",
        False,
        "a",
        "physical",
        "Automated verification checking that a physical IC layout complies with the geometric constraints dictated by the semiconductor foundry's manufacturing process.",
        r"design rule check(?:ing)?",
        False,
    ),
    "ECO": (
        "engineering change order",
        False,
        "an",
        "physical",
        "A formal modification process applied late in the design or physical layout cycle to fix bugs or timing violations with minimal disruption to the netlist.",
        r"engineering\ change\ order",
        True,
    ),
    "ESD": (
        "electrostatic discharge",
        False,
        "an",
        "physical",
        "A sudden transient flow of electric current between charged bodies that requires on-chip protection structures to prevent physical dielectric breakdown.",
        r"electrostatic\ discharge",
        True,
    ),
    "EVM": (
        "emergency voltage mitigation",
        False,
        "an",
        "physical",
        "Dynamic hardware circuitry that rapidly detects supply voltage droop and temporarily throttles clock frequency or compute activity.",
        r"emergency voltage mitigation",
        True,
    ),
    "GAAFET": (
        "gate-all-around field-effect transistor",
        False,
        "a",
        "physical",
        "An advanced transistor architecture where the gate material surrounds all sides of vertically stacked nanosheet or nanowire conduction channels.",
        r"gate\-all\-around\ field\-effect\ transistor",
        True,
    ),
    "GDSII": (
        "Graphic Database System II",
        True,
        "a",
        "physical",
        "The industry-standard binary format for representing integrated circuit planar geometric layout artwork transferred to foundries for photomask fabrication.",
        r"Graphic\ Database\ System\ II",
        True,
    ),
    "IR-drop": (
        "voltage drop",
        False,
        "an",
        "physical",
        "The parasitic reduction in supply voltage across a power distribution network caused by current flow through resistive on-chip metal tracks.",
        r"(?:dynamic\s+|static\s+)?voltage[- ]drop|IR[- ]drop",
        True,
    ),
    "LEF": (
        "Library Exchange Format",
        True,
        "a",
        "physical",
        "An ASCII data format describing standard cell and macro pin geometries, routing layers, and obstruction boundaries for automated place-and-route tools.",
        r"Library\ Exchange\ Format",
        True,
    ),
    "LP": (
        "low-power",
        False,
        "an",
        "physical",
        "A foundry process node or silicon design methodology optimized for minimal active switching and subthreshold leakage power.",
        r"low\-power",
        True,
    ),
    "LVS": (
        "layout versus schematic",
        False,
        "an",
        "physical",
        "Verification confirming that drawn physical layout mask geometry matches the electrical connectivity of the synthesized netlist.",
        r"layout versus schematic",
        False,
    ),
    "MPW": (
        "multi-project wafer",
        False,
        "an",
        "physical",
        "A shared semiconductor fabrication shuttle run combining multiple distinct customer designs onto common reticle masks to amortize tooling charges.",
        r"multi[- ]project wafer",
        False,
    ),
    "MTBF": (
        "mean time between failures",
        False,
        "an",
        "physical",
        "The predicted elapsed time between inherent operational failures of a hardware system during normal operation.",
        r"mean time between failures",
        True,
    ),
    "NDA": (
        "nondisclosure agreement",
        False,
        "an",
        "physical",
        "A confidential legal contract protecting proprietary process design kits, standard cell libraries, and foundry yield data from unauthorized disclosure.",
        r"non[- ]disclosure agreement",
        True,
    ),
    "NRE": (
        "non-recurring engineering",
        False,
        "an",
        "physical",
        "The one-time, upfront engineering and mask tooling costs required to design, verify, and fabricate a new chip design before mass production.",
        r"non-recurring engineering",
        False,
    ),
    "PDK": (
        "process design kit",
        False,
        "a",
        "physical",
        "A collection of device models, design rules, standard-cell libraries, and verification decks supplied by a foundry for a specific fabrication process.",
        r"process design kit",
        False,
    ),
    "PDN": (
        "power delivery network",
        False,
        "a",
        "physical",
        "The on-die, package, and board-level metal interconnect network distributing supply voltage and ground across all active circuitry.",
        r"power delivery network",
        False,
    ),
    "PVT": (
        "process, voltage, and temperature",
        False,
        "a",
        "physical",
        "The three primary operational variation axes evaluated during static timing and power signoff across fast/slow silicon corners.",
        r"process,?\s+voltage,?\s+(?:and )?temperature",
        False,
    ),
    "SEU": (
        "single-event upset",
        False,
        "an",
        "physical",
        "A soft error or radiation-induced state change in a microelectronic device caused by ionizing radiation.",
        r"single[- ]event upset",
        True,
    ),
    "SIMD": (
        "single instruction, multiple data",
        False,
        "a",
        "hardware",
        "An execution model in which one instruction applies the same operation to many data elements in parallel across a wide vector register.",
        r"single instruction, multiple data",
        False,
    ),
    "SPMD": (
        "single-program, multiple-data",
        False,
        "a",
        "hardware",
        "A parallel programming model in which every thread runs the same program over a distinct slice of the data, indexed by its own thread identifier.",
        r"single\-program, multiple\-data",
        False,
    ),
    "SNM": (
        "static noise margin",
        False,
        "a",
        "physical",
        "A circuit figure of merit measuring the maximum DC noise voltage an SRAM bitcell can tolerate without inadvertently flipping its stored logic state.",
        r"static\ noise\ margin",
        True,
    ),
    "STA": (
        "static timing analysis",
        False,
        "an",
        "physical",
        "A deterministic verification method calculating circuit delays across all signal paths to verify setup and hold timing without dynamic simulation.",
        r"static timing analysis",
        False,
    ),
    "TCO": (
        "total cost of ownership",
        False,
        "a",
        "physical",
        "A financial estimate encompassing all direct and indirect capital expenditures and operational costs over the lifetime of a computing system.",
        r"total cost of ownership",
        True,
    ),
    "TNS": (
        "Total Negative Slack",
        True,
        "a",
        "physical",
        "The cumulative sum of all negative timing slacks across all violating endpoints in a design's static timing analysis graph.",
        r"Total\ Negative\ Slack",
        True,
    ),
    "VLSI": (
        "very-large-scale integration",
        False,
        "a",
        "physical",
        "The process of creating integrated circuits by combining millions or billions of MOS transistors onto a single silicon chip.",
        r"very[- ]large[- ]scale integration",
        True,
    ),
    # EDA, Compilers & Intermediate Representations
    "AIG": (
        "and-inverter graph",
        False,
        "an",
        "compilers",
        "A directed acyclic graph representation of a combinational logic circuit composed entirely of two-input AND nodes and logical inverters.",
        r"and[- ]inverter graph",
        True,
    ),
    "AST": (
        "abstract syntax tree",
        False,
        "an",
        "compilers",
        "A tree representation of the abstract syntactic structure of source code, capturing grammatical hierarchy without formatting tokens.",
        r"abstract syntax tree",
        False,
    ),
    "CAD": (
        "computer-aided design",
        False,
        "a",
        "compilers",
        "Software tools used by engineers to create, modify, analyze, and optimize physical hardware and circuit designs.",
        r"computer[- ]aided design",
        True,
    ),
    "CDFG": (
        "control-data flow graph",
        False,
        "a",
        "compilers",
        "A directed graph representation capturing both control branches and data dependencies within a computational block.",
        r"control[- ]data[- ]flow graph|control and data flow graph",
        False,
    ),
    "CIRCT": (
        "Circuit IR Compilers and Tools",
        True,
        "a",
        "compilers",
        "An open-source, LLVM/MLIR-based hardware compiler infrastructure providing dialect-driven lowering from high-level abstractions to synthesizable RTL.",
        r"Circuit (?:IR|Intermediate Representation) Compilers and Tools",
        False,
    ),
    "EDA": (
        "electronic design automation",
        False,
        "an",
        "compilers",
        "The category of software tools, algorithms, and workflows used to design, simulate, verify, and physically layout electronic systems and semiconductors.",
        r"electronic design automation",
        False,
    ),
    "FIRRTL": (
        "Flexible Intermediate Representation for RTL",
        True,
        "a",
        "compilers",
        "An intermediate representation designed for hardware digital design and compiler passes in the Chisel and CIRCT ecosystems.",
        r"Flexible\ Intermediate\ Representation\ for\ RTL",
        True,
    ),
    "FSDB": (
        "Fast Signal Database",
        True,
        "an",
        "compilers",
        "A high-performance proprietary binary waveform database format widely used for storing simulation and emulation signal traces.",
        r"Fast Signal Database",
        True,
    ),
    "HLS": (
        "high-level synthesis",
        False,
        "an",
        "compilers",
        "An automated compilation process transforming algorithmic descriptions into cycle-accurate register-transfer level hardware.",
        r"high-level synthesis",
        False,
    ),
    "IR": (
        "intermediate representation",
        False,
        "an",
        "compilers",
        "A standardized internal data structure or code format used by compilers to represent program or hardware semantics between passes.",
        r"intermediate representation",
        False,
    ),
    "JIT": (
        "just-in-time",
        False,
        "a",
        "compilers",
        "A compilation strategy where intermediate representations or bytecode are compiled into native machine code dynamically during program execution.",
        r"just\-in\-time",
        True,
    ),
    "MLIR": (
        "Multi-Level Intermediate Representation",
        True,
        "an",
        "compilers",
        "A modular compiler infrastructure within LLVM providing extensible dialects for domain-specific transformations and multi-stage hardware/software lowering.",
        r"Multi-Level Intermediate Representation",
        False,
    ),
    "TLM": (
        "transaction-level model",
        False,
        "a",
        "compilers",
        "A high-level abstraction for modeling digital systems where module communication is represented as abstract transactions rather than pin-level clock cycles.",
        r"transaction-level model(?:ing)?",
        False,
    ),
    "VCD": (
        "value change dump",
        False,
        "a",
        "compilers",
        "An ASCII-based industry standard waveform file format capturing signal value transitions during digital logic simulation.",
        r"value change dump",
        True,
    ),
    "VLA": (
        "vector-length-agnostic",
        False,
        "a",
        "compilers",
        "A processor architecture or compiler property where software binaries dynamically adapt to any hardware vector register length without recompilation.",
        r"vector\-length\-agnostic",
        True,
    ),
    # Verification, Power & Standards
    "BMC": (
        "bounded model checking",
        False,
        "a",
        "verification",
        "A formal verification technique unrolling sequential circuit transitions up to a fixed depth $k$ and querying a SAT/SMT solver to prove or disprove properties.",
        r"bounded model checking",
        False,
    ),
    "CDC": (
        "clock-domain crossing",
        False,
        "a",
        "verification",
        "An interface where a signal generated in one clock domain is sampled in an asynchronous or unrelated clock domain, risking metastability.",
        r"clock-domain crossing",
        False,
    ),
    "CEC": (
        "combinational equivalence checking",
        False,
        "a",
        "verification",
        "A formal verification technique using SAT/BDD methods to prove that two combinational logic circuits produce identical Boolean outputs for all inputs.",
        r"combinational equivalence checking",
        True,
    ),
    "CEGAR": (
        "counterexample-guided abstraction refinement",
        False,
        "a",
        "verification",
        "An iterative formal verification algorithm that starts with a coarse abstract model and progressively refines it using concrete counterexamples.",
        r"counterexample[- ]guided abstraction refinement",
        True,
    ),
    "FDIV": (
        "floating-point division",
        False,
        "an",
        "verification",
        "A hardware arithmetic division unit, notably associated with the historic 1994 Pentium microprocessor verification defect.",
        r"floating\-point\ division",
        True,
    ),
    "IEEE": (
        "Institute of Electrical and Electronics Engineers",
        True,
        "an",
        "verification",
        "The professional engineering organization responsible for international standards including SystemVerilog (1800), SystemC (1666), and UPF (1801).",
        r"Institute of Electrical and Electronics Engineers",
        False,
    ),
    "PMP": (
        "Physical Memory Protection",
        True,
        "a",
        "verification",
        "A RISC-V architectural standard providing hardware-enforced memory isolation and access permissions for physical memory regions.",
        r"Physical Memory Protection",
        True,
    ),
    "PRD": (
        "product requirements document",
        False,
        "a",
        "verification",
        "A formal engineering document defining the functionality, performance targets, physical constraints, and delivery requirements for a hardware system.",
        r"product requirements document",
        False,
    ),
    "PST": (
        "power state table",
        False,
        "a",
        "verification",
        "A tabular specification within IEEE 1801 UPF describing valid combinations of power domain voltage states and operating modes.",
        r"power state table",
        True,
    ),
    "RDC": (
        "reset domain crossing",
        False,
        "an",
        "verification",
        "An asynchronous structural boundary where a signal originates in one reset domain and enters logic reset by an unrelated reset controller.",
        r"reset[- ]domain crossing",
        True,
    ),
    "RVWMO": (
        "RISC-V Weak Memory Ordering",
        True,
        "an",
        "verification",
        "The canonical hardware memory consistency model for the RISC-V architecture defining legal ordering for multithreaded loads, stores, and fences.",
        r"RISC-V Weak Memory Ordering",
        False,
    ),
    "SEC": (
        "sequential equivalence checking",
        False,
        "an",
        "verification",
        "A formal verification method that mathematically proves two digital sequential circuits have identical input-output behavior over all cycles.",
        r"sequential equivalence checking",
        True,
    ),
    "SDC": (
        "Synopsys Design Constraints",
        True,
        "an",
        "verification",
        "The industry-standard Tcl-based timing and physical constraint format specifying clock frequencies, input/output delays, and multi-cycle false paths.",
        r"Synopsys Design Constraints",
        False,
    ),
    "SPEC": (
        "Standard Performance Evaluation Corporation",
        True,
        "a",
        "verification",
        "A non-profit organization establishing standardized benchmark suites to measure computing system performance.",
        r"Standard Performance Evaluation Corporation",
        True,
    ),
    "SVA": (
        "SystemVerilog Assertions",
        True,
        "an",
        "verification",
        "A declarative language extension within IEEE 1800 SystemVerilog used to specify temporal and Boolean properties for formal verification and dynamic simulation.",
        r"SystemVerilog Assertions",
        False,
    ),
    "UPF": (
        "Unified Power Format",
        True,
        "a",
        "verification",
        "The standard declarative language (IEEE 1801) specifying power intent, power domains, isolation cells, level shifters, and power switches across physical synthesis.",
        r"(?:IEEE 1801 )?Unified Power Format",
        False,
    ),
    # Bus Protocols & Interconnect Interfaces
    "AMBA": (
        "Arm Microcontroller Bus Architecture",
        True,
        "an",
        "interconnects",
        "An open-standard on-chip interconnect specification governing the connection and management of functional blocks in SoC designs.",
        r"(?:Arm|ARM) Microcontroller Bus Architecture",
        False,
    ),
    "AXI": (
        "Advanced eXtensible Interface",
        True,
        "an",
        "interconnects",
        "A high-performance, high-frequency, burst-based point-to-point interconnect protocol defined under the AMBA specification.",
        r"Advanced e?Xtensible Interface",
        False,
    ),
    "AXI5": (
        "Advanced eXtensible Interface 5",
        True,
        "an",
        "interconnects",
        "The fifth-generation AMBA on-chip interconnect protocol standard providing high-performance point-to-point interface handshakes and atomic transactions.",
        r"Advanced\ eXtensible\ Interface\ 5",
        True,
    ),
    "CXL": (
        "Compute Express Link",
        True,
        "a",
        "interconnects",
        "An open industry-standard cache-coherent interconnect protocol running over PCIe physical layers for high-speed CPU-to-device and CPU-to-memory expansion.",
        r"Compute Express Link",
        False,
    ),
    "UCIe": (
        "Universal Chiplet Interconnect Express",
        True,
        "a",
        "interconnects",
        "An open industry standard defining die-to-die physical, protocol, and software connectivity for 2.5D and 3D multi-chiplet integration.",
        r"Universal Chiplet Interconnect Express",
        False,
    ),
    # AI, Modeling & Design Automation
    "AWC": (
        "Autonomous Workflow Certified",
        True,
        "an",
        "ai",
        "A proposed artifact evaluation credential attesting to the computational reproducibility and explicit audit scope of an automated design workflow.",
        r"Autonomous Workflow Certified",
        False,
    ),
    "BO": (
        "Bayesian optimization",
        False,
        "a",
        "ai",
        "A sequential design strategy for global optimization of black-box objective functions using Gaussian process surrogate models and acquisition functions.",
        r"Bayesian optimization",
        True,
    ),
    "CNN": (
        "convolutional neural network",
        False,
        "a",
        "ai",
        "A class of deep neural networks using spatial convolution kernels, widely used in computer vision and structured tensor representations.",
        r"convolutional neural network",
        True,
    ),
    "DNN": (
        "deep neural network",
        False,
        "a",
        "ai",
        "An artificial neural network with multiple hidden layers between input and output capable of learning hierarchical feature representations.",
        r"deep[- ]neural[- ]network|deep neural network",
        True,
    ),
    "DQN": (
        "deep Q-network",
        False,
        "a",
        "ai",
        "A model-free reinforcement learning algorithm combining Q-learning with deep neural network function approximators.",
        r"[Dd]eep Q[- ][Nn]etwork",
        True,
    ),
    "DSE": (
        "design-space exploration",
        False,
        "a",
        "ai",
        "The systematic evaluation of architectural and microarchitectural parameters to identify Pareto-optimal trade-offs across power, performance, and area.",
        r"design[- ]space exploration",
        False,
    ),
    "ECE": (
        "expected calibration error",
        False,
        "an",
        "ai",
        "A statistical metric measuring the difference between predicted model confidence probabilities and actual empirical accuracy.",
        r"[Ee]xpected [Cc]alibration [Ee]rror",
        True,
    ),
    "FP8": (
        "8-bit floating-point",
        False,
        "an",
        "ai",
        "A low-precision floating-point arithmetic format standardized for high-throughput deep learning training and inference.",
        r"(?:8[- ]bit )?floating[- ]point",
        True,
    ),
    "GNN": (
        "graph neural network",
        False,
        "a",
        "ai",
        "A class of deep learning architectures operating directly on graph-structured data via message-passing between nodes and edges.",
        r"graph neural network",
        True,
    ),
    "HELM": (
        "Holistic Evaluation of Language Models",
        True,
        "an",
        "ai",
        "A standardized benchmark framework that systematically evaluates foundation language models across diverse capabilities, risks, and behavioral metrics.",
        r"Holistic\ Evaluation\ of\ Language\ Models",
        True,
    ),
    "INT4": (
        "4-bit integer",
        False,
        "an",
        "ai",
        "A quantized integer numeric representation using 4 bits per weight or activation to minimize memory bandwidth and footprint in deep learning accelerators.",
        r"4[- ]bit integer",
        True,
    ),
    "INT8": (
        "8-bit integer",
        False,
        "an",
        "ai",
        "An integer data format using 8 bits of precision commonly deployed in quantized neural network inference accelerators.",
        r"8\-bit\ integer",
        True,
    ),
    "KV": (
        "key-value",
        False,
        "a",
        "ai",
        "A pair of tensors storing intermediate attention projections in transformer models, frequently cached across decoding steps.",
        r"key[- ]value",
        True,
    ),
    "LLM": (
        "large language model",
        False,
        "an",
        "ai",
        "A deep neural network trained on vast text or code corpora, capable of autoregressive token generation for natural language reasoning and code synthesis.",
        r"large language model",
        False,
    ),
    "MCTS": (
        "Monte Carlo tree search",
        True,
        "an",
        "ai",
        "A heuristic search algorithm for decision processes combining tree traversal with Monte Carlo rollouts to evaluate candidate actions.",
        r"Monte Carlo (?:tree )?search",
        True,
    ),
    "MDP": (
        "Markov decision process",
        False,
        "an",
        "ai",
        "A formal mathematical framework for modeling decision-making in discrete stochastic environments defined by states, actions, transition probabilities, and rewards.",
        r"Markov decision process",
        False,
    ),
    "MoE": (
        "mixture of experts",
        False,
        "a",
        "ai",
        "A neural network architecture routing individual input tokens to specialized expert sub-networks to scale parameter capacity with constant compute.",
        r"mixture[- ]of[- ]experts",
        True,
    ),
    "OCI": (
        "Open Container Initiative",
        True,
        "an",
        "ai",
        "An open governance structure standardizing container image formats and execution runtime specifications for software isolation.",
        r"Open\ Container\ Initiative",
        True,
    ),
    "PPA": (
        "power, performance, and area",
        False,
        "a",
        "ai",
        "The tripartite metric vector governing semiconductor optimization and architectural figure-of-merit evaluation.",
        r"power,?\s+performance,?\s+and area",
        False,
    ),
    "PPO": (
        "proximal policy optimization",
        False,
        "a",
        "ai",
        "A model-free policy gradient reinforcement learning algorithm using clipped surrogate objectives to maintain stable policy updates.",
        r"[Pp]roximal [Pp]olicy [Oo]ptimization",
        True,
    ),
    "RL": (
        "reinforcement learning",
        False,
        "an",
        "ai",
        "A machine learning paradigm where an autonomous agent learns to optimize a policy by taking actions in an environment to maximize cumulative reward signals.",
        r"reinforcement learning",
        False,
    ),
    "SLSA": (
        "Supply Chain Levels for Software Artifacts",
        True,
        "an",
        "ai",
        "A security framework defining machine-readable, cryptographically signed metadata attestations for build provenance and supply chain integrity.",
        r"Supply Chain Levels for Software Artifacts",
        False,
    ),
}

CMOS_ARTICLE_CHECKS: dict[str, str] = {
    abbr: data[2] for abbr, data in CMOS_ABBREVIATIONS.items()
}

IGNORED_PROSE_ACRONYMS: set[str] = {
    # General English & document abbreviations
    "AI",
    "ML",
    "DL",
    "OS",
    "UI",
    "UX",
    "IO",
    "ID",
    "IP",
    "PR",
    "CI",
    "CD",
    "QA",
    "QC",
    "OK",
    "TV",
    "DC",
    "AC",
    "RF",
    "HW",
    "SW",
    "VS",
    "PM",
    "AM",
    "PDF",
    "HTML",
    "EPUB",
    "SVG",
    "PNG",
    "JSON",
    "YAML",
    "XML",
    "CSV",
    "CLI",
    "URL",
    "HTTP",
    "HTTPS",
    "UTF",
    "ASCII",
    "USA",
    "UK",
    "EU",
    "FAQ",
    "N/A",
    "TBD",
    "TODO",
    "I",
    "II",
    "III",
    "IV",
    "V",
    "VI",
    "VII",
    "VIII",
    "IX",
    "X",
    "XI",
    "XII",
    "UUID",
    "IC",
    "UVM",
    "RNG",
    "PLA",
    "DRAM",
    "ILP",
    "FSM",
    "DFT",
    "ATPG",
    "ECC",
    "EPIC",
    "SAT",
    "SMT",
    "DSP",
    "SMAC",
    "MAC",
    "OOM",
    "WNS",
    "RMSE",
    # Organizations, venues & institutions
    "MIT",
    "ACM",
    "NSF",
    "DARPA",
    "SRC",
    "NASA",
    "DAC",
    "MICRO",
    "ISCA",
    "ASPLOS",
    "DATE",
    "ICCAD",
    "MLCommons",
    "CEDA",
    "IBS",
    "NVIDIA",
    "Google",
    "Intel",
    "AMD",
    "Arm",
    "Apple",
    "Qualcomm",
    "Meta",
    "Micron",
    "Synopsys",
    "Cadence",
    "Siemens",
    "Ansys",
    # Software tools & suites
    "OpenROAD",
    "OpenSTA",
    "Yosys",
    "Verilator",
    "KernelBench",
    "XRBench",
    "MLPerf",
    "SCALE-Sim",
    "RV64GCV",
    "RVV",
    "OAI",
    "MAPT",
    "Partha",
    "LInc",
    "DPC",
    "CBP",
    # Measurement units
    "MiB",
    "GiB",
    "KiB",
    "TiB",
    "MHz",
    "GHz",
    "MIPS",
    "FLOPS",
    "TFLOPS",
    "GFLOPS",
    "TOPS",
}

GLOSSARY_PATH = (
    BOOK_DIR / "contents" / "backmatter" / "apdx-d-glossary" / "apdx-d-glossary.qmd"
)
LUA_GLOSSARY_FILTER_PATH = BOOK_DIR / "filters" / "glossary.lua"


def generate_glossary_markdown() -> str:
    """Generate the canonical markdown source for Appendix D: Glossary."""
    lines = [
        "---",
        "format:",
        "  html:",
        "    output-file: index.html",
        "---",
        "",
        "# Acronyms and Technical Glossary {#sec-appendix-d-glossary}",
        "",
        "::: {.abstract}",
        "This reference appendix consolidates and categorizes the technical acronyms, standards, formal representations, and abbreviations used throughout *Architecture 2.0*. Each entry lists the canonical abbreviation, its spelled-out form per the *Chicago Manual of Style*, and a concise engineering definition, grouped by technical domain across hardware microarchitecture (@tbl-glossary-hardware), physical design and signoff (@tbl-glossary-physical), EDA and compilers (@tbl-glossary-compilers), verification and standards (@tbl-glossary-verification), bus interconnects (@tbl-glossary-interconnects), and AI automation (@tbl-glossary-ai).",
        ":::",
        "",
    ]

    for domain_key, domain_title, table_anchor, sec_anchor in GLOSSARY_DOMAINS:
        lines.append(f"## {domain_title} {{#{sec_anchor}}}")
        lines.append("")
        lines.append(
            "| **Acronym** | **Spelled-out form** | **Engineering definition** |"
        )
        lines.append("| :--- | :--- | :--- |")

        domain_abbrs = [
            (abbr, data)
            for abbr, data in sorted(
                CMOS_ABBREVIATIONS.items(), key=lambda item: item[0].casefold()
            )
            if data[3] == domain_key
        ]

        for abbr, (
            canonical,
            is_proper,
            article,
            dom,
            definition,
            pattern,
            exempt,
        ) in domain_abbrs:
            lines.append(f"| **{abbr}** | {canonical} | {definition} |")

        lines.append(
            f': **{domain_title} Glossary.** {{#{table_anchor} tbl-colwidths="[15,30,55]"}}'
        )
        lines.append("")

    return "\n".join(lines)


def generate_glossary_lua() -> str:
    """Generate the Lua filter for Quarto HTML interactive tooltips."""
    lines = [
        "-- filters/glossary.lua",
        "-- Architecture 2.0 Quarto Filter: Injects semantic <abbr> tooltips for technical acronyms in HTML output.",
        "-- Auto-generated by './arch2 generate glossary' from cli/arch2.py; do not edit directly.",
        "",
        "local acronyms = {",
    ]

    for abbr, (
        canonical,
        is_proper,
        article,
        dom,
        definition,
        pattern,
        exempt,
    ) in sorted(CMOS_ABBREVIATIONS.items(), key=lambda item: item[0].casefold()):
        safe_def = definition.replace('"', '\\"')
        safe_canonical = canonical.replace('"', '\\"')
        lines.append(f'  ["{abbr}"] = "{safe_canonical}: {safe_def}",')

    lines.extend(
        [
            "}",
            "",
            "if not quarto.doc.is_format('html') then",
            "  return {}",
            "end",
            "",
            "local function replace_inlines(inlines)",
            "  local result = pandoc.Inlines({})",
            "  for i, inline in ipairs(inlines) do",
            "    if inline.t == 'Str' then",
            "      local clean, punct = inline.text:match('^([%a%-%d]+)([%p]*)$')",
            "      if clean and acronyms[clean] then",
            "        local title = acronyms[clean]:gsub('\"', '&quot;')",
            "        local html = '<abbr class=\"arch2-abbr\" title=\"' .. title .. '\">' .. clean .. '</abbr>' .. punct",
            "        table.insert(result, pandoc.RawInline('html', html))",
            "      else",
            "        table.insert(result, inline)",
            "      end",
            "    elseif inline.t == 'Link' or inline.t == 'Code' or inline.t == 'Math' or inline.t == 'RawInline' then",
            "      table.insert(result, inline)",
            "    elseif inline.content and type(inline.content) == 'table' then",
            "      inline.content = replace_inlines(inline.content)",
            "      table.insert(result, inline)",
            "    else",
            "      table.insert(result, inline)",
            "    end",
            "  end",
            "  return result",
            "end",
            "",
            "function Para(el)",
            "  el.content = replace_inlines(el.content)",
            "  return el",
            "end",
            "",
            "function Plain(el)",
            "  el.content = replace_inlines(el.content)",
            "  return el",
            "end",
        ]
    )

    return "\n".join(lines)


def glossary_findings() -> list[Finding]:
    """Verify that the Glossary appendix and Lua filter are present, registered, and up to date."""
    findings: list[Finding] = []

    # 1. Check QMD file
    if not GLOSSARY_PATH.exists():
        findings.append(
            Finding(
                "error",
                "missing-glossary-file",
                _relative(GLOSSARY_PATH),
                "Glossary appendix file is missing; run './arch2 generate glossary' to create it.",
            )
        )
    else:
        actual_qmd = GLOSSARY_PATH.read_text(encoding="utf-8").strip()
        expected_qmd = generate_glossary_markdown().strip()
        if actual_qmd != expected_qmd:
            findings.append(
                Finding(
                    "error",
                    "glossary-drift",
                    _relative(GLOSSARY_PATH),
                    "Glossary appendix content is out of sync with CMOS_ABBREVIATIONS; run './arch2 generate glossary' to update.",
                )
            )

    # 2. Check Lua filter file
    if not LUA_GLOSSARY_FILTER_PATH.exists():
        findings.append(
            Finding(
                "error",
                "missing-glossary-filter",
                _relative(LUA_GLOSSARY_FILTER_PATH),
                "Glossary Lua filter file is missing; run './arch2 generate glossary' to create it.",
            )
        )
    else:
        actual_lua = LUA_GLOSSARY_FILTER_PATH.read_text(encoding="utf-8").strip()
        expected_lua = generate_glossary_lua().strip()
        if actual_lua != expected_lua:
            findings.append(
                Finding(
                    "error",
                    "glossary-filter-drift",
                    _relative(LUA_GLOSSARY_FILTER_PATH),
                    "Glossary Lua filter content is out of sync with CMOS_ABBREVIATIONS; run './arch2 generate glossary' to update.",
                )
            )

    # 3. Check _quarto.yml registration
    manifest_path = BOOK_DIR / "_quarto.yml"
    if manifest_path.exists():
        manifest_text = manifest_path.read_text(encoding="utf-8")
        if (
            "contents/backmatter/apdx-d-glossary/apdx-d-glossary.qmd"
            not in manifest_text
        ):
            findings.append(
                Finding(
                    "error",
                    "missing-glossary-manifest",
                    _relative(manifest_path),
                    "_quarto.yml is missing 'contents/backmatter/apdx-d-glossary/apdx-d-glossary.qmd' under appendices",
                )
            )
        if "filters/glossary.lua" not in manifest_text:
            findings.append(
                Finding(
                    "error",
                    "missing-glossary-filter-manifest",
                    _relative(manifest_path),
                    "_quarto.yml is missing 'filters/glossary.lua' under filters",
                )
            )

    return findings


def run_glossary_check() -> None:
    _exit_on_findings(glossary_findings(), title="glossary & acronym catalog")


def run_glossary_generation() -> None:
    GLOSSARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    GLOSSARY_PATH.write_text(generate_glossary_markdown(), encoding="utf-8")
    LUA_GLOSSARY_FILTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    LUA_GLOSSARY_FILTER_PATH.write_text(generate_glossary_lua(), encoding="utf-8")
    console.print(f"[green]generated[/green] {_relative(GLOSSARY_PATH)}")
    console.print(f"[green]generated[/green] {_relative(LUA_GLOSSARY_FILTER_PATH)}")


# Function words that an acronym skips over, so they never begin an expansion
# and never contribute a letter ("dynamic voltage and frequency scaling" -> DVFS).
_EXPANSION_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "at",
        "by",
        "for",
        "from",
        "in",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
    }
)

# Longest run of words an expansion is allowed to span before the parenthetical.
_EXPANSION_MAX_WORDS = 12


def _expansion_spells_abbr(words: list[str], abbr: str) -> bool:
    """Report whether the initials of ``words`` spell ``abbr``.

    Each word contributes its initial. A hyphenated word contributes one
    initial per part, so "domain-specific architecture" spells DSA. An
    all-caps part contributes every one of its letters, so "Flexible
    Intermediate Representation for RTL" spells FIRRTL. An internal capital
    may stand in for the initial, so "Advanced eXtensible Interface 5"
    spells AXI5.
    """
    target = abbr.upper()
    pos = 0
    for word in words:
        for part in re.split(r"[-‐-―/]", word):
            part = part.strip("'’\".,;:()[]")
            if not part or not part[0].isalnum():
                continue
            if pos >= len(target):
                return False
            if len(part) > 1 and part.isupper() and target.startswith(part, pos):
                pos += len(part)
                continue
            if part[0].upper() == target[pos]:
                pos += 1
                continue
            inner = next((c for c in part[1:] if c.isupper()), None)
            if inner is not None and inner == target[pos]:
                pos += 1
                continue
            return False
    return pos == len(target)


def _match_prose_expansion(preceding: str, abbr: str) -> str | None:
    """Return the words immediately before ``(abbr)`` that ``abbr`` abbreviates.

    Scans right to left and returns the *shortest* window that spells the
    acronym, so "chips and Google Tensor Processing Unit (TPU)" yields
    "Tensor Processing Unit" rather than everything back to the last comma.
    Returns None when no window spells it, which is the signal that the
    parenthetical is not an expansion at all.
    """
    tokens = preceding.split()
    if not tokens:
        return None
    window = tokens[-_EXPANSION_MAX_WORDS:]
    for start in range(len(window) - 1, -1, -1):
        if window[start].lower() in _EXPANSION_STOPWORDS:
            continue
        candidate = window[start:]
        significant = [w for w in candidate if w.lower() not in _EXPANSION_STOPWORDS]
        if significant and _expansion_spells_abbr(significant, abbr):
            return " ".join(candidate)
    return None


def abbreviations_findings(paths: list[Path] | None = None) -> list[Finding]:
    """Validate abbreviations against CMOS Chapter 10 standards and first-mention rules.

    Checks:
    1. First-mention expansion: Every technical abbreviation must be defined on or before
       its first occurrence in running prose within each chapter file.
    2. Lowercase common nouns: Common nouns must be lowercase when spelled out
       (e.g., 'register-transfer level (RTL)', not 'Register-Transfer Level (RTL)').
    3. Phonetic article agreement: 'a' vs 'an' matching pronunciation ('an RTL', 'a CPU').
    4. Plural apostrophe misuse: Flag 'SoC\'s' or 'ASIC\'s' when used as plurals.
    """
    targets = paths if paths is not None else content_qmd_files()
    findings: list[Finding] = []

    for path in targets:
        # Skip the Glossary appendix itself from first-mention self-referencing check
        if path.resolve() == GLOSSARY_PATH.resolve():
            continue

        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()

        # Step 1: Map all explicit definitions in the file
        definitions: dict[str, int] = {}
        for lineno, line in enumerate(lines, start=1):
            for abbr, data in CMOS_ABBREVIATIONS.items():
                canonical = data[0]
                is_proper = data[1]
                pattern = data[5]
                def_regex = re.compile(
                    rf"(?i:\b(?:{pattern})s?\b)\s*\([^)]*\b{abbr}s?\b[^)]*\)"
                )
                for match in def_regex.finditer(line):
                    if abbr not in definitions:
                        definitions[abbr] = lineno

                    # Check for over-capitalization if it is a common noun
                    if not is_proper:
                        full_term = match.group(0).split("(")[0].strip()
                        words = full_term.split()
                        cap_words = [
                            w
                            for w in words
                            if w[0].isupper()
                            and w.lower()
                            not in ("and", "or", "in", "of", "the", "a", "an")
                        ]
                        if len(cap_words) >= 2:
                            findings.append(
                                Finding(
                                    "error",
                                    "overcapitalized-expansion",
                                    f"{_relative(path)}:{lineno}",
                                    f"spelled-out form '{full_term}' for '{abbr}' has "
                                    f"over-capitalized common nouns; use lowercase: '{canonical} ({abbr})'",
                                )
                            )

        # Step 2: Check running prose occurrences
        in_fence = False
        flagged_unexpanded: set[str] = set()

        for lineno, line in enumerate(lines, start=1):
            stripped = line.lstrip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = not in_fence
                continue
            if in_fence or stripped.startswith("<!--") or stripped.startswith(":::"):
                continue

            # Strip non-prose elements (inline code, link/image URLs, cross-refs, citations, math)
            prose = re.sub(r"`[^`]+`", "", line)
            prose = re.sub(r"\]\([^)]+\)", "]", prose)
            prose = re.sub(r"[@{#]*(?:fig|tbl|sec|lst|eq)-[a-z0-9-]+", "", prose)
            prose = re.sub(r"@[A-Za-z0-9_:]+", "", prose)
            prose = re.sub(r"\$[^\$]+\$", "", prose)

            # Check phonetic article agreement ('a' vs 'an')
            for match in re.finditer(r"\b(a|an)\s+([A-Z]{2,}|SoC|NoC)\b", prose):
                art = match.group(1).lower()
                abbr_found = match.group(2)
                if abbr_found in CMOS_ARTICLE_CHECKS:
                    expected_art = CMOS_ARTICLE_CHECKS[abbr_found]
                    if art != expected_art:
                        findings.append(
                            Finding(
                                "error",
                                "abbreviation-article-mismatch",
                                f"{_relative(path)}:{lineno}",
                                f"use '{expected_art} {abbr_found}' instead of '{art} {abbr_found}' based on pronunciation",
                            )
                        )

            # Check for plural apostrophe misuse (e.g. 'SoC\'s' used as plural)
            for match in re.finditer(r"\b([A-Z]{2,}|SoC|NoC)'s\b", prose):
                abbr_base = match.group(1)
                match_span = match.start()
                preceding = prose[max(0, match_span - 25) : match_span].lower()
                if any(
                    quant in preceding
                    for quant in (
                        "multiple",
                        "two",
                        "three",
                        "four",
                        "several",
                        "many",
                        "all",
                        "different",
                        "across",
                        "between",
                        "both",
                        "various",
                        "these",
                        "those",
                    )
                ):
                    findings.append(
                        Finding(
                            "error",
                            "abbreviation-plural-apostrophe",
                            f"{_relative(path)}:{lineno}",
                            f"do not use an apostrophe for plural abbreviation '{match.group(0)}'; use '{abbr_base}s'",
                        )
                    )

            # Check unexpanded abbreviations in running prose (flag first unexpanded occurrence per file)
            for abbr, data in CMOS_ABBREVIATIONS.items():
                canonical = data[0]
                pattern = data[5]
                exempt = data[6]
                if exempt or abbr in flagged_unexpanded:
                    continue
                for match in re.finditer(rf"\b({abbr}s?)\b", prose):
                    span_start = match.start()
                    span_end = match.end()
                    # Skip if preceded by '(' (part of a definition or parenthetical)
                    if span_start > 0 and prose[span_start - 1] == "(":
                        continue
                    # Skip 'IR' when it is part of 'IR-drop' or 'IR drop' (voltage drop)
                    if abbr == "IR" and re.match(
                        r"^[- ](?:drop|droop)", prose[span_end:], re.IGNORECASE
                    ):
                        continue
                    # Skip if this line itself defines the abbreviation
                    def_regex = re.compile(
                        rf"(?i:\b(?:{pattern})s?\b)\s*\([^)]*\b{abbr}s?\b[^)]*\)"
                    )
                    if def_regex.search(line):
                        continue

                    # If this abbreviation was never defined in this file or used before its definition
                    if abbr not in definitions or definitions[abbr] > lineno:
                        findings.append(
                            Finding(
                                "error",
                                "unexpanded-abbreviation",
                                f"{_relative(path)}:{lineno}",
                                f"'{abbr}' is used before/without first-mention definition in this chapter "
                                f"(define as '{canonical} ({abbr})' on first use)",
                            )
                        )
                        flagged_unexpanded.add(abbr)
                        break

        # Step 3: Check for unregistered technical abbreviations expanded in prose
        for lineno, line in enumerate(lines, start=1):
            stripped = line.lstrip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = not in_fence
                continue
            if in_fence or stripped.startswith("<!--") or stripped.startswith(":::"):
                continue

            for match in re.finditer(r"\(([A-Z0-9]{2,8})\)", line):
                abbr = match.group(1).strip()

                # Skip registered entries or recognized plurals of registered entries
                base_abbr = (
                    abbr[:-1]
                    if abbr.endswith("s") and abbr[:-1] in CMOS_ABBREVIATIONS
                    else abbr
                )
                if (
                    base_abbr in CMOS_ABBREVIATIONS
                    or abbr in IGNORED_PROSE_ACRONYMS
                    or base_abbr in IGNORED_PROSE_ACRONYMS
                ):
                    continue

                # Recover the words the acronym actually abbreviates. A None
                # result means this parenthetical is not an expansion (a bare
                # citation, a unit, an aside), so there is nothing to register.
                expansion = _match_prose_expansion(line[: match.start()], abbr)
                if expansion is None:
                    continue
                words = [w for w in re.split(r"[\s\-]+", expansion) if w]

                # Recommend proper article and formatting snippet
                first_letter = abbr[0].upper()
                art_hint = (
                    "an"
                    if first_letter
                    in ("A", "E", "F", "H", "I", "L", "M", "N", "O", "R", "S", "X")
                    else "a"
                )
                is_proper = any(
                    w[0].isupper()
                    for w in words
                    if w.lower() not in ("and", "or", "in", "of", "the", "a", "an")
                )

                findings.append(
                    Finding(
                        "warning",
                        "unregistered-abbreviation",
                        f"{_relative(path)}:{lineno}",
                        f"'{abbr}' is expanded as '{expansion}' in prose but is not registered in CMOS_ABBREVIATIONS in cli/arch2.py; "
                        f'add entry: \'"{abbr}": ("{expansion.lower()}", {is_proper}, "{art_hint}", "<domain_key>", "<1-sentence definition>", r"{re.escape(expansion)}", False)\' '
                        f"and run './arch2 generate glossary' to update Appendix D and tooltips.",
                    )
                )

    return findings


def run_abbreviations_check(paths: list[Path] | None = None) -> None:
    _exit_on_findings(abbreviations_findings(paths), title="abbreviations & acronyms")


def run_footnote_check() -> None:
    findings = footnote_in_table_findings()
    findings.extend(footnote_source_findings())
    for path in content_qmd_files():
        findings.extend(footnote_punctuation_findings(path))
    _exit_on_findings(findings, title="footnotes")


def run_prose_style_check() -> None:
    _exit_on_findings(prose_style_findings(), title="prose style")


def run_caption_check() -> None:
    _exit_on_findings(caption_findings(), title="figure captions")


def run_html_check(html: Path = HTML_PATH) -> None:
    _exit_on_findings(html_findings(html), title="HTML site")


def run_rendered_unresolved_check() -> None:
    _exit_on_findings(rendered_unresolved_findings(), title="rendered references")


def run_generated_asset_check() -> None:
    # The site deploy renders figures fresh into _site, so committed-asset drift
    # is a repo-hygiene signal, not a published-output problem. Allow the deploy
    # render to opt out (see build_site.sh), matching the --no-layout policy of
    # not blocking the community-page publish on non-content noise. Figure
    # generation is not yet byte-deterministic, so this is a warning there.
    if os.environ.get("ARCH2_SKIP_ASSET_DRIFT") == "1":
        findings = generated_asset_findings()
        if findings:
            console.print(
                f"[yellow]warning[/yellow] {len(findings)} generated asset(s) "
                "drifted after render; skipped as non-blocking for the site "
                "deploy (ARCH2_SKIP_ASSET_DRIFT=1)"
            )
        return
    _exit_on_findings(generated_asset_findings(), title="generated assets")


def run_svg_check(paths: list[Path] | None = None) -> None:
    _exit_on_findings(svg_text_findings(paths), title="SVG text fit")


def run_citation_check(*, show_context: bool = False) -> None:
    _emit_findings(
        citation_reuse_findings(show_context=show_context), title="citation reuse"
    )


def run_bibliography_check() -> None:
    _exit_on_findings(bibliography_findings(), title="bibliography")


def run_concept_check() -> None:
    _exit_on_findings(concept_findings(), title="concept disclosure")


def run_disclosure_check() -> None:
    _exit_on_findings(disclosure_findings(), title="progressive disclosure")


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _loop_output_dir(out_dir: Path | None = None) -> Path:
    target = out_dir or LOOP_DIR
    if not target.is_absolute():
        target = ROOT / target
    target.mkdir(parents=True, exist_ok=True)
    return target


def _write_loop_artifact(
    kind: str, body: str, *, out_dir: Path | None = None, suffix: str = "md"
) -> Path:
    target_dir = _loop_output_dir(out_dir)
    path = target_dir / f"{kind}-{_timestamp()}.{suffix}"
    path.write_text(body, encoding="utf-8")
    latest = target_dir / f"{kind}-latest.{suffix}"
    latest.write_text(body, encoding="utf-8")
    return path


def _latest_loop_artifact(
    kind: str, *, out_dir: Path | None = None, suffix: str = "md"
) -> Path:
    target_dir = _loop_output_dir(out_dir)
    latest = target_dir / f"{kind}-latest.{suffix}"
    if latest.exists():
        return latest
    matches = sorted(
        target_dir.glob(f"{kind}-*.{suffix}"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not matches:
        console.print(
            f"[red]missing loop artifact[/red] no {kind}-*.{suffix} in {_relative(target_dir)}"
        )
        raise typer.Exit(1)
    return matches[0]


def _markdown_cell(text: str) -> str:
    return " ".join(text.replace("|", "\\|").split())


def _strip_code_fences(text: str) -> str:
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


def _chapter_title(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^#\s+(.+?)(?:\s+\{#.*)?$", text, flags=re.MULTILINE)
    if match:
        return match.group(1).strip()
    return path.parent.name


def _chapter_sections(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [
        match.group(1).strip()
        for match in re.finditer(r"^##\s+(.+?)(?:\s+\{#.*)?$", text, flags=re.MULTILINE)
    ]


def _chapter_word_count(path: Path) -> int:
    text = _strip_code_fences(path.read_text(encoding="utf-8"))
    text = re.sub(r"\\abstract\*\{.*?\}", "", text, flags=re.DOTALL)
    text = re.sub(r"\{#[^}]+\}", "", text)
    return len(re.findall(r"[A-Za-z][A-Za-z0-9'-]*", text))


def _loop_scope_paths(scope: str, paths: list[Path]) -> list[Path]:
    normalized = scope.strip().lower()
    if normalized in {"", "book", "all"}:
        return paths

    matches: list[Path] = []
    for path in paths:
        rel = str(path.relative_to(BOOK_DIR)).lower()
        parent = path.parent.name.lower()
        title = _chapter_title(path).lower()
        if normalized in {rel, parent, path.stem.lower()}:
            matches.append(path)
            continue
        if normalized in rel or normalized in parent or normalized in title:
            matches.append(path)

    return matches or paths


def _chapter_map_markdown(paths: list[Path]) -> str:
    lines = [
        "## Chapter Map",
        "",
        "| Source | Title | Words | Sections |",
        "| --- | --- | ---: | --- |",
    ]
    for path in paths:
        sections = "; ".join(_chapter_sections(path)[:8])
        if len(_chapter_sections(path)) > 8:
            sections += "; ..."
        lines.append(
            f"| `{_relative(path)}` | {_markdown_cell(_chapter_title(path))} | {_chapter_word_count(path)} | {_markdown_cell(sections)} |"
        )
    return "\n".join(lines)


def _scoped_manuscript_markdown(scope: str, paths: list[Path]) -> str:
    scoped_paths = _loop_scope_paths(scope, paths)
    if len(scoped_paths) == len(paths) and scope.strip().lower() in {"", "book", "all"}:
        return "\n".join(
            [
                "## Scoped Manuscript Text",
                "",
                "Scope is the full book, so the packet includes the map and ledgers rather than the full manuscript text.",
            ]
        )

    lines = [
        "## Scoped Manuscript Text",
        "",
        f"Matched {len(scoped_paths)} source file(s) for scope `{scope}`.",
    ]
    for path in scoped_paths:
        lines.extend(
            [
                "",
                f"### `{_relative(path)}`",
                "",
                "```qmd",
                path.read_text(encoding="utf-8").strip(),
                "```",
            ]
        )
    return "\n".join(lines)


def _concept_occurrences(
    concept: str, paths: list[Path]
) -> list[tuple[Path, int, str]]:
    occurrences: list[tuple[Path, int, str]] = []
    pattern = re.compile(rf"\b{re.escape(concept)}\b", re.I)
    for path in paths:
        for line_number_, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            visible_line = QUARTO_REF_RE.sub("", line)
            visible_line = QUARTO_LABEL_RE.sub("", visible_line)
            if pattern.search(visible_line):
                occurrences.append((path, line_number_, line.strip()))
    return occurrences


def _concept_ledger_markdown(
    paths: list[Path], concepts: tuple[str, ...] = DEFAULT_LOOP_CONCEPTS
) -> str:
    lines = [
        "## Concept Introduction Report",
        "",
        "This report lists where the book's defined concepts appear so a reviewer can check their order of introduction, definition, development, application, and synthesis.",
        "",
        "| Concept | First occurrence | Total uses | Chapters/appendices | First context |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for concept in concepts:
        hits = _concept_occurrences(concept, paths)
        if not hits:
            lines.append(f"| {_markdown_cell(concept)} | - | 0 | - | - |")
            continue
        first_path, first_line, first_context = hits[0]
        chapters = sorted({citation_chapter_name(path) for path, _, _ in hits})
        lines.append(
            "| "
            + " | ".join(
                [
                    _markdown_cell(concept),
                    f"`{_relative(first_path)}:{first_line}`",
                    str(len(hits)),
                    _markdown_cell(", ".join(chapters)),
                    _markdown_cell(first_context[:180]),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def _mechanical_state_markdown() -> str:
    ref_findings = manuscript_integrity_findings()
    citation_findings = citation_reuse_findings(show_context=False)
    disclosure_rows = disclosure_findings()
    lines = [
        "## Mechanical State",
        "",
        "| Gate | Errors | Warnings | Notes |",
        "| --- | ---: | ---: | --- |",
        f"| Source refs/paths/tables | {sum(1 for f in ref_findings if f.severity == 'error')} | {sum(1 for f in ref_findings if f.severity == 'warning')} | `arch2 validate refs` |",
        f"| Progressive disclosure | {sum(1 for f in disclosure_rows if f.severity == 'error')} | {sum(1 for f in disclosure_rows if f.severity == 'warning')} | `arch2 validate disclosure` |",
        f"| Citation reuse | {sum(1 for f in citation_findings if f.severity == 'error')} | {sum(1 for f in citation_findings if f.severity == 'warning')} | `arch2 validate citations` |",
    ]
    if PDF_PATH.exists():
        lines.append(f"| Rendered PDF | 0 | 0 | `{_relative(PDF_PATH)}` exists |")
    else:
        lines.append(
            f"| Rendered PDF | 0 | 1 | `{_relative(PDF_PATH)}` missing or not yet rendered |"
        )
    if HTML_PATH.exists():
        lines.append(f"| Rendered HTML | 0 | 0 | `{_relative(HTML_PATH)}` exists |")
    else:
        lines.append(
            f"| Rendered HTML | 0 | 1 | `{_relative(HTML_PATH)}` missing or not yet rendered |"
        )

    if ref_findings:
        lines.extend(["", "### Source Findings", ""])
        for finding in ref_findings[:40]:
            lines.append(
                f"- `{finding.severity}` `{finding.code}` `{finding.location}`: {finding.message}"
            )
        if len(ref_findings) > 40:
            lines.append(f"- ... {len(ref_findings) - 40} more")

    if citation_findings:
        lines.extend(["", "### Citation-Reuse Warnings", ""])
        for finding in citation_findings[:40]:
            lines.append(f"- `{finding.location}`: {finding.message}")
        if len(citation_findings) > 40:
            lines.append(f"- ... {len(citation_findings) - 40} more")

    if disclosure_rows:
        lines.extend(["", "### Progressive-Disclosure Warnings", ""])
        for finding in disclosure_rows[:40]:
            lines.append(f"- `{finding.code}` `{finding.location}`: {finding.message}")
        if len(disclosure_rows) > 40:
            lines.append(f"- ... {len(disclosure_rows) - 40} more")

    return "\n".join(lines)


def _git_state_markdown() -> str:
    proc = _run(["git", "status", "--short"], capture=True)
    body = proc.stdout.strip() if proc.returncode == 0 else proc.stderr.strip()
    if not body:
        return "\n".join(["## Git State", "", "Clean."])

    status_lines = body.splitlines()
    counts = {
        "modified": sum(1 for line in status_lines if line[:2].strip() == "M"),
        "deleted": sum(1 for line in status_lines if line[:2].strip() == "D"),
        "untracked": sum(1 for line in status_lines if line.startswith("??")),
        "other": 0,
    }
    counts["other"] = (
        len(status_lines) - counts["modified"] - counts["deleted"] - counts["untracked"]
    )
    highlights = [
        line
        for line in status_lines
        if any(
            token in line
            for token in (
                "cli/",
                "README",
                ".arch2",
                "book/",
                "references/",
                "scripts/",
            )
        )
    ][:30]
    if not highlights:
        highlights = status_lines[:30]

    lines = [
        "## Git State",
        "",
        f"Dirty worktree: {len(status_lines)} path(s) "
        f"({counts['modified']} modified, {counts['deleted']} deleted, {counts['untracked']} untracked, {counts['other']} other).",
        "",
        "Representative paths:",
        "",
        "```text",
        *highlights,
    ]
    if len(status_lines) > len(highlights):
        lines.append(
            f"... {len(status_lines) - len(highlights)} more git-status lines omitted from packet"
        )
    lines.append("```")
    return "\n".join(lines)


def build_loop_packet(*, scope: str, focus: str) -> str:
    paths = book_ordered_qmd_files()
    heading = f"# Arch2 Manuscript Loop Packet: {focus}"
    lines = [
        heading,
        "",
        f"- Generated: {_timestamp()}",
        f"- Scope: `{scope}`",
        f"- Focus: `{focus}`",
        "- Thesis guard: improve the manuscript and the process that improves the manuscript.",
        "- Progressive-disclosure guard: each finding should name whether the issue is premature introduction, missing definition, repeated reuse, missing application, or weak synthesis.",
        "",
        "## Review Questions",
        "",
        "1. What book-level changes would most improve the lecture's argument?",
        "2. Where does progressive disclosure break across chapters?",
        "3. Which repeated material should be consolidated, moved, or turned into a cross-reference?",
        "4. Which missing figure, table, or card would most improve reader understanding?",
        "5. Which statements need stronger architecture examples, technical plots, quantitative anchors, or evidence artifacts?",
        "6. Which finding should become an `arch2` check, and which should become a reusable Arch2 writing or artifact rule?",
        "",
        _git_state_markdown(),
        "",
        _mechanical_state_markdown(),
        "",
        _chapter_map_markdown(paths),
        "",
        _scoped_manuscript_markdown(scope, paths),
        "",
        _concept_ledger_markdown(paths),
    ]
    return "\n".join(lines) + "\n"


def _packet_focus(packet: str, fallback: str) -> str:
    match = re.search(r"^- Focus:\s+`([^`]+)`", packet, flags=re.MULTILINE)
    return match.group(1) if match else fallback


def build_reviewer_prompt(packet: str, *, focus: str) -> str:
    return f"""You are reviewing a Synthesis Lecture manuscript titled Architecture 2.0.

Your job is not to polish prose. Your job is to improve the book-level argument and the revision loop.

Focus: {focus}

Review requirements:
- Prioritize progressive disclosure across chapters.
- Separate structural fixes from local copyedits.
- Identify repeated case studies, repeated citations, and repeated definitions.
- Audit whether important statements are architecturally grounded with concrete examples.
- Identify where technical plots or quantitative anchors would materially improve the argument.
- Name missing figures/tables/cards only when they would materially improve the argument.
- For each major issue, say whether it should become: manuscript edit, author decision, reusable rule, mechanical arch2 check, or deferred item.
- Be skeptical about overusing the same examples and about introducing concepts before their owner chapter.
- Keep the response actionable and grounded in the packet below.

Return Markdown with these sections:
1. Critical takeaway
2. Top structural fixes
3. Progressive-disclosure breaks
4. Missing or weak artifacts
5. Rule/check candidates
6. Prioritized next loop

PACKET:

{packet}
"""


def run_loop_review(
    packet_path: Path, *, reviewer: str, model: str, timeout: str
) -> str:
    packet = packet_path.read_text(encoding="utf-8")
    prompt = build_reviewer_prompt(
        packet, focus=_packet_focus(packet, packet_path.stem)
    )
    normalized = reviewer.lower()
    if normalized == "none":
        return "\n".join(
            [
                "# Review Skipped",
                "",
                "External review was skipped. Use the packet with:",
                "",
                "```bash",
                f"./arch2 loop review --packet {_relative(packet_path)} --reviewer gemini",
                "```",
                "",
                "## Prompt",
                "",
                "```text",
                prompt,
                "```",
            ]
        )

    if normalized == "gemini":
        agy = shutil.which("agy")
        fallback = Path.home() / ".local" / "bin" / "agy"
        if agy is None and fallback.exists():
            agy = str(fallback)
        if agy is None:
            raise RuntimeError(
                "could not find `agy`; install it or pass --reviewer none"
            )
        cmd = [
            agy,
            "--model",
            model,
            "--print",
            prompt,
            "--dangerously-skip-permissions",
            "--print-timeout",
            timeout,
        ]
    elif normalized == "claude":
        claude = shutil.which("claude")
        if claude is None:
            raise RuntimeError(
                "could not find `claude`; install it or pass --reviewer none"
            )
        cmd = [claude, "-p", prompt]
    else:
        raise RuntimeError("reviewer must be one of: gemini, claude, none")

    proc = _run(cmd, capture=True)
    transcript = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    if proc.returncode != 0:
        raise RuntimeError(
            f"{reviewer} review failed with exit code {proc.returncode}\n{transcript[-3000:]}"
        )
    return transcript.strip() + "\n"


def _extract_review_items(review_text: str) -> list[str]:
    visible_review = _strip_code_fences(review_text)
    if "# Review Skipped" in visible_review:
        return []

    blocks: list[str] = []
    block_re = re.compile(
        r"(?ms)^\s*(?:[-*]|\d+\.)\s+\*\*(?P<title>[^*\n]+?)\*\*:?\s*"
        r"(?P<body>.*?)(?=^\s*(?:[-*]|\d+\.)\s+\*\*|\n### |\n## |\Z)"
    )
    skip_titles = {
        "issue",
        "fix",
        "critique",
        "target",
        "type",
        "manuscript edit",
        "author decision",
        "mechanical arch2 check",
        "reusable rule",
    }
    for match in block_re.finditer(visible_review):
        title = " ".join(match.group("title").split()).rstrip(":")
        if title.lower() in skip_titles or len(title) < 8:
            continue
        body_lines = []
        for raw_line in match.group("body").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            line = re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", line)
            line = re.sub(r"^\*+\s*", "", line)
            line = re.sub(r"\*+", "", line)
            body_lines.append(line)
        summary = title
        if body_lines:
            summary = f"{title}: {' '.join(body_lines[:3])}"
        blocks.append(summary[:700])

    if blocks:
        return blocks[:80]

    items: list[str] = []
    for raw_line in visible_review.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        bullet = re.match(r"^(?:[-*]\s+|\d+\.\s+)(.+)", line)
        if bullet:
            item = bullet.group(1).strip()
            if len(item) > 16 and not item.startswith(
                ("Generated:", "Reviewer:", "Model:", "Packet:")
            ):
                items.append(item)
    return items[:80]


def _classify_review_item(item: str) -> str:
    lowered = item.lower()
    if re.search(r"\bauthor decision\b", lowered):
        return "author decision"
    if re.search(
        r"\bmechanical arch2 check\b|\barch2 check\b|\bcheck candidate\b", lowered
    ):
        return "check candidate"
    if re.search(r"\breusable rule\b|\barch2 rule\b|\brule candidate\b", lowered):
        return "rule candidate"
    if re.search(r"\bmanuscript edit\b", lowered):
        return "fix candidate"
    if re.search(
        r"\b(thesis|positioning|rename|merge appendices)\b|\bmove logca\b", lowered
    ):
        return "author decision"
    if any(
        token in lowered
        for token in ("validate", "verify", "layout", "unresolved", "citation-reuse")
    ):
        return "check candidate"
    if re.search(r"\b(defer|deferred|later|optional)\b", lowered):
        return "defer"
    return "fix candidate"


def build_triage(review_text: str, *, review_path: Path) -> str:
    buckets = {
        "fix candidate": [],
        "author decision": [],
        "rule candidate": [],
        "check candidate": [],
        "defer": [],
    }
    for item in _extract_review_items(review_text):
        buckets[_classify_review_item(item)].append(item)

    lines = [
        "# Arch2 Loop Triage",
        "",
        f"- Generated: {_timestamp()}",
        f"- Review: `{_relative(review_path)}`",
        "",
        "This file is a triage aid, not an accepted edit list. Promote an item only after checking the manuscript context.",
        "",
    ]
    for bucket_name, label in [
        ("fix candidate", "Fix Candidates"),
        ("author decision", "Author Decisions"),
        ("rule candidate", "Rule Candidates"),
        ("check candidate", "Check Candidates"),
        ("defer", "Deferred / Parking Lot"),
    ]:
        lines.extend([f"## {label}", ""])
        items = buckets[bucket_name]
        if not items:
            lines.append("- None detected automatically.")
        else:
            for item in items:
                lines.append(f"- {item}")
        lines.append("")

    lines.extend(
        [
            "## Acceptance Test For The Next Edit Loop",
            "",
            "Before applying edits, choose one primary loop goal and state:",
            "",
            "- manuscript files to touch;",
            "- rules/checks to update if the issue is recurrent;",
            "- rendered artifact to inspect;",
            "- command that verifies the loop is closed.",
            "",
        ]
    )
    return "\n".join(lines)


def build_learning_report(triage_text: str, *, triage_path: Path) -> str:
    issue_classes = {
        "progressive disclosure": ("progressive-disclosure", "rule"),
        "repeated": ("repetition/reuse", "rule"),
        "citation": ("citation reuse", "warning check"),
        "reference": ("cross-reference integrity", "precommit check"),
        "table": ("table/layout hygiene", "precommit or layout check"),
        "figure": ("figure/layout hygiene", "visual rule or SVG check"),
        "layout": ("rendered layout drift", "standard check"),
        "author decision": ("argument ownership", "human gate"),
    }
    detected: list[tuple[str, str, str]] = []
    lowered = triage_text.lower()
    for needle, (label, action) in issue_classes.items():
        if needle in lowered:
            detected.append((label, action, needle))

    lines = [
        "# Arch2 Loop Learning Report",
        "",
        f"- Generated: {_timestamp()}",
        f"- Triage: `{_relative(triage_path)}`",
        "",
        "The loop improves itself by deciding what should become a manuscript edit, a reusable rule, a mechanical check, or a human decision gate.",
        "",
        "## Detected Issue Classes",
        "",
        "| Issue class | Suggested durable home | Trigger |",
        "| --- | --- | --- |",
    ]
    if not detected:
        lines.append(
            "| None | Manual review | No common issue class detected automatically |"
        )
    else:
        for label, action, needle in detected:
            lines.append(
                f"| {_markdown_cell(label)} | {_markdown_cell(action)} | `{needle}` |"
            )

    lines.extend(
        [
            "",
            "## Rule Update Candidates",
            "",
            "- If the issue changes chapter order, concept ownership, or repeated definitions, update the project progressive-disclosure rule.",
            "- If the issue is an artifact layout or typography standard, update the project figure/table or visual-system rule.",
            "- If the issue is deterministic and cheap to detect, add or extend an `arch2 validate ...` or `arch2 check ...` path in `cli/arch2.py`.",
            "- If the issue requires taste or thesis judgment, keep it as an author decision and do not turn it into a brittle check.",
            "",
            "## Next Revision Pass",
            "",
            "1. Pick one high-value issue class.",
            "2. Patch the manuscript or artifact.",
            "3. Update the matching rule/check when the failure is recurrent.",
            "4. Render or validate.",
            "5. Record what changed and what remains a human decision.",
            "",
        ]
    )
    return "\n".join(lines)


def run_python_check() -> None:
    sources = sorted(
        [
            *ROOT.glob("cli/*.py"),
            *ROOT.glob(".github/scripts/*.py"),
            *ROOT.glob("scripts/*.py"),
            *ROOT.glob("tools/*.py"),
            *BOOK_DIR.glob("scripts/*.py"),
        ]
    )
    if not sources:
        console.print("[yellow]skipped[/yellow] Python syntax: no helper scripts found")
        return
    proc = _run(
        [sys.executable, "-m", "py_compile", *[str(path) for path in sources]],
        capture=True,
    )
    _exit_if_failed(proc, "Python syntax")


def run_book_navbar_check() -> None:
    proc = _run(
        [
            sys.executable,
            str(ROOT / ".github/scripts/render_book_navbar.py"),
            "--check",
        ],
        cwd=ROOT,
        capture=True,
    )
    _exit_if_failed(proc, "book navbar sync")


def run_registry_check() -> None:
    for script, label in (
        (ROOT / "tools" / "validate_registries.py", "registry contracts"),
        (ROOT / "tools" / "render_awesome.py", "AWESOME registry mirror"),
    ):
        cmd = [sys.executable, str(script)]
        if script.name == "render_awesome.py":
            cmd.append("--check")
        proc = _run(cmd, cwd=ROOT, capture=True)
        _exit_if_failed(proc, label)


_LATEX_SCRATCH_PATTERNS = (
    "*.aux",
    "*.bbl",
    "*.blg",
    "*.idx",
    "*.ilg",
    "*.ind",
    "*.log",
    "*.out",
    "*.run.xml",
    "*.synctex.gz",
    "*.tex",
    "DescriptionTexts.txt",
)
_PREPARE_SCRIPT = BOOK_DIR / "scripts" / "prepare_render.py"
_RENDER_FORMATS = ("html", "pdf", "epub")


def _prepare_figures() -> None:
    """Convert SVG figures and refresh chapter images before Quarto renders.

    Formerly the Quarto pre-render hook. The CLI now drives it explicitly so the
    build pipeline is owned end to end here rather than by Quarto lifecycle hooks.
    """
    console.print("[cyan]preparing[/cyan] figures and chapter images")
    proc = _run([sys.executable, str(_PREPARE_SCRIPT)], cwd=ROOT, capture=True)
    if proc.returncode != 0:
        console.print("[red]figure preparation failed[/red]")
        console.print(((proc.stdout or "") + (proc.stderr or ""))[-4000:])
        raise typer.Exit(proc.returncode)


def _render_book_navbar() -> None:
    console.print("[cyan]rendering[/cyan] book navbar from shared metadata")
    proc = _run(
        [sys.executable, str(ROOT / ".github/scripts/render_book_navbar.py")],
        cwd=ROOT,
        capture=True,
    )
    if proc.returncode != 0:
        console.print("[red]book navbar render failed[/red]")
        console.print(((proc.stdout or "") + (proc.stderr or ""))[-4000:])
        raise typer.Exit(proc.returncode)


@contextmanager
def _temporary_version_tex(path: Path, release_label: str) -> Iterator[None]:
    original = path.read_bytes() if path.exists() else None
    path.write_text(
        f"\\def\\ArchTwoReleaseVersion{{{release_label}}}\n", encoding="utf-8"
    )
    try:
        yield
    finally:
        if original is None:
            path.unlink(missing_ok=True)
        else:
            path.write_bytes(original)


def _clean_latex_scratch(keep_logs: bool) -> None:
    """Remove LaTeX scratch files left in the book directory after a PDF render."""
    if keep_logs:
        return
    for pattern in _LATEX_SCRATCH_PATTERNS:
        for path in BOOK_DIR.glob(pattern):
            if path.is_file():
                path.unlink()


def _resolve_formats(to: str) -> list[str]:
    fmts = (
        list(_RENDER_FORMATS)
        if to == "all"
        else [t.strip() for t in to.split(",") if t.strip()]
    )
    if not fmts or any(f not in _RENDER_FORMATS for f in fmts):
        console.print(
            "[red]invalid render target[/red] use: all, or a comma list of html, pdf, epub"
        )
        raise typer.Exit(2)
    return fmts


def _render_one(
    to: str,
    *,
    layout: bool,
    keep_logs: bool,
    keep_tex: bool,
    refresh: bool,
    bottom_clearance: float,
) -> None:
    """Prepare, render, and audit one or more formats in a single Quarto pass.

    Owns the whole pipeline natively: figure prep, the Quarto render (with no
    lifecycle hooks), and every post-build audit (figure, HTML, EPUB, PDF layout)
    plus LaTeX scratch cleanup. Multiple formats render in ONE pass so they do not
    clobber each other's output.
    """
    fmts = _resolve_formats(to)

    _render_book_navbar()
    _prepare_figures()

    env: dict[str, str] = {}
    if keep_logs:
        env["ARCH2_KEEP_LATEX_LOGS"] = "1"
    # A Quarto book keeps multiple formats side by side only with a bare
    # "render all"; any explicit --to (even repeated) re-cleans _build between
    # formats and clobbers earlier output. So render ONE requested format with
    # --to, and several by rendering all and pruning the unrequested single-file
    # outputs (pdf/epub) afterward.
    render_all = len(fmts) > 1
    cmd = ["quarto", "render", "book"]
    if not render_all:
        cmd.extend(["--to", fmts[0]])
    if keep_tex:
        cmd.extend(["-M", "keep-tex:true"])
    if refresh:
        cmd.extend(["--execute", "--no-cache"])
    release_version = os.environ.get("ARCH2_VERSION", "").strip()
    if release_version:
        cmd.extend(["-M", f"arch2-version:{release_version}"])
    # Write the LaTeX release label so the PDF matches the site. Written
    # every render: the release version when ARCH2_VERSION is set (publish), the
    # static default otherwise (so local builds leave no git diff). Included ahead
    # of springer-header.tex via _quarto.yml include-in-header.
    version_tex = ROOT / "book" / "tex" / "version.tex"
    release_label = (
        f"Release {release_version}" if release_version else "Development build"
    )
    publish_date = os.environ.get("ARCH2_PUBLISH_DATE", "").strip()
    if publish_date:
        cmd.extend(["-M", f"date:{publish_date}"])
    console.print(f"[cyan]rendering[/cyan] {' '.join(cmd)}")
    with _temporary_version_tex(version_tex, release_label):
        proc = _run(cmd, cwd=ROOT, env=env, capture=True)
    transcript = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    log_path = _record_log("render", transcript)

    if proc.returncode != 0:
        console.print(f"[red]render failed[/red] transcript: {_relative(log_path)}")
        console.print(transcript[-4000:])
        raise typer.Exit(proc.returncode)

    # When we rendered everything to build a subset, drop the unrequested
    # single-file outputs so `build --html --pdf` leaves exactly HTML + PDF.
    if render_all:
        if "pdf" not in fmts and PDF_PATH.exists():
            PDF_PATH.unlink()
        if "epub" not in fmts and EPUB_PATH.exists():
            EPUB_PATH.unlink()

    if "pdf" in fmts:
        console.print(f"[green]rendered[/green] {_relative(PDF_PATH)}")
    if "html" in fmts:
        console.print(f"[green]rendered[/green] {_relative(HTML_PATH)}")
    if "epub" in fmts:
        console.print(f"[green]rendered[/green] {_relative(EPUB_PATH)}")
    console.print(f"[dim]transcript: {_relative(log_path)}[/dim]")
    tex_path = generated_tex()
    if keep_tex and tex_path:
        console.print(f"[dim]generated TeX: {_relative(tex_path)}[/dim]")

    # Native finalization (formerly the Quarto post-render hook).
    if "html" in fmts:
        normalized_link_count = normalize_html_hub_links(BUILD_DIR)
        if normalized_link_count:
            console.print(
                f"[green]normalized[/green] {normalized_link_count} HTML hub links"
            )
        run_html_check(HTML_PATH)
        _exit_on_findings(
            html_unresolved_findings(BUILD_DIR), title="HTML rendered references"
        )
    if "epub" in fmts:
        try:
            normalized_count = normalize_epub_xhtml(EPUB_PATH)
        except (ET.ParseError, zipfile.BadZipFile) as exc:
            console.print(f"[red]EPUB XHTML normalization failed[/red] {exc}")
            raise typer.Exit(1) from exc
        if normalized_count:
            console.print(
                f"[green]normalized[/green] {normalized_count} EPUB XHTML attributes"
            )
        _exit_on_findings(epub_findings(EPUB_PATH), title="EPUB package")
        _exit_on_findings(
            epub_unresolved_findings(EPUB_PATH), title="EPUB rendered references"
        )
        run_epubcheck(EPUB_PATH)
    if "pdf" in fmts:
        run_figures_check(PDF_PATH)
        _exit_on_findings(
            pdf_unresolved_findings(PDF_PATH), title="PDF rendered references"
        )
        layout_error = False
        if layout:
            findings = layout_findings(PDF_PATH, bottom_clearance=bottom_clearance)
            _emit_findings(findings, title="layout audit")
            layout_error = any(finding.severity == "error" for finding in findings)
        _clean_latex_scratch(keep_logs)
        if layout_error:
            raise typer.Exit(1)
    run_generated_asset_check()


@app.command()
def render(
    layout: bool = typer.Option(
        True, "--layout/--no-layout", help="Scan the rendered PDF for layout issues."
    ),
    keep_logs: bool = typer.Option(
        True, "--keep-logs/--clean-logs", help="Preserve LaTeX logs for audit."
    ),
    keep_tex: bool = typer.Option(
        False,
        "--keep-tex/--no-keep-tex",
        help="Ask Quarto to preserve generated TeX for review.",
    ),
    refresh: bool = typer.Option(
        False,
        "--refresh/--no-refresh",
        help="Re-execute code chunks and ignore Quarto execution caches.",
    ),
    bottom_clearance: float = typer.Option(
        72.0, help="Bottom margin warning threshold in PDF points."
    ),
    to: str = typer.Option(
        "all", "--to", help="Render target: all, or a comma list of html, pdf, epub."
    ),
) -> None:
    """Render the book and run post-build audits."""
    _render_one(
        to,
        layout=layout,
        keep_logs=keep_logs,
        keep_tex=keep_tex,
        refresh=refresh,
        bottom_clearance=bottom_clearance,
    )


@app.command()
def build(
    html: bool = typer.Option(False, "--html", help="Build the HTML site."),
    pdf: bool = typer.Option(False, "--pdf", help="Build the PDF."),
    epub: bool = typer.Option(False, "--epub", help="Build the EPUB."),
    all_: bool = typer.Option(False, "--all", help="Build HTML, PDF, and EPUB."),
    layout: bool = typer.Option(
        True, "--layout/--no-layout", help="Scan the rendered PDF for layout issues."
    ),
    keep_logs: bool = typer.Option(
        True, "--keep-logs/--clean-logs", help="Preserve LaTeX logs for audit."
    ),
    keep_tex: bool = typer.Option(
        False,
        "--keep-tex/--no-keep-tex",
        help="Ask Quarto to preserve generated TeX for review.",
    ),
    refresh: bool = typer.Option(
        False,
        "--refresh/--no-refresh",
        help="Re-execute code chunks and ignore Quarto execution caches.",
    ),
    bottom_clearance: float = typer.Option(
        72.0, help="Bottom margin warning threshold in PDF points."
    ),
) -> None:
    """Build selected book formats and run the same post-build audits as render.

    Defaults to HTML + PDF + EPUB when no format flag is given, matching the
    artifact set required by ``arch2 check standard``. Multiple formats render
    in a single Quarto pass, so they never clobber each other's output:

      arch2 build                # HTML + PDF + EPUB
      arch2 build --html --pdf   # HTML + PDF (explicit)
      arch2 build --pdf          # PDF only
      arch2 build --all          # HTML + PDF + EPUB
    """
    if all_ or not any((html, pdf, epub)) or (html and pdf and epub):
        to = "all"
    else:
        chosen = [t for t, on in (("html", html), ("pdf", pdf), ("epub", epub)) if on]
        to = ",".join(chosen)
    shown = list(_RENDER_FORMATS) if to == "all" else to.split(",")
    console.print(f"[cyan]build[/cyan] targets: {', '.join(shown)}")
    _render_one(
        to,
        layout=layout,
        keep_logs=keep_logs,
        keep_tex=keep_tex,
        refresh=refresh,
        bottom_clearance=bottom_clearance,
    )


@app.command()
def preview(
    chapter: str = typer.Argument(
        ..., help="Chapter name (e.g. 01-moonshot) or path to preview."
    ),
    html: bool = typer.Option(False, "--html", help="Build HTML."),
    pdf: bool = typer.Option(False, "--pdf", help="Build PDF."),
    epub: bool = typer.Option(False, "--epub", help="Build EPUB."),
) -> None:
    """Render a single chapter for quick preview by commenting out others in _quarto.yml."""
    if not any([html, pdf, epub]):
        html = True  # Default to HTML preview if no format specified

    path = Path(chapter)
    if not path.exists():
        candidates = [
            BOOK_DIR / "contents" / "chapters" / chapter,
            BOOK_DIR / "contents" / "frontmatter" / chapter,
            BOOK_DIR / "contents" / "backmatter" / chapter,
            BOOK_DIR / "contents" / "parts" / chapter,
            BOOK_DIR / chapter,
        ]
        found = False
        for c in candidates:
            if c.is_dir():
                qmds = sorted(c.glob("*.qmd"))
                if qmds:
                    path = qmds[0]
                    found = True
                    break
            elif c.is_file() and c.suffix == ".qmd":
                path = c
                found = True
                break
            elif c.with_suffix(".qmd").is_file():
                path = c.with_suffix(".qmd")
                found = True
                break

        if not found:
            for c_dir in sorted(
                (BOOK_DIR / "contents" / "chapters").glob(f"*{chapter}*")
            ):
                if c_dir.is_dir():
                    qmds = sorted(c_dir.glob("*.qmd"))
                    if qmds:
                        path = qmds[0]
                        found = True
                        break

        if not found:
            console.print(f"[red]Could not find chapter or file:[/red] {chapter}")
            raise typer.Exit(1)

    _render_book_navbar()
    _prepare_figures()

    chosen = [t for t, on in (("html", html), ("pdf", pdf), ("epub", epub)) if on]
    if len(chosen) > 1:
        console.print(
            "[yellow]Warning: Quarto preview only supports one format at a time well. Using the first one.[/yellow]"
        )

    fmt = chosen[0]

    quarto_yml = BOOK_DIR / "_quarto.yml"
    backup_yml = BOOK_DIR / "_quarto.yml.bak"

    if not quarto_yml.exists():
        console.print("[red]Could not find _quarto.yml[/red]")
        raise typer.Exit(1)

    try:
        target_rel = path.resolve().relative_to(BOOK_DIR.resolve()).as_posix()
    except ValueError:
        target_rel = f"chapters/{path.parent.name}/{path.name}"

    try:
        import shutil
        import re

        shutil.copy2(quarto_yml, backup_yml)

        with open(quarto_yml, "r") as f:
            content = f.read()

        # Replace chapters section
        # Finds '  chapters:\n' up to '\n  appendices:'
        chapters_replacement = f"\n  chapters:\n    - index.qmd\n    - {target_rel}"
        content = re.sub(
            r"\n\s*chapters:\n(?:.*?)(?=\n\s*appendices:)",
            chapters_replacement,
            content,
            flags=re.DOTALL,
        )

        # Replace appendices section
        # Finds '\n  appendices:' up to '\nwebsite:'
        appendices_replacement = "\n  appendices: []"
        content = re.sub(
            r"\n\s*appendices:\n(?:.*?)(?=\nwebsite:)",
            appendices_replacement,
            content,
            flags=re.DOTALL,
        )

        with open(quarto_yml, "w") as f:
            f.write(content)

        render_cmd = ["quarto", "render", str(BOOK_DIR), "--to", fmt]
        console.print(f"[cyan]preview[/cyan] rendering {target_rel} to {fmt}...")
        _run(render_cmd, cwd=ROOT)
        console.print(f"[green]Done.[/green]")

        # Determine the generated file and open it
        if fmt == "pdf":
            out_file = BUILD_DIR / "Architecture-2.0.pdf"
        elif fmt == "html":
            out_file = BUILD_DIR / "index.html"
        elif fmt == "epub":
            out_file = BUILD_DIR / "Architecture-2.0.epub"
        else:
            out_file = None

        if out_file and out_file.exists():
            console.print(f"[cyan]Opening {out_file.name}...[/cyan]")
            import subprocess

            subprocess.run(["open", str(out_file)])

    finally:
        if backup_yml.exists():
            import shutil

            shutil.move(backup_yml, quarto_yml)


@app.command()
def clean(
    scratch_only: bool = typer.Option(
        False, "--scratch-only", help="Only remove LaTeX scratch files; keep _build."
    ),
) -> None:
    """Remove build outputs (_build/) and stray LaTeX scratch files."""
    removed = 0
    for pattern in _LATEX_SCRATCH_PATTERNS:
        for path in BOOK_DIR.glob(pattern):
            if path.is_file():
                path.unlink()
                removed += 1
    if not scratch_only and BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
        console.print(
            f"[green]cleaned[/green] {_relative(BUILD_DIR)} and {removed} LaTeX scratch file(s)"
        )
    else:
        console.print(f"[green]cleaned[/green] {removed} LaTeX scratch file(s)")


@app.command()
def serve(
    port: int = typer.Option(8766, "--port", "-p", help="Port to serve on."),
    prebuild: bool = typer.Option(
        True, "--build/--no-build", help="Build the HTML site before serving."
    ),
) -> None:
    """Build the HTML site (unless --no-build) and serve it locally."""
    if prebuild:
        _render_one(
            "html",
            layout=False,
            keep_logs=True,
            keep_tex=False,
            refresh=False,
            bottom_clearance=72.0,
        )
    if not HTML_PATH.exists():
        console.print(
            "[red]no HTML build found[/red] run 'arch2 build --html' first, or drop --no-build"
        )
        raise typer.Exit(1)
    console.print(
        f"[cyan]serving[/cyan] {_relative(BUILD_DIR)} at http://127.0.0.1:{port}/  (Ctrl-C to stop)"
    )
    _run(
        [
            "python3",
            "-m",
            "http.server",
            str(port),
            "--bind",
            "127.0.0.1",
            "--directory",
            str(BUILD_DIR),
        ]
    )


@validate_app.command("refs")
@validate_app.command("references")
def validate_refs() -> None:
    """Check figure, table, listing, equation, section, and path references."""
    run_refs_check()


@validate_app.command("captions")
def validate_captions() -> None:
    """Check figure captions against the 3-layer pedagogical standard."""
    run_caption_check()


@validate_app.command("card")
def validate_card(
    card: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="YAML or JSON design-loop card to validate.",
    ),
) -> None:
    """Validate a versioned design-loop card and its declared profiles."""
    run_card_check(card)


@migrate_app.command("card")
def migrate_card(
    source: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Version 1.1 YAML or JSON design-loop card.",
    ),
    output: Path
    | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Migration-draft path; defaults beside the source card.",
    ),
) -> None:
    """Map v1.1 fields to a non-inventive v2 migration draft."""
    try:
        if source.suffix.lower() == ".json":
            document = json.loads(source.read_text(encoding="utf-8"))
        elif source.suffix.lower() in {".yaml", ".yml"}:
            import yaml

            document = yaml.safe_load(source.read_text(encoding="utf-8"))
        else:
            raise ValueError("source card must use a .yaml, .yml, or .json extension")
        if not isinstance(document, dict):
            raise ValueError("source card must contain a mapping/object")
        draft = migrate_v1_1_to_v2_draft(document)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        console.print(f"[red]failed[/red] migration: {exc}")
        raise typer.Exit(1) from exc

    target = output or source.with_name(f"{source.stem}.v2-migration-draft.yaml")
    target = target.expanduser().resolve()
    if target.exists():
        console.print(f"[red]failed[/red] migration: output already exists: {target}")
        raise typer.Exit(1)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        import yaml

        target.write_text(
            yaml.safe_dump(draft, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    except OSError as exc:
        console.print(f"[red]failed[/red] migration: {exc}")
        raise typer.Exit(1) from exc
    console.print(
        "[yellow]migration draft requires author input[/yellow] "
        f"({len(draft['missing_semantics'])} missing semantics): {target}"
    )


@validate_app.command("manifest")
def validate_manifest() -> None:
    """Check that the Quarto book manifest owns every intended QMD file."""
    run_manifest_check()


@validate_app.command("footnotes")
def validate_footnotes() -> None:
    """Check footnote placement, identifiers, and defined-term source form."""
    run_footnote_check()


@validate_app.command("prose")
def validate_prose() -> None:
    """Check mechanical prose-style rules: stripped vocabulary and em-dashes."""
    run_prose_style_check()


@verify_app.command("figures")
def verify_figures(
    pdf: Path = typer.Option(PDF_PATH, "--pdf", help="Rendered PDF to inspect."),
) -> None:
    """Check that authored figures are embedded in the rendered PDF."""
    run_figures_check(pdf)


@verify_app.command("html")
def verify_html(
    html: Path = typer.Option(
        HTML_PATH, "--html", help="Rendered HTML index to inspect."
    ),
) -> None:
    """Check that the local HTML site carries release and download metadata."""
    run_html_check(html)


@verify_app.command("epub")
def verify_epub(
    epub: Path = typer.Option(
        EPUB_PATH, "--epub", help="Rendered EPUB package to inspect."
    ),
) -> None:
    """Check EPUB structure, metadata, custom callouts, references, and conformance."""
    _exit_on_findings(epub_findings(epub), title="EPUB package")
    _exit_on_findings(epub_unresolved_findings(epub), title="EPUB rendered references")
    run_epubcheck(epub)


@verify_app.command("unresolved")
def verify_unresolved() -> None:
    """Check rendered PDF, HTML, and EPUB for unresolved ref/citation tokens."""
    run_rendered_unresolved_check()


@verify_app.command("generated-assets")
def verify_generated_assets() -> None:
    """Check that tracked generated figure assets are clean after rendering."""
    run_generated_asset_check()


@validate_app.command("svg")
def validate_svg(
    paths: list[Path]
    | None = typer.Argument(None, help="SVG files or directories to check."),
) -> None:
    """Check SVG text fit across conceptual figures."""
    run_svg_check(paths)


@validate_app.command("citations")
def validate_citations(
    show_context: bool = typer.Option(
        False, help="Show every repeated citation occurrence."
    ),
) -> None:
    """Report repeated citation keys for editorial classification."""
    run_citation_check(show_context=show_context)


@validate_app.command("bibliography")
def validate_bibliography() -> None:
    """Check bibliography style configuration, BibTeX hygiene, and citekey resolution."""
    run_bibliography_check()


@validate_app.command("concepts")
def validate_concepts() -> None:
    """Check duplicate definitions and weakly synthesized loop concepts."""
    run_concept_check()


@validate_app.command("disclosure")
def validate_disclosure() -> None:
    """Check that load-bearing concepts are defined before unmarked reuse."""
    run_disclosure_check()


@validate_app.command("python")
def validate_python() -> None:
    """Check Python helper scripts for syntax errors."""
    run_python_check()


@validate_app.command("book-navbar")
def validate_book_navbar() -> None:
    """Check that the book navbar include matches the shared navbar metadata."""
    run_book_navbar_check()


@validate_app.command("registries")
def validate_registries() -> None:
    """Check registry schemas, generated indexes, status, and AWESOME mirror."""
    run_registry_check()


def apply_line_edits(line: str, edits: list[tuple[str, str]]) -> str:
    """Apply several span replacements to one line without re-matching output.

    Two SI-unit violations can share a line, and a naive repeated ``replace``
    would rewrite the first span twice when the spans are identical. Walking a
    cursor left to right consumes each span exactly once and never inspects
    text a previous replacement produced.

    Edits are sorted by position first. Findings reach here grouped by the rule
    that raised them rather than in document order, so a footnote repair late
    in the line can otherwise arrive before an SI-unit repair early in it and
    strand the cursor past its target.
    """
    cursor = 0
    pieces: list[str] = []
    for span, replacement in sorted(edits, key=lambda edit: line.find(edit[0])):
        index = line.find(span, cursor)
        if index < 0:
            raise ValueError(f"span {span!r} not found at or after column {cursor}")
        pieces.append(line[cursor:index])
        pieces.append(replacement)
        cursor = index + len(span)
    pieces.append(line[cursor:])
    return "".join(pieces)


def apply_fixable_findings(findings: Iterable[Finding]) -> tuple[int, list[str]]:
    """Rewrite every finding that names a deterministic edit.

    Files are read and written once each, and each line's edits are applied
    together, so line offsets never shift under a pending repair.
    """
    by_file: dict[str, dict[int, list[tuple[str, str]]]] = {}
    log: list[str] = []
    for finding in findings:
        if not finding.fixable:
            continue
        record = finding.as_record()
        if "path" not in record:
            continue
        by_file.setdefault(record["path"], {}).setdefault(record["line"], []).append(
            (finding.span, finding.replacement)
        )
        log.append(
            f"{record['path']}:{record['line']}  {finding.code}  "
            f"{finding.span!r} -> {finding.replacement!r}"
        )

    applied = 0
    for relative, per_line in by_file.items():
        path = ROOT / relative
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        for line_no, edits in sorted(per_line.items()):
            index = line_no - 1
            ending = ""
            body = lines[index]
            while body.endswith(("\n", "\r")):
                ending = body[-1] + ending
                body = body[:-1]
            lines[index] = apply_line_edits(body, edits) + ending
            applied += len(edits)
        path.write_text("".join(lines), encoding="utf-8")
    return applied, log


@app.command("fix")
def fix_command(
    apply: bool = typer.Option(
        False, "--apply", help="Write the repairs. Without it, only report them."
    ),
    code: list[str]
    | None = typer.Option(None, "--code", help="Limit to these rule codes."),
) -> None:
    """Apply the source repairs that the checks can name exactly.

    Only findings carrying both a span and a replacement are touched. Anything
    needing an authorial decision is reported and left alone.
    """
    findings = _filter_suppressed(source_repairable_findings())
    if code:
        findings = [finding for finding in findings if finding.code in set(code)]
    fixable = [finding for finding in findings if finding.fixable]
    skipped = len(findings) - len(fixable)

    if not fixable:
        console.print(f"[green]nothing to fix[/green] ({skipped} need a decision)")
        return
    if not apply:
        _emit_findings(fixable, title="repairable findings (dry run)")
        console.print(
            f"[yellow]dry run[/yellow] {len(fixable)} repairable, {skipped} need a "
            "decision; rerun with --apply"
        )
        return

    applied, log = apply_fixable_findings(fixable)
    for entry in log:
        console.print(f"[green]fixed[/green] {entry}")
    console.print(f"[green]applied[/green] {applied} repair(s); {skipped} left alone")


def source_repairable_findings() -> list[Finding]:
    """Collect source-level findings from every no-render gate."""
    findings: list[Finding] = []
    for path in content_qmd_files():
        findings.extend(footnote_punctuation_findings(path))
    findings.extend(prose_style_findings())
    findings.extend(abbreviations_findings())
    findings.extend(glossary_findings())
    return findings


@generate_app.command("glossary")
def generate_glossary() -> None:
    """Generate the canonical Glossary appendix and Lua filter from CMOS_ABBREVIATIONS."""
    run_glossary_generation()


@check_app.command("abbreviations")
def check_abbreviations() -> None:
    """Check abbreviations and acronyms against CMOS first-use disclosure standards."""
    run_abbreviations_check()


@check_app.command("acronyms", hidden=True)
def check_acronyms() -> None:
    """Alias for check abbreviations."""
    run_abbreviations_check()


@check_app.command("glossary")
def check_glossary() -> None:
    """Check that Glossary appendix and Lua filter match CMOS_ABBREVIATIONS without drift."""
    run_glossary_check()


@check_app.command("precommit")
def check_precommit() -> None:
    """Run fast, no-render checks suitable for pre-commit."""
    run_python_check()
    run_book_navbar_check()
    run_registry_check()
    run_manifest_check()
    run_refs_check()
    run_bibliography_check()
    run_footnote_check()
    run_prose_style_check()
    run_caption_check()
    run_abbreviations_check()
    run_glossary_check()
    run_concept_check()
    run_disclosure_check()
    run_citation_check(show_context=False)


@check_app.command("standard")
def check_standard(
    fail_on_layout_warning: bool = typer.Option(
        False, help="Treat layout warnings as failures."
    ),
) -> None:
    """Run the standard rendered-manuscript gate."""
    run_refs_check()
    run_bibliography_check()
    run_footnote_check()
    run_prose_style_check()
    run_caption_check()
    run_abbreviations_check()
    run_glossary_check()
    run_figures_check()
    run_rendered_unresolved_check()
    run_generated_asset_check()
    run_citation_check(show_context=False)
    _exit_on_findings(epub_findings(EPUB_PATH), title="EPUB package")
    run_epubcheck(EPUB_PATH)
    run_layout_check(fail_on_warning=fail_on_layout_warning)


@check_app.command("strict")
def check_strict(
    fail_on_layout_warning: bool = typer.Option(
        False, help="Treat layout warnings as failures."
    ),
) -> None:
    """Run the standard gate plus strict SVG text-fit checks."""
    run_refs_check()
    run_bibliography_check()
    run_footnote_check()
    run_prose_style_check()
    run_caption_check()
    run_abbreviations_check()
    run_glossary_check()
    run_figures_check()
    run_rendered_unresolved_check()
    run_generated_asset_check()
    run_citation_check(show_context=False)
    _exit_on_findings(epub_findings(EPUB_PATH), title="EPUB package")
    run_epubcheck(EPUB_PATH)
    run_svg_check()
    run_layout_check(fail_on_warning=fail_on_layout_warning)


@check_app.command("layout", hidden=True)
def check_layout(
    bottom_clearance: float = typer.Option(
        72.0, help="Bottom margin warning threshold in PDF points."
    ),
    fail_on_warning: bool = typer.Option(
        False, help="Treat bottom-crowding warnings as failures."
    ),
) -> None:
    """Scan rendered PDF geometry and LaTeX overflow logs."""
    run_layout_check(bottom_clearance=bottom_clearance, fail_on_warning=fail_on_warning)


@check_app.command("all", hidden=True)
def check_all(
    include_svg: bool = typer.Option(
        False, "--include-svg/--skip-svg", help="Include full SVG text-fit backlog."
    ),
    fail_on_layout_warning: bool = typer.Option(
        False, help="Treat layout warnings as failures."
    ),
) -> None:
    """Compatibility alias for check standard/strict."""
    run_refs_check()
    run_footnote_check()
    run_figures_check()
    run_citation_check(show_context=False)
    _exit_on_findings(epub_findings(EPUB_PATH), title="EPUB package")
    run_epubcheck(EPUB_PATH)
    if include_svg:
        run_svg_check()
    run_layout_check(fail_on_warning=fail_on_layout_warning)


@layout_app.command("scan")
def layout_scan(
    pdf: Path = typer.Argument(PDF_PATH, help="PDF to scan."),
    bottom_clearance: float = typer.Option(
        72.0, help="Bottom margin warning threshold in PDF points."
    ),
    json_out: Path
    | None = typer.Option(None, "--json", help="Write findings to JSON."),
    fail_on_warning: bool = typer.Option(False, help="Treat warnings as failures."),
) -> None:
    """Scan PDF page geometry and preserved LaTeX logs."""
    findings = layout_findings(pdf, bottom_clearance=bottom_clearance)
    _emit_findings(findings, title="layout audit")
    if json_out:
        json_out.write_text(
            json.dumps([asdict(f) for f in findings], indent=2), encoding="utf-8"
        )
        console.print(f"[dim]wrote {_relative(json_out)}[/dim]")
    if any(
        f.severity == "error" or (fail_on_warning and f.severity == "warning")
        for f in findings
    ):
        raise typer.Exit(1)


@layout_app.command("doctor")
def layout_doctor(
    pdf: Path = typer.Argument(PDF_PATH, help="PDF to inspect."),
    bottom_clearance: float = typer.Option(
        72.0, help="Bottom margin warning threshold in PDF points."
    ),
    sparse_clearance: float = typer.Option(
        DEFAULT_SPARSE_CLEARANCE,
        help="Advisory threshold for unused body space before the footer.",
    ),
    min_body_words: int = typer.Option(
        DEFAULT_SPARSE_MIN_BODY_WORDS,
        help="Minimum body words before sparse-page whitespace becomes actionable.",
    ),
    max_items: int = typer.Option(80, help="Maximum repair items to emit."),
    json_out: Path
    | None = typer.Option(None, "--json", help="Write an LLM-ready JSON packet."),
    markdown_out: Path
    | None = typer.Option(
        None, "--markdown", "--md", help="Write an LLM-ready Markdown packet."
    ),
    print_markdown: bool = typer.Option(
        False, help="Print the Markdown repair packet to stdout."
    ),
    fail_on_error: bool = typer.Option(
        False, help="Exit nonzero when the packet contains an error item."
    ),
) -> None:
    """Create an LLM-ready repair packet for visual PDF layout polish."""
    if not pdf.exists():
        console.print(f"[red]missing PDF[/red] {_relative(pdf)}")
        raise typer.Exit(1)
    if sparse_clearance <= 0 or bottom_clearance <= 0 or min_body_words < 0:
        console.print("[red]invalid layout doctor thresholds[/red]")
        raise typer.Exit(2)

    packet = layout_repair_packet(
        pdf,
        bottom_clearance=bottom_clearance,
        sparse_clearance=sparse_clearance,
        min_body_words=min_body_words,
        max_items=max_items,
    )
    items = [LayoutRepairItem(**item) for item in packet["items"]]
    _emit_layout_repair_items(items)
    markdown = render_layout_repair_markdown(packet)
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(packet, indent=2), encoding="utf-8")
        console.print(f"[dim]wrote {_relative(json_out)}[/dim]")
    if markdown_out:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(markdown, encoding="utf-8")
        console.print(f"[dim]wrote {_relative(markdown_out)}[/dim]")
    if print_markdown:
        console.print(markdown)
    if fail_on_error and any(item.severity == "error" for item in items):
        raise typer.Exit(1)


@layout_app.command("contact-sheet")
def layout_contact_sheet(
    kind: str = typer.Argument(
        "figures", help="Rendered pages to collect: figures or tables."
    ),
    pdf: Path = typer.Option(PDF_PATH, "--pdf", help="Rendered PDF to inspect."),
    output: Path
    | None = typer.Option(None, "--output", "-o", help="PNG contact-sheet path."),
    dpi: int = typer.Option(90, help="PDF rasterization DPI for thumbnails."),
    columns: int = typer.Option(4, help="Number of columns in the contact sheet."),
    thumbnail_width: int = typer.Option(255, help="Thumbnail width in pixels."),
    include_references: bool = typer.Option(
        False,
        "--include-references/--captions-only",
        help="Include pages that mention figures/tables outside captions.",
    ),
) -> None:
    """Render a figure/table page contact sheet for visual manuscript QA."""
    normalized = kind.lower()
    if normalized not in {"figures", "tables"}:
        console.print(
            "[red]invalid contact-sheet kind[/red] use one of: figures, tables"
        )
        raise typer.Exit(2)
    if not pdf.exists():
        console.print(f"[red]missing PDF[/red] {_relative(pdf)}")
        raise typer.Exit(1)
    if columns < 1 or thumbnail_width < 80 or dpi < 30:
        console.print("[red]invalid contact-sheet geometry[/red]")
        raise typer.Exit(2)

    try:
        from PIL import Image, ImageDraw, ImageFont
        from pypdf import PdfReader
    except ImportError as exc:
        console.print(f"[red]missing dependency[/red] {exc.name}")
        console.print("Install Pillow and pypdf, then rerun the command.")
        raise typer.Exit(1)

    logging.getLogger("pypdf").setLevel(logging.ERROR)

    noun = "Figure" if normalized == "figures" else "Table"
    number_pattern = rf"[A-Z]?\d+(?:\.\d+)?"
    page_pattern = (
        re.compile(rf"{noun}\s*{number_pattern}")
        if include_references
        else re.compile(rf"{noun}\s*{number_pattern}(?=\s*:)")
    )
    stem = "figure" if normalized == "figures" else "table"
    out_dir = ROOT / "tmp" / "pdfs" / f"{stem}-audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    sheet_path = output or (out_dir / f"{stem}-contact-sheet.png")
    if not sheet_path.is_absolute():
        sheet_path = ROOT / sheet_path
    sheet_path.parent.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(pdf))
    pages: list[tuple[int, list[str]]] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        matches = sorted(
            {
                re.sub(rf"^{noun}\s*", f"{noun} ", match)
                for match in page_pattern.findall(text)
            }
        )
        if matches:
            pages.append((page_number, matches))

    if not pages:
        mode = "references" if include_references else "captions"
        console.print(f"[yellow]no {noun.lower()} {mode} found[/yellow]")
        raise typer.Exit(1)

    page_list = out_dir / f"{stem}-pages.txt"
    page_list.write_text(
        "\n".join(f"{page}: {', '.join(matches)}" for page, matches in pages) + "\n",
        encoding="utf-8",
    )

    tiles = []
    font = ImageFont.load_default()
    label_height = 38
    for page_number, matches in pages:
        prefix = out_dir / f"page-{page_number:03d}"
        for old_png in out_dir.glob(f"page-{page_number:03d}-*.png"):
            old_png.unlink()
        proc = _run(
            [
                "pdftoppm",
                "-png",
                "-r",
                str(dpi),
                "-f",
                str(page_number),
                "-l",
                str(page_number),
                str(pdf),
                str(prefix),
            ],
            capture=True,
        )
        if proc.returncode != 0:
            console.print(f"[red]failed[/red] render PDF page {page_number}")
            if proc.stdout:
                console.print(proc.stdout)
            if proc.stderr:
                console.print(proc.stderr)
            raise typer.Exit(proc.returncode)
        rendered = sorted(out_dir.glob(f"page-{page_number:03d}-*.png"))
        if not rendered:
            console.print(f"[red]missing rendered page[/red] {page_number}")
            raise typer.Exit(1)

        image = Image.open(rendered[-1]).convert("RGB")
        ratio = thumbnail_width / image.width
        thumbnail_height = int(image.height * ratio)
        image = image.resize(
            (thumbnail_width, thumbnail_height), Image.Resampling.LANCZOS
        )
        tile = Image.new(
            "RGB", (thumbnail_width, thumbnail_height + label_height), "white"
        )
        tile.paste(image, (0, label_height))
        draw = ImageDraw.Draw(tile)
        draw.rectangle(
            [0, 0, thumbnail_width - 1, label_height - 1],
            fill=(246, 247, 244),
            outline=(190, 198, 204),
        )
        label = f"PDF p.{page_number}: {', '.join(matches)}"
        draw.text((6, 8), label[:64], fill=(20, 35, 45), font=font)
        tiles.append(tile)

    padding = 14
    rows = (len(tiles) + columns - 1) // columns
    max_tile_height = max(tile.height for tile in tiles)
    sheet = Image.new(
        "RGB",
        (
            columns * thumbnail_width + (columns + 1) * padding,
            rows * max_tile_height + (rows + 1) * padding,
        ),
        (232, 236, 238),
    )
    for index, tile in enumerate(tiles):
        row, column = divmod(index, columns)
        x = padding + column * (thumbnail_width + padding)
        y = padding + row * (max_tile_height + padding)
        sheet.paste(tile, (x, y))

    sheet.save(sheet_path)
    console.print(f"[green]wrote[/green] {_relative(sheet_path)}")
    console.print(f"[dim]pages: {len(pages)}; list: {_relative(page_list)}[/dim]")


@review_app.command("open")
def review_open(
    port: int = typer.Option(8765, help="Local review server port."),
    no_browser: bool = typer.Option(
        False, help="Do not open the browser automatically."
    ),
    tex: Path
    | None = typer.Option(None, "--tex", help="Generated TeX file to anchor comments."),
    pdf: Path = typer.Option(PDF_PATH, "--pdf", help="Rendered PDF to review."),
    workbench: Path
    | None = typer.Option(
        None,
        "--workbench",
        help="Review-bench engine path. Defaults to ARCH2_REVIEW_WORKBENCH or the local PaperReviewWorkbench checkout.",
    ),
) -> None:
    """Open the Arch2 review bench for PDF-plus-source commenting."""
    workbench_path = workbench or Path(
        os.environ.get("ARCH2_REVIEW_WORKBENCH", str(DEFAULT_REVIEW_WORKBENCH))
    )
    if not workbench_path.exists():
        console.print(f"[red]missing review bench engine[/red] {workbench_path}")
        raise typer.Exit(1)

    tex_path = tex or generated_tex()
    if tex_path is None or not tex_path.exists():
        console.print("[red]missing generated TeX[/red]")
        console.print(
            "Run [cyan]./arch2 render --keep-tex[/cyan] first, then retry [cyan]./arch2 review open[/cyan]."
        )
        raise typer.Exit(1)
    if not pdf.exists():
        console.print(f"[red]missing PDF[/red] {_relative(pdf)}")
        raise typer.Exit(1)

    env = {"PYTHONPATH": str(workbench_path)}
    cmd = [
        sys.executable,
        "-m",
        "paper_review_workbench",
        "open",
        str(BOOK_DIR),
        "--tex",
        str(tex_path),
        "--pdf",
        str(pdf),
        "--port",
        str(port),
    ]
    if no_browser:
        cmd.append("--no-browser")
    console.print(f"[cyan]Arch2 review bench[/cyan] http://127.0.0.1:{port}")
    console.print(f"[dim]engine: {workbench_path}[/dim]")
    console.print(
        f"[dim]comments: {_relative(BOOK_DIR / '.paper-review' / 'comments.json')}[/dim]"
    )
    proc = _run(cmd, cwd=ROOT, env=env, capture=False)
    raise typer.Exit(proc.returncode)


@loop_app.command("packet")
def loop_packet(
    scope: str = typer.Option(
        "book", "--scope", help="Review scope label, such as book or a chapter slug."
    ),
    focus: str = typer.Option(
        "progressive-disclosure",
        "--focus",
        help="Primary review focus for the packet.",
    ),
    out_dir: Path
    | None = typer.Option(None, "--out-dir", help="Private loop artifact directory."),
) -> None:
    """Generate a manuscript packet for an improvement loop."""
    body = build_loop_packet(scope=scope, focus=focus)
    path = _write_loop_artifact("packet", body, out_dir=out_dir)
    console.print(f"[green]wrote[/green] {_relative(path)}")
    console.print(
        f"[dim]latest: {_relative(_loop_output_dir(out_dir) / 'packet-latest.md')}[/dim]"
    )


@loop_app.command("review")
def loop_review(
    packet: Path
    | None = typer.Option(
        None, "--packet", help="Loop packet to review. Defaults to packet-latest.md."
    ),
    reviewer: str = typer.Option(
        "gemini", "--reviewer", help="Reviewer backend: gemini, claude, or none."
    ),
    model: str = typer.Option(
        DEFAULT_GEMINI_MODEL, "--model", help="Model name for Gemini review."
    ),
    timeout: str = typer.Option(
        "15m", "--timeout", help="External reviewer timeout, e.g. 15m."
    ),
    out_dir: Path
    | None = typer.Option(None, "--out-dir", help="Private loop artifact directory."),
) -> None:
    """Run an external or skipped review against a loop packet."""
    packet_path = packet or _latest_loop_artifact("packet", out_dir=out_dir)
    if not packet_path.is_absolute():
        packet_path = ROOT / packet_path
    if not packet_path.exists():
        console.print(f"[red]missing packet[/red] {_relative(packet_path)}")
        raise typer.Exit(1)

    try:
        review_text = run_loop_review(
            packet_path, reviewer=reviewer, model=model, timeout=timeout
        )
    except RuntimeError as exc:
        console.print(f"[red]review failed[/red] {exc}")
        raise typer.Exit(1) from exc

    header = "\n".join(
        [
            "# Arch2 Loop Review",
            "",
            f"- Generated: {_timestamp()}",
            f"- Reviewer: `{reviewer}`",
            f"- Model: `{model if reviewer.lower() == 'gemini' else reviewer}`",
            f"- Packet: `{_relative(packet_path)}`",
            "",
        ]
    )
    path = _write_loop_artifact("review", header + review_text, out_dir=out_dir)
    console.print(f"[green]wrote[/green] {_relative(path)}")
    console.print(
        f"[dim]latest: {_relative(_loop_output_dir(out_dir) / 'review-latest.md')}[/dim]"
    )


@loop_app.command("triage")
def loop_triage(
    review: Path
    | None = typer.Option(
        None, "--review", help="Loop review to triage. Defaults to review-latest.md."
    ),
    out_dir: Path
    | None = typer.Option(None, "--out-dir", help="Private loop artifact directory."),
) -> None:
    """Classify review feedback into fix, decision, rule, check, and defer buckets."""
    review_path = review or _latest_loop_artifact("review", out_dir=out_dir)
    if not review_path.is_absolute():
        review_path = ROOT / review_path
    if not review_path.exists():
        console.print(f"[red]missing review[/red] {_relative(review_path)}")
        raise typer.Exit(1)

    body = build_triage(
        review_path.read_text(encoding="utf-8"), review_path=review_path
    )
    path = _write_loop_artifact("triage", body, out_dir=out_dir)
    console.print(f"[green]wrote[/green] {_relative(path)}")
    console.print(
        f"[dim]latest: {_relative(_loop_output_dir(out_dir) / 'triage-latest.md')}[/dim]"
    )


@loop_app.command("learn")
def loop_learn(
    triage: Path
    | None = typer.Option(
        None,
        "--triage",
        help="Loop triage to learn from. Defaults to triage-latest.md.",
    ),
    out_dir: Path
    | None = typer.Option(None, "--out-dir", help="Private loop artifact directory."),
) -> None:
    """Turn a triage pass into rule/check/update candidates for the next loop."""
    triage_path = triage or _latest_loop_artifact("triage", out_dir=out_dir)
    if not triage_path.is_absolute():
        triage_path = ROOT / triage_path
    if not triage_path.exists():
        console.print(f"[red]missing triage[/red] {_relative(triage_path)}")
        raise typer.Exit(1)

    body = build_learning_report(
        triage_path.read_text(encoding="utf-8"), triage_path=triage_path
    )
    path = _write_loop_artifact("learning", body, out_dir=out_dir)
    console.print(f"[green]wrote[/green] {_relative(path)}")
    console.print(
        f"[dim]latest: {_relative(_loop_output_dir(out_dir) / 'learning-latest.md')}[/dim]"
    )


@loop_app.command("run")
def loop_run(
    scope: str = typer.Option(
        "book", "--scope", help="Review scope label, such as book or a chapter slug."
    ),
    focus: str = typer.Option(
        "progressive-disclosure",
        "--focus",
        help="Primary review focus for the loop.",
    ),
    reviewer: str = typer.Option(
        "gemini", "--reviewer", help="Reviewer backend: gemini, claude, or none."
    ),
    model: str = typer.Option(
        DEFAULT_GEMINI_MODEL, "--model", help="Model name for Gemini review."
    ),
    timeout: str = typer.Option(
        "15m", "--timeout", help="External reviewer timeout, e.g. 15m."
    ),
    out_dir: Path
    | None = typer.Option(None, "--out-dir", help="Private loop artifact directory."),
) -> None:
    """Run packet -> review -> triage -> learn as one manuscript-improvement loop."""
    packet_body = build_loop_packet(scope=scope, focus=focus)
    packet_path = _write_loop_artifact("packet", packet_body, out_dir=out_dir)
    console.print(f"[green]packet[/green] {_relative(packet_path)}")

    try:
        review_text = run_loop_review(
            packet_path, reviewer=reviewer, model=model, timeout=timeout
        )
    except RuntimeError as exc:
        console.print(f"[red]review failed[/red] {exc}")
        raise typer.Exit(1) from exc

    review_header = "\n".join(
        [
            "# Arch2 Loop Review",
            "",
            f"- Generated: {_timestamp()}",
            f"- Reviewer: `{reviewer}`",
            f"- Model: `{model if reviewer.lower() == 'gemini' else reviewer}`",
            f"- Packet: `{_relative(packet_path)}`",
            "",
        ]
    )
    review_path = _write_loop_artifact(
        "review", review_header + review_text, out_dir=out_dir
    )
    console.print(f"[green]review[/green] {_relative(review_path)}")

    triage_body = build_triage(
        review_path.read_text(encoding="utf-8"), review_path=review_path
    )
    triage_path = _write_loop_artifact("triage", triage_body, out_dir=out_dir)
    console.print(f"[green]triage[/green] {_relative(triage_path)}")

    learning_body = build_learning_report(triage_body, triage_path=triage_path)
    learning_path = _write_loop_artifact("learning", learning_body, out_dir=out_dir)
    console.print(f"[green]learning[/green] {_relative(learning_path)}")
    console.print(
        "[dim]next: inspect triage/learning, apply one scoped edit, then render/check[/dim]"
    )


@app.command()
def doctor() -> None:
    """Show tool availability for the manuscript build."""
    checks = [
        ("quarto", ["quarto", "--version"]),
        ("epubcheck", ["epubcheck", "--version"]),
        ("rsvg-convert", ["rsvg-convert", "--version"]),
        ("pdftotext", ["pdftotext", "-v"]),
        ("python", [sys.executable, "--version"]),
    ]
    table = Table(title="arch2 doctor")
    table.add_column("Tool")
    table.add_column("Status")
    table.add_column("Detail")
    for name, cmd in checks:
        if shutil.which(cmd[0]) is None:
            table.add_row(name, "missing", "not found on PATH")
            continue
        proc = _run(cmd, capture=True)
        status = "ok" if proc.returncode == 0 else "missing"
        output = (proc.stdout or proc.stderr or "").strip()
        if name == "epubcheck" and not _has_required_epubcheck_version(output):
            status = "wrong version"
        detail = output.splitlines()
        table.add_row(name, status, detail[0] if detail else "")
    table.add_row("PDF", "ok" if PDF_PATH.exists() else "missing", _relative(PDF_PATH))
    console.print(table)


if __name__ == "__main__":
    app(prog_name="arch2")
