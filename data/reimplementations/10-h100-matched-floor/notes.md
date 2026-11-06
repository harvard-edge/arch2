# Spec 10 notes: H100 matched-workload floor and U-Net interval

## What I did
- `compute.py` refetched all 150 raw MLLOG files by git blob SHA through `gh api repos/mlcommons/<repo>/git/blobs/<sha>`. The owner `mlcommons` comes from the URLs in provenance.yml. Every file passed both the git blob SHA check and the `log_sha256` check. The logs are cached in `logs/` (150 files, 20,351,684 bytes), named by sha256.
- I re-extracted `run_stop - run_start` in ms, plus status, eval count, last eval value and position, and log size. All times in `result.json` come from the logs (`time_source: refetched_logs`), at full precision.
- Field comparison against `mlperf-h100-runs.csv`: 0 mismatches over 150 rows. Each log has exactly one run_start and one run_stop; 0 malformed MLLOG lines; 0 evals without a position. So the table's extraction shows no parsing error for these fields. `ratio_from_table_times` recomputes the ratios from the table's rounded times; they differ only past the sixth decimal.
- Published minutes come from the two sheets, mapped by task-column name. k was fitted per round by comparing the score (scaled for v2.1 ResNet-50 only) printed to the sheet's 3 decimals with the sheet's string.
- Draws (20000) and seed (20261102) are parsed from provenance.yml, not typed in.
- Generator: Python 3.14.4 `random.Random` (MT19937), stdlib, because numpy is not installed. Each draw family restarts the stream at the seed and walks the workloads in a fixed order; v2.1 is drawn before v3.0.
- `result.json` runs twice gave identical content apart from `elapsed_s`.

## Point results (same in all readings unless noted)
| Workload | k | n | v2.1 score / published | v3.0 score / published | Ratio |
|---|---|---|---|---|---|
| ResNet-50 v1.5 | 1 (v3.0 tie 1,2) | 5/5 | 14.684 (x factor = 14.746) | 13.601 / 13.601 | 1.079625 (k=2 in v3.0: 1.079616) |
| 3D U-Net | 4 | 40/40 | 13.1006 / 13.101 | 12.1034 / 12.103 | 1.082393 |
| RetinaNet | 1 | 5/5 | 38.0501 / 38.050 | 37.0092 / 37.009 | 1.028125 |
| Mask R-CNN | 1 | 5/5 | 20.3481 / 20.348 | 19.1798 / 19.180 | 1.060913 |
| RNN-T | 1 (v3.0 tie 1,2) | 10/10 | 18.2018 / 18.202 | 16.6862 / 16.686 | 1.090826 (k=2 in v3.0: 1.090814) |
| BERT | 1 | 10/10 | 6.3780 / 6.378 | 5.4688 / 5.469 | 1.166252 |

- Floor: RetinaNet 1.028125. Ceiling: BERT 1.166252. Same workloads in all 30 readings.
- ResNet-50: scaling factor 1.0042232277526395; unscaled 1.0796; published minutes 1.0842.
- All 12 published times matched at least one k. No workload stopped.
- 3D U-Net interval contains 1 in all 30 readings (about 0.93 to 1.26 percentile, independent draws).
- U-Net time per epoch: 1.0308 to 1.0318 depending on aggregate, with intervals about 1.018 to 1.045.

## Ambiguities and readings (30 full entries in `result.json`, named `<k tie>__<method>__<aborted>`)
1. **k tie, not named in the spec.** v3.0 ResNet-50 and v3.0 RNN-T each match at both k=1 and k=2 at printed precision. The spec only says to stop when no k matches. Readings: `k_tie_smallest` (k=1, equal across rounds) and `k_tie_largest` (k=2 in v3.0, `k` is then an object). Point ratios move by about 0.00001; ResNet-50's bootstrap low moves from about 1.041 to 1.024.
2. **Interval method.** `percentile_linear_independent`, `percentile_lower_rank_independent` (order statistic at floor(N*p)), `bca_independent` (two-sample jackknife acceleration, ties at theta count half), `percentile_linear_joint_paired_index` (same indices in both rounds), `percentile_linear_joint_pooled_rounds` (pool both rounds, draw the total, split by round; a draw with too few runs for k is unusable and counted in `draw_counts`, up to 2,200 of 20,000 for n=5). A resample that spans workloads would leave each workload's marginal interval unchanged, so I did not add it.
3. **A non-success run retained in a draw, not named in the spec.** With k=1, a resample holding two or more copies of an aborted run keeps one after the drops. About 26% of draws do this for BERT v2.1, ResNet-50 v3.0, and Mask R-CNN v3.0. Readings: `retain_time` (its time_min enters the mean), `dnf_infinite` (score is infinite, so the ratio is inf or 0; emitted as the string "inf"), `exclude_draw` (draw removed, counted). **This changes verdicts.**
   - `exclude_draw` (10 readings): only 3D U-Net includes 1. Mask R-CNN interval about 1.06 to 1.064.
   - `retain_time` (10 readings): 3D U-Net and Mask R-CNN include 1. Mask R-CNN low about 0.60 to 0.63, because that aborted run's time is long.
   - `dnf_infinite` (10 readings): 3D U-Net, Mask R-CNN, and in 9 of 10 ResNet-50 include 1, with lows of 0.0; BERT's high is inf. The tenth is `k_tie_largest__bca_independent__dnf_infinite` (see below).
   The spec's rule fixes the rank, not this case, so a comparison on `includes_no_gain` depends on the other side's choice.
4. **Time per epoch.** Five aggregates, listed in each reading's `unet_time_per_epoch` as a list rather than one object: `rule_score_on_time_per_epoch`, `mean_time_per_epoch_of_runs_kept_by_time_rule`, `mean_time_per_epoch_all_converged`, `mean_time_over_mean_epochs_all_converged`, `mean_time_over_mean_epochs_runs_kept_by_time_rule`. All 80 U-Net runs converged, so 0 were excluded. Bootstrap streams restart at the seed for each aggregate.
5. **Floor** is the smallest of six point ratios, as the spec says. No alternative applies.

## Could not compute
- BCa for ResNet-50 under `k_tie_largest` (3 readings): k=2 of 5 leaves no run after a leave-one-out, so the jackknife acceleration is undefined. `ci_low`, `ci_high`, `includes_no_gain` are null with `ci_note`. No stand-in used.
- Everything else computed.

## Dropped
- Runs: 0 dropped of 150; 0 outside the named submissions. The 3 non-success runs stay in the data and rank slowest.
- Draws: only those counted in `draw_counts` per reading and workload.

## Spec and input discrepancies
- Each sheet has three header rows (task, then dataset), not two as the spec says. Mapping by task name is unaffected.
- The sheets name tasks, not models. The workload-to-task map in `compute.py` is my own, and the dataset row (ImageNet, KiTS19, OpenImages, COCO, LibriSpeech, Wikipedia) is consistent with it.
- Mask R-CNN `eval_accuracy` values are dicts; compared to the table as their Python repr.

## Result values seen
provenance.yml, which I read for the non-success rule, seed, and draws, states result values: ratios 1.03x to 1.17x, published ResNet ratio 1.084 and unscaled 1.080, an old floor of 1.08x, a RetinaNet gain of 2.8%, BERT as the largest ratio, the U-Net interval crossing 1 with a smaller time-per-epoch gain, and 8 of 15 pairs separating. I did not aim at them. The forbidden derived CSVs were not opened.

## Runs (from this folder)
| # | Command | Elapsed | Outcome |
|---|---|---|---|
| 0 | `gh api` one blob, manual format check | 2.3 s | OK |
| 1 | `python3 compute.py` | 0.04 s | SyntaxError in my code |
| 2 | `python3 compute.py` | 66.2 s | Fetched all logs, then TypeError: Mask R-CNN eval value is a dict |
| 3 | `python3 compute.py` | 0.12 s | ValueError in my dict comparison |
| 4 | `python3 compute.py` | 5.5 s | Completed, but my code stopped ResNet-50 and RNN-T on a k tie; replaced by tie readings |
| 5 | `python3 compute.py` | 4.0 s | ZeroDivisionError: jackknife at k=2 of 5 |
| 6 | `python3 compute.py` | 9.3 s | OK, 30 readings |
| 7 | `python3 compute.py` | 9.1 s | OK, identical to run 6 apart from `elapsed_s` |

Runs 3 to 7 used the cached logs and re-verified both hashes.
