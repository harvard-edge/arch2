"""
MLPerf Software Dividend vs. Hardware Scaling Plot (2018-2026)
--------------------------------------------------------------
Visualizes the historical progression from MLCommons MLPerf Training & Inference results:
Panel A: The Fixed-Silicon Software Dividend (2.0x-3.8x throughput increase on frozen silicon).
Panel B: Hardware Generational Steps vs. Cumulative In-Place Software Gains.
"""

import csv
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style

apply_style()


def main():
    csv_file = (
        REPO_ROOT / "data" / "source-receipts" / "chapter9-mlperf-software-dividend.csv"
    )
    out_svg = (
        REPO_ROOT
        / "book"
        / "contents"
        / "chapters"
        / "09-patterns"
        / "images"
        / "fig-ch09-mlperf-software-dividend.svg"
    )
    out_pdf = (
        REPO_ROOT
        / "book"
        / "contents"
        / "chapters"
        / "09-patterns"
        / "images"
        / "fig-ch09-mlperf-software-dividend.pdf"
    )
    out_png = (
        REPO_ROOT
        / "book"
        / "contents"
        / "chapters"
        / "09-patterns"
        / "images"
        / "fig-ch09-mlperf-software-dividend.png"
    )
    out_svg.parent.mkdir(parents=True, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(7.5, 3.6), gridspec_kw={"width_ratios": [1.1, 1.05]}
    )
    fig.subplots_adjust(wspace=0.38, left=0.10, right=0.96, top=0.88, bottom=0.18)

    # -------------------------------------------------------------
    # Panel A: The Fixed-Silicon Software Dividend (Normalized Throughput over Months)
    # -------------------------------------------------------------
    v100_m = [0, 7, 19]
    v100_t = [1.0, 2.32, 3.82]

    a100_m = [0, 11, 16, 23]
    a100_t = [1.0, 2.32, 2.45, 2.69]

    tpu4_m = [0, 12]
    tpu4_t = [1.0, 1.50]

    h100_m = [0, 12, 17]
    h100_t = [1.0, 1.27, 1.30]

    ax1.plot(
        v100_m,
        v100_t,
        marker="o",
        color=COLORS["purple"],
        linewidth=1.6,
        markersize=4.2,
        label="V100 (12nm, ResNet-50: 3.82x in 19 mo)",
        zorder=4,
    )
    ax1.plot(
        a100_m,
        a100_t,
        marker="s",
        color=COLORS["blue"],
        linewidth=1.6,
        markersize=4.2,
        label="A100 (7nm, BERT-Large: 2.69x in 23 mo)",
        zorder=3,
    )
    ax1.plot(
        tpu4_m,
        tpu4_t,
        marker="^",
        color=COLORS["green"],
        linewidth=1.4,
        linestyle="--",
        markersize=4.2,
        label="TPU v4 (7nm, Suite Avg: 1.50x in 12 mo)",
        zorder=2,
    )
    ax1.plot(
        h100_m,
        h100_t,
        marker="D",
        color=COLORS["red"],
        linewidth=1.4,
        linestyle="-.",
        markersize=4.2,
        label="H100 (4N, GPT-3 175B: 1.30x in 17 mo)",
        zorder=2,
    )

    # Annotations with clean background padding
    ax1.annotate(
        "DALI NVJPEG +\nCBR Fusion",
        (7, 2.32),
        xytext=(-20, 12),
        textcoords="offset points",
        fontsize=4.8,
        color=COLORS["purple"],
        fontweight="bold",
        bbox=dict(
            boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.85
        ),
    )
    ax1.annotate(
        "Apex Fused MHA +\nCUDA Graphs",
        (11, 2.32),
        xytext=(8, -14),
        textcoords="offset points",
        fontsize=4.8,
        color=COLORS["blue"],
        fontweight="bold",
        bbox=dict(
            boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.85
        ),
    )
    ax1.annotate(
        "FlashAttention-2 +\nFP8 Transformer Eng",
        (12, 1.27),
        xytext=(10, 8),
        textcoords="offset points",
        fontsize=4.8,
        color=COLORS["red"],
        fontweight="bold",
        bbox=dict(
            boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.85
        ),
    )

    ax1.set_xlim(-1, 26)
    ax1.set_ylim(0.8, 4.3)
    ax1.set_xlabel("Months Since Silicon Hardware Deployment", fontsize=6.6)
    ax1.set_ylabel("Normalized In-Place Throughput Multiplier", fontsize=6.6)
    ax1.tick_params(axis="both", labelsize=5.8)
    ax1.set_title(
        "Panel A: The Fixed-Silicon Software Dividend",
        fontsize=7.6,
        fontweight="bold",
        pad=8,
    )
    ax1.grid(True, color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax1.legend(
        loc="upper left",
        fontsize=4.8,
        frameon=True,
        facecolor="white",
        edgecolor="none",
        borderpad=0.25,
    )

    # -------------------------------------------------------------
    # Panel B: Hardware Generational Steps vs. In-Place Software Gains
    # -------------------------------------------------------------
    generations = [
        "Volta V100\n(12nm FFN)",
        "Ampere A100\n(7nm N7)",
        "Hopper H100\n(4N)",
        "Blackwell B200\n(4NP Dual-Die)",
    ]
    hw_base = [1.0, 8.0, 60.0, 156.0]
    sw_peak = [3.82, 21.5, 78.0, 156.0]

    x_gen = np.arange(len(generations))
    width = 0.32
    y_min = 0.5

    h_heights = [h - y_min for h in hw_base]
    s_heights = [s - y_min for s in sw_peak]

    rects1 = ax2.bar(
        x_gen - width / 2,
        h_heights,
        width,
        bottom=y_min,
        label="Silicon Hardware Debut",
        color=COLORS["ink"],
        alpha=0.85,
        zorder=3,
    )
    rects2 = ax2.bar(
        x_gen + width / 2,
        s_heights,
        width,
        bottom=y_min,
        label="Mature Software Stack (+SW Dividend)",
        color=COLORS["orange"],
        alpha=0.90,
        zorder=3,
    )

    ax2.set_yscale("log")
    ax2.set_ylim(0.5, 350)
    ax2.set_xticks(x_gen)
    ax2.set_xticklabels(generations, fontsize=5.4, color=COLORS["ink"])
    ax2.set_ylabel(
        "BERT-Large Throughput (rel. to V100 Debut, Log Scale)", fontsize=6.6
    )
    ax2.tick_params(axis="both", labelsize=5.8)
    ax2.set_title(
        "Panel B: Hardware Steps vs. Software Expansion",
        fontsize=7.6,
        fontweight="bold",
        pad=8,
    )
    ax2.grid(True, which="both", color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax2.legend(
        loc="upper left",
        fontsize=5.0,
        frameon=True,
        facecolor="white",
        edgecolor="none",
        borderpad=0.25,
    )

    for i, (bar1, bar2, h_val, s_val) in enumerate(
        zip(rects1, rects2, hw_base, sw_peak)
    ):
        if h_val == s_val:
            center_x = (
                bar1.get_x()
                + bar1.get_width() / 2
                + bar2.get_x()
                + bar2.get_width() / 2
            ) / 2
            ax2.text(
                center_x,
                h_val * 1.25,
                f"{h_val:.0f}x (Debut)",
                ha="center",
                va="bottom",
                fontsize=4.8,
                fontweight="bold",
                color=COLORS["ink"],
            )
        elif i == 2:  # Hopper H100 - stagger heights to prevent any crowding
            ax2.text(
                bar1.get_x() + bar1.get_width() / 2,
                h_val * 1.15,
                f"{h_val:.0f}x",
                ha="center",
                va="bottom",
                fontsize=4.8,
                fontweight="bold",
                color=COLORS["ink"],
            )
            ax2.text(
                bar2.get_x() + bar2.get_width() / 2,
                s_val * 1.45,
                f"{s_val:.1f}x",
                ha="center",
                va="bottom",
                fontsize=4.8,
                fontweight="bold",
                color=COLORS["orange"],
            )
        else:
            ax2.text(
                bar1.get_x() + bar1.get_width() / 2,
                h_val * 1.25,
                f"{h_val:.0f}x",
                ha="center",
                va="bottom",
                fontsize=4.8,
                fontweight="bold",
                color=COLORS["ink"],
            )
            ax2.text(
                bar2.get_x() + bar2.get_width() / 2,
                s_val * 1.25,
                f"{s_val:.1f}x",
                ha="center",
                va="bottom",
                fontsize=4.8,
                fontweight="bold",
                color=COLORS["orange"],
            )

    plt.savefig(out_svg, format="svg", bbox_inches="tight")
    plt.savefig(out_pdf, format="pdf", bbox_inches="tight")
    plt.savefig(out_png, format="png", dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Generated MLPerf Software Dividend plot -> {out_svg} and {out_pdf}")


if __name__ == "__main__":
    main()
