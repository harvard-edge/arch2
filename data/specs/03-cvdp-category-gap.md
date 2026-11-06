# Spec 03: CVDP category gap

## Claim
`book/contents/chapters/10-evaluation/10-evaluation.qmd:439`: "Across eight models, turning a specification into RTL reaches [VALUE] to [VALUE]% `pass@1`, whereas generating testbench checkers reaches only [VALUE] to [VALUE]% (@fig-ch10-cvdp-category-gap)."

`book/contents/chapters/10-evaluation/10-evaluation.qmd:441`: "**Benchmark pass rates differ widely by task, and [VALUE] sits lowest.** Non-agentic CVDP code-generation `pass@1` by task category, five samples per problem, for eight models. Diamonds mark the model with the best aggregate score, purple for RTL tasks and green for verification tasks; $n$ is the number of problems."

`book/contents/chapters/10-evaluation/10-evaluation.qmd:421`: "[...] the models its authors evaluated reached no more than [VALUE]% aggregate `pass@1` on code generation [@PinckneyEtAl2025CVDP]."

## Raw inputs
- `book/contents/chapters/10-evaluation/data/fig-ch10-cvdp-category-gap/chapter10-cvdp-category-pass1.csv`. Skip lines starting with `#`. Columns: `category_id,category_name,category_group,model,pass_at_1_pct,n_problems,source_table`. This file is the transcription of the paper's Tables 1 and 2 and the rawest retained record.
- Source, not retained: `https://arxiv.org/abs/2506.14074v1`. If it can be fetched, compare the cells; report any difference separately.
- Do not use `book/contents/chapters/10-evaluation/data/fig-ch10-cvdp-category-gap/generate_cvdp_ch10.py` or the figure.

## Definitions
- Category rows: `category_id != overall`. There is one row per model and category.
- For each category: `min_pct`, `max_pct`, and `median_pct` of `pass_at_1_pct` across models, and `spread_pp` as max minus min.
- Spec-to-RTL is `cid03`. Testbench checker is `cid13`. Report each range at the file's precision and rounded to the nearest integer.
- Gap, three forms: `gap_max_pp` is `cid03` max minus `cid13` max. `gap_min_pp` is the same on mins. `disjoint` is true when `cid13` max is below `cid03` min.
- Lowest category: the category with the lowest value under each of max, median, and min. Report all three.
- Best aggregate model: highest `pass_at_1_pct` among `overall` rows. If tied, report all.
- `best_model_by_category`: that model's value in each category.
- `overall_max_pct`: the highest overall value, unrounded and rounded to an integer.
- `overall_recomputed` per model: sum of `n_problems` times category percent over the sum of `n_problems`, for comparison with the printed overall row.

## Expected output
```json
{
  "n_models": 0,
  "categories": {"<category_id>": {"name": "", "n_problems": 0, "min_pct": 0.0, "max_pct": 0.0, "median_pct": 0.0, "spread_pp": 0.0, "best_model_pct": 0.0}},
  "spec_to_rtl_range_int": [0, 0], "checker_range_int": [0, 0],
  "gap": {"gap_max_pp": 0.0, "gap_min_pp": 0.0, "disjoint": false},
  "lowest_category": {"by_max": "", "by_median": "", "by_min": ""},
  "best_aggregate_model": [""],
  "overall_max_pct": 0.0, "overall_max_int": 0,
  "overall_check": {"<model>": {"printed": 0.0, "recomputed": 0.0}}
}
```

## Tolerance
Printed cells, min, max, and gaps: 0.01 points, since they are read directly at one decimal. Rounded integers: exact, except that a cell ending in exactly `.5` may differ by 1 and must be flagged. `overall_recomputed` against printed: 0.1 points, because each category value is rounded to one decimal and the filtering in the source may change the weights.

## Ambiguities
- The prose never defines a numeric "gap". The figure name uses the word and the text prints two ranges, so this spec reports three forms and asserts none.
- "Sits lowest" has no statistic. The agreement test checks max, median, and min separately.
- The printed rounding of the ranges is not stated. Half-up and half-even can differ on cells ending in `.5`.
- The aggregate on line 421 is the rounded overall, and the file's header says so, but the prose does not say which rows it covers.
- This test cannot catch a transcription error, because the CSV is the only retained copy of the table. Provenance lists a generator script for it, and no fetched copy of the table is kept.
