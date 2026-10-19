# Editorial placement: interpreting regression failures

Status: companion case table, proposed October 17, 2026. No new chapter
exhibit. See the [selection proposal](../../../integration/manage-work-tree/PLOT_INTEGRATION_PROPOSAL.md).

The opening of [Chapter 7](../../../book/contents/chapters/07-feedback/07-feedback.qmd)
distinguishes an infrastructure failure from a design failure. This record
could replace a generic example there, but the chapter already contains a
formal-status table, a dynamic-check figure, and a failure-routing matrix.
The full triage table would repeat their function. Keep it as a companion
exercise on separating recorded events from diagnoses.

Two reports attached to [Ibex issue 2187](https://github.com/lowRISC/ibex/issues/2187)
contain 94/1,415 and 40/1,430 failing records. Different commits and seed
ranges prevent a before-and-after fix interpretation. The packet retains
45 explicit issue-author mappings, 32 from the first report and 13 from the
second. The remaining 27 failures in the second report are not assigned by
those mappings. These selected diagnoses are not a complete cause taxonomy
and were not independently verified.

If a brief prose example is later requested, state that the issue author
attributes observations to several components of the test system, then return
to the chapter's qualification procedure. Do not describe all failures as
RTL bugs, reproduce the full event table, or imply that a lower aggregate
count proves a fix worked. Use an issue-specific citation, not only the
general Ibex project reference.

Use [README.md](README.md), [run-results.csv](run-results.csv),
[failure-observations.csv](failure-observations.csv), and the retained issue
JSON linked by [source_manifest.json](source_manifest.json). Reproduce with
`python3 data/studies/22-ibex-triage/scripts/extract.py`. This packet has a case
table, not a finished figure. Preserve its distinction between report events,
explicit mappings, and unverified author explanations.
