# Comparison of reimplemented headline metrics with the book

Compared 2026-11-02 15:12 against the working tree of `edit/evidence-gate` (HEAD 452495e0 with uncommitted edits). Comparator: a session that produced neither side. This comparison is unaudited, and "agrees" means the values match, not that a number is correct.

## Result

| Verdict | Numbers |
| --- | ---: |
| agrees | 217 |
| agrees under one reading only | 31 |
| disagrees | 6 |
| not comparable | 30 |
| total rows | 284 |

| Metric | agrees | one reading | disagrees | not comparable |
| --- | ---: | ---: | ---: | ---: |
| 01-offload-break-even | 20 | 1 | 0 | 1 |
| 02-ibex-nightly-triage | 16 | 9 | 0 | 5 |
| 03-cvdp-category-gap | 13 | 0 | 1 | 0 |
| 04-archeval-feedback-cost | 22 | 2 | 2 | 3 |
| 05-rtl-syntax-gap | 23 | 3 | 0 | 2 |
| 06-errata-history | 21 | 2 | 0 | 0 |
| 07-hameed-energy | 13 | 0 | 3 | 1 |
| 08-verification-scissors | 10 | 6 | 0 | 0 |
| 09-kernel-gain | 25 | 1 | 0 | 2 |
| 10-h100-matched-floor | 22 | 4 | 0 | 11 |
| 11-implementation-stage-costs | 7 | 1 | 0 | 0 |
| 12-shuttle-totals | 25 | 2 | 0 | 5 |

Three findings carry the most weight. The book's number for TT09 on TTIHP25a (333) comes from a different name source than the first-seen count beside it, and the spec's definition gives 329. The Ibex "steadiest stretch" values follow from a chosen segment count that the prose does not state. The sentence that the 2022 staffing point falls inside the range holds for a difference of indices and fails for a ratio.

### Verdict rules

- **agrees:** the reimplemented value and the original output both round to the printed value, or sit within the spec tolerance where the spec sets one on bounds, and no reasonable tested reading changes the printed value.
- **agrees under one reading only:** the printed value matches, and at least one reasonable reading tested by the reimplementer or named in the spec gives a different printed value or truth value.
- **disagrees:** a spec-defined comparison falls outside its tolerance under every reading.
- **not comparable:** no reimplemented value exists, usually because the number was added after the spec or is out of its scope.

In the tables, the first value in the reimplemented column is the reading that matches the book, followed by other readings. Where the spec set no tolerance, the column says so.

## Disagreements

| Metric | Number | Printed | Original output | Reimplemented | Tolerance |
| --- | --- | --- | --- | --- | --- |
| 03 | Overall row against n-weighted recomputation | overall row | 8 printed values | 3 of 8 models exceed 0.1 (Claude 3.7 Sonnet -0.196; Claude 3.7 Sonnet (Extended Thinking) +0.227; GPT 4.1 +0.135) | 0.1 pp |
| 04 | L3 geomean, MiniSWE + Gemma 4 31B (panel a) | 0.72 | 0.72 | 0.713 (difference -0.0070) | 0.005 |
| 04 | L3 geomean, MiniSWE + Gemini 3.1 Flash-Lite (panel a) | 0.45 | 0.45 | 0.4412 (difference -0.0088) | 0.005 |
| 07 | Base energy over ASIC energy, against 500 | 500 | 567.25 | 567.25 (13.45% from 500; Table 3 base 2269 mJ over Table 1 ASIC 4 mJ) | 5% relative |
| 07 | SIMD and VLIW, chart-read check | 7 | 7 | 6.563 (6.66% against chart-read, 6.24% against transcribed) | 5% relative |
| 07 | ASIC, chart-read check | 500 | 500 | 529.3 (5.54% against chart-read, 5.86% against transcribed) | 5% relative |

In each case the book prints or plots the value its source states, so the disagreement is between that value and a recomputation or a second reading of the same source. None is resolved here. The largest is the Hameed energy check: 2269 mJ over 4 mJ is 567, and the book prints roughly 500. Causes offered under each metric are possibilities, not findings.

## Numbers that hold under one reading only

| Metric | Number | Reading that matches | Natural? | Would another reading change a claim? |
| --- | --- | --- | --- | --- |
| 01 | 6 | Small sizes are `n <= 256` or 192 | Natural in scope, cutoff unstated | Printed low changes; claim stays |
| 02 | 27 | Unmapped failures only | Yes in context; the issue covers 28 | No |
| 02 | 1,213 | Distinct nights | Yes | No |
| 02 | July 2024, July 2025, 0.4, 10, 37, 6.6 | Four segments, a chosen parameter | No: the prose names no method | Values change (0.3, 9, 35, 6.4 at k=7); the point stays |
| 02 | most | Steps are plateau changes | Yes | Yes: fails for the largest night-to-night change |
| 04 | 13, 6 | Printed 1.00 reaches the baseline | Yes: the caption says printed, and it matches the source win rates | No: under-half sets do not move |
| 05 | 8.6 | Every directory holding HDL files | Yes | Size changes (7.2); direction stays |
| 05 | 45, 63 | Resolved references | Yes in prose; the caption is looser | Upper end becomes 82; claim stays |
| 06 | 40 | All listed rows | Yes at l.367; weak in the "post-initial" caption | No |
| 06 | 6 | Counted per document | Yes | No |
| 08 | 7.3, 15.8 | Base 2014 | Yes | No |
| 08 | 3.6 | Base 2018 | Yes: base 2016 contradicts "rose" | No |
| 08 | 0.95, 1.07, falls inside | Difference of indices | Yes, but "distance" is open | Yes: under the ratio, 2022 falls outside and "held roughly level" loses support |
| 09 | 2.31 | Final kernel is the source's bold time | Yes: l.180 says Round 3 | No |
| 10 | 1.25, <0.02, <0.02 | Aborted counts fixed | Yes: stated in the caption | Bounds change; no lead rests on them now |
| 10 | 1.9 | Unscaled ResNet-50 ratio | Mixed: the prose says published | Value becomes 2.3; claim stays |
| 11 | 78 | Every outer step, skipped ones included | Yes for "outer steps"; weaker for "flow steps" | No |
| 12 | 333 | Shuttle indexes, not the API names the spec defines | Open; the spec value is 329 | No at 329; at 146 it conflicts with "most" |
| 12 | 642 | Subtiles count as names | Yes | Value changes (600); dip stays |

## Open definitions that make a number work

- Spec 02: "steadiest stretch" has no definition, so the method chooses the stretch and its statistics.
- Spec 08: "distance" is left open, and the claim that 2022 falls inside the range depends on it.
- Spec 12: "module" may mean API rows or index projects, and "by name" does not say which. The 333 exists only under the index reading.
- Spec 01: "small sizes" has no cutoff in the prose, and the low of 6 depends on one.
- Spec 09: "final kernel" is undefined, and the 2.31 depends on it.
- Spec 10: the treatment of a retained aborted run sets the plotted bounds for three workloads. The current text states its rule and claims no lead from it.
- Spec 05: "HDL source directories" is undefined, and the 8.6 depends on the directory rule.

## Specs that quote old prose

A code search for every quoted fragment found these differences. Moved lines alone are not changes.

| Spec | Quoted line to current line | Change |
| --- | --- | --- |
| 01 | 335 to 354, 339 to 358 | New sentences on session spread and on median against mean crossovers |
| 02 | 213 to 227 | New sentence on the suite change at the first step |
| 05 | 595 to 626, 597 to 628 | New: the 5.5 and the written-token 6.7 |
| 07 | unchanged | None quoted; the spec never quoted l.262 |
| 08 | 742 to 790, 747 to 797 | None: plain-search misses are caption line wraps |
| 09 | 640 to 654, 642 to 656 | New sentences on profile elapsed time |
| 10 | 325 to 364, 327 to 366, 333 to 374 | Four cases, rewritten at 15:08; see metric 10 |
| 12 | 132 to 140, 134 to 142, 138 to 146 | Spec l.132 printed a number, now "thousands"; a link was added in l.146; new identity sentences |

## Change during this comparison

`09-patterns.qmd`, `analyze_mlperf_h100_runs.py`, and the spread, pairs, hosts, and dividend CSVs were rewritten at 15:08, after the first render at 14:57. The other eight chapters rendered identically before and after. Metric 10 here uses the 15:08 text. The sha256 prefixes below identify what was compared.

| File | sha256 prefix |
| --- | --- |
| `book/contents/chapters/02-pressures/02-pressures.qmd` | f3d0de8df452 |
| `book/contents/chapters/03-lifecycle/03-lifecycle.qmd` | 45e8c94c8f6a |
| `book/contents/chapters/04-representations/04-representations.qmd` | b66f25529295 |
| `book/contents/chapters/06-environments/06-environments.qmd` | 84a45e097006 |
| `book/contents/chapters/07-feedback/07-feedback.qmd` | f0e5a0a77b4f |
| `book/contents/chapters/09-patterns/09-patterns.qmd` | c04050815df8 |
| `book/contents/chapters/10-evaluation/10-evaluation.qmd` | 007241125bda |
| `book/contents/chapters/11-ownership/11-ownership.qmd` | c95e045b02cb |
| `book/contents/chapters/12-ecosystem/12-ecosystem.qmd` | abc758d5a618 |
| `book/contents/chapters/09-patterns/data/mlperf-h100-spread.csv` | bfeddaeef010 |
| `book/contents/chapters/09-patterns/data/mlperf-h100-pairs.csv` | 3c1c1b7ca056 |

## 01: Offload break-even crossovers

Sources: `02-pressures.qmd` l.354, l.356, l.358; `data/studies/27-offload-break-even/summary.json` and raw CSVs.

| Number | Line | Printed | Original output | Reimplemented, by reading | Tolerance | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| Consecutive runs | l.354 | 5 | 5 | 5 | exact | agrees |
| Resident, first beat, low | l.354 | 512 | 512 | 512; sustained: 512 | exact | agrees |
| Resident, first beat, high | l.354 | 768 | 768 | 768; sustained: 768 | exact | agrees |
| Copy, first beat, low | l.354 | 768 | 768 | 768; sustained: 768 | exact | agrees |
| Copy, first beat, high | l.354 | 1,024 | 1,024 | 1,024; sustained: 1,024 | exact | agrees |
| Sixteen-await, first beat, low | l.354 | 512 | 512 | 512; sustained: 512 | exact | agrees |
| Sixteen-await, first beat, high | l.354 | 768 | 768 | 768; sustained: 768 | exact | agrees |
| One launch, crossover | l.354 | 256 | 256 | 256; max across runs: 256 | exact | agrees |
| Launch ratio, pooled median | l.358 | 15 | 15.4111 | 15.4111; n<=192: 15.4129; n<=384: 15.0923 | 0.1% relative | agrees |
| Launch ratio, low | l.358 | 6 | 5.828 | 5.828; n<=192: 5.828; n<=384: 5.0654; every grid n: 0.7513 | 0.1% relative | agrees under one reading only |
| Launch ratio, high | l.358 | 18 | 17.5931 | 17.5931; n<=384: 17.5931; every grid n: 17.5931 | 0.1% relative | agrees |
| One-launch crossover held (stable) | l.358 | yes | yes | yes | exact | agrees |
| Others moved a full grid step | l.358 | 1 | 1 | 1; min of three pairs: 1 | exact | agrees |
| Copy: runs crossing at low end | l.358 | 1 | 1 | 1 | exact | agrees |
| Copy: low end by median | l.358 | 768 | 768 | 768 | exact | agrees |
| Copy: crossover by mean | l.358 | 1,024 | 1,024 | none (added after the spec; no reimplementation; comparator recomputed 1,024 for all five runs from raw) | none in spec | not comparable |
| Earlier runs, resident, low | l.358 | 768 | 768 | 768 | exact | agrees |
| Earlier runs, resident, high | l.358 | 1,024 | 1,024 | 1,024 | exact | agrees |
| Earlier run, copy, led at | l.358 | 768 | 768 | 768 | exact | agrees |
| Earlier run, copy, fell behind at | l.358 | 1,024 | 1,024 | 1,024 | exact | agrees |
| Earlier run, copy, led again from | l.358 | 1,536 | 1,536 | 1,536 | exact | agrees |
| Earlier runs, one launch | l.358 | 256 | 256 | 256; max: 256 | exact | agrees |

Reading that matches the book: the spec definitions, with first and sustained crossovers equal in every current run, and the ratio range taken over `(run, n <= 256)`. Natural: yes for the crossovers. For the 6, the words "at small sizes" govern the sentence, so a restriction is natural, but the prose never states the cutoff.

Open definition behind the number: `n <= 256` exists only in `provenance.yml` (for the median summary, not the range), and the spec says so. The low of 6 holds at a cutoff of 192 or 256, becomes 5 at 384, and becomes 0.75 over the whole grid. The 6 also rests on few cells: per-run lows are 5.83, 9.25, 6.07, 9.77, 9.05, so three of five runs bottom out above 9. The claim that waiting costs more at small sizes survives every cutoff; the printed low does not. The pooled 15 and the high of 18 do not move.

Spec text: all quoted fragments are still present, moved from l.335 and l.339 to l.354 and l.358. New since the spec: the sentences on spread within the session and on median against mean crossovers. Those carry the 1, 768, and 1,024 rows above.

## 02: Ibex nightly plateaus and triage

Sources: `07-feedback.qmd` l.186, l.227; `data/studies/16-regression-records/summary.json`, `data/studies/22-ibex-triage/`, `data/studies/28-ibex-nightly-history/derived/`.

| Number | Line | Printed | Original output | Reimplemented, by reading | Tolerance | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| Report, passing runs | l.186 | 1,464 | 1,464 | 1,464 | exact | agrees |
| Report, total runs | l.186 | 1,530 | 1,530 | 1,530 | exact | agrees |
| Report, pass rate | l.186 | 95.7 | 95.6863 | 95.6863 | 0.05 pp | agrees |
| Report, failing groups | l.186 | 15 | 15 | 15 | exact | agrees |
| Run 1 failed | l.186 | 94 | 94 | 94 | exact | agrees |
| Run 1 total | l.186 | 1,415 | 1,415 | 1,415 | exact | agrees |
| Run 2 failed | l.186 | 40 | 40 | 40 | exact | agrees |
| Run 2 total | l.186 | 1,430 | 1,430 | 1,430 | exact | agrees |
| Mapped | l.186 | 45 | 45 | 45 | exact | agrees |
| All failures | l.186 | 134 | 134 | 134 | exact | agrees |
| Mapped to non-RTL causes | l.186 | 44 | 44 | 44 | exact | agrees |
| Mapped to possible RTL bug | l.186 | 1 | 1 | 1 | exact | agrees |
| Unmapped | l.186 | 89 | 89 | 89 | exact | agrees |
| First-run family failures | l.186 | 62 | 62 | 62 | exact | agrees |
| Second-run failures compared | l.186 | 27 | 27 | 27; all second-run failures outside the families: 28 | exact | agrees under one reading only |
| Nightly reports | l.227 | 1,213 | 1,213 | 1,213; objects: 1,214 | exact | agrees under one reading only |
| Archive first year | l.227 | 2023 | 2023 | 2023 | exact | agrees |
| Archive last year | l.227 | 2026 | 2026 | 2026 | exact | agrees |
| Steadiest stretch, start | l.227 | July 2024 | July 2024 | July 2024; raw BIC k=7: August 2024; step 1 pp: August 2024 | boundaries are a finding | agrees under one reading only |
| Steadiest stretch, end | l.227 | July 2025 | July 2025 | July 2025; raw BIC k=7: July 2025; step 1 pp: June 2025 | boundaries are a finding | agrees under one reading only |
| Steadiest SD, pp | l.227 | 0.4 | 0.4 | 0.4024; raw BIC k=7: 0.3129; step 1 pp: 0.3091 | 0.01 pp, given matching boundaries | agrees under one reading only |
| Median failing groups | l.227 | 10 | 10 | 10; raw BIC k=7: 9 | 1 group, given matching boundaries | agrees under one reading only |
| Distinct failing groups | l.227 | 37 | 37 | 37; raw BIC k=7: 35 | 1 group, given matching boundaries | agrees under one reading only |
| Churn between reports | l.227 | 6.6 | 6.59 | 6.5925; raw BIC k=7: 6.3511; median: 6 | 1 group, given matching boundaries | agrees under one reading only |
| One group accounts for most of the two largest steps | l.227 | yes | yes | yes; largest night-to-night changes: no (shares: original 1.04, 0.79; k=4 0.67, 0.89; night-to-night 0.11, 0.58) | assumed attribution rule | agrees under one reading only |
| Groups entering at first step | l.227 | 2 | book inline cell | none (added after the spec; no reimplementation) | none in spec | not comparable |
| Runs before first step | l.227 | 1,415 | book inline cell | none (added after the spec; no reimplementation) | none in spec | not comparable |
| Runs after first step | l.227 | 1,530 | book inline cell | none (added after the spec; no reimplementation) | none in spec | not comparable |
| Denominator share of first step | l.227 | 0.2 | book inline cell | none (added after the spec; no reimplementation) | none in spec | not comparable |
| First step size, 14-report means | l.227 | 3.1 | book inline cell | none (added after the spec; no reimplementation) | none in spec | not comparable |

Reading that matches the book: `plateaus.py` with a fixed four-segment partition, which `dp_l2_raw_k3` to `k5` and `dp_l2_med7_k4` and `k5` reproduce (2024-07-04 to 2025-07-01, 347 reports). Natural: no. The prose names no method, and provenance calls the segment count a chosen parameter. BIC on the raw series picks k=7, and every k from 6 to 12 starts the stretch in August 2024 with SD 0.31, median 9, 35 distinct groups, and churn 6.35.

Open definition behind the number: "steadiest stretch" is undefined, as the spec warns, so 0.4, 10, 37, and 6.6 all depend on the choice of k. A different reading changes those four printed values and the start month. It does not change the sentence's point, since each reading shows a quiet aggregate over a changing failing set.

The "most of the two largest steps" claim holds in all 24 segmentations (shares 0.55 to 1.08) and fails on the first of the two largest night-to-night changes, whose top group has share 0.11. That change is a one-night excursion, 94.86 to 90.29 to 93.84, so plateau steps are the natural reading of "moves in steps". The claim depends on that reading, and "accounts for most" has no stated rule.

The 27 matches the study README's count of unmapped second-run failures. In its paragraph it splits the other 89, so that reading is natural there. The issue says the log was reviewed "for the other tests", which covers all 28 failures outside the families, one of them the mapped RTL case. The difference does not change a claim. The 1,213 counts nights; 1,214 objects exist because one date has two uploads.

Spec text: all quoted fragments are present; l.213 moved to l.227. New since the spec: the sentence on the suite change at the first step.

## 03: CVDP category gap

Sources: `10-evaluation.qmd` l.421, l.439, l.441; `book/contents/chapters/10-evaluation/data/fig-ch10-cvdp-category-gap/chapter10-cvdp-category-pass1.csv`, which is the original record for these rows.

| Number | Line | Printed | Original output | Reimplemented, by reading | Tolerance | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| Models | l.439 | 8 | 8 | 8 | exact | agrees |
| Spec to RTL, low | l.439 | 20 | 20 | 20 | 0.01 pp; integer exact | agrees |
| Spec to RTL, high | l.439 | 48 | 48 | 48 | 0.01 pp; integer exact | agrees |
| Checker, low | l.439 | 3 | 3 | 3 | 0.01 pp; integer exact | agrees |
| Checker, high | l.439 | 11 | 11 | 11 | 0.01 pp; integer exact | agrees |
| Lowest category | l.441 | cid13 | cid13 | cid13; by median: cid13; by min: cid13 | exact | agrees |
| Highest aggregate pass@1 | l.421 | 34 | 33.56 | 33.56 (n-weighted recomputation 33.36, integer 33; 'no more than 34%' stays true) | 0.01 pp; integer exact | agrees |
| Debugging range (fig-alt) | l.441 | 26 to 53 | 26 to 53 | 26 to 53 | 0.01 pp; integer exact | agrees |
| RTL modification range (fig-alt) | l.441 | 30 to 45 | 30 to 45 | 30 to 45 | 0.01 pp; integer exact | agrees |
| Lint and quality range (fig-alt) | l.441 | 20 to 45 | 20 to 45 | 20 to 45 | 0.01 pp; integer exact | agrees |
| RTL completion range (fig-alt) | l.441 | 18 to 37 | 18 to 37 | 18 to 37 | 0.01 pp; integer exact | agrees |
| Testbench stimulus range (fig-alt) | l.441 | 13 to 25 | 13 to 25 | 13 to 25 | 0.01 pp; integer exact | agrees |
| Assertion generation range (fig-alt) | l.441 | 5 to 23 | 5 to 23 | 5 to 23 | 0.01 pp; integer exact | agrees |
| Overall row against n-weighted recomputation | not in prose | overall row | 8 printed values | 3 of 8 models exceed 0.1 (Claude 3.7 Sonnet -0.196; Claude 3.7 Sonnet (Extended Thinking) +0.227; GPT 4.1 +0.135) | 0.1 pp | disagrees |

Reading that matches the book: the spec definitions. Rounding convention never matters, because no endpoint ends in `.5`, and the 72 CSV cells match the paper's Table 2 in both the PDF and the HTML per the reimplementer's fetch. Natural: yes. Checker generation is lowest under max, median, and min, and the two ranges are disjoint, so no reading of "sits lowest" or of the gap changes a claim.

Disagreement: the n-weighted recomputation misses the printed overall row by more than the spec's 0.1 for 3 of 8 models. All 64 category cells are whole numbers, so the spec's premise of one-decimal rounding looks wrong, but rounding is not established as the cause. No printed book number changes: the book prints the overall row, and "no more than 34%" holds under both values.

A reader may also find different pass rates in the paper's Table 5, for example 22.77% against 6.0% for one model on `cid13`. The book's caption names five samples per problem, and it uses the Table 2 values the spec names.

Spec text: all quoted fragments are present at the same lines. Line 421 also prints 783 problems and thirteen categories, which no spec covers.

## 04: ArchEval feedback-cost comparison

Sources: `10-evaluation.qmd` l.277, l.279, l.281; `book/contents/chapters/10-evaluation/data/fig-ch10-archeval-feedback-cost/chapter10-archeval-settings.csv` and `chapter10-archeval-l3-per-challenge.csv`, which are the original records.

| Number | Line | Printed | Original output | Reimplemented, by reading | Tolerance | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| Agents with L3 tokens below L2 | l.279 | 4 | 4 | 4 | exact | agrees |
| Under half at L3 | l.279 | 3 | 3 | 3; printed 1.00 is a tie: 3; printed 1.00 is below: 3 | exact | agrees |
| Crossed under half at this step | l.279 | 2 | 2 | 2 | exact | agrees |
| Under half already at L2 | l.279 | 1 | 1 | 1 (MiniSWE + Gemini 3.1 Flash-Lite) | exact | agrees |
| Agents with L3 tokens above L1 | l.279 | 2 | 2 | 2 | exact | agrees |
| Challenges | l.279 | 20 | 20 | 20 | exact | agrees |
| Numeric results | l.279 | 72 | 72 | 72 | exact | agrees |
| Range low | l.279 | 0.02 | 0.02 | 0.02 | exact | agrees |
| Range high | l.279 | 5.52 | 5.52 | 5.52 | exact | agrees |
| Invalid runs | l.279 | 8 | 8 | 8 | exact | agrees |
| All runs | l.279 | 80 | 80 | 80 | exact | agrees |
| Table results below baseline | l.281 | 41 | 41 | 41 (tie reading 41; below reading 43, which recounts a printed 1.00 and is not a count of what the table prints) | exact | agrees |
| Text count, artifacts | l.281 | 56 | CSV comment only | none (in no column; the reimplementer found both in the source text; the conflict with 72 and 41 is the source's and stays unresolved) | out of agreement test | not comparable |
| Text count, below baseline | l.281 | 31 | CSV comment only | none (in no column; the reimplementer found both in the source text; the conflict with 72 and 41 is the source's and stays unresolved) | out of agreement test | not comparable |
| ASTRA-sim challenges | l.281 | 5 | 5 | 5 | exact | agrees |
| Geomean without ASTRA, Gemini 3.5 Flash | l.281 | 1.28 | 1.2802 | 1.2802 | 0.005 | agrees |
| Geomean without ASTRA, Gemma | l.281 | 1.27 | 1.2684 | 1.2684 | 0.005 | agrees |
| Remaining challenges | l.281 | 15 | 15 | 15 | exact | agrees |
| Under half on the remaining 15 | l.281 | 3 | 3 | 3 ([5, 6, 6, 10]) | exact | agrees |
| Gemma printed median | l.281 | 0.99 | 0.99 | 0.99 | exact | agrees |
| Wins, GPT-5.5 + Codex | l.277 | 13 | 13 | 13; printed 1.00 is a tie or below: 12 | exact | agrees under one reading only |
| Wins, MiniSWE + Gemini 3.5 Flash | l.277 | 5 | 5 | 5; printed 1.00 is a tie or below: 5 | exact | agrees |
| Wins, MiniSWE + Gemma 4 31B | l.277 | 7 | 7 | 7; printed 1.00 is a tie or below: 7 | exact | agrees |
| Wins, MiniSWE + Gemini 3.1 Flash-Lite | l.277 | 6 | 6 | 6; printed 1.00 is a tie or below: 5 | exact | agrees under one reading only |
| L3 geomean, GPT-5.5 + Codex (panel a) | not in prose | 1.21 | 1.21 | 1.2091 (difference -0.0009) | 0.005 | agrees |
| L3 geomean, MiniSWE + Gemini 3.5 Flash (panel a) | not in prose | 0.61 | 0.61 | 0.6115 (difference +0.0015) | 0.005 | agrees |
| L3 geomean, MiniSWE + Gemma 4 31B (panel a) | not in prose | 0.72 | 0.72 | 0.713 (difference -0.0070) | 0.005 | disagrees |
| L3 geomean, MiniSWE + Gemini 3.1 Flash-Lite (panel a) | not in prose | 0.45 | 0.45 | 0.4412 (difference -0.0088) | 0.005 | disagrees |
| Ratio of highest to lowest result per agent (fig-alt) | l.277 | 22 to 184 | inline assert | none (no reimplementation) | none in spec | not comparable |

Reading that matches the book: the spec definitions, with a printed 1.00 counted as reaching the baseline. Natural: yes, because the caption says "printed counts at or above baseline" and only this reading reproduces the source's printed win rates. The wins of 13 and 6 hold under this reading alone; each falls by one if a printed 1.00 hides a value below baseline. No under-half set changes under any reading, so no book claim changes.

Disagreement: the geomeans computed from Table 27 miss the printed Table 10 values by more than the spec's 0.005 for Gemma and Flash-Lite. With every cell moved half a unit, the printed values stay inside the bounds (0.7010 to 0.7244 and 0.4264 to 0.4544), which is consistent with rounding but does not establish it. Panel (a) plots the printed values and panel (b) draws bars computed from the cells, and the caption says which is which. The prose prints neither value, and all four stay on the same side of 1.

Spec text: all quoted fragments are present at the same lines. The spec's "[VALUE] was already under it" now names Flash-Lite. The word "cost" is still undefined, and the book computes no combined measure. The reimplementer compared 164 cells with the fetched HTML and found no differences, so the spec's note that this test cannot catch a transcription error does not apply to those cells.

## 05: RTL syntax gap and its sensitivity

Sources: `04-representations.qmd` l.623, l.626, l.628; `data/studies/02-ast-complexity-cliff/` summary and include-sensitivity JSON, and the measured CSV.

| Number | Line | Printed | Original output | Reimplemented, by reading | Tolerance | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| Modules | l.623 | 1,513 | 1,513 | 1,513 | exact | agrees |
| Benchmark median | l.628 | 168 | 168 | 168 | exact | agrees |
| Production median | l.628 | 1,125 | 1,125 | 1,125 | exact | agrees |
| Pooled ratio | l.628 | 6.7 | 6.6964 | 6.6964 | 0.005 | agrees |
| OpenTitan share | l.628 | 72 | 72.2222 | 72.2222 | 0.05 pp | agrees |
| Repository median, VerilogEval | l.628 | 129 | 129 | 129 | exact | agrees |
| Repository median, RTLLM | l.628 | 335 | 335 | 335 | exact | agrees |
| Repository median, VeeR EH1 | l.628 | 206 | 206 | 206 | exact | agrees |
| Repository median, CV32E40P | l.628 | 777 | 777 | 777 | exact | agrees |
| Repository median, OpenTitan | l.628 | 1,205 | 1,205 | 1,205 | exact | agrees |
| Repository median, BlackParrot | l.628 | 1,520 | 1,520 | 1,520 | exact | agrees |
| VeeR library share | l.628 | 58 | 58.0357 | 58.0357 | 0.05 pp | agrees |
| VeeR median without them | l.628 | 3,245 | 3,245 | 3,245 | exact | agrees |
| Ratio of group medians | l.628 | 4.3 | 4.2716 | 4.2716 | 0.005 | agrees |
| Production modules with diagnostics | l.628 | 54 | 54.2438 | 54.2438; substantive only: 54.2438 | 0.05 pp | agrees |
| Filtered pooled ratio | l.628 | 4.0 | 4.0179 | 4.0179; and valid tree: 4.0179 | 0.005 | agrees |
| BlackParrot modules dropped | l.628 | 125 | 125 | 125 | exact | agrees |
| Median of removed modules | l.628 | 2,080 | 2,080 | 2,080 | exact | agrees |
| Median of kept modules | l.628 | 675 | 675 | 675 | exact | agrees |
| Include-path pooled ratio | l.628 | 8.6 | 8.5714 | 8.5714; directories of parsed files only: 7.2321 | 0.05 | agrees under one reading only |
| Include-path ratio, no substantive diagnostic | l.628 | 5.5 | 5.4554 | none (added after the spec; the reimplementation has no filtered include ratio) | none in spec | not comparable |
| Written-token ratio, both parses | l.628 | 6.7 | 6.6889 | none (added after the spec; no reimplementation) | none in spec | not comparable |
| VerilogEval reference share | l.626 | 0 | 0 | 0 | 0.05 pp | agrees |
| RTLLM reference share | l.626 | 16 | 16.3934 | 16.3934 | 0.05 pp | agrees |
| Production reference share, low | l.626 | 45 | 44.6429 | 44.6429; any instantiation: 45.5357 | 0.05 pp | agrees under one reading only |
| Production reference share, high | l.626 | 63 | 63.4615 | 63.4615; any instantiation: 81.6 | 0.05 pp | agrees under one reading only |
| Maximum depth | l.628 | 13 | 13 | 13 | exact | agrees |
| Median depth | l.628 | 2 | 2 | 2 | exact | agrees |

Reading that matches the book: the spec definitions for everything from the CSV. For the include path, the reading that adds every directory holding HDL files, which also matches the study's `sensitivity_include_dirs.py` (BlackParrot median 4,902 in both). Natural: yes for "each repository's HDL source directories". A narrower reading, only the directories of the parsed files, gives 7.2. Either reading raises the ratio, so the direction of the claim holds; the printed 8.6 does not. In all include readings BlackParrot stays partly repaired, because submodule headers were not fetched, and the reimplementer did not compute a ratio with them.

The 45% to 63% range uses resolved references. Counting any instantiation gives 45.5% to 81.6%. The prose says "uniquely defined local submodule", so the resolved reading is natural, and the caption's looser "referencing local children" leaves it open. A filter on tree validity alone, which ignores diagnostics, gives 6.93. The prose names diagnostics explicitly, so that is not a reading of the 4.0 sentence.

The CSV is the study's own output, but the reimplementer reparsed all 1,419 files and reproduced `concrete_syntax_nodes` for 1,513 of 1,513 modules, which narrows the spec's warning for that column. It does not test file selection or the hierarchy columns.

Spec text: all quoted fragments are present; l.595 and l.597 moved to l.626 and l.628. New since the spec: the 5.5 and the written-token 6.7, which the spec's [...] does not cover. Those two carry the book's statement that the rise does not show larger source, and they are not reimplemented.

## 06: Errata history totals and yearly counts

Sources: `11-ownership.qmd` l.264, l.367, l.369; `data/studies/13-errata-dispositions/summary.json`, `18-errata-by-year/summary.json`, `19-errata-history/` summary and annual counts.

| Number | Line | Printed | Original output | Reimplemented, by reading | Tolerance | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| Itemized errata | l.264 | 1,774 | 1,774 | 1,774; distinct family and ID: 1,774 | exact | agrees |
| CPU families | l.264 | 19 | 19 | 19 | exact | agrees |
| Intel families | l.264 | 15 | 15 | 15 | exact | agrees |
| AMD families | l.264 | 4 | 4 | 4 | exact | agrees |
| First introduction year | l.264 | 2016 | 2,016 | 2,016 | exact | agrees |
| Last introduction year | l.264 | 2024 | 2,024 | 2,024 | exact | agrees |
| Revision rows | l.367 | 40 | 40 | 40; post-initial rows: 37; rows naming an added ID: 35 | exact | agrees under one reading only |
| Documents | l.367 | 4 | 4 | 4 | exact | agrees |
| Histories continuing two years | l.367 | 3 | 3 | 3; by date, month start: 3; by date, month end: 3 | exact | agrees |
| Ice Lake-SP additions in 2026 | l.367 | 8 | 8 | 8 | exact | agrees |
| Ice Lake-SP latest month | l.367 | March | March | March | exact | agrees |
| Ice Lake-SP launch year | l.367 | 2021 | 2,021 | 2,021 | exact | agrees |
| Turin addition year | l.367 | 2025 | 2,025 | 2,025 (1 year with additions) | exact | agrees |
| Turin launch year | l.367 | 2024 | 2,024 | 2,024 | exact | agrees |
| Years with no revision | l.367 | 6 | 6 | 6; calendar years, pooled: 5 | exact | agrees under one reading only |
| Family 17h revisions listed | l.367 | 4 | 4 | 4 | exact | agrees |
| Family 17h span | l.367 | 10 | 10 | 10 | exact | agrees |
| Family 17h lowest revision | l.367 | 1.12 | 1.12 | 1.12 | exact | agrees |
| Family 17h highest revision | l.367 | 1.21 | 1.21 | 1.21 | exact | agrees |
| Additions, Broadwell-EP | l.369 | 46 | 46 | 46; distinct: 46 | exact | agrees |
| Additions, Ice Lake-SP | l.369 | 104 | 104 | 104; distinct: 104 | exact | agrees |
| Additions, Family 17h | l.369 | 30 | 30 | 30; distinct: 30 | exact | agrees |
| Additions, Family 1Ah | l.369 | 21 | 21 | 21; distinct: 21 | exact | agrees |

Reading that matches the book: the spec definitions, with revision rows counted as every listed row and blank years counted per document. Natural: yes for the six, since the prose says "inside these histories"; pooling calendar years gives 5, because 2021 is blank in two documents. For the 40, natural in l.367 and less so in the l.369 caption, which reads "post-initial erratum identifiers ... across 40 revision rows". The 40 includes 3 initial-release rows that add nothing, and 5 rows in all name no added identifier. Those readings give 37 and 35. No claim changes, since the additions themselves do not move.

Every other count is the same in all three readings. The list and distinct counts are equal, and the calendar and dated two-year tests agree. The 104 for Ice Lake-SP includes IDs later removed, and its table starts at 003US with no initial row, so the sentence that each count excludes the initial inventory holds by absence of a row. BDF92 is added in row 003 and marked removed in the PDF body with no Removed clause in the table.

Spec text: all quoted fragments are present at the same lines. The corpus total reaches only the mined `errata.csv`, not a reparse of all PDFs.

## 07: Hameed energy decomposition

Sources: `02-pressures.qmd` l.237, l.260, l.262; `book/contents/chapters/02-pressures/data/fig-ch02-specialization-energy/chapter2-hameed-staged-energy.csv` and `chapter2-hameed-component-breakdown.csv`, which are the original records.

| Number | Line | Printed | Original output | Reimplemented, by reading | Tolerance | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| ASIC factor | l.237 | 500 | 500 | 500 | exact (transcribed) | agrees |
| SIMD and VLIW factor (fig-alt) | l.260 | 7 | 7 | 7 | exact (transcribed) | agrees |
| Operation fusion factor (fig-alt) | l.260 | 10 | 10 | 10 | exact (transcribed) | agrees |
| Custom instructions factor (fig-alt) | l.260 | 170 | 170 | 170 | exact (transcribed) | agrees |
| Base energy over ASIC energy, against 500 | l.237 | 500 | 567.25 | 567.25 (13.45% from 500; Table 3 base 2269 mJ over Table 1 ASIC 4 mJ) | 5% relative | disagrees |
| SIMD and VLIW, chart-read check | l.260 | 7 | 7 | 6.563 (6.66% against chart-read, 6.24% against transcribed) | 5% relative | disagrees |
| ASIC, chart-read check | l.260 | 500 | 500 | 529.3 (5.54% against chart-read, 5.86% against transcribed) | 5% relative | disagrees |
| Operation fusion, chart-read check | not in prose | 10 | 10 | 9.822 (1.81%) | 5% relative | agrees |
| Custom instructions, chart-read check | not in prose | 170 | 170 | 172.7 (1.56%) | 5% relative | agrees |
| Share, Instruction fetch | l.262 | 33.6 | 33.5831 | 33.5831; sum-of-components denominator: 33.5831 | 0.1 pp at 1 dp; 0.01 unrounded | agrees |
| Share, Pipeline | l.260 | 22.0 | 21.9921 | 21.9921; sum-of-components denominator: 21.9921 | 0.1 pp at 1 dp; 0.01 unrounded | agrees |
| Share, Data cache | l.260 | 19.2 | 19.2155 | 19.2155; sum-of-components denominator: 19.2155 | 0.1 pp at 1 dp; 0.01 unrounded | agrees |
| Share, Control | l.260 | 9.7 | 9.6959 | 9.6959; sum-of-components denominator: 9.6959 | 0.1 pp at 1 dp; 0.01 unrounded | agrees |
| Share, Register file | l.260 | 9.7 | 9.6959 | 9.6959; sum-of-components denominator: 9.6959 | 0.1 pp at 1 dp; 0.01 unrounded | agrees |
| Share, Functional units | l.262 | 5.8 | 5.8175 | 5.8175; sum-of-components denominator: 5.8175 | 0.1 pp at 1 dp; 0.01 unrounded | agrees |
| Overhead bound from these totals | l.262 | 17 | 17.1894 | 17.1894 | not in spec; comparator computed from the result fields | agrees |
| Source's own statement | l.262 | 20 | source text | none (no reimplementation) | none in spec | not comparable |

Reading that matches the book: the factors the source states in its text, with shares computed from Table 3 energies. Natural: yes, since the caption says "using the factors stated in the source's text". The denominator and the substage table do not change a printed value.

Disagreement: 2269 mJ over 4 mJ is 567.25, which is 13.45% from the 500 the book prints, outside the spec's 5%. The 4 mJ is printed to one figure, and treating it as 3.5 to 4.5 mJ gives 504.2 to 648.3, so the source's tables do not reach 500. The reimplementer's diagnostic from the Table 2 gaps gives 487.2. The reimplementer also notes that a separate source sentence, "over 500x less energy", compares the ASIC with Intel's software encoder. Why the source's text and tables differ is not established here. The book's "roughly" and its attribution to the source's text describe what it prints. They do not close the gap.

Disagreement: the chart-read rows differ from the transcribed factors by more than 5% for SIMD (6.563 against 7) and the ASIC (529.3 against 500). The CSV header states a read error of about 3 to 5%. The book prints the transcribed factors, so its printed values match the source's text, and the source's figure reads differently.

The caption still says the shares are "as tabulated in the source". The source tabulates energies, and the percentages are computed from them. The step from fusion to custom instructions is 17 by division and 18 as printed in the source; the book prints neither.

Spec text: all quoted fragments are present at the same lines. The spec does not quote l.262, which carries the 5.8, 33.6, 17, and 20. The reimplementer compared 60 cells with the PDF and found no differences, with 7 of 7 perturbed cells caught. Chart-read rows were not rechecked.

## 08: Verification scissors rates and gap

Sources: `02-pressures.qmd` l.790, l.795 to l.800; `book/contents/chapters/02-pressures/data/fig-verification-demand-scissors/chapter2-wilson-verification-staffing.csv`, the original record, with the book's inline arithmetic.

| Number | Line | Printed | Original output | Reimplemented, by reading | Tolerance | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| Verification rate, stated | l.790 | 6.2 | 6.2 | 6.2 (computed 6.18) | 0.15 pp against computed | agrees |
| Design rate, stated | l.790 | 2.7 | 2.7 | 2.7 (computed 2.74) | 0.15 pp against computed | agrees |
| Verification, 2007 to 2014 | l.790 | 129 | 129.1667 | 129.1667 | 0.05 pp | agrees |
| Design, 2007 to 2014 | l.790 | 29 | 29.4872 | 29.4872 | 0.05 pp | agrees |
| Verification, then by 2022 | l.790 | 7.3 | 7.2727 | 7.2727; base 2007: 145.8333 | 0.05 pp | agrees under one reading only |
| Design, then by 2022 | l.790 | 15.8 | 15.8416 | 15.8416; base 2007: 50 | 0.05 pp | agrees under one reading only |
| Verification fell, 2016 to 2018 | l.790 | 5.2 | 5.1724 | 5.1724 | 0.05 pp | agrees |
| Verification rose by 2020 | l.790 | 3.6 | 3.6364 | 3.6364; base 2016: -1.7241 | 0.05 pp | agrees under one reading only |
| Design fell by 2020 | l.790 | 1.9 | 1.9048 | 1.9048; base 2016: 1.9048 | 0.05 pp | agrees |
| Distance, low | l.790 | 0.95 | 0.9455 | 0.9455; ratio of indices: 1.7024 | 0.005 | agrees under one reading only |
| Distance, high | l.790 | 1.07 | 1.0705 | 1.0705; ratio of indices: 1.7985 | 0.005 | agrees under one reading only |
| 2022 point inside that range | l.790 | yes | yes | yes; ratio of indices: no (difference 0.9583; ratio 1.6389) | exact | agrees under one reading only |
| Verification growth, 2007 to 2022 | l.796 | 146 | 145.8333 | 145.8333 | 0.05 pp | agrees |
| Design growth, 2007 to 2022 | l.797 | 50 | 50 | 50 | 0.05 pp | agrees |
| Verification index | l.797 | 2.46 | 2.4583 | 2.4583 | 0.005 | agrees |
| Design index | l.798 | 1.50 | 1.5 | 1.5 | 0.005 | agrees |

Reading that matches the book: distance as the difference of indices, "then by 2022" from 2014, and "by 2020" from 2018. The inline cell computes exactly these. Natural: yes. The prose says "distance", and "then" follows a 2014 endpoint. The base-2007 alternatives repeat the caption's figures, and the base-2016 alternative contradicts "rose".

Open definition behind the claim: the spec leaves "distance" open, and that choice decides a sentence. Under the difference, the 2022 point (0.958) sits inside 0.95 to 1.07. Under the ratio, it (1.639) falls below 1.70 to 1.80, the lowest value since 2014, and the caption's "the gap has held roughly level since" loses that support. The 2022 point is chart-read and constrained by the study's stated growth, and "held roughly level" has no test.

The stated and computed 2007 to 2022 rates agree within 0.15 points, but this is partly circular, as the spec warns. Outside the book: a CSV caveat states a 2007 to 2020 design rate of 3.0%, whereas the printed cells give 2.16%. The book does not print that rate.

Spec text: all quoted wording is present. The spec's l.742 and l.747-752 moved to l.790 and l.795-800. The caption fragments reported missing by a plain search are line wraps, not changes.

## 09: Kernel gain against the torch.compile baseline

Sources: `03-lifecycle.qmd` l.178, l.182, l.184; `07-feedback.qmd` l.654, l.656; `data/studies/10-kernelagent-search/summary.json`, its `raw/README.md`, and `data/studies/11-kernelagent-feedback/paired_metrics.csv`.

| Number | Line | Printed | Original output | Reimplemented, by reading | Tolerance | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| Matrix-vector search gain | l.178 | 3.49 | 3.4857 | 3.4857 (README round table 3.478; the caption names per-round records) | 0.005 | agrees |
| Best round | l.178 | 8 | 8 | 8 | exact | agrees |
| Input over torch.compile | l.182 | 4.60 | 4.5964 | 4.5964; matching-worker prompt start: 4.5973; median prompt start: 4.6049 | 0.005 | agrees |
| Round 1 over torch.compile | l.182 | 3.29 | 3.288 | 3.288 | 0.005 | agrees |
| Final speedup, matrix-vector | l.182 | 1.06 | 1.0578 | 1.0578; lowest record: 1.0601 | 0.005 | agrees |
| Final speedup, RMSNorm | l.182 | 2.31 | 2.3078 | 2.3078; lowest record, Round 8: 2.3151 (Round 3 record 2.3117) | 0.005 | agrees under one reading only |
| RMSNorm input ahead of torch.compile | l.182 | yes | yes | yes; matching-worker prompt start: yes | exact | agrees |
| Largest README and record gap, percent | l.184 | 31 | 30.8029 | 30.8029 | not in spec; comparator computed from `readme_over_records_best` | agrees |
| Transposed convolution README over records | l.184 | 1.4 | 1.4451 | 1.4451 | not in spec | agrees |
| RMSNorm, fraction of Round 1 | l.654 | 0.99 | 0.9905 | 0.9905 | 0.005 | agrees |
| Matrix-vector time, Round 1 | l.656 | 6.80 | 6.8029 | 6.8029 | exact to digits | agrees |
| Matrix-vector time, best | l.656 | 1.95 | 1.9516 | 1.9516 | exact to digits | agrees |
| Matrix-vector occupancy, Round 1 | l.656 | 24.2 | 24.24 | 24.24 | 0.01 pp | agrees |
| Matrix-vector occupancy, best | l.656 | 95.2 | 95.22 | 95.22 | 0.01 pp | agrees |
| Matrix-vector DRAM, Round 1 | l.656 | 25.8 | 25.77 | 25.77 | 0.01 pp | agrees |
| Matrix-vector DRAM, best | l.656 | 91.1 | 91.11 | 91.11 | 0.01 pp | agrees |
| MaxPool time, Round 1 | l.656 | 5.22 | 5.2163 | 5.2163 | exact to digits | agrees |
| MaxPool time, best | l.656 | 2.44 | 2.4365 | 2.4365 | exact to digits | agrees |
| MaxPool fraction of Round 1 | l.656 | 0.47 | 0.4671 | 0.4671 | 0.005 | agrees |
| MaxPool occupancy, Round 1 | l.656 | 73.3 | 73.29 | 73.29 | 0.01 pp | agrees |
| MaxPool occupancy, best | l.656 | 57.2 | 57.18 | 57.18 | 0.01 pp | agrees |
| MaxPool DRAM, Round 1 | l.656 | 33.9 | 33.92 | 33.92 | 0.01 pp | agrees |
| MaxPool DRAM, best | l.656 | 66.0 | 66 | 66 | 0.01 pp | agrees |
| Transposed convolution occupancy, Round 1 | l.656 | 24.9 | 24.93 | 24.93 | 0.01 pp | agrees |
| Transposed convolution occupancy, best | l.656 | 12.5 | 12.48 | 12.48 | 0.01 pp | agrees |
| Transposed convolution latency nearly halves | l.656 | 0.53 | 0.5269 | 0.5269 | 0.005 | agrees |
| Profile elapsed against recorded time, low | l.656 | 0.85 | inline cell | none (added after the spec; no reimplementation) | none in spec | not comparable |
| Profile elapsed against recorded time, high | l.656 | 2.11 | inline cell | none (added after the spec; no reimplementation) | none in spec | not comparable |

Reading that matches the book: per-round records for Round 1 and the lowest time, the README for `torch.compile` and the input kernel, and the README's bold best time for "final kernel". Natural: yes for RMSNorm, because `03-lifecycle.qmd` l.180 says its final kernel matches Round 3 and not the lowest record. Dividing by the Round 3 record gives 2.31 as well. Only the Round 8 record gives 2.32, which misses by 0.0051 against a tolerance of 0.005. The claim that the flat curve hides a larger gain over the baseline does not change.

The open definition of "final kernel" is what the 2.31 depends on. For matrix-vector, the two readings differ (1.0578 and 1.0601) and print the same. The l.182 sentence divides across two record sets, which the spec questions. For matrix-vector the two sets sit within 0.3%, so the printed values hold. Transposed convolution is the case where they do not: the base reading gives a final speedup of 3.71 against 2.56 and flips `input_ahead_of_tc`. The book does not print a ratio to `torch.compile` for that task.

Spec text: all quoted fragments are present; `07-feedback.qmd` l.640 and l.642 moved to l.654 and l.656. New since the spec: the l.656 sentences on profile elapsed time. The spec says Round 1 prompts report worker start times. The reimplementer found them in Round 2 prompts instead, and the book's phrase "that each task's four Round 1 workers report" (`03-lifecycle.qmd` l.184) refers to the same values.

## 10: H100 matched-workload floor and U-Net interval

Sources: `09-patterns.qmd` l.364, l.366, l.368, l.370, l.372, l.374, as rewritten at 15:08 during this comparison; `book/contents/chapters/09-patterns/data/` spread, pairs, and dividend CSVs.

| Number | Line | Printed | Original output | Reimplemented, by reading | Tolerance | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| Largest ratio, BERT | l.364 | 1.17 | 1.1662 | 1.1662; rule-score ratio: 1.1663 (first value is published minutes) | 0.002 | agrees |
| Smallest ratio, RetinaNet | l.364 | 1.03 | 1.0281 | 1.0281; rule-score ratio: 1.0281 (first value is published minutes) | 0.002 | agrees |
| RetinaNet gain, percent | l.364 | 2.8 | 2.81 | 2.8125 | 0.2 pp, from the 0.002 ratio tolerance | agrees |
| 3D U-Net ratio | l.374 | 1.08 | 1.0824 | 1.0824 | 0.002 | agrees |
| 3D U-Net interval, low | l.374 | 0.93 | 0.9318 | 0.9322; BCa: 0.9365; paired resample: 0.9246 | 0.02 | agrees |
| 3D U-Net interval, high | l.374 | 1.26 | 1.2576 | 1.2575; BCa: 1.2647; paired resample: 1.2691 | 0.02 | agrees |
| 3D U-Net interval includes no gain | l.366 | yes | yes | yes (30 of 30 readings) | exact | agrees |
| RNN-T interval, low (fig-alt) | l.366 | 1.04 | 1.0384 | 1.0384 | 0.02 | agrees |
| RNN-T interval, high (fig-alt) | l.366 | 1.14 | 1.1425 | 1.1428 | 0.02 | agrees |
| BERT interval, low (fig-alt) | l.366 | 1.11 | 1.1133 | 1.1079 (nearest reading; the fixed-count rule is not reimplemented) | 0.02 | agrees |
| BERT interval, high (fig-alt) | l.366 | 1.25 | 1.246 | 1.2415; aborted run scores as no result: infinite (nearest reading; the fixed-count rule is not reimplemented) | 0.02 | agrees under one reading only |
| ResNet-50 interval narrower than 0.02 (fig-alt) | l.366 | yes | yes | yes; aborted run keeps its logged time: no (widths: original 0.0119; nearest reading 0.0126; logged time 0.0482) | 0.02 on bounds | agrees under one reading only |
| Mask R-CNN interval narrower than 0.02 (fig-alt) | l.366 | yes | yes | yes; aborted run keeps its logged time: no (widths: original 0.0042; nearest reading 0.0043; logged time 0.4385) | 0.02 on bounds | agrees under one reading only |
| RetinaNet interval narrower than 0.02 (fig-alt) | l.366 | yes | yes | yes; aborted run keeps its logged time: yes (widths: original 0.0082; nearest reading 0.0081; logged time 0.0081) | 0.02 on bounds | agrees |
| Plotted Mask R-CNN interval narrower than 1% | l.372 | yes | yes | yes (widths: original 0.0042; nearest reading 0.0043) | 0.02 on bounds | agrees |
| Plotted RetinaNet interval narrower than 1% | l.372 | yes | yes | yes (widths: original 0.0082; nearest reading 0.0081) | 0.02 on bounds | agrees |
| Draws with no comparison, BERT | l.368 | 5,294 | 5,294 | 5,332 (different seed, so counts differ; expected 5,278, SD 62) | none in spec; comparator used 3 binomial SD | agrees |
| Draws with no comparison, ResNet-50 | l.368 | 5,170 | 5,170 | 5,157 (different seed, so counts differ; expected 5,254, SD 62) | none in spec; comparator used 3 binomial SD | agrees |
| Draws with no comparison, Mask R-CNN | l.368 | 5,195 | 5,195 | 5,245 (different seed, so counts differ; expected 5,254, SD 62) | none in spec; comparator used 3 binomial SD | agrees |
| Draws lost, BERT against ResNet-50 | l.368 | 9,114 | 9,114 | none (added after the spec; no reimplementation; comparator expected 9,146) | none in spec | not comparable |
| Draws lost, BERT against Mask R-CNN | l.368 | 9,094 | 9,094 | none (added after the spec; no reimplementation; comparator expected 9,146) | none in spec | not comparable |
| Valid-draw intervals barely move | l.368 | yes | yes | yes (largest shift, fixed to valid in the original 0.0055; `exclude_draw` against the original `valid_` bounds 0.0034) | 0.02 on bounds; "barely" has no test | agrees |
| Published ratios fall in the stated order | l.370 | yes | yes | yes (1.1662, 1.0842, 1.0609, 1.0281) | not in spec; comparator computed from published minutes in the result | agrees |
| Order holds in valid draws | l.370 | yes | pairs CSV | none (added after the spec; no reimplementation) | none in spec | not comparable |
| Four workloads do not overlap between rounds | l.370 | yes | pairs CSV | none (added after the spec; no reimplementation) | none in spec | not comparable |
| RNN-T over RetinaNet is the one separated pair | l.370 | yes | pairs CSV | none (added after the spec; no reimplementation) | none in spec | not comparable |
| v2.1 RNN-T times inside the v3.0 range | l.370 | 8 | spread CSV | none (no reimplementation) | none in spec | not comparable |
| RNN-T slow runs, percent | l.370 | 9.3 | spread CSV | none (no reimplementation) | none in spec | not comparable |
| RNN-T per-epoch ratio, all runs | l.370 | 1.09 | spread CSV | none (no reimplementation) | none in spec | not comparable |
| RNN-T per-epoch ratio, without slow runs | l.370 | 1.04 | spread CSV | none (no reimplementation) | none in spec | not comparable |
| Time per epoch, U-Net | l.374 | 1.03 | 1.0318 | 1.0318; rule_score_on_time_per_epoch: 1.0313; mean_time_per_epoch_of_runs_kept_by_time_rule: 1.0313; mean_time_per_epoch_all_converged: 1.0308; mean_time_over_mean_epochs_runs_kept_by_time_rule: 1.0315 (interval no longer printed) | 0.01 | agrees |
| ResNet scaling factor | l.374 | 1.004 | 1.0042 | 1.0042 | exact to printed digits | agrees |
| ResNet, unscaled ratio | l.374 | 1.080 | 1.0796 | 1.0796 | 0.002 | agrees |
| ResNet, published ratio | l.374 | 1.084 | 1.0842 | 1.0842 | 0.002 | agrees |
| ResNet to Mask R-CNN gap, pp | l.372 | 1.9 | 1.87 | 1.8712; published ratios: 2.3288 | 0.2 pp, from the 0.002 ratio tolerance | agrees under one reading only |
| Sessions, per-epoch range, low | l.374 | 0.996 | 0.9964 | none (added after the spec; no reimplementation) | none in spec | not comparable |
| Sessions, per-epoch range, high | l.374 | 1.074 | 1.0741 | none (added after the spec; no reimplementation) | none in spec | not comparable |

Reading that matches the book: the caption states it, "aborted counts fixed", meaning each draw resamples converged runs and holds the aborted count at the submitted number. Natural: yes as a stated rule. No reimplementation reading is this rule, so the BERT, ResNet-50, and Mask R-CNN interval rows compare against the nearest one. `exclude_draw` removes draws that retain an aborted run, which makes it the reimplemented counterpart of the study's `valid_` columns. It lands within 0.02 of those columns and of the plotted bounds. The BERT high is the largest printed gap: 1.242 against the plotted 1.246, which prints 1.24 against 1.25 and stays inside the tolerance.

The open definition of a retained aborted run still decides the plotted intervals for these three workloads. Giving the aborted run its logged time puts Mask R-CNN's low at 0.63; scoring it as no result puts ResNet-50 and Mask R-CNN at 0 and BERT's high at infinite. The current text no longer rests a claim on that choice. It says the rules give an invalid set no time, reports the lost draws, and claims no lead for any pair touching those three. So a different reading changes printed bounds and no longer changes a claim. Two earlier sentences were affected and are gone: the 14:57 text said ResNet-50 and Mask R-CNN "gains" described the submitted results and that BERT's lead "holds up on both counts".

A reading that does change a printed number: l.372 says the "1.9 percentage-point gap" between ResNet-50 and Mask R-CNN, which uses the unscaled ResNet-50 ratio. l.364 and the figure headline now speak of published ratios, and on those the gap is 2.3 points. Both values fall inside ±2.5%, so the sentence's claim survives, and l.372 already hedges on whether that band applies; the printed number does not survive. The unscaled reading is the figure's, so it is natural for a plotted gap and less natural next to "published". The spec's Ratio definition is rule-score and unscaled; the prose now names published times, and for the two extremes both print the same.

All other numbers hold in all 30 readings. The interval method (percentile, BCa, paired) moves bounds inside the 0.02 tolerance for U-Net and RNN-T, and the k tie moves ratios by about 0.00001. All 150 logs were refetched and passed both hashes, with 0 field mismatches against `mlperf-h100-runs.csv`.

Old prose, four cases, all rewritten at 15:08. (1) Spec l.325 quotes "Time-to-train ratios range from"; current l.364 says "Ratios of the published times range from". (2) Spec l.327 quotes "and lines give 95% bootstrap intervals over runs within these submissions"; the current l.366 caption has a new headline, adds "(aborted counts fixed)" and "so no lead is claimed", and changes which rule the bounds must match. (3) Spec l.333 quotes "a [VALUE]× gain in time per epoch ([VALUE]× to [VALUE]×)"; current l.374 says the two run sets "differ by 1.03×", prints no interval, and says the figure does not establish a smaller gain. The reimplemented interval (about 1.02 to 1.04) has no printed counterpart. (4) The spec does not cover the draw counts and order statements in l.368 and l.370. Lines moved from l.325, l.327, l.333 to l.364, l.366, l.374.

## 11: Implementation stage costs

Sources: `06-environments.qmd` l.417, l.419; `data/studies/20-implementation-stage-costs/time_boundaries.json`, `summary.json`, `stage-costs.csv`.

| Number | Line | Printed | Original output | Reimplemented, by reading | Tolerance | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| Outer steps | l.417 | 78 | 78 | 78; drop 0 ms steps: 74; drop steps logged as skipped: 66 | exact | agrees under one reading only |
| Sum of steps, s | l.417 | 106.3 | 106.292 | 106.292; drop steps logged as skipped: 106.279 | 0.001 s | agrees |
| Detailed routing, s | l.417 | 25.76 | 25.759 | 25.759 | 0.001 s | agrees |
| Run Test, s | l.417 | 108 | 108 | 108; log, sub-second: 108.1171 | exact | agrees |
| Job, s | l.417 | 288 | 288 | 288 | exact | agrees |
| Job over steps | l.419 | 2.7 | 2.7095 | 2.7095; drop steps logged as skipped: 2.7098 | 0.005 | agrees |
| Order of the five longest steps | l.419 | openroad-detailedrouting > magic-writelef > magic-streamout > klayout-drc > magic-drc | openroad-detailedrouting > magic-writelef > magic-streamout > klayout-drc > magic-drc | openroad-detailedrouting > magic-writelef > magic-streamout > klayout-drc > magic-drc | exact | agrees |
| Boundaries nest | l.419 | yes | yes | yes | exact | agrees |

Reading that matches the book: every outer `runtime.txt` counted, API timestamps for the two boundaries. Natural: yes for the time totals, which do not move. The count of 78 includes 4 steps recorded at 0 ms and 12 steps whose logs say they skipped, so "flow steps" that did work could be read as 66. The caption's "outer steps" fits 78 better than the prose's "flow steps". No claim changes, because the book's point concerns boundaries and not the step count.

The prose's list of what the job adds around `Run Test` omits the largest outside step, `Maximize build space` at 93 s, unless "runner preparation" covers it. That is wording, not a number.

Spec text: all quoted fragments are present at the same lines. The spec names building with Nix and enabling PDKs as unlisted job steps; the job record marks both skipped at 0 s.

## 12: Shuttle totals, first-seen count, and catalog shipment labels

Sources: `12-ecosystem.qmd` l.140, l.142, l.146; `book/contents/chapters/12-ecosystem/data/` figure CSV and `tinytapeout-receipts/design-repeats-summary.json`.

| Number | Line | Printed | Original output | Reimplemented, by reading | Tolerance | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| Design submissions | l.140 | thousands | thousands | thousands (total 4,026; the spec's slot held a number, and the prose now prints a word) | exact on the total | agrees |
| Mean per run | l.140 | 183 | 183 | 183 | 0.5 | agrees |
| Cumulative total | l.142 | 4,026 | 4,026 | 4,026 | exact | agrees |
| Plotted runs | l.142 | 22 | 22 | 22 | exact | agrees |
| TT03 carried from TT02 | l.142 | 149 | 149 | 149 | exact | agrees |
| TT03 catalog count | l.146 | 100 | 100 | 100 | exact | agrees |
| Total with carryover | l.146 | 4,175 | 4,175 | 4,175 | exact | agrees |
| Further indexed runs | l.146 | 5 | 5 | 5 | exact | agrees |
| TTCAD25a modules | l.146 | 257 | 257 | 257 | exact | agrees |
| TT09 modules | l.146 | 369 | 369 | 369 | exact | agrees |
| TT09 modules on TTIHP25a | l.146 | 333 | 333 | 333; spec definition, API names: 329; subtiles dropped: 146 (first value is the index reading) | exact | agrees under one reading only |
| First-seen total | l.146 | 3,100 | 3,139 | 3,139; index, no groups: 3,140; subtiles dropped: 3,097; case-folded: 3,132 (group macros added 3,155 and 3,156, not designs) | 0.5% | agrees |
| New names, 2022 | l.146 | 318 | 318 | 318 | 1% | agrees |
| New names, 2023 | l.146 | 401 | 401 | 401; index: 400 | 1% | agrees |
| New names, 2024 | l.146 | 827 | 827 | 827; index: 828 | 1% | agrees |
| New names, 2025 | l.146 | 642 | 642 | 642; index: 643; subtiles dropped: 600; launch order, typo kept: 630 | 1% | agrees under one reading only |
| New names, 2026 | l.146 | 951 | 951 | 951 (launch order with the typo kept 963; the prose says closing year) | 1% | agrees |
| Last close month | l.146 | July | July | July | exact | agrees |
| Entries, 2024 | l.146 | 957 | 957 | 957 | exact | agrees |
| Entries, 2025 | l.146 | 1,233 | 1,233 | 1,233 | exact | agrees |
| TT01 entries | l.146 | 152 | 152 | 152 | exact | agrees |
| Runs marked shipped | l.146 | 7 | 7 | 7 | exact | agrees |
| Entries on them | l.146 | 1,075 | 1,075 | 1,075 | exact | agrees |
| Shipped share | l.146 | 26.7 | 26.7014 | 26.7014 | exact at 0.1 | agrees |
| Test-shuttle runs | l.146 | 5 | 5 | 5 | exact | agrees |
| Test-shuttle entries | l.146 | 371 | 371 | 371 | exact | agrees |
| Other runs | l.146 | 10 | 10 | 10 | exact | agrees |
| Names with more than one owner | l.146 | 70 | design-identity-sensitivity.json | none (added after the spec; no reimplementation) | none in spec | not comparable |
| Repository key, rise | l.146 | 8 | design-identity-sensitivity.json | none (added after the spec; no reimplementation) | none in spec | not comparable |
| Repository key, estimate | l.146 | 3,400 | design-identity-sensitivity.json | none (added after the spec; no reimplementation) | none in spec | not comparable |
| Wokwi-numbered names | l.146 | 880 | design-identity-sensitivity.json | none (added after the spec; no reimplementation) | none in spec | not comparable |
| TT06 feedback sentence | l.146 | 238 | no raw file here | none (out of scope) | out of scope in the spec | not comparable |

Reading that matches the book: the first-seen totals and years match the spec's reading, which uses API names with the index for TT02 and TT03. The 333 does not. It comes from the shuttle indexes for both runs, subtiles kept and groups dropped, as `index_comparison` records. The same paragraph therefore uses two name sources: 329 is what the API names in the first-seen walk give, against the 333 it prints. Under the spec's definition and exact tolerance the 333 misses. Natural: "by name" does not say which source, and the spec lists this as open, so the open definition is what makes 333 the number. The source difference is 4 names and changes no claim.

Dropping subtile entries is a larger swing. It gives 146, so fewer than half of TT09 reappears, against the FAQ's "most digital designs" in the same sentence. That reading is not the natural one, since subtiles are designs on the run, but no text states the rule. The same choice takes 2025 new names from 642 to 600, outside the 1% tolerance. The book's dip and 2026 high survive it, and the total still rounds to 3,100.

The "about 3,100" is 3,139 rounded to hundreds. The printed value is 1.2% below the unrounded count, and the 0.5% tolerance applies between implementations, which match exactly. 11 of the 13 readings print 3,100; the 3,155 and 3,156 readings count group containers, which are not designs, and would print 3,200.

The word "shipped" holds under the catalog label only; provenance says the label does not establish shipment, and the book says "marked". TTSKY25a and TTIHP25a have estimates before August 2026 and no shipped label. The retained catalog is commit 7a575614d5 of 2026-07-27, a stand-in for the 2026-08-22 capture, so "August 2026 catalog snapshot" and every shipment figure cannot be tested against the snapshot.

Old prose: spec l.132 "has drawn [VALUE] design submissions" now reads "thousands", so a printed number left the sentence. Spec l.138 "designs carried over from TT02, which would raise" now carries a link and reads the same; that is markup only. Lines moved from l.132, l.134, l.138 to l.140, l.142, l.146. New since the spec: the 70, 8%, 3,400, and 880 identity sentences, whose claim "the 2025 dip and the 2026 high hold under both keys" is not reimplemented.

## Limits of this comparison

- `result.json` values were read, not regenerated. The reimplementation folders hold no inputs, so `compute.py` cannot be rerun from them as they stand.
- Printed values come from running each chapter's inline cells in a scratch copy with figure writes disabled, then asserting each printed string against the rendered line. Generated by scripts in the session scratchpad, not retained in the repository.
- Rows marked fig-alt are read from alt text. Figure images were not inspected.
- For transcribed datasets (specs 03, 04, 07, 08), the original output is the CSV with the book's arithmetic, so agreement shows arithmetic, not transcription. Reimplementers of 03, 04, and 07 compared cells with fetched sources; spec 08 has no retained source.
- Only numbers in or beside the spec quotes are tabulated. The chapters print many others that no spec covers.
- The tolerance for draw counts in metric 10 is the comparator's, not the spec's, because no spec covers them.
- Reimplementers shared a model family with the producers, and the same blind spots may sit on both sides. Several saw result values among their inputs, as their notes state: 03, 04, 07, 08, 09, and 10.
- Conduct items in the notes: spec 01 truncated a `/tmp/x` file it did not own, and spec 02 installed numpy from PyPI against its brief, then removed it. Neither touched results by their accounts. Spec 02's issue parser was written after seeing the body, because two inputs arrived late.
- The August 2026 catalog capture does not exist, so no shipment figure in metric 12 was tested against the snapshot the book names.

