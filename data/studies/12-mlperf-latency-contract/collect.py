#!/usr/bin/env python3
"""Collect all eligible eight-GPU Llama 2 standard/interactive Server pairs."""
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import requests

HERE = Path(__file__).resolve().parent
REPO = "mlcommons/inference_results_v5.0"
REV = "0bc17ab3f4b33f730d7869e04cc29cb70835e513"


def fetch(path):
    url = f"https://raw.githubusercontent.com/{REPO}/{REV}/{path}"
    dest = HERE / "raw" / path
    if not dest.exists():
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(response.content)
        print(dest.relative_to(HERE), flush=True)
    body = dest.read_bytes()
    return {
        "path": str(dest.relative_to(HERE)),
        "url": url,
        "sha256": hashlib.sha256(body).hexdigest(),
        "bytes": len(body),
    }


def select_pairs(rows):
    groups = {}
    for r in rows:
        if not (
            r["Category"] == "closed"
            and r["Suite"] == "datacenter"
            and r["errors"] == 0
            and r["compliance"] == 1
            and r["inferred"] == 0
            and not r["has_power"]
            and r["Nodes"] == 1
            and r["a#"] == 8
            and r["Scenario"] == "Server"
            and r["Model"] in ("llama2-70b-99", "llama2-70b-interactive-99")
        ):
            continue
        group = groups.setdefault((r["Submitter"], r["Platform"]), {})
        assert r["Model"] not in group, "Duplicate submitted row"
        group[r["Model"]] = r
    pairs = [v for k, v in sorted(groups.items()) if len(v) == 2]
    for pair in pairs:
        a, b = pair["llama2-70b-99"], pair["llama2-70b-interactive-99"]
        for key in (
            "Software",
            "Accelerator",
            "Processor",
            "weight_data_types",
            "operating_system",
            "Availability",
            "host_processors_per_node",
        ):
            assert a[key] == b[key], (a["Platform"], key)
    return pairs, [list(k) for k, v in sorted(groups.items()) if len(v) != 2]


def main():
    receipts = [fetch("summary_results.json"), fetch("README.md")]
    rows = json.loads((HERE / "raw/summary_results.json").read_text())
    pairs, unpaired = select_pairs(rows)
    paths = sorted(
        {
            r["Location"] + "/performance/run_1/mlperf_log_summary.txt"
            for p in pairs
            for r in p.values()
        }
        | {
            f"closed/{r['Submitter']}/systems/{r['Platform']}.json"
            for p in pairs
            for r in p.values()
        }
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        receipts += list(pool.map(fetch, paths))
    (HERE / "selected_pairs.json").write_text(json.dumps(pairs, indent=2) + "\n")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    out = HERE / "source_manifest.json"
    old = json.loads(out.read_text()) if out.exists() else {}
    out.write_text(
        json.dumps(
            {
                "repository": REPO,
                "revision": REV,
                "first_collected_utc": old.get("first_collected_utc", now),
                "last_verified_utc": now,
                "selection": "All matching standard/interactive Server pairs: closed datacenter, non-inferred, non-power, compliance=1, errors=0, one node, eight accelerators, Llama 2 70B 99% accuracy target. Pair on submitter and platform; require matching reported software, hardware, precision, operating system and availability.",
                "population_rows": len(rows),
                "eligible_pairs": len(pairs),
                "unpaired_systems": unpaired,
                "files": receipts,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"Collected {len(pairs)} pairs; {len(receipts)} files")


if __name__ == "__main__":
    main()
