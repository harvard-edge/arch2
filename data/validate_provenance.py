#!/usr/bin/env python3
"""Screen dataset metadata and prevent known withdrawn artifacts returning.

This checks selected fabrication patterns, explicit input records, row counts,
and published-file references. Matching a source-like header or generator name
does not authenticate a measurement. Randomized experiments and bootstraps can
be legitimate; the historical patterns checked here concern fabricated values.
Source accuracy and numerical correctness require separate audits.

    python3 data/validate_provenance.py

Exits non-zero on any violation, so it can gate a commit or a build.
"""

from __future__ import annotations

import csv as csvlib
import itertools
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RECEIPTS = ROOT / "data" / "datasets"
SYNTHETIC = ROOT / "data" / "synthetic"  # must not exist
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

# Exact withdrawn release artifacts, not a filename-pattern ban on new studies.
WITHDRAWN = (
    [f"ch{i}_data.csv" for i in range(1, 13)]
    + [f"plot_ch{i}.png" for i in range(1, 13)]
    + [
        "plot_all_wishlist.py",
        "chapter1-github-software-hardware-divide.csv",
        "chapter1_empirical_data_gap_and_funnel.csv",
        "chapter9-interconnect-logca-specs.csv",
    ]
)
for name in WITHDRAWN:
    if (RECEIPTS / name).exists():
        problems.append(f"Withdrawn release artifact remains: data/datasets/{name}")

records = yaml.safe_load((RECEIPTS / "provenance.yml").read_text()).get("receipts", [])
recorded_paths = {r["path"] for r in records}
for record in records:
    path = (ROOT / record["path"]).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        problems.append(
            f"Recorded input is missing or outside repository: {record['path']}"
        )
        continue
    if path.suffix == ".csv" and "rows" in record:
        with path.open() as handle:
            count = sum(
                1
                for _ in csvlib.DictReader(
                    itertools.dropwhile(lambda line: line.startswith("#"), handle)
                )
            )
        if count != record["rows"]:
            problems.append(
                f"{record['path']}: recorded {record['rows']} rows, found {count}"
            )


def scraper_for(csv_name: str) -> Path | None:
    """Find a scraper mentioning this CSV; this does not establish dataflow."""
    for d in (SCRAPERS,):
        if not d.is_dir():
            continue
        for py in sorted(d.glob("*.py")):
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


# --- rule 1 + 2: datasets must be measured or transcribed -------------------
candidate_csvs: list[Path] = []
if RECEIPTS.is_dir():
    candidate_csvs.extend(sorted(RECEIPTS.glob("*.csv")))
if STUDIES.is_dir():
    candidate_csvs.extend(sorted(STUDIES.rglob("*.csv")))
candidate_csvs.extend(sorted((ROOT / "book" / "contents").rglob("*.csv")))

for csv in candidate_csvs:
    hdr = header_of(csv)
    if SYNTH_MARK in hdr:
        problems.append(
            f"{csv.relative_to(ROOT)} declares itself synthetic. Generated data "
            f"is not kept in the repository; delete it."
        )
        continue

    script = scraper_for(csv.name)
    if script:
        why = fabricates(script)
        if why:
            problems.append(
                f"{csv.relative_to(ROOT)} is GENERATED ({why}). Generated values "
                f"are not evidence; delete the file and its generator."
            )
            continue

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
            notes.append(
                f"metadata  {csv.relative_to(ROOT)}  (generator mention: {script.name}; not executed)"
            )
    else:
        head = hdr
        cols = csv.read_text(errors="ignore").splitlines()
        cols = next((l for l in cols if not l.startswith("#")), "").lower()
        # a transcribed dataset names its source per row, or in its header
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
        if str(csv.relative_to(ROOT)) in recorded_paths:
            notes.append(f"metadata  {csv.relative_to(ROOT)}  (explicit input record)")
        elif per_row or in_header:
            notes.append(
                f"metadata  {csv.relative_to(ROOT)}  (source-like header or column; not authenticated)"
            )
        else:
            unprovenanced.append(csv.relative_to(ROOT))

# --- rule 3: no quarantine directory, and nothing unused on the site -------
if SYNTHETIC.exists():
    problems.append(
        "data/synthetic/ exists. Generated data is deleted, not quarantined."
    )

# --- rule 4: study bundles with build_receipt.json must match retained hashes
import hashlib
import json

for receipt_file in sorted(STUDIES.glob("*/build_receipt.json")):
    study_dir = receipt_file.parent
    if not (study_dir / "provenance.yml").is_file():
        problems.append(f"{study_dir.relative_to(ROOT)} missing provenance.yml")

for prov_file in sorted(
    list(STUDIES.glob("*/provenance.yml"))
    + list((ROOT / "book" / "contents").rglob("provenance.yml"))
):
    prov_dir = prov_file.parent
    prov_data = yaml.safe_load(prov_file.read_text(encoding="utf-8")) or {}
    for ds in prov_data.get("datasets", []) or []:
        if isinstance(ds, dict) and "file" in ds:
            ds_path = (prov_dir / ds["file"]).resolve()
            if not ds_path.is_file():
                problems.append(
                    f"{prov_file.relative_to(ROOT)} declares missing dataset: {ds['file']}"
                )
    prod = prov_data.get("produced_by")
    if (
        isinstance(prod, str)
        and prod.strip().endswith(".py")
        and "," not in prod
        and ";" not in prod
        and " and " not in prod
    ):
        prod_path = (ROOT / prod.strip()).resolve()
        if not prod_path.is_file():
            prod_path = (prov_dir / prod.strip()).resolve()
        if not prod_path.is_file():
            problems.append(
                f"{prov_file.relative_to(ROOT)} declares missing produced_by script: {prod}"
            )

for receipt_file in sorted(STUDIES.glob("*/build_receipt.json")):
    study_dir = receipt_file.parent
    manifest_file = study_dir / "source_manifest.json"
    if manifest_file.is_file():
        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
        for item in manifest_data.get("files", []):
            if not isinstance(item, dict) or "path" not in item or "sha256" not in item:
                continue
            target = study_dir / item["path"]
            if target.is_file():
                actual = hashlib.sha256(target.read_bytes()).hexdigest()
                if actual != item["sha256"]:
                    problems.append(
                        f"{study_dir.name}/source_manifest.json hash mismatch for {item['path']}"
                    )
    receipt_data = json.loads(receipt_file.read_text(encoding="utf-8"))
    files_field = receipt_data.get("files", {})
    if isinstance(files_field, dict):
        for rel_path, expected_sha in files_field.items():
            target = study_dir / rel_path
            if target.is_file():
                actual = hashlib.sha256(target.read_bytes()).hexdigest()
                if actual != expected_sha:
                    problems.append(
                        f"{study_dir.name}/build_receipt.json hash mismatch for {rel_path}"
                    )
    elif isinstance(files_field, list):
        for item in files_field:
            if isinstance(item, dict) and "path" in item and "sha256" in item:
                target = ROOT / item["path"]
                if not target.is_file():
                    target = study_dir / item["path"]
                if target.is_file():
                    actual = hashlib.sha256(target.read_bytes()).hexdigest()
                    if actual != item["sha256"]:
                        problems.append(
                            f"{study_dir.name}/build_receipt.json hash mismatch for {item['path']}"
                        )

site = ROOT / "www" / "data" / "observatory"
if site.is_dir():
    readers = [ROOT / "www", ROOT / "data" / "notebooks"]
    corpus = ""
    for d in readers:
        for f in d.rglob("*"):
            if f.suffix in (".qmd", ".py", ".md") and "observatory" not in f.parts:
                corpus += f.read_text(errors="ignore")
    for pub in sorted(site.iterdir()):
        if pub.name.startswith("."):
            continue
        if f"data/observatory/{pub.name}" not in corpus:
            problems.append(
                f"{pub.relative_to(ROOT)} is published on the site but no page or "
                f"notebook reads it. Remove it or link it from a verified exhibit."
            )


if __name__ == "__main__":
    for n in notes:
        print(n)
    print()
    if unprovenanced:
        print(
            f"{len(unprovenanced)} CSV(s) have no recognized inline metadata or central input record."
        )
        print(
            "Separate study records may cover raw inputs and outputs. This warning "
            "does not establish that their provenance is absent.\n"
        )
        for u in unprovenanced:
            print(f"  ? {u}")
        print()
    if problems:
        print(f"{len(problems)} PROVENANCE VIOLATION(S):\n")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print(
        f"{len(candidate_csvs)} CSVs screened; no selected metadata violations found."
    )
    print(
        "This does not certify numerical correctness, source support, or historical execution."
    )
