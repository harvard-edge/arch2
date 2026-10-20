# Editorial placement: physical-flow accounting

Status: proposed on October 17, 2026; no manuscript change applied. See the
[selection proposal](../../../integration/manage-work-tree/PLOT_INTEGRATION_PROPOSAL.md).

## Decision and chapter purpose

Add one figure to Chapter 6. This is the second recommended addition.
The chapter teaches the environment that executes architectural experiments,
including failure handling, lineage, and resource accounting. It specifies
record fields but needs a measured example of their time boundaries. This
public run supplies one without duplicating the existing repeatability study.

## Placement and surrounding revision

Use [Execution Records](../../../book/contents/chapters/06-environments/06-environments.qmd#sec-execution-records),
after the resource-use list and the paragraph ending “weigh hardware
performance against the full cost of exploration” (currently line 419).
Place the figure before “The depth of record a study needs grows with how much
of the design the automated loop may change.” Keep the six-field schema and
the following discussion of lineage. Do not move the example into the
Lighthouse walkthrough; these are observations of a different design.

Suggested lead-in:

> A resource record is useful only when its time boundary is explicit. One
> retained LibreLane run for the `spm` design on IHP SG13G2 records 78 direct
> step intervals totaling 106.3 seconds. The enclosing `Run Test` action spans
> 108 seconds, while the complete CI job spans 288 seconds.

Suggested caption:

> **Physical-flow cost depends on the boundary being measured.** The upper
> panel shows the longest steps in one retained `spm`/IHP SG13G2 run; the lower
> panel compares summed direct-step time with the enclosing action and CI job.
> Detailed routing takes 25.8 seconds, the longest individual step. The intervals
> are nested and must not be added. Source: LibreLane workflow 37749124131,
> job 113223652131, completed October 8, 2026.

Suggested landing:

> The job total includes work outside the reported implementation steps.
> Adding it to the step total would count part of the execution twice, while
> reporting only routing would omit most of the job. An experiment therefore
> needs both the cost value and the boundary it covers. This one run illustrates
> that accounting requirement; it does not estimate the usual cost of a
> physical-design flow.

Then retain the existing transition from record depth to the amount of design
the automated loop can change. Avoid repeating the complete field list in
the new text. Convert number/unit pairs to the chapter's Quarto spacing.

## Evidence and citation

Use [stage-costs.csv](stage-costs.csv), [time_boundaries.json](time_boundaries.json),
[summary.json](summary.json), and [source_manifest.json](source_manifest.json).
The exact direct-step total is 106.292 seconds. Two nested antenna-process
intervals are excluded from that sum to avoid double counting. The retained
artifact has 915 entries. Process statistics cover 45 of 78 steps; missing
memory records for the other 33 are unknown, not zero.

Add a source-specific citation for the
[retained CI job](https://github.com/librelane/librelane/actions/runs/37749124131/job/113223652131)
and its artifact, with commit `36aa197408e1b6508fc4862b7758d21ec8853048`,
artifact identity, and archive hash from the manifest. The artifact may expire
upstream, so retain the local ZIP and extraction records. Do not label the
run a representative runtime distribution, an AI speedup, or a fully qualified
signoff. DRC/LVS results coexist with recorded constraint and coverage warnings.
Several individual tool version strings are unavailable.

## Asset and integration checks

The source bundle is [figure.svg](figure.svg), [figure.pdf](figure.pdf), and
[figure.png](figure.png). The PNG was visually inspected during this review.
Run `python3 data/studies/20-implementation-stage-costs/reproduce.py` from
the repository root to derive the figure from the retained artifact; see
[build_receipt.json](build_receipt.json) for packages and hashes.

Proposed chapter asset and label: `images/fig-ch06-flow-accounting` and
`fig-ch06-flow-accounting`. Alt text should give the three nested time totals.
The current figure is tall; inspect a book-scale render and, if necessary,
produce a more compact editorial derivative from the same rows. Keep the
source figure intact and retain all time-boundary qualifications.
