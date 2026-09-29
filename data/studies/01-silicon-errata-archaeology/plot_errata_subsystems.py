#!/usr/bin/env python3
"""Draw fig-errata-subsystem-shares for Chapter 11 from the committed data.

Reads errata_classified.csv (through audit_metrics.json, which is computed from
it) and writes SVG, PDF, and PNG twins to
book/contents/chapters/11-ownership/images/fig-errata-subsystem-shares.*

    python3 data/studies/01-silicon-errata-archaeology/plot_errata_subsystems.py

Bars: share of all errata assigned to each reporting class by the committed
rules. Dot and whisker: audit-adjusted share with its 95% bootstrap interval.
The "not resolved" bar is hatched grey so it reads without color.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "book"))
from _python.plots import COLORS, apply_style, save_figure_bundle  # noqa: E402

OUT = (
    ROOT
    / "book"
    / "contents"
    / "chapters"
    / "11-ownership"
    / "images"
    / "fig-errata-subsystem-shares"
)


def main() -> int:
    m = json.loads((HERE / "audit_metrics.json").read_text())
    rep = yaml.safe_load((HERE / "reporting_classes.yml").read_text())
    short = {R["name"]: R["short"] for R in rep["reporting"]}
    unresolved = rep["not_resolved"]["name"]
    short[unresolved] = rep["not_resolved"]["short"]

    reported = sorted(
        (n for n in m["shares"] if n != unresolved),
        key=lambda n: -m["shares"][n]["rule_share"],
    )
    order = reported + [unresolved]

    apply_style()
    fig, ax = plt.subplots(figsize=(4.8, 2.55))
    fig.subplots_adjust(left=0.30, right=0.97, top=0.86, bottom=0.17)

    for i, n in enumerate(order):
        s = m["shares"][n]
        rule = 100 * s["rule_share"]
        adj = 100 * s["adjusted_share"]
        lo, hi = (100 * x for x in s["adjusted_ci95"])
        if n == unresolved:
            ax.barh(
                i,
                rule,
                height=0.62,
                color=COLORS["row"],
                edgecolor=COLORS["muted"],
                hatch="////",
                linewidth=0.6,
                zorder=2,
            )
        else:
            ax.barh(
                i,
                rule,
                height=0.62,
                color=COLORS["evidence_tint"],
                edgecolor=COLORS["evidence"],
                linewidth=0.8,
                zorder=2,
            )
        ax.plot(
            [lo, hi],
            [i, i],
            color=COLORS["ink"],
            linewidth=0.9,
            zorder=4,
            solid_capstyle="butt",
        )
        for x in (lo, hi):
            ax.plot(
                [x, x],
                [i - 0.13, i + 0.13],
                color=COLORS["ink"],
                linewidth=0.9,
                zorder=4,
            )
        ax.plot(adj, i, marker="o", markersize=3.4, color=COLORS["ink"], zorder=5)
        ax.text(
            max(hi, rule) + 0.8,
            i,
            f"{rule:.1f}%",
            va="center",
            ha="left",
            fontsize=5.6,
            color=COLORS["ink"],
            zorder=5,
        )

    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([short[n] for n in order], fontsize=6.0)
    ax.invert_yaxis()
    ax.set_xlim(0, 30)
    ax.set_xticks([0, 5, 10, 15, 20, 25, 30])
    ax.set_xticklabels([f"{t}%" for t in [0, 5, 10, 15, 20, 25, 30]])
    ax.set_xlabel(f"Share of {m['population']:,} published errata", fontsize=6.4)
    ax.grid(axis="x", color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.spines["left"].set_color(COLORS["muted"])
    ax.spines["bottom"].set_color(COLORS["muted"])
    ax.tick_params(axis="y", length=0, pad=3)
    ax.tick_params(axis="x", length=2.5, width=0.6)

    handles = [
        Patch(
            facecolor=COLORS["evidence_tint"],
            edgecolor=COLORS["evidence"],
            linewidth=0.8,
            label="Rule-assigned share",
        ),
        Line2D(
            [0],
            [0],
            color=COLORS["ink"],
            marker="o",
            markersize=3.4,
            linewidth=0.9,
            label="Audit-adjusted share, 95% interval",
        ),
    ]
    fig.legend(
        handles=handles,
        loc="upper center",
        ncol=2,
        frameon=False,
        fontsize=5.6,
        bbox_to_anchor=(0.635, 0.995),
        handlelength=1.6,
        columnspacing=1.0,
        handletextpad=0.5,
    )

    paths = save_figure_bundle(fig, OUT)
    for p in paths.values():
        print(p.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
