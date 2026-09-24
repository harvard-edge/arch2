"""
Empirical Cost-Quality Frontier: Systolic Array DSE Pareto Frontier (Chapter 10)
--------------------------------------------------------------------------------
Plots the empirical trade-off between total silicon area cost and Figure-of-Merit (FOM)
across 4,000 cycle-level SCALE-Sim architectural explorations (2,930 unique configurations,
2,921 dominated designs, and 9 non-dominated Pareto optimal configurations).

Exports SVG, PDF, and 300 DPI PNG to:
- book/contents/chapters/10-evaluation/images/fig-cost-quality-frontier.{png,svg,pdf}
- book/images/fig-cost-quality-frontier.{png,svg,pdf}
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style, save_figure_bundle

apply_style()


def main():
    ch_dir = REPO_ROOT / "book" / "contents" / "chapters" / "10-evaluation" / "images"
    ch_dir.mkdir(parents=True, exist_ok=True)
    out_ch = ch_dir / "fig-cost-quality-frontier"
    out_global = REPO_ROOT / "book" / "images" / "fig-cost-quality-frontier"

    data_path = (
        REPO_ROOT / "data" / "datasets" / "chapter5-dse-empirical-convergence.csv"
    )
    df = pd.read_csv(data_path, comment="#")
    unique_pts = (
        df[["total_area", "fom_score"]].drop_duplicates().sort_values("total_area")
    )

    pareto_pts = []
    cur_max = -1
    for _, row in unique_pts.iterrows():
        if row["fom_score"] > cur_max:
            pareto_pts.append(row)
            cur_max = row["fom_score"]

    pareto_df = pd.DataFrame(pareto_pts)

    fig, ax = plt.subplots(figsize=(6.2, 3.5))
    fig.subplots_adjust(left=0.14, right=0.95, top=0.90, bottom=0.18)

    # Dominated points
    ax.scatter(
        unique_pts["total_area"],
        unique_pts["fom_score"],
        color=COLORS["muted"],
        alpha=0.25,
        s=12,
        label="Dominated designs (2,921 configs)",
        zorder=2,
    )

    # Pareto frontier
    ax.step(
        pareto_df["total_area"],
        pareto_df["fom_score"],
        where="post",
        color=COLORS["blue"],
        linewidth=1.8,
        label="Empirical Pareto frontier",
        zorder=3,
    )
    ax.scatter(
        pareto_df["total_area"],
        pareto_df["fom_score"],
        color=COLORS["blue"],
        s=38,
        zorder=4,
        edgecolor="white",
        linewidth=0.8,
    )

    # Threshold line
    threshold = 650
    ax.axhline(
        threshold,
        color=COLORS["red"],
        linestyle="--",
        linewidth=1.2,
        label=f"Quality target (FOM = {threshold})",
        zorder=1,
    )

    # Annotate minimum cost candidate meeting threshold
    min_meet = pareto_df[pareto_df["fom_score"] >= threshold].iloc[0]
    ax.plot(
        min_meet["total_area"],
        min_meet["fom_score"],
        marker="o",
        markersize=8,
        color=COLORS["green"],
        zorder=5,
    )
    ax.annotate(
        "Optimal admission candidate\n(Area = 83.2 mm², FOM = 694.4)",
        xy=(min_meet["total_area"], min_meet["fom_score"]),
        xytext=(min_meet["total_area"] + 80, min_meet["fom_score"] - 120),
        arrowprops=dict(arrowstyle="->", color=COLORS["ink"], lw=1.0),
        fontsize=6.5,
        fontweight="bold",
        color=COLORS["ink"],
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor="white",
            edgecolor=COLORS["green"],
            lw=0.8,
        ),
    )

    ax.set_xlabel(
        r"Total Silicon Area Cost ($\mathrm{mm^2}$, total_area)", fontsize=7.2
    )
    ax.set_ylabel("Architectural Figure-of-Merit (FOM Score)", fontsize=7.2)
    ax.set_xlim(0, 1000)
    ax.set_ylim(0, 800)
    ax.legend(
        frameon=True,
        facecolor="white",
        edgecolor=COLORS["grid"],
        fontsize=6.2,
        loc="lower right",
    )
    ax.grid(True, color=COLORS["grid"], linewidth=0.5, zorder=0)

    save_figure_bundle(fig, out_ch)
    save_figure_bundle(fig, out_global)
    plt.close(fig)
    print(f"Generated clean cost-quality frontier figure: {out_ch}")


if __name__ == "__main__":
    main()
