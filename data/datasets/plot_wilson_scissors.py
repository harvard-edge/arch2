"""
Wilson Research Group verification-effort and first-silicon plot (2007-2024)
---------------------------------------------------------------------------
Plots only values printed on Foster's published charts or stated in the study text, as recorded
(with a per-value source) in chapter7-wilson-verification-scissors-gap.csv:
  - mean share of project time in verification (printed means, 2010-2020);
  - first-silicon success (stated in text: 2014, 2020, 2022, 2024);
  - verification-to-design staffing ratio (printed engineer counts 2007-2020; 2022 and 2024 derived
    from the studies' stated growth rates and drawn hollow).
Markers appear only for retained values. Lines stop before 2024 because
recruitment changed from industry lists to a qualified sample provider.
Source: Foster, Functional Verification Study Survey Methodology Evolution (2026).
"""

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, FONT_SIZES, apply_style, save_figure_bundle

apply_style()

OUT = (
    REPO_ROOT
    / "book"
    / "contents"
    / "chapters"
    / "02-pressures"
    / "images"
    / "fig-ch07-wilson-verification-scissors"
)


def series(rows, key):
    return [(int(r["study_year"]), float(r[key])) for r in rows if r[key].strip()]


def main():
    csv_file = (
        REPO_ROOT
        / "data"
        / "datasets"
        / "chapter7-wilson-verification-scissors-gap.csv"
    )
    with open(csv_file, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(row for row in f if not row.startswith("#")))

    vt = series(rows, "avg_pct_project_time_in_verification")
    fs = series(rows, "first_silicon_success_pct")
    ratio = [
        (
            int(r["study_year"]),
            float(r["mean_peak_verification_engineers"])
            / float(r["mean_peak_design_engineers"]),
            r["engineers_evidence"] == "printed_data_label",
        )
        for r in rows
    ]

    fig, ax = plt.subplots(figsize=(5.0, 3.5))
    fig.subplots_adjust(left=0.11, right=0.87, top=0.76, bottom=0.15)

    ax.plot(
        [y for y, _ in vt],
        [v for _, v in vt],
        color=COLORS["purple"],
        linewidth=1.8,
        marker="o",
        markersize=4.0,
        label="Mean project time in verification (%)",
        zorder=3,
    )
    historical_fs = [(y, v) for y, v in fs if y < 2024]
    ax.plot(
        [y for y, _ in historical_fs],
        [v for _, v in historical_fs],
        color=COLORS["red"],
        linewidth=1.8,
        marker="s",
        markersize=4.0,
        label="First-silicon success (% of projects)",
        zorder=4,
    )
    for y, v in fs:
        if y >= 2024:
            ax.plot([y], [v], color=COLORS["red"], marker="s", markersize=4.0, zorder=4)

    ax.axvspan(2023, 2025, color=COLORS["row"], alpha=0.65, zorder=0)
    ax.axvline(2023, color=COLORS["muted"], linestyle=":", linewidth=0.8, zorder=1)
    ax.text(
        2024,
        76,
        "2024\nsample\nchange",
        ha="center",
        va="center",
        fontsize=FONT_SIZES["annotation"],
        color=COLORS["muted"],
        bbox=dict(
            boxstyle="round,pad=0.25", facecolor="white", edgecolor="none", alpha=0.92
        ),
        zorder=5,
    )

    sub = ax.twinx()
    sub.spines["right"].set_visible(True)
    sub.spines["right"].set_color(COLORS["ink"])
    sub.spines["right"].set_linewidth(0.7)
    historical_ratio = [(y, v) for y, v, _ in ratio if y < 2024]
    sub.plot(
        [y for y, _ in historical_ratio],
        [v for _, v in historical_ratio],
        color=COLORS["blue"],
        linewidth=1.4,
        linestyle="--",
        zorder=2,
    )
    for y, v, printed in ratio:
        sub.plot(
            [y],
            [v],
            marker="^",
            markersize=4.4,
            color=COLORS["blue"],
            markerfacecolor=COLORS["blue"] if printed else "white",
            markeredgewidth=1.0,
            zorder=3,
        )
    sub.plot(
        [],
        [],
        color=COLORS["blue"],
        linestyle="--",
        marker="^",
        markersize=4.4,
        label="Verification/design staffing ratio (right axis;\nhollow = derived from stated growth rates)",
    )
    sub.set_ylim(0.4, 1.6)
    sub.set_ylabel(
        "Staffing ratio", fontsize=FONT_SIZES["label"], color=COLORS["blue"], labelpad=3
    )
    sub.tick_params(
        axis="y", colors=COLORS["blue"], labelsize=FONT_SIZES["tick"], pad=2
    )

    last_y, last_v = fs[-1]
    ax.annotate(
        f"{last_y}: {last_v:.0f}% first-silicon success",
        xy=(last_y, last_v),
        xytext=(2011.8, 15),
        arrowprops=dict(arrowstyle="->", color=COLORS["red"], lw=0.8),
        fontsize=FONT_SIZES["annotation"],
        fontweight="bold",
        color=COLORS["red"],
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="white",
            edgecolor=COLORS["red"],
            alpha=0.92,
            lw=0.6,
        ),
        zorder=5,
    )

    ax.set_xlim(2006, 2025)
    ax.set_ylim(0, 85)
    ax.set_xticks([y for y in range(2007, 2025) if y in {r[0] for r in ratio}])
    ax.set_xlabel("Survey year")
    ax.set_ylabel("Percent")
    ax.grid(True, color=COLORS["grid"], linewidth=0.55, zorder=0)

    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = sub.get_legend_handles_labels()
    fig.legend(
        h1 + h2,
        l1 + l2,
        loc="upper left",
        bbox_to_anchor=(0.075, 0.995),
        fontsize=FONT_SIZES["legend"],
        frameon=True,
        facecolor="white",
        edgecolor="none",
        borderpad=0.3,
    )

    save_figure_bundle(fig, OUT)
    plt.close(fig)
    print(f"Generated {OUT}.svg/.pdf/.png")


if __name__ == "__main__":
    main()
