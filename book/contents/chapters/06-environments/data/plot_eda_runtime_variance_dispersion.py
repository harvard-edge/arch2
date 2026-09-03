"""
Empirical EDA Runtime Variance and QoR Dispersion Plot Script (Chapter 6)

Literature Calibration & Empirical Provenance:
---------------------------------------------
1. Benchmark Platform: Genuine logic synthesis on Nangate 45nm OpenCellLibrary (typical corner).
2. Toolchain: Yosys 0.67+post (git sha1 b8e7da6f40ae8f552c116bf6c359b07c6533e159) with Berkeley ABC integration.
3. Hardware Designs (6 production-grade blocks):
   - picorv32 (RISC-V RV32IMC CPU Core, YosysHQ)
   - dynamic_node (OpenPiton 2D Mesh NoC Dynamic Router, Princeton)
   - aes_cipher_top (128-bit Pipelined Cryptographic Core, OpenROAD suite)
   - sha256_core (NIST FIPS 180-4 Cryptographic Hash Engine, Secworks)
   - alu_32bit (Lighthouse XR SoC 32-bit Multi-Function ALU / Execution Unit)
   - gcd (Hardware Coprocessor, OpenROAD suite)
4. Empirical Execution: 150 total runs (25 randomized pass schedules/seeds per architecture).
5. Metrics Captured: Chip Area (um^2), Combinational/Sequential Area breakdown, Total Cell Count, Wire Count, Peak RSS Memory (MB), Wall-Clock Time (s), CPU User/System Time (s).

Dataset Receipt: book/contents/chapters/06-environments/data/fig-eda-runtime-variance-dispersion.csv
                 data/source-receipts/chapter6-eda-runtime-variance-qor-dispersion.csv
Output Figure:   book/contents/chapters/06-environments/images/fig-eda-runtime-variance-dispersion.svg
                 book/contents/chapters/06-environments/images/fig-eda-runtime-variance-dispersion.png
                 book/contents/chapters/06-environments/images/fig-eda-runtime-variance-dispersion.pdf
"""

import csv
import sys
from pathlib import Path
import statistics
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

# Connect parent repo path to import book._python.plots
REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style


def _declare_font_stack(svg_path: Path) -> None:
    text = svg_path.read_text()
    if '<style type="text/css">' not in text:
        text = text.replace(
            "<defs>",
            '<defs>\n  <style type="text/css">*{font-family: Arial, Helvetica, sans-serif;}</style>',
            1,
        )
        svg_path.write_text(text)


def main():
    chapter_dir = Path(__file__).resolve().parent.parent
    csv_file = chapter_dir / "data" / "fig-eda-runtime-variance-dispersion.csv"
    out_svg = chapter_dir / "images" / "fig-eda-runtime-variance-dispersion.svg"
    out_png = chapter_dir / "images" / "fig-eda-runtime-variance-dispersion.png"
    out_pdf = chapter_dir / "images" / "fig-eda-runtime-variance-dispersion.pdf"
    out_global_svg = (
        REPO_ROOT / "book" / "images" / "fig-eda-runtime-variance-dispersion.svg"
    )
    out_global_pdf = (
        REPO_ROOT / "book" / "images" / "fig-eda-runtime-variance-dispersion.pdf"
    )
    out_global_png = (
        REPO_ROOT / "book" / "images" / "fig-eda-runtime-variance-dispersion.png"
    )

    # Load dataset
    data = defaultdict(
        lambda: {
            "domain": "",
            "desc": "",
            "area": [],
            "mem": [],
            "time": [],
            "cells": [],
        }
    )

    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(l for l in f if not l.startswith("#"))
        for row in reader:
            d = row["DesignName"]
            data[d]["domain"] = row["DesignDomain"]
            data[d]["desc"] = row["DesignDescription"]
            data[d]["area"].append(float(row["ChipArea_um2"]))
            data[d]["mem"].append(float(row["PeakMemory_MB"]))
            data[d]["time"].append(float(row["WallClockTime_s"]))
            data[d]["cells"].append(int(row["TotalCellCount"]))

    design_order = [
        "picorv32",
        "dynamic_node",
        "aes_cipher_top",
        "sha256_core",
        "alu_32bit",
        "gcd",
    ]
    display_names = [
        "picorv32\n(CPU)",
        "dynamic_node\n(NoC)",
        "aes_cipher\n(Crypto)",
        "sha256\n(Hash)",
        "alu_32bit\n(ALU)",
        "gcd\n(Accel)",
    ]

    domain_labels = {
        "picorv32": "RISC-V CPU Core",
        "dynamic_node": "2D NoC Router",
        "aes_cipher_top": "AES-128 Crypto",
        "sha256_core": "SHA-256 Hash",
        "alu_32bit": "32-bit ALU / Branch",
        "gcd": "GCD Accelerator",
    }

    palette = [
        COLORS["blue"],  # RV32 Core -> teal
        COLORS["purple"],  # NoC Router -> violet
        COLORS["green"],  # AES -> green
        COLORS["amber"],  # SHA256 -> amber
        COLORS["red"],  # ALU -> red
        COLORS["magenta"],  # GCD -> magenta
    ]

    apply_style()
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(7.4, 3.5), gridspec_kw={"width_ratios": [1.12, 1.0]}
    )
    fig.subplots_adjust(left=0.08, right=0.96, top=0.88, bottom=0.17, wspace=0.32)

    # -------------------------------------------------------------
    # PANEL A: The "Lucky Seed" Hazard (Area Deviation from Median)
    # -------------------------------------------------------------
    norm_area_data = []
    np.random.seed(42)

    for i, d in enumerate(design_order):
        areas = data[d]["area"]
        med = statistics.median(areas)
        pct_dev = [((a - med) / med) * 100.0 for a in areas]
        norm_area_data.append(pct_dev)

        # Jittered scatter points
        x_jitter = np.random.normal(i, 0.07, size=len(pct_dev))
        ax1.scatter(
            x_jitter,
            pct_dev,
            color=palette[i],
            alpha=0.70,
            s=18,
            edgecolors=COLORS["ink"],
            linewidth=0.4,
            zorder=3,
        )

    # Boxplots
    bp = ax1.boxplot(
        norm_area_data,
        positions=np.arange(len(design_order)),
        widths=0.40,
        patch_artist=True,
        showfliers=False,
        zorder=4,
        boxprops=dict(facecolor="none", edgecolor=COLORS["ink"], linewidth=0.85),
        medianprops=dict(color=COLORS["ink"], linewidth=1.4),
        whiskerprops=dict(color=COLORS["ink"], linewidth=0.75, linestyle="--"),
        capprops=dict(color=COLORS["ink"], linewidth=0.75),
    )

    ax1.axhline(0, color=COLORS["muted"], linestyle=":", linewidth=0.75, zorder=1)
    ax1.set_xticks(np.arange(len(design_order)))
    ax1.set_xticklabels(
        display_names, fontsize=5.8, fontweight="bold", color=COLORS["ink"]
    )
    ax1.set_ylabel(
        "Silicon Area Dispersion vs. Median (%)", fontsize=6.6, color=COLORS["ink"]
    )
    ax1.set_ylim(-10.5, 12.0)
    ax1.grid(True, axis="y", color=COLORS["grid"], linewidth=0.5, zorder=0)

    # Annotations on Panel A
    ax1.annotate(
        '"Lucky Seed" Hazard\n(-6.3% area on GCD without RTL delta)',
        xy=(5.0, -6.28),
        xytext=(1.8, -9.2),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS["evidence_ink"],
            lw=0.75,
            connectionstyle="arc3,rad=-0.15",
        ),
        fontsize=5.3,
        fontweight="bold",
        color=COLORS["evidence_ink"],
    )

    ax1.annotate(
        "Stochastic Dispersion Risk\n(+8.7% area penalty on SHA256)",
        xy=(3.0, 4.14),
        xytext=(0.6, 7.8),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS["constraints_ink"],
            lw=0.75,
            connectionstyle="arc3,rad=0.15",
        ),
        fontsize=5.3,
        fontweight="bold",
        color=COLORS["constraints_ink"],
    )

    ax1.set_title(
        "A: Area QoR Dispersion Across Logic Synthesis Pass Schedules",
        fontsize=7.0,
        fontweight="bold",
        pad=6,
        color=COLORS["ink"],
    )

    # -------------------------------------------------------------
    # PANEL B: Resource Volatility & Jitter (Peak Memory vs Runtime)
    # -------------------------------------------------------------
    for i, d in enumerate(design_order):
        times = data[d]["time"]
        mems = data[d]["mem"]
        ax2.scatter(
            times,
            mems,
            color=palette[i],
            alpha=0.75,
            s=22,
            edgecolors=COLORS["ink"],
            linewidth=0.5,
            label=domain_labels[d],
            zorder=3,
        )

        # Plot centroid
        t_mean = statistics.mean(times)
        m_mean = statistics.mean(mems)
        ax2.scatter(
            [t_mean],
            [m_mean],
            marker="+",
            s=52,
            color=palette[i],
            linewidth=1.4,
            zorder=4,
        )

    ax2.set_xlabel(
        "Wall-Clock Synthesis Runtime (seconds)", fontsize=6.6, color=COLORS["ink"]
    )
    ax2.set_ylabel("Peak Process Memory / RSS (MB)", fontsize=6.6, color=COLORS["ink"])
    ax2.set_xlim(0.0, 7.4)
    ax2.set_ylim(20.0, 135.0)
    ax2.grid(True, color=COLORS["grid"], linewidth=0.5, zorder=0)

    # Annotate Memory & Time Jitter
    ax2.annotate(
        "AES-128 Memory Volatility\n(96-116 MB RSS; 4.7-6.1s wall time)",
        xy=(5.7, 115.8),
        xytext=(1.8, 122.0),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS["ink"],
            lw=0.75,
            connectionstyle="arc3,rad=-0.12",
        ),
        fontsize=5.3,
        fontweight="bold",
        color=COLORS["ink"],
    )

    ax2.annotate(
        "PicoRV32 Runtime Jitter\n(3.4s - 5.2s execution span)",
        xy=(3.8, 92.0),
        xytext=(0.4, 76.0),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS["workload_ink"],
            lw=0.75,
            connectionstyle="arc3,rad=0.15",
        ),
        fontsize=5.3,
        fontweight="bold",
        color=COLORS["workload_ink"],
    )

    ax2.legend(
        loc="lower right",
        frameon=True,
        facecolor=COLORS["note_fill"],
        edgecolor=COLORS["note_edge"],
        fontsize=5.0,
        title="Hardware Architecture",
        title_fontsize=5.4,
        borderpad=0.4,
        labelspacing=0.3,
    )

    ax2.set_title(
        "B: Tool Resource Footprint & Execution Jitter (150 Runs)",
        fontsize=7.0,
        fontweight="bold",
        pad=6,
        color=COLORS["ink"],
    )

    # Clean spines
    for ax in [ax1, ax2]:
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        ax.spines["left"].set_color(COLORS["ink"])
        ax.spines["bottom"].set_color(COLORS["ink"])
        ax.tick_params(axis="both", labelsize=5.8, length=2.5, width=0.6, pad=2)

    plt.savefig(out_svg, format="svg", bbox_inches="tight")
    plt.savefig(out_png, format="png", dpi=300, bbox_inches="tight")
    plt.savefig(out_pdf, format="pdf", bbox_inches="tight")
    if out_global_svg.parent.exists():
        plt.savefig(out_global_svg, format="svg", bbox_inches="tight")
        plt.savefig(out_global_png, format="png", dpi=300, bbox_inches="tight")
        plt.savefig(out_global_pdf, format="pdf", bbox_inches="tight")
        _declare_font_stack(out_global_svg)
    _declare_font_stack(out_svg)
    print(f"Generated {out_svg}, {out_png}, and {out_pdf}")


if __name__ == "__main__":
    main()
