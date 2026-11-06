# Spec 05: RTL syntax gap and its sensitivity

## Claim
`book/contents/chapters/04-representations/04-representations.qmd:595` (caption): "(a) Syntax nodes and tokens per module separate benchmark reference RTL (median [VALUE]) from production-oriented open RTL (median [VALUE]), a [VALUE]$\times$ module-weighted gap that falls to [VALUE]$\times$ without files with substantive parser diagnostics. (b) Modules referencing local children rise from [VALUE]% in VerilogEval and [VALUE]% in RTLLM to [VALUE]%–[VALUE]% across production-oriented repositories, with source-reference depths up to [VALUE] [...]"

`book/contents/chapters/04-representations/04-representations.qmd:597`: "Benchmark reference modules carry a median of [VALUE] syntax nodes, whereas the pooled production-oriented modules reach [VALUE], a [VALUE]$\times$ difference weighted toward OpenTitan, which supplies [VALUE]% of those modules. Repository medians are [VALUE] for VerilogEval and [VALUE] for RTLLM, against [VALUE] for VeeR EH1, [VALUE] for CV32E40P, [VALUE] for OpenTitan, and [VALUE] for BlackParrot. VeeR EH1 thus falls below RTLLM because two library files supply [VALUE]% of its modules; without them its median rises to [VALUE]. The [VALUE]$\times$ ratio between the group medians of those repository medians [...] [VALUE]% of the production-oriented modules come from files with parser diagnostics. Removing every file with a diagnostic other than a missing final newline lowers the pooled ratio to [VALUE]$\times$ and drops all [VALUE] BlackParrot modules, but that filter removes the larger production-oriented modules (median [VALUE] against [VALUE]) [...] Adding each repository's HDL source directories to the include path repairs many of those parses and raises the pooled ratio to [VALUE]$\times$ [...] whereas [VALUE]% to [VALUE]% of the modules in each of the four production-oriented repositories reference a uniquely defined local submodule, in chains that reach [VALUE] levels even though the median production-oriented module sits at depth [VALUE]."

## Raw inputs
- `data/studies/02-ast-complexity-cliff/hardware_ast_complexity_measured.csv`, one row per module. Column meanings are in the study README section 4. The parsed repositories are not retained, so this per-module table is the rawest retained record.
- For the include-path ratio only: the six repositories at the commits in `hardware_ast_complexity_measured_sources.csv`, parsed with the `pyslang` pinned in `requirements.txt`.
- Do not use `hardware_ast_complexity_measured_summary.json`, `hardware_ast_complexity_include_sensitivity.json`, or anything in `data/scrapers/`.

## Definitions
- Groups: `corpus_category`. Repositories: `dataset_name`.
- Median: for an even count, the mean of the two middle values.
- `benchmark_median`, `production_median`: median of `concrete_syntax_nodes` over all modules in the group.
- `pooled_ratio`: production median over benchmark median.
- `opentitan_share_pct`: OpenTitan modules over production modules.
- `repo_medians`: median per repository.
- `group_median_of_repo_medians`: median of the repository medians within each group; `ratio_of_medians` is production over benchmark.
- VeeR: rank VeeR EH1 `source_path` by module count. The top two paths are the library files. Report the paths, their share, and the median of the remaining VeeR modules.
- Substantive diagnostic: split `syntax_diagnostic_codes` on `;`. A module has one if any code is not `DiagCode(NewlineEOF)`. An empty field has none.
- `filtered_ratio`: `pooled_ratio` recomputed on modules with no substantive diagnostic, in both groups.
- `blackparrot_dropped`: BlackParrot modules removed, and whether that is all of them.
- `removed_median`, `kept_median`: median of production modules with and without a substantive diagnostic.
- `reference_share_pct` per repository: percent of modules with `resolved_internal_submodule_instantiations > 0`.
- `max_depth`: maximum `internal_hierarchy_depth` over production modules. `median_depth`: the median there.

## Expected output
```json
{
  "n_modules": 0, "n_benchmark": 0, "n_production": 0,
  "benchmark_median": 0.0, "production_median": 0.0, "pooled_ratio": 0.0, "opentitan_share_pct": 0.0,
  "repo_medians": {"<dataset_name>": 0.0},
  "group_median_of_repo_medians": {"benchmark": 0.0, "production": 0.0}, "ratio_of_medians": 0.0,
  "veer": {"library_paths": [""], "share_pct": 0.0, "median_without": 0.0},
  "production_any_diagnostic_pct": 0.0, "production_substantive_diagnostic_pct": 0.0,
  "filtered_ratio": 0.0, "filtered_ratio_valid_tree_only": 0.0,
  "blackparrot_dropped": 0, "blackparrot_all_dropped": false, "removed_median": 0.0, "kept_median": 0.0,
  "include_path_ratio": null, "include_path_note": "",
  "reference_share_pct": {"<dataset_name>": 0.0}, "instantiating_share_pct": {"<dataset_name>": 0.0},
  "max_depth": 0, "median_depth": 0.0
}
```

## Tolerance
Counts and medians: exact, because they are order statistics of integers. Ratios: 0.005, finer than the prose's rounding, since the CSV is fixed. Percentages: 0.05 points. `include_path_ratio`: 0.05, only if a parse was run; otherwise null with the reason.

## Ambiguities
- "Parser diagnostics" in the sentence giving the production share may mean any diagnostic or a substantive one. The two differ wherever `DiagCode(NewlineEOF)` is the only code. Report both.
- The filter's sentence does not say whether `syntax_tree_valid` must also hold. Report both forms.
- "Two library files" are not named in the prose. Ranking by module count is an assumption.
- "Each repository's HDL source directories" is not defined, and which files the miner selected is not recorded outside the code. The include-path ratio therefore cannot be computed from the prose alone, so the implementer must state its directory rule or return null.
- "Reference" is used for both "references another module" and "uniquely defined local submodule". Report resolved counts and, as `instantiating_share_pct`, `hierarchy_instantiation_count > 0`.
- The CSV is the study's own measurement output. Without a reparse this test cannot detect a parser or miner error, only an aggregation error.
