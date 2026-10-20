"""Read the inventory, validate it, or run the bounded memory exercise."""

import argparse
import json
from pathlib import Path
import subprocess

from .exercise import run_memory_check
from .inventory import SNAPSHOT, derive_target, validate_target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inspect", "validate", "derive", "check"))
    parser.add_argument("--output", type=Path, help="new output directory for check, or new JSON file for derive")
    parser.add_argument("--timeout-s", type=float, default=60)
    args = parser.parse_args(argv)
    if args.command not in ("derive", "check") and args.output is not None:
        parser.error("--output is only supported by derive and check")
    if args.command == "check" and args.output is None:
        parser.error("check requires --output pointing to a new run directory (for retained evidence)")
    try:
        if args.command == "check":
            result = run_memory_check(args.output, args.timeout_s)
        elif args.command == "derive":
            result = derive_target(args.timeout_s)
            if args.output:
                with args.output.open("x") as stream:
                    stream.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
        else:
            target = json.loads(SNAPSHOT.read_text())
            result = target if args.command == "inspect" else validate_target(target, args.timeout_s)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("status", "pass") == "pass" else 1
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "error", "details": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
