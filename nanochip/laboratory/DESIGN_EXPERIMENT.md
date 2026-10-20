# One learned RTL change through functional checks and GDS

On October 17, 2026, Nanochip executed a trained model's selected design
change through numerical checking, differential RTL simulation, and a fresh
SKY130 implementation flow. The changed block produced GDSII. Compared with
a fresh reference run, its cell area grew 15.75% and its worst setup slack
improved by 6.13 ns under the same constraints. Both implementations still
failed electrical and antenna requirements. This is an executed design
experiment, with no accepted physical improvement or model-superiority claim.

The [student exercise](exercises/RTL_DESIGN.md) adds this component to the same
laboratory. Students implement the transformation; the existing proposer,
materializer, runner, checkers, and physical adapter carry it into execution.
The experiment uses one block of the Kimi-derived accelerator. Full-workload
closure, realized core memories, and RTL-to-netlist correspondence remain
separate obligations on the path to complete checked GDSII.

## What the model selected

The dequantizer consumes a packed row of 4-bit weights in ascending order.
The reference selects a byte using a variable index and then selects its low
or high nibble. The alternative reads `qrow_v[3:0]` and updates the row with
`qrow_v <= {4'b0, qrow_v[1023:4]}` on each output cycle. Arithmetic, input
staging, output packing, addresses, and handshakes remain unchanged.

The saved model had both `retain_indexed_read` and `stream_quantized_row`
available. It decoded `stream_quantized_row`, assigning it probability
0.523942 versus 0.476058 for retaining the reference. These probabilities are
not calibrated confidence. Its raw action and end tokens were valid, and the
runner executed that action once without substitution or retries.

The model selects an authored transformation. It does not generate arbitrary
RTL or discover the transformation. The [proposal](../../output/nanochip/design-change-20261017-1/proposal.json),
[complete diff](../../output/nanochip/design-change-20261017-1/attempts/attempt-0001/candidate/change.diff),
and [execution link](../../output/nanochip/design-change-20261017-1/attempts/attempt-0001/execution-link.json)
make that distinction inspectable.

## Training data and the limits of this model

The design helper is a 20,366-parameter byte-GRU action decoder trained on
CPU with PyTorch 2.11.0. It consumes row length, quantization, reload behavior,
access order, index step, start position, pass count, and reuse. The corpus
contains 80 author-constructed semantic tasks. Labels express a disclosed
legality and engineering-preference rule; no synthesis or physical outcome
was used to label these examples.

| Partition | Distinct row lengths | Unique records |
| --- | --- | ---: |
| Training | 8, 24, 48, 96 | 32 |
| Development | 12, 40, 80 | 24 |
| Final test | 20, 56, 112 | 24 |

Each length has one sequential case and seven altered access or reuse cases.
Positive training records are repeated seven times to balance the training
view. Replicas are identified as replicas. The partitions share constructed
task families; they are not independent natural architecture workloads.
The executed 256-value target was declared before inference and lies outside
the training-length range.

The fixed seed-17 run completed 360 updates in 2.353 seconds including
training setup and checkpoint writing. Parameter hashes changed. There was
no held-out tuning. Exact action accuracy was **25% on both development and
test**, below the **87.5%** constant-retain baseline on those unbalanced
partitions. Recall was 100% for streaming and 14.29% for retaining. This model
does not yet reliably distinguish the conditions governing the design choice.
The original report computes the most frequent class separately per split;
all three original partitions have the same majority. The current helper
freezes that comparator from training frequencies before held-out evaluation.

The [training record](../../output/nanochip/design-learning-20261017-v1/model/report.json)
and [corpus manifest](../../output/nanochip/design-learning-20261017-v1/corpus/manifest.json)
retain the protocol, data, source snapshots, and checkpoint hashes. The bundle
was copied intact from its original temporary directory; historical absolute
paths remain in its metadata. The experiment loads the retained copy.

## What the tools established

The changed source passed the independent integer oracle: 15 rows, 1,740
scalar comparisons, and zero mismatches. Its numerical run took 1.717 seconds.
Differential simulation against the reference completed 409 jobs over 92,417
cycles, checked 13,305 valid writes, injected 15 resets, and exercised 19,178
stream-stall cycles. That run took 1.685 seconds. It checks controls each
cycle and data when output writes are valid, across the declared valid-row
contract. Neither check proves exhaustive sequential equivalence.

Both physical runs used the same pinned ARM64 tool image, SKY130A PDK,
100 ns clock, 35% utilization, 45% placement density, and one CPU. The
[physical guide](physical/README.md) records versions and assumptions.
The comparison uses post-route STA metrics and a separate post-route antenna
stage. Explicit constraint coverage passed in all nine configured corners.

| Measured result | Indexed reference | Model-selected streaming |
| --- | ---: | ---: |
| Cell area, µm² | 90,177.7 | 104,379.0 |
| Instances at post-route STA | 10,363 | 13,719 |
| Worst setup slack, ns | 54.8192 | 60.9507 |
| Worst hold slack, ns | 0.106118 | 0.096553 |
| Setup / hold violations | 0 / 0 | 0 / 0 |
| Slew / capacitance / fanout violations | 22 / 1 / 83 | 88 / 1 / 60 |
| Post-route antenna violations | 11 | 9 |
| Detailed-route / Magic / KLayout DRC errors | 0 / 0 / 0 | 0 / 0 / 0 |
| LVS errors | 0 | 0 |
| Physical execution, seconds | 575.244 | 803.743 |
| All required physical checks pass | No | No |

Cell area is the reported instance area, not die area. Positive slack under
this loose clock does not establish accelerator throughput. Area is not an
energy measurement. The runs overlapped on an ARM64 host with 64 GiB of RAM,
so their elapsed times are not a controlled speed comparison. The complete
candidate campaign took 809.565 seconds, about 13.5 minutes. This observation
does not establish a short-tutorial or minimum-laptop resource guarantee.

The result is a useful counterexample to accepting a plausible optimization
from its description. Removing an indexed read can alter register logic,
buffering, and routing enough to increase implemented area. The measurements
establish the tradeoff here; a causal explanation of the area increase needs
a separate netlist analysis. Nanochip retains the failing checks rather than
treating the existence of GDS as acceptance.

## Evidence and reproduction

The [audited comparison](../../output/nanochip/design-change-20261017-1/comparison.json)
records raw receipt paths, measured differences, and hashes. The
[audit script](../../output/nanochip/design-change-20261017-1/audit_exact_candidate.py)
verified all 1,127 baseline physical artifacts, 1,136 candidate physical
artifacts, and 1,182 artifacts in the composed functional/physical receipt.
It also verified checkpoint files, the candidate manifest, frozen task,
decoded action, and equality of the RTL consumed by all three tool stages.

| Artifact | SHA-256 |
| --- | --- |
| Original RTL | `6294a0a15c11eba09693557f2a23cd4e049ea9776499ff6487cedffcd4724273` |
| Changed RTL | `1a5ad505cea7c60f81e756f7b4fe0c23fba87e1ce04c3d7bd16ceb72e9ffa449` |
| Loaded checkpoint | `950b3747a080cc0ca6900420b18d8c641c8771c79738505a8c0d8c476bed717e` |
| Changed GDSII | `935593b4569f17c3b573042fb2940d1fdeb171b4869fa03a3cc42d59692eadc2` |

Inspect the [candidate campaign](../../output/nanochip/design-change-20261017-1/design-experiment.json),
[candidate physical receipt](../../output/nanochip/design-change-20261017-1/attempts/attempt-0001/physical-d03c65d32824/receipt.json),
[reference physical receipt](../../output/nanochip/design-baseline-20261017-1/physical/receipt.json),
and [generated candidate GDSII](../../output/nanochip/design-change-20261017-1/attempts/attempt-0001/physical-d03c65d32824/runs/physical/final/gds/msh_deq.gds).
The [layout preview](../../output/nanochip/design-change-20261017-1/layout-preview/layout.png)
renders those exact GDS bytes; its script and input hash accompany the image.
These are local ignored outputs, not a published evidence release. Executing
source snapshots remain with the run. Later improvements to metadata binding,
failure classification, and student conformance checks do not rewrite that
historical execution.

Use the [exercise commands](exercises/RTL_DESIGN.md) to train and run a new
candidate. A fresh reference requires its own physical run and numerical
probe, using new output directories:

```bash
python3 -m nanochip.laboratory physical --rtl nanochip/kpu/rtl/msh_deq.v \
  --output output/nanochip/reference-physical-001
python3 -m nanochip.laboratory probe --candidate reference \
  --output output/nanochip/reference-functional-001
```

Retain all checks and compare under the same constraints. The design command
returns a failing status when required block checks fail even if the tools
produced GDS.

The next learning exercise can curate these development outcomes, revise the
representation or model, and evaluate a frozen revision on new tasks. This
first campaign records physical feedback but does not retrain from it. Its
achievement is the complete, inspectable connection from one learned action
to one changed implementation and its measured consequences.

The subsequent [feedback experiment](FEEDBACK_EXPERIMENT.md) now executes
that parameter-update comparison. Its observations remain separate from this
first design experiment and do not change the scope of the measurements above.
