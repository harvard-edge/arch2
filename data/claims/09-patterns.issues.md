# 09-patterns: sentences that need the author's attention

Updated by the round 4 ledger repair, 2026-11-02. The repair is producer work. Nothing here is an independent audit.

## Evidence not opened
- CLM-09-023, workload characterization: only the abstract was read, in the Ghent repository record. Full text is UGent-only there and paywalled at IEEE. The sentence now says what the abstract says, and the claim stays `unopened`.
- CLM-09-001, dataset shift: the book's Chapter 1 was read in Storkey's author-hosted copy. The book itself returned 403, so print wording was not compared.
- CLM-09-028, UCIe: the specifications are by request and were not opened. The sentence now rests on the consortium chair's public slides, which are not independent of UCIe.

## Audit status
- All data-backed figures in this chapter have PASS records in `data/audits/`. `fig-ch09-mlperf-software-dividend` was audited by `codex-ch09-fifth`, a name that points to a different model family from the producer, though the record does not state the model. `fig-ch09-mlperf-latency-contract`, `fig-ch09-linux-arm64-errata-workarounds`, and `fig-ch09-money-plot-software-porting-wall` were audited by `red-team-round5-ch09-baseline-second`.
- The prose around those figures is not bound by the gate. The MLPerf passage and the sentences changed in the final fix pass of 2026-11-02 have not been audited.
- `book/contents/chapters/09-patterns/data/provenance.yml` now records the PASS and keeps the failed-audit history in its defects list.
- The dividend caption still lacks the limit that its intervals are not uncertainty of the gain. The prose carries it. The caption change is escalated, because a caption edit makes the PASS stale.

## Ledger labels
- Chapter rule since the final fix pass: a vendor rating or performance statement is `assumed`, and this book's computation on third-party logs is `modeled` / `own-run`.
- The four-label schema has no slot for definitions, specification or rule statements, and authors' claims. They carry `assumed` with an assumption line saying so. A separate `source-statement` label needs a schema decision.
- CLM-09-073 stays `measured` / `third-party-reported`, because AutoTVM's speedup is a value its authors measured.

## Evidence that is thin
- CLM-09-032: Kconfig help text names affected revisions, so workaround selection by revision is supported. Nothing retained shows a result that differs between revisions. The sentence says "need not hold", which is as far as this goes.
- CLM-09-075: the statement that the retained run data do not show an M>N selection rests on `mlperf-h100-runs.csv`, which has no field for it. Raw logs are not retained.

## Wording
- CLM-09-007, "recommended retaining": the retained record has `accountable_decision_status: awaiting_author_confirmation`. The chapter's wording fits a recommendation, so this needs only your confirmation.
- CLM-09-070: Horowitz's prose says 1 to 2 nJ, and the chapter takes the table's 1.3 to 2.6. The sentence now says the 64-bit reading is ours.
- CLM-09-043: the fig-alt values are typed literals, as are the alt-text counts for the Linux figure. Both figures have PASS audits, so this is escalated. Typed prose counts such as "eight of the ten", "Four of the ten", and "the seven" are asserted in the cell but are not computed values.

## Bibliography
- `RISCV2026UnprivilegedISA`: the note says RVWMO is in Chapter 14. In version 20260120 it is Chapter 18.
- `Brooks1986NoSilverBullet`: the key says 1986 and the entry is the 1987 Computer article. The epigraph matches two web reprints of the Computer text, but not the UNC report or a later reprint. The page was not checked against the Computer pages, so the `p. 10` pin was cut.

## Later repair, 2026-11-02

- **fig-ch09-mlperf-latency-contract.** The audit record is FAIL, and the PASS statement above no longer holds for this figure. CLM-09-077 and CLM-09-078 were removed with their sentences; CLM-09-005 was restated.
