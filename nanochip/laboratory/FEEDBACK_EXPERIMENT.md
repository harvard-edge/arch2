# Tool feedback changed probabilities but not the selected design

The first Nanochip feedback update completed the connection from measured
design results to model parameters and back to the design harness. It did not
improve the selected implementation. Both the equally trained control and
the feedback-adapted model selected the same streaming RTL as before. The
record preserves this unsuccessful update rather than selecting another
checkpoint after observing its decision.

The [student exercise](exercises/FEEDBACK_LOOP.md) explains how to construct
the feedback example, run the matched updates, and inspect the resulting
campaigns. This is the next component in the existing laboratory. It uses the
same model implementation, action vocabulary, materializer, functional
checks, and GDS flow as the [first design experiment](DESIGN_EXPERIMENT.md).

## The feedback and its objective

The retained physical results showed 90,177.7 µm² of cell area for indexed
reads and 104,379 µm² for streaming reads. Streaming improved setup slack but
increased area and slew violations. Both implementations failed electrical
and antenna checks, so neither was an accepted physical design.

The new experiment therefore declares an exploration objective: choose the
smaller area for the next run when both alternatives pass numerical,
differential, routed timing, DRC, and LVS checks and have identical remaining
failed-check families. This makes `retain_indexed_read` the preferred action
for this observed case. The objective was chosen after the original results
were known and frozen before the new updates and executions. It does not
retroactively make the original experiment a preregistered area study.

The [feedback manifest](../../output/nanochip/feedback-evidence-20261017-1/manifest.json)
contains one development example derived from two measured designs. Collection
verified 2,413 source-file hashes and copied 101 evidence files. It reran the
reference differential check, which completed 409 jobs and 15 resets, and
verified that the original candidate used the same comparison semantics.
Raw tool results remain linked to exact RTL and physical settings. Acceptance
is false in the feedback record; its area preference cannot erase failed
checks.

## The controlled update

Both updates start from the original 20,366-parameter byte-GRU checkpoint.
They use 56 original training replay rows and eight identified replicas of the
single new case. Their inputs, row order, sampled batches, optimizer, seed,
and budgets are identical. The control labels the new case using the original
constructed heuristic, which prefers streaming. The adapted model receives
the preference derived from measured area, which favors indexed reads.

The [frozen protocol](../../output/nanochip/feedback-loop-20261017-1/learning/protocol.json)
specifies seed 19, 120 updates, batch size 16, learning rate 0.001, and a
30-second bound per update condition. Each completes all 120 steps from the
same initial parameter hash. The original checkpoint remains byte-identical.
The comparison retains the final checkpoint in each condition; no target
prediction or later tool result chooses it.

| Model condition | P(indexed reads) | P(streaming) | Selected action | Original test accuracy |
| --- | ---: | ---: | --- | ---: |
| Frozen original | 47.61% | 52.39% | Streaming | 25% |
| Matched-update control | 31.91% | 68.09% | Streaming | 25% |
| Measured-feedback adaptation | 45.77% | 54.23% | Streaming | 25% |

The measured label increases probability of the area-preferred action by
13.86 percentage points relative to the equally trained control. It does not
improve that probability relative to the original model, and it does not
change the decoded action. These are uncalibrated action probabilities. The
original constructed development and test partitions remain at 25% exact
action accuracy in all conditions. Always choosing indexed reads would score
87.5% on each of those partitions. The model has not learned a reliable
decision rule for the constructed tasks.

Inspection of the retained test predictions gives a concrete diagnosis to
investigate. All 21 cases with `reuse=0` select streaming, despite differences
in earlier input features; the three cases with `reuse=1` select indexed
reads. This pattern suggests weak feature discrimination, but does not by
itself establish why the model learned it. Improving the representation or
training distribution is a hypothesis for a subsequent experiment.

The fixed-budget updates also did not lower the full training-view loss.
Control loss changed from 0.32318 to 0.32335; adapted loss changed from
0.32918 to 0.33036. Each is masked action-and-end-token cross entropy on its
own labeled training view. Different label distributions prevent treating
the two absolute losses as a common physical objective.

The updates use supervised imitation of a preference derived from tool
measurements. They do not train a new physical predictor. The conventional
selector applies the same declared preference directly and recommends
indexed reads without model training. Nothing in this result establishes an
advantage over that selector.

Training, snapshotting, and regression diagnostics took 4.527 seconds. The
control's update took 0.829 seconds and the feedback update took 0.449 seconds.
These local costs exclude the original data-collection experiments and the
new physical campaigns. The source bundles and training views remain in the
[learning record](../../output/nanochip/feedback-loop-20261017-1/learning/report.json).

## Prospective tool results

Both selected sources passed 1,740 scalar comparisons and a differential
suite of 409 jobs, 92,417 cycles, and 15 resets. The selected RTL SHA-256 is
`1a5ad505cea7c60f81e756f7b4fe0c23fba87e1ce04c3d7bd16ceb72e9ffa449`
in both conditions. The model update therefore proposes no new hardware
relative to the first streaming experiment.

Both physical campaigns completed with the unchanged 100 ns clock, SKY130
platform, pinned tool image, and one CPU per process. Each generated GDSII
and passed detailed-route DRC, Magic DRC, KLayout DRC, LVS, and routed timing.
Both failed electrical constraints and post-route antenna checks.
RTL-to-netlist correspondence, complete-accelerator workload correctness,
and complete-accelerator checked GDS remain unresolved.

| Measurement | Matched-update control | Feedback adaptation |
| --- | ---: | ---: |
| Post-route cell area (µm²) | 104,379 | 104,379 |
| Cell instances | 13,719 | 13,719 |
| Worst setup slack (ns) | 60.951 | 60.951 |
| Worst hold slack (ns) | 0.09655 | 0.09655 |
| Slew / capacitance / fanout violations | 88 / 1 / 60 | 88 / 1 / 60 |
| Antenna violations | 9 | 9 |
| Physical execution (s) | 727.4 | 806.0 |
| Complete design accepted | No | No |

The [study record](../../output/nanochip/feedback-loop-20261017-1/feedback-study.json)
reports zero area change and no accepted or exploratory design improvement.
The complete concurrent study took 819.0 seconds, including learning, checks,
physical implementation, and evidence verification. Elapsed-time differences
between concurrent executions do not establish a model or design speedup.
These costs use an ARM64 host with 64 GiB of memory and a preinstalled physical
tool image; they exclude environment installation and the earlier experiments
that supplied the feedback.

The retained [control GDSII](../../output/nanochip/feedback-loop-20261017-1/control/attempts/attempt-0001/physical-e9913e7061f0/runs/physical/final/gds/msh_deq.gds)
and [adapted GDSII](../../output/nanochip/feedback-loop-20261017-1/adapted/attempts/attempt-0001/physical-4f410ef02bfd/runs/physical/final/gds/msh_deq.gds)
have separate execution records and file hashes. The final audit verifies
1,182 receipt-listed artifacts in each campaign, rederives physical check
statuses from raw tool outputs, and confirms that numerical, differential,
and physical tools consumed the model-selected source. Neither layout meets
the complete acceptance contract. Identical-source reruns cannot count as
learned design improvement, even if physical measurements differ.

## What students can conclude

The example separates a parameter update from architectural improvement.
The feedback changes learned parameters and affects probabilities relative
to a matched control, but the chosen implementation stays the same. The
system must report that failure at the level of the design outcome.

The 256-value case is now training data. A fresh tool execution on that case
is not evidence of generalization. The original constructed test checks
regression under its old labels; it does not test physical transfer. A revised
representation, replay ratio, or learning method would be a new development
experiment. Its unsuccessful predecessors and total costs must remain in the
record, and a transfer claim needs new workloads or design conditions whose
results did not select the revision.

This result supplies a concrete learning exercise without pretending that a
small update is already a useful architect. Students can inspect the data
and its weights, replace the feedback representation or update method, and
test whether their extension changes the next measured result while
preserving all functional and physical requirements.
