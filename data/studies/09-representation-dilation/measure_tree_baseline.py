#!/usr/bin/env python3
"""Compare tree paths of declaration-use pairs with different-signal pairs.

Study 09 reports that the syntax-tree path between a declaration and its use
stays near ten edges at every file length. A path in a tree is bounded by the
tree's depth, so a short path could be a property of shallow parse trees and
not of the declaration-use relation. This script compares the two.

For every pair with a recoverable path, the baseline keeps the declaration and
replaces the use with a use of a different declaration in the same module. Up
to SAMPLES_PER_PAIR such uses are drawn without replacement, seeded by file
path. A use that any measured pair binds to the same declaration is never a
candidate. Files with no such candidate stay in the output with a reason.

A pair enters the comparison only if its declaration and its use lie in one
module or interface. A subroutine in a package has no enclosing module, so its
pairs have no same-module baseline and cannot sit below a module. They are
counted per file in pairs_outside_module and enter neither the baseline, nor
the scope strata, nor the lowest-common-ancestor shares. The retained
measurement CSV and panel (b) still include them.

"Unrelated" in the field names of this script and its outputs means only that
the use binds to a different declaration. It does not mean the two signals have
no dependency. share_candidates_sharing_statement reports how many candidates
belong to signals named in one assign, always block, or instance together with
the declared signal, which is a coarse test: a whole always block counts as one
statement.

Post-hoc reading. The two thresholds below were set on 2026-11-02 after the
outcome was known. Before this script existed, the author had read an audit
estimate of the same comparison: median ratio 1.00, 5th to 95th percentile 0.94
to 1.10. The version that fixed them was saved at 14:30:24 EET and the first
logged run started at 14:30:43 EET. RATIO_THRESHOLD equals that estimate's 95th
percentile. No record states why SUPERIORITY_THRESHOLD is 0.60. No commit pins
either value, so the times above rest on file modification times and the run
log. The rule therefore describes this corpus and does not test a prediction.

    The tree path separates related from unrelated pairs only if the bootstrap
    95 percent interval of the median per-file ratio (unrelated mean over
    related mean) lies wholly above 1.10 and the median per-file probability
    that an unrelated path is longer than a related one, counting each tie as
    half, is at least 0.60. Otherwise: tree-path length does not separate
    declaration-use pairs from unrelated same-module pairs in this corpus.

Because the rule counts ties as half, prob_unrelated_longer_ties_half is 0.5
for any file whose draws split evenly around the ties. The share_unrelated_*
fields report strictly longer, tied, and strictly shorter draws separately.

Results are also split by where a pair's lowest common ancestor sits. Pairs that
meet below the module are selected by the related path, so part of any gap in
that stratum can come from the selection. The split applies no threshold.

The constructed fixtures run with every measurement. Two record that the
comparison can report a separation when scoping produces one. The third holds
functions in a package and no module, and the run stops if it gets a baseline.

Run through data/run_study.py. README.md gives the command.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import random
import statistics
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pyslang as ps
from pyslang import parsing, syntax

import measure_representation_dilation as m

STUDY_DIR = Path(__file__).resolve().parent
DEFAULT_SOURCE_ROOT = STUDY_DIR.parent / "23-representation-access" / ".cache" / "repos"
OUTPUT_CSV = STUDY_DIR / "tree_baseline_by_file.csv"
OUTPUT_JSON = STUDY_DIR / "tree_baseline_summary.json"

SAMPLES_PER_PAIR = 20
SEED = 20261102
BOOTSTRAP_REPS = 10_000
RATIO_THRESHOLD = 1.10
SUPERIORITY_THRESHOLD = 0.60
MODULE_KIND = "SyntaxKind.ModuleDeclaration"
STATEMENT_KINDS = (
    "ContinuousAssign",
    "AlwaysBlock",
    "AlwaysCombBlock",
    "AlwaysFFBlock",
    "AlwaysLatchBlock",
    "InitialBlock",
    "FinalBlock",
    "HierarchyInstantiation",
)
MIN_NESTED_PAIRS = 10


def module_of(chain: list):
    """Innermost module or interface declaration enclosing a node, or None."""
    for key in chain:
        if key[0] in (MODULE_KIND, "SyntaxKind.InterfaceDeclaration"):
            return key
    return None


def in_module(p: dict) -> bool:
    """True when a pair's declaration and use lie in one module or interface."""
    module = module_of(p["use_chain"])
    return module is not None and module == module_of(p["decl_chain"])


def statement_of(chain: list):
    """Innermost statement-level item enclosing a node, or None."""
    for key in chain:
        if key[0].replace("SyntaxKind.", "") in STATEMENT_KINDS:
            return key
    return None


def empty_scope() -> dict:
    return {
        "pairs": 0,
        "related_sum": 0.0,
        "unrelated_sum": 0.0,
        "longer": 0,
        "tied": 0,
        "shorter": 0,
    }


def common_ancestor(a_chain: list, b_chain: list):
    b_keys = set(b_chain)
    for key in a_chain:
        if key in b_keys:
            return key
    return None


def compare_file(all_pairs: list[dict], rng: random.Random) -> dict:
    """Related and unrelated statistics for a file's pairs inside one module."""
    pairs = [p for p in all_pairs if in_module(p)]
    decls_of_use: dict = defaultdict(set)
    use_by_key: dict = {}
    for p in pairs:
        decls_of_use[p["use_key"]].add(p["decl_key"])
        use_by_key.setdefault(p["use_key"], p)
    uses_by_module: dict = defaultdict(list)
    for key, p in use_by_key.items():
        uses_by_module[module_of(p["use_chain"])].append(key)

    decls_in_statement: dict = defaultdict(set)
    for p in pairs:
        statement = statement_of(p["use_chain"])
        if statement is not None:
            decls_in_statement[statement].add(p["decl_key"])
    statement_neighbors: dict = defaultdict(set)
    for decls in decls_in_statement.values():
        for decl in decls:
            statement_neighbors[decl] |= decls

    related, unrelated, tok_related, tok_unrelated = [], [], [], []
    shared_shares = []
    shared_cache: dict = {}
    scopes: dict = defaultdict(empty_scope)
    longer = tied = shorter = draws = 0
    module_lca = 0
    decl_depth, use_depth = [], []
    for p in pairs:
        module = module_of(p["use_chain"])
        lca = common_ancestor(p["decl_chain"], p["use_chain"])
        module_lca += lca == module
        anchor = p["decl_chain"].index(lca)
        decl_depth.append(anchor)
        use_depth.append(p["use_chain"].index(lca))
        candidates = [
            k
            for k in uses_by_module[module]
            if p["decl_key"] not in decls_of_use[k]
        ]
        if not candidates:
            continue
        cache_key = (module, p["decl_key"])
        if cache_key not in shared_cache:
            neighbors = statement_neighbors[p["decl_key"]]
            shared_cache[cache_key] = sum(
                bool(decls_of_use[k] & neighbors) for k in candidates
            ) / len(candidates)
        shared_shares.append(shared_cache[cache_key])
        scope = scopes["module" if lca == module else lca[0].replace("SyntaxKind.", "")]
        if len(candidates) > SAMPLES_PER_PAIR:
            candidates = rng.sample(candidates, SAMPLES_PER_PAIR)
        paths, tok_paths = [], []
        for key in candidates:
            other = use_by_key[key]
            d = m.tree_distance(p["decl_chain"], other["use_chain"])
            paths.append(d)
            tok_paths.append(abs(other["use_token"] - p["decl_token"]))
            longer += d > p["tree_distance"]
            tied += d == p["tree_distance"]
            shorter += d < p["tree_distance"]
            scope["longer"] += d > p["tree_distance"]
            scope["tied"] += d == p["tree_distance"]
            scope["shorter"] += d < p["tree_distance"]
            draws += 1
        related.append(p["tree_distance"])
        tok_related.append(abs(p["use_token"] - p["decl_token"]))
        unrelated.append(statistics.fmean(paths))
        tok_unrelated.append(statistics.fmean(tok_paths))
        scope["pairs"] += 1
        scope["related_sum"] += p["tree_distance"]
        scope["unrelated_sum"] += unrelated[-1]
    nested = merge_scopes(v for k, v in scopes.items() if k != "module")
    return {
        "signals": len({p["decl_key"] for p in pairs}),
        "pairs_outside_module": len(all_pairs) - len(pairs),
        "pairs_with_baseline": len(related),
        "unrelated_draws": draws,
        "related_tree": statistics.fmean(related) if related else None,
        "unrelated_tree": statistics.fmean(unrelated) if related else None,
        "prob_unrelated_longer_ties_half": (longer + 0.5 * tied) / draws if draws else None,
        "draws_longer": longer,
        "draws_tied": tied,
        "draws_shorter": shorter,
        "share_unrelated_longer": longer / draws if draws else None,
        "share_unrelated_tied": tied / draws if draws else None,
        "share_unrelated_shorter": shorter / draws if draws else None,
        "share_candidates_sharing_statement": (
            statistics.fmean(shared_shares) if shared_shares else None
        ),
        "nested_pairs_with_baseline": nested["pairs"],
        "nested_ratio": (
            nested["unrelated_sum"] / nested["related_sum"] if nested["pairs"] else None
        ),
        "scopes": scopes,
        "related_tokens": statistics.fmean(tok_related) if related else None,
        "unrelated_tokens": statistics.fmean(tok_unrelated) if related else None,
        "share_lca_is_module": module_lca / len(pairs) if pairs else None,
        "mean_decl_edges_to_lca": statistics.fmean(decl_depth) if pairs else None,
        "mean_use_edges_to_lca": statistics.fmean(use_depth) if pairs else None,
    }


def merge_scopes(scopes) -> dict:
    total = empty_scope()
    for scope in scopes:
        for key in total:
            total[key] += scope[key]
    return total


def describe_scope(scope: dict) -> dict:
    draws = scope["longer"] + scope["tied"] + scope["shorter"]
    related = scope["related_sum"] / scope["pairs"]
    unrelated = scope["unrelated_sum"] / scope["pairs"]
    return {
        "pairs": scope["pairs"],
        "draws": draws,
        "mean_related": round(related, 4),
        "mean_unrelated": round(unrelated, 4),
        "ratio": round(unrelated / related, 4),
        "share_longer": round(scope["longer"] / draws, 4),
        "share_tied": round(scope["tied"] / draws, 4),
        "share_shorter": round(scope["shorter"] / draws, 4),
    }


def median_ci(values: list[float]) -> dict:
    a = np.array(values)
    rng = np.random.default_rng(SEED)
    boots = np.array(
        [np.median(a[rng.integers(0, len(a), len(a))]) for _ in range(BOOTSTRAP_REPS)]
    )
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {
        "files": len(a),
        "median_ratio": round(float(np.median(a)), 4),
        "median_ratio_ci95": [round(float(lo), 4), round(float(hi), 4)],
    }


def fixture(text: str) -> dict:
    """Run the comparison on a constructed file. Not corpus data."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fixture.sv"
        path.write_text(text, encoding="utf-8")
        pairs: list[dict] = []
        sm = ps.SourceManager()
        bag = ps.Bag([parsing.PreprocessorOptions()])
        m.measure_file(
            path, m.CORPUS_BY_NAME["PicoRV32"], path.parent, [], sm, bag, pairs.append
        )
    r = compare_file(pairs, random.Random(SEED))
    return {
        "construction": "constructed fixture, not corpus data",
        "pairs": len(pairs),
        "pairs_with_baseline": r["pairs_with_baseline"],
        "ratio": (
            round(r["unrelated_tree"] / r["related_tree"], 4)
            if r["pairs_with_baseline"]
            else None
        ),
        "prob_unrelated_longer_ties_half": (
            round(r["prob_unrelated_longer_ties_half"], 4)
            if r["pairs_with_baseline"]
            else None
        ),
    }


FIXTURE_FLAT = """module flat(input logic a, input logic b, input logic c,
                  output logic x, output logic y, output logic z);
  assign x = a;
  assign y = b;
  assign z = c;
endmodule
"""
# Each signal is declared and used only inside its own named generate block,
# with the blocks nested so that crossing between them climbs the tree.
FIXTURE_SCOPED = """module scoped;
  if (1) begin : g0 if (1) begin : h0 if (1) begin : i0
    logic a; logic a2; assign a = 1'b0; assign a2 = a;
  end end end
  if (1) begin : g1 if (1) begin : h1 if (1) begin : i1
    logic b; logic b2; assign b = 1'b0; assign b2 = b;
  end end end
endmodule
"""
# Two functions in a package and no module. No pair has a same-module baseline.
FIXTURE_PACKAGE = """package p;
  function automatic logic f(input logic a);
    return a;
  endfunction
  function automatic logic g(input logic b);
    return b;
  endfunction
endpackage
"""


def fit(rows: list[dict], key: str) -> dict:
    return m.loglog_fit([{**r, key: r[key]} for r in rows], key)


def describe(rows: list[dict]) -> dict:
    ratios = np.array([float(r["ratio"]) for r in rows])
    probs = np.array([float(r["prob_unrelated_longer_ties_half"]) for r in rows])
    draw_totals = {
        k: sum(int(r[f"draws_{k}"]) for r in rows) for k in ("longer", "tied", "shorter")
    }
    all_draws = sum(draw_totals.values())
    token_ratios = np.array(
        [float(r["unrelated_tokens"]) / float(r["related_tokens"]) for r in rows]
    )
    rng = np.random.default_rng(SEED)
    n = len(rows)
    boots = np.empty(BOOTSTRAP_REPS)
    for b in range(BOOTSTRAP_REPS):
        boots[b] = np.median(ratios[rng.integers(0, n, n)])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    weights = np.array([int(r["pairs_with_baseline"]) for r in rows], dtype=float)
    return {
        "files": n,
        "pairs": int(weights.sum()),
        "median_file_mean_related": round(
            float(np.median([float(r["related_tree"]) for r in rows])), 4
        ),
        "median_file_mean_unrelated": round(
            float(np.median([float(r["unrelated_tree"]) for r in rows])), 4
        ),
        "median_ratio": round(float(np.median(ratios)), 4),
        "median_ratio_ci95": [round(float(lo), 4), round(float(hi), 4)],
        "ratio_p05_p95": [
            round(float(v), 4) for v in np.percentile(ratios, [5, 95])
        ],
        "share_files_unrelated_at_least_related": round(
            float(np.mean([float(r["unrelated_tree"]) >= float(r["related_tree"]) for r in rows])), 4
        ),
        "median_prob_unrelated_longer_ties_half": round(float(np.median(probs)), 4),
        "median_file_share_longer": round(
            float(np.median([float(r["share_unrelated_longer"]) for r in rows])), 4
        ),
        "median_file_share_tied": round(
            float(np.median([float(r["share_unrelated_tied"]) for r in rows])), 4
        ),
        "median_file_share_shorter": round(
            float(np.median([float(r["share_unrelated_shorter"]) for r in rows])), 4
        ),
        "pooled_draws": all_draws,
        "pooled_share_longer": round(draw_totals["longer"] / all_draws, 4),
        "pooled_share_tied": round(draw_totals["tied"] / all_draws, 4),
        "pooled_share_shorter": round(draw_totals["shorter"] / all_draws, 4),
        "median_file_share_candidates_sharing_statement": round(
            float(
                np.median([float(r["share_candidates_sharing_statement"]) for r in rows])
            ),
            4,
        ),
        "pair_weighted_related": round(
            float(
                np.average([float(r["related_tree"]) for r in rows], weights=weights)
            ),
            4,
        ),
        "pair_weighted_unrelated": round(
            float(
                np.average([float(r["unrelated_tree"]) for r in rows], weights=weights)
            ),
            4,
        ),
        "tree_slope_related": fit(rows, "related_tree"),
        "tree_slope_unrelated": fit(rows, "unrelated_tree"),
        "median_token_ratio": round(float(np.median(token_ratios)), 4),
        "token_slope_related": fit(rows, "related_tokens"),
        "token_slope_unrelated": fit(rows, "unrelated_tokens"),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    ap.add_argument("--csv", type=Path, default=m.DEFAULT_OUTPUT, help="retained study CSV")
    args = ap.parse_args()

    with args.csv.open(encoding="utf-8") as fh:
        retained = {
            (r["corpus"], r["source_path"]): r
            for r in csv.DictReader(l for l in fh if not l.startswith("#"))
        }
    manifest = m.read_manifest()
    rows = []
    lca_kinds: Counter = Counter()
    scopes: dict = defaultdict(empty_scope)
    for corpus in m.CORPORA:
        root = args.source_root / corpus.checkout
        sm = ps.SourceManager()
        pp = parsing.PreprocessorOptions()
        pp.additionalIncludePaths = [str(root / d) for d in corpus.include_dirs]
        pp.predefines = list(corpus.predefines)
        bag = ps.Bag([pp])
        support = []
        if not corpus.standalone:
            seen = set()
            for pattern in corpus.support_globs:
                for f in sorted(glob.glob(str(root / pattern))):
                    key = str(Path(f).resolve())
                    if key not in seen:
                        seen.add(key)
                        support.append((key, syntax.SyntaxTree.fromFile(f, sm, bag)))
        for row in (r for r in manifest if r["corpus"] == corpus.name):
            path = root / row["source_path"]
            if m.sha256(path) != row["source_sha256"]:
                raise SystemExit(f"hash mismatch: {path}")
            pairs: list[dict] = []
            r = m.measure_file(path, corpus, root, support, sm, bag, pairs.append)
            kept = retained[(corpus.name, row["source_path"])]
            # The sink must see exactly the pairs behind the retained CSV.
            if len(pairs) != int(kept["tree_pairs"]) or int(r.tokens) != int(kept["tokens"]):
                raise SystemExit(f"pair count differs from retained CSV: {path}")
            if pairs and m.fmt(
                statistics.fmean(p["tree_distance"] for p in pairs)
            ) != kept["mean_tree_distance"]:
                raise SystemExit(f"mean path differs from retained CSV: {path}")
            out = {
                "corpus": corpus.name,
                "group": corpus.group,
                "source_path": row["source_path"],
                "source_sha256": row["source_sha256"],
                "tokens": r.tokens,
                "tree_pairs": len(pairs),
            }
            if not pairs:
                rows.append({**out, "status": "excluded", "reason": "no tree pairs"})
                continue
            for p in filter(in_module, pairs):
                lca = common_ancestor(p["decl_chain"], p["use_chain"])
                lca_kinds[lca[0].replace("SyntaxKind.", "")] += 1
            c = compare_file(pairs, random.Random(f"{SEED}:{row['source_path']}"))
            for name, scope in c.pop("scopes").items():
                scopes[name] = merge_scopes([scopes[name], scope])
            status, reason = "compared", ""
            if not c["pairs_with_baseline"]:
                status = "excluded"
                reason = (
                    "no pair lies inside a module or interface"
                    if c["pairs_outside_module"] == len(pairs)
                    else "no use of a different declaration in the same module"
                )
            fmt = {
                k: (m.fmt(v) if isinstance(v, float) else ("" if v is None else v))
                for k, v in c.items()
            }
            ratio = (
                m.fmt(c["unrelated_tree"] / c["related_tree"])
                if c["pairs_with_baseline"]
                else ""
            )
            rows.append({**out, "status": status, "reason": reason, **fmt, "ratio": ratio})

    fields = list(max(rows, key=len))
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n", restval="")
        w.writeheader()
        w.writerows(rows)

    compared = [r for r in rows if r["status"] == "compared"]
    largest = max(compared, key=lambda r: int(r["tree_pairs"]))
    primary = describe(compared)
    lo = primary["median_ratio_ci95"][0]
    separates = (
        lo > RATIO_THRESHOLD
        and primary["median_prob_unrelated_longer_ties_half"] >= SUPERIORITY_THRESHOLD
    )
    total_lca = sum(lca_kinds.values())
    package_fixture = fixture(FIXTURE_PACKAGE)
    if package_fixture["pairs_with_baseline"]:
        raise SystemExit("package-only fixture received a same-module baseline")
    summary = {
        "definition": __doc__.strip().splitlines()[0],
        "pyslang_version": ps.__version__,
        "samples_per_pair": SAMPLES_PER_PAIR,
        "seed": SEED,
        "thresholds": {
            "median_ratio_ci95_low_above": RATIO_THRESHOLD,
            "median_prob_unrelated_longer_ties_half_at_least": SUPERIORITY_THRESHOLD,
            "set": "post hoc, after the outcome was known; see the docstring",
        },
        "files_with_tree_pairs": sum(int(r["tree_pairs"]) > 0 for r in rows),
        "files_compared": len(compared),
        "files_without_baseline": [
            {"corpus": r["corpus"], "source_path": r["source_path"], "reason": r["reason"]}
            for r in rows
            if int(r["tree_pairs"]) > 0 and r["status"] != "compared"
        ],
        "pairs_outside_any_module": {
            "pairs": sum(int(r.get("pairs_outside_module", 0)) for r in rows),
            "files": [
                {
                    "corpus": r["corpus"],
                    "source_path": r["source_path"],
                    "pairs": int(r["pairs_outside_module"]),
                }
                for r in rows
                if int(r.get("pairs_outside_module", 0))
            ],
            "treatment": (
                "Outside the baseline, the scope strata, and the "
                "lowest-common-ancestor shares. Kept in the retained CSV and panel (b)."
            ),
        },
        "all": primary,
        "benchmark": describe([r for r in compared if r["group"] == "benchmark"]),
        "production": describe([r for r in compared if r["group"] == "production"]),
        "without_largest_file": describe([r for r in compared if r is not largest]),
        "files_with_at_least_10_pairs": describe(
            [r for r in compared if int(r["pairs_with_baseline"]) >= 10]
        ),
        "by_corpus": {
            name: median_ci([float(r["ratio"]) for r in compared if r["corpus"] == name])
            for name in sorted({r["corpus"] for r in compared})
        },
        "scope": {
            "module_level": describe_scope(scopes["module"]),
            "nested_below_module": describe_scope(
                merge_scopes(v for k, v in scopes.items() if k != "module")
            ),
            "nested_by_kind": {
                k: describe_scope(v)
                for k, v in sorted(scopes.items(), key=lambda kv: -kv[1]["pairs"])
                if k != "module"
            },
            "selection_note": (
                "Strata are defined from the related pair, so part of a gap can "
                "come from the selection. No threshold is applied here."
            ),
            f"files_with_at_least_{MIN_NESTED_PAIRS}_nested_pairs": median_ci(
                [
                    float(r["nested_ratio"])
                    for r in compared
                    if int(r["nested_pairs_with_baseline"]) >= MIN_NESTED_PAIRS
                ]
            ),
        },
        "files_where_every_candidate_shares_a_statement": sum(
            float(r["share_candidates_sharing_statement"]) == 1 for r in compared
        ),
        "lowest_common_ancestor_kinds_share": {
            k: round(v / total_lca, 4) for k, v in lca_kinds.most_common(8)
        },
        "separates": separates,
        "fixtures": {
            "flat_module_level": fixture(FIXTURE_FLAT),
            "nested_block_scoped": fixture(FIXTURE_SCOPED),
            "package_functions_no_module": package_fixture,
        },
    }
    OUTPUT_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in summary if k != "files_without_baseline"}, indent=2))


if __name__ == "__main__":
    main()
