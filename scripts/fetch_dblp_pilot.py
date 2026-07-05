#!/usr/bin/env python3
"""Fetch and parse the DBLP pilot corpus for Architecture 2.0.

This script intentionally collects bibliographic metadata only. It fetches DBLP
TOC XML pages named in a manifest, caches the raw XML under data/raw, and emits
processed CSV/JSON under data/processed/corpus-pilot.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DEFAULT_MANIFEST = Path("data/manifests/dblp-pilot-pages.json")
DEFAULT_RAW_DIR = Path("data/raw/dblp-toc")
DEFAULT_OUTPUT_DIR = Path("data/processed/corpus-pilot")

TITLE_CATEGORIES = {
    "ai_ml": [
        "artificial intelligence",
        "machine learning",
        "neural",
        "deep learning",
        "llm",
        "dnn",
        "cnn",
        "transformer",
        "inference",
        "training",
        "tensor",
        "sparse",
        "sparsity",
        "recommendation",
        "gpt",
        "bert",
        "rag",
    ],
    "accelerators": [
        "accelerat",
        "gpu",
        "tpu",
        "fpga",
        "dsa",
        "asic",
        "vector",
        "simd",
        "systolic",
        "pim",
        "near-data",
        "near data",
    ],
    "memory": [
        "memory",
        "cache",
        "dram",
        "sram",
        "nvm",
        "flash",
        "ssd",
        "prefetch",
        "coherence",
        "tlb",
        "locality",
    ],
    "interconnect_network": [
        "network",
        "interconnect",
        "noc",
        "communication",
        "collective",
        "bandwidth",
        "routing",
        "ethernet",
    ],
    "software_compilers_runtime": [
        "compiler",
        "runtime",
        "operating system",
        "os-",
        "scheduling",
        "scheduler",
        "programming",
        "software",
        "kernel",
        "jit",
    ],
    "datacenter_cloud": [
        "datacenter",
        "data center",
        "warehouse",
        "cloud",
        "server",
        "fleet",
        "serving",
        "distributed",
    ],
    "power_energy_thermal": [
        "power",
        "energy",
        "thermal",
        "temperature",
        "cooling",
        "voltage",
        "battery",
    ],
    "security_reliability": [
        "security",
        "secure",
        "confidential",
        "privacy",
        "side-channel",
        "fault",
        "reliability",
        "resilien",
        "attack",
    ],
    "verification_tools": [
        "verification",
        "formal",
        "simulation",
        "simulator",
        "modeling",
        "model",
        "emulation",
        "synthesis",
        "eda",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sleep", type=float, default=2.0)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-fetch", action="store_true")
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def iter_pages(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    for venue_entry in manifest["venues"]:
        venue = venue_entry["venue"]
        for year_entry in venue_entry["years"]:
            for ordinal, url in enumerate(year_entry["pages"], start=1):
                pages.append(
                    {
                        "venue": venue,
                        "year": int(year_entry["year"]),
                        "ordinal": ordinal,
                        "url": url,
                        "notes": year_entry.get("notes", ""),
                    }
                )
    return pages


def cache_path(raw_dir: Path, page: dict[str, Any]) -> Path:
    slug = Path(urlparse(page["url"]).path).name
    return raw_dir / page["venue"].lower() / str(page["year"]) / slug


def fetch_url(url: str, retries: int) -> bytes:
    context = ssl.create_default_context(cafile=ca_bundle())
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "arch2 synthesis corpus pilot (bibliographic metadata; contact via repository owner)"
        },
    )
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(
                request, timeout=45, context=context
            ) as response:
                status = getattr(response, "status", 200)
                if status != 200:
                    raise RuntimeError(f"{url} returned HTTP {status}")
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt >= retries:
                raise
            delay = min(60.0, 5.0 * (attempt + 1))
            print(f"HTTP 429 for {url}; retrying in {delay:.1f}s", file=sys.stderr)
            time.sleep(delay)
        except (
            ConnectionResetError,
            TimeoutError,
            urllib.error.URLError,
            OSError,
        ) as exc:
            if attempt >= retries:
                raise
            delay = min(60.0, 5.0 * (attempt + 1))
            print(
                f"{type(exc).__name__} for {url}; retrying in {delay:.1f}s",
                file=sys.stderr,
            )
            time.sleep(delay)
    raise RuntimeError(f"failed to fetch {url}")


def ca_bundle() -> str | None:
    try:
        import certifi  # type: ignore

        return certifi.where()
    except Exception:
        pass
    for candidate in [
        Path("/etc/ssl/cert.pem"),
        Path("/opt/homebrew/etc/ca-certificates/cert.pem"),
        Path("/usr/local/etc/ca-certificates/cert.pem"),
    ]:
        if candidate.exists():
            return str(candidate)
    return None


def maybe_fetch(
    page: dict[str, Any], raw_dir: Path, no_fetch: bool, retries: int
) -> tuple[Path, bytes, dict[str, str]]:
    path = cache_path(raw_dir, page)
    if path.exists():
        data = path.read_bytes()
        return path, data, {"retrieval_method": "cache", "retrieved_at": ""}
    if no_fetch:
        raise FileNotFoundError(f"missing cached file for {page['url']}: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = fetch_url(page["url"], retries)
    path.write_bytes(data)
    return path, data, {"retrieval_method": "network", "retrieved_at": utc_now()}


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def child_text(element: ET.Element, tag: str) -> str:
    child = element.find(tag)
    if child is None:
        return ""
    return clean_text("".join(child.itertext()))


def children_text(element: ET.Element, tag: str) -> list[str]:
    values = []
    for child in element.findall(tag):
        text = clean_text("".join(child.itertext()))
        if text:
            values.append(text)
    return values


def absolute_dblp_url(path_or_url: str) -> str:
    if not path_or_url:
        return ""
    if path_or_url.startswith("http"):
        return path_or_url
    return "https://dblp.org/" + path_or_url.lstrip("/")


def categorize_title(title: str) -> list[str]:
    title_l = title.lower()
    categories = []
    for category, needles in TITLE_CATEGORIES.items():
        if any(term_matches(title_l, needle) for needle in needles):
            categories.append(category)
    return categories


def term_matches(title_l: str, term: str) -> bool:
    if re.fullmatch(r"[a-z0-9]+", term) and len(term) <= 4:
        return (
            re.search(rf"(?<![a-z0-9]){re.escape(term)}s?(?![a-z0-9])", title_l)
            is not None
        )
    return term in title_l


def parse_page_xml(
    xml_bytes: bytes, page: dict[str, Any], source_id: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    root = ET.fromstring(xml_bytes)
    proceedings_rows = []
    paper_rows = []

    for proc in root.iter("proceedings"):
        key = proc.attrib.get("key", "")
        proceedings_rows.append(
            {
                "source_id": source_id,
                "venue": page["venue"],
                "year": page["year"],
                "ordinal": page["ordinal"],
                "volume": child_text(proc, "booktitle"),
                "title": child_text(proc, "title"),
                "publisher": child_text(proc, "publisher"),
                "isbn": child_text(proc, "isbn"),
                "dblp_key": key,
                "dblp_url": absolute_dblp_url(child_text(proc, "url")),
                "ee_url": child_text(proc, "ee"),
            }
        )

    for article in root.iter("inproceedings"):
        title = child_text(article, "title")
        authors = children_text(article, "author")
        categories = categorize_title(title)
        paper_rows.append(
            {
                "source_id": source_id,
                "venue": page["venue"],
                "year": page["year"],
                "ordinal": page["ordinal"],
                "paper_title": title,
                "authors": "; ".join(authors),
                "author_count": len(authors),
                "pages": child_text(article, "pages"),
                "doi_or_ee": child_text(article, "ee"),
                "dblp_key": article.attrib.get("key", ""),
                "dblp_url": absolute_dblp_url(child_text(article, "url")),
                "categories": "; ".join(categories),
            }
        )
    return proceedings_rows, paper_rows


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def summarize(
    paper_rows: list[dict[str, Any]], source_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    by_venue_year = Counter((row["venue"], row["year"]) for row in paper_rows)
    by_category = Counter()
    by_category_venue_year: dict[tuple[str, int, str], int] = Counter()
    for row in paper_rows:
        categories = [c for c in row["categories"].split("; ") if c]
        for category in categories:
            by_category[category] += 1
            by_category_venue_year[(row["venue"], row["year"], category)] += 1

    return {
        "generated_at": utc_now(),
        "paper_count": len(paper_rows),
        "source_count": len(source_rows),
        "paper_counts_by_venue_year": [
            {"venue": venue, "year": year, "papers": count}
            for (venue, year), count in sorted(by_venue_year.items())
        ],
        "category_counts": [
            {"category": category, "papers": count}
            for category, count in sorted(by_category.items())
        ],
        "category_counts_by_venue_year": [
            {"venue": venue, "year": year, "category": category, "papers": count}
            for (venue, year, category), count in sorted(by_category_venue_year.items())
        ],
    }


def write_category_csv(path: Path, summary: dict[str, Any]) -> None:
    rows = summary["category_counts_by_venue_year"]
    write_csv(path, rows, ["venue", "year", "category", "papers"])


def main() -> int:
    args = parse_args()
    manifest = load_manifest(args.manifest)
    pages = iter_pages(manifest)

    if args.dry_run:
        for page in pages:
            print(f"{page['venue']} {page['year']} [{page['ordinal']}]: {page['url']}")
        return 0

    proceedings_rows: list[dict[str, Any]] = []
    paper_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []

    for index, page in enumerate(pages, start=1):
        source_id = f"{page['venue'].lower()}-{page['year']}-{page['ordinal']}"
        try:
            raw_path, data, retrieval = maybe_fetch(
                page, args.raw_dir, args.no_fetch, args.retries
            )
            digest = hashlib.sha256(data).hexdigest()
            source_rows.append(
                {
                    "source_id": source_id,
                    "venue": page["venue"],
                    "year": page["year"],
                    "ordinal": page["ordinal"],
                    "url": page["url"],
                    "raw_path": str(raw_path),
                    "sha256": digest,
                    "retrieved_at": retrieval["retrieved_at"],
                    "retrieval_method": retrieval["retrieval_method"],
                    "notes": page.get("notes", ""),
                }
            )
            page_proceedings, page_papers = parse_page_xml(data, page, source_id)
            proceedings_rows.extend(page_proceedings)
            paper_rows.extend(page_papers)
            print(
                f"{source_id}: {len(page_proceedings)} proceedings, {len(page_papers)} papers"
            )
        except (
            ET.ParseError,
            urllib.error.URLError,
            RuntimeError,
            FileNotFoundError,
        ) as exc:
            print(f"ERROR {source_id} {page['url']}: {exc}", file=sys.stderr)
            return 1
        if index != len(pages) and not args.no_fetch:
            time.sleep(args.sleep)

    summary = summarize(paper_rows, source_rows)

    write_csv(
        args.output_dir / "sources.csv",
        source_rows,
        [
            "source_id",
            "venue",
            "year",
            "ordinal",
            "url",
            "raw_path",
            "sha256",
            "retrieved_at",
            "retrieval_method",
            "notes",
        ],
    )
    write_csv(
        args.output_dir / "proceedings.csv",
        proceedings_rows,
        [
            "source_id",
            "venue",
            "year",
            "ordinal",
            "volume",
            "title",
            "publisher",
            "isbn",
            "dblp_key",
            "dblp_url",
            "ee_url",
        ],
    )
    write_csv(
        args.output_dir / "papers.csv",
        paper_rows,
        [
            "source_id",
            "venue",
            "year",
            "ordinal",
            "paper_title",
            "authors",
            "author_count",
            "pages",
            "doi_or_ee",
            "dblp_key",
            "dblp_url",
            "categories",
        ],
    )
    write_category_csv(args.output_dir / "category_counts.csv", summary)
    write_json(args.output_dir / "summary.json", summary)
    print(f"wrote {len(paper_rows)} papers to {args.output_dir / 'papers.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
