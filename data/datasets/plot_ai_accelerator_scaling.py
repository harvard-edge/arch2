"""Compare dense FP16 throughput and the HBM balance point, 2016–2022.

Use the P100, V100, A100, and H100 SXM rows from the source dataset.
P100 uses conventional FP16 arithmetic; later parts use Tensor Cores.
No structured-sparsity multiplier is included. These specifications are
not application measurements or compute-density measurements.
"""

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
from book._python.plots import COLORS, apply_style


def main():
    apply_style()
    source = REPO_ROOT / "data/datasets/chapter2-ai-accelerator-scaling-frontier.csv"
    with source.open() as stream:
        rows = list(csv.DictReader(line for line in stream if not line.startswith("#")))
    chips = [
        row
        for row in rows
        if row["Vendor"] == "NVIDIA" and 2016 <= int(row["Release_Year"]) <= 2022
    ]
    labels = ["P100\n2016", "V100\n2017", "A100\n2020", "H100\n2022"]
    compute = [float(row["Peak_FP16_BF16_TFLOPS"]) for row in chips]
    bandwidth = [float(row["Memory_Bandwidth_GBs"]) for row in chips]
    power = [float(row["TDP_Watts"]) for row in chips]
    balance = [rate * 1000 / bw for rate, bw in zip(compute, bandwidth)]
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 3.1))
    fig.subplots_adjust(left=0.085, right=0.98, bottom=0.19, top=0.87, wspace=0.40)
    for values, label, color, marker in [
        (compute, "Dense FP16 peak", COLORS["blue"], "o"),
        (bandwidth, "HBM bandwidth", COLORS["green"], "s"),
        (power, "TDP", COLORS["orange"], "^"),
    ]:
        axes[0].plot(
            [value / values[0] for value in values],
            label=label,
            color=color,
            marker=marker,
            markersize=4,
            linewidth=1.5,
        )
    axes[0].set_yscale("log")
    axes[0].set_ylim(0.8, 100)
    axes[0].set_ylabel("Growth relative to P100 (log scale)")
    axes[0].set_title("(a) Arithmetic and data supply", loc="left")
    axes[0].legend(loc="upper left", fontsize=5.8, frameon=False)
    axes[1].bar(range(len(chips)), balance, color=COLORS["blue"], width=0.55)
    for index, value in enumerate(balance):
        axes[1].text(index, value + 8, f"{value:.0f}", ha="center", fontsize=6.5)
    axes[1].set_ylim(0, 350)
    axes[1].set_ylabel("Dense FP16 FLOP per HBM byte")
    axes[1].set_title("(b) Required reuse at peak", loc="left")
    for axis in axes:
        axis.set_xticks(range(len(chips)), labels)
        axis.grid(axis="y", color=COLORS["grid"], linewidth=0.5)
        axis.set_axisbelow(True)
        axis.spines[["top", "right"]].set_visible(False)
    output = (
        REPO_ROOT
        / "book/contents/chapters/02-pressures/images/fig-ch02-accelerator-scaling-frontier"
    )
    for extension in ("svg", "pdf", "png"):
        fig.savefig(output.with_suffix(f".{extension}"), dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    main()
