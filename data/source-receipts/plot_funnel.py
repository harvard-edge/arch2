import csv
import sys
from pathlib import Path
import matplotlib.pyplot as plt

# Connect parent repo path to import book._python.plots
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style

apply_style()


def plot_funnel(csv_path=None, out_path=None):
    if csv_path is None:
        csv_path = (
            REPO_ROOT
            / "data"
            / "source-receipts"
            / "chapter4-synthesis-verification-funnel.csv"
        )
    if out_path is None:
        out_path = (
            REPO_ROOT / "book" / "images" / "fig-synthesis-verification-funnel.svg"
        )

    names = []
    counts = []
    pcts = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            names.append(row["Name"])
            counts.append(int(row["Count"]))
            pcts.append(float(row["Percentage"]))

    fig, ax = plt.subplots(figsize=(6.4, 3.8))

    bar_colors = [
        COLORS["blue"],
        COLORS["orange"],
        COLORS["purple"],
        COLORS["magenta"],
        COLORS["red"],
    ]

    bars = ax.bar(names, counts, color=bar_colors, width=0.55, zorder=3)
    ax.set_yscale("log")
    ax.set_ylim(1, 20000)
    ax.set_ylabel(
        "Candidate Artifact Count (Log Scale)", fontsize=7, color=COLORS["ink"]
    )
    ax.set_title(
        "Hardware Code Synthesis & Verification Funnel (The Scissors Gap)",
        fontsize=8,
        fontweight="bold",
        color=COLORS["ink"],
    )

    # Annotate counts and percentages above bars
    for bar, count, pct in zip(bars, counts, pcts):
        yval = bar.get_height()
        label_text = f"{count:,}\n({pct:.2f}%)" if pct < 100 else f"{count:,}\n(100%)"
        ax.annotate(
            label_text,
            (bar.get_x() + bar.get_width() / 2, yval),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=6.2,
            fontweight="bold",
            color=COLORS["ink"],
        )

    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, fontsize=6.5, rotation=15, ha="right")
    ax.tick_params(axis="both", labelsize=6.0, length=2.5, width=0.6)
    ax.grid(True, which="both", color=COLORS["grid"], linewidth=0.5, zorder=0)

    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    print(f"Funnel plot saved to '{out_path}'")


if __name__ == "__main__":
    plot_funnel()
