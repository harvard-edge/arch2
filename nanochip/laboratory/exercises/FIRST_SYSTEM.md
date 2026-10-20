# Build your first connected Nanochip system

Nanochip teaches students to build an AI-native computer-design system one
working component at a time. This first demonstration connects workload data,
representations, training, inference, an RTL design action, a shared harness,
and fresh checks. The artifacts remain inspectable after the command finishes.

The demonstration is a bounded block exercise inside the Kimi-derived
nano-KPU project. It does not complete the nine-lab course or close a full
accelerator workload through physical implementation. Read the [demo
walkthrough](../../docs/DEMO_WALKTHROUGH.md) while following the run.

## What the demonstration builds

The default run collects diagnostic records from constructed dequantizer
faults, trains and adapts a small action decoder, and runs that checkpoint
through inference. It then builds a separate design-action corpus, trains a
second small decoder, and uses that checkpoint to choose one of two named
RTL actions. A materializer turns the action into an exact candidate source;
fresh numerical and differential checks evaluate that source.

This is a real training and execution path, but its scope is narrow. The
diagnostic labels come from a disclosed teaching policy. The design examples
teach a stated engineering rule, not a measured optimum. The model selects
from a finite action list. It is not a general language model, and it does not
write arbitrary Verilog. The student's transformer implements the meaning of
the action `stream_quantized_row`; the harness controls which action may run
and records the source and check results.

## Run the supplied demonstration

Use an existing Python environment with PyTorch, NumPy, Verilator, Make, and a C++
compiler. The demo does not install tools or download models. The physical
option also needs the cached container and PDK described in the [physical
guide](../physical/README.md).
The [prepared learning container](../../containers/README.md) supplies the
functional toolchain and learning dependencies. Its editable student sources
must be rebuilt into the image after a change; a host editable installation
can be more convenient while developing the exercise.

From the repository root, choose a new output directory:

```bash
nanochip demo --output output/nanochip/demo-001
```

If the `nanochip` launcher is not installed, use the module entry point:

```bash
python -m nanochip.laboratory demo --output output/nanochip/demo-001
```

The demo creates `report.md` and `report.json` at the output root. The report
links to the diagnostic corpus, training reports and checkpoints, inference
result, design corpus, design checkpoint, proposal, exact candidate, and
execution record. Give the output directory a new name for each run; the
command retains the run's inputs and results together.

## Make the RTL transformation your component

The supplied run uses the recovery transformation. To make the design
transformation student-owned, implement
[`transform`](student_design.py) in this directory and select it explicitly:

```bash
nanochip demo --output output/nanochip/demo-student-001 --transformer student
```

The input is the reviewed reference RTL and one action name. Return unchanged
source for `retain_indexed_read`; for `stream_quantized_row`, make the
constrained packed-row rewrite described in the [RTL design exercise](RTL_DESIGN.md).
Keep the input staging, arithmetic, output packing, addresses, and handshakes
intact. The conformance check rejects active RTL edits outside this exercise's
two-action contract. The numerical and differential checks then evaluate the
admitted candidate. A successful block check supports only the tested block
behavior; it does not establish complete-core correctness or physical closure.

The model may choose to retain the reference. The runner does not force the
transformation, and a passing action does not establish that it improves area,
timing, or energy. The model's action is one part of the system. The exact
source, tool results, and checks determine what the run supports.

## Exercise: create and explain a failure

In a temporary copy of your transformer, introduce a plausible error in the
packed-row rewrite while keeping the two action names unchanged. Run the demo
with `--transformer student` into a fresh output directory. Inspect where the
run stops and identify whether the evidence comes from transformation
conformance, numerical checking, or differential simulation. Explain what
that check observes and what it cannot establish. Restore the implementation
before producing your final run.

Then answer these questions from your own output:

1. Which corpus record supplied the inference input, and what is its
provenance?
2. Which action did the saved model select? Where is that action linked to the
candidate source and its hash?
3. Which fresh checks consumed that candidate, and what did each check test?
4. Did the action change the source? What result would the run report if the
model retained the indexed implementation?
5. Which full-workload and physical obligations remain unresolved?

Use the report and retained artifacts as evidence. A generated RTL file,
training loss, or successful command exit does not by itself answer these
questions.
