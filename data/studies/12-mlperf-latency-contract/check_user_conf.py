#!/usr/bin/env python3
"""Compare each log's target_qps with the submitter's user.conf at the pinned commit.

Retains the 40 user.conf files in raw_user_conf/ and writes user_conf_targets.json.
The script reports agreement and disagreement. It does not explain a disagreement,
and the logs stay the plotted record.
"""
import collections
import csv
import hashlib
import json
from pathlib import Path
import re
import requests

HERE = Path(__file__).resolve().parent
REPO = "mlcommons/inference_results_v5.0"
REV = "0bc17ab3f4b33f730d7869e04cc29cb70835e513"


def main():
    with (HERE / "paired_throughput.csv").open() as f:
        rows = list(csv.DictReader(f))
    files = []
    for r in rows:
        for condition in ("standard", "interactive"):
            path = (
                r[condition + "_source"]
                .removeprefix("raw/")
                .replace("/results/", "/measurements/")
                .split("/performance/")[0]
                + "/user.conf"
            )
            url = f"https://raw.githubusercontent.com/{REPO}/{REV}/{path}"
            dest = HERE / "raw_user_conf" / path
            if not dest.exists():
                response = requests.get(url, timeout=60)
                response.raise_for_status()
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(response.content)
            values = re.findall(r"target_qps\s*=\s*([\d.]+)", dest.read_text())
            assert len(values) == 1, (path, values)
            configured = float(values[0])
            logged = float(r[condition + "_target_qps"])
            files.append(
                {
                    "path": "raw_user_conf/" + path,
                    "url": url,
                    "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
                    "user_conf_target_qps": configured,
                    "log_target_qps": logged,
                    "user_conf_over_log": configured / logged,
                }
            )
    ratios = collections.Counter(
        round(f["user_conf_over_log"], 2)
        for f in files
        if f["user_conf_target_qps"] != f["log_target_qps"]
    )
    result = {
        "repository": REPO,
        "revision": REV,
        "user_conf_files": len(files),
        "equal_to_log": sum(
            f["user_conf_target_qps"] == f["log_target_qps"] for f in files
        ),
        "different_from_log": sum(
            f["user_conf_target_qps"] != f["log_target_qps"] for f in files
        ),
        "user_conf_over_log_rounded_counts": {
            str(k): v for k, v in sorted(ratios.items())
        },
        "files": files,
    }
    (HERE / "user_conf_targets.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "files"}, indent=2))


if __name__ == "__main__":
    main()
