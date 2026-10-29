#!/usr/bin/env python3
"""Plot every reported Ibex test group, retaining the run denominators."""
import csv
import json
from pathlib import Path
import subprocess
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))
from book._python.plots import COLORS, apply_style, save_figure_bundle
from evidence_bundle import verify_sources, record_build


def main():
    manifest = verify_sources(HERE)
    subprocess.run([sys.executable, str(HERE / "collect.py")], check=True)
    subprocess.run([sys.executable, str(HERE / "extract.py")], check=True)
    rows = list(csv.DictReader((HERE / "derived/test_summary.csv").open()))
    for row in rows:
        for key in ("passing_runs", "nonpassing_runs", "total_runs"):
            row[key] = int(row[key])
        assert row["passing_runs"] + row["nonpassing_runs"] == row["total_runs"]
        assert row["total_runs"] > 0
    assert len({r["test_name"] for r in rows}) == len(rows)
    partial = sorted(
        [r for r in rows if r["nonpassing_runs"]],
        key=lambda r: (r["passing_runs"] / r["total_runs"], r["test_name"]),
    )
    perfect = [r for r in rows if not r["nonpassing_runs"]]
    totals = {
        k: sum(r[k] for r in rows)
        for k in ("passing_runs", "nonpassing_runs", "total_runs")
    }
    all_passing = {k: sum(r[k] for r in perfect) for k in totals}
    audit = json.loads((HERE / "derived/extraction_audit.json").read_text())
    assert (len(rows), totals["passing_runs"], totals["total_runs"], len(partial)) == (
        56,
        1464,
        1530,
        15,
    )
    assert audit["counts"]["failure_detail_blocks"] == totals["nonpassing_runs"] == 66
    display = [
        {
            "display_label": "All 56 test groups",
            "test_names": ";".join(r["test_name"] for r in rows),
            **totals,
        }
    ]
    display += [
        {
            "display_label": r["test_name"]
            .removeprefix("riscv_")
            .removesuffix("_test"),
            "test_names": r["test_name"],
            **{k: r[k] for k in totals},
        }
        for r in partial
    ]
    display += [
        {
            "display_label": "Other 41 groups (all passing)",
            "test_names": ";".join(r["test_name"] for r in perfect),
            **all_passing,
        }
    ]
    with (HERE / "derived/plot_rows.csv").open("w") as f:
        writer = csv.DictWriter(f, fieldnames=list(display[0]))
        writer.writeheader()
        writer.writerows(display)
    summary = {
        "test_groups": len(rows),
        **totals,
        "aggregate_pass_percentage": 100
        * totals["passing_runs"]
        / totals["total_runs"],
        "groups_with_nonpassing_records": len(partial),
        "groups_with_only_passing_records": len(perfect),
        "only_passing_groups_total_records": all_passing["total_runs"],
        "scope": "One retained report; no inference about chip defects or all scheduled attempts.",
    }
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    apply_style()
    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    ys = [0] + [i + 1.6 for i in range(len(partial))] + [len(partial) + 2.2]
    rates = [r["passing_runs"] / r["total_runs"] for r in display]
    ax.barh(ys, rates, height=0.65, color=COLORS["evidence"], label="Passing")
    ax.barh(
        ys,
        [1 - v for v in rates],
        left=rates,
        height=0.65,
        color=COLORS["constraints"],
        hatch="///",
        edgecolor="white",
        linewidth=0.25,
        label="Nonpassing",
    )
    ax.set(
        yticks=ys,
        yticklabels=[r["display_label"] for r in display],
        xlim=(0, 1),
        ylim=(ys[-1] + 0.8, -0.75),
        xlabel="Share of reported test-run records",
    )
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    ax.tick_params(axis="y", length=0, labelsize=6.3, pad=5)
    ax.grid(axis="x", color=COLORS["grid"], lw=0.5)
    ax.grid(axis="y", visible=False)
    ax.spines[["top", "right", "left"]].set_visible(False)
    for y, row in zip(ys, display):
        label = f'{row["passing_runs"]:,} / {row["total_runs"]:,}'
        if y == 0:
            label += f"  ({rates[0] * 100:.1f}%)"
        ax.text(
            1.025,
            y,
            label,
            va="center",
            ha="left",
            fontsize=6.3,
            fontweight="bold" if y == 0 else "normal",
            clip_on=False,
        )
    ax.text(1.025, -0.9, "Passing / reported", ha="left", fontsize=6.2, clip_on=False)
    ax.axhline(0.8, color=COLORS["grid"], lw=0.7, clip_on=False)
    ax.axhline(ys[-1] - 0.8, color=COLORS["grid"], lw=0.7, clip_on=False)
    ax.legend(
        loc="lower left",
        bbox_to_anchor=(0, 1.02),
        ncol=2,
        frameon=False,
        borderaxespad=0,
    )
    fig.text(
        0.03,
        0.965,
        "An aggregate pass rate can conceal failures in individual checks",
        fontsize=9,
        weight="bold",
    )
    fig.text(
        0.03,
        0.925,
        "Ibex OpenTitan configuration | 16 October 2026, 04:16 UTC | commit 96a34a5617b2",
        fontsize=6.5,
        color=COLORS["muted"],
    )
    fig.text(
        0.03,
        0.035,
        "All 56 groups are included; the 41 entirely passing groups are combined. Labels omit riscv_ and _test.\nNonpassing records include simulator diagnostics and timeouts; they do not identify distinct chip defects.",
        fontsize=6,
        color=COLORS["muted"],
        linespacing=1.4,
    )
    fig.subplots_adjust(left=0.31, right=0.79, top=0.825, bottom=0.14)
    save_figure_bundle(fig, HERE / "figure")
    plt.close(fig)
    record_build(
        HERE,
        {
            "source_files_hash_verified": len(manifest["files"]),
            "all_reported_groups_included": True,
            "failure_details_reconcile": True,
            "plot_rows_retain_full_test_identifiers": True,
        },
        "Offline extraction, source-code inspection, and arithmetic for one public regression report. No simulation rerun, root-cause diagnosis, chip-quality estimate, or AI comparison.",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
