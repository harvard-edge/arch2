import csv
import json
import ssl
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {"User-Agent": "Arch2BookCrossrefScraper/4.0 (mailto:arch2-book@example.com)"}

CONFERENCES = {
    "ISCA": "International Symposium on Computer Architecture",
    "MICRO": "International Symposium on Microarchitecture",
    "ASPLOS": "Architectural Support for Programming Languages and Operating Systems",
    "HPCA": "High-Performance Computer Architecture",
}


def map_category(title):
    t = str(title).lower()
    if any(
        k in t
        for k in [
            "accelerator",
            "gpu",
            "neural",
            "dnn",
            "llm",
            "tensor",
            "systolic",
            "npu",
            "deep learning",
            "ai ",
            "machine learning",
        ]
    ):
        return "Domain Accelerators & AI"
    if any(
        k in t
        for k in [
            "multicore",
            "multi-core",
            "coherence",
            "interconnect",
            "network-on-chip",
            "noc",
            "chiplet",
            "topology",
            "synchronization",
        ]
    ):
        return "Multicore & Coherence"
    if any(
        k in t
        for k in [
            "memory",
            "cache",
            "dram",
            "sram",
            "storage",
            "nvm",
            "hbm",
            "pim",
            "nvram",
            "tlb",
            "prefetch",
        ]
    ):
        return "Memory Hierarchy"
    if any(
        k in t
        for k in [
            "compiler",
            "runtime",
            "software",
            "operating system",
            "os ",
            "code generation",
            "isa",
            "instruction set",
            "programming model",
        ]
    ):
        return "Software/Compilers"
    if any(
        k in t
        for k in [
            "verification",
            "tool",
            "simulation",
            "simulator",
            "benchmark",
            "emulation",
            "formal",
            "assertion",
            "drc",
            "testing",
        ]
    ):
        return "Verification/Tools"
    return "CPU Microarchitecture"


def fetch_crossref_papers(conf_abbr, title_query, max_papers=2000):
    papers = []
    offset = 0
    rows = 100

    print(f"Scraping {conf_abbr} ({title_query}) from Crossref...", flush=True)

    while len(papers) < max_papers and offset < 3000:
        url = f"https://api.crossref.org/works?query.container-title={urllib.parse.quote(title_query)}&rows={rows}&offset={offset}"
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("message", {}).get("items", [])
                if not items:
                    break

                for item in items:
                    title_list = item.get("title") or []
                    if not title_list:
                        continue
                    title = title_list[0]

                    # Extract publication year
                    year = None
                    for date_field in [
                        "published-print",
                        "published-online",
                        "issued",
                        "created",
                    ]:
                        if date_field in item and "date-parts" in item[date_field]:
                            parts = item[date_field]["date-parts"]
                            if parts and parts[0] and isinstance(parts[0][0], int):
                                year = parts[0][0]
                                break

                    doi = item.get("DOI", "")
                    citations = item.get("is-referenced-by-count", 0)

                    if title and year and 1970 <= year <= 2026:
                        # Exclude front matter
                        if any(
                            skip in title.lower()
                            for skip in [
                                "session details",
                                "welcome from",
                                "message from",
                                "table of contents",
                                "author index",
                                "keynote",
                            ]
                        ):
                            continue
                        papers.append(
                            {
                                "title": title,
                                "year": year,
                                "venue": conf_abbr,
                                "citations": citations,
                                "doi": doi,
                            }
                        )

                offset += rows
                print(
                    f"  [{conf_abbr}] Offset {offset}: Accumulated {len(papers)} papers...",
                    flush=True,
                )
                time.sleep(0.3)
        except Exception as e:
            print(f"  Error fetching {conf_abbr} at offset {offset}: {e}", flush=True)
            break

    return papers


def main():
    all_papers = []

    for abbr, full_title in CONFERENCES.items():
        conf_papers = fetch_crossref_papers(abbr, full_title, max_papers=2500)
        print(f"Finished {abbr}: {len(conf_papers)} papers harvested.\n", flush=True)
        all_papers.extend(conf_papers)

    print(f"==================================================", flush=True)
    print(
        f"TOTAL COMPLETE SCRAPED CORPUS ACROSS ALL 4 CONFERENCES: {len(all_papers)} PAPERS",
        flush=True,
    )
    print(f"==================================================", flush=True)

    # Save full raw dataset
    raw_csv_path = (
        REPO_ROOT / "data" / "source-receipts" / "full-conference-corpus-1973-2026.csv"
    )
    with open(raw_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Title", "Year", "Venue", "Citations", "DOI", "Category"])
        for p in all_papers:
            cat = map_category(p["title"])
            p["category"] = cat
            writer.writerow(
                [p["title"], p["year"], p["venue"], p["citations"], p["doi"], cat]
            )

    print(f"Saved full complete corpus to '{raw_csv_path}'", flush=True)

    # Aggregate into yearly trend receipt
    yearly_counts = defaultdict(lambda: defaultdict(int))
    for p in all_papers:
        yr = p["year"]
        cat = p["category"]
        yearly_counts[yr][cat] += 1

    years = sorted(yearly_counts.keys())
    cats = [
        "Domain Accelerators & AI",
        "Memory Hierarchy",
        "Multicore & Coherence",
        "Software/Compilers",
        "Verification/Tools",
        "CPU Microarchitecture",
    ]

    trend_csv_path = (
        REPO_ROOT
        / "data"
        / "source-receipts"
        / "chapter1-conference-paradigm-shifts.csv"
    )
    with open(trend_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Year", "Category", "Count", "SharePercentage"])
        for yr in years:
            total = sum(yearly_counts[yr].values())
            for cat in cats:
                cnt = yearly_counts[yr][cat]
                pct = (cnt / total * 100) if total > 0 else 0
                writer.writerow([yr, cat, cnt, round(pct, 2)])

    print(
        f"Updated conference paradigm shift receipt at '{trend_csv_path}'", flush=True
    )


if __name__ == "__main__":
    main()
