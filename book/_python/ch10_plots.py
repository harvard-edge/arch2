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


def generate_llm_judge_bias_plot(output_dir: Path) -> None:
    apply_style()

    levels = [
        "Level 1\nSyntax & RTL",
        "Level 2\nSDC Exceptions",
        "Level 3\nCDC & Deadlocks",
        "Level 4\nHyperproperties",
    ]
    x = np.arange(len(levels))

    # False pass rates (%) on defective hardware candidates
    llama3_70b = [28.5, 56.4, 79.2, 91.6]
    gpt4o = [18.2, 42.5, 68.4, 84.1]
    claude35 = [14.0, 38.2, 62.1, 79.5]
    sva_ground_truth = [0.0, 0.0, 0.0, 0.0]

    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    fig.subplots_adjust(left=0.12, right=0.95, top=0.86, bottom=0.22)

    # Shaded sycophancy zone
    ax.fill_between(
        x, [10, 35, 60, 75], llama3_70b, color=COLORS["red"], alpha=0.08, zorder=1
    )

    # Plot model lines
    ax.plot(
        x,
        llama3_70b,
        color=COLORS["purple"],
        linewidth=1.8,
        marker="o",
        markersize=5,
        label="Llama-3-70B Judge",
        zorder=3,
    )
    ax.plot(
        x,
        gpt4o,
        color=COLORS["blue"],
        linewidth=1.8,
        marker="s",
        markersize=5,
        label="GPT-4o Judge",
        zorder=3,
    )
    ax.plot(
        x,
        claude35,
        color=COLORS["orange"],
        linewidth=1.8,
        marker="^",
        markersize=5,
        label="Claude 3.5 Sonnet Judge",
        zorder=3,
    )
    ax.plot(
        x,
        sva_ground_truth,
        color=COLORS["green"],
        linewidth=2.5,
        linestyle="-",
        label="SVA Formal Solver (Ground Truth)",
        zorder=4,
    )

    # Annotations
    ax.annotate(
        "Echoing & Sycophancy Zone\nUp to 91.6% False Passes",
        xy=(2.8, 88.0),
        xytext=(1.3, 82.0),
        arrowprops=dict(arrowstyle="->", color=COLORS["constraints_ink"], lw=0.9),
        fontsize=6.4,
        fontweight="bold",
        color=COLORS["constraints_ink"],
    )

    ax.annotate(
        "Deterministic SVA Checks\n0% Error Rate",
        xy=(1.0, 0.0),
        xytext=(0.7, 16.0),
        arrowprops=dict(arrowstyle="->", color=COLORS["evidence_ink"], lw=0.9),
        fontsize=6.4,
        fontweight="bold",
        color=COLORS["evidence_ink"],
    )

    ax.set_title(
        "LLM Evaluator Confirmation Bias vs Formal SVA Ground Truth",
        fontsize=8.0,
        pad=10,
        fontweight="bold",
    )
    ax.set_xlabel(
        "Hardware Verification Complexity and Plausible Justification Depth",
        fontsize=6.8,
        labelpad=6,
    )
    ax.set_ylabel("False Pass Rate (%) on Defective Candidates", fontsize=6.8)
    ax.set_xticks(x)
    ax.set_xticklabels(levels, fontsize=6.2)
    ax.set_ylim(-4, 100)
    ax.legend(frameon=False, fontsize=6.0, loc="upper left")
    ax.tick_params(axis="both", labelsize=6.0, length=2.5, width=0.6, pad=2)
    ax.grid(True, color=COLORS["grid"], linewidth=0.55, zorder=0)

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(COLORS["ink"])
    ax.spines["bottom"].set_color(COLORS["ink"])

    svg_path = output_dir / "fig-llm-judge-confirmation-bias.svg"
    pdf_path = output_dir / "fig-llm-judge-confirmation-bias.pdf"
    plt.savefig(svg_path, format="svg", bbox_inches="tight")
    plt.savefig(pdf_path, format="pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"Generated {svg_path} and {pdf_path}")


if __name__ == "__main__":
    out_dir = (
        Path(__file__).resolve().parents[1] / "chapters" / "10-evaluation" / "images"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    generate_cost_quality_frontier(out_dir)
    generate_whac_a_mole(out_dir)
    generate_llm_judge_bias_plot(out_dir)
