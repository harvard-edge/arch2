"""Render the Chapter 3 constructed checking-cost example, preserving its data."""

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "book" / "_python"))
from plots import COLORS, apply_style


def main():
    source = Path(__file__).with_name("ch3_data.csv")
    with source.open() as stream:
        rows = list(csv.DictReader(line for line in stream if not line.startswith("#")))
    apply_style()
    fig, ax = plt.subplots(figsize=(6.5, 4.1))
    for stage, label, marker, color in (
        ("Lint", "Linting", "o", COLORS["muted"]),
        ("Sim", "RTL simulation", "s", COLORS["evidence"]),
        ("PnR", "Physical place-and-route", "^", COLORS["evidence_ink"]),
    ):
        series = [row for row in rows if row["ci_stage"] == stage]
        ax.scatter(
            [float(row["pr_complexity_loc"]) for row in series],
            [float(row["execution_time_minutes"]) for row in series],
            color=color,
            marker=marker,
            s=32,
            label=label,
            zorder=3,
        )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(8, 8000)
    ax.set_ylim(1.5, 1200)
    ax.set_xlabel("Changed lines of code (log scale)")
    ax.set_ylabel("Assumed execution time (minutes, log scale)")
    ax.set_title(
        "Constructed example: illustrative times, not measurements", loc="left"
    )
    ax.grid(True, which="major", color=COLORS["grid"], linewidth=0.5)
    ax.legend(loc="upper left", frameon=True, facecolor="white", edgecolor="none")
    fig.tight_layout()
    output = REPO_ROOT / "book/contents/chapters/03-lifecycle/images/plot_ch3"
    for extension in ("svg", "pdf", "png"):
        target = output.with_suffix(f".{extension}")
        fig.savefig(target, dpi=300, bbox_inches="tight")
        print(target)
    plt.close(fig)


if __name__ == "__main__":
    main()
