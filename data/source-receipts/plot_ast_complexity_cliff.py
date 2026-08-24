#!/usr/bin/env python3
"""
Figure: The AI Benchmark Mirage vs. Physical Silicon AST Complexity Cliff
Architecture 2.0: Track 2 — Empirical Hardware Representation & Benchmark Analysis

Visualizes the quantitative and topological gap between synthetic AI benchmarks and production silicon:
- Panel A: Cumulative Distribution Function (CDF) of AST Node Count & LoC across 550 hardware modules.
- Panel B: Structural Hierarchy Depth vs. Asynchronous Clock-Domain Crossings (CDC) & Sequential State Bits.

Dataset Receipt:
- data/source-receipts/hardware_ast_complexity_gap.csv

Generated Assets:
- data/source-receipts/fig_ast_complexity_cliff.svg
- data/source-receipts/fig_ast_complexity_cliff.pdf
- data/source-receipts/fig_ast_complexity_cliff.png
- book/contents/chapters/04-representations/images/fig-ch04-ast-complexity-cliff.svg
- book/contents/chapters/04-representations/images/fig-ch04-ast-complexity-cliff.pdf
- book/contents/chapters/04-representations/images/fig-ch04-ast-complexity-cliff.png
"""

import sys
import csv
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import matplotlib.ticker as ticker

# Connect repo root for shared plot style
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style

apply_style()


def _declare_font_stack(svg_path: Path) -> None:
    """Ensure SVG declares standard sans-serif font stack matching House Style."""
    if not svg_path.exists():
        return
    text = svg_path.read_text(encoding="utf-8")
    if '<style type="text/css">' not in text:
        text = text.replace(
            "<defs>",
            '<defs>\n  <style type="text/css">*{font-family: Arial, Helvetica, sans-serif;}</style>',
            1,
        )
        svg_path.write_text(text, encoding="utf-8")


def load_receipt_data(csv_path: Path):
    """Load hardware AST complexity CSV receipt, ignoring metadata comment lines."""
    records = []
    with open(csv_path, "r", encoding="utf-8") as f:
        # Filter out comment lines starting with '#'
        lines = [line for line in f if not line.strip().startswith("#")]
        reader = csv.DictReader(lines)
        for r in reader:
            records.append(
                {
                    "corpus_type": r["corpus_type"],
                    "corpus_name": r["corpus_name"],
                    "module_or_system": r["module_or_system"],
                    "loc_clean": float(r["loc_clean"]),
                    "loc_raw": float(r["loc_raw"]),
                    "ast_nodes": float(r["ast_node_count"]),
                    "ast_depth": float(r["ast_max_depth"]),
                    "clock_domains": float(r["clock_domains_count"]),
                    "is_multiclock": int(r["is_multiclock"]),
                    "cdc_crossings": float(r["cdc_crossings_count"]),
                    "seq_ff_bits": float(r["sequential_state_bits"]),
                    "hierarchy_depth": float(r["hierarchy_depth"]),
                    "submodule_count": float(r["submodule_count"]),
                    "function": r.get("primary_function", ""),
                }
            )
    return records


def main():
    csv_file = (
        REPO_ROOT / "data" / "source-receipts" / "hardware_ast_complexity_gap.csv"
    )
    if not csv_file.exists():
        # Fallback to local execution dir
        csv_file = Path(__file__).resolve().parent / "hardware_ast_complexity_gap.csv"

    records = load_receipt_data(csv_file)
    benchmarks = [r for r in records if r["corpus_type"] == "AI Synthetic Benchmark"]
    silicon = [r for r in records if r["corpus_type"] == "Production Silicon IP & SoC"]

    # Target output paths
    out_receipts_svg = (
        REPO_ROOT / "data" / "source-receipts" / "fig_ast_complexity_cliff.svg"
    )
    out_receipts_pdf = (
        REPO_ROOT / "data" / "source-receipts" / "fig_ast_complexity_cliff.pdf"
    )
    out_receipts_png = (
        REPO_ROOT / "data" / "source-receipts" / "fig_ast_complexity_cliff.png"
    )

    chapter_img_dir = (
        REPO_ROOT / "book" / "contents" / "chapters" / "04-representations" / "images"
    )
    chapter_img_dir.mkdir(parents=True, exist_ok=True)
    out_ch04_svg = chapter_img_dir / "fig-ch04-ast-complexity-cliff.svg"
    out_ch04_pdf = chapter_img_dir / "fig-ch04-ast-complexity-cliff.pdf"
    out_ch04_png = chapter_img_dir / "fig-ch04-ast-complexity-cliff.png"

    all_out_paths = [
        out_receipts_svg,
        out_receipts_pdf,
        out_receipts_png,
        out_ch04_svg,
        out_ch04_pdf,
        out_ch04_png,
    ]

    # Setup two-panel figure
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(7.4, 3.5), gridspec_kw={"width_ratios": [1.1, 1.0]}
    )
    fig.subplots_adjust(left=0.08, right=0.96, top=0.84, bottom=0.15, wspace=0.34)

    # -------------------------------------------------------------------------
    # Panel A: The Structural AST Complexity Cliff (Empirical CDF)
    # -------------------------------------------------------------------------
    bench_ast = np.array(sorted([r["ast_nodes"] for r in benchmarks]))
    silicon_ast = np.array(sorted([r["ast_nodes"] for r in silicon]))

    bench_cdf = np.linspace(0.0, 1.0, len(bench_ast))
    silicon_cdf = np.linspace(0.0, 1.0, len(silicon_ast))

    # Plot CDF curves
    ax1.plot(
        bench_ast,
        bench_cdf,
        color=COLORS["constraints"],
        linewidth=2.0,
        label="AI Synthetic Benchmarks (N=370)\n[VerilogEval, RTLLM, HumanEval]",
        zorder=4,
    )
    ax1.plot(
        silicon_ast,
        silicon_cdf,
        color=COLORS["workload"],
        linewidth=2.0,
        label="Production Silicon RTL (N=180)\n[OpenTitan, BOOM, SweRV, CV32E, BP]",
        zorder=4,
    )

    # Shaded complexity cliff gap between median AI benchmark and median Silicon
    med_bench = np.median(bench_ast)
    med_silicon = np.median(silicon_ast)
    ax1.axvspan(med_bench, med_silicon, color=COLORS["note_fill"], alpha=0.55, zorder=1)

    # Median markers
    ax1.scatter([med_bench], [0.5], color=COLORS["constraints_ink"], s=26, zorder=6)
    ax1.scatter([med_silicon], [0.5], color=COLORS["workload_ink"], s=26, zorder=6)

    # Annotate the 175x complexity cliff gap
    geom_mid = np.exp((np.log(med_bench) + np.log(med_silicon)) / 2.0)
    ax1.annotate(
        "175× AST Complexity Cliff\n(Median 73 → 12,800 Nodes)",
        xy=(geom_mid, 0.5),
        xytext=(geom_mid, 0.24),
        ha="center",
        va="center",
        fontsize=5.3,
        fontweight="bold",
        color=COLORS["note_text"],
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor=COLORS["note_fill"],
            edgecolor=COLORS["note_edge"],
            lw=0.7,
            alpha=0.95,
        ),
        arrowprops=dict(arrowstyle="->", color=COLORS["note_edge"], lw=0.8),
        zorder=7,
    )

    # AI benchmark plateau callout
    ax1.text(
        38,
        0.90,
        "AI Benchmark Mirage\n99.4% < 300 Nodes\n(<100 Clean LoC)",
        fontsize=5.0,
        fontweight="bold",
        color=COLORS["constraints_ink"],
        ha="center",
        va="center",
        bbox=dict(
            boxstyle="round,pad=0.22",
            facecolor="white",
            edgecolor=COLORS["constraints_ink"],
            lw=0.6,
            alpha=0.92,
        ),
        zorder=7,
    )

    # Silicon full-scale callout
    ax1.text(
        95000,
        0.82,
        "Production Silicon\nUp to 448k AST Nodes\n(>150k Clean LoC)",
        fontsize=5.0,
        fontweight="bold",
        color=COLORS["workload_ink"],
        ha="center",
        va="center",
        bbox=dict(
            boxstyle="round,pad=0.22",
            facecolor="white",
            edgecolor=COLORS["workload_ink"],
            lw=0.6,
            alpha=0.92,
        ),
        zorder=7,
    )

    ax1.set_xscale("log")
    ax1.set_xlim(8, 700000)
    ax1.set_ylim(-0.02, 1.04)
    ax1.set_xlabel(
        "Hardware Abstract Syntax Tree Scale (AST Node Count, Log Scale)",
        fontsize=6.5,
        color=COLORS["ink"],
    )
    ax1.set_ylabel(
        "Cumulative Empirical Fraction (CDF)", fontsize=6.5, color=COLORS["ink"]
    )
    ax1.grid(True, which="both", color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax1.legend(
        loc="lower right", fontsize=4.8, framealpha=0.92, edgecolor=COLORS["grid"]
    )
    ax1.set_title(
        "A. Structural AST Complexity Cliff", fontsize=7.2, fontweight="bold", pad=8
    )

    # -------------------------------------------------------------------------
    # Panel B: Clock Domains & CDC Crossings vs Hierarchy Depth
    # -------------------------------------------------------------------------
    np.random.seed(42)

    # Plot AI benchmarks
    bench_h = np.array([r["hierarchy_depth"] for r in benchmarks])
    bench_cdc = np.array([r["cdc_crossings"] for r in benchmarks])
    bench_ff = np.array([r["seq_ff_bits"] for r in benchmarks])

    jitter_h_b = bench_h + np.random.uniform(-0.10, 0.10, len(bench_h))
    jitter_cdc_b = bench_cdc + np.random.uniform(-0.12, 0.12, len(bench_cdc))

    ax2.scatter(
        jitter_h_b,
        jitter_cdc_b,
        s=np.clip(bench_ff * 0.35 + 14, 14, 75),
        color=COLORS["constraints"],
        alpha=0.65,
        edgecolors="none",
        label="AI Benchmarks (99.7% Single-Clock, 0 CDC)",
        zorder=3,
    )

    # Plot Production Silicon
    silicon_h = np.array([r["hierarchy_depth"] for r in silicon])
    silicon_cdc = np.array([r["cdc_crossings"] for r in silicon])
    silicon_ff = np.array([r["seq_ff_bits"] for r in silicon])

    jitter_h_s = silicon_h + np.random.uniform(-0.14, 0.14, len(silicon_h))
    jitter_cdc_s = silicon_cdc + np.random.uniform(-0.35, 0.35, len(silicon_cdc))

    ax2.scatter(
        jitter_h_s,
        jitter_cdc_s,
        s=np.clip(silicon_ff * 0.0035 + 24, 24, 220),
        color=COLORS["workload"],
        alpha=0.75,
        edgecolors=COLORS["workload_ink"],
        linewidth=0.5,
        label="Production Silicon (2–12 Clocks, 4–86 CDCs)",
        zorder=4,
    )

    # Annotate Benchmark Cluster at (1, 0)
    ax2.annotate(
        "Flat Leaf Modules\n(100% Depth=1, 0 CDC)",
        xy=(1.0, 0.0),
        xytext=(2.6, 16.0),
        ha="center",
        va="center",
        fontsize=5.0,
        fontweight="bold",
        color=COLORS["constraints_ink"],
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="white",
            edgecolor=COLORS["constraints_ink"],
            lw=0.6,
            alpha=0.92,
        ),
        arrowprops=dict(arrowstyle="->", color=COLORS["constraints_ink"], lw=0.7),
        zorder=7,
    )

    # Annotate OpenTitan Earl Grey SoC & SonicBOOM top
    ax2.annotate(
        "OpenTitan Earl Grey\n(12 Clocks, 86 CDCs, 36k FFs)",
        xy=(9.0, 86.0),
        xytext=(6.2, 80.0),
        ha="center",
        va="center",
        fontsize=4.8,
        fontweight="bold",
        color=COLORS["workload_ink"],
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="white",
            edgecolor=COLORS["workload_ink"],
            lw=0.6,
            alpha=0.92,
        ),
        arrowprops=dict(arrowstyle="->", color=COLORS["workload_ink"], lw=0.7),
        zorder=7,
    )

    ax2.annotate(
        "SonicBOOM Tile\n(10 Levels, 42k FFs, 22 CDCs)",
        xy=(10.0, 22.0),
        xytext=(7.2, 38.0),
        ha="center",
        va="center",
        fontsize=4.8,
        fontweight="bold",
        color=COLORS["designspace_ink"],
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="white",
            edgecolor=COLORS["designspace_ink"],
            lw=0.6,
            alpha=0.92,
        ),
        arrowprops=dict(arrowstyle="->", color=COLORS["designspace_ink"], lw=0.7),
        zorder=7,
    )

    ax2.set_xlim(0.4, 10.8)
    ax2.set_ylim(-2, 92)
    ax2.set_xticks(range(1, 11))
    ax2.set_xlabel(
        "Structural Submodule Hierarchy Depth", fontsize=6.5, color=COLORS["ink"]
    )
    ax2.set_ylabel(
        "Asynchronous Clock-Domain Crossings (CDC)", fontsize=6.5, color=COLORS["ink"]
    )
    ax2.grid(True, which="both", color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax2.legend(
        loc="upper left", fontsize=4.8, framealpha=0.92, edgecolor=COLORS["grid"]
    )
    ax2.set_title(
        "B. Clock-Domain Crossings vs. Hierarchy Depth",
        fontsize=7.2,
        fontweight="bold",
        pad=8,
    )

    # Save to all target paths
    for path in all_out_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".png":
            plt.savefig(path, dpi=300, bbox_inches="tight")
        else:
            plt.savefig(path, bbox_inches="tight")
        if path.suffix == ".svg":
            _declare_font_stack(path)
        print(f"  [SAVED] {path}")

    plt.close()


if __name__ == "__main__":
    main()
