#!/usr/bin/env python3
"""
Micro-Loop B: RTL Generation, Synthesis, and Timing Closure
==========================================================
Demonstrates the concrete distinction between:
  1. AI-Assisted: Model drafts naive single-cycle RTL; synthesis reports timing violation.
  2. AI-Driven: Synthesis tool flags swept, but cannot break the circular carry-chain dependency.
  3. AI-Native: Negative slack triggers architectural RTL refactoring into carry-save arithmetic,
     verified with automated formal/functional equivalence checks.
"""

from __future__ import annotations

import json
from pathlib import Path
import random
from typing import Any, Dict
import yaml

ROOT = Path(__file__).resolve().parent


def simulate_timing(module_name: str, clock_period_ns: float = 2.0) -> Dict[str, Any]:
    """
    Evaluates timing, logic depth, and area for an accumulator module.
    """
    if module_name == "pe_accumulator_naive":
        # 32-bit ripple carry chain in register feedback loop
        logic_depth = 32
        cell_delay_ns = 0.075
        clk_to_q_ns = 0.12
        setup_margin_ns = 0.08
        datapath_delay_ns = (
            (logic_depth * cell_delay_ns) + clk_to_q_ns + setup_margin_ns
        )
        gate_count = 520
        slack_ns = clock_period_ns - datapath_delay_ns

    elif module_name == "pe_accumulator_naive_tuned":
        # AI-Driven tool tuning: high-effort logic restructuring & sizing
        logic_depth = 26
        cell_delay_ns = 0.072
        clk_to_q_ns = 0.12
        setup_margin_ns = 0.08
        datapath_delay_ns = (
            (logic_depth * cell_delay_ns) + clk_to_q_ns + setup_margin_ns
        )
        gate_count = 680
        slack_ns = clock_period_ns - datapath_delay_ns

    elif module_name == "pe_accumulator_carry_save":
        # AI-Native carry-save arithmetic: single FA delay in feedback path
        logic_depth = 1
        cell_delay_ns = 0.35
        clk_to_q_ns = 0.12
        setup_margin_ns = 0.08
        datapath_delay_ns = (
            (logic_depth * cell_delay_ns) + clk_to_q_ns + setup_margin_ns
        )
        gate_count = 860
        slack_ns = clock_period_ns - datapath_delay_ns

    else:
        raise ValueError(f"Unknown module: {module_name}")

    return {
        "module": module_name,
        "clock_period_ns": clock_period_ns,
        "datapath_delay_ns": round(datapath_delay_ns, 3),
        "slack_ns": round(slack_ns, 3),
        "timing_passed": slack_ns >= 0.0,
        "gate_count": gate_count,
    }


def verify_equivalence(num_vectors: int = 1000) -> bool:
    """
    Verifies that redundant carry-save accumulator outputs match the naive golden model.
    """
    random.seed(42)
    golden_acc = 0
    csa_sum = 0
    csa_carry = 0

    for _ in range(num_vectors):
        val = random.randint(0, 0xFFFF)
        # Golden reference (32-bit wrap)
        golden_acc = (golden_acc + val) & 0xFFFFFFFF

        # Bitwise full adder
        s = csa_sum ^ csa_carry ^ val
        c = (csa_sum & csa_carry) | (csa_carry & val) | (csa_sum & val)

        csa_sum = s & 0xFFFFFFFF
        csa_carry = (c << 1) & 0xFFFFFFFF

    # Final resolve
    resolved = (csa_sum + csa_carry) & 0xFFFFFFFF
    return resolved == golden_acc


def main() -> None:
    contract_path = ROOT / "contract.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    period = contract["constraints"]["clock_period_ns"]

    print("=" * 80)
    print("Micro-Loop B: RTL Generation, Synthesis & Timing Closure")
    print(
        f"Target Clock: {contract['constraints']['target_frequency_mhz']} MHz ({period} ns period) | Max Gates: {contract['constraints']['max_gate_count']}"
    )
    print("=" * 80)

    # 1. AI-Assisted
    assisted = simulate_timing("pe_accumulator_naive", period)
    print(f"\n1. [AI-Assisted]")
    print(f"   Module: {assisted['module']} (Drafted by model)")
    print(
        f"   Delay: {assisted['datapath_delay_ns']} ns | Slack: {assisted['slack_ns']:+.3f} ns"
    )
    print(
        f"   Timing Status: {'PASS' if assisted['timing_passed'] else 'FAIL (Negative Setup Slack)'}"
    )

    # 2. AI-Driven
    driven = simulate_timing("pe_accumulator_naive_tuned", period)
    print(f"\n2. [AI-Driven]")
    print(
        f"   Module: {driven['module']} (Synthesis flags swept: high effort, gate sizing)"
    )
    print(
        f"   Delay: {driven['datapath_delay_ns']} ns | Slack: {driven['slack_ns']:+.3f} ns"
    )
    print(
        f"   Timing Status: {'PASS' if driven['timing_passed'] else 'FAIL (Negative Setup Slack)'}"
    )
    print(
        "   Observation: Synthesis tools cannot break the 32-bit feedback carry loop without RTL redesign."
    )

    # 3. AI-Native
    native = simulate_timing("pe_accumulator_carry_save", period)
    equiv_ok = verify_equivalence(1000)
    native["equivalence_passed"] = equiv_ok
    print(f"\n3. [AI-Native]")
    print(f"   Diagnostic Trigger: Setup timing failure on carry propagation chain.")
    print(
        f"   Cross-layer adaptation: Refactored RTL to redundant carry-save datapath."
    )
    print(f"   Module: {native['module']}")
    print(
        f"   Delay: {native['datapath_delay_ns']} ns | Slack: {native['slack_ns']:+.3f} ns"
    )
    print(f"   Timing Status: {'PASS' if native['timing_passed'] else 'FAIL'}")
    print(
        f"   Formal/Functional Equivalence Check: {'PASS (1,000 vectors matched)' if equiv_ok else 'FAIL'}"
    )
    print(
        f"   Gate Count: {native['gate_count']} GE (Budget: {contract['constraints']['max_gate_count']})"
    )

    print("\n" + "-" * 80)
    print(f"Summary Comparison:")
    print(
        f"  AI-Driven Slack Delta:  {driven['slack_ns'] - assisted['slack_ns']:+.3f} ns (Synthesis tuning alone)"
    )
    print(
        f"  AI-Native Slack Delta:  {native['slack_ns'] - assisted['slack_ns']:+.3f} ns (Microarchitectural RTL refactor)"
    )
    print(
        f"  Timing Signoff:         {'ACHIEVED' if native['timing_passed'] else 'UNRESOLVED'}"
    )
    print("-" * 80)

    out_file = ROOT / "results.json"
    results = {
        "assisted": assisted,
        "driven": driven,
        "native": native,
    }
    out_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Structured results written to {out_file.name}")


if __name__ == "__main__":
    main()
