# Notes: spec 08, verification scissors

## What I did
`compute.py` parses the one CSV, computes every quantity in the spec with exact fractions (the CAGR root alone uses float), and writes `result.json`. Input SHA-256 is recorded there: `b2f6828ab76b5c550f498ae3c8f07d654282c6ac139e12f029cfeba527b593d8`. The spec gives no expected hash, so there was nothing to match it against. No network fetches. Nothing outside this folder was read except `BRIEF.md`.

`result.json` has one entry under `readings` per reading, each in the spec's shape, plus `claim_slots` naming the values that reading assigns to the ambiguous prose slots. Figures in the book's own text are redacted in the spec, so nothing here was compared with them.

All numbers below are computed from the CSV cells. The CSV cells themselves are transcriptions; the 2007-2020 waves are labeled printed data and the 2022 row is chart-read and constrained. I did not see the source charts.

## Result values seen in the inputs
The CSV caveats and the CAGR row carry stated results: +50 and +146 percent since 2007, 2.7 and 6.2 percent CAGR, and 2007-2020 rates of 3.0 and 6.8 percent. They are inputs or check values under the spec, and I did not tune anything toward them.

## Rows
10 data rows: 8 waves, 1 CAGR row, 1 context row.
- Dropped: 1, the `context` row, because the spec puts it out of scope.
- Repaired, not dropped: the 2022 row has one unquoted comma in its caveat, so `csv` returns 7 fields. The extra field is rejoined to the caveat. Numeric cells are unaffected.
- The ledger is in `result.json` under `row_ledger`.

## Readings (5)
Each changes one thing from R1. R1 is a reference point for the comparison, not a preferred reading.
- `R1_diff_then2014_rose2018_cagrAsNamed`: distance = Iv - Id, "then by 2022" from 2014, "by 2020" from 2018, CAGR cells by column name.
- `R2_ratio_distance`: distance = Iv / Id. gap_min 1.7024, gap_max 1.7985, gap_2022 1.6389, **gap_2022_in_range false**. The in-range statement in the prose holds under difference and fails under ratio, so this ambiguity changes a claim's truth.
- `R3_then_by_2022_from_2007`: 2007 to 2022 gives design 50.00, verification 145.83. R1 gives 2014 to 2022: design 15.84, verification 7.27.
- `R4_rose_by_2020_from_2016`: 2016 to 2020 gives verification -1.72, design -1.90. Verification did not rise, so this reading contradicts the sentence and 2018 is the only base that fits. It is reported anyway. `2016_2020` is added to that entry's `pct_change`.
- `R5_cagr_columns_swapped`: stated cells swapped, so design 6.2 and verification 2.7. Computed values disagree by far more than the 0.15 tolerance, and the 2022 caveat says 2.7 is design, so the column-name reading is supported.

## Ambiguities with no test, not implemented
- "Held roughly level" and "movement rather than a trend" have no definition. No value computed.
- "Printed waves from 2014 to 2020" is read inclusive, as the spec says. I saw no other reasonable reading.

## Findings worth a look
- Computed vs stated 2007-2022 CAGR: design 2.74 vs 2.7, verification 6.18 vs 6.2. Both are inside 0.15. This is partly circular, as the spec warns: the 2022 cells are constrained by the same study's callouts. Against those callouts, the 2007-2022 change is +50.00 design (difference 0.00) and +145.83 verification (difference -0.17).
- Outside the spec's shape: the caveat's stated 2007-2020 design rate of 3.0 percent does not match the printed cells, which give 2.16 percent over 13 years. Verification gives 6.88 against 6.8. The design mismatch of about 0.84 points is not explained by rounding of the labels. I did not investigate its cause, since no source is retained. It is in `diagnostics_outside_spec_shape`.
- `share_of_growth_by_2014`: design 0.590, verification 0.886.

## Could not compute
Nothing in the required output was blocked. "Held roughly level" has no test, as above.

## Runs
1. `python3 compute.py` from this folder (Python 3.14.4): success, 0.03 s elapsed. This is the run that wrote `result.json`. No failed runs.
2. Not a compute run: a checking command that printed `result.json` fields and wrote these notes timed out at 120 s after finishing both. It stalled on its trailing directory listing or grep, and `compute.py` was not involved. `result.json` is unchanged (mtime 14:30).
