# Spec 01: Offload break-even crossovers

## Claim
`book/contents/chapters/02-pressures/02-pressures.qmd:335`: "Across [VALUE] consecutive runs in one session, a single $n \times n$ product first beat the host at $n$ between [VALUE] with its operands already on the GPU and between [VALUE] with copies in and out. Batching lowered the break-even. Sixteen products beat the host at $n$ between [VALUE] when the program waited for each launch, and at [VALUE] as one launch."

`book/contents/chapters/02-pressures/02-pressures.qmd:339`: "At small sizes, waiting on sixteen launches costs about [VALUE] times as much as one launch in the pooled medians, and between [VALUE] and [VALUE] times at individual sizes within a run. The one-launch crossover held across these runs, whereas the others moved by a full step of the size grid [...] Three earlier runs [...] crossed at [VALUE] with resident operands. With copies, one of them led the host at [VALUE], fell behind at [VALUE], and led again from [VALUE]. The one-launch crossover stayed at [VALUE] in those runs as well."

## Raw inputs
- `data/studies/27-offload-break-even/raw/run-<k>.csv`, every `k`. Columns: `run_id,n,panel,arm,arm_order,rep,seconds`.
- `data/studies/27-offload-break-even/raw/superseded-shared-wait/run-<k>.csv`, every `k`, same columns. Use only for the "earlier runs" values.
- Do not use `medians.csv`, `summary.json`, or `runs/`.

## Definitions
- Arm pairs: resident is `mps_resident` against `cpu_single`. Copy is `mps_copy` against `cpu_single`. Sixteen-await is `mps_16_launch` against `cpu_bmm`. One-launch is `mps_bmm` against `cpu_bmm`.
- Per-run median: median of `seconds` over all rows for one `(run_id, arm, n)`.
- Pooled median: median of `seconds` over all rows of the current (non-superseded) runs for one `(arm, n)`.
- Ahead at `n`: the GPU-arm median is strictly below the host-arm median. An exact tie is not ahead.
- `first_ahead_n`: smallest grid `n` at which a run is ahead. Null if none.
- `sustained_from_n`: smallest grid `n` such that the run is ahead at it and at every larger grid `n`. Null if none.
- For each pair, report the two values per run, their min and max across current runs, and the same two values on pooled medians.
- `stable`: all current runs share one `first_ahead_n` and in each run `first_ahead_n == sustained_from_n`.
- Launch ratio at `n`: `mps_16_launch` median over `mps_bmm` median, for `n <= 256` (cutoff from the study's `provenance.yml`).
- `launch_ratio_pooled`: median, across those `n`, of the ratio on pooled medians.
- `launch_ratio_lo`, `launch_ratio_hi`: min and max of the ratio over all `(current run, n <= 256)` pairs, on per-run medians.
- Superseded runs: report `first_ahead_n` and `sustained_from_n` per run for all four pairs, and for the copy pair the ascending list of `n` at which each run is ahead.
- Report ratios unrounded. Medians of an even sample average the two middle values.

## Expected output
```json
{
  "n_current_runs": 0,
  "pairs": {"<resident|copy|sixteen_await|one_launch>": {
    "per_run": {"<run_id>": {"first_ahead_n": 0, "sustained_from_n": 0}},
    "first_ahead_min": 0, "first_ahead_max": 0,
    "pooled_first_ahead_n": 0, "pooled_sustained_from_n": 0, "stable": false}},
  "launch_ratio_pooled": 0.0, "launch_ratio_lo": 0.0, "launch_ratio_hi": 0.0,
  "superseded": {"<run_id>": {"pairs": {"<pair>": {"first_ahead_n": 0, "sustained_from_n": 0}}, "copy_ahead_ns": [0]}}
}
```

## Tolerance
Grid sizes and booleans: exact, because they are discrete and the medians are deterministic given the raw rows. Ratios: relative 0.1 percent, which allows only floating-point and median-convention differences. Any larger gap is an analysis difference, since no sampling enters.

## Ambiguities
- "First beat" does not say whether a run that leads and then falls behind counts at its first lead. The provenance rule says first `n` with a separate stays-ahead flag, and the superseded copy sentence treats the two as different. Report both. The agreement test applies to whichever the prose used, which is not stated.
- "Small sizes" is undefined in the prose. The `n <= 256` cutoff comes only from provenance.
- "At individual sizes within a run" is defined nowhere. The restriction to `n <= 256` for the lo and hi values is an assumption, and the provenance record lists only the median summary.
- The prose gives no rounding rule for the launch ratios.
- "Moved by a full step of the size grid" has no stated test. It is read here as adjacent grid points for the min and max.
