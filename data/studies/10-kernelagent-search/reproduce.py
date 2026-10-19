#!/usr/bin/env python3
"""Recompute the published timing series. No network or GPU required."""
import csv
import json
from pathlib import Path
import re
import sys
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))
from book._python.plots import COLORS, apply_style, save_figure_bundle
from evidence_bundle import verify_sources, record_build

LABELS = {
    "04": "Matrix–vector",
    "36": "RMSNorm",
    "43": "MaxPool 3D",
    "77": "Transposed conv. 3D",
    "82": "Depthwise conv. 2D",
}


def main():
    manifest = verify_sources(HERE)
    rows, summaries = [], []
    for problem in sorted((HERE / "raw").iterdir()):
        if not problem.is_dir():
            continue
        records = sorted(
            problem.glob("optimization_trace/round_*/benchmark_results.json")
        )
        assert len(records) == 8
        best = float("inf")
        parameters = None
        group = []
        for f in records:
            j = json.loads(f.read_text())
            params = {k: j[k] for k in ("size", "device", "dtype", "warmup", "repeat")}
            parameters = parameters or params
            assert params == parameters
            assert len(j["kernels"]) == 1
            value = next(iter(j["kernels"].values()))
            latency = value["time_ms"]
            assert np.isfinite(latency) and latency > 0
            best = min(best, latency)
            row = {
                "problem": problem.name,
                "label": LABELS[problem.name[:2]],
                "round": int(f.parent.name.split("_")[1]),
                "time_ms": latency,
                "best_retained_ms": best,
                "source_path": str(f.relative_to(HERE)),
                "reported_worker_path": value["path"],
                **params,
            }
            group.append(row)
        assert [r["round"] for r in group] == list(range(1, 9))
        for r in group:
            r["best_relative_to_round_1"] = r["best_retained_ms"] / group[0]["time_ms"]
        rows.extend(group)
        best_row = min(group, key=lambda r: r["time_ms"])
        summaries.append(
            {
                "problem": problem.name,
                "label": group[0]["label"],
                "first_ms": group[0]["time_ms"],
                "best_ms": best_row["time_ms"],
                "best_round": best_row["round"],
                "first_over_best": group[0]["time_ms"] / best_row["time_ms"],
                "rounds_above_previous_best": sum(
                    group[i]["time_ms"] > group[i - 1]["best_retained_ms"]
                    for i in range(1, 8)
                ),
            }
        )
    assert len(rows) == 40 and len(summaries) == 5
    with (HERE / "timings.csv").open("w") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (HERE / "summary.json").write_text(json.dumps(summaries, indent=2) + "\n")
    # Keep the README cross-check separate; never substitute these narrative values.
    readme = (HERE / "raw/README.md").read_text()
    reported = re.findall(r"Best: round (\d+) — \*\*([\d.]+)ms\*\*", readme)
    assert len(reported) == 5
    disagreements = []
    for row, (rnd, value) in zip(summaries, reported):
        disagreements.append(
            {
                **row,
                "readme_best_ms": float(value),
                "readme_best_round": int(rnd),
                "relative_difference_percent": 100
                * (row["best_ms"] / float(value) - 1),
                "matches_readme_to_three_decimals": round(row["best_ms"], 3)
                == float(value),
            }
        )
    (HERE / "readme_crosscheck.json").write_text(
        json.dumps(disagreements, indent=2) + "\n"
    )
    apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.95), gridspec_kw={"wspace": 0.29})
    group = rows[:8]
    axes[0].plot(
        range(1, 9),
        [r["time_ms"] for r in group],
        "o--",
        color=COLORS["methods"],
        lw=1.1,
        ms=3,
        label="Retained candidate",
    )
    axes[0].step(
        range(1, 9),
        [r["best_retained_ms"] for r in group],
        where="post",
        color=COLORS["evidence"],
        lw=1.7,
        label="Best retained so far",
    )
    axes[0].set(
        title="(a) Matrix–vector multiplication",
        ylabel="Recorded kernel time (ms)",
        ylim=(0, 10.3),
    )
    axes[0].legend(loc="upper right", frameon=False)
    colors = ["workload", "designspace", "methods", "decision", "evidence"]
    markers = ["o", "s", "^", "D", "v"]
    for s, color, marker in zip(summaries, colors, markers):
        group = [r for r in rows if r["problem"] == s["problem"]]
        axes[1].step(
            range(1, 9),
            [r["best_relative_to_round_1"] for r in group],
            where="post",
            color=COLORS[color],
            lw=1.2,
            marker=marker,
            ms=2.8,
            label=s["label"],
        )
    axes[1].set(
        title="(b) Different tasks, different search histories",
        ylabel="Best retained time / round 1 time",
        ylim=(0, 1.13),
    )
    axes[1].legend(
        loc="upper center", bbox_to_anchor=(0.5, -0.27), ncol=2, frameon=False
    )
    for ax in axes:
        ax.set(xlabel="Optimization round", xticks=range(1, 9), xlim=(0.7, 8.3))
        ax.grid(axis="y", color=COLORS["grid"], lw=0.5)
        ax.grid(axis="x", visible=False)
        ax.spines[["top", "right"]].set_visible(False)
    fig.subplots_adjust(bottom=0.30, top=0.87)
    save_figure_bundle(fig, HERE / "figure")
    save_figure_bundle(
        fig,
        ROOT
        / "book/contents/chapters/03-lifecycle/images/fig-ch03-kernelagent-search-trajectories",
    )
    plt.close(fig)
    record_build(
        HERE,
        {
            "source_files_hash_verified": len(manifest["files"]),
            "timings": 40,
            "rounds_per_task": 8,
            "constant_reported_parameters_within_task": True,
            "readme_disagreements": [
                x["label"]
                for x in disagreements
                if not x["matches_readme_to_three_decimals"]
            ],
        },
    )
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
