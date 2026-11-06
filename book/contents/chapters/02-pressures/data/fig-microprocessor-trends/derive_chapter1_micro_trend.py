#!/usr/bin/env python3
"""Recompute the CPU rows of chapter1-micro-trend.csv from the retained Rupp sample.

    python3 book/contents/chapters/02-pressures/data/fig-microprocessor-trends/derive_chapter1_micro_trend.py

Stdlib only. Reads the five 50yrs/*.dat files retained in
rupp-microprocessor-trend-f2121ab2/ (commit f2121ab2b83a156b114fe34e62e1edeca98e8e38 of
github.com/karlrupp/microprocessor-trend-data, CC-BY 4.0, fetched 2026-11-02), checks their
hashes, and compares every recomputed row with the CSV. Exits non-zero on any difference.

Rule: per series, drop the EXCLUDED records, take the maximum in each four-year bucket
counted from 1971, keep the earliest record on a tie, and round the year to two decimals.

The source carries no chip names, so the names below are inferred from the record values.
They are the reason for each exclusion, not facts read from the source. The Xeon Phi
records include a self-hosted part; excluding them is a choice about what the chapter's
CPU line means, and the plotted thread count depends on it.
"""
import csv
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "rupp-microprocessor-trend-f2121ab2"
CSV = HERE / "chapter1-micro-trend.csv"
SHA256 = {
    "cores.dat": "b0efcdfaba82eeefb3963fe6f6837d903d7d498b327e99893423d48e87d1d285",
    "frequency.dat": "ae52bac897771b582461e53ee8a7aba23898c85bc8c66c02806c0b823fdfa99c",
    "specint.dat": "0530676822175382ef53a62715d17bdf5920befd4f2c0269598fa062e49efada",
    "transistors.dat": "7678b84278d7ac0e8a56af9844f1620bbda4c8e0903490f1f0119519de7fa652",
    "watts.dat": "4ede46a852180761cf3ff13412cdec197baf96b08e10efccf5971751c47c439a",
}
SERIES = {
    "transistors": "transistors.dat",
    "specint": "specint.dat",
    "frequency": "frequency.dat",
    "cpu_watts": "watts.dat",
    "cpu_threads": "cores.dat",
}
# (date, inferred part): record value per file. Two records share 2021.9; the second one
# (55 billion transistors, 64 threads, 2600 MHz, 100 W) stays in the sample.
EXCLUDED = {
    (2013.4, "Xeon Phi"): {
        "transistors.dat": 5000000.0,
        "frequency.dat": 1200.0,
        "watts.dat": 300.0,
        "cores.dat": 240.0,
    },
    (2016.5, "Xeon Phi"): {
        "frequency.dat": 1500.0,
        "watts.dat": 245.0,
        "cores.dat": 272.0,
    },
    (2018.5, "Quadro GV100 GPU"): {
        "transistors.dat": 21100000.0,
        "frequency.dat": 1200.0,
        "watts.dat": 250.0,
        "cores.dat": 80.0,
    },
    (2021.9, "Radeon MI250 GPU"): {
        "transistors.dat": 58200000.0,
        "frequency.dat": 1000.0,
        "watts.dat": 500.0,
        "cores.dat": 208.0,
    },
}


def records(name):
    path = SOURCE / name
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != SHA256[name]:
        sys.exit(f"{name}: sha256 {digest} does not match the pinned value")
    out = []
    for line in path.read_text().splitlines():
        parts = line.split()
        if parts and not line.startswith("#"):
            out.append((float(parts[0]), float(parts[1])))
    return out


def derive(name):
    rows = records(name)
    for (date, part), values in EXCLUDED.items():
        if name in values:
            if (date, values[name]) not in rows:
                sys.exit(f"{name}: excluded record ({date}, {values[name]}) for {part} is absent")
            rows.remove((date, values[name]))
    best = {}
    for year, value in rows:
        bucket = int((year - 1971) // 4)
        held = best.get(bucket)
        if held is None or value > held[1] or (value == held[1] and year < held[0]):
            best[bucket] = (year, value)
    return [(round(best[b][0], 2), best[b][1]) for b in sorted(best)]


def main():
    with CSV.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    failures = checked = 0
    for series, name in SERIES.items():
        got = derive(name)
        want = [(float(r["year"]), float(r["value"])) for r in rows if r["series"] == series]
        if len(got) != len(want):
            print(f"{series}: {len(got)} derived rows, {len(want)} in the CSV")
            failures += 1
        for a, b in zip(got, want):
            checked += 1
            if a != b:
                print(f"{series}: derived {a}, CSV has {b}")
                failures += 1
    if failures:
        sys.exit(f"{failures} difference(s)")
    print(f"{checked} rows of {CSV.name} recomputed exactly from {SOURCE.name}/")


if __name__ == "__main__":
    main()
