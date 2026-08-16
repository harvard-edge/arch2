"""
GitHub Software vs Hardware Divide Plot
---------------------------------------
Visualizes the empirical divide between software and hardware ecosystems on GitHub:
Panel A: Public Code Volume & Repository Scale (Software languages vs Hardware HDLs across The Stack v2).
Panel B: The Hardware Synthesizability & Signoff Funnel (From 100% public HDL files to <1% DRC/LVS clean tapeout silicon).
"""

import csv
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style

apply_style()


def main():
    csv_file = (
        REPO_ROOT
        / "data"
        / "source-receipts"
        / "chapter1-github-software-hardware-divide.csv"
    )
    out_svg = (
        REPO_ROOT
        / "book"
        / "contents"
        / "chapters"
        / "01-moonshot"
        / "images"
        / "fig-ch01-github-hardware-divide.svg"
    )
    out_pdf = (
        REPO_ROOT
        / "book"
        / "contents"
        / "chapters"
        / "01-moonshot"
        / "images"
        / "fig-ch01-github-hardware-divide.pdf"
    )
    out_png = (
        REPO_ROOT
        / "book"
        / "contents"
        / "chapters"
        / "01-moonshot"
        / "images"
        / "fig-ch01-github-hardware-divide.png"
    )
    out_svg.parent.mkdir(parents=True, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(7.5, 3.6), gridspec_kw={"width_ratios": [1.02, 1.18]}
    )
    fig.subplots_adjust(wspace=0.36, left=0.10, right=0.96, top=0.88, bottom=0.25)

    # -------------------------------------------------------------
    # Panel A: Public Code Volume on GitHub (The Stack v2 GB)
    # -------------------------------------------------------------
    languages = [
        ("JavaScript", 1115.4, COLORS["purple"], "SW"),
        ("Java", 548.0, COLORS["purple"], "SW"),
        ("C++", 353.9, COLORS["purple"], "SW"),
        ("Python", 233.3, COLORS["purple"], "SW"),
        ("C", 202.1, COLORS["purple"], "SW"),
        ("TypeScript", 61.0, COLORS["purple"], "SW"),
        ("Rust", 15.6, COLORS["purple"], "SW"),
        ("VHDL", 2.1, COLORS["red"], "HW"),
        ("SystemVerilog", 0.8, COLORS["red"], "HW"),
        ("Verilog", 0.7, COLORS["red"], "HW"),
        ("Chisel/BSV", 0.16, COLORS["red"], "HW"),
    ]

    names = [l[0] for l in reversed(languages)]
    sizes = [l[1] for l in reversed(languages)]
    bar_colors = [l[2] for l in reversed(languages)]

    y_pos = np.arange(len(names))
    x_min = 0.05
    bar_widths = [s - x_min for s in sizes]
    bars = ax1.barh(
        y_pos,
        bar_widths,
        left=x_min,
        color=bar_colors,
        alpha=0.88,
        height=0.62,
        zorder=3,
    )
    ax1.set_xscale("log")
    ax1.set_xlim(0.05, 3000)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(names, fontsize=5.8, color=COLORS["ink"])
    ax1.set_xlabel(
        "Deduplicated Code Volume in The Stack v2 (GB, Log Scale)", fontsize=6.6
    )
    ax1.set_title(
        "Panel A: Public Open-Source Code Volume Gap",
        fontsize=7.6,
        fontweight="bold",
        pad=8,
    )
    ax1.grid(True, which="both", color=COLORS["grid"], linewidth=0.5, zorder=0)

    # Annotate total SW vs HW with clear bounding boxes
    ax1.text(
        15.0,
        3.6,
        "Software: >2,500 GB\n(419M+ files)",
        fontsize=5.2,
        fontweight="bold",
        color=COLORS["purple"],
        ha="left",
        va="center",
        bbox=dict(
            boxstyle="round,pad=0.3",
            facecolor="white",
            edgecolor=COLORS["purple"],
            alpha=0.92,
            lw=0.7,
        ),
        zorder=5,
    )
    ax1.text(
        15.0,
        1.1,
        "Hardware HDLs: ~3.8 GB\n(<0.2% of total code)",
        fontsize=5.2,
        fontweight="bold",
        color=COLORS["red"],
        ha="left",
        va="center",
        bbox=dict(
            boxstyle="round,pad=0.3",
            facecolor="white",
            edgecolor=COLORS["red"],
            alpha=0.92,
            lw=0.7,
        ),
        zorder=5,
    )

    # -------------------------------------------------------------
    # Panel B: Hardware Synthesizability & Signoff Funnel
    # -------------------------------------------------------------
    funnel_stages = [
        "1. Public HDLs\n(GitHub)",
        "2. AST Syntax\nParsable",
        "3. Open EDA\nElaboratable",
        "4. Gate Netlist\nSynthesizable",
        "5. Automated CI\n& Testbenches",
        "6. Tapeout-Ready\nSignoff",
    ]
    funnel_pcts = [100.0, 72.4, 38.1, 18.0, 7.2, 0.85]
    funnel_colors = [
        COLORS["ink"],
        COLORS["blue"],
        COLORS["orange"],
        COLORS["green"],
        COLORS["purple"],
        COLORS["red"],
    ]

    x_funnel = np.arange(len(funnel_stages))
    y_min = 0.2
    bar_heights = [p - y_min for p in funnel_pcts]
    bars2 = ax2.bar(
        x_funnel,
        bar_heights,
        bottom=y_min,
        color=funnel_colors,
        alpha=0.88,
        width=0.54,
        zorder=3,
    )
    ax2.set_yscale("log")
    ax2.set_ylim(0.2, 250)
    ax2.set_xticks(x_funnel)
    ax2.set_xticklabels(
        funnel_stages, fontsize=5.2, color=COLORS["ink"], rotation=24, ha="right"
    )
    ax2.set_ylabel("Yield / Pass Rate (% Log Scale)", fontsize=6.6)
    ax2.set_title(
        "Panel B: Hardware Synthesizability & Signoff Funnel",
        fontsize=7.6,
        fontweight="bold",
        pad=8,
    )
    ax2.grid(True, which="both", color=COLORS["grid"], linewidth=0.5, zorder=0)

    for bar, val in zip(bars2, funnel_pcts):
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            val * 1.35,
            f"{val:.1f}%" if val >= 1.0 else f"{val:.2f}%",
            ha="center",
            va="bottom",
            fontsize=5.2,
            fontweight="bold",
            color=COLORS["ink"],
        )

    # Annotate bottom bottleneck without crossing bars
    ax2.annotate(
        "Severe Physical Attrition\n(<1% tapeout-ready silicon)",
        xy=(5, 0.85),
        xytext=(2.6, 0.35),
        arrowprops=dict(arrowstyle="->", color=COLORS["red"], lw=0.9),
        fontsize=5.2,
        fontweight="bold",
        color=COLORS["red"],
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor="white",
            edgecolor=COLORS["red"],
            alpha=0.92,
            lw=0.7,
        ),
        zorder=5,
    )

    plt.savefig(out_svg, format="svg", bbox_inches="tight")
    plt.savefig(out_pdf, format="pdf", bbox_inches="tight")
    plt.savefig(out_png, format="png", dpi=300, bbox_inches="tight")
    plt.close()
    print(
        f"Generated GitHub Software vs Hardware Divide plot -> {out_svg} and {out_pdf}"
    )


if __name__ == "__main__":
    main()
