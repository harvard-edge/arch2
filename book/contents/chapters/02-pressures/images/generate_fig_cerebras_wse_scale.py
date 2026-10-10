"""Compare published WSE and V100 areas without asserting mechanical outlines.

Sources: Cerebras's 2019 WSE announcement (46,225 mm²) and
Choquette et al., IEEE Micro 2018 (V100: 815 mm²).
Squares encode area only; no wafer-containment geometry is implied.
"""

import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))
from book._python.plots import COLORS, apply_style


def generate_figure():
    apply_style()
    wse_area = 46225
    gpu_area = 815
    wse_side = math.sqrt(wse_area)
    gpu_side = math.sqrt(gpu_area)
    fig, ax = plt.subplots(figsize=(6.4, 4.5))
    purple = COLORS.get("purple", "#7B4EA8")
    blue = COLORS["blue"]
    ink = COLORS["ink"]
    ax.add_patch(
        Rectangle(
            (0, 0),
            wse_side,
            wse_side,
            facecolor=purple,
            edgecolor=purple,
            alpha=0.13,
            lw=1.4,
        )
    )
    ax.add_patch(
        Rectangle(
            (0, 0), wse_side, wse_side, facecolor="none", edgecolor=purple, lw=1.4
        )
    )
    gpu_x = 255
    ax.add_patch(
        Rectangle(
            (gpu_x, 0), gpu_side, gpu_side, facecolor=blue, edgecolor=blue, lw=1.2
        )
    )
    ax.text(
        wse_side / 2,
        120,
        "Cerebras WSE",
        color=purple,
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
    )
    ax.text(
        wse_side / 2, 99, "46,225 mm²", color=ink, ha="center", va="center", fontsize=11
    )
    ax.text(
        gpu_x + gpu_side / 2,
        66,
        "NVIDIA V100",
        color=blue,
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold",
    )
    ax.text(
        gpu_x + gpu_side / 2,
        47,
        "815 mm²",
        color=ink,
        ha="center",
        va="center",
        fontsize=10,
    )
    ax.text(
        160,
        -25,
        f"Published area ratio: {wse_area / gpu_area:.1f}×",
        ha="center",
        va="center",
        color=ink,
        fontsize=10,
    )
    ax.text(
        160,
        -45,
        "Area-proportional squares; not mechanical outlines",
        ha="center",
        va="center",
        color=COLORS["muted"],
        fontsize=8,
    )
    ax.set_xlim(-12, 335)
    ax.set_ylim(-57, 230)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.subplots_adjust(left=0.02, right=0.98, bottom=0.02, top=0.98)
    output = Path(__file__).with_name("fig-cerebras-wse-scale")
    for extension in ("svg", "pdf", "png"):
        fig.savefig(output.with_suffix(f".{extension}"), dpi=300, bbox_inches="tight")
    svg = output.with_suffix(".svg")
    svg.write_text(
        "\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n"
    )
    plt.close(fig)


if __name__ == "__main__":
    generate_figure()
