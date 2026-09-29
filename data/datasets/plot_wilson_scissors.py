"""
Wilson Research Group verification-effort and first-silicon plot (2007-2024)
---------------------------------------------------------------------------
Plots only values printed on Foster's published charts or stated in the study text, as recorded
(with a per-value source) in chapter7-wilson-verification-scissors-gap.csv:
  - mean share of project time in verification (printed means, 2010-2020);
  - first-silicon success (stated in text: 2014, 2020, 2022, 2024);
  - verification-to-design staffing ratio (printed engineer counts 2007-2020; 2022 and 2024 derived
    from the studies' stated growth rates and drawn hollow).
Years without a printed or stated value are left blank and not drawn.
"""

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style

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

    fig, ax = plt.subplots(figsize=(5.6, 3.3))
    fig.subplots_adjust(left=0.11, right=0.86, top=0.95, bottom=0.16)

    ax.plot(
        [y for y, _ in vt],
        [v for _, v in vt],
        color=COLORS["purple"],
        linewidth=1.8,
        marker="o",
        markersize=4.0,
        label="Mean share of project time in verification (%)",
        zorder=3,
    )
    ax.plot(
        [y for y, _ in fs],
        [v for _, v in fs],
        color=COLORS["red"],
        linewidth=1.8,
        marker="s",
        markersize=4.0,
        label="First-silicon success (% of projects)",
        zorder=4,
    )

    sub = ax.twinx()
    sub.plot(
        [y for y, _, _ in ratio],
        [v for _, v, _ in ratio],
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
        label="Verification-to-design staffing ratio (right axis;\nhollow = derived from stated growth rates)",
    )
    sub.set_ylim(0.4, 1.6)
    sub.set_ylabel("Staffing ratio", fontsize=6.6, color=COLORS["blue"], labelpad=3)
    sub.tick_params(axis="y", colors=COLORS["blue"], labelsize=6.0, pad=2)

    last_y, last_v = fs[-1]
    ax.annotate(
        f"{last_y}: {last_v:.0f}% first-silicon success",
        xy=(last_y, last_v),
        xytext=(2013.2, 15),
        arrowprops=dict(arrowstyle="->", color=COLORS["red"], lw=0.8),
        fontsize=5.6,
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
    ax.set_xlabel("Survey year", fontsize=6.8)
    ax.set_ylabel("Percent", fontsize=6.8)
    ax.tick_params(axis="both", labelsize=6.0)
    ax.grid(True, color=COLORS["grid"], linewidth=0.5, zorder=0)

    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = sub.get_legend_handles_labels()
    ax.legend(
        h1 + h2,
        l1 + l2,
        loc="upper left",
        fontsize=5.4,
        frameon=True,
        facecolor="white",
        edgecolor="none",
        borderpad=0.3,
    )

    for ext, kw in (("svg", {}), ("pdf", {}), ("png", {"dpi": 300})):
        fig.savefig(OUT.with_suffix(f".{ext}"), bbox_inches="tight", **kw)
    plt.close(fig)
    print(f"Generated {OUT}.svg/.pdf/.png")


if __name__ == "__main__":
    main()
