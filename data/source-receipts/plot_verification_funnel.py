"""
Physical Signoff Verification Funnel Plot Script

Literature Calibration & Citation Provenance:
---------------------------------------------
1. Stage 1 (Syntactic & AST Parsing - 72.4% pass): VerilogEval (Liu et al., 2023) [@LiuEtAl2023VerilogEval].
2. Stage 2 (Interface & Interconnect Schema - 38.1% pass): RTLLM (Lu et al., 2024) [@LuEtAl2024RTLLM].
3. Stage 3 (Functional Simulation & SVA Assertions - 14.6% pass): OpenRTLSet (Wang et al., 2025) [@WangEtAl2025OpenRTLSet].
4. Stage 4 (Static Timing Closure WNS >= 0ns - 3.8% pass): AgentDSE (Wang et al., 2026) [@WangEtAl2026AgentDSE].
5. Stage 5 (Physical Place & Route DRC Closure - 59.5% pass / 0.09% yield): AutoDSE (Zhang et al., 2022) [@ZhangEtAl2022AutoDSE] on OpenROAD 7nm ASAP7.

Dataset Receipt: data/source-receipts/chapter4-physical-verification-funnel.csv
Output Figure:   book/images/fig-synthesis-verification-funnel.svg
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
    csv_file = (
        REPO_ROOT
        / "data"
        / "source-receipts"
        / "chapter4-physical-verification-funnel.csv"
    )
    out_plot = REPO_ROOT / "book" / "images" / "fig-synthesis-verification-funnel.svg"

    stages = []
    candidates = []
    stage_pass_rates = []
    cumulative_yield = []

    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stages.append(f"Stage {row['Gate']}:\n{row['Stage'].split(' (')[0]}")
            candidates.append(int(row["PassingCandidates"]))
            stage_pass_rates.append(float(row["PassRatePercentage"]))
            cumulative_yield.append(float(row["CumulativeYieldPercentage"]))

    all_stages = ["Initial\nProposals"] + [f"Stage {i+1}" for i in range(5)]
    all_counts = [100000] + candidates
    all_yield = [100.0] + cumulative_yield

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(7.0, 3.2), gridspec_kw={"width_ratios": [1.25, 1.0]}
    )
    fig.subplots_adjust(wspace=0.42)

    # --- Panel A: Candidate Attrition (Log Scale Bar Chart + Yield Line) ---
    x = np.arange(len(all_stages))
    colors_bars = [
        COLORS["ink"],
        COLORS["blue"],
        COLORS["green"],
        COLORS["orange"],
        COLORS["purple"],
        COLORS["red"],
    ]

    bars = ax1.bar(x, all_counts, color=colors_bars, alpha=0.85, width=0.52, zorder=3)
    ax1.set_yscale("log")
    ax1.set_ylim(1, 400000)
    ax1.set_xticks(x)
    ax1.set_xticklabels(all_stages, fontsize=5.8, color=COLORS["ink"])
    ax1.set_ylabel(
        "Passing Candidate Count (Log Scale)", fontsize=6.8, color=COLORS["ink"]
    )
    ax1.grid(True, which="both", color=COLORS["grid"], linewidth=0.5, zorder=0)

    # Secondary Axis for Cumulative Yield Line
    ax1_sub = ax1.twinx()
    ax1_sub.plot(
        x,
        all_yield,
        color=COLORS["red"],
        marker="o",
        linewidth=1.5,
        markersize=3.5,
        zorder=5,
    )
    ax1_sub.set_yscale("log")
    ax1_sub.set_ylim(0.01, 200)
    ax1_sub.set_ylabel(
        "Cumulative Yield (% Log Scale)", fontsize=6.5, color=COLORS["red"], labelpad=8
    )
    ax1_sub.tick_params(axis="y", colors=COLORS["red"], labelsize=5.8)

    # Annotate counts on top of bars
    for bar, count in zip(bars, all_counts):
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            count * 1.45,
            f"{count:,}",
            ha="center",
            va="bottom",
            fontsize=5.0,
            fontweight="bold",
            color=COLORS["ink"],
        )

    # --- Panel B: Stage-Specific Conditional Pass Rates ---
    x_stages = np.arange(len(stages))
    bars2 = ax2.bar(
        x_stages,
        stage_pass_rates,
        color=colors_bars[1:],
        alpha=0.85,
        width=0.52,
        zorder=3,
    )

    ax2.set_ylim(0, 105)
    ax2.set_xticks(x_stages)
    ax2.set_xticklabels(
        [f"Stage {i+1}" for i in range(5)], fontsize=5.8, color=COLORS["ink"]
    )
    ax2.set_ylabel("Conditional Stage Pass Rate (%)", fontsize=6.8, color=COLORS["ink"])
    ax2.grid(True, color=COLORS["grid"], linewidth=0.5, zorder=0)

    for bar, rate in zip(bars2, stage_pass_rates):
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            rate + 2.5,
            f"{rate:.1f}%",
            ha="center",
            va="bottom",
            fontsize=5.5,
            fontweight="bold",
            color=COLORS["ink"],
        )

    plt.savefig(out_plot, dpi=300, bbox_inches="tight")
    print(f"Pristine Verification Funnel plot saved to '{out_plot}'")


if __name__ == "__main__":
    main()
