#!/usr/bin/env python3
"""Developmental Editor for Architecture 2.0.

Provides section-by-section developmental analysis, guided walkthroughs,
and editing packets grounded in the book-wide intellectual roadmap.
"""

from __future__ import annotations

import difflib
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

try:
    import typer
    from rich import box
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.table import Table
    from rich.theme import Theme
except ImportError:
    print(
        "Error: Required libraries (typer, rich) are missing. Run in project venv: .venv/bin/python",
        file=sys.stderr,
    )
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[1]
CHAPTERS_DIR = ROOT / "book" / "contents" / "chapters"
RULES_DIR = ROOT / ".claude" / "rules"
CHAPTER_GOALS_FILE = RULES_DIR / "chapter-goals.md"
SECTION_GOALS_FILE = RULES_DIR / "section-goals.md"
PROGRESSIVE_DISCLOSURE_FILE = RULES_DIR / "progressive-disclosure.md"

# Style & Anti-Hype Constraints
FORBIDDEN_HYPE_WORDS = [
    r"\bdelve\b",
    r"\brevolutioniz(?:e|ed|ing|es)\b",
    r"\bgame[- ]chang(?:er|ing)\b",
    r"\bcutting[- ]edge\b",
    r"\brealm\b",
    r"\blandscape\b",
    r"\bunlock(?:s|ed|ing)?\b",
    r"\bparadigm[- ]shift\b",
    r"\bgroundbreaking\b",
    r"\btestament\b",
]

# Concept ownership mapping across chapters (progressive disclosure)
CONCEPT_OWNERSHIP: dict[str, int] = {
    "Architecture 2.0": 1,
    "Lighthouse": 1,
    "design loop": 2,
    "search space": 2,
    "design pressure": 2,
    "design-loop card": 3,
    "life cycle": 3,
    "lifecycle": 3,
    "world model": 4,
    "represented state": 4,
    "AST complexity": 4,
    "method role": 5,
    "predictive surrogate": 5,
    "candidate generator": 5,
    "fidelity ladder": 6,
    "execution harness": 6,
    "tool isolation": 6,
    "feedback budget": 7,
    "rejection authority": 7,
    "formal verification": 7,
    "closed-loop execution": 8,
    "commitment boundary": 8,
    "pattern transfer": 9,
    "generalization": 9,
    "complete system": 10,
    "red-teaming": 10,
    "architectural ownership": 11,
    "hardware errata": 11,
    "ecosystem": 12,
}

console = Console(
    theme=Theme(
        {
            "info": "cyan",
            "warning": "yellow",
            "error": "bold red",
            "success": "bold green",
            "header": "bold magenta",
            "dim": "dim white",
            "accent": "bold cyan",
        }
    )
)


@dataclass
class ChapterGoal:
    number: int
    title: str
    governing_question: str = ""
    goal: str = ""
    reader_outcome: str = ""
    owns: str = ""
    does_not_own: str = ""
    hands_forward: str = ""
    adequacy_test: str = ""


@dataclass
class Section:
    chapter_num: int
    chapter_slug: str
    title: str
    anchor: str
    level: int  # 1 for chapter title/opener, 2 for ##, 3 for ###
    start_line: int  # 1-indexed, inclusive
    end_line: int  # 1-indexed, inclusive
    raw_lines: list[str] = field(default_factory=list)
    figures: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    callouts: list[str] = field(default_factory=list)
    footnotes: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)

    @property
    def raw_text(self) -> str:
        return "\n".join(self.raw_lines)

    @property
    def word_count(self) -> int:
        words = re.findall(r"\b[A-Za-z0-9_-]+\b", self.raw_text)
        return len(words)

    @property
    def identifier(self) -> str:
        if self.anchor:
            return self.anchor
        clean_title = re.sub(r"[^a-zA-Z0-9]+", "-", self.title.lower()).strip("-")
        return f"sec-{clean_title}"


@dataclass
class AuditFinding:
    severity: str  # "error", "warning", "tip", "info"
    dimension: str
    line_number: int
    message: str
    suggestion: str = ""


class KnowledgeBase:
    """Loads chapter goals and book metadata."""

    def __init__(self) -> None:
        self.chapters: dict[int, ChapterGoal] = {}
        self._load_chapter_goals()

    def _load_chapter_goals(self) -> None:
        if not CHAPTER_GOALS_FILE.exists():
            return
        text = CHAPTER_GOALS_FILE.read_text(encoding="utf-8")
        current_ch: Optional[ChapterGoal] = None
        current_field: Optional[str] = None

        for line in text.splitlines():
            m = re.match(r"^###\s+(\d+)\.\s+(.*)$", line)
            if m:
                ch_num = int(m.group(1))
                ch_title = m.group(2).strip()
                current_ch = ChapterGoal(number=ch_num, title=ch_title)
                self.chapters[ch_num] = current_ch
                current_field = None
                continue

            if current_ch:
                fm = re.match(r"^\*\*([A-Za-z\s]+?)\.\*\*\s*(.*)$", line)
                if fm:
                    field_name = fm.group(1).lower().strip().replace(" ", "_")
                    val = fm.group(2).strip()
                    current_field = field_name
                    if hasattr(current_ch, field_name):
                        setattr(current_ch, field_name, val)
                elif (
                    current_field
                    and line.strip()
                    and hasattr(current_ch, current_field)
                ):
                    old_val = getattr(current_ch, current_field)
                    setattr(
                        current_ch, current_field, f"{old_val} {line.strip()}".strip()
                    )

    def get_chapter(self, num: int) -> Optional[ChapterGoal]:
        return self.chapters.get(num)


class SectionParser:
    """Parses a Quarto QMD file into structured sections."""

    @staticmethod
    def parse_chapter(path: Path) -> list[Section]:
        if not path.exists():
            raise FileNotFoundError(f"Chapter file not found: {path}")

        raw_text = path.read_text(encoding="utf-8")
        lines = raw_text.splitlines()

        # Extract chapter number from slug (e.g. 02-pressures -> 2)
        slug_match = re.match(r"^(\d+)-", path.parent.name)
        ch_num = int(slug_match.group(1)) if slug_match else 0
        ch_slug = path.parent.name

        sections: list[Section] = []
        current_lines: list[str] = []
        current_title = "Chapter Opener & Framing"
        current_anchor = ""
        current_level = 1
        current_start = 1

        in_yaml = False
        in_code_block = False

        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped == "---":
                if lineno == 1 or in_yaml:
                    in_yaml = not in_yaml
                    current_lines.append(line)
                    continue

            if stripped.startswith("```"):
                in_code_block = not in_code_block
                current_lines.append(line)
                continue

            if not in_yaml and not in_code_block:
                heading_match = re.match(
                    r"^(#{1,3})\s+(.*?)(?:\s+\{#([^}]+)\})?$", line
                )
                if heading_match:
                    h_level = len(heading_match.group(1))
                    h_title = heading_match.group(2).strip()
                    h_anchor = heading_match.group(3) or ""

                    # We treat # (title) and ## (major section) as section delimiters
                    if h_level in (1, 2):
                        if current_lines:
                            sec = SectionParser._build_section(
                                ch_num,
                                ch_slug,
                                current_title,
                                current_anchor,
                                current_level,
                                current_start,
                                lineno - 1,
                                current_lines,
                            )
                            sections.append(sec)
                        current_title = h_title
                        current_anchor = h_anchor
                        current_level = h_level
                        current_start = lineno
                        current_lines = [line]
                        continue

            current_lines.append(line)

        if current_lines:
            sec = SectionParser._build_section(
                ch_num,
                ch_slug,
                current_title,
                current_anchor,
                current_level,
                current_start,
                len(lines),
                current_lines,
            )
            sections.append(sec)

        return sections

    @staticmethod
    def _build_section(
        ch_num: int,
        ch_slug: str,
        title: str,
        anchor: str,
        level: int,
        start_line: int,
        end_line: int,
        lines: list[str],
    ) -> Section:
        content = "\n".join(lines)
        figures = re.findall(r"\{#(fig-[a-zA-Z0-9_-]+)", content)
        tables = re.findall(r"\{#(tbl-[a-zA-Z0-9_-]+)", content)
        callouts = re.findall(r":::\s+\{\.callout-([a-zA-Z0-9_-]+)", content)
        footnotes = re.findall(r"\[\^(fn-[a-zA-Z0-9_-]+)\]", content)
        citations = re.findall(r"@([a-zA-Z0-9_-]{4,40})", content)

        return Section(
            chapter_num=ch_num,
            chapter_slug=ch_slug,
            title=title,
            anchor=anchor,
            level=level,
            start_line=start_line,
            end_line=end_line,
            raw_lines=lines,
            figures=sorted(list(set(figures))),
            tables=sorted(list(set(tables))),
            callouts=sorted(list(set(callouts))),
            footnotes=sorted(list(set(footnotes))),
            citations=sorted(list(set(citations))),
        )


class DevelopmentalAuditor:
    """Evaluates section quality across developmental and pedagogical dimensions."""

    def __init__(self, kb: KnowledgeBase) -> None:
        self.kb = kb

    def audit_section(
        self,
        section: Section,
        prev_section: Optional[Section] = None,
        next_section: Optional[Section] = None,
    ) -> list[AuditFinding]:
        findings: list[AuditFinding] = []

        # 1. Flow & Inflow Hook Analysis (for non-opener sections)
        if section.level == 2 and prev_section:
            first_prose_para = self._get_first_prose_paragraph(section.raw_lines)
            if first_prose_para:
                # Check if first sentence connects backward
                words = first_prose_para.lower()
                has_bridge = any(
                    token in words
                    for token in [
                        "once",
                        "after",
                        "having",
                        "while",
                        "whereas",
                        "beyond",
                        "these",
                        "this",
                        "such",
                        "to use",
                        "connect",
                        "build",
                        "earlier",
                        "before",
                        "when",
                        "with ",
                        "as ",
                        "because",
                        "since",
                        "given ",
                    ]
                )
                if not has_bridge and not any(
                    f"@{p.anchor}" in first_prose_para
                    for p in [prev_section]
                    if p.anchor
                ):
                    findings.append(
                        AuditFinding(
                            severity="warning",
                            dimension="Transitions & Flow",
                            line_number=section.start_line,
                            message=f"Opening of '{section.title}' may lack a clear backward bridge to '{prev_section.title}'.",
                            suggestion="Consider beginning with a transitional clause connecting the previous section's outcome to this section's core problem.",
                        )
                    )

        # 2. Outflow / Section Handoff Analysis
        if section.level == 2 and next_section:
            last_prose_para = self._get_last_prose_paragraph(section.raw_lines)
            if last_prose_para:
                if len(last_prose_para.split()) < 15:
                    findings.append(
                        AuditFinding(
                            severity="info",
                            dimension="Transitions & Flow",
                            line_number=section.end_line,
                            message=f"Closing paragraph in '{section.title}' is unusually short; ensure it delivers a crisp handoff to '{next_section.title}'.",
                            suggestion="State what the reader now understands that makes the next section necessary.",
                        )
                    )

        # 3. Progressive Disclosure (Concept Lifecycle)
        ch_goal = self.kb.get_chapter(section.chapter_num)
        for lineno_offset, line in enumerate(section.raw_lines):
            line_num = section.start_line + lineno_offset
            for concept, owner_ch in CONCEPT_OWNERSHIP.items():
                if section.chapter_num < owner_ch:
                    # Concept belongs to a later chapter
                    pattern = rf"\b{re.escape(concept)}\b"
                    if re.search(pattern, line, re.IGNORECASE):
                        # Allow preview if brief, but warn against deep definition
                        if any(
                            kw in line.lower()
                            for kw in [
                                "define",
                                "we define",
                                "is defined as",
                                "refers to",
                            ]
                        ):
                            findings.append(
                                AuditFinding(
                                    severity="error",
                                    dimension="Progressive Disclosure",
                                    line_number=line_num,
                                    message=f"Concept '{concept}' is owned by Chapter {owner_ch}; do not define it prematurely here in Chapter {section.chapter_num}.",
                                    suggestion=f"Preview '{concept}' lightly in plain language or defer until Chapter {owner_ch}.",
                                )
                            )

        # 4. CMOS 3-Layer Figure Integration
        for fig_id in section.figures:
            # Check pre-brief: is @fig-id mentioned before the float?
            fig_line_idx = self._find_figure_line(section.raw_lines, fig_id)
            if fig_line_idx != -1:
                pre_prose = "\n".join(section.raw_lines[:fig_line_idx])
                post_prose = "\n".join(section.raw_lines[fig_line_idx + 1 :])
                fig_ref = f"@{fig_id}"

                if fig_ref not in pre_prose and fig_ref not in "\n".join(
                    section.raw_lines[max(0, fig_line_idx - 5) : fig_line_idx]
                ):
                    findings.append(
                        AuditFinding(
                            severity="warning",
                            dimension="Figure Integration (Pre-Brief)",
                            line_number=section.start_line + fig_line_idx,
                            message=f"Figure '{fig_id}' lacks an explicit motivation/pre-brief in the prose directly before its appearance.",
                            suggestion=f"Introduce the question or mechanism motivating @{fig_id} in the paragraph preceding the figure float.",
                        )
                    )

                if fig_ref not in post_prose and len(post_prose.strip()) > 50:
                    # Check whether landing exists
                    landing_para = self._get_next_prose_paragraph(
                        section.raw_lines[fig_line_idx + 1 :]
                    )
                    if not landing_para or len(landing_para.split()) < 20:
                        findings.append(
                            AuditFinding(
                                severity="info",
                                dimension="Figure Integration (Analytical Landing)",
                                line_number=section.start_line + fig_line_idx,
                                message=f"Figure '{fig_id}' may lack a thorough analytical landing walkthrough.",
                                suggestion="Directly following the figure, explain the intermediate stages, physical mechanisms, and architectural delta.",
                            )
                        )

        # 5. Margin Space & Footnote Opportunities
        for lineno_offset, line in enumerate(section.raw_lines):
            line_num = section.start_line + lineno_offset
            # Look for dense parenthetical secondary definitions in prose
            parenthetical_defs = re.findall(
                r"\(([a-z0-9\s,-]+(?:means|stands for|refers to|such as|for example|which is|technique that)[^)]+)\)",
                line,
                re.IGNORECASE,
            )
            for pdef in parenthetical_defs:
                if len(pdef.split()) > 8:
                    findings.append(
                        AuditFinding(
                            severity="tip",
                            dimension="Margin Space Optimization",
                            line_number=line_num,
                            message=f"Dense inline parenthetical found: '({pdef[:45]}...)'.",
                            suggestion="Consider offloading this secondary gloss into a margin footnote ([^fn-...]) or column-margin note to preserve main narrative flow.",
                        )
                    )

        # 6. Mechanical Prose Style & Anti-Hype
        in_code_block = False
        for lineno_offset, line in enumerate(section.raw_lines):
            line_num = section.start_line + lineno_offset
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block or stripped.startswith("#|"):
                continue

            # Em-dash check (exempt blockquote epigraph signature attribution lines)
            if "—" in line and not line.strip().startswith(">"):
                findings.append(
                    AuditFinding(
                        severity="error",
                        dimension="Prose Style",
                        line_number=line_num,
                        message="Em-dash ('—') found in running prose.",
                        suggestion="Recast using a period, comma, colon, or parentheses per prose-style.md.",
                    )
                )

            # Clean line of cross-references, code, and links before scanning
            clean_prose = re.sub(r"@(?:fig|sec|tbl|eq)-[a-zA-Z0-9_-]+", "", line)
            clean_prose = re.sub(r"`[^`]+`", "", clean_prose)
            clean_prose = re.sub(r"\[.*?\]\(.*?\)", "", clean_prose)

            # Forbidden hype words
            for hw_pattern in FORBIDDEN_HYPE_WORDS:
                match = re.search(hw_pattern, clean_prose, re.IGNORECASE)
                if match:
                    findings.append(
                        AuditFinding(
                            severity="warning",
                            dimension="Anti-Hype",
                            line_number=line_num,
                            message=f"Forbidden marketing/hype term detected: '{match.group(0)}'.",
                            suggestion="Replace with precise, scholarly, grounded architectural vocabulary.",
                        )
                    )

            # Colon tic: 'X is <adj>: <restated claim>'
            colon_tic = re.search(
                r"\bis\s+(?:critical|essential|crucial|vital|clear|simple):\s+",
                line,
                re.IGNORECASE,
            )
            if colon_tic:
                findings.append(
                    AuditFinding(
                        severity="warning",
                        dimension="Prose Style",
                        line_number=line_num,
                        message="Colon tic detected ('is <adj>: ...').",
                        suggestion="Integrate into a direct declarative sentence without the colon throat-clearing.",
                    )
                )

            # Sentence-initial 'By <gerund>'
            if re.match(r"^\s*By\s+[a-z]+ing\b", line):
                findings.append(
                    AuditFinding(
                        severity="warning",
                        dimension="Prose Style",
                        line_number=line_num,
                        message="Sentence-initial 'By <gerund>' detected.",
                        suggestion="Recast with the agent/subject leading the action.",
                    )
                )

        return findings

    @staticmethod
    def _get_first_prose_paragraph(lines: list[str]) -> Optional[str]:
        in_code = False
        for line in lines[1:]:  # skip heading line
            s = line.strip()
            if s.startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            if (
                s
                and not s.startswith("#")
                and not s.startswith(":::")
                and not s.startswith("!")
                and not s.startswith("|")
                and not s.startswith("\\")
                and not s.startswith("$$")
                and not s.startswith("$")
                and not s.startswith("[^")
            ):
                return s
        return None

    @staticmethod
    def _get_last_prose_paragraph(lines: list[str]) -> Optional[str]:
        code_mask = []
        c = False
        for l in lines:
            if l.strip().startswith("```"):
                c = not c
                code_mask.append(True)
            else:
                code_mask.append(c)

        for line, is_code in zip(reversed(lines), reversed(code_mask)):
            if is_code:
                continue
            s = line.strip()
            if (
                s
                and not s.startswith("#")
                and not s.startswith(":::")
                and not s.startswith("!")
                and not s.startswith("|")
                and not s.startswith("[^")
                and not s.startswith("\\")
                and not s.startswith("$$")
                and not s.startswith("$")
            ):
                return s
        return None

    @staticmethod
    def _get_next_prose_paragraph(lines: list[str]) -> Optional[str]:
        in_code = False
        for line in lines:
            s = line.strip()
            if s.startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            if (
                s
                and not s.startswith("#")
                and not s.startswith(":::")
                and not s.startswith("!")
                and not s.startswith("|")
                and not s.startswith("[^")
                and not s.startswith("\\")
                and not s.startswith("$$")
                and not s.startswith("$")
            ):
                return s
        return None

    @staticmethod
    def _find_figure_line(lines: list[str], fig_id: str) -> int:
        for idx, line in enumerate(lines):
            if f"#{fig_id}" in line or f"label: {fig_id}" in line:
                return idx
        return -1


class PacketGenerator:
    """Generates comprehensive Developmental Editor packets for focused section editing."""

    def __init__(self, kb: KnowledgeBase, auditor: DevelopmentalAuditor) -> None:
        self.kb = kb
        self.auditor = auditor

    def build_packet(
        self,
        chapter_sections: list[Section],
        target_idx: int,
    ) -> str:
        section = chapter_sections[target_idx]
        prev_section = chapter_sections[target_idx - 1] if target_idx > 0 else None
        next_section = (
            chapter_sections[target_idx + 1]
            if target_idx < len(chapter_sections) - 1
            else None
        )

        ch_goal = self.kb.get_chapter(section.chapter_num)
        findings = self.auditor.audit_section(section, prev_section, next_section)

        lines: list[str] = [
            f"# Developmental Editor Dossier: Section '{section.title}'",
            "",
            "## 1. Global Macro Context (The Big Picture)",
            "",
            f"- **Chapter**: {section.chapter_num:02d} — {ch_goal.title if ch_goal else section.chapter_slug}",
            f"- **Chapter Governing Crux**: {ch_goal.governing_question if ch_goal else 'N/A'}",
            f"- **Chapter Teaching Goal**: {ch_goal.goal if ch_goal else 'N/A'}",
            f"- **Target Reader Delta**: {ch_goal.reader_outcome if ch_goal else 'N/A'}",
            f"- **Chapter Boundary (Owns)**: {ch_goal.owns if ch_goal else 'N/A'}",
            f"- **Chapter Boundary (Does Not Own)**: {ch_goal.does_not_own if ch_goal else 'N/A'}",
            f"- **Forward Handoff**: {ch_goal.hands_forward if ch_goal else 'N/A'}",
            "",
            "## 2. Upstream & Downstream Flow Within This Chapter",
            "",
            f"- **Preceding Section**: {prev_section.title if prev_section else '[Start of Chapter]'}",
        ]

        if prev_section:
            prev_last = DevelopmentalAuditor._get_last_prose_paragraph(
                prev_section.raw_lines
            )
            if prev_last:
                lines.append(
                    f'  - *Preceding Section Departure Point*: "{prev_last[:160]}..."'
                )

        lines.extend(
            [
                f"- **Current Section Under Focus**: {section.title} (Lines {section.start_line}–{section.end_line}, ~{section.word_count} words)",
                f"- **Subsequent Section**: {next_section.title if next_section else '[End of Chapter]'}",
            ]
        )

        if next_section:
            next_first = DevelopmentalAuditor._get_first_prose_paragraph(
                next_section.raw_lines
            )
            if next_first:
                lines.append(
                    f'  - *Subsequent Section Entry Point*: "{next_first[:160]}..."'
                )

        lines.extend(
            [
                "",
                "## 3. Developmental Diagnostic Audit",
                "",
            ]
        )

        if not findings:
            lines.append(
                "🟢 **No developmental friction points detected by automated heuristics.**"
            )
        else:
            for f in findings:
                icon = {
                    "error": "🔴",
                    "warning": "🟡",
                    "tip": "💡",
                    "info": "📌",
                }.get(f.severity, "•")
                lines.append(
                    f"- {icon} **[{f.dimension}] Line {f.line_number}**: {f.message}"
                )
                if f.suggestion:
                    lines.append(f"  *Guidance*: {f.suggestion}")

        lines.extend(
            [
                "",
                "## 4. Developmental Editor Guidance & Instructions",
                "",
                "As the developmental editor, your mission is to elevate this section to the highest pedagogical standard:",
                "1. **Strengthen Flow & Rhythm**: Ensure the opening hook logically grows out of the preceding section and the ending sets up the next.",
                "2. **Audience Accessibility**: Ensure every complex architectural/EDA mechanism is grounded with intuitive physical concepts before mathematical or implementation formalisms.",
                "3. **Progressive Disclosure**: Verify that no concepts owned by future chapters are defined here; keep focus on the chapter's crux.",
                "4. **CMOS 3-Layer Visual Integration**: Motivate all figures beforehand in prose (`pre-brief`) and provide a thorough walkthrough afterwards (`analytical landing`).",
                "5. **Creative Margin Space Utilization**: Consider where compact sidebars, historical anchors, or adjacent-field glossary notes belong in margin notes (`[^fn-...]` or `.column-margin`) to keep the primary argument crisp.",
                "6. **Prose Mechanics**: Strict American English, zero hype vocabulary, no em-dashes in prose, no colon tics.",
                "",
                "## 5. Section Source Code",
                "",
                f"```{section.chapter_slug}:lines {section.start_line}-{section.end_line}",
                section.raw_text,
                "```",
            ]
        )

        return "\n".join(lines) + "\n"


class GuidedReviewSession:
    """Runs interactive section-by-section developmental review walkthrough."""

    def __init__(
        self,
        kb: KnowledgeBase,
        auditor: DevelopmentalAuditor,
        packet_gen: PacketGenerator,
    ) -> None:
        self.kb = kb
        self.auditor = auditor
        self.packet_gen = packet_gen

    def run_chapter(self, qmd_path: Path) -> None:
        sections = SectionParser.parse_chapter(qmd_path)
        if not sections:
            console.print("[red]No sections found in file.[/red]")
            return

        ch_num = sections[0].chapter_num
        ch_goal = self.kb.get_chapter(ch_num)

        console.print(
            Panel(
                f"[bold magenta]Architecture 2.0 Developmental Review[/bold magenta]\n"
                f"[bold cyan]Chapter {ch_num:02d}: {ch_goal.title if ch_goal else qmd_path.name}[/bold cyan]\n"
                f"[dim]Sections: {len(sections)} | Total Lines: {sections[-1].end_line}[/dim]\n"
                f"[italic yellow]Crux: {ch_goal.governing_question if ch_goal else 'N/A'}[/italic yellow]",
                box=box.DOUBLE,
            )
        )

        for idx, sec in enumerate(sections):
            prev_sec = sections[idx - 1] if idx > 0 else None
            next_sec = sections[idx + 1] if idx < len(sections) - 1 else None

            self._display_section_summary(idx, sec, prev_sec, next_sec, len(sections))

            while True:
                prompt_text = (
                    f"[bold green]Section [{idx+1}/{len(sections)}][/bold green] "
                    f"Choose: [b](v)[/b]iew text | [b](a)[/b]udit details | [b](p)[/b]acket export | [b](n)[/b]ext | [b](q)[/b]uit: "
                )
                try:
                    choice = console.input(prompt_text).strip().lower()
                except (EOFError, KeyboardInterrupt):
                    console.print("\n[dim]Walkthrough ended by user.[/dim]")
                    return

                if choice in ("n", ""):
                    break
                elif choice == "q":
                    console.print("[dim]Exiting developmental walkthrough.[/dim]")
                    return
                elif choice == "v":
                    console.print(
                        Panel(
                            Markdown(sec.raw_text),
                            title=f"[bold cyan]{sec.title}[/bold cyan]",
                        )
                    )
                elif choice == "a":
                    findings = self.auditor.audit_section(sec, prev_sec, next_sec)
                    if not findings:
                        console.print(
                            "[green]✓ Clean! No developmental heuristics flagged.[/green]"
                        )
                    else:
                        table = Table(box=box.SIMPLE_HEAVY)
                        table.add_column("Sev", width=4)
                        table.add_column("Dimension", style="cyan")
                        table.add_column("Line", style="dim", width=6)
                        table.add_column("Finding", style="white")
                        table.add_column("Suggestion", style="italic yellow")
                        for f in findings:
                            icon = {
                                "error": "🔴",
                                "warning": "🟡",
                                "tip": "💡",
                                "info": "📌",
                            }.get(f.severity, "•")
                            table.add_row(
                                icon,
                                f.dimension,
                                str(f.line_number),
                                f.message,
                                f.suggestion,
                            )
                        console.print(table)
                elif choice == "p":
                    packet_md = self.packet_gen.build_packet(sections, idx)
                    out_path = ROOT / "tmp" / f"packet-ch{ch_num:02d}-sec{idx+1:02d}.md"
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_text(packet_md, encoding="utf-8")
                    console.print(
                        f"[green]✓ Wrote packet to {out_path.relative_to(ROOT)}[/green]"
                    )
                else:
                    console.print("[red]Invalid option. Enter v, a, p, n, or q.[/red]")

        console.print(
            Panel(
                "[bold green]✓ Chapter developmental walkthrough complete![/bold green]"
            )
        )

    def _display_section_summary(
        self,
        idx: int,
        sec: Section,
        prev_sec: Optional[Section],
        next_sec: Optional[Section],
        total: int,
    ) -> None:
        findings = self.auditor.audit_section(sec, prev_sec, next_sec)
        error_cnt = sum(1 for f in findings if f.severity == "error")
        warn_cnt = sum(1 for f in findings if f.severity == "warning")
        tip_cnt = sum(1 for f in findings if f.severity in ("tip", "info"))

        status = (
            "🟢 Ready"
            if not findings
            else (f"🔴 {error_cnt} issues" if error_cnt else f"🟡 {warn_cnt} warnings")
        )
        if tip_cnt and not error_cnt and not warn_cnt:
            status = f"💡 {tip_cnt} tips"

        info_lines = [
            f"[bold cyan]Section {idx+1}/{total}: {sec.title}[/bold cyan] ({status})",
            f"[dim]Lines {sec.start_line}–{sec.end_line} | {sec.word_count} words | Figures: {len(sec.figures)} | Margins/Footnotes: {len(sec.footnotes)}[/dim]",
            f"[dim white]Inflow Hook: from '{prev_sec.title if prev_sec else 'Chapter Opener'}'[/dim white]",
            f"[dim white]Outflow Handoff: to '{next_sec.title if next_sec else 'Chapter Close'}'[/dim white]",
        ]

        if findings:
            info_lines.append("")
            info_lines.append("[bold]Key Observations:[/bold]")
            for f in findings[:3]:
                icon = {"error": "🔴", "warning": "🟡", "tip": "💡", "info": "📌"}.get(
                    f.severity, "•"
                )
                info_lines.append(f"  {icon} [cyan]{f.dimension}[/cyan]: {f.message}")
            if len(findings) > 3:
                info_lines.append(
                    f"  [dim]... and {len(findings)-3} more finding(s)[/dim]"
                )

        console.print(Panel("\n".join(info_lines), box=box.ROUNDED))


def resolve_chapter_path(target: str) -> Path:
    """Resolves chapter number, slug, or relative path to absolute QMD path."""
    target_clean = target.strip()
    # Case 1: direct file path
    p = Path(target_clean)
    if p.exists() and p.suffix == ".qmd":
        return p.resolve()

    # Case 2: integer number (e.g. 2, 02)
    if target_clean.isdigit():
        num = int(target_clean)
        matches = list(CHAPTERS_DIR.glob(f"{num:02d}-*/*.qmd"))
        if matches:
            return matches[0]

    # Case 3: chapter slug (e.g. pressures, 02-pressures)
    matches = list(CHAPTERS_DIR.glob(f"*{target_clean}*/*.qmd"))
    if matches:
        return matches[0]

    raise ValueError(f"Could not locate chapter matching '{target}' in {CHAPTERS_DIR}")


app = typer.Typer(
    name="developmental_editor",
    help="Architecture 2.0 Developmental Editor: Section-by-section analysis, packets, and walkthroughs.",
    rich_markup_mode="rich",
)


@app.command("list")
def cmd_list(
    chapter: Optional[str] = typer.Argument(
        None, help="Chapter number or slug (e.g. 02, pressures). If omitted, lists all."
    ),
) -> None:
    """Lists sections, line counts, word counts, and figure counts across chapters."""
    kb = KnowledgeBase()

    if chapter:
        targets = [resolve_chapter_path(chapter)]
    else:
        targets = sorted(CHAPTERS_DIR.glob("*/*.qmd"))

    for path in targets:
        sections = SectionParser.parse_chapter(path)
        ch_num = sections[0].chapter_num if sections else 0
        ch_goal = kb.get_chapter(ch_num)

        table = Table(
            title=f"Chapter {ch_num:02d}: {ch_goal.title if ch_goal else path.parent.name}",
            box=box.ROUNDED,
            header_style="bold magenta",
        )
        table.add_column("#", justify="right", width=3)
        table.add_column("Level", justify="center", width=5)
        table.add_column("Section Title", style="bold cyan")
        table.add_column("Lines", justify="center", width=12)
        table.add_column("Words", justify="right", width=7)
        table.add_column("Floats", justify="center", width=8)
        table.add_column("Notes", justify="center", width=7)

        for idx, sec in enumerate(sections, 1):
            floats = (
                f"📊{len(sec.figures)} 📋{len(sec.tables)}"
                if (sec.figures or sec.tables)
                else "—"
            )
            notes = f"📝{len(sec.footnotes)}" if sec.footnotes else "—"
            table.add_row(
                str(idx),
                f"H{sec.level}",
                sec.title,
                f"{sec.start_line}–{sec.end_line}",
                f"{sec.word_count:,}",
                floats,
                notes,
            )
        console.print(table)
        console.print()


@app.command("audit")
def cmd_audit(
    chapter: str = typer.Argument(
        ..., help="Chapter number or slug (e.g. 02, pressures)."
    ),
    section_num: Optional[int] = typer.Option(
        None, "--sec", "-s", help="Specific 1-indexed section number to audit."
    ),
) -> None:
    """Runs a deep developmental audit on a chapter or individual section."""
    kb = KnowledgeBase()
    auditor = DevelopmentalAuditor(kb)
    path = resolve_chapter_path(chapter)
    sections = SectionParser.parse_chapter(path)

    if section_num:
        if section_num < 1 or section_num > len(sections):
            console.print(
                f"[red]Error: Section index {section_num} out of bounds (1..{len(sections)}).[/red]"
            )
            raise typer.Exit(1)
        target_sections = [(section_num - 1, sections[section_num - 1])]
    else:
        target_sections = list(enumerate(sections))

    console.print(
        Panel(f"[bold magenta]Developmental Audit: {path.name}[/bold magenta]")
    )

    total_findings = 0
    for idx, sec in target_sections:
        prev_sec = sections[idx - 1] if idx > 0 else None
        next_sec = sections[idx + 1] if idx < len(sections) - 1 else None

        findings = auditor.audit_section(sec, prev_sec, next_sec)
        total_findings += len(findings)

        if not findings:
            console.print(
                f"[green]✓ Section {idx+1}: {sec.title} (Passed cleanly)[/green]"
            )
            continue

        console.print(
            f"\n[bold cyan]Section {idx+1}: {sec.title}[/bold cyan] [dim](Lines {sec.start_line}–{sec.end_line})[/dim]"
        )
        for f in findings:
            icon = {"error": "🔴", "warning": "🟡", "tip": "💡", "info": "📌"}.get(
                f.severity, "•"
            )
            console.print(
                f"  {icon} [bold]{f.dimension}[/bold] (line {f.line_number}): {f.message}"
            )
            if f.suggestion:
                console.print(
                    f"    [italic yellow]Suggestion: {f.suggestion}[/italic yellow]"
                )

    console.print(
        f"\n[bold]Total findings across evaluated scope: {total_findings}[/bold]"
    )


@app.command("inspect")
def cmd_inspect(
    chapter: str = typer.Argument(
        ..., help="Chapter number or slug (e.g. 02, pressures)."
    ),
    section_num: int = typer.Argument(..., help="1-indexed section number to inspect."),
) -> None:
    """Displays the full text and macro-context dossier for a single section."""
    kb = KnowledgeBase()
    auditor = DevelopmentalAuditor(kb)
    packet_gen = PacketGenerator(kb, auditor)
    path = resolve_chapter_path(chapter)
    sections = SectionParser.parse_chapter(path)

    if section_num < 1 or section_num > len(sections):
        console.print(
            f"[red]Error: Section index {section_num} out of bounds (1..{len(sections)}).[/red]"
        )
        raise typer.Exit(1)

    packet_md = packet_gen.build_packet(sections, section_num - 1)
    console.print(Markdown(packet_md))


@app.command("packet")
def cmd_packet(
    chapter: str = typer.Argument(
        ..., help="Chapter number or slug (e.g. 02, pressures)."
    ),
    section_num: int = typer.Argument(..., help="1-indexed section number."),
    out: Optional[Path] = typer.Option(
        None, "--out", "-o", help="Output path for the generated markdown packet."
    ),
) -> None:
    """Exports a self-contained Developmental Editor Packet markdown file."""
    kb = KnowledgeBase()
    auditor = DevelopmentalAuditor(kb)
    packet_gen = PacketGenerator(kb, auditor)
    path = resolve_chapter_path(chapter)
    sections = SectionParser.parse_chapter(path)

    if section_num < 1 or section_num > len(sections):
        console.print(
            f"[red]Error: Section index {section_num} out of bounds (1..{len(sections)}).[/red]"
        )
        raise typer.Exit(1)

    packet_md = packet_gen.build_packet(sections, section_num - 1)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(packet_md, encoding="utf-8")
        console.print(f"[green]✓ Wrote packet to {out}[/green]")
    else:
        print(packet_md)


@app.command("guide")
def cmd_guide(
    chapter: str = typer.Argument(
        ..., help="Chapter number or slug to walk through (e.g. 03, lifecycle)."
    ),
) -> None:
    """Interactive section-by-section developmental editor walkthrough."""
    kb = KnowledgeBase()
    auditor = DevelopmentalAuditor(kb)
    packet_gen = PacketGenerator(kb, auditor)
    session = GuidedReviewSession(kb, auditor, packet_gen)

    path = resolve_chapter_path(chapter)
    session.run_chapter(path)


@app.command("apply")
def cmd_apply(
    chapter: str = typer.Argument(..., help="Chapter number or slug."),
    section_num: int = typer.Argument(..., help="1-indexed section number to replace."),
    replacement_file: Path = typer.Argument(
        ..., help="Path to file containing improved section content."
    ),
    validate: bool = typer.Option(
        True,
        "--validate/--no-validate",
        help="Run arch2 book validate checks after applying.",
    ),
) -> None:
    """Safely applies an improved section replacement and validates the book."""
    path = resolve_chapter_path(chapter)
    sections = SectionParser.parse_chapter(path)

    if section_num < 1 or section_num > len(sections):
        console.print(
            f"[red]Error: Section index {section_num} out of bounds (1..{len(sections)}).[/red]"
        )
        raise typer.Exit(1)

    target_sec = sections[section_num - 1]
    if not replacement_file.exists():
        console.print(
            f"[red]Error: Replacement file {replacement_file} not found.[/red]"
        )
        raise typer.Exit(1)

    replacement_content = replacement_file.read_text(encoding="utf-8").strip()

    # Read original chapter lines
    orig_lines = path.read_text(encoding="utf-8").splitlines()

    # Target lines: start_line to end_line (1-indexed)
    pre_lines = orig_lines[: target_sec.start_line - 1]
    post_lines = orig_lines[target_sec.end_line :]

    new_full_text = "\n".join(pre_lines)
    if new_full_text:
        new_full_text += "\n"
    new_full_text += replacement_content
    if post_lines:
        new_full_text += "\n" + "\n".join(post_lines)
    new_full_text += "\n"

    # Display diff preview
    diff = list(
        difflib.unified_diff(
            orig_lines[target_sec.start_line - 1 : target_sec.end_line],
            replacement_content.splitlines(),
            fromfile=f"{path.name} (orig section {section_num})",
            tofile=f"{path.name} (improved section {section_num})",
            lineterm="",
        )
    )

    if not diff:
        console.print(
            "[yellow]No diff detected between original section and replacement file.[/yellow]"
        )
        return

    console.print(
        Panel(
            "\n".join(diff[:50]),
            title="[bold cyan]Diff Preview (first 50 lines)[/bold cyan]",
        )
    )

    path.write_text(new_full_text, encoding="utf-8")
    console.print(
        f"[green]✓ Successfully applied improved section {section_num} to {path.name}[/green]"
    )

    if validate:
        console.print("[dim]Running verification checks...[/dim]")
        cmd = [
            sys.executable,
            str(ROOT / "cli" / "arch2.py"),
            "book",
            "validate",
            "prose",
        ]
        res = subprocess.run(cmd, cwd=ROOT)
        if res.returncode != 0:
            console.print(
                "[red]⚠️ Validation flagged potential prose issues. Please inspect.[/red]"
            )
        else:
            console.print("[green]✓ Passed validation checks![/green]")


if __name__ == "__main__":
    app()
