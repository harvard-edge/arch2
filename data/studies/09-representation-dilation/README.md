# Declaration-to-use distance in token order and in the syntax tree

This study measures how far a signal's uses sit from its declaration when RTL is
read as a flat token sequence, and how far the subset with recoverable syntax
paths sits in a parse tree.
It supports `fig-ch04-spatial-semantic-dilation` and the paragraphs around it in
Chapter 4. Every number in that passage is computed inline from the CSV this
study writes or from `tree_baseline_summary.json`, except the 256-token interval
coverage figures, which the chapter reads from
`data/studies/23-representation-access/derived/summary.json`.

Neither distance measures whether two signals are connected. The study's audit
(`data/audits/fig-ch04-spatial-semantic-dilation.yml`, verdict FAIL) raised this
for the tree path. The baseline below supports that at the file level and for
pairs that meet at the module, not for the 5.3 percent of in-module pairs that
meet below it. Panel (b) plots declaration-use pairs only and draws no baseline.

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
| Token distance | `abs(i_use - i_decl)`, the difference between the token positions of the declared name and the use. Adjacent tokens are 1 apart, so this is one more than the number of tokens that intervene. |
| File value | The mean over all pairs in the file (`mean_token_distance`). The CSV also carries the median, 90th percentile, and maximum. |
| Tree distance | Edges on the path between the declaration's syntax node and the use's name node in pyslang's concrete syntax tree, when both nodes and a common ancestor are recoverable (`mean_tree_distance`). |
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

`rtl/ibex_cheriot_pkg.sv` also has no module or interface declaration, but its
package functions yield same-file pairs, so this exclusion does not apply and the
file stays measured and plotted. It has no same-module baseline (see below).

No file had a parse error. Elaboration reported 13 semantic errors in five measured
files (`semantic_errors_in_file`: BaseJump 2 files, Ibex 2, SERV 1); those files
remain measured. Token distances cover 40,995 pairs in 342 files;
tree distances cover 40,825 pairs in 341 files. Eighteen files lack tree
distances for some or all token-distance pairs because syntax nodes or a
common ancestor cannot be recovered. One measured file,
`bsg_fifo_1r1w_small.sv`, has eight token-distance pairs but no tree distance:
all of its uses come through `.*` wildcard port connections, which have no
name node. The remaining 17 files have partial tree coverage. Per-file counts
are recorded in `def_use_pairs` and `tree_pairs`; the two panels therefore
use different available pair sets.

## Coverage

`name_refs` counts expression-name syntax nodes in the file whose text names a
signal declared in the file; `name_refs_bound` counts those slang bound. Across
measured files, 97.2% are bound, leaving 1,170 of 42,341 unbound. Ibex holds 928
of those, with 199 in `ibex_top.sv`. The cause is not established: an earlier
version of this file attributed them to inactive generate branches, but study 23
found bound pairs in the conditional-generate branches of `bsg_scatter_gather`
and assigns no cause to unbound status.
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

## Different-signal baseline

`measure_tree_baseline.py` asks whether a short tree path is a property of the
declaration-use relation or of shallow parse trees. For each pair it keeps the
declaration and draws up to 20 uses of different declarations in the same module
(seeded by file path; a use bound to the same declaration is never a candidate).
A pair enters only if its declaration and use lie in one module or interface. The
589 tree pairs of `rtl/ibex_cheriot_pkg.sv` lie in package functions, so they are
counted in `pairs_outside_module` and `pairs_outside_any_module` and enter neither
the baseline, nor the scope strata, nor the lowest-common-ancestor shares. They
remain in the measurement CSV and in panel (b).
The run stops if its pairs differ from the retained CSV in count or mean for any
file.

"Unrelated" in the script's field names means only that the use binds to a
different declaration. It does not establish that the two signals have no
dependency. In the median file 89.4% of candidate uses belong to signals named in
one assign, always block, or instance together with the declared signal, and in
127 of 336 files all of them do. That test is coarse, since a whole always block
counts as one statement.

**The thresholds are post hoc.** They were set on 2026-11-02 after the outcome was
known. Before writing the script its author had read an audit estimate of the same
comparison: median ratio 1.00, 5th to 95th percentile 0.94 to 1.10. The version
holding them was saved at 14:30:24 EET and the first logged run started at
14:30:43 EET. The ratio threshold of 1.10 equals that estimate's 95th percentile.
No record states why the probability threshold is 0.60, and that probability counts
each tie as half a win. No commit pins either value, so these times rest on file
modification times and the run log, and unlogged trials cannot be excluded. The
rule describes this corpus and does not test a prediction. The 95% interval tops
out at 1.000, so no ratio threshold at or above 1.00 would change the outcome at
the file median.

Five files have no baseline and are listed in `tree_baseline_summary.json`:
three VerilogEval files with one signal, one RTLLM file, and
`rtl/ibex_cheriot_pkg.sv`. 336 of 341 files are compared. Per-file results are in `tree_baseline_by_file.csv`.

| Stratum | Files | Median file mean, related | Unrelated | Median ratio (95% CI) | Median % strictly longer | Tied | Strictly shorter |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| All | 336 | 10.00 | 9.91 | 0.999 (0.998 to 1.000) | 41.5 | 17.4 | 40.4 |
| Benchmark | 202 | 10.13 | 9.90 | 0.995 (0.993 to 0.998) | 41.1 | 17.5 | 41.6 |
| Production | 134 | 9.89 | 9.97 | 1.000 (1.000 to 1.002) | 42.4 | 16.9 | 39.2 |
| Without `bsg_scatter_gather` | 335 | 10.00 | 9.90 | 0.999 (0.998 to 1.000) | 41.5 | 17.3 | 40.4 |
| Files with at least 10 pairs | 230 | 10.39 | 10.35 | 0.998 (0.996 to 1.000) | 42.8 | 15.2 | 41.5 |

The percentages are separate per-file medians, so they need not sum to 100.
Pooled over 780,435 draws the shares are 25.8% longer, 50.8% tied, and 23.4%
shorter; one file supplies most of those ties, and without it the shares are 44.5,
15.3, and 40.3. The post-hoc rule's probability (`prob_unrelated_longer_ties_half`)
counts ties as half, so its median of 0.50 is not a share of strictly longer paths.

`separates` is false under the post-hoc rule. At the file level, tree-path length
does not separate declaration-use pairs from different-signal same-module pairs in
this corpus. Pair-weighted means are 11.53 and 11.67 edges, and log-log slopes
against file length are 0.037 and 0.048. Token distance gives a median ratio of
1.00, with unrelated tokens averaged per pair as the related tokens are. An earlier
run averaged them per draw and gave 1.01.

The file-level result does not hold for every pair. For 94.7% of in-module pairs
the lowest common ancestor is the module declaration, and there the path follows the depth of
the two endpoints below the module (ratio 0.997; 23.4% longer, 53.1% tied, 23.5%
shorter). The other 2,120 pairs with a baseline meet below the module, and those do
separate:

| Lowest common ancestor | Pairs | Mean, related | Unrelated | Ratio | % longer | Tied | Shorter |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Below the module, all | 2,120 | 9.02 | 12.29 | 1.36 | 68.3 | 9.0 | 22.8 |
| Generate block | 1,449 | 8.76 | 11.40 | 1.30 | 65.7 | 10.8 | 23.6 |
| Function | 405 | 10.27 | 14.10 | 1.37 | 68.2 | 6.3 | 25.5 |
| For loop | 255 | 8.56 | 14.27 | 1.67 | 82.4 | 3.0 | 14.6 |

The 22 files with at least 10 such pairs have a median ratio of 1.35 (95% CI 1.30
to 1.44). Across whole files, only Ibex has a median ratio above 1.00 (1.04, 30
files). The stratum is defined from the related pair, so part of the gap can come
from the selection, and no threshold is applied to it.

Three constructed fixtures, not corpus data, run with every measurement. One with
every signal at module level gives ratio 1.00. One with signals scoped to separate
nested generate blocks gives 2.68, so the comparison can report a separation when
scoping produces one. One holds functions in a package and no module, gets no
baseline, and stops the run if that ever changes. The def-use graph is not measured here: it has an edge for
a bound pair by construction.

The first audit reported 9.94 against 10.08 edges and that unrelated paths were at
least as long in 70 percent of files. Its file-level conclusion stands. Its numbers differ
from these, and its control differs in two ways, whose separate effects were not
measured: it compared a use key with a declaration key, so the check meant to
exclude uses of the same signal never fired, and it did not restrict draws to one
module. Here 46.4 percent of files have unrelated paths at least as long.

The slopes here use the 336 compared files, so they differ slightly from the
341-file fit above.

Runs through `20261102T131501Z` keyed each pair by its enclosing module and treated
"no module" as one more key. That pooled the 589 package-function pairs of
`rtl/ibex_cheriot_pkg.sv` into a same-module baseline and into the below-module
stratum (audit finding F1), which the chapter's definition does not allow. Those
runs reported 337 files; 2,709 pairs below the module with ratio 1.33 and 67.3%
longer; 23 files at 1.33 (1.30 to 1.42); and a 93.4% module share over all pairs.
Run `20261102T134827Z` applies the restriction. That one file's row is the only row
whose values changed, and the module-level stratum, the 0.999 median ratio, and
`separates` did not change. The below-module ratio rose from 1.33 to 1.36 because
the removed pairs had a ratio of 1.21. That rise comes only from removing them.

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

`--cache DIR` points at existing clones; `--offline` refuses to clone.
`--source-root DIR` reads commit archives extracted under each checkout name, for
example `../23-representation-access/.cache/repos` after that study's `collect.py`,
and rests on the per-file SHA-256 check. The measurement takes about 20 seconds
after cloning.

The baseline reads those extracted archives by default, and runs through the
study's log:

```bash
python3 data/run_study.py 09-representation-dilation --expected 10 400 \
  --reason "..." -- .venv-dilation/bin/python measure_tree_baseline.py
```

Runs since 2026-11-02 are logged in `runs.jsonl`, with console output in `runs/`.
Attempts before the first logged run, `20261102T123025Z`, have no logs. That
includes the earlier runs named below, so how many attempts were made, and what
they produced, cannot be established.

Run records from dirty checkouts do not pin an exact code snapshot. The runs through
`20261102T141023Z` have `dirty: true` and carry no code hashes. Later records carry
`code_hashes` and `file_hashes_after`, which identify the scripts and outputs of that run. Each such record names the last commit
(`452495e09c44`) but not the uncommitted code that ran, and it hashes only the
outputs that changed, not the scripts or inputs. The file hashes that a run writes
can be compared with a rerun, but the record cannot show which code produced them.
These runs also used a scratch virtual environment, not one built from
`requirements.txt`: it holds numpy 2.5.4 where the file pins 2.5.3, on Python
3.14.4.

## Determinism check

The CSV carries no timestamps, and the bootstrap is seeded, so reruns must be
byte-identical. A non-default `--output` writes its summary beside that file,
which leaves the retained summary alone:

```bash
P=.venv-dilation/bin/python
S=data/studies/09-representation-dilation/measure_representation_dilation.py
$P $S --output /tmp/dil1.csv && $P $S --output /tmp/dil2.csv && cmp /tmp/dil1.csv /tmp/dil2.csv
```

On 2026-09-29 two runs on existing clones and a third from fresh clones produced
identical CSVs (SHA-256
`2d77341ee1a3f95c09f968d9687f25785ce111c1299a1c9fa001a2c6b393fdac`) and identical
summary files. On 2026-11-02 a logged run from study 23's extracted archives
reproduced the CSV hash; its summary differed only in the recorded Python version.

## Limits

- Distances are measured only over bound pairs. The unbound 2.8% is not
  evenly spread (Ibex holds 79% of it), and its cause is not established.
- Token distance depends on declaration style. The result describes these
  files as written, not RTL in general.
- The benchmark and production groups differ in size by construction, so the
  per-group slopes are the check that the trend is not produced by pooling.
- The file-level bootstrap describes resampling stability within this
  convenience corpus. Shared templates and related files are not independent
  draws from a wider population of hardware.
- Tree distances use the recoverable subset of token-distance pairs, not an
  exactly matched pair set.
- The measurement says nothing about whether any model's accuracy depends on
  this distance.
- Neither distance separates related from unrelated signals. Short tree paths
  are not evidence that a syntax tree exposes a connection.
- 16,392 of the 16,464 pairs in `bsg_scatter_gather.sv` lie in generate branches
  that the fixed parameter value of 4 does not select (study 23's diagnostic), and
  they are uses of five signals. The study counts source text, not elaborated
  hardware.
