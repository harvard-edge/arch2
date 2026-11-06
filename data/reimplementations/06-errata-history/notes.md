# Spec 06 notes

## What I did
`compute.py` reads the revision-page JSON, parses rows (two column orders), walks each description clause by verb (Added/Removed/Updated/Modified), expands `to`, `through`, and dash ranges, and counts. It reads `errata.csv` for the corpus and `launch_years.csv` for launch data. No result value appeared anywhere I read: the spec shows only `[VALUE]`, and the forbidden files were not opened (they are not in the folder).

## Page text check
All four pages: whitespace-normalized PyMuPDF text equals `extracted_text`; `pdftotext -layout` gives the same multiset of ID, revision, and date tokens; its (date, revision) pairs equal the parsed rows. Only one page each is needed: the page after each table is Preface or Overview. Revision History appears nowhere else in the PDFs except the Contents and running headers. Hashes are in `result.json`.

## Readings (`result.json` -> `readings`)
Identifier counts, gaps, continuation, and corpus are the same in all three. They differ only in row counts and `first_year`:
- `rows_all_listed`: every table row, including initial-release rows. This is the spec's definition as written: 40 rows.
- `rows_post_initial`: drops the 3 initial-release rows, since the caption says "post-initial ... across [VALUE] revision rows": 37 rows.
- `rows_with_additions`: only rows naming at least one added ID, a second reading of that caption: 35 rows.

Spec-listed ambiguities, resolved inside the shape:
- List vs distinct: both reported; equal everywhere, no ID is added twice in any document.
- Calendar year vs dated two-year test: both reported. Row dates have only a month, so by-date was run with the row at the first and at the last day of the month (`by_date_row_at_month_start/end`). All agree; `n_continuing` is 3 by every test. `continues_two_years_by_date` would be null on disagreement; none is.
- Parenthesis after "CPU families": `vendor` carries families and rows for each.
- Years without rows: per document, as the spec fixes. Same in all three readings.
- `through_month`: "March"; added `through_date_text` for the full string.

## Dropped or excluded (counts)
- Rows dropped: 0. Table rows parsed: 40. Page headers and footers excluded by the parser. The Zen 5 footer has a bare `July 2025` line, rejected because a revision token must follow a date.
- Clauses: 38 Added, 10 Updated, 5 Removed, 1 Modified. 3 Added clauses have no ID and add nothing: `Added Table 5`, `Added Nomenclature S-Spec Number`, and the Threadripper silicon clause (its `Table 4`, `Table 12` are not IDs).
- CSV rows dropped: 0. No blank IDs, no duplicate keys. All 19 families match launch rows one to one.

## Things to know
- Ice Lake-SP's table starts at 003US (July 2021): no initial-release row and no 001/002 rows are listed. So its 104 additions include the July 2021 row, and the document contributes no initial row. ICX1-73 are not in the table.
- Broadwell's first row (May 2015) predates its launch date (2016-03-31). Under `rows_all_listed`, `first_year` is 2015.
- `added_total` counts IDs later removed, as the spec says Removed clauses add nothing: ICX121, ICX132, ICX134 were added and later removed, so they are absent from `errata.csv`. A net count was not requested.
- BDF92 is added in row 003 (range BDF86-BDF99) and has no Removed clause in the revision table, but the PDF body marks it `Removed` / "Removed due to inapplicability", and `errata.csv` omits it. So it counts as added here, as the rule requires, and the CSV agrees with removed entries being excluded for this one ID. Broadwell: 109 less BDF42, BDF61, BDF92 = 106 CSV rows.
- "Itemized" and removed entries: `status` values are No Fix 1547, Fixed 214, Plan Fix 13; no removed value, so the rule cannot be tested, as the spec says.
- PDFs for the other corpus families are absent, so the corpus total was not reparsed.

## Could not compute
Nothing in the spec's output shape was left uncomputed.

## Runs
| Command | Elapsed | Outcome |
|---|---|---|
| `python3 compute.py` (first) | 0.175 s | rc 0, 4 DeprecationWarnings on `re.split` |
| `python3 compute.py` (after fixing that and removing an unused variable) | 0.173 s | rc 0 |
| `python3 compute.py` (final, timed inside a shell script) | 0.222 s | rc 0; `result.json` sha256 e870fba9...33a2. A trailing bare `ls` in that same shell call hung to the 120 s timeout and went to background; compute.py had already finished |
