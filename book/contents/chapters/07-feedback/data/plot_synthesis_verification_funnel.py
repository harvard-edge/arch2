"""Selected verification checks and repair routes, sized for a 4.8-inch column.

This unscaled workflow contains no empirical attrition or runtime data.
"""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from book._python.plots import COLORS, apply_style


def main():
    apply_style()
    fig, ax = plt.subplots(figsize=(4.8, 6.0))
    fig.subplots_adjust(left=0.015, right=0.985, top=0.985, bottom=0.015)
    ax.set(xlim=(0, 4.8), ylim=(0, 6))
    ax.axis("off")

    def box(y, h, role):
        ax.add_patch(
            FancyBboxPatch(
                (0.08, y),
                4.64,
                h,
                boxstyle="round,pad=.01,rounding_size=.05",
                facecolor="white",
                edgecolor=COLORS[role],
                lw=1.1,
                zorder=2,
            )
        )

    def arrow(a, b):
        ax.annotate(
            "",
            xy=(2.4, b),
            xytext=(2.4, a),
            arrowprops=dict(arrowstyle="->", lw=1, color=COLORS["muted"]),
        )

    ax.text(
        2.4,
        5.83,
        "Generative candidate proposals",
        ha="center",
        va="center",
        fontsize=10,
        weight="bold",
    )
    arrow(5.64, 5.48)
    stages = [
        (
            4.80,
            "1. Syntax and elaboration",
            "Grammar, module hierarchy, and port types",
            "Tree-Sitter / Verilator / Slang",
            "workload",
        ),
        (
            3.98,
            "2. Interface and interconnect",
            "Handshake rules, port widths, and clock-domain tags",
            "Schema linters / protocol checkers",
            "evidence",
        ),
        (
            3.16,
            "3. Functional and assertion checks",
            "Temporal properties, deadlocks, and coverage",
            "SVA checkers / BMC / simulators",
            "methods",
        ),
        (
            2.34,
            "4. Static timing analysis",
            "Setup and hold checks under specified modes and corners",
            "OpenSTA / PrimeTime / Tempus",
            "designspace",
        ),
        (
            1.52,
            "5. Physical verification",
            "Design rules and layout-versus-schematic checks",
            "Calibre / KLayout / Netgen",
            "constraints",
        ),
    ]
    for y, title, checks, tools, role in stages:
        box(y, 0.64, role)
        ax.text(
            0.23,
            y + 0.48,
            title,
            ha="left",
            va="center",
            fontsize=9,
            weight="bold",
            color=COLORS[role + "_ink"],
        )
        ax.text(0.23, y + 0.28, checks, ha="left", va="center", fontsize=8)
        ax.text(
            0.23,
            y + 0.095,
            "Example engines: " + tools,
            ha="left",
            va="center",
            fontsize=8,
            fontstyle="italic",
        )
        if y > 1.6:
            arrow(y - 0.035, y - 0.155)
    arrow(1.49, 1.29)
    ax.text(
        2.4,
        1.15,
        "Implementation passing the listed checks",
        ha="center",
        va="center",
        fontsize=9,
        weight="bold",
        color=COLORS["evidence_ink"],
    )
    ax.text(
        0.16,
        0.78,
        "Early structural or functional failure:",
        ha="left",
        va="center",
        fontsize=8.5,
        weight="bold",
        color=COLORS["constraints_ink"],
    )
    ax.text(
        0.16,
        0.58,
        "Revise generated RTL; rerun the affected checks.",
        ha="left",
        va="center",
        fontsize=8,
    )
    ax.text(
        0.16,
        0.32,
        "Physical timing or DRC near-miss:",
        ha="left",
        va="center",
        fontsize=8.5,
        weight="bold",
        color=COLORS["designspace_ink"],
    )
    ax.text(
        0.16,
        0.12,
        "Assess a local ECO; rerun the affected checks.",
        ha="left",
        va="center",
        fontsize=8,
    )
    base = (
        Path(__file__).resolve().parents[1] / "images/fig-synthesis-verification-funnel"
    )
    for ext in ("svg", "pdf", "png"):
        fig.savefig(base.with_suffix("." + ext), dpi=300, bbox_inches="tight")
    svg = base.with_suffix(".svg")
    svg.write_text("\n".join(x.rstrip() for x in svg.read_text().splitlines()) + "\n")
    plt.close(fig)
    print(base)


if __name__ == "__main__":
    main()
