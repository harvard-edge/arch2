# Earlier block demo walkthrough

This guide covers the earlier dequantizer-block `demo` command. For the
complete reduced Kimi-derived workload, small language model, feedback
adaptation, and comparison methods, start with the [system guide](SYSTEM_GUIDE.md)
and its `system` command. The [cumulative course](../laboratory/course/README.md)
builds those components through the nine labs. The block's physical results
do not establish physical closure of the complete teaching core.

This walkthrough follows one run from constructed data through a model-selected
RTL action and fresh checks. It is designed to make the system's parts and
evidence visible, not to claim that the model has learned general architecture
skill.

## Start a run

The default demo collects and trains from the available diagnostic examples,
adapts a checkpoint, runs diagnostic inference, trains a design-action
checkpoint, and executes one action through the shared candidate harness. It
finishes with fresh numerical and differential checks on the selected RTL.
Use an existing Python environment with PyTorch, Verilator, Make, and a C++
compiler. The demo performs no installations or downloads.

From the repository root, choose an output path that does not exist:

```bash
nanochip demo --output output/nanochip/demo-001
```

The equivalent source-checkout command is:

```bash
python -m nanochip.laboratory demo --output output/nanochip/demo-001
```

The command writes a human-readable `report.md` and structured `report.json`
at the output root. Read those first, then follow the linked files below.

## Follow the data into inference

Open `diagnostics/corpus/manifest.json` and `records.jsonl`. The corpus comes
from executed, constructed RTL fault cases. Its labels express the disclosed
diagnostic teaching policy; they are not human expert labels or optimal repair
choices. Each record links to a probe receipt and its candidate artifacts under
`diagnostics/corpus/dequant-*/probe/`.

Read `diagnostics/learning/report.json` and compare the base and adapted
checkpoint evaluations. Then open `diagnostics/inference/diagnosis.json` to
see which diagnostic action inference requested for a retained record. The
model is a small structured action decoder trained on this corpus. It is not a
pretrained language model and does not generate free-form explanations or RTL.

## Follow the design action into RTL

The design corpus and its training report live under `design/corpus/` and
`design/learning/`. The learned proposer selects from the named design actions
described in the [RTL design exercise](../laboratory/exercises/RTL_DESIGN.md).
The materializer uses an authored transformation to produce the complete RTL
source for the selected action. With `--transformer student`, it calls the
student's `student_design.transform` hook instead. The student owns this
action-to-source implementation, not arbitrary Verilog generation.

Inspect `design/execution/proposal.json`, then open
`design/execution/attempts/attempt-0001/candidate/`. The candidate contains
the exact source, reference, and `change.diff`. Follow `execution-link.json`
and the receipts to verify which source the numerical and differential
checkers consumed. A retained reference action produces no design change; the
runner records that outcome without replacing it with the other action.

The differential test compares control signals on every tested cycle and
output data on valid writes. These checks cover a bounded block workload. They
are not exhaustive sequential equivalence proofs and do not establish
RTL-to-netlist correspondence.

## Run the student implementation

The supplied transformation is selected by default. After implementing the
hook in `nanochip/laboratory/exercises/student_design.py`, choose a new output
directory and run:

```bash
nanochip demo --output output/nanochip/demo-student-001 --transformer student
```

If the model chooses the transformation, the runner checks the student's exact
source. If it chooses the reference action, the transformer must return the
reference unchanged. Both branches matter: a component has to implement the
action contract, not only the changed-design case.

For a deliberate failure exercise, make a temporary, plausible mistake in the
rewrite and run the student path again. Record whether the conformance check,
the numerical check, or the differential check stops the candidate. Explain
what that result says about the candidate and what it leaves unknown. Restore
the correct implementation and retain the failing and passing run directories
separately.

## Add the physical block flow

The optional mode sends the same selected source through the existing pinned
block flow:

```bash
nanochip demo --output output/nanochip/demo-physical-001 --physical
```

This requires Docker, the cached physical container, and the PDK documented in
the [physical guide](../laboratory/physical/README.md). The command does not
download them. Inspect each named physical check and its raw report. GDS
generation can succeed while another required check fails. Physical evidence
applies to this dequantizer block; the demo does not close the complete Kimi
nano-KPU workload through checked GDS.

## Explain the run

Use the retained artifacts to answer:

- What source and fault family produced the training records?
- Which records were used for training, adaptation, and evaluation, and what
  limits do their construction and shared RTL base impose?
- Which action did inference choose, and how does the record connect it to the
  exact candidate source?
- Which checks ran on that source? Which checks failed, were unavailable, or
  remain unresolved?
- What can this run support about the block, the action decoder, and the
  complete accelerator? What evidence would be needed to support a broader
  claim?

Treat candidate identity, tool returns, check scope, and failures as part of
the result. A training report alone does not show that a design decision was
correct, and a GDS file alone does not show that required physical checks pass.
