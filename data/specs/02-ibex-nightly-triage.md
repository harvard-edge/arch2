# Spec 02: Ibex nightly plateaus and triage ratio with coverage

## Claim
`book/contents/chapters/07-feedback/07-feedback.qmd:186`: "In one retained OpenTitan Ibex nightly report, [VALUE] of [VALUE] runs pass ([VALUE]%), yet [VALUE] test groups record failures [...] Its two runs failed [VALUE] of [VALUE] cases and [VALUE] of [VALUE], and the issue author mapped [VALUE] of those [VALUE] failures to numbered signatures [...] That triage attributes [VALUE] mapped cases to causes such as generator timeouts, flawed assertions, stale testbench checkers, co-simulation configuration, and host timeouts, and only [VALUE] to a possible RTL bug. The other [VALUE] failures have no case-by-case mapping. The author excluded [VALUE] first-run failures in four test families because fixes had been made, and compared [VALUE] second-run failures by signature under stated assumptions."

`book/contents/chapters/07-feedback/07-feedback.qmd:213`: "Across [VALUE] nightly reports from [VALUE] to [VALUE], the aggregate moves in steps [...] One large test group accounts for most of the two largest steps [...] In the steadiest stretch, from [VALUE] to [VALUE], the nightly pass rate has a standard deviation of only [VALUE] percentage points and a median of [VALUE] groups fail on any night. Over the same months [VALUE] distinct groups failed at least once, and consecutive reports differ by about [VALUE] groups."

## Raw inputs
- `data/studies/28-ibex-nightly-history/manifest.csv`. The raw JSON is not retained. Fetch every `url`, check `sha256`, and stop and report on any mismatch or failed fetch. Do not fall back to `derived/`, which holds the original extractor's output.
- `data/studies/16-regression-records/raw/ibex-opentitan-latest-report.json`, the report named by the bibliography's October 16, 2026 snapshot.
- `data/studies/22-ibex-triage/source/regr-first.log`, `regr-second.log`, and `issue-2187.json` (field `body`). Do not use the study's top-level CSVs.
- Report JSON shape: `results.unmapped_tests[]` with `name`, `passing_runs`, `total_runs`. `results.testpoints` was empty in the reports sampled while writing this spec. Count nights where it is not.

## Definitions
- Night: manifest `date`. One date has two rows whose keys differ by a leading slash. Use the key without the slash.
- Nightly pass rate: 100 times summed `passing_runs` over summed `total_runs`.
- Failing group on a night: `passing_runs < total_runs`. Groups with `total_runs == 0` are not failing and are counted separately.
- Interval statistics for dates `[a, b]`, over the reports present: `sd_pct`, `median_failing`, `distinct_failing` (names that fail on at least one night), and `churn`, the size of the symmetric difference of the failing sets of adjacent reports.
- Log parsing: a case row is `<test>.<seed>: <status>`. `PASS` passes. `FAILED` with or without `{T}` fails. Reconcile the counts with the summary line at the top of each log.
- Mapping: bullet rows `<test>.<seed> - Signature <k>` under each `## Failures` heading of the issue body. Whitespace varies. Signature numbers are local to their regression. Every mapped case must be a failed case in that log.
- `rtl_mapped`: mapped cases whose signature explanation says "Possible RTL bug". `non_rtl_mapped`: the remaining mapped cases.
- `coverage_pct`: 100 times mapped failures over all failures, pooled across both runs. `unmapped`: all failures minus mapped.
- Four families: `riscv_assorted_traps_interrupts_debug_test`, `riscv_pmp_basic_test`, `riscv_pmp_out_of_bounds_test`, `riscv_pmp_full_random_test`, matched exactly.

## Expected output
```json
{
  "single_report": {"passing_runs": 0, "total_runs": 0, "pass_pct": 0.0, "failing_groups": 0, "total_groups": 0},
  "archive": {"n_objects": 0, "n_nights": 0, "first_date": "", "last_date": "", "nights_with_testpoints": 0, "groups_zero_runs_nights": 0},
  "segmentation_method": "",
  "plateaus": [{"start": "", "end": "", "n_reports": 0, "mean_pct": 0.0, "sd_pct_sample": 0.0, "sd_pct_population": 0.0, "median_failing": 0.0, "distinct_failing": 0, "churn_mean": 0.0, "churn_median": 0.0}],
  "steadiest_start": "", "steadiest_end": "",
  "largest_steps": [{"date": "", "delta_pct": 0.0, "top_group": "", "top_group_share": 0.0}],
  "triage": {"run1_failed": 0, "run1_total": 0, "run2_failed": 0, "run2_total": 0, "failed_pooled": 0, "mapped": 0, "mapped_run1": 0, "mapped_run2": 0, "rtl_mapped": 0, "non_rtl_mapped": 0, "unmapped": 0, "coverage_pct": 0.0, "non_rtl_per_rtl": 0.0, "families_failed_run1": 0, "families_failed_run2": 0, "other_tests_failed_run2": 0, "unmapped_run2": 0}
}
```

## Tolerance
Counts and dates in `single_report`, `archive`, and `triage`: exact, because they are counts of fixed text and JSON. Percentages and ratios: 0.05 percentage points or 0.1 percent relative, the rounding of the prose. Plateau statistics: comparable only when boundaries match. Given matching boundaries, allow 0.01 percentage points on `sd_pct` and 1 group on the failing counts, since a window edge of one night moves them slightly.

## Ambiguities
- "Steadiest stretch" has no definition. The prose names no segmentation method, segment count, or steadiness score, and provenance says the segment count is a chosen parameter. Fix and state a method before seeing the book's dates. Any disagreement in boundaries is itself a finding.
- "Moves in steps" and "two largest steps" have no threshold or size measure. "Accounts for most" has no attribution rule. `top_group_share` is read here as the group's change in nonpassing runs over the change in all nonpassing runs across the step, which is an assumption.
- "Differ by about" does not say mean or median, or whether difference means symmetric difference. Date gaps between adjacent reports are not addressed.
- The standard deviation may be sample or population. Report both.
- "[VALUE] nightly reports" may count objects or distinct nights. Report both.
- "Triage ratio" appears nowhere as a ratio in the prose, which prints counts. `non_rtl_per_rtl` and `coverage_pct` are this spec's reading of the task's term.
- "Compared [VALUE] second-run failures" may mean all failures outside the four families or only the unmapped ones. These differ if any mapped second-run failure sits outside the families. Report both.
- "One retained report" names no date in the prose. Only the bibliography note ties it to the snapshot.
