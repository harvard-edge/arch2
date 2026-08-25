"""
The Foundry Cost Inversion & Corporate R&D Escalation Wall (2000-2026)
----------------------------------------------------------------------
Empirical "Money Plot" for Chapter 2 (Pressures):
Panel A: Advanced Foundry Wafer & Transistor Cost Inversion across nodes (90nm to 2nm),
         contrasting 300mm wafer price ($/wafer) and transistor density (MTr/mm2)
         with the Cost per 100 Million Transistors ($/100M Tr).
Panel B: Corporate R&D Expenditure Escalation across semiconductor titans (2000-2026)
         grounded in official SEC EDGAR 10-K/20-F XBRL filings.
"""

import csv
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path("/Users/VJ/GitHub/Arch2")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style

apply_style()


def main():
    scratch_dir = Path(
        "/Users/VJ/.gemini/antigravity-cli/brain/76c6dd2e-a283-4cda-8a38-ad40696d26d7/scratch"
    )
    node_csv = scratch_dir / "foundry_node_cost_inversion.csv"
    sec_csv = scratch_dir / "sec_edgar_semiconductor_rd.csv"

    out_svg = (
        REPO_ROOT
        / "book"
        / "contents"
        / "chapters"
        / "02-pressures"
        / "images"
        / "fig-ch02-foundry-cost-inversion-and-rd-wall.svg"
    )
    out_pdf = (
        REPO_ROOT
        / "book"
        / "contents"
        / "chapters"
        / "02-pressures"
        / "images"
        / "fig-ch02-foundry-cost-inversion-and-rd-wall.pdf"
    )
    out_png = (
        REPO_ROOT
        / "book"
        / "contents"
        / "chapters"
        / "02-pressures"
        / "images"
        / "fig-ch02-foundry-cost-inversion-and-rd-wall.png"
    )
    out_svg.parent.mkdir(parents=True, exist_ok=True)

    scratch_png = scratch_dir / "fig-ch02-foundry-cost-inversion-and-rd-wall.png"
    scratch_pdf = scratch_dir / "fig-ch02-foundry-cost-inversion-and-rd-wall.pdf"
    scratch_svg = scratch_dir / "fig-ch02-foundry-cost-inversion-and-rd-wall.svg"

    # Also save to data/source-receipts
    project_script = (
        REPO_ROOT
        / "data"
        / "source-receipts"
        / "plot_foundry_cost_inversion_and_rd_wall.py"
    )

    # 1. Load Node Economics Data
    nodes = []
    with open(node_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            nodes.append(
                {
                    "node": row["node_name"],
                    "year": float(row["intro_year"]),
                    "density": float(row["transistor_density_mtr_mm2"]),
                    "wafer_cost": float(row["wafer_cost_300mm_usd"]),
                    "cost_mm2": float(row["wafer_cost_per_mm2_usd"]),
                    "cost_100m": float(row["cost_per_100m_transistors_usd"]),
                    "euv": int(row["euv_layers"]),
                }
            )

    # 2. Load SEC EDGAR R&D Data
    sec_records = []
    with open(sec_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sec_records.append(
                {
                    "company": row["company"],
                    "segment": row["segment"],
                    "year": int(row["fiscal_year"]),
                    "rd": float(row["rd_expense_usd"])
                    if row["rd_expense_usd"]
                    else 0.0,
                    "rev": float(row["revenue_usd"]) if row["revenue_usd"] else 0.0,
                    "intensity": float(row["rd_intensity_pct"])
                    if row["rd_intensity_pct"]
                    else 0.0,
                }
            )

    # Create 2-panel figure with refined width ratios and subplots layout
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(7.8, 3.8), gridspec_kw={"width_ratios": [1.12, 1.05]}
    )
    fig.subplots_adjust(wspace=0.40, left=0.08, right=0.935, top=0.88, bottom=0.18)

    # -------------------------------------------------------------
    # Panel A: Advanced Foundry Wafer & Transistor Cost Inversion
    # -------------------------------------------------------------
    years = [n["year"] for n in nodes]
    wafer_costs = [n["wafer_cost"] for n in nodes]
    densities = [n["density"] for n in nodes]
    costs_100m = [n["cost_100m"] for n in nodes]

    # Shaded vertical barrier for EUV / GAA era
    ax1.axvspan(2017.5, 2026.5, color=COLORS["note_fill"], alpha=0.55, zorder=1)
    ax1.text(
        2022.0,
        14.0,
        "EUV & GAA Era\n(Multi-patterning Surge)",
        ha="center",
        va="bottom",
        fontsize=4.6,
        fontstyle="italic",
        color=COLORS["muted"],
        zorder=2,
    )

    # Primary axis (Log scale: Wafer Cost and Density)
    ax1.plot(
        years,
        wafer_costs,
        color=COLORS["purple"],
        marker="s",
        linewidth=1.7,
        markersize=4.2,
        label=r"300mm Wafer Cost (\$ USD, +16.2$\times$)",
        zorder=3,
    )
    ax1.plot(
        years,
        densities,
        color=COLORS["blue"],
        marker="o",
        linewidth=1.7,
        markersize=4.2,
        label=r"Logic Density (MTr/mm$^2$, +224$\times$)",
        zorder=3,
    )

    # Secondary y-axis for Cost per 100M Transistors
    ax1_twin = ax1.twinx()
    ax1_twin.plot(
        years,
        costs_100m,
        color=COLORS["constraints_ink"],
        marker="D",
        linewidth=2.0,
        linestyle="--",
        markersize=4.6,
        label=r"Cost per 100M Transistors (\$ USD)",
        zorder=4,
    )

    # Annotate landmark nodes on Panel A
    for n in nodes:
        name = (
            n["node"]
            .replace(" (N7)", "")
            .replace(" (N5)", "")
            .replace(" (N3E)", "")
            .replace(" (N2)", "")
        )
        y_w = n["wafer_cost"]
        y_c = n["cost_100m"]

        if name == "28 nm":
            ax1.annotate(
                "28nm Planar Sweet Spot\n(\\$3.0k/wafer, \\$0.28/100M)",
                xy=(n["year"], y_w),
                xytext=(-38, 16),
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
        elif name == "7 nm":
            ax1_twin.annotate(
                "7nm (\\$0.15/100M Tr)\nCost scaling stalls",
                xy=(n["year"], y_c),
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
                arrowprops=dict(
                    arrowstyle="->", color=COLORS["constraints_ink"], lw=0.6
                ),
                zorder=6,
            )
        elif name == "2 nm":
            ax1.annotate(
                "2nm GAA (\\$30k/wafer)\nCost Inverts (\\$0.15/100M)",
                xy=(n["year"], y_w),
                xytext=(-72, -15),
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
    ax1.set_ylim(1.0, 55000)
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
    ax1.set_ylabel(r"Wafer Cost (\$) / Logic Density (MTr/mm$^2$)", fontsize=6.6)
    ax1_twin.set_ylabel(
        r"Cost per 100M Transistors (USD \$)",
        fontsize=6.6,
        color=COLORS["constraints_ink"],
    )
    ax1_twin.set_ylim(0.0, 2.35)
    ax1_twin.tick_params(axis="y", labelcolor=COLORS["constraints_ink"], labelsize=5.8)

    ax1.set_title(
        "A. Foundry Transistor Cost Inversion (28nm to 2nm)",
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
        fontsize=4.6,
        frameon=True,
        facecolor="white",
        edgecolor="none",
        borderpad=0.2,
    )

    # -------------------------------------------------------------
    # Panel B: Corporate R&D Escalation Wall (SEC EDGAR 10-K Data)
    # -------------------------------------------------------------
    companies = [
        {
            "name": "NVIDIA",
            "color": COLORS["designspace"],
            "marker": "o",
            "lw": 1.9,
            "label": r"NVIDIA (\$0.08B $\rightarrow$ \$18.5B)",
        },
        {
            "name": "Intel",
            "color": COLORS["workload"],
            "marker": "s",
            "lw": 1.6,
            "label": r"Intel (\$3.9B $\rightarrow$ \$17.5B peak)",
        },
        {
            "name": "Broadcom",
            "color": COLORS["constraints"],
            "marker": "^",
            "lw": 1.5,
            "label": r"Broadcom (\$2.7B $\rightarrow$ \$11.0B)",
        },
        {
            "name": "Qualcomm",
            "color": COLORS["evidence"],
            "marker": "v",
            "lw": 1.5,
            "label": r"Qualcomm (\$0.34B $\rightarrow$ \$9.0B)",
        },
        {
            "name": "AMD",
            "color": COLORS["methods"],
            "marker": "D",
            "lw": 1.5,
            "label": r"AMD (\$0.65B $\rightarrow$ \$8.1B)",
        },
        {
            "name": "Arm",
            "color": COLORS["decision"],
            "marker": "P",
            "lw": 1.4,
            "label": r"Arm (\$1.0B $\rightarrow$ \$2.8B, 61% rev)",
        },
    ]

    for comp in companies:
        c_records = [
            r for r in sec_records if r["company"] == comp["name"] and r["rd"] > 0
        ]
        c_records.sort(key=lambda x: x["year"])
        xs = [r["year"] for r in c_records]
        ys = [r["rd"] / 1e9 for r in c_records]
        ax2.plot(
            xs,
            ys,
            color=comp["color"],
            marker=comp["marker"],
            linewidth=comp["lw"],
            markersize=3.8,
            label=comp["label"],
            zorder=3,
        )

    # Vertical era inflection lines with boxed callouts
    ax2.axvline(2005, color=COLORS["muted"], linestyle=":", linewidth=1.1, zorder=1)
    ax2.text(
        2005.3,
        10.5,
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
        19.7,
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
        "NVIDIA FY26: \\$18.50B R&D\n(230x escalation since 2001)",
        xy=(2026, 18.497),
        xytext=(-88, -28),
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
    ax2.set_ylim(0.0, 20.5)
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
        fontsize=4.5,
        frameon=True,
        facecolor="white",
        edgecolor="none",
        borderpad=0.2,
    )

    # Save to project image assets, receipts, and scratch
    for svg_p, pdf_p, png_p in [
        (out_svg, out_pdf, out_png),
        (scratch_svg, scratch_pdf, scratch_png),
    ]:
        plt.savefig(svg_p, format="svg", bbox_inches="tight")
        plt.savefig(pdf_p, format="pdf", bbox_inches="tight")
        plt.savefig(png_p, format="png", dpi=300, bbox_inches="tight")
    plt.close()
    print(
        f"Generated Foundry Cost Inversion & R&D Wall plot -> {out_svg}, {out_pdf}, {out_png}"
    )


if __name__ == "__main__":
    main()
