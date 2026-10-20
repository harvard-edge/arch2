# Tiny Tapeout TT06 public feedback coverage

This bounded source study asks what can be counted from Tiny Tapeout's public
community silicon-feedback records for TT06. It does not assess silicon yield,
independently verify functionality, or treat absent feedback as a failed design.

## Finding

The frozen TT06 index contains 238 unique project macros. Tiny Tapeout's shuttle
page says the chips were received in November 2024. In the API snapshot collected
on 2026-10-16, 69 macros (29.0%) had at least one public community-feedback
record, and 169 (71.0%) had none returned. The latter group has unknown physical
state: the snapshot cannot distinguish untested macros from tests that were not
reported publicly.

Across the 69 macros with feedback, the API returned 97 entries: 80 labeled
`working`, 14 `partial`, and 3 `broken`. Those are community-entered status
labels and counts of feedback entries. They are not necessarily independent
test runs, and they do not establish how many distinct dies, boards, or testing
conditions were involved. A macro can have entries with different labels, so
status counts by macro are overlapping.

## Scope and unit

The population is every row in the public TT06 shuttle index at the captured
source revision. The analysis unit is one indexed project macro on TT06, keyed
by `(shuttle, macro)`. It is not a unique human designer, repository, or
conceptual project. All 238 rows are retained, including factory-test and
infrastructure macros; the source does not provide a defensible exclusion rule.

TT06 is an arrived shuttle: its official page lists chip receipt in November
2024. That establishes cohort delivery, not that every indexed macro was
individually tested.

## What the records contain

Tiny Tapeout's public app API returns per-macro feedback entries with a GitHub
username, one of three statuses (`working`, `partial`, `broken`), free-text
feedback, an owner flag, and an optional link. Its website implementation uses
the number of `working` entries as the checkmark count on the “Silicon proven”
page; that numeric column does not display counts for feedback labeled
`partial` or `broken`.
The per-macro endpoint was queried for all 238 indexed macros, retaining empty
arrays as explicit “no public feedback returned” observations.

The 97 entries include 24 nonempty optional links. The public feedback schema has no structured feedback-event timestamp,
chip/die/board identifier, standardized test-condition, or measured-value
fields, and it does not require a measurement artifact. The collection timestamp
dates this snapshot only; it does not date any feedback event. Free text or an
optional link may contain measurement details or artifacts, but the linked
pages were not followed and free text was not normalized as part of this count.
Those fields vary by entry and do not make the set a standardized test-record
corpus.

## Chart recommendation

A bounded supporting chart can show public-feedback presence for all 238 TT06
indexed macros (69 with at least one entry; 169 with none returned), alongside
the 97 entry labels (80 `working`, 14 `partial`, 3 `broken`). Label the first
panel “public feedback visible at collection” and the second “community-entered
feedback status.” State in the caption that unreported physical state is
unknown and the labels are not independent silicon validation. Do not call this
a silicon success rate, verification rate, yield estimate, or failure rate.

This chart can support a claim about the visibility of public community
feedback for one enumerated, arrived shuttle. It cannot support a claim about
how many TT06 macros were tested, functioned, failed, or passed under comparable
conditions.

## Reproduction

The retained raw snapshot is verified by the collector and consumed offline by
the extractor:

```sh
python3 data/studies/17-silicon-report-coverage/extract.py
```

The collector's default behavior checks every raw response against
`source_manifest.json` and `capture-manifest.json`. It restores a missing file
only by fetching its recorded URL into a temporary file and verifying the
frozen SHA-256 before installation; it rejects changed bytes and never refreshes
an existing snapshot. The explicit `--refresh --output <new-absent-directory>`
option captures a separate observation. The extractor reads only retained
bytes and refuses a hash mismatch.

`project-feedback.csv` gives one row per indexed macro. `feedback-records.csv`
gives the 97 API entries and marks timestamp, identity, conditions, and
measurement fields as unavailable in structured API fields. Free text and
optional links were not audited for such details. Full unmodified API response
bodies are retained under `raw/feedback/`; `capture-manifest.json` and
`source_manifest.json` record their URLs, byte lengths, HTTP statuses, and
SHA-256 hashes.
