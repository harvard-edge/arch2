#!/usr/bin/env python3
"""Master runner for the 6 Progressive Architecture 2.0 Lifecycle Labs (nanochip/labs/).

Executes Labs 01 through 06 in sequence, prints a unified scoreboard, and writes
nanochip/labs/workbench_summary.json.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any

import yaml
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

LAB_DIRS = [
    "01-formulate",
    "02-explore",
    "03-implement",
    "04-evaluate",
    "05-interpret",
    "06-commit",
]

console = Console()


def _load_lab_module(slug: str, script_path: Path):
    mod_name = f"nanochip_lab_{slug.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(mod_name, script_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_all_labs(mode: str = "summary", emit_json: bool = False) -> int:
    results: list[dict[str, Any]] = []
    t0_all = time.time()

    if not emit_json:
        console.print(
            Panel(
                "[bold cyan]ARCHITECTURE 2.0 — NANOCHIP 6-STAGE PROGRESSIVE LAB CURRICULUM[/bold cyan]\n"
                "Executing all 6 lifecycle labs ([white]1. Formulate -> 2. Explore -> 3. Implement -> "
                "4. Evaluate -> 5. Interpret -> 6. Commit[/white]) against [bold]MoonshotAI/nano-kpu[/bold].",
                box=box.ROUNDED,
                border_style="bright_blue",
            )
        )

    all_passed = True
    for slug in LAB_DIRS:
        lab_dir = HERE / slug
        contract = yaml.safe_load(
            (lab_dir / "contract.yaml").read_text(encoding="utf-8")
        )
        script = lab_dir / "lab.py"

        t0 = time.time()
        mod = _load_lab_module(slug, script)
        if mode == "break":
            b_res = mod.run_break()
            if not emit_json:
                mod.render_break(b_res)
            ok = bool(
                b_res.get("all_tampering_caught")
                or b_res.get("rejected_before_rtl_sim")
                or b_res.get("all_bugs_caught_on_row_0")
                or b_res.get("all_adversarial_checks_verified")
                or b_res.get("blind_loop_failed_on_structural_walls")
                or b_res.get("rubber_stamp_rejected")
            )
            payload: dict[str, Any] = b_res
        elif mode == "verify":
            v_res = mod.run_verify()
            if not emit_json:
                mod.render_verify(v_res)
            ok = bool(v_res.get("passed"))
            payload = v_res
        else:
            b_res = mod.run_break()
            v_res = mod.run_verify()
            if not emit_json:
                mod.render_break(b_res)
                mod.render_verify(v_res)
            b_ok = bool(
                b_res.get("all_tampering_caught")
                or b_res.get("rejected_before_rtl_sim")
                or b_res.get("all_bugs_caught_on_row_0")
                or b_res.get("all_adversarial_checks_verified")
                or b_res.get("blind_loop_failed_on_structural_walls")
                or b_res.get("rubber_stamp_rejected")
            )
            ok = b_ok and bool(v_res.get("passed"))
            payload = {
                "lab": slug,
                "stage": contract.get("stage"),
                "passed": ok,
                "break_test": b_res,
                "verify_test": v_res,
            }

        dt = round(time.time() - t0, 2)
        all_passed = all_passed and ok

        results.append(
            {
                "lab_id": contract.get("lab_id"),
                "slug": slug,
                "stage": contract.get("stage"),
                "title": contract.get("title"),
                "book_chapters": contract.get("book_chapters", []),
                "passed": ok,
                "elapsed_sec": dt,
                "details": payload,
            }
        )

    summary_doc = {
        "curriculum": "Architecture 2.0 nanochip 6-Stage Progressive Labs",
        "target_artifact": "MoonshotAI/nano-kpu (msh_chip_top, Kimi K3)",
        "mode": mode,
        "all_passed": all_passed,
        "total_elapsed_sec": round(time.time() - t0_all, 2),
        "labs": results,
    }

    summary_path = HERE / "workbench_summary.json"
    summary_path.write_text(json.dumps(summary_doc, indent=2), encoding="utf-8")

    if emit_json:
        print(json.dumps(summary_doc, indent=2))
    else:
        tbl = Table(
            title="Architecture 2.0 nanochip — 6-Stage Curriculum Master Scoreboard",
            box=box.ROUNDED,
            show_lines=True,
        )
        tbl.add_column("Lab", style="bold cyan", width=14)
        tbl.add_column("Stage", style="bold yellow", width=16)
        tbl.add_column("Title", style="white", width=44)
        tbl.add_column("Time", justify="right", width=8)
        tbl.add_column("Verdict", justify="center", width=12)

        for r in results:
            verdict = (
                "[bold green]PASS[/bold green]"
                if r["passed"]
                else "[bold red]FAIL[/bold red]"
            )
            tbl.add_row(
                r["slug"], r["stage"], r["title"], f"{r['elapsed_sec']:.2f}s", verdict
            )

        console.print(tbl)
        console.print(
            f"[dim]Wrote structured receipt to [cyan]{summary_path.relative_to(REPO_ROOT)}[/cyan] "
            f"in {summary_doc['total_elapsed_sec']:.2f}s.[/dim]\n"
        )

    return 0 if all_passed else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Run all 6 Architecture 2.0 nanochip labs")
    ap.add_argument("--mode", choices=["verify", "break", "summary"], default="summary")
    ap.add_argument("--json", action="store_true", help="Emit JSON summary to stdout")
    ap.add_argument(
        "--no-visual", action="store_true", help="Compatibility flag for CLI runners"
    )
    ap.add_argument(
        "--demo", action="store_true", help="Compatibility flag for demo mode"
    )
    args = ap.parse_args()
    return run_all_labs(mode=args.mode, emit_json=args.json)


if __name__ == "__main__":
    sys.exit(main())
