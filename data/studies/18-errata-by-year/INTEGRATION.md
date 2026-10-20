# Editorial placement: errata by processor introduction year

Status: supporting material only, proposed October 17, 2026. No manuscript
edit. See the [selection proposal](../../../integration/manage-work-tree/PLOT_INTEGRATION_PROPOSAL.md).

This is the requested historical view of the selected 19-family corpus. It
places retained document counts against processor introduction years. It does
not answer whether chip quality improved or deteriorated over time: product
scope, disclosure practice, document age, revisions, and exposure differ.

Do not add it to [Chapter 11](../../../book/contents/chapters/11-ownership/11-ownership.qmd).
Study 19's explicit document histories support continuing ownership more
directly. A second year-based errata figure would add visual weight without
resolving the cross-family comparison problem. Retain this view and its
launch-year source archive as support for the introduction markers in Study 19.

If shown separately in a talk, introduce it as an index of selected documents,
not a defect trend. Keep combined-family scopes visible and preserve partial
date precision. Do not fit a temporal trend line or normalize by an invented
exposure denominator.

Use [README.md](README.md), the introduction-date sources, and the Study 13
vendor-document corpus. The asset is [figure.svg](figure.svg), with PDF/PNG
twins. Reproduce with `python3 data/studies/18-errata-by-year/collect.py`, then
`python3 data/studies/18-errata-by-year/reproduce.py`. Retain each date's source
URL, excerpt, and hash. A processor introduction date is not the date when
an erratum was discovered or published.
