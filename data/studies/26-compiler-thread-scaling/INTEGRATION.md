# Editorial placement: workload-dependent thread scaling

Status: companion or tutorial exercise, proposed October 17, 2026. No new
book figure. See the [selection proposal](../../../integration/manage-work-tree/PLOT_INTEGRATION_PROPOSAL.md).

The retained IREE report gives ten workload/configuration triples at one,
four, and eight threads. It shows that a shared thread-count choice produces
different scaling across workloads. Chapter 9 already makes workload-dependent
software effects concrete with its MLPerf example. This older report would
repeat that point without supplying a controlled transfer study. Chapter 10
could use it for an exercise on normalization and uncertainty, but it does
not fill the chapter's need for complete-workflow evaluation.

Keep the five-by-two plot in the companion. A useful lab asks students to
recover the selected rows, explain excluded configurations, and distinguish
reported variability from uncertainty about an estimated mean. The plotted
error bars use reported standard deviations normalized by each one-thread
mean; they are not confidence intervals.

Use [README.md](README.md), [source_manifest.json](source_manifest.json),
[latency_inventory.csv](latency_inventory.csv), and [extracted.csv](extracted.csv).
The source is one 2022 benchmark-bot report for a GCP c2-standard-16
Cascade Lake configuration, using the LLVM CPU local-task path. Individual
timing samples and exact host identity are unavailable. There was no
independent rerun. Do not claim an AI effect, general scaling law, or
architecture-quality advantage.

The asset is [figure.svg](figure.svg), with PDF/PNG twins; its PNG was visually
inspected during this review. Reproduce with
`python3 data/studies/26-compiler-thread-scaling/reproduce.py` and cite the
immutable raw report revision in the manifest. Retain the complete report and
row-selection inventory so later readers can reconstruct the comparison.
