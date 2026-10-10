#!/usr/bin/env python3
"""Render an unscaled energy-dependency diagram, with no illustrative data."""

from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))
from book._python.plots import COLORS, apply_style


def main():
    apply_style()
    fig, ax = plt.subplots(figsize=(5.0, 3.7))
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.03, top=0.98)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(
        0.5,
        0.94,
        "Candidate minus baseline\nSame workload and system boundary",
        ha="center",
        va="center",
        fontsize=9.2,
        color=COLORS["ink"],
    )

    boxes = [
        (
            0.035,
            "Compute",
            r"$\Delta E_{\mathrm{compute}} < 0$",
            "Local energy\nsaving",
            "workload",
        ),
        (
            0.365,
            "Memory +\ninterconnect",
            r"$\Delta E_{\mathrm{memory}}$"
            + "\n"
            + r"$+\Delta E_{\mathrm{interconnect}}$",
            "May rise with\nadded traffic",
            "methods",
        ),
        (
            0.695,
            "Control + leakage",
            r"$\Delta E_{\mathrm{control}}$" + "\n" + r"$+\Delta E_{\mathrm{leakage}}$",
            "Also enter the\ncomparison",
            "designspace",
        ),
    ]
    width, bottom, height = 0.27, 0.43, 0.39
    for x, title, equation, note, role in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, bottom),
                width,
                height,
                boxstyle="round,pad=0.008,rounding_size=0.018",
                facecolor=COLORS[f"{role}_tint"],
                edgecolor=COLORS[role],
                linewidth=1.2,
            )
        )
        ax.text(
            x + width / 2,
            bottom + 0.31,
            title,
            ha="center",
            va="center",
            fontsize=9.2,
            fontweight="bold",
            color=COLORS[f"{role}_ink"],
        )
        ax.text(
            x + width / 2,
            bottom + 0.19,
            equation,
            ha="center",
            va="center",
            fontsize=11.2,
            color=COLORS["ink"],
        )
        ax.text(
            x + width / 2,
            bottom + 0.06,
            note,
            ha="center",
            va="center",
            fontsize=8.7,
            color=COLORS["muted"],
        )
        ax.add_patch(
            FancyArrowPatch(
                (x + width / 2, bottom - 0.018),
                (x + width / 2, 0.32),
                arrowstyle="-|>",
                mutation_scale=9,
                linewidth=1.0,
                color=COLORS["muted"],
            )
        )

    ax.add_patch(
        FancyBboxPatch(
            (0.035, 0.025),
            0.93,
            0.27,
            boxstyle="round,pad=0.008,rounding_size=0.018",
            facecolor="white",
            edgecolor=COLORS["ink"],
            linewidth=1.1,
        )
    )
    ax.text(
        0.5,
        0.195,
        r"$\Delta E_{\mathrm{system}} = \Delta E_{\mathrm{compute}} + \Delta E_{\mathrm{memory}}$"
        + "\n"
        + r"$+\Delta E_{\mathrm{interconnect}} + \Delta E_{\mathrm{control}} + \Delta E_{\mathrm{leakage}}$",
        ha="center",
        va="center",
        fontsize=11.2,
        color=COLORS["ink"],
    )
    ax.text(
        0.5,
        0.075,
        r"Lower total energy requires $\Delta E_{\mathrm{system}} < 0$.",
        ha="center",
        va="center",
        fontsize=10.5,
        color=COLORS["ink"],
    )

    stem = Path(__file__).with_name("fig-waterbed-effect")
    for ext, kwargs in (("svg", {}), ("pdf", {}), ("png", {"dpi": 300})):
        fig.savefig(stem.with_suffix(f".{ext}"), bbox_inches="tight", **kwargs)
    svg = stem.with_suffix(".svg")
    svg.write_text(
        "\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n"
    )
    plt.close(fig)
    print(f"Generated {stem}.svg/.pdf/.png")


if __name__ == "__main__":
    main()
