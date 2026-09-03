"""Generate publication-grade 3-Panel Money Plot for Chapter 9:
The Software Porting Wall Across the AI Acceleration Stack (2019-2026).

Panel A: Hardware Primitive Specialization Tax (NVIDIA CUTLASS)
Panel B: Compiler Narrow Waist Absorption (Triton MLIR)
Panel C: Inference Runtime Custom Kernel Fragmentation (vLLM Engine)
"""

import csv
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Add repo root to sys.path
repo_root = Path(__file__).resolve().parents[5]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from book._python.plots import COLORS, apply_style


def load_csv(filepath: Path) -> list[dict]:
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(l for l in f if not l.startswith("#"))
        return list(reader)


def generate_figure(output_dir: Path) -> Path:
    apply_style()

    # Load CSV receipts
    receipts_dir = repo_root / "data" / "source-receipts"
    cutlass_rows = load_csv(receipts_dir / "chapter9-cutlass-porting-wall.csv")
    triton_rows = load_csv(receipts_dir / "chapter9-triton-narrow-waist.csv")
    vllm_rows = load_csv(receipts_dir / "chapter9-vllm-kernel-fragmentation.csv")

    # Create 3-panel horizontal figure with generous spacing
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(11.2, 3.6))
    fig.subplots_adjust(left=0.06, right=0.94, top=0.82, bottom=0.18, wspace=0.38)

    # -------------------------------------------------------------
    # Panel A: NVIDIA CUTLASS (Hardware Primitives & Inline PTX)
    # -------------------------------------------------------------
    x1 = np.arange(len(cutlass_rows))
    width = 0.50

    shared_k = np.array([float(r["shared_infra_loc"]) / 1000.0 for r in cutlass_rows])
    warp_k = np.array([float(r["warp_tb_loc"]) / 1000.0 for r in cutlass_rows])
    arch_k = np.array([float(r["arch_total_loc"]) / 1000.0 for r in cutlass_rows])
    asm_counts = [int(r["inline_ptx_asm_count"]) for r in cutlass_rows]

    ax1.bar(
        x1,
        shared_k,
        width,
        label="Shared Infra",
        color="#CBD5E1",
        edgecolor="#94A3B8",
        linewidth=0.6,
        zorder=3,
    )
    ax1.bar(
        x1,
        warp_k,
        width,
        bottom=shared_k,
        label="Warp/TB Math",
        color="#93C5FD",
        edgecolor="#3B82F6",
        linewidth=0.6,
        zorder=3,
    )
    ax1.bar(
        x1,
        arch_k,
        width,
        bottom=shared_k + warp_k,
        label="Arch-Specific",
        color=COLORS["green"],
        edgecolor=COLORS["evidence_ink"],
        linewidth=0.7,
        zorder=3,
    )

    ax1_twin = ax1.twinx()
    ax1_twin.plot(
        x1,
        asm_counts,
        color=COLORS["red"],
        marker="o",
        markersize=3.8,
        linewidth=1.5,
        zorder=5,
        label="Inline PTX Asm",
    )
    ax1_twin.set_ylabel(
        "Inline PTX Asm Statements",
        fontsize=6.0,
        color=COLORS["constraints_ink"],
        labelpad=5,
    )
    ax1_twin.tick_params(
        axis="y",
        labelsize=5.4,
        labelcolor=COLORS["constraints_ink"],
        length=2,
        width=0.5,
    )
    ax1_twin.set_ylim(0, 3900)
    ax1_twin.set_yticks([0, 1000, 2000, 3000])

    versions_cutlass = [
        "v2.0\n('19)",
        "v2.5\n('21)",
        "v2.10\n('22)",
        "v3.0\n('23)",
        "v3.5\n('24)",
        "v3.6\n('24)",
        "v4.0\n('25)",
        "v4.7\n('26)",
    ]
    ax1.set_xticks(x1)
    ax1.set_xticklabels(versions_cutlass, fontsize=5.4)
    ax1.set_ylabel("CUTLASS Include LOC (Thousands)", fontsize=6.0, color=COLORS["ink"])
    ax1.set_ylim(0, 880)
    ax1.set_yticks([0, 200, 400, 600, 800])
    ax1.tick_params(axis="both", labelsize=5.4, length=2, width=0.5)
    ax1.grid(axis="y", color=COLORS["grid"], linewidth=0.5, zorder=0)

    ax1.annotate(
        "Arch LOC: 48.7x\n(4.3K -> 208K)",
        xy=(7, 735),
        xytext=(2.6, 735),
        fontsize=5.3,
        fontweight="bold",
        color=COLORS["evidence_ink"],
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor=COLORS["note_fill"],
            edgecolor=COLORS["evidence_ink"],
            linewidth=0.7,
        ),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS["evidence_ink"],
            lw=0.8,
            connectionstyle="arc3,rad=-0.1",
        ),
        zorder=6,
    )

    ax1.set_title(
        "A. Hardware Primitives (CUTLASS)\nExplosive Low-Level Specialization",
        fontsize=6.6,
        fontweight="bold",
        pad=8,
        color=COLORS["ink"],
    )

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines1_t, labels1_t = ax1_twin.get_legend_handles_labels()
    ax1.legend(
        lines1 + lines1_t,
        labels1 + labels1_t,
        loc="upper left",
        fontsize=4.8,
        framealpha=0.92,
        edgecolor="#E2E8F0",
    )

    # -------------------------------------------------------------
    # Panel B: Triton Compiler (MLIR Narrow Waist Absorption)
    # -------------------------------------------------------------
    x2 = np.arange(len(triton_rows))
    mlir_k = np.array([float(r["middle_end_mlir_loc"]) / 1000.0 for r in triton_rows])
    nv_k = np.array([float(r["nv_target_loc"]) / 1000.0 for r in triton_rows])
    amd_k = np.array([float(r["amd_target_loc"]) / 1000.0 for r in triton_rows])
    py_k = np.array([float(r["python_frontend_loc"]) / 1000.0 for r in triton_rows])

    ax2.bar(
        x2,
        mlir_k,
        width,
        label="MLIR Middle-End",
        color=COLORS["blue"],
        edgecolor=COLORS["workload_ink"],
        linewidth=0.7,
        zorder=3,
    )
    ax2.bar(
        x2,
        nv_k,
        width,
        bottom=mlir_k,
        label="NVIDIA Backend",
        color="#94A3B8",
        edgecolor="#475569",
        linewidth=0.6,
        zorder=3,
    )
    ax2.bar(
        x2,
        amd_k,
        width,
        bottom=mlir_k + nv_k,
        label="AMD ROCm Backend",
        color=COLORS["orange"],
        edgecolor=COLORS["methods_ink"],
        linewidth=0.7,
        zorder=3,
    )
    ax2.bar(
        x2,
        py_k,
        width,
        bottom=mlir_k + nv_k + amd_k,
        label="Python Frontend",
        color="#FBCFE8",
        edgecolor="#DB2777",
        linewidth=0.6,
        zorder=3,
    )

    versions_triton = [
        "v1.0\n('21)",
        "v2.0\n('23)",
        "v2.1\n('23)",
        "v3.0\n('24)",
        "v3.2\n('24)",
        "v3.5\n('25)",
        "v3.7\n('26)",
    ]
    ax2.set_xticks(x2)
    ax2.set_xticklabels(versions_triton, fontsize=5.4)
    ax2.set_ylabel("Compiler LOC (Thousands)", fontsize=6.0, color=COLORS["ink"])
    ax2.set_ylim(0, 390)
    ax2.set_yticks([0, 100, 200, 300])
    ax2.tick_params(axis="both", labelsize=5.4, length=2, width=0.5)
    ax2.grid(axis="y", color=COLORS["grid"], linewidth=0.5, zorder=0)

    ax2.annotate(
        "Shared MLIR Narrow Waist\nscales 33x (3K -> 100K LOC)",
        xy=(6, 50),
        xytext=(2.6, 320),
        fontsize=5.3,
        fontweight="bold",
        color=COLORS["workload_ink"],
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor=COLORS["note_fill"],
            edgecolor=COLORS["workload_ink"],
            linewidth=0.7,
        ),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS["workload_ink"],
            lw=0.8,
            connectionstyle="arc3,rad=-0.15",
        ),
        zorder=6,
    )

    ax2.set_title(
        "B. Compiler Narrow Waist (Triton)\nMLIR IR Absorbs Target Shifts",
        fontsize=6.6,
        fontweight="bold",
        pad=8,
        color=COLORS["ink"],
    )
    ax2.legend(
        loc="upper left",
        bbox_to_anchor=(0.0, 0.98),
        fontsize=4.8,
        framealpha=0.92,
        edgecolor="#E2E8F0",
    )

    # -------------------------------------------------------------
    # Panel C: vLLM Engine (Inference Serving Kernel Fragmentation)
    # -------------------------------------------------------------
    x3 = np.arange(len(vllm_rows))
    attn_k = np.array([float(r["csrc_attn_loc"]) / 1000.0 for r in vllm_rows])
    quant_k = np.array([float(r["csrc_quant_loc"]) / 1000.0 for r in vllm_rows])
    moe_k = np.array([float(r["csrc_moe_loc"]) / 1000.0 for r in vllm_rows])
    other_k = np.array(
        [
            (
                float(r["csrc_total_loc"])
                - (
                    float(r["csrc_attn_loc"])
                    + float(r["csrc_quant_loc"])
                    + float(r["csrc_moe_loc"])
                )
            )
            / 1000.0
            for r in vllm_rows
        ]
    )

    ax3.bar(
        x3,
        attn_k,
        width,
        label="Attention (Paged/Flash)",
        color=COLORS["purple"],
        edgecolor=COLORS["designspace_ink"],
        linewidth=0.7,
        zorder=3,
    )
    ax3.bar(
        x3,
        quant_k,
        width,
        bottom=attn_k,
        label="Quant (AWQ/FP8/Marlin)",
        color=COLORS["orange"],
        edgecolor=COLORS["methods_ink"],
        linewidth=0.7,
        zorder=3,
    )
    ax3.bar(
        x3,
        moe_k,
        width,
        bottom=attn_k + quant_k,
        label="Dynamic MoE Dispatch",
        color=COLORS["red"],
        edgecolor=COLORS["constraints_ink"],
        linewidth=0.7,
        zorder=3,
    )
    ax3.bar(
        x3,
        other_k,
        width,
        bottom=attn_k + quant_k + moe_k,
        label="ROCm / CPU / Custom",
        color="#94A3B8",
        edgecolor="#475569",
        linewidth=0.6,
        zorder=3,
    )

    versions_vllm = [
        "v0.1\n('23)",
        "v0.2\n('23)",
        "v0.3\n('24)",
        "v0.4\n('24)",
        "v0.6\n('24)",
        "v0.15\n('25)",
        "v0.20\n('25)",
        "v0.27\n('26)",
    ]
    ax3.set_xticks(x3)
    ax3.set_xticklabels(versions_vllm, fontsize=5.4)
    ax3.set_ylabel(
        "Custom C++/CUDA Kernel LOC (Thousands)", fontsize=6.0, color=COLORS["ink"]
    )
    ax3.set_ylim(0, 175)
    ax3.set_yticks([0, 40, 80, 120, 160])
    ax3.tick_params(axis="both", labelsize=5.4, length=2, width=0.5)
    ax3.grid(axis="y", color=COLORS["grid"], linewidth=0.5, zorder=0)

    ax3.annotate(
        "Kernel LOC: 48.7x\n(2.5K -> 120.5K)",
        xy=(7, 120.5),
        xytext=(3.4, 142),
        fontsize=5.3,
        fontweight="bold",
        color=COLORS["designspace_ink"],
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor=COLORS["note_fill"],
            edgecolor=COLORS["designspace_ink"],
            linewidth=0.7,
        ),
        arrowprops=dict(
            arrowstyle="->",
            color=COLORS["designspace_ink"],
            lw=0.8,
            connectionstyle="arc3,rad=-0.1",
        ),
        zorder=6,
    )

    ax3.set_title(
        "C. Inference Engine (vLLM)\nApplication Kernel Fragmentation",
        fontsize=6.6,
        fontweight="bold",
        pad=8,
        color=COLORS["ink"],
    )
    ax3.legend(
        loc="upper left",
        bbox_to_anchor=(0.0, 0.98),
        fontsize=4.8,
        framealpha=0.92,
        edgecolor="#E2E8F0",
    )

    for ax in [ax1, ax2, ax3]:
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        ax.spines["left"].set_color(COLORS["ink"])
        ax.spines["bottom"].set_color(COLORS["ink"])

    ax1_twin.spines["top"].set_visible(False)
    ax1_twin.spines["left"].set_visible(False)
    ax1_twin.spines["bottom"].set_visible(False)
    ax1_twin.spines["right"].set_color(COLORS["constraints_ink"])

    png_path = output_dir / "fig-ch09-software-porting-wall.png"
    svg_path = output_dir / "fig-ch09-software-porting-wall.svg"
    pdf_path = output_dir / "fig-ch09-software-porting-wall.pdf"

    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(svg_path, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Generated: {png_path}")
    return png_path


if __name__ == "__main__":
    out = Path(__file__).resolve().parent
    generate_figure(out)
