"""Render formal-result routing at the book's 4.8-inch print width."""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from book._python.plots import COLORS, apply_style


def generate_plot(output_dir: Path | None = None) -> str:
    apply_style()
    fig, ax = plt.subplots(figsize=(4.8, 4.65))
    fig.subplots_adjust(left=0.015, right=0.985, bottom=0.015, top=0.985)
    ax.set(xlim=(0, 4.8), ylim=(0, 4.65))
    ax.axis("off")

    def box(x, y, w, h, role):
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=.01,rounding_size=.045",
                edgecolor=COLORS[role],
                facecolor=COLORS[role + "_tint"],
                lw=1.0,
                zorder=2,
            )
        )

    box(0.08, 4.03, 4.64, 0.51, "workload")
    ax.text(
        2.4,
        4.36,
        "Formal return",
        ha="center",
        va="center",
        fontsize=9.5,
        weight="bold",
        color=COLORS["workload_ink"],
    )
    ax.text(
        2.4,
        4.15,
        "Property, model, assumptions, engine, and budget",
        ha="center",
        va="center",
        fontsize=8,
    )
    rows = [
        (
            3.50,
            "Counterexample",
            "Violation trace\nreturned",
            "Check reachability\nand realizability",
            "Repair a confirmed failure; refine an\nabstraction or proof if the trace is spurious.",
            "constraints",
        ),
        (
            2.55,
            "Proved",
            "Unbounded proof\ncompleted",
            "Qualify the scoped obligation",
            "Retain property, model, assumptions,\nand relevant vacuity checks.",
            "evidence",
        ),
        (
            1.60,
            "Bounded-only",
            "No violation through\ndepth $k$",
            "Retain the bound",
            "Seek a completeness argument or a\nseparate proof for unbounded safety.",
            "methods",
        ),
        (
            0.65,
            "Inconclusive",
            "Resource limit or\nunfinished query",
            "Revise the verification plan",
            "Qualify any completed bound separately;\na timeout establishes no proof or violation.",
            "designspace",
        ),
    ]
    for y, status, summary, title, body, role in rows:
        box(0.08, y - 0.4, 1.36, 0.8, role)
        ax.text(
            0.76,
            y + 0.17,
            status,
            ha="center",
            va="center",
            fontsize=9,
            weight="bold",
            color=COLORS[role + "_ink"],
        )
        ax.text(
            0.76,
            y - 0.12,
            summary,
            ha="center",
            va="center",
            fontsize=8,
            linespacing=1.35,
        )
        ax.annotate(
            "",
            xy=(1.73, y),
            xytext=(1.47, y),
            arrowprops=dict(arrowstyle="->", color=COLORS["muted"], lw=1.0),
        )
        ax.text(
            1.80,
            y + 0.24,
            title,
            ha="left",
            va="center",
            fontsize=8.2,
            weight="bold",
            linespacing=1.15,
        )
        ax.text(
            1.80, y - 0.14, body, ha="left", va="center", fontsize=8, linespacing=1.35
        )
    if output_dir is None:
        output_dir = Path(__file__).resolve().parent
    base = output_dir / "fig-sva-bmc-coverage-depth"
    for ext in ("svg", "pdf", "png"):
        fig.savefig(base.with_suffix("." + ext), dpi=300, bbox_inches="tight")
    svg = base.with_suffix(".svg")
    svg.write_text("\n".join(x.rstrip() for x in svg.read_text().splitlines()) + "\n")
    plt.close(fig)
    return str(base.with_suffix(".svg"))


if __name__ == "__main__":
    print(generate_plot())
