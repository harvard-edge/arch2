"""Reconciled H100 MLPerf Training version-pair results (Chapter 9).

Published time-to-train values, exact submission IDs, and the computed ratios
and 95% intervals are retained in fig-ch09-mlperf-software-dividend.csv.
analyze_mlperf_h100_runs.py writes the computed columns from per-run logs; this
script only plots them. The GPU model and count match; the preview metadata
cannot establish identity of the complete machine. NVIDIA's software attribution
is separate from the measured comparison.

Writes SVG, PDF, and 300 DPI PNG twins in ../images/.
"""

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, FONT_SIZES, apply_style, save_figure_bundle

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
        row["speedup"] = float(row["ratio"])
        row["low"], row["high"] = float(row["ratio_low"]), float(row["ratio_high"])
        if abs(row["speedup"] - float(row["from_time_min_unscaled"]) / later) > 0.0005:
            raise ValueError(f"{row['workload']}: ratio does not match its unscaled time")
        if abs(float(row["from_time_min_unscaled"]) * float(row["from_rcp_scaling"]) - earlier) > 0.001:
            raise ValueError(f"{row['workload']}: scaling does not give the published time")
        if not row["low"] <= row["speedup"] <= row["high"]:
            raise ValueError(f"{row['workload']}: ratio lies outside its interval")
    return sorted(rows, key=lambda row: -row["speedup"])


def main():
    rows = load_rows()
    first = rows[0]
    fig, ax = plt.subplots(figsize=(5.0, 1.0 + 0.38 * len(rows)))
    for y, row in enumerate(rows):
        speedup = row["speedup"]
        ax.plot(
            [row["low"], row["high"]],
            [y, y],
            color=COLORS["purple"],
            linewidth=1.6,
            solid_capstyle="butt",
            zorder=3,
        )
        ax.plot(
            speedup,
            y,
            marker="o",
            markersize=5.5,
            color=COLORS["purple"],
            markeredgecolor=COLORS["designspace_ink"],
            markeredgewidth=0.6,
            zorder=4,
        )
        ax.text(
            row["high"] + 0.008,
            y,
            f"{speedup:.2f}×",
            va="center",
            ha="left",
            fontsize=FONT_SIZES["annotation"],
            color=COLORS["ink"],
            bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="none"),
            zorder=5,
        )

    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r["workload"] for r in rows], fontsize=FONT_SIZES["body"])
    ax.set_ylim(len(rows) - 0.4, -0.65)
    ax.set_xlim(0.90, 1.32)
    ax.set_xticks([0.9, 1.0, 1.1, 1.2, 1.3])
    ax.set_title(
        f"{first['accelerator'].replace('NVIDIA ', '')} · {first['accelerators']} GPUs",
        loc="left",
        pad=9,
    )
    ax.set_xlabel("Time-to-train speedup, v2.1 / v3.0 (×), with 95% interval")
    ax.axvline(1.0, color=COLORS["muted"], linewidth=0.8, zorder=4)
    ax.grid(axis="x", color=COLORS["grid"], linewidth=0.55, zorder=0)
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", length=0)
    fig.tight_layout()
    save_figure_bundle(fig, OUT_BASE, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {OUT_BASE}.{{svg,pdf,png}}")


if __name__ == "__main__":
    main()
