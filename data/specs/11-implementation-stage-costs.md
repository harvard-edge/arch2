# Spec 11: Implementation stage costs

## Claim
`book/contents/chapters/06-environments/06-environments.qmd:417` (caption): "(a) Individual flow steps in one LibreLane implementation run of the `spm` design on the IHP SG13G2 130\ nm BiCMOS PDK [...], where [VALUE] outer steps total [VALUE]\ s and OpenROAD detailed routing takes [VALUE]\ s. (b) Three nested boundaries for the same run: summed steps ([VALUE]\ s), the `Run Test` job step ([VALUE]\ s), and the full continuous-integration job ([VALUE]\ s)."

`book/contents/chapters/06-environments/06-environments.qmd:419`: "In this LibreLane run, the [VALUE] flow steps, led by OpenROAD detailed routing and followed by Magic LEF generation and streamout and then KLayout and Magic DRC, total [VALUE]\ s. The enclosing `Run Test` job step takes [VALUE]\ s; runner preparation, repository checkout, Nix store and PDK cache restores, and artifact upload bring the full continuous-integration job to [VALUE]\ s, or [VALUE] times the summed steps."

## Raw inputs
Directory `data/studies/20-implementation-stage-costs/raw/`.
- `run-records-subset.tar.gz`: all `runtime.txt` files in the artifact, exact bytes. Format `HH:MM:SS.mmm`.
- `design-job.json`: GitHub job record with `started_at`, `completed_at`, and `steps[]` holding `name`, `number`, `started_at`, `completed_at`.
- `job-113223652131.log.gz`: complete job log, for the sub-second check.
- `artifact-index.tsv`: `path,file_size,compress_size,crc32` of every ZIP member, to confirm no outer step is missing from the subset.
- The ZIP in `raw/` is an untracked local copy; do not require it.
- Do not use `stage-costs.csv`, `process-costs.csv`, `plot_rows.csv`, `time_boundaries.json`, or `summary.json`.

## Definitions
- Outer step: a top-level directory `<NN>-<slug>` with `runtime.txt` directly inside it. `runtime.txt` files nested one level deeper are substeps, excluded from every sum.
- `n_outer_steps`: count of outer steps, confirmed against `artifact-index.tsv`.
- `sum_steps_s`: sum of outer `runtime.txt` durations, in seconds, to the millisecond.
- `detailed_routing_s`: the outer step whose slug is `openroad-detailedrouting`.
- `top_steps`: outer steps sorted by duration, descending; ties by ascending `NN`. Report the six longest and `remainder_s`, the sum of the others.
- `run_test_s`: `completed_at` minus `started_at` of the step named `Run Test`, whole seconds, as API timestamps have one-second resolution.
- `job_s`: job `completed_at` minus `started_at`, whole seconds.
- `run_test_log_s`: from the log's first timestamp in `Run Test` to the first timestamp of the next step. Sub-second, for a check only.
- `job_over_steps`: `job_s / sum_steps_s`.
- `nested_ok`: `sum_steps_s <= run_test_s <= job_s`.
- `job_steps_outside_run_test`: names of the steps in `steps[]` other than `Run Test`, in order.

## Expected output
```json
{
  "n_outer_steps": 0, "n_nested_excluded": 0,
  "sum_steps_s": 0.0, "detailed_routing_s": 0.0,
  "top_steps": [{"step_dir": "", "seconds": 0.0}], "remainder_s": 0.0,
  "run_test_s": 0, "job_s": 0, "run_test_log_s": 0.0,
  "job_over_steps": 0.0, "nested_ok": false,
  "job_steps_outside_run_test": [""]
}
```

## Tolerance
Step counts, order, and API seconds: exact, as they are fixed records. `sum_steps_s`, `detailed_routing_s`, and `remainder_s`: 0.001 s, the record's resolution. `job_over_steps`: 0.005, because the numerator is whole seconds and the prose prints a short ratio. `run_test_log_s`: 0.2 s against `run_test_s` allowed, since the log and API use different clocks and resolutions.

## Ambiguities
- "Flow steps" does not say whether skipped steps with near-zero durations count. Every outer `runtime.txt` is counted here, following provenance.
- The prose gives no decimals for the step total or the ratio.
- "Followed by Magic LEF generation and streamout and then KLayout and Magic DRC" names four steps but does not rank them. The test checks that those are the second through fifth longest, in that listed order. The word "then" leaves room for a looser reading.
- The prose lists what the job adds around `Run Test` without saying whether the list is complete. The job record has steps it does not name, such as building with Nix and enabling PDKs.
- Whether a boundary such as `Run Test` ends at the API timestamp or at the next step's start is not stated. Here the API is the book's boundary, per the study README, and the log is a check.
- The ZIP expires upstream on 2027-01-06, after which subset bytes rest on the CRC-32 index.
