# Declaration-to-use distance in token order and in the syntax tree

This study measures how far a signal's uses sit from its declaration when RTL is
read as a flat token sequence, and how far the same pairs sit in a parse tree.
It supports `fig-ch04-spatial-semantic-dilation` and the paragraphs around it in
Chapter 4. Every number in that passage is computed inline from the CSV this
study writes.

It replaces the first version of the figure, deleted on 29 September 2026. That
dataset named real files at real commits, but its token and syntax-node counts
matched no parser and no extraction script existed. This study keeps its file
list and nothing else.

## Definitions

These match the chapter and the docstring of `measure_representation_dilation.py`.

| Term | Definition |
| --- | --- |
| Token sequence | The non-trivia tokens pyslang's preprocessor and parser read from the file, in source order. Comments, whitespace, compiler-directive lines, and inactive `` `ifdef `` branches are not tokens. A macro invocation counts as one token plus the tokens of its arguments. Text pulled in by `` `include `` is not part of the file. |
| Declaration | A net, variable, or subroutine argument declared in the file (slang symbol kinds `Net`, `Variable`, `FormalArgument`). Ports count through the internal net or variable slang creates for them. Parameters, types, enum values, genvars, and subroutine names are excluded. |
| Use | A reference to a declaration in any expression, read or write, as bound by slang's name lookup (a `NamedValue` expression). Each (declaration position, use position) pair counts once, however many parameterized instances elaborate it. Only pairs whose declaration and use are in the same file count. |
| Token distance | `abs(i_use - i_decl)`, positions between the declared name's token and the use's token. |
| File value | The mean over all pairs in the file (`mean_token_distance`). The CSV also carries the median, 90th percentile, and maximum. |
| Tree distance | Edges on the path between the declaration's syntax node and the use's name node in pyslang's concrete syntax tree (`mean_tree_distance`). |
| Def-use graph distance | One edge per pair, by construction. Not measured. The CSV column `def_use_graph_distance` records the constant so the comparison is explicit. |

The unit of analysis is a source file, because a file is the flat sequence a
text model is given. Most files hold one module; `picorv32.v` holds several.

## Corpus

344 files from six repositories, each cloned at a pinned commit.

| Corpus | Group | Files | Commit |
| --- | --- | ---: | --- |
| VerilogEval (`dataset_spec-to-rtl/*_ref.sv`) | benchmark | 156 | `c498220d0a52` |
| RTLLM (`verified_*.v`) | benchmark | 50 | `51ed553d0ffd` |
| BaseJump STL (`bsg_dataflow`, `bsg_misc`) | production | 86 | `b48037e28544` |
| SERV (`rtl/`) | production | 18 | `41e8aeedfd1e` |
| Ibex (`rtl/`) | production | 33 | `8b8ee086aef7` |
| PicoRV32 (`picorv32.v`) | production | 1 | `a473fc8fca39` |

`corpus_manifest.csv` records repository, full commit, path, SHA-256, and byte
count for every file. It was derived from the deleted dataset
(`git show cba670bb7:book/contents/chapters/04-representations/data/fig-hardware-representation-dilation.csv`),
which recorded only a basename and a byte count per file. Each pair matched
exactly one path at the pinned commit once VerilogEval was restricted to
`dataset_spec-to-rtl` (152 of its reference files also appear, byte-identical,
in `dataset_code-complete-iccad2023`). `--derive-manifest` repeats that
derivation. Why the original author chose these 86 BaseJump files and these 33
Ibex files is not recorded anywhere.

## How files are elaborated

Name resolution needs the definitions a file refers to, so each file is compiled
with support files from its own repository (packages, sibling modules, include
directories). Support files are parsed but not measured. The file's own modules
are the top-level modules.

- VerilogEval, RTLLM, and PicoRV32 are compiled alone. The benchmarks reuse
  module names such as `RefModule` across files.
- BaseJump: `bsg_misc`, `bsg_dataflow`, `bsg_mem`, `bsg_async`, `bsg_noc`, with
  `XCELIUM` predefined. BaseJump declares required parameters through the
  `BSG_INV_PARAM` macro, which has a default only under that branch.
- Every parameter without a usable default (bare declarations, and every
  `BSG_INV_PARAM`) is set to 4 so the module can be a top. This affects 80
  BaseJump files and no others (`required_params_set` column).
- SERV: `rtl/*.v`. Ibex: `rtl/*.sv` plus the lowRISC `prim` and `prim_generic`
  sources and packages vendored in the repository.

## Exclusions

Nothing is dropped. Files that yield no measurement stay in the CSV with
`status=excluded` and an `exclusion_reason`.

| File | Reason |
| --- | --- |
| `ibex/rtl/ibex_pkg.sv` | no module or interface declaration |
| `ibex/rtl/ibex_tracer_pkg.sv` | no module or interface declaration |

No file had a parse error. One measured file, `bsg_fifo_1r1w_small.sv`, has
token distances but no tree distance, because all of its uses come through
`.*` wildcard port connections, which have no name node.

## Coverage

`name_refs` counts expression-name syntax nodes in the file whose text names a
signal declared in the file; `name_refs_bound` counts those slang bound. Across
measured files, 97.2% are bound. Most unbound references sit in generate
branches that the default (or overridden) parameter values leave inactive,
concentrated in `ibex_top`, `ibex_lockstep`, and `ibex_ex_block`.
`cross_file_uses` is zero for every file.

## Results

`representation_dilation_summary.json` holds the fits. Log-log OLS of
`mean_token_distance` on `tokens`, with a 10,000-replicate percentile bootstrap
over files (seed 20260929):

| Subset | Files | Slope | 95% CI | R² |
| --- | ---: | ---: | --- | ---: |
| All | 342 | 0.96 | 0.92 to 0.99 | 0.96 |
| Benchmark | 206 | 0.98 | 0.92 to 1.03 | 0.96 |
| Production | 136 | 0.97 | 0.90 to 1.02 | 0.94 |
| All, median distance per file | 342 | 0.92 | 0.87 to 0.96 | 0.94 |
| All, without `bsg_scatter_gather` | 341 | 0.95 | 0.91 to 0.98 | 0.96 |
| Tree distance, all | 341 | 0.04 | 0.03 to 0.05 | 0.09 |

The mean pair spans a median of 44% of its file's tokens. A slope near one with
that share is what declarations grouped at the top of a module and uses spread
through the body would produce. The syntax-tree path stays between 5 and 22
edges per file (median about 10) across file lengths from 15 to 164,517
tokens.

These numbers are recorded here for orientation. The chapter recomputes every
value it prints from the CSV.

## Reproduce

From the repository root:

```bash
python3 -m venv .venv-dilation
.venv-dilation/bin/pip install -r data/studies/09-representation-dilation/requirements.txt

# 1. Measure. Clones the six pinned commits into data/studies/09-representation-dilation/.cache/
#    (gitignored) on first run, verifies each HEAD and every file's SHA-256, then writes
#    book/contents/chapters/04-representations/data/fig-hardware-representation-dilation.csv
#    and representation_dilation_summary.json.
.venv-dilation/bin/python data/studies/09-representation-dilation/measure_representation_dilation.py

# 2. Redraw the figure twins (svg, pdf, png) into the chapter's images/ folder.
.venv-dilation/bin/python data/studies/09-representation-dilation/plot_representation_dilation.py
```

`--cache DIR` points at existing clones; `--offline` refuses to clone. The
measurement takes about 20 seconds after cloning.

## Determinism check

The CSV carries no timestamps, and the bootstrap is seeded, so reruns must be
byte-identical:

```bash
P=.venv-dilation/bin/python
S=data/studies/09-representation-dilation/measure_representation_dilation.py
$P $S --output /tmp/dil1.csv && $P $S --output /tmp/dil2.csv && cmp /tmp/dil1.csv /tmp/dil2.csv
```

On 2026-09-29 two runs on existing clones and a third from fresh clones produced
identical CSVs (SHA-256 recorded in the chapter 4 report) and identical summary
files.

## Limits

- Distances are measured only over bound pairs. The unbound 2.8% is not
  random; it is concentrated in inactive generate branches.
- Token distance depends on declaration style. The result describes these
  files as written, not RTL in general.
- The benchmark and production groups differ in size by construction, so the
  per-group slopes are the check that the trend is not produced by pooling.
- The measurement says nothing about whether any model's accuracy depends on
  this distance.
