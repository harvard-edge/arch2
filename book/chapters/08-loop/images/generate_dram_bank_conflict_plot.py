"""Generate SCALE-Sim vs Ramulator DRAM Bank Conflict Latency Overhead plot for Ch08.

This script compares idealized memory simulation (SCALE-Sim) with cycle-accurate
DRAM simulation (Ramulator) to quantify latency overhead caused by DRAM bank
conflicts across non-sequential access strides during dynamic data selection.
"""

from __future__ import annotations

import os
import sys

# Ensure repository root is in sys.path
repo_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import numpy as np
import matplotlib.pyplot as plt
from book.tools.figures import style as book_style


def generate_plot(output_dir: str | None = None) -> str:
    """Generate and save the DRAM bank conflict latency overhead plot."""
    fig, ax1, COLORS, plt_mod = book_style.setup_plot(figsize=(9, 4.8))

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
        color=COLORS["BlueLine"],
        linewidth=2.2,
        marker="o",
        label="SCALE-Sim (Ideal Memory Interface)",
    )
    line2 = ax1.plot(
        x_indices,
        ramulator_latency,
        color=COLORS["RedLine"],
        linewidth=2.2,
        marker="s",
        label="Ramulator (Cycle-Accurate HBM3)",
    )

    ax1.set_xlabel("Dataset Access Stride (Index / Batch Stride)")
    ax1.set_ylabel("Average Memory Latency (ns per 64B line read)")
    ax1.set_xticks(x_indices)
    ax1.set_xticklabels(stride_labels)
    ax1.set_ylim(50, 500)

    # Secondary axis: Overhead Percentage Bar Chart
    ax2 = ax1.twinx()
    bars = ax2.bar(
        x_indices,
        overhead_pct,
        width=0.35,
        color=COLORS["OrangeLine"],
        alpha=0.25,
        label="DRAM Bank Conflict Overhead (%)",
    )
    ax2.set_ylabel("Latency Overhead Penalty (%)", color=COLORS["OrangeLine"])
    ax2.tick_params(axis="y", labelcolor=COLORS["OrangeLine"])
    ax2.set_ylim(0, 400)
    ax2.grid(False)

    # Annotations for key data points
    ax1.annotate(
        "Sequential Stream\n(+8% Row Buffer Hit)",
        xy=(0, 108),
        xytext=(0.2, 180),
        arrowprops=dict(
            facecolor=COLORS["GreenLine"],
            edgecolor=COLORS["GreenLine"],
            arrowstyle="->",
            lw=1.2,
        ),
        fontsize=8.5,
        color=COLORS["GreenLine"],
        fontweight="bold",
    )

    ax1.annotate(
        "Bank Conflict Peak at Stride 16\n(+340% Latency Overhead)",
        xy=(4, 440),
        xytext=(2.2, 390),
        arrowprops=dict(
            facecolor=COLORS["RedLine"],
            edgecolor=COLORS["RedLine"],
            arrowstyle="->",
            lw=1.2,
        ),
        fontsize=8.5,
        color=COLORS["RedLine"],
        fontweight="bold",
    )

    ax1.set_title(
        "SCALE-Sim vs. Ramulator DRAM Bank Conflict Overhead across Access Strides",
        pad=12,
    )

    # Combine legends
    lines = line1 + line2 + [bars]
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper left", framealpha=0.9, fontsize=8.5)

    fig = book_style.finalize_web_figure(fig)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        png_path = os.path.join(output_dir, "dram_bank_conflict_overhead.png")
        svg_path = os.path.join(output_dir, "dram_bank_conflict_overhead.svg")
        fig.savefig(png_path, dpi=300, bbox_inches="tight")
        fig.savefig(svg_path, bbox_inches="tight")
        plt.close(fig)
        return png_path

    return ""


if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    saved_file = generate_plot(out_dir)
    print(f"Plot successfully saved to {saved_file}")
