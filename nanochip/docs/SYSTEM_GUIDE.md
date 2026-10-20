# One Nanochip system

An architecture team must connect its workload, design choices, test data, and tools before it can say whether a proposed chip is better. Nanochip makes that connection the subject of one cumulative laboratory. The keynote, book examples, tutorial, student labs, and research extensions use the same target, experiment records, and comparison rules. Students learn to build and judge the system that produces a design result, not only to use a supplied model.

The complete destination is a Kimi nano-KPU-derived workload carried through functional checks and a physically checked implementation. The local system now runs a complete reduced mathematical workload in a new serialized RTL core, trains a separate design helper, and compares learned and conventional methods. Complete-core physical acceptance and the final source-frozen runtime image remain unfinished.

![Flow diagram of Nanochip. Attributed data trains a small design model. Its checkpoint supplies a proposer inside a harness that connects representations, search, candidate artifacts, and functional and physical tools. Tool observations inform the next decision, while only curated development records return to training. Held-out evaluation uses frozen checkpoints and matched budgets, then supports a separate architect decision.](nanochip-system.svg)

## Two model roles, one design loop

Nanochip has two distinct model roles. The workload model is the computation executed by the chip. The design-helper model is a small byte-level language model trained to propose permitted changes to that computation's implementation. The helper is not the model running on the chip, and the chip's numerical fixtures do not demonstrate language quality.

The chip executes the reduced Kimi-derived workload with generated weights and inputs. Its independent floating-point and fixed-point references check the result. The current teaching geometry has model width 8, vocabulary 16, two layers, and at most four tokens. It retains the workload's KDA and MLA operations, causal convolution and attention state, grouped INT4 matrix operations, runtime top-two expert selection, routed and shared experts, residual mixing, and output head. This is a smaller workload configuration, not the upstream model scale or RTL.

The RTL is a new serialized integer microarchitecture. A shape-derived compiler emits instructions using only declared geometry and sequence length. It does not calculate activations, select experts, or inspect expected outputs. The core fetches the program, packed weights, parameters, input tokens, and nonlinear tables through an explicit external-memory interface; it computes the intermediate activations and outputs itself. Control, registers, recurrent state, KV state, and scratch storage lie inside the core boundary. The external memory system lies outside it.

The first legal implementation choice changes whether the multiplier processes one or two multiplier bits per cycle. Both choices execute the same program and must pass the same complete-workload checks. This bounded action space teaches the full path from model input to candidate and measurement. It does not establish open-ended RTL generation or design autonomy.

## How data, models, tools, and feedback connect

A task fixes the workload, objective, legal actions, required checks, and candidate budget. A proposer selects an action. The materializer builds the exact program and RTL for that action, and a candidate manifest binds its files to hashes. Functional and physical backends return scoped receipts with tool identity, checks, metrics, costs, raw outputs, and execution status. A timeout, unavailable tool, failed check, and passing measurement remain separate outcomes.

Training and inference use separate feedback paths. During a campaign the checkpoint is fixed; new tool observations can change which action the proposer selects next. Between campaigns, explicitly curated development records can update the model and produce a new checkpoint. That update records its data, objective, input contract, and predecessor checkpoint. Held-out test records stay outside training and retrieval for the comparison. Changes in text loss or action probabilities do not count as design improvement unless checked outcomes or the cost of reaching them change.

The system compares adapted inference with the unchanged checkpoint, enumeration, and a fixed-action policy. All methods receive the same legal actions, checks, held-out cases, and candidate budget. In the latest retained functional capstone, all four methods chose `serial_mul2` as the best measured action on both held-out groups. They tied at 7,511,563 cycles for the three-token case and 10,012,579 cycles for the four-token case. This shows that the learning and evaluation path executes; it does not show that adaptation improved the design. The records are in [the functional campaign report](../../output/nanochip/course-capstone-functional-20261018-v5/evaluation/campaign/report.json) and [the course comparison](../../output/nanochip/course-capstone-functional-20261018-v5/evaluation/decision.json).

The capstone also keeps prediction separate from measurement, and cost components separate from the total so the same work is not counted twice. The reported receipts measure recorded runtime; they do not include setup or human effort unless those costs are separately recorded.

## Nine cumulative student components

Each course workspace contains editable components, retained attempts, and checks. Later labs consume artifacts from earlier labs. If an upstream source changes, dependent results become stale. Student code runs as written; the course does not silently replace an incomplete implementation with the reference solution. The nine components are implemented in the course framework, while end-to-end completion still depends on physical evidence.

| Lab | Student contribution | What the system checks |
|---|---|---|
| 1. Workload and data | Group records, preserve provenance, characterize coverage, and split data. | Related experiments remain in one partition and records retain their source identity. |
| 2. Representations and numerical checks | Pack and unpack actual INT4 model weights. | The representation matches an independent oracle on generated workload data. |
| 3. Experiment harness | Interpret candidate-bound receipts and summarize measured cost. | Identity mismatches, missing checks, tool failures, and invalid candidates cannot become passes. |
| 4. Train a small model | Build the model and train real parameters. | The checkpoint reloads with its declared input contract and held-out records remain excluded from updates. |
| 5. Adapt and use the model | Serialize a task, retrieve bounded attributed context, and parse a legal action. | A legal proposal reaches the shared harness; malformed proposals and unapproved sources fail explicitly. |
| 6. Predict and search | Predict a metric and choose the next experiment within a budget. | Predictions retain units and error; search uses legal actions and returned tool evidence. |
| 7. Change the architecture | Transform the core between the two multiplier implementations. | Candidate identity and complete-workload numerical and protocol checks remain intact. |
| 8. Close the physical path | Interpret a physical receipt for the exact candidate. | Source identity, physical check scope, and unresolved results remain visible. |
| 9. Evaluate and improve | Update from development feedback and compare frozen methods on held-out cases. | Independent groups, equal budgets, best measured candidates, receipts, and total campaign cost are retained. |

The course can be started and inspected with these commands from the repository root:

```bash
python3 -m nanochip.laboratory doctor
python3 -m nanochip.laboratory course init my-nanochip --mode student
python3 -m nanochip.laboratory course status --workspace my-nanochip
python3 -m nanochip.laboratory course run --workspace my-nanochip --lab 1
```

The instructor recovery path through the first seven labs is:

```bash
python3 -m nanochip.laboratory course init instructor-nanochip --mode instructor
python3 -m nanochip.laboratory course run-all --workspace instructor-nanochip \
  --mode instructor --through 7
```

The source-snapshot candidate image completed this path and retained seven passing course records. Lab 8 invokes the physical backend; Lab 9 composes the resulting physical evidence with the functional comparison. Those later steps are not a substitute for a passing physical receipt.

## Commands and measured effort

Run the connected learning and design comparison on the complete reduced workload with physical implementation explicitly omitted:

```bash
python3 -m nanochip.laboratory system --functional-only \
  --output output/nanochip/my-functional-system
```

This command trains a design helper, adapts it from designated development tool feedback, freezes the relevant checkpoints, then compares adapted, unadapted, enumeration, and constant-action methods on held-out cases. It performs fresh RTL execution and records cycles and memory traffic. It does not run the physical flow. A run from the source-snapshot candidate image took 121.825 seconds inside a two-CPU, 8 GiB container on the validated ARM64 setup. This is one retained execution, not a laptop runtime promise.

For a short demonstration of feedback during a run, use:

```bash
python3 -m nanochip.laboratory core-feedback \
  --output output/nanochip/my-feedback-exercise
```

This exercise injects a numerical fault into a private RTL copy. An authored controller receives the failing check and repairs the candidate; a control run without the feedback stops. It demonstrates inference-time control, not model-weight adaptation. The system campaign demonstrates the separate training and adaptation path.

The default system command also requests physical validation of the nominated design:

```bash
python3 -m nanochip.laboratory system \
  --output output/nanochip/my-physical-system \
  --physical-timeout 14400 --correspondence-timeout 3600
```

Physical implementation and mapped-netlist verification have separate wall-clock budgets of 14400 and 3600 seconds. The outer container launcher defaults to 21600 seconds, allowing one selected physical run, its mapped check, and a further 3600 seconds for course, learning, and collection work. The [budget calculation](../../output/nanochip/complete-core-physical-20261018/flow-runtime-analysis-1/budget-decision.json) binds these provisional limits to the historical stage assembly; it does not measure the new generic profile. These limits bound execution and do not promise completion. Every-candidate physical studies may need a larger explicit outer limit. Final physical acceptance remains unfinished. The prepared dependency image and a source-snapshot candidate image exist, but the final source-frozen full runtime image has not been built. See the current limits below and the [full runtime record](../containers/FULL_RUNTIME.md) for the current image boundary and prior candidate-image execution evidence.

The earlier [dequantizer block demo](DEMO_WALKTHROUGH.md) remains useful for inspecting the first wiring proof and block physical adapter. Its GDS and checks do not stand in for the serialized complete teaching core. Commands that execute experiments require fresh output paths; retained development outputs are evidence for their original runs, not bundled student results or an automatic fallback.

## Current limits

The latest retained gate-readiness checkpoint completes the full nominal workload in 358.534 seconds. Its full output image matches the RTL image byte for byte; all 64 logits and four argmax values match exactly, with zero protocol errors. This is a passing nonfinal checkpoint, not final mapped correspondence or physical acceptance; its receipt marks it ineligible for those claims. The [checkpoint comparison](../../output/nanochip/complete-core-physical-20261018/gate-readiness-checkpoint-full-nominal-2/comparison.json) and [checkpoint receipt](../../output/nanochip/complete-core-physical-20261018/gate-readiness-checkpoint-full-nominal-2/engineering-receipt.json) retain that evidence.

The physical flow has generated GDSII for the complete teaching core, but the layout has not passed the required checks. The [routing continuation](../../output/nanochip/complete-core-physical-20261018/selected-clean-drt-continuation-1/engineering-receipt.json) completed detailed routing with zero router-reported DRC errors. Extracted setup and hold checks passed, and the [constraint-coverage check](../../output/nanochip/complete-core-physical-20261018/selected-clean-drt-continuation-1/coverage-receipt.json) passed at all nine declared corners. The same run found 344 antenna-violating nets and 460 affected pins, together with maximum-corner counts of 5,080 slew violations and 1,359 capacitance violations. These failures prevent physical acceptance despite positive setup and hold slack.

An earlier [combined repair checkpoint](../../output/nanochip/complete-core-physical-20261018/incremental-antenna-electrical-probe-5/receipt.json) had passed electrical and antenna checks using global-route estimates. Its [timing observations](../../output/nanochip/complete-core-physical-20261018/incremental-antenna-electrical-probe-5/observations.json) reported positive setup and hold slack and no fanout, slew, or capacitance violations at the nominal typical, slow, and fast process conditions. A [separate check of that saved design](../../output/nanochip/complete-core-physical-20261018/incremental-antenna-electrical-probe-5/fresh-antenna/or_metrics_out.json) also found no antenna violations. Detailed routing and extraction supplied stronger evidence and exposed the remaining failures. The earlier estimates cannot override those results.

Repair must preserve the relationship between electrical loading and antenna protection. An earlier [instrumented diagnostic](../../output/nanochip/complete-core-physical-20261018/antenna-wrapper-ordering-probe-2/observations.json) showed that cell mirroring and a later full reroute undid much of the antenna repair. The revised sequence preserves repaired routes, but protective diodes add electrical loads. The preliminary checkpoint added a buffer that moved four functional loads off a net while leaving its protective diode attached. Separate [electrical](../../output/nanochip/complete-core-physical-20261018/incremental-antenna-electrical-probe-5/electrical-reachability.json) and [antenna](../../output/nanochip/complete-core-physical-20261018/incremental-antenna-electrical-probe-5/antenna-reachability.json) connectivity checks confirmed that original signal loads still reached their original drivers and clock connectivity was unchanged. These checks support connectivity within their declared scope; they do not replace workload simulation or layout-versus-schematic verification.

After GDSII generation, Magic produced an empty LEF file. The following pin-property check stopped, so final Magic DRC, KLayout DRC, and LVS did not complete in that run. A subsequent [isolated LEF retry](../../output/nanochip/complete-core-physical-20261018/strict-complete-core-lef-retry-1/receipt.json) completed with the original geometry and writer settings under an explicitly larger 7 GiB memory limit. Its [producer record](../../output/nanochip/complete-core-physical-20261018/strict-complete-core-lef-retry-1/lef/nanochip-lef-producer.json) binds a nonempty, completed LEF to a successful Magic exit. The complete-core profile now rejects failed Magic processes rather than admitting their partial output. These results establish producer feasibility; they do not establish final layout correctness or the cause of the earlier process failure.

A continuation using that completed LEF and the unchanged GDSII passed the [layout comparison](../../output/nanochip/complete-core-physical-20261018/strict-layout-tail-continuation-2/runs/physical/02-checker-xor/state_out.json) with zero XOR differences. Magic then checked the GDSII geometry and reported [zero design-rule violations](../../output/nanochip/complete-core-physical-20261018/strict-layout-tail-continuation-2/runs/physical/03-magic-drc/reports/drc_violations.magic.rpt), with a successful producer exit. The independent [KLayout DRC report](../../output/nanochip/complete-core-physical-20261018/strict-layout-tail-continuation-2/runs/physical/04-klayout-drc/reports/drc_violations.klayout.json) also contains zero violations, and both native DRC checkers completed successfully. Netgen then compared the extracted circuit with the powered netlist; its [LVS report](../../output/nanochip/complete-core-physical-20261018/strict-layout-tail-continuation-2/runs/physical/09-netgen-lvs/reports/lvs.netgen.rpt) reports a unique circuit match, and the native LVS checker passed. These checks support the geometry and circuit correspondence of this retained layout. Its antenna and electrical failures still prevent acceptance.

The continuation exited successfully without a Docker-reported out-of-memory termination. Its final resource collector failed because the diagnostic script addressed the wrong mount path, so the run does not establish peak memory or final memory-limit event counts. The [terminal review](../../output/nanochip/complete-core-physical-20261018/strict-layout-tail-terminal-review-1/review.json) records this measurement gap separately from the completed layout checks.

The retained runs are engineering diagnostics that reuse earlier checkpoints. Closure still requires a repaired implementation, repeated checks on its exact artifacts, final mapped-workload verification, and fresh execution through the reusable installed flow.

The functional campaign currently offers only two multiplier implementations, and the conventional methods find the same best action as the learned methods on the held-out cases. No learning advantage has been measured. Final physical closure, final course composition, and the final runtime image still need evidence. Setup time, student-laptop resource use, and independent classroom adoption have not been established. The project remains a research and teaching system under development, with checked GDSII as its destination rather than its present result.
