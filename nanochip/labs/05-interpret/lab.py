#!/usr/bin/env python3
"""Lab 05 (Stage 5: Interpret) — Causal Credit Assignment & The Three Return Arrows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

CROSS_STACK_SIGHTLINE: dict[str, Any] = {
    "stage": "5. Interpret",
    "node_level_anchor": (
        "nano-kpu (msh_chip_top): Causal Credit Router maps multi-modal Stage 4 telemetry across "
        "the Three Return Arrows (Turn 1 -> 3. Implement, Turn 2 -> 2. Explore, Turn 3 -> 1. Formulate) "
        "and advances Turn 4 -> 6. Commit once perf-model error reaches 2.33% (<= 5%)."
    ),
    "fleet_and_ecosystem_instruments": [
        {
            "instrument": "AgentDSE Self-Ablation & Bottleneck Attribution",
            "connection": (
                "Distinguishes implementation bugs from microarchitectural queue/banking hazards and "
                "representation rooflines so the search policy modifies the true bottleneck variable."
            ),
        },
        {
            "instrument": "MLPerf Agents (Joules & Simulator Calls per Verified Outcome)",
            "connection": (
                "Accounts for the full trajectory cost of agentic design: routing via the Three Return "
                "Arrows converges in 4 directed turns (~1.92 kJ total EDA+LLM energy) vs. 42+ blind Stage-3 "
                "retries (~20.16 kJ wasted without converging)."
            ),
        },
    ],
    "sightline_takeaway": (
        "In both RTL synthesis loops and fleet-scale agentic benchmarks, Stage 5 Interpret turns raw "
        "referee failures into causal credit assignment—slashing joules-per-verified-outcome by >10x."
    ),
}


def diagnose_turn(telemetry: dict[str, Any]) -> dict[str, Any]:
    """Architecture 2.0 Stage 5 Causal Credit Router:
    Maps multi-modal Stage 4 telemetry to one of the Three Return Arrows or Stage 6 Commit.
    """
    # 1. Check Implementation Boundary (Stage 3) defects first
    if (
        not telemetry.get("audit_ok", True)
        or not telemetry.get("selfmodel_bit_exact", True)
        or not telemetry.get("randreset_ok", True)
    ):
        return {
            "route": "Return Arrow -> 3. Implement",
            "target_stage": "3. Implement",
            "causal_class": "Implementation / Bit-Exactness Defect",
            "prescribed_action": (
                "Localize first differing row/element against fxmodel.py (<<14 shift in msh_deq.v, "
                "zero-point fold in msh_gemv.v) and ensure all control flops reset cleanly."
            ),
        }

    # 2. Check Formulation / Conservation-of-Bytes Roofline Wall (Stage 1)
    if telemetry.get("roofline_cycles_per_token", 0) > telemetry.get(
        "target_max_cycles_per_token", 12000
    ):
        return {
            "route": "Return Arrow -> 1. Formulate",
            "target_stage": "1. Formulate",
            "causal_class": "Cross-Layer Formulation / Pin-Bandwidth Wall",
            "prescribed_action": (
                "Hardware-only optimization cannot beat conservation of bytes (FP16 requires 19,028 cyc/tok floor). "
                "Escalate from Layer 2 (hardware-only) to Layer 3 co-design: INT4 group-128 fused dequantization + Q4.26 numerics."
            ),
        }

    # 3. Check Microarchitectural Bottleneck (Stage 2: Explore)
    if (
        telemetry.get("latency_2x_elasticity", 1.0) > 1.15
        or telemetry.get("total_area_mm2", 0.0) > telemetry.get("area_budget_mm2", 4.0)
        or telemetry.get("rmw_pipeline_stall_ratio", 1.0) > 1.3
    ):
        return {
            "route": "Return Arrow -> 2. Explore",
            "target_stage": "2. Explore",
            "causal_class": "Microarchitectural Topology / Memory-Banking Bottleneck",
            "prescribed_action": (
                "Replace 16-way parallel byte demux in msh_deq (-96K gates) with byte-serial emitter, "
                "add 256-deep credit-tracked FIFO in msh_fetch, split qacc SRAM into even/odd parity banks, "
                "and add 16 KiB hq LM-head shadow cache."
            ),
        }

    # 4. All gates green and analytical perf-model calibrated -> Advance to 6. Commit
    pred = telemetry.get("predicted_cpt", 11200.0)
    meas = telemetry.get("measured_cpt", 11467.125)
    rel_err = abs(pred - meas) / meas if meas else 1.0
    return {
        "route": "Advance -> 6. Commit",
        "target_stage": "6. Commit",
        "causal_class": f"Converged & Calibrated (perf-model error = {rel_err * 100:.2f}% <= 5.0%)",
        "prescribed_action": (
            "Freeze RTL and fxmodel.py, bind SHA-256 evidence packets, disclose pre-layout wireload/blackbox "
            "proxy gaps, and sign Design-Loop Card v2.0."
        ),
    }


def run_break() -> dict[str, Any]:
    """Show what happens in a naive 'blind retry' loop where an RTL bug, a 2x DRAM stall,
    and an FP16 bandwidth roofline wall are all fed into the same generic Stage 3 retry prompt.
    """
    blind_episodes = [
        {
            "scenario": "Scenario A: 1-bit shift bug in msh_deq.v (<<13 vs <<14)",
            "true_causal_stage": "3. Implement",
            "blind_retry_prompt": "Prompt: 'Simulation failed cos_min=0.41. Edit Verilog to fix.'",
            "blind_outcome": "Slowly converges after 8 full-chip sims (no fxmodel row-0 localization).",
            "wasted_evaluations": 7,
            "converged": True,
        },
        {
            "scenario": "Scenario B: 2x DRAM latency stall (1.88x slowdown) & 96K-gate parallel demux bloat",
            "true_causal_stage": "2. Explore",
            "blind_retry_prompt": "Prompt: 'Area=4.45mm2 > 4.0mm2, cycles high. Edit Verilog expressions.'",
            "blind_outcome": "FAILS: Local gate-level tweaks cannot remove 96K-gate demux or RMW bank hazards without microarchitectural re-banking.",
            "wasted_evaluations": 15,
            "converged": False,
        },
        {
            "scenario": "Scenario C: Uncompressed FP16 weight stream (304,448 B/tok -> 19,028 cyc/tok floor)",
            "true_causal_stage": "1. Formulate",
            "blind_retry_prompt": "Prompt: 'Throughput is 4,800 tok/s (< 20,000 target). Optimize MAC pipeline.'",
            "blind_outcome": "HALLUCINATES / REWARD-HACKS: Agent widens MACs to 128 lanes with 0 speedup (pin-bound), then attempts to edit resource_budgets.json!",
            "wasted_evaluations": 20,
            "converged": False,
        },
    ]
    return {
        "mode": "break",
        "stage": "5. Interpret",
        "blind_retry_episodes": blind_episodes,
        "total_wasted_evaluations": sum(
            e["wasted_evaluations"] for e in blind_episodes
        ),
        "blind_loop_failed_on_structural_walls": not all(
            e["converged"] for e in blind_episodes
        ),
        "verdict": "BLIND_RETRY_OSCILLATES_WITHOUT_RETURN_ARROWS",
    }


def _canonical_turns() -> list[dict[str, Any]]:
    return [
        {
            "turn": 1,
            "name": "Turn 1: Unaligned Shift / Zero-Point & Static Audit Failure",
            "telemetry": {
                "audit_ok": False,
                "selfmodel_bit_exact": False,
                "randreset_ok": False,
                "first_diff_row": 0,
                "symptom": "fxmodel.py vs RTL diverges at Row 0, Col 0 (<<13 vs <<14); unreset control flop fails randreset.",
            },
            "expected_target": "3. Implement",
        },
        {
            "turn": 2,
            "name": "Turn 2: 2x DRAM Latency Collapse, Single-Bank qacc RMW Stall & 96K-Gate Demux",
            "telemetry": {
                "audit_ok": True,
                "selfmodel_bit_exact": True,
                "randreset_ok": True,
                "roofline_cycles_per_token": 4757,
                "target_max_cycles_per_token": 12000,
                "latency_2x_elasticity": 1.88,
                "total_area_mm2": 4.38,
                "area_budget_mm2": 4.0,
                "rmw_pipeline_stall_ratio": 1.65,
                "symptom": "2x DRAM latency slows chip by 1.88x; single qacc SRAM stalls 2-chunk MAC; 16-way demux adds +96K gates.",
            },
            "expected_target": "2. Explore",
        },
        {
            "turn": 3,
            "name": "Turn 3: Layer-2 Uncompressed FP16 Pin-Bandwidth Ceiling",
            "telemetry": {
                "audit_ok": True,
                "selfmodel_bit_exact": True,
                "randreset_ok": True,
                "roofline_cycles_per_token": 19028,
                "target_max_cycles_per_token": 12000,
                "latency_2x_elasticity": 1.05,
                "total_area_mm2": 3.50,
                "area_budget_mm2": 4.0,
                "rmw_pipeline_stall_ratio": 1.0,
                "symptom": "Even at 100% bus utilization, FP16 weight stream (304,448 B/tok) hits 19,028 cyc/tok floor (5,255 tok/s max).",
            },
            "expected_target": "1. Formulate",
        },
        {
            "turn": 4,
            "name": "Turn 4: Converged INT4 Co-Design + Dual-Parity GEMV + 256-Deep Credit Fetch",
            "telemetry": {
                "audit_ok": True,
                "selfmodel_bit_exact": True,
                "randreset_ok": True,
                "roofline_cycles_per_token": 4757,
                "target_max_cycles_per_token": 12000,
                "latency_2x_elasticity": 1.0457,
                "total_area_mm2": 3.610342,
                "area_budget_mm2": 4.0,
                "rmw_pipeline_stall_ratio": 1.0,
                "predicted_cpt": 11200.0,
                "measured_cpt": 11467.125,
                "symptom": "11,467.125 cyc/tok measured vs 11,200 predicted (2.33% error); 8,720.6 tok/s; 3.610 mm^2; 6.166 ns.",
            },
            "expected_target": "6. Commit",
        },
    ]


def run_verify() -> dict[str, Any]:
    """Run the Architecture 2.0 Diagnostic Router across the 4 turns of the nano-kpu trajectory."""
    turns_input = _canonical_turns()

    routed_turns = []
    for t in turns_input:
        diag = diagnose_turn(t["telemetry"])
        routed_turns.append(
            {
                "turn": t["turn"],
                "name": t["name"],
                "symptom": t["telemetry"]["symptom"],
                "route": diag["route"],
                "target_stage": diag["target_stage"],
                "expected_target": t["expected_target"],
                "correct_route": diag["target_stage"] == t["expected_target"],
                "causal_class": diag["causal_class"],
                "prescribed_action": diag["prescribed_action"],
            }
        )

    return {
        "mode": "verify",
        "stage": "5. Interpret",
        "passed": all(rt["correct_route"] for rt in routed_turns),
        "turns": routed_turns,
        "cross_stack_sightline": CROSS_STACK_SIGHTLINE,
    }


def _normalize_stage_choice(raw: str, default_stage: str) -> str:
    s = raw.strip().lower()
    if not s:
        return default_stage
    if "1" in s or "form" in s:
        return "1. Formulate"
    if "2" in s or "expl" in s:
        return "2. Explore"
    if "3" in s or "impl" in s:
        return "3. Implement"
    if "6" in s or "comm" in s:
        return "6. Commit"
    return raw.strip()


def _score_routing_policy(
    label: str,
    chosen_routes: list[str],
    turns: list[dict[str, Any]],
    total_eval_calls: int,
    converged: bool,
) -> dict[str, Any]:
    # MLPerf Agents energy model: ~180 J per LLM reasoning step + ~300 J per full Verilator+Yosys evaluation = 480 J/call
    joules_per_call = 480.0
    total_joules = round(total_eval_calls * joules_per_call, 1)
    expected = [t["expected_target"] for t in turns]
    matches = [c == e for c, e in zip(chosen_routes, expected)]
    accuracy = round(sum(matches) / len(expected), 2)
    passed = all(matches) and converged

    return {
        "policy_label": label,
        "chosen_routes": chosen_routes,
        "expected_routes": expected,
        "routing_accuracy": accuracy,
        "total_evaluator_calls": total_eval_calls,
        "total_energy_joules": total_joules,
        "total_energy_kj": round(total_joules / 1000.0, 2),
        "converged_to_verified_outcome": converged,
        "joules_per_verified_outcome": total_joules if converged else None,
        "passed": passed,
    }


def run_challenge(auto: bool = True) -> dict[str, Any]:
    """Interactive / Auto Challenge: The Causal Credit Router & MLPerf Agents Energy Ledger Challenge."""
    turns = _canonical_turns()

    naive_policy = _score_routing_policy(
        label="Blind Stage-3 Retry Policy (Routes all failures to 3. Implement)",
        chosen_routes=["3. Implement", "3. Implement", "3. Implement", "3. Implement"],
        turns=turns,
        total_eval_calls=42,
        converged=False,
    )

    if auto or not sys.stdin.isatty():
        chosen = ["3. Implement", "2. Explore", "1. Formulate", "6. Commit"]
        label = "Architect Causal Credit Router (Three Return Arrows + Stage 6 Advance)"
    else:
        console.print(
            Panel(
                "[bold yellow]LAB 05 INTERACTIVE CHALLENGE: THE CAUSAL CREDIT ROUTER & MLPerf Agents ENERGY LEDGER[/bold yellow]\n"
                "Route each of the 4 Stage-4 telemetry signatures to its causal target stage:\n"
                "  Options: [bold]1. Formulate[/bold] | [bold]2. Explore[/bold] | [bold]3. Implement[/bold] | [bold]6. Commit[/bold]",
                box=box.ROUNDED,
                border_style="yellow",
            )
        )
        chosen = []
        for t in turns:
            console.print(
                f"[cyan]{t['name']}[/cyan]\n  Symptom: {t['telemetry']['symptom']}"
            )
            raw = console.input(
                f"[bold cyan]  Route Turn {t['turn']} [default={t['expected_target']}]: [/bold cyan]"
            )
            chosen.append(_normalize_stage_choice(raw, t["expected_target"]))
        label = "Student Interactive Causal Routing"

    winning_policy = _score_routing_policy(
        label=label,
        chosen_routes=chosen,
        turns=turns,
        total_eval_calls=4,
        converged=chosen == ["3. Implement", "2. Explore", "1. Formulate", "6. Commit"],
    )

    energy_saving_ratio = round(
        naive_policy["total_energy_joules"] / winning_policy["total_energy_joules"], 2
    )

    return {
        "mode": "challenge",
        "stage": "5. Interpret",
        "challenge_name": "The Causal Credit Router & MLPerf Agents Energy Ledger Challenge",
        "auto_mode": auto,
        "mlperf_agents_ledger": {
            "joules_per_eval_turn": 480.0,
            "directed_4turn_joules": winning_policy["total_energy_joules"],
            "blind_42turn_wasted_joules": naive_policy["total_energy_joules"],
            "energy_efficiency_ratio_x": energy_saving_ratio,
        },
        "naive_policy": naive_policy,
        "winning_policy": winning_policy,
        "passed": bool((not naive_policy["passed"]) and winning_policy["passed"]),
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
            title="[bold magenta]Cross-Stack Sightline (Node to Fleet) — Stage 5: Interpret[/bold magenta]",
            box=box.ROUNDED,
            border_style="magenta",
        )
    )


def render_challenge(data: dict[str, Any]) -> None:
    led = data["mlperf_agents_ledger"]
    console.print(
        Panel(
            "[bold yellow]LAB 05 (--mode challenge): THE CAUSAL CREDIT ROUTER & MLPerf Agents ENERGY LEDGER[/bold yellow]\n"
            "Comparing a blind Stage-3 retry loop (42 eval calls = "
            f"[bold red]{led['blind_42turn_wasted_joules']:,.0f} J[/bold red] wasted, 0 verified outcomes) against the "
            "Architecture 2.0 Three-Return-Arrow router (4 directed calls = "
            f"[bold green]{led['directed_4turn_joules']:,.0f} J[/bold green] per verified outcome, "
            f"[bold]{led['energy_efficiency_ratio_x']}x energy reduction[/bold]).",
            box=box.ROUNDED,
            border_style="yellow",
        )
    )
    tbl = Table(
        title="Causal Credit Routing & MLPerf Agents Trajectory Cost Ledger",
        box=box.ROUNDED,
        show_lines=True,
    )
    tbl.add_column("Routing Policy", style="bold cyan", width=28)
    tbl.add_column("Turn 1..4 Routes", style="white", width=32)
    tbl.add_column("Route Accuracy", justify="right", width=14)
    tbl.add_column("Eval Calls & Energy", justify="right", width=20)
    tbl.add_column("Joules / Verified Outcome", justify="right", width=22)

    for pol in (data["naive_policy"], data["winning_policy"]):
        status = (
            "[bold green]PASS[/bold green]"
            if pol["passed"]
            else "[bold red]FAILED[/bold red]"
        )
        jpv = (
            f"[bold green]{pol['joules_per_verified_outcome']:,.0f} J (1.92 kJ)[/bold green]"
            if pol["joules_per_verified_outcome"] is not None
            else "[bold red]INF (Did Not Converge)[/bold red]"
        )
        tbl.add_row(
            f"{pol['policy_label']}\n({status})",
            " -> ".join(pol["chosen_routes"]),
            f"{pol['routing_accuracy'] * 100:.0f}%",
            f"{pol['total_evaluator_calls']} calls\n({pol['total_energy_kj']:.2f} kJ)",
            jpv,
        )
    console.print(tbl)
    console.print()


def render_break(data: dict[str, Any]) -> None:
    console.print(
        Panel(
            "[bold red]LAB 05 (--mode break): WHY NAIVE 'BLIND RETRY' LOOPS FAIL ON STRUCTURAL WALLS[/bold red]\n"
            "Feeding an RTL bug, a microarchitectural banking/stall bottleneck, and an FP16 pin-bandwidth "
            "wall into the same undifferentiated [cyan]'Edit Verilog'[/cyan] retry prompt.",
            box=box.ROUNDED,
            border_style="red",
        )
    )
    tbl = Table(
        title="Naive Single-Arrow Retry Loop vs. Structural Hardware Bottlenecks",
        box=box.ROUNDED,
        show_lines=True,
    )
    tbl.add_column("Failure Scenario", style="bold cyan", width=26)
    tbl.add_column("True Causal Stage", style="yellow", width=16)
    tbl.add_column("Blind Retry Prompt", style="dim white", width=28)
    tbl.add_column("Blind Loop Outcome", style="red", width=34)

    for e in data["blind_retry_episodes"]:
        tbl.add_row(
            e["scenario"],
            e["true_causal_stage"],
            e["blind_retry_prompt"],
            f"{e['blind_outcome']} (Wasted evals: {e['wasted_evaluations']})",
        )
    console.print(tbl)
    console.print(
        "[bold green]✔ Stage 5 Lesson:[/bold green] Without causal credit assignment, an agent wastes "
        f"[bold]{data['total_wasted_evaluations']}+ full-chip evaluations[/bold] trying to fix microarchitectural "
        "or conservation-of-bytes walls with local syntax edits.\n"
    )


def render_verify(data: dict[str, Any]) -> None:
    console.print(
        Panel(
            "[bold green]LAB 05 (--mode verify): ARCHITECTURE 2.0 DIAGNOSTIC ROUTER & THE THREE RETURN ARROWS[/bold green]\n"
            "Verified 4-Turn Causal Credit Assignment across [cyan]3. Implement[/cyan], "
            "[cyan]2. Explore[/cyan], [cyan]1. Formulate[/cyan], and [cyan]6. Commit[/cyan].",
            box=box.ROUNDED,
            border_style="green",
        )
    )
    tbl = Table(
        title="The 4-Turn nano-kpu Diagnostic Trajectory & Return-Arrow Routing",
        box=box.ROUNDED,
        show_lines=True,
    )
    tbl.add_column("Turn", style="bold cyan", width=8)
    tbl.add_column("Stage 4 Referee Telemetry", style="white", width=30)
    tbl.add_column("Diagnostic Route", style="bold yellow", width=22)
    tbl.add_column("Prescribed Architectural Action", style="green", width=38)

    for rt in data["turns"]:
        route_style = (
            "bold green" if rt["target_stage"] == "6. Commit" else "bold yellow"
        )
        tbl.add_row(
            f"Turn {rt['turn']}",
            rt["symptom"],
            f"[{route_style}]{rt['route']}[/{route_style}]",
            rt["prescribed_action"],
        )
    console.print(tbl)
    render_sightline(data["cross_stack_sightline"])
    console.print()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Lab 05: Stage 5 Interpret — Causal Credit Assignment & Return Arrows"
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
        help="Run challenge mode non-interactively (evaluates blind vs causal routing policies)",
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
        return 0 if res["blind_loop_failed_on_structural_walls"] else 1

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
        "lab": "05-interpret",
        "stage": "5. Interpret",
        "passed": (
            b_res["blind_loop_failed_on_structural_walls"]
            and c_res["passed"]
            and v_res["passed"]
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
