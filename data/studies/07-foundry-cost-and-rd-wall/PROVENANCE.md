# Provenance — Study 07, Design Cost and the R&D Wall

**Evidence class:** Mixed. SEC financials are mined and independently verified.
Foundry economics are unsourced industry estimates.
**Dataset status:** Financial columns verified. Foundry columns misattributed
**Figure status:** Panel A is drawn from an in-script table, see Known defects
**Last independently verified:** 2026-09-09

## The claim this study supports

The binding constraint on leading-edge silicon is the cost of designing and verifying
a part, not the cost of fabricating it. R&D intensity has climbed past 30% of revenue
across the industry, and non-recurring design cost per leading-edge SoC now runs into
the hundreds of millions.

## Where the data comes from

**This receipt mixes two very different kinds of data in one file, and the
`source_type` column currently labels both as SEC EDGAR. That is wrong and is the
main defect below.**

| Column group | Real source | Status |
| --- | --- | --- |
| `annual_revenue_usd_billion`, `rd_expense_usd_billion`, `rd_intensity_pct` | SEC EDGAR 10-K filings | Verified against SEC |
| `wafer_cost_usd`, `full_reticle_mask_cost_usd_million`, `design_cost_per_soc_usd_million` | Industry estimates, source not recorded | **Unsourced** |

Per-row provenance columns for the financial half: `sec_accession_number`,
`filing_url`, `sec_form`. All 189 rows carry a complete accession number and a
filing URL ending in `index.htm`.

## How it was collected

```bash
python3 data/scrapers/mine_sec_edgar_semiconductor_rd.py
```

Note that this script carries a large in-file table of historical financial records
rather than querying EDGAR live for every year. Those transcribed values check out
against SEC (below), but the script is a transcription with a fetch layer, not a pure
miner, and should be described as such.

## What is verified, and how

Recomputed from the raw CSV on 2026-09-09:

| Quantity | Claimed | Recomputed |
| --- | ---: | ---: |
| Firm-years | 189 | 189 |
| 2 nm design cost per SoC | $725M | $725M |
| Peak R&D intensity | 32.4% | 32.35% |
| Rows with accession number | all | 189 / 189 |

**Independent external check.** R&D expense was reconciled against the SEC's own
XBRL `companyconcept` API for NVIDIA, Intel, AMD and Qualcomm, keyed on the fiscal
period end date rather than the filing year:

```
NVDA: 19/19 within 5%   INTC: 19/19 within 5%
AMD:  18/18 within 5%   QCOM: 19/19 within 5%
TOTAL: 75/75 firm-years reconcile
```

This is the strongest external verification of any dataset in the collection. The
financial half of this receipt is real.

## What is NOT verified

The foundry economics columns are not verified and, as far as this audit can tell,
are not verifiable from the recorded source. SEC filings do not report wafer prices,
mask set costs, or per-SoC design cost. Those numbers come from industry analysis
(the usual sources would be IBS, TechInsights or SemiAnalysis) and no citation is
recorded anywhere in the receipt.

Apple (CIK 320193) is included in a semiconductor R&D population. That may be
defensible given its silicon program, but total-company R&D is not silicon R&D and
the inclusion rule is not documented.

## Known defects

1. **Foundry economics are misattributed to SEC filings.** `source_type` reads
   `SEC EDGAR 10-K` on rows whose wafer and design-cost columns cannot come from a
   10-K. Split the receipt into a financial file and a foundry-economics file, and
   give the second one real citations, or drop those columns.
2. **Panel A is drawn from an in-script table.** `nodes_data` at
   `plot_foundry_wafer_cost_and_rd_wall.py:83` is a list of dictionaries supplying
   every plotted value including `density` and `cost_100m`, neither of which exists
   in the published CSV. The transistor cost inversion claim therefore has no receipt
   at all.
3. **A forecast row carries a real accession number.** The 2026 NVIDIA row lists
   $265.0B revenue and $22.8B R&D against accession `0001045810-26-000021`. That
   filing reports $215.938B and $18.497B for FY2026. The row is labeled
   `SEC EDGAR 10-K Item 7 / Consensus Forecast`, but attaching a real accession
   number to a forecast makes the forecast look filed. Separate projections from
   filed figures.

## Files

| File | Role |
| --- | --- |
| `sec_edgar_semiconductor_rd_economics.csv` | Primary receipt, 189 firm-years, see defects 1 and 3 |
| `plot_foundry_wafer_cost_and_rd_wall.py` | Figure generator, see defect 2 |
| `../../scrapers/mine_sec_edgar_semiconductor_rd.py` | Collector |
