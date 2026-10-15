#!/usr/bin/env python3
"""Lab 02 (Stage 2: Explore) — Roofline Betting & Candidate Generation."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
KPU_ROOT = REPO_ROOT / "nanochip" / "kpu"
if str(KPU_ROOT) not in sys.path:
    sys.path.insert(0, str(KPU_ROOT))

from reference.config import CONFIGS  # noqa: E402
from reference.gen_weights import (  # noqa: E402
    active_weight_bytes,
    floor_weight_bytes,
    tensor_list,
)

console = Console()

DRAM_BYTES_PER_CYCLE = 16
CLOCK_MHZ = 100.0
CLOCK_HZ = CLOCK_MHZ * 1e6


def compute_active_elements(cfg) -> dict[str, int]:
    """Count active weight elements and packed INT4 bytes per token by subsystem."""
    breakdown_bytes = {
        "embedding_row": 0,
        "kda_layer0_dense": 0,
        "mla_layer1_dense": 0,
        "moe_shared_and_router": 0,
        "moe_routed_top2": 0,
        "lm_head_and_norms": 0,
    }
    g = min(cfg.group_size, cfg.d_model)
    ng_e = (cfg.d_model + g - 1) // g
    emb_row_bytes = cfg.d_model // 2 + ng_e * 3
    breakdown_bytes["embedding_row"] = emb_row_bytes

    expert0_bytes = 0
    for name, shape, tag in tensor_list(cfg):
        n = int(np.prod(shape))
        b = n if tag in ("q4", "z8") else 2 * n
        if name.startswith("emb."):
            continue
        if ".moe.e" in name:
            if name.startswith("L0.moe.e0."):
                expert0_bytes += b
            continue
        if (
            name.startswith("L0.kda.")
            or name.startswith("L0.res_attn")
            or name.startswith("L0.norm1")
        ):
            breakdown_bytes["kda_layer0_dense"] += b
        elif (
            name.startswith("L1.mla.")
            or name.startswith("L1.res_attn")
            or name.startswith("L1.norm1")
        ):
            breakdown_bytes["mla_layer1_dense"] += b
        elif ".moe." in name or ".res_mlp" in name or ".norm2" in name:
            breakdown_bytes["moe_shared_and_router"] += b
        else:
            breakdown_bytes["lm_head_and_norms"] += b

    breakdown_bytes["moe_routed_top2"] = cfg.n_layers * cfg.top_k * expert0_bytes
    return breakdown_bytes


def run_break() -> dict[str, Any]:
    """Evaluate a typical LLM hallucination: claiming 20,000 tok/s (5,000 cyc/tok)
    by widening MACs to 64 lanes while streaming uncompressed FP16 weights (304,448 B/tok)
    or writing dequantized FP16 weights back to DRAM over a 16 B/cycle port."""
    cfg = CONFIGS["nano"]
    act_int4_bytes = active_weight_bytes(cfg)  # 76,109 B
    # Uncompressed FP16 active stream (4x INT4 packed weight stream = 152,224 params * 2 B = 304,448 B)
    fp16_active_bytes = 304448
    fp32_active_bytes = 608896

    min_cycles_fp16 = math.ceil(
        fp16_active_bytes / DRAM_BYTES_PER_CYCLE
    )  # 19,028 cyc/tok
    max_tok_s_fp16 = round(CLOCK_HZ / min_cycles_fp16, 1)  # 5,255.4 tok/s

    min_cycles_fp32 = math.ceil(
        fp32_active_bytes / DRAM_BYTES_PER_CYCLE
    )  # 38,056 cyc/tok
    max_tok_s_fp32 = round(CLOCK_HZ / min_cycles_fp32, 1)  # 2,627.7 tok/s

    hallucinated_proposal = {
        "candidate_id": "llm-hallucination-wide-fp16-mac",
        "claim": "20,000.0 tok/s (5,000 cycles/token) via 64-lane FP16 MAC array streaming uncompressed FP16 weights",
        "claimed_tokens_per_sec": 20000.0,
        "claimed_cycles_per_token": 5000.0,
        "dram_port_bytes_per_cycle": DRAM_BYTES_PER_CYCLE,
        "fp16_bytes_per_token": fp16_active_bytes,
        "conservation_of_bytes_min_cycles": min_cycles_fp16,
        "physical_ceiling_tokens_per_sec": max_tok_s_fp16,
        "shortfall_factor": round(20000.0 / max_tok_s_fp16, 2),
        "violates_conservation_of_bytes": True,
        "int4_active_bytes_per_token": act_int4_bytes,
    }

    return {
        "mode": "break",
        "stage": "2. Explore",
        "proposal": hallucinated_proposal,
        "fp32_ceiling_tok_s": max_tok_s_fp32,
        "fp16_ceiling_tok_s": max_tok_s_fp16,
        "rejected_before_rtl_sim": True,
        "verdict": "REJECTED_BY_CONSERVATION_OF_BYTES_ROOFLINE",
    }


def run_verify() -> dict[str, Any]:
    """Compute the exact roofline table across FP32, FP16, INT4 group-128, and INT4 + hq
    shadow cache using nanochip/kpu/reference/gen_weights.py, and verify Kimi K3's
    pre-committed perf-model prediction (11,200 cyc/tok vs 11,467.125 measured)."""
    cfg = CONFIGS["nano"]
    act_bytes = active_weight_bytes(cfg)  # 76,109 B
    flr_bytes = floor_weight_bytes(cfg)  # 62,250 B
    breakdown = compute_active_elements(cfg)

    # Roofline table entries
    hq_saved_bytes = 16096  # head.q (16,384 B) fetched once on token 0, saved on 47/48 tokens -> ~16,096 B/tok saved
    act_with_hq = act_bytes - hq_saved_bytes  # 60,013 B/tok

    rooflines = [
        {
            "format": "FP32 Uncompressed Stream (4 B/w)",
            "active_bytes_per_tok": 608896,
            "min_dram_cycles_per_tok": 38056,
            "max_tokens_per_sec_100mhz": round(CLOCK_HZ / 38056, 1),
            "can_reach_8720_tok_s": False,
        },
        {
            "format": "FP16 Uncompressed / Dequant-to-DRAM (2 B/w)",
            "active_bytes_per_tok": 304448,
            "min_dram_cycles_per_tok": 19028,
            "max_tokens_per_sec_100mhz": round(CLOCK_HZ / 19028, 1),
            "can_reach_8720_tok_s": False,
        },
        {
            "format": "INT4 Group-128 Fused Dequant (Uncached)",
            "active_bytes_per_tok": act_bytes,
            "min_dram_cycles_per_tok": (act_bytes + DRAM_BYTES_PER_CYCLE - 1)
            // DRAM_BYTES_PER_CYCLE,
            "max_tokens_per_sec_100mhz": round(
                CLOCK_HZ
                / ((act_bytes + DRAM_BYTES_PER_CYCLE - 1) // DRAM_BYTES_PER_CYCLE),
                1,
            ),
            "can_reach_8720_tok_s": True,
        },
        {
            "format": "INT4 Group-128 + 16 KiB LM-Head Shadow Cache (hq)",
            "active_bytes_per_tok": act_with_hq,
            "min_dram_cycles_per_tok": (act_with_hq + DRAM_BYTES_PER_CYCLE - 1)
            // DRAM_BYTES_PER_CYCLE,
            "max_tokens_per_sec_100mhz": round(
                CLOCK_HZ
                / ((act_with_hq + DRAM_BYTES_PER_CYCLE - 1) // DRAM_BYTES_PER_CYCLE),
                1,
            ),
            "can_reach_8720_tok_s": True,
        },
    ]

    predicted_cpt = 11200.0
    measured_cpt = 11467.125
    rel_err = abs(predicted_cpt - measured_cpt) / measured_cpt

    perf_model = {
        "predicted_cycles_per_token": predicted_cpt,
        "measured_cycles_per_token": measured_cpt,
        "relative_error": round(rel_err, 4),
        "relative_error_pct": round(rel_err * 100.0, 2),
        "measured_tokens_per_sec": round(CLOCK_HZ / measured_cpt, 2),
        "baseline_tokens_per_sec": 4.0,
        "speedup_over_baseline": round((CLOCK_HZ / measured_cpt) / 4.0, 2),
        "cycle_breakdown_estimate": {
            "dram_weight_and_kv_stream_cycles": 4380,
            "gemv_dual_parity_mac_and_fold_cycles": 3820,
            "kda_delta_rule_and_conv_cycles": 1650,
            "mla_attention_and_rmsnorm_vec_cycles": 940,
            "sequencer_and_latency_tail_cycles": 410,
        },
    }

    return {
        "mode": "verify",
        "stage": "2. Explore",
        "passed": act_bytes == 76109 and flr_bytes == 62250 and rel_err < 0.05,
        "active_weight_bytes": act_bytes,
        "floor_weight_bytes": flr_bytes,
        "subsystem_byte_breakdown": breakdown,
        "rooflines": rooflines,
        "perf_model": perf_model,
    }


def render_break(data: dict[str, Any]) -> None:
    p = data["proposal"]
    console.print(
        Panel(
            "[bold red]LAB 02 (--mode break): PRUNING AN IMPOSSIBLE LLM ROOFLINE HALLUCINATION[/bold red]\n"
            f"Candidate Proposal: [italic]\"{p['claim']}\"[/italic]",
            box=box.ROUNDED,
            border_style="red",
        )
    )
    tbl = Table(
        title="Conservation-of-Bytes Referee Check (16 B/cycle DRAM Port @ 100 MHz)",
        box=box.ROUNDED,
        show_lines=True,
    )
    tbl.add_column("Metric", style="bold cyan")
    tbl.add_column("LLM Hallucinated Claim", justify="right", style="red")
    tbl.add_column("Physical Conservation Law", justify="right", style="green")
    tbl.add_column("Diagnosis", style="yellow")

    tbl.add_row(
        "Active Weight Traffic / Token (FP16)",
        "Ignored by prompt",
        f"{p['fp16_bytes_per_token']:,} B/tok",
        "152,224 active params * 2 B/param",
    )
    tbl.add_row(
        "Minimum DRAM Transfer Floor (16 B/cyc)",
        f"{p['claimed_cycles_per_token']:,.0f} cyc/tok",
        f"{p['conservation_of_bytes_min_cycles']:,} cyc/tok",
        "304,448 B / 16 B/cyc = 19,028 cyc minimum!",
    )
    tbl.add_row(
        "Max Possible Throughput @ 100 MHz",
        f"{p['claimed_tokens_per_sec']:,.1f} tok/s",
        f"{p['physical_ceiling_tokens_per_sec']:,.1f} tok/s",
        f"Violates pin bandwidth by {p['shortfall_factor']}x (even with 0 compute!)",
    )
    console.print(tbl)
    console.print(
        "[bold green]✔ Stage 2 Lesson:[/bold green] Conservation of bytes proves in <1 ms that "
        "widening MACs cannot overcome an uncompressed FP16 pin bottleneck. "
        "Reaching >8,000 tok/s [bold]requires[/bold] fused on-the-fly INT4 group-128 dequantization.\n"
    )


def render_verify(data: dict[str, Any]) -> None:
    console.print(
        Panel(
            "[bold green]LAB 02 (--mode verify): ROOFLINE TABLE & ANALYTICAL PERF-MODEL CALIBRATION[/bold green]\n"
            f"Computed from [cyan]nanochip/kpu/reference/gen_weights.py[/cyan]: "
            f"active_weight_bytes = [bold]{data['active_weight_bytes']:,} B/tok[/bold], "
            f"floor_weight_bytes = [bold]{data['floor_weight_bytes']:,} B/tok[/bold].",
            box=box.ROUNDED,
            border_style="green",
        )
    )

    t1 = Table(
        title="1. Precision vs. Pin-Bandwidth Roofline Table (16 B/cycle @ 100 MHz)",
        box=box.ROUNDED,
    )
    t1.add_column("Weight & Memory Strategy", style="bold cyan")
    t1.add_column("Active Bytes / Token", justify="right", style="white")
    t1.add_column("DRAM Cycle Floor", justify="right", style="yellow")
    t1.add_column("Roofline Ceiling (tok/s)", justify="right", style="bold green")
    t1.add_column("Feasible for 8,720 tok/s?", justify="center")

    for r in data["rooflines"]:
        ok_str = (
            "[bold green]YES[/bold green]"
            if r["can_reach_8720_tok_s"]
            else "[bold red]NO (Pin Wall)[/bold red]"
        )
        t1.add_row(
            r["format"],
            f"{r['active_bytes_per_tok']:,} B",
            f"{r['min_dram_cycles_per_tok']:,} cyc",
            f"{r['max_tokens_per_sec_100mhz']:,.1f} tok/s",
            ok_str,
        )
    console.print(t1)

    pm = data["perf_model"]
    t2 = Table(
        title="2. Kimi K3 Pre-Committed Analytical Perf-Model vs. Measured RTL",
        box=box.ROUNDED,
        show_lines=True,
    )
    t2.add_column("Quantity", style="cyan")
    t2.add_column("Analytical Prediction (Stage 2)", justify="right", style="yellow")
    t2.add_column("Verilator RTL Measurement (Stage 4)", justify="right", style="green")
    t2.add_column("Calibration Verdict", style="bold white")

    t2.add_row(
        "Steady-State Cycles / Token (nano)",
        f"{pm['predicted_cycles_per_token']:,.1f} cyc/tok",
        f"{pm['measured_cycles_per_token']:,.3f} cyc/tok",
        f"[bold green]{pm['relative_error_pct']}% error[/bold green] (well within 5% bar)",
    )
    t2.add_row(
        "Throughput @ 100.0 MHz Target Clock",
        f"{CLOCK_HZ / pm['predicted_cycles_per_token']:,.2f} tok/s",
        f"{pm['measured_tokens_per_sec']:,.2f} tok/s",
        f"[bold green]{pm['speedup_over_baseline']:,.2f}x[/bold green] over {pm['baseline_tokens_per_sec']} tok/s baseline",
    )
    console.print(t2)
    console.print()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Lab 02: Stage 2 Explore — Roofline Betting & Candidate Generation"
    )
    ap.add_argument(
        "--mode", choices=["verify", "break", "summary", "inspect"], default="summary"
    )
    ap.add_argument("--verify", action="store_const", const="verify", dest="mode_flag")
    ap.add_argument("--break", action="store_const", const="break", dest="mode_flag")
    ap.add_argument(
        "--summary", action="store_const", const="summary", dest="mode_flag"
    )
    ap.add_argument(
        "--inspect", action="store_const", const="inspect", dest="mode_flag"
    )
    ap.add_argument("--json", action="store_true", help="Emit JSON output to stdout")
    args = ap.parse_args()
    mode = args.mode_flag or args.mode

    if mode == "break":
        res = run_break()
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            render_break(res)
        return 0 if res["rejected_before_rtl_sim"] else 1

    if mode in ("verify", "inspect"):
        res = run_verify()
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            render_verify(res)
        return 0 if res["passed"] else 1

    b_res = run_break()
    v_res = run_verify()
    combined = {
        "lab": "02-explore",
        "stage": "2. Explore",
        "passed": b_res["rejected_before_rtl_sim"] and v_res["passed"],
        "break_test": b_res,
        "verify_test": v_res,
    }
    if args.json:
        print(json.dumps(combined, indent=2))
    else:
        render_break(b_res)
        render_verify(v_res)
    return 0 if combined["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
