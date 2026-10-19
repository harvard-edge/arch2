# Editorial placement: published errata dispositions

Status: retain existing prose support; no new figure. Proposed October 17,
2026. See the [selection proposal](../../../integration/manage-work-tree/PLOT_INTEGRATION_PROPOSAL.md).

[Chapter 11](../../../book/contents/chapters/11-ownership/11-ownership.qmd)
already reports the 87.2-percent no-planned-fix statistic in “Capital Allocation
and Physical Qualification” (currently around line 350), with a qualification
about aggregating the least-resolved status across steppings. Adding this plot
would repeat that point and compete with the more direct ownership evidence
in Study 19's revision histories.

Keep the disposition paragraph as support for continuing obligations, subject
to the surrounding section revision proposed in
[Study 19's note](../19-errata-history/INTEGRATION.md). Preserve the distinctions
between document entries, stepping-specific status, workaround availability,
and deployed risk. “No planned fix” does not mean that every shipped device
exhibits the problem, that a workaround is unavailable, or that the entry is
an independently counted active defect.

Use the existing vendor-document citations only after matching exact retained
revisions in [source_manifest.json](source_manifest.json). The extraction and
revision limits are in [README.md](README.md). The chart
[figure.svg](figure.svg) and its PDF/PNG twins remain useful supporting material.
Reproduce with `python3 data/studies/13-errata-dispositions/collect.py`, then
`python3 data/studies/13-errata-dispositions/reproduce.py`. Do not count this
chart as a new chapter addition or duplicate the same statistic elsewhere.
