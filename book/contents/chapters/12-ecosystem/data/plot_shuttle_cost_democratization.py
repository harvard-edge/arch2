#!/usr/bin/env python3
"""
Chapter 12: open-shuttle submissions per Tiny Tapeout run (2022-2026).

Data: fig-shuttle-cost-democratization-submissions.csv, one row per run,
transcribed from the Tiny Tapeout shuttle catalog (https://tinytapeout.com/chips/,
snapshot 2026-08-22; see QueryTimestampUTC). Counts are submitted designs, not
fabricated or delivered chips. The cumulative series is computed here from the
per-run counts rather than read from the CSV's CumulativeDesignsCount column;
the script asserts that the two agree.

An earlier version of this figure carried a second panel of mask-set and
multi-project-wafer costs by node. Those values were hand-typed and not traceable
to per-row sources, so the panel was removed (2026-09-28 accuracy pass).
"""

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style  # noqa: E402

apply_style()


def _declare_font_stack(svg_path: Path) -> None:
    """Declare the font stack in the SVG for headless text rendering."""
    text = svg_path.read_text(encoding="utf-8")
    font_style = (
        '  <style type="text/css">text, tspan { font-family: Arial, '
        "Helvetica, sans-serif; }</style>\n"
    )
    if "</defs>" in text:
        text = text.replace("</defs>", font_style + "</defs>", 1)
    else:
        text = text.replace("<svg", "<svg><defs>\n" + font_style + "</defs>", 1)
    svg_path.write_text(
        "\n".join(line.rstrip() for line in text.splitlines()) + "\n", encoding="utf-8"
    )


def main() -> None:
    chapter_dir = REPO_ROOT / "book" / "contents" / "chapters" / "12-ecosystem"
    tt_csv = chapter_dir / "data" / "fig-shuttle-cost-democratization-submissions.csv"
    img_dir = chapter_dir / "images"
    out_svg = img_dir / "fig-shuttle-cost-democratization.svg"
    out_pdf = img_dir / "fig-shuttle-cost-democratization.pdf"
    out_png = img_dir / "fig-shuttle-cost-democratization.png"

    runs, dates, counts, groups, csv_cumul = [], [], [], [], []
    with open(tt_csv, "r", encoding="utf-8") as f:
        for row in csv.DictReader(line for line in f if not line.startswith("#")):
            runs.append(row["RunName"])
            y, m, _ = row["CloseDate"].split("-")
            dates.append(f"{m}/{y[2:]}")
            counts.append(int(row["SubmittedDesignsCount"]))
            csv_cumul.append(int(row["CumulativeDesignsCount"]))
            pdk = row["PDK"]
            if "SKY130" in pdk:
                groups.append("SKY130")
            elif "SG13G2" in pdk:
                groups.append("SG13G2")
            else:
                groups.append("GF180MCU")

    cumul = np.cumsum(counts)
    assert list(cumul) == csv_cumul, "CSV cumulative column disagrees with per-run sum"

    style = {
        "SKY130": (COLORS["workload"], "", "SkyWater SKY130 (130 nm)"),
        "SG13G2": (COLORS["evidence"], "////", "IHP SG13G2 (130 nm BiCMOS)"),
        "GF180MCU": (COLORS["methods"], "....", "GlobalFoundries GF180MCU (180 nm)"),
    }

    fig, ax = plt.subplots(figsize=(5.0, 3.3))
    x = np.arange(len(runs))
    for xi, c, g in zip(x, counts, groups):
        color, hatch, _ = style[g]
        ax.bar(
            xi,
            c,
            width=0.68,
            color=color,
            alpha=0.9,
            hatch=hatch,
            edgecolor=COLORS["ink"],
            linewidth=0.35,
            zorder=3,
        )
    ax.set_ylim(0, 700)
    ax.set_ylabel("Designs submitted per run", fontsize=6.8, color=COLORS["ink"])
    ax.grid(True, axis="y", color=COLORS["grid"], linewidth=0.45, zorder=0)
    ax.grid(False, axis="x")
    ax.set_xlim(-0.7, len(runs) - 0.3)
    ax.set_xticks(x)
    ax.set_xticklabels(
        [f"{r} ({d})" for r, d in zip(runs, dates)],
        rotation=60,
        ha="right",
        fontsize=4.6,
        color=COLORS["ink"],
    )
    ax.tick_params(axis="y", labelsize=5.8)

    ax2 = ax.twinx()
    ax2.plot(
        x,
        cumul,
        color=COLORS["constraints"],
        marker="o",
        markersize=2.2,
        linewidth=1.0,
        zorder=5,
    )
    ax2.set_ylim(0, 4700)
    ax2.set_ylabel(
        "Cumulative designs submitted",
        fontsize=6.8,
        color=COLORS["constraints_ink"],
        labelpad=4,
    )
    ax2.tick_params(axis="y", colors=COLORS["constraints_ink"], labelsize=5.8)
    ax2.spines["right"].set_visible(True)

    ax2.annotate(
        f"{cumul[-1]:,} submitted\nacross {len(runs)} runs",
        xy=(x[-1], cumul[-1]),
        xytext=(x[-1] - 5.8, 4350),
        arrowprops=dict(arrowstyle="->", color=COLORS["constraints"], linewidth=0.6),
        fontsize=5.4,
        color=COLORS["constraints_ink"],
        ha="left",
        va="center",
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="white",
            edgecolor=COLORS["constraints"],
            linewidth=0.5,
            alpha=0.95,
        ),
        zorder=6,
    )

    handles = [
        Patch(
            facecolor=style[k][0],
            hatch=style[k][1],
            edgecolor=COLORS["ink"],
            linewidth=0.35,
            label=style[k][2],
        )
        for k in ("SKY130", "SG13G2", "GF180MCU")
    ]
    handles.append(
        plt.Line2D(
            [0],
            [0],
            color=COLORS["constraints"],
            marker="o",
            markersize=2.2,
            linewidth=1.0,
            label="Cumulative (right axis)",
        )
    )
    ax.legend(
        handles=handles,
        loc="upper left",
        fontsize=5.2,
        framealpha=0.95,
        edgecolor=COLORS["grid"],
    )

    fig.tight_layout()
    for out in (out_svg, out_pdf, out_png):
        fig.savefig(out, dpi=300, bbox_inches="tight")
    _declare_font_stack(out_svg)
    print(
        f"runs={len(runs)} total={cumul[-1]} max={max(counts)} "
        f"({runs[counts.index(max(counts))]}) first={counts[0]}"
    )


if __name__ == "__main__":
    main()
