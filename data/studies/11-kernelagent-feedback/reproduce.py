#!/usr/bin/env python3
"""Compare first retained and fastest retained candidates using paired records."""
import csv
import json
from pathlib import Path
import re
import sys
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


def readme_timing_check():
    """Compare the upstream README's running-best table with the round records."""
    readme = (HERE / "raw" / "README.md").read_text()
    out = []
    for d in sorted(p for p in (HERE / "raw").iterdir() if p.is_dir()):
        section = re.search(
            rf"^### {d.name[:2]}\\_.*?^\| Best \(ms\) \|(.*?)\|$", readme, re.S | re.M
        )
        reported = [float(v.strip(" *")) for v in section.group(1).split("|")]
        assert len(reported) == 8
        best = float("inf")
        for n, value in enumerate(reported, start=1):
            f = d / f"optimization_trace/round_{n}/benchmark_results.json"
            record = next(iter(json.loads(f.read_text())["kernels"].values()))
            best = min(best, record["time_ms"])
            out.append(
                {
                    "problem": d.name,
                    "label": LABELS[d.name[:2]],
                    "round": n,
                    "round_time_ms": record["time_ms"],
                    "record_running_best_ms": best,
                    "readme_running_best_ms": value,
                    "readme_over_record": value / best,
                    "warmup": json.loads(f.read_text())["warmup"],
                    "repeat": json.loads(f.read_text())["repeat"],
                }
            )
    with (HERE / "readme_timing_check.csv").open("w") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    return out


def main():
    manifest = verify_sources(HERE)
    rows = []
    for d in sorted((HERE / "raw").iterdir()):
        if not d.is_dir():
            continue
        times = []
        for f in sorted(d.glob("optimization_trace/*/benchmark_results.json")):
            j = json.loads(f.read_text())
            times.append((next(iter(j["kernels"].values()))["time_ms"], f.parent))
        assert len(times) == 8
        best = min(times)
        for state, (time, folder) in [("first", times[0]), ("best", best)]:
            j = json.loads((folder / "optimized_ncu_metrics.json").read_text())
            assert len(j["metrics"]) == 1, "Do not aggregate utilization across kernels"
            name, metrics = next(iter(j["metrics"].items()))
            assert (
                f"def {name}(" in (folder / "kernel.py").read_text()
            ), "Kernel name association differs"
            rows.append(
                {
                    "problem": d.name,
                    "label": LABELS[d.name[:2]],
                    "state": state,
                    "round": int(folder.name.split("_")[1]),
                    "time_ms": time,
                    "relative_time": time / times[0][0],
                    "occupancy_pct": metrics[
                        "sm__warps_active.avg.pct_of_peak_sustained_active"
                    ],
                    "dram_throughput_pct": metrics[
                        "dram__throughput.avg.pct_of_peak_sustained_elapsed"
                    ],
                    "profiled_kernel": name,
                    "ncu_version": j["metadata"]["ncu_version"],
                    "profile_source": str(
                        (folder / "optimized_ncu_metrics.json").relative_to(HERE)
                    ),
                    "timing_source": str(
                        (folder / "benchmark_results.json").relative_to(HERE)
                    ),
                }
            )
    with (HERE / "paired_metrics.csv").open("w") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    readme_check = readme_timing_check()
    tasks = len(rows) // 2
    apply_style()
    fig, axes = plt.subplots(1, 3, figsize=(6.8, 2.55), sharey=True)
    specs = [
        ("relative_time", "(a) Kernel time", "Time / round 1 time", 1.18),
        (
            "occupancy_pct",
            "(b) Achieved occupancy",
            "Percent of peak active warps",
            118,
        ),
        (
            "dram_throughput_pct",
            "(c) DRAM throughput",
            "Percent of peak sustained",
            118,
        ),
    ]
    for ax, (key, title, label, upper) in zip(axes, specs):
        for i in range(tasks):
            a, b = rows[2 * i : 2 * i + 2]
            x0, x1 = a[key], b[key]
            ax.plot([x0, x1], [i, i], color=COLORS["muted"], lw=1, zorder=1)
            ax.scatter(
                [x0],
                [i],
                marker="o",
                facecolor="white",
                edgecolor=COLORS["workload"],
                s=22,
                linewidth=1,
                zorder=3,
                label="Round 1" if i == 0 else None,
            )
            ax.scatter(
                [x1],
                [i],
                marker="s",
                color=COLORS["evidence"],
                s=17,
                zorder=4,
                label="Fastest retained round" if i == 0 else None,
            )
        ax.set(
            xlim=(-0.04 if key == "relative_time" else -5, upper),
            title=title,
            xlabel=label,
            ylim=(4.6, -0.6),
        )
        ax.grid(axis="x", color=COLORS["grid"], lw=0.5)
        ax.grid(axis="y", color=COLORS["row"], lw=0.5)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
    axes[0].set_yticks(range(tasks), [rows[2 * i]["label"] for i in range(tasks)])
    axes[0].set_xticks([0, 0.25, 0.5, 0.75, 1])
    for ax in axes[1:]:
        ax.set_xticks([0, 25, 50, 75, 100])
    fig.legend(
        *axes[0].get_legend_handles_labels(), loc="lower center", ncol=2, frameon=False
    )
    fig.subplots_adjust(left=0.16, right=0.99, bottom=0.27, top=0.85, wspace=0.20)
    save_figure_bundle(fig, HERE / "figure")
    save_figure_bundle(
        fig,
        ROOT
        / "book/contents/chapters/07-feedback/images/fig-ch07-kernelagent-ncu-counterfactual",
    )
    plt.close(fig)
    record_build(
        HERE,
        {
            "source_files_hash_verified": len(manifest["files"]),
            "paired_candidates": tasks,
            "readme_over_record_range": {
                r["label"]: [
                    round(min(x["readme_over_record"] for x in readme_check if x["label"] == r["label"]), 4),
                    round(max(x["readme_over_record"] for x in readme_check if x["label"] == r["label"]), 4),
                ]
                for r in rows
            },
            "single_kernel_per_profile": True,
            "profiled_kernel_name_found_in_associated_source": True,
            "candidate_selection": "Minimum timing across all eight retained rounds; first retained round as reference",
        },
    )
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
