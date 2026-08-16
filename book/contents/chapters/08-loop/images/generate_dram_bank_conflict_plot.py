"""Generate SCALE-Sim vs Ramulator DRAM Bank Conflict Latency Overhead plot for Ch08.

This script compares idealized memory simulation (SCALE-Sim) with cycle-accurate
DRAM simulation (Ramulator) to quantify latency overhead caused by DRAM bank
conflicts across non-sequential access strides during dynamic data selection.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repository root is in sys.path
repo_root = Path(__file__).resolve().parents[4]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import numpy as np
import matplotlib.pyplot as plt
from _python.plots import COLORS, apply_style


def generate_plot(output_dir: Path | None = None) -> str:
    """Generate and save the DRAM bank conflict latency overhead plot."""
    apply_style()
    fig, ax1 = plt.subplots(figsize=(6.4, 3.4))
    fig.subplots_adjust(left=0.12, right=0.86, top=0.88, bottom=0.18)

    strides = np.array([1, 2, 4, 8, 16, 32, 64, 128])
    stride_labels = [str(s) for s in strides]
    x_indices = np.arange(len(strides))

    # Latency values in nanoseconds
    scalesim_latency = np.full(len(strides), 100.0)  # Flat ideal 100 ns
    ramulator_latency = np.array(
        [108.0, 145.0, 210.0, 310.0, 440.0, 350.0, 280.0, 280.0]
    )

    # Percentage overhead penalty
    overhead_pct = ((ramulator_latency - scalesim_latency) / scalesim_latency) * 100.0

    # Primary axis: Latency lines
    line1 = ax1.plot(
        x_indices,
        scalesim_latency,
        color=COLORS["blue"],
        linewidth=2.0,
        marker="o",
        label="SCALE-Sim (Flat Memory Interface)",
    )
    line2 = ax1.plot(
        x_indices,
        ramulator_latency,
        color=COLORS["red"],
        linewidth=2.0,
        marker="s",
        label="Ramulator (Cycle-Accurate DRAM)",
    )

    ax1.set_xlabel("Dataset Access Stride (Index / Batch Stride)", fontsize=6.8)
    ax1.set_ylabel("Average Memory Latency (ns per 64B line read)", fontsize=6.8)
    ax1.set_xticks(x_indices)
    ax1.set_xticklabels(stride_labels, fontsize=6.0)
    ax1.set_ylim(50, 530)
    ax1.tick_params(axis="both", labelsize=6.0, length=2.5, width=0.6, pad=2)
    ax1.grid(True, color=COLORS["grid"], linewidth=0.45, zorder=0)

    # Secondary axis: Overhead Percentage Bar Chart
    ax2 = ax1.twinx()
    bars = ax2.bar(
        x_indices,
        overhead_pct,
        width=0.35,
        color=COLORS["orange"],
        alpha=0.25,
        label="DRAM Bank Conflict Overhead (%)",
    )
    ax2.set_ylabel("Latency Overhead Penalty (%)", fontsize=6.5, color=COLORS["orange"])
    ax2.tick_params(axis="y", labelcolor=COLORS["orange"], labelsize=5.8)
    ax2.set_ylim(0, 420)
    ax2.grid(False)

    # Annotations for key data points with clean background boxes
    ax1.annotate(
        "Sequential Stream\n(+8% Row Buffer Hit)",
        xy=(0, 108),
        xytext=(0.2, 190),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS["green"],
            lw=0.9,
        ),
        fontsize=5.2,
        color=COLORS["green"],
        fontweight="bold",
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="white",
            edgecolor=COLORS["green"],
            alpha=0.9,
            lw=0.6,
        ),
        zorder=5,
    )

    ax1.annotate(
        "Bank Conflict Peak at Stride 16\n(+340% Latency Overhead)",
        xy=(4, 440),
        xytext=(2.2, 470),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS["red"],
            lw=0.9,
        ),
        fontsize=5.2,
        color=COLORS["red"],
        fontweight="bold",
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="white",
            edgecolor=COLORS["red"],
            alpha=0.9,
            lw=0.6,
        ),
        zorder=5,
    )

    ax1.set_title(
        "SCALE-Sim vs. Ramulator DRAM Bank Conflict Overhead across Access Strides",
        fontsize=7.8,
        pad=9,
        fontweight="bold",
    )

    for spine in ["top"]:
        ax1.spines[spine].set_visible(False)
        ax2.spines[spine].set_visible(False)
    ax1.spines["left"].set_color(COLORS["ink"])
    ax1.spines["bottom"].set_color(COLORS["ink"])

    # Combine legends
    lines = line1 + line2 + [bars]
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper left", framealpha=0.9, fontsize=5.2)

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        svg_path = output_dir / "fig-dram-bank-conflict.svg"
        pdf_path = output_dir / "fig-dram-bank-conflict.pdf"
        png_path = output_dir / "fig-dram-bank-conflict.png"
        fig.savefig(svg_path, format="svg", bbox_inches="tight")
        fig.savefig(pdf_path, format="pdf", bbox_inches="tight")
        fig.savefig(png_path, format="png", dpi=300, bbox_inches="tight")
        plt.close(fig)
        return str(svg_path)

    return ""


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    saved_file = generate_plot(out_dir)
    print(f"Plot successfully saved to {saved_file}")
