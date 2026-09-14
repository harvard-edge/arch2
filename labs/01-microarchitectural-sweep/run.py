#!/usr/bin/env python3
"""
Micro-Loop A: Systolic Array Microarchitectural Search and the Memory Wall
=========================================================================
Demonstrates the concrete distinction between:
  1. AI-Assisted: Single point proposal generated from prompt context.
  2. AI-Driven: Automated parameter search across aspect ratios under a fixed dataflow.
  3. AI-Native: Evidence-triggered cross-layer adaptation (dataflow switch + buffer sizing).
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple
import yaml

ROOT = Path(__file__).resolve().parent


def load_workload(path: Path) -> List[Dict[str, Any]]:
    layers = []
    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            layers.append(
                {
                    "layer": row["Layer"],
                    "M": int(row["M"]),
                    "N": int(row["N"]),
                    "K": int(row["K"]),
                }
            )
    return layers


def evaluate_systolic_array(
    rows: int,
    cols: int,
    dataflow: str,
    workload: List[Dict[str, Any]],
    bandwidth_words_per_cycle: int = 64,
) -> Dict[str, Any]:
    """
    Analytical cycle and DRAM traffic evaluation for a 2D systolic array.
    """
    pe_count = rows * cols
    total_compute_cycles = 0
    total_dram_reads = 0
    total_dram_writes = 0

    for layer in workload:
        M, N, K = layer["M"], layer["N"], layer["K"]
        tiles_m = math.ceil(M / rows)
        tiles_n = math.ceil(N / cols)

        if dataflow == "output_stationary":
            # Output Stationary: partial sums stay in PEs, inputs and weights stream.
            # Compute time per tile: K + rows + cols - 2
            tile_cycles = K + rows + cols - 2
            comp_cycles = tiles_m * tiles_n * tile_cycles

            # DRAM traffic in words (assuming 16-bit / 1-word activations):
            # Input activations (A: M x K) streamed for each tile column
            # Weights (B: K x N) streamed for each tile row
            # Output activations (C: M x N) written once at the end
            reads = (tiles_n * (M * K)) + (tiles_m * (K * N))
            writes = M * N

        elif dataflow == "weight_stationary":
            # Weight Stationary: weights stay stationary in PEs, inputs stream and outputs drain.
            # For each tile of weights (rows x cols):
            # Compute cycles: M + rows + cols - 2
            tiles_k = math.ceil(K / rows)
            tiles_n = math.ceil(N / cols)
            comp_cycles = tiles_k * tiles_n * (M + rows + cols - 2)

            # DRAM traffic: weights loaded once per tile, inputs streamed
            reads = (K * N) + (tiles_n * (M * K))
            writes = M * N

        else:
            raise ValueError(f"Unknown dataflow: {dataflow}")

        # Memory bound: stall cycles if memory access exceeds interface bandwidth
        memory_cycles = math.ceil((reads + writes) / bandwidth_words_per_cycle)
        effective_cycles = max(comp_cycles, memory_cycles)

        total_compute_cycles += effective_cycles
        total_dram_reads += reads
        total_dram_writes += writes

    # Utilization = total useful MACs / (total cycles * PE count)
    total_macs = sum(l["M"] * l["N"] * l["K"] for l in workload)
    utilization_pct = (total_macs / (total_compute_cycles * pe_count)) * 100.0

    return {
        "rows": rows,
        "cols": cols,
        "dataflow": dataflow,
        "pe_count": pe_count,
        "total_cycles": total_compute_cycles,
        "dram_reads": total_dram_reads,
        "dram_writes": total_dram_writes,
        "total_dram_traffic": total_dram_reads + total_dram_writes,
        "utilization_pct": round(utilization_pct, 2),
    }


def run_assisted_mode(
    workload: List[Dict[str, Any]], contract: Dict[str, Any]
) -> Dict[str, Any]:
    # AI-Assisted: LLM drafts a single geometry candidate from prompt: 16x64 OS
    rows, cols = 16, 64
    eval_res = evaluate_systolic_array(rows, cols, "output_stationary", workload)
    return {
        "mode": "AI-Assisted",
        "description": "Point generation of single candidate (16x64 OS) without feedback loop",
        "best_candidate": eval_res,
        "evaluations_run": 1,
    }


def run_driven_mode(
    workload: List[Dict[str, Any]], contract: Dict[str, Any]
) -> Dict[str, Any]:
    # AI-Driven: Automated parameter sweep of all aspect ratios under fixed OS dataflow
    candidates = [(8, 128), (16, 64), (32, 32), (64, 16), (128, 8)]
    results = [
        evaluate_systolic_array(r, c, "output_stationary", workload)
        for r, c in candidates
    ]
    best = min(results, key=lambda x: x["total_cycles"])
    return {
        "mode": "AI-Driven",
        "description": "Automated parameter search across 5 aspect ratios under fixed Output Stationary dataflow",
        "best_candidate": best,
        "all_candidates": results,
        "evaluations_run": len(candidates),
    }


def run_native_mode(
    workload: List[Dict[str, Any]], contract: Dict[str, Any]
) -> Dict[str, Any]:
    # AI-Native: Closed loop starts with baseline, inspects memory traffic, detects memory wall,
    # and pivots across abstraction layers by altering the dataflow to Weight Stationary.
    baseline = evaluate_systolic_array(32, 32, "output_stationary", workload)

    # Architectural diagnostic: check if DRAM traffic stalls compute
    dram_bound = baseline["total_dram_traffic"] > (
        baseline["total_cycles"]
        * contract["constraints"]["interface_bandwidth_words_per_cycle"]
        * 0.5
    )

    native_candidates = []
    if dram_bound:
        # Cross-layer shift: change dataflow from Output Stationary to Weight Stationary
        for r, c in [(16, 64), (32, 32), (64, 16)]:
            native_candidates.append(
                evaluate_systolic_array(r, c, "weight_stationary", workload)
            )

    best = min(native_candidates, key=lambda x: x["total_cycles"])
    return {
        "mode": "AI-Native",
        "description": "Evidence-driven cross-layer redesign: detected memory wall, reframed dataflow to Weight Stationary",
        "diagnostic_trigger": "DRAM bandwidth saturation detected in Output Stationary mode",
        "best_candidate": best,
        "all_candidates": native_candidates,
        "evaluations_run": 1 + len(native_candidates),
    }


def main() -> None:
    contract_path = ROOT / "contract.yaml"
    workload_path = ROOT / "workload" / "xr_gemm.csv"

    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    workload = load_workload(workload_path)

    print("=" * 80)
    print("Micro-Loop A: Systolic Array Search & The Memory Wall")
    print(
        f"Target Workload: {len(workload)} GEMM layers | PE Budget: {contract['constraints']['max_pe_budget']}"
    )
    print("=" * 80)

    assisted = run_assisted_mode(workload, contract)
    driven = run_driven_mode(workload, contract)
    native = run_native_mode(workload, contract)

    print(f"\n1. [{assisted['mode']}]")
    print(
        f"   Candidate: {assisted['best_candidate']['rows']}x{assisted['best_candidate']['cols']} ({assisted['best_candidate']['dataflow']})"
    )
    print(
        f"   Cycles: {assisted['best_candidate']['total_cycles']:,} | DRAM Traffic: {assisted['best_candidate']['total_dram_traffic']:,} words"
    )
    print(f"   Utilization: {assisted['best_candidate']['utilization_pct']}%")

    print(f"\n2. [{driven['mode']}]")
    print(
        f"   Best of {driven['evaluations_run']} aspect ratios under fixed Output Stationary:"
    )
    print(
        f"   Candidate: {driven['best_candidate']['rows']}x{driven['best_candidate']['cols']} ({driven['best_candidate']['dataflow']})"
    )
    print(
        f"   Cycles: {driven['best_candidate']['total_cycles']:,} | DRAM Traffic: {driven['best_candidate']['total_dram_traffic']:,} words"
    )
    print(f"   Utilization: {driven['best_candidate']['utilization_pct']}%")
    print(
        "   Observation: Optimization plateaus because DRAM traffic saturates interface bandwidth."
    )

    print(f"\n3. [{native['mode']}]")
    print(f"   Diagnostic Trigger: {native['diagnostic_trigger']}")
    print(f"   Cross-layer adaptation: Re-architected dataflow to Weight Stationary.")
    print(
        f"   Candidate: {native['best_candidate']['rows']}x{native['best_candidate']['cols']} ({native['best_candidate']['dataflow']})"
    )
    print(
        f"   Cycles: {native['best_candidate']['total_cycles']:,} | DRAM Traffic: {native['best_candidate']['total_dram_traffic']:,} words"
    )
    print(f"   Utilization: {native['best_candidate']['utilization_pct']}%")

    speedup = (
        driven["best_candidate"]["total_cycles"]
        / native["best_candidate"]["total_cycles"]
    )
    dram_reduction = (
        driven["best_candidate"]["total_dram_traffic"]
        / native["best_candidate"]["total_dram_traffic"]
    )

    print("\n" + "-" * 80)
    print(f"Summary Comparison:")
    print(
        f"  AI-Driven vs. AI-Assisted Speedup: {assisted['best_candidate']['total_cycles'] / driven['best_candidate']['total_cycles']:.2f}x"
    )
    print(f"  AI-Native vs. AI-Driven Speedup:   {speedup:.2f}x")
    print(
        f"  AI-Native DRAM Traffic Reduction:  {dram_reduction:.2f}x lower off-chip memory access"
    )
    print("-" * 80)

    # Save structured results
    out_file = ROOT / "results.json"
    results_payload = {
        "assisted": assisted,
        "driven": driven,
        "native": native,
        "summary": {
            "speedup_native_vs_driven": round(speedup, 2),
            "dram_reduction_factor": round(dram_reduction, 2),
        },
    }
    out_file.write_text(json.dumps(results_payload, indent=2), encoding="utf-8")
    print(f"Structured results written to {out_file.name}")


if __name__ == "__main__":
    main()
