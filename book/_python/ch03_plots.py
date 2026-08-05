"""Generate Matplotlib figures for Chapter 3 (Life Cycle of an Architecture Study)."""

import sys
from pathlib import Path

# Add book directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import numpy as np

from _python.plots import COLORS, apply_style


def generate_fidelity_vs_latency_tradeoff(output_dir: Path) -> None:
    """Generate scatter plot of evaluation fidelity vs turn-around latency across simulator/EDA tool tiers."""
    apply_style()

    tools = [
        {
            "name": "Analytical / roofline",
            "latency": 0.001,
            "fidelity": 0.35,
            "color": COLORS["methods"],
            "type": "Formulate / Explore",
        },
        {
            "name": "SCALE-Sim / Timeloop",
            "latency": 0.1,
            "fidelity": 0.62,
            "color": COLORS["methods"],
            "type": "Explore",
        },
        {
            "name": "gem5 / Spike",
            "latency": 15.0,
            "fidelity": 0.78,
            "color": COLORS["workload"],
            "type": "Implement",
        },
        {
            "name": "Verilator C++ Sim",
            "latency": 180.0,
            "fidelity": 0.88,
            "color": COLORS["workload"],
            "type": "Implement",
        },
        {
            "name": "FireSim (FPGA)",
            "latency": 1200.0,
            "fidelity": 0.94,
            "color": COLORS["evidence"],
            "type": "Evaluate",
        },
        {
            "name": "Yosys / OpenROAD",
            "latency": 7200.0,
            "fidelity": 0.96,
            "color": COLORS["evidence"],
            "type": "Evaluate",
        },
        {
            "name": "Synopsys / Cadence Signoff",
            "latency": 86400.0,
            "fidelity": 0.99,
            "color": COLORS["constraints"],
            "type": "Review & Decide",
        },
    ]

    fig, ax = plt.subplots(figsize=(6.4, 3.3))
    fig.subplots_adjust(left=0.14, right=0.95, top=0.88, bottom=0.18)

    latencies = [t["latency"] for t in tools]
    fidelities = [t["fidelity"] for t in tools]
    colors = [t["color"] for t in tools]

    ax.scatter(
        latencies,
        fidelities,
        c=colors,
        s=70,
        zorder=3,
        edgecolor="white",
        linewidth=0.9,
    )

    # Pareto frontier line
    sorted_idx = np.argsort(latencies)
    ax.plot(
        np.array(latencies)[sorted_idx],
        np.array(fidelities)[sorted_idx],
        color=COLORS["ink"],
        linestyle="--",
        linewidth=1.0,
        alpha=0.7,
        zorder=2,
    )

    # Label points
    offsets = [
        (0.0012, 0.33),
        (0.12, 0.60),
        (18.0, 0.76),
        (220.0, 0.86),
        (1400.0, 0.92),
        (8500.0, 0.97),
        (100000.0, 0.97),
    ]
    for i, t in enumerate(tools):
        ax.text(
            offsets[i][0],
            offsets[i][1],
            t["name"],
            fontsize=5.8,
            fontweight="bold",
            color=COLORS["ink"],
            va="center",
        )

    ax.set_xscale("log")
    ax.set_xlim(5e-4, 5e5)
    ax.set_ylim(0.25, 1.05)

    xticks = [1e-3, 1e-1, 10, 3600, 86400]
    xtick_labels = ["1 ms", "100 ms", "10 s", "1 hour", "1 day"]
    ax.set_xticks(xticks)
    ax.set_xticklabels(xtick_labels, fontsize=5.8)

    ax.set_title(
        "Evaluation tool fidelity versus turn-around latency",
        fontsize=7.8,
        pad=10,
        fontweight="bold",
        color=COLORS["ink"],
    )
    ax.set_xlabel(
        "Evaluation latency per candidate (seconds, log scale)",
        fontsize=6.5,
        color=COLORS["ink"],
    )
    ax.set_ylabel(
        "Physical & architectural fidelity (normalized)",
        fontsize=6.5,
        color=COLORS["ink"],
    )

    ax.grid(True, color=COLORS["grid"], linewidth=0.45, zorder=0)

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(COLORS["ink"])
    ax.spines["bottom"].set_color(COLORS["ink"])

    output_dir.mkdir(parents=True, exist_ok=True)
    svg_path = output_dir / "fig-eval-fidelity-latency.svg"
    plt.savefig(svg_path, format="svg", bbox_inches="tight")
    plt.close(fig)
    print(f"Generated {svg_path}")


if __name__ == "__main__":
    out_dir = (
        Path(__file__).resolve().parents[1] / "chapters" / "03-lifecycle" / "images"
    )
    generate_fidelity_vs_latency_tradeoff(out_dir)
