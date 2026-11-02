#!/usr/bin/env python3
"""Plot Hameed et al. staged H.264 energy gains and base-energy breakdown for chapter 2.

Inputs: chapter2-hameed-staged-energy.csv, chapter2-hameed-component-breakdown.csv.
Only printed values are used; chart-read rows in the CSV are cross-checks.
Output: book/contents/chapters/02-pressures/images/fig-ch02-specialization-energy.*
"""
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from book._python.plots import (
    COLORS,
    FONT_SIZES,
    apply_style,
    save_figure_bundle,
)  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = ROOT / "book/contents/chapters/02-pressures/images/fig-ch02-specialization-energy"
STAGES = [
    ("plus_SIMD_VLIW", "+ SIMD/VLIW"),
    ("plus_op_fusion", "+ operation fusion"),
    ("plus_magic", "+ custom instructions"),
    ("ASIC", "ASIC"),
]
COMPONENTS = [
    ("IF", "Instruction fetch"),
    ("Pipeline", "Pipeline registers"),
    ("D-cache", "Data cache"),
    ("Control", "Control"),
    ("RegFile", "Register file"),
    ("FU", "Functional units"),
]


def rows(name):
    with open(HERE / name, encoding="utf-8") as fh:
        return list(csv.DictReader(l for l in fh if not l.startswith("#")))


def main():
    staged = rows("chapter2-hameed-staged-energy.csv")
    comp = rows("chapter2-hameed-component-breakdown.csv")
    gains = [1.0]
    for key, _ in STAGES:
        gains.append(
            next(
                float(r["value"])
                for r in staged
                if r["optimization_stage"] == key
                and r["h264_substage_or_total"] == "Total"
                and r["metric"] == "energy_efficiency_ratio_vs_base"
                and r["evidence_class"] == "transcribed"
            )
        )
    totals = {}
    for r in comp:
        if (
            r["optimization_stage"] == "base_RISC_CMP"
            and r["metric"] == "energy_mJ_per_frame"
            and r["evidence_class"] == "transcribed"
            and r["component"] != "Total"
            and r["h264_substage"] != "Total"
        ):
            totals[r["component"]] = totals.get(r["component"], 0.0) + float(r["value"])
    whole = sum(totals.values())
    shares = [100 * totals[c] / whole for c, _ in COMPONENTS]

    apply_style()
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(6.2, 2.25), gridspec_kw={"width_ratios": [1, 1]}
    )
    fig.subplots_adjust(left=0.135, right=0.97, top=0.9, bottom=0.17, wspace=0.62)
    labels = ["Base processors"] + [s[1] for s in STAGES]
    y = range(len(labels))
    fills = [COLORS["workload_tint"]] * 4 + [COLORS["designspace_tint"]]
    edges = [COLORS["workload"]] * 4 + [COLORS["designspace"]]
    ax1.barh(
        list(y),
        [g - 0.8 for g in gains],
        left=0.8,
        height=0.6,
        color=fills,
        edgecolor=edges,
        linewidth=0.9,
        zorder=2,
    )
    for yi, g in zip(y, gains):
        ax1.text(
            g * 1.25,
            yi,
            f"{g:.0f}×",
            va="center",
            fontsize=FONT_SIZES["annotation"],
            fontweight="bold",
            color=COLORS["ink"],
        )
    ax1.set_xscale("log")
    ax1.set_xlim(0.8, 3000)
    ax1.set_xticks([1, 10, 100, 1000])
    ax1.set_xticklabels(["1×", "10×", "100×", "1,000×"])
    ax1.minorticks_off()
    ax1.set_yticks(list(y))
    ax1.set_yticklabels(labels, fontsize=FONT_SIZES["tick"])
    ax1.invert_yaxis()
    ax1.set_xlabel(
        "Energy efficiency vs. base processors", fontsize=FONT_SIZES["label"]
    )

    y2 = range(len(COMPONENTS))
    colors = [COLORS["constraints_tint"]] * 5 + [COLORS["evidence_tint"]]
    edges2 = [COLORS["constraints"]] * 5 + [COLORS["evidence"]]
    ax2.barh(
        list(y2),
        shares,
        height=0.6,
        color=colors,
        edgecolor=edges2,
        linewidth=0.9,
        zorder=2,
    )
    for yi, s in zip(y2, shares):
        ax2.text(
            s + 0.8,
            yi,
            f"{s:.1f}%",
            va="center",
            fontsize=FONT_SIZES["annotation"],
            fontweight="bold",
            color=COLORS["ink"],
        )
    ax2.set_xlim(0, 44)
    ax2.set_yticks(list(y2))
    ax2.set_yticklabels([c[1] for c in COMPONENTS], fontsize=FONT_SIZES["tick"])
    ax2.invert_yaxis()
    ax2.set_xlabel("Share of base-processor energy (%)", fontsize=FONT_SIZES["label"])

    for ax, tag, x in ((ax1, "(a)", -0.46), (ax2, "(b)", -0.46)):
        ax.text(
            x,
            1.04,
            tag,
            transform=ax.transAxes,
            fontsize=7,
            fontweight="bold",
            color=COLORS["ink"],
        )
        ax.tick_params(
            axis="both", labelsize=FONT_SIZES["tick"], length=2.5, width=0.6, pad=2
        )
        ax.grid(True, axis="x", color=COLORS["row"], linewidth=0.4, zorder=0)
        for spine in ("top", "right", "left"):
            ax.spines[spine].set_visible(False)
    save_figure_bundle(fig, OUT)
    print(
        "wrote",
        OUT,
        "shares",
        dict(zip([c for c, _ in COMPONENTS], [round(s, 1) for s in shares])),
        "total",
        whole,
    )


if __name__ == "__main__":
    main()
