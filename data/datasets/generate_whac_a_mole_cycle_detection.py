"""
Architectural Diagram: Closed-Loop Repair & Cryptographic State Hash Cycle Detection (Chapter 10)
------------------------------------------------------------------------------------------------
Visualizes how automated repair loops can become trapped in cyclic regressions (the Whac-a-Mole
effect) and how cryptographic state signatures H(S_t) == H(S_{t+2}) reliably detect state
oscillations that scalar violation counts cannot see.

Exports SVG, PDF, and 300 DPI PNG to:
- book/contents/chapters/10-evaluation/images/fig-whac-a-mole.{png,svg,pdf}
- book/images/fig-whac-a-mole.{png,svg,pdf}
"""

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
    ch_dir = REPO_ROOT / "book" / "contents" / "chapters" / "10-evaluation" / "images"
    ch_dir.mkdir(parents=True, exist_ok=True)
    out_ch = ch_dir / "fig-whac-a-mole"
    out_global = REPO_ROOT / "book" / "images" / "fig-whac-a-mole"

    fig, ax = plt.subplots(figsize=(8.8, 2.3))
    fig.subplots_adjust(left=0.02, right=0.98, top=0.96, bottom=0.04)

    ax.set_xlim(0, 100)
    ax.set_ylim(45, 92)
    ax.axis("off")

    # 3 States across time: t, t+1, t+2
    states = [
        {
            "title": "Iteration $t$: Candidate State $S_t$",
            "hash": "State signature: H(S_t) = hash(RTL, SDC, UPF)",
            "metrics": "Timing: n setup violations (WNS < 0)\nDRC: clean",
            "x": 5,
            "y": 48,
            "w": 25,
            "h": 24,
            "color": COLORS["blue"],
        },
        {
            "title": "Iteration $t+1$: Candidate State $S_{t+1}$",
            "hash": "State signature: H(S_t+1), differs from H(S_t)",
            "metrics": "Timing: setup met (WNS >= 0)\nn routing shorts and hold violations",
            "x": 37.5,
            "y": 48,
            "w": 25,
            "h": 24,
            "color": COLORS["orange"],
        },
        {
            "title": "Iteration $t+2$: Candidate State $S_{t+2}$",
            "hash": "State signature: H(S_t+2) = H(S_t)",
            "metrics": "Timing: n setup violations (WNS < 0)\nDRC: clean",
            "x": 70,
            "y": 48,
            "w": 25,
            "h": 24,
            "color": COLORS["blue"],
        },
    ]

    for s in states:
        rect = patches.FancyBboxPatch(
            (s["x"], s["y"]),
            s["w"],
            s["h"],
            boxstyle="round,pad=0.5,rounding_size=1.2",
            facecolor="white",
            edgecolor=s["color"],
            linewidth=1.6,
            zorder=3,
        )
        ax.add_patch(rect)
        ax.text(
            s["x"] + s["w"] / 2,
            s["y"] + s["h"] - 3.4,
            s["title"],
            ha="center",
            va="center",
            fontsize=6.8,
            fontweight="bold",
            color=s["color"],
            zorder=4,
        )
        ax.text(
            s["x"] + s["w"] / 2,
            s["y"] + s["h"] - 8.2,
            s["hash"],
            ha="center",
            va="center",
            fontsize=5.2,
            fontfamily="monospace",
            color=COLORS["ink"],
            zorder=4,
        )
        ax.text(
            s["x"] + s["w"] / 2,
            s["y"] + 5.0,
            s["metrics"],
            ha="center",
            va="center",
            fontsize=5.1,
            color=COLORS["muted"],
            zorder=4,
        )

    # Transition arrows
    ax.annotate(
        "",
        xy=(37.5, 60),
        xytext=(30, 60),
        arrowprops=dict(arrowstyle="->", color=COLORS["ink"], lw=1.3),
        zorder=5,
    )
    ax.text(
        33.75,
        64.5,
        r"Repair $\Delta_1$" + "\n(Buffer Sizing)",
        ha="center",
        va="center",
        fontsize=4.8,
        color=COLORS["ink"],
    )

    ax.annotate(
        "",
        xy=(70, 60),
        xytext=(62.5, 60),
        arrowprops=dict(arrowstyle="->", color=COLORS["ink"], lw=1.3),
        zorder=5,
    )
    ax.text(
        66.25,
        64.5,
        r"Repair $\Delta_2$" + "\n(Wire Widening)",
        ha="center",
        va="center",
        fontsize=4.8,
        color=COLORS["ink"],
    )

    # Cycle arc from state t+2 back to state t
    # Arc centered at (50, 72), width = 65, height = 24
    arc = patches.Arc(
        (50, 72),
        65,
        22,
        theta1=0,
        theta2=180,
        color=COLORS["red"],
        linewidth=1.8,
        linestyle="--",
        zorder=5,
    )
    ax.add_patch(arc)
    ax.annotate(
        "",
        xy=(17.5, 72),
        xytext=(17.5, 74),
        arrowprops=dict(arrowstyle="->", color=COLORS["red"], lw=1.8),
        zorder=5,
    )
    ax.text(
        50,
        86.5,
        r"Signature match: $H(S_{t+2}) = H(S_t) \rightarrow$ repeated state detected",
        ha="center",
        va="center",
        fontsize=6.5,
        fontweight="bold",
        color=COLORS["red"],
        bbox=dict(
            boxstyle="round,pad=0.3",
            facecolor="white",
            edgecolor=COLORS["red"],
            lw=1.0,
        ),
        zorder=6,
    )

    save_figure_bundle(fig, out_ch)
    save_figure_bundle(fig, out_global)
    print(f"Generated clean cycle detection figure: {out_ch}")
    plt.close(fig)


if __name__ == "__main__":
    main()
