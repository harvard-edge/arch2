#!/usr/bin/env python3
"""Recompute the published timing series. No network or GPU required."""
import collections
import csv
import difflib
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

ATTEMPT = re.compile(r"^#### Attempt \d+ \(Worker \d+\) \[(.*?)\]\s*$", re.M)
PERFORMANCE = re.compile(r"\*\*Performance\*\*:\s*([\d.]+)ms → ([\d.]+)ms")
TOKEN = re.compile(r"\w+|[^\s\w]")


def final_kernel_match(problem):
    """Find the round whose kept kernel the source's final kernel matches.

    Token comparison ignores reformatting. The lowest recorded time need not
    belong to this kernel, so the two are reported separately.
    """
    final = TOKEN.findall(
        (problem / "optimized_kernel_beam_search.py").read_text(encoding="utf-8")
    )
    scores = {}
    for round_ in range(1, 9):
        path = problem / f"optimization_trace/round_{round_}/kernel.py"
        kernel = TOKEN.findall(path.read_text(encoding="utf-8"))
        scores[round_] = difflib.SequenceMatcher(
            None, kernel, final, autojunk=False
        ).ratio()
    return max(scores, key=scores.get), max(scores.values())


def read_attempts(problem, label, records):
    """Recover each round's four attempts from the history in later prompts.

    A round's attempts first appear in the prompt of the next round, so Round 8
    has none. The prompts also carry one older attempt forward, hence the count
    of first appearances. An attempt that failed verification has no timing.
    """
    rows = []
    seen = collections.Counter()
    for prompt_round in range(2, 9):
        path = problem / f"optimization_trace/round_{prompt_round}/opt_prompt.txt"
        text = path.read_text(encoding="utf-8")
        heads = list(ATTEMPT.finditer(text))
        found = collections.Counter()
        for head, after in zip(heads, heads[1:] + [None]):
            body = text[head.end() : after.start() if after else len(text)]
            timing = PERFORMANCE.search(body.split("#### Round", 1)[0])
            found[(head.group(1), *(timing.groups() if timing else ("", "")))] += 1
        fresh = found - seen
        assert sum(fresh.values()) == 4, (path, fresh)
        seen = found
        for (status, baseline, time_ms), count in fresh.items():
            rows.extend(
                {
                    "problem": problem.name,
                    "label": label,
                    "round": prompt_round - 1,
                    "status": status,
                    "baseline_ms": baseline,
                    "time_ms": time_ms,
                    "source_path": str(path.relative_to(HERE)),
                }
                for _ in range(count)
            )
    for round_ in range(1, 8):
        times = [
            float(a["time_ms"])
            for a in rows
            if a["round"] == round_ and a["time_ms"]
        ]
        # History text keeps four decimals, so compare at that precision.
        assert round(records[round_ - 1], 4) == min(times), (problem.name, round_)
    return rows


def main():
    manifest = verify_sources(HERE)
    rows, summaries, attempts = [], [], []
    for problem in sorted((HERE / "raw").iterdir()):
        if not problem.is_dir():
            continue
        records = sorted(
            problem.glob("optimization_trace/round_*/benchmark_results.json")
        )
        assert len(records) == 8
        lowest = float("inf")
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
            lowest = min(lowest, latency)
            row = {
                "problem": problem.name,
                "label": LABELS[problem.name[:2]],
                "round": int(f.parent.name.split("_")[1]),
                "time_ms": latency,
                "lowest_recorded_ms": lowest,
                "source_path": str(f.relative_to(HERE)),
                "reported_worker_path": value["path"],
                **params,
            }
            group.append(row)
        assert [r["round"] for r in group] == list(range(1, 9))
        for r in group:
            r["lowest_relative_to_round_1"] = r["lowest_recorded_ms"] / group[0]["time_ms"]
        rows.extend(group)
        task_attempts = read_attempts(
            problem, group[0]["label"], [r["time_ms"] for r in group]
        )
        attempts.extend(task_attempts)
        starts = [
            float(a["baseline_ms"])
            for a in task_attempts
            if a["round"] == 1 and a["baseline_ms"]
        ]
        best_row = min(group, key=lambda r: r["time_ms"])
        final_round, final_similarity = final_kernel_match(problem)
        summaries.append(
            {
                "problem": problem.name,
                "label": group[0]["label"],
                "first_ms": group[0]["time_ms"],
                "best_ms": best_row["time_ms"],
                "best_round": best_row["round"],
                "first_over_best": group[0]["time_ms"] / best_row["time_ms"],
                "rounds_above_previous_best": sum(
                    group[i]["time_ms"] > group[i - 1]["lowest_recorded_ms"]
                    for i in range(1, 8)
                ),
                "round_1_starting_times_ms": starts,
                "round_1_start_spread": max(starts) / min(starts),
                "final_kernel_round": final_round,
                "final_kernel_token_similarity": final_similarity,
                "final_kernel_round_ms": group[final_round - 1]["time_ms"],
            }
        )
    assert len(rows) == 40 and len(summaries) == 5
    with (HERE / "timings.csv").open("w") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (HERE / "attempts.csv").open("w") as f:
        writer = csv.DictWriter(f, fieldnames=list(attempts[0]))
        writer.writeheader()
        writer.writerows(attempts)
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
        label="Round's best kernel",
    )
    axes[0].step(
        range(1, 9),
        [r["lowest_recorded_ms"] for r in group],
        where="post",
        color=COLORS["evidence"],
        lw=1.7,
        label="Lowest recorded so far",
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
            [r["lowest_relative_to_round_1"] for r in group],
            where="post",
            color=COLORS[color],
            lw=1.2,
            marker=marker,
            ms=2.8,
            label=s["label"],
        )
    axes[1].set(
        title="(b) Different tasks, different search histories",
        ylabel="Lowest recorded time / Round 1 time",
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
            "history_attempts": len(attempts),
            "history_attempts_without_timing": sum(
                not a["time_ms"] for a in attempts
            ),
            "rounds_where_plotted_record_is_fastest_timed_attempt": len(
                {(a["problem"], a["round"]) for a in attempts}
            ),
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
