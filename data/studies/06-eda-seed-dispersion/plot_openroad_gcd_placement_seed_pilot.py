#!/usr/bin/env python3
"""Plot the executed OpenROAD GCD placement-seed pilot candidate."""

from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path

import matplotlib.pyplot as plt


STUDY_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style  # noqa: E402


apply_style()

INPUT_CSV = STUDY_DIR / "openroad_gcd_placement_seed_pilot.csv"
OUTPUT_BASE = STUDY_DIR / "fig_openroad_gcd_placement_seed_pilot"


def declare_font_stack(svg_path: Path) -> None:
    text = svg_path.read_text(encoding="utf-8")
    if '<style type="text/css">' not in text:
        text = text.replace(
            "<defs>",
            '<defs>\n  <style type="text/css">*{font-family: Arial, Helvetica, sans-serif;}</style>',
            1,
        )
    text = "\n".join(line.rstrip() for line in text.splitlines()) + "\n"
    svg_path.write_text(text, encoding="utf-8")


def quartiles(values: list[float]) -> tuple[float, float, float]:
    q1, _, q3 = statistics.quantiles(values, n=4, method="inclusive")
    return q1, statistics.median(values), q3


def main() -> int:
    with INPUT_CSV.open(encoding="utf-8") as handle:
        records = [row for row in csv.DictReader(handle) if row["status"] == "pass"]
    if not records:
        raise SystemExit(f"No successful placement runs in {INPUT_CSV}")

    seeds = [int(record["seed"]) for record in records]
    areas = [float(record["detailedplace_instance_area_um2"]) for record in records]
    wns_ps = [
        1000.0 * float(record["detailedplace_setup_wns_ns"]) for record in records
    ]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.5, 3.25))
    fig.subplots_adjust(left=0.09, right=0.98, top=0.86, bottom=0.22, wspace=0.32)

    for ax, values, color, title, ylabel, precision in (
        (
            ax1,
            areas,
            COLORS["designspace"],
            "(a) Placement-Optimized Cell Area",
            "Detailed-place instance area (µm²)",
            3,
        ),
        (
            ax2,
            wns_ps,
            COLORS["constraints"],
            "(b) Estimated Setup WNS",
            "Detailed-place setup WNS (ps)",
            2,
        ),
    ):
        q1, median, q3 = quartiles(values)
        value_range = max(values) - min(values)
        range_pct = 100.0 * value_range / abs(median)
        ax.axhspan(q1, q3, color=color, alpha=0.10, zorder=0)
        ax.axhline(
            median,
            color=COLORS["muted"],
            linewidth=1.0,
            linestyle="--",
            zorder=2,
        )
        ax.plot(
            seeds,
            values,
            color=color,
            linewidth=0.85,
            marker="o",
            markersize=3.6,
            markeredgecolor="white",
            markeredgewidth=0.45,
            zorder=3,
        )
        margin = max(value_range * 0.18, abs(median) * 0.002)
        ax.set_ylim(min(values) - margin, max(values) + margin)
        seed_span = max(seeds) - min(seeds)
        x_margin = max(0.6, seed_span * 0.03)
        ax.set_xlim(min(seeds) - x_margin, max(seeds) + x_margin)
        tick_step = max(1, round(seed_span / 4))
        ticks = list(range(min(seeds), max(seeds) + 1, tick_step))
        if ticks[-1] != max(seeds):
            ticks.append(max(seeds))
        ax.set_xticks(ticks)
        ax.set_xlabel("Declared global-placement seed")
        ax.set_ylabel(ylabel)
        ax.set_title(title, loc="left", fontweight="bold")
        ax.grid(True, color=COLORS["grid"], linewidth=0.5, zorder=0)
        ax.text(
            0.02,
            0.04,
            f"median {median:.{precision}f}\n"
            f"range {value_range:.{precision}f} ({range_pct:.2f}% of |median|)\n"
            "shaded band: IQR",
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=5.8,
            color=COLORS["ink"],
            bbox={
                "boxstyle": "round,pad=0.22",
                "facecolor": "white",
                "edgecolor": color,
                "linewidth": 0.55,
                "alpha": 0.94,
            },
            zorder=5,
        )

    fig.text(
        0.5,
        0.04,
        f"ORFS GCD / Nangate45 · place target · N={len(records)} · "
        "single-threaded · only GPL_RANDOM_SEED varied",
        ha="center",
        va="bottom",
        fontsize=6.0,
        color=COLORS["muted"],
    )

    for suffix, kwargs in (
        ("svg", {}),
        ("pdf", {}),
        ("png", {"dpi": 300}),
    ):
        path = OUTPUT_BASE.with_suffix(f".{suffix}")
        fig.savefig(path, bbox_inches="tight", **kwargs)
        print(f"generated: {path}")
    plt.close(fig)
    declare_font_stack(OUTPUT_BASE.with_suffix(".svg"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
