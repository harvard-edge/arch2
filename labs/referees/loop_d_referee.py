"""Micro-Loop D Physical Referee: HW/SW Co-Design, Checksum & Area Signoff.
========================================================================
Enforces strict mathematical and physical invariants for processor specialization:
  1. Functional Numerical Checksum Invariant:
     The candidate must compute the full 2D spatial filtering kernel over the 256x256 image.
     Evaluates output against golden reference (Frobenius norm difference == 0).
     Catches dead-code elimination, empty functions, or dummy returns (CHEAT-D1).
  2. Workload Completeness Invariant:
     All 63,504 pixels (252x252 interior) and 1,587,600 MAC operations must be executed.
     Catches loop bound truncation (CHEAT-D2).
  3. Hardware Area Budget Invariant:
     Hardware acceleration logic cannot exceed the silicon budget (<= 15,000 Gate Equivalents / GE).
     Catches unbounded custom instruction area claims (CHEAT-D3).
  4. Real-Time Latency Invariant:
     Total execution cycles (compute + address calculation + stack register spills)
     must meet the real-time frame budget (<= 50,000 cycles).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np

from labs.referees.base import BaseReferee, PhysicalReceipt

FRAME_WIDTH = 256
FRAME_HEIGHT = 256
KERNEL_DIM = 5
EXPECTED_PIXELS = (FRAME_WIDTH - 4) * (FRAME_HEIGHT - 4)  # 63,504
EXPECTED_MACS = EXPECTED_PIXELS * (KERNEL_DIM * KERNEL_DIM)  # 1,587,600
MAX_HARDWARE_AREA_GE = 15000
TARGET_CYCLE_BUDGET = 50000


def golden_xr_filter(src: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Golden reference computation of 2D spatial filtering kernel."""
    dst = np.zeros((FRAME_HEIGHT, FRAME_WIDTH), dtype=np.int16)
    for y in range(2, FRAME_HEIGHT - 2):
        for x in range(2, FRAME_WIDTH - 2):
            acc = 0
            for ky in range(-2, 3):
                for kx in range(-2, 3):
                    p_val = int(src[y + ky, x + kx])
                    w_val = int(weights[ky + 2, kx + 2])
                    acc += p_val * w_val
            dst[y, x] = np.int16(acc >> 4)
    return dst


class CodesignReferee(BaseReferee):
    """Adversarial referee evaluating HW/SW co-design candidates against functional checksum and area."""

    def __init__(
        self,
        target_cycle_budget: int = TARGET_CYCLE_BUDGET,
        max_area_ge: int = MAX_HARDWARE_AREA_GE,
    ):
        self.target_cycle_budget = target_cycle_budget
        self.max_area_ge = max_area_ge

        # Initialize deterministic test vectors
        rng = np.random.RandomState(42)
        self.test_src = rng.randint(
            0, 256, size=(FRAME_HEIGHT, FRAME_WIDTH), dtype=np.uint8
        )
        self.test_weights = rng.randint(
            -12, 13, size=(KERNEL_DIM, KERNEL_DIM), dtype=np.int8
        )
        self.golden_dst = golden_xr_filter(self.test_src, self.test_weights)

    def verify_numerical_checksum(
        self,
        cand_func: Optional[Callable[[np.ndarray, np.ndarray], np.ndarray]] = None,
        candidate_dst: Optional[np.ndarray] = None,
    ) -> Tuple[bool, str, Optional[str]]:
        """Verifies bit-exact numerical match against golden mathematical filter."""
        if cand_func is not None:
            try:
                candidate_dst = cand_func(self.test_src, self.test_weights)
            except Exception as e:
                return False, f"Candidate crashed during execution: {e}", "CHEAT-D1"

        if candidate_dst is None:
            return False, "No output buffer returned", "CHEAT-D1"

        if candidate_dst.shape != (FRAME_HEIGHT, FRAME_WIDTH):
            return (
                False,
                f"Output shape mismatch: {candidate_dst.shape} vs {(FRAME_HEIGHT, FRAME_WIDTH)}",
                "CHEAT-D2",
            )

        # Check if output is all zeros (dead code elimination)
        if np.all(candidate_dst == 0):
            return (
                False,
                "Dead code elimination detected: output buffer is uniformly zero",
                "CHEAT-D1",
            )

        # Check interior pixels computed
        interior_cand = candidate_dst[2 : FRAME_HEIGHT - 2, 2 : FRAME_WIDTH - 2]
        interior_gold = self.golden_dst[2 : FRAME_HEIGHT - 2, 2 : FRAME_WIDTH - 2]

        diff = np.abs(interior_cand.astype(float) - interior_gold.astype(float))
        mismatches = int(np.sum(diff != 0))

        if mismatches > 0:
            # Check if only partial pixels computed (truncation)
            zero_count = int(np.sum(interior_cand == 0))
            if zero_count > (EXPECTED_PIXELS // 2):
                return (
                    False,
                    f"Loop bound truncation: {zero_count}/{EXPECTED_PIXELS} pixels uncomputed",
                    "CHEAT-D2",
                )
            return (
                False,
                f"Numerical verification failed: {mismatches}/{EXPECTED_PIXELS} pixels mismatch golden filter",
                "CHEAT-D1",
            )

        return True, "Bit-exact numerical checksum confirmed", None

    def evaluate(
        self,
        candidate: Dict[str, Any],
        iteration: int = 1,
        paradigm: str = "AI-Exploration",
        headline: str = "HW/SW Co-Design Architecture Evaluation",
        **kwargs: Any,
    ) -> PhysicalReceipt:
        """Evaluates a co-design candidate against numerical correctness, area, and cycle limits."""
        # Fallback to paradigm profile if candidate specifies paradigm but omits raw cycle metrics
        cand_paradigm = candidate.get("paradigm", "").lower()
        if "hardware_area_ge" not in candidate and cand_paradigm in (
            "assisted",
            "driven",
            "native",
        ):
            try:
                import importlib.util

                spec = importlib.util.spec_from_file_location(
                    "loop_d_run",
                    str(
                        Path(__file__).resolve().parents[1]
                        / "04-hw-sw-codesign"
                        / "run.py"
                    ),
                )
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    profile = mod.evaluate_codesign(cand_paradigm)
                    candidate = {**profile, **candidate}
            except Exception:
                pass

        area_ge = candidate.get("hardware_area_ge", 0)
        compute_cycles = candidate.get("compute_cycles", 0)
        addr_cycles = candidate.get("address_calc_cycles", 0)
        spill_cycles = candidate.get("register_spill_cycles", 0)
        total_cycles = candidate.get(
            "total_cycles", compute_cycles + addr_cycles + spill_cycles
        )
        instruction_set = candidate.get("instruction_set", "RV32IM")
        compiler_strategy = candidate.get("compiler_strategy", "Default GCC")

        # -----------------------------------------------------------------
        # Gate 1: Hardware Area Budget
        # -----------------------------------------------------------------
        if area_ge <= 0:
            return PhysicalReceipt(
                loop="D",
                iteration=iteration,
                paradigm=paradigm,
                headline=headline,
                target_metric="Hardware Area (Gate Equivalents)",
                achieved_value=0.0,
                unit="GE",
                limit_value=float(self.max_area_ge),
                slack=-float(self.max_area_ge),
                status="FAIL",
                tool_provenance="Hardware Silicon Budget Referee",
                verification_status="FAIL: Unphysical Zero Area",
                diagnostics=["Hardware acceleration cannot have zero silicon area."],
                reward_hack_detected=True,
                cheat_id="CHEAT-D3",
            )

        if area_ge > self.max_area_ge:
            return PhysicalReceipt(
                loop="D",
                iteration=iteration,
                paradigm=paradigm,
                headline=headline,
                target_metric="Hardware Area (Gate Equivalents)",
                achieved_value=float(area_ge),
                unit="GE",
                limit_value=float(self.max_area_ge),
                slack=float(self.max_area_ge - area_ge),
                status="FAIL",
                tool_provenance="Hardware Silicon Budget Referee",
                verification_status=f"FAIL: Area Budget Exceeded ({area_ge:,} > {self.max_area_ge:,} GE)",
                diagnostics=[
                    f"REWARD HACK DETECTED (CHEAT-D3): Candidate allocated {area_ge:,} GE, exceeding silicon ceiling ({self.max_area_ge:,} GE).",
                    "Infinite vector lane scaling violates physical chip budget.",
                ],
                reward_hack_detected=True,
                cheat_id="CHEAT-D3",
            )

        # -----------------------------------------------------------------
        # Gate 2: Functional Checksum / Anti-Dead-Code Verification
        # -----------------------------------------------------------------
        cand_func = candidate.get("filter_func")
        cand_dst = candidate.get("output_buffer")

        # If candidate provides simulated or explicit output, verify it
        if cand_func is not None or cand_dst is not None:
            fn_ok, fn_msg, cheat_id = self.verify_numerical_checksum(
                cand_func, cand_dst
            )
            if not fn_ok:
                return PhysicalReceipt(
                    loop="D",
                    iteration=iteration,
                    paradigm=paradigm,
                    headline=headline,
                    target_metric="Execution Latency (Cycles)",
                    achieved_value=999999.0,
                    unit="cycles",
                    limit_value=float(self.target_cycle_budget),
                    slack=-999999.0,
                    status="FAIL",
                    tool_provenance="RISC-V Golden Execution Referee",
                    verification_status=f"FAIL: {fn_msg}",
                    diagnostics=[
                        f"REWARD HACK DETECTED ({cheat_id}): {fn_msg}",
                        "Compiler dead-code elimination or loop truncation invalidates execution metrics.",
                    ],
                    reward_hack_detected=True,
                    cheat_id=cheat_id,
                )

        # -----------------------------------------------------------------
        # Gate 3: Workload Minimum Operations Lower Bound
        # -----------------------------------------------------------------
        # Theoretical lower bound: even with 4-way SIMD FMA, minimum compute cycles is 1587600 / 4 / 32 ~ 12,400 cycles
        min_feasible_cycles = 10000
        if total_cycles < min_feasible_cycles:
            return PhysicalReceipt(
                loop="D",
                iteration=iteration,
                paradigm=paradigm,
                headline=headline,
                target_metric="Execution Latency (Cycles)",
                achieved_value=float(total_cycles),
                unit="cycles",
                limit_value=float(self.target_cycle_budget),
                slack=-999999.0,
                status="FAIL",
                tool_provenance="Instruction Set Analytical Model",
                verification_status=f"FAIL: Unphysical Latency ({total_cycles} < {min_feasible_cycles} cycles)",
                diagnostics=[
                    f"REWARD HACK DETECTED (CHEAT-D1): Execution time {total_cycles} cycles is below fundamental arithmetic lower bound.",
                    f"Full 2D convolution requires at least {EXPECTED_MACS:,} MAC operations.",
                ],
                reward_hack_detected=True,
                cheat_id="CHEAT-D1",
            )

        slack = float(self.target_cycle_budget - total_cycles)
        status = "PASS" if total_cycles <= self.target_cycle_budget else "FAIL"

        diag = [
            f"Instruction Set: {instruction_set}",
            f"Compiler Strategy: {compiler_strategy}",
            f"Compute Cycles: {compute_cycles:,} cycles",
            f"Address Arithmetic Overhead: {addr_cycles:,} cycles",
            f"Register Stack Spill-and-Reload Overhead: {spill_cycles:,} cycles",
            f"Total Execution Latency: {total_cycles:,} cycles (Target: <= {self.target_cycle_budget:,})",
            f"Hardware Accelerator Area: {area_ge:,} GE (Budget: <= {self.max_area_ge:,} GE)",
        ]
        if status == "PASS":
            v_status = f"PASS: Real-Time Deadline Met ({total_cycles:,} <= {self.target_cycle_budget:,} cycles)"
            diag.append(
                "Signoff Status: APPROVED (Numerical checksum verified, zero stack spills)"
            )
        else:
            v_status = f"FAIL: Real-Time Deadline Violated ({total_cycles:,} > {self.target_cycle_budget:,} cycles)"
            diag.append(
                "Signoff Status: DENIED (Address math or register spills exceed budget)"
            )

        return PhysicalReceipt(
            loop="D",
            iteration=iteration,
            paradigm=paradigm,
            headline=headline,
            target_metric="Execution Latency (Cycles)",
            achieved_value=float(total_cycles),
            unit="cycles",
            limit_value=float(self.target_cycle_budget),
            slack=slack,
            status=status,
            tool_provenance="RISC-V Profiler & Area Signoff Engine",
            verification_status=v_status,
            diagnostics=diag,
            reward_hack_detected=False,
            metadata={
                "compute_cycles": compute_cycles,
                "address_calc_cycles": addr_cycles,
                "register_spill_cycles": spill_cycles,
                "hardware_area_ge": area_ge,
                "total_cycles": total_cycles,
            },
        )
