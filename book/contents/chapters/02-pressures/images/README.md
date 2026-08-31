# Chapter 2 Figure Inventory

Active hand-authored figures:

- `F2-architecture-levers`: comparison obligations accumulated from a core to
  a warehouse-scale system.
- `ch2_tao_vs_taos`: specialization coupled to technology, architecture, and
  optimization.
- `F2-bottleneck-causal-loop`: a reinforcing cycle in which missing information
  wastes evaluation and overloads review.
- `F2-waterbed-effect`: an illustrative system energy reversal when a local
  compute gain increases memory and interconnect cost.
- `F2-scissors-gap`: architecture complexity versus tool/feedback limits.
- `fig-domain-specificity-shapes`: six stability conditions under which
  specialized silicon stays viable (moved from chapter 9).
- `fig-codegen-narrow-waist`: the executable software path from domain intent
  through the compiler narrow waist to verification checks (moved from chapter 9).

Generated figures with scripts (moved from chapters 7 and 9; receipts in
`data/source-receipts/`):

- `fig-ch09-logca-phase-diagram`: LogCA break-even frontiers across interconnect
  regimes; `generate_ch09_logca_phase_diagram.py` reads
  `chapter9-interconnect-logca-specs.csv`.
- `fig-ch09-software-porting-wall`: CUTLASS, Triton, and vLLM code growth;
  `generate_ch09_software_porting_wall.py` reads the `chapter9-{cutlass,triton,vllm}-*.csv`
  receipts.
- `fig-ch07-wilson-verification-scissors`: Wilson Research / Siemens EDA
  schedule share, first-silicon success, and respin causes;
  `data/source-receipts/plot_wilson_scissors.py` reads
  `chapter7-wilson-verification-scissors-gap.csv`.

Executable Quarto figures in the chapter:

- `fig-microprocessor-trends`: frontier microprocessor trends and the end of
  frequency scaling.
- `fig-ch02-accelerator-scaling-frontier`: 14-year AI accelerator scaling vectors,
  memory bandwidth, TDP, and arithmetic ratio collapse (2012-2026).
- `fig-accelerator-landscape`: the public AI-accelerator power/performance
  landscape.
- `fig-search-vs-eval-gap`: design-space scale anchors.
- `fig-apple-silicon-cadence`: hardware release intervals.
- `fig-training-compute-growth`: growth in the displayed notable-model
  training-compute records.
- `fig-data-movement-energy-scale`: Matplotlib data-movement energy scale plot.
- `fig-verification-demand-scissors`: verification and design staffing demand.
- `fig-design-cost-composition`: leading-node design-cost estimates and their
  published composition.
