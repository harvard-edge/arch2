# Spec 09: Kernel gain against the torch.compile baseline

## Claim
`book/contents/chapters/03-lifecycle/03-lifecycle.qmd:178` (caption): "(a) matrix–vector multiplication per-round best time (dashed line) and lowest recorded time so far (solid step curve), which falls [VALUE]$\times$ from Round 1 to Round [VALUE]; and (b) lowest recorded time relative to Round 1, where RMSNorm stays nearly flat."

`book/contents/chapters/03-lifecycle/03-lifecycle.qmd:182`: "Against `torch.compile`, the PyTorch compiler that the source uses as its baseline [...], the matrix–vector input kernel starts [VALUE]$\times$ slower and the search's Round 1 output is still [VALUE]$\times$ slower, so most of its [VALUE]$\times$ gain recovers ground the generated kernel started behind, and its final kernel ends [VALUE]$\times$ faster. RMSNorm's input kernel already runs ahead of `torch.compile`, and its final kernel ends [VALUE]$\times$ faster, so the nearly flat curve hides the larger gain over that baseline."

`book/contents/chapters/07-feedback/07-feedback.qmd:640` (caption): "Timings carry no reported uncertainty, so RMSNorm, at [VALUE] of Round 1 time, is not an established gain."

`book/contents/chapters/07-feedback/07-feedback.qmd:642`: "[...] matrix–vector multiplication lowers execution time from [VALUE]\ ms to [VALUE]\ ms while raising achieved warp occupancy from [VALUE]% to [VALUE]% and DRAM throughput from [VALUE]% to [VALUE]%. In MaxPool 3D, by contrast, the fastest retained round cuts execution time from [VALUE]\ ms to [VALUE]\ ms ([VALUE] of Round 1 time) while achieved occupancy falls from [VALUE]% to [VALUE]% and DRAM throughput rises from [VALUE]% to [VALUE]%; in 3D transposed convolution, occupancy similarly drops from [VALUE]% to [VALUE]% as latency nearly halves."

## Raw inputs
- `data/studies/10-kernelagent-search/raw/<task>/optimization_trace/round_<r>/benchmark_results.json`: `kernels.<key>.time_ms`, one kernel per file, for every round.
- `.../round_<r>/optimized_ncu_metrics.json`: `metrics.<kernel>.<field>`.
- `data/studies/10-kernelagent-search/raw/README.md`: the only record of `torch.compile` and input-kernel times, and of the source's best and speedup, per task section.
- Do not use `timings.csv`, `attempts.csv`, `summary.json`, `readme_crosscheck.json`, or `data/studies/11-kernelagent-feedback/paired_metrics.csv`. No Python file is needed.

## Definitions
- `T(task, r)`: `time_ms` for round `r`. `T_best`: min over rounds, with `r_best` its round; a tie takes the earliest round. `T_R1`: Round 1.
- `T_tc`, `T_in`: the README's `torch.compile` and input-kernel times.
- `T_final_records`: `T_best`. `T_final_readme`: the README's bold best time.
- Matrix–vector: `input_over_tc = T_in/T_tc`; `r1_over_tc = T_R1/T_tc`; `search_gain = T_R1/T_best`; `final_speedup = T_tc/T_final`, under both `T_final` forms.
- RMSNorm: `input_over_tc`; `final_speedup` under both forms; `lowest_over_r1 = T_best/T_R1`; `input_ahead_of_tc = T_in < T_tc`.
- Every task: `T_R1`, `T_best`, `r_best`, `lowest_over_r1`.
- Occupancy and DRAM at Round 1 and at `r_best`, for matrix–vector, MaxPool 3D, and 3D transposed convolution: from `optimized_ncu_metrics.json`. Each file holds one kernel key.
- `occupancy_falls`: occupancy at `r_best` is below that at Round 1.

## Expected output
```json
{
  "tasks": {"<task>": {"t_tc": 0.0, "t_in": 0.0, "t_r1": 0.0, "t_best": 0.0, "r_best": 0, "t_final_readme": 0.0,
    "input_over_tc": 0.0, "r1_over_tc": 0.0, "search_gain": 0.0, "lowest_over_r1": 0.0,
    "final_speedup_records": 0.0, "final_speedup_readme": 0.0, "input_ahead_of_tc": false,
    "readme_over_records_best": 0.0,
    "profile": {"occupancy_field": "", "dram_field": "", "occupancy_r1": 0.0, "occupancy_best": 0.0, "dram_r1": 0.0, "dram_best": 0.0, "occupancy_falls": false}}}
}
```

## Tolerance
Times read from a record: exact to the digits printed. Ratios: 0.005, the half-unit of a two-decimal ratio. README times have three decimals, so ratios built on them carry roughly this error. Percent fields: 0.01 points, as they are read from fixed fields.

## Ambiguities
- "Final kernel" is not defined. It may be the lowest per-round record, the source's bold README time, or the file `optimized_kernel_beam_search.py`. The study README says these differ for RMSNorm's round. Report both numeric forms; neither is asserted. The kernel file has no timing of its own.
- The baseline and the records may come from different procedures. `torch.compile` and input times exist only in the README, and the book says that README and per-round records disagree for some tasks. The prose divides across these two sets without saying whether that is safe.
- The input time could also be read from Round 1 prompt text in `opt_prompt.txt`, which reports a starting time per worker. The prose does not say which. This spec uses the README because the prose attributes the baseline to the source's table.
- The fields for "achieved warp occupancy" and "DRAM throughput" are not named. The candidates are `sm__warps_active.avg.pct_of_peak_sustained_active`, and `dram__throughput.avg.pct_of_peak_sustained_elapsed` or `gpu__dram_throughput.avg.pct_of_peak_sustained_elapsed`. State the fields used. `raw/README.md` prints labelled values that can settle the choice.
- The profiles carry no hash binding them to the timed kernel, as the prose notes.
- "Fastest retained round" and "lowest recorded" are used as one quantity, read here as `T_best`.
