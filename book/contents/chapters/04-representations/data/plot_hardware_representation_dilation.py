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

    # Corpus styling: distinct marker shapes so the panel survives grayscale.
    corpus_styles = [
        ("Micro-logic & FSM Primitives", "VerilogEval", COLORS["blue"], "o"),
        ("Domain IP & Arithmetic Blocks", "RTLLM", COLORS["orange"], "s"),
        ("Industrial Template Library", "BaseJump STL", COLORS["green"], "^"),
        ("Serial RISC-V CPU", "SERV", COLORS["purple"], "D"),
        ("Embedded 32-bit RISC-V CPU", "Ibex", COLORS["magenta"], "v"),
        ("Monolithic RISC-V CPU", "PicoRV32", COLORS["red"], "P"),
    ]

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(5.6, 2.9), gridspec_kw={"width_ratios": [1.1, 1.0]}
    )
    fig.subplots_adjust(left=0.1, right=0.98, top=0.86, bottom=0.17, wspace=0.62)

    # ----------------------------------------------------
    # Panel (a): definition-use distance in tokens versus module size
    # ----------------------------------------------------
    ax1.set_xscale("log")
    ax1.set_yscale("log")

    ast_nodes_arr = np.array([r["ast_nodes"] for r in valid_rows])
    token_dist_arr = np.array([r["mean_token_dist"] for r in valid_rows])

    handles = []
    for cat, name, color, marker in corpus_styles:
        sub = [r for r in valid_rows if r["category"] == cat]
        if not sub:
            continue
        ax1.scatter(
            [r["ast_nodes"] for r in sub],
            [r["mean_token_dist"] for r in sub],
            color=color,
            marker=marker,
            alpha=0.75,
            s=7,
            linewidths=0,
            zorder=4,
        )
        handles.append(
            Line2D(
                [0],
                [0],
                marker=marker,
                color="w",
                markerfacecolor=color,
                markersize=3.6,
                label=f"{name} (n={len(sub)})",
            )
        )

    # Power-law fit computed from the plotted data; the exponent label is derived.
    log_x = np.log10(ast_nodes_arr)
    poly_tok = np.polyfit(log_x, np.log10(token_dist_arr), 1)
    x_fit = np.logspace(log_x.min(), log_x.max(), 100)
    y_tok_fit = 10 ** (poly_tok[0] * np.log10(x_fit) + poly_tok[1])
    ax1.plot(x_fit, y_tok_fit, color=COLORS["ink"], linewidth=0.9, zorder=5)
    handles.append(
        Line2D(
            [0],
            [0],
            color=COLORS["ink"],
            lw=0.9,
            label=f"fit, slope {poly_tok[0]:.2f}",
        )
    )

    ax1.set_xlim(ast_nodes_arr.min() / 1.5, ast_nodes_arr.max() * 2.5)
    ax1.set_ylim(token_dist_arr.min() / 2, token_dist_arr.max() * 4)
    ax1.set_xlabel("Module size (parsed syntax nodes, log scale)", color=COLORS["ink"])
    ax1.set_ylabel("Mean definition-use distance (tokens)", color=COLORS["ink"])
    ax1.grid(True, which="major", color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax1.legend(
        handles=handles,
        loc="upper left",
        fontsize=4.6,
        framealpha=0.94,
        edgecolor=COLORS["grid"],
        handletextpad=0.3,
        borderpad=0.4,
    )
    ax1.set_title(
        "(a) Definition-use distance in token order",
        loc="left",
        fontweight="bold",
        color=COLORS["ink"],
    )

    # ----------------------------------------------------
    # Panel (b): token composition by corpus
    # ----------------------------------------------------
    y_labels = []
    scaffold_means, semantic_means, identifier_means = [], [], []
    for cat, name, _, _ in corpus_styles:
        sub = [r for r in valid_rows if r["category"] == cat]
        y_labels.append(f"{name} (n={len(sub)})")
        scaffold_means.append(np.mean([r["scaffold_pct"] for r in sub]))
        semantic_means.append(np.mean([r["semantic_pct"] for r in sub]))
        identifier_means.append(100.0 - scaffold_means[-1] - semantic_means[-1])

    y_pos = np.arange(len(y_labels))
    bar_height = 0.56
    ax2.barh(
        y_pos,
        scaffold_means,
        height=bar_height,
        color=COLORS["row"],
        edgecolor=COLORS["muted"],
        linewidth=0.5,
        zorder=3,
    )
    ax2.barh(
        y_pos,
        semantic_means,
        left=scaffold_means,
        height=bar_height,
        color=COLORS["workload"],
        edgecolor=COLORS["workload_ink"],
        linewidth=0.5,
        zorder=3,
    )
    ax2.barh(
        y_pos,
        identifier_means,
        left=np.array(scaffold_means) + np.array(semantic_means),
        height=bar_height,
        color=COLORS["designspace_tint"],
        edgecolor=COLORS["designspace_ink"],
        linewidth=0.5,
        hatch="////",
        zorder=3,
    )
    for i, (sc, sem, idn) in enumerate(
        zip(scaffold_means, semantic_means, identifier_means)
    ):
        ax2.text(
            sc / 2,
            i,
            f"{sc:.0f}%",
            va="center",
            ha="center",
            fontsize=5.0,
            color=COLORS["ink"],
            zorder=6,
        )
        ax2.text(
            sc + sem / 2,
            i,
            f"{sem:.0f}%",
            va="center",
            ha="center",
            fontsize=5.0,
            color="#ffffff",
            fontweight="bold",
            zorder=6,
        )

    ax2.set_xlim(0, 100)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(y_labels, color=COLORS["ink"])
    ax2.invert_yaxis()
    ax2.set_xlabel("Share of lexical tokens (%)", color=COLORS["ink"])
    ax2.grid(axis="x", color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax2.legend(
        handles=[
            Patch(
                facecolor=COLORS["row"],
                edgecolor=COLORS["muted"],
                lw=0.5,
                label="Keywords and delimiters",
            ),
            Patch(
                facecolor=COLORS["workload"],
                edgecolor=COLORS["workload_ink"],
                lw=0.5,
                label="Operators and state",
            ),
            Patch(
                facecolor=COLORS["designspace_tint"],
                edgecolor=COLORS["designspace_ink"],
                lw=0.5,
                hatch="////",
                label="Identifiers",
            ),
        ],
        loc="lower left",
        bbox_to_anchor=(-0.02, 1.0),
        ncol=3,
        fontsize=4.6,
        frameon=False,
        handlelength=1.2,
        handletextpad=0.3,
        columnspacing=0.6,
    )
    ax2.set_title(
        "(b) Token composition by corpus",
        loc="left",
        fontweight="bold",
        color=COLORS["ink"],
        pad=14,
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
