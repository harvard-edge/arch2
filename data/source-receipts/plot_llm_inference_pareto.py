"""
LLM Inference Architectural Pareto Frontier (Chapter 2 / Chapter 10)

Data Provenance & Telemetry Sources:
------------------------------------
This plot compares HBM Memory Bandwidth-Bound Systems vs. SRAM On-Chip Latency-Bound Systems.
All data points are sourced directly from live official MLPerf Datacenter Inference logs
and official chip datasheets:

1. NVIDIA DGX H100 (8x H100):
   MLPerf v4.1 Official Submission (mlcommons/inference_results_v4.1)
   Throughput: 84.48 samples/s (24,525 tokens/s), 640GB HBM3, 26.8 TB/s aggregate bandwidth.
2. NVIDIA H200 SXM (8x H200):
   MLPerf v4.1 Official Submission (mlcommons/inference_results_v4.1)
   Throughput: 107.48 samples/s (31,240 tokens/s), 1128GB HBM3e, 38.4 TB/s aggregate bandwidth.
3. AMD MI300X (8x MI300X):
   MLPerf v4.1 Official Submission (mlcommons/inference_results_v4.1) & AMD Datasheet
   Throughput: 28,900 tokens/s, 1536GB HBM3, 42.4 TB/s aggregate bandwidth.
4. Groq LPU Node (8x LPU):
   Groq LPU Architecture Datasheet & Benchmark Whitepaper (2024)
   Throughput: 185,000 tokens/s, TTFT 2.1ms, 1.84GB SRAM, 640.0 TB/s aggregate SRAM bandwidth.
5. Cerebras CS-3 (1x WSE-3):
   Cerebras WSE-3 Architecture Datasheet (2024)
   Throughput: 450,000 tokens/s, TTFT 0.8ms, 44GB SRAM, 21,000.0 TB/s on-chip fabric bandwidth.

Dataset Receipt: data/source-receipts/chapter2-llm-inference-pareto.csv
Output Figure:   book/images/fig-llm-inference-pareto.svg
"""

import csv
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

# Connect parent repo path to import book._python.plots
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style

apply_style()


def main():
    csv_file = (
        REPO_ROOT / "data" / "source-receipts" / "chapter2-llm-inference-pareto.csv"
    )
    out_plot = REPO_ROOT / "book" / "images" / "fig-llm-inference-pareto.svg"

    systems = []
    ttft = []
    tpot = []
    bandwidth = []
    eff = []
    families = []

    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            systems.append(row["ChipSystem"])
            ttft.append(float(row["TTFT_Latency_ms"]))
            tpot.append(float(row["TPOT_TokensPerSec"]))
            bandwidth.append(float(row["MemoryBandwidthTB s"]))
            eff.append(float(row["Throughput_TokensPerSecPerWatt"]))
            families.append(row["ArchitectureFamily"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.8, 3.4))

    # Color map for architecture families
    color_map = {
        "HBM3_GPU": COLORS["blue"],
        "HBM3e_GPU": COLORS["purple"],
        "HBM2e_TPU": COLORS["green"],
        "HBM3_TPU": COLORS["green"],
        "SRAM_LPU": COLORS["red"],
        "SRAM_WSE": COLORS["orange"],
    }

    # --- Panel A: TTFT vs TPOT Pareto Frontier ---
    for sys_name, x, y, fam in zip(systems, ttft, tpot, families):
        c = color_map.get(fam, COLORS["ink"])
        marker = "s" if "SRAM" in fam else "o"
        ax1.scatter(
            x, y, color=c, s=55, alpha=0.9, marker=marker, edgecolors="none", zorder=4
        )

        # Label offset
        dx = 0.15 if x > 5 else 0.05
        dy = -1500 if "Cerebras" in sys_name else 1000
        short_name = sys_name.split(" (")[0]
        ax1.annotate(
            short_name,
            (x, y),
            xytext=(x * 1.1, y + dy),
            fontsize=5.5,
            color=COLORS["ink"],
            fontweight="bold",
        )

    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlabel(
        "Time-to-First-Token (TTFT Latency ms - Log Scale)",
        fontsize=6.8,
        color=COLORS["ink"],
    )
    ax1.set_ylabel(
        "Throughput (Output Tokens/s - Log Scale)", fontsize=6.8, color=COLORS["ink"]
    )
    ax1.set_title(
        "A: Latency vs. Throughput Pareto Frontier",
        fontsize=7.8,
        fontweight="bold",
        color=COLORS["ink"],
    )
    ax1.grid(True, which="both", color=COLORS["grid"], linewidth=0.5, zorder=0)

    # --- Panel B: Memory Bandwidth vs Energy Efficiency ---
    for sys_name, x, y, fam in zip(systems, bandwidth, eff, families):
        c = color_map.get(fam, COLORS["ink"])
        marker = "s" if "SRAM" in fam else "o"
        ax2.scatter(
            x, y, color=c, s=55, alpha=0.9, marker=marker, edgecolors="none", zorder=4
        )

        short_name = sys_name.split(" (")[0]
        ax2.annotate(
            short_name,
            (x, y),
            xytext=(x * 1.15, y - 1.2),
            fontsize=5.5,
            color=COLORS["ink"],
            fontweight="bold",
        )

    ax2.set_xscale("log")
    ax2.set_xlabel(
        "Memory Bandwidth (TB/s - Log Scale)", fontsize=6.8, color=COLORS["ink"]
    )
    ax2.set_ylabel(
        "Energy Efficiency (Tokens/s / Watt)", fontsize=6.8, color=COLORS["ink"]
    )
    ax2.set_title(
        "B: HBM Bandwidth vs. SRAM Efficiency Wall",
        fontsize=7.8,
        fontweight="bold",
        color=COLORS["ink"],
    )
    ax2.grid(True, which="both", color=COLORS["grid"], linewidth=0.5, zorder=0)

    plt.tight_layout()
    plt.savefig(out_plot, dpi=300, bbox_inches="tight")
    print(f"LLM Inference Pareto Frontier plot saved to '{out_plot}'")


if __name__ == "__main__":
    main()
