# Notes: spec 04, ArchEval feedback-cost comparison

## What was done
`compute.py` reads only the two CSVs in `inputs/` and writes `result.json`. The file has one entry per reading under `readings`, each in the spec's shape, plus a `checks` block with diagnostics that are not part of that shape. `source_check.py` compares the CSVs with the fetched source and writes `source_check.json`. It is separate because the spec asks for source differences to be reported separately. Nothing under /Users/VJ/GitHub was read.

Every value here is computed from printed table cells. None was measured by me, and the per-run records are not public.

## Result values seen before computing
Rule: say so. The CSV headers print the 72 non-hf and 41 below-baseline counts, the 56 and 31 text counts, the L3 win counts per agent (13, 5, 7, 6), and "agree within 0.01" for the geomeans. `compute.py` derives its counts from rows and uses none of these header values.

## Readings
The spec fixes the win rule, but its ambiguity list says a cell printed 1.00 may hide a value below baseline. So there are three readings, and they differ only in how a printed 1.00 is treated:

| Reading | Printed 1.00 is | Wins (GPT-5.5, 3.5 Flash, Gemma, Flash-Lite) | n_below |
|---|---|---|---|
| `printed_1_00_is_win` (spec definition) | win, not below | 13, 5, 7, 6 | 41 |
| `printed_1_00_is_tie` | neither | 12, 5, 7, 5 | 41 |
| `printed_1_00_is_below` | non-win, below | 12, 5, 7, 5 | 43 |

Two cells print 1.00: GPT-5.5 on astrasim_alltoall (inside the ASTRA set) and Flash-Lite on compose_replacement_prefetcher (outside it). So `wins_no_astra` changes only for Flash-Lite, 6 under the spec reading and 5 under the other two. No under-half set changes under any reading, including the sets recomputed from counts and the no-ASTRA test.

Only `printed_1_00_is_win` matches the printed L3 `win_rate_pct` for all four agents. The other two are 5 points below it for GPT-5.5 and Flash-Lite.

## Results that hold under all readings
- Agents with L3 tokens below L2: 4. Agents with L3 tokens above L1: 2 (Gemma, Flash-Lite).
- Under half at L2: Flash-Lite. At L3: 3.5 Flash, Gemma, Flash-Lite. Crossed L2 to L3: 3.5 Flash, Gemma.
- Panel b: 20 challenges, 80 runs, 72 results, 8 hf, range 0.02 to 5.52.
- ASTRA: 5 challenges dropped, 15 remain. All 3 MiniSWE agents stay under half on the 15; GPT-5.5 does not.

| Agent | L3/L2 | L3/L1 | Geomean computed | Geomean printed | Geomean no ASTRA |
|---|---|---|---|---|---|
| GPT-5.5 + Codex | 0.6842 | 0.3639 | 1.2091 | 1.21 | 1.3654 |
| MiniSWE + Gemini 3.5 Flash | 0.6917 | 0.9435 | 0.6115 | 0.61 | 1.2802 |
| MiniSWE + Gemma 4 31B | 0.7973 | 1.9032 | 0.7130 | 0.72 | 1.2684 |
| MiniSWE + Gemini 3.1 Flash-Lite | 0.7600 | 1.1875 | 0.4412 | 0.45 | 0.8869 |

## Disagreement with printed cells
Two computed geomeans miss the printed value by more than the spec's 0.005: Gemma by -0.0070 and Flash-Lite by -0.0088. This is an expected effect of recomputing from rounded cells. With every cell moved 0.005 up or down, the printed value falls inside the bounds for all four agents (Gemma 0.7010 to 0.7244, Flash-Lite 0.4264 to 0.4544). Small cells such as 0.02 drive this, because a half-unit is 25 percent of that cell. The spec's 0.005 is stated as the tolerance for computed geomeans, so if it is applied against the printed cell rather than between implementations, these two fail it.

The computed median matches the printed one for three agents. For 3.5 Flash it is 0.895 against a printed 0.90, a rounding of an even-count midpoint. The median is a diagnostic, not a spec field.

## Dropped
- Comment lines skipped: 12 in the settings file, 8 in the per-challenge file.
- `hf` rows left out of numeric aggregates: 8 (none are ASTRA rows). They stay in `n_runs` and count as non-wins.
- ASTRA rows left out of the subset: 20 (5 challenges, 4 agents each).
- Rows that failed to parse: 0. The code raises on any non-numeric value other than `hf`, so nothing is silently dropped.

## Other ambiguities
- "Cost": no combined measure is defined, so none is computed, as the spec says.
- Rows covered by the token means: unknown. Table 23 states no run filter, and tokens and quality may cover different runs. No input resolves this.
- Decimals: the prose names none, so `result.json` holds unrounded values.
- `crossed_l2_to_l3`: read as under half at L3 and not at L2. No agent moved the other way.

## Could not compute
The 56 and 31 text counts cannot be recomputed, because they appear in no table or column. They are out of the agreement test. The source text does print them, in two places, and the conflict with the table (72 results, 41 below) is in the source and stays unresolved. Without per-run records, the relation between the 56 artifacts and the 72 table results cannot be determined.

## Source check, reported separately
- Fetched `arxiv.org/abs`, `/html` and `/pdf` for 2607.03601v1 into `source_fetch/`. The spec's URL is the abs page; the HTML and PDF were fetched because those are what the header hashes cover.
- HTML sha256 `70735158...554c` and PDF sha256 `26380be3...4397` both match the CSV header.
- 164 cells compared across Tables 10, 23 and 27, including the bottom rows of Table 27 against Table 10: 0 differences. All 20 challenges were found.
- The comparison parses the HTML only. The PDF was hash-checked but its tables were not compared.
- Table 10 lists Gemma before Flash-Lite; Tables 23 and 27 list them the other way round. `source_check.py` matches rows by model name and maps Table 27 columns by header, not position.

This check addresses the spec's note that the test cannot catch a transcription error, for the cells compared. It was run by the same session that computed the results, so it is not an independent verification.

## Runs
Elapsed times are as reported by the shell.

| Command | Elapsed | Outcome |
|---|---|---|
| Inspect CSVs, with `echo =====` | under 1 s | Exit 1. zsh parsed `=====`; the second half never ran. Rerun without it. |
| `curl https://arxiv.org/abs/2607.03601v1` | 5 s | OK |
| `curl https://arxiv.org/html/2607.03601v1` | 51 s | OK, hash matches |
| `curl https://arxiv.org/pdf/2607.03601v1 --max-time 60` | 60 s | Failed, rc 28, 2130861 of 2688690 bytes. Kept as `source_fetch/pdf_truncated_attempt1.bin`; its hash is `e71efa63...fdcd` and carries no meaning. |
| Same with `--max-time 300` | 83 s | OK, hash matches |
| First table index regex | under 1 s | Empty output, attribute order was wrong. Rewritten. |
| Temporary `dump_tables.py` on Tables 10, 23, 27 | under 1 s | OK. Helper then deleted; `rm` moved it to the Trash. |
| `python3 -I compute.py` (first version) | 0.02 s | OK |
| `python3 -I source_check.py` (first version) | 0.02 s | OK, 152 cells, 0 differences |
| `python3 -I compute.py` (added rounding bounds) | 0.02 s | OK, final `result.json` |
| `python3 -I source_check.py` (added Table 27 bottom rows and text search) | 0.03 s | OK, 164 cells, 0 differences |
| Final listing and re-read of outputs, chained after writing this file | over 120 s | Moved to background by the harness and stopped. `notes.md` had been written. No script was involved; rerun with `/bin/ls`, which took under 1 s. Cause not established. |
