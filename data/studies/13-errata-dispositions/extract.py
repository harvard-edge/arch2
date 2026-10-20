#!/usr/bin/env python3
"""Rerun retained extraction code on the pinned PDFs, without touching study 01."""
import contextlib
import csv
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))
from evidence_bundle import verify_sources


def rows(path):
    return list(csv.DictReader(l for l in path.open() if not l.startswith("#")))


def main():
    manifest = verify_sources(HERE)
    (HERE / "derived").mkdir(exist_ok=True)
    spec = importlib.util.spec_from_file_location(
        "retained_miner", HERE / "raw/mine_cpu_errata.py"
    )
    miner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(miner)
    miner.ROOT = ROOT
    miner.CACHE = HERE / "raw"
    miner.FAMILIES = HERE / "raw/families.csv"
    miner.SOURCES = HERE / "derived/sources.csv"
    miner.ERRATA = HERE / "derived/errata.csv"
    miner.TEXT = HERE / "raw/errata_text_DIAGNOSTIC_ONLY.jsonl"
    receipts = {r["family"]: r for r in manifest["files"] if "family" in r}
    source_rows = rows(HERE / "raw/sources.csv")
    for row in source_rows:
        row["sha256"] = receipts[row["family"]]["sha256"]
        row["retrieved"] = manifest["collected_utc"][:10]
    with miner.SOURCES.open("w") as f:
        writer = csv.DictWriter(f, fieldnames=list(source_rows[0]))
        writer.writeheader()
        writer.writerows(source_rows)
    sys.argv = [str(HERE / "extract.py"), "--offline", "--verify-hashes"]
    with (HERE / "extraction_log.txt").open("w") as f, contextlib.redirect_stdout(f):
        miner.main()
    old = {(r["family"], r["erratum_id"]): r for r in rows(HERE / "raw/errata.csv")}
    new = {(r["family"], r["erratum_id"]): r for r in rows(miner.ERRATA)}
    changes = []
    for key in sorted(old.keys() | new.keys()):
        before, after = old.get(key), new.get(key)
        fields = [
            k
            for k in (before or after)
            if (before or {}).get(k) != (after or {}).get(k)
        ]
        if fields:
            changes.append(
                {
                    "family": key[0],
                    "id": key[1],
                    "changed_fields": fields,
                    "before": before,
                    "after": after,
                }
            )
    result = {
        "previous_rows": len(old),
        "current_rows": len(new),
        "source_documents_identical": sum(
            r["matches_study_01"] for r in receipts.values()
        ),
        "source_documents_changed": [
            r["family"] for r in receipts.values() if not r["matches_study_01"]
        ],
        "changes": changes,
    }
    (HERE / "snapshot_changes.json").write_text(json.dumps(result, indent=2) + "\n")
    print({k: v for k, v in result.items() if k != "changes"})


if __name__ == "__main__":
    main()
