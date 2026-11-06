# Spec 12: Shuttle totals, first-seen count, and confirmed shipments

## Claim
`book/contents/chapters/12-ecosystem/12-ecosystem.qmd:132`: "One educational program, Tiny Tapeout, has drawn [VALUE] design submissions at mature nodes since 2022, an average of [VALUE] catalog entries per run [...]"

`book/contents/chapters/12-ecosystem/12-ecosystem.qmd:134` (caption): "[...] with the cumulative total reaching [VALUE] across [VALUE] runs in an August 2026 catalog snapshot (line) [...] Counts include test shuttles, runs the catalog does not mark as shipped, and designs ported from earlier runs, except the [VALUE] that TT03 (\*) omits from TT02."

`book/contents/chapters/12-ecosystem/12-ecosystem.qmd:138`: "The TT03 entry is an exception, because its count of [VALUE] leaves out [VALUE] designs carried over from TT02, which would raise the total to [VALUE]. At least [VALUE] further runs in the public shuttle indexes have no catalog row and so no bar, among them TTCAD25a with [VALUE] modules. Of the [VALUE] modules on TT09, [VALUE] reappear by name on TTIHP25a [...] Counting each module name once, on the first plotted run that lists it, lowers the total to about [VALUE]. New names by closing year run [VALUE], [VALUE], [VALUE], [VALUE], and [VALUE] from 2022 through 2026, the last a partial year of runs closed by [VALUE]. Entries rise from [VALUE] to [VALUE] between 2024 and 2025 while new names fall from [VALUE] to [VALUE] [...] TT01, which has no module data, counts at its full [VALUE] entries [...] The catalog marked only [VALUE] of the [VALUE] plotted runs, holding [VALUE] of the [VALUE] entries ([VALUE]%), as shipped at the snapshot date. Test shuttles that list no shipment account for [VALUE] runs and [VALUE] entries, and the other [VALUE] runs carried an estimated date or none."

## Raw inputs
Directory `book/contents/chapters/12-ecosystem/data/tinytapeout-receipts/`.
- `chips_index_7a575614d5.md`: site source of the catalog. Use the table under `### Current chips`: `Run | Launched | Closed | Shuttle | Designs | Chips expected | Estimated delivery date`.
- `submission-stats_2026-11-02.json`: `shuttles[]` (`id, slug`) and `submissions[]` (`shuttle_id, top_module`).
- `shuttle_index_<run>_2026-11-02.json`: `projects[]` with `macro` and optional `type`. `index-fetch-log_2026-11-02.json` records which runs returned 404.
- `chip_page_tt03_2026-11-02.html`: the TT03 submitted and carried-over counts.
- Do not use `design-repeats-summary.json`, `../fig-shuttle-cost-democratization-submissions.csv`, or `design_repeats.py`.

## Definitions
- Plotted run: a catalog row whose `Designs` cell is an integer. `Open` and blank rows are not plotted. Strip the `\*` mark on TT03.
- `total`: sum of `Designs`. `n_runs`: plotted runs. `mean_per_run`: their ratio.
- `tt03_carried`: the chip page's count of projects added from TT02. `total_with_carryover`: `total` plus that.
- Shipment class from the delivery cell: begins `Shipped` is shipped; contains `test shuttle` is test; anything else is other. For each class give runs and entries. `shipped_pct`: 100 times shipped entries over `total`.
- Module names per run: for each plotted run with a slug in `shuttles[]`, the set of `top_module` values. For TT02 and TT03, which the API omits, the set of `macro` values in the index, excluding `type == "group"`. TT01 has none.
- `tt09_modules`: size of the TT09 set. `tt09_on_ttihp25a`: size of its intersection with the TTIHP25a set, on exact strings.
- First-seen: walk plotted runs in ascending `Closed` date, with ties in catalog order from the bottom of the table up. A name is new on the first run that lists it.
- `new_names_by_year`: new names per year of `Closed`. TT01 contributes its full `Designs` to its closing year.
- `first_seen_total`: the sum of `new_names_by_year`.
- `entries_by_year`: `Designs` summed per closing year. `last_close_date`: latest `Closed` among plotted runs.
- Index-only runs: shuttle index files whose run is not plotted and that hold projects, with their non-group module counts. `ttcad25a_modules` is one of these.

## Expected output
```json
{
  "n_runs": 0, "total": 0, "mean_per_run": 0.0,
  "tt03": {"catalog_count": 0, "carried": 0, "total_with_carryover": 0},
  "shipment": {"shipped": {"runs": 0, "entries": 0, "pct": 0.0}, "test": {"runs": 0, "entries": 0}, "other": {"runs": 0, "entries": 0}},
  "tt09_modules": 0, "tt09_on_ttihp25a": 0,
  "new_names_by_year": {"<year>": 0}, "entries_by_year": {"<year>": 0},
  "first_seen_total": 0, "first_seen_total_case_folded": 0, "last_close_date": "",
  "index_only_runs": {"<run>": 0}, "ttcad25a_modules": 0,
  "order_key_used": "closed_date"
}
```

## Tolerance
Catalog sums, shipment classes, and TT03 values: exact, as they come from a fixed table. `mean_per_run`: 0.5, since the prose prints a whole number. Name counts: `tt09_on_ttihp25a` exact; `first_seen_total` within 0.5 percent and each `new_names_by_year` within 1 percent, because the prose says "about" and calls the estimate rough, and the group and name-matching rules below can move a few names.

## Ambiguities
- "First plotted run" names no order. Closing date is inferred from "by closing year", ties are not addressed, and launch order would differ because the snapshot's TTSKY26a launch date is a known typo.
- Name matching is undefined: case, organizer macros, and repeats within a run. Report the case-folded total too.
- TT02 and TT03 mix API and index naming schemes, and no text states the two agree.
- Group and subtile entries in the indexes (`type`) have no stated rule, and `submissions[]` has no equivalent field.
- "Module" for TT09 and TTCAD25a may mean API rows or index projects. The two sources differ on some runs.
- "Confirmed shipments" is the task's phrase. The prose says the catalog "marked" runs as shipped, and provenance says the label does not establish that chips shipped.
- The retained catalog is a stand-in dated before the August snapshot that the prose names, so it may not match the snapshot. Report any row that seems affected.
- The cumulative total's TT03 treatment is a choice the prose discloses, not a rule for other runs.
- The TT06 feedback sentence at the end of line 138 has no raw file in this directory and is out of scope.
