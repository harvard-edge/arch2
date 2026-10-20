# IREE CPU thread scaling varies by workload

## Claim and evidence class

**Evidence-backed, scoped to one historical IREE bot report:** In ten model/input configurations with the same reported IREE-LLVM-CPU backend and GCP c2-standard-16 / Cascade Lake labels, increasing the `local-task` group count from 1 to 4 lowers reported mean latency by 1.35×–3.14×. Moving from 1 to 8 groups yields 1.30×–5.08× speedups; nine of the ten reported means are lower at 8 than at 4. The relative response depends on the workload and model/input configuration.

This is evidence about one compiler/runtime setup and one historical benchmark report, not a general law about CPU threading. The report's categories classify PR-versus-base changes; this extraction instead compares the report's current-commit 1-, 4-, and 8-thread means. For example, the MobileNetV3Small fp32 mean is 3.3% higher at 8 than at 4 groups. That small reported difference is descriptive; it is not presented as a statistically established regression.

## What researchers can reuse or cite

The reusable result is the comparison method: hold the reported compiler backend, machine label, architecture, model/input, and default configuration constant, then retain each eligible workload's full thread-count response. The 10 workloads show why a single model cannot establish how a runtime responds to added worker groups. The figure can support a narrow discussion of workload-dependent runtime performance and benchmark selection; it does not identify the mechanism behind each curve or support claims about AI assistance, architecture quality, or current IREE performance.

Researchers can cite the upstream source directly as IREE GitHub Actions bot, “IREE Full Benchmark Result 1559,” October 3, 2022, Gist revision `e17830877c662d2e4caec8c68c64a52aaaa4a116`: [pinned report](https://gist.github.com/iree-github-actions-bot/536b0ea87b0be6e93adf4118de88a1b8/e17830877c662d2e4caec8c68c64a52aaaa4a116). The tested IREE commit is [91a524d6c77646eb18d12fb79ad0a62124e1f8d7](https://github.com/iree-org/iree/commit/91a524d6c77646eb18d12fb79ad0a62124e1f8d7), compared in the report with base `baf38ecc5f4496f85389bfb012afaac762006f75`.

## Data and configuration

The complete bot report is retained at `source/iree-full-benchmark-result-1559.md`; its immutable raw Gist revision and SHA-256 are recorded in `source_manifest.json`. The full report, including its GPU, CPU-Sync, and other result tables, is preserved. `latency_inventory.csv` inventories every row in its two average-latency tables and gives an inclusion or exclusion reason. `extracted.csv` retains all 30 selected rows, their source Markdown line IDs, the exact benchmark names and series URLs, current and base means, medians, and standard deviations.

The extraction includes every row in those two latency tables that has an explicit 1-, 4-, or 8-thread tag, the GCP-c2-standard-16 / x86_64-Cascade Lake labels, and the IREE-LLVM-CPU local-task backend. There are ten complete workload/input triples. CPU-Sync rows are retained in the inventory and excluded because they use the separate local-sync driver and have no matching local-task group-count tag. Other report tables are preserved in the full source but are outside this latency analysis.

The IREE source at the tested commit defines a shared Cascade Lake compile configuration and generates 1-, 4-, and 8-thread local-task cases using `--task_topology_group_count=1`, `4`, and `8`. The report labels the corresponding cases `1-thread`, `4-thread`, and `8-thread`; its device configuration says `all-cores`. The source runner defaults `benchmark_min_time` to zero, and its benchmark command requests ten repetitions for embedded-ELF cases. The pinned Buildkite pipeline invocation does not override that default. This establishes the requested repetition count in the retained configuration, but the bot report itself does not expose run-by-run samples.

## Transformation and limitations

`scripts/extract.py` parses the complete retained average-latency tables, preserves every thread-specific source row, and verifies the 30-row / ten-workload / three-thread-point balance. It separately retains the full 40-row latency inventory, including the ten CPU-Sync records and their exclusion reasons. `plot.py` divides each reported mean and standard deviation by the same workload's 1-thread mean. The plotted caps are each configuration's reported standard deviation on that scale; they are not confidence intervals and do not propagate uncertainty in the shared denominator. `plot_data.csv` preserves the derived values and source row IDs.

The perf.iree.dev series links timed out during collection, and the public Buildkite build page returned HTTP 403. The report's per-repetition JSON artifact was therefore unavailable; no independent rerun or raw-sample reconstruction is claimed. The report and configuration identify a machine type and architecture, not a physical host identity. No affinity, power, temperature, or cache-state evidence was recovered. The measurements do not explain why a model scales as it does, and this 2022 result should not be read as representative of later IREE versions or other CPUs.

## Figure handoff

**Caption.** **Thread-count gains vary by workload.** Across ten model/input configurations in one IREE LLVM-CPU report, 1-to-4-thread mean-latency speedups range from 1.35× to 3.14×, and 1-to-8-thread speedups range from 1.30× to 5.08×. Each panel normalizes mean latency to that workload's 1-thread mean; caps show the reported standard deviation, not confidence intervals. Source: IREE GitHub Actions bot report 1559, pinned Gist revision linked above.

**Alt text.** Line chart grid of ten IREE model and input configurations. Each panel plots mean latency as a fraction of its own one-thread mean at local-task group counts of one, four, and eight. Lower values mean lower latency. Most curves continue downward from four to eight groups; MobileNetV3Small rises slightly. Error caps show reported standard deviation, not confidence intervals.

**Candidate placement.** Chapter 10, “Evaluation,” as a short example of workload-dependent measured behavior and why evaluation should preserve workload identity across configuration comparisons. Use it only to illustrate benchmark reasoning; it does not evaluate an AI method.

## Reproduction

From the repository root:

```bash
python3 data/studies/26-compiler-thread-scaling/reproduce.py
```

The command verifies frozen hashes for retained primary sources, regenerates both CSV extracts and the normalized plot data, then emits SVG, PDF, and a 300-DPI PNG. `build_receipt.json` records source, script, shared-style, data, and figure hashes. `--refetch-missing` can retrieve only absent files from their pinned URLs; a hash mismatch stops collection.
