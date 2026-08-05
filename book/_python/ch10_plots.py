"""Generate Matplotlib figures for Chapter 10 (Evaluation)."""

import sys
from pathlib import Path

# Add book directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import numpy as np

from _python.plots import COLORS, apply_style


def generate_cost_quality_frontier(output_dir: Path) -> None:
    apply_style()

    frontier_cost = np.array([1.0, 1.8, 3.0, 4.6])
    frontier_quality = np.array([0.48, 0.67, 0.81, 0.89])
    dominated_cost = np.array([2.4, 3.8, 5.2])
    dominated_quality = np.array([0.56, 0.70, 0.83])
    quality_threshold = 0.78

    fig, ax = plt.subplots(figsize=(5.6, 3.1))
    fig.subplots_adjust(left=0.13, right=0.96, top=0.88, bottom=0.19)

    ax.plot(
        frontier_cost,
        frontier_quality,
        color=COLORS["blue"],
        linewidth=1.8,
        zorder=2,
    )
    ax.scatter(
        frontier_cost,
        frontier_quality,
        color=COLORS["blue"],
        edgecolor="white",
        linewidth=0.8,
        s=42,
        label="Non-dominated workflows",
        zorder=3,
    )
    ax.scatter(
        dominated_cost,
        dominated_quality,
        color=COLORS["muted"],
        alpha=0.5,
        s=34,
        label="Dominated workflows",
        zorder=2,
    )
    ax.axhline(
        quality_threshold,
        color=COLORS["red"],
        linestyle="--",
        linewidth=1.2,
        label="Declared quality threshold",
    )

    ax.annotate(
        "lowest cost above threshold",
        xy=(3.0, 0.81),
        xytext=(3.35, 0.6),
        arrowprops=dict(arrowstyle="->", color=COLORS["ink"], lw=0.8),
        fontsize=6,
        color=COLORS["ink"],
    )

    ax.set_title(
        "Declared architecture outcome versus total workflow cost", fontsize=7.5, pad=10
    )
    ax.set_xlabel("Disclosed illustrative cost index", fontsize=6.5)
    ax.set_ylabel("Declared outcome (normalized)", fontsize=6.5)
    ax.set_xlim(0.6, 5.6)
    ax.set_ylim(0.4, 0.96)
    ax.legend(frameon=False, fontsize=5.8, loc="lower right")
    ax.tick_params(axis="both", labelsize=5.9, length=2.5, width=0.6, pad=2)
    ax.grid(True, color=COLORS["grid"], linewidth=0.55, zorder=0)

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(COLORS["ink"])
    ax.spines["bottom"].set_color(COLORS["ink"])

    svg_path = output_dir / "fig-cost-quality-frontier.svg"
    plt.savefig(svg_path, format="svg", bbox_inches="tight")
    plt.close(fig)
    print(f"Generated {svg_path}")


def generate_whac_a_mole(output_dir: Path) -> None:
    apply_style()

    iterations = np.arange(21)
    directed = [max(0, int(value)) for value in 50 * np.exp(-0.25 * iterations)]
    repeated = [
        int(50 * np.exp(-0.2 * index)) if index < 5 else 15 + 5 * (-1) ** index
        for index in iterations
    ]

    fig, ax = plt.subplots(figsize=(5.6, 3))
    fig.subplots_adjust(left=0.12, right=0.95, top=0.88, bottom=0.18)

    ax.plot(
        iterations,
        directed,
        linewidth=2.5,
        color=COLORS["green"],
        label="Directed repair",
    )
    ax.plot(
        iterations,
        repeated,
        linewidth=2.0,
        linestyle="--",
        color=COLORS["red"],
        label="Recurring violation count",
    )

    ax.annotate(
        "inspect state identity",
        xy=(10, 20),
        xytext=(11, 31),
        arrowprops=dict(arrowstyle="->", color=COLORS["ink"], lw=0.8),
        fontsize=6,
        color=COLORS["ink"],
    )

    ax.set_title("Constraint repair under repeated feedback", fontsize=7.5, pad=10)
    ax.set_xlabel("Tool iteration", fontsize=6.5)
    ax.set_ylabel("Blocking violations", fontsize=6.5)
    ax.set_xlim(0, 20)
    ax.set_ylim(-2, 55)
    ax.legend(frameon=False, fontsize=6.5, loc="upper right")
    ax.tick_params(axis="both", labelsize=5.9, length=2.5, width=0.6, pad=2)
    ax.grid(True, color=COLORS["grid"], linewidth=0.55, zorder=0)

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(COLORS["ink"])
    ax.spines["bottom"].set_color(COLORS["ink"])

    svg_path = output_dir / "fig-whac-a-mole.svg"
    plt.savefig(svg_path, format="svg", bbox_inches="tight")
    plt.close(fig)
    print(f"Generated {svg_path}")


if __name__ == "__main__":
    out_dir = (
        Path(__file__).resolve().parents[1] / "chapters" / "10-evaluation" / "images"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    generate_cost_quality_frontier(out_dir)
    generate_whac_a_mole(out_dir)
