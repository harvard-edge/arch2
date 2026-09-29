#!/usr/bin/env python3
"""Assign each extracted erratum to a subsystem with the committed rule set.

Inputs:
    errata.csv                 every erratum (from data/scrapers/mine_cpu_errata.py)
    .cache/errata_text.jsonl   erratum body text (git-ignored; re-created by the scraper)
    classification_rules.yml   the rules, as data

Output:
    errata_classified.csv      one row per erratum with class, group, the
                               field that matched, and the pattern that matched

The matching semantics are documented at the top of classification_rules.yml.
There is no default class: an erratum no rule matches is "Unclassified".

    python3 data/studies/01-silicon-errata-archaeology/classify_errata.py
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
UNCLASSIFIED = "Unclassified"


def compile_rules(path: Path) -> list[dict]:
    spec = yaml.safe_load(path.read_text())
    out = []
    for c in spec["classes"]:
        pats = []
        for raw, flags in [(p, re.I) for p in c.get("patterns", [])] + [
            (p, 0) for p in c.get("case_sensitive", [])
        ]:
            body = r"[\s-]+".join(re.escape(w) for w in str(raw).split())
            # Whole-word boundaries: no letter or digit on either side.
            rx = re.compile(rf"(?<![A-Za-z0-9]){body}(?:e?s)?(?![A-Za-z0-9])", flags)
            pats.append((str(raw), rx))
        out.append({"name": c["name"], "group": c["group"], "patterns": pats})
    return out


def classify(text: str, rules: list[dict]) -> tuple[str, str, str] | None:
    for c in rules:
        for raw, rx in c["patterns"]:
            if rx.search(text):
                return c["name"], c["group"], raw
    return None


def main() -> int:
    rules = compile_rules(HERE / "classification_rules.yml")
    body = {}
    for line in (HERE / ".cache" / "errata_text.jsonl").open():
        d = json.loads(line)
        body[(d["family"], d["erratum_id"])] = d["description"]
    rows = list(csv.DictReader((HERE / "errata.csv").open()))
    out = []
    for r in rows:
        hit = classify(r["title"], rules)
        where = "title"
        if hit is None:
            hit = classify(body[(r["family"], r["erratum_id"])], rules)
            where = "description"
        if hit is None:
            hit, where = (UNCLASSIFIED, "none", ""), "none"
        out.append(
            {
                **r,
                "source_doc": f"{r['vendor']} {r['doc_number']} rev {r['revision']}",
                "subsystem": hit[0],
                "group": hit[1],
                "matched_on": where,
                "matched_pattern": hit[2],
            }
        )
    dest = HERE / "errata_classified.csv"
    with dest.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["subsystem"]] = counts.get(r["subsystem"], 0) + 1
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"{v:5d}  {100 * v / len(out):5.1f}%  {k}")
    by = {}
    for r in out:
        by[r["matched_on"]] = by.get(r["matched_on"], 0) + 1
    print("matched on:", by)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
