"""Architecture 2.0: Unified Anti-Reward-Hacking Verification Referees.
===================================================================
Master package housing non-bypassable physical verification referees across all 4 micro-loops:
  - Loop A: Systolic Microarchitecture & Workload Conservation (SCALE-Sim)
  - Loop B: RTL Timing Closure & 1,000-Vector Lockstep Equivalence (Yosys + SKY130 + Iverilog)
  - Loop C: Physical Macro Placement, Geometric DRC & 2D RUDY Congestion
  - Loop D: Hardware/Software Co-Design, Numerical Checksum & Area Verification
"""

from __future__ import annotations

from labs.referees.base import BaseReferee, PhysicalReceipt
from labs.referees.loop_a_referee import MicroarchitecturalReferee
from labs.referees.loop_b_referee import RTLVerificationReferee
from labs.referees.loop_c_referee import FloorplanReferee
from labs.referees.loop_d_referee import CodesignReferee

__all__ = [
    "BaseReferee",
    "PhysicalReceipt",
    "MicroarchitecturalReferee",
    "RTLVerificationReferee",
    "FloorplanReferee",
    "CodesignReferee",
]
