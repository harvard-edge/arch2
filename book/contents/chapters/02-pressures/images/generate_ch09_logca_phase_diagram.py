"""Generate the illustrative LogCA break-even diagram used in chapter 2
(fig-ch09-logca-phase-diagram).

Model: nonoverlapped LogCA-style break-even granularity
    g*(OI) = o / [C_h (1 - 1/A) - 1/(OI * B)]
with host cost C_h = 0.4 ns/FLOP and local acceleration A = 50 (both stated in the chapter).
Inputs: data/datasets/chapter9-interconnect-logca-specs.csv. Link bandwidth B is a nominal
per-direction rate derived from each standard's lane count and signaling rate. The invocation
overhead o is an illustrative assumption for each regime, not a specified or measured value.
"""

import csv
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

repo_root = Path(__file__).resolve().parents[5]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from book._python.plots import COLORS, apply_style

C_H = 0.4e-9  # seconds per FLOP on the host
A = 50.0  # local acceleration factor

STYLES = [
    (COLORS["green"], "-"),
    (COLORS["evidence_ink"], "--"),
    (COLORS["blue"], "-."),
    (COLORS["purple"], "-"),
    (COLORS["orange"], "--"),
    (COLORS["red"], "-."),
    (COLORS["constraints_ink"], ":"),
]


def generate_figure(output_dir: Path) -> Path:
    apply_style()
    specs_path = (
        repo_root / "data" / "datasets" / "chapter9-interconnect-logca-specs.csv"
    )
    with open(specs_path, "r", encoding="utf-8") as f:
        specs = list(csv.DictReader(l for l in f if not l.startswith("#")))

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    oi_grid = np.logspace(np.log10(0.001), np.log10(500), 800)

    oi_stars = []
    for row, (color, ls) in zip(specs, STYLES):
        o = float(row["assumed_invocation_overhead_ns"]) * 1e-9
        B = float(row["link_bandwidth_gb_s"]) * 1e9
        oi_star = 1.0 / (B * C_H * (1.0 - 1.0 / A))
        oi_stars.append(oi_star)
        oi_sub = oi_grid[oi_grid > oi_star * 1.01]
        g_star = o / (C_H * (1.0 - 1.0 / A) - 1.0 / (oi_sub * B))
        ax.plot(oi_sub, g_star, color=color, linestyle=ls, linewidth=1.8, zorder=3)
        ax.axvline(
            oi_star, color=color, linestyle=":", linewidth=0.7, alpha=0.6, zorder=1
        )
        label = (
            f"{row['short_label']}: B = {float(row['link_bandwidth_gb_s']):g} GB/s, "
            f"o = {float(row['assumed_invocation_overhead_ns']):g} ns"
        )
        below = row["short_label"].startswith("UCIe")
        ax.text(
            2.0,
            g_star[-1] * (0.80 if below else 1.25),
            label,
            fontsize=7.0,
            color=color,
            ha="left",
            va="top" if below else "bottom",
            zorder=5,
            bbox=dict(
                boxstyle="round,pad=0.15",
                facecolor="white",
                edgecolor="none",
                alpha=0.85,
            ),
        )

    oi_star_min = min(oi_stars)
    ax.axvspan(oi_grid[0], oi_star_min, color=COLORS["red"], alpha=0.07, zorder=0)
    ax.text(
        (oi_grid[0] * oi_star_min) ** 0.5,
        3e5,
        f"No link\nbreaks even\nbelow OI =\n{oi_star_min:.4f}\nFLOP/byte",
        fontsize=6.8,
        color=COLORS["constraints_ink"],
        fontweight="bold",
        ha="center",
        va="center",
    )

    ax.text(
        0.98,
        0.97,
        "o = assumed invocation overhead (illustrative)\nB = nominal per-direction link rate",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=7.0,
        color=COLORS["muted"],
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.001, 400)
    ax.set_ylim(10, 5e7)
    ax.set_xlabel(
        r"Operational intensity OI (FLOP per byte moved across the link)",
        fontsize=9,
        color=COLORS["ink"],
    )
    ax.set_ylabel(
        r"Modeled break-even granularity $g^*$ (FLOPs per offload)",
        fontsize=9,
        color=COLORS["ink"],
    )
    ax.set_xticks([0.001, 0.01, 0.1, 1.0, 10.0, 100.0])
    ax.set_xticklabels(["0.001", "0.01", "0.1", "1", "10", "100"])
    ax.set_yticks([1e1, 1e2, 1e3, 1e4, 1e5, 1e6, 1e7])
    ax.set_yticklabels(
        [r"$10$", r"$10^2$", r"$10^3$", r"$10^4$", r"$10^5$", r"$10^6$", r"$10^7$"]
    )
    ax.tick_params(axis="both", labelsize=8, length=2.5, width=0.5)
    ax.grid(axis="both", color=COLORS["grid"], linewidth=0.5, zorder=0)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    png_path = output_dir / "fig-ch09-logca-phase-diagram.png"
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(output_dir / "fig-ch09-logca-phase-diagram.svg", bbox_inches="tight")
    fig.savefig(output_dir / "fig-ch09-logca-phase-diagram.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"Generated: {png_path}")
    return png_path


if __name__ == "__main__":
    generate_figure(Path(__file__).resolve().parent)
