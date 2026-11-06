#!/usr/bin/env python3
"""Spec 05: RTL syntax gap. Run from this folder: python3 -I compute.py

Reads only the per-module CSV, plus include_reparse.json if the reparse stage
(reparse.py) has produced it. Writes result.json.
"""
import csv
import json
import os
from collections import Counter

CSV_PATH = "inputs/data/studies/02-ast-complexity-cliff/hardware_ast_complexity_measured.csv"
REPARSE_PATH = "include_reparse.json"
BENCH = "AI benchmark reference RTL"
PROD = "Production-oriented open RTL"
NEWLINE = "DiagCode(NewlineEOF)"


def median(values):
    s = sorted(values)
    n = len(s)
    if n == 0:
        raise ValueError("median of empty set")
    mid = n // 2
    return float(s[mid]) if n % 2 else (s[mid - 1] + s[mid]) / 2


def codes(row):
    return [c for c in row["syntax_diagnostic_codes"].split(";") if c != ""]


def substantive(row):
    return any(c != NEWLINE for c in codes(row))


def nodes(rows):
    return [int(r["concrete_syntax_nodes"]) for r in rows]


def pct(part, whole):
    return 100.0 * part / whole


def ratio(rows):
    b = [r for r in rows if r["corpus_category"] == BENCH]
    p = [r for r in rows if r["corpus_category"] == PROD]
    return median(nodes(p)) / median(nodes(b)), median(nodes(b)), median(nodes(p)), len(b), len(p)


def main():
    with open(CSV_PATH, newline="") as f:
        rows = list(csv.DictReader(f))
    categories = Counter(r["corpus_category"] for r in rows)
    if set(categories) != {BENCH, PROD}:
        raise SystemExit(f"unexpected categories: {categories}")

    bench = [r for r in rows if r["corpus_category"] == BENCH]
    prod = [r for r in rows if r["corpus_category"] == PROD]
    repos = sorted({r["dataset_name"] for r in rows})
    by_repo = {d: [r for r in rows if r["dataset_name"] == d] for d in repos}
    group_of = {d: by_repo[d][0]["corpus_category"] for d in repos}

    pooled, b_med, p_med, _, _ = ratio(rows)
    repo_medians = {d: median(nodes(by_repo[d])) for d in repos}
    gm_b = median([repo_medians[d] for d in repos if group_of[d] == BENCH])
    gm_p = median([repo_medians[d] for d in repos if group_of[d] == PROD])

    veer = by_repo["VeeR EH1"]
    ranked = Counter(r["source_path"] for r in veer).most_common()
    if len(ranked) > 2 and ranked[1][1] == ranked[2][1]:
        raise SystemExit(f"tie at rank 2 of VeeR paths: {ranked[:4]}")
    lib_paths = [p for p, _ in ranked[:2]]
    veer_lib = [r for r in veer if r["source_path"] in lib_paths]
    veer_rest = [r for r in veer if r["source_path"] not in lib_paths]

    kept = [r for r in rows if not substantive(r)]
    kept_valid = [r for r in kept if r["syntax_tree_valid"] == "1"]
    valid_only = [r for r in rows if r["syntax_tree_valid"] == "1"]
    prod_sub = [r for r in prod if substantive(r)]
    prod_keep = [r for r in prod if not substantive(r)]
    bp_all = by_repo["BlackParrot"]
    bp_dropped = sum(1 for r in bp_all if substantive(r))

    depth = [int(r["internal_hierarchy_depth"]) for r in prod]

    result = {
        "n_modules": len(rows),
        "n_benchmark": len(bench),
        "n_production": len(prod),
        "benchmark_median": b_med,
        "production_median": p_med,
        "pooled_ratio": pooled,
        "opentitan_share_pct": pct(len(by_repo["OpenTitan"]), len(prod)),
        "repo_medians": repo_medians,
        "group_median_of_repo_medians": {"benchmark": gm_b, "production": gm_p},
        "ratio_of_medians": gm_p / gm_b,
        "veer": {
            "library_paths": lib_paths,
            "share_pct": pct(len(veer_lib), len(veer)),
            "median_without": median(nodes(veer_rest)),
        },
        "production_any_diagnostic_pct": pct(sum(1 for r in prod if codes(r)), len(prod)),
        "production_substantive_diagnostic_pct": pct(len(prod_sub), len(prod)),
        "filtered_ratio": ratio(kept)[0],
        "filtered_ratio_valid_tree_only": ratio(kept_valid)[0],
        "blackparrot_dropped": bp_dropped,
        "blackparrot_all_dropped": bp_dropped == len(bp_all),
        "removed_median": median(nodes(prod_sub)),
        "kept_median": median(nodes(prod_keep)),
        "include_path_ratio": None,
        "include_path_note": "",
        "reference_share_pct": {
            d: pct(sum(1 for r in by_repo[d]
                       if int(r["resolved_internal_submodule_instantiations"]) > 0),
                   len(by_repo[d])) for d in repos},
        "instantiating_share_pct": {
            d: pct(sum(1 for r in by_repo[d] if int(r["hierarchy_instantiation_count"]) > 0),
                   len(by_repo[d])) for d in repos},
        "max_depth": max(depth),
        "median_depth": median(depth),
    }

    # Readings the spec's fixed keys do not separate. Names are defined in notes.md.
    result["additional_readings"] = {
        "filtered_ratio_requires_substantive_clean_and_valid_tree": result["filtered_ratio_valid_tree_only"],
        "filtered_ratio_valid_tree_alone_diagnostics_ignored": ratio(valid_only)[0],
        "filtered_ratio_production_only_benchmark_unfiltered":
            median(nodes(prod_keep)) / b_med,
        "filter_counts": {
            "kept_benchmark": sum(1 for r in kept if r["corpus_category"] == BENCH),
            "kept_production": sum(1 for r in kept if r["corpus_category"] == PROD),
            "kept_valid_benchmark": sum(1 for r in kept_valid if r["corpus_category"] == BENCH),
            "kept_valid_production": sum(1 for r in kept_valid if r["corpus_category"] == PROD),
            "valid_only_benchmark": sum(1 for r in valid_only if r["corpus_category"] == BENCH),
            "valid_only_production": sum(1 for r in valid_only if r["corpus_category"] == PROD),
            "invalid_tree_total": len(rows) - len(valid_only),
            "invalid_tree_that_pass_substantive_filter": len(kept) - len(kept_valid),
        },
        "veer_path_counts_top5": ranked[:5],
        "ambiguous_only_share_pct_note": "reference_share_pct uses resolved > 0; instantiating_share_pct uses hierarchy_instantiation_count > 0",
        "production_only_reference_range_resolved": [
            min(result["reference_share_pct"][d] for d in repos if group_of[d] == PROD),
            max(result["reference_share_pct"][d] for d in repos if group_of[d] == PROD)],
        "production_only_reference_range_instantiating": [
            min(result["instantiating_share_pct"][d] for d in repos if group_of[d] == PROD),
            max(result["instantiating_share_pct"][d] for d in repos if group_of[d] == PROD)],
        "rows_dropped": 0,
    }

    if os.path.exists(REPARSE_PATH):
        with open(REPARSE_PATH) as f:
            rep = json.load(f)
        result["include_path_readings"] = rep["readings"]
        result["include_path_ratio"] = rep["primary_ratio"]
        result["include_path_note"] = rep["note"]
    else:
        result["include_path_note"] = "reparse.py has not produced include_reparse.json"

    with open("result.json", "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
