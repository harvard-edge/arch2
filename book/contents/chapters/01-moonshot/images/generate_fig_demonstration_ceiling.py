#!/usr/bin/env python3
"""
Generate fig-demonstration-ceiling: The Demonstration Ceiling in Game AI and Silicon Architecture
------------------------------------------------------------------------------------------------
Panel A: Game AI Demonstration Ceiling in Go (AlphaGo Lee vs AlphaGo Zero; Nature 2017).
Panel B: Silicon Architecture Demonstration Ceiling in RTL (Layer 1 Imitation vs Layer 3 Closed-Loop).

Adheres strictly to .claude/rules/figures.md:
- Matplotlib script with apply_style() and canonical COLORS from book/_python/plots.py
- Two clean subplots with crisp panel titles (A and B)
- In-panel legends with generous whitespace and zero text clipping
- Exports SVG, PDF, and high-DPI PNG twins
"""

import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style

apply_style()


def main():
    img_dir = REPO_ROOT / "book" / "contents" / "chapters" / "01-moonshot" / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    out_svg = img_dir / "fig-demonstration-ceiling.svg"
    out_pdf = img_dir / "fig-demonstration-ceiling.pdf"
    out_png = img_dir / "fig-demonstration-ceiling.png"

    # Create 2-panel figure with balanced spacing and generous margins
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(7.5, 3.4), gridspec_kw={"width_ratios": [1.0, 1.0]}
    )
    fig.subplots_adjust(wspace=0.38, left=0.10, right=0.96, top=0.88, bottom=0.18)

    # -------------------------------------------------------------------------
    # Panel A: Game AI Demonstration Ceiling in Go
    # -------------------------------------------------------------------------
    ax1.set_title(
        "A. Game AI Demonstration Ceiling (Go)",
        fontsize=7.2,
        fontweight="bold",
        pad=8,
        color=COLORS["ink"],
    )

    x_go = np.linspace(0, 40, 300)

    # AlphaGo Lee / Fan: trained on 100k+ human games; plateaus at ~3500 Elo
    y_lee = 1800 + 1720 * (1.0 - np.exp(-x_go / 2.8)) - 110 * (x_go / 40.0)

    # AlphaGo Zero: pure tabula rasa self-play against game rules; crosses human level at 72h (3d)
    y_zero = 5150 - 4850 / (1.0 + (x_go / 2.22) ** 2.2)

    # Human grandmaster ceiling line
    ax1.axhline(
        3500,
        color=COLORS["red"],
        linestyle="--",
        linewidth=1.2,
        alpha=0.85,
        zorder=2,
    )
    ax1.text(
        21.0,
        3820,
        "Human Grandmaster Ceiling (~3,500 Elo)",
        fontsize=5.1,
        fontweight="bold",
        color=COLORS["constraints_ink"],
        bbox=dict(
            boxstyle="round,pad=0.22",
            facecolor="white",
            edgecolor=COLORS["red"],
            alpha=0.92,
            lw=0.55,
        ),
        zorder=5,
    )

    # Plot curves
    (l_lee,) = ax1.plot(
        x_go,
        y_lee,
        color=COLORS["red"],
        linewidth=1.9,
        label="AlphaGo Lee (100k+ human games; plateaued)",
        zorder=3,
    )
    (l_zero,) = ax1.plot(
        x_go,
        y_zero,
        color=COLORS["green"],
        linewidth=2.2,
        label="AlphaGo Zero (>5,000 Elo; tabula rasa self-play)",
        zorder=4,
    )

    # Point of inflection: 72 hours (3 days)
    idx_3d = np.argmin(np.abs(x_go - 3.0))
    x_cross = x_go[idx_3d]
    y_cross = y_zero[idx_3d]
    ax1.plot(
        x_cross, y_cross, marker="o", markersize=4.8, color=COLORS["green"], zorder=6
    )
    ax1.annotate(
        "Crosses human in 72h",
        xy=(x_cross, y_cross),
        xytext=(7.5, 4150),
        textcoords="data",
        fontsize=5.1,
        fontweight="bold",
        color=COLORS["evidence_ink"],
        bbox=dict(
            boxstyle="round,pad=0.22",
            facecolor="white",
            edgecolor=COLORS["green"],
            alpha=0.94,
            lw=0.55,
        ),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS["green"],
            lw=0.8,
            shrinkB=4,
        ),
        zorder=6,
    )

    # In-panel clean legend in lower right quadrant
    leg1 = ax1.legend(
        handles=[l_zero, l_lee],
        loc="lower right",
        bbox_to_anchor=(0.98, 0.20),
        fontsize=5.1,
        frameon=True,
        facecolor="white",
        edgecolor=COLORS["grid"],
        framealpha=0.94,
    )
    leg1.set_zorder(5)

    ax1.set_xlim(-0.5, 41)
    ax1.set_ylim(0, 5600)
    ax1.set_xticks([0, 3, 10, 20, 30, 40])
    ax1.set_xticklabels(["0", "3d", "10d", "20d", "30d", "40d"], fontsize=5.8)
    ax1.set_yticks([0, 1000, 2000, 3000, 4000, 5000])
    ax1.set_yticklabels(
        ["0", "1,000", "2,000", "3,000", "4,000", "5,000"], fontsize=5.8
    )
    ax1.set_xlabel("Training Duration (Days)", fontsize=6.6)
    ax1.set_ylabel("Elo Rating", fontsize=6.6)
    ax1.grid(True, color=COLORS["grid"], linewidth=0.55, zorder=0)

    # Oracle property card badge at bottom
    ax1.text(
        1.5,
        350,
        "Evaluation Oracle: Exact, deterministic board rules [O(1) cost]",
        fontsize=4.6,
        fontstyle="italic",
        color=COLORS["muted"],
        bbox=dict(
            boxstyle="round,pad=0.22",
            facecolor="#F6F8FA",
            edgecolor=COLORS["grid"],
            alpha=0.92,
            lw=0.5,
        ),
        zorder=5,
    )

    # -------------------------------------------------------------------------
    # Panel B: Silicon Architecture Demonstration Ceiling in RTL
    # -------------------------------------------------------------------------
    ax2.set_title(
        "B. Silicon Architecture Demonstration Ceiling (RTL)",
        fontsize=7.2,
        fontweight="bold",
        pad=8,
        color=COLORS["ink"],
    )

    x_rtl = np.linspace(0, 100, 300)

    # Layer 1: Point Assistance / Imitation: trained on human RTL corpora
    y_l1 = 20.0 + 46.0 * (1.0 - np.exp(-x_rtl / 12.0)) - 2.5 * (x_rtl / 100.0)

    # Layer 3: AI-Native Closed-Loop Exploration against physical verification oracles
    y_l3 = 20.0 + 72.0 / (1.0 + (32.0 / np.maximum(x_rtl, 0.01)) ** 2.2)

    # Human engineering ceiling
    y_human = 64.0
    ax2.axhline(
        y_human,
        color=COLORS["red"],
        linestyle="--",
        linewidth=1.2,
        alpha=0.85,
        zorder=2,
    )
    ax2.text(
        1.5,
        y_human + 2.5,
        "Human Engineering Ceiling\n(Cognitive Templates)",
        fontsize=5.1,
        fontweight="bold",
        color=COLORS["constraints_ink"],
        bbox=dict(
            boxstyle="round,pad=0.22",
            facecolor="white",
            edgecolor=COLORS["red"],
            alpha=0.92,
            lw=0.55,
        ),
        zorder=5,
    )

    # Plot curves
    (l_l1,) = ax2.plot(
        x_rtl,
        y_l1,
        color=COLORS["red"],
        linewidth=1.9,
        label="Layer 1: Imitation (Human RTL corpora; bounded)",
        zorder=3,
    )
    (l_l3,) = ax2.plot(
        x_rtl,
        y_l3,
        color=COLORS["green"],
        linewidth=2.2,
        label="Layer 3: AI-Native (Closed-loop physical oracles)",
        zorder=4,
    )

    # Point of breakthrough
    idx_break = np.argmin(np.abs(y_l3 - y_human))
    x_break = x_rtl[idx_break]
    y_break = y_l3[idx_break]
    ax2.plot(
        x_break, y_break, marker="o", markersize=4.8, color=COLORS["green"], zorder=6
    )
    ax2.annotate(
        "Discovers novel PPA trade-offs",
        xy=(x_break, y_break),
        xytext=(20.0, 83.0),
        textcoords="data",
        fontsize=5.1,
        fontweight="bold",
        color=COLORS["evidence_ink"],
        bbox=dict(
            boxstyle="round,pad=0.22",
            facecolor="white",
            edgecolor=COLORS["green"],
            alpha=0.94,
            lw=0.55,
        ),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS["green"],
            lw=0.8,
            shrinkB=4,
        ),
        zorder=6,
    )

    # In-panel clean legend in lower right quadrant
    leg2 = ax2.legend(
        handles=[l_l3, l_l1],
        loc="lower right",
        bbox_to_anchor=(0.98, 0.20),
        fontsize=5.1,
        frameon=True,
        facecolor="white",
        edgecolor=COLORS["grid"],
        framealpha=0.94,
    )
    leg2.set_zorder(5)

    ax2.set_xlim(-1, 101)
    ax2.set_ylim(10, 100)
    ax2.set_xticks([0, 50, 100])
    ax2.set_xticklabels(["Initial", "Intermediate Search", "Converged"], fontsize=5.8)
    ax2.set_yticks([20, 64, 92])
    ax2.set_yticklabels(["Baseline", "Human Ceiling", "Optimal Frontier"], fontsize=5.8)
    ax2.set_xlabel("Design Exploration Budget (Compute & Iterations)", fontsize=6.6)
    ax2.set_ylabel("Design Quality (PPA Pareto Frontier)", fontsize=6.6, labelpad=4)
    ax2.grid(True, color=COLORS["grid"], linewidth=0.55, zorder=0)

    # Oracle property card badge at bottom
    ax2.text(
        3.0,
        15.5,
        "Evaluation Oracle: Multi-fidelity physical signoff [STA, DRC, power: hours/days]",
        fontsize=4.6,
        fontstyle="italic",
        color=COLORS["muted"],
        bbox=dict(
            boxstyle="round,pad=0.22",
            facecolor="#F6F8FA",
            edgecolor=COLORS["grid"],
            alpha=0.92,
            lw=0.5,
        ),
        zorder=5,
    )

    # Save outputs
    fig.savefig(out_svg, format="svg", bbox_inches="tight")
    fig.savefig(out_pdf, format="pdf", bbox_inches="tight")
    fig.savefig(out_png, format="png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Generated:")
    print(f"  {out_svg}")
    print(f"  {out_pdf}")
    print(f"  {out_png}")


if __name__ == "__main__":
    main()
