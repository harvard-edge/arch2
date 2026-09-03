#!/usr/bin/env python3
"""Fail if a generated dataset is presented as evidence.

Two rules, both learned from real defects in this repository:

1. Nothing under ``data/source-receipts/`` may be produced by a random number
   generator. Two files were, for weeks, while calling themselves provenance
   receipts.
2. A receipt header may not name a tool version that its own generating script
   hardcodes. That combination -- a claimed tool version and a literal in the
   generator -- is the signature of a fabricated measurement, because a real
   run reports its own version.

Also checks that every file under ``data/synthetic/`` says so on line one.

    python3 data/validate_provenance.py

Exits non-zero on any violation, so it can gate a commit or a build.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECEIPTS = ROOT / "data" / "source-receipts"
SYNTHETIC = ROOT / "data" / "synthetic"
SCRAPERS = ROOT / "data" / "scrapers"
STUDIES = ROOT / "data" / "studies"

# Value fabrication. Deliberately does NOT include a bare "random", because a
# legitimate harness passes a random SEED to a real tool -- that is what
# run_openroad_gcd_placement_seed_pilot.py does, and it is measurement.
FABRICATORS = [
    r"\brng\s*\.\s*(gauss|uniform|normalvariate|betavariate|triangular)\b",
    r"\brandom\s*\.\s*(gauss|uniform|normalvariate|triangular)\b",
    r"\bnp\s*\.\s*random\s*\.\s*(normal|randn|uniform|lognormal)\b",
    r"_gaussian_noise\s*\(",
]

# A real run reports these; a fabricated one hardcodes them.
TOOL_TOKENS = [
    "JasperGold",
    "SymbiYosys",
    "Boolector",
    "Bitwuzla",
    "Certitude",
    "OpenROAD",
    "OpenSTA",
    "Yosys",
    "Verilator",
    "TritonRoute",
    "pyslang",
]

SYNTH_MARK = "SYNTHETIC DATA. NOT A MEASUREMENT."

problems: list[str] = []
notes: list[str] = []
unprovenanced: list = []


def scraper_for(csv_name: str) -> Path | None:
    """The script that writes this CSV, if any."""
    if not SCRAPERS.is_dir():
        return None
    for py in sorted(SCRAPERS.glob("*.py")):
        if csv_name in py.read_text(errors="ignore"):
            return py
    return None


def fabricates(script: Path) -> str | None:
    src = script.read_text(errors="ignore")
    for pat in FABRICATORS:
        m = re.search(pat, src)
        if m:
            line = src[: m.start()].count("\n") + 1
            return f"{m.group(0)} at {script.name}:{line}"
    return None


def header_of(csv: Path) -> str:
    out = []
    for line in csv.read_text(errors="ignore").splitlines():
        if not line.startswith("#"):
            break
        out.append(line)
    return "\n".join(out)


# --- rule 1 + 2: receipts must be measured or transcribed -------------------
for csv in sorted(RECEIPTS.glob("*.csv")) if RECEIPTS.is_dir() else []:
    script = scraper_for(csv.name)
    if script:
        why = fabricates(script)
        if why:
            problems.append(
                f"{csv.relative_to(ROOT)} is GENERATED ({why}) but sits in "
                f"source-receipts/. Move it to data/synthetic/."
            )
            continue
        hdr = header_of(csv)
        src = script.read_text(errors="ignore")
        for tok in TOOL_TOKENS:
            if tok in hdr and re.search(rf'["\'][^"\']*{tok}[^"\']*["\']', src):
                problems.append(
                    f"{csv.relative_to(ROOT)} header names {tok}, and "
                    f"{script.name} contains it as a string literal. Either "
                    f"capture the version from the tool or drop the claim."
                )
                break
        else:
            notes.append(f"ok  {csv.name}  (measured via {script.name})")
    else:
        head = header_of(csv)
        cols = csv.read_text(errors="ignore").splitlines()
        cols = next((l for l in cols if not l.startswith("#")), "").lower()
        # a transcribed receipt names its source per row, or in its header
        per_row = any(
            k in cols
            for k in (
                "citation",
                "source",
                "url",
                "evidence_type",
                "source_note",
                "reference",
            )
        )
        in_header = any(
            k in head.lower()
            for k in ("source", "citation", "http", "doi", "derived", "transcribed")
        )
        if per_row or in_header:
            notes.append(f"ok  {csv.name}  (transcribed, carries provenance)")
        else:
            unprovenanced.append(csv.relative_to(ROOT))

# --- rule 3: synthetic files must announce themselves ----------------------
for csv in sorted(SYNTHETIC.glob("*.csv")) if SYNTHETIC.is_dir() else []:
    first = csv.read_text(errors="ignore").splitlines()[0] if csv.stat().st_size else ""
    if SYNTH_MARK not in first:
        problems.append(
            f"{csv.relative_to(ROOT)} does not carry '{SYNTH_MARK}' on line 1."
        )
    else:
        notes.append(f"ok  {csv.name}  (marked synthetic)")

# --- nothing generated may be published on the site ------------------------
site = ROOT / "www" / "data" / "observatory"
if site.is_dir() and SYNTHETIC.is_dir():
    synth_stems = {p.name.replace("SYNTHETIC-", "") for p in SYNTHETIC.glob("*.csv")}
    for pub in sorted(site.glob("*.csv")):
        if pub.name in synth_stems:
            problems.append(
                f"{pub.relative_to(ROOT)} is published on the site but its "
                f"source is quarantined as synthetic."
            )


if __name__ == "__main__":
    for n in notes:
        print(n)
    print()
    if unprovenanced:
        print(f"{len(unprovenanced)} receipt(s) carry NO provenance metadata.")
        print(
            "Not evidence of fabrication; evidence that the source was "
            "never recorded. Add a source column or a header note.\n"
        )
        for u in unprovenanced:
            print(f"  ? {u}")
        print()
    if problems:
        print(f"{len(problems)} PROVENANCE VIOLATION(S):\n")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print(f"{len(notes)} datasets checked. No provenance violations.")
