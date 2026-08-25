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


def generate_mlperf_coevolution_plot(csv_path=None):
    if csv_path is None:
        csv_path = (
            REPO_ROOT / "data" / "source-receipts" / "chapter10-mlperf-coevolution.csv"
        )

    hw_data = []
    sw_data = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cat = row["category"]
            chip = row["chip"]
            peak_tflops = float(row["peak_tflops_bf16"])
            throughput = float(row["realized_relative_throughput"])
            ver = row["mlperf_version"]

            if cat == "hardware_scaling":
                hw_data.append((chip, peak_tflops, throughput, ver))
            elif cat == "software_dividend":
                sw_data.append((chip, peak_tflops, throughput, ver))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2))

    # Panel A: Peak Hardware TFLOPs vs Realized System Throughput
    hw_data.sort(key=lambda x: x[1])
    x_hw = [d[1] for d in hw_data]
    y_hw = [d[2] for d in hw_data]

    ax1.scatter(
        x_hw, y_hw, s=80, color=COLORS["blue"], alpha=0.9, edgecolors="none", zorder=3
    )

    for chip, x, y, _ in hw_data:
        ax1.annotate(
            chip,
            (x, y),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=6.8,
            color=COLORS["ink"],
        )

    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlabel("Peak Hardware TFLOPs (BF16/FP16, log scale)", fontsize=7)
    ax1.set_ylabel("Realized System Throughput (rel. to V100, log scale)", fontsize=7)
    ax1.set_title(
        "A. Peak Hardware vs Realized Throughput",
        fontsize=8,
        fontweight="bold",
        color=COLORS["ink"],
    )
    ax1.grid(True, which="both", color=COLORS["grid"], linewidth=0.5, zorder=0)

    # Panel B: The Software Co-Evolution Dividend (Fixed H100 Hardware)
    x_sw = [d[3] for d in sw_data]
    y_sw = [d[2] for d in sw_data]

    ax2.plot(
        x_sw,
        y_sw,
        marker="o",
        linewidth=2.0,
        markersize=6,
        color=COLORS["orange"],
        zorder=3,
    )

    ax2.set_xlabel("MLPerf Submission Version", fontsize=7)
    ax2.set_ylabel("Throughput Gain (rel. to v2.1 baseline)", fontsize=7)
    ax2.set_title(
        "B. Software & Compiler Dividend on Fixed Silicon",
        fontsize=8,
        fontweight="bold",
        color=COLORS["ink"],
    )
    ax2.grid(True, color=COLORS["grid"], linewidth=0.5, zorder=0)

    # Percentage annotations
    for ver, val in zip(x_sw, y_sw):
        ax2.annotate(
            f"{val:.2f}x",
            (ver, val),
            xytext=(0, 6),
            textcoords="offset points",
            ha="center",
            fontsize=6.8,
            fontweight="bold",
            color=COLORS["methods_ink"],
        )

    plt.tight_layout()
    out_path = REPO_ROOT / "book" / "images" / "fig-mlperf-coevolution.svg"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    print(f"Plot saved to '{out_path}'")


if __name__ == "__main__":
    generate_mlperf_coevolution_plot()
