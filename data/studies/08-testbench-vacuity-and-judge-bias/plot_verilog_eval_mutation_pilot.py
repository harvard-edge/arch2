#!/usr/bin/env python3
"""Plot the executed VerilogEval mutation-testing pilot candidate."""

from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


STUDY_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style  # noqa: E402


apply_style()

INPUT_CSV = STUDY_DIR / "verilog_eval_mutation_pilot.csv"
OUTPUT_BASE = STUDY_DIR / "fig_verilog_eval_mutation_pilot"

CLASS_LABELS = {
    "dynamically_killed": "Dynamically killed",
    "dynamically_killed_formal_conflict": "Dynamic witness; formal conflict",
    "survived_unresolved": "Survived; equivalence unresolved",
    "survived_harness_timeout": "Survived at harness timeout",
    "no_dynamic_witness_formal_equivalent": "No witness; formally equivalent",
    "simulation_timeout": "Simulation timeout",
    "simulation_inconclusive": "Simulation inconclusive",
    "compile_killed": "Did not compile",
}

CLASS_COLORS = {
    "dynamically_killed": COLORS["evidence"],
    "dynamically_killed_formal_conflict": COLORS["decision"],
    "survived_unresolved": COLORS["constraints"],
    "survived_harness_timeout": COLORS["constraints"],
    "no_dynamic_witness_formal_equivalent": COLORS["designspace"],
    "simulation_timeout": COLORS["methods"],
    "simulation_inconclusive": COLORS["muted"],
    "compile_killed": COLORS["muted"],
}

OPERATOR_LABELS = {
    "addition_to_subtraction": "+  →  −",
    "subtraction_to_addition": "−  →  +",
    "bitwise_and_to_or": "bitwise &  →  |",
    "bitwise_or_to_and": "bitwise |  →  &",
    "bitwise_xor_to_and": "bitwise ^  →  &",
    "logical_and_to_or": "logical &&  →  ||",
    "logical_or_to_and": "logical ||  →  &&",
    "equality_to_inequality": "==  →  !=",
    "inequality_to_equality": "!=  →  ==",
    "one_bit_zero_to_one": "1'b0  →  1'b1",
    "one_bit_one_to_zero": "1'b1  →  1'b0",
    "unsized_zero_to_one": "'0  →  '1",
    "unsized_one_to_zero": "'1  →  '0",
    "left_shift_to_right": "<<  →  >>",
    "right_shift_to_left": ">>  →  <<",
}


def declare_font_stack(svg_path: Path) -> None:
    text = svg_path.read_text(encoding="utf-8")
    if '<style type="text/css">' not in text:
        text = text.replace(
            "<defs>",
            '<defs>\n  <style type="text/css">*{font-family: Arial, Helvetica, sans-serif;}</style>',
            1,
        )
    text = "\n".join(line.rstrip() for line in text.splitlines()) + "\n"
    svg_path.write_text(text, encoding="utf-8")


def read_records() -> list[dict[str, str]]:
    with INPUT_CSV.open(encoding="utf-8") as handle:
        return list(csv.DictReader(l for l in handle if not l.startswith("#")))


def main() -> int:
    records = read_records()
    if not records:
        raise SystemExit(f"No mutation records found in {INPUT_CSV}")

    outcomes = Counter(record["classification"] for record in records)
    ordered_outcomes = [
        classification
        for classification in (
            "dynamically_killed",
            "dynamically_killed_formal_conflict",
            "survived_unresolved",
            "survived_harness_timeout",
            "no_dynamic_witness_formal_equivalent",
            "simulation_timeout",
            "simulation_inconclusive",
            "compile_killed",
        )
        if outcomes[classification]
    ]

    by_operator: dict[str, list[dict[str, str]]] = defaultdict(list)
    for record in records:
        by_operator[record["mutation_operator"]].append(record)

    operator_rows: list[tuple[str, float, int, int]] = []
    for operator, operator_records in by_operator.items():
        witnesses = sum(
            bool(record["mismatch_count"]) and int(record["mismatch_count"]) > 0
            for record in operator_records
        )
        denominator = len(operator_records)
        operator_rows.append(
            (operator, 100.0 * witnesses / denominator, denominator, witnesses)
        )
    operator_rows.sort(key=lambda row: (row[1], row[2], row[0]))

    overall_witnesses = sum(
        bool(record["mismatch_count"]) and int(record["mismatch_count"]) > 0
        for record in records
    )
    overall_denominator = len(records)
    overall_rate = 100.0 * overall_witnesses / overall_denominator

    fig, (ax1, ax2) = plt.subplots(
        1,
        2,
        figsize=(8.0, 4.5),
        gridspec_kw={"width_ratios": [0.82, 1.38]},
    )
    fig.subplots_adjust(left=0.08, right=0.98, top=0.90, bottom=0.15, wspace=0.38)

    y1 = np.arange(len(ordered_outcomes))
    bars = ax1.barh(
        y1,
        [outcomes[classification] for classification in ordered_outcomes],
        color=[CLASS_COLORS[classification] for classification in ordered_outcomes],
        height=0.62,
        edgecolor="white",
        linewidth=0.5,
        zorder=3,
    )
    for bar, classification in zip(bars, ordered_outcomes):
        ax1.text(
            bar.get_width() + max(outcomes.values()) * 0.025,
            bar.get_y() + bar.get_height() / 2,
            f"{outcomes[classification]:,}",
            va="center",
            ha="left",
            fontsize=6.2,
            color=COLORS["ink"],
        )
    ax1.set_yticks(y1)
    ax1.set_yticklabels([CLASS_LABELS[item] for item in ordered_outcomes])
    ax1.invert_yaxis()
    ax1.set_xlim(0, max(outcomes.values()) * 1.16)
    ax1.set_xlabel("Single-site mutants")
    ax1.set_title("(a) Executed Outcomes", loc="left", fontweight="bold")
    ax1.grid(axis="x", color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax1.text(
        0.0,
        -0.16,
        f"N={len(records):,} generated mutants",
        transform=ax1.transAxes,
        ha="left",
        va="top",
        fontsize=6.0,
        color=COLORS["muted"],
    )

    y2 = np.arange(len(operator_rows))
    rates = [row[1] for row in operator_rows]
    ax2.hlines(y2, 0, rates, color=COLORS["grid"], linewidth=1.2, zorder=1)
    ax2.scatter(
        rates,
        y2,
        color=COLORS["evidence"],
        edgecolor="white",
        linewidth=0.55,
        s=31,
        zorder=3,
    )
    ax2.axvline(
        overall_rate,
        color=COLORS["constraints_ink"],
        linewidth=1.1,
        linestyle="--",
        zorder=2,
    )
    for y_value, (_, rate, denominator, killed) in zip(y2, operator_rows):
        ax2.text(
            min(rate + 1.3, 104.2),
            y_value,
            f"{rate:.0f}%  ({killed}/{denominator})",
            va="center",
            ha="left",
            fontsize=5.4,
            color=COLORS["ink"],
        )
    ax2.set_yticks(y2)
    ax2.set_yticklabels([OPERATOR_LABELS.get(row[0], row[0]) for row in operator_rows])
    ax2.set_xlim(0, 118)
    ax2.set_xlabel("Mutants with a dynamic mismatch witness (%)")
    ax2.set_title(
        "(b) Dynamic Witnesses by Mutation Operator", loc="left", fontweight="bold"
    )
    ax2.grid(axis="x", color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax2.text(
        1.0,
        1.015,
        f"Overall: {overall_rate:.1f}% ({overall_witnesses}/{overall_denominator})",
        transform=ax2.transAxes,
        ha="right",
        va="bottom",
        fontsize=6.0,
        color=COLORS["constraints_ink"],
    )

    for suffix, kwargs in (
        ("svg", {}),
        ("pdf", {}),
        ("png", {"dpi": 300}),
    ):
        path = OUTPUT_BASE.with_suffix(f".{suffix}")
        fig.savefig(path, bbox_inches="tight", **kwargs)
        print(f"generated: {path}")
    plt.close(fig)
    declare_font_stack(OUTPUT_BASE.with_suffix(".svg"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
