#!/usr/bin/env python3
"""Measure how far a signal's uses sit from its declaration, in token order
and in the parse tree, for pinned public Verilog and SystemVerilog files.

Every row of the output traces to one file at one pinned commit, identified by
its SHA-256. The script clones or verifies the sources, parses each file with
pyslang, binds every name reference to the declaration it resolves to, and
writes one CSV row per file. Files that cannot be measured stay in the CSV with
``status=excluded`` and a reason; nothing is dropped.

Definitions (also in README.md and in Chapter 4):

token sequence
    The non-trivia tokens pyslang's preprocessor and parser read from the file,
    in source order. Comments, whitespace, compiler-directive lines, and
    inactive ``ifdef`` branches are not tokens. A macro invocation counts as one
    token plus the tokens of its arguments. Text pulled in by ``include`` is
    not part of the file's sequence.

declaration
    A net, variable, or subroutine argument (slang symbol kinds Net, Variable,
    FormalArgument) declared in the file. Ports count through the internal net
    or variable slang creates for them. Parameters, types, enum values,
    genvars, and subroutine names are not declarations here.

use
    Any reference to a declaration in an expression, read or write, as resolved
    by slang's name lookup (a NamedValue expression). The same (declaration,
    use) source position pair is counted once, however many parameterized
    instances elaborate it.

token distance
    |i_use - i_decl|, the number of positions between the declaration's name
    token and the use's name token in the token sequence.

tree distance
    The number of edges on the path between the declaration's syntax node and
    the use's syntax node in pyslang's concrete syntax tree.

def-use graph distance
    One edge for every pair, by construction. Not measured; it is the
    comparison the chapter draws.

Run ``--help`` for options. README.md in this folder gives the reproduction
commands.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import glob
import hashlib
import importlib.metadata
import io
import json
import platform
import re
import statistics
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import pyslang as ps
    from pyslang import ast, parsing, syntax
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Install the pinned requirements.txt before running.") from exc

STUDY_DIR = Path(__file__).resolve().parent
REPO_ROOT = STUDY_DIR.parents[2]
MANIFEST = STUDY_DIR / "corpus_manifest.csv"
SUMMARY = STUDY_DIR / "representation_dilation_summary.json"
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "book/contents/chapters/04-representations/data"
    / "fig-hardware-representation-dilation.csv"
)
DEFAULT_CACHE = STUDY_DIR / ".cache" / "repos"

# The deleted dataset whose file list this study re-measures.
LEGACY_COMMIT = "cba670bb7"
LEGACY_PATH = (
    "book/contents/chapters/04-representations/data/"
    "fig-hardware-representation-dilation.csv"
)

BOOTSTRAP_REPS = 10_000
BOOTSTRAP_SEED = 20260929

SIGNAL_KINDS = {
    ast.SymbolKind.Net,
    ast.SymbolKind.Variable,
    ast.SymbolKind.FormalArgument,
}
NAME_SYNTAX_KINDS = {
    syntax.SyntaxKind.IdentifierName,
    syntax.SyntaxKind.IdentifierSelectName,
}
# A module whose parameter has no default cannot be elaborated as a top. Each
# such parameter is set to this value, large enough for vector ranges and
# generate loops to be non-empty.
REQUIRED_PARAM_VALUE = 4
INV_PARAM = re.compile(r"BSG_INV_PARAM\(\s*(\w+)\s*\)")
SKIP_TOKEN_KINDS = {parsing.TokenKind.EndOfFile, parsing.TokenKind.Placeholder}


@dataclass(frozen=True)
class Corpus:
    name: str
    group: str  # "benchmark" or "production"
    url: str
    commit: str
    checkout: str
    legacy_label: str  # CorpusName prefix in the deleted CSV
    standalone: bool  # compile each file alone (benchmarks reuse module names)
    include_dirs: tuple[str, ...] = ()
    support_globs: tuple[str, ...] = ()  # definitions and packages, not measured
    legacy_dir: str | None = None  # disambiguates duplicate basenames
    predefines: tuple[str, ...] = ()
    # BaseJump marks required parameters with the BSG_INV_PARAM macro; treat
    # every such parameter as required even when a predefine gives it a
    # placeholder default.
    macro_required_params: bool = False


CORPORA = (
    Corpus(
        "VerilogEval",
        "benchmark",
        "https://github.com/NVlabs/verilog-eval",
        "c498220d0a52248f8e3fdffe279075215bde2da6",
        "verilog-eval",
        "VerilogEval",
        True,
        legacy_dir="dataset_spec-to-rtl",
    ),
    Corpus(
        "RTLLM",
        "benchmark",
        "https://github.com/hkust-zhiyao/RTLLM",
        "51ed553d0ffd32797a1a0a13e051656bf302c81f",
        "RTLLM",
        "RTLLM",
        True,
    ),
    Corpus(
        "BaseJump STL",
        "production",
        "https://github.com/bespoke-silicon-group/basejump_stl",
        "b48037e28544425839dbd617d45b1a82631bc1a9",
        "basejump_stl",
        "BaseJump",
        False,
        include_dirs=("bsg_misc", "bsg_noc"),
        support_globs=(
            "bsg_misc/*.sv",
            "bsg_dataflow/*.sv",
            "bsg_mem/*.sv",
            "bsg_async/*.sv",
            "bsg_noc/*.sv",
        ),
        # bsg_defines.sv gives BSG_INV_PARAM a placeholder default (-1) only
        # under XCELIUM; REQUIRED_PARAM_VALUE then replaces it.
        predefines=("XCELIUM",),
        macro_required_params=True,
    ),
    Corpus(
        "SERV",
        "production",
        "https://github.com/olofk/serv",
        "41e8aeedfd1e9ad5f95902c5b0dfc83d1c99e5d2",
        "serv",
        "SERV",
        False,
        support_globs=("rtl/*.v",),
    ),
    Corpus(
        "Ibex",
        "production",
        "https://github.com/lowRISC/ibex",
        "8b8ee086aef72e0833b7f0493d9d33f1e4d3c8e2",
        "ibex",
        "Ibex",
        False,
        include_dirs=(
            "rtl",
            "vendor/lowrisc_ip/ip/prim/rtl",
            "vendor/lowrisc_ip/dv/sv/dv_utils",
        ),
        support_globs=(
            "rtl/*_pkg.sv",
            "rtl/*.sv",
            "vendor/lowrisc_ip/ip/prim/rtl/*_pkg.sv",
            "vendor/lowrisc_ip/ip/prim_generic/rtl/*_pkg.sv",
            "vendor/lowrisc_ip/ip/prim/rtl/*.sv",
            "vendor/lowrisc_ip/ip/prim_generic/rtl/*.sv",
        ),
    ),
    Corpus(
        "PicoRV32",
        "production",
        "https://github.com/YosysHQ/picorv32",
        "a473fc8fca393771d83b0ffcf0b14db3393339d8",
        "picorv32",
        "PicoRV32",
        False,
    ),
)
CORPUS_BY_NAME = {c.name: c for c in CORPORA}


# --------------------------------------------------------------------------
# Sources
# --------------------------------------------------------------------------


def git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def ensure_checkout(corpus: Corpus, cache: Path, offline: bool) -> Path:
    """Clone the pinned commit if missing, then verify HEAD is that commit."""
    path = cache / corpus.checkout
    if not path.exists():
        if offline:
            raise SystemExit(f"{path} missing and --offline given")
        path.mkdir(parents=True)
        git("init", "-q", cwd=path)
        git("remote", "add", "origin", corpus.url, cwd=path)
        git("fetch", "-q", "--depth", "1", "origin", corpus.commit, cwd=path)
        git("checkout", "-q", "FETCH_HEAD", cwd=path)
    head = git("rev-parse", "HEAD", cwd=path)
    if head != corpus.commit:
        raise SystemExit(f"{corpus.name}: HEAD {head} is not pinned {corpus.commit}")
    return path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def derive_manifest(cache: Path) -> list[dict[str, str]]:
    """Rebuild the file list from the deleted dataset in git history.

    The legacy CSV recorded only a basename and a byte count per file. Each is
    matched to exactly one path at the pinned commit; an ambiguous or missing
    match stops the run.
    """
    text = git("show", f"{LEGACY_COMMIT}:{LEGACY_PATH}", cwd=REPO_ROOT)
    legacy = list(csv.DictReader(io.StringIO(text)))
    rows = []
    for rec in legacy:
        corpus = next(
            c for c in CORPORA if rec["CorpusName"].startswith(c.legacy_label)
        )
        root = cache / corpus.checkout
        hits = [
            p
            for p in root.rglob(rec["FilePath"])
            if ".git" not in p.parts and p.stat().st_size == int(rec["RawBytes"])
        ]
        if corpus.legacy_dir:
            hits = [p for p in hits if p.parent.name == corpus.legacy_dir]
        if len(hits) != 1:
            raise SystemExit(f"cannot match {rec['FilePath']}: {hits}")
        rel = hits[0].relative_to(root).as_posix()
        rows.append(
            {
                "corpus": corpus.name,
                "group": corpus.group,
                "repository_url": corpus.url,
                "repository_commit": corpus.commit,
                "source_path": rel,
                "source_sha256": sha256(hits[0]),
                "source_bytes": str(hits[0].stat().st_size),
            }
        )
    order = {c.name: i for i, c in enumerate(CORPORA)}
    rows.sort(key=lambda r: (order[r["corpus"]], r["source_path"]))
    return rows


def read_manifest() -> list[dict[str, str]]:
    with MANIFEST.open(encoding="utf-8") as fh:
        return list(csv.DictReader(l for l in fh if not l.startswith("#")))


def write_manifest(rows: list[dict[str, str]]) -> None:
    with MANIFEST.open("w", encoding="utf-8", newline="") as fh:
        fh.write(
            f"# File list re-derived from {LEGACY_PATH} at commit {LEGACY_COMMIT}\n"
            "# (basename + byte count, each matched to exactly one path at the pinned commit).\n"
            "# Regenerate: measure_representation_dilation.py --derive-manifest\n"
        )
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


# --------------------------------------------------------------------------
# Measurement
# --------------------------------------------------------------------------


def file_tokens(tree, sm, buffer_id) -> list[int]:
    """Sorted distinct source offsets of the file's token sequence."""
    tokens: list = []
    tree.root.visit(
        lambda x: tokens.append(x) if isinstance(x, parsing.Token) else None
    )
    positions = set()
    for tok in tokens:
        if tok.kind in SKIP_TOKEN_KINDS or tok.isMissing or not tok.rawText:
            continue
        off = file_offset(sm, tok.location, buffer_id)
        if off is not None:
            positions.add(off)
    return sorted(positions)


def file_offset(sm, loc, buffer_id) -> int | None:
    """Offset of a location in this file, or None if it lies elsewhere.

    Macro-argument text maps to where it is written; macro-body text maps to
    the invocation site.
    """
    orig = sm.getFullyOriginalLoc(loc)
    if orig.buffer == buffer_id:
        return orig.offset
    exp = sm.getFullyExpandedLoc(loc)
    if exp.buffer == buffer_id:
        return exp.offset
    return None


def node_key(node):
    r = node.sourceRange
    return (str(node.kind), r.start.buffer.id, r.start.offset, r.end.offset)


def required_params(module) -> set[str]:
    """Header parameters declared without a default value."""
    out: set[str] = set()
    plist = module.header.parameters
    if plist is None:
        return out
    for decl in plist.declarations:
        for d in getattr(decl, "declarators", []) or []:
            if hasattr(d, "initializer") and d.initializer is None:
                out.add(d.name.valueText)
    return out


def ancestors(node) -> list:
    chain = []
    while node is not None:
        chain.append(node_key(node))
        node = node.parent
    return chain


def tree_distance(a_chain: list, b_chain: list) -> int | None:
    b_index = {k: i for i, k in enumerate(b_chain)}
    for i, k in enumerate(a_chain):
        if k in b_index:
            return i + b_index[k]
    return None


@dataclass
class FileResult:
    tokens: int = 0
    lines: int = 0
    modules: int = 0
    declarations: int = 0
    pairs: int = 0
    token_distances: list = field(default_factory=list)
    tree_distances: list = field(default_factory=list)
    name_refs: int = 0
    name_refs_bound: int = 0
    cross_file_uses: int = 0
    parse_errors: int = 0
    first_parse_error: str = ""
    semantic_errors: int = 0
    required_params: int = 0


def measure_file(
    path: Path, corpus: Corpus, root: Path, support_trees, sm, bag
) -> FileResult:
    res = FileResult()
    tree = syntax.SyntaxTree.fromFile(str(path), sm, bag)
    first = tree.root.getFirstToken()
    buffer_id = first.location.buffer
    res.lines = path.read_bytes().count(b"\n")

    errs = [d for d in tree.diagnostics if d.isError()]
    res.parse_errors = len(errs)
    if errs:
        res.first_parse_error = (
            ps.DiagnosticEngine.reportAll(sm, [errs[0]]).strip().splitlines()[0]
        )

    positions = file_tokens(tree, sm, buffer_id)
    res.tokens = len(positions)

    modules = [
        m
        for m in tree.root.members
        if m.kind
        in (syntax.SyntaxKind.ModuleDeclaration, syntax.SyntaxKind.InterfaceDeclaration)
    ]
    res.modules = len(modules)
    tops = {m.header.name.valueText for m in modules}

    opts = ast.CompilationOptions()
    opts.flags = ast.CompilationFlags.IgnoreUnknownModules
    if tops:
        opts.topModules = tops
    required = set()
    for m in modules:
        required |= required_params(m)
    if corpus.macro_required_params:
        required |= set(INV_PARAM.findall(path.read_text(errors="ignore")))
    if required:
        opts.paramOverrides = [f"{p}={REQUIRED_PARAM_VALUE}" for p in sorted(required)]
    res.required_params = len(required)
    comp = ast.Compilation(ps.Bag([opts]))
    comp.addSyntaxTree(tree)
    own = str(path.resolve())
    for t in support_trees:
        if t[0] != own:
            comp.addSyntaxTree(t[1])

    decls: dict[tuple[str, int], object] = {}
    pairs: dict[tuple[int, int], tuple] = {}
    bound_offsets: set[int] = set()

    def visit(obj):
        if isinstance(obj, ast.Symbol) and obj.kind in SIGNAL_KINDS and obj.name:
            off = file_offset(sm, obj.location, buffer_id)
            if off is not None:
                decls[(obj.name, off)] = obj
        if isinstance(obj, ast.NamedValueExpression):
            use_off = file_offset(sm, obj.sourceRange.start, buffer_id)
            if use_off is not None:
                bound_offsets.add(use_off)
                sym = obj.symbol
                if sym.kind in SIGNAL_KINDS:
                    decl_off = file_offset(sm, sym.location, buffer_id)
                    if decl_off is None:
                        pairs.setdefault((-1, use_off), None)
                    elif decl_off != use_off:
                        pairs.setdefault((decl_off, use_off), (sym, obj))
        return ast.VisitAction.Advance

    comp.getRoot().visit(visit)
    diags = comp.getAllDiagnostics()
    res.semantic_errors = (
        sum(
            1
            for d in diags
            if d.isError() and file_offset(sm, d.location, buffer_id) is not None
        )
        - res.parse_errors
    )

    # Coverage: expression-name syntax nodes in this file whose text names a
    # signal declared in this file, and how many of them slang bound.
    declared_names = {name for name, _ in decls}
    names: list = []
    tree.root.visit(
        lambda x: names.append(x)
        if isinstance(x, syntax.SyntaxNode) and x.kind in NAME_SYNTAX_KINDS
        else None
    )
    name_nodes: dict[int, object] = {}
    for node in names:
        tok = node.identifier
        off = file_offset(sm, tok.location, buffer_id)
        if off is None:
            continue
        name_nodes.setdefault(off, node)
        if tok.valueText not in declared_names:
            continue
        res.name_refs += 1
        if off in bound_offsets:
            res.name_refs_bound += 1

    chains: dict = {}
    for (decl_off, use_off), payload in sorted(pairs.items()):
        if decl_off < 0:
            res.cross_file_uses += 1
            continue
        i = bisect.bisect_right(positions, decl_off) - 1
        j = bisect.bisect_right(positions, use_off) - 1
        res.token_distances.append(abs(j - i))
        sym, expr = payload
        # A use inside a select (a[3:0]) has no syntax node of its own; take
        # the name node written at the use's position.
        dsyn, usyn = sym.syntax, name_nodes.get(use_off, expr.syntax)
        if dsyn is not None and usyn is not None:
            dk, uk = node_key(dsyn), node_key(usyn)
            if dk not in chains:
                chains[dk] = ancestors(dsyn)
            if uk not in chains:
                chains[uk] = ancestors(usyn)
            td = tree_distance(chains[dk], chains[uk])
            if td is not None:
                res.tree_distances.append(td)
    res.pairs = len(res.token_distances)
    res.declarations = len({d for d, _ in pairs if d >= 0})
    return res


def pct(values: list, q: float) -> float:
    s = sorted(values)
    k = (len(s) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def fmt(x: float) -> str:
    return f"{x:.4f}"


def run(cache: Path, offline: bool, output: Path) -> None:
    manifest = read_manifest()
    roots = {c.name: ensure_checkout(c, cache, offline) for c in CORPORA}
    for row in manifest:
        p = roots[row["corpus"]] / row["source_path"]
        if sha256(p) != row["source_sha256"]:
            raise SystemExit(f"hash mismatch: {p}")

    out_rows = []
    for corpus in CORPORA:
        root = roots[corpus.name]
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
        rows = [r for r in manifest if r["corpus"] == corpus.name]
        print(
            f"{corpus.name}: {len(rows)} files, {len(support)} support files",
            file=sys.stderr,
        )
        for row in rows:
            path = root / row["source_path"]
            r = measure_file(path, corpus, root, support, sm, bag)
            status, reason = "measured", ""
            if r.parse_errors:
                status, reason = "excluded", f"parse error: {r.first_parse_error}"
            elif r.pairs == 0:
                status = "excluded"
                reason = (
                    "no module or interface declaration"
                    if r.modules == 0
                    else "no same-file signal declaration-use pairs"
                )
            td, tr = r.token_distances, r.tree_distances
            out_rows.append(
                {
                    "corpus": corpus.name,
                    "group": corpus.group,
                    "repository_url": row["repository_url"],
                    "repository_commit": row["repository_commit"],
                    "source_path": row["source_path"],
                    "source_sha256": row["source_sha256"],
                    "status": status,
                    "exclusion_reason": reason,
                    "lines": r.lines,
                    "tokens": r.tokens,
                    "modules": r.modules,
                    "declarations_used": r.declarations,
                    "def_use_pairs": r.pairs,
                    "mean_token_distance": fmt(statistics.fmean(td)) if td else "",
                    "median_token_distance": fmt(statistics.median(td)) if td else "",
                    "p90_token_distance": fmt(pct(td, 0.9)) if td else "",
                    "max_token_distance": max(td) if td else "",
                    "mean_normalized_distance": fmt(statistics.fmean(td) / r.tokens)
                    if td
                    else "",
                    "tree_pairs": len(tr),
                    "mean_tree_distance": fmt(statistics.fmean(tr)) if tr else "",
                    "median_tree_distance": fmt(statistics.median(tr)) if tr else "",
                    "max_tree_distance": max(tr) if tr else "",
                    "def_use_graph_distance": 1 if td else "",
                    "cross_file_uses": r.cross_file_uses,
                    "name_refs": r.name_refs,
                    "name_refs_bound": r.name_refs_bound,
                    "required_params_set": r.required_params,
                    "parse_errors": r.parse_errors,
                    "semantic_errors_in_file": r.semantic_errors,
                }
            )

    version = importlib.metadata.version("pyslang")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as fh:
        fh.write(
            "# Definition-use distance in token order and in the syntax tree, per source file.\n"
            f"# Parser: pyslang {version}. Generator: data/studies/09-representation-dilation/"
            "measure_representation_dilation.py\n"
            "# Source: pinned public repositories; see repository_url, repository_commit, source_sha256.\n"
        )
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(out_rows)
    write_summary(out_rows, version)
    measured = sum(r["status"] == "measured" for r in out_rows)
    print(
        f"wrote {output} ({measured} measured, {len(out_rows) - measured} excluded)",
        file=sys.stderr,
    )


# --------------------------------------------------------------------------
# Summary: log-log fit with a file-level bootstrap
# --------------------------------------------------------------------------


def loglog_fit(rows: list[dict], y_key: str = "mean_token_distance") -> dict:
    """OLS of log10(y) on log10(tokens), with a percentile bootstrap over files."""
    import numpy as np

    rows = [r for r in rows if r[y_key] != ""]
    x = np.log10([float(r["tokens"]) for r in rows])
    y = np.log10([float(r[y_key]) for r in rows])
    slope, intercept = np.polyfit(x, y, 1)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    n = len(x)
    boots = np.empty(BOOTSTRAP_REPS)
    for b in range(BOOTSTRAP_REPS):
        idx = rng.integers(0, n, n)
        boots[b] = np.polyfit(x[idx], y[idx], 1)[0]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    r = np.corrcoef(x, y)[0, 1]
    return {
        "n": n,
        "slope": round(float(slope), 4),
        "intercept": round(float(intercept), 4),
        "slope_ci95": [round(float(lo), 4), round(float(hi), 4)],
        "r_squared": round(float(r * r), 4),
    }


def write_summary(rows: list[dict], version: str) -> None:
    measured = [r for r in rows if r["status"] == "measured"]
    groups = {
        "all": measured,
        "benchmark": [r for r in measured if r["group"] == "benchmark"],
        "production": [r for r in measured if r["group"] == "production"],
    }
    summary = {
        "pyslang_version": version,
        "python_version": platform.python_version(),
        "bootstrap": {"reps": BOOTSTRAP_REPS, "seed": BOOTSTRAP_SEED, "unit": "file"},
        "files_in_manifest": len(rows),
        "files_measured": len(measured),
        "files_excluded": len(rows) - len(measured),
        "def_use_pairs": sum(int(r["def_use_pairs"]) for r in measured),
        "fits": {k: loglog_fit(v) for k, v in groups.items()},
        "tree_distance_fits": {
            k: loglog_fit(v, "mean_tree_distance") for k, v in groups.items()
        },
        "sensitivity": {
            "median_token_distance": loglog_fit(measured, "median_token_distance"),
            "without_largest_file": loglog_fit(
                sorted(measured, key=lambda r: int(r["tokens"]))[:-1]
            ),
        },
        "binding_coverage": round(
            sum(int(r["name_refs_bound"]) for r in measured)
            / max(1, sum(int(r["name_refs"]) for r in measured)),
            4,
        ),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--cache", type=Path, default=DEFAULT_CACHE, help="where pinned clones live"
    )
    ap.add_argument(
        "--offline",
        action="store_true",
        help="never clone; fail if a checkout is missing",
    )
    ap.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT, help="dataset CSV to write"
    )
    ap.add_argument(
        "--derive-manifest",
        action="store_true",
        help="rebuild corpus_manifest.csv from the deleted dataset in git history",
    )
    args = ap.parse_args()
    if args.derive_manifest:
        for c in CORPORA:
            ensure_checkout(c, args.cache, args.offline)
        rows = derive_manifest(args.cache)
        write_manifest(rows)
        print(f"wrote {MANIFEST} ({len(rows)} files)", file=sys.stderr)
        return
    run(args.cache, args.offline, args.output)


if __name__ == "__main__":
    main()
