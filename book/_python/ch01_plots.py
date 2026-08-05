"""Generate Matplotlib figures for Chapter 1 (The Moonshot)."""

import sys
from pathlib import Path

# Add book directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import numpy as np

from _python.plots import COLORS, apply_style


def generate_verification_scaling(output_dir: Path) -> None:
    """Generate plot contrasting AI candidate generation rate with verification evaluation latency across design scales."""
    apply_style()

    categories = [
        "Tensor Operator\n(AutoTVM / MAESTRO)",
        "Core Microarch\n(gem5 / Spike)",
        "RTL Block Signoff\n(Verilator / Yosys)",
        "Subsystem Macro\n(OpenROAD 7nm)",
        "Full SoC Signoff\n(Cadence / Formality)",
    ]
    y_pos = np.arange(len(categories))

    # Latency per candidate evaluation (seconds, log scale)
    eval_latency_min = np.array([0.001, 10.0, 300.0, 3600.0, 86400.0])
    eval_latency_max = np.array([0.1, 300.0, 3600.0, 28800.0, 604800.0])

    # AI generation latency per candidate (seconds)
    gen_latency = np.array([0.5, 2.0, 5.0, 15.0, 45.0])

    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    fig.subplots_adjust(left=0.28, right=0.94, top=0.88, bottom=0.18)

    # Plot evaluation latency ranges (bars)
    for i in range(len(categories)):
        ax.barh(
            y_pos[i] + 0.15,
            eval_latency_max[i] - eval_latency_min[i],
            left=eval_latency_min[i],
            height=0.35,
            color=COLORS["constraints"],
            alpha=0.85,
            edgecolor=COLORS["constraints_ink"],
            linewidth=0.8,
            label="Hardware verification check time" if i == 0 else "",
            zorder=2,
        )

    # Plot generation throughput (dots)
    ax.scatter(
        gen_latency,
        y_pos - 0.15,
        color=COLORS["workload"],
        s=48,
        zorder=4,
        edgecolor="white",
        linewidth=0.8,
        label="AI candidate proposal latency",
    )

    ax.set_xscale("log")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(categories, fontsize=6.2, color=COLORS["ink"])
    ax.invert_yaxis()  # top-down flow

    ax.set_title(
        "Candidate generation velocity versus verification check time",
        fontsize=7.8,
        pad=10,
        fontweight="bold",
        color=COLORS["ink"],
    )
    ax.set_xlabel(
        "Time per candidate (seconds, log scale)", fontsize=6.5, color=COLORS["ink"]
    )
    ax.set_xlim(1e-4, 1e6)

    # Add custom tick labels for clarity
    xticks = [1e-3, 1e-1, 10, 3600, 86400, 604800]
    xtick_labels = ["1 ms", "100 ms", "10 s", "1 hour", "1 day", "1 week"]
    ax.set_xticks(xticks)
    ax.set_xticklabels(xtick_labels, fontsize=5.8)

    ax.legend(frameon=False, fontsize=6.0, loc="lower right")
    ax.grid(
        True, which="both", axis="x", color=COLORS["grid"], linewidth=0.45, zorder=0
    )

    # Annotate the scissors gap
    ax.annotate(
        "5-order-of-magnitude\nverification gap",
        xy=(1e4, 3.85),
        xytext=(3e1, 3.2),
        arrowprops=dict(arrowstyle="->", color=COLORS["constraints_ink"], lw=0.9),
        fontsize=6.0,
        fontweight="bold",
        color=COLORS["constraints_ink"],
        bbox=dict(
            boxstyle="round,pad=0.3",
            facecolor=COLORS["note_fill"],
            edgecolor=COLORS["constraints"],
            lw=0.6,
        ),
    )

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(COLORS["ink"])
    ax.spines["bottom"].set_color(COLORS["ink"])

    output_dir.mkdir(parents=True, exist_ok=True)
    svg_path = output_dir / "fig-verification-scaling.svg"
    plt.savefig(svg_path, format="svg", bbox_inches="tight")
    plt.close(fig)
    print(f"Generated {svg_path}")


if __name__ == "__main__":
    out_dir = (
        Path(__file__).resolve().parents[1] / "chapters" / "01-moonshot" / "images"
    )
    generate_verification_scaling(out_dir)
