# Spec 09 notes

All values below are copied from `result.json` (measured = source records and README text; ratios computed by `compute.py`). I ran no kernels.

## What I did
`compute.py` reads the 40 `benchmark_results.json` and 80 NCU files (5 tasks, 8 rounds each) and parses `raw/README.md` by regex, matching task folders to README sections by numeric prefix. Round number comes from the folder name. Every field is computed for all five tasks; the spec requires profiles and `r1_over_tc`/`search_gain` for fewer. `result.json` holds `readings.<name>.tasks.<task>` in the spec's shape, plus `dropped` and `diagnostics`. Ratios are unrounded.

No fetches. The spec gave no hashes, so nothing was hash-checked. I read only files in my folder. I did not open `timings.csv`, `attempts.csv`, `summary.json`, `readme_crosscheck.json`, or `paired_metrics.csv`; none are in `inputs/`. `input_ncu_metrics.json` and `opt_prompt.txt` are in `inputs/`; they feed only non-base readings and diagnostics.

## Result values seen
The README prints best times, stated speedups (1.06x, 2.31x, 3.39x, 2.56x, 2.95x), and labelled input-to-optimized NCU values, and it is a required input. Those may equal published [VALUE]s. I did not aim at any book figure; the spec's values are blanked and I saw no book text beyond the spec.

## Readings (7, one change from base each)
| Name | Change |
|---|---|
| `base` | Spec default; DRAM field `dram__throughput...` |
| `dram_gpu_field` | DRAM field `gpu__dram_throughput...` |
| `t_in_prompt_round2` | T_in = start time of the Round 1 worker that ended at T_R1 |
| `t_in_prompt_round2_median` | T_in = median of the four worker starts |
| `readme_example_output` | T_tc, T_in, T_final_readme from README example benchmark block |
| `profile_start_input_kernel` | Profile start from Round 1 `input_ncu_metrics.json` |
| `readme_round_table` | T_R1, T_best, r_best from README running-best table |

`final_speedup_records` and `final_speedup_readme` are both in every reading, per the spec. The `readme_round_table` reading is my addition, as is the input-kernel profile start; the spec's definitions alone give `base`.

## Dropped: 3
`readme_example_output` for tasks 43, 77, 82: the block elides them (`...`), so their README-derived fields are null there. Nothing else dropped: 40/40 rounds parsed, each with exactly one kernel key and one profile key, no ties at best.

## Could not compute as described
The spec says Round 1 `opt_prompt.txt` reports a starting time per worker. It does not: 0 `**Performance**` lines in all five Round 1 prompts. The per-worker pairs are in the Round 2 prompts, which is what the two prompt readings use. Nothing else failed.

## Ambiguities and findings
- Final kernel: differs for matrix-vector (r8 1.9516 vs README 1.956) and RMSNorm (r8 3.5139 vs README r3 3.525). The kernel file is not in `inputs/` and has no timing.
- RMSNorm's README says best is round 3, yet its "optimized" DRAM 89.5% matches round 8 (89.48), not round 3 (86.92). So the README's own section mixes rounds. `base` r_best is 8; `readme_round_table` r_best is 3, and `occupancy_falls` flips between them (true vs false).
- **Task 77 mixes runs.** README times exceed the trace by a nearly constant factor: Round 1 1.4448, best 1.4451, input vs prompt start 1.4445. Tasks 04, 43, 82 sit within 0.3% at Round 1 and best, and RMSNorm within 0.5%. So for 77 the README and trace look like different measurement bases, and `base` ratios that divide T_tc (README) by a trace time are not like-for-like: `final_speedup_records` 3.7052 vs `final_speedup_readme` 2.5639, `r1_over_tc` 0.5122 vs 0.74. `input_ahead_of_tc` also flips: false with README 28.7, true with prompt 19.87 (t_tc 20.052). This is the case the spec's second ambiguity asks about, and division across the two sets is unsafe here. Whether 77 appears in the book's ratio prose I cannot tell; the spec uses only its occupancy and "nearly halves".
- `lowest_over_r1` and `search_gain` for 77 are stable across bases (0.5269 vs 0.5271) since they stay within one set.
- RMSNorm worker starts: three near 5.33, one 7.4809, and that one is the worker that ended at T_R1. README's 5.461 matches none. Hence `input_over_tc` 0.6713 (README), 0.6551 (median), 0.9196 (matching worker). All three keep input ahead of `torch.compile`.
- Matrix-vector `input_over_tc`: 4.5964, 4.5973, 4.6049, 4.5969; `readme_example_output` shows T_in 9.511 vs section 9.510.
- DRAM field: the two candidates are equal in all 80 files, so the choice cannot change a value and README labels cannot separate them (`dram_field_files_differing` = 0).
- Occupancy field: `sm__warps_active...` matches README "Occupancy" labels at input and optimized for tasks 04 and 82 to README rounding (6.25 vs 6.2 is the loosest).
- Profile start: "Round 1" as the spec defines it is the Round 1 output (matrix-vector 24.24% occupancy, 25.77% DRAM). README's "input" column is the input kernel (6.25%, 18.48%). Both are reported.
- `occupancy_falls`: matrix-vector false, MaxPool true (73.29 to 57.18), 77 true (24.93 to 12.48), in `base`. With the input-kernel start the signs are unchanged for those three.
- Binding: worker and round in the benchmark path match the profile's `kernel_file` path in 40/40, which is path agreement only, not a hash. Each round's records come from one of four workers, per the README, so T_best is the minimum over retained workers. The kernel key is `kernel_round_1` and `round_num` is 1 in every folder; I used the folder and confirmed it against `r<N>` in the path.
- `opt_prompt.txt` mtimes (12:50) are later than the other files (11:06). I do not know why.

## Runs
| Command | Elapsed | Outcome |
|---|---|---|
| `python3 ../../../../_peek.py` from `raw/` (scratch look at data) | under 1 s | failed, wrong relative path |
| `python3 $B/_peek.py` (scratch, since deleted) | under 1 s | ok; printed per-round times and profile fields |
| `python3 compute.py` (6 readings) | 0.06 s | ok, tasks=5 dropped=3 |
| `/usr/bin/time -p python3 compute.py` (7 readings, median added) | 0.03 s | ok, tasks=5 readings=7 dropped=3 |
