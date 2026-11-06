# Spec 07: Hameed energy decomposition

## Claim
`book/contents/chapters/02-pressures/02-pressures.qmd:237`: "For the H.264 video encoder studied by @HameedEtAl2010Inefficiency, a fixed-function application-specific integrated circuit (ASIC), with numbers scaled from 180\ nm to 90\ nm, improved energy efficiency roughly [VALUE]-fold relative to a four-core chip multiprocessor."

`book/contents/chapters/02-pressures/02-pressures.qmd:260` (caption): "(a) Energy efficiency of a 720p H.264 encoder as a four-processor 90\ nm chip gains single instruction, multiple data (SIMD) and very-long-instruction-word instructions, fused operations, and custom instructions, compared with an ASIC scaled from 180\ nm, using the factors stated in the source's text. (b) Base-processor energy by component across the encoder, as tabulated in the source [@HameedEtAl2010Inefficiency]."

## Raw inputs
- `book/contents/chapters/02-pressures/data/fig-ch02-specialization-energy/chapter2-hameed-staged-energy.csv`. Skip `#` lines. Columns: `optimization_stage,h264_substage_or_total,metric,value,unit,source_table_or_figure,evidence_class,note`.
- `book/contents/chapters/02-pressures/data/fig-ch02-specialization-energy/chapter2-hameed-component-breakdown.csv`. Skip `#` lines. Columns: `optimization_stage,h264_substage,component,metric,value,unit,source_table_or_figure,evidence_class,note`.
- Source, not retained: `https://csl.stanford.edu/~christos/publications/2010.efficiency.isca.pdf`, sha256 in the CSV headers. If it can be fetched, compare the cells and report any difference separately.
- Do not use `book/contents/chapters/02-pressures/data/fig-ch02-specialization-energy/generate_hameed_ch02.py` or the figure.

## Definitions
- Panel (a) factors: staged rows with `h264_substage_or_total == Total`, `metric == energy_efficiency_ratio_vs_base`, `evidence_class == transcribed`, for stages `plus_SIMD_VLIW`, `plus_op_fusion`, `plus_magic`, `ASIC`. Base is 1 by definition.
- `step_factor`: each stage's factor over the previous stage's, in the order above.
- Chart-read check: the same rows with `evidence_class == chart-read`, and the ratio of transcribed to chart-read for each stage.
- Energy check: base over ASIC, using `energy_mJ_per_frame` on `Total`, `transcribed` rows (base from `Table 3 total`, ASIC from `Table 1`).
- Panel (b) components: breakdown rows with `optimization_stage == base_RISC_CMP`, `h264_substage == Total`, `metric == energy_mJ_per_frame`, `evidence_class == transcribed`, for `IF, Pipeline, D-cache, Control, RegFile, FU`.
- `share_pct`: component energy over the `component == Total` row at the same selection, times 100. Do not use the `derived` rows `fraction_of_stage_energy`.
- `components_sum`: sum of the six components, compared with the Total row.
- `substage_sum`: sum over `IME, FME, IP, CABAC` of the `component == Total` rows, compared with the Total row.
- Rank components by `share_pct`, descending. Ties keep both and flag them.
- Report `share_pct` to one decimal, half-up, and unrounded.

## Expected output
```json
{
  "factors": {"<stage>": {"transcribed": 0.0, "chart_read": 0.0, "transcribed_over_chart_read": 0.0, "step_factor": 0.0}},
  "energy_check": {"base_mJ": 0.0, "asic_mJ": 0.0, "base_over_asic": 0.0},
  "components": {"<component>": {"mJ": 0.0, "share_pct": 0.0, "share_pct_1dp": 0.0, "rank": 0}},
  "total_mJ": 0.0, "components_sum_mJ": 0.0, "substage_sum_mJ": 0.0
}
```

## Tolerance
Transcribed factors and energies: exact, as they are read from fixed cells. `share_pct_1dp`: exact to 0.1 points; the unrounded form within 0.01. Chart-read comparisons: 5 percent relative, the read error stated in the file header. `base_over_asic` against the ASIC factor: 5 percent relative, since the source calls the factor approximate and the two come from different tables.

## Ambiguities
- "Decomposition" has two parts here, the staged factors and the component shares, and the prose never links them. No number joins them.
- The caption says the shares are "as tabulated in the source", but the printed shares are computed from table energies. The source table prints energies, not percentages.
- The share denominator is not stated. It may be the table's Total or the sum of components, which can differ by rounding. Report both inputs; the agreement test uses the Total row.
- The file header notes that per-substage energies differ between two source tables. "Across the encoder" does not say which, so `substage_sum_mJ` is a check, not a definition.
- "Roughly" on line 237 gives no precision, and the factors are stated as round numbers in the source's text. The step from fusion to custom instructions may not equal the factor the source prints for that step.
- This test cannot catch a transcription error unless the PDF is fetched.
