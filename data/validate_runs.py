#!/usr/bin/env python3
"""Check the study run logs: complete, append-only, and honest about timing.

A log may only grow, so a discarded attempt cannot be removed after the fact.
Attempt and failure counts are reported for every study. A run outside its
expected time needs a timing_note record naming the run and explaining it.

This confirms the log is well formed. It cannot detect attempts run outside the
wrapper, and it cannot confirm that a stated expectation was reasonable.

    python3 data/validate_runs.py            (report and enforce logs that exist)
    python3 data/validate_runs.py --require  (also fail when a study has no log)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN_FIELDS = ("run_id", "started_utc", "reason", "command", "exit_code", "elapsed_s", "expected_s",
              "timing", "code_sha", "dirty", "host", "changed_outputs", "log", "log_sha256")
EXEMPT = {"__pycache__", "archived_ch08"}


def committed(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    done = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=ROOT, capture_output=True, text=True)
    return done.stdout if done.returncode == 0 else ""


def check_log(study: Path, errors: list[str]) -> tuple[int, int, int]:
    log = study / "runs.jsonl"
    text = log.read_text(encoding="utf-8")
    if not text.startswith(committed(log)):
        errors.append(f"{study.name}: runs.jsonl rewrites committed history")
    records = [json.loads(line) for line in text.splitlines() if line.strip()]
    runs = [r for r in records if r.get("type") == "run"]
    explained = {r.get("run_id") for r in records if r.get("type") == "timing_note"}
    overwritten = {r.get("run_id") for r in records if r.get("type") == "log_overwritten"}
    for run in runs:
        missing = [field for field in RUN_FIELDS if field not in run]
        if missing:
            errors.append(f"{study.name}: run {run.get('run_id')} is missing {missing}")
            continue
        low, high = run["expected_s"]
        inside = low <= run["elapsed_s"] <= high
        if inside != (run["timing"] == "within_expected"):
            errors.append(f"{study.name}: run {run['run_id']} timing field contradicts its elapsed time")
        if not inside and run["run_id"] not in explained:
            errors.append(f"{study.name}: run {run['run_id']} took {run['elapsed_s']} s, expected {low} to {high} s, unexplained")
        console = study / run["log"]
        if not console.is_file():
            errors.append(f"{study.name}: run {run['run_id']} console log is missing")
        elif run["run_id"] not in overwritten and hashlib.sha256(console.read_bytes()).hexdigest() != run["log_sha256"]:
            errors.append(f"{study.name}: run {run['run_id']} console log was changed")
    failures = sum(1 for run in runs if run.get("exit_code") != 0)
    outside = sum(1 for run in runs if run.get("timing") == "outside_expected")
    return len(runs), failures, outside


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--require", action="store_true")
    args = parser.parse_args()
    errors: list[str] = []
    for study in sorted(p for p in (ROOT / "data/studies").iterdir() if p.is_dir() and p.name not in EXEMPT):
        if (study / "runs.jsonl").is_file():
            attempts, failures, outside = check_log(study, errors)
            print(f"{study.name}: {attempts} attempts, {failures} failed, {outside} outside expected time")
        else:
            print(f"{study.name}: no run log")
            if args.require:
                errors.append(f"{study.name}: no run log")
    for log in sorted((ROOT / "book/contents/chapters").rglob("runs.jsonl")):
        attempts, failures, outside = check_log(log.parent, errors)
        rel = log.parent.relative_to(ROOT / "book/contents/chapters")
        print(f"{rel}: {attempts} attempts, {failures} failed, {outside} outside expected time")
    for error in errors:
        print(f"ERROR {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
