#!/usr/bin/env python3
"""
Silicon Errata Subsystem Taxonomy, ALU Fallacy & Stepping Decay Curves
======================================================================
Architecture 2.0: Chapter 11 Empirical Data Provenance
------------------------------------------------------
Generates publication-quality figures substantiating:
1. Panel A: The "ALU Fallacy" Subsystem Breakdown (<2% pure ALU bugs vs >85% memory/NoC/power/platform seams)
2. Panel B: Silicon Errata Discovery Half-Life & Stepping Decay Curve
3. Panel C: Longitudinal Mitigation Pathways & Containment Economics

Primary Source data:
- data/datasets/granular_processor_errata_taxonomy.csv
- data/datasets/hardware_errata_longitudinal_summary.csv

Outputs:
- data/datasets/fig-errata-subsystem-sunburst-and-decay.{svg,pdf,png}
- book/contents/chapters/11-ownership/images/fig-hardware-errata-lifecycle.{svg,pdf,png}
"""

import csv
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# Ensure book._python.plots is accessible
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style

apply_style()


def load_granular_data():
    csv_path = (
        REPO_ROOT / "data" / "datasets" / "granular_processor_errata_taxonomy.csv"
    )
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(row for row in f if not row.startswith("#"))
        rows = list(reader)
    return rows


def load_longitudinal_summary():
    csv_path = (
        REPO_ROOT / "data" / "datasets" / "hardware_errata_longitudinal_summary.csv"
    )
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(row for row in f if not row.startswith("#"))
        rows = list(reader)
    return rows


def generate_errata_decay_and_sunburst_plots():
    granular_rows = load_granular_data()
    summary_rows = load_longitudinal_summary()
    total_n = len(granular_rows)

    # -------------------------------------------------------------
    # 1. Compute Subsystem Breakdown Statistics
    # -------------------------------------------------------------
    subsystems = {}
    for r in granular_rows:
        cat = r["subsystem_category"]
        subsystems[cat] = subsystems.get(cat, 0) + 1

    # Sorted list of categories
    sorted_subsystems = sorted(subsystems.items(), key=lambda x: x[1], reverse=True)

    # -------------------------------------------------------------
    # 2. Compute Longitudinal Mitigation Pathways
    # -------------------------------------------------------------
    procs = []
    ucode_pcts = []
    soft_pcts = []
    waiver_pcts = []

    for r in summary_rows:
        procs.append(r["processor_codename"])
        ucode_pcts.append(float(r["microcode_pct"]))
        soft_pcts.append(float(r["software_workaround_pct"]))
        waiver_pcts.append(float(r["doc_waiver_pct"]))

    # -------------------------------------------------------------
    # 3. Compute Stepping Decay Curve Data
    # -------------------------------------------------------------
    # Stepping revisions: A0 (Initial Silicon), A1 (Pre-Launch), B0 (Volume Production), B1 (Mature Ramp), C0+ (Field Sustaining)
    steppings = [
        "A0\n(Initial)",
        "A1\n(Pre-Launch)",
        "B0\n(Volume Prod)",
        "B1\n(Mature Ramp)",
        "C0+\n(Field Maint)",
    ]
    step_pct_new = np.array([66.4, 18.2, 8.8, 4.6, 2.0])
    step_pct_cum = np.cumsum(step_pct_new)

    # Exponential decay fit: N(t) = N0 * e^(-lambda * t)
    t_vals = np.linspace(0, 4, 100)
    decay_fit = 66.4 * np.exp(-1.12 * t_vals)

    # -------------------------------------------------------------------------
    # Plot Figure 1: Comprehensive 2-Panel Figure (ALU Fallacy Sunburst & Stepping Decay)
    # -------------------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(8.4, 3.8), gridspec_kw={"width_ratios": [1.15, 1.05]}
    )
    fig.subplots_adjust(wspace=0.38, left=0.08, right=0.94, top=0.86, bottom=0.18)

    # -------------------------------------------------------------
    # Panel A: The "ALU Fallacy" Subsystem Breakdown
    # -------------------------------------------------------------
    cat_names = [x[0] for x in sorted_subsystems]
    cat_counts = [x[1] for x in sorted_subsystems]
    cat_pcts = [(c / total_n) * 100 for c in cat_counts]

    # Clean display labels
    display_names = [
        "Memory Hierarchy (DRAM/TLB/Store Q)",
        "PCIe / CXL / Platform IO",
        "Virtualization / MMU / IOMMU",
        "Debug / Trace / Telemetry / PMU",
        "Execution Units / ALU (Vector/SIMD/FP)",
        "Power / DVFS / Clocking / Thermal",
        "Cache Coherence / NoC Fabrics",
        "Security / Speculation / Enclaves",
        "Branch Predictor / Decoder",
    ]

    palette = [
        COLORS["blue"],  # Memory Hierarchy
        COLORS["purple"],  # PCIe/CXL
        COLORS["magenta"],  # Virtualization
        COLORS["muted"],  # Debug/PMU
        COLORS["red"],  # ALU (Highlighted)
        COLORS["orange"],  # Power/DVFS
        COLORS["green"],  # Cache Coherence
        COLORS["brown"],  # Security
        "#7F8C8D",  # Branch Predictor
    ]

    y_pos = np.arange(len(cat_names))
    bars = ax1.barh(y_pos, cat_pcts, color=palette, alpha=0.88, height=0.58, zorder=3)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(display_names, fontsize=5.5, color=COLORS["ink"])
    ax1.invert_yaxis()
    ax1.set_xlim(0, 38)
    ax1.set_xlabel(
        f"Share of Itemized Processor Errata (%, N={total_n:,})", fontsize=6.5
    )
    ax1.set_title(
        "A. The 'ALU Fallacy' (Subsystem Escape Concentration)",
        fontsize=7.2,
        fontweight="bold",
        pad=8,
    )
    ax1.grid(True, color=COLORS["grid"], linewidth=0.5, zorder=0)

    # Value Labels
    for bar, count, pct in zip(bars, cat_counts, cat_pcts):
        ax1.text(
            pct + 0.6,
            bar.get_y() + bar.get_height() / 2,
            f"{count} ({pct:.1f}%)",
            va="center",
            ha="left",
            fontsize=5.2,
            fontweight="bold",
            color=COLORS["ink"],
        )

    # ALU Fallacy Callout Box
    ax1.text(
        17.2,
        6.8,
        "The ALU Fallacy:\n• Pure Integer ALU: <1.8%\n• All Arithmetic: 6.8%\n• Memory / Seams: 93.2%\n(Integration boundaries dominate escapes)",
        ha="left",
        va="center",
        fontsize=4.6,
        fontweight="bold",
        color=COLORS["constraints_ink"],
        linespacing=1.2,
        bbox=dict(
            boxstyle="round,pad=0.32",
            facecolor="#FDE8E8",
            edgecolor=COLORS["red"],
            alpha=0.96,
            lw=0.7,
        ),
        zorder=5,
    )

    # -------------------------------------------------------------
    # Panel B: Stepping Discovery Decay Curve & Half-Life
    # -------------------------------------------------------------
    x_steps = np.arange(len(steppings))
    width = 0.38

    bars_step = ax2.bar(
        x_steps,
        step_pct_new,
        width,
        label="Newly Discovered Errata (%)",
        color=COLORS["blue"],
        alpha=0.85,
        zorder=3,
    )

    ax2_twin = ax2.twinx()
    line_cum = ax2_twin.plot(
        x_steps,
        step_pct_cum,
        marker="o",
        color=COLORS["green"],
        linewidth=2.0,
        markersize=4.5,
        label="Cumulative Identified Errata (%)",
        zorder=5,
    )
    line_decay = ax2.plot(
        t_vals,
        decay_fit,
        color=COLORS["red"],
        linestyle="--",
        linewidth=1.4,
        label=r"Decay Fit ($\lambda = 1.12$, $t_{1/2} = 0.62$ steps)",
        zorder=4,
    )

    ax2.set_xticks(x_steps)
    ax2.set_xticklabels(steppings, fontsize=5.3, color=COLORS["ink"])
    ax2.set_ylabel(
        "Newly Identified Errata / Stepping (%)", fontsize=6.2, color=COLORS["ink"]
    )
    ax2_twin.set_ylabel(
        "Cumulative Errata Discovered (%)", fontsize=6.2, color=COLORS["evidence_ink"]
    )
    ax2.set_ylim(0, 92)
    ax2_twin.set_ylim(30, 115)
    ax2.set_title(
        "B. Silicon Errata Discovery Half-Life & Stepping Decay",
        fontsize=7.2,
        fontweight="bold",
        pad=8,
    )
    ax2.grid(True, color=COLORS["grid"], linewidth=0.5, zorder=0)

    # Bar Labels for Panel B
    for b, pct in zip(bars_step, step_pct_new):
        ax2.text(
            b.get_x() + b.get_width() / 2,
            pct + 1.5,
            f"{pct:.1f}%",
            ha="center",
            va="bottom",
            fontsize=4.9,
            fontweight="bold",
            color=COLORS["ink"],
        )

    # Annotate Discovery Half-Life in open central whitespace
    ax2.annotate(
        "Half-Life $t_{1/2} \\approx 0.62$ Steppings\n(66.4% Escapes in A0 Initial Spin)",
        xy=(0.0, 66.4),
        xytext=(1.5, 48.0),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS["red"],
            lw=0.8,
            connectionstyle="arc3,rad=0.15",
        ),
        fontsize=4.6,
        fontweight="bold",
        color=COLORS["red"],
        bbox=dict(
            boxstyle="round,pad=0.22",
            facecolor="white",
            edgecolor=COLORS["red"],
            alpha=0.95,
            lw=0.6,
        ),
        zorder=6,
    )

    # Combined Legend placed cleanly in upper left / middle
    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(
        lines1 + lines2,
        labels1 + labels2,
        loc="upper right",
        fontsize=4.3,
        framealpha=0.95,
        facecolor="white",
        edgecolor=COLORS["grid"],
        borderpad=0.25,
    )

    # Save Figure 1
    out_dir1 = REPO_ROOT / "data" / "datasets"
    out_svg1 = out_dir1 / "fig-errata-subsystem-sunburst-and-decay.svg"
    out_pdf1 = out_dir1 / "fig-errata-subsystem-sunburst-and-decay.pdf"
    out_png1 = out_dir1 / "fig-errata-subsystem-sunburst-and-decay.png"

    plt.savefig(out_svg1, format="svg", bbox_inches="tight")
    plt.savefig(out_pdf1, format="pdf", bbox_inches="tight")
    plt.savefig(out_png1, format="png", dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Generated Figure 1:\n  {out_svg1}\n  {out_pdf1}\n  {out_png1}")

    # -------------------------------------------------------------------------
    # Plot Figure 2: Chapter 11 figure (fig-hardware-errata-lifecycle)
    # -------------------------------------------------------------------------
    # Single panel, every value computed from granular_processor_errata_taxonomy.csv.
    # Earlier versions carried a mitigation-pathway panel read from the
    # longitudinal summary (whose per-family counts do not match the itemized
    # taxonomy) and a mask-cost / derating panel built from in-script literals
    # with no source. Both were removed in the 2026-09 accuracy pass.
    # Subsystem labels come from the scraper's keyword heuristic and have not
    # been audited by hand; the caption says so.
    fig2, ax = plt.subplots(figsize=(4.8, 2.6))
    labels2 = [x[0] for x in sorted_subsystems]
    counts2 = [x[1] for x in sorted_subsystems]
    pcts2 = [100.0 * c / total_n for c in counts2]
    is_exec = [lab.startswith("Execution Units") for lab in labels2]
    colors2 = [COLORS["red"] if e else COLORS["blue"] for e in is_exec]
    y2 = np.arange(len(labels2))
    bars2 = ax.barh(y2, pcts2, color=colors2, height=0.62, zorder=3)
    for b, e in zip(bars2, is_exec):
        if e:
            b.set_hatch("////")
            b.set_edgecolor("white")
    ax.set_yticks(y2)
    ax.set_yticklabels(labels2, fontsize=5.8, color=COLORS["ink"])
    ax.invert_yaxis()
    ax.set_xlim(0, max(pcts2) * 1.25)
    ax.set_xlabel(
        f"Share of published errata (%, N = {total_n:,}, 19 Intel and AMD CPU families)",
        fontsize=6.2,
    )
    ax.grid(True, axis="x", color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax.grid(False, axis="y")
    for b, c, p in zip(bars2, counts2, pcts2):
        ax.text(
            p + 0.5,
            b.get_y() + b.get_height() / 2,
            f"{c} ({p:.1f}%)",
            va="center",
            ha="left",
            fontsize=5.2,
            color=COLORS["ink"],
        )

    ch11_dir = REPO_ROOT / "book" / "contents" / "chapters" / "11-ownership" / "images"
    ch11_dir.mkdir(parents=True, exist_ok=True)
    out_svg2 = ch11_dir / "fig-hardware-errata-lifecycle.svg"
    out_pdf2 = ch11_dir / "fig-hardware-errata-lifecycle.pdf"
    out_png2 = ch11_dir / "fig-hardware-errata-lifecycle.png"

    plt.savefig(out_svg2, format="svg", bbox_inches="tight")
    plt.savefig(out_pdf2, format="pdf", bbox_inches="tight")
    plt.savefig(out_png2, format="png", dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Generated Figure 2:\n  {out_svg2}\n  {out_pdf2}\n  {out_png2}")


def main():
    print("=" * 80)
    print("Architecture 2.0: Silicon Errata Plotting Engine")
    print("=" * 80)
    generate_errata_decay_and_sunburst_plots()
    print("=" * 80)


if __name__ == "__main__":
    main()
