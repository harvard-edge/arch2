"""Deferred Chapter 7 transient-execution mitigation chart.

The former chapter figure combined ranges from different processors, kernels,
workloads, years, mitigation sets, and secondary reports. Preserve the source
and receipt, but do not reuse the chart until the observations are made
comparable or are shown as individually identified measurements.

Receipt:
    data/source-receipts/chapter7-mitigation-overhead.csv
"""

import csv
from pathlib import Path

import matplotlib.pyplot as plt

from _python.plots import COLORS, apply_style

apply_style()

repo_root = Path(__file__).resolve().parents[3]
receipt = repo_root / "data" / "source-receipts" / "chapter7-mitigation-overhead.csv"

rows = []
with receipt.open(encoding="utf-8") as handle:
    for record in csv.DictReader(handle):
        rows.append(
            {
                "mitigation": record["mitigation"],
                "threat": record["threat"],
                "low": float(record["low_pct"]),
                "high": float(record["high_pct"]),
            }
        )

rows.sort(key=lambda row: row["high"])


def short_label(mitigation, threat):
    base = (
        "All mitigations" if mitigation.startswith("All") else mitigation.split(" ")[0]
    )
    return f"{base} ({threat})"


figure, axis = plt.subplots(figsize=(5.6, 3.0))
positions = list(range(len(rows)))

for position, row in zip(positions, rows):
    axis.hlines(
        position,
        row["low"],
        row["high"],
        color=COLORS["constraints"],
        linewidth=3.0,
        zorder=2,
    )
    for value in (row["low"], row["high"]):
        axis.scatter(
            [value],
            [position],
            marker="s",
            s=15,
            facecolor=COLORS["note_fill"],
            edgecolor=COLORS["constraints"],
            linewidth=0.9,
            zorder=3,
        )
    axis.text(
        row["high"] + 1.2,
        position,
        f"{row['low']:.0f}–{row['high']:.0f}%",
        ha="left",
        va="center",
        fontsize=5.9,
        fontweight="bold",
        color=COLORS["constraints_ink"],
    )

axis.set_yticks(positions)
axis.set_yticklabels(
    [short_label(row["mitigation"], row["threat"]) for row in rows],
    fontsize=6.4,
)
axis.set_ylim(-0.6, len(rows) - 0.35)
axis.set_xlim(-1, 60)
axis.set_xlabel("Reported slowdown vs. unmitigated (%)", fontsize=7.2)
axis.set_xticks([0, 10, 20, 30, 40, 50])
axis.tick_params(labelsize=6.4, length=2.5, width=0.6)

for spine in ("top", "right"):
    axis.spines[spine].set_visible(False)

axis.grid(axis="x", color=COLORS["row"], linewidth=0.4, zorder=0)
axis.text(
    59,
    len(rows) - 0.75,
    "each bar: lowest to highest reported overhead",
    fontsize=5.0,
    fontstyle="italic",
    color=COLORS["muted"],
    ha="right",
    va="center",
)

figure.subplots_adjust(left=0.22, right=0.97, top=0.94, bottom=0.15)
