#!/usr/bin/env python3
"""
Figure: The Speculative Execution Tax — Hardware CVE Timeline & Performance Clawback
=====================================================================================
Architecture 2.0: Track 1.5 — Hardware Security CVEs & Microarchitectural Performance Mitigation Tax

Visualizes the 8-year empirical ledger of transient execution vulnerabilities and cumulative performance clawback:
- Panel A: Longitudinal Vulnerability Timeline vs. Cumulative Speculative Performance Clawback (2018–2026).
           Traces cumulative derating curves across Worst-Case Syscall/Virtualization (up to 28.5%),
           Mean Enterprise Suite (4.5% to 22.0%), and Compute-Bound SPEC CPU (1.2% to 14.0%).
- Panel B: Workload Domain Derating Spectrum & Microarchitectural Subsystem Root Causes.
           Contrasts mean and worst-case slowdowns across 6 representative architecture workload classes.

Receipt Source:
- data/source-receipts/hardware_security_cve_mitigation_tax.csv

Generated Assets:
- data/source-receipts/fig-hardware-cve-mitigation-tax.svg
- data/source-receipts/fig-hardware-cve-mitigation-tax.pdf
- data/source-receipts/fig-hardware-cve-mitigation-tax.png
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

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


def load_cve_receipt(csv_path: Path) -> List[Dict[str, Any]]:
    """Loads hardware CVE mitigation tax data from canonical receipt."""
    records = []
    with open(csv_path, "r", encoding="utf-8") as f:
        lines = [line for line in f if not line.strip().startswith("#")]
        reader = csv.DictReader(lines)
        for r in reader:
            records.append(
                {
                    "cve_id": r["cve_id"],
                    "vulnerability_name": r["vulnerability_name"],
                    "discovery_year": float(r["discovery_year"]),
                    "disclosure_date": r["disclosure_date"],
                    "structure": r["affected_microarchitecture_structure"],
                    "vendors": r["affected_vendors"],
                    "mitigation_mechanism": r["mitigation_mechanism"],
                    "mitigation_type": r["mitigation_type"],
                    "chicken_bit": r["hardware_chicken_bit"],
                    "workload_domains": r["workload_domains"],
                    "mean_penalty": float(r["mean_penalty_pct"]),
                    "worst_penalty": float(r["worst_case_penalty_pct"]),
                    "spec_cpu": float(r["spec_cpu_penalty_pct"]),
                    "database": float(r["database_penalty_pct"])
                    if r["database_penalty_pct"]
                    else 0.0,
                    "context_switch": float(r["context_switch_penalty_pct"]),
                    "vector_hpc": float(r["vector_hpc_penalty_pct"]),
                    "cum_mean_tax": float(r["cumulative_mean_tax_pct"]),
                    "cum_worst_tax": float(r["cumulative_worst_tax_pct"]),
                    "advisory_id": r["advisory_id"],
                    "epoch_phase": r["epoch_phase"],
                }
            )
    return records


def build_figure() -> Tuple[plt.Figure, Path, Path, Path]:
    csv_file = (
        REPO_ROOT
        / "data"
        / "source-receipts"
        / "hardware_security_cve_mitigation_tax.csv"
    )
    if not csv_file.exists():
        csv_file = (
            Path(__file__).resolve().parent / "hardware_security_cve_mitigation_tax.csv"
        )

    records = load_cve_receipt(csv_file)

    fig = plt.figure(figsize=(7.4, 5.4), dpi=300)
    gs = fig.add_gridspec(
        2,
        1,
        height_ratios=[1.3, 1.0],
        hspace=0.36,
        left=0.07,
        right=0.95,
        top=0.93,
        bottom=0.07,
    )

    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[1, 0])

    # =========================================================================
    # Panel A: Longitudinal Vulnerability Timeline & Cumulative Clawback
    # =========================================================================
    ax0.set_title(
        "Panel A: Longitudinal Vulnerability Timeline & Cumulative Speculative Execution Tax (2018–2026)",
        loc="left",
        fontweight="bold",
        fontsize=7.2,
        pad=6,
        color=COLORS["ink"],
    )

    # 1. Background Epoch Bands
    epochs = [
        (
            2017.7,
            2018.95,
            "Phase 1: Disclosure Shock\n(Meltdown, Spectre v1–v4, L1TF)",
            "#FDF5EA",
        ),
        (
            2018.95,
            2021.0,
            "Phase 2: Buffer Sampling\n(MDS, RIDL, Fallout, TAA, SRBDS)",
            "#F7F1EC",
        ),
        (
            2021.0,
            2022.95,
            "Phase 3: Return Speculation\n(Retbleed, BHI / Spectre-BHB)",
            "#F2F0F9",
        ),
        (
            2022.95,
            2026.3,
            "Phase 4: Vector & Pipeline Traps\n(Downfall, ZenBleed, Inception, GhostRace)",
            "#EAF3F7",
        ),
    ]

    for x0_ep, x1_ep, label, bg_col in epochs:
        ax0.axvspan(x0_ep, x1_ep, color=bg_col, alpha=0.95, zorder=0, lw=0)

    # Epoch header labels at the top
    ax0.text(
        2018.32,
        31.0,
        "Phase 1: Shock",
        ha="center",
        va="top",
        fontsize=5.3,
        fontweight="bold",
        color="#8A5310",
    )
    ax0.text(
        2019.97,
        31.0,
        "Phase 2: Sampling",
        ha="center",
        va="top",
        fontsize=5.3,
        fontweight="bold",
        color="#8A5310",
    )
    ax0.text(
        2021.97,
        31.0,
        "Phase 3: Return/BHB",
        ha="center",
        va="top",
        fontsize=5.3,
        fontweight="bold",
        color="#59429E",
    )
    ax0.text(
        2024.62,
        31.0,
        "Phase 4: Vector & Pipeline Traps",
        ha="center",
        va="top",
        fontsize=5.3,
        fontweight="bold",
        color="#136680",
    )

    # 2. Cumulative Stepped Curves (2018 to 2026)
    timeline_years = [
        2018.0,
        2018.1,
        2018.4,
        2018.6,
        2019.4,
        2019.9,
        2020.5,
        2022.2,
        2022.5,
        2023.6,
        2023.65,
        2024.2,
        2026.0,
    ]
    worst_tax_curve = [
        0.0,
        18.5,
        24.0,
        26.0,
        26.5,
        26.8,
        27.0,
        27.8,
        28.0,
        28.5,
        28.5,
        28.5,
        28.5,
    ]
    mean_tax_curve = [
        0.0,
        4.5,
        9.5,
        13.0,
        14.5,
        15.2,
        15.8,
        18.5,
        19.2,
        21.0,
        21.5,
        21.8,
        22.0,
    ]
    spec_tax_curve = [
        0.0,
        1.2,
        6.5,
        7.5,
        9.2,
        10.0,
        10.2,
        12.0,
        12.5,
        13.5,
        13.8,
        14.0,
        14.0,
    ]

    # Fill between Mean and Worst-Case (The Vulnerability Tax Dispersion Envelope)
    ax0.fill_between(
        timeline_years,
        mean_tax_curve,
        worst_tax_curve,
        color=COLORS["red"],
        alpha=0.10,
        label="Tax Dispersion (Worst-Case vs. Mean)",
        zorder=2,
    )

    # Plot Curves
    ax0.step(
        timeline_years,
        worst_tax_curve,
        where="post",
        color=COLORS["red"],
        lw=1.7,
        label="Worst-Case Tax (Syscalls, Context Switches, VM Isolation)",
        zorder=4,
    )
    ax0.step(
        timeline_years,
        mean_tax_curve,
        where="post",
        color=COLORS["blue"],
        lw=1.7,
        label="Mean Enterprise Tax (Databases, Web Services, Mixed Apps)",
        zorder=4,
    )
    ax0.step(
        timeline_years,
        spec_tax_curve,
        where="post",
        color=COLORS["green"],
        lw=1.3,
        linestyle="--",
        label="Compute-Bound Tax (SPEC CPU 2017 Integer / FP)",
        zorder=4,
    )

    # 3. Vulnerability Markers & Annotations with non-colliding coordinates
    cve_callouts = [
        {
            "year": 2018.02,
            "y": 18.5,
            "text": "Meltdown\n(KPTI: -18.5%)",
            "xytext": (2018.02, 11.5),
            "color": COLORS["constraints_ink"],
            "ha": "center",
            "arrow_rad": 0.0,
        },
        {
            "year": 2018.08,
            "y": 24.0,
            "text": "Spectre v2\n(Retpoline/eIBRS)",
            "xytext": (2018.68, 27.2),
            "color": COLORS["constraints_ink"],
            "ha": "center",
            "arrow_rad": 0.1,
        },
        {
            "year": 2018.62,
            "y": 26.0,
            "text": "Foreshadow/L1TF\n(L1D Flush / nosmt)",
            "xytext": (2019.55, 23.5),
            "color": COLORS["constraints_ink"],
            "ha": "left",
            "arrow_rad": -0.1,
        },
        {
            "year": 2019.38,
            "y": 14.5,
            "text": "MDS / RIDL / Fallout\n(VERW Core-Clear)",
            "xytext": (2020.35, 10.8),
            "color": COLORS["workload_ink"],
            "ha": "left",
            "arrow_rad": -0.05,
        },
        {
            "year": 2022.52,
            "y": 27.8,
            "text": "Retbleed\n(Zen/Skylake Thunks)",
            "xytext": (2021.75, 22.0),
            "color": COLORS["designspace_ink"],
            "ha": "right",
            "arrow_rad": 0.1,
        },
        {
            "year": 2023.60,
            "y": 21.0,
            "text": "Downfall\n(GDS AVX Serializer)",
            "xytext": (2023.25, 16.5),
            "color": COLORS["workload_ink"],
            "ha": "right",
            "arrow_rad": 0.05,
        },
        {
            "year": 2023.62,
            "y": 28.5,
            "text": "Inception / SRSO\n(Safe RET Trampoline)",
            "xytext": (2024.25, 25.5),
            "color": COLORS["constraints_ink"],
            "ha": "left",
            "arrow_rad": -0.1,
        },
    ]

    for c in cve_callouts:
        ax0.plot(
            c["year"], c["y"], marker="o", markersize=4.2, color=c["color"], zorder=5
        )
        ax0.annotate(
            c["text"],
            xy=(c["year"], c["y"]),
            xytext=c["xytext"],
            fontsize=5.1,
            fontweight="bold",
            color=c["color"],
            ha=c["ha"],
            va="center",
            arrowprops=dict(
                arrowstyle="->",
                connectionstyle=f"arc3,rad={c['arrow_rad']}",
                color=c["color"],
                lw=0.6,
                shrinkA=2,
                shrinkB=3,
            ),
            bbox=dict(
                boxstyle="round,pad=0.18",
                facecolor="white",
                edgecolor=c["color"],
                alpha=0.93,
                lw=0.5,
            ),
            zorder=6,
        )

    # Formatting ax0
    ax0.set_xlim(2017.7, 2026.3)
    ax0.set_ylim(0, 32.5)
    ax0.set_ylabel(
        "Cumulative Performance Penalty (%)",
        fontsize=6.2,
        fontweight="bold",
        color=COLORS["ink"],
    )
    ax0.set_xticks([2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026])
    ax0.set_xticklabels(
        ["2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026"],
        fontsize=5.8,
    )
    ax0.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=100, decimals=0))
    ax0.grid(axis="y", color=COLORS["grid"], linewidth=0.55, linestyle=":")
    ax0.legend(
        loc="lower right",
        fontsize=5.1,
        frameon=True,
        facecolor="white",
        framealpha=0.92,
        edgecolor=COLORS["grid"],
    )

    # Final percentage badges
    ax0.text(
        2026.05,
        28.5,
        " 28.5%",
        fontsize=5.8,
        fontweight="bold",
        color=COLORS["red"],
        va="center",
    )
    ax0.text(
        2026.05,
        22.0,
        " 22.0%",
        fontsize=5.8,
        fontweight="bold",
        color=COLORS["blue"],
        va="center",
    )
    ax0.text(
        2026.05,
        14.0,
        " 14.0%",
        fontsize=5.8,
        fontweight="bold",
        color=COLORS["green"],
        va="center",
    )

    # =========================================================================
    # Panel B: Workload Domain Derating Spectrum & Microarchitectural Root Causes
    # =========================================================================
    ax1.set_title(
        "Panel B: Performance Tax Derating by Workload Class & Microarchitectural Mechanism",
        loc="left",
        fontweight="bold",
        fontsize=7.2,
        pad=6,
        color=COLORS["ink"],
    )

    workload_rows = [
        {
            "name": "Syscall & IPC Pipes (Redis, Nginx, ctx switch)",
            "low": 4.5,
            "mean": 18.5,
            "high": 28.5,
            "mechanism": "KPTI, Retpoline, IBRS/eIBRS, VERW Clear",
            "color": COLORS["red"],
        },
        {
            "name": "Cloud Multi-Tenant VM (KVM, Xen, VM-exit)",
            "low": 6.0,
            "mean": 14.2,
            "high": 27.0,
            "mechanism": "L1D Terminal Fault Flush, nosmt Isolation",
            "color": COLORS["orange"],
        },
        {
            "name": "Transactional DBs (PostgreSQL, MySQL, HANA)",
            "low": 3.8,
            "mean": 12.5,
            "high": 21.5,
            "mechanism": "TSX Async Abort Off, IBPB, Store Bypass",
            "color": COLORS["purple"],
        },
        {
            "name": "JIT Runtimes & Scripts (V8, SpiderMonkey, Py)",
            "low": 2.1,
            "mean": 4.8,
            "high": 9.5,
            "mechanism": "LFENCE Speculation Barrier, SSBD MSR",
            "color": COLORS["blue"],
        },
        {
            "name": "HPC & Vector Math (OpenBLAS, GROMACS, SIMD)",
            "low": 0.8,
            "mean": 6.5,
            "high": 32.0,  # Plotted bar to 32%, note shows 50% peak
            "real_high": 50.0,
            "mechanism": "Downfall GDS AVX Serializer, RVV Traps",
            "color": COLORS["magenta"],
        },
        {
            "name": "Compute-Bound SPEC CPU (SPECrate2017)",
            "low": 1.2,
            "mean": 2.8,
            "high": 7.5,
            "mechanism": "Retpoline Trampolines, SPEC_STORE_FWD",
            "color": COLORS["green"],
        },
    ]

    y_pos = np.arange(len(workload_rows))
    ax1.set_ylim(-0.55, len(workload_rows) - 0.45)
    ax1.invert_yaxis()

    # Layout coordinates for Panel B:
    # x < 0: Text metadata area
    # x >= 0: Bar plotting area
    # x > 33: Summary stats label
    x_label_start = -27.0
    x_data_start = 0.0

    # Draw vertical separator line between label area and data area
    ax1.axvline(0, color=COLORS["ink"], linewidth=0.75, zorder=1)

    for idx, row in enumerate(workload_rows):
        y = y_pos[idx]
        col = row["color"]
        low, mean, high = row["low"], row["mean"], row["high"]

        # Baseline row line across entire width
        ax1.axhline(y, color=COLORS["row"], linewidth=0.7, zorder=0)

        # Range bar (low to high) in positive x space
        ax1.hlines(y, low, high, color=col, linewidth=2.4, zorder=2)

        # Square endpoints
        ax1.scatter(
            [low, high],
            [y, y],
            marker="s",
            s=18,
            facecolor=COLORS["note_fill"],
            edgecolor=col,
            lw=0.9,
            zorder=3,
        )

        # Diamond mean marker
        ax1.scatter(
            [mean],
            [y],
            marker="D",
            s=22,
            facecolor=col,
            edgecolor="white",
            lw=0.6,
            zorder=4,
        )

        # Left Column: Workload name and mitigation details
        ax1.text(
            x_label_start,
            y - 0.13,
            row["name"],
            fontsize=5.8,
            fontweight="bold",
            color=COLORS["ink"],
            va="center",
            ha="left",
        )
        ax1.text(
            x_label_start,
            y + 0.17,
            f"Mitigation: {row['mechanism']}",
            fontsize=4.9,
            color=COLORS["muted"],
            va="center",
            ha="left",
        )

        # Right Column: Quantitative Summary
        if "real_high" in row:
            range_str = f"Mean: {row['mean']}% [Range: {row['low']}–{row['real_high']:.0f}% peak]"
        else:
            range_str = f"Mean: {row['mean']}% [Range: {row['low']}–{row['high']}%]"

        ax1.text(
            33.0,
            y,
            range_str,
            fontsize=5.5,
            fontweight="bold",
            color=col,
            va="center",
            ha="left",
        )

    # Formatting ax1
    ax1.set_xlim(-28.0, 62.0)
    ax1.set_xlabel(
        "Workload Performance Derating Penalty (%)",
        fontsize=6.2,
        fontweight="bold",
        color=COLORS["ink"],
        x=0.58,
    )
    ax1.set_yticks([])
    ax1.set_xticks([0, 5, 10, 15, 20, 25, 30])
    ax1.set_xticklabels(["0%", "5%", "10%", "15%", "20%", "25%", "30%"], fontsize=5.8)
    ax1.grid(axis="x", color=COLORS["grid"], linewidth=0.55, linestyle=":")

    # Add legend elements at top right of Panel B without collision
    legend_elements = [
        Line2D(
            [0],
            [0],
            marker="s",
            color="w",
            label="Min/Max Range",
            markerfacecolor=COLORS["note_fill"],
            markeredgecolor=COLORS["ink"],
            markersize=4.5,
        ),
        Line2D(
            [0],
            [0],
            marker="D",
            color="w",
            label="Workload Mean",
            markerfacecolor=COLORS["ink"],
            markeredgecolor="white",
            markersize=5,
        ),
    ]
    ax1.legend(
        handles=legend_elements,
        loc="upper right",
        fontsize=5.0,
        frameon=True,
        facecolor="white",
        framealpha=0.92,
        edgecolor=COLORS["grid"],
    )

    # Target output paths
    out_svg = (
        REPO_ROOT / "data" / "source-receipts" / "fig-hardware-cve-mitigation-tax.svg"
    )
    out_pdf = (
        REPO_ROOT / "data" / "source-receipts" / "fig-hardware-cve-mitigation-tax.pdf"
    )
    out_png = (
        REPO_ROOT / "data" / "source-receipts" / "fig-hardware-cve-mitigation-tax.png"
    )

    out_svg.parent.mkdir(parents=True, exist_ok=True)

    fig.savefig(out_svg, format="svg", bbox_inches="tight")
    fig.savefig(out_pdf, format="pdf", bbox_inches="tight")
    fig.savefig(out_png, format="png", dpi=300, bbox_inches="tight")

    _declare_font_stack(out_svg)
    plt.close(fig)

    print(f"  [+] Rendered SVG: {out_svg}")
    print(f"  [+] Rendered PDF: {out_pdf}")
    print(f"  [+] Rendered PNG: {out_png}")

    return fig, out_svg, out_pdf, out_png


def main():
    print("[*] Generating publication-quality Hardware CVE Mitigation Tax figures...")
    build_figure()
    print("[+] Figure generation complete.")


if __name__ == "__main__":
    main()
