#!/usr/bin/env python3
"""Lab 01 (Stage 1: Formulate) — Locking the Study Contract & Integrity Boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
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
    }


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
    console.print()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Lab 01: Stage 1 Formulate — Locking the Study Contract"
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
        return 0 if res["all_tampering_caught"] else 1

    if mode in ("verify", "inspect"):
        res = run_verify()
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            render_verify(res)
        return 0 if res["passed"] else 1

    # summary mode runs both break and verify
    b_res = run_break()
    v_res = run_verify()
    combined = {
        "lab": "01-formulate",
        "stage": "1. Formulate",
        "passed": b_res["all_tampering_caught"] and v_res["passed"],
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
