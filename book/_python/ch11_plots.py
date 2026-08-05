"""Generate Matplotlib figures for Chapter 11 (Ownership and Governance)."""

import sys
from pathlib import Path

# Add book directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import numpy as np

from _python.plots import COLORS, apply_style


def generate_nre_mask_cost_productivity_plot(output_dir: Path) -> None:
    apply_style()

    nodes = ["90nm", "45nm", "28nm", "16nm", "7nm", "3nm", "2nm"]
    x = np.arange(len(nodes))

    # Fixed Reticle Mask Set & Packaging NRE Cost ($ Millions)
    mask_cost_m = np.array([1.5, 4.2, 12.5, 28.0, 65.0, 120.0, 180.0])

    # Conventional Front-End HDL Engineering Labor Cost ($ Millions per SoC)
    conv_design_cost_m = np.array([8.0, 16.0, 32.0, 55.0, 95.0, 150.0, 210.0])

    # Architecture 2.0 AI-Assisted Front-End Design Labor Cost ($ Millions per SoC) - 100x scaling
    ai_design_cost_m = np.array([0.12, 0.22, 0.40, 0.65, 1.05, 1.50, 2.10])

    fig, ax1 = plt.subplots(figsize=(6.4, 3.8))
    fig.subplots_adjust(left=0.12, right=0.86, top=0.86, bottom=0.20)

    # Primary Axis: Front-End Design Costs (Log scale)
    ax1.set_yscale("log")
    l1 = ax1.plot(
        x,
        conv_design_cost_m,
        color=COLORS["blue"],
        linewidth=2.0,
        marker="o",
        markersize=5,
        label="Conventional Front-End Labor Cost",
        zorder=3,
    )
    l2 = ax1.plot(
        x,
        ai_design_cost_m,
        color=COLORS["green"],
        linewidth=2.2,
        linestyle="--",
        marker="s",
        markersize=5,
        label="Architecture 2.0 AI Design Cost (100x Scaling)",
        zorder=3,
    )

    ax1.set_xlabel("Semiconductor Process Technology Node", fontsize=6.8, labelpad=6)
    ax1.set_ylabel(
        "Front-End Design Labor Cost ($M, Log Scale)", fontsize=6.8, color=COLORS["ink"]
    )
    ax1.set_xticks(x)
    ax1.set_xticklabels(nodes, fontsize=6.2)
    ax1.set_ylim(0.08, 500)
    ax1.tick_params(axis="both", labelsize=6.0, length=2.5, width=0.6, pad=2)
    ax1.grid(True, color=COLORS["grid"], linewidth=0.55, zorder=0)

    # Secondary Axis: Fixed Reticle Mask Cost ($M)
    ax2 = ax1.twinx()
    ax2.set_yscale("log")
    l3 = ax2.plot(
        x,
        mask_cost_m,
        color=COLORS["red"],
        linewidth=2.2,
        marker="^",
        markersize=5.5,
        label="Fixed Reticle Mask Set NRE Cost",
        zorder=4,
    )
    ax2.set_ylabel(
        "Fixed Reticle Mask NRE Cost ($M, Log Scale)",
        fontsize=6.8,
        color=COLORS["constraints_ink"],
    )
    ax2.set_ylim(0.08, 500)

    ax2.tick_params(
        axis="y",
        labelsize=6.0,
        length=2.5,
        width=0.6,
        pad=2,
        colors=COLORS["constraints_ink"],
    )
    ax2.spines["right"].set_color(COLORS["constraints_ink"])
    ax2.spines["top"].set_visible(False)

    # Shaded 100x efficiency gap at 3nm
    ax1.fill_between(
        [4.8, 5.2], [1.5, 1.5], [150, 150], color=COLORS["green"], alpha=0.12, zorder=2
    )

    # Annotations
    ax1.annotate(
        "100x Front-End Cost Collapse\n($150M to $1.5M at 3nm)",
        xy=(5.0, 12.0),
        xytext=(2.3, 3.5),
        arrowprops=dict(arrowstyle="->", color=COLORS["evidence_ink"], lw=0.9),
        fontsize=6.4,
        fontweight="bold",
        color=COLORS["evidence_ink"],
    )

    ax2.annotate(
        "Fixed Mask Cost Wall\n$120M at 3nm Node",
        xy=(5.0, 120.0),
        xytext=(2.6, 170.0),
        arrowprops=dict(arrowstyle="->", color=COLORS["constraints_ink"], lw=0.9),
        fontsize=6.4,
        fontweight="bold",
        color=COLORS["constraints_ink"],
    )

    ax1.set_title(
        "NRE Mask Set Cost vs AI Design Productivity 100x Scaling Curve",
        fontsize=8.0,
        pad=10,
        fontweight="bold",
    )

    # Combine legend handles
    lines = l1 + l2 + l3
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, frameon=False, fontsize=5.8, loc="upper left")

    for spine in ["top"]:
        ax1.spines[spine].set_visible(False)
    ax1.spines["left"].set_color(COLORS["ink"])
    ax1.spines["bottom"].set_color(COLORS["ink"])

    svg_path = output_dir / "fig-nre-mask-cost-productivity.svg"
    pdf_path = output_dir / "fig-nre-mask-cost-productivity.pdf"
    plt.savefig(svg_path, format="svg", bbox_inches="tight")
    plt.savefig(pdf_path, format="pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"Generated {svg_path} and {pdf_path}")


if __name__ == "__main__":
    out_dir = (
        Path(__file__).resolve().parents[1] / "chapters" / "11-ownership" / "images"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    generate_nre_mask_cost_productivity_plot(out_dir)
