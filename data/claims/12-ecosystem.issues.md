# Chapter 12 ledger issues

Open limits on chapter claims, refreshed 2026-11-02 after the final audit fixes. Resolved items were removed.

## Citation supports the sentence only in part

- **Footnote fn-tinytapeout-architecture-c12, TinyTapeoutGPIOSpecs.** The cited page supports the pad ratings. The multiplexer sentence rests on the retained multiplexer explainer, linked inline.
- **CLM-12-046, open question on mature-node tiles.** The pad rating is sourced for SKY130 only. The judgment that such tiles cannot validate a 3 nm-class node is recorded as assumed.
- **CLM-12-051, TTIHP25a post.** Read and hashed, linked inline, not in the bibliography. The post shows that chips exist, not that they reached users.

## Sources stronger than the prose

- None open.

## Weak or limited evidence

- **CLM-12-009, CLM-12-031, CLM-12-036.** No capture of the August 2026 catalog exists. The retained source is the July 2026 commit. CLM-12-036 was also read on the live page on 2026-11-02.
- **CLM-12-047.** The caption's "Counts measure participation" is loose, because 78.4 percent of TTIHP25a API names appeared on earlier runs. The caption is bound to a PASS audit and stays until a reaudit.
- **CLM-12-023 to CLM-12-030, CLM-12-050.** The first-seen metric and calendar bins were not preregistered. The yearly shape depends on the bins, as the chapter says.
- **CLM-12-011, CLM-12-012.** Numbers in the figure alt text are typed, not computed, so they can drift from the CSV.
- **CLM-12-013.** The mask-cost estimate dates from 2022 and comes from one analyst.
- **CLM-12-007.** ASAP7 was checked against the abstract and the project page only.
- **CLM-12-033.** Whether TT06 is representative is untested. Feedback coverage on other shuttles was not collected.
- **CLM-12-054.** No status for the Cadence TT09 dies was found.

## Unopened sources

- **CLM-12-004, IEEE2011SystemC1666.** The IEEE text returned HTTP 403. The systemc.org overview is the evidence read.

## Retention

- `book/contents/chapters/12-ecosystem/data/tinytapeout-receipts/`, this ledger, and the figure's audit record are untracked in git and must be tracked before the clean rebuild.
- `design_repeats.py` is not a declared audit input, as the audit notes.
