# Notes, spec 01 offload break-even

## What I did
`compute.py` reads every `raw/run-<k>.csv` (5 current) and `raw/superseded-shared-wait/run-<k>.csv` (3 superseded), kept apart because run_ids 1-3 occur in both. It computes per-run and pooled medians with `statistics.median`, then the crossovers, launch ratios and superseded values. It writes `result.json`.

`medians.csv`, `summary.json` and `runs/` were not used and were not in my folder. Network: none.

## Result shape
`result.json` has `readings`, one entry per reading, each in the spec's full shape, plus `checks`. Fields added beyond the spec's shape: `ahead_ns`, `sustained_from_min/max`, `pooled_ahead_ns`, `*_grid_steps`, null counts, `launch_ratio_detail`. The spec says to report min and max of "the two values", while its JSON example shows only `first_ahead_*`, so I report both.

## Dropped
0 rows dropped, from all 8 files of 2976 rows each. Every run/arm/n cell has 31 rows; pooled cells have 155. All samples are odd, so no median averaged two values. No exact ties in any comparison. No nulls in any crossover.

## Ambiguities and readings
Four named readings, differing only in the launch-ratio fields:
- `spec_n_le_256`: as written.
- `lohi_all_grid`: median on n <= 256, lo/hi on every grid n, because the prose says "individual sizes within a run" with no restriction. The lo here falls below 1, at the top of the grid (run 3, n=3072).
- `small_n_le_192`, `small_n_le_384`: "small sizes" one grid step either side of the provenance cutoff, which I picked as the neighboring alternatives; applied to both median and lo/hi.

Others:
- First vs. sustained: every reading carries both. They differ in one place only: superseded run 3, copy pair, ahead at 768, behind at 1024, ahead from 1536. In all current runs they are equal.
- "Moved by a full step": `*_grid_steps` is the index distance between min and max. It is 1 for resident, copy and sixteen_await, 0 for one_launch.
- Launch ratio has no rounding rule; values are unrounded.
- I read "within a run" as a pooled range over all (run, n). Per-run ranges are also given in `launch_ratio_detail.per_run_lo_hi`, because the extreme lows come from few cells. Lowest cells at n <= 256: run 1 n=24, run 3 n=16, run 1 n=16; the next is run 5 n=256. So lo rests on small-n cells in runs 1 and 3, while the other three runs bottom out near 9 or above.
- `stable` is false if any run has a null first_ahead_n. This did not arise.

## Could not compute
Nothing in the spec. The provenance cutoff itself could not be checked, since `provenance.yml` is not in my folder; 256 is taken from the spec.

## Result values seen
The spec's prose has [VALUE] placeholders and showed no results. `raw/run-<k>.log` prints per-run medians to 4 significant figures. These are intermediate values, not the published ones. I used them only as a check after computing. The spec's ambiguity note describes the superseded copy pattern in words without numbers.

## Checks (not used for results)
`crosscheck.py` recomputes medians through awk and sort rather than the statistics module: 480 of 480 log medians match at 4 significant figures, and the lo/hi cells and values match. This is my own check, so it is not an independent audit.

Observation from `host.json`, not used: all five current runs were on battery (62% falling to 56%), all three superseded runs on AC power. Reps 31, warmup 5, batch 16, seeds 1001-1005 for current, and superseded seeds 1001-1003. Superseded runs were in the same morning, about two hours earlier.

## Incident outside my folder
A scratch line of mine, `cat > /tmp/x`, was left in a command by mistake. It hung on stdin until the 120 s timeout, and I stopped it. `/tmp/x` existed already (birth 2026-11-02 13:30:23, before this task), and the redirect truncated it to 0 bytes. Its previous content is lost and I do not know what it was or who owned it. This broke the rule to work only in my folder. I did not delete the now-empty file. No project inputs or results were affected.

## Runs
| Command | Elapsed | Outcome |
|---|---|---|
| `python3 compute.py` | 0.08 s | ok, first version |
| `python3 compute.py` after adding `per_run_lo_hi` | 0.06 s | ok |
| Inline cross-check with the stray `cat` | >120 s | hung, stopped; emptied `/tmp/x` |
| `timeout 60 python3 crosscheck.py` | 0.00 s | failed, rc 127, no `timeout` on macOS |
| `python3 crosscheck.py` | 0.20 s | ok |
| `python3 compute.py` | 0.05 s | ok, result.json sha256 87ba3ea0... unchanged |
