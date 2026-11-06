# Manual shortcut review, 2026-11-02

Reviewer: shortcut-review 2026-11-02. I wrote none of this code and read nothing under `.claude/_reviews`. The scanner's hits are in `shortcuts-reviewed.yml`. This file lists what the scanner has no pattern for, in the four areas named in the brief, plus items met along the way.

Status words: **open** needs a person, **low** is a small defect worth fixing, **held** means I tried to break it and could not.

Numbers below are measured by my own scratch reruns unless marked otherwise. Nothing in the repository was edited except this file and `shortcuts-reviewed.yml`.

## Not tested

- `27-offload-break-even/collect.py` was not rerun, so the timings themselves are not reproduced. I tested the analysis from the retained raw runs.
- `pyslang` is not installed and the AST corpus cache is absent, so study 02 was not reparsed. Its tests use the retained CSV only.
- The Tiny Tapeout catalog receipts were not refetched. I reran from retained receipts.
- This session is one reviewer. It audits analysis code, not whether a source was read correctly.

## Outside the four areas: book number affected

### M1. Date window behind the 4.4x training-compute growth (open)

- **Where:** `book/contents/chapters/02-pressures/02-pressures.qmd:483`, caption at lines 442 to 449.
- **What could go wrong:** `2010 <= yr <= 2026.6` removes rows with no count, and the fitted growth factor depends on the lower bound. The caption's 4.4 and 467 are typed text, not bound to the `growth` value computed at line 489.
- **How tested:** refit the same regression on `chapter2-training-compute.csv` under other windows.
- **Result:** 62 of 529 rows fall before 2010 and are dropped. The caption gives the 2010 to 2026 range and the 467 count but not the 62.

| Window | Rows | Growth per year |
| ---: | ---: | ---: |
| 2000 to 2030 | 485 | 3.58 |
| 2005 to 2026.6 | 478 | 4.03 |
| 2010 to 2024 | 371 | 3.71 |
| 2010 to 2026.6 (book) | 467 | 4.35 |
| 2012 to 2026.6 | 457 | 4.54 |
| 2015 to 2026.6 | 425 | 5.22 |

The window sits inside the 4 to 5 range the same paragraph cites from Epoch, and I found no record of how 2010 was chosen. The book's wording ("in this historical sample") is careful, but the range of 3.6 to 5.2 is not shown.

## Study 27, offload break-even

| ID | Where | What could go wrong | How tested | Result |
| --- | --- | --- | --- | --- |
| M2 | `reproduce.py:37` | The glob pools any `raw/run-*.csv`, so an audit rerun left in `raw/` joins the pooled sample and changes `ob_runs` in the chapter. No check against the five declared runs. | Copied run 1 as run 9 in scratch. | low. Reproduce accepted runs 1 to 5 and 9 without complaint. |
| M3 | `collect.py:167` | Sizes always run in ascending order. Arm order is shuffled within a size, but size is confounded with elapsed time and battery state (62 to 56 percent across the session). `pmset` thermal state is read once before the loop (line 76). | Read code and host receipts. | open, low. The receipts cannot separate size from time. Crossovers sit early in each run, so the effect is likely small; that is my inference, not a measurement. |
| M4 | `reproduce.py:64` | Crossover uses the median only. | Recomputed under median, mean, min, and the last 16 repetitions. | The 256 one-launch crossover held in all. The copy range's lower bound of 768 comes only from run 1's median; mean and last-half give 1,024 in every run. The chapter's "between 768 and 1,024" depends on this estimator. |
| M5 | `collect.py:171` | Arm position could shift GPU timings through clock ramp. `arm_order` is recorded but never analyzed. | Compared GPU medians by position at n >= 256. | held. Position medians are 0.89 to 1.03 of the arm median. Run-to-run spread at the crossovers is much larger (up to 71.9 percent). |
| M6 | `reproduce.py:31` | `FLOOR_MAX_N = 256` could be tuned to give the 15x launch ratio. | Recomputed the median ratio for cutoffs 64 to 1,024. | held. 15.41 for 64 through 256, 15.09 at 384, 14.77 at 512, 14.63 at 1,024. |
| M7 | `collect.py:125` | Indexing `a16d[i]` inside the timed region could inflate the sixteen-launch arm. | Compared sixteen-launch time per launch with the resident arm. | held. 0.96 at n = 16 and 1.01 at n = 64. |
| M8 | `reproduce.py` overall | Output might not depend on inputs, or a stored summary might be reused. | Reran on a scratch copy; multiplied `cpu_single` samples by 4. | held. `summary.json` and `medians.csv` are byte-identical on rerun. Mutation moved the resident crossover from 768 to 384. |
| M9 | `reproduce.py:291` | `"batch": 16` is typed rather than read from receipts. | Read all five host receipts. | low. All record 16. |
| M10 | `reproduce.py:254` | Only model, torch, and BLAS are compared across runs. Battery state could differ. | Read all receipts, including `superseded-shared-wait/`. | held. All five on battery, Python 3.12.13, torch 2.14.1. Three superseded runs on AC, as the chapter says. |

## Study 28, Ibex nightly history

| ID | Where | What could go wrong | How tested | Result |
| --- | --- | --- | --- | --- |
| M11 | `scripts/extract.py` overall | Raw JSON is not retained, so derived tables could not be checked. | Refetched all 1,214 reports to scratch and reran the extractor. | held. All sha256 match the manifest. `nightly.csv` and `group_night.csv` are byte-identical; `summary.json` differs only in `extracted_utc`. |
| M12 | `scripts/extract.py:142` | Two different uploads exist for 2024-07-03, and key order picks one. They sit on the largest step. | Parsed both; swapped the other into `plateaus.py`. | low. Kept upload: 1,350 of 1,415 (95.41 percent, 54 groups). Dropped upload, 13 hours later: 1,396 of 1,430 (97.62 percent, 55 groups). The swap moves the boundary a day to 2024-07-03. All printed steady-stretch values hold (sd 0.40, median 10, 37 groups, 6.59). The choice is recorded in `summary.json`. |
| M13 | `plateaus.py:24` to `37` | Three shifts, 14-report windows, and the 60-day gap could be tuned to produce the "steadiest stretch". | Ran 11 parameter combinations. | held. The same stretch wins in all. With a 7-report window it starts a day earlier, sd 0.43. |
| M14 | `plateaus.py:45` | The group attribution could come from a change in run counts. | Read group totals across both steps. | held. `riscv_pmp_full_random_test` has 600 runs on all 1,213 nights. |
| M15 | Book cell 07, step prose | The first step coincides with a suite change: 2 groups enter at 2024-07-04 and total runs go 1,415 to 1,530 by 2024-07-16. | Read `nightly.csv` around each step. | open, low. The chapter says no step was traced, which stands, but pass rate there changes in denominator as well as failures. |
| M16 | `scripts/extract.py:59` | Only `unmapped_tests` is parsed; `testpoints` could hold results. `reported_pass_rate` is parsed and dropped. | Read schema; compared stored `pass_rate` with computed for 67,204 group rows. | held. `testpoints` is empty in every report. Largest difference 0.003. |
| M17 | study folder | No `runs.jsonl`, and `provenance.yml` has no `produced_by` or `reproduce` field. The extraction has no logged run. | Listed folder and read provenance. | low. `plateaus.py` also reproduces byte for byte. |

## Study 02, AST complexity

| ID | Where | What could go wrong | How tested | Result |
| --- | --- | --- | --- | --- |
| M18 | `data/scrapers/mine_hardware_ast_complexity_real.py:191` | OpenTitan's selection includes copies across `top_*/ip_autogen` and `hw/ip`, plus git symlinks (`rglob` follows `is_file`), so identical modules count more than once in the pooled median. | Deduplicated the CSV by dataset, sha256, and module. | low. 136 OpenTitan rows and 1 VerilogEval row are exact repeats. Ratio goes from 6.70 to 7.11, so the headline is lower, not inflated. The copies also make children ambiguous: 303 OpenTitan modules have ambiguous references, which understates the reference share. The chapter does not mention the copies. |
| M19 | `hardware_ast_complexity_measured_summary.json`, line 156 | The recorded `miner_sha256` (`b23af53b`) is not the current miner (`17317e44`). The CSV reads `VeeR EH1` while keeping its 2026-08-25 timestamp, from a run whose code said `VeeR EL2`. | Walked git history. | open, low. Commit `422ae1fef` edited the results files outside a run. The three miner diffs are the rename and docstrings. No study `runs.jsonl`. |
| M20 | miner `:149`, `:167` | `ensure_checkout` reuses an existing cache and checks only HEAD, so a dirty working tree passes. No row is compared to a git blob. The sensitivity log records this failure class: 32 symlinks stored as text. | Read code. The cache is absent, so no test. | open. Untested. |
| M21 | miner `:251`, `:255` | Only top-level `ModuleDeclaration` nodes are kept. A module hidden by a macro leaves no row and no count. OpenTitan selects 1,137 files and 927 have rows, with no reason recorded for the other 210. | Counted distinct paths in the CSV. | open. Most are likely packages and interfaces, which I could not confirm without the corpus. |
| M22 | miner `:355` | `memo` plus the cycle guard makes depth order-dependent if a reference cycle exists, and `graph` is built from `id()` sets. | Read code. Module graph not retained in the CSV. | open, low. The study reports byte-identical reruns, which I did not repeat. |
| M23 | panel (b), 0 percent for VerilogEval | All 156 modules are named `RefModule`, so uniqueness could force 0 percent as an artifact. | Read `hierarchy_instantiation_count`. | held. 0 of 156 instantiate anything. |
| M24 | ratio statistic | One repository could drive the ratio. | Leave-one-out on the CSV. | held as disclosed. 3.36 without VerilogEval, 8.72 without RTLLM. The chapter prints repository medians and the 4.3x group ratio. |
| M25 | `sensitivity_include_dirs.py:78` | Oversize files skip uncounted. | Read `sources.csv`. | held. 0 oversize files in any corpus. The script's hash matches its result JSON. Not rerun. |

## Tiny Tapeout, `book/contents/chapters/12-ecosystem/data/`

| ID | Where | What could go wrong | How tested | Result |
| --- | --- | --- | --- | --- |
| M26 | whole folder | `scan_shortcuts.py` scans `data/` and `.qmd` cells, not `.py` under `book/contents`. These two scripts, and 14 other generators there, have no hits at all. | Listed the files. | open. 16 files outside the gate. |
| M27 | `design_repeats.py:217` | Module name stands in for design identity, and the chapter warns in one direction only: "a shared name does not prove an identical design". | Recounted first-seen designs from the index receipts under other keys. | open, low. Name: 3,140. Name folded with `tt_um_` removed: 3,130. Owner plus cleaned repo name: 3,290. Repository: 3,395. So "about 3,100" can move up 8 percent. 70 names have more than one owner (`tt_um_top` has five), and 881 are Wokwi ID names, which push the other way. The 2025 dip and the 2026 high survive under every key. |
| M28 | `design_repeats.py` overall | Stored summary could be stale. | Reran on a scratch copy. | held. Identical in every field. |
| M29 | `design_repeats.py:100` | `len(cells) != 7: continue` drops catalog rows uncounted, and the comparison runs one way. | Parsed the pinned catalog. | held. Unplotted: TT10, TTIHP26b, TTSKY26c, all disclosed. Two 3-cell rows, TTGF26c and TTSKY26d, are planned runs with no count. |
| M30 | `design_repeats.py:217` | The `set` collapses repeated rows within a run. | Compared API rows to names. | low. TTIHP25a has 546 rows and 542 names, and the index has 547. The difference is disclosed for rows but not for the 4 duplicates. |
| M31 | `plot_shuttle_cost_democratization.py:83` | `else` labels any unknown PDK GF180MCU. | Counted PDK values. | held. 13, 5, and 4 rows in the three known values. |
| M32 | `provenance.yml` status | The audit record still says FAIL and the provenance says repairs await a fresh audit, while the chapter prints these numbers. | Read both files. | open. A process state, not a code defect. |

## Items met along the way

- **M33 (open).** `data/studies/09-representation-dilation/measure_tree_baseline.py` appeared at 14:30 during this review, and `measure_representation_dilation.py` changed at the same time. Another session is working in study 09. Its thresholds were set after the author read the audit estimate, as its docstring states. Hit 59 is marked `defect`.
- **M34 (open).** `data/datasets/regenerate.py:167` and `:203` hold typed tables for `chapter5-simulator-tax.csv` and `chapter7-mitigation-overhead.csv`, with source notes and no raw file. The scanner does not flag them. I did not check them against their sources.
- **M35 (low).** `data/studies/23-representation-access/summarize.py:160` and `:161` hold typed counts (1,170 and 170 of 40,995) in strings written to the results file. Not checked.
- **M36 (open).** `data/validate_provenance.py` cannot catch `mine_github_hdl_trends.py`, because its stand-in is deterministic scaling, not a random draw. The dataset passes as `transcribed`.

## Scanner limits to decide on

The scanner was not edited.

- 369 of 526 hits, and all 29 UNPARSED entries, come from the gitignored `.cache/repos` checkout of third-party code. The gate cannot pass on a machine with that cache while the Python 2 files stay unparsed. Adding `.cache` to `SKIP_PARTS` would remove them.
- The key hashes file, kind, and text, not the line. 526 hits form 436 keys, so identical lines share one review. The 19 entries in `mine_ai_accelerator_power_trend.py` appear as one defect at the gate.

## Second review, 2026-11-02

Reviewer: shortcut-review-second 2026-11-02. I wrote none of this code, did not do the first review, and read nothing under `.claude/_reviews`. Only this file and `shortcuts-reviewed.yml` were edited. Numbers are measured by my scratch reruns unless the evidence column names another record. The scan now reports 0 unreviewed hits and 0 open defects. That covers its patterns only. The findings below that stay open are not in its count.

### Closed

| ID | Evidence |
| --- | --- |
| M1 | `02-pressures.qmd` now prints the dropped 62 of 529, the oldest record, seven other windows, and the fit interval, and concludes the sample supports no exact rate. An assert stops the build if the caption's typed 467 or 4.4 goes stale. How 2010 was chosen is still unrecorded, but the spread is shown. |
| M2 | `reproduce.py` reads only `DECLARED_RUNS`, stops on a missing file, and prints any undeclared one. Planted a copied run 9 in scratch: `summary.json` and `medians.csv` kept their hashes. |
| M4 | The chapter now says the copy range's lower end depends on the statistic, and asserts that mean times agree across runs. |
| M12 | `28-ibex-nightly-history/provenance.yml` records that the uploads differ, both counts, and the boundary move, and says chapter values do not change. The first review's swap supports that; I did not repeat it. |
| M15 | The chapter now states the suite change, the groups that enter, the run counts, and how little of the rise the denominator explains. |
| M26 | `scan_shortcuts.py` now scans `book/contents` Python files: 39 of 199 hits come from there, including `design_repeats.py`. The `raw/` skip is a separate gap, M40. |
| M27 | `design_identity_sensitivity.py` is retained, and the chapter says the estimate can move either way, prints the repository key's rise and the shared-owner and Wokwi counts, and asserts the 2025 dip and 2026 high under every key. |
| M32 | `provenance.yml` status reads `producer_checked_audit_passed`, and the audit record reads PASS. `validate_evidence_audit.py` does not list this figure among its failures. |
| M35 | The typed strings match `23-representation-access/derived/summary.json` (1,170; 170; 40,995) and 40,825 tree pairs recomputed from the by-file CSV. They remain typed, so a later change would not update them. |
| Scanner cache limit | `.cache` is now in `SKIP_PARTS`: 199 hits and 0 unparsed. |

### Still open

| ID | Status | Evidence |
| --- | --- | --- |
| M3 | open, low | `collect.py` still runs sizes in ascending order and reads thermal state once. The README states no thermal control but not the size and time confound. |
| M9 | low | `reproduce.py:300` still types `"batch": 16`. |
| M17 | low | Study 28 has no `runs.jsonl`, and `validate_runs.py` prints `no run log`. |
| M18 | open, low | `fig-ch04-ast-complexity-cliff.yml` records the repeats and finds they do not flatter the ratio. The chapter still does not mention them. |
| M19 | open, low | `provenance.yml` now discloses the hash mismatch and why it was left. The record is explained, not repaired. `runs.jsonl` exists but logs only the sensitivity run. |
| M20 | open | `ensure_checkout` still tests HEAD only. |
| M21 | open | No reason is recorded for selected files with no module row. |
| M22 | open, low | The depth code is unchanged. |
| M30 | low | I found no statement of the 4 repeated names on TTIHP25a. The chapter's "four subtile names" sentence concerns a different comparison. |
| M33 | open, most serious | The thresholds stay post hoc, with no pre-registration and no author ruling, against rule 5 of `evidence-and-provenance.md`. Hit 59 became benign only because no defensible threshold changes the outcome, which I recomputed. `fig-ch04-spatial-semantic-dilation.yml` also reads FAIL on a claim-ledger hash mismatch, so the figure's gate fails. |
| M34 | open | Both typed tables still read `transcribed` and remain unchecked against sources. No chapter names either CSV. |
| M36 | open as a validator limit | Closed for this dataset, since `provenance.yml` now says `constructed`. `validate_provenance.py` still has no way to detect a deterministic stand-in labeled transcribed. |

### New items from this review

- **M37 (low).** `26-compiler-thread-scaling/reproduce.py:57` and `:58` type `True` for two checks in the receipt. `plot.py` enforces the row mapping by carrying `source_row_id`, but nothing tests `visual_qa_png_created_at_300_dpi`. The scanner has no pattern for typed booleans.
- **M38 (low).** `measure_software_porting_wall.py:98` reuses any existing clone at the cache path with no check of its tree, the same failure class as M20. The default path is shared under `TMPDIR`. Not tested.
- **M39 (low).** `data/datasets/README.md` still says the two stand-ins' provenance entries read `transcribed`. They read `constructed`, so the sentence is stale.
- **M40 (open).** `raw` in `SKIP_PARTS` hides `data/studies/13-errata-dispositions/raw/mine_cpu_errata.py`, the errata miner, from the scan. Not reviewed here.
- **Outside this review.** `fig-errata-subsystem-shares.yml` also reads FAIL, on a chapter 11 wording finding. I did not assess it.

### Limits

- Study 13's `reproduce.py` cannot run on this machine because 4 PDFs are absent, and its receipt dates from 2026-10-16.
- The MLPerf logs were not refetched. The 0 malformed lines come from the record in `data/reimplementations/10-h100-matched-floor/result.json`.
- `export_notebooks.py` was read, not run.
- The key still ignores the line number, so identical lines share one review. This session is one reviewer, and it may share blind spots with the code's authors.
