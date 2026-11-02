#!/usr/bin/env python3
"""Parse every retained Ibex nightly regression JSON into longitudinal tables.

Inputs:  manifest.csv (from collect.py) and raw/*.json
Outputs: derived/nightly.csv       one row per report (night)
         derived/group_night.csv   one row per (night, test group)
         derived/summary.json      headline numbers, gaps, duplicates, parse
                                   failures, schema variants, churn

Conventions follow data/studies/16-regression-records: integer counts are
carried through, percentages are computed from the integers, and coverage
columns are named after the JSON keys (results.coverage.<key>).

The raw JSON is untrusted data; it is only json.loads'ed, never executed.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
DERIVED = ROOT / "derived"
# Coverage keys in the order the HTML report prints them, when present.
COVERAGE_ORDER = [
    "covergroup",
    "block",
    "branch",
    "statement",
    "expression",
    "toggle",
    "fsm",
    "assertion",
]


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def parse_report(path: Path) -> dict:
    """Return a dict with parsed fields, or raise on malformed structure."""
    doc = json.loads(path.read_bytes().decode("utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("top level is not an object")
    results = doc.get("results")
    if not isinstance(results, dict):
        raise ValueError("results missing or not an object")
    tests = results.get("unmapped_tests")
    if not isinstance(tests, list):
        raise ValueError("results.unmapped_tests missing or not a list")
    coverage = results.get("coverage")
    if coverage is None:
        coverage = {}
    if not isinstance(coverage, dict):
        raise ValueError("results.coverage is not an object")
    groups = []
    test_keysets = set()
    for t in tests:
        if not isinstance(t, dict):
            raise ValueError("unmapped_tests entry is not an object")
        test_keysets.add(tuple(sorted(t.keys())))
        name = t.get("name")
        p = t.get("passing_runs")
        n = t.get("total_runs")
        if (
            not isinstance(name, str)
            or not isinstance(p, int)
            or not isinstance(n, int)
            or isinstance(p, bool)
            or isinstance(n, bool)
        ):
            raise ValueError(f"bad test entry: {json.dumps(t)[:200]}")
        if p < 0 or n < p:
            raise ValueError(f"invalid counts for {name}: {p}/{n}")
        groups.append(
            {
                "test_name": name,
                "passing_runs": p,
                "total_runs": n,
                "reported_pass_rate": t.get("pass_rate"),
            }
        )
    names = [g["test_name"] for g in groups]
    dup_names = sorted(k for k, v in Counter(names).items() if v > 1)
    schema = {
        "top_keys": tuple(sorted(doc.keys())),
        "results_keys": tuple(sorted(results.keys())),
        "coverage_keys": tuple(sorted(coverage.keys())),
        "test_keysets": tuple(sorted(test_keysets)),
        "testpoints_len": len(results.get("testpoints") or [])
        if isinstance(results.get("testpoints"), list)
        else None,
    }
    return {
        "tool": doc.get("tool"),
        "block_name": doc.get("block_name"),
        "block_variant": doc.get("block_variant"),
        "coverage": {k: coverage[k] for k in coverage},
        "groups": groups,
        "duplicate_test_names": dup_names,
        "schema": schema,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--manifest", type=Path, default=ROOT / "manifest.csv")
    ap.add_argument("--outdir", type=Path, default=DERIVED)
    args = ap.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    with args.manifest.open(encoding="utf-8") as f:
        manifest = [r for r in csv.DictReader(f)]
    ok_rows = [r for r in manifest if r["status"] in ("fetched", "cached")]
    failed_fetch = [
        r["key"] for r in manifest if r["status"] not in ("fetched", "cached")
    ]

    # ---- duplicate dates: keep one canonical report per date -----------------
    by_date: dict[str, list[dict]] = defaultdict(list)
    for r in ok_rows:
        by_date[r["date"]].append(r)
    duplicate_dates = {}
    chosen: list[dict] = []
    for d in sorted(by_date):
        cands = by_date[d]
        if len(cands) > 1:
            # Prefer the canonical (no leading slash) key; record both for the audit.
            canon = sorted(cands, key=lambda r: (r["key"].startswith("/"), r["key"]))
            duplicate_dates[d] = {
                "keys": [c["key"] for c in cands],
                "sha256_identical": len({c["sha256"] for c in cands}) == 1,
                "chosen_key": canon[0]["key"],
            }
            chosen.append(canon[0])
        else:
            chosen.append(cands[0])

    # ---- parse -------------------------------------------------------------
    nightly: list[dict] = []
    group_rows: list[dict] = []
    parse_failures: list[dict] = []
    schema_variants: Counter = Counter()
    schema_example: dict = {}
    coverage_keys_seen: set[str] = set()
    tools: Counter = Counter()
    dup_names_reports: dict[str, list[str]] = {}
    for r in chosen:
        path = ROOT / r["local_file"]
        try:
            rep = parse_report(path)
        except Exception as exc:  # noqa: BLE001
            parse_failures.append(
                {"date": r["date"], "key": r["key"], "error": str(exc)[:300]}
            )
            continue
        sig = json.dumps(rep["schema"], sort_keys=True)
        schema_variants[sig] += 1
        schema_example.setdefault(sig, r["date"])
        coverage_keys_seen.update(rep["coverage"].keys())
        tools[(rep["tool"], rep["block_name"], rep["block_variant"])] += 1
        if rep["duplicate_test_names"]:
            dup_names_reports[r["date"]] = rep["duplicate_test_names"]
        groups = rep["groups"]
        total = sum(g["total_runs"] for g in groups)
        passing = sum(g["passing_runs"] for g in groups)
        row = {
            "date": r["date"],
            "key": r["key"],
            "sha256": r["sha256"],
            "listing_last_modified": r["listing_last_modified"],
            "tool": rep["tool"],
            "n_groups": len(groups),
            "total_runs": total,
            "passing_runs": passing,
            "nonpassing_runs": total - passing,
            "pass_pct": round(100.0 * passing / total, 4) if total else "",
            "n_groups_with_nonpass": sum(
                g["total_runs"] > g["passing_runs"] for g in groups
            ),
            "n_groups_zero_runs": sum(g["total_runs"] == 0 for g in groups),
        }
        for k in rep["coverage"]:
            row[f"coverage_{k}"] = rep["coverage"][k]
        nightly.append(row)
        for g in groups:
            group_rows.append(
                {
                    "date": r["date"],
                    "test_name": g["test_name"],
                    "passing_runs": g["passing_runs"],
                    "total_runs": g["total_runs"],
                    "nonpass": g["total_runs"] > g["passing_runs"],
                }
            )
    nightly.sort(key=lambda x: x["date"])
    group_rows.sort(key=lambda x: (x["date"], x["test_name"]))

    cov_cols = [f"coverage_{k}" for k in COVERAGE_ORDER if k in coverage_keys_seen]
    cov_cols += sorted(
        f"coverage_{k}" for k in coverage_keys_seen if k not in COVERAGE_ORDER
    )
    fields = [
        "date",
        "n_groups",
        "total_runs",
        "passing_runs",
        "nonpassing_runs",
        "pass_pct",
        "n_groups_with_nonpass",
        "n_groups_zero_runs",
        *cov_cols,
        "tool",
        "key",
        "sha256",
        "listing_last_modified",
    ]
    write_csv(args.outdir / "nightly.csv", nightly, fields)
    write_csv(
        args.outdir / "group_night.csv",
        group_rows,
        ["date", "test_name", "passing_runs", "total_runs", "nonpass"],
    )

    # ---- summary -----------------------------------------------------------
    dates = [date.fromisoformat(x["date"]) for x in nightly]
    gaps: list[dict] = []
    if dates:
        for a, b in zip(dates, dates[1:]):
            if (b - a).days > 1:
                gaps.append(
                    {
                        "after": a.isoformat(),
                        "before": b.isoformat(),
                        "missing_days": (b - a).days - 1,
                    }
                )
    missing_days_total = sum(g["missing_days"] for g in gaps)
    per_year = Counter(d.year for d in dates)

    pass_pcts = [x["pass_pct"] for x in nightly if x["pass_pct"] != ""]
    n_groups_list = [x["n_groups"] for x in nightly]
    total_runs_list = [x["total_runs"] for x in nightly]

    # per-group failing-night fractions, over nights in which the group appears
    nights_present: Counter = Counter()
    nights_failing: Counter = Counter()
    for g in group_rows:
        nights_present[g["test_name"]] += 1
        if g["nonpass"]:
            nights_failing[g["test_name"]] += 1
    frac = {n: nights_failing[n] / nights_present[n] for n in nights_present}
    n_names = len(nights_present)
    n_fail_gt50 = sum(v > 0.5 for v in frac.values())
    n_fail_lt10 = sum(v < 0.1 for v in frac.values())
    n_never_fail = sum(v == 0 for v in frac.values())
    n_always_fail = sum(v == 1.0 for v in frac.values())

    # churn: groups entering / leaving the failing set between consecutive nights
    failing_by_date: dict[str, set] = defaultdict(set)
    present_by_date: dict[str, set] = defaultdict(set)
    for g in group_rows:
        present_by_date[g["date"]].add(g["test_name"])
        if g["nonpass"]:
            failing_by_date[g["date"]].add(g["test_name"])
    enters, leaves, set_changes, consecutive_pairs = [], [], [], 0
    for a, b in zip(nightly, nightly[1:]):
        fa, fb = failing_by_date[a["date"]], failing_by_date[b["date"]]
        enters.append(len(fb - fa))
        leaves.append(len(fa - fb))
        set_changes.append(
            len(set(present_by_date[b["date"]]) ^ set(present_by_date[a["date"]]))
        )
        if (date.fromisoformat(b["date"]) - date.fromisoformat(a["date"])).days == 1:
            consecutive_pairs += 1
    # same churn but only over truly consecutive calendar days
    enters_c, leaves_c = [], []
    for a, b in zip(nightly, nightly[1:]):
        if (date.fromisoformat(b["date"]) - date.fromisoformat(a["date"])).days == 1:
            fa, fb = failing_by_date[a["date"]], failing_by_date[b["date"]]
            enters_c.append(len(fb - fa))
            leaves_c.append(len(fa - fb))

    def stats(xs):
        if not xs:
            return None
        return {
            "min": min(xs),
            "median": statistics.median(xs),
            "mean": round(statistics.fmean(xs), 4),
            "max": max(xs),
        }

    summary = {
        "extracted_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_bucket": "https://ibex.reports.lowrisc.org/ (prefix opentitan/ibex-regr-report-DD-MM-YYYY.json)",
        "manifest_rows": len(manifest),
        "fetch_failures": failed_fetch,
        "n_reports_parsed": len(nightly),
        "n_parse_failures": len(parse_failures),
        "parse_failures": parse_failures,
        "duplicate_dates": duplicate_dates,
        "first_date": nightly[0]["date"] if nightly else None,
        "last_date": nightly[-1]["date"] if nightly else None,
        "calendar_span_days": (dates[-1] - dates[0]).days + 1 if dates else None,
        "reports_per_year": {str(k): v for k, v in sorted(per_year.items())},
        "gaps": {
            "n_gaps": len(gaps),
            "missing_days_total": missing_days_total,
            "largest": sorted(gaps, key=lambda g: -g["missing_days"])[:10],
            "all": gaps,
        },
        "pass_pct": stats(pass_pcts),
        "n_groups": stats(n_groups_list),
        "total_runs": stats(total_runs_list),
        "n_groups_with_nonpass": stats([x["n_groups_with_nonpass"] for x in nightly]),
        "nights_with_all_passing": sum(
            x["n_groups_with_nonpass"] == 0 for x in nightly
        ),
        "nights_with_zero_total_runs": sum(x["total_runs"] == 0 for x in nightly),
        "distinct_test_names_ever": n_names,
        "groups_failing_gt50pct_of_their_nights": n_fail_gt50,
        "groups_failing_lt10pct_of_their_nights": n_fail_lt10,
        "groups_never_failing": n_never_fail,
        "groups_always_failing": n_always_fail,
        "group_nights_present_distribution": stats(list(nights_present.values())),
        "churn_all_adjacent_reports": {
            "pairs": len(enters),
            "mean_entering_failing_set": round(statistics.fmean(enters), 4)
            if enters
            else None,
            "mean_leaving_failing_set": round(statistics.fmean(leaves), 4)
            if leaves
            else None,
            "mean_group_membership_change": round(statistics.fmean(set_changes), 4)
            if set_changes
            else None,
        },
        "churn_consecutive_calendar_days_only": {
            "pairs": len(enters_c),
            "mean_entering_failing_set": round(statistics.fmean(enters_c), 4)
            if enters_c
            else None,
            "mean_leaving_failing_set": round(statistics.fmean(leaves_c), 4)
            if leaves_c
            else None,
        },
        "coverage_keys_seen": sorted(coverage_keys_seen),
        "tool_block_variant_counts": {
            " / ".join(str(p) for p in k): v for k, v in tools.items()
        },
        "reports_with_duplicate_test_names": dup_names_reports,
        "schema_variants": [
            {
                "count": c,
                "first_seen": schema_example[sig],
                "signature": json.loads(sig),
            }
            for sig, c in schema_variants.most_common()
        ],
        "per_group_failing_fraction": {n: round(frac[n], 4) for n in sorted(frac)},
        "per_group_nights_present": {
            n: nights_present[n] for n in sorted(nights_present)
        },
    }
    (args.outdir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(args.outdir / "nightly.csv")
    print(args.outdir / "group_night.csv")
    print(args.outdir / "summary.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
