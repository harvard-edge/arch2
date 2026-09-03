#!/usr/bin/env python3
"""Testbench vacuity, rebuilt from a transcribed receipt.

Replaces `fig-testbench-vacuity-and-judge-bias`, whose values came from
`random.Random(seed)` and `rng.gauss()` in
`data/scrapers/mine_testbench_vacuity_and_judge_bias.py` while its caption
attributed them to [@VerilogEval; @RTLLM; @ThakurEtAl2023VeriGen]. That figure
also carried a second panel reporting an LLM-judge calibration experiment that
was never run; it is withdrawn rather than replaced.

Every value here is transcribed from
`data/source-receipts/chapter7-testbench-vacuity-mutation.csv`, which carries a
per-row citation and URL to Herdt, Grosse and Drechsler (ASPDAC 2021) and the
OpenHW CORE-V verification effort. The receipt has no generating script.

    python3 generate_testbench_vacuity.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT / "book"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from _python.plots import COLORS, apply_style

RECEIPT = ROOT / "data" / "source-receipts" / "chapter7-testbench-vacuity-mutation.csv"

SHORT = {
    "Tier 1": "Directed\nunit tests",
    "Tier 2": "Constrained-random\nUVM",
    "Tier 3": "Official compliance\nsuite",
    "Tier 4": "Formal, symbolic",
}


def load():
    raw = [
        r for r in csv.reader(open(RECEIPT)) if r and not r[0].lstrip().startswith("#")
    ]
    rows = [dict(zip(raw[0], r)) for r in raw[1:]]
    out = []
    for r in rows:
        key = r["verification_tier"].split(":")[0].strip()
        out.append(
            (
                SHORT.get(key, key),
                float(r["line_coverage_pct"]),
                float(r["mutation_score_pct"]),
            )
        )
    return out


def main():
    apply_style()
    data = load()
    labels = [d[0] for d in data]
    line = [d[1] for d in data]
    kill = [d[2] for d in data]

    fig, ax = plt.subplots(figsize=(6.6, 2.6))
    x = range(len(labels))
    w = 0.36
    b1 = ax.bar(
        [i - w / 2 for i in x],
        line,
        w,
        color=COLORS["grid"],
        edgecolor=COLORS["muted"],
        linewidth=0.6,
        zorder=3,
        label="Line coverage",
    )
    b2 = ax.bar(
        [i + w / 2 for i in x],
        kill,
        w,
        color=COLORS["constraints"],
        zorder=3,
        label="Seeded faults killed",
    )
    for bars in (b1, b2):
        for b in bars:
            ax.text(
                b.get_x() + b.get_width() / 2,
                b.get_height() + 1.6,
                f"{b.get_height():.1f}",
                ha="center",
                va="bottom",
                fontsize=5.4,
                color=COLORS["muted"],
                zorder=5,
            )

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=5.8)
    ax.set_ylim(0, 122)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel("Percent")
    ax.legend(
        loc="upper left",
        bbox_to_anchor=(0.0, 1.03),
        frameon=False,
        fontsize=6.0,
        ncol=2,
    )
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color=COLORS["grid"], lw=0.5)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)

    gap = line[0] - kill[0]
    xg = 0 + w / 2
    ax.annotate(
        "",
        xy=(xg, line[0]),
        xytext=(xg, kill[0]),
        arrowprops=dict(arrowstyle="<->", color=COLORS["constraints_ink"], lw=0.9),
        zorder=6,
    )
    ax.text(
        xg + 0.09,
        (line[0] + kill[0]) / 2,
        f"{gap:.1f} point\nvacuity gap",
        fontsize=6.0,
        fontweight="bold",
        color=COLORS["constraints_ink"],
        va="center",
        ha="left",
        linespacing=1.3,
        zorder=6,
    )

    fig.tight_layout()
    for ext in ("svg", "pdf", "png"):
        fig.savefig(HERE / f"fig-testbench-vacuity.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("wrote fig-testbench-vacuity.{svg,pdf,png}")
    print(
        f"  directed tests: {line[0]:.1f}% covered, {kill[0]:.1f}% killed, "
        f"{gap:.1f} point gap"
    )
    print(f"  formal:         {line[-1]:.1f}% covered, {kill[-1]:.1f}% killed")


if __name__ == "__main__":
    main()
