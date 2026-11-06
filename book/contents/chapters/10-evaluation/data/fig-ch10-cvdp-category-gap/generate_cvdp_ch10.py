#!/usr/bin/env python3
"""Plot CVDP pass@1 by task category for chapter 10.

Input: chapter10-cvdp-category-pass1.csv.
Output: book/contents/chapters/10-evaluation/images/fig-ch10-cvdp-category-gap.*
"""
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT))
from book._python.plots import (
    COLORS,
    FONT_SIZES,
    apply_style,
    save_figure_bundle,
)  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = ROOT / "book/contents/chapters/10-evaluation/images/fig-ch10-cvdp-category-gap"
CATEGORIES = [
    ("cid16", "Debugging", COLORS["evidence"]),
    ("cid03", "Specification to RTL", COLORS["designspace"]),
    ("cid04", "RTL modification", COLORS["designspace"]),
    ("cid07", "Lint and QoR improvement", COLORS["designspace"]),
    ("cid02", "RTL completion", COLORS["designspace"]),
    ("cid12", "Testbench stimulus", COLORS["evidence"]),
    ("cid14", "Assertion generation", COLORS["evidence"]),
    ("cid13", "Testbench checker", COLORS["evidence"]),
]
BEST = "Claude 3.7 Sonnet"


def main():
    with open(HERE / "chapter10-cvdp-category-pass1.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(l for l in fh if not l.startswith("#")))
    apply_style()
    fig, ax = plt.subplots(figsize=(5.4, 2.7))
    fig.subplots_adjust(left=0.27, right=0.97, top=0.97, bottom=0.15)
    for y, (cid, label, color) in enumerate(CATEGORIES):
        pts = [r for r in rows if r["category_id"] == cid]
        vals = [float(r["pass_at_1_pct"]) for r in pts]
        ax.plot(
            [min(vals), max(vals)],
            [y, y],
            color=COLORS["grid"],
            lw=2.6,
            zorder=1,
            solid_capstyle="round",
        )
        ax.scatter(
            vals,
            [y] * len(vals),
            s=13,
            facecolor="white",
            edgecolor=COLORS["muted"],
            linewidth=0.7,
            zorder=2,
        )
        best = next(float(r["pass_at_1_pct"]) for r in pts if r["model"] == BEST)
        ax.scatter([best], [y], s=26, marker="D", color=color, zorder=3)
        n = pts[0]["n_problems"]
        ax.text(
            66.5,
            y,
            f"n = {n}",
            va="center",
            ha="right",
            fontsize=FONT_SIZES["note"],
            color=COLORS["muted"],
        )
    ax.scatter(
        [],
        [],
        s=13,
        facecolor="white",
        edgecolor=COLORS["muted"],
        linewidth=0.7,
        label="Eight evaluated models",
    )
    ax.scatter(
        [], [], s=24, marker="D", color=COLORS["muted"], label=BEST + " (best overall)"
    )
    ax.set_yticks(range(len(CATEGORIES)))
    ax.set_yticklabels([c[1] for c in CATEGORIES], fontsize=FONT_SIZES["tick"])
    ax.invert_yaxis()
    ax.set_xlim(0, 67)
    ax.set_ylim(len(CATEGORIES) + 0.55, -0.6)
    ax.set_xlabel("pass@1 (%), five samples per problem", fontsize=FONT_SIZES["label"])
    ax.tick_params(
        axis="both", labelsize=FONT_SIZES["tick"], length=2.5, width=0.6, pad=2
    )
    ax.grid(True, axis="x", color=COLORS["row"], linewidth=0.4, zorder=0)
    ax.legend(
        loc="lower center",
        ncol=2,
        frameon=False,
        fontsize=FONT_SIZES["note"],
        handletextpad=0.2,
        columnspacing=1.2,
        borderaxespad=0.0,
    )
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    save_figure_bundle(fig, OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
