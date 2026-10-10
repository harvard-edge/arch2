"""Generate fig-ch09-software-porting-wall from the measured CUTLASS, Triton, and vLLM datasets.

Inputs are written by measure_software_porting_wall.py (the retained harness; bucket
definitions live there). Tick labels show each tag and the year of its tagged commit.
Triton is shown as the sum of the selected source trees: directory reorganizations,
vendored headers, and tests prevent an equivalent shared-versus-backend comparison.
"""

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

repo_root = Path(__file__).resolve().parents[5]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from book._python.plots import COLORS, apply_style


def load(name):
    path = repo_root / "data" / "datasets" / name
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(l for l in fh if not l.startswith("#")))


def ticks(rows):
    return [
        f"{r['tag'].removesuffix('.0')}\n('{r['tag_commit_date'][2:4]})" for r in rows
    ]


def stacked(ax, rows, series, title):
    x = np.arange(len(rows))
    bottom = np.zeros(len(rows))
    for key, label, color, hatch in series:
        vals = np.array([float(r[key]) / 1000.0 for r in rows])
        ax.bar(
            x,
            vals,
            0.6,
            bottom=bottom,
            label=label,
            color=color,
            edgecolor=COLORS["ink"],
            linewidth=0.4,
            hatch=hatch,
            zorder=3,
        )
        bottom += vals
    ax.set_xticks(x)
    ax.set_xticklabels(ticks(rows), fontsize=7.8)
    ax.set_ylabel("Source lines (thousands)", fontsize=8.2)
    ax.set_title(title, fontsize=9.2, fontweight="bold", loc="left", pad=6)
    ax.set_ylim(0, bottom.max() * 1.55)
    ax.tick_params(axis="y", labelsize=7.8)
    ax.grid(axis="y", color=COLORS["grid"], linewidth=0.5, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    return x


def generate_figure(out_dir: Path) -> None:
    apply_style()
    cut, tri, vll = (
        load("chapter9-cutlass-porting-wall.csv"),
        load("chapter9-triton-narrow-waist.csv"),
        load("chapter9-vllm-kernel-fragmentation.csv"),
    )
    # Stack the panels at approximately the book's native column width so their
    # labels remain readable when the complete figure is placed at 4.8 inches.
    fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(5.0, 4.9))
    fig.subplots_adjust(left=0.15, right=0.84, top=0.955, bottom=0.075, hspace=0.55)

    x = stacked(
        a1,
        cut,
        [
            ("shared_loc", "Other include/ headers", COLORS["row"], None),
            ("warp_tb_loc", "Warp/threadblock GEMM", COLORS["workload_tint"], "///"),
            ("arch_loc", "Architecture-specific", COLORS["green"], None),
        ],
        "(a) CUTLASS headers",
    )
    tw = a1.twinx()
    tw.plot(
        x,
        [int(r["inline_ptx_asm_volatile"]) for r in cut],
        color=COLORS["red"],
        marker="o",
        markersize=3.5,
        linewidth=1.4,
        label="Inline asm (right)",
        zorder=5,
    )
    tw.set_ylim(0, 5000)
    tw.set_ylabel(
        "Inline asm statements",
        fontsize=8.2,
        color=COLORS["constraints_ink"],
        labelpad=4,
    )
    tw.tick_params(axis="y", labelsize=7.8, labelcolor=COLORS["constraints_ink"])
    h1, l1 = a1.get_legend_handles_labels()
    h2, l2 = tw.get_legend_handles_labels()
    a1.legend(
        h1 + h2,
        l1 + l2,
        loc="upper left",
        fontsize=7.5,
        frameon=False,
        ncol=2,
        columnspacing=0.9,
        handlelength=1.5,
        handletextpad=0.4,
    )

    # Preserve the measured union, without treating directory buckets as comparable
    # estimates of shared compiler code versus target-specific implementation work.
    for row in tri:
        row["selected_tree_loc"] = sum(
            int(row[key])
            for key in (
                "shared_cpp_loc",
                "nvidia_backend_loc",
                "amd_backend_loc",
                "python_loc",
            )
        )
    stacked(
        a2,
        tri,
        [
            (
                "selected_tree_loc",
                "Selected source trees",
                COLORS["designspace_tint"],
                None,
            ),
        ],
        "(b) Triton source-tree footprint",
    )
    a2.legend(loc="upper left", fontsize=7.8, frameon=False)
    a2.text(
        0.03,
        0.78,
        "Includes vendored headers,\nexamples, and tests",
        transform=a2.transAxes,
        fontsize=7.5,
        va="top",
        color=COLORS["muted"],
        bbox=dict(
            boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.92
        ),
        zorder=5,
    )

    stacked(
        a3,
        vll,
        [
            ("attention_loc", "csrc/attention", COLORS["blue"], None),
            ("quant_loc", "csrc/quantization", COLORS["orange"], "///"),
            ("moe_loc", "csrc/moe", COLORS["purple"], "..."),
            ("other_csrc_loc", "Other csrc/", COLORS["row"], None),
        ],
        "(c) vLLM native kernels (csrc/)",
    )
    a3.legend(
        loc="upper left",
        fontsize=7.8,
        frameon=False,
        ncol=2,
        columnspacing=1.0,
        handlelength=1.5,
        handletextpad=0.4,
    )

    for ext, kw in (("png", {"dpi": 300}), ("svg", {}), ("pdf", {})):
        fig.savefig(
            out_dir / f"fig-ch09-software-porting-wall.{ext}", bbox_inches="tight", **kw
        )
    svg = out_dir / "fig-ch09-software-porting-wall.svg"
    svg.write_text(
        "\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n"
    )
    plt.close(fig)
    print("Generated fig-ch09-software-porting-wall")


if __name__ == "__main__":
    generate_figure(Path(__file__).resolve().parent)
