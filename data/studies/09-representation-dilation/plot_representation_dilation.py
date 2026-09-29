#!/usr/bin/env python3
"""Draw fig-hardware-representation-dilation from the measured CSV.

(a) Mean declaration-to-use distance in token order against file length.
(b) Mean path length between the same pairs in pyslang's syntax tree, on the
    same axes, with the one-edge def-use graph distance marked.

Every plotted value is read from the CSV that measure_representation_dilation.py
writes. The fit and its band are recomputed here with the same seed.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

STUDY_DIR = Path(__file__).resolve().parent
REPO_ROOT = STUDY_DIR.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import (
    COLORS,
    apply_style,
    clean_spines,
    save_figure_bundle,
)  # noqa: E402

CHAPTER = REPO_ROOT / "book/contents/chapters/04-representations"
INPUT_CSV = CHAPTER / "data" / "fig-hardware-representation-dilation.csv"
DEFAULT_OUTPUT_BASE = CHAPTER / "images" / "fig-hardware-representation-dilation"

BOOTSTRAP_REPS = 10_000
BOOTSTRAP_SEED = 20260929

# Shape identifies the corpus; fill identifies the group (hollow = benchmark),
# so the figure reads in grayscale. Hue repeats the group for color readers.
STYLE = {
    "VerilogEval": ("o", "benchmark"),
    "RTLLM": ("s", "benchmark"),
    "BaseJump STL": ("^", "production"),
    "SERV": ("D", "production"),
    "Ibex": ("v", "production"),
    "PicoRV32": ("*", "production"),
}
GROUP_COLOR = {"benchmark": COLORS["methods"], "production": COLORS["designspace"]}
GROUP_INK = {
    "benchmark": COLORS["methods_ink"],
    "production": COLORS["designspace_ink"],
}


def read_rows() -> list[dict]:
    with INPUT_CSV.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(l for l in fh if not l.startswith("#")))
    return [r for r in rows if r["status"] == "measured"]


def fit_with_band(x: np.ndarray, y: np.ndarray, grid: np.ndarray):
    slope, intercept = np.polyfit(x, y, 1)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    preds = np.empty((BOOTSTRAP_REPS, grid.size))
    slopes = np.empty(BOOTSTRAP_REPS)
    for b in range(BOOTSTRAP_REPS):
        idx = rng.integers(0, x.size, x.size)
        s, i = np.polyfit(x[idx], y[idx], 1)
        slopes[b] = s
        preds[b] = s * grid + i
    lo, hi = np.percentile(preds, [2.5, 97.5], axis=0)
    s_lo, s_hi = np.percentile(slopes, [2.5, 97.5])
    return slope, intercept, lo, hi, s_lo, s_hi


def scatter(ax, rows: list[dict], y_key: str) -> None:
    for corpus, (marker, group) in STYLE.items():
        pts = [r for r in rows if r["corpus"] == corpus and r[y_key] != ""]
        hollow = group == "benchmark"
        ax.scatter(
            [float(r["tokens"]) for r in pts],
            [float(r[y_key]) for r in pts],
            marker=marker,
            s=30 if marker == "*" else 11,
            facecolors="none" if hollow else GROUP_COLOR[group],
            edgecolors=GROUP_COLOR[group] if hollow else COLORS["ink"],
            linewidths=0.6 if hollow else 0.25,
            alpha=0.85,
            zorder=3,
        )


def draw_fit(ax, rows: list[dict], y_key: str, label_xy, ha: str) -> None:
    pts = [r for r in rows if r[y_key] != ""]
    x = np.log10([float(r["tokens"]) for r in pts])
    y = np.log10([float(r[y_key]) for r in pts])
    grid = np.linspace(x.min(), x.max(), 60)
    slope, intercept, lo, hi, s_lo, s_hi = fit_with_band(x, y, grid)
    ax.fill_between(
        10**grid, 10**lo, 10**hi, color=COLORS["grid"], alpha=0.9, zorder=1, lw=0
    )
    ax.plot(
        10**grid,
        10 ** (slope * grid + intercept),
        color=COLORS["ink"],
        lw=0.9,
        zorder=4,
    )
    ax.annotate(
        f"log-log slope {slope:.2f}\n95% CI {s_lo:.2f} to {s_hi:.2f}",
        xy=label_xy,
        xycoords="axes fraction",
        ha=ha,
        va="top",
        fontsize=5.6,
        color=COLORS["ink"],
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor="white",
            edgecolor=COLORS["grid"],
            alpha=0.92,
            lw=0.6,
        ),
        zorder=5,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-base", type=Path, default=DEFAULT_OUTPUT_BASE)
    args = ap.parse_args()

    apply_style()
    rows = read_rows()
    fig, axes = plt.subplots(1, 2, figsize=(4.8, 2.55), sharex=True, sharey=True)
    ylim = (0.5, 4e5)
    xlim = (8, 4e5)

    ax = axes[0]
    scatter(ax, rows, "mean_token_distance")
    draw_fit(ax, rows, "mean_token_distance", (0.04, 0.96), "left")
    ax.set_title("(a) Token order", loc="left", pad=4)
    ax.set_ylabel("Mean declaration-to-use distance (tokens)")

    ax = axes[1]
    scatter(ax, rows, "mean_tree_distance")
    draw_fit(ax, rows, "mean_tree_distance", (0.04, 0.96), "left")
    ax.axhline(1, color=COLORS["evidence_ink"], lw=0.9, ls=(0, (4, 2)), zorder=2)
    ax.text(
        11,
        1.3,
        "def-use graph, 1 edge per pair by construction",
        ha="left",
        va="bottom",
        fontsize=5.6,
        color=COLORS["evidence_ink"],
        zorder=5,
    )
    ax.set_title("(b) Syntax tree", loc="left", pad=4)
    ax.set_ylabel("Mean declaration-to-use path (tree edges)")

    for ax in axes:
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_xlabel("File length (tokens)")
        ax.grid(True, which="major", color=COLORS["grid"], linewidth=0.5, zorder=0)
        clean_spines(ax)
    axes[1].tick_params(labelleft=True)

    handles = []
    for corpus, (marker, group) in STYLE.items():
        hollow = group == "benchmark"
        n = sum(r["corpus"] == corpus for r in rows)
        handles.append(
            Line2D(
                [],
                [],
                linestyle="none",
                marker=marker,
                markersize=6 if marker == "*" else 4,
                markerfacecolor="none" if hollow else GROUP_COLOR[group],
                markeredgecolor=GROUP_COLOR[group] if hollow else COLORS["ink"],
                markeredgewidth=0.7 if hollow else 0.3,
                label=f"{corpus} ({n})",
            )
        )
    fig.legend(
        handles=handles,
        loc="lower center",
        ncol=3,
        frameon=False,
        bbox_to_anchor=(0.5, 0.0),
        columnspacing=1.2,
        handletextpad=0.3,
        title="Hollow: benchmark reference RTL.  Filled: production-oriented RTL.",
        title_fontsize=5.6,
    )
    fig.tight_layout(rect=(0, 0.15, 1, 1), w_pad=1.6)
    paths = save_figure_bundle(fig, args.output_base)
    for p in paths.values():
        print(p)


if __name__ == "__main__":
    main()
