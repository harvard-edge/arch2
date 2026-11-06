# 06-environments ledger issues

Round 4 repair of 2026-11-02 acted on every entry below; the outcome of each is in the ledger. The text below is the original record. Kleinrock stays unopened.

Recorded while writing `data/claims/06-environments.yml`. The chapter was not edited.

## Unsupported

- **CLM-06-010, local minima.** "Changing which passes run and in what order steers the optimization into different local minima" gives a cause. The recipe dataset shows only that area differs. The claim has no evidence, so the validator reports it. It needs a citation or softer wording.

## Supported, with a gap in the receipt

- **CLM-06-028 and CLM-06-030 to CLM-06-033, CACTI returns.** Only parsed values are retained. Raw CACTI stdout is not, so the values cannot be checked against the tool's own output without rerunning it.
- **CLM-06-029, 22 nm floor.** The sentence is supported by `parameter.cc` at the pinned commit, where the 22-to-16 branch is commented out. That source is not retained in this repository. The README at the same commit still lists 90 to 32 nm, and the fetch of the CACTI 7 paper returned HTTP 403. A reader who checks the README will find a different floor. Retaining `parameter.cc` would close this.
- **CLM-06-008, re-derived areas.** The 125 of 125 match is stated in the CSV header and in the rerun described in `data/audits/fig-eda-runtime-variance-dispersion.yml`. No rerun log is retained, and the audit notes that the reproducer is not a hash-bound input.
- **CLM-06-009, removed columns.** The reasons for removal are stated only in the CSV header. The removed values are not retained, so the mismatch cannot be rechecked.

## Wording

- **CLM-06-026, Mytkowicz.** The paper varies UNIX environment size. The chapter says "environment-variable layout". "Size" matches the source.
- **CLM-06-017, WNS median.** The sentence reads "its median magnitude (-156.5 ps)". A magnitude is printed with a negative sign. The percentage is computed correctly against the absolute value.
- **CLM-06-024, ZSim.** "Averages" means harmonic mean, and the 12.4 and 14.8 figures are for the two contention settings of the OOO model. The source supports the sentence, but the chapter does not say which mean.

## Sources opened

Fetched on 2026-11-02 and read: ZSim, FireSim, Mytkowicz. Not opened: CACTI 7 (HTTP 403), Kleinrock (book). Tool-attribution citations (ABC, OpenPiton, IHP PDK) name tools only and carry no claim, so they were not opened.
