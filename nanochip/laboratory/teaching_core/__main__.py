"""Inspect the proposed complete target or construct software-reference fixtures."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from . import build_fixture, contract, make_task, TeachingCoreMaterializer, TeachingCoreBackend
from ..contracts import Action


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("contract", "fixture", "run"))
    parser.add_argument("--output")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--prompt-index", type=int, default=0)
    parser.add_argument("--tokens", help="optional comma-separated token ids, at most max_seq")
    parser.add_argument("--action", choices=("serial_mul1", "serial_mul2"), default="serial_mul1")
    parser.add_argument("--timeout", "--timeout-s", type=float, default=180)
    args = parser.parse_args(argv)
    if args.command in ("fixture", "run") and not args.output:
        parser.error("fixture/run requires a new --output directory")
    tokens = None if args.tokens is None else list(map(int, args.tokens.split(",")))
    if args.command == "contract":
        result = contract()
    elif args.command == "fixture":
        result = build_fixture(args.output, args.seed, args.prompt_index, tokens=tokens)
    else:
        output = Path(args.output).resolve()
        output.mkdir(parents=True, exist_ok=False)
        task = make_task(args.seed, args.prompt_index, tokens=tokens)
        candidate = TeachingCoreMaterializer().materialize(task, Action(args.action), output)
        receipt = TeachingCoreBackend(timeout_s=args.timeout).evaluate(task, candidate)
        result = {"schema": "nanochip-complete-core-run/v0", "status": "pass" if receipt.execution_status == "success" and all(c.status == "pass" for c in receipt.checks) else "fail",
                  "task": asdict(task), "candidate": asdict(candidate), "candidate_digest": candidate.digest,
                  "receipt": asdict(receipt), "physical_execution": False, "complete_core_ready": False}
        (output / "run.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if args.command == "contract" or result.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
