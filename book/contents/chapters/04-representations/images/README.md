# Chapter 4 Figure Inventory

Image-backed figures currently used by the chapter:

- `ch04-cover-map.svg`: chapter overview mapping source data to representations, execution traces, world models, and handoff contracts.
- `fig-architecture-data-progression`: the chapter's progression from
  heterogeneous source artifacts through checked data, durable knowledge and
  current state, linked representations, and method handoff.
- `fig-split-brain-causality`: stale reference state diverging from current
  project state.
- `fig-execution-history`: accepted and rejected work linked to the state and
  conditions that produced it.
- `fig-ch04-ast-complexity-cliff`: measured module syntax size and internal
  hierarchy, generated from `data/studies/02-ast-complexity-cliff/`.

Moved to Chapter 5 with their owning method material:

- `../../05-methods/images/F5-architecture-world-model`: separate paths for
  prediction and tool observation.
- `../../05-methods/images/F5c-macro-placement`: policy and reward loop for macro
  placement.

No longer referenced by the chapter (the observation-source table replaced it):

- `fig-observation-source-choice`: property-specific observation paths that preserve source,
  coverage, cost, conditions, and blind spots without imposing a universal
  fidelity order.

Executable figure:

- `fig-public-code-to-rtl`: the OpenRTLSet C/C++ collection path from
  permissively licensed repositories through the authors' synthesizability
  screen and successful Vitis HLS conversion.

Removed 2026-09-29: the orphaned `fig-architecture-data-scarcity` figure, its dataset,
and its generators, and `fig-ch01-money-plot-data-gap-funnel.png`. None was referenced
by the chapter and none was verified.

Removed 2026-09-29: `fig-hardware-representation-dilation` (definition-use token
distance). Its token counts and syntax-node counts could not be re-derived from the
pinned source files with a real parser, so the figure was not verifiable.
