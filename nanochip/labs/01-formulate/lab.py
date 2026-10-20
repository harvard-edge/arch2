#!/usr/bin/env python3
"""Lab 01 (Stage 1: Formulate) — Locking the Study Contract & Integrity Boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
KPU_ROOT = REPO_ROOT / "nanochip" / "kpu"
if str(KPU_ROOT) not in sys.path:
    sys.path.insert(0, str(KPU_ROOT))

from harness import check_integrity, scoring  # noqa: E402

console = Console()

CROSS_STACK_SIGHTLINE: dict[str, Any] = {
    "stage": "1. Formulate",
    "node_level_anchor": (
        "nano-kpu (msh_chip_top): 35 SHA-256 frozen contract files in harness/manifest.json; "
        "conservation-of-bytes proves Layer-2 hardware-only FP16 (19,028 cyc/tok = 5,255.4 tok/s) "
        "cannot reach >8,000 tok/s, forcing Layer-3 INT4 group-128 co-design (<= 1.31 B/weight)."
    ),
    "fleet_and_ecosystem_instruments": [
        {
            "instrument": "QuArch (Cross-Layer Reasoning Benchmark)",
            "connection": (
                "Tests whether an architect or agent can diagnose when a target violates single-layer "
                "(Layer 2 RTL-only) physical bounds and must escalate to Layer 3 (numeric + hardware co-design)."
            ),
        },
        {
            "instrument": "Lighthouse XR SoC Formulation",
            "connection": (
                "Locks multi-sensor XR glasses latency, power, and memory-bandwidth envelopes before "
                "any accelerator microarchitecture is explored, preventing reward-hacked contract drift."
            ),
        },
    ],
    "sightline_takeaway": (
        "From a 3.61 mm^2 edge KPU to an XR SoC or datacenter cluster, Stage 1 Formulate locks C and M "
        "cryptographically and uses conservation laws to set the legal cross-layer boundary Theta."
    ),
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_break() -> dict[str, Any]:
    """Simulate an unguarded agent reward-hacking resource_budgets.json and scoring.py
    in an in-memory/sandbox overlay (never touching nanochip/kpu/) and show how
    check_integrity.py's SHA-256 manifest verification catches it immediately."""
    manifest_path = KPU_ROOT / "harness" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    budgets_rel = "harness/resource_budgets.json"
    scoring_rel = "harness/scoring.py"

    orig_budgets_bytes = (KPU_ROOT / budgets_rel).read_bytes()
    orig_scoring_bytes = (KPU_ROOT / scoring_rel).read_bytes()

    # Simulated unguarded agent tamper 1: relax clock from 100 MHz (10 ns) to 25 MHz (40 ns) & 4x area
    tampered_budgets = json.loads(orig_budgets_bytes.decode("utf-8"))
    tampered_budgets["tech"]["target_freq_mhz"] = 25.0
    tampered_budgets["tech"]["target_period_ns"] = 40.0
    tampered_budgets["resources"]["logic_area_mm2"] = 16.0
    tampered_budgets_bytes = json.dumps(tampered_budgets, indent=2).encode("utf-8")

    # Simulated unguarded agent tamper 2: relax COS_PASS from 0.98 to 0.50
    tampered_scoring_bytes = orig_scoring_bytes.replace(
        b"COS_PASS = 0.98", b"COS_PASS = 0.50"
    )

    attacks = [
        {
            "file": budgets_rel,
            "attack": "Relax target_freq_mhz (100.0 -> 25.0 MHz) & logic_area_mm2 (4.0 -> 16.0 mm^2)",
            "expected_sha256": manifest["files"][budgets_rel],
            "observed_sha256": sha256_bytes(tampered_budgets_bytes),
            "caught": sha256_bytes(tampered_budgets_bytes)
            != manifest["files"][budgets_rel],
        },
        {
            "file": scoring_rel,
            "attack": "Dilute COS_PASS accuracy bar (0.98 -> 0.50) to hide fixed-point overflow",
            "expected_sha256": manifest["files"][scoring_rel],
            "observed_sha256": sha256_bytes(tampered_scoring_bytes),
            "caught": sha256_bytes(tampered_scoring_bytes)
            != manifest["files"][scoring_rel],
        },
    ]

    return {
        "mode": "break",
        "stage": "1. Formulate",
        "sandbox_isolated": True,
        "manifest_frozen_files": len(manifest["files"]),
        "attacks": attacks,
        "all_tampering_caught": all(a["caught"] for a in attacks),
        "verdict": "REJECTED_BY_MANIFEST_SHA256_GUARD",
    }


def run_verify() -> dict[str, Any]:
    """Verify all 35 frozen files in nanochip/kpu/harness/manifest.json and emit the
    formal FormulationRecord separating frozen contracts from mutable design space Theta.
    """
    integrity = check_integrity.check()
    manifest = json.loads(
        (KPU_ROOT / "harness" / "manifest.json").read_text(encoding="utf-8")
    )
    budgets = json.loads(
        (KPU_ROOT / "harness" / "resource_budgets.json").read_text(encoding="utf-8")
    )
    seeds = json.loads(
        (KPU_ROOT / "harness" / "seeds_public.json").read_text(encoding="utf-8")
    )

    filelist_path = KPU_ROOT / "rtl" / "filelist.f"
    rtl_modules = [
        line.strip()
        for line in filelist_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith(("#", "//"))
    ]

    frozen_categories: dict[str, int] = {
        "Specification Docs (docs/*, README, weights)": 0,
        "Golden Reference (reference/*)": 0,
        "Evaluation Harness & Macros (harness/*)": 0,
        "Build & Git Hygiene (Makefile, .gitignore)": 0,
    }
    for rel_path in manifest["files"]:
        if rel_path.startswith("docs/") or "README" in rel_path:
            frozen_categories["Specification Docs (docs/*, README, weights)"] += 1
        elif rel_path.startswith("reference/"):
            frozen_categories["Golden Reference (reference/*)"] += 1
        elif rel_path.startswith("harness/"):
            frozen_categories["Evaluation Harness & Macros (harness/*)"] += 1
        else:
            frozen_categories["Build & Git Hygiene (Makefile, .gitignore)"] += 1

    formulation_record = {
        "study_id": "moonshot-kimi-k3-nano-kpu",
        "integrity_ok": bool(integrity["ok"]),
        "frozen_file_count": len(manifest["files"]),
        "modified_files": integrity["modified"],
        "frozen_breakdown": frozen_categories,
        "hard_constraints_C": {
            "technology": budgets["tech"]["name"],
            "target_freq_mhz": budgets["tech"]["target_freq_mhz"],
            "target_period_ns": budgets["tech"]["target_period_ns"],
            "logic_area_budget_mm2": budgets["resources"]["logic_area_mm2"],
            "onchip_sram_budget_mib": budgets["resources"]["onchip_sram_mib"],
            "macro_pricing_um2_per_mbit": 1.0e6,
            "dram_port_bytes_per_cycle": budgets["bandwidth"][
                "dram_port_bytes_per_cycle"
            ],
            "cos_pass_min": scoring.COS_PASS,
            "argmax_pass_pooled": scoring.ARGMAX_PASS,
            "argmax_tie_rel_std": scoring.ARGMAX_TIE_REL,
            "lint_max_warnings": scoring.LINT_MAX_WARN,
            "public_seed": seeds["seed"],
        },
        "legal_design_space_Theta": {
            "rtl_modules": rtl_modules,
            "rtl_module_count": len(rtl_modules),
            "selfmodel_twin": "rtl/selfmodel/fxmodel.py",
            "lut_tables_dir": "rtl/roms/*.hex (5 nonlinearities: sigmoid, alpha, expneg, rsqrt, recip)",
            "numeric_freedom": "Arbitrary internal fixed-point scales (Q4.26, Q4.27, Q8.37) & LUT depths",
            "microarch_freedom": "Pipelining, SRAM banking, byte-serial vs parallel demux, on-chip shadow caching",
        },
        "objective_metric_M": {
            "primary_metric": "tokens_per_sec = target_freq_hz / cycles_per_token (gated on 100% correctness & budgets)",
            "baseline_tokens_per_sec": budgets["primary"]["baseline_tokens_per_sec"],
            "stretch_target_tokens_per_sec": budgets["primary"][
                "target_tokens_per_sec"
            ],
        },
    }
    return {
        "mode": "verify",
        "stage": "1. Formulate",
        "passed": bool(integrity["ok"]) and len(manifest["files"]) == 35,
        "formulation_record": formulation_record,
        "cross_stack_sightline": CROSS_STACK_SIGHTLINE,
    }


def _score_formulate_attempt(
    label: str,
    bytes_per_weight: float,
    co_design_layer: int,
    budgets_boundary: str,
) -> dict[str, Any]:
    active_weights = 152224
    dram_bw = 16
    clock_hz = 100.0e6
    target_tok_s = 8000.0
    max_cycles_for_8k = clock_hz / target_tok_s  # 12,500 cyc/tok
    max_bytes_for_8k = max_cycles_for_8k * dram_bw  # 200,000 B/tok
    max_allowable_bpw = round(max_bytes_for_8k / active_weights, 2)  # 1.31 B/weight

    stream_bytes = int(round(active_weights * bytes_per_weight))
    min_dram_cycles = math.ceil(stream_bytes / dram_bw)
    ceiling_tok_s = round(clock_hz / min_dram_cycles, 1)

    bpw_ok = bytes_per_weight <= max_allowable_bpw and ceiling_tok_s >= target_tok_s
    layer_ok = co_design_layer == 3
    boundary_ok = budgets_boundary.strip().upper() in ("C", "FROZEN", "FROZEN_CONTRACT")
    passed = bpw_ok and layer_ok and boundary_ok

    reasons = []
    if bpw_ok:
        reasons.append(
            f"{bytes_per_weight:.2f} B/w <= {max_allowable_bpw:.2f} B/w ceiling ({min_dram_cycles:,} cyc/tok floor = {ceiling_tok_s:,.1f} tok/s >= 8,000 tok/s)"
        )
    else:
        reasons.append(
            f"FAILS pin wall: {bytes_per_weight:.2f} B/w streams {stream_bytes:,} B/tok -> {min_dram_cycles:,} cyc/tok floor ({ceiling_tok_s:,.1f} tok/s < 8,000 tok/s)"
        )
    if layer_ok:
        reasons.append("Layer 3 (Numeric + Microarchitecture Co-Design) selected")
    else:
        reasons.append(
            f"Layer {co_design_layer} cannot compress below 2.0 B/w without changing representation"
        )
    if boundary_ok:
        reasons.append("resource_budgets.json locked in Frozen Contract (C)")
    else:
        reasons.append(
            "REWARD HACKING: placing resource_budgets.json in Theta violates manifest SHA-256 lock"
        )

    return {
        "attempt_label": label,
        "bytes_per_weight": bytes_per_weight,
        "active_stream_bytes_per_tok": stream_bytes,
        "min_dram_cycles_per_tok": min_dram_cycles,
        "roofline_ceiling_tok_s": ceiling_tok_s,
        "max_allowable_bytes_per_weight_for_8k": max_allowable_bpw,
        "co_design_layer": co_design_layer,
        "budgets_boundary": budgets_boundary,
        "passed": passed,
        "diagnosis": " | ".join(reasons),
    }


def run_challenge(auto: bool = True) -> dict[str, Any]:
    """Interactive / Auto Challenge: The QuArch Coupling & Boundary Challenge."""
    naive_attempt = _score_formulate_attempt(
        label="Naive Layer-2 Attempt (FP16 RTL-only + Mutable Budgets)",
        bytes_per_weight=2.0,
        co_design_layer=2,
        budgets_boundary="Theta",
    )

    if auto or not sys.stdin.isatty():
        student_bpw = 0.50  # INT4 group-128 (~76,109 B / 152,224 params = 0.50 B/w)
        student_layer = 3
        student_boundary = "C"
        label = "Architect Winning Calculation (INT4 Group-128 Layer-3 Co-Design + Frozen C)"
    else:
        console.print(
            Panel(
                "[bold yellow]LAB 01 INTERACTIVE CHALLENGE: THE QuArch COUPLING & BOUNDARY CHALLENGE[/bold yellow]\n"
                "Given 152,224 active weights/token, a 16 B/cycle DRAM port @ 100 MHz, and a >8,000 tok/s "
                "(<=12,500 cyc/tok = 200,000 B/tok) target:\n"
                "  1. Choose bytes/weight (e.g., 2.0 for FP16, 0.50 for INT4 group-128; max allowable is 1.31 B/w)\n"
                "  2. Choose co-design layer (2 = Hardware-only RTL, 3 = Numeric + Hardware Co-Design)\n"
                "  3. Assign [cyan]harness/resource_budgets.json[/cyan] to Frozen Contract ([bold]C[/bold]) or Mutable Space ([bold]Theta[/bold])",
                box=box.ROUNDED,
                border_style="yellow",
            )
        )
        raw_bpw = console.input(
            "[bold cyan]1. Effective bytes per weight [default=0.50]: [/bold cyan]"
        ).strip()
        raw_layer = console.input(
            "[bold cyan]2. Co-design layer (2 or 3) [default=3]: [/bold cyan]"
        ).strip()
        raw_bound = console.input(
            "[bold cyan]3. Boundary for resource_budgets.json (C or Theta) [default=C]: [/bold cyan]"
        ).strip()
        try:
            student_bpw = float(raw_bpw) if raw_bpw else 0.50
        except ValueError:
            student_bpw = 0.50
        try:
            student_layer = int(raw_layer) if raw_layer else 3
        except ValueError:
            student_layer = 3
        student_boundary = raw_bound if raw_bound else "C"
        label = "Student Interactive Submission"

    winning_attempt = _score_formulate_attempt(
        label=label,
        bytes_per_weight=student_bpw,
        co_design_layer=student_layer,
        budgets_boundary=student_boundary,
    )

    return {
        "mode": "challenge",
        "stage": "1. Formulate",
        "challenge_name": "The QuArch Coupling & Boundary Challenge",
        "auto_mode": auto,
        "max_allowable_bytes_per_weight_for_8000_tok_s": 1.31,
        "fp16_min_dram_cycles_per_token": 19028,
        "int4_active_dram_cycles_per_token": 4757,
        "naive_attempt": naive_attempt,
        "winning_attempt": winning_attempt,
        "passed": bool(
             (not naive_attempt["passed"]) and winning_attempt["passed"]
        ),
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
            title="[bold magenta]Cross-Stack Sightline (Node to Fleet) — Stage 1: Formulate[/bold magenta]",
            box=box.ROUNDED,
            border_style="magenta",
        )
    )


def render_challenge(data: dict[str, Any]) -> None:
    console.print(
        Panel(
            "[bold yellow]LAB 01 (--mode challenge): THE QuArch COUPLING & BOUNDARY CHALLENGE[/bold yellow]\n"
            "Proving why >8,000 tok/s (<12,500 cyc/tok = 200,000 B/tok across 152,224 active weights -> "
            "[bold]<= 1.31 B/weight[/bold]) cannot be solved in Layer 2 (FP16 = 19,028 cyc/tok floor) and why "
            "[cyan]resource_budgets.json[/cyan] must stay in Frozen Contract [bold]C[/bold].",
            box=box.ROUNDED,
            border_style="yellow",
        )
    )
    tbl = Table(
        title="QuArch Cross-Layer Formulation & Boundary Scorecard",
        box=box.ROUNDED,
        show_lines=True,
    )
    tbl.add_column("Attempt", style="bold cyan", width=28)
    tbl.add_column("Bytes/Weight & Layer", justify="right", width=20)
    tbl.add_column("DRAM Floor & Ceiling", justify="right", width=22)
    tbl.add_column("Budgets Boundary", justify="center", width=14)
    tbl.add_column("Referee Diagnosis", style="white", width=36)

    for att in (data["naive_attempt"], data["winning_attempt"]):
        status = (
            "[bold green]PASS[/bold green]"
            if att["passed"]
            else "[bold red]REJECTED[/bold red]"
        )
        tbl.add_row(
            f"{att['attempt_label']}\n({status})",
            f"{att['bytes_per_weight']:.2f} B/w\n(Layer {att['co_design_layer']})",
            f"{att['min_dram_cycles_per_tok']:,} cyc/tok\n({att['roofline_ceiling_tok_s']:,.1f} tok/s)",
            att["budgets_boundary"],
            att["diagnosis"],
        )
    console.print(tbl)
    console.print()


def render_break(data: dict[str, Any]) -> None:
    console.print(
        Panel(
            "[bold red]LAB 01 (--mode break): SIMULATING UNGUARDED AGENT REWARD HACKING[/bold red]\n"
            "Testing what happens when an autonomous agent attempts to relax [cyan]resource_budgets.json[/cyan] "
            "or dilute [cyan]scoring.py[/cyan] instead of fixing hardware bottlenecks.",
            box=box.ROUNDED,
            border_style="red",
        )
    )
    tbl = Table(
        title="Cryptographic Manifest Guard (check_integrity.py) vs. Reward-Hacking Tamper",
        box=box.ROUNDED,
        show_lines=True,
    )
    tbl.add_column("Frozen File", style="bold cyan")
    tbl.add_column("Simulated Agent Attack", style="white")
    tbl.add_column("Pinned Manifest SHA-256", style="green")
    tbl.add_column("Tampered File SHA-256", style="red")
    tbl.add_column("Referee Verdict", style="bold")

    for atk in data["attacks"]:
        verdict = (
            "[bold green]CAUGHT & REJECTED[/bold green]"
            if atk["caught"]
            else "[red]MISSED[/red]"
        )
        tbl.add_row(
            atk["file"],
            atk["attack"],
            atk["expected_sha256"][:16] + "...",
            atk["observed_sha256"][:16] + "...",
            verdict,
        )
    console.print(tbl)
    console.print(
        "[bold green]✔ Stage 1 Lesson:[/bold green] Because [cyan]harness/manifest.json[/cyan] locks all "
        f"[bold]{data['manifest_frozen_files']}[/bold] specification and referee files by SHA-256, "
        "[cyan]evaluate.py[/cyan] aborts at Step 0 whenever the yardstick is touched.\n"
    )


def render_verify(data: dict[str, Any]) -> None:
    rec = data["formulation_record"]
    console.print(
        Panel(
            "[bold green]LAB 01 (--mode verify): FORMULATION RECORD & FROZEN CONTRACT AUDIT[/bold green]\n"
            f"Verified [bold]{rec['frozen_file_count']}/35[/bold] frozen files in [cyan]nanochip/kpu/harness/manifest.json[/cyan] "
            f"(integrity_ok=[bold green]{rec['integrity_ok']}[/bold green]).",
            box=box.ROUNDED,
            border_style="green",
        )
    )

    t1 = Table(
        title="1. Frozen Boundary Inventory (Immutable Referee & Spec Files)",
        box=box.ROUNDED,
    )
    t1.add_column("Category", style="cyan")
    t1.add_column("Frozen File Count", justify="right", style="bold white")
    for cat, cnt in rec["frozen_breakdown"].items():
        t1.add_row(cat, str(cnt))
    t1.add_row(
        "[bold]Total Cryptographically Pinned Files[/bold]",
        f"[bold green]{rec['frozen_file_count']}[/bold green]",
    )
    console.print(t1)

    c = rec["hard_constraints_C"]
    th = rec["legal_design_space_Theta"]
    t2 = Table(
        title="2. Formal Architecture 2.0 Formulation Record: Frozen Constraints (C) vs. Legal Design Space (Theta)",
        box=box.ROUNDED,
        show_lines=True,
    )
    t2.add_column("Dimension", style="bold yellow", width=24)
    t2.add_column("Frozen Contract (C, M) — Immutable", style="cyan", width=38)
    t2.add_column("Legal Agent Design Space (Theta) — Mutable", style="green", width=38)

    t2.add_row(
        "Timing & Clock",
        f"{c['technology']} @ {c['target_freq_mhz']} MHz ({c['target_period_ns']} ns period)",
        "Pipeline depth, FSM partitioning, ABC fanout-friendly topology",
    )
    t2.add_row(
        "Area & Storage",
        f"Logic + Macros <= {c['logic_area_budget_mm2']} mm^2\nSRAM <= {c['onchip_sram_budget_mib']} MiB (macros @ 1 Mbit/mm^2)",
        "39 msh_sram/msh_rom instances (0.861 MiB), dual-parity qacc banking, 16 KiB hq shadow cache",
    )
    t2.add_row(
        "External Memory",
        f"{c['dram_port_bytes_per_cycle']} B/cycle (128-bit), >= 24-cycle read latency",
        "msh_fetch.v 256-deep credit FIFO, 2-beat stream pops, posted writes",
    )
    t2.add_row(
        "Numeric & Functional",
        f"float32 reference/model.py\ncos_min >= {c['cos_pass_min']}, pooled argmax >= {c['argmax_pass_pooled']}",
        f"{th['numeric_freedom']}\nBit-exact twin: {th['selfmodel_twin']}",
    )
    t2.add_row(
        "RTL Deliverables",
        f"Top module msh_chip_top, lint warnings <= {c['lint_max_warnings']}, 0 latches",
        f"{th['rtl_module_count']} Verilog modules in rtl/filelist.f:\n"
        + ", ".join(os.path.basename(m) for m in th["rtl_modules"]),
    )
    console.print(t2)
    render_sightline(data["cross_stack_sightline"])
    console.print()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Lab 01: Stage 1 Formulate — Locking the Study Contract"
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
        help="Run challenge mode non-interactively (evaluates naive and winning attempts)",
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
        return 0 if res["all_tampering_caught"] else 1

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

    # summary mode runs break, challenge (auto), and verify
    b_res = run_break()
    c_res = run_challenge(auto=True)
    v_res = run_verify()
    combined = {
        "lab": "01-formulate",
        "stage": "1. Formulate",
        "passed": (
            b_res["all_tampering_caught"] and c_res["passed"] and v_res["passed"]
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
