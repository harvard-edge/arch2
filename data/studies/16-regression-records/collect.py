#!/usr/bin/env python3
"""Fetch a bounded, inspectable Ibex/OpenTitan verification snapshot.

The Ibex report URL contains `latest` and is mutable. Every retrieval is saved
as raw bytes with its final URL, HTTP headers, retrieval timestamp, and SHA-256.
The report generator source is pinned to the commit printed inside the report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
REPORT_URL = "https://ibex.reports.lowrisc.org/opentitan/latest/report.html"
IBEX_JSON_URL = "https://ibex.reports.lowrisc.org/opentitan/latest/report.json"
DISCOVERY_URL = "https://opentitan.org/dvdata/"
DASHBOARD_URL = "https://opentitan.org/dashboard/"
OT_DASHBOARD_SCRIPT_URL = "https://opentitan.org/js/ot-nightly-results.js"
OT_CHIP_REPORT_URL = (
    "https://reports.opentitan.org/hw/top_earlgrey/dv/latest/report.json"
)
OT_CHIP_SUMMARY_URL = (
    "https://reports.opentitan.org/hw/top_earlgrey/dv/summary/latest/report.html"
)
IBEX_COMMIT = "96a34a5617b2904f4172a350199217d82359c13b"
IBEX_BASE = f"https://raw.githubusercontent.com/lowRISC/ibex/{IBEX_COMMIT}/"
SOURCE_PATHS = [
    "dv/uvm/core_ibex/scripts/report_lib/html.py",
    "dv/uvm/core_ibex/scripts/report_lib/regression_report.tpl.html",
    "dv/uvm/core_ibex/scripts/report_lib/util.py",
    "dv/uvm/core_ibex/scripts/metadata.py",
    "dv/uvm/core_ibex/scripts/test_run_result.py",
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str, path: Path, base_dir: Path = ROOT) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    header_path = path.with_suffix(path.suffix + ".headers.txt")
    cmd = [
        "curl",
        "--fail",
        "--location",
        "--silent",
        "--show-error",
        "--max-time",
        "60",
        "--dump-header",
        str(header_path),
        "--output",
        str(path),
        "--write-out",
        "%{url_effective}\n%{http_code}",
        url,
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    final_url, status = result.stdout.strip().splitlines()[-2:]
    payload = path.read_bytes()
    return {
        "requested_url": url,
        "final_url": final_url,
        "http_status": int(status),
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "path": str(path.relative_to(base_dir)),
        "bytes": len(payload),
        "sha256": sha256(payload),
        "headers_path": str(header_path.relative_to(base_dir)),
        "headers_sha256": sha256(header_path.read_bytes()),
    }


def verify_frozen_snapshot(manifest_path: Path) -> int:
    base_dir = manifest_path.parent.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    missing = []
    for item in manifest["files"]:
        path = base_dir / item["path"]
        headers = base_dir / item["headers_path"]
        if not path.exists() or not headers.exists():
            missing.append((item, path, headers))
            continue
        if sha256(path.read_bytes()) != item["sha256"]:
            raise SystemExit(f"Refusing to replace changed snapshot bytes: {path}")
        if sha256(headers.read_bytes()) != item["headers_sha256"]:
            raise SystemExit(f"Refusing to replace changed response headers: {headers}")

    if missing:
        recovery_root = base_dir / "raw"
        recovery_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="snapshot-recovery-", dir=recovery_root
        ) as tmp:
            tmpdir = Path(tmp)
            for item, target, target_headers in missing:
                temp_path = tmpdir / Path(item["path"]).name
                fetched = fetch(item["requested_url"], temp_path, base_dir)
                if (
                    fetched["sha256"] != item["sha256"]
                    or fetched["headers_sha256"] != item["headers_sha256"]
                ):
                    raise SystemExit(
                        f"Refusing changed upstream snapshot while recovering missing files: {item['requested_url']}"
                    )
                target.parent.mkdir(parents=True, exist_ok=True)
                target_headers.parent.mkdir(parents=True, exist_ok=True)
                os.replace(temp_path, target)
                os.replace(
                    temp_path.with_suffix(temp_path.suffix + ".headers.txt"),
                    target_headers,
                )
                print(target.relative_to(base_dir))
                print(target_headers.relative_to(base_dir))

    report_item = next(
        item
        for item in manifest["files"]
        if item["path"].endswith("ibex-opentitan-latest-report.html")
    )
    report_bytes = (base_dir / report_item["path"]).read_bytes()
    report_text = report_bytes.decode("utf-8", "replace")
    commit = re.search(r"/tree/([0-9a-f]{40})", report_text)
    report_commit = commit.group(1) if commit else None
    expected_commit = manifest["report_identity"]["ibex_git_commit"]
    if report_commit != expected_commit:
        raise SystemExit(
            f"Frozen report commit mismatch: HTML={report_commit}, manifest={expected_commit}"
        )
    for item in manifest["files"]:
        if item.get("repository_path") and item.get("git_commit") != report_commit:
            raise SystemExit(
                f"Report generator source is not pinned to the report commit: {item['path']}"
            )
    reported_date = re.search(r"Date/Time run:\s*([^<]+)", report_text)
    actual_date = reported_date.group(1).strip() if reported_date else None
    expected_date = manifest["report_identity"].get(
        "run_time_text_in_report", "Friday 16 October 2026 04:16 UTC"
    )
    if actual_date != expected_date:
        raise SystemExit(
            f"Frozen report timestamp mismatch: HTML={actual_date}, manifest={expected_date}"
        )
    print(f"Verified and reused manifest-pinned snapshot: {manifest_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--new-snapshot-dir",
        type=Path,
        help="Create a separate, new snapshot directory. The directory must not already exist.",
    )
    args = parser.parse_args()
    if args.new_snapshot_dir is None:
        manifest_path = ROOT / "source_manifest.json"
        if not manifest_path.exists():
            raise SystemExit(
                "No frozen manifest exists. Use --new-snapshot-dir PATH to create a separate snapshot; this study is never overwritten."
            )
        return verify_frozen_snapshot(manifest_path)

    snapshot_dir = args.new_snapshot_dir.expanduser().resolve()
    if snapshot_dir.exists():
        raise SystemExit(
            f"Refusing to overwrite existing snapshot directory: {snapshot_dir}"
        )
    snapshot_dir.mkdir(parents=True)
    raw_dir = snapshot_dir / "raw"
    raw_dir.mkdir(parents=True)

    items = [
        fetch(REPORT_URL, raw_dir / "ibex-opentitan-latest-report.html", snapshot_dir),
        fetch(
            IBEX_JSON_URL, raw_dir / "ibex-opentitan-latest-report.json", snapshot_dir
        ),
        fetch(DISCOVERY_URL, raw_dir / "opentitan-dvdata.html", snapshot_dir),
        fetch(DASHBOARD_URL, raw_dir / "opentitan-dashboard.html", snapshot_dir),
        fetch(
            OT_DASHBOARD_SCRIPT_URL,
            raw_dir / "opentitan-nightly-results.js",
            snapshot_dir,
        ),
        fetch(
            OT_CHIP_REPORT_URL,
            raw_dir / "opentitan-earlgrey-dv-latest-report.json",
            snapshot_dir,
        ),
        fetch(
            OT_CHIP_SUMMARY_URL,
            raw_dir / "opentitan-earlgrey-dv-summary-latest-report.html",
            snapshot_dir,
        ),
    ]
    for rel in SOURCE_PATHS:
        path = raw_dir / "ibex-source" / rel
        item = fetch(IBEX_BASE + rel, path, snapshot_dir)
        item["git_commit"] = IBEX_COMMIT
        item["repository_path"] = rel
        items.append(item)

    report_path = raw_dir / "ibex-opentitan-latest-report.html"
    report_text = report_path.read_text(encoding="utf-8", errors="replace")
    report_commit_match = re.search(r"/tree/([0-9a-f]{40})", report_text)
    reported_run_time = re.search(r"Date/Time run:\s*([^<]+)", report_text)
    report_commit = report_commit_match.group(1) if report_commit_match else None
    if report_commit != IBEX_COMMIT:
        raise SystemExit(
            f"Fetched report commit does not match pinned generator sources: {report_commit}"
        )
    if not reported_run_time:
        raise SystemExit("Fetched report does not expose its run timestamp")
    opentitan_chip_report = json.loads(
        (raw_dir / "opentitan-earlgrey-dv-latest-report.json").read_text(
            encoding="utf-8"
        )
    )
    manifest = {
        "collection_created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "One pinned Ibex/OpenTitan report snapshot and its report-generation code; dashboard pages retained for source inspection.",
        "warning": "The report request URL is a mutable `latest` alias. Use the retained response bytes and internal run timestamp/commit as the observation identity. A later recollection is a different snapshot.",
        "report_identity": {
            "project": "lowRISC Ibex, configuration label opentitan",
            "run_time_text_in_report": reported_run_time.group(1).strip(),
            "ibex_git_commit": IBEX_COMMIT,
            "run_identity_limit": "The HTML exposes no CI job ID or immutable report URL. The run time plus Git commit identify this retained report only; they do not provide a permanent upstream address.",
        },
        "opentitan_dashboard_chip_report_identity": {
            "report_timestamp": opentitan_chip_report.get("report_timestamp"),
            "git_revision": opentitan_chip_report.get("git_revision"),
            "git_branch_name": opentitan_chip_report.get("git_branch_name"),
            "report_type": opentitan_chip_report.get("report_type"),
            "tool": opentitan_chip_report.get("tool"),
            "build_seed": opentitan_chip_report.get("build_seed"),
            "freshness_note": "The dashboard's `latest` top-level Earlgrey simulation report identity is determined by this report's internal timestamp, not by the dashboard page retrieval date.",
        },
        "files": items,
    }
    manifest_path = snapshot_dir / "source_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(manifest_path)
    for item in items:
        print(item["path"])
        print(item["headers_path"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
