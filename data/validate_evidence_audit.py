#!/usr/bin/env python3
"""Require an independent, input-bound audit for every data-backed figure.

The person or process that produces a result cannot be the one that accepts it.
Each figure in data/datasets/provenance.yml that is not purely conceptual
must either pass an audit record in data/audits/<figure>.yml or sit unchanged in
the frozen baseline data/audits/BASELINE.json.

An audit is bound to the sha256 of every declared input and generator and of the
figure's caption and alt text, so a later change to any of them makes it stale. The baseline may only shrink: a new
entry or a changed hash relative to HEAD fails, which stops a result being moved
into the baseline to avoid audit.

This checks that an audit record exists, matches the files, and is complete. It
cannot establish that the audit was honest or that a source was read correctly.

    python3 data/validate_evidence_audit.py
    python3 data/validate_evidence_audit.py --hashes fig-example
    python3 data/validate_evidence_audit.py --freeze-baseline fig-a fig-b  (first use only)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
UNGATED_CLASSES = {"conceptual"}
REQUIRED_FIELDS = (
    "figure",
    "producer",
    "auditor",
    "audited_on",
    "inputs",
    "source_check",
    "rerun",
    "attempts",
    "negative_control",
    "limits",
    "verdict",
)
MIN_ATTEMPTS = 3
VERDICTS = {"PASS", "FAIL"}
ATTEMPT_OUTCOMES = {"survived", "broken"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gated_figures(root: Path) -> dict[str, list[str]]:
    manifest = yaml.safe_load((root / "data/datasets/provenance.yml").read_text(encoding="utf-8"))
    figures = {}
    for name, entry in manifest["figure_evidence"].items():
        if entry.get("evidence_class") in UNGATED_CLASSES:
            continue
        paths = list(entry.get("data") or [])
        generator = entry.get("generator")
        if generator and generator != "inline":
            paths.append(generator)
        figures[name] = sorted(paths)
    return figures


def input_hashes(root: Path, paths: list[str]) -> dict[str, str]:
    return {p: sha256(root / p) if (root / p).is_file() else "MISSING" for p in paths}


def figure_text(root: Path, name: str) -> str | None:
    """Return the caption and alt text of a figure, wherever it is declared."""
    for path in sorted((root / "book/contents").rglob("*.qmd")):
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if re.search(r"\{#" + re.escape(name) + r"[\s}]", line):
                return line
            if line.strip() == f"#| label: {name}":
                block = []
                for other in lines[i:]:
                    if not other.startswith("#|"):
                        break
                    block.append(other)
                return "\n".join(block)
    return None


def bound_hashes(root: Path, name: str, paths: list[str]) -> dict[str, str]:
    """Hashes an audit must record: inputs plus the words that describe them."""
    hashes = input_hashes(root, paths)
    text = figure_text(root, name)
    hashes["caption"] = hashlib.sha256(text.encode("utf-8")).hexdigest() if text else "MISSING"
    return hashes


def audit_problems(record: dict, name: str, current: dict[str, str]) -> list[str]:
    problems = [f"missing field: {f}" for f in REQUIRED_FIELDS if record.get(f) in (None, "", [], {})]
    if problems:
        return problems
    if record["figure"] != name:
        problems.append(f"record names {record['figure']}")
    if str(record["producer"]).strip() == str(record["auditor"]).strip():
        problems.append("auditor is the producer")
    if record["verdict"] not in VERDICTS:
        problems.append(f"verdict must be one of {sorted(VERDICTS)}")
    elif record["verdict"] != "PASS":
        problems.append("verdict is FAIL")
    if record["inputs"] != current:
        changed = sorted(k for k in set(current) | set(record["inputs"]) if current.get(k) != record["inputs"].get(k))
        problems.append(f"stale audit, inputs changed: {changed}")
    attempts = record["attempts"]
    if not isinstance(attempts, list) or len(attempts) < MIN_ATTEMPTS:
        problems.append(f"needs at least {MIN_ATTEMPTS} attempts to break the result")
    else:
        for attempt in attempts:
            if not isinstance(attempt, dict) or not attempt.get("attack") or attempt.get("outcome") not in ATTEMPT_OUTCOMES:
                problems.append("each attempt needs an attack and an outcome of survived or broken")
            elif attempt["outcome"] == "broken" and record["verdict"] == "PASS":
                problems.append("a broken attempt cannot sit under a PASS verdict")
    rerun = record["rerun"]
    if not isinstance(rerun, dict) or not rerun.get("command") or not rerun.get("result"):
        problems.append("rerun needs a command and a result")
    return problems


def baseline_at_head(root: Path) -> dict | None:
    done = subprocess.run(
        ["git", "show", "HEAD:data/audits/BASELINE.json"], cwd=root, capture_output=True, text=True, check=False
    )
    return json.loads(done.stdout) if done.returncode == 0 else None


def check(root: Path = ROOT) -> tuple[list[str], dict[str, int]]:
    failures: list[str] = []
    counts = {"audited": 0, "baseline": 0}
    baseline_path = root / "data/audits/BASELINE.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8")) if baseline_path.exists() else {}
    previous = baseline_at_head(root)
    if previous is not None:
        for name, hashes in baseline.items():
            if name not in previous:
                failures.append(f"{name}: added to the baseline; a new result needs an audit")
            elif previous[name] != hashes:
                failures.append(f"{name}: baseline hashes rewritten; a changed result needs an audit")
    for name, paths in gated_figures(root).items():
        record_path = root / "data/audits" / f"{name}.yml"
        if record_path.exists():
            record = yaml.safe_load(record_path.read_text(encoding="utf-8")) or {}
            problems = audit_problems(record, name, bound_hashes(root, name, paths))
            failures += [f"{name}: {p}" for p in problems]
            counts["audited"] += not problems
        elif name in baseline:
            if baseline[name] != bound_hashes(root, name, paths):
                failures.append(f"{name}: inputs changed since the baseline; audit required")
            else:
                counts["baseline"] += 1
        else:
            failures.append(f"{name}: no independent audit record")
    return failures, counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--hashes", metavar="FIGURE", help="print the input hashes an audit must record")
    parser.add_argument("--freeze-baseline", nargs="+", metavar="FIGURE", help="create the baseline once")
    args = parser.parse_args()
    if args.hashes:
        figures = gated_figures(ROOT)
        print(yaml.safe_dump(bound_hashes(ROOT, args.hashes, figures[args.hashes]), sort_keys=True), end="")
        return 0
    if args.freeze_baseline:
        path = ROOT / "data/audits/BASELINE.json"
        if path.exists():
            print("baseline already exists and may only shrink", file=sys.stderr)
            return 1
        figures = gated_figures(ROOT)
        frozen = {n: bound_hashes(ROOT, n, figures[n]) for n in args.freeze_baseline}
        path.write_text(json.dumps(frozen, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return 0
    failures, counts = check()
    for failure in failures:
        print(f"  FAIL {failure}")
    print(f"{counts['audited']} figures audited; {counts['baseline']} frozen unaudited in the baseline")
    print("This confirms records match files. It does not certify that an audit was honest.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
