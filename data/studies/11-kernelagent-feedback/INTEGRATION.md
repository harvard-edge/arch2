# Editorial placement: interpreting hardware counters

Status: optional prose only, proposed October 17, 2026. Keep the figure in the
companion. See the [selection proposal](../../../integration/manage-work-tree/PLOT_INTEGRATION_PROPOSAL.md).

Chapter 7 already contains a measured systolic-array case and a defect/mutation
figure. Another three-panel performance exhibit would crowd its progression
from qualified observation to diagnosis and next action. A short counterexample
could nevertheless make one diagnostic distinction concrete.

Use [Chapter 7](../../../book/contents/chapters/07-feedback/07-feedback.qmd),
“Outcome, Mechanism, and Counterfactual Reasoning,” after “Useful observations
include performance-counter deltas, cycle-accurate stall breakdowns…” (currently
around line 497). Read that whole section and use the following as a replacement
for a generic example if one can be removed, rather than adding a new subsection.

> Achieved occupancy is one such diagnostic. In retained KernelAgent profiles,
> the selected MaxPool 3D candidate reduces reported time from 5.216 to
> 2.436 milliseconds while occupancy falls from 73.29 to 57.18 percent.
> The selected matrix–vector candidate instead combines lower time with higher
> occupancy. The counters help distinguish the cases; they do not isolate
> which code change caused the timing difference.

Add a source-specific citation for the pinned artifacts before using this
text, and apply Quarto unit spacing. The comparison selects the minimum-time
candidate among eight retained rounds for each of five curated tasks. Timing
uncertainty is unavailable, and profiler records do not identify the executed
kernel by hash. Do not describe the small RMSNorm difference as an established
gain, occupancy as a universal objective, or the pairs as a causal ablation.

Use [paired_metrics.csv](paired_metrics.csv), [source_manifest.json](source_manifest.json),
and [README.md](README.md). The asset is [figure.svg](figure.svg) with PDF/PNG
twins; its PNG was visually inspected in this review. Reproduce with
`python3 data/studies/11-kernelagent-feedback/reproduce.py`. Plotting uses the
packet's retained data; collecting the subset depends on Study 10. No new
hardware execution or causal validation is implied by reproduction.
