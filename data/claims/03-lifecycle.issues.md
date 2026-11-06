# 03-lifecycle ledger issues

Sentences and sources the ledger could not fully support. Rewritten against the current ledger on 2026-11-02.

## Claims without evidence

- `not_claims`, opening section (formerly CLM-03-001): the failure modes are labeled anticipated in the chapter, which is accurate. No run, case, or citation backs them.
- `not_claims`, Stage 3 (formerly CLM-03-022): the runtime clause leans on CLM-03-037 and chapter 7. The commercial license clause has no source and no retained record, and the sentence says so.
- `not_claims`, Stage 3 (formerly CLM-03-023): the ordering of check cost has no citation in this chapter. CLM-03-037 supports lint, synthesis, and routing for one open-flow run with no functional-simulation step. Chapter 7 discusses the ordering in general terms.

## Pending the bibliography

- Zhang et al., arXiv 2607.16241, the published challenge to KernelBench speedups, has no entry in `references.bib`. The chapter states the correctness limit (CLM-03-033) without this citation until the entry exists.
- `Cheng2025KernelAgentArtifacts` has key year 2025 and bib year 2026.

## Citations to check

- CLM-03-031 (22 nm) has no citation in this chapter because the sentence points to @sec-mobile-xr-evaluation, where CACTI 7 is cited. The limit rests on upstream `parameter.cc` at the pinned commit and on the retained probe. `tech_params/16nm.dat` ships in that tree, so the docstring in `run_cacti_lighthouse_l2.py` ("the smallest node CACTI 7 characterizes") is looser than the chapter's "supports". The upstream README lists 90 to 32 nm.

## Evidence limits to keep visible

- CLM-03-010: the 3.29x ratio divides a per-round record by a `torch.compile` value from the summary table. The chapter says the two sets may come from different procedures. The matrix-vector table and records agree to three decimals in Rounds 1 to 7, so the effect here looks small, but no per-round record exists for `torch.compile`.
- All KernelAgent numbers are third-party single reported values. They were transcribed and recomputed here, not rerun on a GPU. Kernel correctness was not repeated (CLM-03-033).
- CLM-03-032 and CLM-03-038 use a small-sample yardstick chosen after the data was seen. It is reported as the widest of five and works against the claim.
- CLM-03-029: the card does not say whether the 22 nm stand-in evaluations draw on its SRAM budget.
- The source repository has no license file, per `data/studies/10-kernelagent-search/provenance.yml`.

## Sources not fully opened

- `HoMaiHorowitz2001FutureOfWires`: abstract only (`unopened`, CLM-03-024). Full text is paywalled.
- `Vaughan1996Challenger`: not opened (`unopened`, CLM-03-026). The paraphrase and any page number remain unchecked.
- `KwonEtAl2023XRBench` and `OuyangEtAl2025KernelBench`: abstracts only, which is enough for what the chapter says of them.
