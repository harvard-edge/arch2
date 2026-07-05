#!/usr/bin/env python3
"""Arch2 command-line interface for the Architecture 2.0 Synthesis Lecture."""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import typer
from rich.console import Console
from rich.table import Table

ROOT = Path(__file__).resolve().parents[1]
BOOK_DIR = ROOT / "book"
BUILD_DIR = BOOK_DIR / "_build"
PDF_PATH = BUILD_DIR / "Architecture-2.0.pdf"
HTML_PATH = BUILD_DIR / "index.html"
EPUB_PATH = BUILD_DIR / "Architecture-2.0.epub"
LOG_DIR = BUILD_DIR / "logs"
DEFAULT_REVIEW_WORKBENCH = ROOT.parent.parent / "PaperReviewWorkbench"
LOOP_DIR = ROOT / ".arch2" / "reviews" / "loop"
DEFAULT_GEMINI_MODEL = "gemini-3.1-pro-preview"

DEFAULT_LOOP_CONCEPTS = (
    "Architecture 2.0",
    "design loop",
    "design-loop card",
    "feedback budget",
    "fidelity ladder",
    "evidence ledger",
    "rejection authority",
    "negative traces",
    "world model",
    "environment",
    "method role",
    "commitment boundary",
    "lighthouse prompt",
    "ArchOps",
)

DISCLOSURE_GATED_CONCEPTS = (
    "design-loop card",
    "feedback budget",
    "fidelity ladder",
    "evidence ledger",
    "rejection authority",
    "negative traces",
    "world model",
    "method role",
    "commitment boundary",
    "lighthouse prompt",
    "ArchOps",
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
verify_app = typer.Typer(
    help="Verify rendered artifacts against manuscript sources.", no_args_is_help=True
)
layout_app = typer.Typer(
    help="Scan PDF and LaTeX layout signals.", no_args_is_help=True
)
review_app = typer.Typer(
    help="Open the Arch2 local review/commenting bench.", no_args_is_help=True
)
loop_app = typer.Typer(
    help="Run self-improving manuscript review loops.", no_args_is_help=True
)
app.add_typer(check_app, name="check")
app.add_typer(validate_app, name="validate")
app.add_typer(verify_app, name="verify")
app.add_typer(layout_app, name="layout")
app.add_typer(review_app, name="review")
app.add_typer(loop_app, name="loop")


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    location: str
    message: str


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
CONTENT_ROOTS = (BOOK_DIR / "chapters", BOOK_DIR / "appendices")
QUARTO_LABEL_RE = re.compile(
    r"\{#(?P<label>(?:fig|tbl|eq)-[A-Za-z0-9_-]+)(?=[\s}])[^}]*\}"
)
LATEX_LABEL_RE = re.compile(r"\\label\{(?P<label>(?:fig|tab|eq):[A-Za-z0-9:_-]+)\}")
QUARTO_REF_RE = re.compile(r"(?<![#\w])@(?P<label>(?:fig|tbl|eq)-[A-Za-z0-9_-]+)\b")
LATEX_REF_RE = re.compile(
    r"\\(?:auto|[cC]|eq)?ref\{(?P<label>(?:fig|tab|eq):[A-Za-z0-9:_-]+)\}"
)
RAW_STRUCTURE_REF_RE = re.compile(
    r"\b(?:(?:[Cc]hapters?|Ch\.)\s*\d+(?:\s*(?:-|and|,)\s*\d+)*|(?:[Aa]ppendix|[Aa]ppendices)\s+[A-Z])\b"
)
CHAP_LABEL_OR_REF_RE = re.compile(
    r"(?<![\w#])@chap-[A-Za-z0-9_-]+\b|#chap-[A-Za-z0-9_-]+\b"
)
LATEX_SECTION_REF_RE = re.compile(r"\\ref\{sec-[A-Za-z0-9_-]+\}")
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
CHUNK_LABEL_RE = re.compile(r"^\s*#\|\s*label:\s*(?P<label>fig-[A-Za-z0-9_-]+)\s*$")
CHUNK_FIG_ALT_RE = re.compile(r"^\s*#\|\s*fig-alt:\s*(?P<alt>.+?)\s*$")
CHUNK_FIG_POS_RE = re.compile(r"^\s*#\|\s*fig-pos:\s*(?P<pos>.+?)\s*$")
CITE_RE = re.compile(r"(?<![\w@])@(?P<key>[A-Za-z0-9:_-]+)")
DEFINITION_RE = re.compile(
    r"^\s*>\s*\*\*(?P<term>[^*\n.][^*\n]{1,90}?)\.\*\*", re.MULTILINE
)
STYLE_RE = re.compile(r"\.(?P<class>[A-Za-z0-9_-]+)\s*\{(?P<body>[^}]*)\}", re.DOTALL)
FONT_SIZE_RE = re.compile(r"font-size\s*:\s*(?P<size>[0-9.]+)px")
TRANSLATE_RE = re.compile(
    r"translate\(\s*(?P<x>-?[0-9.]+)(?:[,\s]+(?P<y>-?[0-9.]+))?\s*\)"
)
MIN_ARRAYSTRETCH = 1.2
MIN_TABCOLSEP_PT = 2.5
MIN_RECT_PADDING = 4.0
MIN_CIRCLE_PADDING = 8.0
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
    rows = list(findings)
    if not rows:
        console.print(f"[green]passed[/green] {title}")
        return

    table = Table(title=title, show_lines=False)
    table.add_column("Severity", style="bold")
    table.add_column("Code")
    table.add_column("Location")
    table.add_column("Message")
    for finding in rows:
        style = "red" if finding.severity == "error" else "yellow"
        table.add_row(
            f"[{style}]{finding.severity}[/{style}]",
            finding.code,
            finding.location,
            finding.message,
        )
    console.print(table)


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
    _emit_findings(findings, title=title)
    if any(
        finding.severity == "error"
        or (fail_on_warning and finding.severity == "warning")
        for finding in findings
    ):
        raise typer.Exit(1)


def content_qmd_files() -> list[Path]:
    paths: list[Path] = []
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

    ordered: list[Path] = []
    in_book = False
    in_content_section = False
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if re.match(r"^\S", line):
            in_book = line.strip() == "book:"
            in_content_section = False
            continue

        if not in_book:
            continue

        section_match = re.match(r"^  (?P<section>chapters|appendices):\s*$", line)
        if section_match:
            in_content_section = True
            continue
        if re.match(r"^  \S", line):
            in_content_section = False
            continue

        item_match = re.match(r"^    -\s+(?P<path>\S.*?)\s*$", line)
        if not (in_content_section and item_match):
            continue

        candidate = (BOOK_DIR / item_match.group("path")).resolve()
        if candidate in content_paths:
            ordered.append(candidate)

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

    return labels


def collect_refs(paths: list[Path]) -> set[str]:
    refs: set[str] = set()
    for path in paths:
        text = path.read_text(encoding="utf-8")
        refs.update(match.group("label") for match in QUARTO_REF_RE.finditer(text))
        refs.update(match.group("label") for match in LATEX_REF_RE.finditer(text))
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
    return {label}


def unreferenced_label_findings(
    targets: list[Path], all_paths: list[Path]
) -> list[Finding]:
    refs = collect_refs(all_paths)
    findings: list[Finding] = []

    for path in targets:
        for label in collect_labels(path):
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
    message = "use top-level {#sec-*} labels and @sec-* cross-references instead of hard-coded chapter/appendix names"

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
        if RAW_STRUCTURE_REF_RE.search(line):
            findings.append(
                Finding(
                    "error",
                    "raw-structure-reference",
                    f"{_relative(path)}:{line_number_value}",
                    message,
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
    findings.extend(unreferenced_label_findings(all_paths, all_paths))
    for path in all_paths:
        findings.extend(figure_path_findings(path))
        findings.extend(figure_source_findings(path))
        findings.extend(table_findings(path))
        findings.extend(structural_reference_findings(path))
    return sorted(
        findings, key=lambda finding: (finding.location, finding.code, finding.message)
    )


def is_crossref_key(key: str) -> bool:
    return key.startswith(
        ("fig-", "tbl-", "eq-", "sec-", "fig:", "tab:", "eq:", "sec:")
    )


def citation_chapter_name(path: Path) -> str:
    try:
        rel = path.relative_to(BOOK_DIR)
    except ValueError:
        rel = path.relative_to(ROOT)
    parts = rel.parts
    if len(parts) >= 2 and parts[0] in {"chapters", "appendices"}:
        return parts[1]
    return str(rel)


def collect_citation_occurrences(
    paths: list[Path],
) -> dict[str, list[CitationOccurrence]]:
    hits: dict[str, list[CitationOccurrence]] = {}
    for path in paths:
        for line, text in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
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
    if "Work in progress" not in text or "ISCA 2026 Architecture 2.0" not in text:
        findings.append(
            Finding(
                "error",
                "html-preview-banner",
                _relative(html_path),
                "preview HTML is missing the WIP / ISCA 2026 Architecture 2.0 announcement banner",
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

            combined = "\n".join(
                epub.read(name).decode("utf-8", errors="replace")
                for name in html_names
                if not name.endswith("nav.xhtml")
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

    if (
        "callout-learning-objectives" not in combined
    ):
        findings.append(
            Finding(
                "warning",
                "epub-custom-callouts",
                _relative(epub_path),
                "EPUB is missing Arch2 custom callout markup",
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


def svg_text_content(element: ET.Element) -> str:
    return " ".join("".join(element.itertext()).split())


def parse_class_font_sizes(root: ET.Element) -> dict[str, float]:
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


def font_size_for(element: ET.Element, class_sizes: dict[str, float]) -> float:
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
    element: ET.Element,
    inherited: tuple[float, float] = (0.0, 0.0),
) -> Iterable[tuple[ET.Element, tuple[float, float]]]:
    own = parse_translate(element.attrib.get("transform"))
    current = (inherited[0] + own[0], inherited[1] + own[1])
    yield element, current
    for child in element:
        yield from walk_with_translate(child, current)


def collect_svg_shapes(root: ET.Element) -> list[SvgShape]:
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


def collect_svg_labels(
    root: ET.Element, class_sizes: dict[str, float]
) -> list[SvgTextLabel]:
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


def parse_viewbox(root: ET.Element) -> tuple[float, float, float, float] | None:
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


def collect_svg_bounds(
    root: ET.Element, class_sizes: dict[str, float]
) -> list[SvgBounds]:
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
    path: Path, root: ET.Element, class_sizes: dict[str, float]
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


def svg_text_findings_for_file(path: Path) -> list[Finding]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return [
            Finding(
                "error", "svg-parse", _relative(path), f"could not parse SVG: {exc}"
            )
        ]

    class_sizes = parse_class_font_sizes(root)
    shapes = collect_svg_shapes(root)
    labels = collect_svg_labels(root, class_sizes)

    findings: list[Finding] = svg_viewbox_findings(path, root, class_sizes)
    for label in labels:
        shape = containing_svg_shape(label, shapes)
        if shape is None:
            continue
        findings.extend(svg_label_findings(path, label, shape))
    return findings


def svg_paths(inputs: list[Path] | None = None) -> list[Path]:
    candidates = inputs or [ROOT / "assets" / "figures" / "src"]
    paths: list[Path] = []
    for raw_path in candidates:
        path = raw_path if raw_path.is_absolute() else ROOT / raw_path
        if path.is_dir():
            paths.extend(sorted(path.glob("*.svg")))
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


def layout_findings(pdf_path: Path, *, bottom_clearance: float = 72.0) -> list[Finding]:
    findings = scan_latex_logs()
    findings.extend(scan_pdf_geometry(pdf_path, bottom_clearance=bottom_clearance))
    findings.extend(footnote_overflow_findings(pdf_path))
    return findings


def run_layout_check(
    *, bottom_clearance: float = 72.0, fail_on_warning: bool = False
) -> None:
    findings = layout_findings(PDF_PATH, bottom_clearance=bottom_clearance)
    _exit_on_findings(findings, title="layout audit", fail_on_warning=fail_on_warning)


def run_refs_check() -> None:
    _exit_on_findings(manuscript_integrity_findings(), title="references")


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


def run_footnote_table_check() -> None:
    _exit_on_findings(footnote_in_table_findings(), title="footnotes in tables")


def run_html_check(html: Path = HTML_PATH) -> None:
    _exit_on_findings(html_findings(html), title="HTML site")


def run_svg_check(paths: list[Path] | None = None) -> None:
    _exit_on_findings(svg_text_findings(paths), title="SVG text fit")


def run_citation_check(*, show_context: bool = False) -> None:
    _emit_findings(
        citation_reuse_findings(show_context=show_context), title="citation reuse"
    )


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
            if pattern.search(line):
                occurrences.append((path, line_number_, line.strip()))
    return occurrences


def _concept_ledger_markdown(
    paths: list[Path], concepts: tuple[str, ...] = DEFAULT_LOOP_CONCEPTS
) -> str:
    lines = [
        "## Progressive-Disclosure Ledger",
        "",
        "This ledger is mechanical: it shows where load-bearing concepts appear so a reviewer can decide whether each one is previewed, defined, deepened, applied, and synthesized in the right order.",
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
            "## Next Loop Contract",
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
            *ROOT.glob("scripts/*.py"),
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
    console.print(f"[cyan]rendering[/cyan] {' '.join(cmd)}")
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
        run_html_check(HTML_PATH)
    if "epub" in fmts:
        _exit_on_findings(epub_findings(EPUB_PATH), title="EPUB package")
    if "pdf" in fmts:
        run_figures_check(PDF_PATH)
        layout_error = False
        if layout:
            findings = layout_findings(PDF_PATH, bottom_clearance=bottom_clearance)
            _emit_findings(findings, title="layout audit")
            layout_error = any(finding.severity == "error" for finding in findings)
        _clean_latex_scratch(keep_logs)
        if layout_error:
            raise typer.Exit(1)


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

    Defaults to HTML + PDF when no format flag is given. Multiple formats render
    in a single Quarto pass, so they never clobber each other's output:

      arch2 build                # HTML + PDF
      arch2 build --html --pdf   # HTML + PDF (explicit)
      arch2 build --pdf          # PDF only
      arch2 build --all          # HTML + PDF + EPUB
    """
    if all_ or (html and pdf and epub):
        to = "all"
    else:
        chosen = [t for t, on in (("html", html), ("pdf", pdf), ("epub", epub)) if on]
        to = ",".join(chosen) if chosen else "html,pdf"
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
def validate_refs() -> None:
    """Check figure, table, equation, and path references."""
    run_refs_check()


@validate_app.command("footnotes")
def validate_footnotes() -> None:
    """Check that no footnote marker sits inside a table cell (breaks the PDF margin build)."""
    run_footnote_table_check()


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
    """Check that the local HTML site was rendered with the preview banner."""
    run_html_check(html)


@verify_app.command("epub")
def verify_epub(
    epub: Path = typer.Option(
        EPUB_PATH, "--epub", help="Rendered EPUB package to inspect."
    ),
) -> None:
    """Check that the local EPUB package contains custom callouts and resolved references."""
    _exit_on_findings(epub_findings(epub), title="EPUB package")


@validate_app.command("svg")
def validate_svg(
    paths: list[Path] | None = typer.Argument(
        None, help="SVG files or directories to check."
    ),
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


@check_app.command("precommit")
def check_precommit() -> None:
    """Run fast, no-render checks suitable for pre-commit."""
    run_python_check()
    run_refs_check()
    run_footnote_table_check()
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
    run_footnote_table_check()
    run_figures_check()
    run_citation_check(show_context=False)
    _exit_on_findings(epub_findings(EPUB_PATH), title="EPUB package")
    run_layout_check(fail_on_warning=fail_on_layout_warning)


@check_app.command("strict")
def check_strict(
    fail_on_layout_warning: bool = typer.Option(
        False, help="Treat layout warnings as failures."
    ),
) -> None:
    """Run the standard gate plus strict SVG text-fit checks."""
    run_refs_check()
    run_footnote_table_check()
    run_figures_check()
    run_citation_check(show_context=False)
    _exit_on_findings(epub_findings(EPUB_PATH), title="EPUB package")
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
    run_footnote_table_check()
    run_figures_check()
    run_citation_check(show_context=False)
    _exit_on_findings(epub_findings(EPUB_PATH), title="EPUB package")
    if include_svg:
        run_svg_check()
    run_layout_check(fail_on_warning=fail_on_layout_warning)


@layout_app.command("scan")
def layout_scan(
    pdf: Path = typer.Argument(PDF_PATH, help="PDF to scan."),
    bottom_clearance: float = typer.Option(
        72.0, help="Bottom margin warning threshold in PDF points."
    ),
    json_out: Path | None = typer.Option(
        None, "--json", help="Write findings to JSON."
    ),
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


@layout_app.command("contact-sheet")
def layout_contact_sheet(
    kind: str = typer.Argument(
        "figures", help="Rendered pages to collect: figures or tables."
    ),
    pdf: Path = typer.Option(PDF_PATH, "--pdf", help="Rendered PDF to inspect."),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="PNG contact-sheet path."
    ),
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
    tex: Path | None = typer.Option(
        None, "--tex", help="Generated TeX file to anchor comments."
    ),
    pdf: Path = typer.Option(PDF_PATH, "--pdf", help="Rendered PDF to review."),
    workbench: Path | None = typer.Option(
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
    out_dir: Path | None = typer.Option(
        None, "--out-dir", help="Private loop artifact directory."
    ),
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
    packet: Path | None = typer.Option(
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
    out_dir: Path | None = typer.Option(
        None, "--out-dir", help="Private loop artifact directory."
    ),
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
    review: Path | None = typer.Option(
        None, "--review", help="Loop review to triage. Defaults to review-latest.md."
    ),
    out_dir: Path | None = typer.Option(
        None, "--out-dir", help="Private loop artifact directory."
    ),
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
    triage: Path | None = typer.Option(
        None,
        "--triage",
        help="Loop triage to learn from. Defaults to triage-latest.md.",
    ),
    out_dir: Path | None = typer.Option(
        None, "--out-dir", help="Private loop artifact directory."
    ),
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
    out_dir: Path | None = typer.Option(
        None, "--out-dir", help="Private loop artifact directory."
    ),
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
        ("rsvg-convert", ["rsvg-convert", "--version"]),
        ("pdftotext", ["pdftotext", "-v"]),
        ("python", [sys.executable, "--version"]),
    ]
    table = Table(title="arch2 doctor")
    table.add_column("Tool")
    table.add_column("Status")
    table.add_column("Detail")
    for name, cmd in checks:
        proc = _run(cmd, capture=True)
        status = "ok" if proc.returncode == 0 else "missing"
        detail = (proc.stdout or proc.stderr or "").strip().splitlines()
        table.add_row(name, status, detail[0] if detail else "")
    table.add_row("PDF", "ok" if PDF_PATH.exists() else "missing", _relative(PDF_PATH))
    console.print(table)


if __name__ == "__main__":
    app(prog_name="arch2")
