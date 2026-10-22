"""Check or execute cumulative Nanochip extension exercises."""

import argparse
from pathlib import Path

from .feedback import check_feedback
from ..contracts import ContractError


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "run"):
        command = sub.add_parser(name)
        command.add_argument(
            "--implementation", required=True, choices=("student", "reference")
        )
        if name == "run":
            command.add_argument("--output", required=True, type=Path)
            command.add_argument("--timeout", type=float, default=120)
    design = sub.add_parser("design-check")
    design.add_argument(
        "--implementation", required=True, choices=("student", "reference")
    )
    design.add_argument("--output", required=True, type=Path)
    design.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args(argv)
    if args.command == "design-check":
        from .design import check_design

        transformer = None
        if args.implementation == "student":
            from .student_design import transform

            transformer = transform
        try:
            result = check_design(
                args.output, transformer=transformer, timeout=args.timeout
            )
        except NotImplementedError as exc:
            print(f"INCOMPLETE: {exc}; no reference fallback")
            return 2
        except (ContractError, OSError, ValueError) as exc:
            print(f"ERROR: {exc}; no reference fallback")
            return 2
        print(
            f"Functional and differential checks: {'PASS' if result['ok'] else 'FAIL'}; no physical execution"
        )
        print(f"Report: {args.output.resolve() / 'student-design-check.json'}")
        return 0 if result["ok"] else 1
    if args.implementation == "student":
        from ..student import StudentProposer

        factory = StudentProposer
    else:
        from ..adapters import ReferenceProposer

        factory = ReferenceProposer
    checks = check_feedback(factory)
    print(
        f"Implementation: {args.implementation}; constructed policy checks, no hardware measurements"
    )
    for check in checks:
        print(f"{check.status.upper()}: {check.name}")
        if check.status != "pass":
            print(f"  {check.details}")
    if any(check.status == "incomplete" for check in checks):
        return 2
    if any(check.status != "pass" for check in checks):
        return 1
    if args.command == "check":
        return 0
    from ..__main__ import main as laboratory_main

    return laboratory_main(
        [
            "run",
            "--policy",
            args.implementation,
            "--output",
            str(args.output),
            "--timeout",
            str(args.timeout),
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
