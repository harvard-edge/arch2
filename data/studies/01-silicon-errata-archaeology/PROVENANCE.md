# Provenance — Study 01, Silicon Errata Archaeology

**Evidence class:** Mined from primary vendor documents
**Dataset status:** Verified
**Figure status:** Two panels contain unsupported values, see Known defects
**Last independently verified:** 2026-09-09

## The claim this study supports

Post-silicon defects concentrate at subsystem integration seams rather than in
arithmetic logic. Across 19 commercial CPU families, 93.2% of itemized errata fall
outside the execution units, which is the part of a processor that AI hardware
benchmarks are almost entirely built from.

## Where the data comes from

Nineteen vendor specification updates and revision guides, downloaded directly from
Intel and AMD. These are the documents each vendor publishes to disclose known
silicon defects in a shipping part.

| Field | Value |
| --- | --- |
| Population | 1,771 itemized errata |
| Families | 19, Broadwell-EP through Arrow Lake, Zen 1 through Zen 5 |
| Vendors | Intel (15 documents), AMD (4 documents) |
| Coverage | 2016 to 2026 |

Per-row provenance columns: `source_doc_id`, `source_doc_url`, `source_doc_sha256`.
Every erratum carries the vendor document number it came from, the URL it was fetched
from, and the SHA-256 of that PDF at fetch time. The document hashes are also listed
in the CSV comment header.

## How it was mined

```bash
python3 data/scrapers/scrape_intel_amd_errata.py
```

The scraper fetches each specification update PDF over the network, hashes it,
extracts the erratum table, and classifies each entry into one of nine subsystem
categories. It does not synthesize any value.

## What is verified, and how

Recomputed from the raw CSV on 2026-09-09, skipping the 25-line comment header:

| Quantity | Claimed | Recomputed |
| --- | ---: | ---: |
| Itemized errata | 1,771 | 1,771 |
| Processor families | 19 | 19 |
| Memory hierarchy | 31.3% | 31.28% |
| PCIe / CXL / platform IO | 16.5% | 16.49% |
| Virtualization / MMU / IOMMU | 16.1% | 16.09% |
| Debug / trace / telemetry | 13.9% | 13.95% |
| Execution units / ALU | 6.8% | 6.83% |
| Power / DVFS / clocking | 6.6% | 6.61% |
| Escapes outside execution units | 93.2% | 93.17% |

The nine categories sum to 1,771 exactly. Both vendor source URLs spot-checked on
2026-09-09 resolve (HTTP 200).

## What is NOT verified

The nineteen source PDFs have not been re-parsed from scratch to audit the
extraction regexes in the scraper. A parser error would produce a
self-consistent but wrong taxonomy, and nothing above would catch it. This is the
single largest open risk in this study.

## Known defects

1. **The "< 1.8% pure integer ALU" claim is not supported.** It appears as an
   annotation string at `plot_errata_subsystem_sunburst_and_decay.py:195`. The
   dataset's finest granularity is `Execution Units / ALU` at 6.83%, and no row
   mentions an ALU, integer unit or adder in its title. Use 6.8%. The 93.2% seam
   figure is the complement of 6.83% and is unaffected.
2. **The stepping decay panel is hardcoded.** `step_pct_new = np.array([66.4, 18.2,
   8.8, 4.6, 2.0])` at line 114, with an exponential fit drawn through it. The CSV
   contains no stepping column, so this panel cannot be derived from the published
   data and must be either removed or backed by a real stepping dataset.
3. **The mask cost curve is hardcoded.** `mask_costs` and `derate_penalties` at
   lines 463 and 464 are in-script literals with no cited source.

## Files

| File | Role |
| --- | --- |
| `granular_processor_errata_taxonomy.csv` | Primary receipt, 1,771 rows |
| `hardware_errata_longitudinal_summary.csv` | Per-family rollup, 19 rows |
| `plot_errata_subsystem_sunburst_and_decay.py` | Figure generator, see defects 2 and 3 |
| `../../scrapers/scrape_intel_amd_errata.py` | Miner |
