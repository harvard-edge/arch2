"""Generate Matplotlib figures for Chapter 2 (The Architecture Design Loop)."""

import sys
from pathlib import Path

# Add book directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import numpy as np

from _python.plots import COLORS, apply_style


def generate_apple_vs_nvidia_cadence(output_dir: Path) -> None:
    """Generate plot comparing hardware cadence vs software evolution window for Apple Silicon and NVIDIA Datacenter."""
    apply_style()

    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    fig.subplots_adjust(left=0.18, right=0.95, top=0.86, bottom=0.18)

    # Apple Data (months relative to Nov 2020)
    apple_months = [0, 19, 35, 42]
    apple_labels = ["M1\nNov 2020", "M2\nJun 2022", "M3\nOct 2023", "M4\nMay 2024"]
    apple_gaps = [19, 16, 7]

    # NVIDIA Data (months relative to Nov 2020: A100 is May 2020 -> -6)
    gpu_months = [-6, 16, 40, 62]
    gpu_labels = [
        "A100\nMay 2020",
        "H100\nMar 2022",
        "B100\nMar 2024",
        "R100\nJan 2026",
    ]
    gpu_gaps = [22, 24, 22]

    # Draw Apple timeline (y=1.0)
    ax.plot([-10, 68], [1.0, 1.0], color=COLORS["grid"], linewidth=1.5, zorder=1)
    ax.scatter(
        apple_months,
        [1.0] * len(apple_months),
        facecolor=COLORS["note_fill"],
        edgecolor=COLORS["workload"],
        s=80,
        linewidth=1.8,
        zorder=3,
    )

    for m, l in zip(apple_months, apple_labels):
        ax.text(
            m,
            1.18,
            l,
            ha="center",
            va="bottom",
            fontweight="bold",
            color=COLORS["ink"],
            fontsize=5.8,
        )
    for i in range(len(apple_months) - 1):
        mid = (apple_months[i] + apple_months[i + 1]) / 2
        ax.annotate(
            "",
            xy=(apple_months[i + 1] - 0.8, 0.88),
            xytext=(apple_months[i] + 0.8, 0.88),
            arrowprops=dict(
                arrowstyle="<->",
                color=COLORS["magenta"],
                linewidth=1.2,
            ),
        )
        ax.text(
            mid,
            0.75,
            f"{apple_gaps[i]} mo",
            ha="center",
            va="top",
            color=COLORS["decision_ink"],
            fontweight="bold",
            fontsize=5.8,
        )

    # Draw GPU timeline (y=-0.5)
    ax.plot([-10, 68], [-0.5, -0.5], color=COLORS["grid"], linewidth=1.5, zorder=1)
    ax.scatter(
        gpu_months,
        [-0.5] * len(gpu_months),
        facecolor=COLORS["note_fill"],
        edgecolor=COLORS["designspace"],
        s=80,
        linewidth=1.8,
        zorder=3,
    )

    for m, l in zip(gpu_months, gpu_labels):
        ax.text(
            m,
            -0.32,
            l,
            ha="center",
            va="bottom",
            fontweight="bold",
            color=COLORS["ink"],
            fontsize=5.8,
        )
    for i in range(len(gpu_months) - 1):
        mid = (gpu_months[i] + gpu_months[i + 1]) / 2
        ax.annotate(
            "",
            xy=(gpu_months[i + 1] - 0.8, -0.62),
            xytext=(gpu_months[i] + 0.8, -0.62),
            arrowprops=dict(
                arrowstyle="<->",
                color=COLORS["magenta"],
                linewidth=1.2,
            ),
        )
        ax.text(
            mid,
            -0.75,
            f"{gpu_gaps[i]} mo",
            ha="center",
            va="top",
            color=COLORS["decision_ink"],
            fontweight="bold",
            fontsize=5.8,
        )

    ax.set_yticks([1.0, -0.5])
    ax.set_yticklabels(
        ["Apple Mobile SoC\n(Consumer)", "NVIDIA Datacenter\n(Enterprise AI)"],
        fontsize=6.5,
        fontweight="bold",
        color=COLORS["ink"],
    )
    ax.set_ylim(-1.1, 1.6)
    ax.set_xlim(-12, 68)

    ax.set_xlabel(
        "Timeline (months relative to Nov 2020)", fontsize=6.5, color=COLORS["ink"]
    )
    ax.set_title(
        "Silicon release cadences and software adaptation exposure windows",
        fontsize=7.8,
        pad=12,
        fontweight="bold",
        color=COLORS["ink"],
    )

    # Grid and spines
    ax.grid(True, axis="x", color=COLORS["grid"], linewidth=0.45, zorder=0)
    for spine in ["top", "right", "left", "bottom"]:
        ax.spines[spine].set_visible(False)

    output_dir.mkdir(parents=True, exist_ok=True)
    svg_path = output_dir / "fig-silicon-cadence.svg"
    plt.savefig(svg_path, format="svg", bbox_inches="tight")
    plt.close(fig)
    print(f"Generated {svg_path}")


if __name__ == "__main__":
    out_dir = (
        Path(__file__).resolve().parents[1] / "chapters" / "02-pressures" / "images"
    )
    generate_apple_vs_nvidia_cadence(out_dir)
