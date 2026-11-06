# 01-moonshot claim issues

- **CLM-01-009, wrong study name.** The sentence opens "In the Wilson Research Group studies" and gives the 2007 mean. Foster's Part 5 credits the 2007 value to the Far West Research study; Wilson begins in 2010. The 49 percent also conflicts with 46 percent in Foster's DAC 2015 paper, according to the header of `data/datasets/chapter7-wilson-verification-scissors-gap.csv`, which leaves 2007 blank for that reason. I did not open the DAC paper. The chapter shows only the 49.
- **CLM-01-010, mixed populations.** The 2010 and 2012 means are for non-FPGA designs, and 2014 to 2020 are for ASIC/IC projects. The sentence does not say so. The 53 percent minimum comes from 2018, so the bound does not depend on the older values.
- **CLM-01-017, "logic optimization".** The Spectrum article describes an LLM workflow around XLS high-level synthesis and "AI-guided physical design optimization", including a 10 percent area reduction. I found no "logic optimization" there. The OpenAI post may support it, but it returned 403, so this wording is unverified.
- **CLM-01-018, unverified negative.** The sentence says the reports omit a controlled total-cost comparison and a closed loop. This was checked against Spectrum only.
- **CLM-01-019, "spans several frames".** The ILLIXR preprint defines motion-to-photon latency, gives targets of 20 ms for VR and 5 ms for AR, and lists a 120 Hz display (8.33 ms). Those targets are at most about 2.4 frames, and the AR target is under one. Stages do have separate deadlines. The several-frames wording is an inference, not a statement I found in the source.
- **CLM-01-015, Goldie citation scope.** Goldie et al. (2024) answers the earlier ISPD 2023 assessment, not the updated 2026 paper cited beside it. The dispute is real, but the pair does not show a direct exchange.
- **CLM-01-020, no evidence.** "Runs that take hours and can disagree" has no citation or data file.

## Round 4 resolutions (2026-11-02)

The findings above are kept as written. Three statements in them were later overtaken: the OpenAI post was read through a Wayback snapshot, the negative in CLM-01-018 was checked against both sources, and the pair in CLM-01-015 is a direct exchange.

- **CLM-01-009, fixed.** The sentence now credits 49 percent to the 2007 Far West Research study, as given in the 2012 report. The DAC 2015 value of 46 remains unopened (ACM returned 403).
- **CLM-01-010, fixed.** The sentence names both populations. Figures read directly.
- **CLM-01-017, fixed.** "Logic optimization" became "optimization of arithmetic circuits", OpenAI's own wording. Broadcom wording follows Spectrum.
- **CLM-01-018, checked.** Sentence unchanged; both sources read.
- **CLM-01-019, fixed.** "Spans several frames" and "pipelined across frames" were removed; the sentence now states different rates, own deadlines, and a separate latency target.
- **CLM-01-015, rejected.** The TCAD text states that it responds to Goldie et al. (Section I and Table XII), so both citations stay.
- **CLM-01-020, fixed.** "Take hours" was cut. The disagreement is restated as a fast estimate ranking candidates differently from the slower tool, cited to Cheng et al. and Goldie et al.

## Round 5 resolutions (2026-11-02, final audit `final/ch01.md`)

- **CLM-01-009, retired.** The sentence giving the 2007 Far West Research mean of 49 percent was deleted. The dataset withdrew that value because Foster's sources disagree, and the bound never used it. The exclusion and its computed effect (2.04 times at 49, 2.17 times at 46) are recorded in CLM-01-010. The ID is not reused.
- **CLM-01-010, reworded.** The callout now names the sponsor and says the means are survey responses. The evidence class stays `measured`/`transcribed` because the schema has no self-report origin (open, see final/edits-ch01.md).
- **CLM-01-013, narrowed.** The Pinckney citation moved to CLM-01-023, which carries its result.
- **CLM-01-017, split.** Attribution to OpenAI is restored; the physical-design claim and the schedule are CLM-01-021 and CLM-01-022. The new sentences report the favorable vendor results together with their limits.
- **CLM-01-020, corrected.** The range is 0.051 to 0.402. The earlier 0.058 minimum misread Table IX; the "30 placements" detail was dropped because the reread did not confirm it.
- **New claims.** CLM-01-021 to CLM-01-024.
