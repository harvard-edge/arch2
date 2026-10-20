#!/usr/bin/env python3
"""Capture public Tiny Tapeout TT06 index and community feedback responses.

The collector preserves exact response bodies under raw/ and records response
codes, URLs, and SHA-256 hashes in capture-manifest.json. It never submits or
modifies feedback.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote


INDEX_URL = "https://index.tinytapeout.com/tt06.json"
SHUTTLE_URL = "https://www.tinytapeout.com/chips/tt06/"
FEEDBACK_LIST_URL = "https://app.tinytapeout.com/api/shuttles/feedback"
FEEDBACK_BASE = "https://app.tinytapeout.com/api/shuttles/tt06"
INDEX_REPO_COMMIT = "953ee731882f3710306f9d4ac2667caf10207738"
SITE_REPO_COMMIT = "c8a667269685a38bd10a41aefb8a25a7e3660cdb"

PINNED_SOURCE_FILES = [
    (
        "index-source/README.md",
        f"https://raw.githubusercontent.com/TinyTapeout/tinytapeout-index/{INDEX_REPO_COMMIT}/README.md",
    ),
    (
        "index-source/tt06.json",
        f"https://raw.githubusercontent.com/TinyTapeout/tinytapeout-index/{INDEX_REPO_COMMIT}/index/tt06.json",
    ),
    (
        "index-source/shuttle.schema.json",
        f"https://raw.githubusercontent.com/TinyTapeout/tinytapeout-index/{INDEX_REPO_COMMIT}/schemas/shuttle.schema.json",
    ),
    (
        "site-source/feedback.ts",
        f"https://raw.githubusercontent.com/TinyTapeout/tinytapeout_www/{SITE_REPO_COMMIT}/functions/model/feedback.ts",
    ),
    (
        "site-source/SiliconProvenProjects.tsx",
        f"https://raw.githubusercontent.com/TinyTapeout/tinytapeout_www/{SITE_REPO_COMMIT}/functions/components/SiliconProvenProjects.tsx",
    ),
    (
        "site-source/ProjectFeedbackList.tsx",
        f"https://raw.githubusercontent.com/TinyTapeout/tinytapeout_www/{SITE_REPO_COMMIT}/functions/components/ProjectFeedbackList.tsx",
    ),
    (
        "site-source/silicon-proven.tsx",
        f"https://raw.githubusercontent.com/TinyTapeout/tinytapeout_www/{SITE_REPO_COMMIT}/functions/chips/silicon-proven.tsx",
    ),
]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def fetch(url: str) -> tuple[int, bytes]:
    # curl is used because this host's Python certificate store may not trust
    # the system proxy CA. The response body remains byte-for-byte intact.
    result = subprocess.run(
        [
            "curl",
            "--silent",
            "--show-error",
            "--location",
            "--max-time",
            "40",
            "--user-agent",
            "Arch2EvidenceResearch/1.0 (public-source snapshot)",
            "--write-out",
            "\n%{http_code}",
            url,
        ],
        check=False,
        capture_output=True,
    )
    if result.returncode:
        raise RuntimeError(
            f"curl failed for {url}: {result.stderr.decode(errors='replace').strip()}"
        )
    body, sep, status = result.stdout.rpartition(b"\n")
    if not sep:
        raise RuntimeError(f"curl did not return an HTTP status for {url}")
    return int(status), body


def write_raw(root: pathlib.Path, rel: str, url: str) -> dict[str, object]:
    code, body = fetch(url)
    if code != 200:
        raise RuntimeError(f"HTTP {code} from {url}")
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    return {
        "url": url,
        "path": f"raw/{rel}",
        "http_status": code,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
    }


def verify_or_recover(root: pathlib.Path) -> int:
    """Verify pinned local sources; recover only missing files after hash check."""
    source_manifest_path = root / "source_manifest.json"
    capture_manifest_path = root / "capture-manifest.json"
    if not source_manifest_path.is_file() or not capture_manifest_path.is_file():
        raise RuntimeError(
            "Frozen source_manifest.json and capture-manifest.json are required"
        )
    source_manifest = json.loads(source_manifest_path.read_text())
    capture_manifest = json.loads(capture_manifest_path.read_text())
    files = source_manifest.get("files")
    if not isinstance(files, list) or not files:
        raise RuntimeError("source_manifest.json has no pinned files list")
    capture_rows = {row["path"]: row for row in capture_manifest.get("responses", [])}
    if set(capture_rows) != {row.get("path") for row in files}:
        raise RuntimeError(
            "capture-manifest and source_manifest file inventories differ"
        )
    if source_manifest.get("population") != capture_manifest.get("population"):
        raise RuntimeError(
            "capture-manifest and source_manifest population identities differ"
        )
    recovered = 0
    for row in files:
        rel = row["path"]
        expected = row["sha256"]
        if capture_rows[rel].get("sha256") != expected:
            raise RuntimeError(f"Manifest hash disagreement for {rel}")
        target = root / rel
        if target.exists():
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            if actual != expected:
                raise RuntimeError(
                    f"Frozen source hash changed for {rel}: expected {expected}, got {actual}"
                )
            continue
        url = row.get("url")
        if not url:
            raise RuntimeError(f"Cannot recover missing file without URL: {rel}")
        code, body = fetch(url)
        actual = hashlib.sha256(body).hexdigest()
        if code != 200 or actual != expected:
            raise RuntimeError(
                f"Recovery rejected for {rel}: HTTP {code}, SHA-256 {actual} != {expected}"
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".restore-", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(body)
            os.replace(tmp_name, target)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        recovered += 1
    return recovered


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=pathlib.Path, default=pathlib.Path(__file__).parent
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="capture a new snapshot into a new, absent output directory",
    )
    args = parser.parse_args()
    if not 1 <= args.workers <= 4:
        parser.error("--workers must be between 1 and 4")
    out = args.output.resolve()
    if not args.refresh:
        recovered = verify_or_recover(out)
        print(
            f"Frozen snapshot verified; recovered {recovered} missing raw files by exact hash."
        )
        print(
            f"Verified: {out / 'source_manifest.json'} and {out / 'capture-manifest.json'}"
        )
        return 0
    if out.exists():
        raise RuntimeError(
            f"Refresh output must be a new, absent directory; refusing to overwrite {out}"
        )
    out.mkdir(parents=True, exist_ok=False)
    raw = out / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    started = utc_now()
    index_rec = write_raw(raw, "tt06-index.json", INDEX_URL)
    shuttle_rec = write_raw(raw, "tt06-shuttle.html", SHUTTLE_URL)
    aggregate_rec = write_raw(raw, "all-shuttles-feedback.json", FEEDBACK_LIST_URL)
    pinned_sources = [write_raw(raw, path, url) for path, url in PINNED_SOURCE_FILES]
    index_snapshot = json.loads((raw / "tt06-index.json").read_bytes())
    indexed_source = json.loads((raw / "index-source/tt06.json").read_bytes())
    if indexed_source != index_snapshot:
        raise RuntimeError(
            "Live index API response differs from pinned index-repository file"
        )
    index = index_snapshot
    if index.get("id") != "tt06" or not isinstance(index.get("projects"), list):
        raise RuntimeError("Unexpected TT06 index shape")
    projects = index["projects"]
    macros = [project.get("macro") for project in projects]
    if any(not isinstance(macro, str) or not macro for macro in macros):
        raise RuntimeError("Index contains project row without a macro ID")
    if len(macros) != len(set(macros)):
        raise RuntimeError(
            "Duplicate macro IDs within TT06 index; resolve before extraction"
        )

    def collect_one(macro: str) -> dict[str, object]:
        safe_macro = quote(macro, safe="")
        macro_key = hashlib.sha256(macro.encode("utf-8")).hexdigest()
        rel = f"feedback/{macro_key}.json"
        rec = write_raw(raw, rel, f"{FEEDBACK_BASE}/{safe_macro}/feedback")
        # Brief spacing per worker keeps the public API load modest.
        time.sleep(0.08)
        return rec

    feedback_records: list[dict[str, object]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(collect_one, macro): macro for macro in macros}
        for future in concurrent.futures.as_completed(futures):
            try:
                feedback_records.append(future.result())
            except Exception as exc:
                for other in futures:
                    other.cancel()
                raise RuntimeError(
                    f"Could not capture feedback for {futures[future]}: {exc}"
                ) from exc
    feedback_records.sort(key=lambda rec: str(rec["path"]))

    manifest = {
        "study": "Tiny Tapeout TT06 community feedback coverage",
        "collection_started_utc": started,
        "collection_finished_utc": utc_now(),
        "population": {
            "shuttle_id": index["id"],
            "index_name": index.get("name"),
            "index_updated": index.get("updated"),
            "index_commit": index.get("commit"),
            "indexed_macro_rows": len(projects),
            "unique_macro_ids": len(set(macros)),
            "unit": "one indexed project macro on shuttle TT06",
            "exclusions": [],
        },
        "upstream_source_revisions": {
            "tinytapeout-index_git_commit": INDEX_REPO_COMMIT,
            "tinytapeout_www_git_commit": SITE_REPO_COMMIT,
        },
        "responses": [
            index_rec,
            shuttle_rec,
            aggregate_rec,
            *pinned_sources,
            *feedback_records,
        ],
    }
    (out / "capture-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    source_manifest = {
        "study": "Tiny Tapeout TT06 community feedback coverage",
        "collected_utc": manifest["collection_finished_utc"],
        "population": manifest["population"],
        "upstream_source_revisions": manifest["upstream_source_revisions"],
        "files": [
            {
                "path": record["path"],
                "sha256": record["sha256"],
                "url": record["url"],
                "http_status": record["http_status"],
                "bytes": record["bytes"],
            }
            for record in manifest["responses"]
        ],
    }
    (out / "source_manifest.json").write_text(
        json.dumps(source_manifest, indent=2) + "\n"
    )
    print(
        f"Captured {len(projects)} indexed macros and {len(feedback_records)} feedback responses."
    )
    print(f"Generated: {out / 'capture-manifest.json'}")
    print(f"Generated raw directory: {raw}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
