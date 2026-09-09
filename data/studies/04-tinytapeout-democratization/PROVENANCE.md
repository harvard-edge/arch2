# Provenance — Study 04, Open Silicon Democratization

**Evidence class:** Transcribed and API-mined
**Dataset status:** Headline verified, provenance column fabricated
**Figure status:** Numeric panels data-driven, annotation text hardcoded
**Last independently verified:** 2026-09-09

## The claim this study supports

Access to silicon fabrication stopped being the constraint on who can design a chip.
Participant entry cost fell roughly three orders of magnitude over four decades, which
moves the bottleneck upstream into design and verification capability.

## Where the data comes from

Two receipts. A shuttle-by-shuttle census of the Tiny Tapeout and Open MPW programs,
and a historical cost series from 1981 to 2026.

| Receipt | Rows | Source |
| --- | ---: | --- |
| `tinytapeout_democratization_census.csv` | 27 | Tiny Tapeout API, Open MPW program data |
| `shuttle_cost_historical_collapse.csv` | 12 | Mead and Conway (1980), MOSIS, Efabless, foundry MPW pricing |

The cost series carries a `primary_citation_and_source` on all 12 rows.

## How it was collected

```bash
python3 data/scrapers/scrape_tinytapeout_census.py
```

## What is verified, and how

Recomputed from the raw CSV on 2026-09-09:

| Quantity | Claimed | Recomputed |
| --- | ---: | ---: |
| Entry cost, 1981 dedicated mask lot | $150,000 | $150,000 |
| Entry cost, 2026 Tiny Tapeout slot | $50 | $50 |
| Collapse factor | 3,000x | 3,000x |

## What is NOT verified

Shuttle participant counts and the affiliation mix have not been reconciled against
the Tiny Tapeout API as of today. The census reports 4,768 designs across 27
shuttles; prose elsewhere rounds this to "4,780+", which overstates the receipt.

## Known defects

1. **The `provenance_commit_hash` column is fabricated.** All 27 values are
   40-character hex strings that resolve to nothing. Ten were tested against every
   plausible repository in the TinyTapeout GitHub organization on 2026-09-09 and all
   ten returned HTTP 404. This is the same fabrication signature as the withdrawn
   175.3x AST study. **Remove the column or replace it with real tagged release
   commits before this dataset is published.**
2. **A sentinel value is published as a measurement.** The 2020 Google and SkyWater
   row records a participant cost of `0.0`, because participation was fully
   subsidized, and stores `cost_collapse_factor_vs_1981_dedicated` as `999999.0`.
   That is an encoding of a division by zero, not a measurement, and it will corrupt
   anything that plots or aggregates that column. Replace with an explicit
   "fully subsidized" marker or an empty cell.
3. **Affiliation percentages are hardcoded in the figure.** The participant
   breakdown callout at `plot_tinytapeout_democratization.py:303` is a literal string
   and does not agree with the census, which gives a weighted high-school share of
   12.9% against the figure's 15%.

The 3,000x headline uses the 1981 and 2026 endpoints and is unaffected by all three.

## Files

| File | Role |
| --- | --- |
| `tinytapeout_democratization_census.csv` | Shuttle census, 27 rows, see defect 1 |
| `shuttle_cost_historical_collapse.csv` | Cost series, 12 rows, see defect 2 |
| `plot_tinytapeout_democratization.py` | Figure generator, see defect 3 |
| `../../scrapers/scrape_tinytapeout_census.py` | Miner |
