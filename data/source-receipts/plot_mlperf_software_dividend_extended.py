"""
MLPerf Extended Longitudinal Software Dividend & Inference Kernel Fragmentation Plotter
======================================================================================
Visualizes:
1. In-Place Software Dividend vs. Generational Silicon Hardware Leaps (1.5x - 3.8x software maturation on fixed silicon).
2. Custom Kernel Proliferation & The Software Porting Wall Across Leading LLM Serving Engines (vLLM, TensorRT-LLM, SGLang, TGI).
3. Master Composite 4-Panel Executive Visualization connecting software dividends directly to custom kernel growth.

Saves publication-quality figures (PNG at 300 DPI, PDF vector, SVG) into:
  - data/source-receipts/
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

RECEIPTS_DIR = REPO_ROOT / "data" / "source-receipts"


def load_receipt(filename: str) -> list[dict]:
    """Loads a CSV receipt from data/source-receipts."""
    path = RECEIPTS_DIR / filename
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        # Skip comment lines starting with '#'
        lines = [line for line in f if not line.startswith("#")]
        reader = csv.DictReader(l for l in lines if not l.startswith("#"))
        for r in reader:
            rows.append(r)
    return rows


def plot_mlperf_software_dividend() -> tuple[Path, Path, Path]:
    """Generates Figure 1: The Longitudinal Software Dividend on Fixed Silicon vs Hardware Leaps."""
    out_svg = RECEIPTS_DIR / "mlperf_longitudinal_software_dividend.svg"
    out_pdf = RECEIPTS_DIR / "mlperf_longitudinal_software_dividend.pdf"
    out_png = RECEIPTS_DIR / "mlperf_longitudinal_software_dividend.png"

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(8.6, 3.8), gridspec_kw={"width_ratios": [1.14, 1.0]}
    )
    fig.subplots_adjust(wspace=0.35, left=0.08, right=0.96, top=0.88, bottom=0.18)

    # -------------------------------------------------------------
    # Panel A: The Fixed-Silicon Software Dividend (Normalized Throughput over Months)
    # -------------------------------------------------------------
    v100_m = [0, 7, 19]
    v100_t = [1.0, 2.32, 3.82]

    a100_m = [0, 11, 16, 23]
    a100_t = [1.0, 2.32, 2.45, 2.69]

    tpu4_m = [0, 12]
    tpu4_t = [1.0, 1.50]

    h100_m = [0, 7, 12, 17, 36]
    h100_t = [1.0, 1.17, 1.27, 1.30, 1.48]

    h100_inf_m = [0, 6, 13, 25]
    h100_inf_t = [1.0, 1.12, 1.28, 1.45]

    tpu6e_m = [0, 12]
    tpu6e_t = [1.0, 1.42]

    mi300_m = [0, 12]
    mi300_t = [1.0, 1.32]

    ax1.plot(
        v100_m,
        v100_t,
        marker="o",
        color=COLORS["purple"],
        linewidth=1.7,
        markersize=4.6,
        label="V100 (12nm, ResNet-50: 3.82x in 19 mo)",
        zorder=4,
    )
    ax1.plot(
        a100_m,
        a100_t,
        marker="s",
        color=COLORS["blue"],
        linewidth=1.7,
        markersize=4.6,
        label="A100 (7nm, BERT-Large: 2.69x in 23 mo)",
        zorder=4,
    )
    ax1.plot(
        h100_m,
        h100_t,
        marker="D",
        color=COLORS["red"],
        linewidth=1.5,
        markersize=4.2,
        label="H100 Train (4N, Suite: 1.48x in 36 mo)",
        zorder=3,
    )
    ax1.plot(
        h100_inf_m,
        h100_inf_t,
        marker="v",
        color=COLORS["orange"],
        linewidth=1.4,
        linestyle="-.",
        markersize=4.2,
        label="H100 Inf (4N, Llama 2: 1.45x in 25 mo)",
        zorder=3,
    )
    ax1.plot(
        tpu4_m,
        tpu4_t,
        marker="^",
        color=COLORS["green"],
        linewidth=1.3,
        linestyle="--",
        markersize=4.2,
        label="TPU v4 (7nm, Suite: 1.50x in 12 mo)",
        zorder=2,
    )
    ax1.plot(
        tpu6e_m,
        tpu6e_t,
        marker="P",
        color="#059669",
        linewidth=1.2,
        linestyle=":",
        markersize=4.2,
        label="TPU v6e (4nm, Llama 2: 1.42x in 12 mo)",
        zorder=2,
    )
    ax1.plot(
        mi300_m,
        mi300_t,
        marker="X",
        color="#B45309",
        linewidth=1.2,
        linestyle=":",
        markersize=4.2,
        label="MI300X (ROCm, Llama 2: 1.32x in 12 mo)",
        zorder=2,
    )

    # Key Milestone Annotations
    ax1.annotate(
        "DALI NVJPEG +\nCBR Fusion",
        (7, 2.32),
        xytext=(-26, 14),
        textcoords="offset points",
        fontsize=4.7,
        color=COLORS["purple"],
        fontweight="bold",
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="white",
            edgecolor=COLORS["grid"],
            alpha=0.92,
            lw=0.5,
        ),
    )
    ax1.annotate(
        "Apex Fused MHA +\nCUDA Graphs",
        (11, 2.32),
        xytext=(8, -14),
        textcoords="offset points",
        fontsize=4.7,
        color=COLORS["blue"],
        fontweight="bold",
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="white",
            edgecolor=COLORS["grid"],
            alpha=0.92,
            lw=0.5,
        ),
    )
    ax1.annotate(
        "FlashAttention-3 +\nAsync TMA-2",
        (36, 1.48),
        xytext=(-52, 10),
        textcoords="offset points",
        fontsize=4.7,
        color=COLORS["red"],
        fontweight="bold",
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="white",
            edgecolor=COLORS["grid"],
            alpha=0.92,
            lw=0.5,
        ),
    )

    ax1.set_xlim(-1, 39)
    ax1.set_ylim(0.8, 4.4)
    ax1.set_xlabel("Months Since Silicon Hardware Deployment", fontsize=6.6)
    ax1.set_ylabel("Normalized In-Place Throughput Multiplier", fontsize=6.6)
    ax1.tick_params(axis="both", labelsize=5.6)
    ax1.set_title(
        "A. The Fixed-Silicon Software Dividend (2018-2026)",
        fontsize=7.4,
        fontweight="bold",
        pad=8,
    )
    ax1.grid(True, color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax1.legend(
        loc="upper left",
        fontsize=4.5,
        frameon=True,
        facecolor="white",
        edgecolor=COLORS["grid"],
        framealpha=0.95,
        borderpad=0.3,
    )

    # -------------------------------------------------------------
    # Panel B: Hardware Generational Steps vs. In-Place Software Gains
    # -------------------------------------------------------------
    generations = [
        "Volta V100\n(12nm FFN)",
        "Ampere A100\n(7nm N7)",
        "Hopper H100\n(4N TSMC)",
        "Blackwell B200\n(4NP Dual-Die)",
    ]
    hw_base = [1.0, 8.0, 60.0, 156.0]
    sw_peak = [3.82, 21.5, 88.8, 215.3]

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
        label="Silicon Hardware Debut Baseline",
        color=COLORS["ink"],
        alpha=0.88,
        zorder=3,
    )
    rects2 = ax2.bar(
        x_gen + width / 2,
        s_heights,
        width,
        bottom=y_min,
        label="Mature Stack (+SW Dividend Peak)",
        color=COLORS["orange"],
        alpha=0.92,
        zorder=3,
    )

    ax2.set_yscale("log")
    ax2.set_ylim(0.5, 450)
    ax2.set_xticks(x_gen)
    ax2.set_xticklabels(generations, fontsize=5.2, color=COLORS["ink"])
    ax2.set_ylabel("BERT/LLM Throughput (rel. to V100 Debut, Log Scale)", fontsize=6.6)
    ax2.tick_params(axis="both", labelsize=5.6)
    ax2.set_title(
        "B. Hardware Steps vs. In-Place Software Expansion",
        fontsize=7.4,
        fontweight="bold",
        pad=8,
    )
    ax2.grid(True, which="both", color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax2.legend(
        loc="upper left",
        fontsize=4.8,
        frameon=True,
        facecolor="white",
        edgecolor=COLORS["grid"],
        framealpha=0.95,
        borderpad=0.3,
    )

    for i, (bar1, bar2, h_val, s_val) in enumerate(
        zip(rects1, rects2, hw_base, sw_peak)
    ):
        # Debut label
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
        # Mature label
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
    print(f"Generated: {out_png}, {out_pdf}, {out_svg}")
    return out_png, out_pdf, out_svg


def plot_inference_kernel_fragmentation() -> tuple[Path, Path, Path]:
    """Generates Figure 2: The Software Porting Wall & Inference Custom Kernel Explosion."""
    out_svg = RECEIPTS_DIR / "inference_kernel_fragmentation.svg"
    out_pdf = RECEIPTS_DIR / "inference_kernel_fragmentation.pdf"
    out_png = RECEIPTS_DIR / "inference_kernel_fragmentation.png"

    kernel_data = load_receipt("inference_kernel_fragmentation.csv")

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(8.6, 3.8), gridspec_kw={"width_ratios": [1.08, 1.04]}
    )
    fig.subplots_adjust(wspace=0.35, left=0.08, right=0.96, top=0.88, bottom=0.18)

    # -------------------------------------------------------------
    # Panel A: Custom Kernel LOC Growth Curve Across Runtimes (2023-2026)
    # -------------------------------------------------------------
    engines = {
        "vLLM": ([], []),
        "TensorRT-LLM": ([], []),
        "SGLang": ([], []),
        "TGI": ([], []),
    }

    for row in kernel_data:
        eng = row["engine"]
        if eng in engines:
            parts = [int(x) for x in row["release_date"].split("-")]
            year_frac = parts[0] + (parts[1] - 1) / 12.0 + parts[2] / 365.0
            kernel_loc_k = float(row["total_custom_kernel_loc"]) / 1000.0
            engines[eng][0].append(year_frac)
            engines[eng][1].append(kernel_loc_k)

    engine_styles = {
        "TensorRT-LLM": (COLORS["purple"], "o", "-", "TensorRT-LLM (NVIDIA, 342K LOC)"),
        "vLLM": (COLORS["blue"], "s", "-", "vLLM (UC Berkeley / Red Hat, 120K LOC)"),
        "SGLang": (COLORS["red"], "^", "--", "SGLang (LMSYS / SGL-Kernel, 195K LOC)"),
        "TGI": (COLORS["green"], "D", "-.", "TGI (HuggingFace / Rust, 145K LOC)"),
    }

    for eng, (dates, locs) in engines.items():
        color, marker, lstyle, label = engine_styles[eng]
        ax1.plot(
            dates,
            locs,
            marker=marker,
            color=color,
            linewidth=1.6,
            linestyle=lstyle,
            markersize=4.4,
            label=label,
            zorder=4,
        )

    ax1.set_xlim(2023.3, 2026.8)
    ax1.set_ylim(0, 380)
    ax1.set_xticks([2023.5, 2024.0, 2024.5, 2025.0, 2025.5, 2026.0, 2026.5])
    ax1.set_xticklabels(
        ["'23-M", "'24", "'24-M", "'25", "'25-M", "'26", "'26-M"], fontsize=5.6
    )
    ax1.set_xlabel("Release Timeline (2023 - 2026)", fontsize=6.6)
    ax1.set_ylabel("Custom Handwritten Kernel LOC (Thousands)", fontsize=6.6)
    ax1.tick_params(axis="both", labelsize=5.6)
    ax1.set_title(
        "A. Proliferation of Custom Handwritten Kernels",
        fontsize=7.4,
        fontweight="bold",
        pad=8,
    )
    ax1.grid(True, color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax1.legend(
        loc="upper left",
        fontsize=4.6,
        frameon=True,
        facecolor="white",
        edgecolor=COLORS["grid"],
        framealpha=0.95,
        borderpad=0.3,
    )

    ax1.annotate(
        "82x Kernel Proliferation\nin 36 Months",
        xy=(2026.55, 342),
        xytext=(2024.6, 290),
        fontsize=4.8,
        fontweight="bold",
        color=COLORS["purple"],
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor=COLORS["note_fill"],
            edgecolor=COLORS["purple"],
            linewidth=0.7,
        ),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS["purple"],
            lw=0.8,
            connectionstyle="arc3,rad=-0.15",
        ),
        zorder=6,
    )

    # -------------------------------------------------------------
    # Panel B: Functional Subsystem Breakdown in 2026 (Stack Bar Chart)
    # -------------------------------------------------------------
    latest_entries = {}
    for row in kernel_data:
        latest_entries[row["engine"]] = row

    engine_names = [
        "vLLM\n(v0.27)",
        "SGLang\n(v0.6.0)",
        "TGI\n(v3.0.0)",
        "TensorRT-LLM\n(v1.5.0)",
    ]
    keys = ["vLLM", "SGLang", "TGI", "TensorRT-LLM"]

    attn_k = [float(latest_entries[k]["attention_kernel_loc"]) / 1000.0 for k in keys]
    quant_k = [
        float(latest_entries[k]["quantization_kernel_loc"]) / 1000.0 for k in keys
    ]
    moe_k = [float(latest_entries[k]["moe_dispatch_kernel_loc"]) / 1000.0 for k in keys]
    comm_k = [
        float(latest_entries[k]["collective_comm_kernel_loc"]) / 1000.0 for k in keys
    ]
    arch_k = [float(latest_entries[k]["backend_arch_loc"]) / 1000.0 for k in keys]

    x_b = np.arange(len(keys))
    w_b = 0.52

    b1 = ax2.bar(
        x_b,
        attn_k,
        w_b,
        label="Attention (Paged/Flash/MLA)",
        color=COLORS["purple"],
        zorder=3,
    )
    b2 = ax2.bar(
        x_b,
        quant_k,
        w_b,
        bottom=attn_k,
        label="Quant (FP8/FP4/Marlin/AWQ)",
        color=COLORS["orange"],
        zorder=3,
    )
    b3 = ax2.bar(
        x_b,
        moe_k,
        w_b,
        bottom=np.array(attn_k) + np.array(quant_k),
        label="Dynamic MoE Dispatch & Group GEMM",
        color=COLORS["red"],
        zorder=3,
    )
    b4 = ax2.bar(
        x_b,
        comm_k,
        w_b,
        bottom=np.array(attn_k) + np.array(quant_k) + np.array(moe_k),
        label="Custom Collective Comm / NVLink",
        color=COLORS["blue"],
        zorder=3,
    )
    b5 = ax2.bar(
        x_b,
        arch_k,
        w_b,
        bottom=np.array(attn_k)
        + np.array(quant_k)
        + np.array(moe_k)
        + np.array(comm_k),
        label="Arch Specialization (SM90/SM100/CDNA)",
        color="#94A3B8",
        zorder=3,
    )

    ax2.set_xticks(x_b)
    ax2.set_xticklabels(engine_names, fontsize=5.4, color=COLORS["ink"])
    ax2.set_ylabel("Custom Kernel LOC Breakdown (Thousands)", fontsize=6.6)
    ax2.set_ylim(0, 390)
    ax2.tick_params(axis="both", labelsize=5.6)
    ax2.set_title(
        "B. Kernel Specialization Subsystems (2026 State)",
        fontsize=7.4,
        fontweight="bold",
        pad=8,
    )
    ax2.grid(axis="y", color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax2.legend(
        loc="upper left",
        fontsize=4.5,
        frameon=True,
        facecolor="white",
        edgecolor=COLORS["grid"],
        framealpha=0.95,
        borderpad=0.3,
    )

    # Annotate total LOC on top of bars
    for i, k in enumerate(keys):
        tot = float(latest_entries[k]["total_custom_kernel_loc"]) / 1000.0
        ax2.text(
            x_b[i],
            tot + 8,
            f"{tot:.1f}K",
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
    print(f"Generated: {out_png}, {out_pdf}, {out_svg}")
    return out_png, out_pdf, out_svg


def plot_master_composite() -> tuple[Path, Path, Path]:
    """Generates a 4-panel master money plot linking software dividend to custom kernel fragmentation."""
    out_svg = RECEIPTS_DIR / "mlperf_software_dividend_extended_master.svg"
    out_pdf = RECEIPTS_DIR / "mlperf_software_dividend_extended_master.pdf"
    out_png = RECEIPTS_DIR / "mlperf_software_dividend_extended_master.png"

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(9.8, 7.2))
    fig.subplots_adjust(
        wspace=0.32, hspace=0.36, left=0.08, right=0.96, top=0.93, bottom=0.09
    )

    # 1. Panel A: In-Place Dividend
    v100_m, v100_t = [0, 7, 19], [1.0, 2.32, 3.82]
    a100_m, a100_t = [0, 11, 16, 23], [1.0, 2.32, 2.45, 2.69]
    tpu4_m, tpu4_t = [0, 12], [1.0, 1.50]
    h100_m, h100_t = [0, 7, 12, 17, 36], [1.0, 1.17, 1.27, 1.30, 1.48]
    h100_inf_m, h100_inf_t = [0, 6, 13, 25], [1.0, 1.12, 1.28, 1.45]

    ax1.plot(
        v100_m,
        v100_t,
        marker="o",
        color=COLORS["purple"],
        linewidth=1.5,
        markersize=4,
        label="V100 (3.82x in 19 mo)",
    )
    ax1.plot(
        a100_m,
        a100_t,
        marker="s",
        color=COLORS["blue"],
        linewidth=1.5,
        markersize=4,
        label="A100 (2.69x in 23 mo)",
    )
    ax1.plot(
        h100_m,
        h100_t,
        marker="D",
        color=COLORS["red"],
        linewidth=1.5,
        markersize=4,
        label="H100 Train (1.48x in 36 mo)",
    )
    ax1.plot(
        h100_inf_m,
        h100_inf_t,
        marker="v",
        color=COLORS["orange"],
        linewidth=1.3,
        linestyle="-.",
        markersize=4,
        label="H100 Inf (1.45x in 25 mo)",
    )
    ax1.plot(
        tpu4_m,
        tpu4_t,
        marker="^",
        color=COLORS["green"],
        linewidth=1.3,
        linestyle="--",
        markersize=4,
        label="TPU v4 (1.50x in 12 mo)",
    )

    ax1.set_xlim(-1, 39)
    ax1.set_ylim(0.8, 4.4)
    ax1.set_xlabel("Months Since Silicon Hardware Deployment", fontsize=6.2)
    ax1.set_ylabel("In-Place Throughput Multiplier", fontsize=6.2)
    ax1.tick_params(axis="both", labelsize=5.4)
    ax1.set_title(
        "A. Fixed-Silicon Software Dividend (2018-2026)",
        fontsize=7.2,
        fontweight="bold",
        pad=6,
    )
    ax1.grid(True, color=COLORS["grid"], linewidth=0.5)
    ax1.legend(
        loc="upper left",
        fontsize=4.6,
        frameon=True,
        facecolor="white",
        edgecolor=COLORS["grid"],
        framealpha=0.95,
    )

    # 2. Panel B: Hardware Generational Steps vs Software Peak
    generations = ["V100\n(12nm)", "A100\n(7nm)", "H100\n(4N)", "B200\n(4NP)"]
    hw_base = [1.0, 8.0, 60.0, 156.0]
    sw_peak = [3.82, 21.5, 88.8, 215.3]
    x_gen = np.arange(len(generations))
    w = 0.32
    rects1 = ax2.bar(
        x_gen - w / 2,
        [h - 0.5 for h in hw_base],
        w,
        bottom=0.5,
        label="Silicon Debut",
        color=COLORS["ink"],
        alpha=0.88,
    )
    rects2 = ax2.bar(
        x_gen + w / 2,
        [s - 0.5 for s in sw_peak],
        w,
        bottom=0.5,
        label="Mature SW Stack",
        color=COLORS["orange"],
        alpha=0.92,
    )
    ax2.set_yscale("log")
    ax2.set_ylim(0.5, 450)
    ax2.set_xticks(x_gen)
    ax2.set_xticklabels(generations, fontsize=5.2)
    ax2.set_ylabel("BERT/LLM Speedup (rel. to V100 Debut, Log)", fontsize=6.2)
    ax2.tick_params(axis="both", labelsize=5.4)
    ax2.set_title(
        "B. Hardware Generational Steps vs. Software Maturation",
        fontsize=7.2,
        fontweight="bold",
        pad=6,
    )
    ax2.grid(True, which="both", color=COLORS["grid"], linewidth=0.5)
    ax2.legend(
        loc="upper left",
        fontsize=4.8,
        frameon=True,
        facecolor="white",
        edgecolor=COLORS["grid"],
        framealpha=0.95,
    )

    for bar1, bar2, h_val, s_val in zip(rects1, rects2, hw_base, sw_peak):
        ax2.text(
            bar1.get_x() + bar1.get_width() / 2,
            h_val * 1.22,
            f"{h_val:.0f}x",
            ha="center",
            va="bottom",
            fontsize=4.6,
            fontweight="bold",
            color=COLORS["ink"],
        )
        ax2.text(
            bar2.get_x() + bar2.get_width() / 2,
            s_val * 1.22,
            f"{s_val:.1f}x",
            ha="center",
            va="bottom",
            fontsize=4.6,
            fontweight="bold",
            color=COLORS["orange"],
        )

    # 3. Panel C: Kernel Proliferation Curves
    kernel_data = load_receipt("inference_kernel_fragmentation.csv")
    engines = {
        "vLLM": ([], []),
        "TensorRT-LLM": ([], []),
        "SGLang": ([], []),
        "TGI": ([], []),
    }
    for row in kernel_data:
        eng = row["engine"]
        if eng in engines:
            parts = [int(x) for x in row["release_date"].split("-")]
            year_frac = parts[0] + (parts[1] - 1) / 12.0 + parts[2] / 365.0
            engines[eng][0].append(year_frac)
            engines[eng][1].append(float(row["total_custom_kernel_loc"]) / 1000.0)

    ax3.plot(
        engines["TensorRT-LLM"][0],
        engines["TensorRT-LLM"][1],
        marker="o",
        color=COLORS["purple"],
        linewidth=1.5,
        label="TensorRT-LLM (342K LOC)",
    )
    ax3.plot(
        engines["SGLang"][0],
        engines["SGLang"][1],
        marker="^",
        color=COLORS["red"],
        linewidth=1.5,
        linestyle="--",
        label="SGLang (195K LOC)",
    )
    ax3.plot(
        engines["TGI"][0],
        engines["TGI"][1],
        marker="D",
        color=COLORS["green"],
        linewidth=1.3,
        linestyle="-.",
        label="TGI (145K LOC)",
    )
    ax3.plot(
        engines["vLLM"][0],
        engines["vLLM"][1],
        marker="s",
        color=COLORS["blue"],
        linewidth=1.5,
        label="vLLM (120K LOC)",
    )

    ax3.set_xlim(2023.3, 2026.8)
    ax3.set_ylim(0, 380)
    ax3.set_xticks([2023.5, 2024.5, 2025.5, 2026.5])
    ax3.set_xticklabels(["2023.5", "2024.5", "2025.5", "2026.5"], fontsize=5.4)
    ax3.set_xlabel("Release Timeline (2023-2026)", fontsize=6.2)
    ax3.set_ylabel("Custom Kernel LOC (Thousands)", fontsize=6.2)
    ax3.tick_params(axis="both", labelsize=5.4)
    ax3.set_title(
        "C. Inference Engine Custom Kernel Proliferation",
        fontsize=7.2,
        fontweight="bold",
        pad=6,
    )
    ax3.grid(True, color=COLORS["grid"], linewidth=0.5)
    ax3.legend(
        loc="upper left",
        fontsize=4.6,
        frameon=True,
        facecolor="white",
        edgecolor=COLORS["grid"],
        framealpha=0.95,
    )

    # 4. Panel D: Kernel Subsystem Breakdown
    latest_entries = {row["engine"]: row for row in kernel_data}
    keys = ["vLLM", "SGLang", "TGI", "TensorRT-LLM"]
    attn_k = [float(latest_entries[k]["attention_kernel_loc"]) / 1000.0 for k in keys]
    quant_k = [
        float(latest_entries[k]["quantization_kernel_loc"]) / 1000.0 for k in keys
    ]
    moe_k = [float(latest_entries[k]["moe_dispatch_kernel_loc"]) / 1000.0 for k in keys]
    comm_k = [
        float(latest_entries[k]["collective_comm_kernel_loc"]) / 1000.0 for k in keys
    ]
    arch_k = [float(latest_entries[k]["backend_arch_loc"]) / 1000.0 for k in keys]

    x_d = np.arange(len(keys))
    w_d = 0.52
    ax4.bar(x_d, attn_k, w_d, label="Attention", color=COLORS["purple"])
    ax4.bar(
        x_d, quant_k, w_d, bottom=attn_k, label="Quantization", color=COLORS["orange"]
    )
    ax4.bar(
        x_d,
        moe_k,
        w_d,
        bottom=np.array(attn_k) + np.array(quant_k),
        label="MoE Dispatch",
        color=COLORS["red"],
    )
    ax4.bar(
        x_d,
        comm_k,
        w_d,
        bottom=np.array(attn_k) + np.array(quant_k) + np.array(moe_k),
        label="Collectives",
        color=COLORS["blue"],
    )
    ax4.bar(
        x_d,
        arch_k,
        w_d,
        bottom=np.array(attn_k)
        + np.array(quant_k)
        + np.array(moe_k)
        + np.array(comm_k),
        label="Arch-Specific",
        color="#94A3B8",
    )

    ax4.set_xticks(x_d)
    ax4.set_xticklabels(["vLLM", "SGLang", "TGI", "TRT-LLM"], fontsize=5.4)
    ax4.set_ylabel("Kernel LOC Breakdown (Thousands)", fontsize=6.2)
    ax4.set_ylim(0, 390)
    ax4.tick_params(axis="both", labelsize=5.4)
    ax4.set_title(
        "D. Custom Kernel Subsystem Specialization (2026)",
        fontsize=7.2,
        fontweight="bold",
        pad=6,
    )
    ax4.grid(axis="y", color=COLORS["grid"], linewidth=0.5)
    ax4.legend(
        loc="upper left",
        fontsize=4.4,
        frameon=True,
        facecolor="white",
        edgecolor=COLORS["grid"],
        framealpha=0.95,
    )

    for i, k in enumerate(keys):
        tot = float(latest_entries[k]["total_custom_kernel_loc"]) / 1000.0
        ax4.text(
            x_d[i],
            tot + 8,
            f"{tot:.1f}K",
            ha="center",
            va="bottom",
            fontsize=4.6,
            fontweight="bold",
            color=COLORS["ink"],
        )

    plt.savefig(out_svg, format="svg", bbox_inches="tight")
    plt.savefig(out_pdf, format="pdf", bbox_inches="tight")
    plt.savefig(out_png, format="png", dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Generated: {out_png}, {out_pdf}, {out_svg}")
    return out_png, out_pdf, out_svg


def main() -> None:
    print(
        "Generating publication-quality MLPerf software dividend & kernel proliferation plots..."
    )
    plot_mlperf_software_dividend()
    plot_inference_kernel_fragmentation()
    plot_master_composite()
    print("All plots generated successfully.")


if __name__ == "__main__":
    main()
