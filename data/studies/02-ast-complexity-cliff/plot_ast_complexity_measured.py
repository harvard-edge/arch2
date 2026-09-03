#!/usr/bin/env python3
"""Plot the measured, pinned-repository RTL complexity candidate."""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


STUDY_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style  # noqa: E402


apply_style()

INPUT_CSV = STUDY_DIR / "hardware_ast_complexity_measured.csv"
DEFAULT_OUTPUT_BASE = STUDY_DIR / "fig_ast_complexity_measured"

BENCHMARK = "AI benchmark reference RTL"
PRODUCTION = "Production-oriented open RTL"


def resolve_output_base() -> Path:
    """Where to write the figure twins.

    The chapter needs this figure under its own label, and the study package
    needs it under the study name. One generator serves both, so the figure
    the reader sees is always the one this script produced.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-base",
        type=Path,
        default=DEFAULT_OUTPUT_BASE,
        help="path stem for the .svg/.pdf/.png twins",
    )
    return parser.parse_args().output_base


def read_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    with INPUT_CSV.open(encoding="utf-8") as handle:
        for row in csv.DictReader(l for l in handle if not l.startswith("#")):
            records.append(
                {
                    "category": row["corpus_category"],
                    "dataset": row["dataset_name"],
                    "nodes": int(row["concrete_syntax_nodes"]),
                    "hierarchy_depth": int(row["internal_hierarchy_depth"]),
                }
            )
    return records


def ecdf(values: list[int]) -> tuple[np.ndarray, np.ndarray]:
    x = np.sort(np.asarray(values, dtype=float))
    y = np.arange(1, len(x) + 1, dtype=float) / len(x)
    return x, y


def declare_font_stack(svg_path: Path) -> None:
    text = svg_path.read_text(encoding="utf-8")
    if '<style type="text/css">' not in text:
        text = text.replace(
            "<defs>",
            '<defs>\n  <style type="text/css">*{font-family: Arial, Helvetica, sans-serif;}</style>',
            1,
        )
    text = "\n".join(line.rstrip() for line in text.splitlines()) + "\n"
    svg_path.write_text(text, encoding="utf-8")


def main() -> int:
    records = read_records()
    benchmark_nodes = [
        int(record["nodes"]) for record in records if record["category"] == BENCHMARK
    ]
    production_nodes = [
        int(record["nodes"]) for record in records if record["category"] == PRODUCTION
    ]
    benchmark_median = statistics.median(benchmark_nodes)
    production_median = statistics.median(production_nodes)
    ratio = production_median / benchmark_median

    fig, (ax1, ax2) = plt.subplots(
        1,
        2,
        figsize=(7.4, 3.25),
        gridspec_kw={"width_ratios": [1.08, 0.92]},
    )
    fig.subplots_adjust(left=0.075, right=0.975, top=0.88, bottom=0.19, wspace=0.36)

    bench_x, bench_y = ecdf(benchmark_nodes)
    prod_x, prod_y = ecdf(production_nodes)
    ax1.plot(
        bench_x,
        bench_y,
        color=COLORS["methods"],
        linewidth=1.9,
        label=f"Benchmark reference RTL (N={len(benchmark_nodes):,})",
        zorder=4,
    )
    ax1.plot(
        prod_x,
        prod_y,
        color=COLORS["designspace"],
        linewidth=1.9,
        label=f"Production-oriented RTL (N={len(production_nodes):,})",
        zorder=4,
    )
    ax1.axvspan(
        benchmark_median,
        production_median,
        color=COLORS["note_fill"],
        alpha=0.65,
        zorder=0,
    )
    ax1.axvline(benchmark_median, color=COLORS["methods_ink"], linewidth=0.8)
    ax1.axvline(production_median, color=COLORS["designspace_ink"], linewidth=0.8)
    ax1.text(
        np.sqrt(benchmark_median * production_median),
        0.43,
        f"{ratio:.1f}× module-weighted median gap\n"
        f"{benchmark_median:,.0f} → {production_median:,.0f} nodes",
        ha="center",
        va="center",
        fontsize=5.6,
        color=COLORS["ink"],
        bbox={
            "boxstyle": "round,pad=0.25",
            "facecolor": "white",
            "edgecolor": COLORS["designspace_ink"],
            "alpha": 0.94,
            "linewidth": 0.6,
        },
        zorder=6,
    )
    ax1.set_xscale("log")
    ax1.set_xlim(8, max(production_nodes) * 1.15)
    ax1.set_ylim(0, 1.02)
    ax1.set_xlabel("Concrete syntax nodes per module (log scale)")
    ax1.set_ylabel("Cumulative fraction of modules")
    ax1.set_title(
        "(a) Measured Module Syntax Distributions", loc="left", fontweight="bold"
    )
    ax1.grid(True, which="major", color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax1.legend(loc="lower right", frameon=True, framealpha=0.96)

    dataset_order = [
        "VerilogEval",
        "RTLLM",
        "VeeR EL2",
        "CV32E40P",
        "BlackParrot",
        "OpenTitan",
    ]
    dataset_stats: list[tuple[str, float, int, str]] = []
    for dataset in dataset_order:
        subset = [record for record in records if record["dataset"] == dataset]
        share = (
            100.0
            * sum(int(record["hierarchy_depth"]) > 1 for record in subset)
            / len(subset)
        )
        max_depth = max(int(record["hierarchy_depth"]) for record in subset)
        category = str(subset[0]["category"])
        dataset_stats.append((dataset, share, max_depth, category))

    y = np.arange(len(dataset_stats))
    colors = [
        COLORS["methods"] if category == BENCHMARK else COLORS["designspace"]
        for _, _, _, category in dataset_stats
    ]
    bars = ax2.barh(
        y,
        [share for _, share, _, _ in dataset_stats],
        color=colors,
        height=0.58,
        edgecolor="white",
        linewidth=0.5,
        zorder=3,
    )
    for bar, (_, share, max_depth, _) in zip(bars, dataset_stats):
        ax2.text(
            share + 1.7,
            bar.get_y() + bar.get_height() / 2,
            f"{share:.0f}%  (max depth {max_depth})",
            va="center",
            ha="left",
            fontsize=5.5,
            color=COLORS["ink"],
        )
    ax2.axhline(1.5, color=COLORS["grid"], linewidth=0.9)
    ax2.set_yticks(y)
    ax2.set_yticklabels([name for name, _, _, _ in dataset_stats])
    ax2.invert_yaxis()
    ax2.set_xlim(0, 110)
    ax2.set_xlabel("Modules reaching a uniquely defined local child (%)")
    ax2.set_title("(b) Repository-Internal Hierarchy", loc="left", fontweight="bold")
    ax2.grid(axis="x", color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax2.legend(
        handles=[
            Patch(color=COLORS["methods"], label="Benchmark reference RTL"),
            Patch(color=COLORS["designspace"], label="Production-oriented RTL"),
        ],
        loc="upper right",
        frameon=True,
        framealpha=0.96,
    )

    output_base = resolve_output_base()
    for suffix, kwargs in (
        ("svg", {}),
        ("pdf", {}),
        ("png", {"dpi": 300}),
    ):
        path = output_base.with_suffix(f".{suffix}")
        fig.savefig(path, bbox_inches="tight", **kwargs)
        print(f"generated: {path}")
    plt.close(fig)
    declare_font_stack(output_base.with_suffix(".svg"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
