#!/usr/bin/env python3
"""Verify retained sources and rebuild pair data, summaries, and figure twins."""
from __future__ import annotations
import subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))
from evidence_bundle import record_build, verify_sources


def run(*args):
    subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, check=True)


def main():
    verify_sources(HERE)
    run(HERE / "collect.py")
    run(HERE / "extract_pairs.py", "--offline")
    run(HERE / "summarize.py")
    run(HERE / "diagnose_generate_scope.py")
    run(HERE / "plot_access.py")
    record_build(
        HERE,
        checks=[
            "source_manifest hashes verified",
            "six pinned public archives extracted",
            "pyslang pair extraction completed",
            "matched-pair coverage summaries regenerated",
            "generate-scope diagnostic regenerated",
            "SVG/PDF/300-dpi PNG regenerated",
        ],
        verification_scope="Descriptive static analysis of retained pinned public RTL source; no model or hardware experiments. Visual inspection is recorded separately in visual_qa.json.",
    )


if __name__ == "__main__":
    main()
