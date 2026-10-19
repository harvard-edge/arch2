# Editorial placement: latency contracts

Status: proposed on October 17, 2026; no manuscript change applied. This note
supersedes the broader placement suggestion in the packet README. See the
[selection proposal](../../../integration/manage-work-tree/PLOT_INTEGRATION_PROPOSAL.md).

## Decision and chapter purpose

Add one figure to Chapter 2. This is one of the two recommended additions.
The chapter explains why workload assumptions and service requirements belong
in an architectural comparison. Its specialization diagram names quality of
service, but the adjacent discussion does not measure its consequence. These
paired public submissions provide that concrete example. They do not establish
an advantage for an AI design method.

## Placement and surrounding revision

Use [Changing Software and Fixed Hardware](../../../book/contents/chapters/02-pressures/02-pressures.qmd#sec-software-changes-faster-than-silicon),
after the paragraph ending “tracking the assumptions behind a design decision
tells the team which measurements an update requires” (currently line 373).
The next paragraph begins “Recent AI workloads illustrate how quickly both
model structure and compute scale can cross those boundaries.”

Keep the specialization diagram and the following compute-growth evidence.
Introduce the service-contract example as one measured consequence of the
listed assumptions, then return to model and workload change. Do not add a
new subsection or repeat the chapter's later benchmark-comparability discussion.
Read the whole section after insertion; it already contains several figures.

Suggested lead-in:

> The service contract can change the usable operating point even when the
> named model and accelerator remain the same. Nineteen matched pairs from
> MLPerf Inference v5.0 report Llama 2 70B throughput under standard and
> interactive latency limits. The interactive submissions deliver between
> 42.0 and 63.9 percent of their paired standard throughput, with a median of
> 58.8 percent.

Suggested caption:

> **Tighter latency contracts accompany lower throughput in paired public
> submissions.** The panels show the standard and interactive limits and
> interactive throughput normalized to each standard result. The 19 pairs
> match reported system metadata for closed, one-node, eight-accelerator
> Llama 2 70B Server submissions in MLPerf's 99-percent accuracy category. The
> comparison describes submitted operating points; it does not isolate the
> latency limits from serving configuration.

Suggested landing:

> These results show why an architect must retain the service contract
> alongside a throughput measurement. The published pairs do not hold every
> batching and scheduling choice fixed, so they cannot assign the entire
> difference to the latency limits. They do show that the standard result
> cannot stand in for performance under the interactive contract.

Then revise the next opening to connect service requirements to model changes,
for example, “Model changes can cross the other specialization boundaries just
as quickly.” Preserve the existing technical explanation that follows.

## Evidence and citation

Use [paired_throughput.csv](paired_throughput.csv), [summary.json](summary.json),
and [source_manifest.json](source_manifest.json). The 38 raw logs reconcile
with the selected summary rows; 19 system records support pairing. The limits
are 2,000 versus 450 ms to first token and 200 versus 40 ms per output token.
Use nonbreaking unit spacing when transferring these values into Quarto.

Add a source-specific bibliography entry for the
[pinned MLCommons v5.0 results](https://github.com/mlcommons/inference_results_v5.0/blob/0bc17ab3f4b33f730d7869e04cc29cb70835e513/summary_results.json)
at revision `0bc17ab3f4b33f730d7869e04cc29cb70835e513`. A general MLPerf
methodology citation does not source these observations. Cite this study's
derived pairing method as well. Different accelerator families use different
precisions; the figure makes within-pair comparisons. The 19 submissions are
not 19 independent controlled experiments.

## Asset and integration checks

The source bundle is [figure.svg](figure.svg), [figure.pdf](figure.pdf), and
[figure.png](figure.png). The PNG was visually inspected during this review.
Reproduce from the repository root with
`python3 data/studies/12-mlperf-latency-contract/reproduce.py`; dependencies
and exact output hashes are recorded in [build_receipt.json](build_receipt.json).

Proposed chapter asset and label: `images/fig-ch02-latency-contract` and
`fig-ch02-latency-contract`. Alt text should state the two latency-limit pairs
and the 42.0–63.9-percent throughput range. Add the exact source citation before
integration, preserve the frozen packet, and inspect the rendered chapter for
figure size and continuity with the two neighboring exhibits.
