#!/usr/bin/env python3
"""Classify what each erratum's Workaround field says, without committing the text.

Inputs:
    errata.csv                 every erratum (from data/scrapers/mine_cpu_errata.py)
    .cache/errata_text.jsonl   erratum body text, including the Workaround field
                               (git-ignored; re-created by the scraper from the
                               hash-verified vendor PDFs)

Output:
    workaround_status.csv      one row per erratum: family, erratum_id, vendor,
                               status (the document's fix disposition), and
                               workaround_class

workaround_class is assigned by these rules, applied to the field with
surrounding whitespace removed:

    none_stated         the field is only "None", "None identified", or
                        "None Identified", with or without a final period
    none_with_guidance  the field begins with "None" or "None identified" and
                        then continues, usually with software guidance or a
                        partial mitigation
    workaround_stated   any other non-empty field (a BIOS, microcode, OS, or
                        software workaround, including "It is possible for the
                        BIOS to contain a workaround")
    not_extracted       the scraper recovered no Workaround text

Only the class is committed. The vendor text stays in the git-ignored cache,
as the rest of this study's descriptions do.

    python3 data/studies/01-silicon-errata-archaeology/workaround_status.py
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
NONE_ONLY = re.compile(r"none(\s+identified)?\.?", re.I)
NONE_PREFIX = re.compile(r"none(\s+identified)?\b", re.I)


def classify(text: str) -> str:
    t = text.strip()
    if not t:
        return "not_extracted"
    if NONE_ONLY.fullmatch(t):
        return "none_stated"
    if NONE_PREFIX.match(t):
        return "none_with_guidance"
    return "workaround_stated"


def main() -> int:
    errata = list(csv.DictReader((HERE / "errata.csv").open(encoding="utf-8")))
    text = {}
    with (HERE / ".cache" / "errata_text.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            j = json.loads(line)
            text[(j["family"], j["erratum_id"])] = j.get("workaround", "")
    missing = [
        (r["family"], r["erratum_id"])
        for r in errata
        if (r["family"], r["erratum_id"]) not in text
    ]
    if missing:
        raise SystemExit(
            f"{len(missing)} errata have no cached text; rerun the scraper"
        )
    out = HERE / "workaround_status.csv"
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["family", "erratum_id", "vendor", "status", "workaround_class"])
        for r in errata:
            cls = classify(text[(r["family"], r["erratum_id"])])
            w.writerow([r["family"], r["erratum_id"], r["vendor"], r["status"], cls])
    print(out.relative_to(HERE.parents[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
