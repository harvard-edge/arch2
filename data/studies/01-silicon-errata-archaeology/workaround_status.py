#!/usr/bin/env python3
"""Export unvalidated workaround text for parser diagnosis; not publication data.

The former workaround_status.csv and its subgroup counts were withdrawn after
source checks found page furniture, repeated titles, and omitted continuations.
This helper preserves the parsed text and literal text-pattern labels so a future
field-level audit can find defects. A label does not establish the presence of a
workaround or usable guidance. See README.md for the confirmed source cases.

Inputs: errata.csv and the git-ignored .cache/errata_text.jsonl.
Output: .cache/workaround_candidates.csv, with every row marked unvalidated.

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
        return "none_with_trailing_text"
    return "other_text"


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
    out = HERE / ".cache" / "workaround_candidates.csv"
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "family",
                "erratum_id",
                "vendor",
                "status",
                "text_pattern",
                "validation_status",
                "parsed_text",
            ]
        )
        for r in errata:
            parsed = text[(r["family"], r["erratum_id"])]
            cls = classify(parsed)
            w.writerow(
                [
                    r["family"],
                    r["erratum_id"],
                    r["vendor"],
                    r["status"],
                    cls,
                    "unvalidated",
                    parsed,
                ]
            )
    print(
        f"UNVALIDATED diagnostic worksheet, not publication data: {out.relative_to(HERE.parents[2])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
