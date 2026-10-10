# Chapter Datasets

This directory contains source snapshots, chapter datasets, and plotting scripts.
The current book-figure inventory is [provenance.yml](provenance.yml). It records
which figures use each input, their evidence class, and current CSV row counts.
A file's presence in this directory does not establish that the book uses it or
that every value has been independently verified.

## Current evidence inventory

`figure_evidence` maps each active figure label to an explicit evidence class:

| Class | Meaning | What it does not establish |
| --- | --- | --- |
| `measured` | Values produced by an executed parser, simulator, or measurement harness; retained input/output paths are named | Silicon behavior, generalization, or independent replication |
| `transcribed` | Source-attributed values, specifications, or published counts, sometimes with derived arithmetic | Independent confirmation of the source's result |
| `analytical` | A stated equation evaluated under declared assumptions | A measured outcome or implementation-specific magnitude |
| `conceptual` | A diagram explaining relationships or workflow | Empirical evidence or measured scale |

The `receipts` list indexes current input files and their `feeds_figures` links.
Historical audit findings and revalidation notes are retained with each record;
`historical_findings` is not a list of current unresolved book errors.
`retired_receipts` preserves the audit history of removed inputs without keeping
the withdrawn numerical data in the release tree. A `verified` status applies
only to the checks and scope described in that record.

Most source-attributed datasets carry URLs, citations, extraction notes, or
source fields in the CSV. Measured studies carry fuller provenance in
[`data/studies/`](../studies/README.md). Follow those records to pinned repository
commits, source-document versions, raw outputs, dependencies, and reproduction
commands. Counts derived from public source trees describe the counted files;
they do not measure engineering effort. Simulator returns describe a configured
model and workload; they are not silicon measurements.

## Validation

```bash
python3 data/validate_provenance.py
python3 data/validate_figure_provenance.py
```

The dataset check verifies listed input paths and CSV row counts, screens selected
metadata patterns, and prevents known withdrawn artifacts from returning. It
also reports files without recognized inline metadata; raw tool reports can be
covered by separate study records.

The figure check requires an explicit declaration for every active figure,
checks declared input and generator paths, and resolves bibliographic keys.
Internal figure, table, and equation references are not treated as citations.
SVG and raster formats do not determine evidence class. Neither check executes
the plots, verifies dataflow, compares every value to a primary source, or
certifies the manuscript's numerical claims.

## Withdrawn material

The October 2026 release cleanup removed the twelve obsolete `chN_data.csv`
files, their `plot_chN.png` outputs, the disabled `plot_all_wishlist.py`, and two
obsolete Chapter 1 funnel datasets. The illustrative LogCA input table was also
removed with its numerical figure. See [the withdrawal record](PROVENANCE.md)
and [study history](../studies/README.md#withdrawn-predecessors).

The inventory covers active manuscript figures. Other retained source or legacy
files are not certified merely by sharing this directory; their status must be
assessed before reuse.
