#!/usr/bin/env python3
"""Find silent shortcuts in analysis code and report any that nobody has reviewed.

Patterns: failures hidden by except blocks, fallback defaults, hardcoded result
values or plotted series, mock or random data, silently dropped items, and reuse
of cached results. Python files under data/ and book/contents/, and {python}
cells in the chapters, are scanned. A hit is a candidate, not a defect. Each one needs a disposition in
data/audits/shortcuts-reviewed.yml from a reviewer who did not write the code,
bound to the hash of the flagged line, so an edited line is reviewed again.

A pattern scan misses any shortcut it has no pattern for. Reading the code
remains necessary.

    python3 data/scan_shortcuts.py           (fail on unreviewed hits)
    python3 data/scan_shortcuts.py --list    (print every hit as JSON lines)
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REVIEWED = ROOT / "data/audits/shortcuts-reviewed.yml"
SKIP_PARTS = {".cache", "__pycache__", "archived_ch08", "raw", ".venv", "venv", "upstream", "vendor", "runs"}
TOOLING = {"run_study.py", "validate_runs.py", "scan_shortcuts.py", "validate_claims.py", "clean_rebuild.py"}
RESULT_NAME = re.compile(r"(total|count|mean|median|ratio|gain|score|accuracy|rate|speedup|percent|pct|sum)", re.I)
FAKE_NAME = re.compile(r"(mock|fake|dummy|stub|placeholder|fabricat|synthetic)", re.I)
CHECK_CALL = re.compile(r"(exists|is_file|isfile|match|search|startswith)")
PYTHON_CELL = re.compile(r"^```\{python\}\n(.*?)^```", re.S | re.M)


def is_number(node: ast.AST) -> bool:
    if isinstance(node, ast.UnaryOp):
        return is_number(node.operand)
    return isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool)


def numeric_sequence(node: ast.AST) -> bool:
    if isinstance(node, (ast.List, ast.Tuple)):
        return len(node.elts) >= 4 and all(is_number(e) for e in node.elts)
    return False


def scan_tree(tree: ast.AST):
    for node in ast.walk(tree):
        if numeric_sequence(node):
            yield node.lineno, "hardcoded-values"
        elif isinstance(node, ast.Dict) and sum(is_number(v) for v in node.values) >= 4:
            yield node.lineno, "hardcoded-values"
        if isinstance(node, ast.ExceptHandler):
            quiet = all(isinstance(s, (ast.Pass, ast.Continue, ast.Return, ast.Assign, ast.AugAssign)) for s in node.body)
            if node.type is None or quiet:
                yield node.lineno, "hidden-failure"
        elif isinstance(node, ast.Call):
            name = getattr(node.func, "attr", getattr(node.func, "id", ""))
            if name in {"get", "getattr", "getenv", "setdefault"} and len(node.args) >= (3 if name == "getattr" else 2):
                if is_number(node.args[-1]) or isinstance(node.args[-1], ast.Constant) and node.args[-1].value not in (None, ""):
                    yield node.lineno, "fallback-default"
            text = ast.unparse(node.func)
            if re.search(r"(^|\.)random\.", text) or text.startswith(("np.random", "numpy.random", "torch.rand")):
                yield node.lineno, "random-data"
            if name in {"lru_cache", "cache"}:
                yield node.lineno, "cached-result"
        elif isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and is_number(node.values[-1]):
            yield node.lineno, "fallback-default"
        elif isinstance(node, ast.Assign):
            target = ast.unparse(node.targets[0])
            if is_number(node.value) and RESULT_NAME.search(target) and not target.startswith(("self.", "_")):
                yield node.lineno, "hardcoded-result"
            if FAKE_NAME.search(target):
                yield node.lineno, "mock-data"
        elif isinstance(node, ast.FunctionDef) and FAKE_NAME.search(node.name):
            yield node.lineno, "mock-data"
        elif isinstance(node, ast.If):
            test = ast.unparse(node.test)
            first = node.body[0] if node.body else None
            if isinstance(first, ast.Continue) and CHECK_CALL.search(test):
                yield node.lineno, "dropped-items"
            if "exists" in test and isinstance(first, ast.Return) and first.value is not None:
                yield node.lineno, "cached-result"


def sources():
    scripts = sorted((ROOT / "data").rglob("*.py")) + sorted((ROOT / "book/contents").rglob("*.py"))
    for path in scripts:
        rel = path.relative_to(ROOT)
        if not SKIP_PARTS.intersection(rel.parts) and path.name not in TOOLING:
            yield rel.as_posix(), path.read_text(encoding="utf-8", errors="replace"), 0
    for path in sorted((ROOT / "book/contents").rglob("*.qmd")):
        text = path.read_text(encoding="utf-8")
        for cell in PYTHON_CELL.finditer(text):
            yield path.relative_to(ROOT).as_posix(), cell.group(1), text[: cell.start(1)].count("\n")


def findings() -> tuple[list[dict], list[str]]:
    hits, unparsed = [], []
    for name, code, offset in sources():
        try:
            tree = ast.parse(code)
        except SyntaxError as error:
            unparsed.append(f"{name}: {error}")
            continue
        lines = code.splitlines()
        for lineno, kind in sorted(set(scan_tree(tree))):
            text = lines[lineno - 1].strip()
            hits.append({"file": name, "line": lineno + offset, "kind": kind, "text": text,
                         "key": hashlib.sha256(f"{name}|{kind}|{text}".encode()).hexdigest()[:16]})
    return hits, unparsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    hits, unparsed = findings()
    if args.list:
        for hit in hits:
            print(json.dumps(hit))
        return 0
    reviewed = {}
    if REVIEWED.is_file():
        reviewed = {r["key"]: r for r in yaml.safe_load(REVIEWED.read_text(encoding="utf-8")) or []}
    open_hits = [h for h in hits if h["key"] not in reviewed]
    defects = [r for r in reviewed.values() if r.get("disposition") == "defect"]
    for hit in open_hits:
        print(f"UNREVIEWED {hit['file']}:{hit['line']} {hit['kind']}: {hit['text'][:90]}", file=sys.stderr)
    for row in defects:
        print(f"OPEN DEFECT {row['file']} {row['kind']}: {row.get('reason', '')}", file=sys.stderr)
    for item in unparsed:
        print(f"UNPARSED {item}", file=sys.stderr)
    print(f"shortcut scan: {len(hits)} hits, {len(open_hits)} unreviewed, {len(defects)} open defects, {len(unparsed)} unparsed")
    return 1 if open_hits or defects or unparsed else 0


if __name__ == "__main__":
    sys.exit(main())
