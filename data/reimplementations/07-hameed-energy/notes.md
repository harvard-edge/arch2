# Notes, spec 07: Hameed energy decomposition

Status: everything in the expected output computed. Four readings. Three tolerance comparisons in the spec fail; see "Check failures".

## What I did
- `compute.py` reads both CSVs with `#` lines skipped, selects rows exactly as the spec defines, requires exactly one row per selection (exits otherwise), and does all arithmetic in `Fraction` so half-up rounding and tie detection are exact.
- Fetched the source PDF, because the spec allows it. HTTP 200, 466837 bytes, sha256 f536fbe9...3df9e, matching the CSV headers. It is kept at `pdf/source.pdf`, and `compute.py` fetches it only if that file is missing.
- `pdftotext` is required for the PDF comparison.

## Readings in result.json
Each axis is varied one at a time from R0, because the axes do not interact.
- R0 `R0_total_denominator_competition_rank_table3_substages`: Total-row denominator, ties share a rank and the next rank is skipped, substages from breakdown Table 3 rows.
- R1 `R1_components_sum_denominator`: share denominator is the sum of components. Numerically the same as R0, because the sum equals the Total row (2269).
- R2 `R2_dense_rank`: FU ranks 5 rather than 6. The spec says ties "keep both" but not what the next rank is.
- R3 `R3_table2_substages`: `substage_sum_mJ` is 2276 from the Table 2 rows (CABAC 39) rather than 2269 from Table 3 (CABAC 32).

R0 is the one the spec's agreement test uses. Nothing in the factors or energy check varies across readings.

## Ambiguities
- Share denominator: both computed, no numeric difference.
- Rank after a tie: Control and RegFile tie exactly at 220 mJ, flagged in `checks.ties`. Ranked both ways (R0, R2).
- Which substage table: both computed (R0, R3).
- `step_factor` for `plus_SIMD_VLIW`: I took the previous stage as base = 1, from "Base is 1 by definition". This is not a separate reading.
- "5 percent relative" does not name the denominator. Both are in `checks`; the pass/fail outcome is the same either way.
- "Decomposition": the staged factors and component shares are reported separately. No number joins them, as the spec says.

## Check failures (spec tolerances)
- `base_over_asic` = 567.25 against the ASIC factor 500: 13.45% relative to 500, 11.86% relative to 567.25. FAILS the 5% tolerance.
- Chart-read, `plus_SIMD_VLIW`: 7 vs 6.563, ratio 1.0666. FAILS 5%.
- Chart-read, `ASIC`: 500 vs 529.3, ratio 0.9446. FAILS 5%.
- Chart-read, `plus_op_fusion` (1.0181) and `plus_magic` (0.9844) pass.
- These are the arithmetic outcome. I did not loosen anything.

Possible causes of the energy gap, from reading the PDF. These are observations, not established explanations:
- The ~4 mJ/frame in Table 1 is a rounded number, so the ratio is sensitive to it.
- `checks.asic_efficiency_diagnostic` (not a spec metric): base substage energy times 1/gap from Table 2 implies an ASIC energy of 4.657 mJ, giving 487.2x against the Table 3 total and 488.7x against the Table 2 sum. That is close to the paper's 500x, so the 500 may rest on the Table 2 gaps rather than on Table 1's 4 mJ.
- A separate sentence in Sec 2.3, "consumes over 500x less energy", compares the ASIC with Intel's software encoder, not the Tensilica CMP. Table 1 gives 2023/4 = 505.75 for that pair (typed from PDF Table 1, printed by code).

## Step factors vs printed
- Fusion: computed 1.4286, printed 1.4.
- Magic: computed 17.0, printed 18. The spec anticipated this.
- ASIC: computed 2.941, printed "within 3x".
- `step_factor` is the spec's ratio. Printed values are in `checks.step_vs_printed`, parsed from the CSV header.

## Source comparison (reported separately)
- 60 cells compared: 35 Table 3 breakdown cells, 16 Table 2, 1 Table 3 total, 2 Table 1, 6 quoted sentences. 0 differences.
- Negative control `negcontrol.py`: 7 perturbed cells of different kinds, 7 caught, 0 differences on the baseline.
- Label issue, not a value issue: the row labeled "Sec 1 text: 'ASIC is 500x more energy efficient'" quotes the Abstract. Sec 1 says "a 500x energy penalty" and "(500x)".
- The 170x sentence reads "efficiencies improve by 170x", without the word "energy". The CSV treats it as energy efficiency.
- The 10x and 500x are round numbers in the source. "Almost 10x" is transcribed as 10.
- Not checked against the PDF: all chart-read rows. They are pixel reads from figures with no printed cell, and I did not re-read the figures.

## Dropped
- 0 malformed rows, 0 blank rows, in either file.
- Staged: 6 comment lines, 100 data rows. Breakdown: 6 comment lines, 161 data rows. Rows outside a selection are simply unused; all were parsed.
- The `derived` `fraction_of_stage_energy` rows are excluded, as the spec requires.

## Result values seen
- While inspecting the CSV I saw the `derived` fractions for base Total (lines 67 to 72 of the breakdown file), the chart-read rows, and the header's "Printed cross-checks". I did not use the derived fractions; shares come from the energies.
- The spec's claim text hides [VALUE]; the 500x from the paper and CSV is an input here.
- CSV quirk: the Table 2 gap rows use metric `energy_efficiency_ratio_vs_base` with value 1/gap and unit "ratio ASIC/base", inverted relative to the other rows of that metric. They are outside the panel (a) selection because of the `Total` filter; the diagnostic uses them as multipliers.

## Runs
All from this folder.
1. `cat spec.md ...; cat staged csv; echo =========; ...`: failed part way (zsh treats `=========` as filename expansion, exit 1). No computation involved. Rerun as separate commands.
2. `curl -sS -L --max-time 60 -o source.pdf <url>`: HTTP 200, hash matched. Under 60 s; not timed precisely.
3. `time python3 compute.py`: success, 0.132 s total (`run1.log`).
4. `time python3 negcontrol.py`: success, 0.631 s total (`negcontrol.log`).
5. `time python3 compute.py > run2.log`: success, 0.132 s total, printed output the same as run 3.
6. Shell command that wrote this file, then ran `ls -la` and a one-line listing of reading names: the notes were written, but the command stalled past the 120 s limit, and I stopped it. It did no computation.

result.json sha256 4fa24dd7737c7e754e5f8d39a1f7bc9da25aa200e5b7c47f8172d3a791f1d999.

Producer-side checks only. This session did not audit itself independently.
