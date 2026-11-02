#!/usr/bin/env python3
"""Plot ArchEval feedback settings against token cost for chapter 10.

Inputs: chapter10-archeval-settings.csv, chapter10-archeval-l3-per-challenge.csv.
Output: book/contents/chapters/10-evaluation/images/fig-ch10-archeval-feedback-cost.*
"""
import csv
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from book._python.plots import (
    COLORS,
    FONT_SIZES,
    apply_style,
    save_figure_bundle,
)  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = (
    ROOT / "book/contents/chapters/10-evaluation/images/fig-ch10-archeval-feedback-cost"
)
AGENTS = [
    ("GPT-5.5 + Codex", "GPT-5.5", "o", COLORS["workload"]),
    ("MiniSWE + Gemini 3.5 Flash", "Gemini 3.5 Flash", "s", COLORS["designspace"]),
    ("MiniSWE + Gemma 4 31B", "Gemma 4 31B", "^", COLORS["methods"]),
    ("MiniSWE + Gemini 3.1 Flash-Lite", "Flash-Lite", "D", COLORS["constraints"]),
]


LABEL_OFFSETS = {
    ("GPT-5.5", "L2"): (-3, 5),
    ("GPT-5.5", "L1"): (5, -7),
    ("Gemini 3.5 Flash", "L1"): (-5, -8),
    ("Gemini 3.5 Flash", "L2"): (5, 2),
}


def rows(name):
    with open(HERE / name, encoding="utf-8") as fh:
        return list(csv.DictReader(l for l in fh if not l.startswith("#")))


def main():
    settings = rows("chapter10-archeval-settings.csv")
    l3 = rows("chapter10-archeval-l3-per-challenge.csv")
    apply_style()
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(6.2, 2.9), gridspec_kw={"width_ratios": [1.15, 1]}
    )
    fig.subplots_adjust(left=0.08, right=0.985, top=0.9, bottom=0.17, wspace=0.26)

    for agent, short, marker, color in AGENTS:
        pts = {r["setting"]: r for r in settings if r["agent"] == agent}
        xs = [float(pts[s]["mean_mtok"]) for s in ("L1", "L2", "L3")]
        ys = [float(pts[s]["geomean_norm_perf"]) for s in ("L1", "L2", "L3")]
        ax1.plot(xs, ys, color=color, lw=1.0, zorder=2)
        for s, x, y in zip(("L1", "L2", "L3"), xs, ys):
            filled = s != "L3"
            ax1.scatter(
                [x],
                [y],
                marker=marker,
                s=26,
                zorder=3,
                edgecolor=color,
                linewidth=0.9,
                facecolor=color if filled else "white",
            )
            dx, dy = LABEL_OFFSETS.get((short, s), (4, 3))
            ax1.annotate(
                s,
                (x, y),
                textcoords="offset points",
                xytext=(dx, dy),
                ha="right" if dx < 0 else "left",
                fontsize=FONT_SIZES["note"],
                color=COLORS["muted"],
                zorder=4,
            )
        ax1.plot([], [], color=color, marker=marker, ms=3.5, lw=1.0, label=short)
    ax1.axhline(1.0, color=COLORS["muted"], lw=0.7, ls=(0, (4, 3)), zorder=1)
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(0.1, 7)
    ax1.set_ylim(0.3, 3.2)
    ax1.set_xticks([0.1, 0.3, 1, 3])
    ax1.set_xticklabels(["0.1", "0.3", "1", "3"])
    ax1.set_yticks([0.5, 1, 2])
    ax1.set_yticklabels(["0.5×", "1×", "2×"])
    ax1.minorticks_off()
    ax1.set_xlabel("Mean tokens per run (millions)", fontsize=FONT_SIZES["label"])
    ax1.set_ylabel("Geometric mean vs. baseline", fontsize=FONT_SIZES["label"])
    ax1.legend(
        loc="lower right", frameon=False, fontsize=FONT_SIZES["note"], handlelength=1.6
    )

    for i, (agent, short, marker, color) in enumerate(AGENTS):
        vals = [
            float(r["norm_perf"])
            for r in l3
            if r["agent"] == agent and r["norm_perf"] != "hf"
        ]
        offsets = [i + 0.26 * math.sin(j * 2.4) * 0.8 for j in range(len(vals))]
        ax2.scatter(
            offsets,
            vals,
            marker=marker,
            s=11,
            facecolor="white",
            edgecolor=color,
            linewidth=0.7,
            zorder=3,
        )
        gm = math.exp(sum(math.log(v) for v in vals) / len(vals))
        ax2.plot([i - 0.32, i + 0.32], [gm, gm], color=COLORS["ink"], lw=1.3, zorder=4)
    ax2.axhline(1.0, color=COLORS["muted"], lw=0.7, ls=(0, (4, 3)), zorder=1)
    ax2.set_yscale("log")
    ax2.set_ylim(0.01, 10)
    ax2.set_yticks([0.01, 0.1, 1, 10])
    ax2.set_yticklabels(["0.01×", "0.1×", "1×", "10×"])
    ax2.minorticks_off()
    ax2.set_xticks(range(4))
    ax2.set_xticklabels(
        [a[1].replace(" ", "\n", 1) if a[1] != "GPT-5.5" else a[1] for a in AGENTS],
        fontsize=FONT_SIZES["note"],
    )
    ax2.set_xlim(-0.6, 3.6)
    ax2.set_ylabel("L3 result per challenge vs. baseline", fontsize=FONT_SIZES["label"])

    for ax, tag in ((ax1, "(a)"), (ax2, "(b)")):
        ax.text(
            -0.02,
            1.04,
            tag,
            transform=ax.transAxes,
            fontsize=7,
            fontweight="bold",
            color=COLORS["ink"],
        )
        ax.tick_params(
            axis="both", labelsize=FONT_SIZES["tick"], length=2.5, width=0.6, pad=2
        )
        ax.grid(True, color=COLORS["row"], linewidth=0.4, zorder=0)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
    save_figure_bundle(fig, OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
