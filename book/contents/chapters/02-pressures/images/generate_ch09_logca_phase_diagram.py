"""Generate publication-grade 2D LogCA Offload Break-Even Phase Diagram for Chapter 9:
LogCA Break-Even Offload Frontiers Across Physical Interconnect Regimes.

Grounded in published physical standards:
1. UCIe 2.0 Advanced Package (CoWoS/EMIB, 1600 GB/s, 2.5 ns)
2. UCIe 2.0 Standard Organic Substrate (400 GB/s, 8.0 ns)
3. NVLink 5 / C2C (Blackwell B200, 900 GB/s, 15.0 ns)
4. CXL 3.1 / PCIe 6.0 (.mem/.cache PAM4, 128 GB/s, 85.0 ns)
5. PCIe Gen 5 x16 (NRZ, 64 GB/s, 140.0 ns)
6. Ultra Ethernet (UEC 1.0 / 800G RoCEv2, 100 GB/s, 450.0 ns)
7. InfiniBand NDR 400G / XDR 800G (50 GB/s, 650.0 ns)
"""

import csv
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Add repo root to sys.path
repo_root = Path(__file__).resolve().parents[5]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from book._python.plots import COLORS, apply_style


def generate_figure(output_dir: Path) -> Path:
    apply_style()

    # Load physical specs CSV
    receipts_dir = repo_root / "data" / "source-receipts"
    specs_path = receipts_dir / "chapter9-interconnect-logca-specs.csv"

    with open(specs_path, "r", encoding="utf-8") as f:
        specs = list(csv.DictReader(l for l in f if not l.startswith("#")))

    fig, ax = plt.subplots(figsize=(6.8, 4.0))
    fig.subplots_adjust(left=0.11, right=0.96, top=0.88, bottom=0.15)

    # Baseline host execution parameters (2.5 GHz CPU core: 1 FLOP/cycle = 0.4 ns/FLOP)
    C_h = 0.4e-9  # seconds per FLOP
    A = 50.0  # Local compute acceleration factor (50x)

    # Operational Intensity grid (FLOP/byte) on log scale: 0.05 to 500 FLOP/byte
    oi_grid = np.logspace(np.log10(0.05), np.log10(500), 500)

    # Color mapping for interconnect families
    regime_colors = {
        "UCIe 2.0 (Advanced TSMC CoWoS / Intel EMIB)": (COLORS["green"], "-"),
        "UCIe 2.0 (Standard Package Substrate)": (COLORS["evidence_ink"], "--"),
        "NVLink 5 / C2C (Blackwell B200)": (COLORS["blue"], "-"),
        "CXL 3.1 / PCIe 6.0 (.mem / .cache PAM4)": (COLORS["purple"], "-"),
        "PCIe Gen 5 x16 (128b/130b NRZ)": (COLORS["orange"], "-"),
        "Ultra Ethernet (UEC 1.0 / 800G RoCEv2)": (COLORS["red"], "--"),
        "InfiniBand NDR 400G / XDR 800G": (COLORS["constraints_ink"], "-"),
    }

    # Compute and plot break-even curves: g*(OI) = o / [C_h*(1 - 1/A) - 1/(OI * B)]
    # where B is in bytes/sec
    for row in specs:
        tech = row["technology"]
        if tech not in regime_colors:
            continue
        color, linestyle = regime_colors[tech]
        o = float(row["typical_host_invocation_ns"]) * 1e-9  # seconds
        B = float(row["raw_bandwidth_gb_s"]) * 1e9  # bytes/sec

        # Critical balance asymptote: OI* = 1 / (B * C_h * (1 - 1/A))
        oi_star = 1.0 / (B * C_h * (1.0 - 1.0 / A))

        # Valid OI values above asymptote
        valid_mask = oi_grid > oi_star * 1.01
        oi_sub = oi_grid[valid_mask]

        denom = C_h * (1.0 - 1.0 / A) - (1.0 / (oi_sub * B))
        g_star = o / denom

        # Short label
        short_label = tech.split("(")[0].strip()
        if "CXL" in tech:
            short_label = "CXL 3.1 / PCIe 6.0"
        elif "PCIe Gen 5" in tech:
            short_label = "PCIe Gen 5 x16"
        elif "NVLink 5" in tech:
            short_label = "NVLink 5 / C2C"
        elif "Advanced" in tech:
            short_label = "UCIe 2.0 (Adv. Package)"
        elif "Standard" in tech:
            short_label = "UCIe 2.0 (Std. Package)"
        elif "Ultra Ethernet" in tech:
            short_label = "Ultra Ethernet (800G)"
        elif "InfiniBand" in tech:
            short_label = "InfiniBand NDR (400G)"

        ax.plot(
            oi_sub,
            g_star,
            color=color,
            linestyle=linestyle,
            linewidth=1.8,
            label=short_label,
            zorder=3,
        )

        # Vertical dashed asymptote line
        ax.axvline(
            oi_star, color=color, linestyle=":", linewidth=0.7, alpha=0.6, zorder=1
        )

    # Shaded infeasibility zone (leftmost)
    ax.axvspan(0.05, 0.25, color=COLORS["red"], alpha=0.07, zorder=0)
    ax.text(
        0.06,
        3e6,
        "Physical Infeasibility Zone\n(Link Bandwidth Bound:\nOffload loses for all g)",
        fontsize=5.6,
        color=COLORS["constraints_ink"],
        fontweight="bold",
        va="center",
    )

    # Annotate domain viability bands on right
    ax.axhspan(10, 1.2e2, color=COLORS["green"], alpha=0.06, zorder=0)
    ax.text(
        380,
        22,
        "On-Package Viability\n(Sub-μs fine-grained)",
        fontsize=5.2,
        color=COLORS["evidence_ink"],
        ha="right",
        va="center",
    )

    ax.axhspan(1.2e2, 1.5e3, color=COLORS["blue"], alpha=0.05, zorder=0)
    ax.text(
        380,
        3.5e2,
        "Coherent Socket / C2C Viability\n(Mid-granularity)",
        fontsize=5.2,
        color=COLORS["workload_ink"],
        ha="right",
        va="center",
    )

    ax.axhspan(1.5e3, 5e5, color=COLORS["orange"], alpha=0.05, zorder=0)
    ax.text(
        380,
        6e4,
        "Rack / Cluster Viability\n(Coarse batch offload)",
        fontsize=5.2,
        color=COLORS["methods_ink"],
        ha="right",
        va="center",
    )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.05, 400)
    ax.set_ylim(10, 5e7)

    ax.set_xlabel(
        r"Workload Operational Intensity $\mathrm{OI}$ (FLOPs / Byte moved across interface)",
        fontsize=6.5,
        color=COLORS["ink"],
    )
    ax.set_ylabel(
        r"Break-Even Granularity $g^*$ (Operations amortized per offload)",
        fontsize=6.5,
        color=COLORS["ink"],
    )

    ax.set_xticks([0.1, 1.0, 10.0, 100.0])
    ax.set_xticklabels([r"0.1", r"1.0", r"10", r"100"], fontsize=5.8)

    ax.set_yticks([1e1, 1e2, 1e3, 1e4, 1e5, 1e6, 1e7])
    ax.set_yticklabels(
        [r"$10$", r"$10^2$", r"$10^3$", r"$10^4$", r"$10^5$", r"$10^6$", r"$10^7$"],
        fontsize=5.8,
    )

    ax.tick_params(axis="both", labelsize=5.8, length=2.5, width=0.5)
    ax.grid(axis="both", color=COLORS["grid"], linewidth=0.5, zorder=0)

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(COLORS["ink"])
    ax.spines["bottom"].set_color(COLORS["ink"])

    legend = ax.legend(
        loc="upper right",
        fontsize=5.0,
        framealpha=0.94,
        edgecolor="#E2E8F0",
        frameon=True,
        borderpad=0.3,
        labelspacing=0.25,
    )
    for text in legend.get_texts():
        text.set_color(COLORS["ink"])

    png_path = output_dir / "fig-ch09-logca-phase-diagram.png"
    svg_path = output_dir / "fig-ch09-logca-phase-diagram.svg"
    pdf_path = output_dir / "fig-ch09-logca-phase-diagram.pdf"

    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(svg_path, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Generated: {png_path}")
    return png_path


if __name__ == "__main__":
    out = Path(__file__).resolve().parent
    generate_figure(out)
