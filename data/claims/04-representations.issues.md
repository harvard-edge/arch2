# 04-representations: open items

Refreshed 2026-11-02 against `data/claims/04-representations.yml`, the audit records, and the chapter. `data/validate_claims.py` reports no error in this ledger.

## Labels

1. **CLM-04-036 and CLM-04-038 pass as `constructed`.** The prose says "by our reasoning" and "our reading", and no study or agreement stands behind either. The validator accepts `constructed` as evidence. CLM-04-020, 021, 022, and 024 (readings of absence) and CLM-04-041 (a process statement) sit under `measured` because no label for "read from the paper" exists.

## Evidence state

2. **AST sensitivity values sit outside the PASS audit.** CLM-04-070 and CLM-04-071 come from a JSON that the audit does not bind.

3. **CLM-04-082 is unaudited.** The clock-like signal shares come from a column of the audited CSV that the audit did not attack.

4. **Run records.** The AST miner has no run log; the study's `runs.jsonl` holds only the sensitivity run. Attempts before the first logged dilation run have no logs. The dilation file-selection rule was not recorded, which the chapter discloses.

5. **Provenance class mismatch.** `data/datasets/provenance.yml` calls `chapter4-simulation-time-explosion.csv` transcribed. The file's own header says arithmetic, not measurement.

6. **Selection effect in the nested stratum is not sized.** CLM-04-053 says the selection favors the gap. No comparison restricts different-signal uses to the same local scope.

7. **Line 663 premise has no citation.** The chapter marks clock domains and bus interfaces as common design practice, not a measurement. `Cummings2008CDC` is in the bibliography, but nobody has opened it.
