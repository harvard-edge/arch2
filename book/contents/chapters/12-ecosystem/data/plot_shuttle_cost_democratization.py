#!/usr/bin/env python3
"""
Chapter 12 Money Plot (Final Polished Version):
Shuttle Tapeout Accessibility, Physical Fabrication Cost Democratization,
and the Silicon Submission Renaissance (1981-2026).
"""

import csv
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.patches import Patch
import numpy as np

# Connect repo root for Arch2 plotting style
REPO_ROOT = Path("/Users/VJ/GitHub/Arch2")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style

apply_style()


def _declare_font_stack(svg_path: Path) -> None:
    """Ensure font stack is explicitly declared in SVG for headless text rendering."""
    text = svg_path.read_text(encoding="utf-8")
    if '<style type="text/css">' not in text:
        text = text.replace(
            "<defs>",
            '<defs>\n  <style type="text/css">*{font-family: Arial, Helvetica, sans-serif;}</style>',
            1,
        )
        svg_path.write_text(text, encoding="utf-8")


def main():
    scratch_dir = Path(
        "/Users/VJ/.gemini/antigravity-cli/brain/1eede783-2881-4556-9742-43bf7b56ec23/scratch"
    )
    econ_csv = scratch_dir / "historical_silicon_fabrication_economics.csv"
    tt_csv = scratch_dir / "tinytapeout_shuttle_submissions_2022_2026.csv"

    chapter_img_dir = (
        REPO_ROOT / "book" / "contents" / "chapters" / "12-ecosystem" / "images"
    )
    chapter_img_dir.mkdir(parents=True, exist_ok=True)
    chapter_data_dir = (
        REPO_ROOT / "book" / "contents" / "chapters" / "12-ecosystem" / "data"
    )
    chapter_data_dir.mkdir(parents=True, exist_ok=True)

    out_svg = chapter_img_dir / "fig-shuttle-cost-democratization.svg"
    out_pdf = chapter_img_dir / "fig-shuttle-cost-democratization.pdf"
    out_png = chapter_img_dir / "fig-shuttle-cost-democratization.png"

    # --- Dataset 1: Historical Commercial vs Open Economics ---
    comm_points = [
        ("2 µm\n(1981)", 35000, 450 * 4, 1200),  # 4mm^2 standard tile
        ("0.5 µm\n(1995)", 120000, 1200 * 4, 4500),
        ("180 nm\n(2001)", 380000, 2200 * 4, 8800),
        ("65 nm\n(2007)", 1600000, 9500 * 4, 38000),
        ("28 nm\n(2013)", 4500000, 18500 * 5, 92500),  # 5mm^2 prototype
        ("16 nm\n(2016)", 9800000, 36000 * 5, 180000),
        ("7 nm\n(2019)", 26000000, 92000 * 5, 460000),
        ("3 nm\n(2024)", 48000000, 260000 * 5, 1300000),
        (
            "Open PDK\n('22–'26)",
            450000,
            975 * 0.016,
            50,
        ),  # Tiny Tapeout tile ($50-$300)
    ]

    # --- Dataset 2: Tiny Tapeout Shuttle Submissions ---
    tt_runs = []
    tt_dates = []
    tt_designs = []
    tt_cumul = []
    tt_pdk_group = []

    with open(tt_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(l for l in f if not l.startswith("#"))
        for row in reader:
            tt_runs.append(row["RunName"])
            close_d = row["CloseDate"]
            parts = close_d.split("-")
            short_d = f"{parts[1]}/{parts[0][2:]}"
            tt_dates.append(short_d)

            d_count = int(row["SubmittedDesignsCount"])
            tt_designs.append(d_count)
            tt_cumul.append(int(row["CumulativeDesignsCount"]))

            pdk = row["PDK"]
            if "SKY130" in pdk:
                tt_pdk_group.append("SKY130")
            elif "SG13G2" in pdk or "IHP" in pdk:
                tt_pdk_group.append("SG13G2")
            else:
                tt_pdk_group.append("GF180MCU")

    # Create figure with 2 panels
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(7.2, 3.4), gridspec_kw={"width_ratios": [1.02, 1.28]}
    )
    fig.subplots_adjust(wspace=0.48, bottom=0.22, top=0.88, left=0.09, right=0.91)

    # -------------------------------------------------------------
    # PANEL A: The Silicon Fabrication Cost Barrier & Open Collapse
    # -------------------------------------------------------------
    x_nodes = np.arange(len(comm_points))
    labels_nodes = [p[0] for p in comm_points]
    mask_costs = [p[1] for p in comm_points[:-1]]  # exclude open pdk from mask line
    mpw_costs = [p[2] for p in comm_points[:-1]]  # commercial prototype

    # Plot Commercial Mask Set Cost (Red)
    ax1.plot(
        x_nodes[:-1],
        mask_costs,
        color=COLORS["constraints"],
        marker="s",
        markersize=3.8,
        linewidth=1.3,
        label=r"Full Reticle Mask Set ($C_{\mathrm{mask}}$)",
        zorder=4,
    )

    # Plot Commercial Prototype Cost (Purple)
    ax1.plot(
        x_nodes[:-1],
        mpw_costs,
        color=COLORS["designspace"],
        marker="o",
        markersize=3.8,
        linewidth=1.3,
        label="Commercial MPW (4–5 mm²)",
        zorder=4,
    )

    # Plot Open PDK / Tiny Tapeout Disruption (Green Star)
    open_x = x_nodes[-1]
    open_cost = comm_points[-1][3]
    ax1.scatter(
        [open_x],
        [open_cost],
        color=COLORS["evidence"],
        edgecolor=COLORS["ink"],
        marker="*",
        s=140,
        linewidth=0.8,
        label="Tiny Tapeout Tile ($50–$300)",
        zorder=6,
    )

    # Also plot Google Open MPW $0 point as reference annotation
    ax1.scatter(
        [open_x],
        [15],  # Visual floor on log scale
        color=COLORS["workload"],
        edgecolor=COLORS["ink"],
        marker="D",
        s=36,
        linewidth=0.8,
        label="Google Open MPW (Free: $0)",
        zorder=6,
    )

    # University Budget Threshold Line ($50k)
    ax1.axhline(50000, color=COLORS["muted"], linestyle="--", linewidth=0.8, zorder=2)
    ax1.text(
        0.05,
        85000,
        "Academic Grant Ceiling (~$50k)",
        fontsize=4.9,
        fontweight="bold",
        color=COLORS["muted"],
        bbox=dict(
            boxstyle="square,pad=0.15",
            facecolor="#ffffff",
            edgecolor="none",
            alpha=0.85,
        ),
        zorder=5,
    )

    # Shaded Lockout Zone (Graduate Apprenticeship Gap)
    ax1.axhspan(
        50000,
        1e8,
        xmin=0.42,
        xmax=0.88,
        color=COLORS["constraints"],
        alpha=0.07,
        zorder=1,
    )
    ax1.text(
        4.8,
        2.2e6,
        "Commercial Lockout Zone\n(Apprenticeship Gap)",
        fontsize=4.9,
        fontweight="bold",
        ha="center",
        va="center",
        color=COLORS["constraints_ink"],
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor="#FDECEC",
            edgecolor=COLORS["constraints"],
            linewidth=0.5,
        ),
        zorder=5,
    )

    ax1.set_yscale("log")
    ax1.set_ylim(10, 1.2e8)
    ax1.set_xlim(-0.6, len(comm_points) - 0.4)
    ax1.set_xticks(x_nodes)
    ax1.set_xticklabels(labels_nodes, fontsize=4.6, color=COLORS["ink"])
    ax1.set_ylabel(
        "Fabrication Cost (USD, Log Scale)", fontsize=6.2, color=COLORS["ink"]
    )
    ax1.set_title(
        "A. Physical Silicon Fabrication Cost Barrier",
        fontsize=6.8,
        fontweight="bold",
        pad=8,
    )
    ax1.grid(
        True, which="both", color=COLORS["grid"], linewidth=0.45, alpha=0.7, zorder=0
    )
    ax1.legend(
        loc="upper left", fontsize=4.4, framealpha=0.92, edgecolor=COLORS["grid"]
    )

    # -------------------------------------------------------------
    # PANEL B: The Silicon Submission Renaissance (Tiny Tapeout Real Data)
    # -------------------------------------------------------------
    x_tt = np.arange(len(tt_runs))

    pdk_colors = {
        "SKY130": COLORS["workload"],  # Teal
        "SG13G2": COLORS["evidence"],  # Green
        "GF180MCU": COLORS["methods"],  # Amber
    }
    bar_colors = [pdk_colors[g] for g in tt_pdk_group]

    bars = ax2.bar(
        x_tt,
        tt_designs,
        color=bar_colors,
        width=0.64,
        alpha=0.88,
        edgecolor=COLORS["ink"],
        linewidth=0.35,
        zorder=3,
        label="Per-Shuttle Submissions",
    )

    ax2.set_ylim(0, 680)
    ax2.set_ylabel("Submissions per Shuttle", fontsize=6.2, color=COLORS["ink"])
    ax2.set_title(
        "B. Open Silicon Submission Renaissance", fontsize=6.8, fontweight="bold", pad=8
    )
    ax2.grid(True, axis="y", color=COLORS["grid"], linewidth=0.45, alpha=0.7, zorder=0)

    # Twin axis for Cumulative Tapeout Count
    ax2_cumul = ax2.twinx()
    line_cumul = ax2_cumul.plot(
        x_tt,
        tt_cumul,
        color=COLORS["constraints"],
        marker="o",
        markersize=2.8,
        linewidth=1.2,
        zorder=5,
        label="Cumulative Tapeouts",
    )
    ax2_cumul.set_ylim(0, 4800)
    ax2_cumul.set_ylabel(
        "Cumulative Verified Tapeouts", fontsize=6.2, color=COLORS["constraints_ink"]
    )
    ax2_cumul.tick_params(axis="y", colors=COLORS["constraints_ink"], labelsize=5.4)

    # Subsample X-ticks: every 2 runs, with 45 degree rotation
    step = 2
    ax2.set_xticks(x_tt[::step])
    ax2.set_xticklabels(
        [f"{tt_runs[i]}\n({tt_dates[i]})" for i in range(0, len(tt_runs), step)],
        fontsize=4.4,
        rotation=45,
        ha="right",
        color=COLORS["ink"],
    )

    # Custom PDK legend in Panel B (compact in upper left)
    legend_elements = [
        Patch(
            facecolor=COLORS["workload"],
            edgecolor=COLORS["ink"],
            linewidth=0.35,
            label="SKY130 (130nm)",
        ),
        Patch(
            facecolor=COLORS["evidence"],
            edgecolor=COLORS["ink"],
            linewidth=0.35,
            label="SG13G2 (130nm SiGe)",
        ),
        Patch(
            facecolor=COLORS["methods"],
            edgecolor=COLORS["ink"],
            linewidth=0.35,
            label="GF180 (180nm)",
        ),
        plt.Line2D(
            [0],
            [0],
            color=COLORS["constraints"],
            marker="o",
            markersize=2.5,
            linewidth=1.1,
            label="Cumulative",
        ),
    ]
    ax2.legend(
        handles=legend_elements,
        loc="upper left",
        fontsize=4.4,
        framealpha=0.92,
        edgecolor=COLORS["grid"],
    )

    # Annotate record shuttle: TTIHP25a (547 designs) placed to the RIGHT of the bar
    rec_idx = tt_runs.index("TTIHP25a")
    ax2.annotate(
        "TTIHP25a: 547 designs\n(IHP 130nm BiCMOS)",
        xy=(rec_idx, 547),
        xytext=(rec_idx + 1.2, 580),
        arrowprops=dict(arrowstyle="->", color=COLORS["ink"], linewidth=0.65),
        fontsize=4.6,
        fontweight="bold",
        color=COLORS["ink"],
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="#ffffff",
            edgecolor=COLORS["evidence"],
            linewidth=0.6,
        ),
        zorder=6,
    )

    # Annotate cumulative milestone: 4,026 tapeouts
    last_idx = len(tt_runs) - 1
    ax2_cumul.annotate(
        "4,026 Cumulative\nSilicon Designs",
        xy=(last_idx, tt_cumul[-1]),
        xytext=(last_idx - 6.5, 2300),
        arrowprops=dict(arrowstyle="->", color=COLORS["constraints"], linewidth=0.65),
        fontsize=4.7,
        fontweight="bold",
        color=COLORS["constraints_ink"],
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="#FDECEC",
            edgecolor=COLORS["constraints"],
            linewidth=0.6,
        ),
        zorder=6,
    )

    # Save vector & raster outputs
    plt.savefig(out_svg, dpi=300, bbox_inches="tight")
    plt.savefig(out_pdf, dpi=300, bbox_inches="tight")
    plt.savefig(out_png, dpi=300, bbox_inches="tight")
    _declare_font_stack(out_svg)

    # Copy files to chapter data directory
    import shutil

    shutil.copy(
        econ_csv, chapter_data_dir / "fig-shuttle-cost-democratization-economics.csv"
    )
    shutil.copy(
        tt_csv, chapter_data_dir / "fig-shuttle-cost-democratization-submissions.csv"
    )

    print(f"Figure successfully updated:")
    print(f"  SVG: {out_svg}")
    print(f"  PDF: {out_pdf}")
    print(f"  PNG: {out_png}")


if __name__ == "__main__":
    main()
