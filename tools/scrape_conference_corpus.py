import csv
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


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


def main():
    raw_csv_path = (
        REPO_ROOT / "data" / "source-receipts" / "full-conference-corpus-1973-2026.csv"
    )
    trend_csv_path = (
        REPO_ROOT
        / "data"
        / "source-receipts"
        / "chapter1-conference-paradigm-shifts.csv"
    )

    yearly_counts = defaultdict(lambda: defaultdict(int))
    total_papers = 0

    with open(raw_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row["Year"].isdigit():
                continue
            yr = int(row["Year"])
            if yr < 1979 or yr > 2026:
                continue
            cat = map_category(row["Title"])
            yearly_counts[yr][cat] += 1
            total_papers += 1

    years = sorted(yearly_counts.keys())
    cats = [
        "Domain Accelerators & AI",
        "Memory Hierarchy",
        "Multicore & Coherence",
        "Software/Compilers",
        "Verification/Tools",
        "CPU Microarchitecture",
    ]

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
        f"Processed {total_papers} papers across {len(years)} continuous years (1979-2026)."
    )
    print(f"Saved complete continuous receipt to '{trend_csv_path}'")


if __name__ == "__main__":
    main()
