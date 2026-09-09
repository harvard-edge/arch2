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

## Status, audited 2026-09-09

| # | Study | Class | Status | Open defects |
| --- | --- | --- | --- | ---: |
| 01 | Silicon errata archaeology | mined | defective | 5 |
| 02 | RTL source complexity | measured | **verified** | 0 |
| 03 | Fixed-silicon software dividend | transcribed | defective | 3 |
| 04 | Open silicon democratization | transcribed | defective | 3 |
| 05 | Hardware CVE mitigation tax | transcribed | defective | 2 |
| 06 | Placement seed dispersion | measured | defective | 2 |
| 07 | Design cost and R&D wall | mined | defective | 4 |
| 08 | Testbench mutation vacuity | — | **withdrawn** | RNG-generated |

Study 02 is the only clean one. Study 06's measured pilot and Study 07's SEC
financials are sound data underneath broken figures; the defects there are packaging
and plotting, not measurement.

## The manuscript is not affected

Verified 2026-09-09. No withdrawn or defective receipt is referenced anywhere in
`book/contents/`. This is structural rather than lucky:

```
data/studies/          -> www/data.qmd          (the website)
data/source-receipts/  -> book/contents/*.qmd   (the manuscript)
```

The studies feed the public data page. The book's figures read a different set of
`chapterNN-*.csv` receipts. **That second population has not been audited.**

## The four ways a number gets past a reader

Every defect found in this audit is one of these. They are listed in the order they
are hard to catch.

1. **Generated values with real tool metadata.** A receipt header names JasperGold,
   SymbiYosys and Verilator; the values came from `rng.gauss()`. Three datasets were
   withdrawn for this in September 2026.
2. **A real dataset under a hardcoded figure.** The script opens the CSV, then plots
   literal arrays. Studies 01, 03, 05 and 07 all do this. The data is fine and the
   picture is asserted.
3. **A headline that exists only as an annotation string.** `<1.8%` and `82x` are
   matplotlib text, not measurements. Both are contradicted by the data beneath them.
4. **Fabricated identifiers.** 27 commit hashes in Study 04 that resolve to nothing,
   and a forecast row in Study 07 carrying a real SEC accession number.

A fifth, weaker signal worth checking for: numbers that are internally consistent but
externally false. Study 01's containment figures sum to exactly 100% and disagree
with the data in every term.

## Why the existing validators pass all of this

`validate_provenance.py` never scans `data/studies/`, and treats a script mentioning
a CSV filename as proof the file was used. `validate_figure_provenance.py` accepts
any script containing a `.csv` string literal, and only reads `book/contents/`, never
`www/data.qmd`. Both report zero violations today.
