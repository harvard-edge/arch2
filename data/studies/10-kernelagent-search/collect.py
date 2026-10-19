#!/usr/bin/env python3
"""Fetch the complete published timing series at an immutable Git revision."""
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import requests

HERE = Path(__file__).resolve().parent
REPO = "kaiming-cheng/kernelagent-optimization-artifacts"
REV = "56cf9183b527307538ccbe8f554a88502918d2d1"
ROOT = HERE.parents[2]
TREE = (
    ROOT
    / "data/source-receipts/operational-discovery/kaiming-cheng__kernelagent-optimization-artifacts.json"
)


def fetch(entry):
    path = entry["path"]
    url = f"https://raw.githubusercontent.com/{REPO}/{REV}/{path}"
    dest = HERE / "raw" / path
    if dest.exists():
        body = dest.read_bytes()
    else:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        body = response.content
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
        print(dest.relative_to(ROOT), flush=True)
    blob = hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
    assert blob == entry["sha"], f"Git blob mismatch: {path}"
    return {
        "path": "raw/" + path,
        "url": url,
        "git_blob_sha1": blob,
        "sha256": hashlib.sha256(body).hexdigest(),
        "bytes": len(body),
    }


def main():
    inventory = HERE / "source_tree.json"
    if not inventory.exists():
        inventory = TREE
    tree = json.loads(inventory.read_text())
    assert tree["commit"] == REV and not tree["tree"].get("truncated")
    wanted = {
        "README.md",
        "benchmark.py",
        "input_kernel.py",
        "problem.py",
        "optimized_kernel_beam_search.py",
        "benchmark_results.json",
        "input_ncu_metrics.json",
        "optimized_ncu_metrics.json",
        "kernel.py",
    }
    entries = [
        e
        for e in tree["tree"]["tree"]
        if e["type"] == "blob"
        and (Path(e["path"]).name in wanted or "license" in e["path"].lower())
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        receipts = list(pool.map(fetch, entries))
    out = HERE / "source_manifest.json"
    previous = json.loads(out.read_text()) if out.exists() else {}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    out.write_text(
        json.dumps(
            {
                "repository": REPO,
                "revision": REV,
                "first_collected_utc": previous.get("first_collected_utc", now),
                "last_verified_utc": now,
                "inventory_complete": True,
                "selection": "Every benchmark and NCU JSON, every per-round kernel, root benchmark and README, and all problem/input/final kernels in the complete Git tree.",
                "files": receipts,
            },
            indent=2,
        )
        + "\n"
    )
    (HERE / "source_tree.json").write_bytes(inventory.read_bytes())
    print(f"Verified {len(receipts)} source blobs at {REV}")


if __name__ == "__main__":
    main()
