"""Generate the static candidate-check capacity figure for Chapter 5."""

from __future__ import annotations

import sys
from pathlib import Path

# book/ is on sys.path so `from _python.plots import ...` works when run as a script.
_BOOK_DIR = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_BOOK_DIR))

import matplotlib.pyplot as plt
import numpy as np

from _python.plots import COLORS, apply_style


def generate_candidate_capacity_plot(output_dir: Path) -> None:
    """Generate analytical plot contrasting candidate generation arrival rate (g) with downstream tool stage utilization (rho_i)."""
    apply_style()

    # Candidate arrival rates g (proposals per day)
    g = np.linspace(0, 50, 250)

    # Stage capacities and advance fractions from Section 5.2.2 / Table 5.2
    # Stage 1: Structural screen (1 slot, 1 min => 1440/day, p1 = 0.25)
    rho_1 = (g * 1.0) / 1440.0

    # Stage 2: Cycle-level simulation (4 slots, 8 hrs => 12/day, p2 = 0.10)
    rho_2 = (g * 0.25) / 12.0

    # Stage 3: Physical implementation screen (1 slot, 24 hrs => 1/day, p3 = 0.50)
    rho_3 = (g * 0.025) / 1.0

    fig, ax = plt.subplots(figsize=(6.2, 3.5))
    fig.subplots_adjust(left=0.13, right=0.95, top=0.86, bottom=0.19)

    # Shaded queue instability zone (rho > 1.0)
    ax.fill_between(
        g,
        1.0,
        1.3,
        where=(g >= 40.0),
        color=COLORS["red"],
        alpha=0.10,
        label="Unstable Queue Backlog (ρ3 > 1.0)",
        zorder=1,
    )

    # Plot utilization curves for tool stages
    ax.plot(
        g,
        rho_1,
        color=COLORS["workload"],
        linewidth=1.8,
        label="Stage 1: Structural Screen (μ1 = 1440/day)",
        zorder=3,
    )
    ax.plot(
        g,
        rho_2,
        color=COLORS["methods"],
        linewidth=1.8,
        linestyle="--",
        label="Stage 2: Cycle Simulation (μ2 = 12/day)",
        zorder=3,
    )
    ax.plot(
        g,
        rho_3,
        color=COLORS["constraints"],
        linewidth=2.2,
        label="Stage 3: Physical Implementation (μ3 = 1/day)",
        zorder=4,
    )

    # Horizontal queue stability limit (rho = 1.0)
    ax.axhline(
        1.0,
        color=COLORS["constraints_ink"],
        linestyle=":",
        linewidth=1.3,
        zorder=2,
    )

    # Highlight Table 5.2 operating point (g = 32 candidates/day)
    ax.scatter(
        [32.0],
        [0.80],
        color=COLORS["constraints"],
        edgecolor="white",
        s=55,
        linewidth=1.0,
        zorder=5,
    )
    ax.annotate(
        "Table 5.2 Operating Point\n(g = 32 candidates/day, ρ3 = 80%)",
        xy=(32.0, 0.80),
        xytext=(22.0, 0.28),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS["ink"],
            lw=0.8,
            connectionstyle="arc3,rad=-0.12",
        ),
        fontsize=6.2,
        fontweight="bold",
        color=COLORS["ink"],
        bbox=dict(
            boxstyle="round,pad=0.4",
            facecolor=COLORS["note_fill"],
            edgecolor=COLORS["workload"],
            lw=0.7,
        ),
    )

    # Annotate critical generation rate limit (g_max = 40 candidates/day)
    ax.axvline(
        40.0,
        color=COLORS["constraints_ink"],
        linestyle="--",
        linewidth=1.0,
        zorder=2,
    )
    ax.annotate(
        "Maximum Stable Rate\ng_max = 40 proposals/day",
        xy=(40.0, 1.0),
        xytext=(26.5, 1.15),
        arrowprops=dict(arrowstyle="->", color=COLORS["constraints_ink"], lw=0.9),
        fontsize=6.2,
        fontweight="bold",
        color=COLORS["constraints_ink"],
    )

    ax.set_title(
        "Candidate arrival rate versus downstream tool stage utilization",
        fontsize=7.5,
        pad=10,
        fontweight="bold",
        color=COLORS["ink"],
    )
    ax.set_xlabel(
        "Candidate generation arrival rate g (proposals / day)",
        fontsize=6.5,
        color=COLORS["ink"],
    )
    ax.set_ylabel(
        "Stage utilization ρi = λi / μi",
        fontsize=6.5,
        color=COLORS["ink"],
    )

    ax.set_xlim(0, 50)
    ax.set_ylim(0, 1.28)

    # Percentage tick labels on y-axis
    yticks = [0.0, 0.25, 0.50, 0.75, 1.0, 1.25]
    ytick_labels = ["0%", "25%", "50%", "75%", "100% (Limit)", "125%"]
    ax.set_yticks(yticks)
    ax.set_yticklabels(ytick_labels, fontsize=5.8)

    ax.legend(frameon=False, fontsize=5.8, loc="upper left")
    ax.grid(
        True, which="both", axis="both", color=COLORS["grid"], linewidth=0.45, zorder=0
    )

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(COLORS["ink"])
    ax.spines["bottom"].set_color(COLORS["ink"])

    output_dir.mkdir(parents=True, exist_ok=True)
    svg_path = output_dir / "fig-candidate-check-capacity.svg"
    pdf_path = output_dir / "fig-candidate-check-capacity.pdf"
    png_path = output_dir / "fig-candidate-check-capacity.png"

    plt.savefig(svg_path, format="svg", bbox_inches="tight")
    plt.savefig(pdf_path, format="pdf", bbox_inches="tight")
    plt.savefig(png_path, format="png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Generated {svg_path}, {pdf_path}, and {png_path}")


if __name__ == "__main__":
    generate_candidate_capacity_plot(Path(__file__).resolve().parent)
