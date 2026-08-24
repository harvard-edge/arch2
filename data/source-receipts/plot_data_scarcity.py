"""
Domain Corpus Volume & Data Scarcity Spectrum Plot Script

Literature Calibration & Citation Provenance:
---------------------------------------------
1. Natural Language Web Text (~10^13 Tokens): Meta Llama-3 (2024); RedPajama-V2 (Together AI, 2023) [@TogetherAI2023RedPajama].
2. General Software Code (~10^11 Tokens): StarCoder 2 & The Stack v2 (Lozhkov et al., 2024) [@LozhkovEtAl2024TheStackV2].
3. Hardware RTL Code (~10^9 Tokens): OpenRTLSet (Wang et al., 2025) [@WangEtAl2025OpenRTLSet].
4. Curated Architecture Data (~10^9 Tokens): Arch2 Curated Computer Architecture Corpus [@PrakashEtAl2025QuArch].
5. Physical EDA Signoff Traces (~10^7 Records): CircuitNet (Chai et al., 2022) [@ChaiEtAl2022CircuitNet].

Dataset Receipt: data/source-receipts/chapter4-data-scarcity-spectrum.csv
Output Figure:   book/images/fig-architecture-data-scarcity.svg
"""

import sys
from pathlib import Path

# Connect parent repo path to import canonical Chapter 4 script
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

ch4_data_dir = (
    REPO_ROOT / "book" / "contents" / "chapters" / "04-representations" / "data"
)
if str(ch4_data_dir) not in sys.path:
    sys.path.insert(0, str(ch4_data_dir))

import plot_architecture_data_scarcity


def main():
    plot_architecture_data_scarcity.main()


if __name__ == "__main__":
    main()
