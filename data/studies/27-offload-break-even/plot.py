#!/usr/bin/env python3
"""Plot the offload break-even sweep from medians.csv; every run is drawn."""
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from book._python.plots import (
    COLORS,
    FONT_SIZES,
    apply_style,
    save_figure_bundle,
)  # noqa: E402

PANELS = [
    (
        "One product",
        [
            ("cpu_single", "Host CPU", "o", COLORS["ink"]),
            ("mps_resident", "GPU, operands resident", "s", COLORS["workload"]),
            ("mps_copy", "GPU, copies in and out", "^", COLORS["methods"]),
        ],
    ),
    (
        "Sixteen products",
        [
            ("cpu_bmm", "Host CPU, batched", "o", COLORS["ink"]),
            ("mps_16_launch", "GPU, sixteen launches", "^", COLORS["methods"]),
            ("mps_bmm", "GPU, one launch", "s", COLORS["workload"]),
        ],
    ),
]


def main():
    with open(HERE / "medians.csv", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["run"] in {"1", "2", "3"}]
    apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(6.2, 2.75), sharey=True)
    fig.subplots_adjust(left=0.085, right=0.985, top=0.9, bottom=0.16, wspace=0.08)
    for ax, (title, arms), tag in zip(axes, PANELS, ("(a)", "(b)")):
        for arm, label, marker, color in arms:
            for run in ("1", "2", "3"):
                pts = sorted(
                    (int(r["n"]), float(r["median"]))
                    for r in rows
                    if r["arm"] == arm and r["run"] == run
                )
                ax.plot(
                    [p[0] for p in pts],
                    [p[1] for p in pts],
                    color=color,
                    lw=0.8,
                    marker=marker,
                    ms=2.2,
                    alpha=0.8,
                    label=label if run == "1" else None,
                    zorder=3,
                )
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_xticks([16, 64, 256, 1024])
        ax.set_xticklabels(["16", "64", "256", "1,024"])
        ax.minorticks_off()
        ax.set_xlabel("Matrix dimension n", fontsize=FONT_SIZES["label"])
        ax.text(
            0.0,
            1.04,
            f"{tag} {title}",
            transform=ax.transAxes,
            fontsize=FONT_SIZES["title"],
            fontweight="bold",
            color=COLORS["ink"],
        )
        ax.legend(
            loc="upper left",
            frameon=False,
            fontsize=FONT_SIZES["note"],
            handlelength=1.6,
        )
        ax.tick_params(
            axis="both", labelsize=FONT_SIZES["tick"], length=2.5, width=0.6, pad=2
        )
        ax.grid(True, color=COLORS["row"], linewidth=0.4, zorder=0)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
    axes[0].set_ylabel("Median time (s)", fontsize=FONT_SIZES["label"])
    save_figure_bundle(fig, HERE / "figure")
    save_figure_bundle(
        fig,
        ROOT / "book/contents/chapters/02-pressures/images/fig-ch02-offload-break-even",
    )


if __name__ == "__main__":
    main()
