#!/usr/bin/env python3
"""Measure syntax complexity from pinned, retained Verilog repositories.

This pipeline is deliberately separate from ``mine_hardware_ast_complexity.py``.
The earlier receipt remains available as a baseline, while this script produces
an independently named measured receipt whose rows are traceable to source
files and commit hashes.

The unit of analysis is a successfully parsed Verilog/SystemVerilog module
declaration. Metrics describe source syntax, not elaborated hardware. In
particular, clock-event signals and recognized CDC primitive mentions are
lexical indicators; they are not verified clock-domain or CDC counts.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

try:
    import pyslang
except ImportError as exc:  # pragma: no cover - dependency error is user-facing
    raise SystemExit(
        "Install pyslang==11.0.0 from requirements.txt before running this miner."
    ) from exc


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE = Path(__file__).resolve().parent / ".cache" / "ast-corpus"
DEFAULT_STUDY_DIR = REPO_ROOT / "data" / "studies" / "02-ast-complexity-cliff"


@dataclass(frozen=True)
class Corpus:
    name: str
    category: str
    url: str
    commit: str
    checkout_dir: str


CORPORA = (
    Corpus(
        name="VerilogEval",
        category="AI benchmark reference RTL",
        url="https://github.com/NVlabs/verilog-eval.git",
        commit="c498220d0a52248f8e3fdffe279075215bde2da6",
        checkout_dir="verilog-eval",
    ),
    Corpus(
        name="RTLLM",
        category="AI benchmark reference RTL",
        url="https://github.com/hkust-zhiyao/RTLLM.git",
        commit="51ed553d0ffd32797a1a0a13e051656bf302c81f",
        checkout_dir="RTLLM",
    ),
    Corpus(
        name="OpenTitan",
        category="Production-oriented open RTL",
        url="https://github.com/lowRISC/opentitan.git",
        commit="e3f3234aa3772760cdf40e79a8ae4471b6b02213",
        checkout_dir="opentitan",
    ),
    Corpus(
        name="CV32E40P",
        category="Production-oriented open RTL",
        url="https://github.com/openhwgroup/cv32e40p.git",
        commit="6033d2b1be3295ec774d17ac4cf226faacfdeb08",
        checkout_dir="cv32e40p",
    ),
    Corpus(
        name="VeeR EL2",
        category="Production-oriented open RTL",
        url="https://github.com/chipsalliance/Cores-SweRV.git",
        commit="d04b1c7ae675a63dc4307cacfd10547ec937b928",
        checkout_dir="Cores-SweRV",
    ),
    Corpus(
        name="BlackParrot",
        category="Production-oriented open RTL",
        url="https://github.com/black-parrot/black-parrot.git",
        commit="f91010f654a5dfd00f83dbe25dbda482218d540b",
        checkout_dir="black-parrot",
    ),
)


CDC_PRIMITIVE_PATTERN = re.compile(
    r"\b(?:async_fifo|fifo_async|cdc_[A-Za-z0-9_]*|[A-Za-z0-9_]*_cdc|"
    r"prim_flop_2sync|prim_pulse_sync|sync_[23]ff|two_ff_sync|"
    r"synchronizer|gray_sync|pulse_sync|handshake_sync)\b",
    re.IGNORECASE,
)
EVENT_SIGNAL_PATTERN = re.compile(
    r"@\s*\([^)]*?\b(?:posedge|negedge)\s+"
    r"(?P<signal>[A-Za-z_][A-Za-z0-9_$]*(?:\.[A-Za-z_][A-Za-z0-9_$]*)?)",
    re.IGNORECASE | re.DOTALL,
)
CLOCK_NAME_PATTERN = re.compile(r"(?:^|_)(?:clk|clock)(?:$|_)", re.IGNORECASE)


@dataclass
class ModuleRecord:
    corpus_category: str
    dataset_name: str
    repository_url: str
    repository_commit: str
    source_path: str
    source_sha256: str
    module_name: str
    clean_loc: int
    concrete_syntax_nodes: int
    concrete_syntax_depth: int
    syntax_diagnostic_count: int
    syntax_diagnostic_codes: str
    syntax_tree_valid: int
    event_control_signal_count: int
    clock_like_event_signal_count: int
    clock_like_event_signals: str
    recognized_cdc_primitive_mentions: int
    hierarchy_instantiation_count: int
    resolved_internal_submodule_instantiations: int
    ambiguous_internal_submodule_instantiations: int
    internal_hierarchy_depth: int
    extraction_timestamp: str
    _instantiated_modules: tuple[str, ...]


def run_git(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def ensure_checkout(corpus: Corpus, cache_dir: Path, offline: bool) -> Path:
    target = cache_dir / corpus.checkout_dir
    if not target.exists():
        if offline:
            raise RuntimeError(f"Missing offline checkout: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        run_git(
            [
                "clone",
                "--filter=blob:none",
                "--no-checkout",
                corpus.url,
                str(target),
            ]
        )
        run_git(["fetch", "--depth", "1", "origin", corpus.commit], cwd=target)
        run_git(["checkout", "--detach", corpus.commit], cwd=target)

    actual = run_git(["rev-parse", "HEAD"], cwd=target)
    if actual != corpus.commit:
        raise RuntimeError(
            f"Checkout mismatch for {corpus.name}: expected {corpus.commit}, "
            f"found {actual}. Remove only this gitignored cache checkout or use "
            "a separate --cache-dir."
        )
    return target


def selected_files(corpus: Corpus, checkout: Path) -> list[Path]:
    files = [
        path
        for path in checkout.rglob("*")
        if path.is_file() and path.suffix.lower() in {".v", ".sv"}
    ]

    def include(path: Path) -> bool:
        rel = path.relative_to(checkout).as_posix()
        if corpus.name == "VerilogEval":
            return rel.startswith("dataset_spec-to-rtl/") and rel.endswith("_ref.sv")
        if corpus.name == "RTLLM":
            return not rel.startswith("_") and path.name.startswith("verified_")
        if corpus.name == "OpenTitan":
            return rel.startswith("hw/") and "/rtl/" in rel and "/dv/" not in rel
        if corpus.name == "CV32E40P":
            return rel.startswith("rtl/")
        if corpus.name == "VeeR EL2":
            return rel.startswith("design/")
        if corpus.name == "BlackParrot":
            excluded = ("/test/", "/testbench/", "/simulation/", "/syn/", "/mock/")
            return "/src/v/" in rel and not any(token in rel for token in excluded)
        return False

    return sorted((path for path in files if include(path)), key=lambda p: str(p))


def syntax_node_metrics(node: object) -> tuple[int, int]:
    count = 0
    max_depth = 0

    def visit(current: object) -> None:
        nonlocal count, max_depth
        count += 1
        depth = 1
        parent = getattr(current, "parent", None)
        while parent is not None and parent is not node:
            depth += 1
            parent = getattr(parent, "parent", None)
        max_depth = max(max_depth, depth)

    node.visit(visit)
    return count, max_depth


def clean_loc(text: str) -> int:
    without_blocks = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    without_line_comments = re.sub(r"//[^\n]*", "", without_blocks)
    return sum(1 for line in without_line_comments.splitlines() if line.strip())


def module_records(
    corpus: Corpus,
    checkout: Path,
    timestamp: str,
) -> tuple[list[ModuleRecord], dict[str, int]]:
    records: list[ModuleRecord] = []
    selected = selected_files(corpus, checkout)
    stats = {"selected_files": len(selected), "oversize_files": 0, "modules": 0}

    for path in selected:
        if path.stat().st_size > 2_000_000:
            stats["oversize_files"] += 1
            continue
        source = path.read_bytes()
        file_hash = hashlib.sha256(source).hexdigest()
        tree = pyslang.syntax.SyntaxTree.fromFile(str(path))
        rel = path.relative_to(checkout).as_posix()
        diagnostic_codes = sorted(
            {str(diagnostic.code) for diagnostic in tree.diagnostics}
        )
        diagnostic_count = len(tree.diagnostics)
        tree_valid = int(tree.validate())

        for node in tree.root.members:
            if str(node.kind) != "SyntaxKind.ModuleDeclaration":
                continue
            module_name = node.header.name.valueText
            if not module_name:
                continue
            module_text = str(node)
            node_count, node_depth = syntax_node_metrics(node)

            instantiated: list[str] = []

            def collect_instantiations(child: object) -> None:
                if str(child.kind) != "SyntaxKind.HierarchyInstantiation":
                    return
                target = child.type.valueText
                if target:
                    instantiated.append(target)

            node.visit(collect_instantiations)

            event_signals = sorted(
                {
                    match.group("signal")
                    for match in EVENT_SIGNAL_PATTERN.finditer(module_text)
                }
            )
            clock_signals = sorted(
                signal
                for signal in event_signals
                if CLOCK_NAME_PATTERN.search(signal.replace(".", "_"))
            )

            records.append(
                ModuleRecord(
                    corpus_category=corpus.category,
                    dataset_name=corpus.name,
                    repository_url=corpus.url.removesuffix(".git"),
                    repository_commit=corpus.commit,
                    source_path=rel,
                    source_sha256=file_hash,
                    module_name=module_name,
                    clean_loc=clean_loc(module_text),
                    concrete_syntax_nodes=node_count,
                    concrete_syntax_depth=node_depth,
                    syntax_diagnostic_count=diagnostic_count,
                    syntax_diagnostic_codes=";".join(diagnostic_codes),
                    syntax_tree_valid=tree_valid,
                    event_control_signal_count=len(event_signals),
                    clock_like_event_signal_count=len(clock_signals),
                    clock_like_event_signals=";".join(clock_signals),
                    recognized_cdc_primitive_mentions=len(
                        CDC_PRIMITIVE_PATTERN.findall(module_text)
                    ),
                    hierarchy_instantiation_count=len(instantiated),
                    resolved_internal_submodule_instantiations=0,
                    ambiguous_internal_submodule_instantiations=0,
                    internal_hierarchy_depth=1,
                    extraction_timestamp=timestamp,
                    _instantiated_modules=tuple(instantiated),
                )
            )
    stats["modules"] = len(records)
    return records, stats


def assign_internal_hierarchy_depth(records: list[ModuleRecord]) -> None:
    by_dataset: dict[str, list[ModuleRecord]] = {}
    for record in records:
        by_dataset.setdefault(record.dataset_name, []).append(record)

    for dataset_records in by_dataset.values():
        definitions: dict[str, list[ModuleRecord]] = {}
        for record in dataset_records:
            definitions.setdefault(record.module_name, []).append(record)
        unique_definitions = {
            name: definition_records[0]
            for name, definition_records in definitions.items()
            if len(definition_records) == 1
        }

        graph: dict[int, set[int]] = {}
        for record in dataset_records:
            resolved = [
                child
                for child in record._instantiated_modules
                if child in unique_definitions
            ]
            ambiguous = [
                child
                for child in record._instantiated_modules
                if child in definitions and child not in unique_definitions
            ]
            record.resolved_internal_submodule_instantiations = len(resolved)
            record.ambiguous_internal_submodule_instantiations = len(ambiguous)
            graph[id(record)] = {id(unique_definitions[child]) for child in resolved}

        memo: dict[int, int] = {}

        def depth(record_id: int, active: set[int]) -> int:
            if record_id in memo:
                return memo[record_id]
            if record_id in active:
                return 1
            children = graph.get(record_id, set())
            value = 1 + max(
                (depth(child, active | {record_id}) for child in children), default=0
            )
            memo[record_id] = value
            return value

        for record in dataset_records:
            record.internal_hierarchy_depth = depth(id(record), set())


def write_csv(path: Path, records: list[ModuleRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    public_fields = [
        field
        for field in ModuleRecord.__dataclass_fields__
        if not field.startswith("_")
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=public_fields, lineterminator="\n")
        writer.writeheader()
        for record in records:
            row = asdict(record)
            writer.writerow({field: row[field] for field in public_fields})


def write_sources(path: Path, stats: dict[str, dict[str, int]], timestamp: str) -> None:
    fields = [
        "dataset_name",
        "corpus_category",
        "repository_url",
        "repository_commit",
        "selected_files",
        "oversize_files",
        "parsed_modules",
        "extraction_timestamp",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for corpus in CORPORA:
            corpus_stats = stats[corpus.name]
            writer.writerow(
                {
                    "dataset_name": corpus.name,
                    "corpus_category": corpus.category,
                    "repository_url": corpus.url.removesuffix(".git"),
                    "repository_commit": corpus.commit,
                    "selected_files": corpus_stats["selected_files"],
                    "oversize_files": corpus_stats["oversize_files"],
                    "parsed_modules": corpus_stats["modules"],
                    "extraction_timestamp": timestamp,
                }
            )


def distribution_summary(records: list[ModuleRecord]) -> dict[str, float | int]:
    import statistics

    return {
        "parsed_modules": len(records),
        "modules_from_files_with_syntax_diagnostics": sum(
            record.syntax_diagnostic_count > 0 for record in records
        ),
        "modules_with_invalid_recovered_syntax_trees": sum(
            not record.syntax_tree_valid for record in records
        ),
        "median_concrete_syntax_nodes": statistics.median(
            record.concrete_syntax_nodes for record in records
        ),
        "median_clean_loc": statistics.median(record.clean_loc for record in records),
        "median_internal_hierarchy_depth": statistics.median(
            record.internal_hierarchy_depth for record in records
        ),
        "resolved_internal_submodule_instantiations": sum(
            record.resolved_internal_submodule_instantiations for record in records
        ),
        "ambiguous_internal_submodule_instantiations": sum(
            record.ambiguous_internal_submodule_instantiations for record in records
        ),
        "modules_with_ambiguous_internal_instantiations": sum(
            record.ambiguous_internal_submodule_instantiations > 0 for record in records
        ),
        "share_with_multiple_clock_like_event_signals": sum(
            record.clock_like_event_signal_count > 1 for record in records
        )
        / len(records),
    }


def summary(
    records: list[ModuleRecord],
    stats: dict[str, dict[str, int]],
    timestamp: str,
) -> dict:
    import statistics

    groups: dict[str, dict[str, float | int]] = {}
    for category in sorted({record.corpus_category for record in records}):
        group = [r for r in records if r.corpus_category == category]
        groups[category] = distribution_summary(group)

    benchmark = groups["AI benchmark reference RTL"]
    production = groups["Production-oriented open RTL"]
    pooled_ratios = {
        "median_concrete_syntax_node_ratio": production["median_concrete_syntax_nodes"]
        / benchmark["median_concrete_syntax_nodes"],
        "median_clean_loc_ratio": production["median_clean_loc"]
        / benchmark["median_clean_loc"],
    }

    diagnostic_free_groups: dict[str, dict[str, float | int]] = {}
    for category in sorted({record.corpus_category for record in records}):
        diagnostic_free = [
            record
            for record in records
            if record.corpus_category == category
            and record.syntax_diagnostic_count == 0
            and record.syntax_tree_valid
        ]
        diagnostic_free_groups[category] = distribution_summary(diagnostic_free)
    diagnostic_free_benchmark = diagnostic_free_groups["AI benchmark reference RTL"]
    diagnostic_free_production = diagnostic_free_groups["Production-oriented open RTL"]
    diagnostic_free_ratios = {
        "median_concrete_syntax_node_ratio": diagnostic_free_production[
            "median_concrete_syntax_nodes"
        ]
        / diagnostic_free_benchmark["median_concrete_syntax_nodes"],
        "median_clean_loc_ratio": diagnostic_free_production["median_clean_loc"]
        / diagnostic_free_benchmark["median_clean_loc"],
    }

    datasets: dict[str, dict[str, float | int | str]] = {}
    for corpus in CORPORA:
        dataset_records = [
            record for record in records if record.dataset_name == corpus.name
        ]
        datasets[corpus.name] = {
            "corpus_category": corpus.category,
            **distribution_summary(dataset_records),
        }
    benchmark_dataset_medians = [
        float(dataset["median_concrete_syntax_nodes"])
        for dataset in datasets.values()
        if dataset["corpus_category"] == "AI benchmark reference RTL"
    ]
    production_dataset_medians = [
        float(dataset["median_concrete_syntax_nodes"])
        for dataset in datasets.values()
        if dataset["corpus_category"] == "Production-oriented open RTL"
    ]
    corpus_balanced = {
        "definition": (
            "median of production-repository syntax-node medians divided by "
            "median of benchmark-repository syntax-node medians"
        ),
        "benchmark_median_of_repository_medians": statistics.median(
            benchmark_dataset_medians
        ),
        "production_median_of_repository_medians": statistics.median(
            production_dataset_medians
        ),
    }
    corpus_balanced["median_concrete_syntax_node_ratio"] = (
        corpus_balanced["production_median_of_repository_medians"]
        / corpus_balanced["benchmark_median_of_repository_medians"]
    )

    return {
        "execution": {
            "python_version": platform.python_version(),
            "pyslang_version": importlib.metadata.version("pyslang"),
            "operating_system": platform.system(),
            "kernel_release": platform.release(),
            "architecture": platform.machine(),
            "miner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "extraction_timestamp": timestamp,
        },
        "measurement_boundary": (
            "Each source file is parsed as a standalone SystemVerilog syntax tree. "
            "Diagnostic counts are file-level and repeat on every module row from "
            "that file. Error-recovered trees remain in the pooled result."
        ),
        "corpora": stats,
        "datasets": datasets,
        "module_weighted_groups": groups,
        "module_weighted_ratios": pooled_ratios,
        "diagnostic_free_sensitivity": {
            "groups": diagnostic_free_groups,
            "ratios": diagnostic_free_ratios,
        },
        "corpus_balanced_sensitivity": corpus_balanced,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_STUDY_DIR)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Require all pinned checkouts to exist locally; never clone or fetch.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    conflict_marker = "<" * 7
    if conflict_marker in Path(__file__).read_text(encoding="utf-8"):
        raise RuntimeError("Refusing to run with conflict markers in the miner.")

    timestamp = datetime.now(timezone.utc).isoformat()
    records: list[ModuleRecord] = []
    stats: dict[str, dict[str, int]] = {}

    for corpus in CORPORA:
        checkout = ensure_checkout(corpus, args.cache_dir, args.offline)
        corpus_records, corpus_stats = module_records(corpus, checkout, timestamp)
        records.extend(corpus_records)
        stats[corpus.name] = corpus_stats
        print(
            f"{corpus.name}: {corpus_stats['selected_files']} files, "
            f"{corpus_stats['modules']} module declarations"
        )

    assign_internal_hierarchy_depth(records)
    records.sort(
        key=lambda r: (r.corpus_category, r.dataset_name, r.source_path, r.module_name)
    )

    output_csv = args.output_dir / "hardware_ast_complexity_measured.csv"
    sources_csv = args.output_dir / "hardware_ast_complexity_measured_sources.csv"
    summary_json = args.output_dir / "hardware_ast_complexity_measured_summary.json"
    write_csv(output_csv, records)
    write_sources(sources_csv, stats, timestamp)
    summary_json.write_text(
        json.dumps(summary(records, stats, timestamp), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    for path in (output_csv, sources_csv, summary_json):
        print(f"generated: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
