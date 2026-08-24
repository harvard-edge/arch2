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

# Connect parent repo path to import book._python.plots
REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import (
    COLORS,
    apply_style,
    draw_spectrum_bars,
    save_figure_bundle,
)

apply_style()


def main():
    chapter_dir = Path(__file__).resolve().parents[1]
    csv_file = chapter_dir / "data" / "fig-architecture-data-scarcity.csv"
    out_plot_ch = chapter_dir / "images" / "fig-architecture-data-scarcity"
    global_img_base = REPO_ROOT / "book" / "images" / "fig-architecture-data-scarcity"

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

    fig, ax = plt.subplots(figsize=(6.2, 2.7))
    fig.subplots_adjust(left=0.34, right=0.94, top=0.90, bottom=0.18)

    colors_bars = [
        COLORS["ink"],
        COLORS["workload"],
        COLORS["evidence"],
        COLORS["designspace"],
        COLORS["constraints"],
    ]

    labels_fmt = [
        r"$\sim 1.5{\times}10^{13}$ Tokens (Llama-3 / RedPajama)",
        r"$\sim 9{\times}10^{11}$ Tokens (The Stack v2 / StarCoder2)",
        r"$\sim 1.3{\times}10^5$ Modules (OpenRTLSet)",
        r"$\sim 10^4$ Layouts (CircuitNet)",
        r"$\sim 1.5{\times}10^3$ QA Pairs (QuArch v0.1)",
    ]

    draw_spectrum_bars(
        ax,
        categories=categories,
        values=tokens,
        labels_fmt=labels_fmt,
        colors=colors_bars,
        height=0.48,
        left=1e2,
        xlim=(1e2, 6e14),
        xlabel="Corpus Scale (log; units differ per tier)",
        threshold_inside=1e10,
        bar_edgecolor=COLORS["note_edge"],
        fontsize=5.8,
    )

    save_figure_bundle(fig, out_plot_ch)
    save_figure_bundle(fig, global_img_base)
    print(
        f"Data Scarcity Spectrum plot saved to '{out_plot_ch}' and '{global_img_base}'"
    )


if __name__ == "__main__":
    main()
