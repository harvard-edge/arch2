# Studies

Each study folder carries a `provenance.yml` recording where its data came from,
what has been verified, what has not, and what is still wrong with it. That file is
the only provenance record. Anything not listed in it has no recorded source.

## Schema

`arch2-provenance/v1`. Same keys in every folder, in the same order.

| Key | Meaning |
| --- | --- |
| `claim` | The one sentence this study supports |
| `evidence_class` | `mined` (we pulled it from primary documents), `measured` (we ran it), `transcribed` (somebody else's number, attributed) |
| `status` | `verified`, `defective`, or `withdrawn` |
| `sources` | Where the data came from, with resolvable identifiers |
| `datasets` | Each file, its row count, and which columns carry per-row provenance |
| `produced_by` / `reproduce` | The script, and the command that re-derives it |
| `defects` | Open problems, with file and line |
| `verified` / `not_verified` | What was checked, and what was not |

An empty `row_provenance: []` means values in that file cannot be traced to a source
one row at a time. That is a warning, not a formality.

## Status, audited 2026-09-29

| # | Study | Class | Status | How it was checked |
| --- | --- | --- | --- | --- |
| 02 | RTL source complexity | measured | **verified** | All headline ratios recomputed from the CSV; 279 of 1,513 rows (every VerilogEval and CV32E40P module) re-parsed with pyslang 11.0.0 at the pinned commits and matched exactly |
| 06 | Placement seed dispersion | measured | **verified** | All 20 raw ORFS JSON files hash-match the CSV; 0.84% area and 3.83% slack spreads recomputed from them |
| 08 | Executed VerilogEval mutation pilot | measured | **verified** | 25 baselines and 22 mutants re-run with Icarus and Yosys and matched exactly; 328 of 338 recomputed from the CSV |

Studies 01 (silicon errata), 03 (MLPerf software dividend), 04 (Tiny Tapeout
democratization), 05 (hardware CVE mitigation tax) and 07 (foundry cost and R&D)
were deleted on 29 September 2026, with their datasets, figures, plot scripts,
and the scrapers that produced them. Each was checked value by value against its
primary sources:

- **01.** The erratum IDs and titles were largely extracted correctly, but the
  subsystem classifier misassigned about half of a 40-row sample, the `<1.8%`
  ALU headline appeared nowhere in the data, and the stepping-decay panel was
  literal constants.
- **03.** The scraper held hand-typed literals and fetched nothing. 22 of 31
  checkable MLPerf rows disagreed with the MLCommons logs (the 3.82x headline is
  1.9x in the logs), and none of the 26 recorded commit SHAs existed.
- **04.** The commit hashes resolved to nothing, the 1981 cost endpoint had no
  source, and the affiliation shares were typed into the scraper.
- **05.** The cumulative 22.0% tax was a constant with no composition rule, two
  CVE IDs belonged to unrelated products, and four penalties contradicted their
  cited papers.
- **07.** 70 of 189 SEC accession numbers pointed at other filings, forecasts
  carried real accession numbers, and the node-cost table had no openable source
  for wafer price, density or cost per transistor.

Study 08's earlier RNG-generated vacuity and judge-bias data was deleted on the
same date; only the executed pilot remains in that folder.

## The manuscript is not affected

No study in this directory is read by `book/contents/`. The studies feed the
public data page (`www/data.qmd`); the book's figures read `data/datasets/` and
chapter-local data.

## Four ways a number got past a reader

These are the defect shapes the audits found, in the order they are hard to catch.

1. **Generated values with real tool metadata.** A dataset header named
   JasperGold, SymbiYosys and Verilator; the values came from `rng.gauss()`.
2. **A "scraper" that scrapes nothing.** A script named `mine_*` or `scrape_*`
   that contains the data as literals looks like a pipeline and is a table.
3. **A headline that exists only as an annotation string.** `<1.8%` and `82x`
   were matplotlib text, contradicted by the data beneath them.
4. **Fabricated identifiers.** Commit hashes that resolve to nothing, accession
   numbers that belong to other filers, and CVE IDs assigned to other products.

## Validators

`python3 data/validate_provenance.py` scans `data/datasets/` and `data/studies/`,
fails on any RNG-based generator, and fails on any file under
`www/data/observatory/` that no page or notebook reads.
`python3 data/validate_figure_provenance.py` checks the book's figures.
