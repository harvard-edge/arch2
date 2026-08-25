"""
Wilson Research Group Functional Verification Scissors Gap Plot (2002-2024)
---------------------------------------------------------------------------
Visualizes 22 years of longitudinal empirical data from Harry Foster / Wilson Research / Siemens EDA:
Panel A: Verification Schedule & Staffing Divergence vs. First-Pass Silicon Success Collapse (2002-2024).
Panel B: Silicon Respin Flaw Distribution & Logic Defect Root Causes.
"""

import csv
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

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
        / "chapter7-wilson-verification-scissors-gap.csv"
    )
    out_svg = (
        REPO_ROOT
        / "book"
        / "contents"
        / "chapters"
        / "07-feedback"
        / "images"
        / "fig-ch07-wilson-verification-scissors.svg"
    )
    out_pdf = (
        REPO_ROOT
        / "book"
        / "contents"
        / "chapters"
        / "07-feedback"
        / "images"
        / "fig-ch07-wilson-verification-scissors.pdf"
    )
    out_png = (
        REPO_ROOT
        / "book"
        / "contents"
        / "chapters"
        / "07-feedback"
        / "images"
        / "fig-ch07-wilson-verification-scissors.png"
    )
    out_svg.parent.mkdir(parents=True, exist_ok=True)

    years = []
    verif_time = []
    first_silicon = []
    staff_ratio_years = []
    staff_ratio = []

    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader((row for row in f if not row.startswith("#")))
        for row in reader:
            y = float(row["study_year"])
            years.append(y)
            verif_time.append(float(row["avg_pct_project_time_in_verification"]))
            first_silicon.append(float(row["first_silicon_success_pct"]))
            if row["staffing_ratio_verif_to_design"] != "N/A":
                staff_ratio_years.append(y)
                staff_ratio.append(float(row["staffing_ratio_verif_to_design"]))

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(7.8, 3.6), gridspec_kw={"width_ratios": [1.12, 1.08]}
    )
    fig.subplots_adjust(wspace=0.58, left=0.08, right=0.94, top=0.88, bottom=0.18)

    # -------------------------------------------------------------
    # Panel A: 22-Year Verification Resource Trends vs. First Silicon Success
    # -------------------------------------------------------------
    ax1.plot(
        years,
        verif_time,
        marker="o",
        color=COLORS["purple"],
        linewidth=1.8,
        markersize=4.0,
        label="% Project Time in Verification (~58%)",
        zorder=3,
    )
    ax1.plot(
        years,
        first_silicon,
        marker="s",
        color=COLORS["red"],
        linewidth=1.8,
        markersize=4.0,
        label="First-Pass Silicon Success (Plunged to 14%)",
        zorder=4,
    )

    # Secondary axis for Staffing Ratio with proper padding
    ax1_sub = ax1.twinx()
    ax1_sub.plot(
        staff_ratio_years,
        staff_ratio,
        marker="^",
        color=COLORS["blue"],
        linewidth=1.5,
        linestyle="--",
        markersize=4.0,
        label="Verif-to-Design Staffing Ratio",
        zorder=2,
    )
    ax1_sub.set_ylim(0.4, 1.6)
    ax1_sub.set_ylabel("Staffing Ratio", fontsize=5.8, color=COLORS["blue"], labelpad=2)
    ax1_sub.tick_params(axis="y", colors=COLORS["blue"], labelsize=5.6, pad=2)

    ax1.set_xlim(2001, 2025)
    ax1.set_ylim(8, 85)
    ax1.set_xlabel("Study Year (Wilson Research / Siemens EDA Biennial)", fontsize=6.6)
    ax1.set_ylabel("Share of Projects / Schedule (%)", fontsize=6.6)
    ax1.set_title(
        "A. 22-Year Verification Scissors Divergence",
        fontsize=7.6,
        fontweight="bold",
        pad=8,
    )
    ax1.grid(True, color=COLORS["grid"], linewidth=0.5, zorder=0)

    # Annotate key milestones with clean boxes
    ax1.annotate(
        "2024 All-Time Low: 14%\n(86% require respin)",
        xy=(2024, 14),
        xytext=(2014.5, 18),
        arrowprops=dict(arrowstyle="->", color=COLORS["red"], lw=0.8),
        fontsize=4.8,
        fontweight="bold",
        color=COLORS["red"],
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="white",
            edgecolor=COLORS["red"],
            alpha=0.9,
            lw=0.6,
        ),
        zorder=5,
    )
    ax1.annotate(
        "58% Project Time\nin Verification",
        xy=(2024, 58),
        xytext=(2014.0, 68),
        arrowprops=dict(arrowstyle="->", color=COLORS["purple"], lw=0.8),
        fontsize=4.8,
        fontweight="bold",
        color=COLORS["purple"],
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="white",
            edgecolor=COLORS["purple"],
            alpha=0.9,
            lw=0.6,
        ),
        zorder=5,
    )

    # Unified Legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax1_sub.get_legend_handles_labels()
    ax1.legend(
        lines1 + lines2,
        labels1 + labels2,
        loc="upper left",
        fontsize=4.6,
        frameon=True,
        facecolor="white",
        edgecolor="none",
        borderpad=0.25,
    )

    # -------------------------------------------------------------
    # Panel B: Flaws Contributing to Silicon Respins (2024 Data)
    # -------------------------------------------------------------
    categories = [
        "Logic or Functional Flaws",
        "Analog / Mixed-Signal Tuning",
        "Clocking / CDC Flaws",
        "Static Timing Defects (Setup)",
        "Firmware / HW-SW Interaction",
        "Power Consumption / IR Drop",
    ]
    pcts = [48.0, 43.0, 29.0, 23.0, 21.0, 19.0]
    cat_colors = [
        COLORS["red"],
        COLORS["orange"],
        COLORS["blue"],
        COLORS["green"],
        COLORS["purple"],
        COLORS["muted"],
    ]

    y_cat = np.arange(len(categories))
    bars = ax2.barh(y_cat, pcts, color=cat_colors, alpha=0.88, height=0.58, zorder=3)
    ax2.set_yticks(y_cat)
    ax2.set_yticklabels(categories, fontsize=5.4, color=COLORS["ink"])
    ax2.tick_params(axis="y", pad=3)
    ax2.invert_yaxis()  # Highest on top
    ax2.set_xlim(0, 60)
    ax2.set_xlabel(
        "Projects Reporting Defect Cause (%, Multiple Allowed)", fontsize=6.6
    )
    ax2.set_title(
        "B. Primary Root Causes of Silicon Respins (2024)",
        fontsize=7.6,
        fontweight="bold",
        pad=8,
    )
    ax2.grid(True, color=COLORS["grid"], linewidth=0.5, zorder=0)

    for bar, val in zip(bars, pcts):
        ax2.text(
            val + 1.2,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.0f}%",
            va="center",
            ha="left",
            fontsize=5.4,
            fontweight="bold",
            color=COLORS["ink"],
        )

    plt.savefig(out_svg, format="svg", bbox_inches="tight")
    plt.savefig(out_pdf, format="pdf", bbox_inches="tight")
    plt.savefig(out_png, format="png", dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Generated Wilson Verification Scissors plot -> {out_svg} and {out_pdf}")


if __name__ == "__main__":
    main()
