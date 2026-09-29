#!/usr/bin/env python3
"""
Generate fig-lifecycle-defect-latency: time to close issues in three open
hardware repositories, grouped by the issue category recorded in the dataset.

Every value comes from data/datasets/chapter3-silicon-lifecycle-empirical-issues.csv,
which lists 4,564 closed GitHub issues (one URL per row) from lowRISC/opentitan,
The-OpenROAD-Project/OpenROAD, and ucb-bar/chipyard with their created and closed
timestamps. The script plots the median and interquartile range of close time
per category and prints the counts and medians quoted in the chapter. No values
are typed in this script.

What the data does not show: categories come from repository labels and title
tags, each category belongs to one repository, most issues are not labeled as
bugs, and nothing records where a problem was introduced. The figure therefore
compares close times by category; it does not measure defect escape across
lifecycle stages.

Adheres to .claude/rules/figures.md: apply_style() and COLORS from
book/_python/plots.py, marker shape (not only color) encodes repository, and
SVG/PDF/PNG twins are exported.
"""

import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style  # noqa: E402

apply_style()

DATA = (
    REPO_ROOT / "data" / "datasets" / "chapter3-silicon-lifecycle-empirical-issues.csv"
)
IMG = Path(__file__).resolve().parent
STEM = "fig-lifecycle-defect-latency"

# Categories too broad to say anything about where in the flow an issue sits.
EXCLUDE = {"Other/Unassigned", "General Infrastructure & Docs"}
MIN_N = 20

REPO_STYLE = {
    "lowRISC/opentitan": ("OpenTitan", "o", COLORS["workload"], COLORS["workload_ink"]),
    "The-OpenROAD-Project/OpenROAD": (
        "OpenROAD",
        "s",
        COLORS["methods"],
        COLORS["methods_ink"],
    ),
    "ucb-bar/chipyard": (
        "Chipyard",
        "^",
        COLORS["designspace"],
        COLORS["designspace_ink"],
    ),
}


def clean_label(label: str) -> str:
    """Drop the dataset's 'Stage N:' prefix, which does not match the book's stages."""
    return re.sub(r"^Stage \d+:\s*", "", label)


def main():
    df = pd.read_csv(DATA)
    total = len(df)
    bugs = int(df["IsBug"].astype(str).str.lower().eq("true").sum())
    print(f"issues={total} labeled_bug={bugs} ({100 * bugs / total:.1f}%)")
    print(df["Repository"].value_counts().to_string())

    rows = []
    for (cat, repo), g in df.groupby(["LifecycleStage", "Repository"]):
        if cat in EXCLUDE or len(g) < MIN_N:
            continue
        q = g["DurationDays"].quantile([0.25, 0.5, 0.75])
        rows.append(
            dict(
                cat=clean_label(cat),
                repo=repo,
                n=len(g),
                p25=q[0.25],
                med=q[0.5],
                p75=q[0.75],
            )
        )
    tab = pd.DataFrame(rows).sort_values("med").reset_index(drop=True)
    print(tab.round(1).to_string())

    fig, ax = plt.subplots(figsize=(4.8, 3.6))
    fig.subplots_adjust(left=0.42, right=0.97, top=0.97, bottom=0.2)

    for i, r in tab.iterrows():
        _, marker, mark, ink = REPO_STYLE[r.repo]
        ax.hlines(i, r.p25, r.p75, color=mark, lw=2.2, alpha=0.45, zorder=2)
        ax.plot(
            r.med,
            i,
            marker=marker,
            ms=4.2,
            color=mark,
            markeredgecolor=ink,
            markeredgewidth=0.6,
            zorder=3,
        )
        ax.text(
            r.p75 * 1.12,
            i,
            f"{r.med:.0f} d",
            va="center",
            ha="left",
            fontsize=5.2,
            color=COLORS["ink"],
            zorder=4,
        )

    ax.set_yticks(range(len(tab)))
    ax.set_yticklabels([f"{r.cat} (n={r.n})" for r in tab.itertuples()], fontsize=5.4)
    ax.set_xscale("log")
    ax.set_xlim(0.5, 2000)
    ax.set_ylim(-0.7, len(tab) - 0.3)
    ax.set_xlabel("Days from issue opened to closed (log scale)")
    ax.grid(axis="x", color=COLORS["grid"], lw=0.5)
    ax.grid(axis="y", visible=False)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    handles = [
        Line2D([], [], marker=m, ls="", color=c, markeredgecolor=k, ms=4.2, label=name)
        for name, m, c, k in REPO_STYLE.values()
    ]
    handles.append(
        Line2D(
            [],
            [],
            color=COLORS["muted"],
            lw=2.2,
            alpha=0.45,
            label="25th to 75th percentile",
        )
    )
    ax.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.3, -0.13),
        ncol=4,
        frameon=False,
        fontsize=5.4,
        handletextpad=0.3,
        columnspacing=1.0,
    )

    for ext in ("svg", "pdf", "png"):
        fig.savefig(IMG / f"{STEM}.{ext}", dpi=300, bbox_inches="tight")
    print("wrote", [str(IMG / f"{STEM}.{e}") for e in ("svg", "pdf", "png")])


if __name__ == "__main__":
    main()
