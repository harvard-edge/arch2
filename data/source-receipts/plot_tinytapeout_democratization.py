"""
Open Silicon Democratization & The 3,000x Fabrication Cost Collapse
-------------------------------------------------------------------
Architecture 2.0 Empirical Provenance & Figure Generator (Track 6)

Panel A: Cumulative Custom Silicon Submissions & Domain Specialization (2022-2026)
         across 27 Tiny Tapeout shuttle rounds (4,780+ designs), showing the
         transition from basic educational logic to RISC-V, Neural Accelerators,
         DSP audio, Demoscene graphics, and BiCMOS RF/Analog.
Panel B: The 45-Year Historical Silicon Fabrication Cost Collapse (1981-2026),
         tracing the 3,000x cost drop from $150,000 dedicated mask sets down to
         $50-$100 fine-grain multiplexed custom silicon slots.
"""

import csv
import sys
from datetime import datetime
from pathlib import Path
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style

apply_style()


def parse_census_csv(filepath: Path) -> list[dict]:
    """Parse census CSV, skipping metadata comments."""
    rows = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = None
        for line in reader:
            if not line or line[0].startswith("#"):
                continue
            if header is None:
                header = line
                continue
            row_dict = dict(zip(header, line))
            rows.append(row_dict)
    return rows


def parse_cost_csv(filepath: Path) -> list[dict]:
    """Parse historical cost CSV, skipping metadata comments."""
    rows = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = None
        for line in reader:
            if not line or line[0].startswith("#"):
                continue
            if header is None:
                header = line
                continue
            row_dict = dict(zip(header, line))
            rows.append(row_dict)
    return rows


def main():
    receipts_dir = REPO_ROOT / "data" / "source-receipts"
    census_csv = receipts_dir / "tinytapeout_democratization_census.csv"
    cost_csv = receipts_dir / "shuttle_cost_historical_collapse.csv"

    out_receipt_png = receipts_dir / "fig-tinytapeout-democratization-census.png"
    out_receipt_pdf = receipts_dir / "fig-tinytapeout-democratization-census.pdf"
    out_receipt_svg = receipts_dir / "fig-tinytapeout-democratization-census.svg"

    out_book_dir = (
        REPO_ROOT / "book" / "contents" / "chapters" / "01-moonshot" / "images"
    )
    out_book_dir.mkdir(parents=True, exist_ok=True)
    out_book_png = out_book_dir / "fig-ch01-tinytapeout-democratization-census.png"
    out_book_pdf = out_book_dir / "fig-ch01-tinytapeout-democratization-census.pdf"
    out_book_svg = out_book_dir / "fig-ch01-tinytapeout-democratization-census.svg"

    # 1. Load Data
    census_data = parse_census_csv(census_csv)
    cost_data = parse_cost_csv(cost_csv)

    # 2. Setup Figure
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(7.8, 3.8), gridspec_kw={"width_ratios": [1.18, 1.02]}
    )
    fig.subplots_adjust(wspace=0.38, left=0.07, right=0.96, top=0.88, bottom=0.17)

    # -------------------------------------------------------------
    # Panel A: Cumulative Submissions & Domain Breakdown (2022-2026)
    # -------------------------------------------------------------
    dates = []
    cum_subs = []
    shuttle_codes = []
    dom_cpus = []
    dom_neural = []
    dom_audio = []
    dom_games = []
    dom_analog = []
    dom_logic = []

    for r in census_data:
        dt = datetime.strptime(r["tapeout_deadline"][:10], "%Y-%m-%d")
        dates.append(dt)
        cum_subs.append(int(r["cumulative_submissions"]))
        shuttle_codes.append(r["shuttle_code"])
        dom_cpus.append(int(r["domain_cpus_riscv_count"]))
        dom_neural.append(int(r["domain_neural_accel_count"]))
        dom_audio.append(int(r["domain_audio_dsp_count"]))
        dom_games.append(int(r["domain_games_graphics_count"]))
        dom_analog.append(int(r["domain_analog_rf_count"]))
        dom_logic.append(int(r["domain_digital_logic_count"]))

    date_nums = mdates.date2num(dates)
    width = 22  # bar width in days

    b_logic = np.array(dom_logic)
    b_analog = np.array(dom_analog)
    b_games = np.array(dom_games)
    b_audio = np.array(dom_audio)
    b_neural = np.array(dom_neural)
    b_cpus = np.array(dom_cpus)

    c_logic = "#C5CBD3"  # crisp soft slate
    c_cpus = COLORS["purple"]  # violet for CPUs/RISC-V
    c_neural = COLORS["orange"]  # amber for Neural/AI
    c_audio = COLORS["blue"]  # teal for Audio/DSP
    c_games = COLORS["magenta"]  # magenta for Games/Graphics
    c_analog = COLORS["green"]  # green for Analog/RF

    ax1.bar(
        date_nums,
        b_logic,
        width=width,
        color=c_logic,
        label="Digital Logic / Periph.",
        zorder=2,
    )
    ax1.bar(
        date_nums,
        b_analog,
        width=width,
        bottom=b_logic,
        color=c_analog,
        label="Analog / RF & BiCMOS",
        zorder=2,
    )
    ax1.bar(
        date_nums,
        b_games,
        width=width,
        bottom=b_logic + b_analog,
        color=c_games,
        label="Games / Graphics",
        zorder=2,
    )
    ax1.bar(
        date_nums,
        b_audio,
        width=width,
        bottom=b_logic + b_analog + b_games,
        color=c_audio,
        label="Audio / DSP Synth",
        zorder=2,
    )
    ax1.bar(
        date_nums,
        b_neural,
        width=width,
        bottom=b_logic + b_analog + b_games + b_audio,
        color=c_neural,
        label="Neural / Accelerators",
        zorder=2,
    )
    ax1.bar(
        date_nums,
        b_cpus,
        width=width,
        bottom=b_logic + b_analog + b_games + b_audio + b_neural,
        color=c_cpus,
        label="CPUs / RISC-V",
        zorder=2,
    )

    # Plot cumulative submissions on twin axis
    ax1_twin = ax1.twinx()
    ax1_twin.plot(
        dates,
        cum_subs,
        color=COLORS["ink"],
        linewidth=1.7,
        linestyle="-",
        marker="o",
        markersize=3.0,
        label="Cumulative Tapeouts",
        zorder=5,
    )
    ax1_twin.set_ylabel(
        "Cumulative Tapeout Submissions",
        color=COLORS["ink"],
        fontsize=6.5,
        fontweight="bold",
    )
    ax1_twin.tick_params(axis="y", labelsize=5.8, colors=COLORS["ink"])
    ax1_twin.set_ylim(0, 5400)

    # Annotate final milestone badge cleanly to the left of the final point
    ax1_twin.scatter(
        [dates[-1]], [cum_subs[-1]], color=COLORS["red"], s=28, zorder=6, marker="D"
    )
    ax1_twin.annotate(
        "TT-SKY-26c\n4,780+ Designs\n(27 Shuttles)",
        xy=(dates[-1], cum_subs[-1]),
        xytext=(-85, -28),
        textcoords="offset points",
        fontsize=5.3,
        fontweight="bold",
        color=COLORS["ink"],
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor="#FFF9E6",
            edgecolor=COLORS["orange"],
            linewidth=0.7,
        ),
        arrowprops=dict(
            arrowstyle="->", color=COLORS["ink"], lw=0.6, shrinkA=2, shrinkB=3
        ),
    )

    # Annotate TT-IHP-25a
    ihp_idx = 12
    ax1.annotate(
        "TT-IHP 25a (548 designs)\n250 GHz BiCMOS Peak",
        xy=(dates[ihp_idx], 550),
        xytext=(-82, -36),
        textcoords="offset points",
        fontsize=5.0,
        fontweight="bold",
        color=COLORS["designspace_ink"],
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="#F3EFFF",
            edgecolor=COLORS["purple"],
            linewidth=0.5,
            alpha=0.9,
        ),
        arrowprops=dict(
            arrowstyle="->", color=COLORS["designspace_ink"], lw=0.55, shrinkB=3
        ),
    )

    # Format Date Axis
    ax1.xaxis.set_major_locator(mdates.YearLocator())
    ax1.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax1.set_xlim(datetime(2022, 5, 1), datetime(2026, 12, 31))
    ax1.set_ylim(0, 620)
    ax1.set_xlabel("Shuttle Round Deadline (2022–2026)", fontsize=6.5)
    ax1.set_ylabel("Projects per Shuttle Round", fontsize=6.5)
    ax1.tick_params(axis="both", labelsize=5.8)
    ax1.grid(True, linestyle="--", linewidth=0.45, color=COLORS["grid"], alpha=0.7)

    ax1.set_title(
        "A  Open Silicon Democratization Wave (Tiny Tapeout)",
        fontsize=7.2,
        fontweight="bold",
        loc="left",
        pad=8,
    )

    # Add compact legend for domain categories
    handles, labels = ax1.get_legend_handles_labels()
    ax1.legend(
        handles[::-1],
        labels[::-1],
        loc="upper left",
        fontsize=4.8,
        frameon=True,
        facecolor="white",
        edgecolor=COLORS["grid"],
        framealpha=0.92,
        ncol=2,
        handlelength=1.0,
        handletextpad=0.4,
        columnspacing=0.6,
    )

    # Submitter affiliation profile note box (clean upper-center-left placement, NO trailing arrow)
    aff_text = (
        "Participant Affiliations:\n"
        "• 34% Undergrad (Stanford, UCSC, TU Wien)\n"
        "• 21% Graduate / PhD Architectures\n"
        "• 16% Open-Source Makers & Demoscene\n"
        "• 15% High School / K-12 (Hack Club)\n"
        "• 9% Academic Labs  • 5% Startups"
    )
    ax1.text(
        0.03,
        0.58,
        aff_text,
        transform=ax1.transAxes,
        fontsize=4.6,
        verticalalignment="top",
        bbox=dict(
            boxstyle="round,pad=0.3",
            facecolor="#F4F8FA",
            edgecolor=COLORS["blue"],
            linewidth=0.55,
            alpha=0.95,
        ),
    )

    # -------------------------------------------------------------
    # Panel B: 45-Year Silicon Fabrication Cost Collapse (1981-2026)
    # -------------------------------------------------------------
    years = [int(r["year"]) for r in cost_data]
    nom_costs = [float(r["participant_nominal_cost_usd"]) for r in cost_data]
    mask_costs = [float(r["dedicated_mask_lot_cost_usd"]) for r in cost_data]

    # Plot Dedicated Mask Cost Wall
    ax2.plot(
        years,
        mask_costs,
        color=COLORS["red"],
        linewidth=1.5,
        linestyle="--",
        marker="s",
        markersize=3.2,
        label="Dedicated Mask Set (Full Reticle)",
        zorder=3,
    )

    # Filter non-zero points for log plot
    mpw_years = [y for y, c in zip(years, nom_costs) if c > 0]
    mpw_costs = [c for c in nom_costs if c > 0]

    # Add zero-cost Google Open MPW as baseline marker
    zero_year = 2020
    zero_cost_display = 1.0  # display at bottom of log scale ($1)

    ax2.plot(
        mpw_years,
        mpw_costs,
        color=COLORS["blue"],
        linewidth=1.8,
        linestyle="-",
        marker="o",
        markersize=3.8,
        label="Multi-Project Fabrication Cost",
        zorder=4,
    )

    # Add zero cost star marker at 2020
    ax2.scatter(
        [zero_year],
        [zero_cost_display],
        color=COLORS["green"],
        s=48,
        marker="*",
        zorder=6,
        label="Google Open MPW ($0 Subsidized)",
    )

    # Historical Step Annotations
    # 1981 Dedicated (above red line)
    ax2.annotate(
        "1981: Pre-MOSIS\nDedicated ($150k)",
        xy=(1981, 150000),
        xytext=(10, 8),
        textcoords="offset points",
        fontsize=4.9,
        color=COLORS["constraints_ink"],
        fontweight="bold",
    )
    # 1982 MOSIS (below blue line)
    ax2.annotate(
        "1982: MOSIS\n($25k MPW)",
        xy=(1982, 25000),
        xytext=(10, -18),
        textcoords="offset points",
        fontsize=4.8,
        color=COLORS["workload_ink"],
    )
    # 2000 TSMC
    ax2.annotate(
        "2000: TSMC\nCyberShuttle ($16k)",
        xy=(2000, 16000),
        xytext=(-38, -18),
        textcoords="offset points",
        fontsize=4.8,
        color=COLORS["workload_ink"],
    )
    # 2016 FinFET Wall
    ax2.annotate(
        "2016: FinFET MPW ($85k)",
        xy=(2016, 85000),
        xytext=(-68, 6),
        textcoords="offset points",
        fontsize=4.8,
        color=COLORS["constraints_ink"],
    )
    # 2020 Google $0
    ax2.annotate(
        "2020: Google Open MPW\n($0 Subsidized)",
        xy=(2020, 1.0),
        xytext=(-125, 12),
        textcoords="offset points",
        fontsize=4.8,
        fontweight="bold",
        color=COLORS["evidence_ink"],
        arrowprops=dict(
            arrowstyle="->", color=COLORS["evidence_ink"], lw=0.55, shrinkB=3
        ),
    )
    # 2026 Tiny Tapeout $50
    ax2.annotate(
        "2026: Tiny Tapeout\n$50 – $100 / Slot\n(3,000× Cost Collapse)",
        xy=(2026, 50),
        xytext=(-78, -32),
        textcoords="offset points",
        fontsize=5.1,
        fontweight="bold",
        color=COLORS["ink"],
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor="#E8F8F0",
            edgecolor=COLORS["green"],
            linewidth=0.65,
        ),
        arrowprops=dict(
            arrowstyle="->", color=COLORS["ink"], lw=0.55, shrinkA=2, shrinkB=3
        ),
    )

    ax2.set_yscale("log")
    ax2.set_xlim(1978, 2029)
    ax2.set_ylim(0.8, 8000000)
    ax2.set_yticks([1, 10, 100, 1000, 10000, 100000, 1000000])
    ax2.set_yticklabels(
        ["$0*", "$10", "$100", "$1k", "$10k", "$100k", "$1M"], fontsize=5.8
    )
    ax2.set_xlabel("Year (1981–2026)", fontsize=6.5)
    ax2.set_ylabel("Fabrication Cost per Participant (USD, Log Scale)", fontsize=6.5)
    ax2.tick_params(axis="both", labelsize=5.8)
    ax2.grid(True, linestyle="--", linewidth=0.45, color=COLORS["grid"], alpha=0.7)

    ax2.set_title(
        "B  The 3,000× Custom Silicon Cost Collapse",
        fontsize=7.2,
        fontweight="bold",
        loc="left",
        pad=8,
    )

    ax2.legend(
        loc="upper right",
        fontsize=5.0,
        frameon=True,
        facecolor="white",
        edgecolor=COLORS["grid"],
        framealpha=0.92,
        handlelength=1.1,
    )

    # Cost collapse callout badge with raw string escaping for dollar signs
    badge_text = (
        "Democratization Drivers:\n"
        "1. Sub-Tile Multiplexing (Tiny Tapeout)\n"
        "2. Open EDA (OpenROAD / Yosys / Wokwi)\n"
        "3. Open PDKs (Sky130, SG13G2, GF180)\n"
        r"→ From \$150k mask sets to \$50 custom silicon"
    )
    ax2.text(
        0.03,
        0.44,
        badge_text,
        transform=ax2.transAxes,
        fontsize=4.8,
        verticalalignment="top",
        bbox=dict(
            boxstyle="round,pad=0.3",
            facecolor="#FFF9E6",
            edgecolor=COLORS["orange"],
            linewidth=0.55,
            alpha=0.95,
        ),
    )

    # 3. Export Formats
    for p in [out_receipt_png, out_book_png]:
        fig.savefig(p, dpi=300, bbox_inches="tight")
        print(f"Saved PNG: {p}")

    for p in [out_receipt_pdf, out_book_pdf]:
        fig.savefig(p, bbox_inches="tight")
        print(f"Saved PDF: {p}")

    for p in [out_receipt_svg, out_book_svg]:
        fig.savefig(p, bbox_inches="tight")
        print(f"Saved SVG: {p}")

    plt.close(fig)
    print("Plot generation completed successfully.")


if __name__ == "__main__":
    main()
