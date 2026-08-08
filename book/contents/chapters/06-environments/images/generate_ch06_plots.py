"""Generate Matplotlib figures for Chapter 6 (Environments)."""

import sys
from pathlib import Path

# Add book directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

import matplotlib.pyplot as plt
import numpy as np

from _python.plots import COLORS, apply_style


def generate_simulation_spectrum(output_dir: Path) -> None:
    """Generate high-impact plot of gem5 vs FireSim vs VCS simulation speedup vs fidelity spectrum."""
    apply_style()

    # Data points: (Name, Throughput_KIPS, Cycle_Error_Pct, Setup_Time_Hours, Color, Align_H, Align_V, Text_Offset)
    environments = [
        (
            "VCS / Verilator\n(Cycle-exact RTL)",
            4.5,
            0.0,
            1.5,
            COLORS["red"],
            "left",
            "bottom",
            (8, 0.6),
        ),
        (
            "FireSim FPGA\n(Cycle-exact @ 25 MHz)",
            24000.0,
            0.0,
            4.0,
            COLORS["green"],
            "center",
            "bottom",
            (0, 1.2),
        ),
        (
            "gem5 / SST\n(Detailed microarch)",
            280.0,
            4.2,
            0.1,
            COLORS["blue"],
            "left",
            "top",
            (8, -1.2),
        ),
        (
            "Spike / QEMU\n(Functional ISA)",
            48000.0,
            18.5,
            0.01,
            COLORS["orange"],
            "left",
            "center",
            (8, 0),
        ),
        (
            "Analytical Roofline\n(Bound model)",
            8500000.0,
            26.0,
            0.001,
            COLORS["muted"],
            "right",
            "top",
            (-8, -1.0),
        ),
        (
            "Fabricated Silicon\n(Physical chip)",
            2200000.0,
            0.0,
            720.0,
            COLORS["magenta"],
            "right",
            "bottom",
            (-10, 0.8),
        ),
    ]

    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    fig.subplots_adjust(left=0.12, right=0.95, top=0.88, bottom=0.18)

    # Plot Pareto optimal frontier connecting key simulation points
    pareto_x = [4.5, 24000.0, 2200000.0]
    pareto_y = [0.0, 0.0, 0.0]
    ax.plot(
        pareto_x,
        pareto_y,
        color=COLORS["grid"],
        linewidth=1.2,
        linestyle="--",
        zorder=1,
    )

    tradeoff_x = [4.5, 280.0, 48000.0, 8500000.0]
    tradeoff_y = [0.0, 4.2, 18.5, 26.0]
    ax.plot(
        tradeoff_x,
        tradeoff_y,
        color=COLORS["grid"],
        linewidth=1.2,
        linestyle=":",
        zorder=1,
    )

    # Plot scatter bubbles (size proportional to log setup time)
    for name, kips, error, setup_h, color, ha, va, offset in environments:
        # Scale bubble size: min 40, max 220
        bubble_size = 45 + 25 * np.log10(max(0.01, setup_h * 60) + 1.0)
        ax.scatter(
            kips,
            error,
            s=bubble_size * 2.2,
            color=color,
            alpha=0.85,
            edgecolor=COLORS["ink"],
            linewidth=0.8,
            zorder=4,
        )

        ax.annotate(
            name,
            xy=(kips, error),
            xytext=(offset[0], offset[1] * 1.8),
            textcoords="offset points",
            fontsize=5.8,
            fontweight="bold",
            color=color if color != COLORS["muted"] else COLORS["ink"],
            ha=ha,
            va=va,
            zorder=5,
        )

    # Callout annotation for FireSim hardware acceleration advantage
    ax.annotate(
        "FireSim FPGA Sweet Spot\n(5,300x faster than VCS @ 0% RTL error)",
        xy=(24000.0, 0.0),
        xytext=(150, 8.5),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS["ink"],
            lw=0.8,
            connectionstyle="arc3,rad=-0.2",
        ),
        fontsize=6.0,
        fontweight="bold",
        color=COLORS["evidence_ink"],
    )

    ax.set_xscale("log")
    ax.set_xlim(1.0, 20000000.0)
    ax.set_ylim(-1.5, 30.0)

    ax.set_title(
        "Simulation Speedup versus Fidelity Spectrum Across Hardware Environments",
        fontsize=8.0,
        pad=9,
        fontweight="bold",
    )
    ax.set_xlabel(
        "Simulation Throughput (Kilo-Instructions Per Second, log scale)", fontsize=6.8
    )
    ax.set_ylabel(
        "Microarchitectural Cycle Error Rate (%) (lower is better)", fontsize=6.8
    )

    ax.tick_params(axis="both", labelsize=6.0, length=2.5, width=0.6, pad=2)
    ax.grid(True, color=COLORS["grid"], linewidth=0.45, zorder=0)

    # Add legend note for bubble sizes
    ax.text(
        0.03,
        0.92,
        "Bubble size indicates setup & build overhead time",
        transform=ax.transAxes,
        fontsize=5.6,
        color=COLORS["muted"],
        fontweight="bold",
        bbox=dict(
            boxstyle="round,pad=0.3",
            facecolor=COLORS["note_fill"],
            edgecolor=COLORS["note_edge"],
            lw=0.5,
        ),
    )

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(COLORS["ink"])
    ax.spines["bottom"].set_color(COLORS["ink"])

    svg_path = output_dir / "fig-ch06-simulation-spectrum.svg"
    plt.savefig(svg_path, format="svg", bbox_inches="tight")
    plt.close(fig)
    print(f"Generated {svg_path}")


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)
    generate_simulation_spectrum(out_dir)
