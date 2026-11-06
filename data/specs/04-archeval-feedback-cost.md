# Spec 04: ArchEval feedback-cost comparison

## Claim
`book/contents/chapters/10-evaluation/10-evaluation.qmd:279`: "Moving from the simulator-code container to the agent-only setting lowers token use for [VALUE] agents, and [VALUE] of the [VALUE] reach the baseline on fewer than half of the challenges [...] [VALUE] of those [VALUE] drop under half at this step, whereas [VALUE] was already under it in the container. The saving is not general either, because [VALUE] agents use more tokens in the agent-only setting than under the full harness. [...] Across the [VALUE] challenges, the [VALUE] results in the study's per-challenge table range from [VALUE] to [VALUE] times the baseline [...] The other [VALUE] of [VALUE] runs are marked as having no valid submission [...]"

`book/contents/chapters/10-evaluation/10-evaluation.qmd:281`: "Its per-challenge table prints [VALUE] results, [VALUE] of them below baseline, whereas its text counts [VALUE] final artifacts that run and satisfy the hard constraints, [VALUE] of them below baseline [...] Without the [VALUE] ASTRA-sim challenges, geometric means computed from the rounded table values rise to [VALUE] for Gemini 3.5 Flash and [VALUE] for Gemma, although all [VALUE] agents still reach the baseline on fewer than half of the remaining [VALUE] challenges. Gemma's printed median of [VALUE] is also close to the baseline."

`book/contents/chapters/10-evaluation/10-evaluation.qmd:277` (caption): "**[VALUE] of [VALUE] agents reach the baseline on fewer than half of the challenges without a runnable simulator, and the token saving depends on the starting setting.**"

## Raw inputs
- `book/contents/chapters/10-evaluation/data/fig-ch10-archeval-feedback-cost/chapter10-archeval-settings.csv`. Skip `#` lines. Columns: `agent,model,framework,setting,geomean_norm_perf,median_norm_perf,win_rate_pct,mean_mtok,mean_turns,mean_minutes,source_table`.
- `book/contents/chapters/10-evaluation/data/fig-ch10-archeval-feedback-cost/chapter10-archeval-l3-per-challenge.csv`. Skip `#` lines. Columns: `challenge_id,challenge_idx,challenge_name,domain,simulator,metric,baseline,agent,model,norm_perf,source_table`. `norm_perf` holds `hf` for no valid submission.
- Source, not retained: `https://arxiv.org/abs/2607.03601v1`, with hashes in the CSV headers. Report any difference separately.

## Definitions
- Settings: L1 full harness, L2 simulator-code container, L3 agent-only.
- Per agent: `mtok` at each setting, `l3_lt_l2` (L3 below L2), `l3_gt_l1` (L3 above L1), and the ratios L3/L2 and L3/L1.
- Win in L3: numeric `norm_perf >= 1.00` as printed. `hf` is a non-win. Below baseline: numeric `norm_perf < 1.00`.
- `wins_l3` per agent: count of wins over all challenges, including `hf` rows. Compare with the printed L3 `win_rate_pct` as a percentage of challenges.
- Under half: win rate strictly below 50 percent. Compute the set under half at L2 and at L3 from `win_rate_pct`, plus the set that crossed from L2 to L3.
- Panel (b): `n_challenges` distinct `challenge_id`; `n_results` numeric rows; `n_hf`; `n_runs`, all rows; min and max numeric `norm_perf`; `n_below`.
- Geometric mean per agent: exp of the mean of log `norm_perf` over numeric rows only.
- ASTRA subset: drop rows where `simulator == "ASTRA-sim"`. Report the dropped challenge count, the remaining count, each agent's geomean on the remainder, and each agent's wins on the remainder.
- Printed L3 values: `geomean_norm_perf`, `median_norm_perf`, read directly per agent.

## Expected output
```json
{
  "agents": {"<agent>": {
    "mtok": {"L1": 0.0, "L2": 0.0, "L3": 0.0}, "l3_lt_l2": false, "l3_gt_l1": false,
    "ratio_l3_l2": 0.0, "ratio_l3_l1": 0.0, "win_rate_pct": {"L1": 0.0, "L2": 0.0, "L3": 0.0},
    "wins_l3": 0, "wins_l3_pct": 0.0, "geomean_l3_printed": 0.0, "geomean_l3_computed": 0.0, "median_l3_printed": 0.0,
    "geomean_no_astra": 0.0, "wins_no_astra": 0}},
  "under_half": {"L2": [""], "L3": [""], "crossed_l2_to_l3": [""]},
  "agents_l3_lower_than_l2": 0, "agents_l3_higher_than_l1": 0,
  "panel_b": {"n_challenges": 0, "n_runs": 0, "n_results": 0, "n_hf": 0, "n_below": 0, "min": 0.0, "max": 0.0},
  "astra": {"dropped_challenges": 0, "remaining_challenges": 0}
}
```

## Tolerance
Counts, sets, booleans, and printed cells: exact, because they are read from fixed rows. Computed geometric means: 0.005, the half-unit of a cell printed to two decimals, which is also the rounding of the prose. Token ratios: 0.5 percent relative, as the token means carry limited printed digits.

## Ambiguities
- The word "cost" is not defined. The prose compares tokens and quality without stating a combined measure, so no combined number is computed.
- "Reach the baseline" hides a tie rule. The file's header states that a cell printed as 1.00 counts as a win, but cells are rounded, so a value just below baseline can print as 1.00. The win count inherits that rounding.
- The two "text counts" on line 281 appear only in a CSV comment, not in any column. They cannot be recomputed from inputs and are out of the agreement test. The conflict with the table is unresolved in the source.
- The token means have no stated run filter, so tokens and quality may cover different runs. The prose says this and no input resolves it.
- The prose names no decimals for the printed range, geomeans, or ratios.
- This test cannot catch a transcription error, since the CSVs are the only retained copy of the tables.
