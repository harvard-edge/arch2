"""Generate SVA Formal State-Space Coverage vs BMC Depth plot for Ch07.

This script models formal verification state-space coverage and solver runtime
scaling during Bounded Model Checking (BMC) across hardware execution units
in machine learning accelerators.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add repository root to sys.path
repo_root = Path(__file__).resolve().parents[4]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import numpy as np
import matplotlib.pyplot as plt
from _python.plots import COLORS, apply_style


def generate_plot(output_dir: Path | None = None) -> str:
    """Generate and save the SVA formal coverage vs BMC depth plot."""
    apply_style()
    fig, ax1 = plt.subplots(figsize=(6.4, 3.4))
    fig.subplots_adjust(left=0.12, right=0.86, top=0.88, bottom=0.18)

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
        color=COLORS["green"],
        linewidth=2.0,
        label="DMA Ring Buffer Controller",
    )
    line2 = ax1.plot(
        depths,
        cov_barrier,
        color=COLORS["blue"],
        linewidth=2.0,
        label="All-Reduce Barrier Synchronizer",
    )
    line3 = ax1.plot(
        depths,
        cov_arbiter,
        color=COLORS["orange"],
        linewidth=2.0,
        label="Weight Buffer Arbiter",
    )
    line4 = ax1.plot(
        depths,
        cov_systolic,
        color=COLORS["red"],
        linewidth=2.0,
        label="Systolic Array Controller",
    )

    # Highlight Formal Verification Wall (SAT Solver Timeout Region)
    ax1.axvspan(
        45, 60, color=COLORS["red"], alpha=0.12, label="SAT Solver Timeout Region"
    )
    ax1.axhline(100, color=COLORS["muted"], linestyle=":", linewidth=1.0, alpha=0.7)

    ax1.set_xlabel("Bounded Model Checking (BMC) Unroll Depth (k)", fontsize=6.8)
    ax1.set_ylabel("Formal State-Space Coverage (%)", fontsize=6.8)
    ax1.set_xlim(1, 60)
    ax1.set_ylim(0, 105)
    ax1.tick_params(axis="both", labelsize=6.0, length=2.5, width=0.6, pad=2)
    ax1.grid(True, color=COLORS["grid"], linewidth=0.45, zorder=0)

    # Secondary Axis for Solver Runtime
    ax2 = ax1.twinx()
    line_rt = ax2.plot(
        depths,
        runtime_sec,
        color=COLORS["purple"],
        linewidth=1.6,
        linestyle="--",
        label="SAT Solver Runtime (s)",
    )
    ax2.set_yscale("log")
    ax2.set_ylabel(
        "Solver Runtime per Property (seconds, log scale)",
        fontsize=6.5,
        color=COLORS["purple"],
    )
    ax2.tick_params(axis="y", labelcolor=COLORS["purple"], labelsize=5.8)
    ax2.grid(False)

    # Annotations with clean background boxes in open whitespace
    ax1.annotate(
        "100% Formal Proof\n(Full Coverage at k=32)",
        xy=(32, 99.5),
        xytext=(22, 88),
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
            alpha=0.92,
            lw=0.6,
        ),
        zorder=5,
    )

    ax1.annotate(
        "State Space Explosion\n(Timeout at k > 45)",
        xy=(45, 62),
        xytext=(48, 15),
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
            alpha=0.92,
            lw=0.6,
        ),
        zorder=5,
    )

    ax1.set_title(
        "SystemVerilog Assertion Coverage vs. BMC Unroll Depth in Accelerator Units",
        fontsize=7.8,
        pad=9,
        fontweight="bold",
    )

    for spine in ["top"]:
        ax1.spines[spine].set_visible(False)
        ax2.spines[spine].set_visible(False)
    ax1.spines["left"].set_color(COLORS["ink"])
    ax1.spines["bottom"].set_color(COLORS["ink"])

    # Combine legends from both axes and place in upper left
    lines = line1 + line2 + line3 + line4 + line_rt
    labels = [l.get_label() for l in lines]
    ax1.legend(
        lines, labels, loc="upper left", framealpha=0.92, fontsize=5.0, borderpad=0.25
    )

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        svg_path = output_dir / "fig-sva-bmc-coverage-depth.svg"
        pdf_path = output_dir / "fig-sva-bmc-coverage-depth.pdf"
        png_path = output_dir / "fig-sva-bmc-coverage-depth.png"
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
