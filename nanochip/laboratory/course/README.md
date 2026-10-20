# Build the Nanochip system

The course builds one experimental system. Each lab adds a component that
later labs use: data handling, numerical representations, a harness, a small
model, inference and retrieval, prediction and search, an RTL transformation,
physical checks, and evaluation. The final question is whether the assembled
system finds a better checked design or reaches one at lower total cost.

The model trained here proposes design actions. The chip executes a separate
small Kimi-derived numerical workload. Keeping these roles distinct prevents
an improvement in language-model loss from being mistaken for an improvement
in hardware.

## Start a workspace

The tools must already be installed, either locally or in the prepared
Nanochip container. The Python commands install no compiler, PDK, or model.
Use the installed `nanochip` command; from a source checkout,
`python3 -m nanochip.laboratory` is the equivalent prefix.

```bash
nanochip doctor
nanochip course init my-nanochip --mode student
nanochip course status --workspace my-nanochip
```

Edit the files in `my-nanochip/labs/`. Each begins with explicit unimplemented
functions. After implementing a lab, execute it and inspect its retained
results:

```bash
nanochip course run --workspace my-nanochip --lab 1
```

The workspace retains every attempt under `runs/labNN/attempt-NNN/`.
Each attempt begins with `start.json`, which identifies the loaded
implementation and its upstream inputs. `progress.jsonl` records the checks
and output hashes. A later edit makes dependent completion records stale.
Failed attempts remain available for diagnosis. The checker never silently
substitutes an instructor implementation.

After interrupting a running lab with Ctrl-C, inspect its `interruption.json`
and incomplete progress entry. Rerun that lab's command when ready; it starts
a new attempt and preserves earlier output. Completed upstream labs remain
usable when their sources and artifacts still match. Recovery restarts the
interrupted lab from its beginning. It does not resume an optimizer midway
through training. A forced process kill can leave only the start record and
partial files, because a killed process cannot finish an interruption receipt.

An instructor can inspect the supplied path in a separate workspace:

```bash
nanochip course init instructor-nanochip --mode instructor
nanochip course run-all --workspace instructor-nanochip --through 7
```

The foundation commands prepare attributed documentation, a real packed-weight
fixture, and a baseline candidate automatically. Physical Lab 8 requires the
prepared physical runtime. `--physical-timeout-s` defaults to 14400 seconds for
complete-core physical implementation; `--correspondence-timeout-s` separately
defaults to 3600 seconds for the mapped-netlist workload check. These are
declared wall-clock budgets, not runtime guarantees. The historical completed
stage assembly totals 9136.582 seconds across checkpoint continuations. That
assembly does not measure a fresh run; each run's receipt establishes
its elapsed time and acceptance. The host container launcher defaults
to 21600 seconds, allowing 14400 for one selected physical candidate, 3600 for
mapped correspondence, and 3600 for course, learning, and collection work.
Lab 9's additional mapped check shares that extra allowance with other course
work; the outer limit does not reserve every nested maximum in sequence.
Every-candidate physical studies may require an explicit larger outer budget.
`--cores` sets the tool budget, and `--physical-mode native` runs inside the
prepared full container.
A short tutorial can inspect explicitly retained physical evidence while
running fresh training and functional iterations. The full course executes
the physical path and accounts for its longer cost.

A checked final capstone also requires accepted physical evidence for its
selected hardware. Treat an incomplete or pending physical result as unfinished
work, even when earlier functional labs pass.

## Lab 1: decide what the data represents

Implement `split_records(records, seed=..., fractions=...)` in
`labs/lab01_data.py`. Return copies in the original order, changing only the
`split` field. Keep related `group_id` values together and preserve frozen
development and test assignments. Source receipts, attribution, and record
identities must survive the split.

Inspect `data/records.jsonl`, `data/split-manifest.json`, and
`data/characterization.json` in the attempt. Follow one record back to its
retained source. Compare source-group counts with record counts; many chunks
from one document do not create many independent design problems. Try placing
one source group in two partitions and confirm that the checker rejects it.

Explain what the corpus can support before training. Documentation supports
text prediction. A tool trajectory can support a measured feasibility or
preference label only when its checks and objective justify that label.

## Lab 2: preserve numerical meaning across representations

Implement `pack_int4(values)` and `unpack_int4(packed)` in
`labs/lab02_representation.py`. Packed fields use unsigned nibble values in
the range 0 through 15, with the low nibble first. Scale and zero-point
interpretation belongs to the workload's quantization contract.

The lab extracts actual embedding bytes from a generated workload image.
Inspect `representation/int4-vectors.json` and trace the source-image hash.
Check an independent packing expression, rather than relying only on a
round trip: two functions can make the same ordering mistake and still undo
each other. Swapping the high and low nibble should fail the oracle check.

The capstone applies the codec to the packed tensors in each new candidate's
runtime image. The candidate's own weight seed remains authoritative.

## Lab 3: make tool results usable and accountable

Implement `adapt_receipt(raw, task, candidate)` and
`summarize_cost(receipts)` in `labs/lab03_harness.py`. The adapter returns a
typed `RunReceipt` only when task and candidate identities agree. Preserve
each check's name, status, and scope, each metric's units, and the execution
status. The cost summary aggregates recorded work while retaining evidence
modes and failures.

Inspect `harness/receipt-contract-check.json`. A tool that exits successfully
can still report a failed design check. A missing required check cannot become
a pass. Change a receipt's candidate hash and confirm rejection; remove a
required check and confirm that the candidate becomes ineligible. Later labs
use this adapter on actual backend output.

Run the connected failure exercise to see why these distinctions matter:

```bash
nanochip core-feedback --output my-feedback-exercise
```

The exercise flips each output logit's low bit in a private RTL copy. The complete
workload still finishes, but its exact numerical check fails. An authored
controller chooses a repair only after receiving that failure; a control run
with the feedback hidden stops without repairing it. Inspect the source diff
and both event streams. This demonstrates a decision during execution.
Parameter updates from measured development records occur separately in Lab 9.

## Lab 4: train and reload a small model

Implement `build_model(config)` and `train(...)` in `labs/lab04_train.py`.
The supplied byte-language trainer is a usable building block. A replacement
model factory must return a CPU-capable module with the same declared input
and output tensor contract. Its forward call returns token logits and hidden
state. Bind the trainer to that factory and save an explicit architecture
identity when replacing the supplied architecture.

Training consumes Lab 1's training partition. Save the tokenizer, model
configuration, actual weights, training record, and `ModelIOContract` together.
Inspect `learning/checkpoint/training.json` and
`learning/training-check.json`. Confirm that parameter hashes change, the
checkpoint reloads, and held-out records do not enter the update. The
`language evaluate` command provides separate held-out text diagnostics.

Changing a metadata flag is not training. Explain what the loss measures and
why lower text loss alone says nothing about the quality of a proposed chip.

## Lab 5: turn inference into a bounded design action

Implement `serialize(task, history)`, `retrieve(query, documents, limit=...)`,
and `parse_action(text, allowed_actions)` in `labs/lab05_inference.py`.
The serializer should retain the facts needed for a decision within the
checkpoint's byte budget. Retrieval may return attributed excerpts only from
the supplied source set. The parser admits one legal action or rejects the
output.

Inspect `inference/inference-check.json` and its candidate and tool receipts.
Follow the model's selected action to the exact executed RTL. Try an unknown
action, an unapproved retrieval source, and an over-budget input. None should
silently become a default action or truncated observation. Real parameter
adaptation from measured development feedback occurs in the capstone, using
the same training component and checkpoint lineage.

## Lab 6: connect prediction to measured search

Implement `predict(task, candidate)` and
`choose(task, proposals, history, budget)` in `labs/lab06_search.py`.
A prediction carries a metric value, unit, and nonnegative uncertainty.
The chooser selects a permitted next action using remaining budget and
previous observations. Returning no action ends the search.

Inspect `search/campaign.json`. Compare predicted cycles with freshly
measured cycles, and retain the prediction error. The supplied first-untried
policy is a conventional baseline. A surrogate can help choose what to
measure, but its estimate does not replace a functional or physical check.
Explain why a confident estimate for an unseen workload may be wrong.

## Lab 7: make the proposal change hardware

Implement `transform(source, action)` in `labs/lab07_architecture.py`.
The first exercise exposes one-bit and two-bit serial-multiplier
implementations under a frozen action contract. Both use the same workload
program and must preserve numerical results. The checker compares the
transformation with the declared legal implementation before executing it.

Inspect both directories beneath `design/candidate/`. Compare RTL bytes,
cycles, memory traffic, and required checks. A later extension can introduce
a new transformation by versioning the task and action contract for every
comparison method. Changing the action's meaning while retaining its old
identity invalidates the experiment.

## Lab 8: connect the exact design to physical consequences

Implement `summarize_physical_receipt(raw, candidate_sha256)` in
`labs/lab08_physical.py`. Validate source identity before interpreting named
checks. Preserve failed, unresolved, and unavailable outcomes. A GDS file is
an implementation artifact; acceptance also depends on correspondence,
timing, electrical constraints, antenna checks, DRC, and LVS under the
declared platform.

Inspect `physical/receipt-summary.json` and the referenced raw reports.
Follow the RTL hash from Lab 7 into implementation. Distinguish the complete
core's realized storage from its declared external memory interface. A
retained physical result can support later work only when the relevant
hardware, constraints, platform, and tool identities match; identify that
reuse explicitly.

## Lab 9: test the assembled system

Implement `compare_campaigns(campaigns, *, evaluation_groups, campaign_cost)`
in `labs/lab09_evaluate.py`. The capstone composes the active earlier
components, updates the saved model from designated development results,
freezes it, and executes held-out comparisons. The function receives the
resulting records for adapted inference, unchanged inference, enumeration,
and the constant-action baseline. Each method contains the same evaluation
groups, objective and units, candidate budget, and per-case outcomes with
their actual tool receipts.

Return a summary that preserves each method and case, the outcome and eligible
counts, the best measured candidate or `None`, and the recorded costs. The
starter module documents the exact fields. The checker compares these facts
with immutable campaign records, so omitting a baseline, changing a unit,
promoting an invalid candidate, or rewriting an input cannot complete the lab.
The interpretation remains the student's responsibility.

Report `campaign_cost` once at the top level. It includes preparation,
training, adaptation, and campaign totals. Method and case costs explain
parts of that work; adding them to the campaign total would count work twice.
Preserve the explicit `cost_allocation` labels. A hypothetical reuse of the
trained model does not remove its measured preparation cost from this run.

Inspect `evaluation/decision.json` and its source and checkpoint identities.
The adjacent `evaluation/architect-review.json` is an immutable template marked
`pending_review`. Copy it outside the retained attempt, for example into the
workspace's `reviews/` directory, before recording your identity, disposition,
and rationale. Preserve its evidence paths and hashes. Editing the original
template would invalidate the course record. The separate human review does
not replace mechanical functional or physical acceptance.
Separate parameter updates, action changes, checked design outcomes, and
total cost. A tie is a valid experimental result. The final hardware decision
also needs physical evidence for the actual selected implementation; a GDS
file for a different candidate cannot satisfy that condition.

## Assess a student extension

Freeze a task, dataset, budget, and baseline before changing one component.
Retain the changed implementation and rerun affected labs. Inspect whether
the change reaches the intended downstream boundary, then compare held-out
results and total work. Examples include a different representation, a
retriever, a model architecture, a predictor, or an experiment-selection
policy.

A retrieval extension provides a small example. Follow an attributed excerpt
into the recorded model input, confirm that inference loads the same frozen
checkpoint, and trace its action to the executed RTL. The reference and
extension may select the same design. That result can establish that the
component is connected correctly without establishing an improvement. The
held-out comparison must still measure the effect on designs and total work.

A passing submission explains the data's limits, traces a result to its
candidate and raw evidence, diagnoses a deliberately introduced failure,
and states what the comparison supports. A faster invalid design, lower
training loss without better decisions, or a physically unverified winner
does not establish architectural improvement.
