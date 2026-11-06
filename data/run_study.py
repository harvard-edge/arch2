#!/usr/bin/env python3
"""Run a study command and append the attempt to the study's run log.

Every attempt is logged, including failures and runs that are later discarded.
The log is data/studies/<study>/runs.jsonl, with the full console output beside
it in runs/. State the expected duration before the run so that a result that
arrives implausibly fast, or implausibly slowly, is flagged by the record itself.

    python3 data/run_study.py 27-offload-break-even --expected 30 900 --reason "rerun after harness fix" -- python3 reproduce.py

The wrapper returns the command's exit code. It does not judge the result.
A name with a slash is a repository-relative folder, such as a chapter data folder.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_PARTS = {"runs", "__pycache__", ".venv", "venv", ".git", ".cache"}


def snapshot(study: Path) -> dict[str, str]:
    hashes = {}
    for path in sorted(study.rglob("*")):
        rel = path.relative_to(study)
        if path.is_file() and not SKIP_PARTS.intersection(rel.parts) and rel.name != "runs.jsonl":
            hashes[rel.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def digest_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "MISSING"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("study")
    parser.add_argument("--expected", nargs=2, type=float, required=True, metavar=("MIN_S", "MAX_S"))
    parser.add_argument("--reason", required=True, help="why this attempt is being run")
    parser.add_argument("--inputs", nargs="*", default=[], help="repo-relative input files to hash before the run")
    parser.add_argument("--outputs", nargs="*", default=[], help="repo-relative output files elsewhere to hash after the run")
    parser.add_argument("--timeout", type=float, help="stop the run after this many seconds; logged as exit 124")
    argv = sys.argv[1:]
    split = argv.index("--") if "--" in argv else len(argv)
    args = parser.parse_args(argv[:split])
    command = argv[split + 1:]
    study = ROOT / args.study if "/" in args.study else ROOT / "data/studies" / args.study
    if not study.is_dir() or not command:
        parser.error("need an existing study and a command after --")
    low, high = args.expected

    logs = study / "runs"
    logs.mkdir(exist_ok=True)
    started = dt.datetime.now(dt.timezone.utc)
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    input_hashes = {name: digest_of(ROOT / name) for name in args.inputs}
    before = snapshot(study)
    code = {name: digest for name, digest in before.items() if name.endswith(".py")}
    shared = study.parent / "evidence_bundle.py"
    if shared.is_file():
        code["../evidence_bundle.py"] = hashlib.sha256(shared.read_bytes()).hexdigest()
    clock = time.monotonic()
    try:
        done = subprocess.run(command, cwd=study, capture_output=True, text=True, errors="replace", timeout=args.timeout)
    except subprocess.TimeoutExpired as expired:
        output = (expired.stdout or b"").decode(errors="replace") if isinstance(expired.stdout, bytes) else (expired.stdout or "")
        done = subprocess.CompletedProcess(command, 124, output, "timed out")
    elapsed = round(time.monotonic() - clock, 3)
    after = snapshot(study)

    log_path = logs / f"{stamp}.log"
    attempt = 1
    while log_path.exists():  # never overwrite an earlier attempt from the same second
        attempt += 1
        log_path = logs / f"{stamp}-{attempt}.log"
    log_path.write_text(f"$ {' '.join(command)}\n--- stdout\n{done.stdout}\n--- stderr\n{done.stderr}\n", encoding="utf-8")
    changed = {name: digest for name, digest in after.items() if before.get(name) != digest}
    record = {
        "type": "run",
        "run_id": log_path.stem,
        "started_utc": started.isoformat(),
        "reason": args.reason,
        "command": command,
        "exit_code": done.returncode,
        "elapsed_s": elapsed,
        "expected_s": [low, high],
        "timing": "within_expected" if low <= elapsed <= high else "outside_expected",
        "code_sha": git("rev-parse", "HEAD"),
        "dirty": bool(git("status", "--porcelain")),
        "code_hashes": code,
        "host": {"machine": platform.machine(), "system": platform.platform(), "python": platform.python_version()},
        "changed_outputs": changed,
        "file_hashes_after": after,
        "input_hashes": input_hashes,
        "output_hashes": {name: digest_of(ROOT / name) for name in args.outputs},
        "removed_outputs": sorted(set(before) - set(after)),
        "log": f"runs/{log_path.name}",
        "log_sha256": hashlib.sha256(log_path.read_bytes()).hexdigest(),
    }
    with (study / "runs.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    print(f"{args.study}: exit {done.returncode}, {elapsed} s, {record['timing']}, {len(changed)} files changed")
    return done.returncode


if __name__ == "__main__":
    sys.exit(main())
