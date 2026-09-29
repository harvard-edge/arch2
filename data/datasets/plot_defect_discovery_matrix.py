"""
Chapter 7: defect discovery by method and mutant survival across test suites.
-----------------------------------------------------------------------------
Panel (a): the method that found each of the 47 RTL issues resolved before
CV32E40P v1 RTL freeze, as reported in the OpenHW CV32E40P User Manual
(verification chapter).
Panel (b): Herdt et al. (ASP-DAC 2021) Table 1 totals. Mutants seeded into a
reference RISC-V instruction-set simulator; each test suite runs on the
mutants the previous suite left alive.

Datasets (transcribed, per-row citation and url):
- data/datasets/chapter7-defect-discovery-modalities.csv
- data/datasets/chapter7-herdt-mutation-compliance.csv

The earlier panel (b) plotted chapter7-testbench-vacuity-mutation.csv, whose
coverage and kill-rate values do not appear in the cited paper. That file is
withdrawn and no longer read here.
"""

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style, save_figure_bundle  # noqa: E402

apply_style()


def read_rows(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(row for row in f if not row.startswith("#")))


def main() -> None:
    mod_rows = read_rows(
        REPO_ROOT / "data" / "datasets" / "chapter7-defect-discovery-modalities.csv"
    )
    mut_rows = read_rows(
        REPO_ROOT / "data" / "datasets" / "chapter7-herdt-mutation-compliance.csv"
    )

    out_base = (
        REPO_ROOT
        / "book"
        / "contents"
        / "chapters"
        / "07-feedback"
        / "images"
        / "fig-ch07-defect-discovery-modalities"
    )

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(5.4, 2.5), gridspec_kw={"width_ratios": [1.25, 1.0]}
    )
    fig.subplots_adjust(wspace=0.95, left=0.30, right=0.97, top=0.86, bottom=0.2)

    # ---------------- (a) issues found by method ----------------
    short = {
        "Formal verification": "Formal verification",
        "Inspection (human review)": "Inspection",
        "Simulation: directed, self-checking test": "Sim: directed test",
        "Simulation: step-and-compare with ISS": "Sim: step-and-compare",
        "Simulation: constrained-random": "Sim: constrained-random",
        "Lint": "Lint",
        "Unknown": "Unknown",
    }
    labels = [short[r["modality"]] for r in mod_rows]
    counts = [int(r["issues_found"]) for r in mod_rows]
    groups = [r["method_group"] for r in mod_rows]
    style = {
        "non-simulation": dict(color=COLORS["green"], hatch=None),
        "simulation": dict(color=COLORS["blue"], hatch="////"),
        "unknown": dict(color=COLORS["grid"], hatch=None),
    }
    y = np.arange(len(labels))
    for yi, c, g in zip(y, counts, groups):
        s = style[g]
        ax1.barh(
            yi,
            c,
            height=0.6,
            color=s["color"] if s["hatch"] is None else "white",
            edgecolor=s["color"],
            hatch=s["hatch"],
            linewidth=0.9,
            zorder=3,
        )
        ax1.text(
            c + 0.4,
            yi,
            str(c),
            va="center",
            ha="left",
            fontsize=5.4,
            color=COLORS["ink"],
            zorder=4,
        )
    ax1.set_yticks(y)
    ax1.set_yticklabels(labels, fontsize=5.6)
    ax1.invert_yaxis()
    ax1.set_xlim(0, 16)
    ax1.set_xlabel("RTL issues found (of 47)")
    ax1.grid(True, axis="x", color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax1.set_title("CV32E40P issues by finding method", fontsize=6.8, pad=6)
    # direct group key instead of a colour-only legend
    ax1.text(
        15.8,
        5.45,
        "solid: non-simulation\nhatched: simulation",
        ha="right",
        va="center",
        fontsize=4.9,
        color=COLORS["muted"],
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="white",
            edgecolor=COLORS["grid"],
            lw=0.5,
        ),
        zorder=5,
    )
    ax1.text(
        -0.62,
        1.10,
        "(a)",
        transform=ax1.transAxes,
        fontsize=6.8,
        fontweight="bold",
        color=COLORS["ink"],
    )

    # ---------------- (b) kill rate per successive suite ----------------
    stage_short = {
        "Official compliance tests": "Official\ncompliance",
        "Specification-based compliance tests": "Spec-based\ncompliance",
        "Symbolic-execution mutation tests": "Symbolic-\nexecution tests",
    }
    st = [stage_short[r["stage"]] for r in mut_rows]
    pct = [float(r["kill_pct_of_entering"]) for r in mut_rows]
    ent = [int(r["mutants_entering"]) for r in mut_rows]
    kil = [int(r["mutants_killed"]) for r in mut_rows]
    yb = np.arange(len(st))
    ax2.barh(
        yb,
        [100] * len(st),
        height=0.6,
        color="white",
        edgecolor=COLORS["red"],
        hatch="....",
        linewidth=0.8,
        zorder=2,
    )
    ax2.barh(
        yb,
        pct,
        height=0.6,
        color=COLORS["green"],
        edgecolor=COLORS["green"],
        linewidth=0.8,
        zorder=3,
    )
    for yi, p, e, k in zip(yb, pct, ent, kil):
        ax2.text(
            50,
            yi + 0.47,
            f"{k:,} of {e:,} killed ({p:.1f}%)",
            ha="center",
            va="top",
            fontsize=5.0,
            color=COLORS["ink"],
            zorder=5,
        )
    ax2.set_yticks(yb)
    ax2.set_yticklabels(st, fontsize=5.6)
    ax2.invert_yaxis()
    ax2.set_xlim(0, 100)
    ax2.set_ylim(2.75, -0.55)
    ax2.set_xlabel("Share of entering mutants (%)\nsolid: killed   dotted: left alive")
    ax2.grid(True, axis="x", color=COLORS["grid"], linewidth=0.5, zorder=0)
    ax2.set_title("Suites run in turn on survivors", fontsize=6.8, pad=6)
    ax2.text(
        -0.62,
        1.10,
        "(b)",
        transform=ax2.transAxes,
        fontsize=6.8,
        fontweight="bold",
        color=COLORS["ink"],
    )

    for ax in (ax1, ax2):
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        ax.tick_params(axis="both", length=2.5, width=0.6, pad=2)

    save_figure_bundle(fig, out_base)
    plt.close(fig)
    print(f"Figure written: {out_base}.{{svg,pdf,png}}")


if __name__ == "__main__":
    main()
