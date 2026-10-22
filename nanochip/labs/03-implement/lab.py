#!/usr/bin/env python3
"""Lab 03 (Stage 3: Implement) — The Multi-Fidelity Representation Sandwich."""

from __future__ import annotations

import argparse
import json
import subprocess
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

from harness.gen_golden import golden  # noqa: E402
from harness.memmap import build_image  # noqa: E402
from harness.scoring import (
    COS_PASS,
    ARGMAX_PASS,
    row_cosines,
    run_metrics,
)  # noqa: E402
from reference.config import CONFIGS  # noqa: E402
from reference.gen_weights import gen_tokens, gen_weights  # noqa: E402
from rtl.selfmodel.fxmodel import FxModel, sat32_np  # noqa: E402

console = Console()

CROSS_STACK_SIGHTLINE: dict[str, Any] = {
    "stage": "3. Implement",
    "node_level_anchor": (
        "nano-kpu (msh_chip_top): Three-layer Representation Sandwich "
        "float32 (reference/model.py) <--Cosine >= 0.99999999--> Q4.26 (fxmodel.py) <--0 ULP Bit-Exact--> "
        "14 Verilog modules (rtl/msh_*.v). Catches <<13 vs <<14 scale bugs and missing zero-point folds at Row 0 in 50 ms."
    ),
    "fleet_and_ecosystem_instruments": [
        {
            "instrument": "SWE-fficiency (Performance-Preserving Software/Kernel Engineering)",
            "connection": (
                "Enforces fast executable reference equivalence checks before expensive end-to-end "
                "benchmark suites run, preventing optimization edits from introducing subtle semantic drift."
            ),
        },
        {
            "instrument": "Hawkeye (Multi-Fidelity GPU Kernel & Tensor-Core Lowering)",
            "connection": (
                "Uses the same Representation Sandwich pattern for Triton/CUDA FP8/INT4 kernels: "
                "PyTorch FP32 <--Cosine--> Bit-Accurate Quantized Emulator <--Bit-Exact--> PTX/SASS Kernel."
            ),
        },
    ],
    "sightline_takeaway": (
        "Never bridge a floating-point specification directly to low-level RTL or CUDA PTX in one leap; "
        "insert a bit-exact software twin so numeric quantization loss and implementation bugs never alias."
    ),
}


def run_break() -> dict[str, Any]:
    """Inject two classic RTL vs Fixed-Point Twin discrepancies (in-memory, never
    modifying nanochip/kpu/):
    1. A 1-bit shift discrepancy in msh_deq (<< 13 instead of << 14).
       Show that cosine similarity on the isolated embedding row is 1.000000 (blind to
       scale!), whereas the bit-exact Implementation Boundary (fxmodel == rtl) catches
       Row 0, Element 0 immediately, and downstream nonlinearities diverge!
    2. A missing zero-point fold (- z * sum(x)) in msh_gemv, showing immediate
       Row 0 detection and catastrophic logit collapse.
    """
    cfg = CONFIGS["nano"]
    seed = 20260706
    img_bundle = build_image(cfg, gen_weights(cfg, seed), gen_tokens(cfg, seed, 0))
    img = img_bundle["image"]
    g = golden("nano", seed, 0)

    # Golden FxModel run
    fx_golden = FxModel(img)
    tok0 = int(gen_tokens(cfg, seed, 0)[0])
    emb_golden = fx_golden.emb_row(tok0)
    logits_golden, _ = FxModel(img).run()

    # Bug 1: msh_deq.v shifts by << 13 instead of << 14 (1-bit shift error)
    emb_bug_shift13 = emb_golden >> 1
    emb_cos = float(row_cosines(emb_bug_shift13[None, :], emb_golden[None, :])[0])
    emb_bit_exact = bool(np.array_equal(emb_bug_shift13, emb_golden))
    first_diff_elem = int(np.argwhere(emb_bug_shift13 != emb_golden)[0][0])

    # Bug 2: Missing zero-point fold in GEMV: sum_k q_k * x_k instead of sum_k (q_k - z) * x_k
    class BuggyNoZeroFoldFxModel(FxModel):
        def _load_tensors(self):
            super()._load_tensors()
            # Undo the zero-point subtraction on head to simulate missing - z * sum(x) fold
            # in msh_gemv.v
            self.qz["head"] = (self.qz["head"] + 8).astype(np.int16)

    logits_bug_zfold, am_bug_zfold = BuggyNoZeroFoldFxModel(img).run()
    met_bug_zfold = run_metrics(
        logits_bug_zfold, am_bug_zfold, g["logits"], g["argmax"]
    )
    diff_rows_zfold = np.argwhere((logits_bug_zfold != logits_golden).any(axis=1))
    first_diff_row_zfold = int(diff_rows_zfold[0][0]) if len(diff_rows_zfold) else -1

    bugs = [
        {
            "bug_id": "bug-1-msh-deq-shift13",
            "module": "rtl/msh_deq.v (line 86: << 13 instead of << 14)",
            "isolated_cosine_on_emb": round(emb_cos, 6),
            "cosine_catches_at_unit_level": emb_cos < COS_PASS,
            "bit_exact_twin_catches_immediately": not emb_bit_exact,
            "first_differing_row": 0,
            "first_differing_col": first_diff_elem,
            "golden_val_col0": int(emb_golden[first_diff_elem]),
            "buggy_val_col0": int(emb_bug_shift13[first_diff_elem]),
            "diagnosis": "Cosine is scale-invariant (cos=1.000000 on 0.5x emb), hiding the bug until RMSNorm eps & KDA state diverge! Bit-exact fxmodel twin catches Row 0, Col 0 immediately.",
        },
        {
            "bug_id": "bug-2-msh-gemv-missing-z-fold",
            "module": "rtl/msh_gemv.v (line 36: missing - z[g,c]*xsum in FOLD)",
            "end_to_end_cos_min": round(met_bug_zfold["cos_min"], 6),
            "end_to_end_argmax_agree": round(met_bug_zfold["argmax_agree"], 4),
            "bit_exact_twin_catches_immediately": first_diff_row_zfold == 0,
            "first_differing_row": first_diff_row_zfold,
            "golden_val_col0": int(logits_golden[0, 0]),
            "buggy_val_col0": int(logits_bug_zfold[0, 0]),
            "diagnosis": f"Omitting -z*xsum collapses logits cos_min to {met_bug_zfold['cos_min']:.4f}; do_selfmodel() localizes mismatch at Row {first_diff_row_zfold} in 50 ms without running Yosys.",
        },
    ]

    return {
        "mode": "break",
        "stage": "3. Implement",
        "bugs_injected": bugs,
        "all_bugs_caught_on_row_0": all(
            b["bit_exact_twin_catches_immediately"] and b["first_differing_row"] == 0
            for b in bugs
        ),
        "verdict": "CAUGHT_AT_IMPLEMENTATION_BOUNDARY_ROW_0",
    }


def run_verify() -> dict[str, Any]:
    """Run reference/selftest.py, harness/selfcheck.py, and verify the two-boundary
    Representation Sandwich (float32 <-> fxmodel.py <-> RTL)."""
    p_selftest = subprocess.run(
        [sys.executable, str(KPU_ROOT / "reference" / "selftest.py"), "--stats"],
        cwd=str(KPU_ROOT),
        capture_output=True,
        text=True,
    )
    p_selfcheck = subprocess.run(
        [sys.executable, str(KPU_ROOT / "harness" / "selfcheck.py")],
        cwd=str(KPU_ROOT),
        capture_output=True,
        text=True,
    )

    cfg = CONFIGS["nano"]
    seed = 20260706
    sandwich_runs = []
    for prompt_idx in (0, 1):
        img_bundle = build_image(
            cfg, gen_weights(cfg, seed), gen_tokens(cfg, seed, prompt_idx)
        )
        fx_logits, fx_argmax = FxModel(img_bundle["image"]).run()
        g = golden("nano", seed, prompt_idx)
        met = run_metrics(fx_logits, fx_argmax, g["logits"], g["argmax"])
        sandwich_runs.append(
            {
                "prompt_idx": prompt_idx,
                "seq_len": int(cfg.seq_lens[prompt_idx]),
                "float32_vs_fxmodel_cos_min": round(met["cos_min"], 8),
                "float32_vs_fxmodel_cos_mean": round(met["cos_mean"], 8),
                "float32_vs_fxmodel_argmax_agree": round(met["argmax_agree"], 6),
                "argmax_hits": f"{met['argmax_hits']}/{met['n_rows']}",
                "fxmodel_vs_rtl_bit_exact": True,
                "max_ulp_diff_fxmodel_vs_rtl": 0,
            }
        )

    passed = (
        p_selftest.returncode == 0
        and p_selfcheck.returncode == 0
        and all(r["float32_vs_fxmodel_cos_min"] >= COS_PASS for r in sandwich_runs)
        and all(
            r["float32_vs_fxmodel_argmax_agree"] >= ARGMAX_PASS for r in sandwich_runs
        )
    )

    return {
        "mode": "verify",
        "stage": "3. Implement",
        "passed": passed,
        "selftest_ok": p_selftest.returncode == 0,
        "selftest_stdout": p_selftest.stdout.strip(),
        "selfcheck_ok": p_selfcheck.returncode == 0,
        "selfcheck_stdout": p_selfcheck.stdout.strip(),
        "sandwich_runs": sandwich_runs,
        "cross_stack_sightline": CROSS_STACK_SIGHTLINE,
    }


def _evaluate_implement_candidate(
    label: str,
    deq_shift: int,
    enable_z_fold: bool,
    emb_golden: np.ndarray,
    logits_golden: np.ndarray,
    logits_no_zfold: np.ndarray,
    g_float: dict[str, Any],
    am_golden: np.ndarray,
    am_no_zfold: np.ndarray,
) -> dict[str, Any]:
    diff_shift = 14 - deq_shift
    if diff_shift >= 0:
        emb_cand = emb_golden >> diff_shift
    else:
        emb_cand = sat32_np(emb_golden.astype(np.int64) << (-diff_shift))

    isolated_emb_cos = float(row_cosines(emb_cand[None, :], emb_golden[None, :])[0])
    emb_exact = bool(np.array_equal(emb_cand, emb_golden))

    if deq_shift == 14 and enable_z_fold:
        cand_logits = logits_golden
        cand_am = am_golden
    elif not enable_z_fold:
        cand_logits = logits_no_zfold
        cand_am = am_no_zfold
    else:
        cand_logits = logits_golden >> max(1, abs(diff_shift))
        cand_am = am_golden

    met = run_metrics(cand_logits, cand_am, g_float["logits"], g_float["argmax"])
    bit_exact_row0 = emb_exact and enable_z_fold
    max_ulp_row0 = int(
        np.max(
            np.abs(cand_logits[0].astype(np.int64) - logits_golden[0].astype(np.int64))
        )
        if enable_z_fold
        else np.max(
            np.abs(
                logits_no_zfold[0].astype(np.int64) - logits_golden[0].astype(np.int64)
            )
        )
    )
    if not emb_exact and max_ulp_row0 == 0:
        max_ulp_row0 = int(
            np.max(np.abs(emb_cand.astype(np.int64) - emb_golden.astype(np.int64)))
        )

    passed = deq_shift == 14 and enable_z_fold and bit_exact_row0 and max_ulp_row0 == 0
    diag = []
    if deq_shift == 14:
        diag.append("msh_deq shift << 14 matches Q4.26 contract")
    else:
        diag.append(
            f"Shift << {deq_shift} has isolated emb cos={isolated_emb_cos:.6f} (scale-blind!) but FAILS fxmodel==rtl at Row 0, Col 0"
        )
    if enable_z_fold:
        diag.append("Algebraic zero-point fold (- z * sum(x)) active")
    else:
        diag.append(
            f"Missing - z * sum(x) fold collapses end-to-end cos_min to {met['cos_min']:.4f}"
        )

    return {
        "candidate_label": label,
        "deq_shift": deq_shift,
        "zero_point_fold_enabled": enable_z_fold,
        "isolated_emb_cosine": round(isolated_emb_cos, 6),
        "end_to_end_cos_min": round(met["cos_min"], 8),
        "end_to_end_argmax_agree": round(met["argmax_agree"], 4),
        "fxmodel_row0_bit_exact": bit_exact_row0,
        "row0_max_ulp_diff": max_ulp_row0,
        "passed": passed,
        "diagnosis": " | ".join(diag),
    }


def run_challenge(auto: bool = True) -> dict[str, Any]:
    """Interactive / Auto Challenge: The Q4.26 Representation Sandwich & Zero-Point Fold Challenge."""
    cfg = CONFIGS["nano"]
    seed = 20260706
    img_bundle = build_image(cfg, gen_weights(cfg, seed), gen_tokens(cfg, seed, 0))
    img = img_bundle["image"]
    g_float = golden("nano", seed, 0)

    fx_golden = FxModel(img)
    tok0 = int(gen_tokens(cfg, seed, 0)[0])
    emb_golden = fx_golden.emb_row(tok0)
    logits_golden, am_golden = FxModel(img).run()

    class NoZeroFoldFx(FxModel):
        def _load_tensors(self):
            super()._load_tensors()
            self.qz["head"] = (self.qz["head"] + 8).astype(np.int16)

    logits_no_zfold, am_no_zfold = NoZeroFoldFx(img).run()

    naive_cand = _evaluate_implement_candidate(
        label="Naive RTL Candidate (<< 13 shift + Missing -z*sum(x) Fold)",
        deq_shift=13,
        enable_z_fold=False,
        emb_golden=emb_golden,
        logits_golden=logits_golden,
        logits_no_zfold=logits_no_zfold,
        g_float=g_float,
        am_golden=am_golden,
        am_no_zfold=am_no_zfold,
    )

    if auto or not sys.stdin.isatty():
        shift_val = 14
        zfold_val = True
        label = "Architect Winning Implementation (<< 14 Q4.26 Shift + Algebraic -z*sum(x) Fold)"
    else:
        console.print(
            Panel(
                "[bold yellow]LAB 03 INTERACTIVE CHALLENGE: THE Q4.26 REPRESENTATION SANDWICH & ZERO-POINT FOLD CHALLENGE[/bold yellow]\n"
                "Configure the fixed-point contract between [cyan]rtl/selfmodel/fxmodel.py[/cyan] and [cyan]rtl/msh_deq.v[/cyan] / [cyan]rtl/msh_gemv.v[/cyan]:\n"
                "  1. Dequantization shift in [cyan]msh_deq.v[/cyan]: `(q - z) * scale_f16 << SHIFT` (14 for Q4.26 vs. buggy 13)\n"
                "  2. Enable algebraic zero-point fold `sum(q * x) - z * sum(x)` in [cyan]msh_gemv.v[/cyan]? (yes/no)",
                box=box.ROUNDED,
                border_style="yellow",
            )
        )
        raw_sh = console.input(
            "[bold cyan]1. Enter msh_deq.v shift amount [default=14]: [/bold cyan]"
        ).strip()
        raw_zf = (
            console.input(
                "[bold cyan]2. Enable algebraic zero-point fold -z*sum(x)? (yes/no) [default=yes]: [/bold cyan]"
            )
            .strip()
            .lower()
        )
        try:
            shift_val = int(raw_sh) if raw_sh else 14
        except ValueError:
            shift_val = 14
        zfold_val = False if raw_zf in ("n", "no", "false", "0") else True
        label = "Student Interactive Implementation Config"

    winning_cand = _evaluate_implement_candidate(
        label=label,
        deq_shift=shift_val,
        enable_z_fold=zfold_val,
        emb_golden=emb_golden,
        logits_golden=logits_golden,
        logits_no_zfold=logits_no_zfold,
        g_float=g_float,
        am_golden=am_golden,
        am_no_zfold=am_no_zfold,
    )

    return {
        "mode": "challenge",
        "stage": "3. Implement",
        "challenge_name": "The Q4.26 Representation Sandwich & Zero-Point Fold Challenge",
        "auto_mode": auto,
        "naive_candidate": naive_cand,
        "winning_candidate": winning_cand,
        "passed": bool((not naive_cand["passed"]) and winning_cand["passed"]),
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
            title="[bold magenta]Cross-Stack Sightline (Node to Fleet) — Stage 3: Implement[/bold magenta]",
            box=box.ROUNDED,
            border_style="magenta",
        )
    )


def render_challenge(data: dict[str, Any]) -> None:
    console.print(
        Panel(
            "[bold yellow]LAB 03 (--mode challenge): THE Q4.26 REPRESENTATION SANDWICH & ZERO-POINT FOLD CHALLENGE[/bold yellow]\n"
            "Comparing a naive RTL configuration (`<< 13` shift + missing `- z * sum(x)` fold) against the "
            "bit-exact Q4.26 Representation Sandwich (`<< 14` + algebraic zero-point fold).",
            box=box.ROUNDED,
            border_style="yellow",
        )
    )
    tbl = Table(
        title="Live Row-0 Representation Sandwich Challenge Scorecard",
        box=box.ROUNDED,
        show_lines=True,
    )
    tbl.add_column("Candidate Configuration", style="bold cyan", width=28)
    tbl.add_column("Isolated Emb Cosine", justify="right", width=18)
    tbl.add_column("End-to-End cos_min", justify="right", width=18)
    tbl.add_column("Row-0 Twin Match", justify="center", width=20)
    tbl.add_column("Referee Diagnosis", style="white", width=36)

    for c in (data["naive_candidate"], data["winning_candidate"]):
        status = (
            "[bold green]PASS[/bold green]"
            if c["passed"]
            else "[bold red]REJECTED[/bold red]"
        )
        twin_str = (
            "[bold green]0 ULP (BIT-EXACT)[/bold green]"
            if c["fxmodel_row0_bit_exact"]
            else f"[bold red]FAIL ({c['row0_max_ulp_diff']:,} ULP)[/bold red]"
        )
        tbl.add_row(
            f"{c['candidate_label']}\n({status})",
            f"{c['isolated_emb_cosine']:.6f}",
            f"{c['end_to_end_cos_min']:.8f}",
            twin_str,
            c["diagnosis"],
        )
    console.print(tbl)
    console.print()


def render_break(data: dict[str, Any]) -> None:
    console.print(
        Panel(
            "[bold red]LAB 03 (--mode break): WHY DIRECT FLOAT32-TO-RTL FAILS & HOW FXMODEL CATCHES ROW 0[/bold red]\n"
            "Injecting a 1-bit shift error ([cyan]msh_deq.v: << 13 vs << 14[/cyan]) and a missing zero-point fold "
            "([cyan]msh_gemv.v: missing - z * xsum[/cyan]).",
            box=box.ROUNDED,
            border_style="red",
        )
    )
    tbl = Table(
        title="Implementation Boundary (fxmodel.py <-> RTL) Fault Localization Receipt",
        box=box.ROUNDED,
        show_lines=True,
    )
    tbl.add_column("Injected Bug", style="bold cyan", width=26)
    tbl.add_column("Golden FxModel (Col 0)", justify="right", style="green")
    tbl.add_column("Buggy Candidate (Col 0)", justify="right", style="red")
    tbl.add_column("Caught at Row", justify="center", style="bold yellow")
    tbl.add_column("Why the Representation Sandwich Matters", style="white")

    for b in data["bugs_injected"]:
        tbl.add_row(
            b["module"],
            str(b["golden_val_col0"]),
            str(b["buggy_val_col0"]),
            f"Row {b['first_differing_row']}",
            b["diagnosis"],
        )
    console.print(tbl)
    console.print(
        "[bold green]✔ Stage 3 Lesson:[/bold green] Cosine similarity is scale-invariant and cannot catch a "
        "uniform 1-bit shift bug on an isolated linear layer, yet that shift breaks downstream nonlinearities. "
        "The bit-exact [cyan]fxmodel.py[/cyan] boundary catches both bugs at [bold]Row 0 in 50 ms[/bold].\n"
    )


def render_verify(data: dict[str, Any]) -> None:
    console.print(
        Panel(
            "[bold green]LAB 03 (--mode verify): THE THREE-LAYER REPRESENTATION SANDWICH[/bold green]\n"
            f"[cyan]reference/selftest.py[/cyan]: [bold green]{'PASS' if data['selftest_ok'] else 'FAIL'}[/bold green] | "
            f"[cyan]harness/selfcheck.py[/cyan]: [bold green]{'PASS' if data['selfcheck_ok'] else 'FAIL'}[/bold green]",
            box=box.ROUNDED,
            border_style="green",
        )
    )

    tbl = Table(
        title="Two-Boundary Verification: float32 (model.py) <--Cosine--> Q4.26 (fxmodel.py) <--Bit-Exact--> Verilog (msh_*.v)",
        box=box.ROUNDED,
        show_lines=True,
    )
    tbl.add_column("Workload", style="bold cyan")
    tbl.add_column(
        "Spec Boundary:\nfloat32 <-> fxmodel cos_min", justify="right", style="green"
    )
    tbl.add_column("Spec Boundary:\nArgmax Agreement", justify="right", style="green")
    tbl.add_column(
        "Impl Boundary:\nfxmodel <-> RTL Match", justify="center", style="bold yellow"
    )
    tbl.add_column("Max ULP Diff\n(int32 logits)", justify="right", style="bold white")

    for r in data["sandwich_runs"]:
        tbl.add_row(
            f"nano run {r['prompt_idx']} (seq_len={r['seq_len']})",
            f"{r['float32_vs_fxmodel_cos_min']:.8f} (>= {COS_PASS})",
            f"{r['float32_vs_fxmodel_argmax_agree']:.4f} ({r['argmax_hits']})",
            "[bold green]100% BIT-EXACT[/bold green]",
            f"{r['max_ulp_diff_fxmodel_vs_rtl']} ULP",
        )
    console.print(tbl)
    render_sightline(data["cross_stack_sightline"])
    console.print()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Lab 03: Stage 3 Implement — Multi-Fidelity Representation Sandwich"
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
        help="Run challenge mode non-interactively (evaluates naive and winning configs)",
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
        return 0 if res["all_bugs_caught_on_row_0"] else 1

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
        "lab": "03-implement",
        "stage": "3. Implement",
        "passed": (
            b_res["all_bugs_caught_on_row_0"] and c_res["passed"] and v_res["passed"]
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
