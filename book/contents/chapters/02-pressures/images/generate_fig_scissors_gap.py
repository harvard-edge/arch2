#!/usr/bin/env python3
"""Generate an unscaled diagram of admitted checking work and waiting work.

Box sizes and arrow lengths encode no quantities. The diagram identifies the
stages to measure; it supplies no candidate counts, rates, or scope trend.
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style

apply_style()


def generate_scissors_figure(output_dir: Path):
    """Retain the figure's existing asset name for chapter cross-references."""
    output_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(4.8, 4.2))
    fig.subplots_adjust(left=0.015, right=0.985, top=0.99, bottom=0.01)
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.set_axis_off()

    left, width, height = 0.035, 0.52, 0.108
    center = left + width / 2
    right, right_width = 0.655, 0.315

    def card(x, y, w, h, role, title, body=None, title_size=9.0):
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.006,rounding_size=0.012",
                linewidth=0.85,
                edgecolor=COLORS[f"{role}_ink"],
                facecolor=COLORS[f"{role}_tint"],
                zorder=3,
            )
        )
        if body is None:
            ax.text(
                x + w / 2,
                y + h / 2,
                title,
                ha="center",
                va="center",
                fontsize=title_size,
                color=COLORS[f"{role}_ink"],
                zorder=4,
            )
        else:
            ax.text(
                x + w / 2,
                y + h * 0.70,
                title,
                ha="center",
                va="center",
                fontsize=title_size,
                fontweight="bold",
                color=COLORS[f"{role}_ink"],
                zorder=4,
            )
            ax.text(
                x + w / 2,
                y + h * 0.29,
                body,
                ha="center",
                va="center",
                fontsize=8.0,
                color=COLORS["ink"],
                zorder=4,
            )

    def arrow(start, end):
        ax.add_patch(
            FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=8.0,
                linewidth=0.9,
                color=COLORS["muted"],
                shrinkA=2.5,
                shrinkB=2.5,
                zorder=2,
            )
        )

    stages = [
        (0.857, height, "methods", "Generate proposals", "Candidate proposals"),
        (
            0.702,
            height,
            "methods",
            "Admission and screening",
            "Scope, legality, and study budget",
        ),
        (0.602, 0.055, "constraints", "Waiting for evaluation", None),
        (0.450, height, "evidence", "Evaluate", "Run tools and required checks"),
        (0.351, 0.055, "constraints", "Waiting for review", None),
        (0.200, height, "evidence", "Review", "Interpret evidence and remaining risk"),
        (
            0.044,
            height,
            "decision",
            "Completed decision",
            "Accept, reject, or seek more evidence",
        ),
    ]
    for y, h, role, title, body in stages:
        card(
            left,
            y,
            width,
            h,
            role,
            title,
            body,
            title_size=8.3 if body is None else 9.0,
        )
    for upper, lower in zip(stages, stages[1:]):
        arrow((center, upper[0]), (center, lower[0] + lower[1]))

    card(
        right,
        0.702,
        right_width,
        height,
        "designspace",
        "Discard or defer",
        "Not admitted",
        title_size=8.5,
    )
    arrow((left + width, 0.756), (right, 0.756))

    # Dashed leaders relate the note to both queues; they carry no flow or rate.
    for y in (0.6295, 0.3785):
        ax.plot(
            [left + width, right],
            [y, y],
            linestyle=(0, (2.5, 2.5)),
            linewidth=0.7,
            color=COLORS["constraints_ink"],
            zorder=1,
        )
    ax.add_patch(
        FancyBboxPatch(
            (right, 0.310),
            right_width,
            0.350,
            boxstyle="round,pad=0.006,rounding_size=0.012",
            linewidth=0.85,
            edgecolor=COLORS["constraints_ink"],
            facecolor=COLORS["constraints_tint"],
            zorder=3,
        )
    )
    note_center = right + right_width / 2
    ax.text(
        note_center,
        0.625,
        "Backlog grows when",
        ha="center",
        va="center",
        fontsize=8.5,
        fontweight="bold",
        color=COLORS["constraints_ink"],
        zorder=4,
    )
    ax.text(
        note_center,
        0.540,
        "admitted checking work\nexceeds completed work\nin the same interval.",
        ha="center",
        va="center",
        fontsize=8.0,
        linespacing=1.3,
        color=COLORS["ink"],
        zorder=4,
    )
    ax.text(
        note_center,
        0.397,
        "Compare work as well\nas candidate counts;\nchecking costs differ.",
        ha="center",
        va="center",
        fontsize=8.0,
        linespacing=1.3,
        color=COLORS["ink"],
        zorder=4,
    )
    ax.text(
        note_center,
        0.250,
        "Measure tool time\nand reviewer effort.",
        ha="center",
        va="center",
        fontsize=8.0,
        linespacing=1.3,
        color=COLORS["muted"],
    )

    for suffix in ("pdf", "svg", "png"):
        path = output_dir / f"fig-scissors-gap.{suffix}"
        fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=0.06)
        if suffix == "svg":
            path.write_text(
                "\n".join(line.rstrip() for line in path.read_text().splitlines())
                + "\n"
            )
        print(f"Generated: {path}")
    plt.close(fig)


if __name__ == "__main__":
    generate_scissors_figure(Path(__file__).resolve().parent)
