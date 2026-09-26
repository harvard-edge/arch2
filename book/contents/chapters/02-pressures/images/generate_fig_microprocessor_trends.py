#!/usr/bin/env python3
"""Generate fig-microprocessor-trends: 50-year CPU trends joined with AI accelerator frontier.

This script extends Karl Rupp's 50-year CPU scaling frontier (1971-2021) with the
14-year AI accelerator scaling frontier (2012-2024, 23 primary-cited parts).

Inputs:
  - data/datasets/chapter1-micro-trend.csv (Rupp microprocessor-trend-data, CC-BY 4.0)
  - data/datasets/chapter2-ai-accelerator-scaling-frontier.csv (Primary-cited accelerators)

Outputs:
  - book/contents/chapters/02-pressures/images/fig-microprocessor-trends.png
  - book/contents/chapters/02-pressures/images/fig-microprocessor-trends.pdf
"""

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# Add repository root to path
REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style

CPU_CSV = REPO_ROOT / "data" / "datasets" / "chapter1-micro-trend.csv"
ACC_CSV = (
    REPO_ROOT / "data" / "datasets" / "chapter2-ai-accelerator-scaling-frontier.csv"
)
DEFAULT_OUT_DIR = Path(__file__).resolve().parent


def cpu_series():
    with open(CPU_CSV, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(l for l in f if not l.startswith("#")))
    out = {}
    for r in rows:
        out.setdefault(r["series"], []).append((float(r["year"]), float(r["value"])))
    for k in out:
        out[k].sort()
    return out


def accelerator_frontier():
    """Extract running maximum frontier by release year for packaged parts, plus wafer-scale."""
    with open(ACC_CSV, "r", encoding="utf-8") as f:
        rows = [r for r in csv.reader(f) if r and not r[0].startswith("#")]
    head, rows = rows[0], rows[1:]
    idx = {name: i for i, name in enumerate(head)}
    chips = []
    for r in rows:
        chips.append(
            {
                "name": r[idx["Chip_Name"]],
                "year": int(r[idx["Release_Year"]]),
                "trans_k": float(r[idx["Transistors_Billion"]])
                * 1e6,  # billions -> thousands
                "watts": float(r[idx["TDP_Watts"]]),
                "wafer": "Wafer-Scale" in r[idx["Packaging_Type"]],
            }
        )
    packaged = sorted((c for c in chips if not c["wafer"]), key=lambda c: c["year"])

    def frontier(key):
        pts, best = [], 0.0
        for c in packaged:
            if c[key] > best:
                best = c[key]
                pts.append((c["year"], best, c["name"]))
        return pts

    return frontier("trans_k"), frontier("watts"), [c for c in chips if c["wafer"]]


def generate_figure(out_dir: Path | None = None):
    apply_style()

    out_dir = out_dir or DEFAULT_OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    cpu = cpu_series()
    acc_trans, acc_watts, wafer = accelerator_frontier()

    # Color palette
    c_purple = COLORS.get("purple", "#7B4EA8")
    c_blue = COLORS.get("blue", "#1F77B4")
    c_orange = COLORS.get("orange", "#E8A33D")
    c_red = COLORS.get("red", "#D62728")
    c_green = COLORS.get("green", "#2CA02C")
    c_ink = COLORS.get("ink", "#212121")
    c_grey = "#70757A"
    c_accent_bg = COLORS.get("red", "#A51C30")

    fig, ax = plt.subplots(figsize=(12.4, 4.6))
    ax.set_yscale("log")

    # dy nudges the end-of-line labels apart to avoid collisions
    lines = [
        ("transistors", c_purple, "Transistors\n(thousands)", -9),
        ("specint", c_blue, "Single-thread perf\n(SpecINT x 1000)", 0),
        ("frequency", c_orange, "Frequency (MHz)", 7),
        ("cpu_watts", c_red, "CPU power: 4-year max (W)", -4),
        ("cpu_threads", c_green, "CPU logical\nhardware threads", -14),
    ]
    for key, colour, label, dy in lines:
        xs, ys = zip(*cpu[key])
        ax.plot(xs, ys, "o-", color=colour, ms=3.4, lw=1.5, zorder=3)
        ax.annotate(
            label,
            xy=(xs[-1], ys[-1]),
            xytext=(6, dy),
            textcoords="offset points",
            color=colour,
            fontsize=8.6,
            fontweight="bold",
            va="center",
        )

    # Accelerator frontier
    for pts, colour, label, marker in (
        (acc_trans, c_purple, "Accelerator transistors", "^"),
        (acc_watts, c_red, "Accelerator TDP (W)", "s"),
    ):
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        ax.plot(
            xs,
            ys,
            marker=marker,
            ls="--",
            color=colour,
            ms=4.6,
            lw=1.6,
            alpha=0.95,
            mfc="white",
            mew=1.4,
            zorder=4,
        )
        ax.annotate(
            label,
            xy=(xs[-1], ys[-1]),
            xytext=(6, 0),
            textcoords="offset points",
            color=colour,
            fontsize=8.6,
            fontweight="bold",
            style="italic",
            va="center",
        )

    # Cerebras wafer-scale parts, shown for scale but deliberately off the packaged frontier line
    wx = [c["year"] for c in sorted(wafer, key=lambda c: c["year"])]
    wy = [c["trans_k"] for c in sorted(wafer, key=lambda c: c["year"])]
    ax.plot(
        wx,
        wy,
        ls=":",
        marker="D",
        ms=4,
        color=c_grey,
        lw=1.1,
        alpha=0.75,
        mfc="white",
        mew=1.1,
        zorder=2,
    )
    ax.annotate(
        "Cerebras wafer-scale\n(shown for scale, not on the frontier)",
        xy=(wx[-1], wy[-1]),
        xytext=(6, -2),
        textcoords="offset points",
        fontsize=8.0,
        color=c_grey,
        style="italic",
        va="center",
    )

    # Vertical era boundaries
    ax.axvline(2005, color=c_ink, ls="--", lw=0.9, alpha=0.65)
    ax.axvline(2016, color=c_ink, ls="--", lw=0.9, alpha=0.65)
    ax.text(
        2004.4,
        2.2e6,
        "Dennard\nscaling ends",
        fontsize=8.0,
        color=c_ink,
        ha="right",
        va="center",
    )
    ax.text(
        2015.4,
        3.0e5,
        "specialization\nturn",
        fontsize=8.0,
        color=c_ink,
        ha="right",
        va="center",
    )

    # Era headers
    for a, b, name in (
        (1971, 2005, "Device-scaling era"),
        (2005, 2016, "Parallelism era"),
        (2016, 2026, "Specialization era"),
    ):
        ax.text(
            (a + b) / 2,
            8.0e9,
            name,
            ha="center",
            fontsize=9.5,
            fontweight="bold",
            color=c_ink,
        )

    # Shaded band for specialization era
    ax.axvspan(2016, 2026, color=c_accent_bg, alpha=0.04, zorder=0)

    ax.set_xlim(1970, 2026)
    ax.set_ylim(0.5, 2.2e10)
    ax.set_xticks(range(1970, 2021, 10))
    ax.set_yticks([1, 1e2, 1e4, 1e6, 1e8, 1e10])
    ax.set_yticklabels(
        [r"$10^0$", r"$10^2$", r"$10^4$", r"$10^6$", r"$10^8$", r"$10^{10}$"]
    )
    ax.grid(axis="y", color="#E8EAED", lw=0.6)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color("#DADCE0")
    ax.spines["bottom"].set_color("#DADCE0")
    ax.tick_params(labelsize=8.5, colors=c_ink)

    # Legend placed cleanly in lower right whitespace without overlapping labels
    ax.legend(
        handles=[
            Line2D(
                [],
                [],
                color=c_ink,
                lw=1.5,
                marker="o",
                ms=3.4,
                label="CPU frontier (Rupp, 1971–2021)",
            ),
            Line2D(
                [],
                [],
                color=c_ink,
                lw=1.6,
                ls="--",
                marker="^",
                ms=4.6,
                mfc="white",
                label="Accelerator frontier (2012–2024)",
            ),
        ],
        loc="lower right",
        fontsize=8.2,
        frameon=False,
        bbox_to_anchor=(0.98, 0.02),
    )

    fig.subplots_adjust(left=0.055, right=0.815, top=0.90, bottom=0.10)

    out_png = out_dir / "fig-microprocessor-trends.png"
    out_pdf = out_dir / "fig-microprocessor-trends.pdf"
    out_svg = out_dir / "fig-microprocessor-trends.svg"

    fig.savefig(out_png, dpi=220)
    fig.savefig(out_pdf)
    fig.savefig(out_svg)
    plt.close(fig)
    print(f"Generated {out_png}, {out_pdf}, and {out_svg}")


if __name__ == "__main__":
    generate_figure()
