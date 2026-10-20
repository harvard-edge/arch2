#!/usr/bin/env python3
"""Plot source-interval coverage and syntax paths for the matched pair set."""
from __future__ import annotations
import csv, sys
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from book._python.plots import COLORS, apply_style, clean_spines, save_figure_bundle

PAIR_INPUT = HERE / "derived" / "pairs.csv"
OUTPUT = HERE / "figures" / "fig-representation-source-access"
REPOS = ["VerilogEval", "RTLLM", "BaseJump STL", "SERV", "Ibex", "PicoRV32"]
DISPLAY = {
    "VerilogEval": "VerilogEval",
    "RTLLM": "RTLLM",
    "BaseJump STL": "BaseJump",
    "SERV": "SERV",
    "Ibex": "Ibex",
    "PicoRV32": "PicoRV32",
}
STYLES = {
    "VerilogEval": ("solid", "o", "benchmark"),
    "RTLLM": ("dashed", "s", "benchmark"),
    "BaseJump STL": ("solid", "^", "production"),
    "SERV": ("dashed", "D", "production"),
    "Ibex": ("dashdot", "v", "production"),
    "PicoRV32": ("dotted", "P", "production"),
}


def read_pairs():
    with PAIR_INPUT.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def curve(
    ax,
    pairs,
    key,
    color,
    linestyle="solid",
    label=None,
    lw=1.15,
    weights=None,
    marker=None,
):
    vals = [int(r[key]) for r in pairs]
    weights = weights or [1 / len(vals)] * len(vals)
    ordered = sorted(zip(vals, weights))
    x = []
    y = []
    cumulative = 0.0
    i = 0
    while i < len(ordered):
        threshold = ordered[i][0]
        while i < len(ordered) and ordered[i][0] == threshold:
            cumulative += ordered[i][1]
            i += 1
        x.append(threshold)
        y.append(cumulative * 100)
    ax.step(
        x,
        y,
        where="post",
        color=color,
        linestyle=linestyle,
        linewidth=lw,
        label=label,
        zorder=3,
        marker=marker,
        markevery=max(2, len(x) // 8) if marker else None,
        markersize=2.1,
    )


def format_ax(ax, xticks, xlabels, xlabel):
    ax.set_xscale("log")
    ax.set_xticks(xticks, labels=xlabels)
    ax.set_ylim(-2, 102)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_xlabel(xlabel)
    ax.grid(axis="y", color=COLORS["grid"], linewidth=0.5, zorder=0)
    clean_spines(ax)


def main():
    pairs = read_pairs()
    matched = [r for r in pairs if r["tree_path_recoverable"] == "1"]
    apply_style()
    fig, axes = plt.subplots(1, 3, figsize=(8.8, 3.45), sharey=True)
    ax1, ax2, ax3 = axes
    for repo in REPOS:
        style, marker, group = STYLES[repo]
        color = COLORS["methods"] if group == "benchmark" else COLORS["designspace"]
        repo_pairs = [r for r in matched if r["corpus"] == repo]
        curve(
            ax1,
            repo_pairs,
            "minimum_interval_tokens",
            color,
            style,
            DISPLAY[repo],
            marker=marker,
        )
        curve(
            ax3,
            repo_pairs,
            "tree_path_edges",
            color,
            style,
            DISPLAY[repo],
            marker=marker,
        )
    curve(
        ax2,
        matched,
        "minimum_interval_tokens",
        COLORS["evidence"],
        "solid",
        "Pair weighted",
        1.7,
    )
    file_sizes = {}
    for r in matched:
        file_sizes[(r["corpus"], r["source_path"])] = (
            file_sizes.get((r["corpus"], r["source_path"]), 0) + 1
        )
    file_n = len(file_sizes)
    weights = [
        1 / (file_n * file_sizes[(r["corpus"], r["source_path"])]) for r in matched
    ]
    curve(
        ax2,
        matched,
        "minimum_interval_tokens",
        COLORS["designspace"],
        "dashed",
        "Equal file weighted",
        1.7,
        weights,
    )
    format_ax(
        ax1,
        [1, 16, 256, 4096, 65536, 262144],
        ["1", "16", "256", "4k", "64k", "256k"],
        "Minimum source interval (tokens)",
    )
    format_ax(
        ax2,
        [1, 16, 256, 4096, 65536, 262144],
        ["1", "16", "256", "4k", "64k", "256k"],
        "Minimum source interval (tokens)",
    )
    format_ax(
        ax3,
        [1, 2, 4, 8, 16, 32, 64, 128],
        ["1", "2", "4", "8", "16", "32", "64", "128"],
        "Syntax path (edges)",
    )
    ax1.set_ylabel("Matched pairs covered (%)")
    ax1.set_title("Source interval by repository", pad=7)
    ax2.set_title("Pair and file weighting", pad=7)
    ax3.set_title("Syntax path by repository", pad=7)
    for ax, letter in zip(axes, ["(a)", "(b)", "(c)"]):
        ax.text(
            0.01,
            1.04,
            letter,
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontweight="bold",
            color=COLORS["muted"],
            fontsize=6.2,
        )
    repo_handles = []
    for repo in REPOS:
        style, marker, group = STYLES[repo]
        color = COLORS["methods"] if group == "benchmark" else COLORS["designspace"]
        repo_handles.append(
            Line2D(
                [0],
                [0],
                color=color,
                linestyle=style,
                marker=marker,
                markersize=2.4,
                linewidth=1.1,
                label=DISPLAY[repo],
            )
        )
    weight_handles = [
        Line2D([0], [0], color=COLORS["evidence"], lw=1.5, label="Pair weighted"),
        Line2D(
            [0],
            [0],
            color=COLORS["designspace"],
            lw=1.5,
            ls="--",
            label="Equal file weighted",
        ),
    ]
    fig.legend(
        handles=repo_handles + weight_handles,
        loc="lower center",
        ncol=4,
        frameon=False,
        bbox_to_anchor=(0.5, -0.02),
        columnspacing=1.3,
        handlelength=1.8,
        handletextpad=0.45,
    )
    fig.subplots_adjust(left=0.07, right=0.995, top=0.84, bottom=0.23, wspace=0.29)
    save_figure_bundle(
        fig, OUTPUT, formats=("svg", "pdf", "png"), dpi=300, bbox_inches="tight"
    )
    plt.close(fig)
    print(
        "\n".join(str(OUTPUT.with_suffix("." + ext)) for ext in ("svg", "pdf", "png"))
    )


if __name__ == "__main__":
    main()
