"""
Physical Signoff Verification Funnel Plot Script (Chapter 7)

Literature Calibration & Citation Provenance:
---------------------------------------------
1. Stage 1 (Syntactic & AST Parsing - 72.4% pass): VerilogEval (Liu et al., 2023) [@LiuEtAl2023VerilogEval].
2. Stage 2 (Interface & Interconnect Schema - 38.1% pass): RTLLM (Lu et al., 2024) [@LuEtAl2024RTLLM].
3. Stage 3 (Functional Simulation & SVA Assertions - 14.6% pass): OpenRTLSet (Wang et al., 2025) [@WangEtAl2025OpenRTLSet].
4. Stage 4 (Static Timing Closure WNS >= 0ns - 3.8% pass): AgentDSE (Wang et al., 2026) [@WangEtAl2026AgentDSE].
5. Stage 5 (Physical Place & Route DRC Closure - 59.5% pass / 0.09% yield): AutoDSE (Zhang et al., 2022) [@ZhangEtAl2022AutoDSE] on OpenROAD 7nm ASAP7.

Dataset Receipt: book/contents/chapters/07-feedback/data/fig-synthesis-verification-funnel.csv
Output Figure:   book/contents/chapters/07-feedback/images/fig-synthesis-verification-funnel.svg
"""

import csv
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

# Connect parent repo path to import book._python.plots
REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import (
    COLORS,
    apply_style,
    clean_spines,
    save_figure_bundle,
)

apply_style()


def main():
    chapter_dir = Path(__file__).resolve().parents[1]
    csv_file = chapter_dir / "data" / "fig-synthesis-verification-funnel.csv"
    out_plot_ch = chapter_dir / "images" / "fig-synthesis-verification-funnel"
    out_plot_global = (
        REPO_ROOT / "book" / "images" / "fig-synthesis-verification-funnel"
    )

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
    fig.subplots_adjust(wspace=0.42, bottom=0.18, top=0.90)

    # --- Panel A: Candidate Attrition (Log Scale Bar Chart + Yield Line) ---
    x = np.arange(len(all_stages))
    colors_bars = [
        COLORS["ink"],
        COLORS["workload"],
        COLORS["evidence"],
        COLORS["methods"],
        COLORS["designspace"],
        COLORS["constraints"],
    ]

    bars = ax1.bar(
        x,
        all_counts,
        bottom=1,
        color=colors_bars,
        edgecolor=COLORS["note_edge"],
        linewidth=0.6,
        width=0.52,
        zorder=3,
    )
    ax1.set_yscale("log")
    ax1.set_ylim(1, 400000)
    ax1.set_xticks(x)
    ax1.set_xticklabels(all_stages, fontsize=5.8, color=COLORS["ink"])
    ax1.set_ylabel(
        "Passing Candidate Count (Log Scale)", fontsize=6.8, color=COLORS["ink"]
    )
    ax1.grid(axis="y", color=COLORS["grid"], linewidth=0.5, zorder=0)
    clean_spines(ax1, keep=("bottom", "left"))

    # Secondary Axis for Cumulative Yield Line
    ax1_sub = ax1.twinx()
    ax1_sub.plot(
        x,
        all_yield,
        color=COLORS["constraints_ink"],
        marker="o",
        linewidth=1.5,
        markersize=3.5,
        zorder=5,
    )
    ax1_sub.set_yscale("log")
    ax1_sub.set_ylim(0.01, 200)
    ax1_sub.set_ylabel(
        "Cumulative Yield (% Log Scale)",
        fontsize=6.5,
        color=COLORS["constraints_ink"],
        labelpad=8,
    )
    ax1_sub.tick_params(axis="y", colors=COLORS["constraints_ink"], labelsize=5.8)
    clean_spines(ax1_sub, keep=("right",))

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
        edgecolor=COLORS["note_edge"],
        linewidth=0.6,
        width=0.52,
        zorder=3,
    )

    ax2.set_ylim(0, 105)
    ax2.set_xticks(x_stages)
    ax2.set_xticklabels(
        [f"Stage {i+1}" for i in range(5)], fontsize=5.8, color=COLORS["ink"]
    )
    ax2.set_ylabel("Conditional Stage Pass Rate (%)", fontsize=6.8, color=COLORS["ink"])
    ax2.grid(axis="y", color=COLORS["grid"], linewidth=0.5, zorder=0)
    clean_spines(ax2, keep=("bottom", "left"))

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

    save_figure_bundle(fig, out_plot_ch)
    save_figure_bundle(fig, out_plot_global)
    print(f"Verification Funnel plot saved to '{out_plot_ch}' and '{out_plot_global}'")


if __name__ == "__main__":
    main()
