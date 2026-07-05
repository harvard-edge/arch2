#!/usr/bin/env python3
"""Generate SVG figures from the corpus pilot tables."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

DEFAULT_INPUT = Path("data/processed/corpus-pilot/era_category_counts.csv")
DEFAULT_OUTPUT = Path("tmp/figures/F2-corpus-pilot-topic-shift.svg")

ERAS = ["early", "2005_2006", "2015", "latest"]
ERA_LABELS = {
    "early": "1970s-1990s",
    "2005_2006": "2005-2006",
    "2015": "2015",
    "latest": "2025-2026",
}
CATEGORIES = [
    ("memory", "Memory", "#4E79A7"),
    ("accelerators", "Accelerators", "#D88A30"),
    ("ai_ml", "AI/ML", "#54A24B"),
    ("verification_tools", "Verification/tools", "#7E6AA8"),
    ("datacenter_cloud", "Datacenter/cloud", "#C44E52"),
]
LABEL_THRESHOLD = 0.03


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def load_shares(path: Path) -> dict[tuple[str, str], float]:
    shares: dict[tuple[str, str], float] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            shares[(row["era"], row["category"])] = float(row["share"])
    return shares


def svg_text(
    x: float,
    y: float,
    text: str,
    size: int = 13,
    anchor: str = "start",
    weight: str = "400",
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="#222">{text}</text>'
    )


def make_svg(shares: dict[tuple[str, str], float]) -> str:
    width = 980
    height = 560
    margin_left = 88
    margin_right = 36
    margin_top = 84
    margin_bottom = 128
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    max_share = 0.40
    group_w = plot_w / len(ERAS)
    bar_w = 24
    gap = 7

    def y_pos(share: float) -> float:
        return margin_top + plot_h - (share / max_share) * plot_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img">',
        "<title>F2 corpus pilot topic shift</title>",
        "<desc>Pilot title-level topic signals across selected ISCA, MICRO, HPCA, and ASPLOS years.</desc>",
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        svg_text(
            34,
            38,
            "Pilot topic signals in architecture conference titles",
            22,
            weight="700",
        ),
        svg_text(
            34,
            62,
            "DBLP title metadata only; heuristic categories; use as directional evidence, not a final claim.",
            12,
        ),
    ]

    for tick in [0.0, 0.1, 0.2, 0.3, 0.4]:
        y = y_pos(tick)
        parts.append(
            f'<line x1="{margin_left}" y1="{y:.1f}" x2="{width - margin_right}" y2="{y:.1f}" stroke="#DDE5EA"/>'
        )
        parts.append(
            svg_text(margin_left - 12, y + 4, f"{int(tick * 100)}%", 12, anchor="end")
        )

    parts.append(
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_h}" stroke="#5A646B" stroke-width="1.1"/>'
    )
    parts.append(
        f'<line x1="{margin_left}" y1="{margin_top + plot_h}" x2="{width - margin_right}" y2="{margin_top + plot_h}" stroke="#5A646B" stroke-width="1.1"/>'
    )

    for era_index, era in enumerate(ERAS):
        group_x = margin_left + era_index * group_w
        start_x = (
            group_x
            + (group_w - (len(CATEGORIES) * bar_w + (len(CATEGORIES) - 1) * gap)) / 2
        )
        for cat_index, (category, _label, color) in enumerate(CATEGORIES):
            share = shares.get((era, category), 0.0)
            x = start_x + cat_index * (bar_w + gap)
            y = y_pos(share)
            h = margin_top + plot_h - y
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w}" height="{h:.1f}" fill="{color}"/>'
            )
            if share == 0.0:
                parts.append(
                    svg_text(
                        x + bar_w / 2,
                        margin_top + plot_h + 13,
                        "0%",
                        9,
                        anchor="middle",
                    )
                )
            elif share >= LABEL_THRESHOLD:
                parts.append(
                    svg_text(
                        x + bar_w / 2, y - 6, f"{share * 100:.0f}%", 10, anchor="middle"
                    )
                )
        parts.append(
            svg_text(
                group_x + group_w / 2,
                margin_top + plot_h + 28,
                ERA_LABELS[era],
                14,
                anchor="middle",
                weight="700",
            )
        )

    legend_x = margin_left
    legend_y = height - 70
    for index, (_category, label, color) in enumerate(CATEGORIES):
        x = legend_x + index * 170
        parts.append(
            f'<rect x="{x}" y="{legend_y}" width="14" height="14" fill="{color}"/>'
        )
        parts.append(svg_text(x + 22, legend_y + 12, label, 12))

    parts.append(
        svg_text(
            width - margin_right,
            height - 24,
            "Source: DBLP pilot metadata; see data/processed/corpus-pilot",
            11,
            anchor="end",
        )
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> int:
    args = parse_args()
    shares = load_shares(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(make_svg(shares), encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
