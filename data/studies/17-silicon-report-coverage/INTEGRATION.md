# Editorial placement: public silicon evidence

Status: optional prose only, proposed October 17, 2026. There is no figure in
this packet. See the [selection proposal](../../../integration/manage-work-tree/PLOT_INTEGRATION_PROPOSAL.md).

Use the shared-data-schema discussion in
[Chapter 12](../../../book/contents/chapters/12-ecosystem/12-ecosystem.qmd),
after its explanation of schema interpretation and before implementation
access (currently around lines 96–102). The chapter's Tiny Tapeout shuttle
figure already illustrates access and participation. Another chart could
invite the mistaken reading that unreported projects failed on silicon.

Suggested prose, only if this example improves that section's continuity:

> Public silicon records also need explicit states for missing evidence.
> A retained TT06 index contains 238 macros, of which 69 have public feedback.
> The feedback entries do not consistently provide structured test dates,
> board or die identity, conditions, and measured results. Absence of a report
> therefore leaves the physical outcome unknown, while a community status
> label still requires its supporting test record.

There are 97 community feedback entries associated with the 69 macros. Keep
entries and macros distinct. Do not infer a working-chip rate from feedback
presence or treat community status labels as independently verified outcomes.
The existing chapter edits predate this review and should be assessed separately.

Use [README.md](README.md), [source_manifest.json](source_manifest.json), and
the retained capture manifest for exact index/API snapshots. Add source-specific
citations before insertion. Reproduce with
`python3 data/studies/17-silicon-report-coverage/extract.py`. The companion
record already contains the counts and missing-field analysis; no new plot
is needed to make the schema point.
