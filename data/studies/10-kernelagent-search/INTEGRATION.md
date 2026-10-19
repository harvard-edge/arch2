# Editorial placement: retained search histories

Status: companion only, proposed October 17, 2026. No manuscript edit.
See the [selection proposal](../../../integration/manage-work-tree/PLOT_INTEGRATION_PROPOSAL.md).

Chapter 3 defines a design loop by evidence changing the represented state and
the next action. Its stage diagram and prospective Lighthouse walkthrough
already perform that explanatory work. This plot shows candidate timing and
preservation of the best observed candidate, but it cannot reconstruct why a
measurement caused the next proposal. It would add a second example without
establishing the chapter's central mechanism.

The closest potential location is the Explore discussion in
[Chapter 3](../../../book/contents/chapters/03-lifecycle/03-lifecycle.qmd),
near the existing explanation of preserving a measured incumbent. Do not
insert it now or replace the lifecycle diagram. A companion exercise can ask
students to distinguish the most recent result from the best retained result
and identify what evidence is missing for a claim about adaptive search.

The retained records cover five curated tasks and one worker per round from a
four-worker search. Round 1 is not the original input baseline. Complete search
cost is unavailable, and three README values differ from the raw records.
Use the reconciled timing data; do not claim complete search efficiency,
causal feedback improvement, or advantage over conventional optimization.

The source is pinned at KernelAgent artifacts revision
`56cf9183b527307538ccbe8f554a88502918d2d1`; use the source URLs and hashes in
[source_manifest.json](source_manifest.json), [timings.csv](timings.csv), and
[README.md](README.md). The figure is [figure.svg](figure.svg), with PDF/PNG
twins. Reproduce with
`python3 data/studies/10-kernelagent-search/reproduce.py` from the repository
root. This rebuilds the analysis without running GPU kernels. Review the
upstream source-redistribution status before publishing retained code.
