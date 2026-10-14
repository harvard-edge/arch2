# Chapter 2 Figure Inventory

Active conceptual diagrams:

- `fig-architecture-levers`: five architectural scales and their comparison
  obligations, stacked from a warehouse-scale system at the top down to a core at the bottom (funneling outward as the boundary expands from core to warehouse-scale); hand-authored SVG.
- `ch2_tao_vs_taos`: specialization coupled to technology, architecture, and
  optimization.
- `fig-waterbed-effect`: an unscaled energy-dependency diagram, hand-authored
  SVG. It contains no numerical energy estimates.
- `fig-scissors-gap`: an unscaled generation, admission, evaluation, and review
  flow, hand-authored SVG. Backlog is conditional on
  admitted work exceeding completions; the diagram contains no numerical rates,
  empirical-looking curves, or assumed crossover with architectural scope.
- `fig-domain-specificity-shapes`: six stability conditions under which
  specialized silicon stays viable (moved from chapter 9).
- `fig-codegen-narrow-waist`: the executable software path from domain intent
  through the compiler narrow waist to verification checks (moved from chapter 9).

Generated figures with scripts (moved from chapters 7 and 9; datasets in
`data/datasets/`):

- `fig-microprocessor-trends`: the 1971–2021 CPU sample joined with the
  2012–2026 accelerator specification frontier; `generate_fig_microprocessor_trends.py`
  reads `chapter1-micro-trend.csv` and `chapter2-ai-accelerator-scaling-frontier.csv`.
  The CPU cutoff and mixed published power-rating boundaries are explicit.
- `fig-ch09-software-porting-wall`: CUTLASS, Triton, and vLLM code growth;
  `measure_software_porting_wall.py` (retained harness, rerun 2026-09-29) writes the
  `chapter9-{cutlass,triton,vllm}-*.csv` datasets and `generate_ch09_software_porting_wall.py`
  plots them. Triton is plotted as the union of selected source trees, including
  vendored headers, examples, and tests; repository moves do not support a stable
  shared-versus-backend split.
- `fig-ch07-wilson-verification-scissors`: Wilson Research / Siemens EDA
  verification-time share, first-silicon success, and staffing ratio (printed or stated
  values only; Collett rows and respin-cause panel removed 2026-09-29);
  `data/datasets/plot_wilson_scissors.py` reads
  `chapter7-wilson-verification-scissors-gap.csv`. The 2024 observations are separated
  from the historical lines because participant recruitment changed that year.
- `fig-cerebras-wse-scale`: `generate_fig_cerebras_wse_scale.py` draws separate
  area-proportional squares from published WSE and V100 areas. They are not
  mechanical outlines or a wafer-cutting layout.

The numerical LogCA phase diagram and its generator were removed: assumed
invocation costs were not measurements of the named interconnects. The chapter
retains the analytical break-even equations and explains the measurements needed
to apply them.

The static `fig-ch02-accelerator-scaling-frontier` compares dense FP16 peak
throughput, HBM bandwidth, and TDP for P100, V100, A100, H100, and B200 (2016–2024).

Executable Quarto figures in the chapter:

- `fig-accelerator-landscape`: the public AI-accelerator power/performance
  landscape.
- `fig-search-vs-eval-gap`: three published design-space scale anchors. No toy
  configuration count is plotted.
- `fig-silicon-cadence`: elapsed intervals between first public announcements,
  computed from dates rather than calendar-month indices.
- `fig-training-compute-growth`: growth in the displayed notable-model
  reported and estimated training-compute records; every fitted point is visible.
- `fig-data-movement-energy-scale`: Matplotlib data-movement energy scale plot.
- `fig-verification-demand-scissors`: verification and design staffing demand.
- `fig-design-cost-by-node`: leading-node design-cost estimates, separated by
  the vintage of the published estimate.

The earlier accelerator photo collage and promotional WSE photograph are not used.
