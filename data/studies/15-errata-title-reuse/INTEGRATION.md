# Editorial placement: related records and dataset splits

Status: optional prose only, proposed October 17, 2026. No manuscript edit.
See the [selection proposal](../../../integration/manage-work-tree/PLOT_INTEGRATION_PROPOSAL.md).

Chapter 4 already carries several empirical and conceptual exhibits. The
representation replacement in Study 23 is the stronger visual contribution.
This packet can ground the discussion of related rows without another chart.

Use [Chapter 4](../../../book/contents/chapters/04-representations/04-representations.qmd),
“Cleaning Logs and Preventing Train-Test Leakage,” between the sentence ending
“tests a different capability from holding out an operator family that never
appeared in training” and “Protected evaluation splits must therefore follow
the transfer claim” (currently lines 324–328).

Suggested connecting prose:

> Public errata records show why row identity alone may be insufficient.
> Of 1,774 retained entries, 1,093 share a normalized title with an entry in
> another processor family. Repeated wording identifies groups worth examining
> before splitting the dataset, although it does not establish a common defect
> or prove that a particular split leaks information.

Let the existing protected-split paragraph supply the prescription. Do not
repeat its argument in a new landing paragraph. Normalization uses Unicode
NFKC, case, and whitespace; punctuation and numbers are retained. Matching
titles are a screening signal rather than independent defects or common root
causes. The corpus is selected, not a population estimate of all chip errata.

Use [README.md](README.md), the normalized-title data, and the retained Study 13
vendor sources. Add the exact source revisions and the normalization method
to the citation/provenance trail before insertion. The chart
[figure.svg](figure.svg) and PDF/PNG twins remain in the companion.
Reproduction runs Study 13's collector and reproducer, followed by
`python3 data/studies/15-errata-title-reuse/collect.py` and
`python3 data/studies/15-errata-title-reuse/reproduce.py` from the repository root.
