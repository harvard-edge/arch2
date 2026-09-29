"""
Benchmark health figure for Chapter 10 (zero-point flaws and contamination indicators).

Reads two transcribed, per-row-cited CSVs:
- chapter10-agentic-benchmark-flaws.csv  (Zhu et al. 2025, arXiv:2507.02825)
- chapter10-verilog-contamination.csv    (Wang et al. 2025, arXiv:2503.13572, Table I)

Writes SVG, PDF, and 300 DPI PNG to
book/contents/chapters/10-evaluation/images/fig-benchmark-health-zero-point-contamination.*
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style, save_figure_bundle  # noqa: E402

apply_style()

DATA = REPO_ROOT / "data" / "datasets"
OUT = (
    REPO_ROOT
    / "book"
    / "contents"
    / "chapters"
    / "10-evaluation"
    / "images"
    / "fig-benchmark-health-zero-point-contamination"
)


def main():
    flaws = pd.read_csv(DATA / "chapter10-agentic-benchmark-flaws.csv", comment="#")
    cont = pd.read_csv(DATA / "chapter10-verilog-contamination.csv", comment="#")

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(7.0, 2.9), gridspec_kw={"width_ratios": [1.0, 1.0]}
    )
    fig.subplots_adjust(wspace=0.55)

    # (a) Reported benchmark flaws, ordered as in the CSV (top to bottom).
    labels = {
        "trivial_agent_score": "no task solved",
        "absolute_misestimate": "flawed check",
    }
    y = list(range(len(flaws)))[::-1]
    for yi, (_, r) in zip(y, flaws.iterrows()):
        trivial = r["kind"] == "trivial_agent_score"
        ax1.barh(
            yi,
            r["value_pct"],
            height=0.55,
            color=COLORS["red"] if trivial else COLORS["amber"],
            hatch="" if trivial else "////",
            edgecolor=COLORS["ink"],
            linewidth=0.5,
            zorder=3,
        )
        v = r["value_pct"]
        txt = f"{v:+.0f} pp" if not trivial else f"{v:.0f}%"
        xpos = v + 3 if v >= 0 else 3
        ax1.text(
            xpos,
            yi,
            f"{txt}  ({labels[r['kind']].replace(chr(10), ' ')})",
            va="center",
            ha="left",
            fontsize=5.4,
            color=COLORS["ink"],
            zorder=5,
        )
    ax1.set_yticks(y)
    ax1.set_yticklabels(flaws["benchmark"], fontsize=6.0)
    ax1.axvline(0, color=COLORS["ink"], linewidth=0.7)
    ax1.set_xlim(-40, 185)
    ax1.set_ylim(-0.7, len(flaws) - 0.3)
    ax1.set_xlabel(
        "Reported effect of the flaw (percent or percentage points)", fontsize=6.4
    )
    ax1.set_title("Agentic benchmark flaws (ABC audit)", fontsize=7.2, pad=5)
    ax1.grid(True, axis="x", color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax1.text(
        -0.30,
        1.06,
        "(a)",
        transform=ax1.transAxes,
        fontsize=7.2,
        fontweight="bold",
        ha="right",
    )

    # (b) CDD flag rate against pass@1, two benchmarks distinguished by marker shape.
    styles = {
        "VerilogEval": dict(marker="o", color=COLORS["purple"], s=22),
        "RTLLM": dict(marker="s", color=COLORS["blue"], s=20),
    }
    for bench, st in styles.items():
        sub = cont[cont["benchmark"] == bench]
        ax2.scatter(
            sub["cdd_pct"],
            sub["pass1_pct"],
            edgecolor=COLORS["ink"],
            linewidth=0.5,
            label=bench,
            zorder=4,
            **st,
        )
    for model, dx, dy in [
        ("GPT-4o", -4, 4),
        ("GPT-3.5", -4, -9),
        ("DeepSeek-Coder", 4, 3),
    ]:
        r = cont[(cont["model"] == model) & (cont["benchmark"] == "VerilogEval")].iloc[
            0
        ]
        ax2.annotate(
            model,
            xy=(r["cdd_pct"], r["pass1_pct"]),
            xytext=(r["cdd_pct"] + dx, r["pass1_pct"] + dy),
            fontsize=5.4,
            ha="right" if dx < 0 else "left",
            color=COLORS["ink"],
            arrowprops=dict(arrowstyle="-", color=COLORS["muted"], lw=0.5),
            bbox=dict(
                boxstyle="round,pad=0.15",
                facecolor="white",
                edgecolor="none",
                alpha=0.9,
            ),
            zorder=5,
        )
    ax2.set_xlim(-5, 110)
    ax2.set_ylim(-4, 75)
    ax2.set_xlabel("Problems flagged by CDD (%)", fontsize=6.4)
    ax2.set_ylabel("Reported pass@1 (%)", fontsize=6.4)
    ax2.set_title("Verilog contamination flag vs. pass@1", fontsize=7.2, pad=5)
    ax2.grid(True, color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax2.legend(
        loc="upper left",
        fontsize=5.8,
        frameon=True,
        facecolor="white",
        edgecolor=COLORS["grid"],
    )
    ax2.text(
        -0.14,
        1.06,
        "(b)",
        transform=ax2.transAxes,
        fontsize=7.2,
        fontweight="bold",
        ha="right",
    )

    save_figure_bundle(fig, OUT)
    plt.close(fig)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
