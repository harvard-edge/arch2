# Spec 03 notes: CVDP category gap

## What I did
`compute.py` reads `inputs/book/contents/chapters/10-evaluation/data/fig-ch10-cvdp-category-gap/chapter10-cvdp-category-pass1.csv` (sha256 `d46b7003...4490b0`, recorded in full in `result.json`) and computes every spec output with exact arithmetic. `result.json` has `readings` (one spec-shaped entry per reading, plus the ranges at file precision as `spec_to_rtl_range_pct` and `checker_range_pct`), `meta`, `overall_check_flags`, and `source_comparison`. Every number below is measured from those files unless marked otherwise.

## Dropped and skipped
- Rows dropped: 0 of 72.
- Comment lines skipped: 8 (spec instruction). Blank lines: 0.
- `overall` rows held out of category statistics: 8 (spec definition). 64 category rows used.
- No try/except anywhere. Duplicate or missing cells stop the run; none occurred.

## Readings (12, the cross product)
- Rounding: `half_up`, `half_even`. Spec names both. No range endpoint or overall value ends in exactly `.5` (`exact_half_cells` is empty), so they agree everywhere.
- Median across eight models, an even count: `midpoint` (mean of the middle two, the usual reading), `low`, `high`. These change only `median_pct` of categories. `lowest_category.by_median` stays `cid13` in all three.
- Aggregate on line 421: `printed` (the overall rows, the spec's own definition) and `recomputed` (the n-weighted figure). I added the second because the spec says the prose does not say what the aggregate covers. It is the weaker reading: `recomputed` gives 33.364 and an integer of 33, against 33.56 and 34 for `printed`. Same best model either way. Use `printed` as the literal spec result; `round_half_up__median_midpoint__aggregate_printed` is that entry.

The category table, ranges, gaps, `disjoint`, and all three lowest-category results are the same in all 12 readings, apart from `median_pct`.

## Results that do not meet the spec's tolerance
`overall_recomputed` differs from the printed overall by more than the 0.1 tolerance for three of eight models: Claude 3.7 Sonnet (-0.196), Claude 3.7 Sonnet (Extended Thinking) (+0.227), GPT 4.1 (+0.135). The other five are within it. See `overall_check_flags`.

Likely cause, assumed and not proven: all 64 category cells are whole numbers printed with `.0` (counted in `meta`), which suggests the paper rounded them to integers, so the spec's reasoning of rounding to one decimal understates the error. Filtering changing the weights, which the spec also names, is not excluded. I cannot separate the two from these inputs.

## Source comparison (reported separately)
The spec's URL fetched. I also fetched `https://arxiv.org/pdf/2506.14074v1` and `https://arxiv.org/html/2506.14074v1` for the table itself, into `src/` (HTTP 200 for all). The PDF is parsed with `pdftotext -layout`, the HTML with `html.parser`.
- Table 2: 72 of 72 cells match the CSV in both PDF and HTML.
- Table 1: 8 of 8 category names and non-agentic counts match in both.
- Model rows align by order. The one label that differs is the paper's ditto row (`" Thinking`), which the CSV writes as `Claude 3.7 Sonnet (Extended Thinking)`. The paper's method text says "with and without Extended Thinking", so I accept that mapping.

So the spec's last ambiguity, that a transcription error cannot be caught, does not apply to this run. The fetched copy exists only in my folder, and it is not retained elsewhere.

## Ambiguities and observations
- Spec asks for one `best_model_pct`; the shape allows only one. Best model is unique, so nothing was lost. Code adds `best_model_pct_all` if tied; not triggered.
- `lowest_category` values are single strings. A tie would join with ` | `; not triggered.
- Line 421 scope: the file holds non-agentic rows only. An aggregate that included agentic problems cannot be computed from the input. The paper's Table 3 prints a highest agentic overall of 29.0, recorded in `source_comparison`, so it would not raise the maximum if read as a separate aggregate. A pooled agentic plus non-agentic figure was not computed, because it needs agentic per-category work outside the spec.
- The paper's Table 5 (`pass@1 (n=1)`) prints different pass rates for the same categories, for example 22.77% for Claude 3.7 Sonnet on cid13 against 6.0% in Table 2. Not used; the spec names Tables 1 and 2. Worth a look by whoever owns the claim, since a reader could find either figure.
- `n_problems` per category sums to 494 and matches the overall rows.

## Result values seen before computing
The spec's claim text hides its values, but two other things showed some. The CSV header prints 33.56% and 34%. While reading the paper's Table 2 and body text for comparison I saw 34% and the table cells; this was after `spec.md` and before `compute.py` was written. Neither was typed into code, and no target was aimed at.

## Could not compute
Nothing in the spec. Pooled agentic and non-agentic aggregate: out of scope and not attempted.

## Runs
| Command | Elapsed | Outcome |
|---|---|---|
| `curl` of abs, pdf, html into `src/` | not timed | all HTTP 200 |
| `python3 compute.py` (first version) | 0.13 s | success, 12 readings |
| `rm result.json; python3 compute.py` (added whole-cell count) | 0.12 s | success, 12 readings |

No run failed.
