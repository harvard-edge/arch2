# Chapter 9 Figure Inventory

Figures used by the chapter (checked 2026-10-10; MLPerf entry revised 2026-11-02):

- `ch09-cover-map.svg`: schematic chapter overview; source units carried,
  updated, replaced, or retired under changed conditions.
- `fig-transfer-test-flow`: schematic transfer test, from admission check through
  transfer units, changed dependencies, target actions, and target checks.
- `fig-ch09-mlperf-software-dividend`: MLPerf Training time-to-train ratios
  with 95% bootstrap intervals for NVIDIA submissions listing eight
  H100-SXM5-80GB GPUs, from the v2.1 preview submission to v3.0 available
  submissions. `../data/analyze_mlperf_h100_runs.py` computes ratios and
  intervals from the per-run logs in `../data/mlperf-h100-runs.csv` and writes
  them to `../data/fig-ch09-mlperf-software-dividend.csv`.
  `../data/plot_mlperf_software_dividend.py` plots that CSV and emits SVG, PDF,
  and 300 DPI PNG twins. The CSV keeps result IDs and source URLs.

## MLPerf source reconciliation

The CSV transcribes the official tables linked from the archived MLCommons
[v2.1 results](https://mlcommons.netlify.app/en/training-normal-21/) and
[v3.0 results](https://mlcommons.netlify.app/en/training-normal-30/) pages.
Three rows were retrieved October 10, 2026 and three November 2, 2026; both
sheets were refetched and retained under `../data/mlperf-h100-sources/` on
November 2, 2026. Times are minutes at the precision published in those tables.
Each row uses eight GPUs, so dividing the per-accelerator normalized times
yields the same ratio as dividing the server times.

The published table has no spread, so `../data/collect_mlperf_h100_runs.py`
reads all 150 result logs at pinned commits, including three aborted runs, and
`../data/analyze_mlperf_h100_runs.py` rescores them under the MLPerf rules.
Rule scores match all 12 published times to three decimals, one of them only
after that submission's `scaling.json` factor. The figure's ratio divides
unscaled times, so the table below separates the published ratio from the
plotted one. Computed columns are in `../data/mlperf-h100-spread.csv` and
`../data/mlperf-h100-pairs.csv`.

The plotted intervals resample converged runs and hold each set's count of
aborted runs at the submitted value. Those two files also resample all submitted
runs. An invalid set has no result under the rules, so a draw that holds one has no
comparison: 5,294 of 20,000 draws for BERT, 5,170 for ResNet-50, and 5,195 for
Mask R-CNN (`no_comparison_draws`). Those draws get no value. Any pair containing
one of these workloads therefore depends on how aborted runs are handled, and no
lead is claimed for it, BERT included. What the published times and valid runs
show is reported as such.

| Workload | v2.1 result ID | v2.1 time (min) | v3.0 result ID | v3.0 time (min) | Published ratio | Plotted ratio (95% interval) |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| BERT | 2.1-2091 | 6.378 | 3.0-2064 | 5.469 | 1.166 | 1.166 (1.113 to 1.246) |
| RNN-T | 2.1-2091 | 18.202 | 3.0-2064 | 16.686 | 1.091 | 1.091 (1.038 to 1.143) |
| 3D U-Net | 2.1-2091 | 13.101 | 3.0-2062 | 12.103 | 1.082 | 1.082 (0.932 to 1.258) |
| ResNet-50 v1.5 | 2.1-2091 | 14.746 | 3.0-2062 | 13.601 | 1.084 | 1.080 (1.078 to 1.089) |
| Mask R-CNN | 2.1-2091 | 20.348 | 3.0-2064 | 19.180 | 1.061 | 1.061 (1.060 to 1.064) |
| RetinaNet | 2.1-2091 | 38.050 | 3.0-2064 | 37.009 | 1.028 | 1.028 (1.026 to 1.034) |

[NVIDIA's account](https://developer.nvidia.com/blog/breaking-mlperf-training-records-with-nvidia-h100-gpus/)
attributes the gains to software optimization. It reports 17% for BERT, 8.4% for
ResNet-50, 8.2% for 3D U-Net, and 6.1% for Mask R-CNN. Its text gives no RNN-T
percentage, although its Figure 1 plots an RNN-T gain as a bar, and for RetinaNet
it says only that per-accelerator performance was enhanced, while listing improvements of 10%, 10%, and up to 7.5% that its text does not
scope to eight GPUs. That attribution is distinct from the published time
comparison. The v2.1 preview system record names the GPU model and count but
omits host-memory capacity and detailed software versions, and the records of
both rounds leave clocks blank. The preview record gives the
same core count and operating system as v3.0, and the logs of both rounds state
the platform as 1xNVIDIA DGX H100. Matching these fields does not independently
establish identical complete machines or isolate a compiler effect. Each row's
CSV metadata links both system descriptions.

The earlier A100 panel is excluded. Its NVIDIA blog source cites v2.0
partner results on different host configurations and, for several workloads,
80 GB A100 GPUs with a 500 W power limit, whereas the v0.7 NVIDIA results used
40 GB A100 GPUs at 400 W. Those comparisons cannot support an unchanged-hardware
software-gain claim. The chapter makes no cross-generation hardware comparison.

Removed 2026-09-29: `generate_logca_offload_plot.py` and
`logca_offload_break_even.png`, an unreferenced plot built from hand-typed
interconnect parameters with no recorded source.
