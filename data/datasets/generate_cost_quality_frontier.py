"""
Cost-quality frontier for Chapter 10: systolic-array exploration record.
-----------------------------------------------------------------------
Reads data/datasets/chapter5-dse-empirical-convergence.csv (4,000 evaluations =
4 optimizers x 10 seeds x 100 steps from a cycle-level systolic-array simulation;
the generating harness is not retained, see that file's header).

Cost axis: the record's area proxy `total_area`, which is a model quantity
(1 unit per processing element plus 0.8 units per KiB of on-chip buffer), not a
silicon area in mm^2.
Quality axis: total simulated cycles for the record's two-workload suite
(`total_cycles`, lower is better). The record's `fom_score` is not used because
it equals 1e9 / (total_cycles * total_area) and already divides by area.

Each distinct configuration is counted once (its cycle count is identical across
repeated evaluations). A configuration is nondominated when no other
configuration has area <= and cycles <= with at least one strict inequality.

Exports SVG, PDF, and 300 DPI PNG to
book/contents/chapters/10-evaluation/images/fig-cost-quality-frontier.{svg,pdf,png}
and prints every number the chapter quotes.
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

CFG = [
    "array_height",
    "array_width",
    "ifmap_kb",
    "filter_kb",
    "ofmap_kb",
    "dataflow",
    "bandwidth",
]
CYCLE_TARGET = 10_000  # illustrative admission threshold, declared before selection


def nondominated(d):
    d = d.sort_values(["total_area", "total_cycles"])
    keep, best = [], float("inf")
    for _, r in d.iterrows():
        if r["total_cycles"] < best:
            keep.append(r)
            best = r["total_cycles"]
    return pd.DataFrame(keep)


def main():
    out = (
        REPO_ROOT
        / "book"
        / "contents"
        / "chapters"
        / "10-evaluation"
        / "images"
        / "fig-cost-quality-frontier"
    )
    df = pd.read_csv(
        REPO_ROOT / "data" / "datasets" / "chapter5-dse-empirical-convergence.csv",
        comment="#",
    )
    assert df.groupby(CFG)["total_cycles"].nunique().max() == 1
    d = df.drop_duplicates(CFG).copy()
    front = nondominated(d)
    admitted = front[front["total_cycles"] <= CYCLE_TARGET].iloc[0]

    n_eval, n_cfg, n_front = len(df), len(d), len(front)
    print(
        f"evaluations={n_eval} distinct_configs={n_cfg} nondominated={n_front} "
        f"dominated={n_cfg - n_front} ({100 * (n_cfg - n_front) / n_cfg:.1f}%)"
    )
    print(front[CFG + ["total_area", "total_cycles"]].to_string(index=False))
    print("admitted:", dict(admitted[CFG + ["total_area", "total_cycles"]]))
    lo, mid, hi = (
        front.iloc[0],
        front[front["array_height"].eq(16) & front["array_width"].eq(16)].iloc[0],
        front.iloc[-1],
    )
    print(
        f"frontier {lo.total_area}->{mid.total_area}: area x{mid.total_area / lo.total_area:.1f}, "
        f"cycles /{lo.total_cycles / mid.total_cycles:.1f}"
    )
    print(
        f"frontier {mid.total_area}->{hi.total_area}: area x{hi.total_area / mid.total_area:.1f}, "
        f"cycles /{mid.total_cycles / hi.total_cycles:.1f}"
    )

    fig, ax = plt.subplots(figsize=(4.8, 3.1))
    ax.scatter(
        d["total_area"],
        d["total_cycles"] / 1e3,
        s=7,
        marker="o",
        color=COLORS["muted"],
        alpha=0.25,
        linewidths=0,
        label=f"Dominated configurations ({n_cfg - n_front:,})",
        zorder=2,
    )
    ax.step(
        front["total_area"],
        front["total_cycles"] / 1e3,
        where="post",
        color=COLORS["blue"],
        linewidth=1.4,
        zorder=3,
    )
    ax.scatter(
        front["total_area"],
        front["total_cycles"] / 1e3,
        s=22,
        marker="D",
        color=COLORS["blue"],
        edgecolor="white",
        linewidth=0.6,
        label=f"Nondominated configurations ({n_front})",
        zorder=4,
    )
    ax.axhline(
        CYCLE_TARGET / 1e3,
        color=COLORS["red"],
        linestyle="--",
        linewidth=1.0,
        label=f"Admission threshold ({CYCLE_TARGET:,} cycles)",
        zorder=1,
    )
    ax.scatter(
        [admitted["total_area"]],
        [admitted["total_cycles"] / 1e3],
        s=70,
        marker="*",
        color=COLORS["green"],
        edgecolor=COLORS["ink"],
        linewidth=0.5,
        zorder=5,
    )
    ax.annotate(
        f"Lowest-area admitted: {int(admitted.array_height)}$\\times${int(admitted.array_width)} array\n"
        f"area proxy {admitted.total_area:.1f}, {int(admitted.total_cycles):,} cycles",
        xy=(admitted["total_area"], admitted["total_cycles"] / 1e3),
        xytext=(420, 40),
        fontsize=5.6,
        color=COLORS["ink"],
        arrowprops=dict(arrowstyle="->", color=COLORS["ink"], lw=0.7),
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor="white",
            edgecolor=COLORS["green"],
            lw=0.6,
            alpha=0.95,
        ),
        zorder=6,
    )
    ax.set_yscale("log")
    ax.set_xlim(0, 1400)
    ax.set_ylim(1.5, 500)
    ax.set_xlabel(
        "Area proxy (1 per PE + 0.8 per KiB buffer; model units)", fontsize=6.6
    )
    ax.set_ylabel("Total simulated cycles (thousands, log scale)", fontsize=6.6)
    ax.grid(True, color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax.legend(
        loc="upper right",
        fontsize=5.6,
        frameon=True,
        facecolor="white",
        edgecolor=COLORS["grid"],
    )
    save_figure_bundle(fig, out)
    plt.close(fig)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
