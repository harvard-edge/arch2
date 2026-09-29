#!/usr/bin/env python3
"""Draw the seeded, class-stratified audit sample of classified errata.

Writes audit_sample.csv with one row per sampled erratum and an empty
`audit_label` column. The rule label is kept in the file but the blind
worksheet the auditor reads (.cache/audit_worksheet.txt, git-ignored) omits it
and presents the rows in a shuffled order, so the reader labels each erratum
from its title and body text alone.

    python3 data/studies/01-silicon-errata-archaeology/audit_sample.py

Design: 18 errata per class drawn without replacement (every row when a class
has fewer), seed 20260929. The rules were frozen before this sample was drawn.
"""

from __future__ import annotations

import csv
import json
import random
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = 20260929
PER_CLASS = 18


def main() -> int:
    rows = list(csv.DictReader((HERE / "errata_classified.csv").open()))
    by = defaultdict(list)
    for r in rows:
        by[r["subsystem"]].append(r)
    rng = random.Random(SEED)
    sample = []
    for cls in sorted(by):
        pool = sorted(by[cls], key=lambda r: (r["family"], r["erratum_id"]))
        k = min(PER_CLASS, len(pool))
        sample += rng.sample(pool, k)
    order = list(range(len(sample)))
    rng.shuffle(order)
    out = []
    for n, i in enumerate(order, 1):
        r = sample[i]
        out.append(
            {
                "audit_id": f"A{n:03d}",
                "family": r["family"],
                "erratum_id": r["erratum_id"],
                "source_doc": r["source_doc"],
                "title": r["title"],
                "rule_label": r["subsystem"],
                "matched_on": r["matched_on"],
                "class_size": len(by[r["subsystem"]]),
                "audit_label": "",
                "audit_note": "",
                "arithmetic_datapath": "",
            }
        )
    dest = HERE / "audit_sample.csv"
    if dest.exists():
        # Never overwrite recorded labels. Instead, prove the committed sample is
        # exactly the one this seed draws from the committed classification.
        have = [
            (r["audit_id"], r["family"], r["erratum_id"], r["rule_label"])
            for r in csv.DictReader(dest.open())
        ]
        want = [
            (r["audit_id"], r["family"], r["erratum_id"], r["rule_label"]) for r in out
        ]
        if have != want:
            raise SystemExit(
                f"{dest.name} does not match the seeded draw; the classification changed"
            )
        print(
            f"{dest.name}: {len(have)} rows match the seeded draw exactly; labels left untouched"
        )
        return 0
    with dest.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)

    text = {}
    for line in (HERE / ".cache" / "errata_text.jsonl").open():
        d = json.loads(line)
        text[(d["family"], d["erratum_id"])] = d
    with (HERE / ".cache" / "audit_worksheet.txt").open("w") as f:
        for r in out:
            d = text[(r["family"], r["erratum_id"])]
            f.write(f"{r['audit_id']} | {r['family']} {r['erratum_id']}\n")
            f.write(f"  TITLE: {r['title']}\n")
            f.write(f"  PROBLEM: {d['description'][:900]}\n")
            f.write(f"  IMPLICATION: {d['implication'][:300]}\n\n")
    print(f"{len(out)} errata sampled from {len(by)} classes -> {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
