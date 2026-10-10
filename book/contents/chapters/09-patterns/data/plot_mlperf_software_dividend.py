"""Reconciled H100 MLPerf Training version-pair results (Chapter 9).

Published time-to-train values and exact submission IDs are retained in
fig-ch09-mlperf-software-dividend.csv. Speedups are calculated from those
values, not from vendor-rounded percentages. The GPU model and count match;
the preview metadata cannot establish identity of the complete machine.
NVIDIA's software attribution is separate from the measured comparison.

Writes SVG, PDF, and 300 DPI PNG twins in ../images/.
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
        rows = list(csv.DictReader(line for line in f if not line.startswith("#")))
    identities = {
        (r["accelerator"], r["accelerators"], r["from_round"], r["to_round"])
        for r in rows
    }
    if len(identities) != 1:
        raise ValueError("This chart requires one GPU model, count, and version pair")
    for row in rows:
        earlier, later = float(row["from_time_min"]), float(row["to_time_min"])
        if earlier <= 0 or later <= 0:
            raise ValueError("Published training times must be positive")
        row["speedup"] = earlier / later
    return sorted(rows, key=lambda row: -row["speedup"])


def main():
    rows = load_rows()
    first = rows[0]
    fig, ax = plt.subplots(figsize=(5.0, 2.15))
    for y, row in enumerate(rows):
        speedup = row["speedup"]
        ax.barh(
            y,
            speedup - 1.0,
            left=1.0,
            height=0.56,
            color=COLORS["purple"],
            edgecolor=COLORS["designspace_ink"],
            linewidth=0.6,
            zorder=3,
        )
        ax.text(
            speedup + 0.006,
            y,
            f"{speedup:.3f}×",
            va="center",
            ha="left",
            fontsize=7.2,
            color=COLORS["ink"],
            bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="none"),
            zorder=5,
        )

    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r["workload"] for r in rows], fontsize=7.2)
    ax.set_ylim(len(rows) - 0.4, -0.65)
    ax.set_xlim(1.0, 1.23)
    ax.set_xticks([1.0, 1.05, 1.10, 1.15, 1.20])
    ax.set_title(
        f"{first['accelerator'].replace('NVIDIA ', '')} · {first['accelerators']} GPUs",
        loc="left",
        fontsize=8.2,
        fontweight="bold",
        pad=9,
    )
    ax.set_xlabel("Time-to-train speedup, v2.1 / v3.0 (×)", fontsize=7.4)
    ax.axvline(1.0, color=COLORS["muted"], linewidth=0.8, zorder=4)
    ax.grid(axis="x", color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax.grid(axis="y", visible=False)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="x", labelsize=7.0)
    ax.tick_params(axis="y", length=0)
    fig.tight_layout()
    paths = save_figure_bundle(fig, OUT_BASE, dpi=300, bbox_inches="tight")
    svg = paths["svg"]
    svg.write_text(
        "\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n"
    )
    plt.close(fig)
    print(f"wrote {OUT_BASE}.{{svg,pdf,png}}")


if __name__ == "__main__":
    main()
