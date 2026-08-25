import sys
from pathlib import Path

STUDY_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
DATA_DIR = STUDY_DIR
OUTPUT_DIR = STUDY_DIR

#!/usr/bin/env python3
"""
Publication Figure: Testbench Mutation Vacuity & LLM-as-a-Judge Calibration
===========================================================================
Architecture 2.0: Track 2.3 & Track 2.5

Generates publication-quality 2-panel figure:
- Panel A: The Vacuity Gap (High Line/Branch Coverage masking low Mutation Kill Rates).
- Panel B: LLM Judge Calibration & In-Family Confirmation Bias (Reliability Diagram).

Input Receipt:
- data/source-receipts/testbench_vacuity_and_judge_calibration.csv

Output Assets:
- data/source-receipts/fig_testbench_vacuity_and_judge_bias.png
- data/source-receipts/fig_testbench_vacuity_and_judge_bias.pdf
- data/source-receipts/fig_testbench_vacuity_and_judge_bias.svg
"""

import csv
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

# Ensure book._python.plots is accessible
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


def load_receipt_data(csv_path: Path) -> List[Dict[str, Any]]:
    """Load evaluation records from CSV receipt, ignoring comments."""
    records = []
    with open(csv_path, "r", encoding="utf-8") as f:
        lines = [line for line in f if not line.strip().startswith("#")]
        reader = csv.DictReader(lines)
        for r in reader:
            records.append(
                {
                    "benchmark_suite": r["benchmark_suite"],
                    "testbench_id": r["testbench_id"],
                    "module_name": r["module_name"],
                    "hardware_domain": r["hardware_domain"],
                    "generator_model": r["generator_model"],
                    "generator_family": r["generator_family"],
                    "judge_model": r["judge_model"],
                    "judge_family": r["judge_family"],
                    "is_same_model_family": int(r["is_same_model_family"]),
                    "line_coverage_pct": float(r["line_coverage_pct"]),
                    "branch_coverage_pct": float(r["branch_coverage_pct"]),
                    "toggle_coverage_pct": float(r["toggle_coverage_pct"]),
                    "total_mutants_injected": int(r["total_mutants_injected"]),
                    "mutants_killed": int(r["mutants_killed"]),
                    "mutants_escaped": int(r["mutants_escaped"]),
                    "mutation_kill_rate_pct": float(r["mutation_kill_rate_pct"]),
                    "vacuity_gap_pct": float(r["vacuity_gap_pct"]),
                    "is_design_defective": int(r["is_design_defective"]),
                    "judge_confidence_score": float(r["judge_confidence_score"]),
                    "judge_verdict": r["judge_verdict"],
                    "judge_decision_category": r["judge_decision_category"],
                    "judge_false_acceptance": int(r["judge_false_acceptance"]),
                    "judge_false_acceptance_rate_pct": float(
                        r["judge_false_acceptance_rate_pct"]
                    ),
                    "expected_calibration_error": float(
                        r["expected_calibration_error"]
                    ),
                    "family_overlap_bias_score": float(r["family_overlap_bias_score"]),
                }
            )
    return records


def compute_reliability_curve(
    records: List[Dict[str, Any]], bin_edges: List[float]
) -> Tuple[np.ndarray, np.ndarray, float]:
    """Calculate empirical confidence bins, empirical correctness rate, and ECE over specified bin edges."""
    num_bins = len(bin_edges) - 1
    bins = [[] for _ in range(num_bins)]

    for r in records:
        conf = r["judge_confidence_score"]
        for i in range(num_bins):
            if (
                i == num_bins - 1 and conf >= bin_edges[i] and conf <= bin_edges[i + 1]
            ) or (conf >= bin_edges[i] and conf < bin_edges[i + 1]):
                bins[i].append(r)
                break

    conf_list = []
    acc_list = []
    ece = 0.0
    total_n = len(records)

    for i in range(num_bins):
        b = bins[i]
        if not b:
            continue

        avg_conf = sum(r["judge_confidence_score"] for r in b) / len(b)
        correct_count = sum(1 for r in b if r["is_design_defective"] == 0)
        emp_acc = correct_count / len(b)
        gap = abs(emp_acc - avg_conf)
        ece += (len(b) / total_n) * gap
        conf_list.append(avg_conf)
        acc_list.append(emp_acc)

    return np.array(conf_list), np.array(acc_list), ece


def main():
    csv_file = (
        REPO_ROOT
        / "data"
        / "source-receipts"
        / "testbench_vacuity_and_judge_calibration.csv"
    )
    if not csv_file.exists():
        csv_file = (
            Path(__file__).resolve().parent
            / "testbench_vacuity_and_judge_calibration.csv"
        )

    records = load_receipt_data(csv_file)

    # Output paths
    receipts_dir = REPO_ROOT / "data" / "source-receipts"
    ch07_img_dir = (
        REPO_ROOT / "book" / "contents" / "chapters" / "07-feedback" / "images"
    )
    ch07_img_dir.mkdir(parents=True, exist_ok=True)

    out_paths = [
        receipts_dir / "fig_testbench_vacuity_and_judge_bias.svg",
        receipts_dir / "fig_testbench_vacuity_and_judge_bias.pdf",
        receipts_dir / "fig_testbench_vacuity_and_judge_bias.png",
        ch07_img_dir / "fig-testbench-vacuity-and-judge-bias.svg",
        ch07_img_dir / "fig-testbench-vacuity-and-judge-bias.pdf",
        ch07_img_dir / "fig-testbench-vacuity-and-judge-bias.png",
    ]

    # Create figure with 2 panels
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(11.8, 4.6), gridspec_kw={"width_ratios": [1.12, 1.18]}
    )
    fig.subplots_adjust(wspace=0.34, left=0.07, right=0.96, top=0.88, bottom=0.16)

    # =========================================================================
    # Panel A: The Vacuity Gap
    # =========================================================================
    categories = [
        "VerilogEval\n(NVlabs)",
        "RTLLM\n(HKUST)",
        "VeriGen\n(NYU)",
        "Frontier LLM\nAverage",
        "CV32E40P\n(UVM Base)",
        "Formal SVA\n(Signoff)",
    ]

    # Extract averages from dataset
    ve_recs = [r for r in records if r["benchmark_suite"] == "VerilogEval"]
    rt_recs = [r for r in records if r["benchmark_suite"] == "RTLLM"]
    vg_recs = [r for r in records if r["benchmark_suite"] == "VeriGen"]

    line_vals = [
        np.mean([r["line_coverage_pct"] for r in ve_recs]),
        np.mean([r["line_coverage_pct"] for r in rt_recs]),
        np.mean([r["line_coverage_pct"] for r in vg_recs]),
        np.mean([r["line_coverage_pct"] for r in records]),
        98.6,  # OpenHW CV32E40P UVM empirical baseline
        100.0,  # Formal SVA Signoff
    ]

    branch_vals = [
        np.mean([r["branch_coverage_pct"] for r in ve_recs]),
        np.mean([r["branch_coverage_pct"] for r in rt_recs]),
        np.mean([r["branch_coverage_pct"] for r in vg_recs]),
        np.mean([r["branch_coverage_pct"] for r in records]),
        86.4,  # OpenHW CV32E40P UVM branch coverage
        100.0,  # Formal SVA Signoff
    ]

    kill_vals = [
        np.mean([r["mutation_kill_rate_pct"] for r in ve_recs]),
        np.mean([r["mutation_kill_rate_pct"] for r in rt_recs]),
        np.mean([r["mutation_kill_rate_pct"] for r in vg_recs]),
        np.mean([r["mutation_kill_rate_pct"] for r in records]),
        58.6,  # OpenHW CV32E40P UVM kill rate
        100.0,  # Formal SVA Signoff
    ]

    x = np.arange(len(categories))
    bar_w = 0.26

    rects1 = ax1.bar(
        x - bar_w,
        line_vals,
        width=bar_w,
        label="Line Coverage (%)",
        color=COLORS["blue"],
        edgecolor="none",
        zorder=3,
    )
    rects2 = ax1.bar(
        x,
        branch_vals,
        width=bar_w,
        label="Branch Coverage (%)",
        color=COLORS["purple"],
        edgecolor="none",
        zorder=3,
    )
    rects3 = ax1.bar(
        x + bar_w,
        kill_vals,
        width=bar_w,
        label="Mutation Kill Rate (%)",
        color=COLORS["red"],
        edgecolor="none",
        zorder=3,
    )

    # Highlight Vacuity Gap on Frontier LLM Average
    gap_x = x[3]
    top_y = line_vals[3]
    bot_y = kill_vals[3]
    ax1.annotate(
        "",
        xy=(gap_x + bar_w / 2, bot_y + 2),
        xytext=(gap_x + bar_w / 2, top_y - 2),
        arrowprops=dict(arrowstyle="<->", color=COLORS["constraints_ink"], lw=2.0),
        zorder=4,
    )
    ax1.text(
        gap_x + 0.38,
        (top_y + bot_y) / 2.0,
        f"Vacuity Gap\nΔ = {top_y - bot_y:.1f}%",
        color=COLORS["constraints_ink"],
        fontsize=8.5,
        fontweight="bold",
        va="center",
        ha="left",
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor="#FDE8E8",
            edgecolor=COLORS["red"],
            lw=0.8,
        ),
        zorder=5,
    )

    # Formatting Panel A
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories, fontsize=8.5)
    ax1.set_ylim(0, 122)
    ax1.set_ylabel(
        "Verification Coverage / Detection (%)",
        fontsize=9.5,
        fontweight="bold",
        color=COLORS["ink"],
    )
    ax1.set_title(
        "A. The Vacuity Gap: Dynamic Coverage vs. Fault Detection",
        fontsize=10.5,
        fontweight="bold",
        pad=10,
        loc="left",
        color=COLORS["ink"],
    )
    ax1.yaxis.set_major_locator(ticker.MultipleLocator(20))
    ax1.grid(True, axis="y", linestyle="--", alpha=0.6, color=COLORS["grid"], zorder=0)
    ax1.legend(
        loc="upper left",
        frameon=True,
        fontsize=8.0,
        facecolor="white",
        edgecolor=COLORS["grid"],
    )

    # Baseline signoff dashed guide
    ax1.axhline(
        100, color=COLORS["green"], linestyle=":", linewidth=1.4, alpha=0.9, zorder=2
    )
    ax1.text(
        5.0,
        103.5,
        "Formal Proof Signoff (100% Bound)",
        color=COLORS["evidence_ink"],
        fontsize=7.8,
        fontweight="bold",
        ha="center",
        va="bottom",
    )

    # =========================================================================
    # Panel B: LLM Judge Calibration & Confirmation Bias Curve
    # =========================================================================
    # Partition records: Cross-Family vs In-Family
    cross_recs = [r for r in records if r["is_same_model_family"] == 0]
    in_fam_recs = [r for r in records if r["is_same_model_family"] == 1]

    bin_edges = [0.10, 0.45, 0.65, 0.80, 0.90, 1.00]
    conf_cross, acc_cross, ece_cross = compute_reliability_curve(cross_recs, bin_edges)
    conf_in, acc_in, ece_in = compute_reliability_curve(in_fam_recs, bin_edges)

    # Calibration diagonal
    ax2.plot(
        [0.20, 1.0],
        [0.20, 1.0],
        linestyle="--",
        color=COLORS["muted"],
        linewidth=1.5,
        label="Perfect Calibration ($y = x$)",
        zorder=2,
    )

    # Plot Cross-family calibration
    ax2.plot(
        conf_cross,
        acc_cross,
        marker="o",
        markersize=6.5,
        linewidth=2.2,
        color=COLORS["blue"],
        label=f"Cross-Family Judge (ECE = {ece_cross:.3f})",
        zorder=4,
    )

    # Plot In-family calibration (Confirmation Bias)
    ax2.plot(
        conf_in,
        acc_in,
        marker="s",
        markersize=6.5,
        linewidth=2.2,
        color=COLORS["red"],
        label=f"In-Family Judge / Sycophancy (ECE = {ece_in:.3f})",
        zorder=4,
    )

    # Fill bias gap between curves in overconfident region
    common_x = np.linspace(
        max(conf_cross[0], conf_in[0]), min(conf_cross[-1], conf_in[-1]), 50
    )
    interp_cross = np.interp(common_x, conf_cross, acc_cross)
    interp_in = np.interp(common_x, conf_in, acc_in)

    ax2.fill_between(
        common_x,
        interp_in,
        interp_cross,
        where=(interp_cross >= interp_in),
        color=COLORS["red"],
        alpha=0.15,
        label="In-Family Sycophancy Penalty",
        zorder=1,
    )

    # Compute actual FARs for annotation
    defective_cross = [r for r in cross_recs if r["is_design_defective"] == 1]
    defective_in = [r for r in in_fam_recs if r["is_design_defective"] == 1]
    far_cross = (
        (
            sum(r["judge_false_acceptance"] for r in defective_cross)
            / len(defective_cross)
        )
        * 100.0
        if defective_cross
        else 0.0
    )
    far_in = (
        (sum(r["judge_false_acceptance"] for r in defective_in) / len(defective_in))
        * 100.0
        if defective_in
        else 0.0
    )
    bias_mult = far_in / far_cross if far_cross > 0 else 1.0

    # Annotation of Confirmation Bias
    target_x = 0.76
    y_in = float(np.interp(target_x, conf_in, acc_in))
    y_cross = float(np.interp(target_x, conf_cross, acc_cross))

    ax2.annotate(
        f"In-Family Sycophancy\nFAR: {far_in:.1f}% vs {far_cross:.1f}%\n(+{bias_mult:.2f}× Defect Escape)",
        xy=(target_x, (y_in + y_cross) / 2.0),
        xytext=(0.52, 0.26),
        arrowprops=dict(arrowstyle="->", color=COLORS["constraints_ink"], lw=1.5),
        fontsize=8.5,
        fontweight="bold",
        color=COLORS["constraints_ink"],
        bbox=dict(
            boxstyle="round,pad=0.3",
            facecolor="#FDE8E8",
            edgecolor=COLORS["red"],
            lw=0.8,
        ),
        zorder=5,
    )

    # Formatting Panel B
    ax2.set_xlim(0.20, 1.00)
    ax2.set_ylim(-0.02, 1.05)
    ax2.set_xlabel(
        "Judge Confidence Score $\\hat{p}$",
        fontsize=9.5,
        fontweight="bold",
        color=COLORS["ink"],
    )
    ax2.set_ylabel(
        "Empirical Hardware Correctness",
        fontsize=9.5,
        fontweight="bold",
        color=COLORS["ink"],
    )
    ax2.set_title(
        "B. LLM Judge Calibration & Confirmation Bias vs. Formal Proofs",
        fontsize=10.5,
        fontweight="bold",
        pad=10,
        loc="left",
        color=COLORS["ink"],
    )
    ax2.xaxis.set_major_locator(ticker.MultipleLocator(0.1))
    ax2.yaxis.set_major_locator(ticker.MultipleLocator(0.2))
    ax2.grid(True, linestyle="--", alpha=0.6, color=COLORS["grid"], zorder=0)
    ax2.legend(
        loc="upper left",
        frameon=True,
        fontsize=8.0,
        facecolor="white",
        edgecolor=COLORS["grid"],
    )

    # Save to all target paths
    for p in out_paths:
        fig.savefig(p, dpi=300, bbox_inches="tight")
        if p.suffix == ".svg":
            _declare_font_stack(p)
        print(f"  ✓ Saved {p}")

    plt.close(fig)
    print("\n✅ All publication-quality figures successfully rendered and saved.")


if __name__ == "__main__":
    main()
