"""
Empirical Verification Defect Discovery & Testbench Vacuity Plot Script (Chapter 7)
-----------------------------------------------------------------------------------
Substantiates Chapter 7's core thesis on:
1. Checker Diversity & Modality Breakdown (OpenHW Group CV32E40P TRL-5 Signoff Audit)
2. Testbench Vacuity & The Coverage Illusion (ASPDAC 2021 / OpenHW Group Telemetry)

Primary Datasets:
- data/source-receipts/chapter7-defect-discovery-modalities.csv
- data/source-receipts/chapter7-testbench-vacuity-mutation.csv
- data/source-receipts/chapter7-subsystem-defect-breakdown.csv
"""

import csv
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

# Ensure book._python.plots is accessible
REPO_ROOT = Path("/Users/VJ/GitHub/Arch2")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style

apply_style()


def main():
    csv_modalities = (
        REPO_ROOT
        / "data"
        / "source-receipts"
        / "chapter7-defect-discovery-modalities.csv"
    )
    csv_vacuity = (
        REPO_ROOT
        / "data"
        / "source-receipts"
        / "chapter7-testbench-vacuity-mutation.csv"
    )

    out_ch_dir = REPO_ROOT / "book" / "contents" / "chapters" / "07-feedback" / "images"
    out_ch_dir.mkdir(parents=True, exist_ok=True)
    out_svg = out_ch_dir / "fig-ch07-defect-discovery-modalities.svg"
    out_pdf = out_ch_dir / "fig-ch07-defect-discovery-modalities.pdf"
    out_png = out_ch_dir / "fig-ch07-defect-discovery-modalities.png"

    scratch_png = Path(
        "/Users/VJ/.gemini/antigravity-cli/brain/3d006a40-dbce-4cfa-a3ef-6720bbd8c472/scratch/fig-ch07-defect-discovery-modalities.png"
    )

    # Load Modality Data
    modalities = []
    mod_counts = []
    mod_pcts = []
    with open(csv_modalities, "r", encoding="utf-8") as f:
        reader = csv.DictReader(row for row in f if not row.startswith("#"))
        for row in reader:
            modalities.append(row["modality"])
            mod_counts.append(int(row["bugs_discovered"]))
            mod_pcts.append(float(row["percentage"]))

    # Load Vacuity Data
    tiers = []
    line_cov = []
    branch_cov = []
    mutation_score = []
    assertion_cov = []
    with open(csv_vacuity, "r", encoding="utf-8") as f:
        reader = csv.DictReader(row for row in f if not row.startswith("#"))
        for row in reader:
            tier_name = row["verification_tier"].split(":")[1].strip()
            if "Directed Sanity" in tier_name:
                tier_name = "Directed\nSanity Tests"
            elif "Constrained-Random" in tier_name:
                tier_name = "Constrained\nRandom (UVM)"
            elif "Architectural Compliance" in tier_name:
                tier_name = "Architectural\nCompliance (CT)"
            elif "Formally-Guided" in tier_name:
                tier_name = "Formally-Guided\nSymbolic + SVA"
            tiers.append(tier_name)
            line_cov.append(float(row["line_coverage_pct"]))
            branch_cov.append(float(row["branch_coverage_pct"]))
            mutation_score.append(float(row["mutation_score_pct"]))
            assertion_cov.append(float(row["sva_assertion_coverage_pct"]))

    # Create 2-Panel Figure
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(8.0, 3.4), gridspec_kw={"width_ratios": [1.18, 1.12]}
    )
    fig.subplots_adjust(wspace=0.48, left=0.08, right=0.94, top=0.86, bottom=0.18)

    # -------------------------------------------------------------
    # Panel A: Defect Discovery by Verification Modality
    # -------------------------------------------------------------
    y_pos = np.arange(len(modalities))
    bar_colors = [
        COLORS["green"],  # Formal SVA
        COLORS["purple"],  # Human Review
        COLORS["blue"],  # Directed Sim
        COLORS["orange"],  # Golden ISS
        COLORS["red"],  # Constrained Random
        COLORS["muted"],  # Static Linting
    ]

    bars = ax1.barh(
        y_pos, mod_pcts, color=bar_colors, alpha=0.88, height=0.54, zorder=3
    )
    ax1.set_yticks(y_pos)
    display_modalities = [
        "Formal SVA Model Checking",
        "Human Inspection & Peer Review",
        "Directed Testbench Simulation",
        "Golden ISS Step-and-Compare",
        "Constrained-Random UVM Sim",
        "Static Linting & Rule Checks",
    ]
    ax1.set_yticklabels(display_modalities, fontsize=5.6, color=COLORS["ink"])
    ax1.invert_yaxis()  # Top-down order
    ax1.set_xlim(0, 36)
    ax1.set_xlabel("RTL Defects Discovered (%, N=47 Total Issues)", fontsize=6.5)
    ax1.set_title(
        "A. Defect Discovery by Modality (OpenHW CV32E40P Audit)",
        fontsize=7.2,
        fontweight="bold",
        pad=8,
    )
    ax1.grid(True, color=COLORS["grid"], linewidth=0.5, zorder=0)

    # Bar Value Labels
    for bar, count, pct in zip(bars, mod_counts, mod_pcts):
        ax1.text(
            pct + 0.7,
            bar.get_y() + bar.get_height() / 2,
            f"{count} ({pct:.1f}%)",
            va="center",
            ha="left",
            fontsize=5.2,
            fontweight="bold",
            color=COLORS["ink"],
        )

    # Callout Box in Open Whitespace (Lower Right)
    ax1.text(
        19.5,
        4.4,
        "Checker Diversity Gap:\n• Non-Simulation: 59.6%\n  (Formal + Review: 55.3%)\n• Random UVM: only 4.3%",
        ha="left",
        va="center",
        fontsize=4.7,
        fontweight="bold",
        color=COLORS["ink"],
        linespacing=1.2,
        bbox=dict(
            boxstyle="round,pad=0.3",
            facecolor=COLORS["note_fill"],
            edgecolor=COLORS["note_edge"],
            alpha=0.95,
            lw=0.7,
        ),
        zorder=5,
    )

    # -------------------------------------------------------------
    # Panel B: The Testbench Vacuity Paradox: Code Coverage vs. Mutation Kill Rate
    # -------------------------------------------------------------
    x = np.arange(len(tiers))
    width = 0.28

    rects1 = ax2.bar(
        x - width / 2,
        line_cov,
        width,
        label="Line Coverage (%)",
        color=COLORS["blue"],
        alpha=0.82,
        zorder=3,
    )
    rects2 = ax2.bar(
        x + width / 2,
        branch_cov,
        width,
        label="Branch Coverage (%)",
        color=COLORS["orange"],
        alpha=0.82,
        zorder=3,
    )

    line_mut = ax2.plot(
        x,
        mutation_score,
        marker="s",
        color=COLORS["red"],
        linewidth=1.8,
        markersize=4.2,
        label="Mutation Kill Rate (Fault Detection %)",
        zorder=5,
    )
    line_sva = ax2.plot(
        x,
        assertion_cov,
        marker="o",
        color=COLORS["green"],
        linewidth=1.6,
        linestyle="--",
        markersize=3.8,
        label="SVA Assertion Coverage (%)",
        zorder=5,
    )

    ax2.set_ylim(0, 118)
    ax2.set_xticks(x)
    ax2.set_xticklabels(tiers, fontsize=5.3, color=COLORS["ink"])
    ax2.set_ylabel("Verification Metric Score (%)", fontsize=6.5)
    ax2.set_title(
        "B. The Testbench Vacuity Paradox (Coverage vs. Mutation Score)",
        fontsize=7.2,
        fontweight="bold",
        pad=8,
    )
    ax2.grid(True, color=COLORS["grid"], linewidth=0.5, zorder=0)

    # Annotate Vacuity Gap at Tier 2 (UVM) cleanly
    ax2.annotate(
        "Vacuity Gap: 98.6% Line Cov\nbut 41.4% Mutants Escape",
        xy=(1, 58.6),
        xytext=(0.15, 78.0),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS["red"],
            lw=0.8,
            connectionstyle="arc3,rad=-0.15",
        ),
        fontsize=4.6,
        fontweight="bold",
        color=COLORS["red"],
        bbox=dict(
            boxstyle="round,pad=0.22",
            facecolor="white",
            edgecolor=COLORS["red"],
            alpha=0.92,
            lw=0.6,
        ),
        zorder=6,
    )

    # Annotate 100% Invariant Discharge at Tier 4
    ax2.annotate(
        "100% Kill Rate\n(Exhaustive SVA)",
        xy=(3, 100.0),
        xytext=(2.3, 38.0),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS["green"],
            lw=0.8,
            connectionstyle="arc3,rad=0.15",
        ),
        fontsize=4.6,
        fontweight="bold",
        color=COLORS["green"],
        bbox=dict(
            boxstyle="round,pad=0.22",
            facecolor="white",
            edgecolor=COLORS["green"],
            alpha=0.92,
            lw=0.6,
        ),
        zorder=6,
    )

    ax2.legend(
        loc="lower right",
        fontsize=4.3,
        framealpha=0.92,
        facecolor="white",
        edgecolor=COLORS["grid"],
        borderpad=0.25,
    )

    plt.savefig(out_svg, format="svg", bbox_inches="tight")
    plt.savefig(out_pdf, format="pdf", bbox_inches="tight")
    plt.savefig(out_png, format="png", dpi=300, bbox_inches="tight")
    plt.savefig(scratch_png, format="png", dpi=300, bbox_inches="tight")
    plt.close()

    print(
        f"Figure successfully updated:\n  {out_svg}\n  {out_pdf}\n  {out_png}\n  {scratch_png}"
    )


if __name__ == "__main__":
    main()
