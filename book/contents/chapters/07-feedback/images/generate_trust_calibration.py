"""Render proxy qualification at print width; no invented data curves."""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from book._python.plots import COLORS, apply_style


def generate_plot():
    apply_style()
    fig, ax = plt.subplots(figsize=(4.8, 4.55))
    fig.subplots_adjust(left=0.015, right=0.985, bottom=0.015, top=0.985)
    ax.set(xlim=(0, 4.8), ylim=(0, 4.55))
    ax.axis("off")

    def box(y, h, role):
        ax.add_patch(
            FancyBboxPatch(
                (0.37, y),
                4.32,
                h,
                boxstyle="round,pad=.01,rounding_size=.045",
                edgecolor=COLORS[role],
                facecolor=COLORS[role + "_tint"],
                lw=1.0,
                zorder=2,
            )
        )

    rows = [
        (
            3.61,
            "Relevant observations",
            "Candidate and intended use; workload, tool, and operating scope\nMatched proxy/reference results",
            "workload",
        ),
        (
            2.53,
            "Agreement checks",
            "Held-out error and ranking; false acceptance and rejection\nAgreement assessed against the declared decision tolerance",
            "methods",
        ),
        (
            1.45,
            "Bounded use",
            "Use supported by the checks; retain assessed scope and limits\nReopen qualification when conditions change",
            "evidence",
        ),
    ]
    for y, title, body, role in rows:
        box(y, 0.76, role)
        ax.text(
            2.53,
            y + 0.55,
            title,
            ha="center",
            va="center",
            fontsize=9.5,
            weight="bold",
            color=COLORS[role + "_ink"],
        )
        ax.text(
            2.53, y + 0.23, body, ha="center", va="center", fontsize=8, linespacing=1.5
        )
        if y > 1.5:
            ax.annotate(
                "",
                xy=(2.53, y - 0.29),
                xytext=(2.53, y - 0.035),
                arrowprops=dict(arrowstyle="->", lw=1, color=COLORS["muted"]),
            )
        ax.plot(
            [0.36, 0.16],
            [y + 0.38, y + 0.38],
            color=COLORS["designspace_ink"],
            lw=0.9,
            ls="--",
            zorder=1,
        )
    box(0.12, 1.03, "designspace")
    ax.text(
        2.53,
        0.93,
        "Requalify before relying on the proxy",
        ha="center",
        va="center",
        fontsize=9,
        weight="bold",
        color=COLORS["designspace_ink"],
    )
    ax.text(
        2.53,
        0.68,
        "Missing evidence, inadequate agreement, or changed scope:",
        ha="center",
        va="center",
        fontsize=8,
    )
    ax.text(
        2.53,
        0.37,
        "Collect matched reference results, revise the proxy, or defer use.\nAssess agreement again under the intended conditions.",
        ha="center",
        va="center",
        fontsize=8,
        linespacing=1.5,
    )
    ax.plot(
        [0.16, 0.16],
        [0.64, 3.99],
        color=COLORS["designspace_ink"],
        lw=0.9,
        ls="--",
        zorder=1,
    )
    ax.annotate(
        "",
        xy=(0.35, 0.64),
        xytext=(0.16, 0.64),
        arrowprops=dict(arrowstyle="->", color=COLORS["designspace_ink"], lw=0.9),
    )
    base = Path(__file__).resolve().parent / "fig-trust-calibration"
    for ext in ("svg", "pdf", "png"):
        fig.savefig(base.with_suffix("." + ext), dpi=300, bbox_inches="tight")
    svg = base.with_suffix(".svg")
    svg.write_text("\n".join(x.rstrip() for x in svg.read_text().splitlines()) + "\n")
    plt.close(fig)
    return str(base.with_suffix(".svg"))


if __name__ == "__main__":
    print(generate_plot())
