# Learn from the design's measured consequences

The previous exercise connects a model's action to RTL and GDS. This exercise
connects the returned measurements to a parameter update, then tests the next
model-selected implementation through the same tools. The learning loop is
complete only when the updated checkpoint actually chooses an action and the
harness evaluates its artifact.

The first measured example exposes a useful difficulty. Streaming packed
weights increased cell area while improving setup slack. Both implementations
still failed electrical and antenna checks. Those observations do not define
one universally correct action. An architect must state the objective before
turning measurements into training labels.

## Build the feedback example

The supplied objective chooses the smaller measured area for the next
experiment, provided both alternatives pass numerical and differential RTL
checks, routed timing, DRC, and LVS, and have the same remaining failed
physical-check families. It is a preference for further exploration.
Acceptance still requires every declared check. In particular, an area
advantage cannot erase an antenna violation.

Read [`derive_preference`](../design_feedback_data.py). This small function
is the student's curation component: identify comparable measurements,
distinguish missing evidence from a failed check, and derive an action from
the declared objective. Its surrounding collector verifies source and receipt
identities, compares raw logs with parsed results, and retains unsuccessful
checks. A tie or incomparable pair produces no invented preference.

The collector produces one development example from two measured designs.
It does not turn hundreds of tool files, clock cycles, or repeated training
rows into hundreds of independent examples. Its label is objective-dependent,
and its workload becomes training data once the example is admitted.

Run from the repository root with the retained baseline and first candidate:

```bash
python3 -m nanochip.laboratory feedback-collect \
  --baseline-run output/nanochip/design-baseline-20261017-1 \
  --prior-run output/nanochip/design-change-20261017-1 \
  --output output/nanochip/feedback-evidence-001
```

This reads the original physical results and runs a bounded reference
differential check. It does not run physical implementation. Inspect the
new `manifest.json`, `evidence.json`, copied raw files, both failed-check
profiles, and the derived `selected_action`. Original bundles remain intact.
The loader rejects stale hashes, mismatched settings, changed labels,
incomplete checks, and nonfinite metrics.

## Build and compare the update

[`adapt_from_feedback`](../design_feedback_learning.py) reloads the original
checkpoint and updates real parameters through the existing trainer. Its
training view contains the original 56 replay rows and eight explicitly
identified replicas of the single development example. Replay preserves
exposure to the original task distribution; it can also compete with the new
feedback. Replica count is a training weight, not evidence quantity.

The supplied comparison has three model conditions and one conventional
alternative:

| Condition | Parameter updates | New example's label |
| --- | --- | --- |
| Frozen model | None | None |
| Matched-update control | 120 steps from the original checkpoint | Original constructed heuristic |
| Feedback adaptation | Same 120 steps from the same checkpoint | Preference derived from measured area |
| Conventional selector | No model | Apply the declared preference directly |

The two updates use the same represented inputs, row order, random seed,
batch schedule, optimizer, learning rate, and checkpoint selection rule.
Their new example differs in label and disclosed provenance. Both updates
finish before either physical campaign begins. The experiment keeps the
final checkpoint at the fixed budget; it never trains until a desired action
appears.

```bash
python3 -m nanochip.laboratory feedback \
  --checkpoint output/nanochip/design-learning-20261017-v1/model/checkpoint \
  --corpus output/nanochip/design-learning-20261017-v1/corpus/manifest.json \
  --feedback output/nanochip/feedback-evidence-001/manifest.json \
  --output output/nanochip/feedback-loop-001
```

Use a new output directory. CPU PyTorch, Verilator, and the cached physical
environment from the [physical guide](../physical/README.md) are required.
The command launches two isolated physical campaigns concurrently, each
limited to one CPU and one selected candidate. Each has a 900-second physical
budget. Failed attempts count. Concurrent elapsed times cannot support a
runtime-speedup claim. A nonzero final command status preserves unresolved
acceptance even when the experiment itself executed successfully.

## Inspect the causal chain

Start with the frozen study protocol. Confirm that the two update records
have the same inputs and that only the new label source changes. Check the
base, initial, and final parameter hashes. Then inspect each campaign's
`proposal.json`, complete RTL diff, source hashes, functional results, and
physical receipts. Both architectural actions remain available at decoding.
The runner does not force a change or replace a repeated choice.

The original development and test partitions are evaluated only after both
updates. They provide a regression diagnostic for the old constructed task;
they do not establish physical generalization. A fresh physical run on the
adaptation workload is still a run on the training case.

The final `feedback-study.json` distinguishes probability changes, selected
actions, identical RTL, area differences, and complete acceptance. If the
models choose identical source, physical variation cannot count as a learned
design improvement. If the feedback model chooses a smaller implementation
that still fails required checks, report the area preference and the failed
acceptance separately. Matching the conventional selector establishes no
advantage over that selector.

## Decide what the extension contributed

The [first feedback study](../FEEDBACK_EXPERIMENT.md) preserves a negative
result: the update changes probabilities but both trained models select the
streaming implementation. No candidate is substituted to make the lesson
appear successful.

A student extension should state what it changes before evaluation. A new
feedback representation, replay balance, update method, or dataset is a new
experimental condition. Keep the earlier unsuccessful condition and charge
its cost. If a revision is developed using this case, assess transfer on new
workloads and design conditions whose results were not used to choose it.

The student deliverable is a reproducible claim about the contribution of
the update: which feedback entered training, what changed in the model,
which implementation it selected, and whether the tools established a useful
result. A closed learning loop can fail to improve a design. Recognizing that
outcome is part of learning to build an AI-native design system.
