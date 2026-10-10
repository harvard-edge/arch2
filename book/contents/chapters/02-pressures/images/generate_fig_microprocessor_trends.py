#!/usr/bin/env python3
"""Generate fig-microprocessor-trends: sampled CPU trends and accelerator specifications.

Show Karl Rupp's CPU sample maxima (1971-2021) beside a separate
2012-2026 accelerator frontier (25 accelerators including GPUs; undisclosed specs are N/A).
The earlier CPU cutoff does not establish a power ceiling after 2021.

Inputs:
  - data/datasets/chapter1-micro-trend.csv (Rupp microprocessor-trend-data, CC-BY 4.0)
  - data/datasets/chapter2-ai-accelerator-scaling-frontier.csv (Primary-cited accelerators)
  - data/datasets/chapter2-ai-design-milestones.csv (dated, primary-cited AI-assisted design events)

The band after 2026 is a hypothesis, not data: it marks the possibility that the design
process becomes the next lever. Milestones are events drawn on their own rail and carry
no y value.

Outputs (4.8 × 5.2 inches, with a 300-dpi PNG):
  - book/contents/chapters/02-pressures/images/fig-microprocessor-trends.png
  - book/contents/chapters/02-pressures/images/fig-microprocessor-trends.pdf
  - book/contents/chapters/02-pressures/images/fig-microprocessor-trends.svg
"""

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# Add repository root to path
REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style

CPU_CSV = REPO_ROOT / "data" / "datasets" / "chapter1-micro-trend.csv"
ACC_CSV = (
    REPO_ROOT / "data" / "datasets" / "chapter2-ai-accelerator-scaling-frontier.csv"
)
MILESTONE_CSV = REPO_ROOT / "data" / "datasets" / "chapter2-ai-design-milestones.csv"
DEFAULT_OUT_DIR = Path(__file__).resolve().parent


def milestones():
    with open(MILESTONE_CSV, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(l for l in f if not l.startswith("#")))
    return [(float(r["decimal_year"]), r) for r in rows]


def cpu_series():
    with open(CPU_CSV, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(l for l in f if not l.startswith("#")))
    out = {}
    for r in rows:
        out.setdefault(r["series"], []).append((float(r["year"]), float(r["value"])))
    for k in out:
        out[k].sort()
    return out


def accelerator_frontier():
    """Extract running maximum frontier by release year for packaged parts, plus wafer-scale."""
    with open(ACC_CSV, "r", encoding="utf-8") as f:
        rows = [r for r in csv.reader(f) if r and not r[0].startswith("#")]
    head, rows = rows[0], rows[1:]
    idx = {name: i for i, name in enumerate(head)}

    def num(text):
        # Undisclosed specifications are recorded as N/A and never plotted.
        try:
            return float(text)
        except ValueError:
            return None

    chips = []
    for r in rows:
        chips.append(
            {
                "name": r[idx["Chip_Name"]],
                "year": int(r[idx["Release_Year"]]),
                "trans_k": (
                    num(r[idx["Transistors_Billion"]]) * 1e6  # billions -> thousands
                    if num(r[idx["Transistors_Billion"]]) is not None
                    else None
                ),
                "watts": num(r[idx["TDP_Watts"]]),
                "wafer": "Wafer-Scale" in r[idx["Packaging_Type"]],
            }
        )
    packaged = sorted((c for c in chips if not c["wafer"]), key=lambda c: c["year"])

    def frontier(key):
        pts, best = [], 0.0
        for c in packaged:
            if c[key] is not None and c[key] > best:
                best = c[key]
                pts.append((c["year"], best, c["name"]))
        return pts

    return frontier("trans_k"), frontier("watts"), [c for c in chips if c["wafer"]]


def generate_figure(out_dir: Path | None = None):
    apply_style()
    out_dir = out_dir or DEFAULT_OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    cpu = cpu_series()
    acc_trans, acc_watts, wafer = accelerator_frontier()

    purple = COLORS.get("purple", "#7B4EA8")
    blue = COLORS.get("blue", "#1F77B4")
    orange = COLORS.get("orange", "#E8A33D")
    red = COLORS.get("red", "#D62728")
    green = COLORS.get("green", "#2CA02C")
    ink = COLORS.get("ink", "#212121")
    grey = "#62676C"
    decision = COLORS.get("decision_ink", "#A82E70")

    # Match the book's physical column width. Keeping a fixed canvas prevents
    # long annotations from silently expanding the PDF and shrinking every label.
    fig = plt.figure(figsize=(4.8, 5.2))
    ax = fig.add_axes((0.115, 0.535, 0.86, 0.395))
    ax.set_yscale("log")
    handles = []
    for key, color, label in (
        ("transistors", purple, "CPU transistors (thousands)"),
        ("specint", blue, "CPU SpecINT × 1000"),
        ("frequency", orange, "CPU frequency (MHz)"),
        ("cpu_watts", red, "CPU sampled power (W)"),
        ("cpu_threads", green, "CPU hardware threads"),
    ):
        xs, ys = zip(*cpu[key])
        (line,) = ax.plot(
            xs, ys, "o-", color=color, ms=2.3, lw=1.05, label=label, zorder=3
        )
        handles.append(line)

    for pts, color, label, marker in (
        (acc_trans, purple, "Accel. transistors (thousands)", "^"),
        (acc_watts, red, "Accel. power rating (W)", "s"),
    ):
        (line,) = ax.plot(
            [p[0] for p in pts],
            [p[1] for p in pts],
            marker=marker,
            ls="--",
            color=color,
            ms=3.2,
            lw=1.1,
            mfc="white",
            mew=0.8,
            zorder=4,
            label=label,
        )
        handles.append(line)

    # Wafer-scale points remain separate from the packaged-part frontier.
    wafer = sorted(wafer, key=lambda c: c["year"])
    (line,) = ax.plot(
        [c["year"] for c in wafer],
        [c["trans_k"] for c in wafer],
        ls=":",
        marker="D",
        ms=2.8,
        color=grey,
        lw=1.0,
        mfc="white",
        mew=0.8,
        zorder=2,
        label="Wafer-scale transistors (thousands)",
    )
    handles.append(line)

    for year in (2005, 2016):
        ax.axvline(year, color=ink, ls="--", lw=0.65, alpha=0.55)
    ax.axvspan(2016, 2026, color=red, alpha=0.04, zorder=0)
    ax.axvline(2026, color=decision, ls="--", lw=0.75, alpha=0.9)
    ax.axvspan(
        2026,
        2040,
        facecolor="none",
        edgecolor=decision,
        hatch="////",
        lw=0,
        alpha=0.16,
        zorder=0,
    )
    for year, label in (
        (1987.5, "Device scaling"),
        (2010.5, "Parallelism"),
        (2021, "Specialization"),
    ):
        ax.text(
            year,
            1.055,
            label,
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="bottom",
            fontsize=6.8,
            color=ink,
        )
    ax.text(
        2033,
        1.2e6,
        "AI-native\ndesign era?",
        ha="center",
        va="center",
        fontsize=7.3,
        fontweight="bold",
        color=decision,
    )
    ax.text(
        2033,
        1.5e4,
        "Hypothesis",
        ha="center",
        fontsize=7.0,
        color=decision,
        style="italic",
    )
    ax.set_xlim(1970, 2040)
    ax.set_ylim(0.45, 2.2e10)
    ax.set_xticks(range(1970, 2041, 10))
    ax.set_yticks([1, 1e2, 1e4, 1e6, 1e8, 1e10])
    ax.set_yticklabels(
        [r"$10^0$", r"$10^2$", r"$10^4$", r"$10^6$", r"$10^8$", r"$10^{10}$"]
    )
    ax.set_xlabel("Release year", fontsize=7.2, labelpad=4)
    ax.grid(axis="y", color="#E8EAED", lw=0.5)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#DADCE0")
    ax.tick_params(labelsize=7.0, colors=ink, pad=2, length=2.5)

    # The wafer label wraps within its column rather than enlarging the canvas.
    handles[-1].set_label(
        "Cerebras wafer-scale transistors\n(thousands; shown for scale)"
    )
    ordered = [handles[i] for i in (0, 1, 2, 3, 4, 5, 6, 7)]
    fig.legend(
        handles=ordered,
        loc="upper left",
        bbox_to_anchor=(0.06, 0.477),
        ncol=2,
        fontsize=7.0,
        frameon=False,
        handlelength=2.0,
        columnspacing=1.1,
        handletextpad=0.55,
        labelspacing=0.50,
        borderaxespad=0,
    )
    fig.text(
        0.075,
        0.323,
        "CPU: 4-year sample maxima, 1971–2021 (Rupp).",
        fontsize=7.0,
        color=grey,
    )
    fig.text(
        0.075,
        0.302,
        "Accelerators: packaged-part frontier, 2012–2026.",
        fontsize=7.0,
        color=grey,
    )
    fig.text(
        0.075,
        0.281,
        "2005: Dennard scaling ends; 2016: specialization turn.",
        fontsize=7.0,
        color=grey,
    )

    # A separate chronological report rail has no hardware-performance y value.
    # Equal row spacing is explicitly stated; dates retain their full precision.
    fig.text(
        0.075,
        0.249,
        "AI-assisted design reports",
        fontsize=8.1,
        fontweight="bold",
        color=decision,
    )
    fig.text(
        0.075,
        0.228,
        "Report dates; rail spacing is not to scale.",
        fontsize=7.0,
        color=grey,
    )
    short = {
        "AlphaChip": "AlphaChip: TPU block floorplans",
        "ChipNeMo": "ChipNeMo: domain-adapted LLM",
        "Design Conductor": "Design Conductor: RISC-V CPU",
        "Design Conductor 2.0": "Design Conductor 2.0: accelerator",
        "AlphaEvolve": "AlphaEvolve: next-generation TPU circuit",
        "Jalapeno": "Jalapeño: nine months to tapeout",
    }
    rows = sorted(milestones(), key=lambda item: item[0])
    ys = [0.191 - i * 0.031 for i in range(len(rows))]
    fig.add_artist(
        Line2D(
            [0.086, 0.086],
            [ys[-1], ys[0]],
            transform=fig.transFigure,
            color=decision,
            lw=0.9,
            alpha=0.55,
        )
    )
    for (_, row), y in zip(rows, ys):
        fig.add_artist(
            Line2D(
                [0.086],
                [y],
                transform=fig.transFigure,
                marker="D",
                ms=3.4,
                color=decision,
                mec="white",
                mew=0.5,
            )
        )
        fig.text(0.112, y, row["date"], va="center", fontsize=7.1, color=grey)
        fig.text(
            0.268, y, short[row["milestone"]], va="center", fontsize=7.1, color=ink
        )

    out_png = out_dir / "fig-microprocessor-trends.png"
    out_pdf = out_dir / "fig-microprocessor-trends.pdf"
    out_svg = out_dir / "fig-microprocessor-trends.svg"
    # Exact 4.8-inch width: all text is authored at its final print size.
    fig.savefig(out_png, dpi=300)
    fig.savefig(out_pdf)
    fig.savefig(out_svg)
    out_svg.write_text(
        "\n".join(line.rstrip() for line in out_svg.read_text().splitlines()) + "\n"
    )
    plt.close(fig)
    print(f"Generated {out_png}, {out_pdf}, and {out_svg}")


if __name__ == "__main__":
    generate_figure()
