#!/usr/bin/env python3
"""Compute audit agreement and audit-adjusted subsystem shares.

Inputs:
    errata_classified.csv    rule label for every erratum (the population)
    audit_sample.csv         seeded stratified sample with the auditor's label
    reporting_classes.yml    post-audit merge of rule classes into reporting classes

Output:
    audit_metrics.json       every number the chapter and the figure use

Definitions
    Stratum      a rule class (including Unclassified); N_c errata in the
                 population, n_c audited.
    Precision    for a class c, the fraction of audited errata in stratum c whose
                 audit label equals c. Wilson 95% interval.
    Agreement    the population share of errata whose rule label equals the
                 audit label, estimated from the stratified sample by weighting
                 each stratum's agreement rate by N_c / N. An Unclassified
                 erratum always counts as a disagreement.
    Adjusted share
                 for a reporting class R, the estimated population share of
                 errata whose AUDIT label falls in R:
                     sum_c (N_c / N) * (share of stratum-c sample with audit label in R).
                 This corrects for errata the rules put in the wrong class in
                 both directions.
    Intervals    95% percentile intervals from a stratified bootstrap (10,000
                 replicates, seed 20260929) that resamples audited errata within
                 each stratum. Strata audited in full (n_c = N_c) are held fixed.
                 Resampling without a finite-population correction makes the
                 intervals slightly conservative.

    python3 data/studies/01-silicon-errata-archaeology/audit_metrics.py
"""

from __future__ import annotations

import csv
import json
import math
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SEED = 20260929
B = 10_000
MIN_PRECISION = 0.70
MIN_WILSON_LOW = 0.50


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def pct(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    i = q * (len(xs) - 1)
    lo, hi = math.floor(i), math.ceil(i)
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)


def main() -> int:
    pop = list(csv.DictReader((HERE / "errata_classified.csv").open()))
    aud = list(csv.DictReader((HERE / "audit_sample.csv").open()))
    rep = yaml.safe_load((HERE / "reporting_classes.yml").read_text())
    if any(not r["audit_label"] for r in aud):
        raise SystemExit("audit_sample.csv has unlabeled rows")

    N = len(pop)
    Nc = Counter(r["subsystem"] for r in pop)
    strata = defaultdict(list)
    for r in aud:
        strata[r["rule_label"]].append(r)
    for c, rows in strata.items():
        if rows[0]["class_size"] and int(rows[0]["class_size"]) != Nc[c]:
            raise SystemExit(
                f"class size for {c} changed since the sample was drawn; redraw"
            )
    if set(strata) != set(Nc):
        raise SystemExit("every rule class must be sampled")

    to_rep = {}
    for R in rep["reporting"]:
        for m in R["members"]:
            to_rep[m] = R["name"]
    for m in rep["not_resolved"]["members"]:
        to_rep[m] = rep["not_resolved"]["name"]
    rep_names = [R["name"] for R in rep["reporting"]] + [rep["not_resolved"]["name"]]

    def rep_of(label: str) -> str:
        # Audit labels are rule-class names or "Unclassifiable".
        return to_rep.get(label, rep["not_resolved"]["name"])

    # --- per-class precision at the rule-class level -------------------------
    per_class = {}
    for c in sorted(Nc, key=lambda k: -Nc[k]):
        rows = strata[c]
        k = sum(r["audit_label"] == c for r in rows)
        lo, hi = wilson(k, len(rows))
        per_class[c] = {
            "population": Nc[c],
            "audited": len(rows),
            "agree": k,
            "precision": k / len(rows),
            "wilson_low": lo,
            "wilson_high": hi,
            "passes": c != "Unclassified"
            and k / len(rows) >= MIN_PRECISION
            and lo >= MIN_WILSON_LOW,
            "audit_labels": dict(Counter(r["audit_label"] for r in rows).most_common()),
        }

    # --- precision at the reporting-class level -----------------------------
    per_rep = {}
    for R in rep["reporting"]:
        rows = [r for m in R["members"] for r in strata[m]]
        k = sum(rep_of(r["audit_label"]) == R["name"] for r in rows)
        # population-weighted precision across member strata
        w = sum(Nc[m] for m in R["members"])
        wp = (
            sum(
                Nc[m]
                * sum(rep_of(r["audit_label"]) == R["name"] for r in strata[m])
                / len(strata[m])
                for m in R["members"]
            )
            / w
        )
        lo, hi = wilson(k, len(rows))
        per_rep[R["name"]] = {
            "members": R["members"],
            "audited": len(rows),
            "agree": k,
            "precision_sample": k / len(rows),
            "precision_weighted": wp,
            "wilson_low": lo,
            "wilson_high": hi,
        }

    # --- estimators -----------------------------------------------------------
    def estimate(sample: dict[str, list[dict]]) -> dict:
        agree = sum(
            Nc[c] / N * sum(r["audit_label"] == c for r in rows) / len(rows)
            for c, rows in sample.items()
        )
        agree_rep = sum(
            Nc[c]
            / N
            * sum(rep_of(r["audit_label"]) == rep_of(c) for r in rows)
            / len(rows)
            for c, rows in sample.items()
        )
        adj = {name: 0.0 for name in rep_names}
        arith = 0.0
        for c, rows in sample.items():
            for r in rows:
                adj[rep_of(r["audit_label"])] += Nc[c] / N / len(rows)
                arith += Nc[c] / N / len(rows) * (r["arithmetic_datapath"] == "yes")
        return {"agree": agree, "agree_rep": agree_rep, "adj": adj, "arith": arith}

    point = estimate(strata)
    rng = random.Random(SEED)
    boots = []
    for _ in range(B):
        s = {}
        for c, rows in strata.items():
            s[c] = (
                rows
                if len(rows) == Nc[c]
                else [rows[rng.randrange(len(rows))] for _ in rows]
            )
        boots.append(estimate(s))

    def ci(f) -> list[float]:
        xs = [f(b) for b in boots]
        return [pct(xs, 0.025), pct(xs, 0.975)]

    rule_share = Counter(rep_of(r["subsystem"]) for r in pop)
    shares = {}
    for name in rep_names:
        shares[name] = {
            "rule_count": rule_share[name],
            "rule_share": rule_share[name] / N,
            "adjusted_share": point["adj"][name],
            "adjusted_ci95": ci(lambda b, n=name: b["adj"][n]),
        }

    # --- unique-title robustness ------------------------------------------------
    def key(t: str) -> str:
        return re.sub(r"[^a-z0-9]", "", t.lower())

    uniq = {}
    for r in pop:
        uniq.setdefault(key(r["title"]), r)
    uniq_share = Counter(rep_of(r["subsystem"]) for r in uniq.values())

    fam = Counter(r["family"] for r in pop)
    out = {
        "population": N,
        "families": len(fam),
        "documents": len(fam),
        "intel_errata": sum(r["vendor"] == "Intel" for r in pop),
        "amd_errata": sum(r["vendor"] == "AMD" for r in pop),
        "unclassified": Nc.get("Unclassified", 0),
        "matched_on_title": sum(r["matched_on"] == "title" for r in pop),
        "matched_on_description": sum(r["matched_on"] == "description" for r in pop),
        "audited": len(aud),
        "audited_agree_raw": sum(r["audit_label"] == r["rule_label"] for r in aud),
        "agreement_weighted": point["agree"],
        "agreement_weighted_ci95": ci(lambda b: b["agree"]),
        "agreement_reporting_weighted": point["agree_rep"],
        "agreement_reporting_weighted_ci95": ci(lambda b: b["agree_rep"]),
        "arithmetic_datapath_audited": sum(
            r["arithmetic_datapath"] == "yes" for r in aud
        ),
        "arithmetic_datapath_share": point["arith"],
        "arithmetic_datapath_share_ci95": ci(lambda b: b["arith"]),
        "criterion": {"min_precision": MIN_PRECISION, "min_wilson_low": MIN_WILSON_LOW},
        "failed_classes": [
            c for c, d in per_class.items() if c != "Unclassified" and not d["passes"]
        ],
        "dropped_classes": [
            m for m in rep["not_resolved"]["members"] if m != "Unclassified"
        ],
        "merged_classes": [
            c
            for c, d in per_class.items()
            if c != "Unclassified"
            and not d["passes"]
            and c not in rep["not_resolved"]["members"]
        ],
        "rule_classes": len([c for c in per_class if c != "Unclassified"]),
        "status_counts": dict(Counter(r["status"] for r in pop)),
        "per_class": per_class,
        "per_reporting_class": per_rep,
        "shares": shares,
        "unique_titles": len(uniq),
        "unique_title_shares": {n: uniq_share[n] / len(uniq) for n in rep_names},
        "bootstrap": {"replicates": B, "seed": SEED},
    }
    (HERE / "audit_metrics.json").write_text(json.dumps(out, indent=2) + "\n")

    print(
        f"population {N}; audited {len(aud)}; raw agreement {out['audited_agree_raw']}/{len(aud)}"
    )
    a, (l, h) = point["agree"], out["agreement_weighted_ci95"]
    print(f"weighted agreement, 12 classes: {a:.3f} [{l:.3f}, {h:.3f}]")
    a, (l, h) = point["agree_rep"], out["agreement_reporting_weighted_ci95"]
    print(f"weighted agreement, reporting classes: {a:.3f} [{l:.3f}, {h:.3f}]")
    print("\nper rule class: precision (Wilson 95%)")
    for c, d in per_class.items():
        flag = "pass" if d["passes"] else "FAIL"
        print(
            f"  {d['agree']:2d}/{d['audited']:2d} {d['precision']:.2f} [{d['wilson_low']:.2f}, {d['wilson_high']:.2f}] {flag}  {c}"
        )
    print("\nper reporting class: sample precision, population-weighted precision")
    for c, d in per_rep.items():
        print(
            f"  {d['agree']:2d}/{d['audited']:2d} {d['precision_sample']:.2f} weighted {d['precision_weighted']:.2f} [{d['wilson_low']:.2f}, {d['wilson_high']:.2f}]  {c}"
        )
    print("\nshares: rule / audit-adjusted [95% CI] / unique titles")
    for n, d in shares.items():
        l, h = d["adjusted_ci95"]
        print(
            f"  {d['rule_share']:.3f} / {d['adjusted_share']:.3f} [{l:.3f}, {h:.3f}] / {out['unique_title_shares'][n]:.3f}  {n}"
        )
    l, h = out["arithmetic_datapath_share_ci95"]
    print(f"\narithmetic datapath share: {point['arith']:.3f} [{l:.3f}, {h:.3f}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
