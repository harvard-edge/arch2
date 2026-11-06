# Chapter 11 ledger issues

Recorded by the ledger pass on 2026-11-02. The chapter was not edited.

## Sentences the evidence does not fully support

1. **Resolved 2026-11-02: the sentence is gone, and the chapter now states the departure from the written rule (CLM-11-048).** **Reason for the class merge (CLM-11-020).** The chapter says the largest class combines I/O, memory controllers, and coherence "because the audit could not reliably separate coherence errata from those neighbors." In `audit_sample.csv`, the 8 coherence entries the audit relabeled went to power (4), machine check (3), and I/O (1), with none to memory controller. `reporting_classes.yml` says a failed class merges with the class it is most often confused with, which would be power. The shares reproduce; the stated reason does not.
2. **Resolved 2026-11-02: the 120 FPS target was cut (CLM-11-003).** **120 FPS has no origin (CLM-11-003).** The chapter calls it "the proposed 120 FPS operating point," but no other chapter states it and nothing retained proposes it. The 3 W target is declared in the Chapter 1 request.
3. **Resolved 2026-11-02: both dollar phrasings were cut (CLM-11-005, CLM-11-046).** **Respin dollars (CLM-11-005).** Patel gives mask-set totals and says a revision needs some new masks and a few months. It gives no respin cost, so "millions of dollars" is an inference. The same applies to "multimillion-dollar silicon mask respins" in `tbl-architect-technical-judgments`, which has no citation and no claim of its own.
4. **Mask figures (CLM-11-001, CLM-11-015).** The chapter calls them an analyst estimate, which fits. The article shows no source table or method for the node figures. They are labeled modeled, not measured.
5. **UCIe package redesign (footnote `fn-ucie-phy-c11`).** A text search of `UCIeConsortium2024Overview` found no statement that adding lanes may require an expensive package redesign. The Das Sharma slides do support the bump pitches and link rates. They say standard package, not "organic," and the interposer example is CoWoS; bridges are not named in the matching lines.
6. **Unsourced assertion (Open Questions).** "Standard text and token scanners fail on hardware descriptions" has no citation. It is not a measured result, so no claim was opened.

## Evidence state

- **Claims without evidence:** CLM-11-003 and CLM-11-004 are constructed author examples and have no file or citation. The validator reports both. Citing the book's own Chapter 1 would pass the check without adding evidence, so the fields stay empty. The ledger needs a decision on how constructed claims are evidenced.
- **Unopened:** CLM-11-006, `SeilerEtAl2008Larrabee`. The ACM page returned HTTP 403.
- **Web sources not retained:** Patel, the four Intel press releases, and both UCIe documents were opened online for this pass. No copy is in the repository, and the UCIe PDFs sit only in a session cache.
- **Audit-dependent numbers:** the 76% agreement, adjusted shares, and 4 of 231 are labeled modeled because the labeler also wrote the rules, as the chapter discloses.
- **Array study label:** this ledger says modeled for SCALE-Sim outputs, matching `evidence_status: computed_by_scale_sim_not_measured_silicon` in `study_results.json`. The study's `provenance.yml` says `evidence_class: measured`.
- **Errata PDFs:** of the 19 sources, 15 PDFs are under `13-errata-dispositions/raw/pdf`. Alder, Meteor, Lunar, and Arrow Lake are absent, and `RaptorLake.pdf` does not match the hash in `sources.csv`. The per-document identifier match behind CLM-11-014 was therefore not rerun; only the recorded columns and their arithmetic were checked. `replay.py verify` passed for the array study, with its known prompt limitation.
- **Figure audit (updated 2026-11-02):** `fig-errata-subsystem-shares` has an audit record in `data/audits/` with verdict FAIL, pending the author. The figure stays unpassed.

## Validator defect

**Resolved 2026-11-02: `validate_claims.py` now strips code cells before the inline check, and this chapter reports no such errors.**

`INLINE` in `data/validate_claims.py` runs on the raw text, so a fence such as three backticks followed by `{python}` matches it. Each code cell then counts as an inline value and fails with "inline value #| echo: false". This chapter gets three such errors. They are not fixable from the ledger without pasting code cells into `inline_values`, which was not done. Every chapter with a Python cell should show the same error.
