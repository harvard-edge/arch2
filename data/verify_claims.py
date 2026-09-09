#!/usr/bin/env python3
"""Recompute every published headline number from the dataset it claims to come from.

The gap this closes: validate_provenance.py checks that a receipt RECORDS a source.
It does not check that the number a reader sees can be DERIVED from that source. A
figure whose headline exists only as a string literal in a matplotlib annotation
passes every existing gate. This one fails it.

Each claim declares the value a reader is shown and the expression that produces it
from the CSV. A claim that cannot be expressed against its own data does not belong
on the website.

    python3 data/verify_claims.py [--json]

Exits non-zero on any mismatch.
"""
from __future__ import annotations
import csv, io, json, statistics, sys
from pathlib import Path

ROOT = (
    Path(__file__).resolve().parent.parent
    if (Path(__file__).resolve().parent.name == "data")
    else Path("/Users/VJ/GitHub/Arch2")
)
STUDIES = ROOT / "data" / "studies"
SPEC = Path(sys.argv[0]).resolve().parent / "claims.json"
if not SPEC.exists():
    SPEC = Path(
        "/tmp/claude-501/-Users-VJ-GitHub/7c967237-04b0-4eed-bc31-104e95536225/scratchpad/claims.json"
    )


def load(p: Path):
    """Read a receipt CSV, skipping the '#' provenance header block."""
    return list(
        csv.DictReader(
            io.StringIO("".join(l for l in p.open() if not l.startswith("#")))
        )
    )


def spread(v):
    """Full range as a percentage of the mean magnitude."""
    return (max(v) - min(v)) / abs(sum(v) / len(v)) * 100


ENV = {
    "median": statistics.median,
    "spread": spread,
    "len": len,
    "sum": sum,
    "max": max,
    "min": min,
    "float": float,
    "int": int,
    "set": set,
    "abs": abs,
}


def main() -> int:
    spec = json.loads(SPEC.read_text())
    results, fails = [], 0
    for study, cfg in sorted(spec.items()):
        path = STUDIES / study / cfg["csv"]
        if not path.exists():
            print(f"MISSING  {study}: {cfg['csv']}")
            fails += 1
            continue
        rows = load(path)
        for c in cfg["claims"]:
            try:
                got = eval(c["derive"], {"__builtins__": {}, **ENV, "rows": rows}, {})
            except Exception as e:
                print(f"ERROR    {study}/{c['id']}: {e}")
                fails += 1
                continue
            want, tol = c["value"], c["tol"]
            ok = abs(got - want) <= tol
            fails += 0 if ok else 1
            results.append(
                {
                    "study": study,
                    "id": c["id"],
                    "label": c["label"],
                    "claimed": want,
                    "computed": round(got, 4),
                    "ok": ok,
                }
            )
            mark = "  ok  " if ok else " FAIL "
            print(
                f"[{mark}] {study[:2]}  {c['label']:44s} claimed={want:<10} computed={round(got,4)}"
            )
    print()
    print(
        f"{len(results)} published claims recomputed from source data, {fails} mismatch(es)."
    )
    if "--json" in sys.argv:
        (Path(SPEC).parent / "claims-result.json").write_text(
            json.dumps(results, indent=2)
        )
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
