#!/usr/bin/env python3
"""Rebuild a frozen commit from a fresh clone and compare it with a submission PDF.

Clones the commit into an empty directory with no private configuration, reruns
every study reproduce script and figure generator from retained raw outputs,
builds the PDF, and reports what differs. Regenerated files that differ from the
commit, failed commands, and page or text differences from the submission all
count as failures. Reproducing the numbers from retained outputs does not rerun
the original experiments; those need their own rerun.

    python3 data/clean_rebuild.py --ref <sha> --submission path/to.pdf --out /path/report.json
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def run(command: list[str], cwd: Path, env: dict, log: list[dict], timeout: int = 7200) -> bool:
    clock = time.monotonic()
    try:
        done = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, errors="replace", timeout=timeout)
        code = done.returncode
        tail = (done.stdout + done.stderr)[-1500:]
    except subprocess.TimeoutExpired:
        code, tail = -1, "timeout"
    log.append({"command": command, "cwd": str(cwd), "exit_code": code,
                "elapsed_s": round(time.monotonic() - clock, 1), "tail": "" if code == 0 else tail})
    return code == 0


def page_text(pdf: Path) -> list[str]:
    text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout
    return text.split("\f")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--submission", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--venv", type=Path, default=Path("/Users/VJ/GitHub/Arch2/.venv"))
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()

    workspace = Path(tempfile.mkdtemp(prefix="arch2-clean-rebuild-"))
    clone = workspace / "repo"
    log: list[dict] = []
    subprocess.run(["git", "clone", "--no-hardlinks", "--quiet", str(ROOT), str(clone)], check=True)
    subprocess.run(["git", "checkout", "--quiet", args.ref], cwd=clone, check=True)
    env = {**os.environ, "PATH": f"{args.venv}/bin:{os.environ['PATH']}", "PYTHONDONTWRITEBYTECODE": "1"}

    for script in sorted(clone.glob("data/studies/*/reproduce.py")):
        if (script.parent / "source_manifest.json").is_file() and (script.parent / "collect.py").is_file():
            run(["python3", "collect.py"], script.parent, env, log)  # refetch gitignored sources by pinned hash
        run(["python3", script.name], script.parent, env, log)
    manifest = yaml.safe_load((clone / "data/datasets/provenance.yml").read_text(encoding="utf-8"))
    generators = sorted({e["generator"] for e in manifest["figure_evidence"].values() if e.get("generator")})
    for generator in generators:
        script = clone / generator
        if script.suffix == ".py":
            run(["python3", script.name], script.parent, env, log)
    drift = subprocess.run(["git", "status", "--porcelain"], cwd=clone, capture_output=True, text=True).stdout.splitlines()
    built = run(["python3", "cli/arch2.py", "build", "--pdf", "--no-layout"], clone, env, log)

    pdfs = sorted((clone / "book").rglob("*.pdf"), key=lambda p: p.stat().st_mtime)
    book_pdf = next((p for p in reversed(pdfs) if "_build" in p.parts or "_book" in p.parts or "output" in p.parts), None)
    comparison: dict = {"built_pdf": str(book_pdf) if book_pdf else None}
    if book_pdf and args.submission:
        ours, theirs = page_text(book_pdf), page_text(args.submission)
        changed = [i + 1 for i, (a, b) in enumerate(zip(ours, theirs)) if a != b]
        comparison.update(pages_built=len(ours), pages_submission=len(theirs), pages_differing=changed,
                          first_difference=list(difflib.unified_diff(theirs[changed[0] - 1].splitlines(), ours[changed[0] - 1].splitlines(), lineterm="", n=0))[:20] if changed else [],
                          submission_sha256=hashlib.sha256(args.submission.read_bytes()).hexdigest())
    failed = [entry for entry in log if entry["exit_code"] != 0]
    matches = bool(args.submission) and comparison.get("pages_built") == comparison.get("pages_submission") and not comparison.get("pages_differing")
    report = {"ref": args.ref, "clone": str(clone), "commands": log, "failed_commands": len(failed),
              "regenerated_files_differing": drift, "pdf_built": built, "comparison": comparison, "pdf_matches": matches}
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"commands {len(log)}, failed {len(failed)}, regenerated files differing {len(drift)}, pdf built {built}, pdf matches {matches}")
    if not args.keep:
        shutil.rmtree(workspace, ignore_errors=True)
    return 0 if not failed and not drift and built and (matches or not args.submission) else 1


if __name__ == "__main__":
    sys.exit(main())
