import csv
import sys
from pathlib import Path
from collections import defaultdict
import matplotlib.pyplot as plt

# Connect parent repo path to import book._python.plots
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style

apply_style()


def main():
    trend_csv = (
        REPO_ROOT
        / "data"
        / "source-receipts"
        / "chapter1-conference-paradigm-shifts.csv"
    )
    out_plot = REPO_ROOT / "book" / "images" / "fig-conference-paradigm-shifts.svg"

    yearly_data = defaultdict(dict)

    with open(trend_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yr = int(row["Year"])
            cat = row["Category"]
            pct = float(row["SharePercentage"])
            yearly_data[yr][cat] = pct

    years = sorted(yearly_data.keys())
    cats = [
        "Domain Accelerators & AI",
        "Memory Hierarchy",
        "Multicore & Coherence",
        "Software/Compilers",
        "Verification/Tools",
        "CPU Microarchitecture",
    ]

    # Build continuous arrays per category
    shares_per_cat = []
    for cat in cats:
        cat_shares = [yearly_data[yr].get(cat, 0.0) for yr in years]
        shares_per_cat.append(cat_shares)

    # Apply a 3-year rolling average to smooth year-to-year noise
    smoothed_shares = []
    for cat_shares in shares_per_cat:
        smoothed = []
        for i in range(len(cat_shares)):
            start = max(0, i - 1)
            end = min(len(cat_shares), i + 2)
            window = cat_shares[start:end]
            smoothed.append(sum(window) / len(window))
        smoothed_shares.append(smoothed)

    # Normalize smoothed shares so sum = 100% per year
    for yr_idx in range(len(years)):
        tot = sum(smoothed_shares[c_idx][yr_idx] for c_idx in range(len(cats)))
        if tot > 0:
            for c_idx in range(len(cats)):
                smoothed_shares[c_idx][yr_idx] = (
                    smoothed_shares[c_idx][yr_idx] / tot
                ) * 100.0

    fig, ax = plt.subplots(figsize=(6.4, 3.8))

    colors = [
        COLORS["purple"],
        COLORS["blue"],
        COLORS["green"],
        COLORS["orange"],
        COLORS["red"],
        "#7A8B99",
    ]

    ax.stackplot(
        years, smoothed_shares, labels=cats, colors=colors, alpha=0.85, zorder=3
    )

    ax.set_title(
        "44-Year Paradigm Shift in Computer Architecture (1979–2026)",
        fontsize=8,
        fontweight="bold",
        color=COLORS["ink"],
    )
    ax.set_ylabel(
        "Percentage Share of Publications (%)", fontsize=7, color=COLORS["ink"]
    )
    ax.set_xlabel(
        "Publication Year (Scraped from 8,979 ISCA, MICRO, ASPLOS, HPCA Papers)",
        fontsize=6.5,
        color=COLORS["ink"],
    )
    ax.set_xlim(1980, 2026)
    ax.set_ylim(0, 100)

    # Add vertical line for ~2016 crossover
    ax.axvline(2016, color=COLORS["ink"], linestyle="--", linewidth=1.2, zorder=4)
    ax.text(
        2016.3,
        92,
        "AI/Accelerators Overtake CPU (~2016)",
        fontsize=6.2,
        fontweight="bold",
        color=COLORS["ink"],
    )

    ax.tick_params(axis="both", labelsize=6.0, length=2.5, width=0.6)
    ax.grid(True, color=COLORS["grid"], linewidth=0.5, zorder=0)

    # Place legend inside top left
    ax.legend(
        loc="lower left",
        fontsize=5.8,
        framealpha=0.9,
        facecolor="white",
        edgecolor=COLORS["grid"],
    )

    plt.tight_layout()
    plt.savefig(out_plot, dpi=300, bbox_inches="tight")
    print(f"Continuous 47-year conference paradigm shift plot saved to '{out_plot}'")


if __name__ == "__main__":
    main()
