# 02-pressures: issues found while writing the ledger

The chapter was not edited. Each item names the claim and what was checked.

## Claim with no evidence

- **CLM-02-003.** The footnote on subthreshold leakage (60 mV per decade, tenfold leakage) has no citation. It also says this is why supply voltage stopped falling, which is a causal claim with no source.

## Sentences that look stronger than what I opened

- **CLM-02-052, "A window that closes at 2024".** The code keeps `y <= 2024`, and `y` is a decimal year, so the window ends on 1 January 2024 and drops every 2024 record. That gives 3.7 from 371 records. Ending at the close of 2024 gives 4.1 from 419 records, on the same regression. A reader will take the sentence to mean the second.
- **CLM-02-047, Epoch rate.** The prose says "for notable models". The cited page's headline finding is about frontier models, the running top ten by training compute, and it reports similar growth for notable models. Worth checking which population the sentence should name.
- **CLM-02-049, "frozen July 2026 snapshot".** I found no recorded retrieval date in the CSV header or in `data/datasets/provenance.yml`. The latest record is dated 2026-07-15, which is consistent with the sentence and does not establish it.
- **CLM-02-080 and CLM-02-082, Arm prospectus.** The dollar values and the 71% match. "July 2022" did not appear in the first 200,000 of 485,682 characters of the filing, where the IBS sentences sit, and the IBS sentences carry no date. The dataset also records July 2022. The rest of the filing was not read. The filing spells the firm "International Business Strategy, Inc."; the chapter writes "Strategies".
- **CLM-02-077, RTL benchmarks.** RTLLM reports syntax and functionality failures. VerilogEval's abstract names functional tests only. I did not find "interface compliance" in what I opened. OpenRTLSet is a dataset paper and was not opened, so I cannot say what failure it reports.
- **CLM-02-058, AutoTVM.** The abstract says "billions of possible program variants". "For a single GPU operator" was not confirmed, because only the abstract was opened. The paper PDF timed out.
- **CLM-02-035, Pal et al.** The abstract says "about 100" modules and "about 40" buildable. "Reduced usable capacity" can read as an observed result, but this is a design study with no fabricated wafer.
- **CLM-02-075, Foster 2024 report.** The public landing page lists no respin causes. The report was not opened, so the list of mechanisms in this sentence is unconfirmed here.
- **CLM-02-008, Hennessy and Patterson.** The book was not opened. "About 23% per year" has no date range in the prose, unlike the 52% rate beside it.
- **CLM-02-062, FX-9590.** The cited document is a Spanish-language channel brochure. Its row is labeled "Watt/Vatio" with 220, not TDP.
- **Summary, "a wider vector grouping can trigger register spills".** The chapter says its examples make these couplings concrete. This one was never run and carries no number, and the sentence does not read as an illustration.

## Provenance gaps

- **Horowitz.** Figure 1.1.9 prints 1.3-2.6 nJ for DRAM, matching the chapter. The same paper's prose says "1 to 2nJ". No change is needed; a reviewer may ask.
- **Study 12.** `data/studies/12-mlperf-latency-contract/provenance.yml` records that `raw/summary_results.json` is absent, so pair selection is not rechecked on rerun. The numbers recompute from the retained logs.
- **Hameed DOI.** `references.bib` gives 10.1145/1815961.1815968. The CSV headers give 10.1145/1815961.1816001. I did not resolve which is right.
- **Wilson 2007-2020 labels.** I read the post text, not the chart image. The printed labels rest on the dataset and on `data/audits/fig-verification-demand-scissors.yml`.
- **Unaudited figures.** These have no record in `data/audits/`: fig-accelerator-landscape, fig-ch02-accelerator-scaling-frontier, fig-ch09-mlperf-latency-contract, fig-ch09-money-plot-software-porting-wall, fig-data-movement-energy-scale, fig-design-cost-by-node, fig-training-compute-growth.

## Later resolution, 2026-11-02

- **CLM-02-080 and CLM-02-082, July 2022.** The audit of fig-design-cost-by-node found this file and the ledger in conflict. No direct text of the filing could be retained, and summarized reads of all 485,682 characters found no date or Source line. The chapter no longer states July 2022, and the ledger entry records why. The entries above stand as written.
- **Frontier flag.** The CLM-02-047 entry above says top ten. Epoch's documentation says top 5, and the chapter now says top five.

## Correction, 2026-11-02, second repair of the chapter 2 baseline figures

- **CLM-02-080, July 2022.** The resolution above was wrong. The filing prints "Source: IBS July 2022." directly after the chart in the Business section. The earlier edit withdrew the date on summarized reads, and that withdrawal was an error. The date is restored in the prose, caption, dataset, and ledger. The entries above stand as written.
- **CLM-02-081, reports differ.** The entry named 7\ nm alone. The two reports differ at all five shared nodes, the 2018 article higher at each by 6.9% to 20.8%, and neither states why.
- **fig-design-cost-by-node, selection.** The figure plots 5 of 15 published chart points, and the prose and caption now say so. The 10 others are in the dataset as plotted=no. At 5\ nm the figure shows LaPedus's \$542.2M and Arm's chart prints \$449M.
- **Arm chart, labels against bars.** By pixel reading of the image, the drawn bars sit about 5% below their printed labels. The file uses the printed labels, which agree with the filing text at 7\ and 2\ nm. The filing does not explain the difference. Not stated in the chapter.
- **fig-ch02-accelerator-scaling-frontier, citations.** The values were read from NVIDIA whitepapers. The four IEEE Micro papers were cited without being opened and are closed access by OpenAlex. They are removed from this figure's caption and prose, and the whitepapers are cited instead, pending bib entries.
- **Still open.** FoleyDanskin2017Pascal in CLM-02-014, and the same Micro keys in the chapter's two paragraphs on the microprocessor trends and transistor counts, remain cited and unopened. Those sentences fall outside this repair.
- **P100 bandwidth.** The datasheet prints 732\ GB/s; the A100 whitepaper table prints 720\ GB/sec. 732 is plotted, and the balance point prints as 29 under either.

## Final fix pass, 2026-11-02

- **Still open above, now resolved.** FoleyDanskin2017Pascal and the three Choquette keys left the chapter; the NVIDIA whitepapers that were read replace them. HennessyPatterson2017QuantitativeApproach left the chapter; the 2019 CACM article, opened, replaces it. Williams2009Roofline was opened through eScholarship.
- **Still unopened.** ButlerEtAl2011Bulldozer is paywalled. An AMD workshop deck read in its place confirms the organization, but it is not in the bibliography.
- **Hameed.** CLM-02-023 to 030 are relabeled modeled. The 3 to 5% read error in the staged-energy CSV header has no receipt; the book no longer prints it.
- **Bulldozer callout.** It now states a design trade-off. CLM-02-062 and CLM-02-064 are retired with the sentences they supported. Launch reviews show the shortfall but no such source is in the bibliography.
- **fig-ch09-mlperf-latency-contract repair.** Caption, alt text, and prose now say the shares follow the submitters' target rates. The audit record stays FAIL and is stale until a fresh audit. The rule text behind CLM-02-123 has no bibliography entry.

## Repair of 2026-11-06 (chapter text revised, evidence files moved)

- **2007-2022 growth (CLM-02-066, 073, 074, 146).** The 6.2, 2.7, 146, and 50 percent figures reproduce from the CSV only because the 2022 row was constrained to the study's callouts. The recomputation (6.18, 2.74, 145.8, 50.0) is a consistency check, not independent evidence. The stated values come from the 2022 study text.
- **Deleted.** CLM-02-070, 071, 105 (gap, ratio, and re-indexing sentences) no longer appear in the chapter.
- **Restamped without value change.** CLM-02-044 to 046 and 092 to 095 changed only because `measure_software_porting_wall.py` changed (paths, commit column, step-file output, a read error now stops the run). Their values follow from the unchanged CSVs. The harness was not rerun here.
- **CLM-02-136.** The 3,352 GB/s row is marked Not Finalized in the H100 whitepaper. The product 2 x 2619 MHz x 5120 bits / 8 gives 3,352.3, which is the CSV header's own cross-check, not a second source.
- **Format.** The ledger file was re-serialized with PyYAML, so the diff touches unchanged entries in layout only.
