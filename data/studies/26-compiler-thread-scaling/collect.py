#!/usr/bin/env python3
"""Verify pinned public sources and regenerate the two CSV extracts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "source_manifest.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_sources(refetch_missing: bool) -> list[dict[str, str]]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    verified = []
    for source in manifest["files"]:
        path = HERE / source["path"]
        if not path.exists() and refetch_missing:
            path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["curl", "-fsSL", source["url"], "-o", str(path)], check=True
            )
        if not path.is_file():
            raise FileNotFoundError(
                f"Missing retained source: {path}; pass --refetch-missing to retrieve it"
            )
        actual = sha256(path)
        if actual != source["sha256"]:
            raise ValueError(
                f"Frozen source hash mismatch for {source['path']}: {actual}"
            )
        verified.append(
            {"path": source["path"], "sha256": actual, "url": source["url"]}
        )
    return verified


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refetch-missing",
        action="store_true",
        help="fetch only source files absent from the packet",
    )
    args = parser.parse_args()
    verified = verify_sources(args.refetch_missing)

    sys.path.insert(0, str(HERE / "scripts"))
    import extract  # noqa: E402

    extract.main()
    outputs = [HERE / "extracted.csv", HERE / "latency_inventory.csv"]
    extracted = list(csv.DictReader(outputs[0].open(encoding="utf-8", newline="")))
    inventory = list(csv.DictReader(outputs[1].open(encoding="utf-8", newline="")))
    selected = [
        r for r in inventory if r["included_in_thread_scaling_extract"] == "yes"
    ]
    excluded_sync = [
        r for r in inventory if "distinct local-sync driver" in r["selection_reason"]
    ]
    if (
        len(extracted) != 30
        or len(inventory) != 40
        or len(selected) != 30
        or len(excluded_sync) != 10
    ):
        raise ValueError(
            "Inventory reconciliation failed: expected 40 latency rows, 30 included thread rows, 10 excluded local-sync rows"
        )
    receipt = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "collection_scope": "Offline extraction of the pinned IREE bot report; original public measurement rows are retained unchanged.",
        "verified_source_files": verified,
        "checks": {
            "pinned_source_hashes_verified": len(verified),
            "all_latency_summary_rows_in_inventory": 40,
            "thread_rows_included": 30,
            "workloads_with_all_1_4_8_points": 10,
            "local_sync_rows_excluded_with_reason": 10,
        },
        "files": {str(p.relative_to(HERE)): sha256(p) for p in outputs},
        "verification_scope": "Report parsing and source-code configuration inspection only. No rerun, independent host, or raw per-repetition dataset is claimed.",
    }
    (HERE / "build_receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    print("Verified sources:")
    for item in verified:
        print(f"  {item['path']}  {item['sha256']}")
    print("Generated files:")
    for p in [*outputs, HERE / "build_receipt.json"]:
        print(f"  {p}")


if __name__ == "__main__":
    main()
