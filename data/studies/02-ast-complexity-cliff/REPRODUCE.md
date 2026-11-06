# Reproducing the AST complexity measurement

This study reports a **6.7x** source-complexity gap between the reference RTL
shipped with AI hardware benchmarks and production-oriented open RTL. Everything
below regenerates that number from source. No result in this directory is typed
in by hand.

It replaces `hardware_ast_complexity_gap.csv`, which claimed 175x. That file was
never measured; its per-module values were literal tables inside its own
generator, and the upstream commits in its header were hand-typed placeholders.
It and its generator were deleted on 29 September 2026.

## What you need

| | |
| --- | --- |
| Python | 3.11 or newer (3.11.15 and 3.12.13 both verified) |
| git | any recent version, on `PATH` |
| Disk | about 400 MB for the cloned corpora |
| Network | first run only; later runs can use `--offline` |
| Time | about 3 minutes, dominated by cloning |

No container, no EDA tool, and no license. `pyslang` is a self-contained
SystemVerilog parser and is the only dependency the measurement needs.

## Run it

```bash
cd <repo root>

python3 -m venv .venv-ast
.venv-ast/bin/pip install -r data/studies/02-ast-complexity-cliff/requirements.txt

# 1. Measure. Clones six pinned repositories into a gitignored cache on first run.
.venv-ast/bin/python data/scrapers/mine_hardware_ast_complexity_real.py \
    --output-dir data/studies/02-ast-complexity-cliff

# 2. Redraw the figure, both where the study keeps it and where the book reads it.
.venv-ast/bin/python data/studies/02-ast-complexity-cliff/plot_ast_complexity_measured.py
.venv-ast/bin/python data/studies/02-ast-complexity-cliff/plot_ast_complexity_measured.py \
    --output-base book/contents/chapters/04-representations/images/fig-ch04-ast-complexity-cliff
```

Step 1 prints the per-corpus module counts as it goes. They are fixed by the
pinned commits, so they are the first thing to check:

```
VerilogEval: 156 files, 156 module declarations
RTLLM: 50 files, 61 module declarations
OpenTitan: 1137 files, 936 module declarations
CV32E40P: 126 files, 123 module declarations
VeeR EH1: 44 files, 112 module declarations
BlackParrot: 125 files, 125 module declarations
```

## What is pinned

The miner clones each repository and verifies the checked-out SHA before parsing.
A moved branch cannot silently change the result.

| Corpus | Role | Commit |
| --- | --- | --- |
| VerilogEval | AI benchmark reference RTL | `c498220d0a52248f8e3fdffe279075215bde2da6` |
| RTLLM | AI benchmark reference RTL | `51ed553d0ffd32797a1a0a13e051656bf302c81f` |
| OpenTitan | Production-oriented open RTL | `e3f3234aa3772760cdf40e79a8ae4471b6b02213` |
| CV32E40P | Production-oriented open RTL | `6033d2b1be3295ec774d17ac4cf226faacfdeb08` |
| VeeR EH1 | Production-oriented open RTL | `d04b1c7ae675a63dc4307cacfd10547ec937b928` |
| BlackParrot | Production-oriented open RTL | `f91010f654a5dfd00f83dbe25dbda482218d540b` |

Each output row additionally carries `source_path` and `source_sha256`, so any
single measurement can be traced back to the exact file that produced it.

## Check that it reproduced

```bash
.venv-ast/bin/python - <<'PY'
import json
d = json.load(open("data/studies/02-ast-complexity-cliff/"
                   "hardware_ast_complexity_measured_summary.json"))
r = d["module_weighted_ratios"]
assert round(r["median_concrete_syntax_node_ratio"], 3) == 6.696, r
assert round(r["median_clean_loc_ratio"], 3) == 6.188, r
assert round(d["corpus_balanced_sensitivity"]
              ["median_concrete_syntax_node_ratio"], 3) == 4.272
assert round(d["diagnostic_free_sensitivity"]["ratios"]
              ["median_concrete_syntax_node_ratio"], 3) == 4.770
print("reproduced:", d["execution"]["python_version"],
      "pyslang", d["execution"]["pyslang_version"])
PY
```

`hardware_ast_complexity_measured.csv` reproduces byte-for-byte across all 1,513
rows except `extraction_timestamp`, which records when the run happened. Verified
2026-09-03 on Python 3.11.15 against a run recorded under 3.12.13.

## The numbers this study supports

| Comparison | Benchmark | Production | Ratio |
| --- | ---: | ---: | ---: |
| Median concrete syntax nodes per module | 168 | 1,125 | 6.70x |
| Median clean lines of code per module | 16 | 99 | 6.19x |
| Median syntax nodes, diagnostic-free files only | 141.5 | 675 | 4.77x |
| Median syntax nodes, no substantive diagnostic | 168 | 675 | 4.02x |
| Median syntax nodes, repository include path | 168 | 1,440 | 8.57x |
| Median written tokens, plain or include-path parse | 90 | 602 | 6.69x |
| Median of repository syntax-node medians | 232 | 991 | 4.27x |

Modules parsed: 217 benchmark (VerilogEval 156, RTLLM 61) and 1,296 production
(OpenTitan 936, CV32E40P 123, VeeR EH1 112, BlackParrot 125).

The pooled 6.7x is a module-weighted figure over these six repositories. It is
not a universal ratio, and the sensitivity checks are reported alongside it
rather than behind it. The diagnostic-free row drops any file with a diagnostic
and requires a valid tree. The no-substantive-diagnostic row, which Chapter 4
prints, ignores only `DiagCode(NewlineEOF)`.

## Include-path sensitivity

The filters above remove files; they do not repair a parse. To see which way the
parse bias runs, `sensitivity_include_dirs.py` reparses every selected file with
all of that repository's HDL directories on the include path and writes
`hardware_ast_complexity_include_sensitivity.json`:

```bash
.venv-ast/bin/python data/studies/02-ast-complexity-cliff/sensitivity_include_dirs.py
```

Production-oriented modules in files with a substantive diagnostic fall from 703
to 378, and the pooled ratio rises from 6.70x to 8.57x (5.46x on modules still
free of substantive diagnostics). All 125 BlackParrot modules stay flagged
because the BaseJump files they include sit in a submodule outside the pinned
repository. Files still parse alone, with no predefined macros and no build-time
generated headers, so this is a direction and a size, not a clean parse.

The 8.57x is a preprocessed count: a repaired parse expands macro text into the
module, and those nodes count. Written tokens, located in the file and outside
any macro expansion, give 6.69x under both parses, so the rise is expansion
rather than more source. The primary measure is source syntax, so 8.57x is a
different quantity and not a corrected 6.70x.

Run log for the recorded result, 2026-11-02, Python 3.12, pyslang 11.0.0:

1. Failed. OpenTitan `hw/ip/tlul/rtl/tlul_adapter_shim.sv` failed the check
   against the primary CSV's SHA-256, because the first fetch stored the 32 HDL
   git symlinks under `hw/` as text files. No result was written.
2. Recorded. Symlinks restored; every primary file matched its SHA-256.

The written-token fields were added on the same date in a third run, logged in
`runs.jsonl` with its console output in `runs/`. Its node counts and diagnostics
equal run 2. The miner has no run log, so its attempts cannot be checked.

The run used `--archive-root` because `git` fetches over the network stalled:
commit archives for five repositories, and for OpenTitan the 3,973 HDL files
under `hw/` listed by the pinned commit's git tree, each checked against its git
blob hash. Rerun without that flag to use the miner's git checkouts.

## What this measurement does not establish

These boundaries are the reason the study is credible, so do not drop them when
citing it.

- `concrete_syntax_nodes` counts every element `pyslang` visits, so tokens count
  as leaves alongside interior nodes.
- It measures **source syntax**, not elaborated design. Files are parsed
  standalone with error recovery, not preprocessed or elaborated with a full
  include path.
- Parser diagnostics are retained rather than used to exclude macro-heavy
  production RTL, which would bias the comparison toward simple files. The
  diagnostic-free sensitivity check exists to show the size of that effect.
- Source-reference depth follows an instantiation only when the child module
  name has exactly one definition in the selected corpus. It is not elaborated
  instance depth or a bound on it: conditional branches can add inactive
  references, while unresolved children can shorten a path. Ambiguous cases
  are counted in their own column.
- Clock-event signal counts and CDC primitive mentions are **lexical
  indicators**. They are not verified clock domains and not verified crossings.
  No claim about asynchronous crossing counts follows from this data.
- The corpora are six repositories chosen for being public and pinnable, with no
  recorded sampling rule. Nothing here generalizes to closed commercial IP, and
  the 45% to 63% reference share describes these four repositories only.
- The reference share counts uniquely defined children, so it understates
  reference. BlackParrot's `bsg_` children sit outside the pinned repository, which
  makes its depth a lower estimate.
