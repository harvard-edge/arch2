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
    datasets_dir = REPO_ROOT / "data" / "datasets"
    study7_dir = REPO_ROOT / "data" / "studies" / "07-foundry-cost-and-rd-wall"
    data_csv = datasets_dir / "sec_edgar_semiconductor_rd_economics.csv"
    nodes_csv = datasets_dir / "foundry_node_economics_timeline.csv"

    # Destination output paths
    out_dataset_png = datasets_dir / "fig-foundry-wafer-cost-and-rd-wall.png"
    out_dataset_pdf = datasets_dir / "fig-foundry-wafer-cost-and-rd-wall.pdf"
    out_dataset_svg = datasets_dir / "fig-foundry-wafer-cost-and-rd-wall.svg"

    chapter2_img_dir = (
        REPO_ROOT / "book" / "contents" / "chapters" / "02-pressures" / "images"
    )
    chapter2_img_dir.mkdir(parents=True, exist_ok=True)
    out_ch2_png = chapter2_img_dir / "fig-ch02-foundry-cost-inversion-and-rd-wall.png"
    out_ch2_pdf = chapter2_img_dir / "fig-ch02-foundry-cost-inversion-and-rd-wall.pdf"
    out_ch2_svg = chapter2_img_dir / "fig-ch02-foundry-cost-inversion-and-rd-wall.svg"

    study7_png = study7_dir / "fig-foundry-wafer-cost-and-rd-wall.png"
    study7_pdf = study7_dir / "fig-foundry-wafer-cost-and-rd-wall.pdf"
    study7_svg = study7_dir / "fig-foundry-wafer-cost-and-rd-wall.svg"

    obs_img_dir = REPO_ROOT / "www" / "images" / "observatory"
    obs_img_dir.mkdir(parents=True, exist_ok=True)
    obs_png = obs_img_dir / "fig-foundry-wafer-cost-and-rd-wall.png"
    obs_pdf = obs_img_dir / "fig-foundry-wafer-cost-and-rd-wall.pdf"
    obs_svg = obs_img_dir / "fig-foundry-wafer-cost-and-rd-wall.svg"

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

    # 2. Node Economics Reference Points (from foundry_node_economics_timeline.csv)
    nodes_data: list[dict] = []
    with open(nodes_csv, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        n_header = []
        for row in reader:
            if not row or row[0].startswith("#"):
                continue
            if not n_header:
                n_header = row
                continue
            d = dict(zip(n_header, row))
            nodes_data.append(
                {
                    "node": d["process_node"],
                    "year": int(d["introduction_year"]),
                    "wafer_cost": float(d["wafer_cost_usd"]),
                    "density": float(d["transistor_density_m_tr_mm2"]),
                    "cost_100m": float(d["cost_per_100m_transistors_usd"]),
                    "design_cost": float(d["design_cost_per_soc_usd_million"]),
                }
            )

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

    # Dynamic scaling multiples for Panel A legend
    wafer_mult = wafer_costs[-1] / wafer_costs[0]
    design_mult = design_costs[-1] / design_costs[0]

    # Left Y-Axis (Log scale): Wafer Cost ($) and Scaled SoC Design Cost ($M x 10)
    ax1.plot(
        node_years,
        wafer_costs,
        color=COLORS["purple"],
        marker="s",
        linewidth=1.7,
        markersize=4.2,
        label=f"300mm Wafer Cost (\\$ USD, +{wafer_mult:.1f}x)",
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
        label=f"SoC Design Cost (\\$M \u00d7 10, +{design_mult:.1f}x)",
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
        label="Cost per 100M Transistors (\\$ USD)",
        zorder=4,
    )

    # Dynamic Landmark Node Annotations
    n28 = next(n for n in nodes_data if "28" in n["node"])
    n7 = next(n for n in nodes_data if "7" in n["node"] and "725" not in n["node"])
    n2 = next(n for n in nodes_data if n["node"].strip() in ("2 nm", "2nm"))

    # 28nm Planar Sweet Spot
    ax1.annotate(
        f"28nm Planar Sweet Spot\n(\\${n28['wafer_cost']/1000:.1f}k/wafer, \\${n28['cost_100m']:.2f}/100M)",
        xy=(n28["year"], n28["wafer_cost"]),
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
        f"7nm (\\${n7['cost_100m']:.2f}/100M Tr)\nCost scaling stalls",
        xy=(n7["year"], n7["cost_100m"]),
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
        f"2nm GAA (\\${int(n2['wafer_cost']/1000)}k/wafer)\n\\${int(n2['design_cost'])}M SoC Design Cost",
        xy=(n2["year"], n2["wafer_cost"]),
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
        "Wafer Cost (\\$) / Scaled Design Cost (\\$M \u00d7 10)", fontsize=6.6
    )
    ax1_twin.set_ylabel(
        "Cost per 100M Transistors (USD \\$)",
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
        },
        {
            "ticker": "INTC",
            "name": "Intel",
            "color": COLORS["workload"],
            "marker": "s",
            "lw": 1.6,
        },
        {
            "ticker": "AVGO",
            "name": "Broadcom",
            "color": COLORS["constraints"],
            "marker": "^",
            "lw": 1.5,
        },
        {
            "ticker": "QCOM",
            "name": "Qualcomm",
            "color": COLORS["evidence"],
            "marker": "v",
            "lw": 1.5,
        },
        {
            "ticker": "AMD",
            "name": "AMD",
            "color": COLORS["methods"],
            "marker": "D",
            "lw": 1.5,
        },
        {
            "ticker": "TSM",
            "name": "TSMC",
            "color": COLORS["decision"],
            "marker": "P",
            "lw": 1.4,
        },
        {
            "ticker": "AAPL",
            "name": "Apple",
            "color": COLORS["muted"],
            "marker": "x",
            "lw": 1.3,
        },
    ]

    for cfg in company_configs:
        c_recs = [r for r in records if r["ticker"] == cfg["ticker"] and r["rd"] > 0]
        c_recs.sort(key=lambda x: x["year"])
        xs = [r["year"] for r in c_recs]
        ys = [r["rd"] for r in c_recs]
        start_rd = ys[0]
        latest_rd = ys[-1]
        if cfg["ticker"] == "INTC":
            peak_rd = max(ys)
            label = f"{cfg['name']} (\\${start_rd:.1f}B \u2192 \\${peak_rd:.1f}B peak)"
        else:
            fmt = ".2f" if start_rd < 1 else ".1f"
            label = f"{cfg['name']} (\\${start_rd:{fmt}}B \u2192 \\${latest_rd:.1f}B)"
        ax2.plot(
            xs,
            ys,
            color=cfg["color"],
            marker=cfg["marker"],
            linewidth=cfg["lw"],
            markersize=3.6,
            label=label,
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

    # Annotate NVIDIA exponential explosion dynamically
    nvda_recs = [r for r in records if r["ticker"] == "NVDA" and r["rd"] > 0]
    nvda_recs.sort(key=lambda x: x["year"])
    nvda_base = nvda_recs[0]
    nvda_latest = nvda_recs[-1]
    nvda_mult = int(round(nvda_latest["rd"] / nvda_base["rd"]))

    ax2.annotate(
        f"NVIDIA FY26: \\${nvda_latest['rd']:.1f}B R&D\n({nvda_mult}x escalation since {nvda_base['year']})",
        xy=(nvda_latest["year"], nvda_latest["rd"]),
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
    ax2.set_ylabel("Annual R&D Expenditure (US\\$ Billions)", fontsize=6.6)
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

    # Save to all target locations
    target_triplets = [
        (out_dataset_svg, out_dataset_pdf, out_dataset_png),
        (out_ch2_svg, out_ch2_pdf, out_ch2_png),
        (study7_svg, study7_pdf, study7_png),
        (obs_svg, obs_pdf, obs_png),
    ]

    for svg_path, pdf_path, png_path in target_triplets:
        plt.savefig(svg_path, format="svg", bbox_inches="tight")
        plt.savefig(pdf_path, format="pdf", bbox_inches="tight")
        plt.savefig(png_path, format="png", dpi=300, bbox_inches="tight")

    plt.close()
    print(
        "Generated publication-quality figures successfully across datasets, ch2, study7, and observatory."
    )


if __name__ == "__main__":
    main()
