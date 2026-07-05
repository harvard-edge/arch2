#!/usr/bin/env python3
"""Generate lightweight analysis tables for the DBLP corpus pilot."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

DEFAULT_INPUT = Path("data/processed/corpus-pilot/papers.csv")
DEFAULT_OUTPUT_DIR = Path("data/processed/corpus-pilot")

ERAS = {
    "early": {("ISCA", 1973), ("MICRO", 1972), ("HPCA", 1995), ("ASPLOS", 1982)},
    "2005_2006": {("ISCA", 2005), ("MICRO", 2005), ("HPCA", 2005), ("ASPLOS", 2006)},
    "2015": {("ISCA", 2015), ("MICRO", 2015), ("HPCA", 2015), ("ASPLOS", 2015)},
    "latest": {("ISCA", 2025), ("MICRO", 2025), ("HPCA", 2026), ("ASPLOS", 2026)},
}

KEYWORDS = [
    "chiplet",
    "package",
    "wafer",
    "llm",
    "transformer",
    "pim",
    "near-data",
    "datacenter",
    "cloud",
    "compiler",
    "runtime",
    "verification",
    "formal",
    "synthesis",
    "simulator",
    "benchmark",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def load_papers(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def category_tokens(row: dict[str, str]) -> list[str]:
    return [token for token in row["categories"].split("; ") if token]


def build_era_category_counts(papers: list[dict[str, str]]) -> list[dict[str, object]]:
    rows = []
    for era, venue_years in ERAS.items():
        subset = [
            row for row in papers if (row["venue"], int(row["year"])) in venue_years
        ]
        category_counts: Counter[str] = Counter()
        for row in subset:
            category_counts.update(category_tokens(row))
        total = len(subset)
        for category, count in sorted(category_counts.items()):
            rows.append(
                {
                    "era": era,
                    "category": category,
                    "papers": count,
                    "total_papers": total,
                    "share": round(count / total, 4) if total else 0,
                }
            )
    return rows


def build_keyword_hits(papers: list[dict[str, str]]) -> list[dict[str, object]]:
    rows = []
    for keyword in KEYWORDS:
        matches = [row for row in papers if keyword in row["paper_title"].lower()]
        rows.append(
            {
                "keyword": keyword,
                "papers": len(matches),
                "examples": " | ".join(
                    f"{row['venue']} {row['year']}: {row['paper_title']}"
                    for row in matches[:5]
                ),
            }
        )
    return rows


def main() -> int:
    args = parse_args()
    papers = load_papers(args.input)
    write_csv(
        args.output_dir / "era_category_counts.csv",
        build_era_category_counts(papers),
        ["era", "category", "papers", "total_papers", "share"],
    )
    write_csv(
        args.output_dir / "keyword_hits.csv",
        build_keyword_hits(papers),
        ["keyword", "papers", "examples"],
    )
    print(f"analyzed {len(papers)} pilot papers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
