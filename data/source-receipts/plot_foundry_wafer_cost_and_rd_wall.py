#!/usr/bin/env python3
"""
Foundry Wafer Cost Inversion vs. Corporate R&D Spend (SEC EDGAR 10-K)
====================================================================
Dual-axis economic wall plot for Architecture 2.0 (Track 5.2 / Chapter 2):
Panel A: Leading-Edge Foundry Wafer Cost & SoC Design Cost Escalation (90nm to 2nm)
         paired with the Transistor Cost Inversion ($/100M Transistors).
Panel B: Corporate R&D Expenditure Escalation across 7 semiconductor leaders (2000-2026)
         grounded in official SEC EDGAR 10-K/20-F filings, highlighting the 25%+ intensity wall.
"""

from __future__ import annotations

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


def main() -> None:
    receipts_dir = REPO_ROOT / "data" / "source-receipts"
    data_csv = receipts_dir / "sec_edgar_semiconductor_rd_economics.csv"

    # Destination output paths
    out_receipts_png = receipts_dir / "fig-foundry-wafer-cost-and-rd-wall.png"
    out_receipts_pdf = receipts_dir / "fig-foundry-wafer-cost-and-rd-wall.pdf"
    out_receipts_svg = receipts_dir / "fig-foundry-wafer-cost-and-rd-wall.svg"

    chapter2_img_dir = (
        REPO_ROOT / "book" / "contents" / "chapters" / "02-pressures" / "images"
    )
    chapter2_img_dir.mkdir(parents=True, exist_ok=True)
    out_ch2_png = chapter2_img_dir / "fig-ch02-foundry-cost-inversion-and-rd-wall.png"
    out_ch2_pdf = chapter2_img_dir / "fig-ch02-foundry-cost-inversion-and-rd-wall.pdf"
    out_ch2_svg = chapter2_img_dir / "fig-ch02-foundry-cost-inversion-and-rd-wall.svg"

    # 1. Load SEC EDGAR R&D Financials
    records: list[dict] = []
    with open(data_csv, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = []
        for row in reader:
            if not row or row[0].startswith("#"):
                continue
            if not header:
                header = row
                continue
            d = dict(zip(header, row))
            records.append(
                {
                    "year": int(d["fiscal_year"]),
                    "ticker": d["company_ticker"],
                    "company": d["company_name"],
                    "rev": float(d["annual_revenue_usd_billion"]),
                    "rd": float(d["rd_expense_usd_billion"]),
                    "intensity": float(d["rd_intensity_pct"]),
                    "node_nm": int(d["leading_process_node_nm"]),
                    "wafer_cost": float(d["wafer_cost_usd"]),
                    "mask_cost": float(d["full_reticle_mask_cost_usd_million"]),
                    "design_cost": float(d["design_cost_per_soc_usd_million"]),
                }
            )

    # 2. Node Economics Reference Points (from TSMC / IBS / Gartner)
    nodes_data = [
        {
            "node": "90 nm",
            "year": 2004,
            "wafer_cost": 1850.0,
            "density": 1.25,
            "cost_100m": 2.094,
            "design_cost": 24.0,
        },
        {
            "node": "65 nm",
            "year": 2006,
            "wafer_cost": 2100.0,
            "density": 2.65,
            "cost_100m": 1.121,
            "design_cost": 30.0,
        },
        {
            "node": "40 nm",
            "year": 2008,
            "wafer_cost": 2450.0,
            "density": 5.80,
            "cost_100m": 0.598,
            "design_cost": 48.0,
        },
        {
            "node": "28 nm",
            "year": 2011,
            "wafer_cost": 3000.0,
            "density": 15.3,
            "cost_100m": 0.277,
            "design_cost": 75.0,
        },
        {
            "node": "20 nm",
            "year": 2014,
            "wafer_cost": 3800.0,
            "density": 21.8,
            "cost_100m": 0.247,
            "design_cost": 110.0,
        },
        {
            "node": "16 nm",
            "year": 2015,
            "wafer_cost": 4500.0,
            "density": 28.8,
            "cost_100m": 0.221,
            "design_cost": 160.0,
        },
        {
            "node": "10 nm",
            "year": 2017,
            "wafer_cost": 6000.0,
            "density": 52.5,
            "cost_100m": 0.162,
            "design_cost": 175.0,
        },
        {
            "node": "7 nm",
            "year": 2018,
            "wafer_cost": 9800.0,
            "density": 91.2,
            "cost_100m": 0.152,
            "design_cost": 249.0,
        },
        {
            "node": "5 nm",
            "year": 2020,
            "wafer_cost": 16500.0,
            "density": 138.2,
            "cost_100m": 0.169,
            "design_cost": 540.0,
        },
        {
            "node": "3 nm",
            "year": 2022,
            "wafer_cost": 20000.0,
            "density": 215.0,
            "cost_100m": 0.132,
            "design_cost": 600.0,
        },
        {
            "node": "2 nm",
            "year": 2025,
            "wafer_cost": 30000.0,
            "density": 280.0,
            "cost_100m": 0.152,
            "design_cost": 725.0,
        },
    ]

    # Create 2-panel figure with refined width ratios and tight layout
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(8.0, 3.8), gridspec_kw={"width_ratios": [1.14, 1.08]}
    )
    fig.subplots_adjust(wspace=0.38, left=0.08, right=0.935, top=0.88, bottom=0.15)

    # -------------------------------------------------------------------------
    # Panel A: Advanced Foundry Wafer & Design Cost Escalation / Inversion
    # -------------------------------------------------------------------------
    node_years = [n["year"] for n in nodes_data]
    wafer_costs = [n["wafer_cost"] for n in nodes_data]
    design_costs = [n["design_cost"] for n in nodes_data]
    costs_100m = [n["cost_100m"] for n in nodes_data]

    # Shaded vertical era indicator for EUV & GAA multi-patterning
    ax1.axvspan(2017.5, 2026.5, color=COLORS["note_fill"], alpha=0.55, zorder=1)
    ax1.text(
        2022.0,
        220.0,
        "EUV & GAA Era\n(Multi-patterning Surge)",
        ha="center",
        va="center",
        fontsize=4.6,
        fontstyle="italic",
        color=COLORS["muted"],
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="white",
            edgecolor=COLORS["grid"],
            alpha=0.85,
            lw=0.4,
        ),
        zorder=2,
    )

    # Left Y-Axis (Log scale): Wafer Cost ($) and Scaled SoC Design Cost ($M x 10)
    ax1.plot(
        node_years,
        wafer_costs,
        color=COLORS["purple"],
        marker="s",
        linewidth=1.7,
        markersize=4.2,
        label=r"300mm Wafer Cost (\$ USD, +16.2$\times$)",
        zorder=3,
    )
    ax1.plot(
        node_years,
        [
            d * 10 for d in design_costs
        ],  # Scaled for direct visual comparison ($240 -> $7250)
        color=COLORS["blue"],
        marker="o",
        linewidth=1.7,
        markersize=4.2,
        label=r"SoC Design Cost (\$M $\times 10$, +25.9$\times$)",
        zorder=3,
    )

    # Right Y-Axis (Linear scale): Cost per 100M Transistors ($)
    ax1_twin = ax1.twinx()
    ax1_twin.plot(
        node_years,
        costs_100m,
        color=COLORS["constraints_ink"],
        marker="D",
        linewidth=2.0,
        linestyle="--",
        markersize=4.6,
        label=r"Cost per 100M Transistors (\$ USD)",
        zorder=4,
    )

    # Annotations on landmark nodes
    # 28nm Planar Sweet Spot
    ax1.annotate(
        "28nm Planar Sweet Spot\n(\\$3.0k/wafer, \\$0.28/100M)",
        xy=(2011, 3000),
        xytext=(-42, 16),
        textcoords="offset points",
        fontsize=4.7,
        fontweight="bold",
        color=COLORS["ink"],
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="white",
            edgecolor=COLORS["grid"],
            alpha=0.9,
            lw=0.5,
        ),
        arrowprops=dict(arrowstyle="->", color=COLORS["ink"], lw=0.6),
        zorder=6,
    )

    # 7nm EUV stall
    ax1_twin.annotate(
        "7nm (\\$0.15/100M Tr)\nCost scaling stalls",
        xy=(2018, 0.152),
        xytext=(-38, 22),
        textcoords="offset points",
        fontsize=4.6,
        fontweight="bold",
        color=COLORS["constraints_ink"],
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="white",
            edgecolor=COLORS["constraints_ink"],
            alpha=0.9,
            lw=0.5,
        ),
        arrowprops=dict(arrowstyle="->", color=COLORS["constraints_ink"], lw=0.6),
        zorder=6,
    )

    # 2nm GAA Inversion
    ax1.annotate(
        "2nm GAA (\\$30k/wafer)\n\\$725M SoC Design Cost",
        xy=(2025, 30000),
        xytext=(-78, -16),
        textcoords="offset points",
        fontsize=4.7,
        fontweight="bold",
        color=COLORS["purple"],
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="white",
            edgecolor=COLORS["purple"],
            alpha=0.9,
            lw=0.6,
        ),
        arrowprops=dict(arrowstyle="->", color=COLORS["purple"], lw=0.6),
        zorder=6,
    )

    ax1.set_yscale("log")
    ax1.set_xlim(2003, 2026.5)
    ax1.set_ylim(100.0, 60000)
    ax1.set_xticks([2004, 2008, 2011, 2015, 2018, 2020, 2022, 2025])
    ax1.set_xticklabels(
        [
            "'04\n90nm",
            "'08\n40nm",
            "'11\n28nm",
            "'15\n16nm",
            "'18\n7nm",
            "'20\n5nm",
            "'22\n3nm",
            "'25\n2nm",
        ],
        fontsize=5.6,
    )
    ax1.set_xlabel("Node Introduction Year & Feature Scale", fontsize=6.8)
    ax1.set_ylabel(
        r"Wafer Cost (\$) / Scaled Design Cost (\$M $\times 10$)", fontsize=6.6
    )
    ax1_twin.set_ylabel(
        r"Cost per 100M Transistors (USD \$)",
        fontsize=6.6,
        color=COLORS["constraints_ink"],
    )
    ax1_twin.set_ylim(0.0, 2.35)
    ax1_twin.tick_params(axis="y", labelcolor=COLORS["constraints_ink"], labelsize=5.8)

    ax1.set_title(
        "A. Foundry Wafer & Design Cost Inversion (90nm to 2nm)",
        fontsize=7.4,
        fontweight="bold",
        pad=8,
    )
    ax1.grid(True, which="major", color=COLORS["grid"], linewidth=0.5, zorder=0)

    # Combined legend for Panel A
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax1_twin.get_legend_handles_labels()
    ax1.legend(
        h1 + h2,
        l1 + l2,
        loc="upper left",
        fontsize=4.5,
        frameon=True,
        facecolor="white",
        edgecolor="none",
        borderpad=0.2,
    )

    # -------------------------------------------------------------------------
    # Panel B: Corporate R&D Expenditure Escalation (SEC EDGAR 10-K Data)
    # -------------------------------------------------------------------------
    company_configs = [
        {
            "ticker": "NVDA",
            "name": "NVIDIA",
            "color": COLORS["designspace"],
            "marker": "o",
            "lw": 1.9,
            "label": r"NVIDIA (\$0.08B $\rightarrow$ \$22.8B)",
        },
        {
            "ticker": "INTC",
            "name": "Intel",
            "color": COLORS["workload"],
            "marker": "s",
            "lw": 1.6,
            "label": r"Intel (\$3.9B $\rightarrow$ \$17.5B peak)",
        },
        {
            "ticker": "AVGO",
            "name": "Broadcom",
            "color": COLORS["constraints"],
            "marker": "^",
            "lw": 1.5,
            "label": r"Broadcom (\$0.21B $\rightarrow$ \$12.8B)",
        },
        {
            "ticker": "QCOM",
            "name": "Qualcomm",
            "color": COLORS["evidence"],
            "marker": "v",
            "lw": 1.5,
            "label": r"Qualcomm (\$0.34B $\rightarrow$ \$9.6B)",
        },
        {
            "ticker": "AMD",
            "name": "AMD",
            "color": COLORS["methods"],
            "marker": "D",
            "lw": 1.5,
            "label": r"AMD (\$0.65B $\rightarrow$ \$9.8B)",
        },
        {
            "ticker": "TSM",
            "name": "TSMC",
            "color": COLORS["decision"],
            "marker": "P",
            "lw": 1.4,
            "label": r"TSMC (\$0.25B $\rightarrow$ \$8.8B)",
        },
        {
            "ticker": "AAPL",
            "name": "Apple",
            "color": COLORS["muted"],
            "marker": "x",
            "lw": 1.3,
            "label": r"Apple (\$0.38B $\rightarrow$ \$37.5B)",
        },
    ]

    for cfg in company_configs:
        c_recs = [r for r in records if r["ticker"] == cfg["ticker"] and r["rd"] > 0]
        c_recs.sort(key=lambda x: x["year"])
        xs = [r["year"] for r in c_recs]
        ys = [r["rd"] for r in c_recs]
        ax2.plot(
            xs,
            ys,
            color=cfg["color"],
            marker=cfg["marker"],
            linewidth=cfg["lw"],
            markersize=3.6,
            label=cfg["label"],
            zorder=3,
        )

    # Vertical era inflection lines
    ax2.axvline(2005, color=COLORS["muted"], linestyle=":", linewidth=1.1, zorder=1)
    ax2.text(
        2005.3,
        28.5,
        "Dennard\nEnd (~2005)",
        fontsize=4.6,
        fontweight="bold",
        color=COLORS["muted"],
        va="center",
        ha="left",
        bbox=dict(
            boxstyle="round,pad=0.15",
            facecolor="white",
            edgecolor=COLORS["muted"],
            alpha=0.9,
            lw=0.4,
        ),
        zorder=4,
    )

    ax2.axvline(2016, color=COLORS["orange"], linestyle=":", linewidth=1.1, zorder=1)
    ax2.text(
        2016.3,
        34.5,
        "Specialization\nTurn (~2016)",
        fontsize=4.6,
        fontweight="bold",
        color=COLORS["orange"],
        va="top",
        ha="left",
        bbox=dict(
            boxstyle="round,pad=0.15",
            facecolor="white",
            edgecolor=COLORS["orange"],
            alpha=0.9,
            lw=0.4,
        ),
        zorder=4,
    )

    # Annotate NVIDIA's exponential explosion
    ax2.annotate(
        "NVIDIA FY26: \\$22.8B R&D\n(278x escalation since 2000)",
        xy=(2026, 22.8),
        xytext=(-95, -24),
        textcoords="offset points",
        fontsize=4.7,
        fontweight="bold",
        color=COLORS["designspace"],
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="white",
            edgecolor=COLORS["designspace"],
            alpha=0.9,
            lw=0.6,
        ),
        arrowprops=dict(arrowstyle="->", color=COLORS["designspace"], lw=0.6),
        zorder=6,
    )

    ax2.set_xlim(1999.5, 2026.8)
    ax2.set_ylim(0.0, 40.0)
    ax2.set_xticks([2000, 2005, 2010, 2015, 2020, 2025])
    ax2.set_xticklabels(["2000", "2005", "2010", "2015", "2020", "2025"], fontsize=5.8)
    ax2.set_xlabel("Fiscal Year (SEC EDGAR 10-K / 20-F)", fontsize=6.8)
    ax2.set_ylabel(r"Annual R&D Expenditure (US\$ Billions)", fontsize=6.6)
    ax2.set_title(
        "B. Corporate R&D Escalation Wall (2000–2026)",
        fontsize=7.4,
        fontweight="bold",
        pad=8,
    )
    ax2.grid(True, which="major", color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax2.legend(
        loc="upper left",
        fontsize=4.3,
        frameon=True,
        facecolor="white",
        edgecolor="none",
        borderpad=0.2,
    )

    # Save to all target locations (receipts and chapter 2 image directories)
    target_triplets = [
        (out_receipts_svg, out_receipts_pdf, out_receipts_png),
        (out_ch2_svg, out_ch2_pdf, out_ch2_png),
    ]

    for svg_path, pdf_path, png_path in target_triplets:
        plt.savefig(svg_path, format="svg", bbox_inches="tight")
        plt.savefig(pdf_path, format="pdf", bbox_inches="tight")
        plt.savefig(png_path, format="png", dpi=300, bbox_inches="tight")

    plt.close()
    print("Generated publication-quality figures successfully:")
    print(f"  - Receipts: {out_receipts_svg}, {out_receipts_pdf}, {out_receipts_png}")
    print(f"  - Chapter2: {out_ch2_svg}, {out_ch2_pdf}, {out_ch2_png}")


if __name__ == "__main__":
    main()
