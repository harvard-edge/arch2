# Ibex regression triage record

This packet preserves [lowRISC Ibex issue 2187](https://github.com/lowRISC/ibex/issues/2187), its two attached regression reports, and the linked issue, pull request, and patches needed to inspect the author's explanations. The issue author reports local regressions and triage; this packet did not rerun the simulations or independently verify the reported diagnoses.

The report summaries reconcile exactly to the case rows in the attached logs:

| Run | Commit | Reported and parsed | Passed | Failed |
| --- | --- | ---: | ---: | ---: |
| First | `1449ed5ea8f3d03127f7c3624e635e132830367d` | 1,415 | 1,321 | 94 |
| Second | `3384bf4c421781a2f5129307b912ac586c784977` | 1,430 | 1,390 | 40 |

The issue explicitly maps 32 first-run test/seed pairs to its numbered
signatures. It expressly excludes four test families from that list and says
those failures were re-triaged in the second regression. The first report has
62 failed cases in those families. The second report has 12 failed cases in
those families; the issue explicitly maps those 12 and one additional
`riscv_debug_single_step_test` failure, for 13 second-run pairs total. The
remaining 27 second-run failures stay in the complete outcome and observation
tables, with their raw report evidence; they are not assigned issue signature
numbers by this packet.

`run-results.csv` retains every pass and failure from both report summaries.
`failure-observations.csv` retains every failed case, its report detail block's
first raw failure line, and any heading supplied by the report. These are
observed report events. They are not a count of unique causes and do not imply
an RTL defect. `issue-explicit-mappings.csv` contains only test/seed pairs
explicitly linked to numbered signatures in the issue body. `retriaged-groups.csv`
reconciles the four expressly excluded test families across the two reports;
the runs use different commits and seed ranges, so these counts do not support
a causal before/after claim.

The issue author's explanations attribute most failures to test generation,
environment, testbench, simulator, coverage, checker, or co-simulation behavior,
and describe one possible low-concern RTL behavior. These remain author-reported
diagnoses. The record preserves unresolved outcomes and distinctions in the
source rather than relabeling every failing test as an RTL bug.

Regenerate the derived CSV files offline from the preserved sources with:

```sh
python3 data/studies/22-ibex-triage/scripts/extract.py
```

The extractor uses only the Python standard library. It checks the parsed
pass/fail totals against each report summary, requires a detailed block for each
failed case, and checks that every explicit issue mapping names a failed case.
It deliberately does not infer causes from log strings.

`source_manifest.json` is the canonical path/hash/URL manifest consumed by the
shared evidence-bundle verifier. `source-manifest.csv` is retained as a readable
companion. GitHub's issue and pull request content is retained as raw JSON; the
issue body Markdown is derived from the retained issue API JSON; regression
attachments are retained byte-for-byte as downloaded.

To verify or recover missing pinned sources, run:

```sh
python3 data/studies/22-ibex-triage/collect.py
```

The collector verifies existing bytes before writing. It stages missing network
downloads and checks their manifest hashes before installing them. The issue
body is regenerated from `source/issue-2187.json`, never scraped from the HTML
issue page. To regenerate the outcome tables and build receipt offline, run:

```sh
python3 data/studies/22-ibex-triage/scripts/extract.py
```

A case-level table is the appropriate representation for this record. The
issue maps a selected set of individual test identifiers to numbered
signatures, while the logs report all outcomes and some second-run cases remain
unmapped to an issue signature. A compact aggregate plot would conceal that
selection difference and would invite false comparisons across distinct
commits and seeds. The complete case tables keep the explicit mappings, raw
observations, passes, failures, and unresolved cases inspectable.
