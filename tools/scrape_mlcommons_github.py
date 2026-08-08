import csv
import json
import re
import ssl
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {"User-Agent": "Arch2BookMLPerfScraper/1.0 (mailto:arch2-book@example.com)"}

REPOS = [
    ("v4.1", "inference_results_v4.1"),
    ("v4.0", "inference_results_v4.0"),
    ("v3.1", "inference_results_v3.1"),
    ("v3.0", "inference_results_v3.0"),
    ("v2.1", "inference_results_v2.1"),
    ("v2.0", "inference_results_v2.0"),
    ("v1.1", "inference_results_v1.1"),
    ("v1.0", "inference_results_v1.0"),
]

TARGET_ORGS = ["NVIDIA", "Google", "AMD", "Intel", "Groq", "Tenstorrent", "UntetherAI"]


def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return None


def fetch_text(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        return None


def main():
    print("Starting MLCommons Official GitHub Results Scraper...")
    out_csv = (
        REPO_ROOT / "data" / "source-receipts" / "full-mlcommons-datacenter-results.csv"
    )
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    scraped_records = []

    for version_label, repo_name in REPOS:
        print(f"\nScanning repo: {repo_name} ({version_label})...")
        closed_url = (
            f"https://api.github.com/repos/mlcommons/{repo_name}/contents/closed"
        )
        orgs = fetch_json(closed_url)
        if not orgs or not isinstance(orgs, list):
            print(f"  -> Could not access closed division for {repo_name}")
            continue

        org_names = [item["name"] for item in orgs if item.get("type") == "dir"]
        print(f"  Found organizations: {org_names}")

        for org in org_names:
            if not any(t.lower() in org.lower() for t in TARGET_ORGS):
                continue

            results_url = f"https://api.github.com/repos/mlcommons/{repo_name}/contents/closed/{org}/results"
            systems = fetch_json(results_url)
            if not systems or not isinstance(systems, list):
                continue

            for sys_item in systems:
                sys_name = sys_item["name"]
                benchmarks_url = f"https://api.github.com/repos/mlcommons/{repo_name}/contents/closed/{org}/results/{sys_name}"
                benchmarks = fetch_json(benchmarks_url)
                if not benchmarks or not isinstance(benchmarks, list):
                    continue

                for bench_item in benchmarks:
                    bench_name = bench_item["name"]
                    # Check for Offline performance log
                    log_url = f"https://raw.githubusercontent.com/mlcommons/{repo_name}/main/closed/{org}/results/{sys_name}/{bench_name}/Offline/performance/run_1/mlperf_log_summary.txt"
                    log_text = fetch_text(log_url)

                    if not log_text:
                        continue

                    samples_per_sec = None
                    tokens_per_sec = None
                    valid = "VALID" in log_text

                    for line in log_text.splitlines():
                        if "Samples per second:" in line:
                            m = re.search(r"Samples per second:\s*([\d\.]+)", line)
                            if m:
                                samples_per_sec = float(m.group(1))
                        elif "Tokens per second:" in line:
                            m = re.search(r"Tokens per second:\s*([\d\.]+)", line)
                            if m:
                                tokens_per_sec = float(m.group(1))

                    if samples_per_sec or tokens_per_sec:
                        scraped_records.append(
                            {
                                "version": version_label,
                                "organization": org,
                                "system": sys_name,
                                "benchmark": bench_name,
                                "samples_per_sec": samples_per_sec,
                                "tokens_per_sec": tokens_per_sec,
                                "valid": valid,
                                "log_url": log_url,
                            }
                        )
                        print(
                            f"    [+ Record] {org} | {sys_name} | {bench_name} -> {samples_per_sec or tokens_per_sec}/s"
                        )

    print(
        f"\nScraping complete! Total MLPerf datacenter records harvested: {len(scraped_records)}"
    )

    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "version",
                "organization",
                "system",
                "benchmark",
                "samples_per_sec",
                "tokens_per_sec",
                "valid",
                "log_url",
            ],
        )
        writer.writeheader()
        writer.writerows(scraped_records)

    print(f"Saved scraped MLCommons dataset to '{out_csv}'")


if __name__ == "__main__":
    main()
