#!/usr/bin/env python3
"""Reparse the corpus with repository include directories on the search path.

The primary measurement parses each file alone, so an `include it cannot open
loses its macros and the parser recovers around the gap. This script asks which
way that bias runs. It repeats the miner's file selection and node count, adds
every repository directory holding HDL source to the include path, and reports
the pooled median ratio, both over all modules and over modules whose file
still has no substantive diagnostic. A substantive diagnostic is any code other
than DiagCode(NewlineEOF), the same definition Chapter 4 uses.

The node count of a repaired parse includes macro text expanded into a module,
so it is a preprocessed count. Each module therefore also reports its written
tokens, those located in the file itself and outside any macro expansion, under
this parse and under the plain parse with no include directories.

This is a sensitivity check on a retained, pinned corpus. It does not replace
the primary CSV, and files parse alone still: no compilation unit, elaboration,
or predefined macro set is supplied. Headers generated at build time, and
submodules outside the pinned repository, stay unresolved.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import sys
from pathlib import Path

import pyslang

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "data" / "scrapers"))

from mine_hardware_ast_complexity_real import (  # noqa: E402
    CORPORA,
    DEFAULT_CACHE,
    ensure_checkout,
    selected_files,
    syntax_node_metrics,
)

STUDY_DIR = Path(__file__).resolve().parent
OUTPUT = STUDY_DIR / "hardware_ast_complexity_include_sensitivity.json"
PRIMARY_CSV = STUDY_DIR / "hardware_ast_complexity_measured.csv"
HDL_SUFFIXES = {".sv", ".svh", ".v", ".vh"}


def include_dirs(checkout: Path) -> list[str]:
    dirs = {
        path.parent
        for path in checkout.rglob("*")
        if path.is_file()
        and path.suffix.lower() in HDL_SUFFIXES
        and ".git" not in path.parts
    }
    return sorted(str(d) for d in dirs)


def written_tokens(node, manager, buffer) -> tuple[int, int]:
    """Tokens written in the file and tokens that came from expansion."""
    tokens: list = []
    node.visit(lambda x: tokens.append(x) if isinstance(x, pyslang.parsing.Token) else None)
    written = expanded = 0
    for token in tokens:
        if token.isMissing:
            continue
        location = token.location
        if manager.isMacroLoc(location) or location.buffer != buffer:
            expanded += 1
        else:
            written += 1
    return written, expanded


def module_nodes(tree):
    return [
        node
        for node in tree.root.members
        if str(node.kind) == "SyntaxKind.ModuleDeclaration"
        and node.header.name.valueText
    ]


def plain_written(path: Path) -> list[int]:
    """Written tokens per module under the plain parse, in file order."""
    manager = pyslang.SourceManager()
    tree = pyslang.syntax.SyntaxTree.fromFile(str(path), manager)
    buffer = tree.root.getFirstToken().location.buffer
    return [written_tokens(node, manager, buffer)[0] for node in module_nodes(tree)]


def substantive(codes: set[str]) -> bool:
    return any(code != "DiagCode(NewlineEOF)" for code in codes)


def primary_hashes(name: str) -> dict[str, str]:
    with PRIMARY_CSV.open(encoding="utf-8") as handle:
        rows = csv.DictReader(line for line in handle if not line.startswith("#"))
        return {
            r["source_path"]: r["source_sha256"]
            for r in rows
            if r["dataset_name"] == name
        }


def corpus_records(corpus, checkout: Path) -> tuple[list[dict], int]:
    dirs = include_dirs(checkout)
    records: list[dict] = []
    expected = primary_hashes(corpus.name)
    seen: set[str] = set()
    for path in selected_files(corpus, checkout):
        if path.stat().st_size > 2_000_000:
            continue
        rel = path.relative_to(checkout).as_posix()
        if rel in expected:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != expected[rel]:
                raise RuntimeError(f"{corpus.name}: {rel} differs from the primary CSV")
            seen.add(rel)
        manager = pyslang.SourceManager()
        for directory in dirs:
            manager.addUserDirectories(directory)
        tree = pyslang.syntax.SyntaxTree.fromFile(str(path), manager)
        codes = {str(d.code) for d in tree.diagnostics}
        nodes = module_nodes(tree)
        buffer = tree.root.getFirstToken().location.buffer
        plain = plain_written(path)
        for index, node in enumerate(nodes):
            written, expanded = written_tokens(node, manager, buffer)
            records.append(
                {
                    "category": corpus.category,
                    "dataset": corpus.name,
                    "nodes": syntax_node_metrics(node)[0],
                    "substantive": substantive(codes),
                    "written_tokens": written,
                    "expanded_tokens": expanded,
                    # A parse repair can change how many modules a file yields.
                    "plain_written_tokens": plain[index]
                    if len(plain) == len(nodes)
                    else None,
                }
            )
    missing = set(expected) - seen
    if missing:
        raise RuntimeError(f"{corpus.name}: {len(missing)} primary files not found")
    return records, len(dirs)


def summarize(records: list[dict]) -> dict:
    def median(rows: list[dict]) -> float | None:
        return statistics.median(r["nodes"] for r in rows) if rows else None

    bench = [r for r in records if r["category"].startswith("AI")]
    prod = [r for r in records if r["category"].startswith("Production")]
    bench_clean = [r for r in bench if not r["substantive"]]

    def token_median(rows: list[dict], key: str) -> float:
        return statistics.median(r[key] for r in rows if r[key] is not None)

    prod_clean = [r for r in prod if not r["substantive"]]
    return {
        "modules": len(records),
        "benchmark_median": median(bench),
        "production_median": median(prod),
        "pooled_ratio": median(prod) / median(bench),
        "production_modules_with_substantive_diagnostics": sum(
            r["substantive"] for r in prod
        ),
        "benchmark_clean_modules": len(bench_clean),
        "production_clean_modules": len(prod_clean),
        "benchmark_clean_median": median(bench_clean),
        "production_clean_median": median(prod_clean),
        "clean_ratio": median(prod_clean) / median(bench_clean),
        "written_tokens": {
            "benchmark_median_include_path": token_median(bench, "written_tokens"),
            "production_median_include_path": token_median(prod, "written_tokens"),
            "ratio_include_path": token_median(prod, "written_tokens")
            / token_median(bench, "written_tokens"),
            "benchmark_median_plain": token_median(bench, "plain_written_tokens"),
            "production_median_plain": token_median(prod, "plain_written_tokens"),
            "ratio_plain": token_median(prod, "plain_written_tokens")
            / token_median(bench, "plain_written_tokens"),
            "modules_without_plain_match": sum(
                r["plain_written_tokens"] is None for r in records
            ),
            "production_expanded_tokens_include_path": sum(
                r["expanded_tokens"] for r in prod
            ),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument(
        "--archive-root",
        type=Path,
        help="directory of commit archives extracted under each corpus checkout "
        "name; used in place of git checkouts, and every file is still matched "
        "to the SHA-256 in the primary CSV",
    )
    ap.add_argument("--output", type=Path, default=OUTPUT)
    args = ap.parse_args()

    records: list[dict] = []
    per_repo: dict[str, dict] = {}
    commits: dict[str, str] = {}
    for corpus in CORPORA:
        if args.archive_root:
            checkout = args.archive_root / corpus.checkout_dir
        else:
            checkout = ensure_checkout(corpus, args.cache_dir, args.offline)
        rows, n_dirs = corpus_records(corpus, checkout)
        records.extend(rows)
        commits[corpus.name] = corpus.commit
        per_repo[corpus.name] = {
            "modules": len(rows),
            "include_directories": n_dirs,
            "median_nodes": statistics.median(r["nodes"] for r in rows),
            "modules_with_substantive_diagnostics": sum(
                r["substantive"] for r in rows
            ),
        }
        print(corpus.name, per_repo[corpus.name])

    result = {
        "definition": __doc__.strip().split("\n\n")[0],
        "pyslang_version": pyslang.__version__,
        "python_version": sys.version.split()[0],
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "commits": commits,
        "repositories": per_repo,
        "pooled": summarize(records),
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["pooled"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
