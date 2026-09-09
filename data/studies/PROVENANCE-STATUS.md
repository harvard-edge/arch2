# Study provenance status

Audited 2026-09-09 by three independent passes: this repository's own checks, a
Codex pass, and an agy pass. Each study has a `PROVENANCE.md` recording where its
data comes from, what has been verified, and what has not.

## The one question that matters first

**Is any invalid figure used in the book?**

**No.** Verified 2026-09-09 by direct search of `book/contents/**/*.qmd`:

| Check | Result |
| --- | --- |
| Withdrawn receipts referenced in `book/` | none |
| `eda_seed_dispersion_qor_lottery` | not referenced |
| `testbench_vacuity_and_judge_calibration` | not referenced |
| `hardware_ast_complexity_gap` (175.3x) | not referenced |
| Fabricated figures 55.8%, 92.9%, 37.1%, 175.3x in prose | 0 occurrences |
| Synthesizing scrapers feeding book figures | none |

The two apparent hits are coincidences: `66.4` matches inside the git SHA
`f5516e52e66243c2d753191e350a5cfac56c83af`, and `1.8\%` matches inside `88.4\%` in
the Herdt transcription. Neither is a data claim.

**The reason the book is insulated is structural, and worth knowing.** There are two
independent data paths in this repository:

```
data/studies/           -> www/data.qmd          (the website)
data/source-receipts/   -> book/contents/*.qmd   (the manuscript)
```

The study packages feed the public data page. The book's figures read a different set
of `chapterNN-*.csv` receipts. Every defect below is confined to the website path and
to the study packages. **The corollary is that the book's own receipts are a separate
population that this audit did not cover.**

## Status by study

| # | Study | Data | Figure | Blocking defects |
| --- | --- | --- | --- | --- |
| 01 | Silicon errata archaeology | Verified | **Defective** | `<1.8%` unsupported; stepping decay and mask cost panels hardcoded |
| 02 | RTL source complexity | Verified | Verified | none |
| 03 | Fixed-silicon software dividend | Headline verified | **Defective** | `82x` unsupported (real range 8x-49x); trajectory panel hardcoded |
| 04 | Open silicon democratization | Headline verified | Partial | 27 fabricated commit hashes; `999999` sentinel |
| 05 | Hardware CVE mitigation tax | Verified | **Defective** | cumulative curves hardcoded |
| 06 | Placement seed dispersion | Verified | Verified | withdrawn synthetic CSV still in the directory |
| 07 | Design cost and R&D wall | Financials verified | **Defective** | foundry columns misattributed to SEC; Panel A hardcoded |
| 08 | Testbench mutation vacuity | **Withdrawn** | **Withdrawn** | entirely RNG-generated |

**Study 02 is the only study with no open defect.** Study 06's measured pilot and
Study 07's SEC financials are both independently verified and sound; the defects
around them are packaging and figure problems, not data problems.

## The defect class that keeps recurring

Every remaining defect is one shape:

> A number a reader sees exists only as a literal in a plotting script or a prose
> file, and cannot be derived from the dataset published beneath it.

This is the same shape as the three datasets withdrawn in September, one level up.
Those fabricated the *data*. These fabricate the *headline over real data*, which is
harder to spot and reads exactly like a measurement.

## Why the existing gates did not catch it

| Gate | What it checks | What it misses |
| --- | --- | --- |
| `validate_provenance.py` | a receipt in `data/source-receipts/` records a source | does not scan `data/studies/` at all; treats "script mentions the CSV name" as proof it was used |
| `validate_figure_provenance.py` | a figure script contains a `.csv` string literal | does not check the CSV is actually plotted; only reads `book/contents/`, never `www/data.qmd` |

Both report zero violations today. Both would pass every defect in the table above.

## The gate that closes it

`data/verify_claims.py` with `claims.json` declares each published headline together
with the expression that derives it from its own dataset, and recomputes all of them
on every commit.

```bash
$ python3 data/verify_claims.py
[  ok  ] 01  Itemized errata                     claimed=1771   computed=1771
[  ok  ] 02  Complexity ratio                    claimed=6.7    computed=6.6964
[  ok  ] 06  Setup slack spread (%)              claimed=3.83   computed=3.8358
[  ok  ] 07  2 nm design cost per SoC ($M)       claimed=725    computed=725.0
[ FAIL ] 04  Rows with sentinel collapse factor  claimed=0      computed=1
20 published claims recomputed from source data, 1 mismatch.
```

A number that cannot be expressed against its own data cannot be declared, and a
number that is not declared does not go on the website. That is the whole rule.

Two gates still need writing:

1. **Fail when a plot script loads a CSV and then plots list literals.** An AST check
   on whether the parsed rows actually reach a `plot`, `bar` or `scatter` call. This
   is what catches studies 01, 03, 05 and 07.
2. **Fail when a receipt header names a tool version its generator hardcodes.** This
   was recommendation 4 in `FABRICATED-CLAIM-TRACE.md` and is still unimplemented. It
   is what catches the next Study 08 before it ships.

## Repair order

1. Remove the withdrawn synthetic CSV, plot script and figures from
   `data/studies/06-eda-seed-dispersion/`. Quarantine leak, smallest fix, highest
   embarrassment if found by a reader.
2. Drop or replace the `provenance_commit_hash` column in Study 04. Fabricated
   provenance is the worst category of defect on a page whose entire argument is
   provenance.
3. Correct `<1.8%` to 6.8% and `82x` to the real 8x-49x range, in
   `www/data.qmd`, both study READMEs, and both plot annotations.
4. Rebuild the four hardcoded figure panels from their CSVs, or delete the panels
   whose data does not exist (Study 01 stepping decay, Study 07 transistor cost).
5. Split Study 07's receipt so foundry estimates stop being labeled SEC EDGAR.
6. Extend `validate_provenance.py` to scan `data/studies/`, and add the two gates
   above.
7. Only then publish `dev` to `main`. The live site currently serves the withdrawn
   175.3x, 55.8% and N=550 figures, which is the most urgent exposure of all.

## What was not verified anywhere

Stated plainly so it is not mistaken for coverage:

- The 19 Intel and AMD errata PDFs have not been re-parsed to audit the extraction.
- The 20 CVE penalty figures have not been checked against their source papers.
- MLPerf throughput values have not been reconciled against MLCommons result tables.
- The 20 OpenROAD runs were not re-executed, though retained raw output matches.
- The book's own `data/source-receipts/chapterNN-*.csv` population was not audited.
