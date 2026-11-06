# Spec 12 notes: shuttle totals, first-seen count, shipment classes

## What I did
`compute.py` parses the `### Current chips` table, the TT03 chip page, `submission-stats`, the shuttle indexes, and the fetch log, then writes `result.json`. Every reading is an entry under `readings`, each in the spec's shape with a few extra keys (`new_names_by_year_case_folded`, `tt09_on_ttihp25a_case_folded`, `new_names_by_run`, `excluded_names`). `diagnostics` holds the per-run source comparison. `inputs_sha256` lists the files used.

No published result value was visible: the spec has `[VALUE]` placeholders. The TT03 counts 100 and 149 were seen as inputs on the chip page. I read `provenance.yml` (no values) and the openings of `efabless-faq` and `chip_page_tt01`; none of them feed the computation. The forbidden files (`design-repeats-summary.json`, the CSV, `design_repeats.py`) are not in the folder.

## Spec-literal results (reading `spec_literal`)
All values below come from `result.json`.
- 22 plotted runs, total 4026, mean 183.0.
- TT03: catalog 100, carried 149, total with carryover 4175.
- Shipment: shipped 7 runs / 1075 entries / 26.70%; test 5 / 371; other 10 / 2580.
- TT09 369 modules, 329 on TTIHP25a (case-folded also 329).
- New names by year 2022 to 2026: 318, 401, 827, 642, 951. Sum 3139; case-folded 3132.
- Entries by year: 317, 417, 957, 1233, 1102. Last close 2026-07-07.
- Index-only runs: tt03p5 29, ttcad25a 257, ttgf0p1 24, ttihp0p1 24, ttihp0p3 23 (5 runs).

## Dropped or excluded, with counts
- Catalog rows not plotted: 3 (TTIHP26b `Open`, TTSKY26c `Open`, TT10 `-`). The spec names `Open` and blank; I treated `-` as blank because it is not an integer.
- API rows on non-plotted runs: 973 of 4580 (tt10 112, ttboat26 2, ttcad25a 257, ttgf26c 9, ttgf26d 36, ttihp0p3 23, ttihp26b 123, ttsky26c 242, ttsky26d 169).
- Index group rows dropped: 16, all in ttihp25a.
- Within-run repeats collapsed by the set: 4 API rows in ttihp25a, 1 index non-group row in ttihp25a.
- TT01 has no names (index 404, not in `shuttles[]`), so its 152 go in whole, as specified.
- TT10 has 112 API rows, no index (404), and a `-` Designs cell. It is neither plotted nor index-only.

## Readings (13)
Each changes one thing from `spec_literal`. `first_seen_total` / case-folded / `tt09_on_ttihp25a`:

| Reading | What changes | Total | Folded | TT09 on 25a |
|---|---|---|---|---|
| spec_literal | closed date, ties bottom-up, API plus TT02/TT03 index, no groups | 3139 | 3132 | 329 |
| order_closed_ties_top_down | tie order reversed (TTGF26a/b, same year) | 3139 | 3132 | 329 |
| order_launched_as_listed | Launched as printed, with the TTSKY26a typo | 3139 | 3132 | 329 |
| order_launched_ttsky26a_from_api | as above, but TTSKY26a uses its earliest API submission | 3139 | 3132 | 329 |
| source_index_nongroup | indexes for all runs, subtiles kept | 3140 | 3133 | 333 |
| source_index_no_group_no_subtile | indexes, subtiles and groups dropped | 3098 | 3091 | 146 |
| source_index_all_rows | indexes, groups kept | 3156 | 3149 | 333 |
| source_api_drop_subtile_names | API, minus names the index tags subtile | 3097 | 3090 | 146 |
| source_api_add_group_macros | API, plus index group macros | 3155 | 3148 | 329 |
| exclude_organizer_narrow | drop names matching `factory_test` or `chip_rom` | 3136 | 3129 | 327 |
| exclude_organizer_wide | also the name(s) on the most runs (`tt_um_urish_simon`) | 3135 | 3128 | 326 |
| normalize_cross_scheme | strip `tt_um_`; key any 15+ digit id alone | 3132 | 3125 | 329 |
| count_within_run_repeats | count rows, not unique names, on the first-seen run | 3139 | 3132 | 329 |

Only launch-as-listed moves names between years among the order readings: 2025 is 630 and 2026 is 963, against 642 and 951. Repairing TTSKY26a from the API restores the closing-date split. That reading's date comes from `first_submission_time` (2026-02-27), not from a typed value. Launch order with the typo left in is also the only order reading that fails the 1 percent year tolerance against `spec_literal`.

The subtile rule is the largest swing. Dropping subtiles lowers `tt09_on_ttihp25a` from 329 to 146, because many TT09 names return on TTIHP25a as subtiles, and it lowers 2025 by 41 or 42. `tt09_on_ttihp25a` has an exact tolerance, so this one choice decides it, as does API versus index (329 versus 333, where the 4 extra are names the API lacks on TTIHP25a).

## Ambiguities and how they were handled
- Order, ties, group and subtile, organizer macros, and API versus index naming: readings above.
- Organizer macros have no list in the inputs. The name patterns and the "most runs" rule are my definition, and the matched names are in `excluded_names`.
- Repeats within a run: `count_within_run_repeats` matches `spec_literal` because all 4 repeated TTIHP25a names were already seen on earlier runs. The 4 are still listed in `diagnostics`.
- TT02/TT03 naming: the two schemes hardly overlap with the API. Exact-string matching finds only what is identical; `normalize_cross_scheme` removes 7 names, all in 2023. Generic names (`tt_um_top`, `tt_um_essen`, and the case pairs such as `tt_um_alu`/`tt_um_ALU`) may be different designs sharing a name. Neither the exact nor the folded count can tell.
- TT03 carryover: the index holds 249 projects, equal to 100 + 149. 155 macros match TT02 by exact name, more than the 149 stated as carried, and 147 match by repo, fewer. So first-seen credits TT03 with 94 new names, not 100. I added no reading, since the spec fixes the set as all index macros.
- TT05 and TT07: the API and index differ by one name each, opposite ways. `source_index_nongroup` shows the effect (2023 400, 2024 828).
- "Confirmed shipments": this is only the catalog's `Shipped` label, not evidence chips shipped. Classes are label classes.
- `Shipped` matched case-sensitively as the spec states. All 7 use that spelling.

## Catalog rows possibly affected by the stand-in
The retained catalog has no date, and I could not obtain the August snapshot, so I cannot test whether it matches. Rows worth checking:
- TTSKY25a (estimate 2026-07-03) and TTIHP25a (estimate 2026-05-31) have an estimate before August 2026 but no `Shipped`. An August snapshot could have marked them, which would change all shipment figures.
- TTIHP25a Designs 547, API rows 546 (542 unique), index non-group rows 548 (547 unique).
- TT02 Designs 165, index 166. TT05 Designs 174, API 174, index 173. TT07 Designs 120, API 119, index 120.
- TTGF0p3 Closed 2026-07-07 versus API deadline 2026-07-03, TTIHP25a Closed 2025-03-28 versus API deadline 2025-03-12. Neither changes a year or the order.
- TTSKY26a Launched 2025-02-27; its earliest API submission is 2026-02-27, which is consistent with the typo the spec describes.

## Could not compute
- Nothing in the spec's output shape is missing.
- Agreement with the August snapshot cannot be checked: no snapshot is in the inputs.
- The TT06 feedback sentence is out of scope.
- The spec gives no input hashes, so none could be verified. The `7a575614d5` in the catalog file name does not match its SHA-256, SHA-1, or git blob hash prefix. It may be a commit id; I cannot tell.

## Runs
- Exploratory `explore.py` and inline checks of the inputs, not timed. First attempt exit 1, caused only by a trailing `sed` on a missing `../provenance.yml` path; its outputs were complete.
- Second inline probe of TT03 and organizer names: succeeded, not timed.
- `python3 compute.py`: success, 0.083 s.
- `python3 compute.py` rerun: success, 0.079 s, `result.json` hash unchanged.
- Inline repeat check, not timed: the 4 repeated TTIHP25a names are all also on TT09, which explains `count_within_run_repeats` matching `spec_literal`.
