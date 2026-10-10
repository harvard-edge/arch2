"""Draw the conceptual candidate-recurrence diagram for Chapter 10.

The native width matches the book column so labels remain readable in print.
A repair followed by rollback restores candidate artifacts, while a controller
state check is still needed before calling the recurrence a workflow cycle.
Exports identical SVG, PDF, and 300 DPI PNG twins to both image directories.
"""

import shutil
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as patches

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style, save_figure_bundle

apply_style()


def main():
    fig, ax = plt.subplots(figsize=(4.8, 4.5))
    fig.subplots_adjust(left=0.035, right=0.975, top=0.98, bottom=0.02)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 120)
    ax.axis("off")

    ax.text(
        52,
        114,
        "A rollback restores the earlier candidate",
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold",
        color=COLORS["ink"],
    )

    states = [
        (94, r"Candidate $S_t$", r"Signature $H(S_t)$", "Before repair", "blue"),
        (
            70,
            r"Candidate $S_{t+1}$",
            r"$H(S_{t+1}) \ne H(S_t)$",
            "Physical artifacts changed",
            "orange",
        ),
        (
            46,
            r"Candidate $S_{t+2}$",
            r"$H(S_{t+2}) = H(S_t)$",
            "Earlier artifacts restored",
            "blue",
        ),
    ]
    for y, title, signature, note, color in states:
        ax.add_patch(
            patches.FancyBboxPatch(
                (19, y - 8),
                74,
                16,
                boxstyle="round,pad=0.5,rounding_size=1.2",
                facecolor="white",
                edgecolor=COLORS[color],
                linewidth=1.3,
                zorder=3,
            )
        )
        for offset, content, size, weight, ink in [
            (4.5, title, 10, "bold", COLORS[color]),
            (0, signature, 10, "normal", COLORS["ink"]),
            (-4.5, note, 8, "normal", COLORS["muted"]),
        ]:
            ax.text(
                56,
                y + offset,
                content,
                ha="center",
                va="center",
                fontsize=size,
                fontweight=weight,
                color=ink,
                zorder=4,
            )

    for y0, y1, label in [(85.3, 78.7, "Physical repair"), (61.3, 54.7, "Rollback")]:
        ax.annotate(
            "",
            xy=(56, y1),
            xytext=(56, y0),
            arrowprops=dict(arrowstyle="->", color=COLORS["ink"], lw=1.1),
            zorder=5,
        )
        ax.text(
            62,
            (y0 + y1) / 2,
            label,
            ha="left",
            va="center",
            fontsize=8,
            color=COLORS["ink"],
            zorder=5,
        )

    # Recurrence links candidate artifacts, not the complete controller state.
    ax.plot(
        [18.5, 11, 11],
        [46, 46, 94],
        linestyle="--",
        color=COLORS["red"],
        linewidth=1.1,
        zorder=2,
    )
    ax.annotate(
        "",
        xy=(18.5, 94),
        xytext=(11, 94),
        arrowprops=dict(arrowstyle="->", color=COLORS["red"], lw=1.1),
        zorder=5,
    )
    ax.text(
        5,
        70,
        "Matching candidate signatures",
        rotation=90,
        ha="center",
        va="center",
        fontsize=8,
        color=COLORS["constraints_ink"],
        zorder=5,
    )

    ax.text(
        52,
        28,
        "Signature inputs: canonical netlist, placement/routing\n"
        "database, and effective loaded constraints.",
        ha="center",
        va="center",
        fontsize=8,
        linespacing=1.35,
        color=COLORS["ink"],
        zorder=5,
    )
    ax.text(
        52,
        10,
        "Before retrying: check tool configuration, random state,\n"
        "policy state, and action history. A candidate match alone\n"
        "does not establish a workflow cycle.",
        ha="center",
        va="center",
        fontsize=8,
        linespacing=1.4,
        color=COLORS["ink"],
        bbox=dict(
            boxstyle="round,pad=0.55",
            facecolor=COLORS["row"],
            edgecolor=COLORS["grid"],
            lw=0.7,
        ),
        zorder=5,
    )

    chapter_images = (
        REPO_ROOT / "book" / "contents" / "chapters" / "10-evaluation" / "images"
    )
    bundle = save_figure_bundle(fig, chapter_images / "fig-whac-a-mole", dpi=300)
    svg = bundle["svg"]
    svg.write_text(
        "\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n"
    )
    global_images = REPO_ROOT / "book" / "images"
    global_images.mkdir(parents=True, exist_ok=True)
    for artifact in bundle.values():
        shutil.copy2(artifact, global_images / artifact.name)
    plt.close(fig)
    print("Wrote print-sized candidate-recurrence figure twins")


if __name__ == "__main__":
    main()
