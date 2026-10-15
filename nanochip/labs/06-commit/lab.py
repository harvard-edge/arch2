#!/usr/bin/env python3
"""Lab 06 (Stage 6: Commit) — Signoff Governance, Proxy Gaps & The Design-Loop Card v2.0."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cli.arch2 import card_validation_findings  # noqa: E402

console = Console()

CARD_PATH = REPO_ROOT / "nanochip" / "cards" / "nano-kpu-study-card.yaml"
REPLAY_SCRIPT = REPO_ROOT / "nanochip" / "cards" / "replay.py"


def run_break() -> dict[str, Any]:
    """Construct an unguarded 'rubber-stamp' card in a temporary file that:
    1. Claims full silicon tapeout readiness from pre-layout Yosys synthesis (ignoring
       blackboxed msh_sram/msh_rom macros, statistical 5K_hvratio_1_1 wireload vs routed
       metal parasitics, and single-corner STA),
    2. Assigns the accountable 'commit' decision to the AI model without a declared
       commit/reject decision right or valid SHA-256 evidence bindings.
    Show how both ./arch2 validate card and the Proxy-Gap Governance Audit reject it."""
    rubber_stamp_card = {
        "schema_version": "2.0",
        "design_loop_card": {
            "card_id": "flawed-rubber-stamp-tapeout-card",
            "profiles": {
                "context": "complete",
                "inspectability": "partial",  # Missing profile_gaps.inspectability!
                "replay": "not_claimed",
                "independent_review": "not_claimed",
                "disclosure": "not_claimed",
                "decision_rights": "complete",
            },
            "profile_gaps": {},
            "intent": {
                "objective": "Ship msh_chip_top directly to foundry tapeout from Yosys pre-layout synthesis.",
                "constraints": ["Run Yosys once."],
                "non_goals": ["None — claiming full silicon tapeout signoff!"],
            },
            "task": {
                "kind": "rubber_stamp_signoff",
                "description": "Conflate pre-layout wireload synthesis with manufacturable GDSII tapeout.",
            },
            "design_space": {
                "legal": ["rtl/*"],
                "invalid": ["none"],
                "deferred": ["none"],
            },
            "claims": [
                {
                    "claim_id": "claim-tapeout-ready",
                    "claim_type": "architecture_outcome",
                    "statement": "msh_chip_top is 100% ready for TSMC/SkyWater foundry tapeout at 162.2 MHz.",
                    "baseline_or_comparator": "Pre-layout Yosys synthesis.",
                    "outcome": "6.166 ns pre-layout delay equals guaranteed post-route silicon timing.",
                    "scope": "Full commercial production.",
                    "non_claims": ["None"],
                    "status": "supported",
                    "evidence_refs": ["non-existent-evidence-id"],
                }
            ],
            "evidence": {"records": []},
            "failed_or_rejected": [],
            "gates": [
                {
                    "gate_id": "gate-rubber-stamp",
                    "category": "timing",
                    "criterion": "Yosys synthesis finishes.",
                    "result": "passed",
                    "authority_id": "kimi-k3-autonomous-architect",  # Lacks reject right!
                    "waiver_rule": {"allowed": False},
                    "evidence_refs": ["non-existent-evidence-id"],
                    "disposition": "continue",
                }
            ],
            "decision_rights": [
                {
                    "action": "propose",
                    "holder_id": "kimi-k3-autonomous-architect",
                    "holder_type": "model",
                    "scope": "All",
                    "conditions": "None",
                }
                # Missing execute, reject, waive, recommend, commit!
            ],
            "accountable_decision": {
                "status": "authorized",
                "holder_id": "kimi-k3-autonomous-architect",
                "action": "Authorize immediate foundry tapeout without P&R.",
                "rationale": "Yosys stime reported 6.166 ns.",
                "claim_refs": ["claim-tapeout-ready"],
                "authorized_scope": "Unconditional silicon fabrication.",
                "recorded_at": "2026-10-15T00:00:00Z",
                "reopen_conditions": ["Never"],
            },
        },
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", dir=str(CARD_PATH.parent), delete=False
    ) as tmp:
        yaml.safe_dump(rubber_stamp_card, tmp)
        tmp_path = Path(tmp.name)

    try:
        findings = card_validation_findings(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    proxy_gap_violations = [
        {
            "proxy_gap": "1. Statistical Wireload (5K_hvratio_1_1) vs. Post-Route RC Parasitics",
            "rubber_stamp_error": "Treats pre-layout topological delay (6.166 ns) as post-route signoff without placement, global/detailed routing, or SPEF RC extraction.",
        },
        {
            "proxy_gap": "2. Blackboxed Memory Macros (39 msh_sram / msh_rom instances)",
            "rubber_stamp_error": "Ignores that msh_sram_bb.v has zero internal Liberty setup/hold/clk-to-Q timing arcs and zero physical routing blockage modeling.",
        },
        {
            "proxy_gap": "3. Single-Corner Nominal Typical STA vs. Multi-Corner PVT & CTS",
            "rubber_stamp_error": "Evaluates only Nangate45 typical.lib with ideal 0-skew clock; omits SS setup corner, FF hold corner after CTS, and IR drop.",
        },
        {
            "proxy_gap": "4. AI Self-Certification (Generator == Committer)",
            "rubber_stamp_error": "Lets the generator model (kimi-k3) hold 'commit' and 'reject' rights without independent human signoff or SHA-256 replay packets.",
        },
    ]

    return {
        "mode": "break",
        "stage": "6. Commit",
        "schema_and_semantic_error_count": len(findings),
        "validator_findings": [
            {"code": f.code, "location": f.location, "message": f.message}
            for f in findings
        ],
        "proxy_gap_violations": proxy_gap_violations,
        "rubber_stamp_rejected": len(findings) >= 3,
        "verdict": "REJECTED_BY_SCHEMA_V2_AND_PROXY_GAP_GOVERNANCE",
    }


def run_verify() -> dict[str, Any]:
    """Validate nanochip/cards/nano-kpu-study-card.yaml using card_validation_findings
    (and ./arch2 validate card) + run nanochip/cards/replay.py verify-all."""
    findings = card_validation_findings(CARD_PATH)

    p_cli = subprocess.run(
        [
            str(REPO_ROOT / "arch2"),
            "validate",
            "card",
            "nanochip/cards/nano-kpu-study-card.yaml",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    p_replay = subprocess.run(
        [sys.executable, str(REPLAY_SCRIPT), "verify-all"],
        cwd=str(CARD_PATH.parent),
        capture_output=True,
        text=True,
    )

    card_doc = yaml.safe_load(CARD_PATH.read_text(encoding="utf-8"))
    dlc = card_doc["design_loop_card"]

    summary = {
        "card_id": dlc["card_id"],
        "schema_version": card_doc["schema_version"],
        "profiles": dlc["profiles"],
        "profile_gaps": dlc["profile_gaps"],
        "claims_count": len(dlc["claims"]),
        "evidence_records_count": len(dlc["evidence"]["records"]),
        "failed_or_rejected_count": len(dlc["failed_or_rejected"]),
        "gates_count": len(dlc["gates"]),
        "gates_all_passed": all(g["result"] == "passed" for g in dlc["gates"]),
        "decision_rights_count": len(dlc["decision_rights"]),
        "accountable_decision": {
            "status": dlc["accountable_decision"]["status"],
            "holder_id": dlc["accountable_decision"]["holder_id"],
            "authorized_scope": dlc["accountable_decision"]["authorized_scope"],
            "reopen_conditions": dlc["accountable_decision"]["reopen_conditions"],
        },
        "replay_validation_status": dlc["replay"]["validation_status"],
    }

    passed = (
        len(findings) == 0
        and p_cli.returncode == 0
        and p_replay.returncode == 0
        and summary["gates_all_passed"]
    )
    return {
        "mode": "verify",
        "stage": "6. Commit",
        "passed": passed,
        "arch2_validate_card_stdout": p_cli.stdout.strip(),
        "replay_verify_ok": p_replay.returncode == 0,
        "card_summary": summary,
    }


def render_break(data: dict[str, Any]) -> None:
    console.print(
        Panel(
            "[bold red]LAB 06 (--mode break): AUDITING A FLAWED 'RUBBER-STAMP' SILICON TAPEOUT CARD[/bold red]\n"
            "Testing what happens when a card claims foundry tapeout readiness from pre-layout Yosys synthesis "
            "and lets the AI generator certify its own commitment.",
            box=box.ROUNDED,
            border_style="red",
        )
    )

    t1 = Table(
        title="1. Architecture 2.0 Proxy-to-Purpose Governance Audit",
        box=box.ROUNDED,
        show_lines=True,
    )
    t1.add_column("Physical / Governance Proxy Gap", style="bold cyan", width=36)
    t1.add_column("Why the Rubber-Stamp Card Is Invalid", style="red")
    for v in data["proxy_gap_violations"]:
        t1.add_row(v["proxy_gap"], v["rubber_stamp_error"])
    console.print(t1)

    t2 = Table(
        title=f"2. Automated ./arch2 validate card v2.0 Rejection Receipt ({data['schema_and_semantic_error_count']} errors caught)",
        box=box.ROUNDED,
    )
    t2.add_column("Rule Code", style="bold red")
    t2.add_column("JSON Path", style="yellow")
    t2.add_column("Validation Error", style="white")
    for f in data["validator_findings"]:
        t2.add_row(f["code"], f["location"].split(":")[-1], f["message"])
    console.print(t2)
    console.print()


def render_verify(data: dict[str, Any]) -> None:
    cs = data["card_summary"]
    console.print(
        Panel(
            "[bold green]LAB 06 (--mode verify): DESIGN-LOOP CARD v2.0 VALIDATION & SIGNOFF SUMMARY[/bold green]\n"
            f"[cyan]./arch2 validate card[/cyan]: [bold green]{data['arch2_validate_card_stdout']}[/bold green]\n"
            f"[cyan]replay.py verify-all[/cyan]: [bold green]{'PASS (replay_verified)' if data['replay_verify_ok'] else 'FAIL'}[/bold green]",
            box=box.ROUNDED,
            border_style="green",
        )
    )

    t = Table(
        title=f"Signed Design-Loop Card v2.0 Summary ({cs['card_id']})",
        box=box.ROUNDED,
        show_lines=True,
    )
    t.add_column("Governance Dimension", style="bold cyan", width=28)
    t.add_column("Verified Binding in nano-kpu-study-card.yaml", style="green")

    profiles_str = ", ".join(f"{k}={v}" for k, v in cs["profiles"].items())
    t.add_row(
        "Schema Version & Profiles",
        f"v{cs['schema_version']} | {profiles_str} (0 profile gaps)",
    )
    t.add_row(
        "Claims & SHA-256 Evidence",
        f"{cs['claims_count']} supported claims bound to {cs['evidence_records_count']} SHA-256 verified evidence packets",
    )
    t.add_row(
        "Predeclared Rejection Gates",
        f"{cs['gates_count']}/{cs['gates_count']} passed (manifest, audit/lint, cos/argmax, selfmodel, randreset/2x-lat, timing, area)",
    )
    t.add_row(
        "Retained Negative Results",
        f"{cs['failed_or_rejected_count']} rejected candidates/turns recorded (Turn 1 -> Implement, Turn 2 -> Explore, Turn 3 -> Formulate, Unbuffered STA)",
    )
    t.add_row(
        "Separated Decision Rights",
        f"{cs['decision_rights_count']} explicit rights: propose/recommend (kimi-k3), execute/reject (frozen-harness), waive/commit (arch2-signoff-architect)",
    )
    t.add_row(
        "Authorized Commitment Scope",
        f"[bold white]{cs['accountable_decision']['authorized_scope']}[/bold white]\n"
        f"Holder: {cs['accountable_decision']['holder_id']} ({cs['accountable_decision']['status']})",
    )
    t.add_row(
        "Mandatory Reopen Conditions",
        " • " + "\n • ".join(cs["accountable_decision"]["reopen_conditions"]),
    )
    console.print(t)
    console.print()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Lab 06: Stage 6 Commit — Signoff Governance & Design-Loop Card v2.0"
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
        return 0 if res["rubber_stamp_rejected"] else 1

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
        "lab": "06-commit",
        "stage": "6. Commit",
        "passed": b_res["rubber_stamp_rejected"] and v_res["passed"],
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
