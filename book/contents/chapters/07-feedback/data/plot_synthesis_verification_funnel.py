"""
Architectural Workflow: Multi-Fidelity Synthesis & Verification Signoff Funnel (Chapter 7)
-----------------------------------------------------------------------------------------
Visualizes the hierarchical multi-fidelity screening pipeline that protects scarce
downstream compute and commercial EDA licenses during automated architectural search.

Key Architectural Elements:
1. Five progressive screening tiers with increasing physical fidelity and execution latency.
2. Two closed-loop recovery pathways:
   - Early structural/functional rejections route back to Generative Agent Revision.
   - Late physical/timing near-misses route to Localized ECO Optimization.
3. Clean architectural taxonomy with ZERO synthetic numbers or invented percentages.

Exports SVG, PDF, and 300 DPI PNG to:
- book/contents/chapters/07-feedback/images/fig-synthesis-verification-funnel.{png,svg,pdf}
- book/images/fig-synthesis-verification-funnel.{png,svg,pdf}
"""

import sys
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style, save_figure_bundle

apply_style()


def main():
    chapter_dir = Path(__file__).resolve().parents[1]
    out_plot_ch = chapter_dir / "images" / "fig-synthesis-verification-funnel"
    out_plot_global = (
        REPO_ROOT / "book" / "images" / "fig-synthesis-verification-funnel"
    )

    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    fig.subplots_adjust(left=0.04, right=0.96, top=0.95, bottom=0.06)

    ax.set_xlim(0, 100)
    ax.set_ylim(-6, 104)
    ax.axis("off")

    # Title
    ax.text(
        50,
        101,
        "Multi-Fidelity Verification & Physical Signoff Funnel",
        ha="center",
        va="center",
        fontsize=9.2,
        fontweight="bold",
        color=COLORS["ink"],
    )

    # 5 Tiers Data
    tiers = [
        {
            "name": "Stage 1: Syntactic & AST Parsing",
            "tools": "Tree-Sitter / Verilator / Slang",
            "checks": "Syntax valid, elaborated module hierarchy, port types",
            "latency": "Milliseconds (free / open-source)",
            "y": 78,
            "width": 64,
            "color": COLORS["blue"],
        },
        {
            "name": "Stage 2: Interface Schema & Interconnect",
            "tools": "Static Schema Linters / Protocol Checkers",
            "checks": "AXI / TLM handshakes, port widths, clock domain tags",
            "latency": "Seconds (low compute overhead)",
            "y": 62,
            "width": 54,
            "color": COLORS["green"],
        },
        {
            "name": "Stage 3: Functional & Assertion Verification",
            "tools": "SystemVerilog Assertions (SVA) / BMC / Sim",
            "checks": "Temporal invariants, state-machine deadlocks, coverage",
            "latency": "Minutes (simulation pool / SAT solver)",
            "y": 46,
            "width": 44,
            "color": COLORS["orange"],
        },
        {
            "name": "Stage 4: Static Timing Analysis (STA)",
            "tools": "OpenSTA / Synopsys PrimeTime / Cadence Tempus",
            "checks": "Multi-corner setup & hold slack, WNS/TNS, max transition",
            "latency": "Tens of minutes (licensed STA seat)",
            "y": 30,
            "width": 34,
            "color": COLORS["purple"],
        },
        {
            "name": "Stage 5: Physical DRC / LVS Signoff",
            "tools": "OpenROAD / Cadence Innovus / Synopsys ICC2",
            "checks": "Design rule clean (DRC), layout vs. schematic (LVS)",
            "latency": "Hours to days (full signoff toolchain)",
            "y": 14,
            "width": 24,
            "color": COLORS["red"],
        },
    ]

    # Draw funneled tiers
    for i, t in enumerate(tiers):
        y = t["y"]
        w = t["width"]
        x = 42 - w / 2

        # Main tier box
        rect = patches.FancyBboxPatch(
            (x, y - 5.5),
            w,
            11,
            boxstyle="round,pad=0.6,rounding_size=1.2",
            facecolor="white",
            edgecolor=t["color"],
            linewidth=1.6,
            zorder=3,
        )
        ax.add_patch(rect)

        # Stage header & description
        ax.text(
            x + 1.8,
            y + 2.2,
            t["name"],
            ha="left",
            va="center",
            fontsize=6.8,
            fontweight="bold",
            color=t["color"],
            zorder=4,
        )
        ax.text(
            x + 1.8,
            y - 0.4,
            f"Checks: {t['checks']}",
            ha="left",
            va="center",
            fontsize=5.2,
            color=COLORS["ink"],
            zorder=4,
        )
        ax.text(
            x + 1.8,
            y - 2.8,
            f"Engines: {t['tools']}  •  Cost: {t['latency']}",
            ha="left",
            va="center",
            fontsize=4.7,
            fontstyle="italic",
            color=COLORS["muted"],
            zorder=4,
        )

        # Connecting downward funnel arrow to next stage
        if i < len(tiers) - 1:
            next_y = tiers[i + 1]["y"]
            ax.annotate(
                "",
                xy=(42, next_y + 5.5),
                xytext=(42, y - 5.5),
                arrowprops=dict(
                    arrowstyle="->",
                    color=COLORS["ink"],
                    lw=1.2,
                    shrinkA=1,
                    shrinkB=1,
                ),
                zorder=2,
            )

    # Top Input: Generative Candidate Proposals
    ax.annotate(
        "",
        xy=(42, 83.5),
        xytext=(42, 91.5),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS["ink"],
            lw=1.4,
            shrinkA=1,
            shrinkB=1,
        ),
        zorder=2,
    )
    ax.text(
        42,
        92.8,
        "Generative Proposals (Candidate Pool $N_0$)",
        ha="center",
        va="center",
        fontsize=6.5,
        fontweight="bold",
        color=COLORS["ink"],
        bbox=dict(
            boxstyle="round,pad=0.3",
            facecolor="#F6F8FA",
            edgecolor=COLORS["grid"],
            lw=0.8,
        ),
    )

    # Bottom Output: Tapeout-Ready Silicon
    ax.annotate(
        "",
        xy=(42, 0.5),
        xytext=(42, 8.5),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS["green"],
            lw=1.5,
            shrinkA=1,
            shrinkB=1,
        ),
        zorder=2,
    )
    ax.text(
        42,
        -1.2,
        "Tapeout-Qualified Clean Implementation (GDSII / OASIS)",
        ha="center",
        va="center",
        fontsize=6.5,
        fontweight="bold",
        color=COLORS["green"],
        bbox=dict(
            boxstyle="round,pad=0.3",
            facecolor="#E7F5EC",
            edgecolor=COLORS["green"],
            lw=0.8,
        ),
    )

    # Left Column: Invalidation & Generative Revision Feedback Loop
    ax.annotate(
        "",
        xy=(8, 88),
        xytext=(8, 46),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS["red"],
            lw=1.2,
            linestyle="--",
        ),
    )
    # Lines from stages 1, 2, 3 to rejection line
    for st_idx in [0, 1, 2]:
        sy = tiers[st_idx]["y"]
        sx = 42 - tiers[st_idx]["width"] / 2
        ax.plot([sx, 8], [sy, sy], color=COLORS["red"], lw=1.0, linestyle="--")

    # Connect top of rejection line to Generative Proposals
    ax.plot([8, 22], [88, 88], color=COLORS["red"], lw=1.0, linestyle="--")
    ax.text(
        8,
        92,
        "Structural & Functional Failures\nRoute to Generative Prompt / AST Repair",
        ha="center",
        va="bottom",
        fontsize=5.2,
        fontweight="bold",
        color=COLORS["red"],
    )

    # Right Column: Near-Miss Physical ECO Loop & Signoff Economics
    ax.annotate(
        "",
        xy=(76, 36),
        xytext=(76, 14),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS["purple"],
            lw=1.2,
            linestyle="-.",
        ),
    )
    ax.plot([54, 76], [14, 14], color=COLORS["purple"], lw=1.0, linestyle="-.")
    ax.plot([59, 76], [30, 30], color=COLORS["purple"], lw=1.0, linestyle="-.")
    ax.text(
        76,
        40,
        "Near-Miss Timing & DRC Failures\nRoute to Localized ECO Optimization\n(Buffer insertion, gate sizing, wire widening)",
        ha="left",
        va="center",
        fontsize=5.2,
        fontweight="bold",
        color=COLORS["purple"],
        bbox=dict(
            boxstyle="round,pad=0.3",
            facecolor="#FBF0DE",
            edgecolor=COLORS["orange"],
            lw=0.6,
        ),
    )

    # Right side architectural principles card
    ax.text(
        76,
        72,
        "Signoff Funnel Economics:\n"
        "• Hierarchical Multi-Fidelity:\n"
        "  Fast AST & schema checks prune non-viable\n"
        "  candidates before licensed tools run.\n"
        "• License Capacity Protection:\n"
        "  Commercial STA & PnR tools are strictly\n"
        "  rate-limited by license pool seats.\n"
        "• Separation of Concerns:\n"
        "  Architectural search proposes candidate RTL;\n"
        "  ECO closures repair physical margins without\n"
        "  restarting the generative loop.",
        ha="left",
        va="center",
        fontsize=5.0,
        color=COLORS["ink"],
        bbox=dict(
            boxstyle="round,pad=0.4",
            facecolor="#F6F8FA",
            edgecolor=COLORS["grid"],
            lw=0.7,
        ),
    )

    save_figure_bundle(fig, out_plot_ch)
    save_figure_bundle(fig, out_plot_global)
    print(f"Generated clean workflow funnel: {out_plot_ch}")
    plt.close(fig)


if __name__ == "__main__":
    main()
