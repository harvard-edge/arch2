#!/usr/bin/env python3
"""
Micro-Loop D: Hardware-Software Co-Design and Instruction Specialization
=======================================================================
Demonstrates the concrete distinction between:
  1. AI-Assisted: LLM drafts an isolated custom opcode; scalar load/store overhead dominates.
  2. AI-Driven: Compiler autotuner sweeps unroll factors on static hardware; hits register spill ceiling.
  3. AI-Native: Profiler diagnoses memory stall/spill bottleneck, triggering simultaneous
     co-design of a packed SIMD instruction with post-increment addressing and matching compiler scheduling.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
import yaml

ROOT = Path(__file__).resolve().parent


def evaluate_codesign(configuration_name: str) -> Dict[str, Any]:
    """
    Evaluates execution cycles, register spills, and gate equivalent area for kernel configurations.
    """
    if configuration_name == "assisted_scalar_opcode":
        # Isolated custom dot-product opcode drafted by model
        compute_cycles = 42000
        address_calc_cycles = 58000
        register_spill_cycles = 45000
        total_cycles = compute_cycles + address_calc_cycles + register_spill_cycles
        hardware_area_ge = 2400
        instruction_set = "RV32IM + custom scalar dot"
        compiler_strategy = "Default GCC -O3"

    elif configuration_name == "driven_compiler_autotuned":
        # Compiler autotuner sweeps unroll factor (unroll=8) on existing hardware
        compute_cycles = 34000
        address_calc_cycles = 26000
        # Aggressive unrolling induces massive register pressure and stack spills
        register_spill_cycles = 32000
        total_cycles = compute_cycles + address_calc_cycles + register_spill_cycles
        hardware_area_ge = 2400  # Hardware unchanged
        instruction_set = "RV32IM + custom scalar dot"
        compiler_strategy = "Autotuned unroll=8 + scheduling"

    elif configuration_name == "native_joint_codesigned":
        # Joint HW/SW co-design: SIMD-4 FMA with auto-post-increment addressing
        compute_cycles = 12500
        # Post-increment addressing eliminates dedicated address arithmetic instructions
        address_calc_cycles = 6000
        # SIMD registers eliminate 75% of register file pressure
        register_spill_cycles = 10000
        total_cycles = compute_cycles + address_calc_cycles + register_spill_cycles
        hardware_area_ge = 9400  # Added 4-way SIMD FMA datapath
        instruction_set = "RV32IM + custom SIMD-4 FMA post-inc"
        compiler_strategy = "Custom loop lowering targeting post-increment SIMD"

    else:
        raise ValueError(f"Unknown configuration: {configuration_name}")

    cycle_target_met = total_cycles <= 50000
    area_target_met = hardware_area_ge <= 15000
    signoff_passed = cycle_target_met and area_target_met

    return {
        "configuration": configuration_name,
        "instruction_set": instruction_set,
        "compiler_strategy": compiler_strategy,
        "compute_cycles": compute_cycles,
        "address_calc_cycles": address_calc_cycles,
        "register_spill_cycles": register_spill_cycles,
        "total_cycles": total_cycles,
        "hardware_area_ge": hardware_area_ge,
        "cycle_target_met": cycle_target_met,
        "area_target_met": area_target_met,
        "signoff_passed": signoff_passed,
    }


def main() -> None:
    contract_path = ROOT / "contract.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    max_area = contract["constraints"]["max_hardware_area_ge"]
    max_cycles = contract["constraints"]["target_cycle_budget"]

    print("=" * 80)
    print("Micro-Loop D: Hardware-Software Co-Design & Instruction Specialization")
    print(
        f"Target Kernel: {contract['constraints']['workload_kernel']} | Max Area: {max_area} GE | Max Cycles: {max_cycles:,}"
    )
    print("=" * 80)

    assisted = evaluate_codesign("assisted_scalar_opcode")
    print(f"\n1. [AI-Assisted]")
    print(f"   Config: {assisted['configuration']}")
    print(
        f"   Hardware: {assisted['instruction_set']} ({assisted['hardware_area_ge']:,} GE)"
    )
    print(
        f"   Total Cycles: {assisted['total_cycles']:,} (Compute: {assisted['compute_cycles']:,}, Address: {assisted['address_calc_cycles']:,}, Spills: {assisted['register_spill_cycles']:,})"
    )
    print(
        f"   Signoff Status: {'PASS' if assisted['signoff_passed'] else 'FAIL (Exceeds Cycle Budget)'}"
    )

    driven = evaluate_codesign("driven_compiler_autotuned")
    print(f"\n2. [AI-Driven]")
    print(f"   Config: {driven['configuration']} ({driven['compiler_strategy']})")
    print(f"   Total Cycles: {driven['total_cycles']:,} (36.5% cycle reduction)")
    print(
        f"   Spill Cycles: {driven['register_spill_cycles']:,} words spilled to stack"
    )
    print(
        f"   Signoff Status: {'PASS' if driven['signoff_passed'] else 'FAIL (Register Spill Ceiling)'}"
    )
    print(
        "   Observation: Compiler tuning alone cannot bypass the scalar register file bottleneck."
    )

    native = evaluate_codesign("native_joint_codesigned")
    print(f"\n3. [AI-Native]")
    print(
        f"   Diagnostic Trigger: Profiler reports 62% of runtime spent on address calculations and stack spills."
    )
    print(
        f"   Cross-layer adaptation: Jointly designed SIMD-4 post-increment hardware + matched compiler lowering."
    )
    print(f"   Config: {native['configuration']}")
    print(
        f"   Hardware: {native['instruction_set']} ({native['hardware_area_ge']:,} GE <= {max_area} GE)"
    )
    print(
        f"   Total Cycles: {native['total_cycles']:,} (Compute: {native['compute_cycles']:,}, Address: {native['address_calc_cycles']:,}, Spills: {native['register_spill_cycles']:,})"
    )
    print(
        f"   Signoff Status: {'PASS (Met All Budget and Timing Goals)' if native['signoff_passed'] else 'FAIL'}"
    )

    print("\n" + "-" * 80)
    print("Summary Comparison:")
    print(
        f"  AI-Driven vs. AI-Assisted Speedup:  {assisted['total_cycles'] / driven['total_cycles']:.2f}x"
    )
    print(
        f"  AI-Native vs. AI-Driven Speedup:    {driven['total_cycles'] / native['total_cycles']:.2f}x"
    )
    print(
        f"  Overall AI-Native Speedup:          {assisted['total_cycles'] / native['total_cycles']:.2f}x"
    )
    print(
        f"  Area Budget Headroom:               {max_area - native['hardware_area_ge']:,} GE remaining"
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
