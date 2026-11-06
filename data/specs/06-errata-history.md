# Spec 06: Errata history totals and yearly counts

## Claim
`book/contents/chapters/11-ownership/11-ownership.qmd:264`: "Our retained analysis covers [VALUE] itemized errata across [VALUE] CPU families ([VALUE] from Intel and [VALUE] from AMD) introduced between [VALUE] and [VALUE] [...]"

`book/contents/chapters/11-ownership/11-ownership.qmd:367`: "Across [VALUE] revision-history entries in [VALUE] selected CPU documents, vendors continued adding erratum identifiers after the initial release [...] In [VALUE] of the [VALUE] histories, additions continue at least two years after launch. Ice Lake-SP, for example, received [VALUE] additions in 2026 through [VALUE], years after its [VALUE] launch. The Turin guide shows additions only in [VALUE], soon after its [VALUE] launch. [...] Each count excludes the document's initial inventory, [VALUE] years inside these histories list no revision at all, and the AMD Family 17h guide lists only [VALUE] of the [VALUE] revision numbers from [VALUE] to [VALUE]."

`book/contents/chapters/11-ownership/11-ownership.qmd:369` (caption): "Annual post-initial erratum identifiers explicitly listed as added across [VALUE] revision rows in [VALUE] selected CPU documents [...]: (a) Broadwell-EP ([VALUE] added), (b) Ice Lake-SP ([VALUE] added, [VALUE] in 2026), (c) AMD Family 17h `00h–0Fh` ([VALUE] added), and (d) AMD Family 1Ah `00h–0Fh` ([VALUE] added)."

## Raw inputs
- `data/studies/19-errata-history/source_pages/revision_history_pages.json`: `{pdf_name: {pdf_page_1based, extracted_text}}`, the revision-table page text for four documents.
- `data/studies/13-errata-dispositions/raw/pdf/{BroadwellEP,IceLakeSP,Zen1Naples,Zen5Turin}.pdf`: to check the page text. Gitignored; four of the corpus PDFs (`AlderLake`, `MeteorLake`, `LunarLake`, `ArrowLake`) are absent from this worktree, though not needed here.
- `data/studies/13-errata-dispositions/raw/errata.csv`: columns `family,vendor,erratum_id,title,status,doc_number,revision`. This is the mined table, the rawest row-level record short of reparsing all PDFs.
- `data/studies/18-errata-by-year/launch_years.csv`: `family,vendor,launch_year,launch_date,...,source_quote,date_basis`, hand-checked against `launch_sources/`.
- Do not use `annual_counts.csv`, `revision_rows.csv`, `identifier_events.csv`, `range_expansions.csv`, `history_rows.json`, `family_year_counts.csv`, or any `summary.json`.

## Definitions
- Corpus: rows of `errata.csv`. Report total rows, distinct `(family, erratum_id)`, rows per family, family count, and for each vendor both family count and row count.
- Introduction range: min and max `launch_year` over the corpus families.
- Document mapping: `BroadwellEP.pdf` is Broadwell-EP, `IceLakeSP.pdf` is Ice Lake-SP, `Zen1Naples.pdf` is Zen 1 (Naples) and AMD Family 17h, `Zen5Turin.pdf` is Zen 5 (Turin) and AMD Family 1Ah.
- Revision row: one date, revision, and description entry in the table. Descriptions wrap across lines. Page headers and footers are not rows.
- Added identifier: an ID named in an "Added ..." clause. Expand `X to Y` and dash ranges inclusively. Trailing periods are not part of an ID. "Removed", "Updated", and "Modified" clauses add nothing, and an ID after "duplicate of" is not an addition. Initial-release rows add nothing.
- Annual count: added identifiers per document and calendar year of the row's date. Report list count and distinct count. Do not pool across documents.
- `years_without_rows`: for each document, calendar years from its first to its last listed year, inclusive, with no row. The prose total is the sum across documents.
- Family 17h revision span: `listed` is the number of listed revision numbers; `span` is the count of numbers from lowest to highest in steps of 0.01, inclusive.
- `continues_two_years`: last year with an addition minus `launch_year` is at least 2.
- Ice Lake-SP 2026: added identifiers in 2026 and the latest row's month. Turin: years with additions, and `launch_year`.

## Expected output
```json
{
  "corpus": {"rows": 0, "distinct_family_id": 0, "families": 0, "vendor": {"<vendor>": {"families": 0, "rows": 0}}, "by_family": {"<family>": 0}, "launch_year_min": 0, "launch_year_max": 0},
  "history": {"n_rows": 0, "n_documents": 0, "years_without_rows_total": 0,
    "documents": {"<document>": {"n_rows": 0, "added_total": 0, "added_distinct": 0, "first_year": 0, "last_year": 0, "launch_year": 0, "launch_date": "", "last_addition_year": 0, "continues_two_years_by_year": false, "continues_two_years_by_date": false, "years_without_rows": [0], "annual": {"<year>": {"rows": 0, "added": 0, "added_distinct": 0}}}}},
  "n_continuing": 0,
  "icelake_2026": {"added": 0, "through_month": ""},
  "turin_addition_years": [0],
  "family17h_revisions": {"listed": 0, "span": 0, "lowest": "", "highest": ""}
}
```

## Tolerance
All fields exact, because every value is a count of explicit identifiers or rows in fixed text. A difference of one identifier points to a range or clause parse and must be traced to the row.

## Ambiguities
- "Totals" could be list count or distinct identifiers when an ID is added twice. The prose says "identifiers explicitly listed as added". Report both.
- "At least two years after launch" does not say calendar-year difference or dated difference, and some launch dates carry only a year. Report both where possible.
- "[VALUE] years inside these histories" does not say whether the endpoints count or whether a calendar year missing from two documents counts twice. This spec counts per document.
- The parenthesis after "CPU families" most naturally counts families, not errata. Both are reported.
- "Itemized" is unclear on removed entries. Study 18's README says removed entries are excluded, and `status` in `errata.csv` has no removed value, so this rule cannot be tested from that file.
- This test reaches the mined table, not the PDF parse, for the corpus total.
