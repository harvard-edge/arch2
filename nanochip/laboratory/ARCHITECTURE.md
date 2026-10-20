# Nanochip implementation blueprint

Nanochip is one cumulative ecosystem laboratory. Students build and replace
components of an AI-native design system while following the same Kimi-derived
accelerator from workload through checked GDSII. The [starter guide](README.md)
owns current commands.

## Purpose and architectural boundary

The project's North Star is explicit:

> *Architecture 2.0* teaches architects the discipline of AI-native system and
> chip design. The book begins with architecture problems rather than AI
> products, and its object of study is the AI-native design system, the
> configured ensemble of learned models, conventional simulators, versioned
> artifacts, tool interfaces, feedback loops, and verification checks that
> carries compact system intent through real tools, measurements, and checks to
> a supported architecture result, under human commitment authority.

The course asks how a small accelerator should organize weight delivery and
computation within numerical, area, and timing constraints. Its complete target
includes control and realized on-chip memories. External memory remains an
explicit interface. A smaller teaching configuration needs its own contract
and reference checks while retaining the defining attention, expert-routing,
quantization, state, and memory mechanisms.

The [official nano-kpu repository](https://github.com/MoonshotAI/nano-kpu)
supplies an RTL design, reference computation, specifications, and evaluation
harness. It describes a Kimi K3 demonstration and pre-layout synthesis
estimates. It is a source artifact rather than a supplied student notebook;
this checkout contains no Kimi notebook. Its [weight documentation](https://github.com/MoonshotAI/nano-kpu/blob/main/weights/README.md)
states that scored evaluation uses seeded synthetic weights. Preserve this
reference and teach training through the separate design helper.

## Current files and ownership

Keep `nanochip/kpu/` as the frozen upstream reference. Student extensions belong
outside it and materialize new candidate snapshots. The executable laboratory
currently has these responsibilities:

| Files | Responsibility |
| --- | --- |
| `contracts.py`, `interfaces.py` | Task, action, candidate, receipt, observation, and method boundaries |
| `runner.py`, `evidence.py` | Bounded execution, artifact checks, assessment, and event records |
| `adapters.py`, `dequant_probe.py`, `assets/dequant_tb.cpp` | Reference/fault materialization, conventional controller, and finite RTL checking |
| `data.py`, `datasets/dequant_corpus.py` | Provenance, grouped partitions, constructed cases, and observation serialization |
| `models/sequence.py`, `models/proposer.py` | Recurrent action-decoder training, adaptation, saved-checkpoint inference, and proposer adapter |
| `context.py`, `experiments.py` | Bounded keyword retrieval, learning study, and explicit diagnostic execution |
| `design_learning.py`, `design_changes.py`, `design_experiment.py` | Constructed design-action data, learned selection, explicit RTL transformation, differential checks, and composition with the physical adapter |
| `design_feedback_data.py`, `design_feedback_learning.py`, `design_feedback.py` | Audited tool-derived preferences, matched parameter updates, and fresh control/adapted campaigns through the same design command |
| `physical/flow.py`, `physical/config.json` | Pinned block implementation and scoped physical receipts |
| `student.py`, `exercises/`, `__main__.py` | Student feedback and RTL-transformation hooks, component checks, and command-line entry points |

These are ordinary modules, not a plugin registry. Extract further packages
only when independent implementations make their ownership clearer. Future
exercise folders should contain instructions, student components, integration
checks, and recovery-checkpoint pointers into this runtime. They should share
RTL, datasets, models, and tool adapters. Generated runs belong under ignored
`output/` directories, separate from source and historical walkthroughs.

## Dependencies and feedback

The existing [system plan](../docs/nanochip-system-plan.svg) depicts the proposed
whole. The execution dependencies are:

```text
workload contract + action -> materializer -> manifested candidate
candidate -> functional and physical tools -> receipts -> observations
observations + permitted context + remaining budget -> next action

development receipts -> curated training view -> train/adapt -> checkpoint
checkpoint + represented observation + retrieved sources -> inference
independent evaluation -> comparison -> architect's disposition
```

The harness owns required checks, identities, and execution budgets. A method
cannot weaken them. Retrieval supplies bounded, identified sources to the
proposer; it does not authorize actions. Training changes parameters between
campaigns. Inference loads an identified checkpoint during a campaign. Final
evaluation stays outside parameter updates and retrieval corpora.

The diagnostic path executes the decoded inspection of retained evidence.
The design path instead decodes an explicit architectural action and
materializes its RTL before invoking functional and physical tools. Both use
the shared proposer, candidate, and receipt interfaces. The original
reference/fault campaign still exercises conventional feedback. Useful
architectural search requires reliable learned decisions across a broader
space than the first two-action experiment.

## Implementation and evidence status

**Implemented:** candidate-linked execution, finite dequantizer checking,
constructed corpus collection, action-decoder training and adaptation,
checkpoint inference, keyword context, diagnostic inspection, a packed-row
RTL transformation, a block physical adapter, and feedback-derived adaptation
with an equally trained control. The alpha adds one integrated `demo` command,
model representation contracts, an installed Python launcher, and an
executable memory-mapping exercise. The decoders train action
and end tokens from represented inputs; this is structured action imitation,
not general language-model pretraining.

**Measured:** the [initial measurement record](MEASUREMENTS.md) links actual
block and learning executions to their inputs, tool outputs, costs, and
limitations. Diagnostic learning and adaptation ran locally; the model still
poorly distinguishes numerical and protocol cases. A physical run produced
block GDSII and passed several checks, but electrical and antenna violations
remain. The [design experiment](DESIGN_EXPERIMENT.md) adds a fresh baseline
comparison for the model-selected RTL. The [feedback study](FEEDBACK_EXPERIMENT.md)
tests whether learning from those results changes the next selected design.
No laptop runtime envelope, retrieval advantage, model superiority,
or complete-core physical result follows from these point experiments.

**Planned:** broader language training, additional architectural extensions,
complete-workload campaigns, realized memories, full-core correspondence and
physical checks, independent comparisons, and the complete cumulative course.
The complete course must exercise those components together.

## Nine cumulative student artifacts

| Lab | Student artifact retained in later work |
| --- | --- |
| 1. Workload and data | Workload manifest, provenance checks, grouped development/evaluation split, baseline record |
| 2. Representations | Packed-weight conversion, independent numerical oracle, structured failure localization |
| 3. Harness | Candidate materializer or tool adapter with timeout, failure parsing, and artifact identity |
| 4. Train | Tokenization/batching or training component, changed parameters, reloadable checkpoint, held-out record |
| 5. Adapt and infer | Adapted checkpoint, legal-action parser, executed proposer, optional sourced retrieval |
| 6. Predict and search | Analytical bound, conventional baseline, budgeted policy, measured prediction comparison |
| 7. Extend the architecture | New implementation family, corresponding representation changes, complete-workload regressions |
| 8. Physical implementation | Realized memory integration, candidate-linked layout, constraints, physical and correspondence reports |
| 9. Evaluate | Curated development feedback, another adaptation, independent campaigns, total-cost comparison, disposition |

Each exercise needs a visible input, executed command, retained output,
deliberate failure, and next decision. Recovery checkpoints identify supplied
components. The instructor system must be complete before advertising the full
course; a tutorial may supply more checkpoints from that same system.

## Graduated integration milestones

1. **Execution:** distinct artifacts produce fresh checks that change a later
   action; errors and missing evidence remain distinguishable.
2. **Executed corpus:** every example resolves to checked source artifacts and
   raw receipts; constructed faults and related partitions remain disclosed.
3. **Train and adapt:** record parameter changes, checkpoint lineage, data
   views, held-out behavior, and measured cost.
4. **Inference and retrieval:** execute the checkpoint's legal diagnostic with
   identified context; compare with conventional and no-retrieval baselines.
5. **Physical block:** implement the exact checked block and retain named
   layout, DRC, LVS, timing, and unresolved correspondence obligations. Connect
   an explicit learned design action to that same source and its measurements.
6. **Full-core physical:** realize memories, preserve workload behavior, and
   connect functional correspondence through implementation to checked GDSII.
7. **Complete course:** reproduce cumulative checkpoints from a clean prepared
   environment and compare architecture outcomes and total process cost within
   a measured student-laptop envelope.

A point demonstration or block layout can establish an intermediate component.
The complete accelerator claim requires the final two milestones. Checked
GDSII remains limited to the declared platform and checks; fabrication and
foundry-approved tapeout readiness are separate outcomes.
