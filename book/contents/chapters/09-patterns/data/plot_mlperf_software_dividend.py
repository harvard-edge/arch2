"""
Vendor-reported software gains on unchanged accelerators (Chapter 9)
--------------------------------------------------------------------
Plots per-accelerator MLPerf Training speedups that NVIDIA reports for the same
accelerator across two benchmark rounds. Every plotted value is read from
fig-ch09-mlperf-software-dividend.csv, which carries a source key, URL, and the
quoted sentence or table cell for each row. Nothing is computed or typed here.

Replaces an earlier generator whose coordinates were in-script literals and whose
generational-step panel had no data behind it (see data/datasets/provenance.yml,
chapter9-mlperf-software-dividend.csv defects).

Writes SVG, PDF, and 300 DPI PNG to
book/contents/chapters/09-patterns/images/fig-ch09-mlperf-software-dividend.*
"""

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style, save_figure_bundle

apply_style()

CHAPTER_DIR = Path(__file__).resolve().parents[1]
CSV_PATH = Path(__file__).resolve().parent / "fig-ch09-mlperf-software-dividend.csv"
OUT_BASE = CHAPTER_DIR / "images" / "fig-ch09-mlperf-software-dividend"


def load_rows():
    with open(CSV_PATH, encoding="utf-8") as f:
        return list(csv.DictReader(line for line in f if not line.startswith("#")))


def main():
    rows = load_rows()
    groups = []
    for r in rows:
        key = (r["accelerator"], r["from_round"], r["to_round"])
        if key not in [g[0] for g in groups]:
            groups.append((key, []))
        next(g for g in groups if g[0] == key)[1].append(r)

    group_style = {
        "NVIDIA A100": (COLORS["blue"], COLORS["workload_ink"], ""),
        "NVIDIA H100": (COLORS["purple"], COLORS["designspace_ink"], "///"),
    }

    fig, ax = plt.subplots(figsize=(5.0, 3.1))
    y = 0.0
    yticks, ylabels, header_y = [], [], []
    for (accel, r0, r1), members in groups:
        header_y.append(
            (
                y,
                f"{accel.replace('NVIDIA ', '')}: {r0.replace('Training ', '')} to {r1.replace('Training ', '')}",
            )
        )
        y -= 0.85
        mark, ink, hatch = group_style[accel]
        for r in sorted(members, key=lambda m: -float(m["speedup"])):
            s = float(r["speedup"])
            ax.barh(
                y,
                s - 1.0,
                left=1.0,
                height=0.62,
                color=mark,
                edgecolor=ink,
                linewidth=0.6,
                hatch=hatch,
                zorder=3,
            )
            ax.text(
                s + 0.03,
                y,
                f"{s:.2f}x",
                va="center",
                ha="left",
                fontsize=5.8,
                color=COLORS["ink"],
                zorder=5,
            )
            yticks.append(y)
            ylabels.append(r["workload"])
            y -= 0.85
        y -= 0.45

    for hy, label in header_y:
        ax.text(
            1.02,
            hy,
            label,
            va="center",
            ha="left",
            fontsize=6.4,
            fontweight="bold",
            color=COLORS["ink"],
        )

    ax.set_yticks(yticks)
    ax.set_yticklabels(ylabels, fontsize=5.8)
    ax.set_xlim(1.0, 3.05)
    ax.set_ylim(y + 0.4, 0.55)
    ax.axvline(1.0, color=COLORS["muted"], linewidth=0.8, zorder=4)
    ax.set_xlabel(
        "Per-accelerator time-to-train speedup on the same accelerator (x)",
        fontsize=6.8,
    )
    ax.grid(axis="x", color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax.grid(axis="y", visible=False)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="x", labelsize=5.8)
    ax.tick_params(axis="y", length=0)

    fig.tight_layout()
    save_figure_bundle(fig, OUT_BASE)
    plt.close(fig)
    print(f"wrote {OUT_BASE}.{{svg,pdf,png}}")


if __name__ == "__main__":
    main()
