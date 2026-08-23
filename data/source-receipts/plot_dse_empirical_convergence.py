#!/usr/bin/env python3
"""
Plot Empirical DSE Optimizer Convergence for Chapter 5 (Methods)
---------------------------------------------------------------
Generates high-resolution publication figures comparing matched-budget
architectural optimization strategies (GP-BO, GA, SA, RS)
on genuine SCALE-Sim hardware simulations (4,000 evaluations across 10 seeds).

Applies Arch2 typography, palette, and formatting guidelines.
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# Add book directory to import house style helper
repo_root = Path("/Users/VJ/GitHub/Arch2")
sys.path.insert(0, str(repo_root / "book"))
from _python.plots import COLORS, apply_style, add_note_box


def load_data(csv_path):
    records = defaultdict(lambda: defaultdict(list))
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            alg = row["algorithm"]
            step = int(row["evaluation_step"])
            gain = float(row["best_so_far_gain_pct"])
            records[alg][step].append(gain)
    return records


def main():
    csv_path = (
        repo_root
        / "data"
        / "source-receipts"
        / "chapter5-dse-empirical-convergence.csv"
    )
    if not csv_path.exists():
        print(f"Error: CSV not found at {csv_path}")
        sys.exit(1)

    records = load_data(csv_path)
    steps = sorted(list(next(iter(records.values())).keys()))

    apply_style()
    fig, ax = plt.subplots(figsize=(10.5, 6.0), dpi=300)

    # Styling mapping
    styles = {
        "Bayesian Optimization (GP-BO)": {
            "color": COLORS["blue"],
            "linestyle": "-",
            "linewidth": 2.8,
            "label": "Bayesian Optimization (GP-BO, Matérn 5/2)",
            "zorder": 5,
            "fill_alpha": 0.18,
        },
        "Simulated Annealing": {
            "color": COLORS.get("green", "#2CA02C"),
            "linestyle": "-.",
            "linewidth": 2.4,
            "label": "Simulated Annealing (Geometric Decay)",
            "zorder": 4,
            "fill_alpha": 0.12,
        },
        "Genetic Algorithm": {
            "color": COLORS["purple"],
            "linestyle": "--",
            "linewidth": 2.4,
            "label": "Genetic Algorithm (Tournament k=3, Pop=12)",
            "zorder": 3,
            "fill_alpha": 0.14,
        },
        "Random Search": {
            "color": COLORS["muted"],
            "linestyle": ":",
            "linewidth": 2.2,
            "label": "Random Search (Uniform Sampling Baseline)",
            "zorder": 2,
            "fill_alpha": 0.10,
        },
    }

    # Plot each algorithm with mean and IQR shaded band
    for alg, cfg in styles.items():
        if alg not in records:
            continue
        means = []
        p25s = []
        p75s = []
        for s in steps:
            vals = records[alg][s]
            means.append(np.mean(vals))
            p25s.append(np.percentile(vals, 25))
            p75s.append(np.percentile(vals, 75))

        means = np.array(means)
        p25s = np.array(p25s)
        p75s = np.array(p75s)

        ax.plot(
            steps,
            means,
            color=cfg["color"],
            linestyle=cfg["linestyle"],
            linewidth=cfg["linewidth"],
            label=cfg["label"],
            zorder=cfg["zorder"],
        )
        ax.fill_between(
            steps,
            p25s,
            p75s,
            color=cfg["color"],
            alpha=cfg["fill_alpha"],
            zorder=cfg["zorder"] - 1,
        )

    # Axes limits and labels
    ax.set_xlim(1, 100)
    ax.set_ylim(-30, 260)
    ax.set_xlabel(
        "Simulation Budget (Evaluations $N$, Matched Compute Cost)",
        fontsize=11.5,
        fontweight="bold",
        labelpad=9,
    )
    ax.set_ylabel(
        "PPA Gain over Baseline Anchor (%)",
        fontsize=11.5,
        fontweight="bold",
        labelpad=9,
    )

    # Baseline reference line at 0%
    ax.axhline(
        0, color=COLORS["muted"], linestyle="-", linewidth=1.0, alpha=0.6, zorder=1
    )
    ax.text(
        3,
        4,
        "Baseline Anchor (16×16, 96kB SRAM, WS) = 0.0%",
        fontsize=8.5,
        color=COLORS["muted"],
        fontstyle="italic",
        zorder=2,
    )

    # Annotations / Callout Boxes
    # 1. Early GP-BO advantage
    ax.annotate(
        "GP-BO Sample Efficiency:\nSurges to +152% gain by N=20\n(Active surrogate uncertainty reduction)",
        xy=(20, 152),
        xytext=(6, 198),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS["blue"],
            lw=1.4,
            connectionstyle="arc3,rad=-0.15",
        ),
        fontsize=8.5,
        color=COLORS["blue"],
        fontweight="semibold",
        bbox=dict(
            boxstyle="round,pad=0.4", fc="white", ec=COLORS["blue"], lw=1.1, alpha=0.95
        ),
        zorder=7,
    )

    # 2. Heuristic exploration (SA)
    ax.annotate(
        "Heuristic Exploration:\nSA scales to +207% at N=100\nvia continuous perturbation",
        xy=(97, 207),
        xytext=(52, 222),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS.get("green", "#2CA02C"),
            lw=1.4,
            connectionstyle="arc3,rad=0.1",
        ),
        fontsize=8.5,
        color=COLORS.get("green", "#2CA02C"),
        fontweight="semibold",
        bbox=dict(
            boxstyle="round,pad=0.4",
            fc="white",
            ec=COLORS.get("green", "#2CA02C"),
            lw=1.1,
            alpha=0.95,
        ),
        zorder=7,
    )

    # 3. Random Search plateau
    ax.annotate(
        "Random Search Plateau:\nStalls at +118% due to\n161k sparse state space",
        xy=(75, 117),
        xytext=(52, 60),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS["muted"],
            lw=1.4,
            connectionstyle="arc3,rad=-0.1",
        ),
        fontsize=8.5,
        color=COLORS["muted"],
        fontweight="semibold",
        bbox=dict(
            boxstyle="round,pad=0.4", fc="white", ec=COLORS["muted"], lw=1.1, alpha=0.95
        ),
        zorder=7,
    )

    # Legend
    leg = ax.legend(
        loc="lower right",
        frameon=True,
        framealpha=0.95,
        edgecolor="#D0D7DE",
        fontsize=9.0,
        labelspacing=0.45,
        handlelength=2.2,
    )
    leg.get_frame().set_linewidth(0.8)

    # Clean grid
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.5, color="#D0D7DE")
    ax.set_axisbelow(True)

    plt.tight_layout()

    # Save outputs in chapters/05-methods/images/
    out_dir = repo_root / "book" / "contents" / "chapters" / "05-methods" / "images"
    out_dir.mkdir(parents=True, exist_ok=True)

    svg_path = out_dir / "fig-ch05-search-efficiency.svg"
    pdf_path = out_dir / "fig-ch05-search-efficiency.pdf"
    png_path = out_dir / "fig-ch05-search-efficiency.png"

    plt.savefig(svg_path, format="svg", bbox_inches="tight")
    plt.savefig(pdf_path, format="pdf", bbox_inches="tight")
    plt.savefig(png_path, format="png", dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Generated Polished Money Plots for Chapter 5:")
    print(f"  - SVG: {svg_path}")
    print(f"  - PDF: {pdf_path}")
    print(f"  - PNG: {png_path}")


if __name__ == "__main__":
    main()
