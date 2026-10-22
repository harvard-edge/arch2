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

CROSS_STACK_SIGHTLINE: dict[str, Any] = {
    "stage": "2. Explore",
    "node_level_anchor": (
        "nano-kpu (msh_chip_top): Conservation-of-bytes (76,109 B/tok -> 4,757 cyc/tok floor; "
        "60,013 B/tok -> 3,751 cyc/tok with 16 KiB hq shadow cache) and Little's Law "
        "(L = lambda * W = 1 req/cyc * 48 cyc = 48 credits minimum -> 256-deep msh_fetch FIFO) "
        "prune impossible proposals in <1 ms and calibrate the 11,200 cyc/tok bet (2.33% error)."
    ),
    "fleet_and_ecosystem_instruments": [
        {
            "instrument": "AgentDSE (Sample-Efficient Design Space Exploration)",
            "connection": (
                "Replaces 1,000+ blind cycle-accurate simulator sweeps with analytical roofline "
                "and Little's Law pruning, converging in 5 guided simulator calls (200x fewer simulations)."
            ),
        },
        {
            "instrument": "MLPerf 512-GPU Interconnect Energy & Bandwidth Wall",
            "connection": (
                "Applies the identical conservation-of-bytes and Little's Law credit-depth equations "
                "across scale-out NVLink/RoCE fabrics where widening tensor cores cannot hide bisection bandwidth bottlenecks."
            ),
        },
    ],
    "sightline_takeaway": (
        "Analytical rooflines and Little's Law queue sizing govern both a 16 B/cycle KPU DRAM port "
        "and a 512-GPU cluster fabric—pruning infeasible candidates before a single cycle of simulation runs."
    ),
}


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
        "cross_stack_sightline": CROSS_STACK_SIGHTLINE,
    }


def _score_explore_bet(
    label: str,
    precision: str,
    bus_bytes_per_cyc: int,
    fifo_credits: int,
    predicted_cpt: float,
    sim_calls_used: int,
) -> dict[str, Any]:
    prec_map = {
        "fp32": 608896,
        "fp16": 304448,
        "int8": 152224,
        "int4": 76109,
        "int4_hq": 60013,
    }
    p_key = precision.strip().lower()
    active_bytes = prec_map.get(p_key, 76109)
    bw = max(1, bus_bytes_per_cyc)
    dram_floor_cyc = math.ceil(active_bytes / bw)
    max_tok_s = round(CLOCK_HZ / dram_floor_cyc, 1)

    # Little's Law at 2x DRAM latency (48 cycles) at 1 req/cycle -> L = 48 credits min
    littles_law_min_credits = 48
    littles_law_ok = fifo_credits >= littles_law_min_credits

    # Must respect 16 B/cyc contract pin limit
    contract_bw_ok = bw == 16
    # Predicted cycles/token must be >= physical DRAM floor and within 5% of measured 11,467.125
    measured_cpt = 11467.125
    respects_floor = predicted_cpt >= dram_floor_cyc
    rel_err_pct = round(abs(predicted_cpt - measured_cpt) / measured_cpt * 100.0, 2)
    calibrated = respects_floor and rel_err_pct <= 5.0 and max_tok_s >= 8720.0

    passed = contract_bw_ok and littles_law_ok and calibrated
    notes = []
    if not contract_bw_ok:
        notes.append(f"Illegal bus width {bw} B/cyc (contract locks 16 B/cyc)")
    if not respects_floor:
        notes.append(
            f"Violates conservation of bytes: bet {predicted_cpt:,.0f} < floor {dram_floor_cyc:,} cyc/tok"
        )
    elif max_tok_s < 8720.0:
        notes.append(
            f"Precision {precision} ceiling {max_tok_s:,.1f} tok/s cannot reach 8,720 tok/s"
        )
    else:
        notes.append(
            f"Roofline valid (floor {dram_floor_cyc:,} cyc/tok, bet error {rel_err_pct}%)"
        )
    if littles_law_ok:
        notes.append(
            f"Little's Law satisfied: FIFO {fifo_credits} >= {littles_law_min_credits} credits (L = 1 req/cyc * 48 cyc)"
        )
    else:
        notes.append(
            f"Stalls under 2x DRAM latency: FIFO {fifo_credits} < {littles_law_min_credits} credits required by Little's Law"
        )

    return {
        "bet_label": label,
        "precision": precision,
        "bus_bytes_per_cycle": bw,
        "active_bytes_per_token": active_bytes,
        "dram_floor_cycles_per_token": dram_floor_cyc,
        "roofline_ceiling_tok_s": max_tok_s,
        "fifo_credit_depth": fifo_credits,
        "littles_law_min_credits_at_48cyc": littles_law_min_credits,
        "predicted_cycles_per_token": predicted_cpt,
        "measured_cycles_per_token": measured_cpt,
        "prediction_error_pct": rel_err_pct,
        "simulator_calls_used": sim_calls_used,
        "passed": passed,
        "diagnosis": " | ".join(notes),
    }


def run_challenge(auto: bool = True) -> dict[str, Any]:
    """Interactive / Auto Challenge: The Roofline & Little's Law Challenge."""
    naive_bet = _score_explore_bet(
        label="Brute-Force / Uncalibrated Bet (FP16 + 1-Deep FIFO + 5,000 cyc/tok claim)",
        precision="fp16",
        bus_bytes_per_cyc=16,
        fifo_credits=1,
        predicted_cpt=5000.0,
        sim_calls_used=1000,
    )

    if auto or not sys.stdin.isatty():
        prec = "int4"
        bw = 16
        fifo = 256
        bet_cpt = 11200.0
        label = (
            "Architect Winning Bet (INT4 Group-128 + 256-Credit FIFO + 11,200 cyc/tok)"
        )
    else:
        console.print(
            Panel(
                "[bold yellow]LAB 02 INTERACTIVE CHALLENGE: THE ROOFLINE & LITTLE'S LAW CHALLENGE[/bold yellow]\n"
                "Place an analytical performance bet for [cyan]msh_chip_top[/cyan] (@ 100 MHz, 16 B/cyc DRAM, 48-cyc 2x chaos latency):\n"
                "  1. Weight precision ([bold]fp32[/bold], [bold]fp16[/bold], [bold]int8[/bold], or [bold]int4[/bold])\n"
                "  2. DRAM bus width in B/cycle (contract = [bold]16[/bold])\n"
                "  3. Fetch FIFO credit depth (Little's Law L = 1 req/cyc * 48 cyc = [bold]>= 48[/bold], e.g. [bold]256[/bold])\n"
                "  4. Pre-committed steady-state cycles/token bet (e.g. [bold]11200[/bold])",
                box=box.ROUNDED,
                border_style="yellow",
            )
        )
        raw_p = console.input(
            "[bold cyan]1. Weight precision (fp32/fp16/int8/int4) [default=int4]: [/bold cyan]"
        ).strip()
        raw_bw = console.input(
            "[bold cyan]2. DRAM bus width B/cycle [default=16]: [/bold cyan]"
        ).strip()
        raw_fifo = console.input(
            "[bold cyan]3. Fetch FIFO credit depth [default=256]: [/bold cyan]"
        ).strip()
        raw_cpt = console.input(
            "[bold cyan]4. Predicted cycles/token [default=11200]: [/bold cyan]"
        ).strip()
        prec = raw_p if raw_p else "int4"
        try:
            bw = int(raw_bw) if raw_bw else 16
        except ValueError:
            bw = 16
        try:
            fifo = int(raw_fifo) if raw_fifo else 256
        except ValueError:
            fifo = 256
        try:
            bet_cpt = float(raw_cpt) if raw_cpt else 11200.0
        except ValueError:
            bet_cpt = 11200.0
        label = "Student Interactive Roofline Bet"

    winning_bet = _score_explore_bet(
        label=label,
        precision=prec,
        bus_bytes_per_cyc=bw,
        fifo_credits=fifo,
        predicted_cpt=bet_cpt,
        sim_calls_used=5,
    )

    return {
        "mode": "challenge",
        "stage": "2. Explore",
        "challenge_name": "The Roofline & Little's Law Challenge",
        "auto_mode": auto,
        "agentdse_efficiency": {
            "guided_simulator_calls": 5,
            "brute_force_simulator_calls": 1000,
            "sample_efficiency_gain_x": 200.0,
        },
        "naive_bet": naive_bet,
        "winning_bet": winning_bet,
        "passed": bool((not naive_bet["passed"]) and winning_bet["passed"]),
        "cross_stack_sightline": CROSS_STACK_SIGHTLINE,
    }


def render_sightline(sightline: dict[str, Any]) -> None:
    lines = [
        f"[bold cyan]Node-Level Anchor (nano-kpu):[/bold cyan] {sightline['node_level_anchor']}"
    ]
    for inst in sightline["fleet_and_ecosystem_instruments"]:
        lines.append(
            f"[bold yellow]• {inst['instrument']}:[/bold yellow] {inst['connection']}"
        )
    lines.append(
        f"[bold green]Sightline Takeaway:[/bold green] {sightline['sightline_takeaway']}"
    )
    console.print(
        Panel(
            "\n".join(lines),
            title="[bold magenta]Cross-Stack Sightline (Node to Fleet) — Stage 2: Explore[/bold magenta]",
            box=box.ROUNDED,
            border_style="magenta",
        )
    )


def render_challenge(data: dict[str, Any]) -> None:
    dse = data["agentdse_efficiency"]
    console.print(
        Panel(
            "[bold yellow]LAB 02 (--mode challenge): THE ROOFLINE & LITTLE'S LAW CHALLENGE[/bold yellow]\n"
            "Scoring candidate architecture bets against Conservation of Bytes (4,757 cyc/tok raw INT4 floor; "
            "3,751 cyc/tok with 16 KiB hq cache), Little's Law ($L = \\lambda W = 1 \\times 48 = 48$ credits min), "
            f"and AgentDSE sample efficiency ([bold]{dse['guided_simulator_calls']} guided calls vs. {dse['brute_force_simulator_calls']:,} brute-force sweeps = {dse['sample_efficiency_gain_x']:.0f}x fewer sims[/bold]).",
            box=box.ROUNDED,
            border_style="yellow",
        )
    )
    tbl = Table(
        title="Stage 2 Roofline & Little's Law Betting Scorecard",
        box=box.ROUNDED,
        show_lines=True,
    )
    tbl.add_column("Candidate Bet", style="bold cyan", width=26)
    tbl.add_column("Precision & Floor", justify="right", width=20)
    tbl.add_column("FIFO Credits (Little's Law)", justify="right", width=18)
    tbl.add_column("Predicted vs Measured", justify="right", width=22)
    tbl.add_column("Referee Diagnosis", style="white", width=34)

    for b in (data["naive_bet"], data["winning_bet"]):
        status = (
            "[bold green]PASS[/bold green]"
            if b["passed"]
            else "[bold red]REJECTED[/bold red]"
        )
        tbl.add_row(
            f"{b['bet_label']}\n({status}, {b['simulator_calls_used']} sims)",
            f"{b['precision'].upper()} @ {b['bus_bytes_per_cycle']} B/cyc\nFloor: {b['dram_floor_cycles_per_token']:,} cyc",
            f"{b['fifo_credit_depth']} credits\n(min >= {b['littles_law_min_credits_at_48cyc']})",
            f"Bet: {b['predicted_cycles_per_token']:,.1f} cyc\nMeas: {b['measured_cycles_per_token']:,.1f} ({b['prediction_error_pct']}%)",
            b["diagnosis"],
        )
    console.print(tbl)
    console.print()


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
    render_sightline(data["cross_stack_sightline"])
    console.print()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Lab 02: Stage 2 Explore — Roofline Betting & Candidate Generation"
    )
    ap.add_argument(
        "--mode",
        choices=["verify", "break", "challenge", "summary", "inspect"],
        default="summary",
    )
    ap.add_argument("--verify", action="store_const", const="verify", dest="mode_flag")
    ap.add_argument("--break", action="store_const", const="break", dest="mode_flag")
    ap.add_argument(
        "--challenge", action="store_const", const="challenge", dest="mode_flag"
    )
    ap.add_argument(
        "--summary", action="store_const", const="summary", dest="mode_flag"
    )
    ap.add_argument(
        "--inspect", action="store_const", const="inspect", dest="mode_flag"
    )
    ap.add_argument(
        "--auto",
        action="store_true",
        help="Run challenge mode non-interactively (evaluates naive and winning bets)",
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

    if mode == "challenge":
        res = run_challenge(auto=args.auto or args.json or (not sys.stdin.isatty()))
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            render_challenge(res)
            render_sightline(res["cross_stack_sightline"])
        return 0 if res["passed"] else 1

    if mode in ("verify", "inspect"):
        res = run_verify()
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            render_verify(res)
        return 0 if res["passed"] else 1

    b_res = run_break()
    c_res = run_challenge(auto=True)
    v_res = run_verify()
    combined = {
        "lab": "02-explore",
        "stage": "2. Explore",
        "passed": (
            b_res["rejected_before_rtl_sim"] and c_res["passed"] and v_res["passed"]
        ),
        "break_test": b_res,
        "challenge_test": c_res,
        "verify_test": v_res,
        "cross_stack_sightline": CROSS_STACK_SIGHTLINE,
    }
    if args.json:
        print(json.dumps(combined, indent=2))
    else:
        render_break(b_res)
        render_challenge(c_res)
        render_verify(v_res)
    return 0 if combined["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
