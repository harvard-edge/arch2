"""
EDA recipe-sensitivity plot (Chapter 6): mapped area across ABC pass sequences.

Provenance
----------
1. Platform: logic synthesis on the Nangate45 OpenCellLibrary (typical corner).
2. Toolchain: Yosys 0.67+post (git sha1 b8e7da6f40ae8f552c116bf6c359b07c6533e159) with ABC.
3. Designs (five open blocks, pinned in reproduce_eda_recipe_area.py):
   picorv32 (YosysHQ), dynamic_node (OpenPiton router, ORFS), aes_cipher_top (ORFS),
   sha256_core (secworks), gcd (ORFS).
4. 125 runs: 25 ABC pass sequences per design, each (design, sequence) pair once, so
   the data measure recipe sensitivity, not run-to-run nondeterminism.
5. Every plotted area is re-derived exactly by reproduce_eda_recipe_area.py. Runtime and
   memory columns were removed from the dataset because no retained log supports them.

Dataset: book/contents/chapters/06-environments/data/fig-eda-runtime-variance-dispersion.csv
Output:  book/contents/chapters/06-environments/images/fig-eda-runtime-variance-dispersion.{svg,png,pdf}
"""

import csv
import sys
from pathlib import Path
import statistics
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

# Connect parent repo path to import book._python.plots
REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style


def _declare_font_stack(svg_path: Path) -> None:
    text = svg_path.read_text()
    if '<style type="text/css">' not in text:
        text = text.replace(
            "<defs>",
            '<defs>\n  <style type="text/css">*{font-family: Arial, Helvetica, sans-serif;}</style>',
            1,
        )
        svg_path.write_text(text)


def main():
    chapter_dir = Path(__file__).resolve().parent.parent
    csv_file = chapter_dir / "data" / "fig-eda-runtime-variance-dispersion.csv"
    out_svg = chapter_dir / "images" / "fig-eda-runtime-variance-dispersion.svg"
    out_png = chapter_dir / "images" / "fig-eda-runtime-variance-dispersion.png"
    out_pdf = chapter_dir / "images" / "fig-eda-runtime-variance-dispersion.pdf"

    # Load dataset
    data = defaultdict(
        lambda: {
            "domain": "",
            "desc": "",
            "area": [],
        }
    )

    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(l for l in f if not l.startswith("#"))
        for row in reader:
            d = row["DesignName"]
            data[d]["domain"] = row["DesignDomain"]
            data[d]["desc"] = row["DesignDescription"]
            data[d]["area"].append(float(row["ChipArea_um2"]))

    design_order = [
        "picorv32",
        "dynamic_node",
        "aes_cipher_top",
        "sha256_core",
        "gcd",
    ]
    display_names = [
        "Pico-\nRV32",
        "NoC\nrouter",
        "AES-\n128",
        "SHA-\n256",
        "GCD",
    ]

    domain_labels = {
        "picorv32": "PicoRV32 core",
        "dynamic_node": "NoC router",
        "aes_cipher_top": "AES-128",
        "sha256_core": "SHA-256",
        "gcd": "GCD",
    }

    palette = [
        COLORS["blue"],  # RV32 Core -> teal
        COLORS["purple"],  # NoC Router -> violet
        COLORS["green"],  # AES -> green
        COLORS["amber"],  # SHA256 -> amber
        COLORS["magenta"],  # GCD -> magenta
    ]

    markers = ["o", "s", "^", "D", "P"]

    apply_style()
    fig, ax1 = plt.subplots(figsize=(4.8, 3.0))
    fig.subplots_adjust(left=0.14, right=0.98, top=0.88, bottom=0.2)

    # Panel A: mapped area relative to each design's median, across pass sequences
    norm_area_data = []
    for i, d in enumerate(design_order):
        areas = data[d]["area"]
        med = statistics.median(areas)
        pct_dev = [((a - med) / med) * 100.0 for a in areas]
        norm_area_data.append(pct_dev)
        x_jitter = i + 0.12 * np.sin(np.arange(len(pct_dev)) * 2.39)
        ax1.scatter(
            x_jitter,
            pct_dev,
            marker=markers[i],
            color=palette[i],
            alpha=0.75,
            s=13,
            edgecolors=COLORS["ink"],
            linewidth=0.35,
            zorder=3,
        )

    ax1.boxplot(
        norm_area_data,
        positions=np.arange(len(design_order)),
        widths=0.42,
        patch_artist=True,
        showfliers=False,
        zorder=4,
        boxprops=dict(facecolor="none", edgecolor=COLORS["ink"], linewidth=0.8),
        medianprops=dict(color=COLORS["ink"], linewidth=1.3),
        whiskerprops=dict(color=COLORS["ink"], linewidth=0.7, linestyle="--"),
        capprops=dict(color=COLORS["ink"], linewidth=0.7),
    )

    ax1.axhline(0, color=COLORS["muted"], linestyle=":", linewidth=0.7, zorder=1)
    ax1.set_xticks(np.arange(len(design_order)))
    ax1.set_xticklabels(display_names, fontsize=7.6, color=COLORS["ink"])
    ax1.set_ylabel("Mapped area vs. design median (%)", fontsize=8.6)
    ax1.set_yticks([-5, 0, 5, 10])
    ax1.grid(True, axis="y", color=COLORS["grid"], linewidth=0.5, zorder=0)

    # Spread (max - min) as a percentage of the median, computed from the data
    top = max(max(v) for v in norm_area_data)
    bottom = min(min(v) for v in norm_area_data)
    for i, v in enumerate(norm_area_data):
        spread = max(v) - min(v)
        ax1.text(
            i,
            top + 1.6,
            f"{spread:.1f}%",
            ha="center",
            va="bottom",
            fontsize=7.4,
            color=COLORS["ink"],
            zorder=5,
        )
    ax1.text(
        -0.45,
        top + 4.2,
        "Spread across 25 recipes (% of median)",
        ha="left",
        va="bottom",
        fontsize=7.2,
        color=COLORS["muted"],
    )
    ax1.set_ylim(bottom - 1.5, top + 6.8)
    ax1.set_title(
        "Mapped area across 25 ABC pass sequences",
        fontsize=8.8,
        fontweight="bold",
        pad=5,
        color=COLORS["ink"],
    )

    for ax in [ax1]:
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        ax.spines["left"].set_color(COLORS["ink"])
        ax.spines["bottom"].set_color(COLORS["ink"])
        ax.tick_params(axis="both", labelsize=7.4, length=2.5, width=0.6, pad=2)

    plt.savefig(out_svg, format="svg", bbox_inches="tight")
    plt.savefig(out_png, format="png", dpi=300, bbox_inches="tight")
    plt.savefig(out_pdf, format="pdf", bbox_inches="tight")
    _declare_font_stack(out_svg)
    print(f"Generated {out_svg}, {out_png}, and {out_pdf}")


if __name__ == "__main__":
    main()
