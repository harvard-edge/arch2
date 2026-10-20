# First cumulative exercise: use evidence to choose the next action

Implement [`StudentProposer.propose`](../student.py), then execute it through
the same harness used by the reference policy and learned proposer. This is
the first thin exercise entry. The next
[RTL design exercise](RTL_DESIGN.md) adds a student transformation that a
trained model can select and the shared harness can carry into the GDS flow.
The [feedback learning exercise](FEEDBACK_LOOP.md) uses its tool results for
parameter updates and a controlled comparison. This directory does not
contain nine completed labs.

The policy starts with an intentionally incorrect dequantization block. A
completed numerical check can justify selecting the reference block. A tool
error requires a different response from a numerical mismatch. Once the block
passes, the policy stops; the harness still reports complete-workload and
physical obligations as unresolved. This exercises feedback and artifact
linkage, without claiming architectural optimization or model learning.

## Inputs, hook, and checks

Read [`interfaces.py`](../interfaces.py), [`contracts.py`](../contracts.py),
and [`runner.py`](../runner.py). The editable hook is already present in
`student.py`; it raises `NotImplementedError` until completed. Use the task,
observation history, and remaining budget supplied through the `Proposer`
interface. The runner owns candidate identity and eligibility.

Run from the repository root:

```bash
python3 -S -m nanochip.laboratory.exercises check --implementation student
```

Before implementation this command exits with status 2 and an `INCOMPLETE`
message. It never substitutes the reference policy. After implementation it
checks seven explicitly constructed policy inputs, including absent evidence,
an execution error, and a check with the right name at the wrong scope. These
inputs are behavior tests, not simulator results or training examples.

The supplied recovery checkpoint can be inspected and checked explicitly:

```bash
python3 -S -m nanochip.laboratory.exercises check --implementation reference
```

[`ReferenceProposer`](../adapters.py) is a conventional policy. Passing its
behavior checks establishes neither hardware correctness nor model quality.

## Execute the student component

Check prerequisites with `python3 -m nanochip.laboratory doctor`. A live run
requires Verilator, Make, and a C++ compiler. Choose a new output directory:

```bash
python3 -m nanochip.laboratory.exercises run --implementation student \
  --output output/nanochip/exercise-feedback-001
```

The exercise first checks the selected implementation, then delegates to the
existing laboratory `run` command. It uses `DequantMaterializer`,
`VerilatorBackend`, `run_campaign`, and the ordinary recorder. The selected
policy is identified in `campaign.json`; raw build and simulation logs remain
beside exact candidate snapshots. No alternate toolchain is created here.
To run the recovery checkpoint, explicitly choose `--implementation reference`
and another output directory.

Inspect `events.jsonl` and both attempt directories. Establish which source
changed, which returned check triggered the next action, and why the passing
reference block remains ineligible as a complete accelerator. Then run
`python3 -m nanochip.laboratory dataset-check output/nanochip/exercise-feedback-001/dataset.json`.
[`data.py`](../data.py) checks provenance and split declarations; that manifest
is a collection example, not an independently evaluated training corpus.

## How this component survives the nine labs

| Lab | Connection to this first exercise |
| --- | --- |
| 1. Data | Identify workload inputs, receipt provenance, and related experiment groups. |
| 2. Representations | Interpret the numerical checker and later extend packing or oracle logic. |
| 3. Harness | Implement this feedback policy and follow its action to the exact executed artifact. |
| 4. Training | Build a model from designated training records with real parameter updates. |
| 5. Adaptation and inference | Replace the policy through the same `Proposer` interface; execute its actual legal action. |
| 6. Prediction and search | Compare alternative policies under a common action space and budgets. |
| 7. Architecture | Add a consequential legal transformation and matching regression checks. |
| 8. Physical implementation | Evaluate that candidate with realized memories and named physical checks. |
| 9. Evaluation | Compare checked outcomes and total cost on independent campaigns. |

The existing [`context.py`](../context.py) supplies optional identified
retrieval sources. Its output may inform a proposer, while the harness retains
authority over allowed actions and checks. The existing diagnostic model emits
inspection requests; those actions are distinct from this exercise's
reference/fault selection. The [design exercise](RTL_DESIGN.md) supplies a
separate, explicit design-action decoder and transformation boundary.

The feedback and RTL design exercises have executable entries here. The
[implementation blueprint](../ARCHITECTURE.md) distinguishes current modules
from the complete-core and course milestones still required.
