"""Deferred source for the former Chapter 6 simulator-tax figure.

The chart mixed instruction and cycle throughput through an approximate
IPC-equals-one conversion. Preserve it for a later evidence and visual pass,
but do not treat the derived slowdown values as a universal tool ordering.
The frozen inputs remain in
data/source-receipts/chapter5-simulator-tax.csv.
"""

import csv
from pathlib import Path

import matplotlib.pyplot as plt

import _python.plots as _ap
from _python.plots import COLORS, apply_style

apply_style()

root = Path(_ap.__file__).resolve().parents[2]
rows = []
with open(
    root / "data" / "source-receipts" / "chapter5-simulator-tax.csv",
    encoding="utf-8",
) as source:
    for entry in csv.DictReader(source):
        rows.append(
            {
                "name": entry["rung"],
                "example": entry["example"],
                "slowdown": float(entry["slowdown_vs_silicon"]),
            }
        )

kind = {
    "Native silicon": COLORS["workload"],
    "FPGA emulation": COLORS["evidence"],
}
figure, axis = plt.subplots(figsize=(6.0, 3.3))
count = len(rows)

for index, row in enumerate(rows):
    y = count - 1 - index
    color = kind.get(row["name"], COLORS["methods"])
    slowdown = row["slowdown"]
    axis.hlines(y, 1, max(slowdown, 1.02), color=color, lw=2.4, zorder=2)
    axis.scatter(
        [max(slowdown, 1.02)],
        [y],
        s=46,
        color=color,
        edgecolor=color,
        zorder=3,
    )
    tag = "1× (real time)" if slowdown < 1.5 else f"~{slowdown:,.0f}× slower"
    axis.text(
        max(slowdown, 1.02) * 1.35,
        y + 0.02,
        tag,
        va="center",
        ha="left",
        fontsize=6.0,
        fontweight="bold",
        color=color,
    )
    axis.text(
        1.05,
        y + 0.34,
        row["name"],
        va="center",
        ha="left",
        fontsize=7.0,
        fontweight="bold",
        color=COLORS["ink"],
    )
    axis.text(
        1.05,
        y - 0.30,
        row["example"],
        va="center",
        ha="left",
        fontsize=5.4,
        color=COLORS["muted"],
    )

axis.set_xscale("log")
axis.set_xlim(1, 6e5)
axis.set_ylim(-0.7, count - 0.2)
axis.set_yticks([])
axis.set_xlabel("Slowdown versus real hardware (log)", fontsize=7.2)
axis.set_xticks([1, 1e1, 1e2, 1e3, 1e4, 1e5])
axis.set_xticklabels(
    ["1×", "10×", "100×", "1,000×", "10,000×", "100,000×"],
    fontsize=6.2,
)
axis.tick_params(labelsize=6.2, length=2.5, width=0.6)
for spine in ("top", "right", "left"):
    axis.spines[spine].set_visible(False)
axis.grid(axis="x", color=COLORS["row"], linewidth=0.4, zorder=0)
figure.subplots_adjust(left=0.02, right=0.985, top=0.97, bottom=0.14)
plt.show()
