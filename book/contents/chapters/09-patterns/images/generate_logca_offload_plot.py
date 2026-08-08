"""Generate LogCA Break-Even Offload Speedup Frontier plot for Ch09.

This script implements the LogCA (Logistics-based Communication and Acceleration)
analytical model to project net offload speedup frontiers across payload sizes
for model compression and decompression offloading across interconnects.
"""

from __future__ import annotations

import os
import sys

# Ensure repository root is in sys.path
repo_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import numpy as np
import matplotlib.pyplot as plt
from book.tools.figures import style as book_style


def generate_plot(output_dir: str | None = None) -> str:
    """Generate and save the LogCA break-even offload speedup frontier plot."""
    fig, ax, COLORS, plt_mod = book_style.setup_plot(figsize=(9, 4.8))

    # Payload sizes in bytes (1 KB to 100 MB on log scale)
    payload_kb = np.logspace(0, 5, 200)  # 1 KB to 100,000 KB (100 MB)
    payload_bytes = payload_kb * 1024.0

    # Host execution throughput (12 GB/s CPU decompression rate)
    beta_host = 12.0e9  # B/s

    # Offload configuration parameters
    # 1. NVLink-C2C: Latency 2 us, Interconnect 900 GB/s, Accel 250 GB/s
    l_nvlink = 2.0e-6
    beta_nvlink = 900.0e9
    accel_nvlink = 250.0e9

    # 2. PCIe Gen5 x16: Latency 12 us, Interconnect 128 GB/s, Accel 200 GB/s
    l_gen5 = 12.0e-6
    beta_gen5 = 128.0e9
    accel_gen5 = 200.0e9

    # 3. PCIe Gen4 x16: Latency 18 us, Interconnect 64 GB/s, Accel 150 GB/s
    l_gen4 = 18.0e-6
    beta_gen4 = 64.0e9
    accel_gen4 = 150.0e9

    # Execution times
    t_host = payload_bytes / beta_host

    t_nvlink = l_nvlink + (payload_bytes / beta_nvlink) + (payload_bytes / accel_nvlink)
    t_gen5 = l_gen5 + (payload_bytes / beta_gen5) + (payload_bytes / accel_gen5)
    t_gen4 = l_gen4 + (payload_bytes / beta_gen4) + (payload_bytes / accel_gen4)

    # Speedups
    sp_nvlink = t_host / t_nvlink
    sp_gen5 = t_host / t_gen5
    sp_gen4 = t_host / t_gen4

    # Plot curves
    ax.plot(
        payload_kb,
        sp_nvlink,
        color=COLORS["GreenLine"],
        linewidth=2.2,
        label="NVLink-C2C (900 GB/s)",
    )
    ax.plot(
        payload_kb,
        sp_gen5,
        color=COLORS["BlueLine"],
        linewidth=2.2,
        label="PCIe Gen5 x16 (128 GB/s)",
    )
    ax.plot(
        payload_kb,
        sp_gen4,
        color=COLORS["OrangeLine"],
        linewidth=2.2,
        label="PCIe Gen4 x16 (64 GB/s)",
    )

    # Reference lines and regions
    ax.axhline(
        1.0,
        color="#444444",
        linestyle="--",
        linewidth=1.2,
        label="1.0x Break-Even Threshold",
    )
    ax.fill_between(
        payload_kb,
        1.0,
        16.0,
        color=COLORS["GreenFill"],
        alpha=0.25,
        label="Offload Advantage Zone",
    )
    ax.fill_between(
        payload_kb,
        0.0,
        1.0,
        color=COLORS["RedFill"],
        alpha=0.25,
        label="Interconnect Overhead Zone",
    )

    ax.set_xscale("log")
    ax.set_xlabel("Compression Payload Size (KB, Log Scale)")
    ax.set_ylabel("Net Offload Speedup Factor over Host CPU (x)")
    ax.set_xlim(1, 100000)
    ax.set_ylim(0, 16)

    # Key Annotations
    ax.annotate(
        "NVLink Break-Even (8 KB)",
        xy=(8, 1.0),
        xytext=(2, 3.5),
        arrowprops=dict(
            facecolor=COLORS["GreenLine"],
            edgecolor=COLORS["GreenLine"],
            arrowstyle="->",
            lw=1.2,
        ),
        fontsize=8.5,
        color=COLORS["GreenLine"],
        fontweight="bold",
    )

    ax.annotate(
        "PCIe Gen5 Break-Even (96 KB)",
        xy=(96, 1.0),
        xytext=(40, 4.8),
        arrowprops=dict(
            facecolor=COLORS["BlueLine"],
            edgecolor=COLORS["BlueLine"],
            arrowstyle="->",
            lw=1.2,
        ),
        fontsize=8.5,
        color=COLORS["BlueLine"],
        fontweight="bold",
    )

    ax.annotate(
        "Asymptotic Bandwidth Limit (~13x)",
        xy=(50000, 12.8),
        xytext=(3000, 14.2),
        arrowprops=dict(
            facecolor=COLORS["GreenLine"],
            edgecolor=COLORS["GreenLine"],
            arrowstyle="->",
            lw=1.2,
        ),
        fontsize=8.5,
        color=COLORS["GreenLine"],
        fontweight="bold",
    )

    ax.set_title(
        "LogCA Analytical Break-Even Offload Speedup Frontier across Interconnects",
        pad=12,
    )

    ax.legend(loc="upper left", framealpha=0.9, fontsize=8.5)

    fig = book_style.finalize_web_figure(fig)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        png_path = os.path.join(output_dir, "logca_offload_break_even.png")
        svg_path = os.path.join(output_dir, "logca_offload_break_even.svg")
        fig.savefig(png_path, dpi=300, bbox_inches="tight")
        fig.savefig(svg_path, bbox_inches="tight")
        plt.close(fig)
        return png_path

    return ""


if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    saved_file = generate_plot(out_dir)
    print(f"Plot successfully saved to {saved_file}")
