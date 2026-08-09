"""
Domain Corpus Volume & Data Scarcity Spectrum Plot Script (Chapter 4)

Literature Calibration & Citation Provenance (per-tier units differ):
1. Natural Language Web Text (~1.5e13 tokens): Llama 3 training scale (Meta, 2024); RedPajama (Together AI, 2023) [@MetaAI2024Llama31; @TogetherAI2023RedPajama].
2. General Software Code (~9e11 tokens): The Stack v2 / StarCoder2 [@LozhkovEtAl2024TheStackV2].
3. Synthesizable Hardware RTL (~1.31e5 modules): OpenRTLSet [@WangEtAl2025OpenRTLSet].
4. Physical Layout Samples (~1.02e4 layouts): CircuitNet [@ChaiEtAl2022CircuitNet].
5. Curated Architecture QA (~1.5e3 validated pairs): QuArch v0.1 [@PrakashEtAl2025QuArch].

Dataset Receipt: book/contents/chapters/04-representations/data/fig-architecture-data-scarcity.csv
Output Figure:   book/contents/chapters/04-representations/images/fig-architecture-data-scarcity.svg
"""

import csv
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

# Connect parent repo path to import book._python.plots
REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style
import matplotlib as mpl

apply_style()


def _declare_font_stack(svg_path: Path) -> None:
    # The SVG text-fit check requires the shared font stack declared in the file.
    text = svg_path.read_text()
    text = text.replace(
        "<defs>",
        '<defs>\n  <style type="text/css">*{font-family: Arial, Helvetica, sans-serif;}</style>',
        1,
    )
    svg_path.write_text(text)


def main():
    chapter_dir = Path(__file__).resolve().parent.parent
    csv_file = chapter_dir / "data" / "fig-architecture-data-scarcity.csv"
    out_plot_ch = chapter_dir / "images" / "fig-architecture-data-scarcity.svg"

    categories = []
    corpora = []
    tokens = []
    constraints = []
    citations = []

    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            categories.append(row["DomainCategory"])
            corpora.append(row["CorpusName"])
            tokens.append(float(row["TokenVolumeBucket"]))
            constraints.append(row["PrimaryAccessConstraint"])
            citations.append(row["RepresentativeCitations"])

    fig, ax = plt.subplots(figsize=(6.4, 3.0))

    y_pos = np.arange(len(corpora))
    colors_bars = [
        COLORS["ink"],
        COLORS["blue"],
        COLORS["green"],
        COLORS["purple"],
        COLORS["red"],
    ]

    bars = ax.barh(
        y_pos[::-1],
        tokens,
        left=1e2,
        color=colors_bars,
        alpha=0.85,
        height=0.52,
        zorder=3,
    )
    ax.set_xscale("log")
    ax.set_xlim(1e2, 5e14)
    ax.set_yticks(y_pos[::-1])
    ax.set_yticklabels(categories, fontsize=6.2, fontweight="bold", color=COLORS["ink"])
    ax.set_xlabel(
        "Corpus Scale (log; units differ per tier)",
        fontsize=7.0,
        color=COLORS["ink"],
    )
    ax.grid(True, which="both", color=COLORS["grid"], linewidth=0.5, zorder=0)

    labels_fmt = [
        r"$\sim 1.5{\times}10^{13}$ Tokens (Llama-3 / RedPajama)",
        r"$\sim 9{\times}10^{11}$ Tokens (The Stack v2 / StarCoder2)",
        r"$\sim 1.3{\times}10^5$ Modules (OpenRTLSet)",
        r"$\sim 10^4$ Layouts (CircuitNet)",
        r"$\sim 1.5{\times}10^3$ QA Pairs (QuArch v0.1)",
    ]

    for bar, val, lbl in zip(bars, tokens, labels_fmt):
        if val >= 1e10:
            ax.text(
                val / 1.4,
                bar.get_y() + bar.get_height() / 2,
                lbl,
                va="center",
                ha="right",
                fontsize=5.8,
                fontweight="bold",
                color="#ffffff",
            )
        else:
            ax.text(
                val * 1.35,
                bar.get_y() + bar.get_height() / 2,
                lbl,
                va="center",
                fontsize=5.8,
                fontweight="bold",
                color=COLORS["ink"],
            )

    plt.tight_layout()
    plt.savefig(out_plot_ch, dpi=300, bbox_inches="tight")
    _declare_font_stack(out_plot_ch)
    print(f"Data Scarcity Spectrum plot saved to '{out_plot_ch}'")


if __name__ == "__main__":
    main()
