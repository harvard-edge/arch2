"""Generate the conceptual BMC-depth schematic for Chapter 7.

CONCEPTUAL SCHEMATIC, NOT DATA. Every curve below is a hand-chosen logistic
or exponential shape used only to show qualitative behavior: shallow control
logic can reach a depth at which a separate completeness or induction argument
closes the proof, while complex controllers exhaust the solver budget first.
The axes carry qualitative labels only and no measured depth, runtime, or
coverage value is implied.
"""

from __future__ import annotations

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[4]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from _python.plots import COLORS, apply_style  # noqa: E402


def generate_plot(output_dir: Path | None = None) -> str:
    apply_style()
    fig, ax1 = plt.subplots(figsize=(5.2, 2.9))
    fig.subplots_adjust(left=0.2, right=0.72, top=0.95, bottom=0.17)

    k = np.linspace(1, 60, 240)
    curves = [
        (
            "Shallow control logic\n(e.g., DMA ring buffer)",
            100 / (1 + np.exp(-0.22 * (k - 12))),
            COLORS["green"],
            "-",
        ),
        (
            "Hierarchical protocol FSM",
            100 / (1 + np.exp(-0.16 * (k - 20))),
            COLORS["blue"],
            (0, (6, 2)),
        ),
        (
            "Credit-queue arbiter",
            82 / (1 + np.exp(-0.13 * (k - 24))),
            COLORS["orange"],
            (0, (4, 1.5, 1, 1.5)),
        ),
        (
            "Multi-tile controller",
            62 / (1 + np.exp(-0.10 * (k - 28))),
            COLORS["red"],
            (0, (1.2, 1.4)),
        ),
    ]
    label_y = [106, 92, 80, 61]
    for (label, y, color, ls), ly in zip(curves, label_y):
        ax1.plot(k, y, color=color, linewidth=1.6, linestyle=ls, zorder=3)
        ax1.text(
            61.2,
            ly,
            label,
            color=COLORS["ink"],
            fontsize=5.3,
            ha="left",
            va="center",
            clip_on=False,
        )

    ax1.axvspan(45, 60, color=COLORS["red"], alpha=0.10, zorder=0)
    ax1.text(
        52.5,
        6,
        "solver budget\nexhausted",
        ha="center",
        va="bottom",
        fontsize=5.2,
        color=COLORS["constraints_ink"],
        zorder=5,
    )
    ax1.axhline(100, color=COLORS["muted"], linestyle=":", linewidth=0.8)

    ax1.set_xlabel("BMC unroll depth $k$ (no scale implied)")
    ax1.set_xlim(1, 60)
    ax1.set_ylim(0, 112)
    ax1.set_xticks([1, 60])
    ax1.set_xticklabels(["shallow", "deep"])
    ax1.set_yticks([0, 50, 100])
    ax1.set_yticklabels(
        ["nothing\nchecked", "bounded\nclaim only", "completeness\nthreshold reached"],
        fontsize=5.4,
    )
    ax1.grid(True, color=COLORS["grid"], linewidth=0.45, zorder=0)

    ax1.annotate(
        "proof still needs a separate\ncompleteness or induction argument",
        xy=(36, 99),
        xytext=(21, 4),
        fontsize=5.2,
        color=COLORS["evidence_ink"],
        arrowprops=dict(arrowstyle="->", color=COLORS["green"], lw=0.7),
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="white",
            edgecolor=COLORS["green"],
            alpha=0.95,
            lw=0.5,
        ),
        zorder=6,
    )

    # Solver cost, conceptual, on a secondary log axis with markers for grayscale
    ax2 = ax1.twinx()
    runtime = 0.05 * np.exp(0.21 * k)
    ax2.plot(
        k,
        runtime,
        color=COLORS["purple"],
        linewidth=0.9,
        marker="o",
        markevery=24,
        markersize=2.4,
        zorder=2,
    )
    ax2.set_yscale("log")
    ax2.set_yticks([])
    ax2.minorticks_off()
    ax1.text(
        61.2,
        119,
        "Solver cost (log scale,\nconceptual, circle markers)",
        color=COLORS["designspace_ink"],
        fontsize=5.3,
        ha="left",
        va="center",
        clip_on=False,
    )

    for spine in ("top", "right"):
        ax1.spines[spine].set_visible(False)
        ax2.spines[spine].set_visible(False)

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        base = output_dir / "fig-sva-bmc-coverage-depth"
        fig.savefig(base.with_suffix(".svg"), format="svg", bbox_inches="tight")
        fig.savefig(base.with_suffix(".pdf"), format="pdf", bbox_inches="tight")
        fig.savefig(
            base.with_suffix(".png"), format="png", dpi=300, bbox_inches="tight"
        )
        plt.close(fig)
        return str(base.with_suffix(".svg"))
    return ""


if __name__ == "__main__":
    print(generate_plot(Path(__file__).resolve().parent))
