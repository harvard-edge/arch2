#!/usr/bin/env python3
"""
Generate fig-demonstration-ceiling: playing strength of AlphaGo versions.

Every value comes from data/datasets/chapter1-alphago-elo.csv, which transcribes
the Elo ratings Silver et al. (Nature 2017) report from one 5 s per move
tournament (text accompanying their Fig. 6b). The figure separates versions that
started from human expert games from versions trained only by self-play against
the rules of the game. No values are typed in this script.

Adheres to .claude/rules/figures.md: apply_style() and COLORS from
book/_python/plots.py, color is never the only channel (hatching marks human
data), and SVG/PDF/PNG twins are exported.
"""

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator
from matplotlib.patches import Patch

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style  # noqa: E402

apply_style()

DATA = REPO_ROOT / "data" / "datasets" / "chapter1-alphago-elo.csv"


def load_rows():
    with DATA.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["elo"] = int(row["elo"])
        row["human"] = row["human_data"].strip().lower() == "yes"
    return sorted(rows, key=lambda r: r["elo"])


def main():
    img_dir = REPO_ROOT / "book" / "contents" / "chapters" / "01-moonshot" / "images"
    out_svg = img_dir / "fig-demonstration-ceiling.svg"
    out_pdf = img_dir / "fig-demonstration-ceiling.pdf"
    out_png = img_dir / "fig-demonstration-ceiling.png"

    rows = load_rows()
    names = [r["system"] for r in rows]
    elos = [r["elo"] for r in rows]
    human_style = dict(
        color=COLORS["methods"], edgecolor=COLORS["methods_ink"], hatch="////"
    )
    self_style = dict(color=COLORS["evidence"], edgecolor=COLORS["evidence_ink"])

    fig, ax = plt.subplots(figsize=(4.8, 2.3))
    fig.subplots_adjust(left=0.22, right=0.97, top=0.95, bottom=0.2)

    for i, row in enumerate(rows):
        style = human_style if row["human"] else self_style
        ax.barh(i, row["elo"], height=0.6, linewidth=0.6, zorder=3, **style)
        ax.text(
            row["elo"] + 60,
            i,
            f"{row['elo']:,}",
            va="center",
            ha="left",
            fontsize=5.8,
            color=COLORS["ink"],
            zorder=5,
        )

    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(names, fontsize=6.2)
    top = max(elos)
    ax.set_xlim(0, top * 1.14)
    ax.xaxis.set_major_locator(MultipleLocator(1000))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v):,}"))
    ax.set_xlabel("Elo rating (5 s per move tournament)", fontsize=6.6)
    ax.grid(axis="x", color=COLORS["grid"], linewidth=0.55, zorder=0)
    ax.grid(axis="y", visible=False)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    handles = [
        Patch(
            facecolor=COLORS["methods"],
            edgecolor=COLORS["methods_ink"],
            hatch="////",
            label="Started from human expert games",
        ),
        Patch(
            facecolor=COLORS["evidence"],
            edgecolor=COLORS["evidence_ink"],
            label="Self-play only, no human data",
        ),
    ]
    ax.legend(
        handles=handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.0),
        ncol=2,
        fontsize=5.8,
        frameon=False,
        facecolor="white",
        edgecolor=COLORS["grid"],
        framealpha=0.95,
    )

    fig.savefig(out_svg, format="svg", bbox_inches="tight")
    fig.savefig(out_pdf, format="pdf", bbox_inches="tight")
    fig.savefig(out_png, format="png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    for path in (out_svg, out_pdf, out_png):
        print(f"Generated: {path}")


if __name__ == "__main__":
    main()
