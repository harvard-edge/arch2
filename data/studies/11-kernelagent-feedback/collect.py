#!/usr/bin/env python3
"""Retain a self-contained subset of Study 10's immutable source receipts."""
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from evidence_bundle import verify_sources

source = HERE.parent / "10-kernelagent-search"
manifest = verify_sources(source)
keep = {
    "README.md",
    "benchmark_results.json",
    "optimized_ncu_metrics.json",
    "kernel.py",
    "problem.py",
}
receipts = [r for r in manifest["files"] if Path(r["path"]).name in keep]
for receipt in receipts:
    out = HERE / receipt["path"]
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source / receipt["path"], out)
    print(out.relative_to(HERE))
(HERE / "source_manifest.json").write_text(
    json.dumps(
        {
            **manifest,
            "selection": "All 40 timing files, all 40 output profiler records, all 40 per-round kernels, all five problem specifications, and README from Study 10. Complete within this selection.",
            "files": receipts,
        },
        indent=2,
    )
    + "\n"
)
