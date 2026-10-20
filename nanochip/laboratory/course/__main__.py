"""Command-line entry point for the cumulative Nanochip student workspace."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from ..contracts import ContractError
from .api import LabExecutionError, run_lab
from .workspace import course_status, init_workspace


_PENDING_PHYSICAL_CHECKS = {
    8: {"physical_receipt_binds_checked_source"},
    9: {"final_physical_acceptance_for_adapted_winner"},
}


def _has_unresolved_physical_check(lab_number: int, event) -> bool:
    """Classify only the course's explicit physical acceptance obligations as pending."""
    if not isinstance(event, dict) or event.get("status") != "incomplete":
        return False
    names = _PENDING_PHYSICAL_CHECKS.get(lab_number, set())
    return any(isinstance(check, dict)
               and check.get("name") in names
               and check.get("status") == "unresolved"
               for check in event.get("checks", ()))


def _mode(workspace: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    manifest = json.loads((workspace / "course.json").read_text(encoding="utf-8"))
    return manifest["mode"]


def _run_inputs(args) -> dict:
    return {"timeout_s": args.timeout_s,
            "physical_timeout_s": args.physical_timeout_s,
            "correspondence_timeout": args.correspondence_timeout_s,
            "cores": args.cores,
            "physical_mode": args.physical_mode}


def _add_run_controls(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--timeout-s", type=float, default=180)
    parser.add_argument("--physical-timeout-s", type=float, default=14400,
                        help="Declared wall-clock budget for complete-core physical implementation, not a runtime guarantee")
    parser.add_argument("--correspondence-timeout-s", "--correspondence-timeout",
                        dest="correspondence_timeout_s", type=float, default=3600,
                        help="Declared wall-clock budget for mapped correspondence, not a runtime guarantee")
    parser.add_argument("--cores", type=int, default=1)
    parser.add_argument("--physical-mode", choices=("native", "docker"), default=None)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m nanochip.laboratory.course")
    commands = parser.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser("init", help="create a persistent course workspace")
    initialize.add_argument("workspace", type=Path)
    initialize.add_argument("--mode", choices=("student", "instructor"), default="student")
    run = commands.add_parser("run", help="execute one lab using retained upstream artifacts")
    run.add_argument("--workspace", required=True, type=Path)
    run.add_argument("--lab", required=True, type=int, choices=range(1, 10))
    run.add_argument("--mode", choices=("student", "instructor"))
    _add_run_controls(run)
    status = commands.add_parser("status", help="inspect current evidence and stale downstream runs")
    status.add_argument("--workspace", required=True, type=Path)
    all_labs = commands.add_parser("run-all", help="run labs in dependency order")
    all_labs.add_argument("--workspace", required=True, type=Path)
    all_labs.add_argument("--mode", choices=("student", "instructor"))
    all_labs.add_argument("--through", type=int, choices=range(1, 10), default=9)
    _add_run_controls(all_labs)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "init":
            manifest = init_workspace(args.workspace, mode=args.mode)
            print(json.dumps({"workspace": str(args.workspace.resolve()), "course": manifest["course_id"],
                              "mode": args.mode, "labs": len(manifest["labs"])}, indent=2))
            return 0
        if args.command == "status":
            print(json.dumps(course_status(args.workspace), indent=2))
            return 0
        if args.command == "run":
            mode = _mode(args.workspace, args.mode)
            event = run_lab(args.workspace, args.lab, mode=mode,
                            inputs=_run_inputs(args))
            print(json.dumps(event, indent=2))
            return 0 if event["status"] == "complete" else 1
        mode = _mode(args.workspace, args.mode)
        events = []
        for number in range(1, args.through + 1):
            try:
                event = run_lab(args.workspace, number, mode=mode,
                                inputs=_run_inputs(args))
            except LabExecutionError as exc:
                if _has_unresolved_physical_check(number, exc.event):
                    state = course_status(args.workspace)
                    completed = [item["lab"] for item in state["labs"] if item["status"] == "complete"]
                    print(json.dumps({"status": "pending_final_physical", "completed_labs": completed,
                                      "failing_lab": number, "error": str(exc),
                                      "meaning": "A final candidate-linked physical or mapped-netlist check remains unresolved."},
                                     indent=2))
                    return 2
                raise
            events.append(event)
            if events[-1]["status"] != "complete":
                if _has_unresolved_physical_check(number, events[-1]):
                    print(json.dumps({"status": "pending_final_physical", "events": events,
                                      "failing_lab": number,
                                      "meaning": "A candidate-linked physical or mapped-netlist check remains unresolved."},
                                     indent=2))
                    return 2
                break
        print(json.dumps({"events": events, "status": events[-1]["status"] if events else "empty"}, indent=2))
        return 0 if len(events) == args.through and all(item["status"] == "complete" for item in events) else 1
    except (ContractError, LabExecutionError, OSError, ValueError, StopIteration) as exc:
        print(json.dumps({"status": "incomplete", "error": f"{type(exc).__name__}: {exc}"}, indent=2),
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
