# Editorial placement: regression groups behind an aggregate

Status: companion only, proposed October 17, 2026. No manuscript edit.
See the [selection proposal](../../../integration/manage-work-tree/PLOT_INTEGRATION_PROPOSAL.md).

The natural book location would be “Dynamic Coverage and Mutation Testing” in
[Chapter 7](../../../book/contents/chapters/07-feedback/07-feedback.qmd),
after its opening paragraph. The chapter already has a more relevant figure
on defect-finding methods and surviving mutants. It demonstrates check scope
and the need to test the checker. This chart would repeat the warning about
aggregate scores while adding another verification case.

Keep it for a companion exercise on denominators and failure classification.
One retained Ibex OpenTitan report records 1,464 passing results out of 1,530,
or 95.7 percent. The `debug_triggers` group is 0/5 and `illegal_instr` is 1/15.
The 56 groups have different denominators; the overall fraction cannot
describe every group. Nonpassing results include timeouts and simulator
diagnostics. They are not counts of distinct RTL defects.

The report snapshot is dated October 16, 2026 at 04:16 UTC, with generator
commit `96a34a5617b2904f4172a350199217d82359c13b`. The upstream `latest` URL
is mutable. The retained HTML and JSON agree, but they come from one pipeline
and are not independent validation. The denominator covers recorded results,
not every job that may have been initiated.

Use [README.md](README.md), [source_manifest.json](source_manifest.json), and
[derived/test_summary.csv](derived/test_summary.csv). Cite the exact snapshot
if it is ever used in prose; the generic Ibex citation alone does not identify
this run. The asset is [figure.svg](figure.svg), with PDF/PNG twins. Reproduce
with `python3 data/studies/16-regression-records/reproduce.py`. Do not add this
figure and Study 22's triage table to the chapter together.
