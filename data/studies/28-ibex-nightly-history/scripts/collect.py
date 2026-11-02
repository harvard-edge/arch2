#!/usr/bin/env python3
"""Enumerate and download every dated Ibex/OpenTitan nightly regression JSON.

The lowRISC bucket at https://ibex.reports.lowrisc.org/ is a public GCS bucket
that answers S3-style XML listings (1,000 keys per page, `marker` pagination).
Dated reports are named opentitan/ibex-regr-report-DD-MM-YYYY.{json,html}.

Outputs (all under the study root, the parent of this scripts/ directory):
  listing.csv   every key in the bucket as listed (key, size, etag, last_modified)
  raw/          one file per dated JSON key, named after the key's basename
  manifest.csv  key, url, date (ISO), bytes, sha256, http_status, fetched_utc,
                plus listing metadata and an error column for failed keys

Rerunnable: a file already on disk whose MD5 equals the listing ETag is not
re-fetched (status "cached"); pass --refetch to force. Downloads are polite:
bounded concurrency, retries with exponential backoff.

Downloaded bytes are untrusted data: nothing here executes or imports them.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
BUCKET = "https://ibex.reports.lowrisc.org/"
KEY_RE = re.compile(r"^/?opentitan/ibex-regr-report-(\d{2})-(\d{2})-(\d{4})\.json$")
NS = "{http://doc.s3.amazonaws.com/2006-03-01}"
USER_AGENT = (
    "arch2-ibex-nightly-collector/1.0 (research; contact via lowRISC issue if needed)"
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def http_get(url: str, timeout: int = 60, retries: int = 5) -> tuple[int, bytes]:
    """GET with exponential backoff. Returns (status, body). Raises on final failure."""
    delay = 1.0
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            if 400 <= exc.code < 500 and exc.code != 429:
                return exc.code, exc.read()
            last_exc = exc
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            last_exc = exc
        time.sleep(delay)
        delay = min(delay * 2, 30)
    raise RuntimeError(f"GET failed after {retries} attempts: {url}: {last_exc}")


def list_bucket() -> list[dict]:
    """Walk every listing page of the bucket and return all Contents entries."""
    items: list[dict] = []
    marker = ""
    page = 0
    while True:
        params = {"max-keys": "1000"}
        if marker:
            params["marker"] = marker
        url = BUCKET + "?" + urllib.parse.urlencode(params)
        status, body = http_get(url)
        if status != 200:
            raise RuntimeError(f"listing page {page} returned HTTP {status}")
        root = ET.fromstring(body)
        page += 1
        page_items = []
        for c in root.iter(NS + "Contents"):
            page_items.append(
                {
                    "key": c.findtext(NS + "Key"),
                    "size": int(c.findtext(NS + "Size") or 0),
                    "etag": (c.findtext(NS + "ETag") or "").strip('"'),
                    "last_modified": c.findtext(NS + "LastModified"),
                    "generation": c.findtext(NS + "Generation"),
                }
            )
        items.extend(page_items)
        truncated = (root.findtext(NS + "IsTruncated") or "false").lower() == "true"
        next_marker = root.findtext(NS + "NextMarker")
        print(
            f"listing page {page}: {len(page_items)} keys, truncated={truncated}",
            file=sys.stderr,
        )
        if not truncated:
            break
        marker = next_marker or (page_items[-1]["key"] if page_items else "")
        if not marker:
            raise RuntimeError("truncated listing without a usable marker")
    return items


def key_url(key: str) -> str:
    """URL for a key. A key that begins with "/" must have that slash
    percent-encoded: the host collapses "//opentitan/..." to the canonical
    object, which silently serves the wrong bytes (seen for 03-07-2024)."""
    if key.startswith("/"):
        return BUCKET + "%2F" + urllib.parse.quote(key[1:], safe="/")
    return BUCKET + urllib.parse.quote(key, safe="/")


def key_date(key: str) -> str:
    m = KEY_RE.match(key)
    dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
    return f"{yyyy}-{mm}-{dd}"


def local_name(key: str) -> str:
    """raw/ filename. A leading-slash key gets a distinguishing prefix."""
    base = key.rsplit("/", 1)[-1]
    return ("leadingslash__" + base) if key.startswith("/") else base


def fetch_one(item: dict, refetch: bool) -> dict:
    key = item["key"]
    url = key_url(key)
    dest = RAW / local_name(key)
    row = {
        "key": key,
        "url": url,
        "date": key_date(key),
        "local_file": str(dest.relative_to(ROOT)),
        "listing_size": item["size"],
        "listing_etag": item["etag"],
        "listing_last_modified": item["last_modified"],
        "bytes": "",
        "sha256": "",
        "md5": "",
        "md5_matches_etag": "",
        "http_status": "",
        "fetched_utc": "",
        "status": "",
        "error": "",
    }
    if dest.exists() and not refetch:
        data = dest.read_bytes()
        md5 = hashlib.md5(data).hexdigest()
        if md5 == item["etag"] and len(data) == item["size"]:
            row.update(
                bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
                md5=md5,
                md5_matches_etag=True,
                http_status=200,
                status="cached",
                fetched_utc=datetime.fromtimestamp(
                    dest.stat().st_mtime, timezone.utc
                ).isoformat(timespec="seconds"),
            )
            return row
    try:
        status, data = http_get(url)
    except Exception as exc:  # noqa: BLE001 - record and move on
        row.update(status="error", error=str(exc)[:300], fetched_utc=now_utc())
        return row
    row["http_status"] = status
    row["fetched_utc"] = now_utc()
    if status != 200:
        row.update(status="http_error", error=f"HTTP {status}")
        return row
    dest.write_bytes(data)
    md5 = hashlib.md5(data).hexdigest()
    row.update(
        bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        md5=md5,
        md5_matches_etag=(md5 == item["etag"]),
        status="fetched",
    )
    if md5 != item["etag"]:
        row["error"] = "md5 != listing etag"
    return row


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--workers", type=int, default=6, help="concurrent downloads (<=8)")
    ap.add_argument("--refetch", action="store_true", help="ignore cached raw files")
    ap.add_argument("--limit", type=int, default=0, help="debug: only first N keys")
    args = ap.parse_args()
    workers = max(1, min(args.workers, 8))
    RAW.mkdir(parents=True, exist_ok=True)

    items = list_bucket()
    items.sort(key=lambda d: d["key"])
    with (ROOT / "listing.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=["key", "size", "etag", "last_modified", "generation"]
        )
        w.writeheader()
        w.writerows(items)
    print(f"bucket keys listed: {len(items)}", file=sys.stderr)

    targets = [it for it in items if KEY_RE.match(it["key"])]
    targets.sort(key=lambda it: (key_date(it["key"]), it["key"]))
    if args.limit:
        targets = targets[: args.limit]
    print(f"dated JSON keys: {len(targets)}", file=sys.stderr)

    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fetch_one, it, args.refetch): it for it in targets}
        done = 0
        for fut in as_completed(futs):
            rows.append(fut.result())
            done += 1
            if done % 100 == 0:
                print(f"  {done}/{len(targets)}", file=sys.stderr)
    rows.sort(key=lambda r: (r["date"], r["key"]))
    fields = list(rows[0].keys()) if rows else ["key"]
    with (ROOT / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    n_ok = sum(r["status"] in ("fetched", "cached") for r in rows)
    n_bad = len(rows) - n_ok
    n_mismatch = sum(r["md5_matches_etag"] is False for r in rows)
    print(
        f"manifest rows: {len(rows)}  ok: {n_ok}  failed: {n_bad}  md5/etag mismatches: {n_mismatch}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
