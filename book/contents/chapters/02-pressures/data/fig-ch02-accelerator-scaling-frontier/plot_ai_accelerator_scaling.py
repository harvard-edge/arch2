"""Compare FP16 peak rates and the HBM balance point, 2016–2024, row by row.

Plot the plotted=yes rows of chapter2-gpu-balance-point.csv. B200 is the HGX
configuration at its printed dense rate; the file also keeps the alternatives
the prose discloses. Non-Tensor and Tensor Core FP16 are separate rows in
NVIDIA's tables with different operation constraints, so each keeps its own
series and no multiple crosses them. Panel (a) uses V100 as the base because it
is the first generation with both rows. NA cells are left unplotted. No
structured-sparsity multiplier is included. These specifications are not
application measurements or compute-density measurements.
"""

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(REPO_ROOT))
from book._python.plots import COLORS, apply_style


def main():
    apply_style()
    source = REPO_ROOT / "book/contents/chapters/02-pressures/data/fig-ch02-accelerator-scaling-frontier/chapter2-gpu-balance-point.csv"
    with source.open() as stream:
        rows = list(csv.DictReader(line for line in stream if not line.startswith("#")))
    chips = [row for row in rows if row["plotted"] == "yes"]
    base = next(index for index, row in enumerate(chips) if row["Chip_Name"] == "V100")
    # Tick labels come from the rows themselves.
    labels = [row["Chip_Name"] + "\n" + row["Release_Year"] for row in chips]

    def column(name):
        return [None if row[name] == "NA" else float(row[name]) for row in chips]

    tensor = column("Peak_FP16_Tensor_TFLOPS")
    non_tensor = column("Peak_FP16_nonTensor_TFLOPS")
    bandwidth = column("Memory_Bandwidth_GBs")
    power = column("TDP_Watts")
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 3.1))
    fig.subplots_adjust(left=0.085, right=0.98, bottom=0.19, top=0.87, wspace=0.34)
    for values, label, color, marker in [
        (tensor, "Tensor Core FP16 (dense)", COLORS["blue"], "o"),
        (non_tensor, "Non-Tensor FP16", COLORS["purple"], "D"),
        (bandwidth, "HBM bandwidth", COLORS["green"], "s"),
        (power, "TDP", COLORS["orange"], "^"),
    ]:
        points = [(i, v / values[base]) for i, v in enumerate(values) if v is not None]
        axes[0].plot(
            [i for i, _ in points],
            [v for _, v in points],
            label=label,
            color=color,
            marker=marker,
            markersize=4,
            linewidth=1.5,
        )
    axes[0].set_yscale("log")
    axes[0].set_ylim(0.5, 40)
    axes[0].set_yticks([0.5, 1, 2, 5, 10, 20], ["0.5", "1", "2", "5", "10", "20"])
    axes[0].minorticks_off()
    axes[0].set_ylabel("Multiple of each series' V100 value (log scale)")
    axes[0].set_title("(a) Each series against its own V100 value", loc="left")
    axes[0].legend(loc="upper left", fontsize=5.8, frameon=False)
    width = 0.38
    for values, shift, color, name in [
        (non_tensor, -width / 2, COLORS["purple"], "Non-Tensor FP16"),
        (tensor, width / 2, COLORS["blue"], "Tensor Core FP16 (dense)"),
    ]:
        points = [(i, v * 1000 / b) for i, (v, b) in enumerate(zip(values, bandwidth)) if v is not None]
        axes[1].bar(
            [i + shift for i, _ in points],
            [v for _, v in points],
            color=color,
            width=width,
            label=name,
        )
        for index, value in points:
            axes[1].text(index + shift, value + 8, f"{value:.0f}", ha="center", fontsize=6.5)
    axes[1].set_ylim(0, 350)
    axes[1].set_ylabel("FP16 FLOP per HBM byte")
    axes[1].set_title("(b) Required reuse at peak, by row", loc="left")
    axes[1].legend(loc="upper left", fontsize=5.8, frameon=False)
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
