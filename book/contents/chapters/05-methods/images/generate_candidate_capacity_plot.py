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

    # Constructed parameters from the chapter's illustrative capacity table
    # (tbl-candidate-check-capacity): parallel slots c_i, mean runtime t_i in
    # hours, and conditional advance fraction p_i. Nothing here is measured.
    stages = [
        {"slots": 1, "hours": 1.0 / 60.0, "advance": 0.25},  # structural screen
        {"slots": 4, "hours": 8.0, "advance": 0.10},  # cycle-level simulation
        {"slots": 1, "hours": 24.0, "advance": 0.50},  # implementation screen
    ]
    capacity = [st["slots"] * 24.0 / st["hours"] for st in stages]  # mu_i per day
    reach = [1.0]  # fraction of proposals arriving at stage i
    for st in stages[:-1]:
        reach.append(reach[-1] * st["advance"])
    g_max = min(mu / r for mu, r in zip(capacity, reach))
    g_op = 32.0
    rho3_op = g_op * reach[2] / capacity[2]

    g = np.linspace(0, 50, 250)
    rho_1, rho_2, rho_3 = (g * r / mu for mu, r in zip(capacity, reach))

    fig, ax = plt.subplots()
    fig.subplots_adjust(left=0.13, right=0.95, top=0.86, bottom=0.19)

    # Shaded queue instability zone (rho > 1.0)
    ax.fill_between(
        g,
        1.0,
        1.3,
        where=(g >= g_max),
        color=COLORS["red"],
        alpha=0.10,
        label="Implementation overload (ρ3 > 1)",
        zorder=1,
    )

    # Plot utilization curves for tool stages
    ax.plot(
        g,
        rho_1,
        color=COLORS["workload"],
        linewidth=1.8,
        label=f"Structural screen (μ1 = {capacity[0]:,.0f}/day)",
        zorder=3,
    )
    ax.plot(
        g,
        rho_2,
        color=COLORS["methods"],
        linewidth=1.8,
        linestyle="--",
        label=f"Cycle-level simulation (μ2 = {capacity[1]:.0f}/day)",
        zorder=3,
    )
    ax.plot(
        g,
        rho_3,
        color=COLORS["constraints"],
        linewidth=2.2,
        label=f"Implementation screen (μ3 = {capacity[2]:.0f}/day)",
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

    # Highlight the illustrative operating point (g = 32 candidates/day)
    ax.scatter(
        [g_op],
        [rho3_op],
        color=COLORS["constraints"],
        edgecolor="white",
        s=55,
        linewidth=1.0,
        zorder=5,
    )
    ax.annotate(
        f"Illustrative operating point\n(g = {g_op:.0f} proposals/day, ρ3 = {rho3_op:.0%})",
        xy=(g_op, rho3_op),
        xytext=(22.0, 0.28),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS["ink"],
            lw=0.8,
            connectionstyle="arc3,rad=-0.12",
        ),
        fontsize=9.9,
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
        g_max,
        color=COLORS["constraints_ink"],
        linestyle="--",
        linewidth=1.0,
        zorder=2,
    )
    ax.annotate(
        f"Full-utilization boundary\ng_max = {g_max:.0f} proposals/day",
        xy=(g_max, 1.0),
        xytext=(26.5, 1.15),
        arrowprops=dict(arrowstyle="->", color=COLORS["constraints_ink"], lw=0.9),
        fontsize=9.9,
        fontweight="bold",
        color=COLORS["constraints_ink"],
        bbox=dict(facecolor="white", edgecolor="none", pad=1.5),
    )

    ax.set_xlabel(
        "Proposal rate g (proposals/day)",
        fontsize=10.4,
        color=COLORS["ink"],
    )
    ax.set_ylabel(
        "Stage utilization ρi = λi / μi",
        fontsize=10.4,
        color=COLORS["ink"],
    )

    ax.set_xlim(0, 50)
    ax.set_ylim(0, 1.28)

    # Percentage tick labels on y-axis
    yticks = [0.0, 0.25, 0.50, 0.75, 1.0, 1.25]
    ytick_labels = ["0%", "25%", "50%", "75%", "100%", "125%"]
    ax.set_yticks(yticks)
    ax.set_yticklabels(ytick_labels, fontsize=9.3)
    ax.tick_params(axis="x", labelsize=9.3)

    ax.legend(
        frameon=False,
        fontsize=8.5,
        loc="lower left",
        bbox_to_anchor=(0.0, 1.02),
        ncol=2,
    )
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
