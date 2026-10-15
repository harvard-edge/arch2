"""NanochipLoopRunner: Executable 6-stage Architecture 2.0 loop runner for nanochip.

Supports three execution modes:
  1. `replay`:      Replays the 5-turn Kimi K3 trajectory from `nanochip/trajectories/`
                    with instant integrity verification.
  2. `live-verify`: Runs live EDA/Python referees (`check_integrity.py`, `audit.py`,
                    `roofline.py`, `yosys` + Nangate45 synthesis on `msh_deq.v`, and
                    Verilator + `fxmodel.py` simulation via `evaluate.py`).
  3. `agent`:       Runs the closed-loop 6-stage engine using a pluggable proposer
                    (`reference`, `kimi-k3`, `claude`, `gemini`, `openai`) where each
                    turn's `2. Explore` proposal is conditioned on the prior turn's
                    `5. Interpret` diagnostic return arrow.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from typing import Any, Dict, List, Optional

from .lifecycle import CANONICAL_STAGES, TurnTrajectory
from .proposers import SUPPORTED_PROPOSERS, NanochipProposer
from .referees import (
    RTL_DIR,
    VARIANTS_DIR,
    audit_verilog_file,
    check_deq_bit_exactness,
    check_frozen_integrity,
    run_kpu_evaluate,
    synthesize_module_yosys,
)
from .roofline import evaluate_rooflines

HERE = os.path.dirname(os.path.abspath(__file__))
NANOCHIP_ROOT = os.path.abspath(os.path.join(HERE, ".."))
TRAJECTORIES_DIR = os.path.join(NANOCHIP_ROOT, "trajectories")

TURN_FILES = [
    "turn0_baseline.json",
    "turn1_implement_fault.json",
    "turn2_explore_chaos_stall.json",
    "turn3_formulate_bw_wall.json",
    "turn4_kimi_k3_winner.json",
]


class NanochipLoopRunner:
    """Orchestrates the 6-stage Architecture 2.0 research loop for nanochip."""

    def __init__(self, trajectories_dir: str = TRAJECTORIES_DIR):
        self.trajectories_dir = trajectories_dir

    def load_campaign_summary(self) -> Dict[str, Any]:
        path = os.path.join(self.trajectories_dir, "campaign_summary.json")
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def load_turns(self) -> List[TurnTrajectory]:
        turns: List[TurnTrajectory] = []
        for fn in TURN_FILES:
            p = os.path.join(self.trajectories_dir, fn)
            with open(p, encoding="utf-8") as f:
                turns.append(TurnTrajectory.from_dict(json.load(f)))
        return turns

    def load_turn(self, turn_id: int) -> TurnTrajectory:
        if not (0 <= turn_id < len(TURN_FILES)):
            raise ValueError(
                f"turn_id must be in 0..{len(TURN_FILES) - 1}, got {turn_id}"
            )
        p = os.path.join(self.trajectories_dir, TURN_FILES[turn_id])
        with open(p, encoding="utf-8") as f:
            return TurnTrajectory.from_dict(json.load(f))

    def run_replay(self, turn_id: Optional[int] = None) -> Dict[str, Any]:
        """Replay the 5-turn trajectory (or a single turn) and check frozen harness integrity."""
        t0 = time.time()
        integrity = check_frozen_integrity()
        campaign = self.load_campaign_summary()
        turns = (
            [self.load_turn(turn_id).to_dict()]
            if turn_id is not None
            else [t.to_dict() for t in self.load_turns()]
        )
        return {
            "mode": "replay",
            "canonical_stages": CANONICAL_STAGES,
            "integrity": integrity,
            "campaign_meta": campaign.get("campaign_meta", {}),
            "roofline_summary": campaign.get("roofline_summary", {}),
            "turns": turns,
            "wall_seconds": round(time.time() - t0, 4),
        }

    def run_live_verify(
        self,
        quick: bool = False,
        include_par16_synth: bool = False,
    ) -> Dict[str, Any]:
        """Run live tools (check_integrity, audit, selfmodel, roofline, yosys, evaluate.py)."""
        t0 = time.time()
        integrity = check_frozen_integrity()
        audit_cheat = audit_verilog_file(
            os.path.join(VARIANTS_DIR, "msh_deq_cheat_fread.v"),
            rel_label="rtl/msh_deq.v (cheat variant)",
        )
        audit_clean = audit_verilog_file(
            os.path.join(RTL_DIR, "msh_deq.v"),
            rel_label="rtl/msh_deq.v",
        )
        selfmodel_bad = check_deq_bit_exactness(
            os.path.join(VARIANTS_DIR, "msh_deq_bad_shift.v")
        )
        selfmodel_good = check_deq_bit_exactness(os.path.join(RTL_DIR, "msh_deq.v"))
        rooflines = evaluate_rooflines()
        synth_deq_serial = synthesize_module_yosys(
            os.path.join(RTL_DIR, "msh_deq.v"),
            top_module="msh_deq",
            include_macros=False,
        )
        synth_deq_par16 = (
            synthesize_module_yosys(
                os.path.join(VARIANTS_DIR, "msh_deq_parallel16_demux.v"),
                top_module="msh_deq",
                include_macros=False,
            )
            if include_par16_synth
            else None
        )
        kpu_eval = run_kpu_evaluate(skip_synth=True, quick=quick)

        return {
            "mode": "live-verify",
            "ok": bool(
                integrity["ok"]
                and (not audit_cheat["ok"])
                and audit_clean["ok"]
                and (not selfmodel_bad["bit_exact"])
                and selfmodel_good["bit_exact"]
                and synth_deq_serial["ok"]
                and kpu_eval["ok"]
            ),
            "integrity": integrity,
            "turn1_audit_cheat_caught": audit_cheat,
            "turn1_selfmodel_drift_caught": selfmodel_bad,
            "turn3_roofline_proof": rooflines["co_design_proof"],
            "turn4_msh_deq_yosys": synth_deq_serial,
            "turn2_msh_deq_par16_yosys": synth_deq_par16,
            "turn4_kpu_evaluate": kpu_eval,
            "wall_seconds": round(time.time() - t0, 2),
        }

    def run_agent_loop(
        self,
        proposer_provider: str = "reference",
        live_referees: bool = False,
    ) -> Dict[str, Any]:
        """Run the 5-turn closed loop with a pluggable LLM/reference proposer."""
        t0 = time.time()
        proposer = NanochipProposer(provider=proposer_provider)
        ref_turns = [t.to_dict() for t in self.load_turns()]
        executed_turns: List[Dict[str, Any]] = []
        prior_interp: Optional[Dict[str, Any]] = None

        for idx, ref_t in enumerate(ref_turns):
            prop_out = proposer.propose_turn(
                turn_id=idx,
                reference_turn_data=ref_t,
                prior_interpretation=prior_interp,
            )
            turn_copy = dict(ref_t)
            turn_copy["explore"] = prop_out["proposal"]
            turn_copy["proposer_meta"] = prop_out["proposer_meta"]
            executed_turns.append(turn_copy)
            prior_interp = turn_copy["interpret"]

        live_receipt = self.run_live_verify(quick=True) if live_referees else None
        return {
            "mode": "agent",
            "proposer": {
                "requested_provider": proposer.meta.provider,
                "effective_provider": proposer.meta.effective_provider,
                "model_id": proposer.meta.model_id,
                "api_key_detected": proposer.meta.api_key_detected,
                "fallback_used": proposer.meta.fallback_used,
            },
            "turns": executed_turns,
            "live_receipt": live_receipt,
            "wall_seconds": round(time.time() - t0, 3),
        }


def main():
    ap = argparse.ArgumentParser(
        description="Nanochip Architecture 2.0 6-Stage Loop Runner"
    )
    ap.add_argument(
        "--mode",
        choices=("replay", "live-verify", "agent"),
        default="replay",
        help="Execution mode (default: replay)",
    )
    ap.add_argument(
        "--proposer",
        choices=SUPPORTED_PROPOSERS,
        default="reference",
        help="Stage 2 proposer provider for --mode agent",
    )
    ap.add_argument(
        "--turn", type=int, default=None, help="Specific turn ID (0..4) for replay"
    )
    ap.add_argument(
        "--quick", action="store_true", help="Use quick simulation in live-verify"
    )
    args = ap.parse_args()

    runner = NanochipLoopRunner()
    if args.mode == "replay":
        res = runner.run_replay(turn_id=args.turn)
    elif args.mode == "live-verify":
        res = runner.run_live_verify(quick=args.quick)
    else:
        res = runner.run_agent_loop(proposer_provider=args.proposer)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
