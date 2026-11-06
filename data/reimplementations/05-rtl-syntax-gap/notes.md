# Spec 05 notes

## What I did
- `compute.py` (standard library only) computes every CSV metric from
  `hardware_ast_complexity_measured.csv` and writes `result.json`.
- `reparse.py` fetches nothing. It parses the CSV's files at the recorded commits with
  pyslang 11.0.0 and writes `include_reparse.json` and `include_reparse_modules.csv`
  (per-module node counts for every include configuration). `compute.py` merges these.
- `tools/fetch.sh`, `tools/fetch2.sh` fetched the repositories into `fetched/<repo>`.

Rerun: `python3 -I compute.py` from this folder; for the reparse first
`.venv/bin/python -I reparse.py`.

No result value appeared in the spec, the column notes, or the inputs (the spec's are
`[VALUE]`). The forbidden summary and sensitivity JSONs are not in this folder and were not
read. `inputs/data/scrapers/` is empty.

Status of numbers: CSV metrics are computed from the study's own measured table. Include
ratios are measured here; receipts are `include_reparse_modules.csv` and
`include_reparse.json`. This session produced them, so they are not independently verified.

## Dropped
- CSV rows: 0 of 1,513.
- Reparse files: 0 of 1,419 CSV-named files. Every file was present at its commit and matched
  `source_sha256`.
- Reparse declarations: 1 per configuration, an empty-named module declaration recovered from
  a parse error in VeeR `design/lib/beh_lib.sv`. The CSV has no empty names, and this module
  is the only baseline extra, so I drop it in all configurations.

## Counter check (baseline, no added include directories)
1,513 of 1,513 CSV modules reproduced `concrete_syntax_nodes` exactly, none missing, none
extra after the drop above. File-level diagnostic code sets also matched the CSV for all
1,419 files. Counter: `node.visit` on each `ModuleDeclaration`, counting every callback,
which includes tokens and Placeholder tokens. So for the node column the spec's caveat that
a parser or miner error cannot be detected is narrowed: this counter, written from the column
description, agrees. It does not test the miner's file selection or the hierarchy columns.

## Ambiguities and readings
1. Any vs substantive diagnostic: `production_any_diagnostic_pct`,
   `production_substantive_diagnostic_pct`. They are equal: no production row has
   NewlineEOF as its only code (all 44 such rows are benchmark).
2. Filter and `syntax_tree_valid`: `filtered_ratio` (no substantive diagnostic) and
   `filtered_ratio_valid_tree_only` (that, and valid tree). They are equal: all 27 invalid-tree
   rows already fail the substantive test. The key name could also mean a valid-tree filter
   alone, which ignores diagnostics; that is
   `additional_readings.filtered_ratio_valid_tree_alone_diagnostics_ignored`.
   The spec says filter both groups; a production-only form is also reported and is equal,
   because the one benchmark row removed does not move the benchmark median.
3. VeeR library files: ranked by module count, as the spec assumes. Top two are 41 and 24, next
   is 3, so there is no tie. Whether they are library files I take from the `design/lib/` path.
4. Reference: `reference_share_pct` (resolved > 0) and `instantiating_share_pct`
   (`hierarchy_instantiation_count` > 0). The production ranges of both are in
   `additional_readings`.
5. Include path, 7 configurations (`include_path_readings`), each with two module sets. The
   `all_reparsed` set is every named module found; `csv_matched` joins to CSV keys. The sets are
   identical in every configuration (no module gained or lost).
   - `baseline`: no directories. 6.6964, equal to `pooled_ratio`.
   - `csv_source_dirs`: parent directories of CSV files. 7.2321.
   - `all_hdl_dirs`: every directory directly holding .v/.sv/.vh/.svh. 8.5714.
     Declared in `reparse.py` as primary before any parse ran; this is `include_path_ratio`.
   - `all_hdl_dirs_reverse_order`: same, reversed search order. 8.5714.
   - `all_hdl_dirs_no_verification`: excludes directories under dv, tb, test, tests, testbench,
     testbenches, sim, verification, bench. 8.5714.
   - `csv_source_dirs_plus_demanded`, `all_hdl_dirs_plus_demanded`: adds any directory that
     satisfies an include still unopened, repeating until none can be added. 8.5714 both.
   The benchmark median stays 168 throughout. Production median 1,125 becomes 1,215 or 1,440.
   BlackParrot's median goes 1,520 to 4,902 once its header directories are searched.

## Could not compute / limits
- BlackParrot: all 125 files still fail an include in every configuration. Unopened:
  `bsg_defines.sv`, `bsg_noc_links.svh`, `bsg_wormhole_router.svh`, `bsg_cache.svh`,
  `HardFloat_consts.vi`, `HardFloat_specialize.vi`. None is in the tree at the commit; they
  come from the git submodules `external/basejump_stl` and `external/HardFloat`, which the spec
  does not name. I did not fetch them, so every include ratio here has BlackParrot partly
  repaired. A ratio with those submodules present was not computed.
- VeeR: `pic_map_auto.h` is not in the tree at the commit (1 file). 26 to 28 VeeR files keep
  unknown directives, and 42 OpenTitan files do in the fuller rules.
- File selection: the CSV names only files that yielded a module, 1,419 against 1,638 selected in
  the sources table (OpenTitan 927 of 1,137, CV32E40P 118 of 126, VeeR 43 of 44, others all).
  The other 219 files were not reparsed. A file that gains a module only under include paths
  would be missed.
- Include preprocessing is per file: no macro state is shared across files and no defines are
  passed. A miner run may differ on this, and that difference would change the node counts.
- `syntax_tree_valid` and the hierarchy columns were not recomputed; only node counts and
  diagnostic codes were compared to the CSV.

## Fetch
- Permitted fetch of six repositories, about 14 minutes of elapsed time in all, under the 30
  minute limit. The link ran near 65 KB/s.
- Attempt 1, full shallow (`tools/fetch.sh`): VerilogEval 22 s, RTLLM 85 s. OpenTitan stopped by
  me at about 9.5 minutes, 21 MB received of a repository GitHub lists at about 232 MB.
- Attempt 2, partial (`tools/fetch2.sh`): `--depth 1 --filter=blob:none` with sparse checkout of
  `*.v *.sv *.vh *.svh *.inc *.svi .gitmodules`. OpenTitan 151 s, CV32E40P 6 s, VeeR 4 s,
  BlackParrot 6 s. HEAD equals the recorded SHA for all four. The `fatal: early EOF` line in
  `fetch.log` comes from stopping attempt 1.
- A first reparse missed VeeR `design/include/global.h` and `build.h`, which my sparse pattern
  excluded. I added `*.h` for VeeR only, after which `all_hdl_dirs` moved from 8.5476 to 8.5714.
  The primary rule was not changed. OpenTitan, CV32E40P and BlackParrot `.h` files were not
  fetched; the demand closure reports the only unopened headers, and the ones listed above were
  checked against `git ls-tree`.

## Runs
| Command | Elapsed | Outcome |
| :--- | :--- | :--- |
| `python3 -I tools/profile_csv.py` | under 1 s | ok |
| `python3 -I compute.py` (CSV stage) | 0.03 s | ok |
| `python3 -m venv .venv; pip install pyslang==11.0.0` | 2.2 s for pip | ok |
| `bash tools/fetch.sh` | about 10 min | stopped by me during OpenTitan, exit 144 |
| shell wait loop on `fetch.log` | seconds | failed, exit 1, my loop was wrong; no effect on data |
| `bash tools/fetch2.sh` | about 2.8 min | ok |
| counter check on VerilogEval and RTLLM (scratch script, since removed) | seconds | 217 of 217 |
| `.venv/bin/python -I reparse.py` run 1 | 67.1 s | ok, 1 empty-named extra found |
| same, run 2, after empty-name drop and header logging | 67.9 s | ok, VeeR headers found missing |
| `git sparse-checkout add '*.h'` in VeeR | seconds | ok |
| same, run 3, with demanded configurations | 141.3 s | ok, final |
| `python3 -I compute.py` (final) | 0.03 s | ok |
