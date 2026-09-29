# Chapter 5 Figure Inventory

Static figures used by the chapter (hand-authored schematics unless noted):

- `ch05-cover-map`: chapter opening map (schematic).
- `fig-role-method-map`: many-to-many relationship among engineering roles,
  method families, concrete techniques, inspectable outputs, and next checks.
- `fig-method-selection-guide`: conditional recipe for choosing direct
  evaluation, a conventional method, prediction, generation, optimization, or a
  justified composition from the limiting work.
- `fig-architecture-cost-model`: separate prediction and tool-observation paths.
- `fig-alphachip-placement`: sequential placement actions and weighted proxy
  feedback in the published reinforcement-learning placement framework.
- `fig-candidate-check-capacity`: analytical stage-utilization plot computed
  from the constructed parameters of `tbl-candidate-check-capacity`
  (regenerate with `generate_candidate_capacity_plot.py`).

Executable Quarto figures in the chapter:

- `fig-eval-fidelity-latency`: schematic tool-to-property matrix.
- `fig-ch05-kernel-funnel`: correct and correct-and-faster KernelBench one-shot
  results, read from `data/datasets/chapter5-kernelbench-funnel.csv`.
- `fig-ai-study-result`: recorded SCALE-Sim systolic-array study, read from
  `data/studies/ai_systolic_array_study/recorded/reference/study_results.json`.
- `fig-bayesian-optimization`: analytical Gaussian-process posterior and
  upper-confidence-bound acquisition over author-chosen points (schematic).
- `fig-rejection-bound-ceiling`: analytical curves of the screening speedup
  equation.

The `.pdf` files beside active SVG sources are generated print companions.
