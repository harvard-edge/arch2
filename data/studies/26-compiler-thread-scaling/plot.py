#!/usr/bin/env python3
"""Plot all retained IREE CPU local-task thread-scaling observations."""

from __future__ import annotations

import csv
import sys
from collections import OrderedDict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
STUDY = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "book/_python"))
from plots import COLORS, apply_style  # noqa: E402


def main() -> None:
    rows = list(
        csv.DictReader((STUDY / "extracted.csv").open(encoding="utf-8", newline=""))
    )
    groups: OrderedDict[str, list[dict[str, str]]] = OrderedDict()
    for row in rows:
        groups.setdefault(row["model_and_input"], []).append(row)
    if len(groups) != 10:
        raise ValueError(f"Expected ten complete workloads; found {len(groups)}")

    names = {
        "MiniLML12H384Uncased [int32,seqlen128] (TF)": "MiniLM-L12-H384 | int32 / TF",
        "MobileNetV3Small [fp32,imagenet] (TFLite)": "MobileNetV3Small | fp32 / TFLite",
        "MobileSSD [fp32] (TFLite)": "MobileSSD | fp32 / TFLite",
        "MobileBertSquad [fp32] (TFLite)": "MobileBertSquad | fp32 / TFLite",
        "EfficientNet [int8] (TFLite)": "EfficientNet | int8 / TFLite",
        "MobileBertSquad [int8] (TFLite)": "MobileBertSquad | int8 / TFLite",
        "PoseNet [fp32] (TFLite)": "PoseNet | fp32 / TFLite",
        "DeepLabV3 [fp32] (TFLite)": "DeepLabV3 | fp32 / TFLite",
        "MobileNetV2 [fp32,imagenet] (TFLite)": "MobileNetV2 | fp32 / TFLite",
        "PersonDetect [int8] (TFLite)": "PersonDetect | int8 / TFLite",
    }
    points = []
    for model, model_rows in groups.items():
        by_thread = {int(r["thread_count"]): r for r in model_rows}
        if set(by_thread) != {1, 4, 8}:
            raise ValueError(
                f"Incomplete thread sweep for {model}: {sorted(by_thread)}"
            )
        baseline = float(by_thread[1]["reported_mean_ms"])
        display = names.get(model)
        if not display:
            raise ValueError(
                f"Add a concise display title for retained model {model!r}"
            )
        for thread in (1, 4, 8):
            row = by_thread[thread]
            mean = float(row["reported_mean_ms"])
            stdev = float(row["reported_stdev_ms"])
            points.append(
                {
                    "source_row_id": row["source_row_id"],
                    "model_and_input": model,
                    "display_label": display,
                    "thread_count": thread,
                    "mean_latency_ms": mean,
                    "reported_stdev_ms": stdev,
                    "relative_mean_latency": mean / baseline,
                    "relative_reported_stdev": stdev / baseline,
                    "speedup_vs_one_thread": baseline / mean,
                    "speedup_per_group_count": (baseline / mean) / thread,
                }
            )

    with (STUDY / "plot_data.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(points[0]))
        w.writeheader()
        w.writerows(points)

    apply_style()
    fig, axes = plt.subplots(5, 2, sharex=True, sharey=True, figsize=(7.1, 6.4))
    x = np.array([1, 4, 8], dtype=float)
    marker_for_thread = {1: "o", 4: "s", 8: "^"}
    for ax, (model, model_rows) in zip(axes.flat, groups.items()):
        by_thread = {int(r["thread_count"]): r for r in model_rows}
        base = float(by_thread[1]["reported_mean_ms"])
        mean = np.array(
            [float(by_thread[t]["reported_mean_ms"]) / base for t in (1, 4, 8)]
        )
        sd = np.array(
            [float(by_thread[t]["reported_stdev_ms"]) / base for t in (1, 4, 8)]
        )
        ax.plot(x, mean, color=COLORS["workload"], linewidth=1.15, zorder=2)
        ax.errorbar(
            x,
            mean,
            yerr=sd,
            fmt="none",
            color=COLORS["workload"],
            linewidth=1.15,
            elinewidth=0.7,
            capsize=2.0,
            capthick=0.7,
            zorder=3,
        )
        for thread, marker in marker_for_thread.items():
            i = (1, 4, 8).index(thread)
            ax.scatter(
                [thread],
                [mean[i]],
                s=15,
                marker=marker,
                facecolor=COLORS["workload"],
                edgecolor="white",
                linewidth=0.4,
                zorder=4,
            )
        ax.set_title(names[model], loc="left", pad=2.0, fontsize=6.2, fontweight="bold")
        ax.set_xlim(0.3, 8.7)
        ax.set_ylim(0.08, 1.24)
        ax.set_xticks([1, 4, 8], labels=["1", "4", "8"])
        ax.set_yticks([0.25, 0.5, 0.75, 1.0])
        ax.grid(axis="y", color=COLORS["grid"], linewidth=0.45, zorder=0)
        ax.axhline(
            1.0, color=COLORS["muted"], linewidth=0.55, linestyle=(0, (2, 2)), zorder=1
        )
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_linewidth(0.55)
        ax.spines["bottom"].set_linewidth(0.55)
        ax.tick_params(axis="both", length=2, width=0.5, pad=1.5)

    fig.suptitle(
        "Thread scaling depends on the workload",
        fontsize=8.0,
        fontweight="bold",
        y=0.985,
    )
    fig.text(
        0.5,
        0.955,
        "IREE bot report 1559 · GCP c2-standard-16 label · Cascade Lake · LLVM-CPU local-task",
        ha="center",
        va="center",
        fontsize=5.9,
        color=COLORS["muted"],
    )
    fig.supylabel("Mean latency / same workload's 1-thread mean", fontsize=6.6, x=0.04)
    fig.supxlabel(
        "Local-task group count (benchmark thread tags: 1, 4, 8)", fontsize=6.6, y=0.045
    )
    fig.text(
        0.5,
        0.012,
        "Points: reported mean latency. Caps: reported standard deviation scaled by the 1-thread mean; not confidence intervals.",
        ha="center",
        va="bottom",
        fontsize=5.3,
        color=COLORS["muted"],
    )
    fig.subplots_adjust(
        left=0.12, right=0.985, top=0.925, bottom=0.11, wspace=0.18, hspace=0.47
    )

    fig.savefig(STUDY / "figure.svg", bbox_inches="tight")
    fig.savefig(STUDY / "figure.pdf", bbox_inches="tight")
    fig.savefig(STUDY / "figure.png", dpi=300, bbox_inches="tight")
    print("Generated:")
    for p in (
        STUDY / "plot_data.csv",
        STUDY / "figure.svg",
        STUDY / "figure.pdf",
        STUDY / "figure.png",
    ):
        print(f"  {p}")


if __name__ == "__main__":
    main()
