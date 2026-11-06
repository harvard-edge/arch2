# Notes: Spec 11, implementation stage costs

## What I did
`compute.py` reads four raw inputs, checks them, and writes `result.json`: a `readings` list (9 entries, each in the spec's shape, plus `reading`, `is_spec_definition`, `description`), a `checks` block, and a `manifest` with input hashes. Durations are integer milliseconds until the output step. No stated value was typed in; literals are spec names only (`Run Test`, `openroad-detailedrouting`, and the four prose slugs for the order check).

All numbers below are measured from the supplied records; the receipts are the files in `inputs/.../raw/`. This session has not been audited by anyone else.

Spec-definition reading `all_outer__api_completed_at`: 78 outer steps, 2 nested excluded, sum 106.292 s, detailed routing 25.759 s, remainder 25.945 s, Run Test 108 s, job 288 s, log check 108.117 s, ratio 2.7095, nested_ok true.

## Input checks
- All 144 files in the tarball match `artifact-index.tsv` on size and CRC-32.
- runtime.txt sets are identical in tarball and index: 78 outer, 2 nested, none elsewhere.
- Every numbered top-level directory has a runtime.txt (0 lacking one).
- `spec.md` gives no SHA-256 for any input, so nothing could be hash-checked against the spec. Hashes are recorded in the manifest. The ZIP's SHA-256 (by `shasum` during inspection) equals the `digest` in `artifact-metadata.json`, but `compute.py` does not use the ZIP, as the spec says not to require it.
- Unused: the ZIP, `workflow-run.json`, `artifact-metadata.json`. Forbidden derived files are not in my folder.

## Dropped items
- Nested `runtime.txt`: 2 (`43-openroad-repairantennas/1-openroad-diodeinsertion`, `.../2-openroad-checkantennas`), per spec. Parent step 43 records 1.026 s against their 1.018 s.
- Top-level entries that are not steps: 6 (`error.log`, `final`, `flow.log`, `resolved.json`, `tmp`, `warning.log`).
- Log lines without a timestamp: 0. Runtime records that failed to parse: 0.
- The non-default readings drop 4 steps (`excl_zero_ms`) or 12 steps (`excl_log_skip`), listed in `checks`.

## Ambiguities and readings
Nine readings: 3 step sets crossed with 3 Run Test boundaries.

Step sets:
- `all_outer`: spec definition.
- `excl_zero_ms`: drops 4 steps recorded as 00:00:00.000. n = 74, sum unchanged.
- `excl_log_skip`: drops 12 steps whose own log block says they skipped. n = 66, sum 106.279 s, remainder 25.932 s, ratio 2.7098. This is my rule, not the spec's: a flow record of level I or W with "skipping" or "skipped", attributed to the most recent `Running ...` step, leaving out `sequential.py` gating messages (they concern steps that have no directory), "for layer" tool warnings, and the end-of-flow digest. The word-match rule can miss a step that skipped silently, and `25-openroad-ioplacement` may have done part of its work.

Run Test boundaries:
- `api_completed_at`: spec definition, 108 s.
- `api_next_step_started`: also 108 s (next step, Upload Run Folder, starts at the same API second).
- `log_subsecond`: 108.117 s, used only for `nested_ok` in those readings; `run_test_s` stays the API value.

`nested_ok` is true and the top six are the same in all nine readings. Only `n_outer_steps`, `sum_steps_s`, `remainder_s`, and the ratio move, and only with the step set.

Prose order: reported as two booleans rather than extra readings. Both pass: `prose_order_rank_2_to_5_listed` (exact listed order) and `..._grouped` (LEF and streamout before the two DRC steps, any order within a pair). "Led by" detailed routing also holds.

## Observations for the comparison
- Log step boundaries: the log has no step names. I found Run Test as the single `##[group]Run` block containing `python3 -m librelane` and `--run-tag`; the next `##[group]Run` opens the next step. Both boundary seconds match the API. Log minus API is 0.117 s, within the 0.2 s tolerance. Last line of Run Test is at 108.050 s.
- The spec's ambiguity note gives "building with Nix and enabling PDKs" as job steps the prose omits. `design-job.json` marks both `skipped`, 0 s. `job_steps_outside_run_test` keeps all 20 names per the definition; the 14 that ran are in `checks`.
- The largest step outside Run Test is `Maximize build space`, 93 s. The prose lists no such item unless "runner preparation" covers it.
- Outside steps sum to 177 s; with Run Test that is 285 s, first step start to last step end. The other 3 s of the 288 s job fall before the first step and after the last, and no step accounts for them.
- The gap between the sum and Run Test is 1.708 s. I did not attribute it; the inputs do not itemize it.

## Result values seen
No published value appeared anywhere; the spec masks them as [VALUE]. I did not open any forbidden file.

## Could not compute
Nothing in the spec's output is missing.

## Runs
Scratch: I extracted the tarball's runtime files to `inputs/_peek` to look at them, then removed it (it went to Trash).

A later shell call that wrote these notes stalled past its 120 s limit after the rerun finished, on `ls -la` or the trailing one-liner. It was not a `compute.py` run, and `notes.md` and `result.json` were already written.

| Command | Result | Elapsed |
|---|---|---|
| `python3 compute.py` (first run, `/usr/bin/time -p`) | rc 0 | 0.04 s real |
| `python3 compute.py` (rerun, same code) | rc 0; `readings` and `checks` identical to first run | 0.04 s real |
