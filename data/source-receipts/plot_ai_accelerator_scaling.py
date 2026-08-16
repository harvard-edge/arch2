"""
AI Accelerator Scaling Frontier Plot (2012-2026)
------------------------------------------------
Visualizes 14 years of AI accelerator scaling across landmark chips:
Panel A: Multi-vector scaling of Peak Compute (TFLOPS), Memory Bandwidth (GB/s),
         and Thermal Power (TDP in Watts), highlighting the Packaging Inflection (Reticle Limit).
Panel B: The Arithmetic Ratio / Operational Intensity Wall (Bytes per FLOP collapse),
         contrasting HBM-based architectures against On-Chip SRAM architectures.
"""

import csv
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

# Ensure root is in path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style

apply_style()


def main():
    csv_file = (
        REPO_ROOT
        / "data"
        / "source-receipts"
        / "chapter2-ai-accelerator-scaling-frontier.csv"
    )
    out_svg = (
        REPO_ROOT
        / "book"
        / "contents"
        / "chapters"
        / "02-pressures"
        / "images"
        / "fig-ch02-accelerator-scaling-frontier.svg"
    )
    out_pdf = (
        REPO_ROOT
        / "book"
        / "contents"
        / "chapters"
        / "02-pressures"
        / "images"
        / "fig-ch02-accelerator-scaling-frontier.pdf"
    )
    out_png = (
        REPO_ROOT
        / "book"
        / "contents"
        / "chapters"
        / "02-pressures"
        / "images"
        / "fig-ch02-accelerator-scaling-frontier.png"
    )
    out_svg.parent.mkdir(parents=True, exist_ok=True)

    chips = []
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader((row for row in f if not row.startswith("#")))
        for row in reader:
            chips.append(
                {
                    "name": row["Chip_Name"],
                    "vendor": row["Vendor"],
                    "year": float(row["Release_Year"]),
                    "node": row["Process_Node"],
                    "die_area": float(row["Die_Area_mm2"]),
                    "tdp": float(row["TDP_Watts"]),
                    "fp32": float(row["Peak_FP32_TFLOPS"]),
                    "fp16": float(row["Peak_FP16_BF16_TFLOPS"]),
                    "fp8": float(row["Peak_FP8_TFLOPS"]),
                    "fp4": float(row["Peak_FP4_TFLOPS"]),
                    "mem_tech": row["Memory_Technology"],
                    "mem_bw": float(row["Memory_Bandwidth_GBs"]),
                    "bytes_per_flop": float(row["Bytes_Per_FLOP_Primary"]),
                    "op_intensity": float(row["Operational_Intensity_FLOP_Per_Byte"]),
                }
            )

    # Filter frontier tracking chips for Nvidia & TPU timeline
    frontier_nvidia = [c for c in chips if c["vendor"] == "NVIDIA"]
    frontier_tpu = [c for c in chips if c["vendor"] == "Google"]
    sram_chips = [
        c
        for c in chips
        if "SRAM" in c["mem_tech"] and c["vendor"] in ["Groq", "Cerebras"]
    ]

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(7.5, 3.6), gridspec_kw={"width_ratios": [1.12, 1.05]}
    )
    fig.subplots_adjust(wspace=0.36, left=0.09, right=0.96, top=0.88, bottom=0.18)

    # -------------------------------------------------------------
    # Panel A: Multi-Vector Scaling (Compute, Memory BW, TDP)
    # -------------------------------------------------------------
    nv_years = [c["year"] for c in frontier_nvidia]
    nv_compute = [c["fp16"] if c["fp16"] > 0 else c["fp32"] for c in frontier_nvidia]
    # For H100 and B200, take peak dense low-precision (FP8/FP4) as upper frontier
    nv_compute_max = [max(c["fp16"], c["fp8"], c["fp4"]) for c in frontier_nvidia]
    nv_bw = [c["mem_bw"] for c in frontier_nvidia]
    nv_tdp = [c["tdp"] for c in frontier_nvidia]

    ax1.plot(
        nv_years,
        nv_compute_max,
        marker="o",
        color=COLORS["purple"],
        linewidth=1.8,
        markersize=4.5,
        label="Peak Compute (Dense TFLOPS, +1100x)",
        zorder=4,
    )
    ax1.plot(
        nv_years,
        nv_bw,
        marker="s",
        color=COLORS["blue"],
        linewidth=1.6,
        markersize=4.0,
        label="Memory Bandwidth (GB/s, +32x)",
        zorder=3,
    )
    ax1.plot(
        nv_years,
        nv_tdp,
        marker="^",
        color=COLORS["red"],
        linewidth=1.5,
        linestyle="--",
        markersize=4.0,
        label="Thermal Power / TDP (Watts, +4.3x)",
        zorder=2,
    )

    # Annotations on specific chips with clear placement
    for c in frontier_nvidia:
        short_name = (
            c["name"].replace("NVIDIA ", "").replace("Tesla ", "").split(" (")[0]
        )
        y_pos = max(c["fp16"], c["fp8"], c["fp4"])
        if short_name == "Kepler K20X":
            ax1.annotate(
                f"{short_name}\n(3.9 TF / 250W)",
                (c["year"], y_pos),
                xytext=(8, -6),
                textcoords="offset points",
                fontsize=5.0,
                color=COLORS["ink"],
                fontweight="bold",
            )
        elif short_name == "Volta V100":
            ax1.annotate(
                f"{short_name}\n(125 TF / 1st TC)",
                (c["year"], y_pos),
                xytext=(-12, 10),
                textcoords="offset points",
                fontsize=5.0,
                color=COLORS["ink"],
                fontweight="bold",
            )
        elif short_name == "Hopper H100":
            ax1.annotate(
                f"{short_name}\n(1979 TF / 700W)",
                (c["year"], y_pos),
                xytext=(-55, 6),
                textcoords="offset points",
                fontsize=5.0,
                color=COLORS["ink"],
                fontweight="bold",
            )
        elif short_name == "Blackwell B200":
            ax1.annotate(
                f"{short_name}\n(9000 TF FP4 / 1000W)",
                (c["year"], y_pos),
                xytext=(-65, -18),
                textcoords="offset points",
                fontsize=5.0,
                color=COLORS["ink"],
                fontweight="bold",
            )

    # Reticle limit transition line with clean boxed note
    ax1.axvline(2021.5, color=COLORS["orange"], linestyle=":", linewidth=1.2, zorder=1)
    ax1.text(
        2021.6,
        12.0,
        "Reticle Limit Wall (~858 mm²)\n→ 2.5D/3D Chiplets (CoWoS/SoIC)",
        fontsize=4.8,
        color=COLORS["orange"],
        fontweight="bold",
        rotation=90,
        va="bottom",
        ha="left",
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="white",
            edgecolor=COLORS["orange"],
            alpha=0.9,
            lw=0.6,
        ),
        zorder=5,
    )

    ax1.set_yscale("log")
    ax1.set_xlim(2011.5, 2025.5)
    ax1.set_ylim(1.0, 30000)
    ax1.set_xlabel("Release Year", fontsize=6.8)
    ax1.set_ylabel("Metric Value (Log Scale: TFLOPS, GB/s, Watts)", fontsize=6.6)
    ax1.set_title(
        "Panel A: 14-Year AI Accelerator Scaling Vectors",
        fontsize=7.6,
        fontweight="bold",
        pad=8,
    )
    ax1.grid(True, which="both", color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax1.legend(
        loc="upper left",
        fontsize=5.0,
        frameon=True,
        facecolor="white",
        edgecolor="none",
        borderpad=0.3,
    )

    # -------------------------------------------------------------
    # Panel B: Operational Intensity & Arithmetic Ratio Collapse
    # -------------------------------------------------------------
    # Plot Bytes per FLOP (Arithmetic Ratio) over time for HBM vs SRAM
    hbm_chips = [c for c in chips if "HBM" in c["mem_tech"] or "GDDR" in c["mem_tech"]]

    # Scatter for HBM chips
    x_hbm = [c["year"] for c in hbm_chips]
    y_hbm = [c["bytes_per_flop"] for c in hbm_chips]
    ax2.scatter(
        x_hbm,
        y_hbm,
        color=COLORS["blue"],
        s=28,
        alpha=0.85,
        label="HBM / DRAM (GPU/TPU/Gaudi)",
        zorder=3,
    )

    # Connect Nvidia trend line
    nv_bpf = [c["bytes_per_flop"] for c in frontier_nvidia]
    ax2.plot(
        nv_years, nv_bpf, color=COLORS["blue"], linewidth=1.4, linestyle="-", zorder=2
    )

    # Scatter for on-chip SRAM architectures
    x_sram = [c["year"] for c in sram_chips]
    y_sram = [c["bytes_per_flop"] for c in sram_chips]
    ax2.scatter(
        x_sram,
        y_sram,
        color=COLORS["green"],
        marker="D",
        s=34,
        label="On-Chip SRAM (Groq/Cerebras)",
        zorder=4,
    )

    # SRAM annotations positioned cleanly
    for c in sram_chips:
        sname = c["name"].replace("Groq ", "").replace("Cerebras ", "")
        if "WSE-1" in sname:
            ax2.annotate(
                f"{sname} ({c['bytes_per_flop']:.2f} B/F)",
                (c["year"], c["bytes_per_flop"]),
                xytext=(6, 4),
                textcoords="offset points",
                fontsize=4.8,
                color=COLORS["green"],
                fontweight="bold",
            )
        elif "WSE-2" in sname:
            ax2.annotate(
                f"{sname} ({c['bytes_per_flop']:.2f} B/F)",
                (c["year"], c["bytes_per_flop"]),
                xytext=(6, 4),
                textcoords="offset points",
                fontsize=4.8,
                color=COLORS["green"],
                fontweight="bold",
            )
        elif "LPU" in sname:
            ax2.annotate(
                f"{sname} ({c['bytes_per_flop']:.2f} B/F)",
                (c["year"], c["bytes_per_flop"]),
                xytext=(-65, -12),
                textcoords="offset points",
                fontsize=4.8,
                color=COLORS["green"],
                fontweight="bold",
            )
        elif "WSE-3" in sname:
            ax2.annotate(
                f"{sname} ({c['bytes_per_flop']:.2f} B/F)",
                (c["year"], c["bytes_per_flop"]),
                xytext=(-65, -8),
                textcoords="offset points",
                fontsize=4.8,
                color=COLORS["green"],
                fontweight="bold",
            )

    # Annotate K20X vs B200 collapse with clear box
    ax2.annotate(
        "Kepler K20X\n(0.064 B/F = 15.7 FLOP/B)",
        (2012, 0.0635),
        xytext=(8, 10),
        textcoords="offset points",
        fontsize=4.8,
        color=COLORS["ink"],
        bbox=dict(
            boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.85
        ),
    )
    ax2.annotate(
        "Blackwell B200 / Trillium\n(~0.002-0.003 B/F = 300-560 FLOP/B)",
        xy=(2024, 0.002),
        xytext=(2019.2, 0.00065),
        arrowprops=dict(arrowstyle="->", color=COLORS["red"], lw=0.8),
        fontsize=4.8,
        fontweight="bold",
        color=COLORS["red"],
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="white",
            edgecolor=COLORS["red"],
            alpha=0.9,
            lw=0.6,
        ),
        zorder=5,
    )

    ax2.set_yscale("log")
    ax2.set_xlim(2011.5, 2025.5)
    ax2.set_ylim(0.0005, 1.8)
    ax2.set_xlabel("Release Year", fontsize=6.8)
    ax2.set_ylabel("Arithmetic Ratio: Bytes per FLOP (Log Scale)", fontsize=6.6)
    ax2.set_title(
        "Panel B: Operational Intensity Wall (Byte/FLOP Collapse)",
        fontsize=7.6,
        fontweight="bold",
        pad=8,
    )
    ax2.grid(True, which="both", color=COLORS["grid"], linewidth=0.5, zorder=0)
    # Put legend in lower left with tight box
    ax2.legend(
        loc="lower left",
        bbox_to_anchor=(0.01, 0.01),
        fontsize=4.5,
        frameon=True,
        facecolor="white",
        edgecolor="none",
        borderpad=0.2,
    )

    plt.savefig(out_svg, format="svg", bbox_inches="tight")
    plt.savefig(out_pdf, format="pdf", bbox_inches="tight")
    plt.savefig(out_png, format="png", dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Generated AI Accelerator Scaling Frontier plot -> {out_svg} and {out_pdf}")


if __name__ == "__main__":
    main()
