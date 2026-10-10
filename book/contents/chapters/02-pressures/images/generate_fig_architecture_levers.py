#!/usr/bin/env python3
"""Render the conceptual architecture-scale diagram at its final print size.

The five scales, their obligations, and their common comparison path are
conceptual categories, not quantitative observations. All wording from the
original diagram is retained; only the layout changes from columns to rows.
Outputs: SVG, PDF, and 300-dpi PNG, each 4.8 × 4.7 inches.
"""

from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from book._python.plots import apply_style

SCALES = [
    (
        "Core",
        "one microarchitecture",
        [
            "pipeline and cache policies",
            "coherence and corner cases",
            "timing and physical checks",
        ],
    ),
    (
        "Accelerator",
        "one specialized function",
        ["workload mapping", "programming interface", "data movement"],
    ),
    (
        "SoC or chiplet",
        "one composed package",
        ["integration and package", "interconnect and opaque IP", "test and signoff"],
    ),
    (
        "Wafer-scale",
        "one physical fabric",
        ["yield and repair", "power delivery and reach", "placement and scheduling"],
    ),
    (
        "Warehouse-scale",
        "one deployed service",
        [
            "network and facility limits",
            "failure and tail behavior",
            "deployment policy",
        ],
    ),
]


def generate_figure(out_dir: Path | None = None):
    apply_style()
    out_dir = out_dir or Path(__file__).resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(4.8, 4.7))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set(xlim=(0, 4.8), ylim=(0, 4.7))
    ax.set_axis_off()
    ink, muted, flow = "#222222", "#596772", "#3E474B"

    def text(x, y, value, size=7.5, **kwargs):
        return ax.text(
            x,
            y,
            value,
            fontsize=size,
            color=kwargs.pop("color", ink),
            va="center",
            **kwargs,
        )

    def arrow(start, end):
        ax.add_patch(
            FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=7,
                linewidth=0.7,
                color=flow,
                shrinkA=0,
                shrinkB=0,
            )
        )

    text(0.28, 4.56, "System boundary expands", 9.0, fontweight="bold")
    text(0.39, 4.34, "Scale", 7.7, fontweight="bold", color=muted)
    text(2.27, 4.34, "Added obligations", 7.7, fontweight="bold", color=muted)
    arrow((0.13, 4.22), (0.13, 1.12))

    centers = []
    for i, (name, description, obligations) in enumerate(SCALES):
        bottom = 3.64 - i * 0.63
        centers.append(bottom + 0.29)
        ax.add_patch(
            Rectangle(
                (0.28, bottom),
                1.71,
                0.58,
                facecolor="#F0ECFA",
                edgecolor="#6A4FC7",
                linewidth=0.75,
            )
        )
        ax.add_patch(
            Rectangle(
                (2.16, bottom),
                2.35,
                0.58,
                facecolor="#F5F8FA",
                edgecolor="#9AA8B5",
                linewidth=0.75,
            )
        )
        text(0.39, bottom + 0.365, name, 8.5, fontweight="bold")
        text(0.39, bottom + 0.185, description, 7.3)
        arrow((1.99, bottom + 0.29), (2.16, bottom + 0.29))
        for j, obligation in enumerate(obligations):
            text(2.27, bottom + 0.44 - j * 0.15, obligation, 7.5)
        ax.plot([4.51, 4.67], [bottom + 0.29] * 2, color=flow, linewidth=0.65)

    # All five branches join one comparison path; vertical position is ordinal.
    ax.plot([4.67, 4.67, 2.4], [centers[0], 0.90, 0.90], color=flow, linewidth=0.65)
    text(
        2.4,
        1.01,
        "Comparison obligations accumulate",
        7.7,
        fontweight="bold",
        color=muted,
        ha="center",
    )
    arrow((2.4, 0.90), (2.4, 0.80))

    ax.add_patch(
        Rectangle(
            (0.28, 0.10),
            4.23,
            0.70,
            facecolor="#E7F5EC",
            edgecolor="#1E9E48",
            linewidth=0.85,
        )
    )
    text(
        2.395,
        0.64,
        "Cross-scale architecture comparison",
        8.1,
        fontweight="bold",
        color="#1B7837",
        ha="center",
    )
    for y, value in (
        (0.48, "Constraints • interfaces • workload and software path"),
        (0.335, "Tool feedback • failures • rejected alternatives"),
        (0.19, "Conditions that can reverse the decision"),
    ):
        text(2.395, y, value, 7.3, ha="center")

    stem = out_dir / "fig-architecture-levers"
    fig.savefig(stem.with_suffix(".png"), dpi=300)
    fig.savefig(stem.with_suffix(".pdf"))
    fig.savefig(stem.with_suffix(".svg"))
    svg = stem.with_suffix(".svg")
    svg.write_text(
        "\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n"
    )
    plt.close(fig)
    print(f"Generated {stem}.svg, .pdf, and .png")


if __name__ == "__main__":
    generate_figure()
