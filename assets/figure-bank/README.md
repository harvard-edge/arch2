# Figure Bank

Receipted, generator-backed figures not currently referenced by the book.
Kept for future use (chapters, talks, revisions). Each figure's data receipt
and generator live under `data/source-receipts/`; regenerate from the
generator rather than editing the SVG.

| Figure | Data receipt | Generator | Candidate future use |
| --- | --- | --- | --- |
| `fig-conference-paradigm-shifts.svg` | `chapter1-conference-paradigm-shifts.csv` + `full-conference-corpus-1973-2026.csv` (10,327 rows, ISCA/MICRO/ASPLOS/HPCA scrape) | `plot_conference_shifts.py` | Strongest candidate: empirical support for the book's argued paradigm shift (ch1 epochs or ch2). Verify corpus numbers at wiring time. |
| `fig-mlperf-coevolution.svg` | `chapter10-mlperf-coevolution.csv` | `plot_mlperf_coevolution.py` | Panel B (2.05x software dividend on fixed silicon, MLPerf v2.1-v4.1) fits ch9's hardware-software co-evolution point. Verify against MLPerf results at wiring time. |
| `fig-reuther-precision-frontier.svg` | `chapter1-reuther-precision-frontier.csv` | `plot_reuther_frontier.py` | Alternate cut of the Reuther survey already used in ch2 (precision modes + memory-wall ceiling). The ~100 TOPS/W ceiling annotation needs sourcing before any book use. |
| `fig-llm-inference-pareto.svg` | `chapter2-llm-inference-pareto.csv` | `plot_llm_inference_pareto.py` | Talks only: vendor inference snapshots age fast and sit outside the book's durability rule. |
