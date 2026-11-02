#!/usr/bin/env python3
"""Plot nightly Ibex aggregate pass rate above the failing-group raster."""
import csv
import datetime as dt
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from book._python.plots import (
    COLORS,
    FONT_SIZES,
    apply_style,
    save_figure_bundle,
)  # noqa: E402


def d(text):
    return dt.date.fromisoformat(text)


def main():
    nightly = list(
        csv.DictReader((HERE / "derived/nightly.csv").open(encoding="utf-8"))
    )
    cells = list(
        csv.DictReader((HERE / "derived/group_night.csv").open(encoding="utf-8"))
    )
    first, last = d(nightly[0]["date"]), d(nightly[-1]["date"])
    days = (last - first).days + 1
    fails, seen = {}, {}
    for c in cells:
        name = c["test_name"]
        seen[name] = seen.get(name, 0) + 1
        fails[name] = fails.get(name, 0) + (c["nonpass"] in {"True", "true", "1"})
    order = sorted(seen, key=lambda n: fails[n] / seen[n], reverse=True)
    index = {n: i for i, n in enumerate(order)}
    grid = np.zeros((len(order), days), dtype=int)  # 0 absent, 1 pass, 2 nonpass
    for c in cells:
        grid[index[c["test_name"]], (d(c["date"]) - first).days] = (
            2 if c["nonpass"] in {"True", "true", "1"} else 1
        )

    apply_style()
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(6.2, 3.7), sharex=True, gridspec_kw={"height_ratios": [1, 2.1]}
    )
    fig.subplots_adjust(left=0.085, right=0.985, top=0.96, bottom=0.09, hspace=0.13)
    xs = [d(r["date"]) for r in nightly]
    ys = [float(r["pass_pct"]) for r in nightly]
    # Break the line across gaps longer than a week so missing reports are not interpolated.
    start = 0
    for i in range(1, len(xs) + 1):
        if i == len(xs) or (xs[i] - xs[i - 1]).days > 7:
            ax1.plot(
                xs[start:i], ys[start:i], color=COLORS["workload"], lw=0.7, zorder=2
            )
            start = i
    ax1.set_ylim(85, 100)
    ax1.set_yticks([85, 90, 95, 100])
    ax1.set_ylabel("Passing runs (%)", fontsize=FONT_SIZES["label"])
    ax1.grid(True, axis="y", color=COLORS["row"], linewidth=0.4, zorder=0)

    cmap = ListedColormap(["#FFFFFF", COLORS["row"], COLORS["constraints"]])
    extent = [mdates.date2num(first) - 0.5, mdates.date2num(last) + 0.5, len(order), 0]
    ax2.imshow(
        grid,
        aspect="auto",
        cmap=cmap,
        vmin=0,
        vmax=2,
        extent=extent,
        interpolation="nearest",
    )
    ax2.xaxis_date()
    ax2.xaxis.set_major_locator(mdates.YearLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax2.set_yticks([])
    ax2.set_ylabel(
        "Test groups, most often\nfailing at top", fontsize=FONT_SIZES["label"]
    )
    ax2.legend(
        handles=[
            Patch(color=COLORS["constraints"], label="Nonpassing run recorded"),
            Patch(color=COLORS["row"], label="All runs passed"),
            Patch(
                facecolor="white",
                edgecolor=COLORS["grid"],
                label="No report or group absent",
            ),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.09),
        ncol=3,
        frameon=False,
        fontsize=FONT_SIZES["note"],
        handlelength=1.1,
    )
    for ax, tag in ((ax1, "(a)"), (ax2, "(b)")):
        ax.text(
            0.005,
            0.9 if ax is ax1 else 1.02,
            tag,
            transform=ax.transAxes,
            fontsize=7,
            fontweight="bold",
            color=COLORS["ink"],
        )
        ax.tick_params(
            axis="both", labelsize=FONT_SIZES["tick"], length=2.5, width=0.6, pad=2
        )
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
    save_figure_bundle(fig, HERE / "figure")
    save_figure_bundle(
        fig,
        ROOT / "book/contents/chapters/07-feedback/images/fig-ch07-ibex-nightly-churn",
    )


if __name__ == "__main__":
    main()
