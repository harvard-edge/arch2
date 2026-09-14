#!/usr/bin/env python3
"""Architecture 2.0: Physical Verification Referee.
===================================================
An adversarial, non-bypassable verification harness that evaluates candidate
hardware blocks produced by human or AI agents.

Enforces three strict physical invariants:
  1. Module Contract Invariant:
     Candidate must preserve exact pinout and port semantics.
  2. Functional Invariant (Anti-Reward Hacking):
     Candidate is simulated in lockstep with the golden specification over 1,000
     vectors including harsh corner cases and interleaved idle cycles.
     Any cycle mismatch or static/stuck-at tie-off triggers immediate hard rejection.
  3. Physical Synthesis & Timing Invariant:
     Timing slack is evaluated via real standard-cell mapping (Yosys + SKY130).
     Comments are stripped prior to parsing to prevent comment-injection attacks.
     Timing slack is marked INVALID if functional verification fails.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from labs.referees.base import BaseReferee, PhysicalReceipt
from labs.referees.loop_b_referee import RTLVerificationReferee, strip_verilog_comments

ROOT = Path(__file__).resolve().parent
RTL_DIR = ROOT / "02-rtl-timing" / "rtl"


class PhysicalVerificationReferee(RTLVerificationReferee):
    """Backward-compatible alias for RTLVerificationReferee."""

    pass


__all__ = [
    "BaseReferee",
    "PhysicalReceipt",
    "PhysicalVerificationReferee",
    "RTLVerificationReferee",
    "strip_verilog_comments",
]
