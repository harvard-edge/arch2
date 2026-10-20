# Build the link from a model decision to a changed design

This exercise adds an architectural transformation to the same Nanochip
laboratory. A saved model chooses an action, the materializer writes its RTL,
and the existing harness carries that exact source through numerical checks,
differential simulation, and physical implementation. The student builds the
transformation. The harness supplies the execution boundary and records.

## The design question

The Kimi-derived dequantizer stores a packed row of 4-bit weights in a
1,024-bit register. Its reference implementation uses a variable index to
select each weight. A complete row is consumed in ascending order, once.
That access pattern permits another implementation: read the lowest four
bits and shift the register right by four bits after each output cycle.

The change removes the variable read selector but adds shifting behavior to
the register. Whether it helps area or timing depends on synthesis and
routing. A legal transformation and an attractive physical implementation are
separate questions. The model's preference answers neither by itself.

Implement [`student_design.transform`](student_design.py). Its input is the
reference RTL and one of two action names. For `retain_indexed_read`, return
the source unchanged. For `stream_quantized_row`, return the complete modified
RTL. The hook raises `NotImplementedError` until completed; the runner does
not substitute an answer.

The first exercise admits this specific structural rewrite. Its conformance
check ignores comments and formatting, accepts the shift as concatenation or
`qrow_v >> 4`, and permits the old read declarations to remain unused. Other
active RTL edits require a new action and corresponding checks. Both action
branches are checked before simulation; comment-only changes do not count.

Keep input staging, arithmetic, output packing, addresses, and handshakes
unchanged. Shift only during the output state, using a nonblocking assignment.
The relevant invariant is that the next unread nibble occupies the lowest
four bits before each output cycle. A new row reloads its active packed bits.
Stale bits outside a shorter row need not agree with the reference.

The supplied recovery checkpoint is
[`apply_design_change`](../design_changes.py). It makes this transformation
explicitly and records a complete diff. This is an authored action library;
the small model selects an implementation rather than generating arbitrary
Verilog.

## Check the student component

Run from the repository root with Verilator, Make, and a C++ compiler installed:

```bash
python3 -m nanochip.laboratory.exercises design-check \
  --implementation student --output output/nanochip/student-design-001
```

Choose a new output directory for each execution. To examine the supplied
checkpoint, select `--implementation reference` explicitly and use another
output directory.

The numerical checker compares 1,740 scalar results across 15 rows with an
independent integer oracle. The differential checker then drives the original
and modified RTL together. It covers valid row lengths, one and two groups,
stream stalls, consecutive jobs, and reset during intake and output. Controls
must agree each cycle; output data must agree when the write signal is valid.
The deterministic suite completes 409 jobs and injects 15 resets. A wrong
eight-bit shift is a negative control in the regression tests.

These are bounded functional checks. A separate Yosys test proves a local
combinational extraction identity, but neither result establishes exhaustive
sequential equivalence or correspondence to the synthesized netlist.

## Train and connect the proposer

The design helper consumes a compact representation of row size, quantization,
load behavior, access order, index step, reuse, and number of passes. Its
constructed training examples teach when a destructive sequential read is
appropriate. Their labels express a disclosed engineering rule; they are not
measured labels for optimal area, timing, or energy. Training requires CPU
PyTorch and does not download a model.

```bash
python3 -m nanochip.laboratory design-train \
  --output output/nanochip/design-learning-001
python3 -m nanochip.laboratory design \
  --checkpoint output/nanochip/design-learning-001/model/checkpoint \
  --transformer student --output output/nanochip/student-physical-001
```

The physical step requires the cached container and PDK in the
[physical guide](../physical/README.md). Both actions remain available during
inference. A model that chooses to retain the original produces an unchanged
candidate, and the report says so. A transformation is never forced after
decoding. The supplied implementation can be selected explicitly with
`--transformer supplied`.

The first model performs poorly on held-out constructed examples. Its ability
to emit a legal action demonstrates the connection between learning and
execution; it does not establish reliable architectural judgment. Inspect its
accuracy and per-action recall before interpreting one successful selection.
See the [experiment record](../DESIGN_EXPERIMENT.md) for the measured result.

## Follow the evidence to GDS

Read `proposal.json`, `task.json`, the candidate's `change.diff`, and
`attempts/attempt-0001/execution-link.json`. Establish that the decoded action
produced the candidate, and that numerical simulation, differential simulation,
and physical implementation consumed the same source hash. Raw logs and
receipts remain alongside each stage. Missing tools and execution failures
must remain distinguishable from completed checks that reject a design.

The physical flow reports GDS generation, route and layout checks, LVS,
routed timing, electrical constraints, and antenna checks separately. A GDS
file can exist while required checks fail. The report also leaves full-core
workload closure and RTL-to-netlist correspondence unresolved.

Compare the changed block with a fresh reference execution under the same
constraints, platform, and tool versions. Report area and timing together
with every failed or missing check. Do not infer energy savings from area or
use concurrent runs as a controlled runtime comparison. A useful extension
must improve a defined outcome without losing the required checks.

This component contributes to labs 7 and 8. Data, training, inference,
materialization, checking, and physical tools remain parts of one project.
The next [feedback exercise](FEEDBACK_LOOP.md) curates these development
results, adapts the proposer, and executes a comparison against an equally
trained control. The first design experiment retains its original one-proposal
scope. Full-accelerator closure and physical transfer to unseen tasks remain
later work.
