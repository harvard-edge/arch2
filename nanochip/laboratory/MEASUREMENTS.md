# First Nanochip component measurements

These October 17, 2026 executions establish the first working components.
They do not establish the complete course, a useful architecture optimizer,
or a laptop runtime guarantee. Runs used an ARM64 host with 64 GiB of RAM.
The physical flow ran while some learning and checking work was in progress.
Setup and download costs are excluded because prerequisites were installed.

The linked run folders are local, ignored experiment outputs. They retain
data, checkpoints, raw logs, and hashes; they are not a published dataset.
Publication will require a frozen source revision and an archived evidence
bundle. The executable commands are in the [laboratory guide](README.md).

The subsequent [design experiment](DESIGN_EXPERIMENT.md) connects a learned
action to modified RTL, fresh functional checks, and a fresh baseline/candidate
physical comparison. The measurements below retain their original scope.
The [feedback experiment](FEEDBACK_EXPERIMENT.md) extends that sequence with
matched parameter updates and prospective executions of the selected designs.

## Functional execution and data

The [initial campaign](../../output/nanochip-starter-20261017-1/campaign.json)
freshly compiled and simulated two dequantizer candidates in 6.417 seconds
using Verilator 5.052. Each executed 1,740 scalar comparisons. The constructed
incorrect-shift variant produced 1,461 mismatches; the reference produced
none. The conventional controller responded to the returned failure. This
establishes feedback execution, without attributing the choice to a model.

The [diagnostic corpus](../../output/nanochip/corpus-point-final/manifest.json)
contains 15 fresh builds and 12 simulations, totaling 27.965 seconds of probe
time. Its records comprise six training, five development, and four final-test
cases. There is one passing reference, six numerical faults, five protocol
faults, and three compile failures. Each record resolves to its source,
receipt, raw outputs, and numerical vectors. The record-file SHA-256 is
`c6b5b712bd9c0d4dfcb04aa26a1ee43f14daec4097ca1ca46566937f7f480d2f`.

The faults were deliberately constructed. Labels follow a disclosed
diagnostic teaching rule. Partitioned mutation templates share the same RTL
base and vector suite. Exact duplicate observations do not cross partitions;
there are no passing/accept cases in development or final test. This corpus
can expose plumbing and representation failures, but cannot establish
generalization to natural design faults or other architectures.

## Training, adaptation, and inference

The [learning study](../../output/nanochip/learning-point-v1/study.json)
trained a 17,736-parameter byte-GRU action decoder with PyTorch 2.11.0 on CPU.
The model receives observation bytes and predicts one of four action tokens
followed by an end token. Only action and end-token loss drives updates;
this is diagnostic imitation, not general language-model pretraining.

| Phase | Data used for updates | Steps | Wall time |
| --- | --- | ---: | ---: |
| Initial training | Six training records | 300 | 8.320 s |
| Adaptation from saved initial weights | Five explicitly promoted development records | 150 | 3.686 s |
| Complete study, including evaluation | Four final-test records used only for evaluation | — | 12.048 s |

The saved parameter hashes confirm real updates and adaptation from the
exact initial checkpoint. Both updates finished before either model was
evaluated on the final partition. The initial model agreed with the teaching
labels on two of four cases; the adapted model agreed on three. A training-set
majority baseline also agreed on two. These counts are too small for a
superiority claim, and inspecting predictions reveals a more specific problem.

The simulated fault cases receive almost identical probabilities for
`inspect_numerics` and `inspect_protocol`. Adaptation changes which of these
nearly tied classes wins. The input-insensitivity is consistent with the
final-state recurrent model losing early diagnostic information after a long
shared suffix. The accuracy change does not establish improved diagnosis,
repair, or architecture quality. This is a useful representation exercise
for development data; a revised method needs a newly frozen evaluation set.

The [checkpoint diagnostic](../../output/nanochip/diagnosis-point-v2/diagnosis.json)
executed the decoded `inspect_numerics` request. A separate
[retrieval integration run](../../output/nanochip/diagnosis-rag-point-v2/diagnosis.json)
loaded the same adapted checkpoint, retrieved one attributed specification
excerpt, and executed `inspect_build`. This second run added context only at
inference and establishes wiring, not retrieval benefit. Both runs inspected
retained RTL evidence. Neither reran simulation, changed RTL, or claimed
complete-design acceptance.

## Physical implementation

The [physical audit](../../output/nanochip-physical-api/audited-receipt.json)
binds 1,144 retained artifacts to the dequantizer source, configuration,
pinned container, PDK, and producing stages. Its input SHA-256 matches the
reference candidate in the functional corpus. The run used SKY130 HD,
a 100 ns clock, 35% core utilization, 45% placement density, and one CPU.
It completed the tool flow within the declared 900-second process bound.
The exact complete-flow wall time was not recovered after a driver failure;
it must not be reconstructed from file modification times.

| Check | Observed result |
| --- | --- |
| GDSII output | 20,868,850 bytes; retained and parsed for a layout preview |
| Detailed-router, Magic, and KLayout DRC | Zero reported errors in each check |
| Netgen LVS | Zero reported errors |
| Post-route setup/hold | Zero violations; worst slack 54.819201 ns / 0.106118 ns |
| Explicit STA constraint coverage | Passed all nine configured corners; 6.799 s supplementary execution |
| Post-route antenna | **11 violations** |
| Maximum slew / capacitance / fanout | **22 / 1 / 83 violations** |

The [layout preview](../../output/nanochip-physical-api/layout.png) was rendered
from the actual [GDSII](../../output/nanochip-physical-api/runs/physical/final/gds/msh_deq.gds)
and visually inspected. The GDS SHA-256 is
`54e6d67c79a1574eaa633c2c029e2142cd4b0189b8ba371be419e02a674ba443`.

The original Python driver failed when strict JSON serialization encountered
an inherited infinite metric. Raw output and the failure remain retained.
The corrected reader represents that value explicitly and never treats it
as a passing check. The supplementary audit reproduces producing-stage
checks and preserves the original driver error and `eligible=false`.
No repeat physical run or remedial optimization was used to hide this result.

This is generated block GDSII with outstanding failures, not a fully checked
accelerator. Complete workload correspondence, realized full-core memories,
RTL/netlist equivalence, electrical closure, and antenna closure remain.
The next implementation work should make those obligations executable while
extending learned actions from inspection to consequential design changes.
