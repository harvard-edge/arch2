"""Generate SVA Formal State-Space Coverage vs BMC Depth plot for Ch07.

This script models formal verification state-space coverage and solver runtime
scaling during Bounded Model Checking (BMC) across hardware execution units
in machine learning accelerators.
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
    """Generate and save the SVA formal coverage vs BMC depth plot."""
    fig, ax1, COLORS, plt_mod = book_style.setup_plot(figsize=(9, 4.8))

    # BMC unroll depth array
    depths = np.arange(1, 61, 1)

    # 1. DMA Ring Buffer Controller (Fast formal convergence)
    cov_dma = 100.0 / (1.0 + np.exp(-0.22 * (depths - 12)))
    cov_dma = np.clip(cov_dma, 5.0, 100.0)

    # 2. All-Reduce Ring Barrier Synchronizer (Moderate convergence)
    cov_barrier = 100.0 / (1.0 + np.exp(-0.16 * (depths - 20)))
    cov_barrier = np.clip(cov_barrier, 3.0, 100.0)

    # 3. Weight Buffer Arbiter (Hits SAT solver timeout around depth 48)
    cov_arbiter = 92.0 / (1.0 + np.exp(-0.13 * (depths - 24)))
    cov_arbiter = np.clip(cov_arbiter, 2.0, 92.0)

    # 4. Systolic Array Controller (Complex state machine, state space explosion)
    cov_systolic = 78.0 / (1.0 + np.exp(-0.10 * (depths - 28)))
    cov_systolic = np.clip(cov_systolic, 1.0, 78.0)

    # Solver Runtime (seconds, exponential explosion on twin axis)
    runtime_sec = 0.05 * np.exp(0.21 * depths)

    # Plot Coverage Curves on Primary Axis
    line1 = ax1.plot(
        depths,
        cov_dma,
        color=COLORS["GreenLine"],
        linewidth=2.2,
        label="DMA Ring Buffer Controller",
    )
    line2 = ax1.plot(
        depths,
        cov_barrier,
        color=COLORS["BlueLine"],
        linewidth=2.2,
        label="All-Reduce Barrier Synchronizer",
    )
    line3 = ax1.plot(
        depths,
        cov_arbiter,
        color=COLORS["OrangeLine"],
        linewidth=2.2,
        label="Weight Buffer Arbiter",
    )
    line4 = ax1.plot(
        depths,
        cov_systolic,
        color=COLORS["RedLine"],
        linewidth=2.2,
        label="Systolic Array Controller",
    )

    # Highlight Formal Verification Wall (SAT Solver Timeout Region)
    ax1.axvspan(
        45, 60, color=COLORS["RedFill"], alpha=0.35, label="SAT Solver Timeout Region"
    )
    ax1.axhline(100, color="#888888", linestyle=":", linewidth=1.0, alpha=0.7)

    ax1.set_xlabel("Bounded Model Checking (BMC) Unroll Depth (k)")
    ax1.set_ylabel("Formal State-Space Coverage (%)")
    ax1.set_xlim(1, 60)
    ax1.set_ylim(0, 105)

    # Secondary Axis for Solver Runtime
    ax2 = ax1.twinx()
    line_rt = ax2.plot(
        depths,
        runtime_sec,
        color=COLORS["VioletLine"],
        linewidth=1.8,
        linestyle="--",
        label="SAT Solver Runtime (s)",
    )
    ax2.set_yscale("log")
    ax2.set_ylabel(
        "Solver Runtime per Property (seconds, log scale)", color=COLORS["VioletLine"]
    )
    ax2.tick_params(axis="y", labelcolor=COLORS["VioletLine"])
    ax2.grid(False)

    # Annotations
    ax1.annotate(
        "100% Formal Proof\n(Full Coverage at k=32)",
        xy=(32, 100),
        xytext=(18, 92),
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
        "State Space Explosion\n(Timeout at k > 45)",
        xy=(48, 76),
        xytext=(34, 55),
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

    # Title & Legend
    ax1.set_title(
        "SystemVerilog Assertion (SVA) Coverage vs. BMC Unroll Depth in Accelerator Logic",
        pad=12,
    )

    # Combine legends from both axes
    lines = line1 + line2 + line3 + line4 + line_rt
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper left", framealpha=0.9, fontsize=8.5)

    fig = book_style.finalize_web_figure(fig)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        png_path = os.path.join(output_dir, "sva_bmc_coverage_depth.png")
        svg_path = os.path.join(output_dir, "sva_bmc_coverage_depth.svg")
        fig.savefig(png_path, dpi=300, bbox_inches="tight")
        fig.savefig(svg_path, bbox_inches="tight")
        plt.close(fig)
        return png_path

    return ""


if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    saved_file = generate_plot(out_dir)
    print(f"Plot successfully saved to {saved_file}")
