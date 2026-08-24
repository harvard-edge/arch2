"""
Physical Signoff Verification Funnel Plot Script

Literature Calibration & Citation Provenance:
---------------------------------------------
1. Stage 1 (Syntactic & AST Parsing - 72.4% pass): VerilogEval (Liu et al., 2023) [@LiuEtAl2023VerilogEval].
2. Stage 2 (Interface & Interconnect Schema - 38.1% pass): RTLLM (Lu et al., 2024) [@LuEtAl2024RTLLM].
3. Stage 3 (Functional Simulation & SVA Assertions - 14.6% pass): OpenRTLSet (Wang et al., 2025) [@WangEtAl2025OpenRTLSet].
4. Stage 4 (Static Timing Closure WNS >= 0ns - 3.8% pass): AgentDSE (Wang et al., 2026) [@WangEtAl2026AgentDSE].
5. Stage 5 (Physical Place & Route DRC Closure - 59.5% pass / 0.09% yield): AutoDSE (Zhang et al., 2022) [@ZhangEtAl2022AutoDSE] on OpenROAD 7nm ASAP7.

Dataset Receipt: data/source-receipts/chapter4-physical-verification-funnel.csv
Output Figure:   book/images/fig-synthesis-verification-funnel.svg
"""

import sys
from pathlib import Path

# Connect parent repo path to import canonical Chapter 7 script
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

ch7_data_dir = REPO_ROOT / "book" / "contents" / "chapters" / "07-feedback" / "data"
if str(ch7_data_dir) not in sys.path:
    sys.path.insert(0, str(ch7_data_dir))

import plot_synthesis_verification_funnel


def main():
    plot_synthesis_verification_funnel.main()


if __name__ == "__main__":
    main()
