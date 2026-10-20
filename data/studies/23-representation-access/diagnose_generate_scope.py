#!/usr/bin/env python3
"""Record BaseJump conditional-generate source coverage and override value."""
from __future__ import annotations
import csv, glob, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from evidence_bundle import verify_sources
import pyslang as ps
from pyslang import ast, parsing, syntax


def main():
    verify_sources(HERE)
    manifest = json.loads((HERE / "source_manifest.json").read_text())
    root = HERE / ".cache" / "repos" / "basejump_stl"
    source = root / "bsg_dataflow" / "bsg_scatter_gather.sv"
    text = source.read_text(encoding="utf-8")
    regex = re.compile(r"^\s*if\s*\(\s*vec_size_lp\s*==\s*(\d+)\s*\)", re.M)
    matches = list(regex.finditer(text))
    starts = [(int(m.group(1)), text.count("\n", 0, m.start()) + 1) for m in matches]
    pair_file = HERE / "derived" / "pairs.csv"
    with pair_file.open(encoding="utf-8", newline="") as f:
        pairs = [
            r
            for r in csv.DictReader(f)
            if r["corpus"] == "BaseJump STL"
            and r["source_path"] == "bsg_dataflow/bsg_scatter_gather.sv"
        ]
    branch_counts = {v: 0 for v, _ in starts}
    pre_branch = 0
    for row in pairs:
        line = int(row["use_line"])
        eligible = [(v, s) for v, s in starts if s <= line]
        if not eligible:
            pre_branch += 1
        else:
            branch_counts[max(eligible, key=lambda x: x[1])[0]] += 1

    corpus = next(
        c for c in __import__("extract_pairs").CORPORA if c.name == "BaseJump STL"
    )
    sm = ps.SourceManager()
    pp = parsing.PreprocessorOptions()
    pp.additionalIncludePaths = [str(root / d) for d in corpus.include_dirs]
    pp.predefines = list(corpus.predefines)
    bag = ps.Bag([pp])
    support = []
    seen = set()
    for pattern in corpus.support_globs:
        for file in sorted(glob.glob(str(root / pattern))):
            key = str(Path(file).resolve())
            if key not in seen:
                seen.add(key)
                support.append((key, syntax.SyntaxTree.fromFile(file, sm, bag)))
    tree = syntax.SyntaxTree.fromFile(str(source), sm, bag)
    modules = [
        m
        for m in tree.root.members
        if m.kind
        in (syntax.SyntaxKind.ModuleDeclaration, syntax.SyntaxKind.InterfaceDeclaration)
    ]
    tops = {m.header.name.valueText for m in modules}
    required = set()
    for module in modules:
        required |= __import__("extract_pairs").required_params(module)
    required |= set(__import__("extract_pairs").INV_PARAM.findall(text))
    opts = ast.CompilationOptions()
    opts.flags = ast.CompilationFlags.IgnoreUnknownModules
    opts.topModules = tops
    opts.paramOverrides = [f"{p}=4" for p in sorted(required)]
    comp = ast.Compilation(ps.Bag([opts]))
    comp.addSyntaxTree(tree)
    for _, st in support:
        comp.addSyntaxTree(st)
    instances = [
        i for i in comp.getRoot().topInstances if i.name == "bsg_scatter_gather"
    ]
    if len(instances) != 1:
        raise SystemExit(f"expected one bsg_scatter_gather top, found {len(instances)}")
    param = next(
        (p for p in instances[0].body.parameters if p.name == "vec_size_lp"), None
    )
    if param is None:
        raise SystemExit("vec_size_lp parameter not found")
    receipt = {
        "pyslang_version": ps.__version__,
        "repository_url": corpus.url,
        "repository_commit": corpus.commit,
        "source_path": "bsg_dataflow/bsg_scatter_gather.sv",
        "source_sha256": next(r["source_sha256"] for r in pairs),
        "top_parameter_override": {
            "name": "vec_size_lp",
            "requested_value": 4,
            "observed_instance_value": str(param.value),
        },
        "measurement_scope": "The pair extractor visits bound source references in all conditional-generate branches present in the module body, not only the branch selected by the parameter value.",
        "pair_rows_by_source_branch": [
            {
                "condition": f"vec_size_lp == {value}",
                "if_line": line,
                "pair_rows": branch_counts[value],
            }
            for value, line in starts
        ],
        "pair_rows_before_first_branch": pre_branch,
        "pair_rows_total": len(pairs),
    }
    (HERE / "diagnostics" / "bsg_scatter_gather_generate_scope.json").write_text(
        json.dumps(receipt, indent=2) + "\n"
    )
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
