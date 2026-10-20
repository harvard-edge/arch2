# Build the Nanochip laboratory

Nanochip is a modular ecosystem laboratory for learning AI-native system and
chip design. Students build the system across cumulative exercises, learn
which components exist, and identify, replace, and evaluate those components.
The destination is a complete Kimi-derived accelerator experiment,
from a workload contract through checked GDSII.

The system connects training and inference. Development experiments
produce data; a student trains or adapts a small model on designated records;
that checkpoint proposes actions; real tools evaluate the resulting artifacts;
returned evidence determines the next action. Later development records can
support another adaptation cycle. Independent evaluation tests whether the
change improved the architecture result, the cost of reaching it, or both.

## Complete-workload learning path

The current system trains a small byte language model, executes its proposed
multiplier implementations on the complete teaching workload, updates the
same model from measured development feedback, and compares frozen methods
on held-out workloads:

```bash
python3 -m nanochip.laboratory system --functional-only \
  --output output/nanochip/complete-functional-001
```

The first complete functional campaign passed its workload checks. Adapted
inference, unchanged inference, enumeration, and a fixed-action policy tied
on the best observed result. Learning did not improve design selection in
that experiment. Complete-core physical closure and final course/container
validation remain in progress.

The [system guide](../docs/SYSTEM_GUIDE.md) explains the component diagram,
the distinction between the design helper and the workload running on the
chip, the cumulative student contributions, and the comparison protocol.
`nanochip core`, `nanochip language`, and `nanochip course` expose the same
components separately. Earlier block experiments below remain useful scoped
examples and retain their original evidence boundaries.

## Earlier block alpha

The local alpha has a single cumulative demonstration:

```bash
python3 -m nanochip.laboratory demo --output output/nanochip/demo-001
```

It collects fresh constructed fault records, trains and adapts a diagnostic
decoder, executes its requested inspection, trains a design-action decoder,
and checks the exact RTL selected by that model. PyTorch, Verilator, Make,
and a C++ compiler must already be available. The command writes `report.md`
and `report.json`, with links to the data, checkpoints, proposals, source
changes, and checks. Add `--physical` to execute the cached block physical
flow. The [walkthrough](../docs/DEMO_WALKTHROUGH.md) and
[first system exercise](exercises/FIRST_SYSTEM.md) connect the run to a
student-owned transformation.

The starter establishes a dependency-light Python core for task contracts,
candidate identity, tool observations, and feedback-driven execution. Its first
hardware probe freshly compiles and simulates a dequantization RTL block. It
compares the reference block with an intentionally constructed incorrect-shift
variant. A conventional controller uses the returned evidence to choose its
next action.

This is a block-level integration exercise. It establishes that an action
selects a particular artifact, a checker evaluates that artifact, and the
observation affects execution. Inspect the raw tool output alongside the
structured result. A failed tool invocation, a numerical mismatch, and a
passing check must remain distinguishable.

The laboratory also collects 15 constructed RTL cases into a validated corpus,
trains a small recurrent action decoder, adapts its saved weights on designated
development records, and evaluates held-out diagnostic actions. Checkpoint
inference executes the selected inspection through the same harness.
An optional keyword retriever supplies bounded, attributed specification text.
The physical adapter implements this block with a pinned SKY130 toolchain.

The next component connects a learned design action to an actual RTL change.
A second action decoder chooses between indexed packed-weight reads and a
sequential shifting implementation. The shared harness runs the selected
source through numerical checks, differential simulation, and the GDS flow.
Students implement the transformation in the
[RTL design exercise](exercises/RTL_DESIGN.md). The
[design experiment record](DESIGN_EXPERIMENT.md) reports the model's weak
held-out behavior and the physical outcome without attributing design skill
to one selection.

The [feedback exercise](exercises/FEEDBACK_LOOP.md) then curates the measured
outcomes into a training example, updates the saved model, and executes its
next choice. An equally trained control isolates the new label's contribution
from additional training. The first update changes probabilities but leaves
the selected RTL unchanged. The [feedback experiment record](FEEDBACK_EXPERIMENT.md)
retains that result and its fresh tool evidence.

These block components preceded the current byte-language model and complete
serialized teaching core. The first block physical execution produced GDSII
but failed antenna and electrical checks.
See the [implementation blueprint](ARCHITECTURE.md) for module ownership and
the [measured results](MEASUREMENTS.md) for the evidence and limitations.

## Run the starter

Run these commands from the repository root with Python 3.10 or newer.
The core uses the standard library. The RTL probe also requires Verilator,
a C++ compiler, and Make; it installs nothing.

```bash
python3 -m nanochip.laboratory doctor
python3 -m nanochip.laboratory labs
python3 -m nanochip.laboratory probe --output /tmp/nanochip-probe-first
python3 -m nanochip.laboratory run --output /tmp/nanochip-run-first
python3 -m nanochip.laboratory dataset-check /tmp/nanochip-run-first/dataset.json
```

`doctor` reports execution prerequisites. `labs` lists the cumulative learning
path. `probe` runs the block checker; `run` connects candidate execution to
feedback and a subsequent action. Use a new output directory for each
experiment and retain its artifacts and receipts together. Python contracts
can remain lightweight even when a hardware adapter requires an installed
compiler and simulator. Consult `doctor` before interpreting an unavailable
tool as a design failure.

The [first cumulative exercise](exercises/README.md) guides the first
student-editable component,
[`student.py`](student.py). Implement `StudentProposer.propose`, then use
`run --policy student --output /tmp/nanochip-student-first`. The supplied
[`ReferenceProposer`](adapters.py) is a recovery checkpoint. Both implementations
use the same artifact materializer, simulator, checks, and records. There is
no silent fallback when the student implementation is incomplete.

The generated directory contains `campaign.json`, `events.jsonl`, environment
information, candidate source snapshots, raw build and simulation logs, test
vectors, and a dataset manifest. That manifest demonstrates collection and
split validation; it has one training group and no action labels or independent
evaluation set. It is not the labeled corpus used by the learning commands.
The laboratory runs from this checkout or a locally built Python wheel with
the `nanochip` console command. The local package retains the required RTL,
testbenches, and configuration. The [container guide](../containers/README.md)
records the prepared learning image and its validation boundary; physical
execution uses a separate pinned external container.
The complete course and public distribution remain development work.

## Connect data, learning, inference, and physical tools

The learning path requires an installed CPU-capable PyTorch and NumPy. Collection uses
the same Verilator prerequisites as the starter. These commands execute fresh
experiments, so choose new output paths:

```bash
python3 -m nanochip.laboratory collect --output output/nanochip/corpus-001
python3 -m nanochip.laboratory learn \
  --corpus output/nanochip/corpus-001/manifest.json \
  --output output/nanochip/learning-001
python3 -m nanochip.laboratory diagnose \
  --corpus output/nanochip/corpus-001/manifest.json --record dequant-011 \
  --checkpoint output/nanochip/learning-001/adapted \
  --output output/nanochip/diagnosis-001
```

`collect` preserves source snapshots, build and simulation logs, numerical
vectors, tool receipts, costs, and explicit constructed-fault provenance.
`learn` writes its protocol before training, saves an initial and an adapted
checkpoint, then compares both on the final partition. Adaptation uses an
explicit training view of development records. The final partition supplies
neither parameter updates nor retrieval documents.

`diagnose` loads the requested checkpoint and executes its decoded inspection.
Its record distinguishes a fresh inspection from the retained RTL execution
being inspected. Omitting `--checkpoint` explicitly selects the disclosed
teaching rule. Add `--context keyword` to both `learn` and `diagnose` to use
the supplied retrieval component consistently. New checkpoints bind their
representation and context mode into the saved model contract. Inference
rejects a different declaration before calling the model. Earlier checkpoints
remain explicitly unbound; adding retrieval only at inference changes their
input distribution and may help or hurt.

The physical command requires a running Docker engine and the cached image
and PDK described in the [physical guide](physical/README.md). It never
downloads them:

```bash
python3 -m nanochip.laboratory physical \
  --rtl output/nanochip/corpus-001/dequant-000/probe/candidate.v \
  --output output/nanochip/physical-001 --timeout 900
```

This feeds the exact reference snapshot from collection into implementation.
The source hash links functional and physical evidence; equivalence through
implementation is a separate check still to add. The diagnostic model has
not chosen or improved this reference. To execute a design decision instead,
use the separate `design-train` and `design` commands in the
[RTL design exercise](exercises/RTL_DESIGN.md). They use the same model and
harness interfaces, with an explicit architectural action space.

## Initial measured scope

On October 17, 2026, one complete starter campaign freshly compiled both
candidates and finished in 6.417 seconds on an ARM64 machine with 64 GiB of
RAM, using Verilator 5.052. Each candidate executed 1,740 scalar numerical
comparisons. The constructed fault produced 1,461 mismatches; the reference
produced none. Other focused tests were compiling concurrently, and this is
one local observation, not a minimum-laptop runtime guarantee.

Separate runs collected the diagnostic corpus in 27.965 seconds of probe time
and completed training, adaptation, and evaluation in 12.048 seconds. These
are small local observations on the same machine, not tutorial hardware
guarantees. The [measurement note](MEASUREMENTS.md) explains the weak model
result and the physical checks that failed. Setup, peak memory, broader
workloads, and the complete accelerator still need separate measurements.

## Nine cumulative labs

Each lab contributes an artifact used later. Recovery checkpoints identify
supplied and student-built components. The table describes the intended
curriculum. Executable components cover several stages; student exercises
now cover feedback and an RTL transformation. The nine construction exercises are not
yet a complete course.

| Lab | Student artifact | Integration check |
| --- | --- | --- |
| 1. Workload and data | Workload manifest, provenance labels, dataset index, grouped splits | Changed inputs invalidate affected records; evaluation groups stay outside training. |
| 2. Representations and numerical checks | Packed-weight conversion, numerical checks, structured failures | A deliberate arithmetic error is detected and becomes a usable observation. |
| 3. Experiment harness | Candidate materializer, tool adapter, run receipts | Distinct candidates produce distinct artifacts and fresh results; tool failures cannot become passing measurements. |
| 4. Train a small model | Data loader, training components, checkpoint, evaluation record | Parameters actually change; the checkpoint reloads; held-out behavior and training cost are reported. |
| 5. Adapt and use the model | Adapted checkpoint, action parser, proposer adapter, optional retrieval | A generated legal action reaches the exact evaluated artifact; malformed actions are rejected. |
| 6. Predict and search | Analytical predictor, conventional baseline, budgeted next-action policy | Returned observations change later actions; methods receive the same legal space and budgets. |
| 7. Change the architecture | New implementation transformation, representation changes, regression checks | The extension survives complete-workload checks and is available to every comparison method. |
| 8. Close the physical path | Physical adapter, realized memory interfaces, candidate-linked GDSII and reports | Required physical checks support the selected implementation; physical evidence changes or confirms an upstream decision. |
| 9. Evaluate and improve the system | Curated development data, another adapted checkpoint, independent campaigns, comparison report | A fresh run connects workload through checked implementation; held-out comparisons assess outcomes and total cost. |

The prepared environment supplies engineering tools, platform assets,
reference designs, reference solutions, and recovery checkpoints as they
become available. Students contribute the data processing, checks, adapters,
models, control policies, architecture extensions, and comparisons that make
those tools one experimental system.

## Where learning data comes from

The corpus must grow from real candidate-linked development executions.
Retain source identities, task conditions, actions, raw outputs, checks,
failures, tool versions, and measured costs. Label numerical faults, state or
reset failures, unsupported constructs, stale results, missing evidence,
tool errors, and physical failures. Preserve unsuccessful experiments.

The current [diagnostic corpus](datasets/README.md) has six initial training
records, five development records, and four final-test records. Its labels
come from a disclosed teaching policy, and its independent templates still
share one RTL base and one vector suite. It is enough to exercise collection
and learning interfaces; it cannot establish broad design competence.
Historical narration also requires an evidence audit before it can supply
training examples. Keep constructed faults, replay, source estimates, and
fresh execution explicitly identified.

Split related experiments together before making training examples. Candidate
lineages, workload conditions, and fault families can otherwise leak across
training and evaluation. Paraphrases of one record are not independent
experiments. An observed human action is a recorded choice, not an automatic
label for the best possible action.

## From this foundation to the complete demonstration

The current decoder consumes represented observations and emits a diagnostic
request. Its small first study exposes a representation problem: numerical
and protocol failures receive almost identical model probabilities. Students
can investigate information placement and model capacity using development
data. A new evaluation set must be frozen before assessing a revised method.

The design extension now exposes a packed-row transformation through the same
action interface, with matching functional and physical checks. Its model
selects an authored implementation; both the selection and the complete RTL
diff are retained. The remaining learning question is whether a better
representation, dataset, or model can make useful choices across independent
tasks. Adaptation from physical feedback now has an executable comparison,
with model changes and design outcomes assessed separately. Broader language
training and full-core memory integration remain work in the blueprint.

Action validity and training loss diagnose the model. Checked outcomes,
attempts, failures, and total cost assess its contribution to design. The
complete course must also execute the full physical path with realized
memories and named checks. Laptop resource requirements, training duration,
physical runtime, and useful improvement all require measurement.
