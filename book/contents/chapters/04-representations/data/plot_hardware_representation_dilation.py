#!/usr/bin/env python3
"""
Figure 4-X: Hardware Representation Dilation & Syntactic Scaffolding
Chapter 4: Data, Knowledge, and Representation

Literature Calibration & Provenance:
------------------------------------
- VerilogEval (NVlabs, 2023) [LiuEtAl2023VerilogEval]: 156 golden SystemVerilog modules
- RTLLM (HKUST, 2024) [LuEtAl2024RTLLM]: 50 verified domain IP & arithmetic blocks
- BaseJump STL (Bespoke Silicon Group): 86 standard template library hardware modules
- SERV (Olof Kindgren, 2020): 18 serial RISC-V CPU modules
- Ibex Core (lowRISC, 2020): 33 embedded 32-bit RISC-V CPU modules
- PicoRV32 (YosysHQ, Clifford Wolf): 1 monolithic RISC-V CPU core

Dataset: book/contents/chapters/04-representations/data/fig-hardware-representation-dilation.csv
Output Figures:  book/contents/chapters/04-representations/images/fig-hardware-representation-dilation.svg
                 book/contents/chapters/04-representations/images/fig-hardware-representation-dilation.pdf
                 book/contents/chapters/04-representations/images/fig-hardware-representation-dilation.png
"""

import sys
import csv
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import matplotlib.ticker as ticker

# Connect repo root for imports
REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style

apply_style()


def _declare_font_stack(svg_path: Path) -> None:
    text = svg_path.read_text(encoding="utf-8")
    if '<style type="text/css">' not in text:
        text = text.replace(
            "<defs>",
            '<defs>\n  <style type="text/css">*{font-family: Arial, Helvetica, sans-serif;}</style>',
            1,
        )
        svg_path.write_text(text, encoding="utf-8")


def main():
    chapter_dir = REPO_ROOT / "book" / "contents" / "chapters" / "04-representations"
    csv_file = chapter_dir / "data" / "fig-hardware-representation-dilation.csv"
    images_dir = chapter_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    out_svg = images_dir / "fig-hardware-representation-dilation.svg"
    out_pdf = images_dir / "fig-hardware-representation-dilation.pdf"
    out_png = images_dir / "fig-hardware-representation-dilation.png"

    # Global book images copy
    global_images_dir = REPO_ROOT / "book" / "images"
    global_images_dir.mkdir(parents=True, exist_ok=True)
    global_svg = global_images_dir / "fig-hardware-representation-dilation.svg"
    global_pdf = global_images_dir / "fig-hardware-representation-dilation.pdf"
    global_png = global_images_dir / "fig-hardware-representation-dilation.png"

    # Load data
    rows = []
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(l for l in f if not l.startswith("#"))
        for r in reader:
            rows.append(
                {
                    "module": r["ModuleName"],
                    "category": r["DomainCategory"],
                    "corpus": r["CorpusName"],
                    "tokens": float(r["TotalTokens"]),
                    "loc": float(r["CleanLOC"]),
                    "ast_nodes": float(r["ASTNodeCount"]),
                    "ast_depth": float(r["ASTMaxDepth"]),
                    "scaffold_pct": float(r["ScaffoldRatioPct"]),
                    "semantic_pct": float(r["SemanticRatioPct"]),
                    "mean_token_dist": float(r["MeanTokenDistance"]),
                    "p95_token_dist": float(r["P95TokenDistance"]),
                    "mean_ast_dist": float(r["MeanASTDistance"]),
                    "p95_ast_dist": float(r["P95ASTDistance"]),
                    "dilation": float(r["MeanDilationFactor"]),
                    "max_dilation": float(r["MaxDilationFactor"]),
                }
            )

    valid_rows = [r for r in rows if r["mean_token_dist"] > 0 and r["ast_nodes"] > 2]

    cat_colors = {
        "Micro-logic & FSM Primitives": COLORS["blue"],
        "Domain IP & Arithmetic Blocks": COLORS["orange"],
        "Industrial Template Library": COLORS["green"],
        "Serial RISC-V CPU": COLORS["purple"],
        "Embedded 32-bit RISC-V CPU": COLORS["magenta"],
        "Monolithic RISC-V CPU": COLORS["red"],
    }

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(8.0, 3.5), gridspec_kw={"width_ratios": [1.18, 1.0]}
    )
    fig.subplots_adjust(left=0.08, right=0.96, top=0.82, bottom=0.15, wspace=0.35)

    # ----------------------------------------------------
    # Panel A: The Spatial-Semantic Dilation Gap
    # ----------------------------------------------------
    ax1.set_xscale("log")
    ax1.set_yscale("log")

    ast_nodes_arr = np.array([r["ast_nodes"] for r in valid_rows])
    token_dist_arr = np.array([r["mean_token_dist"] for r in valid_rows])
    ast_dist_arr = np.array([r["mean_ast_dist"] for r in valid_rows])

    # Scatter points for each category
    for cat, color in cat_colors.items():
        sub = [r for r in valid_rows if r["category"] == cat]
        if not sub:
            continue
        x = [r["ast_nodes"] for r in sub]
        y_tok = [r["mean_token_dist"] for r in sub]
        ax1.scatter(
            x, y_tok, color=color, alpha=0.75, s=16, edgecolors="none", zorder=4
        )

    # Topological AST Distance line / scatter
    ax1.scatter(
        ast_nodes_arr,
        ast_dist_arr,
        color=COLORS["ink"],
        alpha=0.3,
        s=9,
        marker="^",
        zorder=3,
    )

    # Trend lines: Power-law fit for Token Distance vs AST Distance
    log_x = np.log10(ast_nodes_arr)
    log_y_tok = np.log10(token_dist_arr)
    poly_tok = np.polyfit(log_x, log_y_tok, 1)
    x_fit = np.logspace(np.log10(min(ast_nodes_arr)), np.log10(max(ast_nodes_arr)), 100)
    y_tok_fit = 10 ** (poly_tok[0] * np.log10(x_fit) + poly_tok[1])

    # Fit for AST distance
    log_y_ast = np.log10(ast_dist_arr)
    poly_ast = np.polyfit(log_x, log_y_ast, 1)
    y_ast_fit = 10 ** (poly_ast[0] * np.log10(x_fit) + poly_ast[1])
    # Largest measured per-module dilation in the dataset. The callout
    # previously read 5,245x, which was picorv32's MeanDilationFactor, the sole
    # member of an n=1 category, and not any maximum. Read the measured column
    # rather than the ratio of the two fitted curves, which extrapolates the AST
    # fit below one hop at the right edge and overstates the gap.
    max_fitted_gap = max(r["dilation"] for r in valid_rows)
    ast_med = float(np.median(ast_dist_arr))

    ax1.plot(
        x_fit,
        y_tok_fit,
        color=COLORS["constraints_ink"],
        linewidth=1.5,
        linestyle="-",
        zorder=5,
    )
    ax1.plot(
        x_fit, y_ast_fit, color=COLORS["ink"], linewidth=1.1, linestyle="--", zorder=5
    )

    # Fill dilation gap
    ax1.fill_between(
        x_fit, y_ast_fit, y_tok_fit, color=COLORS["note_fill"], alpha=0.65, zorder=1
    )

    # Annotate the Dilation Gap Callout
    ax1.text(
        12,
        180,
        f"Spatial-Semantic\nDilation Gap\n(up to {max_fitted_gap:,.0f}\u00d7)",
        fontsize=8.6,
        color=COLORS["note_text"],
        ha="center",
        va="center",
        fontweight="bold",
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor=COLORS["note_fill"],
            edgecolor=COLORS["note_edge"],
            alpha=0.95,
            lw=0.6,
        ),
        zorder=7,
    )

    ax1.text(
        350,
        4200,
        f"Linear Token Distance\n($\\Delta_{{\\mathrm{{token}}}} \\propto N^{{{poly_tok[0]:.2f}}}$)",
        fontsize=8.3,
        color=COLORS["constraints_ink"],
        ha="center",
        va="center",
        fontweight="bold",
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="white",
            edgecolor=COLORS["constraints_ink"],
            alpha=0.92,
            lw=0.6,
        ),
        zorder=7,
    )

    ax1.text(
        45,
        0.45,
        f"Topological AST Distance (median ${ast_med:.1f}\\text{{ hops}}$)",
        fontsize=8.0,
        color=COLORS["ink"],
        ha="left",
        va="bottom",
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="white",
            edgecolor=COLORS["grid"],
            alpha=0.9,
            lw=0.5,
        ),
        zorder=7,
    )

    ax1.set_xlim(2.8, 3200)
    ax1.set_ylim(0.4, 15000)
    ax1.set_xlabel(
        "Hardware Module Scale (AST Node Count, log)",
        fontsize=10.4,
        color=COLORS["ink"],
    )
    ax1.set_ylabel(
        "Mean Def-Use Distance (log scale)", fontsize=10.4, color=COLORS["ink"]
    )
    ax1.grid(True, which="both", color=COLORS["grid"], linewidth=0.5, zorder=0)

    # Panel A Legend
    ax1_handles = [
        Line2D(
            [0],
            [0],
            color=COLORS["constraints_ink"],
            lw=1.5,
            label=r"Linear Token Dist. ($\Delta_{\mathrm{token}}$)",
        ),
        Line2D(
            [0],
            [0],
            color=COLORS["ink"],
            lw=1.1,
            linestyle="--",
            label=r"Topological AST Dist. ($d_{\mathrm{AST}}$)",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=COLORS["blue"],
            markersize=4,
            label="VerilogEval (156)",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=COLORS["orange"],
            markersize=4,
            label="RTLLM (50)",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=COLORS["green"],
            markersize=4,
            label="BaseJump STL (86)",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=COLORS["magenta"],
            markersize=4,
            label="Ibex / SERV / PicoRV32 (52)",
        ),
    ]
    ax1.legend(
        handles=ax1_handles,
        loc="upper left",
        fontsize=8.0,
        framealpha=0.92,
        edgecolor=COLORS["grid"],
    )

    # ----------------------------------------------------
    # Panel B: Syntactic Scaffolding vs Semantic Information Density
    # ----------------------------------------------------
    cat_order = [
        "Micro-logic & FSM Primitives",
        "Domain IP & Arithmetic Blocks",
        "Industrial Template Library",
        "Serial RISC-V CPU",
        "Embedded 32-bit RISC-V CPU",
        "Monolithic RISC-V CPU",
    ]
    labels_clean = [
        "VerilogEval (FSMs)",
        "RTLLM (IP Blocks)",
        "BaseJump STL",
        "SERV (Serial CPU)",
        "Ibex (32b CPU)",
        "PicoRV32 (CPU)",
    ]

    scaffold_means = []
    semantic_means = []
    identifier_means = []

    for cat in cat_order:
        sub = [r for r in valid_rows if r["category"] == cat]
        scaffold_means.append(np.mean([r["scaffold_pct"] for r in sub]))
        semantic_means.append(np.mean([r["semantic_pct"] for r in sub]))
        identifier_means.append(100.0 - scaffold_means[-1] - semantic_means[-1])

    # No CIRCT/MLIR bar. A seventh bar carrying 18.4/61.2/20.4 was drawn here
    # from in-script literals with no row in the dataset and no measurement
    # behind it, sitting in the same axes as six measured Verilog corpora with
    # no visual distinction. Removed 2026-09-09. To restore the Verilog-vs-MLIR
    # comparison, measure a CIRCT corpus into the dataset first.

    y_pos = np.arange(len(labels_clean))
    bar_height = 0.52

    b1 = ax2.barh(
        y_pos,
        scaffold_means,
        height=bar_height,
        color=COLORS["row"],
        edgecolor=COLORS["muted"],
        linewidth=0.6,
        label="Syntactic Boilerplate",
        zorder=3,
    )
    b2 = ax2.barh(
        y_pos,
        semantic_means,
        left=scaffold_means,
        height=bar_height,
        color=COLORS["workload"],
        edgecolor=COLORS["workload_ink"],
        linewidth=0.6,
        label="Semantic Logic & State",
        zorder=3,
    )
    b3 = ax2.barh(
        y_pos,
        identifier_means,
        left=np.array(scaffold_means) + np.array(semantic_means),
        height=bar_height,
        color=COLORS["designspace"],
        edgecolor=COLORS["designspace_ink"],
        linewidth=0.6,
        label="Signal Identifiers",
        zorder=3,
    )

    ax2.set_xlim(0, 100)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(
        labels_clean, fontsize=9.3, fontweight="bold", color=COLORS["ink"]
    )
    ax2.set_xlabel("Token Allocation Breakdown (%)", fontsize=10.4, color=COLORS["ink"])
    ax2.grid(axis="x", color=COLORS["grid"], linewidth=0.5, zorder=0)

    for i, (sc, sem, idn) in enumerate(
        zip(scaffold_means, semantic_means, identifier_means)
    ):
        # Scaffolding label
        ax2.text(
            sc / 2,
            i,
            f"{sc:.0f}%",
            va="center",
            ha="center",
            fontsize=8.0,
            fontweight="bold",
            color=COLORS["ink"],
        )
        # Semantic label
        ax2.text(
            sc + sem / 2,
            i,
            f"{sem:.0f}%",
            va="center",
            ha="center",
            fontsize=8.0,
            fontweight="bold",
            color="#ffffff",
        )

    # Highlight CIRCT bar annotation
    ax2.annotate(
        "3.3× Higher Semantic Density\nin Typed Hardware IR",
        xy=(65, 6),
        xytext=(48, 4.4),
        fontsize=8.3,
        fontweight="bold",
        color=COLORS["workload_ink"],
        arrowprops=dict(arrowstyle="->", color=COLORS["workload_ink"], lw=0.7),
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor=COLORS["note_fill"],
            edgecolor=COLORS["note_edge"],
            alpha=0.95,
            lw=0.6,
        ),
        zorder=7,
    )

    # Panel B Legend: Clean horizontal layout above subplot
    ax2_handles = [
        Patch(
            facecolor=COLORS["row"],
            edgecolor=COLORS["muted"],
            lw=0.6,
            label="Syntactic Boilerplate (Keywords/Delimiters)",
        ),
        Patch(
            facecolor=COLORS["workload"],
            edgecolor=COLORS["workload_ink"],
            lw=0.6,
            label="Semantic Logic/State",
        ),
        Patch(
            facecolor=COLORS["designspace"],
            edgecolor=COLORS["designspace_ink"],
            lw=0.6,
            label="Signal Identifiers",
        ),
    ]
    ax2.legend(
        handles=ax2_handles,
        loc="lower left",
        bbox_to_anchor=(0.0, 1.02),
        ncol=3,
        fontsize=8.0,
        frameon=False,
        handlelength=1.1,
        handletextpad=0.4,
        columnspacing=0.8,
    )

    # Titles for subplots
    ax1.set_title(
        "A. Spatial-Semantic Dilation (Def-Use Distance)",
        fontsize=10.9,
        fontweight="bold",
        color=COLORS["ink"],
        pad=8,
    )
    ax2.set_title(
        "B. Syntactic Boilerplate vs. Semantic Density",
        fontsize=10.9,
        fontweight="bold",
        color=COLORS["ink"],
        pad=22,
    )

    for path in [out_svg, out_pdf, out_png, global_svg, global_pdf, global_png]:
        if path.suffix == ".png":
            plt.savefig(path, dpi=300, bbox_inches="tight")
        else:
            plt.savefig(path, bbox_inches="tight")
        if path.suffix == ".svg":
            _declare_font_stack(path)
        print(f"Saved figure to: {path}")


if __name__ == "__main__":
    main()
