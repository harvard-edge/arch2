"""
MLPerf Software Dividend vs. Hardware Scaling Plot (2018-2026)
--------------------------------------------------------------
Visualizes the historical progression from MLCommons MLPerf Training & Inference results:
Panel A: The Fixed-Silicon Software Dividend (2.0x-3.8x throughput increase on frozen silicon).
Panel B: Hardware Generational Steps vs. Cumulative In-Place Software Gains.
"""

import csv
import re
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
    csv_file = REPO_ROOT / "data" / "datasets" / "chapter9-mlperf-software-dividend.csv"
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

    # Read the dataset. This script previously named csv_file and never opened
    # it: `import csv` was unused and every plotted value was an in-script
    # literal. It passed the provenance validator because the filename appeared
    # as a string.
    with open(csv_file, "r", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(l for l in f if not l.startswith("#"))]

    def months_since(dates):
        base = dates[0]
        return [
            (int(d[:4]) - int(base[:4])) * 12 + (int(d[5:7]) - int(base[5:7]))
            for d in dates
        ]

    def series(platform_key, workload_key):
        """In-place dividend over time for one platform on one workload."""
        sel = [
            r
            for r in rows
            if platform_key in r["platform"]
            and workload_key in r["benchmark_workload"]
            and r["software_dividend_multiplier"]
        ]
        sel.sort(key=lambda r: r["release_date"])
        return months_since([r["release_date"] for r in sel]), [
            float(r["software_dividend_multiplier"]) for r in sel
        ]

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(7.5, 3.6), gridspec_kw={"width_ratios": [1.1, 1.05]}
    )
    fig.subplots_adjust(wspace=0.38, left=0.10, right=0.96, top=0.88, bottom=0.18)

    # -------------------------------------------------------------
    # Panel A: The Fixed-Silicon Software Dividend (Normalized Throughput over Months)
    # -------------------------------------------------------------
    v100_m, v100_t = series("V100", "ResNet-50")
    a100_m, a100_t = series("A100 (DGX A100)", "BERT-Large")
    tpu4_m, tpu4_t = series("TPU v4", "ResNet-50")
    h100_m, h100_t = series("H100 (Fixed 512", "GPT-3 175B")

    ax1.plot(
        v100_m,
        v100_t,
        marker="o",
        color=COLORS["purple"],
        linewidth=1.6,
        markersize=4.2,
        label=f"V100 (12nm, ResNet-50: {v100_t[-1]:.2f}x in {v100_m[-1]} mo)",
        zorder=4,
    )
    ax1.plot(
        a100_m,
        a100_t,
        marker="s",
        color=COLORS["blue"],
        linewidth=1.6,
        markersize=4.2,
        label=f"A100 (7nm, BERT-Large: {a100_t[-1]:.2f}x in {a100_m[-1]} mo)",
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
        label=f"TPU v4 (7nm, ResNet-50: {tpu4_t[-1]:.2f}x in {tpu4_m[-1]} mo)",
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
        label=f"H100 (4N, GPT-3 175B: {h100_t[-1]:.2f}x in {h100_m[-1]} mo)",
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
        "A. The Fixed-Silicon Software Dividend",
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
    # Panel B: Hardware Generational Step vs. In-Place Software Dividend
    #
    # Both series are read from the dataset. This panel previously plotted
    # hw_base = [1.0, 8.0, 60.0, 156.0] and sw_peak = [3.82, 21.5, 78.0, 156.0]
    # as in-script literals. 8.0, 60.0 and 156.0 appear nowhere in the dataset
    # and are not derivable from it: the largest single generational step in the
    # file is 7.17 and the longest cumulative chain is 9.13. The invented bases
    # were then multiplied by real software dividends, so the second series
    # inherited the fabrication. The honest comparison the dataset does support
    # is per platform, not cumulative.
    # -------------------------------------------------------------
    platform_order = ["V100", "A100", "H100", "B200"]
    platform_labels = {
        "V100": "Volta V100\n(12nm FFN)",
        "A100": "Ampere A100\n(7nm N7)",
        "H100": "Hopper H100\n(4N)",
        "B200": "Blackwell B200\n(4NP)",
    }

    hw_step = {}
    sw_div = {}
    for r in rows:
        plat = next((k for k in platform_order if k in r["platform"]), None)
        if plat is None:
            continue
        try:
            sw = float(r["software_dividend_multiplier"])
            sw_div[plat] = max(sw_div.get(plat, 1.0), sw)
        except ValueError:
            pass
        m = re.match(r"([0-9.]+)\s*vs", r["generational_step_multiplier"].strip())
        if m:
            hw_step[plat] = max(hw_step.get(plat, 0.0), float(m.group(1)))

    generations = [platform_labels[k] for k in platform_order]
    hw_vals = [hw_step.get(k, 1.0) for k in platform_order]
    sw_vals = [sw_div.get(k, 1.0) for k in platform_order]

    x_gen = np.arange(len(generations))
    width = 0.34

    rects1 = ax2.bar(
        x_gen - width / 2,
        hw_vals,
        width,
        label="Hardware step vs. previous generation",
        color=COLORS["ink"],
        alpha=0.85,
        zorder=3,
    )
    rects2 = ax2.bar(
        x_gen + width / 2,
        sw_vals,
        width,
        label="In-place software dividend on frozen silicon",
        color=COLORS["orange"],
        alpha=0.90,
        zorder=3,
    )

    ax2.axhline(1.0, color=COLORS["muted"], linewidth=0.7, linestyle=":", zorder=2)
    ax2.set_ylim(0, max(hw_vals + sw_vals) * 1.28)
    ax2.set_xticks(x_gen)
    ax2.set_xticklabels(generations, fontsize=5.4, color=COLORS["ink"])
    ax2.set_ylabel("Speedup multiplier (1.0 = no gain)", fontsize=6.6)
    ax2.tick_params(axis="both", labelsize=5.8)
    ax2.set_title(
        "B. Generational Hardware Step vs. Software Dividend",
        fontsize=7.6,
        fontweight="bold",
        pad=8,
    )
    ax2.grid(True, axis="y", color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax2.legend(
        loc="upper right",
        fontsize=5.0,
        frameon=True,
        facecolor="white",
        edgecolor="none",
        borderpad=0.25,
    )

    for bar, val in list(zip(rects1, hw_vals)) + list(zip(rects2, sw_vals)):
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            val + max(hw_vals + sw_vals) * 0.03,
            f"{val:.2f}x",
            ha="center",
            va="bottom",
            fontsize=4.8,
            fontweight="bold",
            color=COLORS["ink"],
        )

    plt.savefig(out_svg, format="svg", bbox_inches="tight")
    plt.savefig(out_pdf, format="pdf", bbox_inches="tight")
    plt.savefig(out_png, format="png", dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Generated MLPerf Software Dividend plot -> {out_svg} and {out_pdf}")


if __name__ == "__main__":
    main()
