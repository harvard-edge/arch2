#!/usr/bin/env python3
"""
Publication Figure: Physical EDA Seed Dispersion & Stochastic QoR Lottery
==========================================================================
Architecture 2.0: Track 4.1 — The Physical EDA Seed Dispersion & Stochastic QoR Lottery

Generates publication-quality multi-panel visualization:
- Panel A: Empirical Seed QoR Dispersion Distribution (KDE & Gaussian fit across 684 runs, 1σ/2σ bands)
- Panel B: 'The 3% Illusion' — Published AI EDA Claims vs. Empirical Seed Noise on Identical RTL
- Panel C: Multi-Thread Concurrency & Asynchronous Lock Jitter Variance Expansion

Dataset Receipt:
- data/source-receipts/eda_seed_dispersion_qor_lottery.csv

Generated Assets:
- data/source-receipts/eda_seed_dispersion_distribution.png
- data/source-receipts/eda_seed_dispersion_distribution.pdf
- data/source-receipts/eda_seed_dispersion_distribution.svg
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

# Connect repo root for shared plot style
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style, add_note_box

apply_style()


def _declare_font_stack(svg_path: Path) -> None:
    """Ensure SVG declares standard sans-serif font stack matching House Style."""
    if not svg_path.exists():
        return
    text = svg_path.read_text(encoding="utf-8")
    if '<style type="text/css">' not in text:
        text = text.replace(
            "<defs>",
            '<defs>\n  <style type="text/css">*{font-family: Arial, Helvetica, sans-serif;}</style>',
            1,
        )
        svg_path.write_text(text, encoding="utf-8")


def load_receipt_data(csv_path: Path) -> List[Dict[str, Any]]:
    """Load EDA seed dispersion CSV receipt, ignoring comment lines."""
    records = []
    with open(csv_path, "r", encoding="utf-8") as f:
        lines = [line for line in f if not line.strip().startswith("#")]
        reader = csv.DictReader(l for l in lines if not l.startswith("#"))
        for r in reader:
            records.append(
                {
                    "design_name": r["design_name"],
                    "toolchain": r["toolchain"],
                    "process_node": r["process_node"],
                    "random_seed": int(r["random_seed"]),
                    "thread_count": int(r["thread_count"]),
                    "os_kernel": r["os_kernel"],
                    "clock_period_ns": float(r["clock_period_ns"]),
                    "worst_negative_slack_ns": float(r["worst_negative_slack_ns"]),
                    "total_negative_slack_ns": float(r["total_negative_slack_ns"]),
                    "cell_area_um2": float(r["cell_area_um2"]),
                    "total_wirelength_um": float(r["total_wirelength_um"]),
                    "runtime_s": float(r["runtime_s"]),
                    "peak_memory_mb": float(r["peak_memory_mb"]),
                    "drc_violations": int(r["drc_violations"]),
                    "dispersion_spread_pct": float(r["dispersion_spread_pct"]),
                    "qor_composite_score": float(r["qor_composite_score"]),
                }
            )
    return records


def main():
    csv_file = (
        REPO_ROOT / "data" / "source-receipts" / "eda_seed_dispersion_qor_lottery.csv"
    )
    if not csv_file.exists():
        csv_file = (
            Path(__file__).resolve().parent / "eda_seed_dispersion_qor_lottery.csv"
        )

    records = load_receipt_data(csv_file)
    print(f"Loaded {len(records)} runs from {csv_file}")

    # Output file paths
    out_png = (
        REPO_ROOT / "data" / "source-receipts" / "eda_seed_dispersion_distribution.png"
    )
    out_pdf = (
        REPO_ROOT / "data" / "source-receipts" / "eda_seed_dispersion_distribution.pdf"
    )
    out_svg = (
        REPO_ROOT / "data" / "source-receipts" / "eda_seed_dispersion_distribution.svg"
    )

    # Create figure with 3 panels
    fig = plt.figure(figsize=(12.0, 4.5), dpi=150)
    gs = fig.add_gridspec(
        1,
        3,
        width_ratios=[1.10, 1.45, 0.95],
        wspace=0.28,
        left=0.055,
        right=0.975,
        top=0.90,
        bottom=0.24,
    )

    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[0, 2])

    # =========================================================================
    # Panel A: Gaussian QoR Dispersion Distribution
    # =========================================================================
    spreads = np.array([r["dispersion_spread_pct"] for r in records])
    mu = float(np.mean(spreads))
    sigma = float(np.std(spreads, ddof=1))

    # Histogram
    bins = np.linspace(-7.0, 8.5, 32)
    n_counts, bin_edges, patches = ax_a.hist(
        spreads,
        bins=bins,
        density=True,
        color=COLORS["blue"],
        alpha=0.38,
        edgecolor=COLORS["blue"],
        linewidth=0.7,
        label="Empirical Runs (N=684)",
        zorder=2,
    )

    # Gaussian PDF curve
    x_grid = np.linspace(-7.5, 9.0, 250)
    pdf = (1.0 / (sigma * np.sqrt(2 * np.pi))) * np.exp(
        -0.5 * ((x_grid - mu) / sigma) ** 2
    )
    ax_a.plot(
        x_grid,
        pdf,
        color=COLORS["workload_ink"],
        linewidth=1.8,
        label=f"Normal Fit (σ={sigma:.2f}%)",
        zorder=4,
    )

    # 1-sigma and 2-sigma shaded zones
    ax_a.axvspan(
        mu - sigma,
        mu + sigma,
        color=COLORS["blue"],
        alpha=0.12,
        zorder=1,
        label="±1σ Zone (±2.22%)",
    )
    ax_a.axvspan(
        mu - 2 * sigma,
        mu + 2 * sigma,
        color=COLORS["purple"],
        alpha=0.07,
        zorder=0,
        label="±2σ Zone (±4.43%)",
    )

    # Annotations for percentiles
    p10 = np.percentile(spreads, 10)
    p90 = np.percentile(spreads, 90)
    ax_a.axvline(p10, color=COLORS["red"], linestyle="--", linewidth=1.0, zorder=3)
    ax_a.axvline(p90, color=COLORS["red"], linestyle="--", linewidth=1.0, zorder=3)
    ax_a.text(
        p10 - 0.20,
        0.145,
        f"10th %ile\n{p10:.1f}%",
        color=COLORS["constraints_ink"],
        fontsize=5.5,
        ha="right",
        fontweight="bold",
    )
    ax_a.text(
        p90 + 0.20,
        0.145,
        f"90th %ile\n+{p90:.1f}%",
        color=COLORS["constraints_ink"],
        fontsize=5.5,
        ha="left",
        fontweight="bold",
    )

    ax_a.set_title(
        "A. QoR Dispersion (N=684 Signoff Runs)",
        fontsize=7.6,
        fontweight="bold",
        color=COLORS["ink"],
        pad=6,
    )
    ax_a.set_xlabel(
        "Wirelength Deviation from Mean (ΔQoR %)", fontsize=6.6, color=COLORS["ink"]
    )
    ax_a.set_ylabel("Probability Density", fontsize=6.6, color=COLORS["ink"])
    ax_a.set_xlim(-7.5, 8.8)
    ax_a.set_ylim(0, 0.23)
    ax_a.xaxis.set_major_formatter(ticker.PercentFormatter(decimals=0))
    ax_a.legend(
        loc="upper left",
        fontsize=5.2,
        frameon=True,
        facecolor="white",
        edgecolor=COLORS["grid"],
    )
    ax_a.grid(True, color=COLORS["grid"], linestyle=":", linewidth=0.55, zorder=0)

    # =========================================================================
    # Panel B: "The 3% Illusion" — AI Claims vs Empirical Seed Noise
    # =========================================================================
    designs = [
        "PicoRV32",
        "Ibex_Core",
        "SystolicArray_16x16",
        "AES256_GCM",
        "DynamicNode_NoC",
        "BlackParrot_FE",
    ]
    design_labels = [
        "PicoRV32\n(RV32IMC)",
        "Ibex\n(CV32E40P)",
        "Systolic\n16x16",
        "AES-256\nGCM",
        "Dynamic\nNoC Router",
        "BlackParrot\nFrontend",
    ]

    # Shaded AI Noise Trap Band: [-4.5%, +4.5%]
    ax_b.axhspan(-4.5, 4.5, color=COLORS["orange"], alpha=0.13, zorder=0)
    ax_b.axhline(0.0, color=COLORS["muted"], linestyle="-", linewidth=0.8, zorder=1)

    # Plot published AI claims as horizontal dashed markers
    ax_b.axhline(3.4, color=COLORS["red"], linestyle=":", linewidth=1.2, zorder=2)
    ax_b.axhline(3.8, color=COLORS["purple"], linestyle=":", linewidth=1.2, zorder=2)
    ax_b.axhline(4.1, color=COLORS["magenta"], linestyle=":", linewidth=1.2, zorder=2)

    # Boxplot + Swarm points for each design
    pos_list = list(range(len(designs)))
    box_data = []
    for i, des in enumerate(designs):
        des_spreads = [
            r["dispersion_spread_pct"] for r in records if r["design_name"] == des
        ]
        box_data.append(des_spreads)

        # Jittered scatter points
        rng = np.random.default_rng(seed=42 + i)
        jitter = rng.uniform(-0.16, 0.16, size=len(des_spreads))
        ax_b.scatter(
            np.array([i] * len(des_spreads)) + jitter,
            des_spreads,
            s=7.5,
            color=COLORS["blue"],
            alpha=0.45,
            edgecolor="none",
            zorder=3,
        )

    bp = ax_b.boxplot(
        box_data,
        positions=pos_list,
        widths=0.38,
        patch_artist=True,
        showfliers=False,
        boxprops=dict(
            facecolor="white",
            edgecolor=COLORS["workload_ink"],
            linewidth=1.1,
            alpha=0.85,
        ),
        medianprops=dict(color=COLORS["red"], linewidth=1.5),
        whiskerprops=dict(color=COLORS["workload_ink"], linewidth=1.0),
        capprops=dict(color=COLORS["workload_ink"], linewidth=1.0),
        zorder=4,
    )

    # Legend for published AI claims
    ai_legend = [
        Line2D(
            [0],
            [0],
            color=COLORS["red"],
            linestyle=":",
            linewidth=1.2,
            label="RL Macro Placement (+3.4% WL)",
        ),
        Line2D(
            [0],
            [0],
            color=COLORS["purple"],
            linestyle=":",
            linewidth=1.2,
            label="LLM Prompt Tuning (+3.8% Area)",
        ),
        Line2D(
            [0],
            [0],
            color=COLORS["magenta"],
            linestyle=":",
            linewidth=1.2,
            label="AI Phase Ordering (+4.1% Delay)",
        ),
    ]
    ax_b.legend(
        handles=ai_legend,
        loc="upper right",
        fontsize=5.1,
        frameon=True,
        facecolor="white",
        edgecolor=COLORS["grid"],
    )

    # Callout badge for The 3% Illusion Zone
    ax_b.text(
        0.05,
        -6.2,
        "The 3% Illusion Zone (±4.5% Seed Variance)\nAI claims fall within single-seed lottery noise",
        color=COLORS["methods_ink"],
        fontsize=5.8,
        fontweight="bold",
        zorder=5,
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor=COLORS["note_fill"],
            edgecolor=COLORS["orange"],
            linewidth=0.7,
        ),
    )

    ax_b.set_title(
        "B. 'The 3% Illusion': AI Claims vs. Empirical Seed Lottery",
        fontsize=7.6,
        fontweight="bold",
        color=COLORS["ink"],
        pad=6,
    )
    ax_b.set_xticks(pos_list)
    ax_b.set_xticklabels(design_labels, fontsize=5.8)
    ax_b.set_ylabel("QoR Wirelength Spread (%)", fontsize=6.6, color=COLORS["ink"])
    ax_b.set_ylim(-7.5, 8.5)
    ax_b.yaxis.set_major_formatter(ticker.PercentFormatter(decimals=0))
    ax_b.grid(True, color=COLORS["grid"], linestyle=":", linewidth=0.55, zorder=0)

    # =========================================================================
    # Panel C: Multi-Thread Non-Determinism & Variance Expansion
    # =========================================================================
    thread_counts = [1, 4, 8, 16]
    t_data = []
    t_stds = []
    for tc in thread_counts:
        t_spreads = [
            r["dispersion_spread_pct"] for r in records if r["thread_count"] == tc
        ]
        t_data.append(t_spreads)
        t_stds.append(float(np.std(t_spreads, ddof=1)))

    x_threads = list(range(len(thread_counts)))

    # Violins or Box plots for threads
    bp_c = ax_c.boxplot(
        t_data,
        positions=x_threads,
        widths=0.42,
        patch_artist=True,
        showfliers=False,
        boxprops=dict(
            facecolor=COLORS["note_fill"], edgecolor=COLORS["purple"], linewidth=1.1
        ),
        medianprops=dict(color=COLORS["red"], linewidth=1.5),
        whiskerprops=dict(color=COLORS["designspace_ink"], linewidth=1.0),
        capprops=dict(color=COLORS["designspace_ink"], linewidth=1.0),
        zorder=3,
    )

    # Overlay std dev line on top
    for idx, (tc, s_val) in enumerate(zip(thread_counts, t_stds)):
        ax_c.text(
            idx,
            6.0,
            f"1σ=±{s_val:.2f}%\n({s_val/t_stds[0]:.2f}x)",
            color=COLORS["designspace_ink"],
            fontsize=5.3,
            ha="center",
            fontweight="bold",
            bbox=dict(
                boxstyle="square,pad=0.2",
                facecolor="white",
                edgecolor=COLORS["purple"],
                linewidth=0.5,
            ),
        )

    ax_c.set_title(
        "C. Thread Race Concurrency",
        fontsize=7.6,
        fontweight="bold",
        color=COLORS["ink"],
        pad=6,
    )
    ax_c.set_xticks(x_threads)
    ax_c.set_xticklabels(
        [f"T=1\n(Hermetic)", f"T=4\n(Race)", f"T=8\n(Race)", f"T=16\n(Extreme)"],
        fontsize=5.8,
    )
    ax_c.set_xlabel("Thread Concurrency", fontsize=6.6, color=COLORS["ink"], labelpad=4)
    ax_c.set_ylabel("QoR Wirelength Spread (%)", fontsize=6.6, color=COLORS["ink"])
    ax_c.set_ylim(-7.5, 8.5)
    ax_c.yaxis.set_major_formatter(ticker.PercentFormatter(decimals=0))
    ax_c.grid(True, color=COLORS["grid"], linestyle=":", linewidth=0.55, zorder=0)

    # Shared bottom note box
    note_text = (
        "EMPIRICAL TAKEAWAY: Physical EDA flows (OpenROAD/Yosys/OpenSTA) exhibit a natural 3%–8% QoR dispersion "
        "(1σ = ±2.22%, peak-to-peak = 14.2%) on identical RTL across seeds and thread races. "
        "Published AI-for-EDA gains (+3% to +5%) evaluated on single seeds measure stochastic noise rather than true optimization."
    )
    add_note_box(fig, note_text, xywh=(0.055, 0.025, 0.92, 0.11), fontsize=5.7)

    # Save figure formats
    fig.savefig(out_png, dpi=300, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    fig.savefig(out_svg, bbox_inches="tight")

    # Also sync with Chapter 6 images if directory exists
    ch06_img_dir = (
        REPO_ROOT / "book" / "contents" / "chapters" / "06-environments" / "images"
    )
    if ch06_img_dir.is_dir():
        fig.savefig(
            ch06_img_dir / "fig-eda-runtime-variance-dispersion.png",
            dpi=300,
            bbox_inches="tight",
        )
        fig.savefig(
            ch06_img_dir / "fig-eda-runtime-variance-dispersion.pdf",
            bbox_inches="tight",
        )
        fig.savefig(
            ch06_img_dir / "fig-eda-runtime-variance-dispersion.svg",
            bbox_inches="tight",
        )
        _declare_font_stack(ch06_img_dir / "fig-eda-runtime-variance-dispersion.svg")

    plt.close(fig)

    _declare_font_stack(out_svg)

    print(f"✅ Saved publication figures:")
    print(f"   - {out_png}")
    print(f"   - {out_pdf}")
    print(f"   - {out_svg}")


if __name__ == "__main__":
    main()
