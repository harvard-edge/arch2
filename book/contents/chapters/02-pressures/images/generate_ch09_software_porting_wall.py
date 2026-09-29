"""Generate fig-ch09-software-porting-wall from the measured CUTLASS, Triton, and vLLM datasets.

Inputs are written by measure_software_porting_wall.py (the retained harness; bucket
definitions live there). Tick labels show each tag and the year of its tagged commit.
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
    ax.set_xticklabels(ticks(rows), fontsize=6.0)
    ax.set_ylabel("Lines of code (thousands)", fontsize=7.0)
    ax.set_title(title, fontsize=7.6, fontweight="bold", loc="left")
    ax.set_ylim(0, bottom.max() * 1.35)
    ax.tick_params(axis="y", labelsize=6.2)
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
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(10.0, 3.4))
    fig.subplots_adjust(left=0.06, right=0.95, top=0.86, bottom=0.2, wspace=0.42)

    x = stacked(
        a1,
        cut,
        [
            ("shared_loc", "Other include/ headers", COLORS["row"], None),
            ("warp_tb_loc", "Warp/threadblock GEMM", COLORS["workload_tint"], "///"),
            ("arch_loc", "Architecture-specific (arch/)", COLORS["green"], None),
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
        label='Inline "asm volatile" (right)',
        zorder=5,
    )
    tw.set_ylim(0, 4200)
    tw.set_ylabel(
        'Inline "asm volatile" statements',
        fontsize=6.6,
        color=COLORS["constraints_ink"],
        labelpad=4,
    )
    tw.tick_params(axis="y", labelsize=6.0, labelcolor=COLORS["constraints_ink"])
    h1, l1 = a1.get_legend_handles_labels()
    h2, l2 = tw.get_legend_handles_labels()
    a1.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=5.4, frameon=False)

    stacked(
        a2,
        tri,
        [
            ("shared_cpp_loc", "Shared C++ (include/, lib/)", COLORS["purple"], None),
            ("nvidia_backend_loc", "NVIDIA backend", COLORS["green"], "///"),
            ("amd_backend_loc", "AMD backend", COLORS["orange"], "..."),
            ("python_loc", "Python front end", COLORS["row"], None),
        ],
        "(b) Triton compiler",
    )
    a2.legend(loc="upper left", fontsize=5.4, frameon=False)

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
    a3.legend(loc="upper left", fontsize=5.4, frameon=False)

    for ext, kw in (("png", {"dpi": 300}), ("svg", {}), ("pdf", {})):
        fig.savefig(
            out_dir / f"fig-ch09-software-porting-wall.{ext}", bbox_inches="tight", **kw
        )
    plt.close(fig)
    print("Generated fig-ch09-software-porting-wall")


if __name__ == "__main__":
    generate_figure(Path(__file__).resolve().parent)
