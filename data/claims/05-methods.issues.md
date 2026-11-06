# 05-methods: sentences that look unsupported

Recorded by the ledger pass for `data/claims/05-methods.yml`. The chapter was not edited.

## Support problems

1. **CLM-05-030, MAESTRO "far too large to evaluate exhaustively."** The sentence calls these "accelerator mapping spaces" and says they are too large to evaluate exhaustively. The MAESTRO paper reports a hardware design space exploration over four hardware parameters: 480M designs searched, 2.5M valid, at 0.17M designs per second, with four runs finishing within 24 minutes. That is a hardware sweep with pruning, not a mapping space, and it completed. Chapter 2's table describes the same numbers as DSE, so the two chapters disagree. Timeloop is unopened (the fetch returned no paper), so its half is unchecked.

2. **CLM-05-045, "tune in thirty evaluations."** No citation, no study, and no mark that the figure is illustrative. Kept as `assumed` with no evidence rather than `constructed`, because the chapter does not read as an example here.

3. **CLM-05-047 and CLM-05-048, "in milliseconds" and "sub-second latency."** Stated as facts with no source or measurement.

4. **CLM-05-013, "their cycles and utilization match exactly."** True only for the fields the score uses (`Total Cycles`, `Overall Util %`). `Total Cycles (incl. prefetch)` differs (17,371 against 17,500 summed), and `Compute Util %` differs on every layer (50.59 against 44.91 on layer 0). The study README records the prefetch difference. The chapter does say the score excludes prefetch, but "exactly" reads wider than that.

## Weaker than the prose implies

5. **CLM-05-011 and CLM-05-012, fold arithmetic.** The study record does not contain this derivation. I fit cycles = folds x (2R + C + M - 2) - 1, with folds = ceil(K/R) x ceil(N/C), and it matches all 36 layer rows in the twelve retained reports. That is a fit to outputs, not a reading of SCALE-Sim's source. Labeled `modeled`.

6. **CLM-05-005, Chip-Chat.** The chapter says "human engineers." The paper describes "a hardware engineer," singular.

7. **CLM-05-034, Ovadia.** The source measures classifiers under dataset shift such as image corruption. It does not study a candidate distribution moved by an optimizer, so the citation supports the general lesson by analogy only.

8. **CLM-05-001, KernelBench range.** The prose gives 0 to 67 percent without saying this covers four models. Table 1 lists seven for fast_1, and correctness is printed only for the plotted four. The figure caption does say four. Correction, 2026-11-02: Figure 7 also prints one-shot correctness for GPT-4o, Claude 3.5 Sonnet, and Qwen coder, so "only for the plotted four" holds for the tables, not for the paper.

## Evidence to re-check

9. **CLM-05-020, ArchGym digitized values.** The prose matches the CSV, but I did not re-read the bars in Figure 7(a). In the CSV, BO is 0.112 / 0.042 / 0.182 at three consecutive budgets and the random walker's mean is 0.132 at three. That may be plateaus, or it may be a digitization artifact. An auditor should look at the image.

10. **CLM-05-004, Sakana.** The bib URL now redirects to a different report and no longer carries the acknowledgment. The support survives only in the Wayback snapshot named in the bib note, so the URL should point there.

11. **Source copies.** KernelBench, PrefixRL, AutoTVM, and Chip-Chat were read from text copies already in this session's scratch directory, not fetched by this pass. Their titles match; the KernelBench copy was not confirmed to be arXiv v1. The 2026 Cheng claim was read from arXiv, not the TCAD copy.

## Unopened

CLM-05-030 (Timeloop half), CLM-05-035 (Schlansker and Rau), CLM-05-036 (Smith and Winkler), CLM-05-038 (Kleinrock), CLM-05-039 (Amdahl). The last three are classical results whose derivations were followed by reading.

Descriptive tool citations that report no result (PowerNet, ChatEDA, AutoBench, Apollo, DeepRM, VerilogEval, RTLLM, and similar) are not in the ledger and were not opened.

## Resolutions, 2026-11-02

This list records the ledger pass as it stood. The state below replaces it.

- Item 1 (CLM-05-030): closed. The MAESTRO text left the chapter; the claim now rests on Timeloop, opened.
- Items 2 and 3 (CLM-05-045, 047, 048): closed. The "thirty evaluations", "in milliseconds", and "sub-second" text left the chapter, and these three IDs were retired with it.
- Item 4 (CLM-05-013): closed. The prose names both unread fields and gives their effect (CLM-05-055).
- Item 6 (CLM-05-005): closed. The chapter says "a hardware engineer".
- Item 8 (CLM-05-001): closed. The prose says four plotted models.
- Unopened list: Timeloop, Schlansker and Rau, Smith and Winkler, and Amdahl were opened. Kleinrock (CLM-05-038) remains unopened; its derivation was followed by reading.
- Items 5, 7, 9, 10, and 11 stay as recorded. Item 10 waits on a bib change.
