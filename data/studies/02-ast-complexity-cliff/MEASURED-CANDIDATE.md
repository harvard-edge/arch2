# Measured AST-complexity candidate

This candidate preserves the original `hardware_ast_complexity_gap.csv` and
`fig_ast_complexity_cliff.*` files unchanged. It provides an independently named
replacement for review before any manuscript integration.

## Evidence status

- Every row comes from a module declaration parsed from a retained public Git
  checkout at the full commit recorded in
  `hardware_ast_complexity_measured_sources.csv`.
- `source_path` and `source_sha256` identify the exact source file behind each
  measurement.
- `pyslang` 11.0.0 supplies a standalone, error-recovered SystemVerilog
  concrete syntax tree for each selected source file. This is a source-syntax
  measurement, not a fully preprocessed or elaborated design measurement.
- Parser diagnostics are file-level observations repeated on each module row
  from that file. Missing include files and unknown project-specific
  preprocessing directives therefore remain visible rather than silently
  excluding macro-heavy production RTL.
- The summary records the Python and parser versions, host operating system and
  architecture, miner hash, and extraction timestamp.
- Clock-event signal counts and CDC primitive mentions are lexical indicators,
  not verified clock-domain or crossing counts.
- Repository-internal hierarchy follows an instantiation only when its child
  module name has exactly one definition in the selected source corpus.
  Ambiguous duplicate definitions and unresolved external children are not
  followed. Ambiguous internal occurrences are retained in a separate column,
  so hierarchy depth remains a conservative lower bound on elaborated depth.

## Current measured result

The pinned corpus contains 217 AI-benchmark reference modules and 1,296
production-oriented open RTL modules. The module-weighted median concrete
syntax size is 168 nodes for benchmark reference RTL and 1,125 nodes for
production-oriented RTL, a measured 6.7× gap in these repositories. Median
clean source size differs by 6.2× (16 versus 99 lines).

Two sensitivity checks narrow that claim. Restricting the comparison to valid
trees from files with no parser diagnostics yields a 4.77× syntax-node gap.
Giving each repository equal weight through the median of repository medians
yields a 4.27× gap. The pooled 6.7× result is therefore not presented as a
universal ratio or as a corpus-balanced estimate.

All three comparisons support a substantial source-complexity difference in
the selected corpora, but not the original 175× claim. The hierarchy receipt
also shows that RTLLM contains some uniquely resolved local hierarchy, so the
original claim that all benchmark designs are flat is too strong.

## Reproduction

```bash
uv run --with pyslang==11.0.0 \
  python data/scrapers/mine_hardware_ast_complexity_real.py
uv run --with matplotlib --with numpy \
  python data/studies/02-ast-complexity-cliff/plot_ast_complexity_measured.py
```

The first command clones six pinned repositories into the gitignored
`data/scrapers/.cache/ast-corpus/` directory when needed. Pass `--offline`
to require existing checkouts.
