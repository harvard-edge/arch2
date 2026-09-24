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

    fig, ax = plt.subplots(figsize=(8.8, 4.4))
    fig.subplots_adjust(left=0.02, right=0.98, top=0.96, bottom=0.04)

    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Title
    ax.text(
        50,
        96.5,
        "Cyclic State Detection via Cryptographic Signatures vs. Scalar Violation Counts",
        ha="center",
        va="center",
        fontsize=9.2,
        fontweight="bold",
        color=COLORS["ink"],
    )

    # 3 States across time: t, t+1, t+2
    states = [
        {
            "title": "Iteration $t$: Candidate State $S_t$",
            "hash": "Hash: SHA256(RTL, SDC) = 0x8f3c...",
            "metrics": "Timing: 15 Setup Violations (WNS = -0.42ns)\nDRC: 0 Spacing / Antenna Violations",
            "x": 5,
            "y": 48,
            "w": 25,
            "h": 24,
            "color": COLORS["blue"],
        },
        {
            "title": "Iteration $t+1$: Candidate State $S_{t+1}$",
            "hash": "Hash: SHA256(RTL, SDC) = 0x2b1e...",
            "metrics": "Timing: 0 Setup Violations (WNS > 0)\nDRC: 15 Routing Shorts / Hold Violations",
            "x": 37.5,
            "y": 48,
            "w": 25,
            "h": 24,
            "color": COLORS["orange"],
        },
        {
            "title": "Iteration $t+2$: Candidate State $S_{t+2}$",
            "hash": "Hash: SHA256(RTL, SDC) = 0x8f3c... (Match!)",
            "metrics": "Timing: 15 Setup Violations (WNS = -0.42ns)\nDRC: 0 Spacing / Antenna Violations",
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

    # Lower Left Card: The Naive Violation-Count Trap
    trap_rect = patches.FancyBboxPatch(
        (5, 5),
        43.5,
        36,
        boxstyle="round,pad=0.6,rounding_size=1.2",
        facecolor="#FBF0DE",
        edgecolor=COLORS["orange"],
        linewidth=1.4,
        zorder=2,
    )
    ax.add_patch(trap_rect)
    ax.text(
        26.75,
        36.5,
        "The Naive Scalar Count Trap (Blind to State Identity)",
        ha="center",
        va="center",
        fontsize=6.8,
        fontweight="bold",
        color=COLORS["orange"],
        zorder=3,
    )
    trap_text = (
        "• Scalar Monitoring: Counts total violations (15 -> 15 -> 15).\n"
        "• The Illusion: Optimizer assumes continuous search progress or\n"
        "  stalls because violation count does not decrease.\n"
        "• The Hazard: Cannot distinguish productive exploration along a\n"
        "  Pareto boundary from cyclic thrashing between two inverted\n"
        "  failure modes (setup timing vs. hold / routing congestion)."
    )
    ax.text(
        7.5,
        20.0,
        trap_text,
        ha="left",
        va="center",
        fontsize=5.2,
        color=COLORS["ink"],
        linespacing=1.4,
        zorder=3,
    )

    # Lower Right Card: Cryptographic State-Signature Comparator
    antidote_rect = patches.FancyBboxPatch(
        (51.5, 5),
        43.5,
        36,
        boxstyle="round,pad=0.6,rounding_size=1.2",
        facecolor="#E7F5EC",
        edgecolor=COLORS["green"],
        linewidth=1.4,
        zorder=2,
    )
    ax.add_patch(antidote_rect)
    ax.text(
        73.25,
        36.5,
        "Cryptographic Cycle Detection (The Architectural Antidote)",
        ha="center",
        va="center",
        fontsize=6.8,
        fontweight="bold",
        color=COLORS["green"],
        zorder=3,
    )
    antidote_text = (
        "• State Fingerprint: Hashes RTL AST, SDC constraints, and UPF intent.\n"
        "• Exact Cycle Check: Evaluates H(S_t) == H(S_{t+2}) equality.\n"
        "• Deterministic Halt: Identifies that state S_{t+2} exactly repeats S_t\n"
        "  despite identical violation counts.\n"
        "• Recovery Action: Breaks the infinite loop, releases EDA licenses,\n"
        "  rolls back to last trusted checkpoint, and requests strategy change."
    )
    ax.text(
        54.0,
        20.0,
        antidote_text,
        ha="left",
        va="center",
        fontsize=5.2,
        color=COLORS["ink"],
        linespacing=1.4,
        zorder=3,
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
        r"Cryptographic Match: $H(S_{t+2}) = H(S_t) \rightarrow$ Infinite Cycle Detected!",
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
