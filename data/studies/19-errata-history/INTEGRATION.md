# Editorial placement: errata revision histories

Status: proposed on October 17, 2026; no manuscript change applied. See the
[selection proposal](../../../integration/manage-work-tree/PLOT_INTEGRATION_PROPOSAL.md).

## Decision and chapter purpose

Make this Chapter 11's principal errata figure and move the existing subsystem
classification figure to supporting material. This replaces the chapter's
main errata exhibit rather than adding another. Chapter 11 concerns who owns
a decision, the evidence required before commitment, and responsibilities that
continue afterward. Document revisions fit that argument more directly than a
long comparison of subsystem shares.

## Placement and surrounding revision

Use [Sustaining Architectural Ownership](../../../book/contents/chapters/11-ownership/11-ownership.qmd#sec-sustaining-responsibility),
after the paragraph ending “Diagnostic capability therefore belongs in the
handoff to the team responsible for the deployed system” (currently line 386).
The following paragraph begins “Keeping that diagnostic capability sharp
requires deliberate practice.” Introduce the revision history, explain the
owner's response, then return to the skills needed for that response.

Earlier in “Capital Allocation and Physical Qualification,” move the subsystem
share figure and its extended classification discussion (around lines 338–348)
to companion material. Preserve a concise paragraph establishing that reported
limitations span multiple subsystems, supported by the source documents.
Retain the physical-qualification argument and the distinction between a
method claim and a product commitment. Preserve or tighten the existing
qualified disposition discussion; do not add Study 13's chart beside it.
Review the complete earlier section after the removal so its capital-allocation
argument still reaches the following decision criteria naturally.

Suggested lead-in at the new location:

> A processor's published errata record can continue to change after its
> introduction. The retained Ice Lake-SP specification history lists eight
> erratum identifiers added in 2026 through March, several years after the
> processor family's 2021 introduction. Three other selected histories also
> record additions during their documented periods.

Suggested caption:

> **Published errata histories continue to record additions after introduction.**
> The four panels count identifiers explicitly added in retained vendor revision
> histories, grouped by revision year. Document coverage and endpoints differ;
> shaded years fall outside the retained history. Additions date publication
> changes, not defect discovery. Incomplete initial inventories and an undated
> Broadwell removal prevent a common cumulative-defect interpretation.

Suggested landing:

> A new entry gives the owner a reason to check whether the affected condition
> occurs in the released configuration and whether an earlier recommendation
> depends on it. The record supports that review without establishing when
> the defect was discovered or how often it occurs. An unmarked year outside
> the retained history supplies no evidence that the design had no defects.

Then revise the next opening to connect these reviews to preserving diagnostic
practice, rather than introducing that responsibility a second time.

## Evidence and citation

Use [annual_counts.csv](annual_counts.csv), [revision_rows.csv](revision_rows.csv),
[identifier_events.csv](identifier_events.csv),
[final_id_reconciliation.json](final_id_reconciliation.json), and
[source_manifest.json](source_manifest.json). Forty retained history rows
distinguish additions, updates, and removals. Do not pool the families into a
cross-vendor trend or interpret additions as independent discovered defects.

Broadwell BDF92 is explicitly added but absent from the final inventory and
marked removed without a dated removal row. Ice Lake's early history is
incomplete, and the AMD histories also have gaps. None establishes a common
initial inventory. The figure therefore uses annual additions, not cumulative
inventories or launch-year defect-quality comparisons.

Use the existing bibliography keys `Intel2022XeonE5v4SpecUpdate`,
`Intel2026XeonScalableGen3SpecUpdate`, `AMD2023Family17h00hRevisionGuide`, and
`AMD2025Family1Ah00hRevisionGuide`. Verify their exact document revisions
against the manifest. The source PDFs are retained in Study 13; introduction
dates are sourced in Study 18. The derivation and its exclusions require a
link to this packet in the reproducibility material.

## Asset and integration checks

Use [figure.svg](figure.svg) with its PDF/PNG twins. The PNG was visually
inspected during this review. Reproduce from the repository root with
`python3 data/studies/19-errata-history/reproduce.py`, retaining the Study 13
PDF dependency and the Study 18 introduction-date sources.

Proposed chapter asset and label: `images/fig-ch11-errata-revisions` and
`fig-ch11-errata-revisions`. Alt text should describe four separate histories,
unequal coverage, and the eight Ice Lake additions in 2026 through March.
The figure is tall; inspect the rendered page before acceptance. Search all
references before retiring the old subsystem figure. Preserve its evidence
and methods in the companion rather than deleting them.
