#!/usr/bin/env python3
"""Generate the twelve Architecture 2.0 chapter-opening cover maps."""

from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WIDTH = 960
HEIGHT = 285

INK = "#20252B"
MUTED = "#3E474B"
GRID = "#D5DEE3"
ROW = "#E4E8ED"
WHITE = "#FFFFFF"

ROLES = {
    "neutral": (WHITE, GRID, INK),
    "workload": ("#E4F1F6", "#1683A6", "#136680"),
    "artifact": ("#F0ECFA", "#6A4FC7", "#59429E"),
    "constraint": ("#FDECEC", "#DE3D3C", "#C62A2A"),
    "method": ("#FBF0DE", "#E68A17", "#8A5310"),
    "evidence": ("#E7F5EC", "#1E9E48", "#157A38"),
    "decision": ("#FBEDF4", "#D24D96", "#A82E70"),
}

PARTS = (
    "I - INTENT & LIFECYCLE",
    "II - TECHNICAL BUILDING BLOCKS",
    "III - OPERATION & OWNERSHIP",
    "IV - ECOSYSTEM",
)


@dataclass(frozen=True)
class Chapter:
    number: int
    part: int
    slug: str
    move: str
    thesis: str
    alt: str

    @property
    def target(self) -> Path:
        return (
            ROOT
            / "book"
            / "contents"
            / "chapters"
            / self.slug
            / "images"
            / f"ch{self.number:02d}-cover-map.svg"
        )


CHAPTERS = (
    Chapter(
        1,
        1,
        "01-moonshot",
        "EXPAND COMPACT INTENT",
        "A prompt is not yet an architecture result",
        "Compact Lighthouse intent expands into a cross-stack specification, an AI-native design system, checked evidence, and a separate commitment decision.",
    ),
    Chapter(
        2,
        1,
        "02-pressures",
        "FIND THE LIMITING WORK",
        "Compounding pressures move the bottleneck",
        "Fading technology gains, coupled design obligations, and finite checking capacity converge on the work limiting the next supported decision.",
    ),
    Chapter(
        3,
        1,
        "03-lifecycle",
        "ORGANIZE THE WORK",
        "Six responsibilities create inspectable handoffs",
        "Six lifecycle responsibilities run from formulation through review and decision, with targeted repair returning to the responsibility that owns an inadequacy.",
    ),
    Chapter(
        4,
        2,
        "04-representations",
        "EXPOSE THE RIGHT STATE",
        "Every representation enables action and creates blind spots",
        "A source-linked project record feeds a task-specific representation that exposes some properties while declaring blind spots and retaining provenance.",
    ),
    Chapter(
        5,
        2,
        "05-methods",
        "CHOOSE THE SMALLEST APPROACH",
        "The engineering job selects the method",
        "Four conditions map to direct comparison, prediction, generation, or optimization, with a named check, fallback, and stopping condition.",
    ),
    Chapter(
        6,
        2,
        "06-environments",
        "CONTROL REAL TOOL USE",
        "An environment is more than a tool wrapper",
        "Nested environment, harness, wrapper, and tool boundaries turn an authorized request into a complete execution record for later qualification.",
    ),
    Chapter(
        7,
        2,
        "07-feedback",
        "QUALIFY, ROUTE, RETAIN",
        "A returned signal never explains itself",
        "A returned signal passes through verification qualification and a bounded claim before feedback routes the next action and learning is retained.",
    ),
    Chapter(
        8,
        3,
        "08-loop",
        "REPORT HONEST STOPS",
        "Two records stop at different evidence boundaries",
        "The prospective cache record stops before dispatch; the separate retained array record reaches a limited technical stop; neither closes a design loop.",
    ),
    Chapter(
        9,
        3,
        "09-patterns",
        "TRANSFER WITH CONDITIONS",
        "Reusable units can move; conclusions stay with their evidence",
        "A source record meets a changed condition, after which units are carried, updated, replaced, or retired and target claims are checked anew.",
    ),
    Chapter(
        10,
        3,
        "10-evaluation",
        "EVALUATE THE RIGHT OBJECT",
        "Name the object, then judge the complete claim",
        "Evaluation distinguishes the object, four judgments, a matched alternative, deliberate challenges, and a qualified claim that is not a commitment.",
    ),
    Chapter(
        11,
        3,
        "11-ownership",
        "SEPARATE OWNERSHIP FROM COMMITMENT",
        "Technical assessment does not authorize itself",
        "Substantial AI-native design work and architectural ownership remain distinct from a named commitment authority inside an accountable organization.",
    ),
    Chapter(
        12,
        4,
        "12-ecosystem",
        "SEPARATE EFFORT FROM COORDINATION",
        "Start locally; coordinate when the claim expands",
        "One team can improve records and comparisons now, while cross-team, physical or silicon, and public-program claims require different shared infrastructure.",
    ),
)


def esc(value: str) -> str:
    return html.escape(value, quote=False)


class SVG:
    def __init__(self, chapter: Chapter) -> None:
        self.chapter = chapter
        self.items: list[str] = []

    def add(self, value: str) -> None:
        self.items.append(value)

    def text(
        self,
        x: float,
        y: float,
        value: str,
        *,
        size: float = 15,
        weight: int = 400,
        fill: str = INK,
        anchor: str = "start",
        letter_spacing: float | None = None,
    ) -> None:
        spacing = (
            "" if letter_spacing is None else f' letter-spacing="{letter_spacing}"'
        )
        self.add(
            f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="Arial, Helvetica, sans-serif" '
            f'font-size="{size}" font-weight="{weight}" fill="{fill}"{spacing}>{esc(value)}</text>'
        )

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        role: str = "neutral",
        stroke_width: float = 1.5,
        fill: str | None = None,
        stroke: str | None = None,
    ) -> None:
        role_fill, role_stroke, _ = ROLES[role]
        self.add(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill or role_fill}" '
            f'stroke="{stroke or role_stroke}" stroke-width="{stroke_width}"/>'
        )

    def line(
        self,
        d: str,
        *,
        color: str = INK,
        width: float = 1.8,
        arrow: bool = True,
        dash: str | None = None,
    ) -> None:
        marker = ' marker-end="url(#arrow-ink)"' if arrow else ""
        dash_attr = "" if dash is None else f' stroke-dasharray="{dash}"'
        self.add(
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
            f'stroke-linecap="square" stroke-linejoin="miter"{dash_attr}{marker}/>'
        )

    def card(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        title: str,
        lines: tuple[str, ...] = (),
        *,
        role: str = "neutral",
        title_size: float = 16,
        body_size: float = 13.5,
        center: bool = False,
        title_offset: float = 25,
        body_offset: float = 48,
        body_gap: float = 18,
    ) -> None:
        self.rect(x, y, w, h, role=role)
        _, _, role_ink = ROLES[role]
        tx = x + w / 2 if center else x + 13
        anchor = "middle" if center else "start"
        self.text(
            tx,
            y + title_offset,
            title,
            size=title_size,
            weight=700,
            fill=role_ink,
            anchor=anchor,
        )
        for index, line in enumerate(lines):
            self.text(
                tx,
                y + body_offset + index * body_gap,
                line,
                size=body_size,
                fill=MUTED,
                anchor=anchor,
            )

    def diamond(
        self, cx: float, cy: float, rx: float, ry: float, *, role: str = "decision"
    ) -> None:
        role_fill, role_stroke, _ = ROLES[role]
        points = f"{cx},{cy - ry} {cx + rx},{cy} {cx},{cy + ry} {cx - rx},{cy}"
        self.add(
            f'<polygon points="{points}" fill="{role_fill}" stroke="{role_stroke}" stroke-width="1.7"/>'
        )

    def begin(self) -> None:
        chapter = self.chapter
        self.add('<?xml version="1.0" encoding="utf-8"?>')
        self.add(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" '
            f'role="img" aria-labelledby="cover-title-{chapter.number} cover-desc-{chapter.number}">'
        )
        self.add(
            f'<title id="cover-title-{chapter.number}">Chapter {chapter.number} opening map</title>'
        )
        self.add(f'<desc id="cover-desc-{chapter.number}">{esc(chapter.alt)}</desc>')
        self.add(
            '<defs><marker id="arrow-ink" viewBox="0 0 10 10" refX="8" refY="5" '
            'markerWidth="7" markerHeight="7" orient="auto"><path d="M 0 1 L 9 5 L 0 9 Z" '
            f'fill="{INK}"/></marker></defs>'
        )
        self.add(
            f'<rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" fill="{WHITE}"/>'
        )
        self.part_strip()
        self.text(
            14,
            58,
            chapter.move,
            size=13,
            weight=700,
            fill=ROLES["workload"][2],
            letter_spacing=0.7,
        )
        self.text(14, 83, chapter.thesis, size=20, weight=700)

    def part_strip(self) -> None:
        gap = 4
        w = (WIDTH - 28 - 3 * gap) / 4
        for index, label in enumerate(PARTS, start=1):
            x = 14 + (index - 1) * (w + gap)
            active = index == self.chapter.part
            fill = ROLES["workload"][1] if active else "#F1F5F9"
            stroke = ROLES["workload"][2] if active else "#CBD5E1"
            text_fill = WHITE if active else "#64748B"
            self.rect(x, 8, w, 27, fill=fill, stroke=stroke, stroke_width=1.0)
            self.text(
                x + w / 2,
                26,
                label,
                size=11.5,
                weight=700 if active else 600,
                fill=text_fill,
                anchor="middle",
            )

    def finish(self) -> str:
        self.add("</svg>")
        return "\n".join(self.items) + "\n"


def flow_arrow(svg: SVG, x1: float, x2: float, y: float) -> None:
    svg.line(f"M {x1} {y} H {x2}")


def chapter_1(svg: SVG) -> None:
    y, h = 112, 103
    cards = (
        (14, 136, "Compact intent", ("Lighthouse request",), "workload"),
        (
            176,
            190,
            "Cross-stack specification",
            ("requirements + constraints", "checks + evidence needs"),
            "artifact",
        ),
        (
            392,
            204,
            "AI-native design system",
            ("state + methods + real tools", "independent checks included"),
            "neutral",
        ),
        (
            622,
            154,
            "Supported result",
            ("better result", "or lower cost", "reference / unresolved"),
            "evidence",
        ),
    )
    for x, w, title, lines, role in cards:
        svg.card(x, y, w, h, title, lines, role=role, title_size=14, body_size=11)
    flow_arrow(svg, 150, 176, 163)
    flow_arrow(svg, 366, 392, 163)
    flow_arrow(svg, 596, 622, 163)
    flow_arrow(svg, 776, 804, 163)
    svg.card(
        804,
        y,
        142,
        h,
        "Named authority",
        ("advance / hold", "reject"),
        role="decision",
        title_size=14,
        body_size=11,
        center=True,
    )
    svg.text(
        784,
        244,
        "RECOMMENDATION INFORMS; AUTHORITY COMMITS",
        size=11.5,
        weight=700,
        fill=ROLES["decision"][2],
        anchor="middle",
    )


def chapter_2(svg: SVG) -> None:
    pressure_cards = (
        (104, "Fading automatic gains", "architecture must supply more"),
        (
            151,
            "Coupled design obligations",
            "workload + software + hardware + physical",
        ),
        (198, "Finite checking capacity", "simulation + EDA + verification + review"),
    )
    for y, title, sub in pressure_cards:
        svg.card(
            14,
            y,
            300,
            42,
            title,
            (sub,),
            role="constraint",
            title_size=14.5,
            body_size=11.5,
            title_offset=17,
            body_offset=35,
        )
    for y in (125, 172, 219):
        svg.line(f"M 314 {y} H 347 V 170 H 380", arrow=False)
    svg.line("M 347 170 H 380")
    svg.diamond(470, 170, 82, 57, role="constraint")
    svg.text(
        470,
        161,
        "NEXT-DECISION",
        size=14,
        weight=700,
        fill=ROLES["constraint"][2],
        anchor="middle",
    )
    svg.text(
        470,
        181,
        "BOTTLENECK",
        size=14,
        weight=700,
        fill=ROLES["constraint"][2],
        anchor="middle",
    )
    svg.line("M 552 170 H 596")
    svg.card(
        596,
        117,
        350,
        106,
        "Relieve the limiting work",
        (
            "point assistance / AI-native system",
            "conventional method / no added assistance",
            "authoritative checks remain",
        ),
        role="decision",
        title_size=16.5,
        body_size=13,
    )


def chapter_3(svg: SVG) -> None:
    stages = (
        ("Formulate", "scoped plan", "workload"),
        ("Explore", "legal candidates", "artifact"),
        ("Implement", "execution record", "method"),
        ("Evaluate", "checked comparison", "evidence"),
        ("Interpret & explain", "supported account", "evidence"),
        ("Review & decide", ("advance / revise", "reject / stop"), "decision"),
    )
    x, y, w, h, gap = 14, 111, 143, 83, 14
    centers: list[float] = []
    for index, (title, sub, role) in enumerate(stages):
        sx = x + index * (w + gap)
        centers.append(sx + w / 2)
        lines = sub if isinstance(sub, tuple) else (sub,)
        svg.card(
            sx,
            y,
            w,
            h,
            title,
            lines,
            role=role,
            title_size=14.5,
            body_size=11.5,
            center=True,
        )
        if index:
            flow_arrow(svg, sx - gap, sx, y + h / 2)
    svg.rect(72, 222, 816, 42, role="neutral", stroke=ROLES["artifact"][1])
    svg.text(
        480,
        240,
        "TARGETED REPAIR",
        size=13.5,
        weight=700,
        fill=ROLES["artifact"][2],
        anchor="middle",
    )
    svg.text(
        480,
        257,
        "re-enter the responsibility that owns the inadequacy; retain valid prior work",
        size=12.5,
        fill=MUTED,
        anchor="middle",
    )
    for cx in centers:
        svg.line(
            f"M {cx} 222 V 204", color=ROLES["artifact"][1], width=1.2, arrow=False
        )


def chapter_4(svg: SVG) -> None:
    svg.card(
        14,
        125,
        205,
        90,
        "Source-linked record",
        ("sources + checked observations", "knowledge + live state"),
        role="workload",
        title_size=15.5,
        body_size=12.5,
    )
    svg.card(
        282,
        111,
        250,
        118,
        "Task-specific representation",
        (
            "native + structured",
            "optional learned views",
            "linked to authoritative state",
        ),
        role="artifact",
        title_size=15,
        body_size=12.5,
    )
    svg.card(
        615,
        104,
        331,
        68,
        "Exposed to the method",
        ("legal actions + relationships + conditions",),
        role="evidence",
        title_size=15.5,
        body_size=12.5,
    )
    svg.card(
        615,
        187,
        331,
        68,
        "Declared blind spots",
        ("omissions + stale links + unverified effects",),
        role="constraint",
        title_size=15.5,
        body_size=12.5,
    )
    flow_arrow(svg, 219, 282, 170)
    svg.line("M 532 170 H 570 V 138 H 615")
    svg.line("M 570 170 V 221 H 615")
    svg.line("M 130 246 H 580", color=ROLES["artifact"][1], width=1.5, arrow=False)
    svg.text(
        355,
        267,
        "Persistent provenance: identity + version + lineage + cost + failures + access",
        size=12.5,
        weight=700,
        fill=ROLES["artifact"][2],
        anchor="middle",
    )


def chapter_5(svg: SVG) -> None:
    columns = (
        ("Affordable direct comparison", "DIRECT / NO ADDED AI", "neutral"),
        ("Expensive outcome measurement", "PREDICTION", "artifact"),
        ("Missing candidate artifact", "GENERATION", "method"),
        ("Too many legal alternatives", "OPTIMIZATION", "method"),
    )
    x, y, w, h, gap = 14, 111, 220, 92, 17
    for index, (title, method, role) in enumerate(columns):
        sx = x + index * (w + gap)
        svg.card(
            sx,
            y,
            w,
            h,
            title,
            (method,),
            role=role,
            title_size=13.2,
            body_size=13,
            center=True,
        )
    svg.rect(44, 226, 872, 42, role="neutral", stroke=ROLES["workload"][1])
    svg.text(
        480,
        244,
        "SMALLEST SUFFICIENT APPROACH",
        size=13.5,
        weight=700,
        fill=ROLES["workload"][2],
        anchor="middle",
    )
    svg.text(
        480,
        261,
        "combine only for distinct jobs; retain a named check, fallback, and stopping condition",
        size=12.5,
        fill=MUTED,
        anchor="middle",
    )


def chapter_6(svg: SVG) -> None:
    svg.card(
        14,
        142,
        118,
        70,
        "Authorized input",
        ("request", "+ pinned state"),
        role="workload",
        title_size=12.5,
        body_size=10.5,
        center=True,
        title_offset=18,
        body_offset=37,
        body_gap=15,
    )
    svg.rect(166, 103, 610, 148, role="workload", fill="#F7FBFC")
    svg.text(181, 124, "ENVIRONMENT", size=15.5, weight=700, fill=ROLES["workload"][2])
    svg.text(
        310,
        124,
        "observable state + allowed requests + reachable tools + expected returns",
        size=12,
        fill=MUTED,
    )
    svg.rect(234, 136, 486, 96, role="artifact", fill="#FAF8FD")
    svg.text(249, 156, "HARNESS", size=14.5, weight=700, fill=ROLES["artifact"][2])
    svg.text(
        337,
        156,
        "attempt identity + isolation + budgets + recovery",
        size=11.8,
        fill=MUTED,
    )
    svg.card(
        286,
        166,
        190,
        58,
        "Wrapper",
        ("validate + translate", "invoke + parse"),
        role="method",
        title_size=13.5,
        body_size=10.5,
        center=True,
        title_offset=18,
        body_offset=35,
        body_gap=14,
    )
    svg.card(
        513,
        166,
        160,
        58,
        "Tool / simulator",
        ("transformation or check",),
        role="neutral",
        title_size=13.5,
        body_size=10.5,
        center=True,
        title_offset=20,
        body_offset=43,
    )
    svg.card(
        810,
        136,
        136,
        82,
        "Execution record",
        ("status + artifacts", "cost + lineage"),
        role="evidence",
        title_size=13.5,
        body_size=11.5,
        center=True,
    )
    flow_arrow(svg, 132, 166, 177)
    flow_arrow(svg, 476, 513, 195)
    flow_arrow(svg, 776, 810, 177)
    svg.text(
        878,
        242,
        "qualification follows",
        size=10.5,
        weight=700,
        fill=ROLES["evidence"][2],
        anchor="middle",
    )


def chapter_7(svg: SVG) -> None:
    cards = (
        ("Returned signal", ("source + target + lineage", "conditions"), "neutral"),
        (
            "Verification",
            ("property-appropriate check", "uncertainty + assumptions"),
            "evidence",
        ),
        (
            "Claim boundary",
            ("supported / contradicted", "unresolved + nonclaims"),
            "constraint",
        ),
        ("Feedback route", ("repair / revise / retain", "rerun / stop"), "workload"),
        ("Learning retained", ("run + project + later work",), "artifact"),
    )
    x, y, w, h, gap = 14, 115, 171, 103, 21
    for index, (title, lines, role) in enumerate(cards):
        sx = x + index * (w + gap)
        svg.card(
            sx,
            y,
            w,
            h,
            title,
            lines,
            role=role,
            title_size=14.5,
            body_size=11.5,
            center=True,
        )
        if index:
            flow_arrow(svg, sx - gap, sx, y + h / 2)
    svg.text(
        480,
        249,
        "Signals and checks stay bound to the source, property, and claim they qualify",
        size=13,
        weight=700,
        fill=ROLES["evidence"][2],
        anchor="middle",
    )


def chapter_8(svg: SVG) -> None:
    svg.rect(14, 103, 932, 70, role="neutral", fill="#F8FAFB")
    svg.text(
        28,
        126,
        "PROSPECTIVE CACHE RECORD",
        size=13.5,
        weight=700,
        fill=ROLES["constraint"][2],
    )
    svg.card(
        242,
        111,
        280,
        54,
        "Declared comparison",
        ("cross-stack obligations; no retained execution",),
        role="artifact",
        title_size=14,
        body_size=11.5,
        center=True,
        title_offset=20,
        body_offset=42,
    )
    svg.card(
        600,
        111,
        322,
        54,
        "STOP BEFORE DISPATCH",
        ("outcome and mechanism unresolved",),
        role="constraint",
        title_size=14,
        body_size=11.5,
        center=True,
        title_offset=20,
        body_offset=42,
    )
    flow_arrow(svg, 522, 600, 138)

    svg.rect(14, 180, 932, 70, role="neutral", fill="#F8FAFB")
    svg.text(
        28,
        203,
        "RETAINED ARRAY RECORD",
        size=13.5,
        weight=700,
        fill=ROLES["evidence"][2],
    )
    svg.card(
        242,
        188,
        280,
        54,
        "Frozen local simulator sweep",
        ("PE array + on-chip traffic",),
        role="evidence",
        title_size=14,
        body_size=11.5,
        center=True,
        title_offset=20,
        body_offset=42,
    )
    svg.card(
        600,
        186,
        322,
        58,
        "LOCAL TECHNICAL STOP",
        ("tie; predicted reversal failed", "32x32 retained; authority pending"),
        role="decision",
        title_size=14,
        body_size=10.5,
        center=True,
        title_offset=18,
        body_offset=35,
        body_gap=14,
    )
    flow_arrow(svg, 522, 600, 215)
    svg.rect(170, 255, 620, 27, role="neutral", stroke=ROLES["constraint"][1])
    svg.text(
        480,
        274,
        "TWO SEPARATE RECORDS  -  NEITHER CLOSES A DESIGN LOOP",
        size=12,
        weight=700,
        fill=ROLES["constraint"][2],
        anchor="middle",
    )


def chapter_9(svg: SVG) -> None:
    cards = (
        ("Source record", ("versioned units", "+ supported conclusion"), "artifact"),
        ("Changed condition", ("decision / dependency", "/ interface"), "constraint"),
        ("Unit action", ("carry / update", "/ replace / retire"), "method"),
        ("Target checks", ("affected claims", "+ changed neighbors"), "evidence"),
        ("Target decision", ("supported anew", "/ unresolved"), "decision"),
    )
    x, y, w, h, gap = 14, 113, 171, 101, 21
    for index, (title, lines, role) in enumerate(cards):
        sx = x + index * (w + gap)
        svg.card(
            sx,
            y,
            w,
            h,
            title,
            lines,
            role=role,
            title_size=14.5,
            body_size=11.5,
            center=True,
        )
        if index:
            flow_arrow(svg, sx - gap, sx, y + h / 2)
    svg.rect(14, 233, 330, 35, role="neutral", stroke=ROLES["constraint"][1])
    svg.text(
        179,
        255,
        "Source conclusion stays with source conditions",
        size=12.5,
        weight=700,
        fill=ROLES["constraint"][2],
        anchor="middle",
    )
    svg.line("M 344 233 V 268", color=ROLES["constraint"][1], width=2.0, arrow=False)
    svg.text(
        635,
        255,
        "A change at any layer may reopen dependent claims",
        size=12.5,
        weight=700,
        fill=ROLES["evidence"][2],
        anchor="middle",
    )


def list_card(
    svg: SVG, x: float, y: float, w: float, title: str, rows: tuple[str, ...], role: str
) -> None:
    h = 118
    svg.rect(x, y, w, h, role=role)
    _, _, role_ink = ROLES[role]
    svg.text(x + 13, y + 24, title, size=14.5, weight=700, fill=role_ink)
    for index, row in enumerate(rows):
        svg.text(x + 13, y + 48 + index * 17, row, size=11.8, fill=MUTED)


def chapter_10(svg: SVG) -> None:
    svg.rect(14, 101, 932, 152, role="constraint", fill=WHITE, stroke_width=1.7)
    svg.text(
        28,
        121,
        "CHALLENGE ARTIFACT AND WORKFLOW",
        size=13,
        weight=700,
        fill=ROLES["constraint"][2],
    )
    svg.text(
        333,
        121,
        "varied conditions + red team + faults + interruption and recovery",
        size=11.8,
        fill=MUTED,
    )
    list_card(
        svg,
        28,
        132,
        275,
        "EVALUATION OBJECT",
        (
            "candidate design",
            "method / component",
            "configured technical system",
            "complete human + technical workflow",
        ),
        "artifact",
    )
    list_card(
        svg,
        327,
        132,
        292,
        "FOUR JUDGMENTS",
        (
            "architecture result",
            "decision and evidence quality",
            "total human + machine cost",
            "reliability of the advantage",
        ),
        "evidence",
    )
    list_card(
        svg,
        643,
        132,
        289,
        "MATCHED ALTERNATIVE",
        (
            "same task and checks",
            "same budgets",
            "same stopping rules",
            "strongest practical comparator",
        ),
        "workload",
    )
    svg.rect(165, 257, 630, 25, role="decision")
    svg.text(
        480,
        274,
        "QUALIFIED CLAIM: SUPPORTED / UNSUPPORTED / UNRESOLVED  -  ASSESSMENT, NOT COMMITMENT",
        size=11.2,
        weight=700,
        fill=ROLES["decision"][2],
        anchor="middle",
    )


def chapter_11(svg: SVG) -> None:
    svg.rect(
        14,
        101,
        932,
        168,
        role="neutral",
        fill="#F8FAFB",
        stroke=MUTED,
        stroke_width=1.7,
    )
    svg.text(28, 122, "ACCOUNTABLE ORGANIZATION", size=13.5, weight=700)
    svg.text(
        250,
        122,
        "assigns roles + supplies resources + owns product consequences",
        size=12,
        fill=MUTED,
    )
    svg.card(
        34,
        139,
        250,
        86,
        "Substantial design work",
        (
            "AI-native system + specialists",
            "formulate + generate + run",
            "interpret + recommend",
        ),
        role="method",
        title_size=15,
        body_size=10.5,
        body_offset=44,
        body_gap=14,
    )
    svg.card(
        329,
        139,
        320,
        86,
        "Architectural ownership",
        (
            "frame + bound + reconcile evidence",
            "state residual risk + reopen technical work",
        ),
        role="workload",
        title_size=15,
        body_size=11.5,
    )
    svg.line("M 649 182 H 735", width=3.0)
    svg.rect(735, 139, 190, 86, role="decision")
    svg.text(
        830,
        164,
        "NAMED COMMITMENT",
        size=13.5,
        weight=700,
        fill=ROLES["decision"][2],
        anchor="middle",
    )
    svg.text(
        830,
        184,
        "AUTHORITY",
        size=13.5,
        weight=700,
        fill=ROLES["decision"][2],
        anchor="middle",
    )
    svg.text(830, 207, "ADVANCE / HOLD / REJECT", size=10, fill=MUTED, anchor="middle")
    svg.text(
        692,
        168,
        "RECOMMENDS",
        size=8.8,
        weight=700,
        fill=ROLES["decision"][2],
        anchor="middle",
    )
    svg.rect(329, 238, 320, 22, role="evidence")
    svg.text(
        489,
        253,
        "MONITORING + CHANGED CONDITIONS",
        size=11.8,
        weight=700,
        fill=ROLES["evidence"][2],
        anchor="middle",
    )
    svg.line("M 489 238 V 226", color=ROLES["evidence"][1], width=1.6)


def chapter_12(svg: SVG) -> None:
    svg.card(
        54,
        104,
        852,
        63,
        "LOCAL PRACTICE NOW  -  NO CONSORTIUM REQUIRED",
        (
            "record total cost and lineage + retain failed attempts + run matched baselines",
        ),
        role="workload",
        title_size=15.5,
        body_size=12.5,
        center=True,
    )
    svg.line("M 480 167 V 190", color=ROLES["artifact"][1], width=1.5, arrow=False)
    svg.line("M 187 190 H 773", color=ROLES["artifact"][1], width=1.5, arrow=False)
    svg.add(
        '<rect x="254" y="170" width="452" height="23" fill="#FFFFFF" stroke="none"/>'
    )
    svg.text(
        480,
        186,
        "SHARED INFRASTRUCTURE  -  DEPENDENCY FOLLOWS THE CLAIM",
        size=13.5,
        weight=700,
        fill=ROLES["artifact"][2],
        anchor="middle",
    )
    shared = (
        (
            54,
            "Cross-team comparison",
            ("common record contracts", "comparable disclosures"),
        ),
        (
            347,
            "Physical or silicon claim",
            ("qualified path at named node", "and declared checks"),
        ),
        (640, "Public program", ("neutral rules + audit", "+ stewardship")),
    )
    for x, title, lines in shared:
        svg.card(
            x,
            198,
            266,
            72,
            title,
            lines,
            role="artifact",
            title_size=14.5,
            body_size=11.5,
            center=True,
            title_offset=22,
            body_offset=43,
            body_gap=15,
        )
    for cx in (187, 480, 773):
        svg.line(
            f"M {cx} 190 V 198", color=ROLES["artifact"][1], width=1.5, arrow=False
        )


DRAWERS = {
    1: chapter_1,
    2: chapter_2,
    3: chapter_3,
    4: chapter_4,
    5: chapter_5,
    6: chapter_6,
    7: chapter_7,
    8: chapter_8,
    9: chapter_9,
    10: chapter_10,
    11: chapter_11,
    12: chapter_12,
}


def render(chapter: Chapter) -> str:
    svg = SVG(chapter)
    svg.begin()
    DRAWERS[chapter.number](svg)
    return svg.finish()


def main() -> None:
    for chapter in CHAPTERS:
        target = chapter.target
        if target.exists() and any(
            marker in target.read_text(encoding="utf-8")
            for marker in ("<<<<<<<", "=======", ">>>>>>>")
        ):
            raise SystemExit(f"refusing to overwrite conflict markers in {target}")
        target.write_text(render(chapter), encoding="utf-8")
        print(target.relative_to(ROOT))


if __name__ == "__main__":
    main()
