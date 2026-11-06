# Spec 10: H100 matched-workload floor and U-Net interval

## Claim
`book/contents/chapters/09-patterns/09-patterns.qmd:325`: "Between MLPerf Training v2.1 (November 2022) and v3.0 (June 2023), NVIDIA's submissions with eight H100-SXM5-80GB GPUs match on six workloads, comparing preview result 2.1-2091 with available results 3.0-2064 (BERT, RNN-T, Mask R-CNN, and RetinaNet) and 3.0-2062 (ResNet-50 and 3D U-Net). [...] Time-to-train ratios range from [VALUE]$\times$ for [VALUE] to [VALUE]$\times$ for [VALUE] [...]"

`book/contents/chapters/09-patterns/09-patterns.qmd:327` (caption): "Points divide MLPerf Training v2.1 preview times by v3.0 available times on eight H100-SXM5-80GB GPUs, and lines give 95% bootstrap intervals over runs within these submissions [...] The 3D U-Net interval [VALUE]. The ResNet-50 point excludes a scaling factor in its published v2.1 time."

`book/contents/chapters/09-patterns/09-patterns.qmd:333`: "The [VALUE]$\times$ ratio therefore has an interval of [VALUE]$\times$ to [VALUE]$\times$ [...] a [VALUE]$\times$ gain in time per epoch ([VALUE]$\times$ to [VALUE]$\times$). [...] The published v2.1 ResNet-50 time includes a [VALUE] scaling factor under MLPerf's convergence rules, and the v3.0 time includes none, so the figure divides unscaled times and reports [VALUE]$\times$ where the published minutes give [VALUE]$\times$."

## Raw inputs
Directory `book/contents/chapters/09-patterns/data/`.
- `mlperf-h100-runs.csv`. Skip `#` lines. Fields used: `round,result_id,workload,time_min,status,eval_count,last_eval_position,position_key`. The raw MLLOG files are not retained; each row's `repo,commit,git_blob_sha,log_sha256` allows a refetch from GitHub. Prefer refetching and re-extracting `run_stop - run_start`. If that fails, use this table and say so.
- `mlperf-h100-sources/results-v2.1-sheet.csv`, `results-v3.0-sheet.csv`: published minutes. Two header rows; the v3.0 sheet has an extra LLM column, so map columns by name.
- `mlperf-h100-sources/v2.1-resnet-scaling.json`: `scaling_factor`.
- Do not use `mlperf-h100-pairs.csv`, `mlperf-h100-spread.csv`, `mlperf-h100-hosts.csv`, or `fig-ch09-mlperf-software-dividend.csv`.

## Definitions
- Submission: one `(round, workload)` set of runs in the result IDs named above.
- Rule score with drop `k`: treat each non-success `status` as slower than every success (provenance rule), sort by `time_min`, drop `k` fastest and `k` slowest, and take the mean of the rest.
- Choice of `k`: for each submission, use the `k` whose score matches the published minutes at printed precision, multiplying by `scaling_factor` for v2.1 ResNet-50 only. Report `k`, score, and published minutes. If no `k` matches, stop on that workload and report it.
- Ratio: v2.1 rule score over v3.0 rule score, unscaled. For ResNet-50 also report published v2.1 minutes over published v3.0 minutes.
- `floor`: minimum ratio over the six workloads, with its workload. `ceiling`: the maximum, with its workload.
- Bootstrap: for each round independently, resample runs with replacement to the submission's run count, recompute the rule score, and form the ratio. Use 20000 draws, seed 20261102 (both from provenance), and the 2.5th and 97.5th percentiles. State the generator. Compute for all six workloads.
- `includes_no_gain`: the interval contains 1.
- Time per epoch for 3D U-Net: per run, `time_min / last_eval_position`, using converged runs. Aggregate and bootstrap as below.

## Expected output
```json
{
  "workloads": {"<workload>": {"k": 0, "n_v21": 0, "n_v30": 0, "score_v21": 0.0, "published_v21": 0.0, "score_v30": 0.0, "published_v30": 0.0, "ratio": 0.0, "ci_low": 0.0, "ci_high": 0.0, "includes_no_gain": false}},
  "resnet": {"scaling_factor": 0.0, "ratio_unscaled": 0.0, "ratio_published": 0.0},
  "floor": {"workload": "", "ratio": 0.0}, "ceiling": {"workload": "", "ratio": 0.0},
  "unet_time_per_epoch": {"aggregate": "", "ratio": 0.0, "ci_low": 0.0, "ci_high": 0.0},
  "bootstrap": {"draws": 0, "seed": 0, "rng": "", "method": ""}
}
```

## Tolerance
Rule scores against published minutes: the sheet's printed precision. Point ratios: 0.002, finer than the prose, since run times are fixed. `floor` workload and `k`: exact. Bootstrap bounds: 0.02, because a different generator or percentile convention shifts them by Monte Carlo error, and the U-Net distribution is wide. Time-per-epoch point and bounds: 0.01 and 0.02.

## Ambiguities
- The prose says the published time averages runs "after the rules discard the extremes" and gives no `k`. It may differ by workload. It is fitted here against the published minutes because those are independent of the logs.
- "95% bootstrap intervals" does not name percentile, BCa, or joint resampling. Provenance notes that a joint resample changed one pairwise verdict, so the method matters at the margin.
- Time per epoch has no stated aggregation. It may be the rule score over kept runs, a mean over all converged runs, or a ratio of mean time to mean epochs. Implementers must name their choice in `aggregate`. Provenance adds only that the last logged eval is taken as convergence.
- "Floor" is not a word in the prose. It is read as the smallest of the six point ratios.
- Non-converged runs: the rule that they count as slowest is in provenance, not in the prose.
- `mlperf-h100-runs.csv` is itself an extraction, so without a refetch this test cannot detect a parsing error in it.
