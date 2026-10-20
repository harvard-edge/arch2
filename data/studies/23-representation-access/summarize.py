#!/usr/bin/env python3
"""Summarize exact matched pair accessibility and retain weighting sensitivity."""
from __future__ import annotations
import csv, json, statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUDGETS = [1, 4, 16, 64, 256, 1024, 4096, 16384, 65536, 262144]
TREE_BUDGETS = [1, 2, 4, 8, 16, 32, 64, 128]


def rows(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_csv(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(data)


def cov(values, b):
    return sum(v <= b for v in values) / len(values) if values else 0


def main():
    all_pairs = rows(HERE / "derived/pairs.csv")
    files = rows(HERE / "derived/file_summary.csv")
    matched = [r for r in all_pairs if r["tree_path_recoverable"] == "1"]
    by_repo = defaultdict(list)
    by_file = defaultdict(list)
    for r in matched:
        by_repo[r["corpus"]].append(r)
        by_file[(r["corpus"], r["source_path"])].append(r)
    long_pairs = [r for r in matched if int(r["minimum_interval_tokens"]) > 4096]
    by_file_long = defaultdict(list)
    for r in long_pairs:
        by_file_long[(r["corpus"], r["source_path"])].append(r)
    budget_rows = []
    for repo, pairs in by_repo.items():
        for b in BUDGETS:
            budget_rows.append(
                {
                    "measure": "source_interval_tokens",
                    "aggregation": "pair_weighted_by_repository",
                    "corpus": repo,
                    "budget": b,
                    "coverage_fraction": f'{cov([int(x["minimum_interval_tokens"]) for x in pairs],b):.8f}',
                    "pairs_denominator": len(pairs),
                    "files_denominator": len(set(x["source_path"] for x in pairs)),
                }
            )
    for b in BUDGETS:
        pv = cov([int(x["minimum_interval_tokens"]) for x in matched], b)
        file_values = [
            cov([int(x["minimum_interval_tokens"]) for x in p], b)
            for p in by_file.values()
        ]
        budget_rows.extend(
            [
                {
                    "measure": "source_interval_tokens",
                    "aggregation": "pair_weighted_all_repositories",
                    "corpus": "All",
                    "budget": b,
                    "coverage_fraction": f"{pv:.8f}",
                    "pairs_denominator": len(matched),
                    "files_denominator": len(by_file),
                },
                {
                    "measure": "source_interval_tokens",
                    "aggregation": "equal_file_weighted_all_repositories",
                    "corpus": "All",
                    "budget": b,
                    "coverage_fraction": f"{statistics.fmean(file_values):.8f}",
                    "pairs_denominator": len(matched),
                    "files_denominator": len(by_file),
                },
            ]
        )
    for repo, pairs in by_repo.items():
        for b in TREE_BUDGETS:
            budget_rows.append(
                {
                    "measure": "syntax_path_edges",
                    "aggregation": "pair_weighted_by_repository",
                    "corpus": repo,
                    "budget": b,
                    "coverage_fraction": f'{cov([int(x["tree_path_edges"]) for x in pairs],b):.8f}',
                    "pairs_denominator": len(pairs),
                    "files_denominator": len(set(x["source_path"] for x in pairs)),
                }
            )
    save_csv(HERE / "derived/budget_coverage.csv", budget_rows)
    sums = {r["corpus"]: r for r in files}
    total_refs = sum(int(x["name_refs"]) for x in files)
    bound_refs = sum(int(x["name_refs_bound"]) for x in files)
    tree_n = len(matched)
    result = {
        "claim_class": "evidence-backed descriptive source analysis",
        "measurement": "minimum contiguous token interval containing the declaration and use; minimum_interval_tokens = abs(token-index difference) + 1",
        "pair_dataset_rows": len(all_pairs),
        "bound_in_file_pairs": len(all_pairs),
        "exact_token_tree_matched_pairs": tree_n,
        "token_pairs_without_recoverable_tree_path": len(all_pairs) - tree_n,
        "files_in_manifest": len(files),
        "files_with_bound_pairs": sum(int(x["status"] == "measured") for x in files),
        "excluded_files": [
            {k: r[k] for k in ("corpus", "source_path", "exclusion_reason")}
            for r in files
            if r["status"] == "excluded"
        ],
        "name_reference_nodes": total_refs,
        "bound_name_reference_nodes": bound_refs,
        "unbound_name_reference_nodes": total_refs - bound_refs,
        "binding_fraction": bound_refs / total_refs if total_refs else None,
        "matched_pair_counts_by_repository": {
            repo: len(p) for repo, p in by_repo.items()
        },
        "long_span_threshold": "> 4096 minimum interval tokens",
        "long_span_pairs": len(long_pairs),
        "long_span_pair_fraction": len(long_pairs) / tree_n if tree_n else None,
        "pairs_by_repository": {repo: len(p) for repo, p in by_repo.items()},
        "long_span_pairs_by_repository": {
            repo: sum(int(x["minimum_interval_tokens"]) > 4096 for x in ps)
            for repo, ps in by_repo.items()
        },
        "top_files_by_matched_pair_count": [
            {
                "corpus": repo,
                "source_path": path,
                "matched_pairs": len(ps),
                "share_of_matched_pairs": len(ps) / tree_n,
            }
            for (repo, path), ps in sorted(
                by_file.items(), key=lambda kv: (-len(kv[1]), kv[0])
            )[:10]
        ],
        "top_files_by_long_span_pair_count": [
            {
                "corpus": repo,
                "source_path": path,
                "long_span_pairs": len(ps),
                "share_of_long_span_pairs": len(ps) / len(long_pairs),
            }
            for (repo, path), ps in sorted(
                by_file_long.items(), key=lambda kv: (-len(kv[1]), kv[0])
            )[:10]
        ],
        "selected_budget_sensitivity": [],
        "without_largest_file_sensitivity": [],
        "limits": [
            "The interval is a minimum source span and ignores surrounding prompt material.",
            "This measures source layout and parser binding only; it does not measure model attention, retrieval, accuracy, or task success.",
            "The inherited file list is a convenience corpus with an undocumented original selection rule; benchmark and production files are not population samples.",
            "The parser records 1,170 same-file signal-name syntax references without a corresponding bound NameValue expression. The diagnostic confirms that the source visitor includes every conditional-generate branch under the selected top-level configuration; the unbound count is a parser coverage measure with no causal attribution.",
            "The tree-distance comparison includes exactly the recoverable subset of token pairs; 170 of 40,995 pairs have no recoverable tree path.",
        ],
    }
    for b in [64, 256, 1024, 4096, 16384]:
        p = cov([int(x["minimum_interval_tokens"]) for x in matched], b)
        f = statistics.fmean(
            [
                cov([int(x["minimum_interval_tokens"]) for x in ps], b)
                for ps in by_file.values()
            ]
        )
        result["selected_budget_sensitivity"].append(
            {
                "budget_tokens": b,
                "pair_weighted_coverage": p,
                "equal_file_weighted_coverage": f,
                "difference_percentage_points": (p - f) * 100,
            }
        )
        largest = ("BaseJump STL", "bsg_dataflow/bsg_scatter_gather.sv")
        remaining = [r for r in matched if (r["corpus"], r["source_path"]) != largest]
        result["without_largest_file_sensitivity"].append(
            {
                "budget_tokens": b,
                "pair_weighted_coverage": cov(
                    [int(x["minimum_interval_tokens"]) for x in remaining], b
                ),
                "pairs_denominator": len(remaining),
            }
        )
    (HERE / "derived/summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "bound_in_file_pairs",
                    "exact_token_tree_matched_pairs",
                    "token_pairs_without_recoverable_tree_path",
                    "binding_fraction",
                    "selected_budget_sensitivity",
                    "excluded_files",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
