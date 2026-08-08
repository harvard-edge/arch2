"""
Domain Corpus Volume & Data Scarcity Spectrum Plot Script (Chapter 1)

Literature Calibration & Citation Provenance:
---------------------------------------------
1. Natural Language Web Text (~10^13 Tokens): Meta Llama-3 (2024); RedPajama-V2 (Together AI, 2023) [@TogetherAI2023RedPajama].
2. General Software Code (~10^11 Tokens): StarCoder 2 & The Stack v2 (Lozhkov et al., 2024) [@LozhkovEtAl2024TheStackV2].
3. Hardware RTL Code (~10^9 Tokens): OpenRTLSet (Wang et al., 2025) [@WangEtAl2025OpenRTLSet].
4. Curated Architecture Data (~10^9 Tokens): Arch2 Curated Computer Architecture Corpus [@PrakashEtAl2025QuArch].
5. Physical EDA Signoff Traces (~10^7 Records): CircuitNet (Chai et al., 2022) [@ChaiEtAl2022CircuitNet].

Dataset Receipt: book/contents/chapters/01-moonshot/data/fig-architecture-data-scarcity.csv
Output Figure:   book/contents/chapters/01-moonshot/images/fig-architecture-data-scarcity.svg
"""

import csv
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[5]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style


apply_style()


def main():
    chapter_dir = Path(__file__).resolve().parent.parent
    csv_file = chapter_dir / "data" / "fig-architecture-data-scarcity.csv"
    out_plot_ch = chapter_dir / "images" / "fig-architecture-data-scarcity.svg"
    out_plot_global = (
        REPO_ROOT / "book" / "images" / "fig-architecture-data-scarcity.svg"
    )

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
        y_pos[::-1], tokens, color=colors_bars, alpha=0.85, height=0.52, zorder=3
    )
    ax.set_xscale("log")
    ax.set_xlim(1e6, 5e14)
    ax.set_yticks(y_pos[::-1])
    ax.set_yticklabels(categories, fontsize=6.2, fontweight="bold", color=COLORS["ink"])
    ax.set_xlabel(
        "Corpus Volume Scale (Tokens / Records - Log Scale)",
        fontsize=7.0,
        color=COLORS["ink"],
    )
    ax.grid(True, which="both", color=COLORS["grid"], linewidth=0.5, zorder=0)

    labels_fmt = [
        r"$\sim 10^{13}$ Tokens (Llama-3 / RedPajama 3T)",
        r"$\sim 10^{11}$ Tokens (The Stack v2 / StarCoder2)",
        r"$\sim 10^9$ Tokens (OpenRTLSet / Verilog)",
        r"$\sim 10^9$ Tokens (Arch2 Curated 1B Corpus)",
        r"$\sim 10^7$ Records (CircuitNet / OpenROAD)",
    ]

    for bar, val, lbl in zip(bars[::-1], tokens, labels_fmt):
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
    plt.savefig(out_plot_global, dpi=300, bbox_inches="tight")
    print(
        f"Data Scarcity Spectrum plot saved to '{out_plot_ch}' and '{out_plot_global}'"
    )


if __name__ == "__main__":
    main()
