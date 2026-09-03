"""
DSE Search Efficiency & Convergence Curve Plot Script

Literature Calibration & Citation Provenance:
---------------------------------------------
1. Agentic LLM Zero-Shot Priors (+12.8% at N=5): AgentDSE (Wang et al., 2026) [@WangEtAl2026AgentDSE].
2. Bayesian Optimization (BoTorch): AutoDSE (Zhang et al., 2022) [@ZhangEtAl2022AutoDSE].
3. Reinforcement Learning (PPO): Graph Placement (Mirhoseini et al., 2021) [@MirhoseiniEtAl2021GraphPlacement].
4. Reward-Hacking Defense: PPA gains awarded strictly to candidates passing Stage 3 functional verification.

Dataset Receipt: data/source-receipts/chapter5-dse-convergence.csv
Output Figure:   book/images/fig-dse-convergence-pareto.svg
"""

import csv
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

# Connect parent repo path to import book._python.plots
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style

apply_style()


def main():
    csv_file = REPO_ROOT / "data" / "source-receipts" / "chapter5-dse-convergence.csv"
    out_plot = REPO_ROOT / "book" / "images" / "fig-dse-convergence-pareto.svg"

    budget = []
    random_ppa = []
    rl_ppa = []
    bo_ppa = []
    llm_ppa = []

    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(l for l in f if not l.startswith("#"))
        for row in reader:
            budget.append(int(row["EvaluationBudget"]))
            random_ppa.append(float(row["RandomSearch_PPA_Gain"]))
            rl_ppa.append(float(row["RL_PPA_Gain"]))
            bo_ppa.append(float(row["BayesianOpt_PPA_Gain"]))
            llm_ppa.append(float(row["AgenticLLM_PPA_Gain"]))

    fig, ax = plt.subplots(figsize=(6.4, 3.2))

    ax.plot(
        budget,
        llm_ppa,
        label="Agentic LLM (Reasoning-Augmented)",
        color=COLORS["purple"],
        linewidth=2.2,
        marker="o",
        markersize=4,
        zorder=5,
    )
    ax.plot(
        budget,
        bo_ppa,
        label="Bayesian Optimization (BoTorch)",
        color=COLORS["blue"],
        linewidth=1.8,
        marker="s",
        markersize=3.5,
        zorder=4,
    )
    ax.plot(
        budget,
        rl_ppa,
        label="Reinforcement Learning (PPO)",
        color=COLORS["green"],
        linewidth=1.6,
        marker="^",
        markersize=3.5,
        zorder=3,
    )
    ax.plot(
        budget,
        random_ppa,
        label="Random Search (Baseline)",
        color="#7A8B99",
        linestyle="--",
        linewidth=1.4,
        marker="x",
        markersize=3.5,
        zorder=2,
    )

    # Position annotation in open white space ABOVE the curves (x=1.8, y=20.5) -> pointing down to (5, 12.8)
    ax.annotate(
        "Zero-Shot Architectural Prior\n(+12.8% Gain at N=5)",
        (5, 12.8),
        xytext=(1.8, 20.5),
        arrowprops=dict(
            facecolor=COLORS["purple"],
            edgecolor=COLORS["purple"],
            shrink=0.08,
            width=1.0,
            headwidth=4.5,
        ),
        fontsize=6.0,
        fontweight="bold",
        color=COLORS["purple"],
        zorder=6,
    )

    # Reward Hacking Defense note in top-left box
    ax.text(
        1.25,
        32.2,
        "Note: PPA Gain reflects ONLY functionally verified, non-reward-hacked candidates.",
        fontsize=5.6,
        fontstyle="italic",
        fontweight="bold",
        color=COLORS["red"],
        bbox=dict(
            boxstyle="round,pad=0.3",
            facecolor="#FFF5F5",
            edgecolor=COLORS["red"],
            linewidth=0.6,
        ),
        zorder=6,
    )

    ax.set_xscale("log")
    ax.set_xlim(1, 1000)
    ax.set_ylim(0, 36)
    ax.set_xlabel(
        "EDA Tool Evaluation Budget N (Log Scale - Simulators & Signoff Runs)",
        fontsize=7.0,
        color=COLORS["ink"],
    )
    ax.set_ylabel(
        "Verified Functional PPA Improvement Over Baseline (%)",
        fontsize=7.0,
        color=COLORS["ink"],
    )
    ax.grid(True, which="both", color=COLORS["grid"], linewidth=0.5, zorder=0)

    ax.legend(
        loc="lower right",
        fontsize=6.0,
        framealpha=0.95,
        facecolor="white",
        edgecolor=COLORS["grid"],
    )

    plt.tight_layout()
    plt.savefig(out_plot, dpi=300, bbox_inches="tight")
    print(f"Pristine DSE Search Efficiency plot saved to '{out_plot}'")


if __name__ == "__main__":
    main()
