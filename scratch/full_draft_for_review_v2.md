# The Architecture 2.0 Moonshot {#sec-moonshot}

```{=latex}
\abstract*{This chapter introduces the Architecture 2.0 moonshot and explains why it is a computer architecture problem rather than a generic AI-generation problem, automated optimizer demo, or product forecast.}
```

::: {.callout-crux}
What would it take for AI to help architects turn intent into a system design
that others can check, compare, and reject, not just a plausible answer?
:::

Computer architecture is the discipline of turning workload intent,
technology constraints, software assumptions, physical limits, and evidence
into credible hardware-software systems. It has never been only about which
tools you use; it is about how well you build, holding efficiency, safety,
robustness, and reliability to evidence rather than to assertion. Architecture
2.0 names the next step in that practice: architects must design not only
artifacts, but also the design loops that produce, evaluate, reject, and justify
those artifacts [@ReddiYazdanbakhsh2025Architecture20].

This shift toward designing loops is easiest to state as a rule: a prompt is not yet an architecture
claim. It becomes one only when the loop can say what state it saw, what actions
it allowed, what alternatives it rejected, what evidence supports the result,
and who owns the commitment if the claim is wrong. When plausible artifacts are
cheap, that burden of proof, not the artifact, becomes the scarce work.

The practical reason architecture needs this discipline is efficiency, but
efficiency no longer means a single
performance number. The classical quantitative tradition already treated
performance, cost, and power as coupled architectural questions
[@HennessyPatterson2017QuantitativeApproach]. Dennard scaling, the trend that
held power density roughly constant as transistors shrank, made that coupling
favorable for a time; dark silicon (the share of a chip that must stay powered
off to fit its thermal budget), data-movement energy, warehouse scale, and
carbon accounting make it more difficult
[@DennardEtAl1974Scaling; @EsmaeilzadehEtAl2011DarkSilicon; @Horowitz2014Energy; @BarrosoHolzleRanganathan2019DatacenterAsComputer; @GuptaEtAl2021ChasingCarbon]. Today, efficiency includes performance, energy,
power delivery, reliability, scalability, sustainability, cost, verification
burden, engineering effort, and time to credible evidence. Across that range,
the design problem is increasingly coupled across hardware, software, tools,
and deployment.
This multidimensional coupling is exactly what makes naive generation insufficient: an
AI-assisted loop must know which constraints, tools, and evidence can change
the architectural claim.

It helps to see how unusual this moment is. For roughly fifty years, processor
generations improved through a remarkably stable loop. Device scaling delivered
faster, cheaper, lower-power transistors on a predictable cadence; the
quantitative method turned design choices into measured comparisons; when
scaling slowed, microarchitecture, parallelism, and then domain specialization
kept the gains coming [@HennessyPatterson2019GoldenAge]. That run of
specialization is often called a new golden age for computer architecture; its
quieter companion is a golden age of complexity, in which every design must
navigate an explosion of workloads, software interfaces, and physical
constraints. The artifacts changed every generation, but the loop that produced
them stayed largely the same:
propose, model, measure, and commit. What is new is not another lever inside that
loop. It is that the loop itself, the rate at which credible choices can be
proposed, evaluated, rejected, and justified, has become the bottleneck.
What is missing is an explicit representation of that loop, and that
representation is also the state an AI system would need before it can act
inside the loop rather than merely emit another candidate.
@sec-design-loop-no-longer-scales develops that breakdown in detail; this chapter asks what a
redesigned loop would have to be.

The quantitative method made architecture arguments measurable at the artifact
level. Architecture 2.0 keeps that discipline but moves it one level up: the
data, feedback, evidence, and rejection processes that produce the artifact
must themselves be represented and designed.

The need for this explicit representation stems from the growing distance between an architectural intent and a
software or hardware artifact that is implemented, tested, and credible enough
to use. AI can shorten parts
of that distance, but only when the work between intent and artifact is
represented as a loop with explicit state, actions, feedback, evidence, and
decision authority. The moonshot is therefore not instant realization. It is a
discipline for making the path to realization inspectable enough that humans
and AI systems can work inside it.

The purpose of this chapter is to make that shift concrete. We build toward a
single concrete design request, not because the request is already solvable, but
because it reveals the hidden architecture state that any credible solution would need.

::: {.callout-learning-objectives}
After this chapter you can turn a compact architecture request into an AI-assisted loop
contract. That means you can:

- explain why "AI for architecture" means designing the AI-assisted design loop, not prompt-to-chip generation;
- explain why cheap plausible artifacts from AI methods move the scarce work toward credible commitment;
- distinguish the familiar human-carried architecture loop from an explicit, represented Architecture 2.0 AI loop;
- decompose a one-line design request into the architecture state a generative model hides;
- treat efficiency as a multidimensional, loop-level property rather than a single metric;
- separate generation, prediction, and optimization as distinct AI method roles in a design loop.
:::

## Ask What AI Can Do for Architecture

The phrase "AI for architecture" can be read in a shallow way: use a model to
generate text, write scripts, summarize papers, or propose configurations. All
of those may be useful, but they are not the core shift. The deeper question is
how the practice of architecture changes when AI systems can participate inside
represented, instrumented, and checked design loops.

That distinction matters because architecture work has always been organized
around loops. Architects frame a problem, choose abstractions, construct models
or simulators, select workloads, explore alternatives, evaluate results,
reject weak candidates, and revise assumptions. For example, an architect
weighing a larger L2 cache frames the question (does it help this workload mix
without hurting energy?), sets up a cycle-level simulator (like gem5) or a full-system register-transfer-level (RTL) emulator (like FireSim), selects a benchmark suite,
sweeps cache sizes, associativities, and replacement policies, reads the
resulting miss rates and energy estimates, rejects the configurations that help
one workload while hurting another, and revises the design before committing it
to RTL. Tools already participate in this loop. Simulators, compilers,
profilers, synthesis tools, spreadsheets, dashboards, and design reviews all
mediate architectural judgment.

AI systems become interesting when they can act inside that loop rather than
around it. They may generate candidates, call tools, summarize evidence,
predict outcomes, search design spaces, critique assumptions, or coordinate
subtasks. But participation is credible only if the loop exposes what the
system can see, what it can change, how feedback is obtained, what evidence is
trusted, and what can reject the result.

This book uses four names carefully. AI systems are participants in the loop,
not the loop itself. Methods play bounded roles such as generation, prediction,
optimization, critique, repair, verification, explanation, or coordination.
Tools become useful architecture environments only when they expose actions,
feedback, costs, and failure modes. Architects still own the intent, evidence
standard, rejection authority, and final commitment.

::: {.callout-architect-checkpoint title="Architect-Owned Commitment"}
AI methods can act within the design loop, proposing and testing candidates, but the human architect acts as the ultimate decision gate, retaining rejection authority and finalizing any commitment.
:::

The term *participant* is often singular in the prose and figures, but it names an
AI-assisted system in the loop. A real implementation may use one generative method, a
pipeline of methods, or several specialized tools; the Architecture 2.0
question is still what each participant may see, change, test, reject, and
return for architect-owned decision.

Those four roles together define a single discipline, Architecture 2.0, whose
central act is synthesizing systems: turning intent into a defensible
computing-system design. That act does not mean only logic synthesis or
high-level synthesis. The short phrase is simple, but the loop is not. To
synthesize a system credibly, the loop must coordinate constraints,
representations, tools, methods, feedback, evidence, and human judgment. The
two terms below fix the discipline and describe the bounded role each method
plays inside the loop.

> **Architecture 2.0.** Architecture 2.0 is the **engineering discipline** of
> building the **design loops** that automatically produce computing systems, so that
> AI-assisted architecture claims can be made **credible, comparable, and
> reviewable**.

> **Method role.** A method role is the bounded job an AI method, model, search
> procedure, or tool wrapper plays inside the loop: generate, predict, optimize,
> critique, repair, verify, explain, or coordinate. The role is credible only
> when the loop defines what the method can read, what it can change, what
> feedback it receives, and what can reject its output.

That a loop can produce a system automatically is the premise of Architecture
2.0, not its achievement. The achievement is a claim another architect can
believe, reject if it is wrong, and trace to whoever owns the commitment, which
is why the rest of the book is about evidence, rejection, and commitment rather
than automation for its own sake.

It helps to place that act on a familiar ladder. The dates are approximate; the
point is the widening unit of intent and the widening artifact produced.

- **1980s--1990s: logic synthesis.** Boolean and RTL intent became gate-level
  structure under libraries, constraints, and timing feedback
  [@DeMicheli1994SynthesisOptimization].
- **1990s--2000s: high-level synthesis.** Algorithmic behavior became RTL
  candidates, with tools taking on more of the microarchitecture search
  [@CoussyMorawiec2008HighLevelSynthesis].
- **2000s--2010s: modern program and domain-specific synthesis.** Building on
  deductive program synthesis from the 1970s, specifications, kernels, and DSL
  intent became code or hardware/software artifacts inside specialized toolchains
  [@GulwaniPolozovSingh2017ProgramSynthesis].
- **Architecture 2.0: computing-system synthesis.** Workload intent,
  architectural constraints, software contracts, tool feedback, evidence, and
  human judgment become a defensible system organization. After this point, this
  book often shortens the phrase to *system synthesis* when the context is
  clear.

The lower rungs are largely automated; the top rung is what Architecture 2.0
has to learn to support.

The architecture design loop is the object this book will make precise. For
now, treat it as the repeated movement from intent to bounded action, feedback,
evidence, rejection, revision, and architect-owned commitment.

The framework should be useful in three concrete situations. First, a
researcher should be able to describe an AI-for-architecture paper by naming its
task, representation, environment, method role, feedback, evidence, and human
decision point. Second, a tool builder should be able to ask whether a harness
records enough state for another method or team to learn from it. Third, an
author or reviewer should be able to ask what would reject the result, not only
what result was produced. Later chapters turn those needs into reusable cards,
ledgers, and review checks.

## From Architecture 1.0 to Architecture 2.0

To see what changes, it helps to name the practice this framework is moving
beyond. Architecture 1.0 is the familiar practice of human-orchestrated artifact
design. The architect defines the problem, chooses models, uses tools,
interprets feedback, and decides what to build. This practice is not obsolete.
It is the foundation on which the field stands.

Architecture 2.0 shifts the emphasis. The architect still owns intent,
constraints, abstraction, evidence standards, rejection, and accountability.
But the architect must now also design the loop around the artifact. The
architect must decide how tasks are represented, which tools become
environments, which method roles are allowed, what feedback budget is
available, what evidence is required, and what can say no.

The difference can be seen in a familiar design-space exploration. In
Architecture 1.0, an architect might manually script a simulator sweep over
cache sizes, associativities, and replacement policies, then inspect the
results. In Architecture 2.0, the architect may design a loop in which a
method proposes candidates, a surrogate[^fn-surrogate-model-c01] estimates outcomes, a simulator
evaluates selected points, a critic flags invalid assumptions, and a human
decides whether the evidence is strong enough. The artifact may still be a
cache hierarchy. The new contribution is the explicit, inspectable, and
rejectable loop that produced it.

@fig-design-loop-breaks makes the shift explicit. The left loop is the familiar
human-carried practice: intent, models, candidates, tool runs, and expert review
are coordinated by architectural judgment. The right loop does not remove that
judgment. It represents enough loop state, action boundaries, evidence,
rejection, and decision authority that bounded AI methods can participate
without becoming an uninspectable prompt-to-chip shortcut.

![**The architecture design loop changes form:** Architecture 2.0 represents loop state, tool interfaces, evidence, rejection, and decision authority rather than leaving them implicit in human-carried practice.](images/F2a-design-loop-breaks){#fig-design-loop-breaks width="100%" fig-alt="Two side-by-side loop diagrams compare an implicit human-carried architecture loop with a represented Architecture 2.0 loop that exposes state, evidence, rejection, and decision authority."}

This need for inspectability is why the subtitle uses the phrase *agentic design loops*, meaning loops
where AI systems can choose bounded actions, call tools, revise state, and use
feedback without owning the commitment. The AI-assisted participant, whether singular or a
coordinated set of role-specific methods, is not the whole system. The governed
loop is the system around the artifact. The automated parts must be embedded in
representations, environments, evidence ledgers, and human decision points.

::: {#pri-design-the-loop .callout-design-principle title="Design the AI-assisted loop, not only the artifact"}
The key move is to design the AI-assisted loop, not only the thing it produces. A single
artifact, a generated design from an AI model, a candidate configuration, or a plausible answer,
is not the contribution. The durable object is the AI loop that exposes state,
action, feedback, rejection, and decision, because that is what another architect
can inspect, compare, reject, and improve before an AI method's output crosses a commitment
boundary.
:::

To see why the loop itself must be designed, work backward from the systems tradition. A useful AI-assisted system should
not merely know how to call a simulator, propose RTL, or summarize papers. It
should carry the habits that make systems engineering credible: suspect the
bottleneck, account for memory movement and physical limits, compare tradeoffs
numerically, preserve provenance, expose failure modes, and ask what evidence is
strong enough for the next commitment. Those habits do not appear automatically
because a model is capable. They have to be designed into the loop.

## The Architecture Moonshot

Before introducing a concrete design prompt, we must fix two terms: *architecture* and *architect*. In
this book, architecture does not mean only microarchitecture, a block diagram,
or a chip artifact.

> **Architecture.** Architecture is the hardware-software contract and system
> organization that turn workload intent and technology constraints into a
> defensible system design. It includes ISA and microarchitecture, memory and
> interconnect, accelerators and chiplets, compiler/runtime interfaces,
> physical-design constraints, verification, deployment, and the evidence used
> to justify choices.

> **Architect.** The architect is the human who owns the intent, frames the
> problem, chooses the abstractions, sets the evidence standard, and retains
> rejection authority and final accountability for the committed design. AI
> methods act inside the loop; the architect owns it.

With those terms fixed, consider the lighthouse prompt itself. We ground the Architecture 2.0 framework in a running prompt sequence.

> **Sandbox Prompt:** Design a matrix multiplication systolic array in Chisel, optimized for INT8 latency, targeting the open-source sky130 PDK.

While a sandbox prompt is excellent for learning to code an agentic loop locally (and we encourage students to start there), evaluating the full scale of Architecture 2.0 requires a moonshot. Our primary running example pushes the limit. It asks for a compute subsystem
serving real-time mobile extended reality (XR), under a thermal-design-power
(TDP) budget in a low-power (LP) mobile process class, and it asks for a report
rather than a chip:

> **Moonshot Prompt:** Design a low-power, 64-bit RISC-V-based compute subsystem for an
> XRBench-class real-time mobile XR workload. Realize it as a vector-capable
> CPU, accelerator, or SoC block under a 3 W TDP target in a 3 nm-class LP
> mobile process, and return a design-space report with evidence and rejected
> alternatives.

Finally, while our examples primarily trace the mobile XR prompt to keep node-level concepts concrete, modern architecture is distributed hardware-software co-design. The most extreme version of our lighthouse prompt scales to the datacenter:

> **Datacenter-Scale Lighthouse Prompt:** Design a scale-out TPU supercomputer topology for training 10T-parameter mixture-of-experts models. Ensure the tensor compiler (XLA/MLIR) can discover an efficient mapping, bound tail latency across 10,000 optical links, and guarantee recovery from synchronous faults.

This sentence is quoted, fragment by fragment, throughout the book, so it is
worth reading once in full. @fig-moonshot-prompt keeps it visible as an object of
analysis. The top panel restates the prompt; the middle panel names the
architectural obligations embedded in that request; and the bottom panel shows
the loop turn that would be needed before an AI system's answer deserved
architectural trust: represent the task, act through bounded tools and methods,
gather evidence, reject weak outputs, decide what to commit, and revise the
next turn. The point is not "type a prompt and get a chip." The point is to
expose what a credible loop would need to know.

![**The lighthouse prompt exposes hidden loop state:** It is useful because it surfaces the loop state, evidence, rejection, and decision authority a credible architecture answer would need.](images/F1-moonshot-stack){#fig-moonshot-prompt width="92%" fig-alt="Stacked diagram with the full lighthouse prompt sentence at the top, decomposed into architecture obligations and the design-loop requirements needed before a result can be trusted."}

> **Lighthouse prompt.** The lighthouse prompt is this compact Architecture 2.0
> design request, used throughout the book: a request for a low-power,
> RISC-V-based mobile XR compute subsystem that must be answered with a
> design-space report carrying evidence and rejected alternatives.

::: {.callout-lighthouse title="Read the prompt as an AI-assisted loop request"}
**Context.** The lighthouse prompt is not a miniature product specification. It
is a compact way to expose the state a credible AI-assisted architecture loop would have to
carry.

**In the Lighthouse prompt.** "64-bit RISC-V-based compute subsystem" sets the
ISA/ABI and software contract the method must respect. "XRBench-class real-time mobile XR workload" sets
the workload scope the AI method must optimize. "vector-capable CPU, accelerator, or SoC block" sets the
compute organization bounds for the method's action space. "3\ W TDP target in a 3\ nm-class LP mobile
process" sets the physical-design envelope that can reject a generated proposal, and "design-space report
with evidence and rejected alternatives" sets the evidence standard the AI loop owes the human architect.
Those fragments force the AI-assisted loop to carry memory, data movement, compiler,
runtime, reliability, and verification state rather than treating the prompt
as a simple hardware generation task.

**Takeaway.** Treat the prompt as a recurring stress test: if a proposed AI-assisted loop
cannot say what it represents, what it may change, what evidence it records,
what it rejects, and who decides, it has not yet answered the prompt.
:::

The prompt is deliberately extreme. No architect, and no model, can turn that
sentence into a verified subsystem today, and that is the point. Pushing the
request past what is currently feasible is a forcing function: it exposes the
hidden architectural state, evidence, and decisions a credible design loop would
have to handle, rather than letting a plausible-sounding answer conceal them.

With that concrete prompt in view, the word *moonshot* can be used precisely.
The term should not mean a prediction that the field can already automate
architecture end to end. X, the Moonshot Factory, frames a moonshot as the
intersection of a huge problem, a radical solution, and a breakthrough
technology that makes the solution plausible enough to pursue
[@XCompanyMoonshotBlueprint]. This book adapts that structure to computer
architecture.

Use the moonshot analogy only to name a loop requirement: a hard target becomes
useful when it defines shared state, instruments, feedback, rejection rules, and
commitment boundaries. Apollo, the Human Genome Project, DARPA's Grand
Challenge, and AlphaFold matter here as examples of targets that created shared
tasks, instruments, datasets, tests, and evidence standards, not as a claim that
architecture should imitate their politics, budgets, or technical domains
[@NASA2008Apollo11; @NHGRI2025HumanGenomeProject; @DARPA2014GrandChallenge; @JumperEtAl2021AlphaFold].

The common pattern is not that a moonshot is
large or fashionable. It is that the target organizes a community around a hard
problem, a different way of working, and an enabling technical shift.

There is a sharper lesson here than the analogy first suggests. Each example
is remembered as a singular achievement: a flag on the Moon, a finished genome,
a solved protein structure. But the durable contribution was rarely the single
result. It was the shared task, the instruments, the methods, and the evidence
standards that turned an exceptional effort into a process others could run.
Architecture 2.0 takes that stance. The goal is not to celebrate one impressive
design that a generative method happens to emit. It is to engineer the design and
discovery process itself, the loop, the representations, the instruments, and
the evidence, so that credible architecture results can be produced, checked,
and reproduced rather than admired as isolated showcases. Computer architecture
has done exactly this before, more than once.

The Mead and Conway VLSI design methodology turned chip design into a
structured, reusable discipline with shared abstractions and design rules
[@MeadConway1980VLSI], and the reduced-instruction-set program
reshaped the hardware/software contract around quantitative evidence
[@PattersonDitzel1980RISC]. Both changed the loop, not just the artifact.
Architecture 2.0 belongs in that lineage: the next shift is in the design loop
itself.

> **Architecture moonshot.** An architecture moonshot is an aspirational target
> at the intersection of three conditions: a grand architecture challenge that
> ordinary ad hoc coordination cannot evaluate credibly enough, a radical
> design-loop target that changes how architectural work is represented and
> evaluated, and an enabling AI/data/tool breakthrough that makes the target
> technically plausible enough to study without pretending it is solved.

@fig-moonshot-venn shows that pattern in the architecture vocabulary used here.
The phrase is deliberately about loop capacity, not about dismissing classical
architecture practice. Classical architecture already has models, measurements,
review, and signoff discipline. The moonshot is to make enough of that loop
explicit, tool-connected, and evidence-bearing that AI methods can participate
without hiding what would reject their output.

![**A moonshot needs three conditions at once:** An architecture moonshot is not just a big challenge, a radical target, or a promising technology. It sits at the intersection of a grand architecture challenge, a design-loop target that changes how work is represented and evaluated, and an enabling AI/data/tool breakthrough that makes the target plausible enough to study.](images/F1c-moonshot-venn){#fig-moonshot-venn width="100%" fig-alt="Three-circle Venn diagram showing an architecture moonshot at the intersection of grand challenge, radical target, and enabling breakthrough."}

This architecture-specific moonshot is worth naming because the pressure is real but the
solution is not yet settled. The grand challenge is that hardware/software
systems now span workloads, software stacks, ISAs, microarchitecture,
accelerators, memory systems, EDA, physical constraints, verification, and
deployment. The radical target is not to automate architects away; it is to
design interoperable loops that represent these choices, call the right tools,
preserve evidence, record failures, and give humans rejection authority across
ISA, microarchitecture, compiler, RTL, physical-design, and deployment
boundaries. The enabling shift is the arrival of AI methods, architecture
datasets, executable environments, and tool interfaces that make pieces of those
loops plausible enough to study. Publicly reported examples already include reinforcement
learning[^fn-reinforcement-learning-c01] systems for physical-design exploration and learned circuit-generation
loops with silicon evidence
[@Synopsys2023DSOai; @RoyEtAl2021PrefixRL]. @sec-loop-patterns-across-stack returns to those examples
as loop-pattern cases. These examples show bounded loop pieces with evidence,
not end-to-end architecture autonomy. The moonshot is not that these pieces
exist; it is assembling them into a family of represented, evidence-bearing
loops that a human can still govern.

Returning to the lighthouse prompt, each fragment sets a specific constraint. XRBench, a benchmark suite for mobile XR workloads, gives the prompt a workload anchor rather than a vague application
label [@KwonEtAl2023XRBench]. Real-time mobile XR stresses latency,
energy, memory movement, model concurrency, sensing, graphics, and deployment
constraints. End-to-end XR systems research has shown how tightly those stages
couple across the full perception-to-display pipeline, which is what makes mobile
XR a demanding architecture target rather than a single kernel to optimize
[@HuzaifaEtAl2021ILLIXR]. A 64-bit RISC-V contract (an open standard instruction set architecture) gives the design an ISA boundary. Vector
capability makes the compute organization concrete but does not decide whether
the realization should be a CPU extension, accelerator, or SoC block. The 3\ W
TDP target and 3\ nm-class LP mobile process assumption
force the prompt into a contemporary technology envelope. The node is
intentionally stated as a class rather than as a named foundry PDK (process design kit); current
mobile SoCs are publicly
described in 3-nanometer-class technology, but a credible architecture loop
must still state which process, libraries, voltage assumptions, and signoff
path it actually uses [@Apple2024A18Pro; @Apple2024M4]. The requested
deliverable is not merely a design. It is a design-space report with evidence
and rejected alternatives.

Another way to read the prompt's requirements is through the familiar foundation-model[^fn-foundation-model-c01] stack. In
the generic version, many kinds of inputs feed a central foundation model, and
many downstream applications fan out on the other side. The architecture
analogy is different. The left side includes workload traces, specifications,
RTL or IP blocks, simulator configurations, process and library assumptions,
verification logs, papers, and prior designs. The middle should not be read as
a single language model or as a current capability claim. It is a placeholder
for a represented design loop connected to tools, constraints, evidence, and
rejection. The right side is not "a chip" as a single output. It includes ISA proposals,
microarchitecture sketches, accelerator or SoC partitioning choices, RTL and
testbench fragments, design-space reports, verification packages, and
deployment decisions.
@fig-foundation-wall-stack should be read in two steps. Panel A
shows the generic foundation-model pattern. Panel B translates each part of the
pattern into architecture: the inputs become design artifacts and evidence, the
middle becomes a represented and tool-connected design loop, and the outputs
become architecture deliverables with different commitment levels.

![**A foundation-model analogy for architecture loops, not a prompt-to-chip shortcut:** The center is a represented design loop tied to architecture artifacts, tools, constraints, evidence, and rejection.](images/F1a-foundation-wall-stack){#fig-foundation-wall-stack width="100%" fig-alt="Two-panel diagram contrasting a generic foundation-model stack with an architecture loop substrate centered on a represented tool-connected design loop."}

Read Panel B as a loop substrate, not as a single model call. For the
lighthouse prompt, one loop turn might ingest an XRBench trace slice and a
software pipeline description, generate vector-width, local-memory, and
CPU/accelerator partition candidates, run a cheap performance and power proxy,
reject candidates that miss the latency or 3\ W envelope, and preserve the
rejected alternatives as evidence for the next turn. A higher-commitment turn
would replace some of that proxy evidence with simulator runs, compiler output,
RTL fragments, or physical-design feedback. The foundation-model analogy is
useful only if it points to that maintained architecture state and evidence
path.

::: {.callout-architect-checkpoint title="Higher-Commitment Decision Gate"}
Before a design loop transitions from proxy evidence to expensive simulator or physical-design feedback, the architect must evaluate the retained evidence and authorize the higher-commitment turn. Automation does not cross this boundary autonomously.
:::

```{=latex}
\FloatBarrier
```

The prompt should be treated as a moonshot, not as a current capability claim.
A present-day generative method may draft a plausible answer. It may produce a list of
architectural choices, cite related ideas, or generate code fragments. That is
not enough. The useful question is what loop would be required before such an
answer deserved architectural trust.
The book uses this prompt as a spine rather than as the only example. Later
chapters zoom into facets of the same request: memory and data movement,
software drift, chiplet partitioning, verification, physical design, and
deployment. Additional examples appear only when a facet needs a more specific
loop.

## Why the Prompt Spans the Stack

The prompt is architectural because each phrase creates obligations beyond the
surface words. A credible loop must track workload behavior, software
contracts, hardware organization, physical feasibility, evidence, and rejection
paths together. @tbl-moonshot-decomposition keeps that
obligation compact. The table is not meant to exhaust every subtask. It is a
reader's checklist for why the prompt crosses boundaries that architecture
cannot ignore.

Read the table as a stack of obligations rather than as a shopping list. The
workload phrase says what behavior the design must serve. The ISA and compute
phrases say what boundary the hardware/software interface must expose. The
power and process phrase says what physical world can reject the idea. The
report phrase says what kind of evidence the loop owes the architect before
the answer deserves trust. Each row therefore names both a design decision and
a way for the loop to be wrong.

| **Prompt fragment** | **Architectural decisions** | **Evidence or rejection need** |
| --- | --- | --- |
| XRBench mobile XR | Workload slice, input distribution, quality-of-service target, latency deadline, memory traffic, software pipeline, and drift assumptions. | Trace provenance, benchmark version, workload coverage, and rejection when results miss real-time behavior. |
| 64-bit RISC-V with vector or accelerator option | ISA boundary, custom extension policy, programming model, compiler/runtime path, library support, and software compatibility. | Correctness, toolchain support, generated-code evidence, portability checks, and rejection of unsupported software semantics. |
| Compute subsystem | CPU, accelerator, tightly coupled unit, SoC block, memory hierarchy, interconnect, chiplet boundary if any, and integration point. | Design-space comparison and rejection of candidates that only win by moving cost, bandwidth, energy, or complexity elsewhere. |
| 3\ W, 3\ nm-class low-power envelope | Power, voltage/frequency, thermal, area, process/library assumptions, RTL feasibility, EDA constraints, and physical signoff path. | Power-model provenance, synthesis or timing feedback, sensitivity analysis, and rejection when stronger physical evidence violates the envelope. |
| Design-space report with evidence and rejected alternatives | Alternatives, Pareto fronts (designs that nothing else beats on every objective at once), assumptions, uncertainty, verification plan, rejected or failed candidates, and human decision points. | Evidence ledger: connected measurements, assumptions, checks, rejections, coverage, reproducible artifacts, and explicit rejection authority before higher commitment. |

: **Prompt fragments create architecture obligations:** The lighthouse prompt maps to decisions about workload definition, software and ISA contracts, hardware organization, physical feasibility, and evidence. {#tbl-moonshot-decomposition tbl-colwidths="[18,34,35]"}

The table gives the first concrete version of a loop contract. It says what
state must be represented, which parts of the design space can be exposed to
methods, what feedback matters, and what can reject a result before commitment.
Later chapters make each field more precise, but the contract begins here.
A weak lighthouse answer can be rejected immediately if it cannot say which
workload slice, software contract, evidence level, and human decision owner
its design claim depends on.
The terms below are signposts for that later precision; the only idea needed
now is simple. A loop should say what it may change (the part of the design
space the architect exposes to methods, narrower than the full space), what
evidence it owes, what can reject it, and who decides.

> **Loop contract.** A loop contract is the explicit agreement a design loop
> makes visible before a method acts: the task, represented state, permitted
> actions, architecture environment, feedback budget, evidence standard,
> rejection authority, and human decision owner.

::: {.callout-engineer-move title="Fill in an AI-assisted loop contract"}
A compact request becomes an AI-assisted loop contract by answering seven questions. For the
lighthouse prompt the answers are the entries in @tbl-moonshot-decomposition; for
a new request, fill them in.

1. **Workload or scenario.** Which workload slice, input distribution, and
   quality-of-service target is the AI-assisted loop actually optimizing?
2. **Interface or software contract.** Which ISA, programming model,
   compiler/runtime path, and compatibility must the method respect?
3. **Legal action space.** Which design choices may the AI method change, and which
   are fixed or deferred to a later turn?
4. **Environment or tool path.** Through which simulator, flow, or harness does
   the AI loop act and observe?
5. **Feedback budget.** How many evaluations, at what cost, latency, and fidelity,
   can the AI method afford?
6. **Evidence and rejection gate.** What evidence does an AI claim owe, and what can
   reject it before human commitment?
7. **Human commitment boundary.** What is the strongest claim the evidence
   licenses, and who owns the final architectural commitment?

A request that cannot answer these is not yet a credible AI-assisted loop; it is a wish, and the architect
can reject it on that basis.
:::

> **Design-loop card.** A design-loop card is a compact review artifact that
> records the intent, task, design space, representation, environment, method
> role, feedback budget, evidence, rejected and failed candidates, rejection
> authority, commitment boundary, and human decision for a loop.

The rest of the vocabulary in the loop contract is a signpost here, not a full definition stack.
Later chapters give sharper treatment to evidence ledgers, feedback budgets,
rejection authority, and commitment boundaries. For now, the point is that those
terms turn the lighthouse prompt from a request for an answer into a reviewable
contract for a loop.

::: {#pri-system-synthesis .callout-design-principle title="Make AI synthesis obligations explicit"}
System synthesis is credible only when the AI-assisted loop exposes the obligations that
make a result reviewable: what state it represents, which actions are bounded,
which environment returns feedback, which AI method role acts, what feedback budget
it spends, what evidence ledger it preserves, and what can reject the claim
before human commitment.
:::

These obligations are the chapter-level preview of the design-loop card,
not a competing schema. Represented state maps to the card's intent, task, and
representation fields; bounded action maps to design space and method role;
architecture environment and feedback budget map directly; evidence ledger
maps to evidence and negative traces; and rejection authority carries the
commitment boundary and human decision fields that keep the loop accountable.

No single model can make these obligations disappear. The table is deliberately
compressed; each row expands into many implementation and evidence questions.
The "3\ W, 3\ nm-class" row, for example, reaches down into RTL, synthesis,
floorplanning, timing, IR drop, leakage, thermal behavior, and signoff. The
"RISC-V with vector or accelerator option" row reaches sideways into compilers,
runtimes, libraries, generated code, and portability. Architecture development
therefore means proposing artifacts, predicting consequences, optimizing under
constraints, and rejecting weak evidence across changing fidelity levels. This
is why the moonshot is a computer architecture problem rather than prompt
engineering: the loop has to carry architectural state across the stack.

## Architecture Development Spans Three Roles

These obligations of the lighthouse prompt also clarify what the word *development* has to cover.
Architecture development is not one AI task. It is a loop in which different
roles produce different kinds of architectural work.

This chapter emphasizes generation, prediction, and optimization because they
are the development roles most easily mistaken for the whole story. Later
chapters add critique, repair, verification, explanation, and coordination as
the checking and governance roles that keep automated participation credible.

Generation proposes objects the architect can inspect: an ISA extension,
microarchitecture sketch, accelerator interface, memory hierarchy option, RTL
fragment, testbench, benchmark harness, or design-space report. Prediction
estimates what those objects would do before every expensive evaluation:
latency, energy, memory traffic, timing risk, compiler support, verification
burden, or deployment behavior. Optimization searches among alternatives:
which cache shape, vector width, dataflow, voltage/frequency policy, chiplet
partition, or compiler schedule best satisfies the objective and constraints.

The lighthouse prompt needs all three. A generator might propose a vector
extension for XR kernels, but prediction has to estimate whether the extension
actually improves latency and energy under the mobile power envelope.
Optimization then has to compare that extension against an accelerator, a
tighter memory hierarchy, or a software/runtime change. None of those steps is
credible without rejection: a compiler may not generate valid code, a power
model may be out of support, a timing check may fail, or a workload slice may
not represent the intended XR behavior.

Those roles overlap, but none is sufficient alone. At the center, systems are
synthesized in a closed loop: generated candidates are predicted, optimized,
checked, rejected, and revised under explicit evidence standards.

@fig-architecture-development-triad visualizes this distinction.
Its purpose is not to introduce three disconnected topics. It shows why an
architecture loop needs all three roles at once: generation without prediction
produces unsupported artifacts, prediction without optimization does not search
the space, and optimization without generation and evidence can overfit[^fn-overfitting-c01] a
proxy. @sec-methods-generation-prediction-optimization returns to the methods in detail; here they establish that
Architecture 2.0 is about the loop among these roles, not only about producing
candidate designs.

![**Architecture development is broader than generation:** Generation proposes artifacts and candidates, prediction estimates behavior and risk, and optimization searches tradeoffs under constraints. Architecture 2.0 is concerned with the closed loop in the middle, governed by evidence, rejection, and human architectural judgment.](images/F1b-architecture-development-triad){#fig-architecture-development-triad width="100%" fig-alt="Three-circle diagram showing generation, prediction, and optimization overlapping around closed-loop architectural synthesis governed by evidence and rejection."}

The figure shifts the reader from a list of AI capabilities to a loop contract:
each method role is useful only when its output is checked by the other roles
and by evidence strong enough for the next commitment boundary.

```{=latex}
\FloatBarrier
```

## Efficiency Claims Need Rejectable Loops

Naming the roles inside the loop does not yet say what the loop is optimizing
for. Architecture still cares about efficiency: the discipline turns scarce
resources into useful work through durable hardware/software interfaces. But the
loop optimizes for credible efficiency claims, not raw artifact output. A design
that is faster but consumes too much power, is impossible to verify, or depends
on fragile software assumptions has not really solved the architectural problem.
If Architecture 2.0 only made architects produce more artifacts, it would not be
enough. The goal is to produce better, more credible, and more efficient systems
under rising complexity.

The hard shift is not from performance to a single new metric called power. It
is that efficiency itself is becoming more multidimensional. Classical computer
architecture made performance quantitative, but it also treated cost and power
as first-class constraints
[@HennessyPatterson2017QuantitativeApproach]. Dennard-style scaling once
made it easier to improve performance while keeping power density manageable
[@DennardEtAl1974Scaling]. As that story weakened, dark silicon and the limits
of multicore scaling pushed the field toward specialization
[@BorkarChien2011FutureMicroprocessors; @EsmaeilzadehEtAl2011DarkSilicon; @HennessyPatterson2019GoldenAge].
Data-movement energy made arithmetic alone an insufficient efficiency story
[@Horowitz2014Energy]. Warehouse-scale operation expanded the boundary to
power delivery, utilization, networking, operations, and total cost of
ownership [@BarrosoHolzleRanganathan2019DatacenterAsComputer].
Sustainability adds another layer because carbon depends on operational
energy, hardware manufacturing and infrastructure, utilization, geography, and
lifetime
[@GuptaEtAl2021ChasingCarbon].
For an AI-assisted architecture loop, each efficiency dimension becomes represented
state, an evidence requirement, and a possible rejection condition.

Given this multidimensional efficiency, the question is not whether traditional architecture methods suddenly stop
working. Many still work extremely well when the workload, abstraction,
feedback path, and commitment level are bounded. The harder question is where
the classical loop becomes too slow, too implicit, or too expensive to manage
the coupled objectives. Architecture 2.0 should be understood as a way to make
that boundary explicit: which parts can still be handled by familiar models,
scripts, simulation, and expert review, and which parts need more explicit
state, tool feedback, evidence ledger entries, rejected alternatives, or AI-assisted
search.

To make these boundaries explicit, a credible loop must also record what failed as well as what worked, not only the
winners. That record keeps later methods, reviewers, and architects from
re-exploring ground the loop already ruled out. Later chapters give it a
sharper name and make it part of the evidence ledger.

Modern benchmark suites show this same pressure toward multidimensional efficiency. MLPerf, the community benchmark effort for
making machine-learning performance claims reproducible across systems, treats
deployment scenario, latency, throughput, accuracy, and power as part of the
comparison rather than as one scalar claim [@MattsonEtAl2020MLPerf].
@sec-design-loop-no-longer-scales develops that case with the numbers; the
architectural lesson here is that efficiency is not one number. It is a
structured claim about useful work under constraints. Useful work must be
evaluated against the relevant scarce resource: latency, throughput, energy,
power, area, dollar cost, carbon, reliability, verification effort, engineering
time, or risk.

A compact way to write the point is that every efficiency claim has a design,
workload, scenario, and resource denominator:

$$
\mathrm{Eff}_r(d,w,s) =
\frac{\mathrm{UsefulWork}(d,w,s)}{\mathrm{Resource}_r(d,w,s)}.
$$

Here, $d$ is the design, $w$ is the workload, $s$ is the deployment or
evaluation scenario, and $r$ may be time, energy, power, area, dollar cost,
carbon, validation effort, or another scarce resource. In an AI-assisted design
loop, $d$, $w$, $s$, and $r$ are represented state, not only notation: changing
any one changes what evidence can support the claim and what should reject it.
The equation is simple on purpose. It prevents the loop from treating a faster design as efficient if
the useful work, scenario, or resource denominator has quietly changed, and
because the denominator is stated openly, it also lets a second architect
compare two competing designs on equal footing rather than trusting whichever
number looks larger.

@tbl-efficiency-dimensions summarizes the dimensions that this chapter
will treat as part of efficiency. The rows are not separate goals to optimize
independently. They are coupled obligations that a design loop must represent
and test.

| **Dimension** | **Efficiency question** | **Why it complicates the loop** |
| --- | --- | --- |
| Performance | How much useful work is delivered per unit time, latency budget, or service-level target? | The answer depends on workload selection, scenario, software stack, and whether the measured behavior matches the deployment claim. |
| Power and energy | How much useful work is delivered per watt, joule, thermal budget, or battery envelope? | The loop must model activity, data movement, voltage/frequency choices, thermal constraints, and fidelity gaps between estimates and signoff. |
| Reliability and correctness | How much useful work survives faults, corner cases, nondeterminism, and validation? | A faster candidate is not efficient if it spends its savings on fragility, debug burden, or invalid software and hardware assumptions. |
| Scalability and cost | How much useful work is delivered per dollar, rack, network hop, operator action, or unit of capacity? | Local wins can shift cost to memory, network, power delivery, utilization, operations, or total cost of ownership. |
| Sustainability | How much useful work is delivered per unit of operational and embodied environmental footprint? | Carbon depends on hardware lifetime, manufacturing, energy mix, utilization, and where and when computation runs. |
| Evidence and engineering effort | How much credible evidence is obtained per simulation, experiment, verification run, or engineer-hour? | A loop that generates more candidates can still be inefficient if it consumes scarce feedback, hides failures, or produces evidence that cannot reject outputs. |

: **Efficiency is becoming multidimensional:** Performance, power, reliability, scalability, sustainability, and evidence cost are increasingly coupled. The architecture question is which parts traditional loops can still handle and which parts need more explicit state, feedback, and rejection. {#tbl-efficiency-dimensions tbl-colwidths="[22,32,34]"}

The word efficient should therefore be read broadly. A candidate that improves
simulated performance while increasing verification burden may not be
efficient. A candidate that reduces energy but requires fragile software
assumptions may not be efficient. A candidate that looks good under a proxy
metric but fails under a more faithful workload may not be efficient.
Architecture 2.0 should treat efficiency as a loop property, not only an
artifact property.

The lighthouse prompt makes this concrete. The requested subsystem must
support a workload class, meet a power envelope, fit a technology assumption,
interact with software, and produce evidence. The design loop must reason about
tradeoffs among energy, latency, memory traffic, programmability,
verification, and deployment risk. A single scalar objective may be useful
inside the loop, but it cannot be the whole architectural judgment.

## Boundaries of the Argument

Having set credible efficiency claims as the loop-level target, it is worth
being equally clear about what this book is not trying to do. The goal is not to
produce a paper
catalog. The field is moving too quickly
for a catalog to remain useful for long. The goal is to give readers a
framework that can organize current work and still be useful as models, tools,
and benchmarks change.

Nor is the goal to make a product forecast. The book does not claim that a
particular model, tool harness, simulator, EDA flow, or benchmark will define
the field. Those will evolve. The durable question is what must be represented,
measured, checked, rejected, and decided.

Nor is this a tool manual. Tools matter deeply, but the focus is the
architecture of the design loop rather than installation instructions or
process recipes. @sec-appendix-a-bootstrapping gives a compact bootstrap
path. @sec-appendix-b-design-loop-card gives the design-loop card and rubric.

It is also not a claim that AI systems replace architects. The opposite is
closer to the book's argument. As design loops become more automated, the
architect's responsibility moves upward. The architect must frame the task,
choose representations, define environments, set evidence standards, inspect
rejected and failed candidates, maintain rejection authority, and own the final
commitment. @sec-data-representations-world-models gives those records a
sharper name and shows why they matter as loop state.

::: {.callout-failure-mode title="What not to claim"}
Architecture 2.0 should not be read as push-button chip design, replacement of
architects, or a claim that today's generative methods define the field. The defensible
claim is narrower and stronger: architecture can move toward synthesizing
systems under governance when design loops expose state, actions, feedback,
evidence, rejection authority, and architect-owned commitment.
:::

The rest of the book follows the loop exposed by the moonshot. @sec-design-loop-no-longer-scales
explains why the classical architecture loop strains as specialization,
chiplets, software velocity, data movement, EDA constraints, reliability
expectations, sustainability pressure, and verification burden grow together.
@sec-architecture-20-ontology names the ontology of the new loop.
@sec-data-representations-world-models asks what architecture data must
represent, including the world models[^fn-world-model-c01] introduced by the ontology.
@sec-architecture-environments-tool-interfaces
turns tools into environments with actions, observations, feedback, and
constraints. @sec-methods-generation-prediction-optimization separates
generation, prediction, optimization, critique, and repair as method roles.
@sec-feedback-verification-trust defines feedback, verification, and trust.
@sec-running-the-loop runs one loop end to end on the lighthouse prompt.
@sec-loop-patterns-across-stack compares loop patterns across the stack.
@sec-what-architect-owns returns to what the architect owns, then turns the
framework into long-horizon challenge tasks and a research agenda. The
appendices then equip the reader: a bootstrap path for a first loop, the
design-loop card and review rubric, and a loop-role resource catalog with
living links.

## Open research questions

These open research questions represent unsettled, forward-looking directions that push the boundaries of current architecture research. Carry them as conceptual challenges to consider as subsequent chapters formalize the design loop.

1. **How do we ensure reproducibility across non-deterministic AI methods?**
   Building on the "loop contract" defined in the *Why the Prompt Spans the Stack* section, we must figure out how an architectural claim remains reviewable and defensible even when the underlying generative methods are inherently stochastic or frequently updated.

2. **What constitutes an adversarial stress-test for an AI-assisted design loop?**
   While the *Efficiency Claims Need Rejectable Loops* section argues for making efficiency multidimensional, it is unknown how to systematically design "red-team" workloads and constraints specifically engineered to trick an AI method into proposing plausible but fatally flawed hardware.

3. **How do we standardize the cost of evidence?**
   The *Architecture Development Spans Three Roles* section outlines generation, prediction, and optimization, but we lack a standardized currency for the "feedback budget." We need to establish how to rigorously quantify and trade off the computational and financial costs of querying large models versus running cycle-accurate simulators.

4. **How can failure taxonomies become shared infrastructure?**
   The *From Architecture 1.0 to Architecture 2.0* section emphasizes designing explicit loops with rejection authority, yet we lack a universal taxonomy for *why* an AI-generated candidate was rejected. Structuring and sharing these negative traces across the community is essential to prevent different AI-assisted systems from independently repeating the same architectural mistakes.

## What to carry forward
- **Reader test:** For any AI architecture result, can you say what state was
  represented, what method role acted, what evidence was preserved, what could
  reject it, and where the commitment boundary stays human-owned?
- **Next loop state:** Cheap generation makes that reading habit matter more, not
  less; the next chapter turns it into a pressure test by asking why the classical
  loop no longer scales.

[^fn-surrogate-model-c01]: **Surrogate model**: A data-driven approximation used to quickly estimate the results of a computationally expensive simulator.
[^fn-reinforcement-learning-c01]: **Reinforcement learning**: A machine learning method in which an agent learns to choose actions that maximize a cumulative reward signal from its environment, often used to navigate complex design spaces [@SuttonBarto2018ReinforcementLearning].
[^fn-foundation-model-c01]: **Foundation model**: A large-scale AI model trained on a vast quantity of data that can be adapted to a wide range of downstream tasks.
[^fn-overfitting-c01]: **Overfitting**: In machine learning, fitting the noise and idiosyncrasies of a training sample so that performance fails to generalize to new data. An optimizer can *overfit a proxy* in the same way, raising the proxy's measured score by exploiting its quirks rather than improving the true objective.
[^fn-world-model-c01]: **World model**: A predictive model of an environment used to anticipate the consequences of actions. The seminal sense is a *learned* latent model [@HaSchmidhuber2018WorldModels]; this book uses the term more broadly, covering simulators, surrogates, cost models, and design rules that encode what the loop expects to happen.
# Why Classical Architecture Loops Strain {#sec-design-loop-no-longer-scales}

```{=latex}
\abstract*{Architecture 2.0 is motivated by pressure inside computer architecture, not by enthusiasm for AI. The classical architecture loop remains valuable, but it strains when specialization, heterogeneous integration, software velocity, memory movement, physical constraints, and verification burden grow together. The central bottleneck is not idea generation. It is trusted feedback: the ability to evaluate, reject, revise, and commit design choices at the speed and fidelity the problem now requires. That bottleneck makes AI-assisted architecture a loop-design problem because generative models can increase proposal volume faster than they increase trusted rejection capacity.}
```

::: {.callout-crux}
When architecture choices grow faster than trusted feedback, what must the loop
record so AI helps rather than just adding more candidates?
:::

@sec-moonshot named Architecture 2.0 as a discipline for designing the design loop
itself. It then made the claim concrete with a compact lighthouse prompt:
design a low-power, RISC-V-based compute subsystem for real-time mobile XR
under a 3\ W, 3\ nm-class mobile envelope, and return a design-space
report with evidence and rejected alternatives. The prompt is intentionally
small. The architecture state it implies is not.

This chapter explains why that state cannot be handled by merely asking a
larger model to produce a larger answer. Computer architects already use
models, simulators, benchmarks, profilers, spreadsheets, compilers, RTL flows,
EDA tools, and expert reviews. The problem is not the absence of tools. The
problem is that the design loop that coordinates those tools is under pressure.
The space to search, the constraints to satisfy, and the evidence required to
trust a result now grow faster than manual coordination, review, and
verification capacity.

The claim is not that the old loop is obsolete. It is that the old loop must
become a first-class object of design alongside the artifact it produces.

> **Scissors gap.** The scissors gap is the widening gap between the rate at
> which design choices, constraints, and evidence demands expand and the rate at
> which a team can obtain trusted feedback, reject weak candidates, and commit
> responsibly.

The gap opens when the number of plausible actions, constraints, feedback
sources, and evidence requirements grows faster than the loop's ability to
evaluate, reject, revise, and commit architecture candidates credibly. That is
the visible failure mode. Trusted feedback cannot keep up with the choices and
evidence demands the loop has created.
For automation, the scissors gap sets the safe operating boundary. The loop can
delegate only as much search, prediction, and synthesis as it can review and
reject.

::: {.callout-architect-checkpoint title="The Delegation Gate"}
An automated method can only be delegated tasks where the loop has explicit, trusted rejection checks. If you cannot reject a bad candidate, you cannot safely delegate its generation.
:::

The practical diagnostic is therefore not "where can we add a model?" It is
"which part of the loop cannot keep up?" A loop may be representation-bound,
action-bound, feedback-bound, rejection-bound, or commitment-bound. Each names a
different part of the loop that saturates first, and each shows a different
symptom, needs a different record to confirm, and calls for a different first fix
(@tbl-loop-bottleneck-diagnostic).

| **Bound** | **Symptom** | **Lighthouse example** | **Record to inspect** | **First fix** |
| --- | --- | --- | --- | --- |
| Representation-bound | The loop cannot encode the state that decides the outcome, so it proposes candidates the environment later rejects. | It ranks XR compute organizations without representing memory-movement cost, so a later estimate overturns the proxy order. | The state schema: which fields the loop can read and write. | Add the missing fields (workload, interface, memory-traffic) to the representation. |
| Action-bound | The legal action set is too narrow, or too loose, to reach the candidate that would clear the gates. | The loop can retune parameters but cannot change the accelerator interface, so it never reaches the organization that would meet both the real-time deadline and the power envelope. | The action schema: which moves are legal, and recorded. | Widen or tighten the legal action set and record it in the loop contract. |
| Feedback-bound | Trusted feedback is too scarce or too expensive to keep up with the candidates generated. | Only a few simulation-stage estimates are affordable, so most candidates are dropped or committed unjudged. | The feedback budget and each check's cost and fidelity. | Add cheaper proxies and a ladder of feedback fidelities so scarce feedback is spent where it changes a decision. |
| Rejection-bound | The loop generates faster than it can reject, so weak candidates survive to expensive stages. | Lacking a gate, an accelerator that leads a cheap proxy ranking is not rejected until an expensive check exposes its data-movement cost. | The rejection gates and the negative-trace log. | Add explicit gates and record every rejection with its reason. |
| Commitment-bound | The loop cannot say what evidence licenses which commitment, so it over- or under-commits. | A candidate clears both gates, but nothing states whether that authorizes more exploration or an implementation commitment. | The commitment boundary and the evidence level attached to it. | Set a commitment level the current evidence supports, and name what would raise it. |

: **A diagnostic for which part of the loop cannot keep up:** each bound shows a different symptom, needs a different record to confirm, and has a different first fix. {#tbl-loop-bottleneck-diagnostic tbl-colwidths="[15,25,26,16,18]"}

@sec-the-rejection-bound turns the rejection bound into a quantitative limit,
but the pressure starts here. A loop that can generate faster than it can
reject only widens the gap.

Because this failure mode is the central problem, the remainder of this chapter is not a general technology-trend survey. Specialization,
chiplets, software velocity, memory movement, EDA, physical design, and
verification matter here specifically because they create that common failure mode. The
architecture team can imagine more candidates than it can evaluate, reject,
and justify. Architecture 2.0 begins by making that failure mode explicit.

Read each section as a pressure test on one part of the loop. Cadence exposes
gates and commitment policy. Architecture levers expand the state the loop must
carry. Specialization and chiplets (multiple smaller dies integrated in one package) multiply actions. Software drift changes
the workload contract. Physical constraints create early rejection conditions.
Engineering cost makes feedback scarce. Generic AI assumptions fail because
architecture work is not a cheap-label pipeline. Together, those pressures
explain why the loop becomes a first-class architectural object alongside the
artifact.

::: {.callout-learning-objectives}
After this chapter you can use the scissors gap to audit whether an
AI-assisted architecture loop has enough trusted feedback to reject and commit
responsibly. That means you can:

- recognize the scissors gap between choices and trusted feedback in a real architecture setting;
- explain why the bottleneck is trusted feedback, not idea generation;
- diagnose whether a loop is limited by representation, action validity, feedback, rejection, or commitment;
- point to the design and verification costs that make high-fidelity feedback scarce;
- connect each pressure source to loop state that can no longer remain implicit;
- identify where generic AI assumptions break at architecture boundaries;
- distinguish bounded AI roles from architect-owned commitment decisions.
:::

## Classical Loops Already Use Feedback

Computer architecture has always been a loop. A typical loop begins with an
intent: improve latency, reduce energy, raise throughput, support a workload,
or fit a system into a power and cost envelope. The architect then chooses an
abstraction, builds or selects a model, runs an analysis or simulation, studies
the result, revises the design, and repeats. Eventually the work crosses into
implementation, validation, verification, and signoff. That basic pattern is
visible in textbook architecture practice and in industrial design loops
[@HennessyPatterson2017QuantitativeApproach].

A traditional SPEC CPU-style study makes the loop concrete. An architect might
choose a subset of SPEC CPU workloads, propose a cache hierarchy or branch
predictor change, run a simulator or performance model, inspect IPC, miss
rates, branch-misprediction rates, area and power proxies, reject candidates
that help one workload while hurting others, and repeat. Human judgment enters
repeatedly: selecting workloads, deciding which proxy is credible, noticing
unexpected behavior, choosing when a candidate is worth deeper analysis, and
deciding which risk to accept. SPEC CPU 2017, for example, was designed as an
industry-standardized suite for compute-intensive performance, stressing
processor, memory subsystem, and compiler behavior
[@SPEC2017CPU]. The important point is not the specific suite version. It is
the loop discipline: a bounded workload set, an explicit model, comparable
metrics, rejection of weak candidates, and expert judgment about whether the
evidence is strong enough.

@sec-moonshot made the Architecture 1.0 to Architecture 2.0 loop shift visible in
@fig-design-loop-breaks. The point here is why that shift becomes necessary.
Classical architecture loops already have intent, models, candidates, tool runs,
and expert review. They strain when the state, action boundaries, evidence,
rejection, and decision authority become too large to remain mostly implicit.

For the lighthouse prompt, the difference is not that Architecture 2.0 invents
review discipline. The difference is what the loop must record before a result
can be trusted. @tbl-classical-vs-arch2-review summarizes that delta.

| **Classical review might record** | **Architecture 2.0 additionally requires** |
| --- | --- |
| Candidate design and measured result. | The represented task, workload slice, assumptions, and candidate provenance. |
| Tool output or benchmark score. | Tool version, feedback fidelity, uncertainty, cost, and what the feedback is allowed to reject. |
| Expert judgment about whether the result looks plausible. | Explicit rejection authority, failed or rejected candidates, and the commitment level the evidence supports. |

: **Architecture 2.0 makes review state inspectable:** Disciplined architects already review results. The new requirement is that the loop records the state, feedback, rejection, and commitment information needed for bounded methods to participate without hiding the architectural judgment. {#tbl-classical-vs-arch2-review tbl-colwidths="[40,50]"}

This loop is powerful because it does not require perfect automation. It
combines formal models, approximations, domain knowledge, and review. It also
rests on an unstated balance: the number of choices, the cost of evaluation, and
the evidence needed to make progress must remain within the capacity of the
team and tools. When that balance holds, the loop works. When it
breaks, the team may still generate ideas, but it cannot evaluate and reject
them fast enough to make credible progress. The loop contract of @sec-moonshot
is that balance written down and made visible.

## Cadence and Gates Manage Risk

One way industrial practice has long held that contract together is by treating
cadence itself as a loop policy. It limits which action class may change at a
commitment boundary and defines the evidence needed to advance. Intel's
tick-tock model is the cleanest familiar example. A "tick" moved a
known microarchitecture to a new process technology; a "tock" introduced a new
microarchitecture on a more mature process. The point was not that product
development was literally two steps. The point was risk isolation. Avoid
changing every hard thing at once, preserve a cadence, and let evidence from
one step inform the next. When node transitions lengthened, Intel described a
move toward process-architecture-optimization, explicitly using longer-lived
14\ nm and 10\ nm process technologies while further optimizing products and
processes to maintain product cadence [@Intel2015Form10K].

That history is useful for Architecture 2.0 because it shows that a design
loop is not only a sequence of tools. It is also a policy for what is allowed
to change, which evidence is strong enough to advance commitment, and how the
organization reacts when feedback latency changes. Tick-tock separated process
risk from microarchitecture risk. Process-architecture-optimization added an
explicit optimization phase when process shrinks no longer arrived on the old
schedule. Instead of every generation requiring both a new process step and a
new architecture step, the loop could spend another cycle improving products,
libraries, physical implementation, frequency, power, and yield on a known
process. In other words, the cadence changed because the feedback and
commitment costs of the physical process changed.
Architecture 2.0 generalizes the same lesson. If AI methods increase the rate
at which candidates are proposed, the loop must become stricter about change
scope, evidence gates, rejection authority, and what kind of optimization is
being performed.

Adjacent systems practices offer compatible lessons. EDA timing closure shows
that a late tool can reject an early abstraction. The source-backed examples
later in this chapter make the pattern concrete. Autotuning[^fn-autotuning-c02] treats measurements
as samples from a costly space, and benchmark governance depends on maintained
rules and comparability contracts. A loop without observability, a decision
policy, and escalation gates is not a credible loop. These analogies should
not displace computer architecture. They help name the reusable loop properties
architects already care about: cadence, state, feedback, gates, rejection, and
commitment.

This is not the first time architecture has had to redesign its loop. Read the
historical rows as examples of explicit action schemas, environment access,
workload records, and rejection gates, not as a history survey. Each row names
one kind of state, rule, or rejection path that would have to be exposed before
an automated loop could help without weakening the evidence standard. The
point is not nostalgia. The point is that many ideas that once looked
unmanageable became tractable only after the field made some part of the loop
explicit: the interface, the rules, the workload, the tool contract, the
evidence gate, or the software path.

| **Shift** | **What the loop made explicit** | **Architecture 2.0 lesson** |
| --- | --- | --- |
| System/360 compatibility | A stable ISA contract separated architecture from implementation across a product family [@AmdahlBlaauwBrooks1964System360]. | Architecture is a durable interface and commitment policy, not only a circuit or microarchitecture. |
| Mead--Conway VLSI and MOSIS | Design rules, layout abstractions, and fabrication access turned custom-chip design into a shareable and reusable loop [@MeadConway1980VLSI; @USCISI2025MOSISFirstYear]. | Representation and access to feedback can change who can participate in architecture work. |
| RISC | Workload, compiler, VLSI, and implementation-cost assumptions became part of the architectural argument [@PattersonDitzel1980RISC]. | Evidence can reject attractive complexity when the full loop cost is visible. |
| SPEC-style benchmarking | Workload selection, run rules, reporting conventions, and comparability became community infrastructure [@SPEC2017CPU]. | Benchmarks are loop governance, not just input programs. |
| Logic synthesis and timing closure | HDL, libraries, constraints, and timing reports gave downstream tools authority to reject upstream choices [@DeMicheli1994SynthesisOptimization]. | Implementation feedback belongs in the architecture loop before commitment. |
| CUDA-style GPU programming | Kernels, thread hierarchies, memory spaces, libraries, and toolchains made specialized hardware programmable [@NickollsEtAl2008CUDA]. | Specialized hardware succeeds only when the software loop is designed with it. |

: **Architecture progress often comes from redesigning the loop:** Historical shifts became durable when they exposed a representation, interface, tool path, benchmark, or evidence gate that let the community coordinate work. {#tbl-historical-loop-transformations tbl-colwidths="[22,39,28]"}

These examples should make the Architecture 2.0 claim less exotic. The field
has repeatedly advanced by turning tacit craft into explicit loop structure.
The new challenge is that AI methods can propose, search, summarize, and
optimize at a scale that makes the loop state itself the bottleneck.

## Architecture Levers Add State

That loop state did not appear all at once. It accumulated as architecture
advanced by adding levers. For decades, technology scaling made
the same basic design style better by providing smaller, faster, cheaper, and
more energy-efficient transistors. Dennard scaling gave architects a favorable
energy story as devices shrank [@DennardEtAl1974Scaling]. As that story
weakened, the field leaned harder on microarchitecture, instruction-level
parallelism, caches, speculation, vector units, multicore, accelerators,
specialization, and system-level optimization. The result is not a simple
failure narrative. It is an accumulation of levers.

The accumulation matters because each lever creates both opportunity and
obligation. Better microarchitecture adds policies and corner cases. Multicore adds
coherence, synchronization, memory ordering, and workload partitioning.
Specialization improves efficiency when the workload and software stack are
understood, but it adds interfaces, data movement, programmability, and
verification burden. Chiplets and heterogeneous integration promise modularity
and scaling beyond a monolithic die, but they add partitioning, die-to-die
interfaces, package-level constraints, test, yield, thermal coupling, and
supply-chain questions.

@fig-architecture-levers summarizes the first part of the point. The field
keeps adding levers because efficiency still matters. But the same moves that
recover efficiency also increase the burden of representing the design state
and producing trusted feedback.

![**Architecture levers add state:** Scaling, microarchitecture, optimization, specialization, and composition create new opportunities for efficiency, but each also adds constraints, interfaces, tool feedback, rejected alternatives, and evidence that the loop must carry.](images/F2-architecture-levers){#fig-architecture-levers width="100%" fig-alt="Horizontal chain of architecture levers from scaling through composition, showing that each efficiency lever adds new loop state and evidence obligations."}

While @fig-architecture-levers illustrates a broad accumulation of design levers, the end of Dennard-style scaling and the limits of multicore scaling specifically explain why specialization became
so central [@BorkarChien2011FutureMicroprocessors; @EsmaeilzadehEtAl2011DarkSilicon].
Hennessy and Patterson's Turing Award lecture framed this moment as a new
golden age for architecture, driven by domain-specific hardware/software
co-design, open architectures, and agile hardware development
[@HennessyPatterson2019GoldenAge]. Architecture 2.0 should be read in that
lineage, but with an explicit connection to the RISC revolution that preceded it. RISC was not just a simplified instruction set; it was the realization that making an architectural claim required a compiler, a benchmark, and a simulator. Architecture 1.0 gave us the tools to measure IPC and power, anchoring the field to the Iron Law of Performance ($\text{Time} = \frac{\text{Instructions}}{\text{Program}} \times \frac{\text{Cycles}}{\text{Instruction}} \times \frac{\text{Time}}{\text{Cycle}}$). 

Architecture 2.0 does not break the Iron Law; it leverages the AI loop as an active co-designer to negotiate across the hardware-software boundary (compiler, ISA, microarchitecture), much like the early RISC teams did. The "rejection authority" in an AI-assisted loop enforces the Iron Law at scale. Architecture 2.0 is the quantitative method applied to the *process of design discovery* itself, aiming to produce interpretable insights—like Pareto curves and bottleneck analyses—not just parameter sweeps. Furthermore, just as RISC required compilers to succeed, Architecture 2.0 requires Agile Hardware (parameterized generators, hardware construction languages) as its native enabling substrate to safely manipulate design intent.
quantitative method from comparing candidate artifacts to designing the data,
feedback, and evidence loops that make a larger, more coupled design space
tractable. In that sense, the loop becomes a first-class architecture object:
something to represent, instrument, test, reject, and improve.

That is the architectural consequence for Architecture 2.0. The new golden age
gives the field more architectural levers; Architecture 2.0 asks how to govern
the loop that uses them. Without that layer, AI assistance can only make the
design space larger. With it, AI methods can be assigned bounded roles in
search, evidence, rejection, and revision.

## Specialization and Chiplets Expand Search

Specialization is attractive because efficiency claims are multidimensional, the
point @sec-moonshot made explicit. The binding constraint differs across scales,
from a battery- and thermally-limited mobile part to a warehouse-scale system
bounded by power delivery and total cost of ownership (TCO)
[@BarrosoHolzleRanganathan2019DatacenterAsComputer]. What this chapter adds is
the consequence for the loop. Specialization does not just change which metric
matters, it multiplies the decisions the loop must evaluate.

Specialization increases the number of architectural decisions because the
architect must decide what to specialize, where to specialize it, and how it
communicates with the rest of the system. A low-power XR subsystem is not just
a choice between CPU and accelerator. It raises questions about vector length,
memory hierarchy, local buffers, compression, dataflow, quantization, runtime
scheduling, compiler support, sensor streams, display deadlines, thermal
behavior, and fallback modes.

Chiplets compound the effect. They make it possible to compose systems from
multiple dies and to mix process technologies, IP blocks, and memory
technologies. But a chiplet system is not simply a bigger board-level system
inside a package. The package changes latency, bandwidth, energy, thermal
coupling, test, repair, physical constraints, and business boundaries. Open
standards such as UCIe aim to make die-to-die integration more composable by
standardizing interface layers, protocols, software models, and compliance
expectations [@UCIeConsortium2026Spec]. That standardization is valuable,
but it also makes the architecture question more explicit: what should be
partitioned, through which interface, under which evidence standard?

The combinatorics are easy to understate. The following arithmetic is
illustrative, not a measurement. Suppose a team is exploring only a narrow slice
of the lighthouse prompt: an accelerator and memory subsystem for one
XRBench-class workload family. Even if it considers five compute
organizations, four vector or accelerator interface choices, six memory
hierarchy choices, four interconnect choices, three voltage/frequency
policies, three compiler/runtime policies, and three verification or fidelity
levels, the crude product is already:

```{python}
#| echo: false
toy_design_loop_states = 5 * 4 * 6 * 4 * 3 * 3 * 3
```

$$
5 \times 4 \times 6 \times 4 \times 3 \times 3 \times 3
$$
That is `{python} f"{toy_design_loop_states:,}"` candidate loop states before workload versions, process corners, thermal
constraints, reliability cases, and rejected configurations are counted. This
number is intentionally conservative. More realistic architecture-adjacent
loops quickly become much larger, or much slower, even before final silicon
evidence is involved.

The product is also not just a counting problem. If each surviving state needs
even a cheap analytical model, a simulator run, a synthesis check, or a human
review, the loop is immediately limited by feedback cost and fidelity. Cheap
models are essential, but they move the architecture problem rather than
removing it. The loop must know when a proxy is good enough, when uncertainty is
too wide, and when to escalate to stronger evidence. @sec-data-representations-world-models turns that
intuition into sample-cost and simulation-time representations,
@sec-architecture-environments-tool-interfaces separates feedback regimes by
latency, fidelity, and rejection authority, and
@sec-methods-generation-prediction-optimization returns to this same count in an evidence-gap plot that compares
candidate scale with affordable high-fidelity samples.

In the Lighthouse slice, the same count is not search-space trivia. The
CPU/accelerator/SoC choice also fixes interfaces, memory paths,
compiler/runtime assumptions, physical constraints, and an evidence schedule:
which states get cheap proxies, which get simulation, which escalate, and which
rejected regions are preserved.

::: {.callout-engineer-move title="Triage a design-space slice before you simulate it"}
1. **Situation.** A 12,960-state slice of the design space faces a fixed simulator-hour budget; not every state can be evaluated at full fidelity.
2. **Architecture decision.** Which states get a cheap proxy, which get a cycle-level simulation, which escalate to stronger tools, and which regions to reject outright.
3. **Bound the loop.** Fix the slice, the per-week simulator budget, and the metrics that decide the question (latency, energy, power).
4. **Method role.** Use the AI system as a *searcher and predictor*: rank states by a cheap proxy and propose the next most informative simulation. It proposes; it does not decide.
5. **Evidence path and escalation.** Proxy-rank all states, simulate only the top candidates with logged provenance, and escalate to synthesis only after a candidate survives the cycle-level check.
6. **Negative trace.** Record rejected regions with their reason (infeasible power, dominated latency) so the loop does not re-explore the same dead ends.
7. **Architect signs off.** A human approves which surviving candidate has evidence strong enough for the next commitment, and owns the schedule risk if the proxy mis-ranked.
:::

Beyond the lighthouse example, @tbl-design-loop-scale-anchors grounds this combinatorial pressure in other concrete architecture
settings. The examples are not meant to be a single measurement scale; they show
that mapping, design-space exploration (DSE), physical design, and software
tuning each impose a different
kind of loop burden. Timeloop, an analytical framework for evaluating and mapping
deep-neural-network (DNN) accelerators, makes the mapping case especially
concrete. For a single convolutional-neural-network (CNN) layer with seven nested
loop dimensions, mapped onto a four-level memory hierarchy, the number of legal
mappings is astronomically large. Before hitting the raw math, consider what is being multiplied: for every level of the memory hierarchy, we must permute the order of the seven loop dimensions, and for every tensor, we must decide whether it bypasses each memory level. The exact expression matters less than its
size: the unconstrained mapspace contains $(7!)^4 \times (2^4)^3$ arrangements
before co-factor choices are even counted. The $(7!)^4$ factor counts loop-order
permutations of the seven tensor dimensions at each of the four memory levels,
and $(2^4)^3$ counts the level-bypass choices that decide which tensors skip
which levels [@ParasharEtAl2019Timeloop].

| **Loop example** | **Scale anchor** | **Loop lesson** |
| --- | --- | --- |
| DNN accelerator mapping | Timeloop exposes loop permutations, factorization choices, and level-bypass alternatives. | Mapping is itself a combinatorial problem; architecture evaluation depends on the mapper and its constraints. |
| DNN accelerator DSE | MAESTRO, an analytical cost model for estimating DNN dataflow performance, reports 480M candidates, 2.5M valid designs, and 0.17M designs/s [@KwonEtAl2019MAESTRO]. | Validity and pruning shape what evidence can be trusted. |
| TPU-block floorplanning | Learned floorplanning reported a months-to-hours loop compression; later work challenged baselines and reproducibility [@MirhoseiniEtAl2021GraphPlacement; @ChengEtAl2023AssessmentRL]. | High-fidelity tool feedback and rejection authority determine whether generation is credible. |
| Tensor-program tuning | AutoTVM, a machine learning-based tensor program optimizer, describes tensor-operator search spaces on the order of billions of possible implementations for a single GPU operator [@ChenEtAl2018AutoTVM]. | The software side of specialization also has a large hardware-dependent loop. |

: **The scissors gap has source-backed scale anchors:** Mapping, accelerator DSE, floorplanning, and tensor-program tuning all show candidate scale, validity, feedback cost, and evidence standards growing together. {#tbl-design-loop-scale-anchors tbl-colwidths="[25,36,28]"}

The exact size of any one space is not the point. These examples differ in
task, fidelity, and tool chain, but they share the same pressure pattern.
Candidate count, validity, feedback cost, and evidence standards grow together.
More candidates are useful only if the loop can evaluate, explain, and reject
them.

![**The Scissors Gap:** The gap opens when the capacity to generate candidate designs (growing exponentially with generative methods) diverges from the capacity to produce trusted, high-fidelity feedback (which remains flat or scales slowly). This visually justifies why the loop requires strict rejection gates.](images/F2-scissors-gap){#fig-scissors-gap width="100%" fig-alt="Line chart showing candidate generation capacity diverging sharply from trusted feedback capacity over time."}

## Specialized Hardware Needs a Software Loop

Specialization also exposes a software obligation. It is one thing to build an
accelerator, vector unit, memory hierarchy, or chiplet partition that looks
efficient in isolation. It is another thing to let programmers, compilers,
runtimes, libraries, and deployment systems use it without destroying the
efficiency claim through data movement, synchronization, code-generation
overhead, or maintenance burden.

The historical examples in @tbl-historical-loop-transformations show the same pattern.
RISC depended on a compiler story. CUDA made GPU specialization useful by
making the programming and toolchain loop explicit [@NickollsEtAl2008CUDA].
The tensor-program row in @tbl-design-loop-scale-anchors pushes the point further.
Billion-scale operator search is already a software-side obligation of
specialization. Systems such as Halide and MLIR, advanced compiler infrastructures used to define and schedule domain-specific operations, make scheduling, lowering, and
intermediate representations central parts of the performance loop
[@RaganKelleyEtAl2017HalideCACM; @LattnerEtAl2020MLIR].

For the lighthouse prompt, this means that a "64-bit RISC-V compute subsystem"
cannot be judged by hardware structure alone. If the answer proposes a vector
extension, custom accelerator, memory-local dataflow, or chiplet boundary, the
loop must also represent how code reaches that mechanism, what compiler or
runtime assumptions are required, which libraries or kernels use it, and which
tests reject a design that is efficient only in a hand-written kernel. The
software path is not downstream polish. It is part of the architectural claim.
For an AI assistant, a hardware candidate is incomplete unless it also names
the software contract and the tests that can reject unsupported semantics.

::: {.callout-lighthouse title="RISC-V is a software contract"}
**Context.** The ISA phrase fixes more than an instruction encoding. It names
the boundary where AI-generated hardware choices become visible to compilers, runtimes,
libraries, operating systems, and compatibility tests.

**In the Lighthouse prompt.** "64-bit RISC-V-based" and "vector-capable CPU,
accelerator, or SoC block" make the software path part of the claim. An AI-assisted loop
must explain how code reaches the mechanism, what ABI, memory-model, and
toolchain assumptions it preserves, and what tests reject unsupported semantics.

**Takeaway.** The ISA is part of the evidence path for whether the AI-proposed
subsystem can actually be used, not a label on the hardware box.
:::

## Software Changes Faster than Silicon

Specialization depends on stable enough targets. But modern software stacks
move quickly. AI models change. Compiler passes change. Kernel libraries
change. Runtimes, serving systems, quantization formats, batching strategies,
fleet policies, and benchmark versions change. The hardware design cycle does
not move at the same pace.

Generative AI sharpens this mismatch rather than easing it. As models lower the
marginal cost of producing code, the volume and churn of software rise rather
than fall, a software-era instance of Jevons' paradox[^fn-jevons-paradox-c02]. The
shift is already visible in practice. By the mid-2020s, AI coding assistants had
been adopted at scale. The 2024 Stack Overflow Developer Survey reported that a
majority of professional developers were already using AI tools in their
workflow [@StackOverflow2024DeveloperSurvey].
The
design target stops being a fixed workload an architect samples once and becomes
the output of its own fast, semi-autonomous loop, retrained and regenerated
faster than a hardware team can respond. A silicon program measured in years is
then committed against a snapshot the software has already moved past. The
architect cannot answer this by demanding faster silicon alone, because the
fabrication cycle and physical closure set a floor on how short the hardware loop
can be.

This forces a tradeoff the classical loop could often ignore. Peak efficiency
comes from specialization, which is brittle when the workload drifts, while
generality preserves agility at a cost in performance per watt. Under fast
software churn, committing to a specialized design is a bet on workload
stability, and that bet is increasingly made without evidence that the stability
holds. The Architecture 2.0 response is not to abandon specialization but to make
the bet explicit. Bound the workload the design serves, measure how fast it is
drifting, and specialize only with evidence that the target will hold long enough
to repay the silicon. The artifact remains the commitment target; the loop
carries the evidence about whether the workload bet still holds.

The scale of the target workload is not static either. For the loop, the important fact
is not the compute-growth curve itself; it is that workload records expire. The
compute behind notable AI systems has grown by roughly twenty orders of
magnitude in nearly seven decades (@fig-ai-compute-growth), so the workloads an
architecture must serve can shift faster than a silicon program can absorb. A
lighthouse loop should version model, compiler, runtime, benchmark, trace, and
deployment snapshots, then trigger re-evaluation when drift crosses a
commitment boundary.

```{python}
#| label: fig-ai-compute-growth
#| fig-cap: |
#|   **AI compute demand is a fast-moving target:** Training compute for notable AI systems has grown by roughly twenty orders of magnitude since the Perceptron, with a sharp acceleration in the deep-learning era after 2012 and continued frontier growth well past GPT-4 [@SevillaEtAl2022ComputeTrends]. Points are notable-model training-compute estimates from Epoch AI's database; the dashed line is the deep-learning-era trend and the 2025 frontier point is an order-of-magnitude estimate. The architecture that serves these systems is designed against workloads whose scale and shape can change faster than a silicon program can respond.
#| out-width: "78%"
#| fig-alt: "Log-scale scatter of AI training compute by year for a dozen notable models, rising about twenty orders of magnitude from the 1958 Perceptron to frontier 2024-2025 systems, with a steep deep-learning-era trend line after 2012."

import math
import matplotlib.pyplot as plt
from _python.arch2_plots import COLORS, apply_style

apply_style()

# (year, training-compute FLOP, label, show_label). Notable-model estimates
# from Epoch AI's database; the three-eras trend is from Sevilla et al. 2022.
# Mantissas are estimates; the 2025 frontier point is order-of-magnitude only.
points = [
    (1958, 7e5,    "Perceptron", True),
    (2012, 4.7e17, "AlexNet", True),
    (2014, 1.6e19, "VGG-16", False),
    (2016, 1.9e23, "AlphaGo", False),
    (2017, 7.4e18, "Transformer", False),
    (2018, 2.9e20, "BERT-Large", True),
    (2019, 1.5e21, "GPT-2", False),
    (2020, 3.1e23, "GPT-3", True),
    (2021, 6.3e23, "Gopher", False),
    (2022, 2.5e24, "PaLM", False),
    (2023, 2.1e25, "GPT-4", True),
    (2024, 3.8e25, "Llama 3.1 405B", False),
    (2025, 1e26,   "frontier (est.)", True),
]

pre = [p for p in points if p[0] < 2012]
dl = [p for p in points if p[0] >= 2012]
fit = [p for p in dl if p[2] != "AlphaGo"]  # outlier RL run skews the slope

# plain log-linear least squares for the deep-learning-era trend line
fx = [p[0] for p in fit]
fy = [math.log10(p[1]) for p in fit]
n = len(fx)
mx = sum(fx) / n
my = sum(fy) / n
slope = sum((x - mx) * (y - my) for x, y in zip(fx, fy)) / sum((x - mx) ** 2 for x in fx)
intercept = my - slope * mx
tx = [2012, 2026]

fig, ax = plt.subplots(figsize=(4.65, 2.45))
fig.subplots_adjust(left=0.16, right=0.96, top=0.95, bottom=0.18)
ax.plot(tx, [10 ** (intercept + slope * x) for x in tx], color=COLORS["muted"],
        linewidth=1.0, linestyle=(0, (4, 3)), zorder=1)
ax.scatter([p[0] for p in pre], [p[1] for p in pre], s=20, color=COLORS["muted"], zorder=3)
ax.scatter([p[0] for p in dl], [p[1] for p in dl], s=24, color=COLORS["blue"], zorder=3)
ax.set_yscale("log")
ax.set_ylim(1e4, 1e28)
ax.set_xlim(1953, 2028)
ax.set_ylabel("training compute (FLOP)", fontsize=7)
ax.set_xticks([1960, 1980, 2000, 2020])
ax.tick_params(axis="both", labelsize=6.5, length=2.5, width=0.6, pad=2)
offsets = {
    "Perceptron": (8, -3),
    "AlexNet": (7, -8),
    "BERT-Large": (7, -3),
    "GPT-3": (7, -2),
    "GPT-4": (5, -10),
    "frontier (est.)": (4, 4),
}
for x, y, lab, show in points:
    if show:
        dx, dy = offsets.get(lab, (5, -2))
        ax.annotate(lab, (x, y), textcoords="offset points", xytext=(dx, dy), fontsize=5.7, color=COLORS["ink"])
ax.grid(axis="y", color=COLORS["grid"], linewidth=0.6)
for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)
ax.spines["left"].set_color(COLORS["ink"])
ax.spines["bottom"].set_color(COLORS["ink"])
```

This growing need to track moving workloads reflects a broader breakdown of abstractions, a shift that Compiler 2.0 offers as a useful adjacent warning. Amarasinghe's framing is that
compilers originally made hardware disappear for programmers, but multicore
processors, vector instructions, accelerators, and heterogeneous systems have
pushed more performance burden back onto programmers
[@Amarasinghe2020Compiler20; @Amarasinghe2026Compiler20CSAIL]. The same
pattern appears at the architecture level. Abstractions still matter, but the
design loop must now expose more of the workload, software, hardware, and
physical state that earlier abstractions could hide.

To manage this rapidly changing software state, the community has had to formalize its workload agreements, making MLPerf a useful example. It was built to create common, reproducible
machine-learning system benchmarks across a rapidly changing field
[@MattsonEtAl2020MLPerf]. MLPerf Inference sharpened the deployment-facing
version of that problem. The paper reports more than 100 organizations building
ML inference chips, systems spanning at least three orders of magnitude in
power and five orders of magnitude in performance, and more than 600
reproducible measurements from 14 organizations in the first submission round
[@ReddiEtAl2020MLPerfInference]. The lesson is not only that benchmarks
need rules. It is that a benchmark must encode scenarios, latency constraints,
accuracy targets, software stacks, and comparability rules before performance
numbers mean the same thing across systems
[@ReddiEtAl2021VisionBehindMLPerf]. That is also the challenge for
architecture. A benchmark is not a fixed oracle. It is a maintained agreement
about what evidence should count for a class of systems. The loop artifact is a
versioned workload packet: traces, scenario constraints, acceptance tests, and
expiration or review triggers.

For the lighthouse prompt, the workload is not merely "XR." It is a moving
bundle of sensing, perception, graphics, display, interaction, latency,
quality-of-experience, and energy constraints. Even with XRBench
[@KwonEtAl2023XRBench], a credible architecture loop must still decide
which traces, model versions, deadlines, input distributions, and quality
targets matter. If the software stack changes faster than the hardware loop
can absorb, the design may optimize yesterday's workload.

## Physical Constraints Move into Architecture {#sec-physical-constraints-move-into-architecture}

Drifting workloads are only one source of pressure, pushing down from the software stack; physical limits
push up on the loop from below just as hard. Architecture does not sit above physical
reality. It is the layer where
software intent, hardware mechanisms, and physical constraints become one
design problem.

For example, data-movement estimates serve as early physical constraints, providing cheap rejection evidence rather than merely confirming that
memory is expensive. Moving data through the memory hierarchy often
costs far more energy than arithmetic, and Horowitz's widely used energy
estimates made this point concrete for a generation of architects
[@Horowitz2014Energy]. That changes what architecture work means. A design loop
cannot only ask which compute block is fastest. It must
ask where the data lives, how often it moves, who schedules it, what locality
exists, what precision is acceptable, and what the software stack can express.

A useful architecture-level decomposition is
$$
E_{\mathrm{system}} =
E_{\mathrm{compute}} + E_{\mathrm{memory}} +
E_{\mathrm{interconnect}} + E_{\mathrm{control}} +
E_{\mathrm{leakage}} .
$$
This is not a circuit-level energy model. Use this decomposition as loop state.
If any term is unrepresented, stale, or estimated outside its validity regime,
the candidate should not cross the next commitment boundary. A candidate that
reduces arithmetic but increases memory movement, interconnect traffic, control
overhead, or leakage has not necessarily improved the system.

![The Waterbed Effect: Optimizing one term of the physical energy constraint often causes others to balloon. A naive AI optimization might squeeze down compute energy while massively inflating memory and interconnect costs if it fails to represent data movement.](images/F2-waterbed-effect){#fig-waterbed-effect width="100%" fig-alt="Bar chart showing a baseline energy breakdown alongside a naive AI-optimized candidate where compute energy shrinks but memory and interconnect energy balloon."}

Interconnect costs have the same character as memory movement. On-chip networks, package links, memory
interfaces, collectives, and host-device protocols define what a design can
actually sustain. EDA and physical-design constraints also move upward. Timing,
placement, routing, IR drop, thermal behavior, leakage, signoff, and test are
not late implementation details when they can overturn an architectural choice.
For a design loop, this means that a simulator score or model prediction is
not enough. The loop needs a path from low-fidelity estimates to stronger
evidence, and it needs rules for when physical constraints reject an otherwise
promising candidate.

The Architecture 2.0 move is to make those physical assumptions inspectable
before the loop delegates work. A generic generator can propose a faster block
or a clever dataflow; an architecture loop must say which power model, memory
traffic model, placement assumption, timing margin, and escalation rule make
that proposal credible. Without that state, AI merely produces more candidates
for a later physical-design step to reject. With that state, physical reality
becomes an early design constraint, not a late surprise.

The important consequence is not that every early idea needs signoff-quality
evidence. It is that the loop must know which physical assumptions are being
made, what evidence would overturn them, and when to escalate from a proxy to
stronger feedback. Otherwise the apparent speedup from AI-generated candidates
is paid back later as discarded work.

The order-of-magnitude spread in @fig-data-movement-energy-scale is not
something to memorize or treat as a current-node prediction. The architectural
use is simpler. Local arithmetic and memory movement live on very different
energy scales, so a loop that optimizes only arithmetic can improve the wrong
thing. Advanced-node designs do not remove this lesson; if anything, the gap
between local logic and moving data, driving wires, and feeding memory systems
is one reason locality remains an architectural problem rather than a solved
device-scaling detail. For the 3\ nm-class lighthouse prompt, the loop would
need a fresh power model before making a design decision.

```{python}
#| label: fig-data-movement-energy-scale
#| fig-cap: |
#|   **Data movement can dominate arithmetic energy:** Rough Horowitz 45\ nm energy values show why architecture loops must represent locality, buffering, precision, scheduling, and memory hierarchy rather than counting arithmetic alone. The values are order-of-magnitude interpretive anchors, not current-node device estimates.
#| out-width: "92%"
#| fig-alt: "Log-scale plot comparing arithmetic and memory-access energy, showing that SRAM and DRAM movement cost orders of magnitude more than local arithmetic."

import matplotlib.pyplot as plt
from _python.arch2_plots import COLORS, add_note_box, apply_style, draw_range_rows, row_axis, top_log_axis

rows = [
    {"display_label": "32b integer add", "display_note": "baseline arithmetic", "energy_low_pj": 0.1, "energy_high_pj": 0.1, "right_label": "1x", "color": COLORS["blue"]},
    {"display_label": "32b floating-point add", "display_note": "local arithmetic", "energy_low_pj": 0.9, "energy_high_pj": 0.9, "right_label": "9x", "color": COLORS["blue"]},
    {"display_label": "32b integer multiply", "display_note": "local arithmetic", "energy_low_pj": 3.1, "energy_high_pj": 3.1, "right_label": "31x", "color": COLORS["blue"]},
    {"display_label": "32b floating-point multiply", "display_note": "local arithmetic", "energy_low_pj": 3.7, "energy_high_pj": 3.7, "right_label": "37x", "color": COLORS["blue"]},
    {"display_label": "8 KB SRAM access", "display_note": "64b cache access", "energy_low_pj": 10, "energy_high_pj": 10, "right_label": "100x", "color": COLORS["green"]},
    {"display_label": "32 KB SRAM access", "display_note": "64b cache access", "energy_low_pj": 20, "energy_high_pj": 20, "right_label": "200x", "color": COLORS["green"]},
    {"display_label": "1 MB SRAM access", "display_note": "on-chip memory access", "energy_low_pj": 100, "energy_high_pj": 100, "right_label": "1000x", "color": COLORS["orange"]},
    {"display_label": "off-chip DRAM access", "display_note": "off-chip memory access", "energy_low_pj": 1300, "energy_high_pj": 1300, "right_label": "~13000x", "color": COLORS["red"]},
]

apply_style()
fig, ax = plt.subplots(figsize=(4.9, 3.45))
fig.subplots_adjust(left=0.40, right=0.80, top=0.82, bottom=0.17)

row_axis(ax, len(rows))
top_log_axis(
    ax,
    xlim=(0.06, 4000),
    xticks=[0.1, 1, 10, 100, 1000],
    xticklabels=["0.1 pJ", "1 pJ", "10 pJ", "100 pJ", "1 nJ"],
    xlabel="rough energy per operation or access",
)
draw_range_rows(ax, rows, low_key="energy_low_pj", high_key="energy_high_pj", label_x=-0.82, right_x=1.04, label_fontsize=6.6, note_fontsize=5.4, right_fontsize=6.1, label_dy=-0.17, note_dy=0.23)
add_note_box(fig, "Rough 45 nm, 0.9 V values from Horowitz; use for orders of magnitude.", xywh=(0.14, 0.035, 0.72, 0.075), fontsize=5.5)

plt.show()
plt.close(fig)
```

The plot changes the section's claim from "data movement is expensive" to
"locality is an early rejection condition". A loop that cannot represent memory
movement cannot support a power or efficiency commitment.

## Engineering Cost Creates the Scissors Gap

Each of these pressures, physical reality included, lands on the same fault
line, a scissors gap. On one blade are design choices,
workload variants, tool outputs, cross-layer assumptions, simulator hours,
verification cases, EDA reports, physical constraints, and deployment signals.
On the other blade are human attention, expert review time, tool budget,
schedule, and verification capacity. The first blade rises quickly. The second
does not.

@fig-scissors-gap makes the metaphor explicit. The upper blade is not only
candidate count; it is the coupled burden of choices, constraints, evidence,
software paths, and physical feasibility. The lower blade is not the ability
to think; it is the slower-growing capacity to evaluate, review, reject, and
commit with confidence.

![**The scissors gap is a feedback gap:** Architecture pressure rises when design choices, constraints, and evidence demand grow faster than unaided manual coordination and verification capacity. The widening region is the gap that Architecture 2.0 tries to make explicit and manageable.](images/F2-scissors-gap){#fig-scissors-gap width="92%" fig-alt="Scissors-style diagram where rising choices, constraints, and evidence demand separate from slower manual verification capacity, creating a feedback gap."}

The gap is also an engineering-cost problem. Public estimates vary, and they
should not be treated as universal accounting rules, but their scale is useful.
The Semiconductor Industry Association reports that the cost of designing a
latest-node chip rose from about \$30M for a 65\ nm chip in 2006 to more than
\$540M for a 5\ nm chip in 2020, a greater than $18\times$ increase
[@SemiconductorIndustryAssociation2026ChipDesign]. A McKinsey analysis
gives a similar order of magnitude, estimating roughly \$175M for a 10\ nm
design, \$300M for a 7\ nm design, and \$540M for a 5\ nm design when validation,
IP qualification, and related development costs are included
[@BauerEtAl2020SemiconductorDesignManufacturing]. These are not only mask
or wafer costs. They are costs of architecture, design, validation,
verification, IP, tools, and people.

Verification makes the people cost visible. In a summary of the 2022 Wilson
Research Group functional-verification study, Foster reports that demand for
IC/ASIC verification engineers grew faster than demand for design engineers
from 2007 to 2022; the same summary reports that mean peak staffing is roughly one verification
engineer per design engineer across most market segments, that processor
projects can reach a 5-to-1 verification-to-design ratio, and that
design engineers spent 49 percent of their time in verification in 2022
[@Foster2022WilsonVerificationStudy]. A later 2024 Wilson Research Group
IC/ASIC report makes the commitment risk visible from another angle. It
reports first-silicon success at 14 percent, the lowest level in two decades
[@Foster2025WilsonVerification2024]. This is why feedback and rejection
are central to Architecture 2.0. Each invalid candidate consumes scarce
engineering capacity and commitment risk, not just compute cycles.
This is the economic reason rejection, not generation, must pace automated
search. Generated candidates are cheap only until they consume scarce
verification, tool, and review capacity.

::: {.callout-field-note title="Rejected too late: FDIV" icon=false}
Most computer architects will recall the 1994 Intel Pentium FDIV bug. Early
processors returned incorrect results for certain floating-point divisions
because five of the 1,066 entries in a lookup table used by the division
algorithm were wrong. The cause was small, but the cost was not. Intel took a
\$475 million charge to replace the affected chips, and the episode pushed the
industry toward formal verification of floating-point hardware
[@IntelPentiumFDIV]. It is worth re-reading that lesson through an AI lens. No
cheap check rejected the error before it reached silicon, and the missing
rejection, not the missing entries, set the price. An automated loop that proposed
or modified such a table would need the table-generation assumptions on record,
independent division checks, failing-case coverage, and a named owner for
accepting or rejecting the residual risk. The bug is old; the discipline it
demands is exactly what an AI-assisted loop must make explicit.
:::

@fig-leading-node-design-cost turns the public dollar estimates
into a scale check. It should not be read as a universal cost curve. Different
products, IP reuse strategies, node maturities, organizations, and accounting
boundaries produce different numbers. The robust point is simpler. As the loop
moves toward leading-edge implementation, feedback and commitment consume real
engineering budgets, not only simulator cycles.

```{python}
#| label: fig-leading-node-design-cost
#| fig-cap: |
#|   **Leading-node design-cost estimates make the scissors concrete:** Public SIA and McKinsey estimates [@SemiconductorIndustryAssociation2026ChipDesign; @BauerEtAl2020SemiconductorDesignManufacturing] put latest-node chip design costs from tens of millions of dollars at 65 nm to more than $500M at 5 nm, with IBS estimates extending the trend to roughly $725M at 2 nm [@InternationalBusinessStrategies2024ChipDesignCost]. The accounting boundaries vary, but the scale makes feedback, validation, IP, tools, and human engineering effort part of the architecture loop.
#| out-width: "86%"
#| fig-alt: "Line and area plot showing public chip design cost estimates increasing from tens of millions at 65 nanometers to roughly 725 million dollars at 2 nanometers."

import matplotlib.pyplot as plt
from _python.arch2_plots import COLORS, add_note_box, apply_style

rows = [
    {"node_label": "65 nm", "cost_musd": 30, "source": "SIA", "right_label": "~$30M"},
    {"node_label": "10 nm", "cost_musd": 175, "source": "McKinsey", "right_label": "~$175M"},
    {"node_label": "7 nm", "cost_musd": 300, "source": "McKinsey", "right_label": "~$300M"},
    {"node_label": "5 nm", "cost_musd": 540, "source": "SIA / McKinsey", "right_label": ">$540M"},
    {"node_label": "3 nm", "cost_musd": 590, "source": "IBS", "right_label": "~$590M"},
    {"node_label": "2 nm", "cost_musd": 725, "source": "IBS", "right_label": "~$725M"},
]

apply_style()
labels = [row["node_label"] for row in rows]
costs = [row["cost_musd"] for row in rows]
sources = [row["source"] for row in rows]
right_labels = [row["right_label"] for row in rows]
x_values = list(range(len(rows)))

fig, ax = plt.subplots(figsize=(4.65, 2.25))
fig.subplots_adjust(left=0.14, right=0.95, top=0.88, bottom=0.33)

ax.plot(x_values, costs, color=COLORS["blue"], linewidth=1.7, marker="s", markersize=4.5, markerfacecolor=COLORS["note_fill"], markeredgewidth=1.0)
ax.fill_between(x_values, costs, [0] * len(costs), color=COLORS["design_cost_fill"], alpha=0.75, zorder=0)
ax.set_xlim(-0.35, len(rows) - 0.65)
ax.set_ylim(0, 800)
ax.set_xticks(x_values)
ax.set_xticklabels(labels, fontsize=6.8)
ax.set_yticks([0, 100, 300, 500, 700])
ax.set_yticklabels(["$0", "$100M", "$300M", "$500M", "$700M"], fontsize=6.5)
ax.set_ylabel("public design-cost estimate", fontsize=7)
ax.tick_params(axis="both", length=2.5, width=0.6, pad=2)
ax.grid(axis="y", color=COLORS["grid"], linewidth=0.6)

for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)
ax.spines["left"].set_color(COLORS["ink"])
ax.spines["bottom"].set_color(COLORS["ink"])

for x, cost, source, right_label in zip(x_values, costs, sources, right_labels):
    ax.text(x, cost + 24, right_label, ha="center", va="bottom", fontsize=6.6, fontweight="bold", color=COLORS["ink"])
    ax.text(x, -83, source, ha="center", va="top", fontsize=5.7, color=COLORS["muted"], clip_on=False)

add_note_box(fig, "Directional estimates: accounting boundaries vary by chip, node, IP reuse, and organization.", xywh=(0.16, 0.04, 0.72, 0.12), fontsize=5.8)

plt.show()
plt.close(fig)
```

The cost plot is not an indictment of architects. It says the unit of work has
changed. The bottleneck is trusted feedback. That means preserving invalid candidates,
proxy failures, assumptions, and the decision a human can responsibly commit to.
Without that record, teams rerun old mistakes, rediscover invalid regions, and
mistake more output for more architectural progress.

This bottleneck is not only a diagnosis. It has a bound. The diagnostic table
earlier in this chapter asked which part of one loop saturates first;
@sec-loop-patterns-across-stack makes the stronger, loop-wide claim precise.
Whichever part saturates, end-to-end throughput is set by how cheaply the loop
can reject, not by how much it can generate. Generating proposals faster than
trusted feedback cannot keep up widens the scissors gap rather than closing it. Just as Amdahl's Law dictates that sequential code bottlenecks multicore speedups, the Architecture 2.0 loop has its own Amdahl's Law: no matter how fast the generative AI proposes candidates, the throughput of the design loop is strictly bounded by the serial fraction of human review and rejection capacity.

## Feedback and Verification Become the Bottleneck {#sec-feedback-and-verification-become-the-bottleneck}

Architecture feedback has uneven cost and uneven authority. A spreadsheet
model is cheap but weak. A simulator may be more informative but slow or
biased. A synthesis result exposes more implementation reality but depends on
tool settings and constraints. Physical design and signoff are stronger still,
but expensive and late. Silicon and deployment telemetry are authoritative in
different ways, but they arrive after major commitments.

This feedback-regime structure makes naive autonomy dangerous. An optimizer that targets a
cheap proxy may move quickly in the wrong direction. A search method that
reports a Pareto frontier (the set of optimal designs where no objective can be improved without degrading another) may hide invalid configurations, failed tool runs,
or assumptions that would not survive signoff. A generated RTL fragment may
look plausible but fail under verification or integration. Feedback becomes
evidence only when its fidelity and provenance are clear, the discipline that
@sec-feedback-verification-trust develops in full.

This is why Architecture 2.0 does not begin with autonomy. It begins with the
loop. The loop must say what can be changed, what can be observed, what can
reject a candidate, what evidence is strong enough for the next commitment,
and what remains a human decision.

::: {.callout-architect-checkpoint title="The Automation Gate"}
When does an automated proxy ranking escalate to a human architectural decision? 
The loop must explicitly define which metrics, constraints, and failures 
require human signoff before the automated method can move a design to the next commitment level. 
:::

::: {#pri-treat-feedback .callout-design-principle title="Treat feedback as the bottleneck"}
More AI-generated candidates do not help a loop that cannot evaluate, reject, and justify
them. Design for the rate of trusted feedback first, and add AI generation only as
fast as human or automated rejection can keep up.
:::

## Architecture Violates Generic AI Assumptions

Many successful AI systems are built in domains that generic machine-learning
workflows take for granted, domains with abundant data, cheap feedback, stable
labels, and clear losses. Those are exactly the conditions a design loop would
want, and computer architecture violates them at almost every boundary. Data are often proprietary, incomplete,
stale, or missing the rejected and failed candidates that explain why a design
space has certain boundaries. @sec-data-representations-world-models gives
those records a sharper name and makes them part of loop state. Feedback ranges
from a quick proxy to a simulation, synthesis run, physical-design report,
expert review, emulation result, or silicon measurement, each with different
latency, cost, fidelity, and authority. The action space is also unusual. Many
generated configurations are not merely low quality; they are illegal,
unsupported by tools, unverifiable, or incompatible with software and physical
constraints.

The result is not a simple lack of data. It is a mismatch between generic AI
assumptions and architecture-loop requirements. Architecture loops need
representations that carry constraints, provenance, feedback cost,
uncertainty, and rejection conditions. They also need methods that understand
when a proxy result is only a proxy and when a decision is moving toward a
higher commitment level.

A conventional machine-learning workflow is still useful as a foil. Students
often learn a pipeline that runs from data collection to preprocessing,
training, validation, deployment, and monitoring. @fig-ai-workflow-mismatch
keeps that familiar picture but shows why the architecture version cannot be a
simple pipeline: every step must carry validity constraints, tool costs,
provenance, drift, rejected alternatives, and a commitment boundary.

![**Architecture turns the ML pipeline into a constrained loop:** A generic ML workflow can be taught as data, preprocessing, training, validation, and deployment. In architecture, the corresponding workflow must also represent constraints, legal actions, expensive tool feedback, an evidence ledger, failed and rejected candidates, drift, rejection authority, and a commitment boundary.](images/F2c-ai-workflow-mismatch){#fig-ai-workflow-mismatch width="100%" fig-alt="Comparison diagram showing a generic machine-learning pipeline transformed into an architecture loop with constraints, tool feedback, evidence ledgers, rejection, and commitment boundaries."}

The mismatch has several concrete forms. Data are not just examples; they are
design artifacts with permissions, tool versions, and missing failures.
Feedback is not just a label; it spans regimes such as proxies, simulation,
synthesis, physical design, expert review, emulation, and silicon. Actions are
not just tokens; they are edits to configuration spaces, software interfaces,
RTL, constraints, and deployment policies, many of which can be invalid. Losses
are not just scalar rewards; they are multiobjective efficiency claims under
performance, power, area, cost, reliability, sustainability, and verification
burden. @tbl-ai-assumptions-architecture-violations gives the
checklist version of that argument.

| **Common AI assumption** | **Architecture violation** | **Loop implication** |
| --- | --- | --- |
| Abundant labeled data | Many labels are proprietary, expensive, stale, or not recorded. | The loop must build source records, provenance, and reusable failure records. |
| Cheap feedback | Simulation, synthesis, EDA, emulation, and review can be slow or scarce. | Methods must be sample-efficient and aware of feedback budgets. |
| Stable distribution | Workloads, software stacks, compilers, models, and deployment policies drift. | Benchmarks and representations must be versioned and revisited. |
| Valid actions are easy to define | Many generated configurations are invalid, unsafe, unverifiable, or unsupported by tools. | Environments need action schemas, constraint checks, and rejection authority. |
| Reward is clear | Efficiency mixes performance, energy, area, cost, reliability, sustainability, verification burden, and risk. | Objectives must be explicit, multiobjective, and tied to human decisions. |
| Proxy metrics are enough | Proxy wins can vanish at higher fidelity or under different workloads. | Evidence needs fidelity-regime checks and sensitivity checks. |
| Failures are just bad samples | Failed runs, rejected candidates, and invalid states describe the design space. | Failure records should be preserved as architecture data. |

: **Generic AI assumptions break at architecture boundaries:** Architecture loops must represent proprietary or incomplete data, expensive feedback, invalid actions, drifting workloads, multiobjective efficiency, proxy mismatch, and rejected or failed candidates. {#tbl-ai-assumptions-architecture-violations tbl-colwidths="[28,31,30]"}

```{=latex}
\FloatBarrier
```

This mismatch does not make AI irrelevant. It makes representation and loop
design central. Architecture needs generation, prediction, optimization,
critique, retrieval, and tool use. But those capabilities must operate inside
an environment that knows what actions are legal, what feedback means, and who
can say no.

## AI Helps Only When the Loop Is Designed

AI becomes important because the classical loop is under pressure. It can help
summarize tool outputs, propose candidates, search spaces, predict costs,
construct tests, critique assumptions, retrieve prior designs, and coordinate
subtasks. In domains with expensive feedback and large design spaces, even
partial improvements in search, triage, and explanation can matter.

But AI is not sufficient because architecture is not only generation. The
architectural problem is to produce a credible system artifact under
constraints. That requires state, tools, evidence, rejection, and commitment.
A model that proposes a design without exposing its assumptions has not solved
the architecture problem. A loop that finds a better proxy score without
recording rejected and failed candidates has not produced trusted evidence. A
system that cannot say what rejects its own output cannot be given
high-commitment authority.

The right conclusion is therefore narrower and stronger than generic AI
optimism. We should not merely search larger design spaces. We should design
loops that learn, record, reject, and justify architecture work. That is the
transition to the ontology in the next chapter. Once the pressure is visible,
the next task is to name the minimum loop state that makes AI assistance
inspectable rather than merely impressive.

## Open research questions
For the strained-loop regime:

1. What minimum loop-state record (task, action schema, constraints,
   candidate provenance, feedback regime, uncertainty, rejected alternatives,
   escalation rule, and commitment owner) makes an AI-assisted architecture
   loop reviewable when high-fidelity simulation, synthesis, or signoff samples
   are scarce?
2. When proprietary or low-sample design records are redacted, what corpus and
   representation let an AI-assisted loop preserve failures, uncertainty,
   permissions, tool versions, and unsupported claims as reusable evidence?
3. Which cheap rejection tests let AI-generated or AI-ranked candidates improve
   loop throughput without hiding false acceptances or false rejections,
   measured across a staged proxy, simulation, synthesis, physical-design, and
   verification environment?
4. What versioned workload, benchmark, model, compiler/runtime, and deployment
   snapshots should an AI-assisted specialization loop publish so its validity
   horizon is explicit and drift triggers re-evaluation before stronger
   commitment?

## What to carry forward
- **Reader test:** When candidate scale and feedback cost grow together, can you
  say why trusted feedback, not idea generation, is the bottleneck, and what loop
  state the scissors gap demands?
- **Next loop state:** AI helps only when the loop records state, failures,
  evidence, rejection authority, and each commitment's human owner;
  @sec-architecture-20-ontology names the minimum loop state that makes that
  pressure inspectable.

[^fn-autotuning-c02]: **Autotuning**: The process of automatically searching for optimal program or system parameters.
[^fn-jevons-paradox-c02]: **Jevons' paradox**: From nineteenth-century resource economics, the observation that making a resource cheaper to use can raise its total consumption instead of lowering it.
# Architectural Claims and Design Loops {#sec-architecture-20-ontology}

```{=latex}
\abstract*{This chapter introduces how the book states and reviews architectural claims, along with its ontology and compact framework. Architecture 2.0 is the engineering discipline of making architectural claims and their design loops explicit enough that AI systems can act inside them credibly.}
```

::: {.callout-crux}
What does a design loop need to make explicit before an AI output can be
accepted or rejected as an architectural claim?
:::

Computer architecture has always depended on disciplined abstraction. An
architect rarely reasons directly from every transistor to every application
behavior. The field instead builds models, simulators, workload
characterizations, cost estimates, design rules, and review practices that make
large design spaces tractable. That quantitative tradition is central to
modern architecture practice [@HennessyPatterson2017QuantitativeApproach].
It also explains why Architecture 2.0 should not be framed as a sudden break
from the past. The field has always designed through loops of abstraction,
measurement, feedback, and judgment.

What becomes first-class alongside the artifact is the loop that produces and
tests claims about it. In Architecture 1.0, the architect uses tools to design
artifacts: an ISA extension, a cache hierarchy, an accelerator, a memory
system, a chiplet partition, a compiler policy, or a system configuration. But
an artifact matters because it supports an architectural claim: that a design
improves useful work, reduces energy, meets a latency target, preserves
correctness, exposes a tradeoff, or changes what is possible under a workload
and set of constraints. In Architecture 2.0, the architect must also design the
loop that produces, tests, rejects, and revises those claims.
The loop itself needs a task boundary, a design space, a representation, a
world model, an environment, method roles, feedback channels, evidence
standards, rejection authority, and human decision points
[@ReddiYazdanbakhsh2025Architecture20]. Without those pieces, an AI
system may still produce plausible text, code, or configurations, but it is not
participating in architecture work in a way the field should trust.

Making a design process explicit is what mature engineering fields do once the
cost of an undetected error grows. Aviation did not become safe by trusting more
skilled pilots; it formalized the process with checklists, assurance cases
[@Kelly2004GSN], and
certification standards that make the evidence for a safety claim auditable.
Software operations did not become reliable by hiring more careful engineers;
DevOps and site-reliability practice made deployment, monitoring, and rollback
explicit, with error budgets and runbooks that state what evidence justifies a
change [@BeyerEtAl2016SRE]. The common pattern is a move from individual judgment
to a represented process with explicit evidence and rejection rules. Architecture
2.0 makes the same move for system design. The alternative is not creative
freedom; it is an ad hoc loop whose assumptions, rejected alternatives, and
evidence live only in people's heads, which is exactly the state that stops
scaling when the design space and the verification burden grow together.

This chapter gives the reusable language for that shift. The goal is not to
classify every paper or tool. A taxonomy of current systems will age quickly.
The more durable contribution is a consistent way to state the architectural
claim being made, together with an ontology of the entities and relationships
that must exist before AI systems can act inside the architecture design loop
credibly.

The ontology has to earn its space by being useful. A researcher should be
able to cite it when explaining the structure of an Architecture 2.0
contribution. A reviewer should be able to use it to ask what state, action,
feedback, evidence, and rejection authority a paper exposes. A tool builder
should be able to use it as a checklist for a harness or environment. An author
should be able to use it to state the claim and loop for a concrete design
problem. If the ontology cannot support those uses, it is only vocabulary.
Its test is whether it exposes enough state for a generative method to act within bounds
and enough evidence for a human architect to reject or commit the result.

The deeper reason we need such an ontology is that architecture reasoning still lacks a durable
structured layer above RTL. Below RTL, design flows already have artifacts that
tools can parse, transform, reject, and sign off. Above RTL, much of the
reasoning that decides *what* should be built still lives in whiteboards,
spreadsheets, scripts, slides, review memories, and natural-language specs. The
design-loop card, loop contract, environment contract
(@sec-architecture-environments-tool-interfaces), and evidence ledger are
not paperwork around the real work. They are candidate structured abstractions
for the part of architecture practice that has not yet been made inspectable.

The hierarchy in this chapter is simple. The artifact is what may eventually be
built. The architectural claim is what a reviewer accepts or rejects about that
artifact. The design loop is the process that tests the claim. The ontology names
the state and relationships the loop must expose. The design-loop card is the
compact record that makes the claim and loop reviewable. The loop contract from
@sec-moonshot is the same object seen before action: it states the task, state,
actions, feedback, evidence standard, and decision owner the loop promises to
expose, and the card records how the loop kept that promise.

@fig-structured-layer-above-rtl places that layer between tacit reasoning and
implementation flows. Its purpose is not to add ceremony. It is to make the
part of architecture reasoning above RTL explicit enough that tools, automated participants,
reviewers, and architects can all see the same loop state.

![**Architecture 2.0 needs a structured layer above RTL:** Whiteboards, spreadsheets, and natural-language specs still carry much of the reasoning that decides what should be built. The loop contract, represented state, environment contract, and evidence ledger turn that reasoning into a reviewable layer that can connect to simulators, compilers, RTL, EDA, and software evidence.](images/F4d-structured-layer-above-rtl){#fig-structured-layer-above-rtl width="100%" fig-alt="Three-layer diagram showing tacit architecture reasoning flowing into a represented design-loop layer, which then connects to executable implementation flows such as simulators, compilers, RTL, EDA, and signoff."}

::: {.callout-learning-objectives}
After this chapter you can turn an AI prompt, paper, tool, or project into a
reviewable design-loop card. That means you can:

- write an AI-generated architectural claim as a reviewable object: workload, baseline, design space, objectives, constraints, evidence, rejection authority, commitment boundary, and human decision;
- audit an AI-assisted paper, tool, or project by naming the loop state, legal actions, environment feedback, evidence ledger, rejection and escalation rules, and human-owned commitment it exposes;
- explain how artifact, claim, loop, ontology, checklist, and design-loop card fit together in an AI-assisted workflow;
- distinguish an ontology from a taxonomy and say why ontology comes first;
- judge how much autonomy an AI-driven loop has actually earned.
:::

## The Architectural Claim Is the Unit of Review

The most common question is too coarse: can a model design hardware? The more
architecture-native question is: what claim is being made, and what would make
that claim credible? Architects rarely accept an artifact by itself. They
accept or reject a claim about that artifact relative to a workload, baseline,
design space, objectives, constraints, and evidence. The definition below names
that review object so the rest of the chapter can ask what state a loop must
carry before an AI-assisted result can be accepted or rejected.

> **Architectural claim.** An architectural claim is a statement that a
> proposed artifact, method, or loop improves, preserves, or explains a
> hardware/software behavior for a specified workload or scenario relative to a
> baseline, under explicit objectives, constraints, evidence, rejection
> conditions, and decision authority.

A plain-language version might say: this candidate improves useful work for
this workload, relative to this baseline, inside this design space, under these
constraints, using this evidence, and with this rejection authority. A compact
way to write the same review object is
$$
\mathcal{C} =
\langle W, B, \mathcal{D}, \mathbf{J}, \mathcal{K}, E, R, M, H \rangle .
$$
Here, $W$ is the workload or scenario, $B$ is the baseline, $\mathcal{D}$
is the legal design space, $\mathbf{J}$ is the objective vector, $\mathcal{K}$
is the constraint set, $E$ is the evidence, $R$ is the rejection authority,
$M$ is the commitment boundary, and $H$ is the human or organizational decision
authority. This tuple is the claim slice of the design-loop card, not a second
schema. The notation
prevents a generated artifact from masquerading as an architectural result
before the comparison, constraints, evidence, rejection authority, and
commitment boundary are visible.

![The Architecture Tuple: The core relationship in the design loop connecting state (S), actions (A), transitions (T), observations (O), and rewards/constraints (R).](images/F3-architecture-tuple){#fig-architecture-tuple width="100%" fig-alt="Block diagram showing state flowing to action, action to transition, transition to observation, observation to reward/cost, with a loop iteration back to state."}

In card terms, $W$ and $B$ anchor the task and evidence comparison, $\mathcal{D}$
is the design space, $\mathbf{J}$ and $\mathcal{K}$ belong in the representation
and evidence standard, $E$ is the evidence ledger, $R$ is the rejection
authority, $M$ is the commitment boundary, and $H$ is the human decision owner.

@tbl-architectural-claim-schema turns the tuple into a reader
checklist for the lighthouse prompt. The important point is that the prompt's
compact wording hides a large amount of architectural state. A credible answer
must expose that state before the reader can judge whether the result deserves
trust.

| **Claim field** | **Reader question** | **Lighthouse instance** |
| --- | --- | --- |
| **Workload or scenario** | What behavior is the design supposed to serve? | XRBench-class real-time mobile XR workloads, with latency, sensing, graphics, and interaction requirements. |
| **Baseline** | Compared to what architecture, software stack, or prior result? | A scalar CPU-only baseline, a vector-capable CPU, an accelerator baseline, or an existing mobile XR subsystem. |
| **Design space** | What choices are legal, and which regions are invalid? | RISC-V ISA options, vector width, CPU/accelerator partitioning, memory hierarchy, clocking, compiler/runtime path, and tool-flow limits. |
| **Objective vector** | What counts as improvement, and what tradeoffs matter? | Throughput, tail latency, energy, area, programmability, verification burden, and evidence cost under the 3\ W target. |
| **Constraints** | What cannot be violated even if a metric improves? | ISA compatibility, correctness, thermal limits, process assumptions, package limits, software compatibility, and 3\ nm-class low-power envelope. |
| **Evidence** | What supports the claim at the required commitment level? | Workload traces, simulations, power model, sensitivity checks, rejected candidates, tool logs, and comparison against baselines. |
| **Rejection authority** | What observation, tool, review, or rule can invalidate or weaken the result? | Missed latency target, power envelope violation, invalid RTL/configuration, compiler failure, simulator mismatch, or weak coverage. |
| **Commitment boundary** | What claim is the evidence strong enough to support, and what remains uncommitted? | Exploration, RTL study, implementation, deployment, or silicon-facing commitment, with stronger evidence required at each boundary. |
| **Human decision** | Who can accept, revise, escalate, or commit the claim? | The architect or review process that owns assumptions, evidence thresholds, risk, and final commitment. |

: **An architectural claim needs more than an artifact:** The lighthouse prompt becomes reviewable only when the workload, baseline, design space, objectives, constraints, evidence, rejection authority, commitment boundary, and human decision are explicit. {#tbl-architectural-claim-schema tbl-colwidths="[18,33,39]"}

```{=latex}
\FloatBarrier
```

This schema also clarifies what AI systems are being asked to do. Generation
can propose artifacts inside $\mathcal{D}$. Prediction can estimate
components of $\mathbf{J}$ before expensive feedback. Optimization can search
tradeoffs under $\mathcal{K}$. Critique and verification can apply $R$.
The architectural result is not any one of those operations. It is the claim
that survives the loop.

::: {#pri-state-the-claim .callout-design-principle title="State the claim as a review object"}
An AI-generated architectural result is credible only when the loop names its workload, baseline,
design space, objective, constraints, evidence, rejection rule, and decision
owner. Until it states those, the AI output is an artifact, not an architectural claim.
:::

## The Design Loop Is the Unit of Analysis

Once the claim is explicit, the next question is: what design loop can test it?
That shift matters because architecture work is not a single act of generation.
It is a repeated process of framing a problem, choosing abstractions, exploring
alternatives, measuring candidates, rejecting weak results, revising
assumptions, and deciding when evidence is strong enough to commit.

> **Architecture design loop.** An architecture design loop is the repeated
> process that carries architecture state through bounded actions, feedback,
> evidence, rejection, revision, and architect-owned commitment until it produces an
> artifact or a revised loop.

For Architecture 2.0, this is the loop an AI system enters. If its state,
actions, feedback, and stopping rules are implicit, the system is only
producing outputs, not participating credibly in architecture work.

For the lighthouse prompt, the distinction is immediate. A request for a
low-power, 64-bit RISC-V-based compute subsystem for XRBench-class mobile XR
under a 3\ W, 3\ nm-class low-power mobile envelope sounds compact. But the
prompt does not define the design loop. It does not say which workload traces
are authoritative, which vector operations matter, which memory hierarchy is
admissible, which software stack must run, which simulator is trusted, which
power model applies, which process assumptions are available, which
alternatives must be considered, or what evidence is enough to reject a
candidate. These are not details to add after a generative method responds. They are the
architecture problem.

In practice, the loop has at least the following elements. It has a
state: what is known about the workload, design, tools, constraints, and prior
evidence. It has actions: what can be changed, generated, queried, tuned, or
tested. It has observations: what the loop can see after an action. It has
objectives and constraints: what counts as progress and what is not allowed.
It has a feedback path: the measurement, simulation, synthesis report, trace,
review, or deployment signal returned by the environment. It has stopping and
escalation rules. It has decisions: accept, reject, revise, or request stronger
evidence. It has artifacts: reports, configurations, design descriptions,
plots, RTL fragments, benchmarks, or implementation plans.

A compact way to write the loop is
$$
s_{t+1} =
\operatorname{Update}(s_t, a_t, o_t, e_t, d_t).
$$
Here, $s_t$ is the represented architecture state, $a_t$ is the bounded
action taken by the loop, $o_t$ is the observation returned by the
environment, $e_t$ is the evidence ledger entry that makes the observation
auditable, and $d_t$ is the human or policy decision to accept, reject,
revise, or escalate. The equation is not claiming that every architecture
loop is a Markov decision process[^fn-markov-decision-process-c03]. It is a bookkeeping discipline: if a loop
cannot say how actions, feedback, evidence, and decisions update state, then
it is not yet represented well enough for credible AI-mediated architecture
work.

Architecture 2.0 uses that loop as the unit of analysis. A model is one
participant in the loop. It may generate candidates, summarize evidence,
predict outcomes, call tools, critique assumptions, or coordinate subtasks. But
the credibility of the result comes from the whole loop, not from the model in
isolation.

The cross-layer reach of architectural decisions is another reason the loop, not the model, is the unit of
analysis. An architecture decision moves through the whole stack at once: a
choice that is legal at the microarchitecture level can still force a new
compiler pass above it or trip a timing and routing bottleneck below it. The
model that proposes the choice sees only its own layer, while the consequences
ripple up into software and down into physical design. Representing those layers
as intertwined, rather than as isolated abstractions, is part of what the loop
has to carry, because that cross-layer state is what lets a reviewer reject a
candidate that looks valid in one layer but breaks another the model never saw.

## Design Spaces Make Claims Meaningful

An architectural claim is meaningful only relative to a design space. A system
that reports "the best" candidate without exposing the alternatives, invalid
regions, baseline, and tradeoffs has not made an architecture result easy to
review. It has hidden the comparison that gives the result meaning.

In architecture, the design space is not the set of all strings a model might
emit. It is a constrained set of legal choices:
$$
\mathcal{D} = \{x \in X \mid x \text{ is valid under the task, tool chain, and
constraints}\}.
$$
Here, $X$ is that unconstrained space of candidate artifacts, everything a
method could emit. The validity conditions may include ISA compatibility, memory semantics,
software support, timing assumptions, power limits, package constraints,
verification requirements, and deployment policy. A candidate outside
$\mathcal{D}$ is not a bold design. It is an invalid action unless the loop
explicitly revises the design space and records why.

The lighthouse prompt makes this concrete. A 64-bit RISC-V-based mobile XR
subsystem might vary vector width, cache and memory hierarchy, accelerator
partitioning, dataflow, clocking, voltage assumptions, compiler/runtime
support, and verification scope. Some choices are legal but unattractive. Some
are attractive under a proxy but fail at higher fidelity. Some violate the
power envelope, process assumptions, software contract, or workload coverage.
An Architecture 2.0 loop must represent those distinctions. Otherwise it cannot
know whether it is improving a design or exploiting a hole in the problem
statement.

The design space is also where multiobjective efficiency enters the ontology. The objective
is rarely a scalar reward. It is a vector of performance, energy, latency,
area, reliability, programmability, verification burden, cost, and evidence
requirements. A design-space report is therefore an evidence object: it should
show what was explored, what was rejected, what tradeoffs remain, and what the
architect must still decide.

## The Architecture 2.0 Ontology {#sec-arch2-ontology}

A method label is not enough to review an architecture claim. A paper can say
it uses an LLM, reinforcement learning, Bayesian optimization[^fn-bayesian-optimization-c03], or a surrogate
model and still leave the important state invisible: what task was bounded, what
actions were legal, what feedback was used, what failed, and who accepted the
commitment. A taxonomy groups things. It can list tasks, methods, benchmarks,
tools, system architectures, or evaluation settings. Taxonomies are useful, and
this chapter will use them where they help a reader make decisions. But a
taxonomy is not enough for a field that is still moving. Model interfaces will
change. Method harnesses will change. Benchmarks will change. EDA flows and
simulator stacks will change. If the book is organized only around today's
artifacts, it will age with them.

> **Architecture 2.0 ontology.** The Architecture 2.0 ontology names the
> entities and relationships that must exist for AI-mediated architecture work to
> be represented, acted on, evaluated, rejected, and committed by a human
> architect.

Two of those entities matter enough to name now, because the rest of the book
leans on them: the world model the loop reasons with, and the evidence ledger it
reasons from.

> **World model.** A world model is the loop's belief about how architecture
> actions change outcomes, whether that belief lives in a simulator, a learned
> surrogate, a cost model, or design rules. This chapter uses the term only at
> that working level; @sec-data-representations-world-models gives the canonical
> definition and shows what such a model must encode, scope, and keep credible.

> **Evidence ledger.** An evidence ledger is the durable record that ties
> a candidate to the feedback that evaluated it, the constraints it faced, and
> the decision that accepted or rejected it. To flatten the learning curve, consider these terms as the hardware equivalent of software CI/CD (Continuous Integration/Continuous Deployment): a *rejection gate* is analogous to a failing integration test that blocks a code merge, and an *evidence ledger* is analogous to the immutable test logs generated by a GitHub Actions run.

Read the chapter as a chain of loop obligations. The claim states what is at
stake; the ontology names the state, action, feedback, evidence, and decision
relationships; the checklist tests whether an automated system can act safely; and the
design-loop card records the contract for review.
Within this framework, architecture environments act as the tool-connected settings that
define legal actions, observable feedback, costs, failure modes, provenance, and
invalid-action behavior; @sec-architecture-environments-tool-interfaces gives
the canonical definition.

Zooming out, the ontology asks a deeper question: what entities must exist, and how must
they relate, for AI-mediated architecture work to be credible? The important
pieces are not only the nouns. They are the relationships. Intent constrains tasks.
Tasks determine what must be represented. Representation limits what the loop
can observe and modify. The world model encodes beliefs about how actions
change outcomes. Tools and environments define valid actions and measurable
feedback. Methods are selected for the task, representation, and feedback
budget. Feedback becomes evidence only when fidelity, provenance, uncertainty,
and relevance are understood. Human decisions accept, reject, revise, or
escalate the result.

This is why ontology should precede taxonomy. We should not first ask whether
a paper uses an LLM, reinforcement learning, Bayesian optimization, a surrogate
model, or a simulator wrapper. We should first ask what loop the work exposes.
What is the task? What state is represented? What actions are legal? What
environment returns feedback? What is the feedback budget? What evidence
supports the claim? What can reject the result? What does the architect still
decide? Once those questions are answered, a taxonomy of methods becomes
useful. Before that, method labels can hide more than they reveal.

The practical implication is not to build a chip-specific language model first.
A field becomes AI-addressable only when its objects of work, legal actions,
feedback, evidence, rejection rules, and commitment boundaries are represented
well enough for methods to act and for experts to judge. For architecture,
those objects are not only papers or text. They include workloads, design
states, tool configurations, invalid actions, failure records, fidelity levels,
and commitment decisions. That is why this book starts with an ontology of the
design loop rather than a catalog of current models.

## The Compact Five-Part Framework

@fig-ontology-chain asks what has to become explicit before an AI method can
participate in architecture work. Read it left to right as a chain of
obligations: intent bounds the task, representation and world model bound what
can be known, architecture environments return feedback, and the evidence
ledger plus human decision determine commitment.

![**The Architecture 2.0 ontology chain makes the loop explicit:** Intent, task, and design space define what work the loop is allowed to do; representation and world model define what the loop can know; tools and environments define valid action and feedback; compound methods act inside the loop; evidence and human decision determine whether an artifact is accepted, rejected, or used to revise the loop.](images/F4-ontology-chain){#fig-ontology-chain width="100%" fig-alt="Process diagram connecting intent, task, design space, representation, environment, methods, evidence, and human decision into an explicit Architecture 2.0 loop."}

The change is that the loop, not the model, becomes the review object; missing
links are reasons to withhold commitment rather than details to fill in later.

For practical use, this book compresses the ontology into five pieces. These
pieces group the same fields that the design-loop card records: intent, task,
design space, representation (which carries the world model), environment,
method role, feedback
budget, evidence, negative traces, rejection authority, commitment boundary,
and human decision.

First, there is *task, intent, and design space*. Intent states what the
architect or organization is trying to achieve, what constraints matter, what
risks are acceptable, and what cost of failure is tolerable. The task is the
bounded work unit that can be assigned, repeated, measured, or decomposed. The
design space states which choices are legal, which regions are invalid, and
which tradeoffs the loop is allowed to explore.

Second, there is *representation and world model*. A representation is
the encoded design state: specifications, workload traces, architecture
descriptions, graphs, RTL, compiler IR, simulator configurations, EDA reports,
benchmark metadata, tool logs, design documents, or review notes. A world model
is the loop's belief about how architecture actions change outcomes. It may be
explicit, learned, simulator-backed, symbolic, statistical, or partly implicit
in tools.

Third, there is the *architecture environment*. Tools become environments when
they define actions, observations, constraints, costs, rewards or objectives,
latency, provenance, and invalid-action behavior. An architecture simulator is
not merely a measurement device in such a loop. It is part of the state
transition and feedback system.

Fourth, there are *method roles*. The credible
unit is rarely a single model. It is a composition of roles: generator,
predictor, optimizer, searcher, critic, verifier, planner, tool caller, and
coordinator. Some roles may be played by language models, some by search
algorithms, some by learned surrogates, some by scripts, some by formal tools,
and some by humans.

Fifth, there is *feedback, evidence ledger, and human decision*. Feedback is
any signal returned by the loop. Evidence becomes useful when it is tied to
provenance, fidelity, assumptions, uncertainty, coverage, rejection, and a
decision. The decision is where the architect accepts, rejects, revises, or
escalates the result.

@tbl-compact-framework-checklist gives the checklist version. It is
the question a reader should be able to ask of a paper, benchmark, tool, or
internal loop before trusting an Architecture 2.0 claim.

| **Framework piece** | **Reader question** | **Lighthouse instance** |
| --- | --- | --- |
| Task, intent, and design space | What architectural objective is being pursued, under what constraints, risk, and legal choices? | Improve mobile XR efficiency within a 3\ W, 3\ nm-class low-power mobile envelope while exploring legal RISC-V, vector, memory, accelerator, and software-stack choices. |
| Representation and world model | What state is encoded, and what does the loop believe about how actions change outcomes? | Workload traces, parameters, compiler assumptions, power model, memory behavior, and constraints. |
| Architecture environment | What actions are legal, what feedback is returned, and what failures are observable? | Simulator, cost model, workload harness, and invalid-configuration checks. |
| Method roles | Which roles generate, predict, search, critique, verify, call tools, or coordinate? | Candidate generator, surrogate or search method, verifier, evidence writer, coordinator, and human reviewer. |
| Feedback, evidence ledger, and human decision | What supports the claim, what can reject it, and what remains an architect-owned commitment? | Pareto evidence, sensitivity checks, failure records, rejection authority, and final architectural judgment. |

: **The framework becomes a checklist when each loop state is explicit:** A project is easier to review when it names the task, representation, architecture environment, method roles, feedback, evidence ledger, rejection authority, and human decision before claiming autonomy or architectural progress. {#tbl-compact-framework-checklist tbl-colwidths="[20,36,34]"}

```{=latex}
\FloatBarrier
```

This checklist is intentionally stricter than many current demonstrations. A
system can be a useful demonstration while still not being a credible
Architecture 2.0 loop; unanswered rows identify where a method lacks action
bounds, evidence standards, rejection authority, or a human commit gate.

The practical artifact is the design-loop card introduced later in this chapter
and expanded in @sec-appendix-b-design-loop-card. The card is not a new concept
on top of the framework. It is the same framework compressed into a reusable
review object, with the five framework pieces serving as grouped views of the
card fields. @sec-appendix-b-design-loop-card also gives the card a
machine-checkable schema and four conformance levels, from context-only to an
independently rejectable loop, so "we used the card" becomes a claim a tool and a
reviewer can check rather than a gesture.

Beyond structuring the review process, the checklist also keeps the vocabulary from drifting into generic AI
language. Words such as state, action, observation, environment, reward, and
critic are useful only after they are translated into architecture objects.
@tbl-architecture-translation-matrix gives the translation rule.
If a paper says an automated method acts in an environment, the reader should be able to
name the architecture state it reads, the action it is allowed to take, the
tool feedback it observes, and the authority that can reject the result.

| **Generic term** | **Architecture translation** | **Example artifacts or observations** | **What can reject it** |
| --- | --- | --- | --- |
| State | Workload, design, software, tool, constraint, and evidence state. | Traces, configs, RTL, compiler IR, simulator stats, EDA reports, review notes. | Missing provenance or hidden assumptions. |
| Action | Legal architecture, compiler, runtime, or tool-flow change. | Change cache size, vector width, mapping, schedule, constraint, partition, or test. | Invalid parameter, noncompilable code, nonsynthesizable RTL, or policy violation. |
| Observation | Feedback returned by a tool, benchmark, review, or deployment path. | Latency, energy, area, timing, congestion, warnings, failures, telemetry. | Wrong workload, stale tool version, simulator mismatch, or weak fidelity. |
| Environment | Tool-connected harness that defines legal actions and feedback. | Simulator wrapper, compiler pipeline, RTL flow, EDA stage, benchmark harness. | Unmodeled constraints, nondeterminism, incomplete logging, or invalid actions. |
| Objective | Explicit architecture tradeoff, not a generic reward. | Performance, power, and area; tail latency; power envelope; reliability; carbon; cost; evidence budget. | Proxy gaming, lost Pareto tradeoff, or missing human decision rule. |
| Critic/verifier | Independent check that can challenge or reject a claim. | Tests, formal checks, baseline replay, cross-simulator comparison, signoff review. | Unsupported claim, failed check, counterexample, or insufficient evidence. |

: **AI loop terms need architecture translations:** Architecture 2.0 uses generic loop vocabulary only when each term is grounded in concrete hardware/software design objects, tool outputs, and rejection mechanisms. {#tbl-architecture-translation-matrix tbl-colwidths="[16,28,28,18]"}

The five pieces are not a pipeline that runs once. They form a loop. A failed
simulation may revise the representation. A weak benchmark result may revise
the task. A provenance problem may invalidate the evidence. A human rejection
may change the environment, not merely reject a candidate. Architecture 2.0 is
therefore not only about adding AI into existing work. It is about designing the
loop so that AI participation is bounded, observable, and accountable.

::: {.callout-architect-checkpoint title="The Loop Revision Gate"}
When an AI method fails or produces an invalid result, the architect must make a decision at the loop boundary: does the failure simply reject the candidate, or does it require revising the environment, design space, or evidence standard to keep the method bounded?
:::

## Autonomy Is Earned, Not Declared

The first stress test for the framework is autonomy. It is tempting to ask
whether Architecture 2.0 systems are autonomous. That question is too coarse.
Autonomy is not a personality trait of a model. It is a property of a bounded
loop, and broader autonomy must be earned by stronger evidence.

@fig-autonomy-ladder-human-agent shows four stages of allowed loop
authority. The point is not that the automated system gradually replaces the human
architect. The point is that each stage grants the AI participant a larger role only
when the loop also defines the allowed action space, feedback budget, evidence
standard, rollback or escalation path, and architect-owned commitment boundary. The human and the automated system
are both visible because Architecture 2.0 is a shared loop with asymmetric
responsibility: the AI participant may act inside the loop, but the architect owns the
boundary conditions.
The figure draws one automated participant to keep the contract legible. The same autonomy test
applies when the implementation uses several AI-assisted systems: every generated proposal,
tool call, critique, repair, verification, or coordination step must still be
bound to the loop's state, allowed actions, evidence obligations, rejection
path, and architect-owned commitment boundary.

![**Autonomy is earned by the loop:** Higher autonomy is a property of a bounded loop with explicit actions, feedback, evidence, rollback or escalation paths, rejection authority, and architect-owned commitment boundaries.](images/F4c-autonomy-ladder-human-agent){#fig-autonomy-ladder-human-agent width="100%" fig-alt="Ladder diagram showing autonomy rising only as actions, feedback, evidence, rollback or escalation paths, rejection authority, and architect-owned commitments become explicit."}

At the lowest level, AI systems support assisted exploration. They summarize
prior work, draft experiment scripts, explain tool output, suggest candidate
parameters, or help prepare design reviews. The architect still directly
drives the loop.

At the next level, AI systems provide coordinated intelligence. A model or
agent can call tools, track state, propose alternatives, compare candidates,
and route work among specialized components. The loop becomes more explicit,
but human approval remains frequent.

At a higher level, semiautonomous human-in-the-loop systems can perform bounded
subtasks: search a design space, tune a configuration, generate a benchmark
variant, build a surrogate, or identify invalid candidates. These systems need
clear action spaces, feedback budgets, logging, and rejection authority.

The strongest level is bounded autonomous ecosystems. Here, agents can adapt
parts of the loop, choose among methods, allocate feedback budget, and revise
representations within a constrained domain. Even then, autonomy is bounded by
commitment cost, evidence standards, and human accountability.

The stage of autonomy depends on architecture-specific risk. A compiler flag
that can be rolled back after telemetry is not the same as an RTL change that
affects timing closure. A simulator configuration is not the same as a
mask-level choice. A benchmark-generation loop is not the same as a signoff
loop. The more irreversible the action, the stronger the evidence and
rejection authority must be.

::: {.callout-architect-checkpoint}
Before granting an AI-driven loop a higher autonomy stage, confirm it defines:

- the allowed action space, and which actions are illegal;
- the feedback budget and evidence standard the stage requires;
- the rollback or escalation path when a candidate fails;
- the rejection authority that can still say no;
- the architect-owned commitment boundary the automated participant may not cross.

If any of these is missing, the autonomy is declared, not earned.
:::

With that stress test in place, the rest of the chapter walks through the
framework pieces in order.

## Intent Defines the Task

Architecture tasks do not appear naturally. They are carved out of messy
intent. A product goal such as "improve mobile XR efficiency" is not yet a task.
It must be translated into bounded work: characterize the workload, choose a
candidate ISA extension, compare vector and accelerator organizations,
estimate memory traffic, build a power model, explore clock and voltage
points, evaluate compiler support, or prepare a design-space report.

This translation is architectural judgment. It decides what is in scope, what
is out of scope, what can be measured, and what cost of being wrong is
acceptable. It also decides how ambitious an AI-assisted loop can be. A loop
that critiques a design report needs different state and evidence than a loop
that edits RTL. A loop that predicts energy needs different calibration than a
loop that generates workload questions. A loop that searches an accelerator
tiling space needs different invalid-action semantics than a loop that proposes
chiplet partitionings.

To ground this translation of intent into tasks, this book treats several task families as recurring: design-space exploration,
workload characterization, generation, prediction, optimization, critique,
verification, and benchmark construction. The list is not meant to be
exhaustive. Its purpose is to remind the reader that "use AI" is never a task.
The task must be bounded before the method can be chosen, and each family
becomes an Architecture 2.0 task only after its action space, feedback budget,
evidence standard, rejection rule, and owner are named. These are not content
categories; they are recurring loop shapes that differ in represented state,
legal actions, feedback cost, invalid-action semantics, escalation rules, and
ownership.

## Representations and World Models

Representation is the first hard problem because it determines what the loop
can see. Architecture knowledge lives in many forms: natural-language
specifications, ISA documents, traces, graphs, simulator configurations, RTL,
compiler IR, EDA reports, design reviews, benchmark metadata, spreadsheets,
scripts, and plots. Much of the most important state is implicit. It may live
in default flags, workload selection, tuned scripts, undocumented assumptions,
or the memory of the architect who knows why one experiment was abandoned.

AI systems are brittle around hidden state. If a constraint is not represented,
the automated optimizer may violate it. If a simulator option is undocumented, a result may
not be replayable. If rejected candidates are missing, a method may relearn
known failures. If benchmark provenance is unclear, a comparison may be
misleading.

A world model is different from a representation. The representation says what
is encoded. The world model says what the loop believes will happen when an
action is taken. A simulator embodies one kind of world model. A learned
surrogate embodies another. A set of design rules, expert heuristics, or
calibrated equations can also function as a world model. None is automatically
true. Each has a scope, fidelity, uncertainty, and failure mode.

Distinguishing between representations and world models helps clarify what we are testing. For example, QuArch, an architecture-centric benchmark dataset, is useful as a boundary test:
it can assess whether a model knows architecture concepts, but not whether an
automated participant has the represented workload, tool, action, evidence, and rejection state
needed to synthesize or reject a candidate
[@PrakashEtAl2025QuArch]. That distinction is the bridge to
@sec-data-representations-world-models.

## Tools Become Environments

Architecture tools become Architecture 2.0 environments when they define how an
automated participant or method can act. A simulator, compiler, profiler, RTL tool, EDA flow,
runtime system, or fleet telemetry pipeline does more than return a number. It
defines which actions are legal, how long feedback takes, what observations are
available, what costs are incurred, what provenance is recorded, and what
failure means.

@fig-tools-become-environments-preview turns the distinction into a visual
test: a wrapper connects a method to a tool, while an environment exposes the
contract that lets the loop audit action, feedback, failure, and rejection.

![**Tools become environments when the wrapper exposes a contract:** A tool wrapper is useful only when it returns more than a score. It must define legal actions, observations, cost and fidelity, provenance, invalid-action semantics, and rejection conditions so feedback can become architecture evidence.](images/F4e-tools-become-environments-preview){#fig-tools-become-environments-preview width="100%" fig-alt="Side-by-side diagram contrasting a basic tool wrapper that calls a tool and returns a score with an architecture environment that exposes legal actions, observations, cost and fidelity, provenance, invalid-action semantics, and rejection conditions."}

This is why wrapping tools is not mere engineering plumbing. The wrapper
defines the research question. If the action space permits invalid
configurations, the loop needs invalid-action semantics. If the observation
schema hides memory traffic, the loop cannot reason about data movement. If the
reward combines performance and energy without preserving the separate
components, the method may optimize a proxy that the architect cannot audit. If
the environment does not log tool versions, seeds, workload revisions, and
failed runs, the feedback may not become evidence.

Building on this need for principled tool wrappers, ArchGym, an open-source evaluation environment, is an important example because
it treats the connection between search algorithms and architecture simulators as
a first-class interface [@KrishnanEtAl2023ArchGym]. Its durable lesson is that a
simulator wrapper becomes architectural only when it exposes legal actions,
invalid-action semantics, feedback cost, provenance, comparable baselines, and
rejection conditions. @sec-architecture-environments-tool-interfaces expands
this point and asks what such environments can and cannot prove.

## Agents and Methods Have Roles in a Compound System

The word "agent" can hide too much. In credible Architecture 2.0 systems, there
may be several roles rather than one monolithic actor. A generator proposes
candidates. A predictor estimates behavior before expensive evaluation. An
optimizer chooses what to try next. A critic challenges assumptions. A verifier
checks constraints. A planner decomposes work. A tool caller executes actions.
A coordinator tracks state, provenance, and dependencies. A human architect
sets intent and decides what evidence is enough.

These roles can be implemented by different mechanisms. A language model may
draft an architecture description or critique a result. Bayesian optimization
may choose the next candidate. Reinforcement learning may learn a policy for a
bounded environment. A surrogate model may estimate energy or latency. A formal
tool may reject invalid behavior. A script may maintain the experiment ledger.
The important question is not which method is fashionable. The important
question is which role the method plays in the loop, what state it consumes,
what action it takes, what feedback it receives, and what evidence can reject
its output.

This role-based view is also more faithful to architecture practice. Even
before AI systems entered the discussion, architects already worked through
compound systems: simulators, models, scripts, profilers, spreadsheets,
benchmarks, reviews, and signoff processes. Architecture 2.0 makes that
compound structure explicit and asks where AI systems can participate without
erasing accountability.

## Feedback Becomes Evidence

Feedback is not evidence by default. A simulator result, benchmark score,
synthesis report, generated explanation, or model confidence value is feedback.
It becomes evidence only when it is tied to a claim, a decision, and a
provenance trail.

::: {.callout-lighthouse title="A 3 W claim needs evidence, not a number"}
**Context.** A reported power result is feedback. It becomes evidence only when
the loop records enough state for a reviewer to judge what the number means.

**In the Lighthouse prompt.** If a generative method claims that a "vector-capable CPU,
accelerator, or SoC block" for the "XRBench-class real-time mobile XR workload"
meets the "3\ W TDP target in a 3\ nm-class LP mobile process," the loop must
record the workload, input distribution, memory traffic, power model, process
assumptions, compiled software stack, rejected alternatives, uncertainty, and
rejection rule.

**Evidence rule.** The same power number has different authority as a proxy
estimate, cycle-level simulation, synthesis result, post-layout estimate, or
silicon measurement. A proxy estimate may support exploration; post-layout or
silicon evidence is needed before stronger implementation or deployment
commitments.

**Takeaway.** The design-space report must say which evidence level supports the
claim and which commitment boundary it has not crossed.
:::

Evidence also includes negative information. Rejected candidates, failed
simulator runs, invalid configurations, proxy wins that disappear at higher
fidelity, and assumptions that had to be abandoned are not waste. They are
architecture data. They tell the loop where not to go and tell the human
reviewer why a surviving candidate deserves attention.

This distinction between feedback and evidence is one of the main safeguards
against hype. Architecture 2.0 is not credible because a generative method can produce
outputs quickly. It is credible only when the loop can explain why an output
should be believed, what evidence would overturn it, and who has authority to
say no.

::: {.callout-architect-checkpoint title="The Feedback vs. Evidence Gate"}
Before committing a model-generated candidate, the architect must evaluate the decision gate:
- Does the loop provide a durable evidence ledger, or just a feedback score?
- What specific evidence would overturn this claim?
- Who holds the authority to say no?
If these are undefined, the AI output cannot pass the commitment boundary.
:::

## The Design-Loop Card

The ontology becomes operational through a design-loop card. The card is the
practical payload of the ontology: a compact way to describe a paper, project,
tool, benchmark, or internal loop. It asks for the loop, not only the
result.

@fig-design-loop-card-example shows a compact example for the
lighthouse prompt. The point is not that the card completes the design. The
point is that it exposes the state a credible loop must carry before any
generated candidate should be trusted.

![**A filled design-loop card turns a prompt into reviewable state:** The lighthouse prompt becomes explicit loop state: intent, task, design space, representation, environment, method role, feedback budget, evidence, failure records, rejection authority, commitment boundary, and human decision.](images/F4b-design-loop-card-example){#fig-design-loop-card-example width="100%" fig-alt="Filled design-loop card mapping the lighthouse prompt into fields such as intent, design space, representation, environment, feedback, evidence, failure records, rejection authority, commitment boundary, and human decision."}

The card is deliberately simple. Its purpose is not to create paperwork. Its
purpose is to reveal whether a claimed Architecture 2.0 contribution exposes
the loop that makes it credible. A paper that reports a better search result
but hides its feedback budget, rejected candidates, or environment validity is
hard to compare. A tool that produces designs but cannot say what rejects them
is hard to trust. A benchmark that measures model accuracy but not
architecture-relevant reasoning may be useful, but it should not be mistaken
for a complete design-loop evaluation.
Missing card fields are review outcomes, not formatting problems: ask for
evidence, escalate fidelity, reject the claim, or narrow the commitment until
the loop can support what it reports.

@sec-appendix-b-design-loop-card gives the full 12-field card and review
rubric. The important point here is that every major Architecture 2.0 claim
should be able to expose its loop.

## How the Rest of the Book Uses the Ontology

The remaining chapters unpack the ontology as missing conditions for credible
AI participation. @sec-data-representations-world-models asks what
architecture data must encode before AI systems can reason about it.
@sec-architecture-environments-tool-interfaces asks how simulators, compilers,
EDA flows, benchmarks, and deployment systems become action settings.
@sec-methods-generation-prediction-optimization asks which method roles are
valid under a feedback budget. @sec-feedback-verification-trust asks when
feedback becomes evidence strong enough for rejection and commitment.
@sec-running-the-loop runs one loop end to end on the lighthouse prompt.
@sec-loop-patterns-across-stack applies the framework across loop patterns in software, architecture
DSE, co-design, systems, and high-commitment silicon-facing work. @sec-what-architect-owns
returns to the architect: what remains nondelegable, what the community must
build, and what it would mean for Architecture 2.0 to become a discipline
rather than a collection of demonstrations.

The ontology is not a guarantee of correctness. It is a way to expose what
must be represented, measured, checked, rejected, and decided. That is why it
can outlast current models and tools. The lasting question is not which method
wins. The lasting question is how architects design loops that can synthesize
systems credibly.

### Open research questions

The ontology and framework proposed here map the known requirements for Architecture 2.0, but establishing them as standard practice exposes several unsettled research directions. The following open questions push beyond the current conceptualization to explore how these loops can be formalized, enforced, and scaled:

1. **How do we standardize a machine-readable format for cross-organizational design loop replay?**
   While this chapter introduces the design-loop card (@sec-appendix-b-design-loop-card) as a human-reviewable artifact, the unsettled challenge is scaling this to a formal, executable schema. Research is needed to determine how automated systems can automatically replay, verify, and compare architectural claims across different organizations, proprietary toolchains, and competing evidence standards.

2. **How can legacy EDA and simulation tools automatically enforce environment contracts?**
   Building on the concepts from tools as environments (@sec-architecture-environments-tool-interfaces), future research must determine how to retrofit decades of existing, opaque architecture infrastructure. We need robust methods for legacy tools to actively expose their legal actions and invalid-action semantics, ensuring an automated optimizer cannot silently exploit simulation inaccuracies to generate false claims.

3. **What is the canonical representation for negative architectural knowledge?**
   The ontology requires an evidence ledger that captures rejected candidates and failed assumptions (@sec-arch2-ontology). However, discovering how to efficiently encode and curate this "dark matter" of architectural design—such as proxy wins that fail at higher fidelity or abandoned design paths—into training datasets remains an open problem for developing more grounded AI systems.

4. **Can formal protocols cryptographically enforce human-owned commitment boundaries?**
   As autonomous loops approach higher levels of authority (@fig-autonomy-ladder-human-agent), we must push beyond policy-based rejection. A critical open question is how to develop rigorous, potentially cryptographically-enforced commit-gate protocols that mechanically prevent an automated system from moving a claim across fidelity boundaries without explicit, verified human authorization.

## What to carry forward
- **Reader test:** Can you review an AI-generated architectural claim through the loop that
  produced it: its environment, method roles, evidence ledger, rejection
  authority, and commitment boundary?
- **Next loop state:** The next chapter asks what representations and world models
  must encode before an AI-assisted loop can synthesize systems credibly.

[^fn-markov-decision-process-c03]: **Markov decision process (MDP)**: A mathematical framework for modeling decision-making where outcomes are partly random and partly under the control of a decision maker; it forms the foundation of reinforcement learning.
[^fn-bayesian-optimization-c03]: **Bayesian optimization**: A strategy for optimizing expensive black-box functions, where each candidate evaluation (such as a cycle-accurate simulation) is costly.
# Representations and World Models {#sec-data-representations-world-models}

```{=latex}
\abstract*{Representation is the first hard problem in Architecture 2.0. Automated optimizers cannot act credibly unless architecture work is made legible: workload state, architecture state, tool state, constraints, assumptions, provenance, feedback, and rejected alternatives must be captured in forms the loop can read, replay, compare, and revise.}
```

::: {.callout-crux}
What must architecture data record before an automated optimizer can act on it and a human
architect can audit the result?
:::

@sec-architecture-20-ontology defined the ontology. This chapter deepens
representation and world model, the piece that determines what every later
piece can see. That ordering is deliberate. It is
tempting to begin Architecture 2.0 by asking which model, agent framework[^fn-agent-framework-c04], or
optimization method to use. But a method can only act on what the loop can
represent. If the relevant workload, constraint, tool option, rejected
candidate, or uncertainty is invisible, a more capable model may simply move
faster in the wrong direction.

Fundamentally, this is a low-resource loop-state problem: the scarce resource is
not examples in the abstract, but records that bind intent, workload, tool
state, actions tried, failures, accepted evidence, and architect decisions.
Architecture does not need data in the same way a web language model needs text.
The durable question is therefore not only how to collect more architecture
data. It is how to represent scarce architecture data so that a loop can act on
it and a human can audit it.
The architectural risk is not just small data; it is that a generative method may infer
authority from public text where the actionable state was never recorded.

::: {.callout-learning-objectives}
After this chapter you can turn an architecture prompt, result, or artifact
into an actionable loop-state record for automation. That means you can:

- explain why architecture data is not web data: sparse, tool-bound, and full of state the final paper omits;
- treat a feedback event as a sample that carries cost, fidelity, and provenance;
- spot undocumented design state and the missing negative traces in an AI-assisted loop;
- identify when the human architect must accept evidence, reject candidates, escalate fidelity, and own residual risk;
- tell the optimizer's architecture representation apart from its world model.
:::

## Why Architecture Data Is Not Web Data

Many successful AI systems benefit from abundant public text, images, code,
logs, or interaction traces. Architecture work is different. Some useful
material is public: papers, textbooks, manuals, open-source tools, benchmark
descriptions, and selected design artifacts. But much of the state that makes
an architecture decision meaningful is not public, not standardized, and not
preserved in the final paper. Some of it is tacit knowledge: the design-review
habit that recognizes a fragile assumption, the instinct that a simulator
result is outside its calibrated regime, the memory of why a workload slice was
excluded, or the experience that a supposedly local change will become a
verification problem later.

The missing state matters. Workload traces may be proprietary or too large to
share. Simulator configurations may live in scripts rather than in the paper.
EDA reports may be confidential or tied to licensed process assumptions.
Labels may require expert judgment. Negative results are rarely published.
High-fidelity measurements may be slow, expensive, or unavailable until late
in the design process. The cost of a wrong action is also different. A weak
answer in a question-answering task may be corrected immediately. A weak
architecture proposal can consume weeks of simulation, mislead a design
review, or push effort toward a candidate that cannot survive synthesis,
timing, power, or software integration.

::: {.callout-lighthouse title="The AI prompt is not the loop state"}
Context. This chapter's representation question is visible in the first noun
phrase of the lighthouse prompt. A user sentence can name a workload and technology
target, but it does not yet represent the design state the loop can act on.

In the Lighthouse prompt. "64-bit RISC-V-based compute subsystem" and
"XRBench-class real-time mobile XR workload" cannot be answered from public text
alone. XRBench gives a workload anchor [@KwonEtAl2023XRBench], and RISC-V gives
a software-contract anchor.

Representation. The AI-assisted loop must also record the scenario, input distribution,
frame deadline, candidate compute organization, SoC boundary, software stack,
ISA and ABI assumptions, compiler choices, memory behavior, power model, process
assumptions, verification and reliability status, deployment context, and rejected
alternatives.

Takeaway. Treat the user's prompt as an index into missing loop state. An
automated design-space report is credible only when the representation carries enough
provenance, coverage, and negative traces for a human architect to audit.
:::

This is why internet-scale recipes transfer poorly if they are used naively.
Architecture data is sparse, expensive, tool-bound, and full of hidden
constraints. @tbl-web-vs-arch-data makes the contrast explicit.

| Dimension | Web Data (Internet-Scale AI) | Architecture Data (Architecture 2.0) |
| --- | --- | --- |
| Abundance | Hundreds of trillions of tokens. | Sparse; bound by slow simulation and engineering time. |
| Format | Mostly unstructured text, code, and images. | Heavily state-based: tool flags, workloads, constraints, negative traces. |
| Visibility | Publicly accessible (scraped corpora). | Often proprietary, tacit, or lost after publication. |
| Feedback Cost | Cheap (e.g., fast automated grading or immediate user correction). | Expensive (hours/days of cycle-level simulation or physical synthesis). |
| Cost of Failure | Low (a poor chat response is easily ignored). | High (a poor design choice wastes compute budgets or fails timing). |

: Web Data vs. Architecture Data: Internet-scale assumptions fail in architecture because the data regime is fundamentally different in scale, structure, cost, and visibility. {#tbl-web-vs-arch-data tbl-colwidths="[20,40,40]"}

The right response is not despair. It is representation design:
make the state explicit enough that methods can act within the boundaries of
what is known, what is assumed, and what must still be checked. Representation
design has two halves: the representation that records that state, and the world
model that predicts what acting on it will do.

> **Architecture representation.** An architecture representation is the
> record of workload state, design state, tool state, constraints, assumptions,
> evidence, uncertainty, negative traces, and decisions that a loop can read,
> compare, change, replay, and audit.

> **Architecture world model.** An architecture world model[^fn-world-model-c04] is the loop's
> belief about what will happen when an architecture action is taken: what a
> simulator, surrogate, rule system, or constraint model
> predicts, permits, rejects, or leaves uncertain. Human review is not part of the
> world model; it is an external rejection authority that acts on the model's output.

The boundary test in @tbl-representation-world-model-boundary is simple. A
representation records the state a loop can read and replay. A world model
predicts or constrains the consequences of acting on that state. The same
artifact can contribute to both, but the loop must know which role it is
playing.

| Example | Representation role | World-model role |
| --- | --- | --- |
| Simulator configuration | Records flags, model version, workload slice, seed, and command. | Defines what behavior the simulator can predict and where its calibration fails. |
| Candidate parameter table | Records legal choices and candidate values. | Feeds a surrogate or rule system that predicts latency, energy, area, or invalidity. |
| Constraint file | Records declared limits and assumptions. | Rejects actions that violate timing, power, interface, or policy boundaries. |
| Failed run log | Records what happened, with provenance. | Updates the loop's belief about invalid regions and escalation rules. |

: Representation records state; world models predict consequences: The loop needs both, and it must not confuse replayable artifacts with evidence that an action will remain valid under new workloads, tools, or fidelity levels. {#tbl-representation-world-model-boundary tbl-colwidths="[20,35,35]"}

To see why we cannot simply extract this state from internet-scale text, the token count makes the contrast sharper. A broad corpus built from roughly
fifty years of public computer-architecture, systems, and EDA literature might
only be on the order of $10^9$ tokens. The bounds are driven by the simulation speed:
$$
T_{\mathrm{arch\text{-}text}}
\approx
N_{\mathrm{artifacts}} \times \bar{t}_{\mathrm{artifact}}
\approx
10^5 \times 10^4
\approx 10^9 \ \mathrm{tokens}.
$$
That sounds large, but it is small by web-scale pretraining[^fn-pretraining-c04] standards.
More importantly, it is incomplete in the wrong way. Papers preserve accepted
claims far better than failed
configurations, simulator flags, workload revisions, EDA reports, review
arguments, and rejected alternatives. Architecture 2.0 therefore cannot treat
"all architecture text" as the dataset. The dataset must include the loop
state that made the text credible, and it must expose enough tacit judgment to
make assumptions, exclusions, and rejection decisions inspectable.
The token count matters only because it limits what a generative method can infer about
action authority: text may retrieve concepts, but it cannot recover which
candidate was legal, what feedback was observed, why alternatives were rejected,
or who accepted the risk.

The math yielding $10^9$ tokens is an intuition-scale receipt, not a measured corpus inventory.
@tbl-architecture-data-scarcity shows why the exact token count is not the main
claim. The important scarcity is that the most useful architecture data are
often not public, not textual, or not preserved as reusable loop state.

| Data layer | Rough public visibility | What is missing for Architecture 2.0 |
| --- | --- | --- |
| Published papers, manuals, and tutorials | Public and mostly textual. | Failed runs, rejected alternatives, exact workload slices, scripts, seeds, and review rationale. |
| Open-source RTL, simulators, compilers, and benchmarks | Public but heterogeneous and version-sensitive. | Tool settings, run provenance, invalid configurations, and cross-tool disagreement. |
| Commercial EDA reports, PDK assumptions, and signoff context | Often private or redacted. | Timing, power, physical, waiver, and closure evidence tied to the claim. |
| Design reviews and engineer memory | Usually tacit. | Why an experiment was abandoned, which proxy was distrusted, and who accepted risk. |

: Architecture data scarcity is about missing loop state, not only token count: Public text is useful, but the decisive records are often provenance, negative traces, tool settings, and commitment decisions. {#tbl-architecture-data-scarcity tbl-colwidths="[26,28,36]"}

To visualize just how small the public-text estimate is, @fig-token-scale-contrast puts the architecture token count on the same log-scale
axis as three public AI-data anchors: the 1.4 trillion tokens used to train
DeepMind's Chinchilla model, Meta's report that Llama 3.1 405B was trained on more than 15 trillion
tokens, and a public human-text-stock estimate on the order of hundreds of
trillions of tokens
[@HoffmannEtAl2022Chinchilla; @MetaAI2024Llama31; @VillalobosEtAl2024DataLimits].
The point is not that architecture should race to scrape the web. The point is
that even a generous public architecture-text estimate is tiny by modern
pretraining standards, while the most important missing records are not ordinary
text at all.

```{python}
#| label: fig-token-scale-contrast
#| fig-cap: |
#|   Architecture text is small by web-scale standards: The missing architecture data are reusable loop-state records, not just more public text.
#| out-width: "100%"
#| fig-alt: "Scale comparison plot showing that public architecture text is small relative to web-scale language-model corpora, while important loop-state records are often missing."

import matplotlib.pyplot as plt
from _python.arch2_plots import COLORS, add_note_box, apply_style, row_axis, top_log_axis

rows = [
    {"display_label": "architecture corpus receipt", "display_note": "100k artifacts x 10k tokens", "right_label": "1B", "tokens": 1_000_000_000, "color": COLORS["blue"]},
    {"display_label": "Chinchilla training run", "display_note": "Hoffmann et al. 2022", "right_label": "1.4T", "tokens": 1_400_000_000_000, "color": COLORS["green"]},
    {"display_label": "Llama 3.1 405B pretraining", "display_note": "Meta reports over 15T tokens", "right_label": ">15T", "tokens": 15_000_000_000_000, "color": COLORS["orange"]},
    {"display_label": "public human text stock", "display_note": "Villalobos et al. 2024 scale anchor", "right_label": "~400T", "tokens": 400_000_000_000_000, "color": COLORS["purple"]},
]

apply_style()
fig, ax = plt.subplots(figsize=(4.65, 2.35))
fig.subplots_adjust(left=0.43, right=0.86, top=0.78, bottom=0.30)

row_axis(ax, len(rows))
top_log_axis(
    ax,
    xlim=(1e8, 1e15),
    xticks=[1e8, 1e9, 1e12, 1e15],
    xticklabels=[r"$10^8$", r"$10^9$", r"$10^{12}$", r"$10^{15}$"],
    xlabel="log-scale token count",
    tick_fontsize=6.5,
)

for y, row in enumerate(rows):
    token_count = row["tokens"]
    color = row["color"]
    ax.axhline(y, color=COLORS["row"], linewidth=0.7, zorder=0)
    ax.hlines(y, 1e8, token_count, color=color, linewidth=2.2, zorder=2)
    ax.scatter([token_count], [y], marker="s", s=18, facecolor=COLORS["note_fill"], edgecolor=color, linewidth=0.9, zorder=3)
    ax.text(-0.70, y - 0.12, row["display_label"], transform=ax.get_yaxis_transform(), ha="left", va="center", fontsize=6.8, fontweight="bold", color=COLORS["ink"], clip_on=False)
    ax.text(-0.70, y + 0.18, row["display_note"], transform=ax.get_yaxis_transform(), ha="left", va="center", fontsize=5.5, color=COLORS["muted"], clip_on=False)
    ax.text(1.04, y, row["right_label"], transform=ax.get_yaxis_transform(), ha="left", va="center", fontsize=6.8, fontweight="bold", color=color, clip_on=False)

add_note_box(fig, "The missing architecture data are loop-state records,\nnot only more public text.", xywh=(0.09, 0.055, 0.82, 0.13), fontsize=6.3)

plt.show()
plt.close(fig)
```

@tbl-architecture-data-receipt makes the receipt explicit. It is
not a measured corpus inventory. It is a scale check that separates the easy
counts from the hard missing records. The multiplication that gives $10^9$
tokens is deliberately simple; the point is that even a generous public-text
corpus is small, and the public surfaces we can count most easily are not the
same thing as architecture loop state.
Treat the counts themselves as a release-time snapshot, not a durable
benchmark.

| Receipt | Current value | What it supports | Caveat |
| --- | --- | --- | --- |
| Public architecture, systems, and EDA artifacts | $10^5$ paper-equivalent artifacts | Order-of-magnitude basis for the $10^9$-token scale check. | Assumption for intuition; not a measured corpus boundary. |
| Tokens per paper-equivalent artifact | $10^4$ tokens per artifact | Transparent multiplication: $10^5 \times 10^4 = 10^9$. | Tokenization and artifact length vary; manuals and specifications can be much larger. |
| DBLP title pilot | 1,015 title records from selected ISCA, MICRO, HPCA, and ASPLOS years | Shows that public metadata is easy to collect and useful for trajectory signals. | Title-only pilot; not full text, artifacts, tool state, or design-loop evidence. |
| GitHub RTL language proxy | 141,288 Verilog repositories; 43,371 SystemVerilog repositories | Shows a large public RTL-adjacent surface that could seed artifact mining. | Broad language counts include small, toy, forked, stale, and non-architecture repositories. |
| GitHub RTL keyword proxy | 4,292 Verilog+"rtl" repositories; 1,657 SystemVerilog+"rtl" repositories | Gives a narrower proxy for RTL-oriented repositories. | Keyword-sensitive and unvalidated; it is still not a count of usable architecture design examples. |
| GitHub topic proxy | 353 computer-architecture-tagged Verilog repositories; 1,817 FPGA-tagged Verilog repositories | Shows that curated labels are much smaller than broad language counts. | Topic labels are voluntary, incomplete, and uneven across projects. |
| Missing loop-state records | Not counted | The highest-value architecture data are traces, configs, logs, reports, reviews, negative results, and rejected candidates. | Much of this state is private, tacit, uncodified, or discarded before publication. |

: The architecture-data receipt is an assumption log, not a corpus claim: The current \(10^9\)-token estimate comes from transparent back-of-the-envelope assumptions, while the available mining signals are artifact proxies. GitHub counts are single Search API snapshots and drift over time. {#tbl-architecture-data-receipt tbl-colwidths="[23,19,26,22]"}

The useful lesson from the receipt is the mismatch. A title corpus can help
map topic drift, but it cannot recover simulator flags, failed configurations,
or review arguments. A Verilog repository count can show that public RTL-like
material exists, but it does not say whether the repository contains a
well-specified architecture decision, a reusable testbench, a valid workload,
or evidence that rejected alternatives were considered. Architecture 2.0
therefore needs corpus building only when artifacts are converted into loop
records: candidate, workload, tool version, legal and invalid actions, feedback,
provenance, rejected alternatives, and decision owner.

Domain adaptation matters here only if it helps construct or retrieve loop
records; vocabulary and retrieval gains do not grant an automated optimizer action authority.
The medical AI lineage is a useful comparison because it shows both the power
and the limit of domain adaptation[^fn-domain-adaptation-c04]. BioBERT adapted a general language model
to biomedical text; ClinicalBERT adapted representations to clinical notes;
Med-BERT adapted BERT-style pretraining to structured electronic health
records rather than ordinary prose
[@LeeEtAl2020BioBERT; @HuangEtAl2019ClinicalBERT; @RasmyEtAl2021MedBERT].
Those systems mattered because they treated the domain's data format as a
first-order problem. Chip design has its own instance. ChipNeMo adapts language
models to hardware-design text with a custom tokenizer, domain-continued
pretraining[^fn-pretraining-c04-2], and retrieval over internal corpora, then applies them to
engineering question-answering, electronic-design-automation script drafting,
and bug-report summarization [@LiuEtAl2023ChipNeMo]. It demonstrates that domain
adaptation can improve text-facing hardware tasks, and it illustrates the limit
this chapter presses: it maps text to text, so it addresses the data-ingestion
problem, not action authority in a closed design loop. Architecture must do
the same domain work, but the representation burden is broader. A
compute-subsystem design loop needs not only domain terms, but also executable
tool state, workload provenance, constraints, multi-fidelity feedback, rejected
alternatives, and decision authority. A paper corpus can bootstrap knowledge;
it cannot by itself represent the design loop.

Moving from training text to evaluation, benchmark lineages such as SQuAD and GLUE[^fn-squad-and-glue-c04] offer a
related lesson: shared, scoreable examples can move a whole field. The
Architecture 2.0 lesson is not to seek a cheap labeled row,
but to ask what a shared evaluation object must record before an automated optimizer can act.
Architecture needs shared evaluation objects too, but their purpose is not only
scoring models; it is constraining what an automated optimizer may try next, what evidence
can update the loop, and what a human reviewer can reject. An architecture
"example" is rarely just a cheap labeled row. It may
be a simulator run, a synthesis run, a physical-design report, a workload
trace, a failed configuration, or an expert review tied to a specific fidelity
level. The cost of a sample is therefore part of the representation problem,
not an afterthought.

## Sample Cost Is Architecture Data

In many benchmark settings, a sample is treated as an input-output pair: a
question and answer, an image and label, a prompt and reference response. In an
architecture design loop, a sample is better understood as a feedback event
that changes what the loop believes. It might be a cycle-level simulation, a
compiler report, a failed synthesis run, a power estimate, a rejected
floorplan, an expert review, or a silicon measurement. Each event has a cost,
fidelity, provenance, and commitment level.

> **Architecture sample.** An architecture sample is any feedback event
> that changes the loop's belief about a design candidate, including its cost,
> fidelity, provenance, assumptions, rejected-space coverage, and commitment
> level.

For an automated design loop, sample cost is part of the action policy: it
determines which evaluations are cheap enough to explore, which require
escalation, and which decisions should remain human-owned.

::: {.callout-architect-checkpoint title="Architect Checkpoint: The Cost of Fidelity"}
Before the loop consumes days of compute on a cycle-accurate simulation or physical synthesis run, it must hit a fidelity gate. The architect must own the decision to authorize expensive, high-fidelity samples, balancing the exploration budget against the cost of the feedback event.
:::

```{=latex}
\begin{samepage}
```
A useful representation should therefore record the burden and evidence context
of feedback, not only the feedback value. A sample is best written as a vector
of incommensurable dimensions, not a single number, since they do not share
units:
$$
\begin{aligned}
M_{\mathrm{sample}} = \langle\, & C_{\mathrm{setup}}, C_{\mathrm{tool}}, C_{\mathrm{license}}, C_{\mathrm{compute}}, C_{\mathrm{human}}, \\
& F_{\mathrm{fidelity}}, P_{\mathrm{provenance}}, K_{\mathrm{coverage}}, C_{\mathrm{opportunity}}, C_{\mathrm{risk}} \,\rangle .
\end{aligned}
$$
```{=latex}
\end{samepage}
```

The vector does not collapse into one currency; its dimensions carry different
units. It is a reminder that an architecture sample carries hidden state. A
simulator point may require setup time, tool availability, license access,
calibration work, human triage, provenance, coverage context, and the
opportunity cost of not evaluating another candidate. A post-layout result may
carry higher fidelity but also higher latency and risk. A field deployment
measurement may be authoritative for one population and irrelevant for another.

Concrete architecture tools span this range. Analytical mapping and dataflow
models are designed for broad design-space exploration
[@ParasharEtAl2019Timeloop; @KwonEtAl2019MAESTRO]. Physical-design and
verification flows expose the other end of the spectrum, where feedback can
take hours or days and the human and engineering cost becomes part of the
sample itself
[@MirhoseiniEtAl2021GraphPlacement; @SemiconductorIndustryAssociation2026ChipDesign; @BauerEtAl2020SemiconductorDesignManufacturing; @Foster2022WilsonVerificationStudy].
@tbl-sample-cost-regimes is therefore not a tool taxonomy. It is a
representation checklist: if the row changes, the loop must record different
state.

| Feedback source | Latency / cost intuition | What it exposes | Record for reuse |
| --- | --- | --- | --- |
| Analytical model or mapper | Milliseconds to seconds; low direct cost; high model-risk exposure. | Useful for pruning and sensitivity checks, not final evidence. | Model assumptions, workload slice, constraints, and proxy-validity notes. |
| Trace, profile, or replay | Seconds to hours depending on capture and replay setup. | Workload provenance is part of the sample. | Trace version, sampling policy, software stack, and filtering choices. |
| Cycle-level simulation | Minutes to days depending on model detail and target workload. | Simulator evidence is scoped by abstraction, calibration, and unsupported states. | Simulator version, configuration, seeds, workload revision, and calibration notes. |
| RTL, gate, or EDA feedback | Hours to days when synthesis, timing, power, or physical feedback enters the loop. | High-fidelity samples are scarce and multiobjective. | Tool versions, constraints, process assumptions, waived warnings, and rejected candidates. |
| FPGA, emulation, or prototype | High setup and shared-resource cost; high throughput once mapped. | Speed changes observability and debugging semantics, not only wall-clock time. | Mapping constraints, observability limits, debug hooks, and queue/resource state. |
| Silicon or field telemetry | Weeks to years and high commitment. | Authoritative measurements still require context and human decision authority. | Population, deployment version, rollback policy, incident context, and decision owner. |

: Architecture samples carry cost, fidelity, and commitment: A feedback event is useful only when the representation records what it cost, what assumptions it used, and what future decision it can support or reject. {#tbl-sample-cost-regimes tbl-colwidths="[20,24,24,22]"}

For tools like simulators, the timing side of this cost is multiplicative. A simulator is not slow in the abstract; it
is slow relative to the target cycles the workload demands. For a target clock
$f_{\mathrm{target}}$, workload duration $T_{\mathrm{workload}}$, and
simulation throughput $R_{\mathrm{sim}}$, the wall time is
$$
T_{\mathrm{wall}} =
\frac{N_{\mathrm{cycles}}}{R_{\mathrm{sim}}}
= \frac{f_{\mathrm{target}} \times T_{\mathrm{workload}}}{R_{\mathrm{sim}}}.
$$
@tbl-simulation-time gives the intuition for a 1 GHz
target. Read each row as a span of target execution time, each column as a
simulator throughput, and each cell as the wall-clock time to simulate that
span: one second of a 1 GHz target takes about 11.6 days at 1 kcycle/s but only
10 s at 100 Mcycle/s. The rates are illustrative, but the multiplication is the
point: a loop can afford many cheap proxy samples, fewer cycle-level samples,
and very few high-fidelity samples unless it has a disciplined plan for
escalation and rejection.

```{python}
#| output: asis
#| echo: false
import math


def human_time(s):
    if s < 60:
        return f"{s:g} s"
    m = s / 60
    if m < 60:
        return f"{m:.1f}".rstrip("0").rstrip(".") + " min"
    h = s / 3600
    if h < 24:
        return f"{h:.1f}".rstrip("0").rstrip(".") + " h"
    d = s / 86400
    if d < 365:
        return f"{d:.1f}".rstrip("0").rstrip(".") + " days"
    y = d / 365
    return (f"{y:.1f}".rstrip("0").rstrip(".") if y < 10 else f"{y:.0f}") + " years"


def sci(x):
    e = int(math.floor(math.log10(x)))
    m = x / 10 ** e
    return f"$10^{{{e}}}$" if abs(m - 1) < 0.05 else f"${m:g}\\times 10^{{{e}}}$"


freq = 1e9
workloads = [("1 ms", 1e-3), ("1 s", 1.0), ("1 min", 60.0), ("1 h", 3600.0)]
rates = [("1 kcycle/s", 1e3), ("100 kcycle/s", 1e5), ("10 Mcycle/s", 1e7), ("100 Mcycle/s", 1e8)]

rows = [
    "| Target workload at 1 GHz | Target cycles | " + " | ".join(r[0] for r in rates) + " |",
    "|:--|:--|" + "|".join([":--:"] * len(rates)) + "|",
]
for wname, dur in workloads:
    cyc = freq * dur
    cells = " | ".join(human_time(cyc / rate) for _, rate in rates)
    rows.append(f"| {wname} | {sci(cyc)} | {cells} |")
rows.append("")
rows.append(
    ": Target cycles turn simulator throughput into wall-clock pressure: even "
    "simple workloads become expensive when target execution time is multiplied by "
    "target frequency and divided by simulation throughput. Wall-clock values are "
    "computed from the cycle count and rate. {#tbl-simulation-time}"
)
print("\n".join(rows))
```

This cost structure changes how we should think about design spaces. A small
co-design exercise with five workload slices, four architecture configurations,
and six compiler or mapping settings has $5 \times 4 \times 6 = 120$
candidates and can sometimes be enumerated. A physical-design, compiler,
mapping, or chiplet-integration space may be combinatorial, sequential,
tool-bound, and partially invalid.
Learning-assisted chip placement makes the point concrete: the design problem
can be formulated as a learning problem, but the value of each sample depends
on the representation of macros, nets, constraints, tool feedback, and
placement validity [@MirhoseiniEtAl2021GraphPlacement]; that result was later
contested on its baselines and reproducibility (@sec-feedback-verification-trust)
[@ChengEtAl2023AssessmentRL], which only sharpens the point. The architecture
lesson is broader than placement. When samples are expensive, the loop record
must capture what each sample cost, what region of the space it informs, what it
rules out, and how it should constrain the next optimizer action.

@sec-methods-generation-prediction-optimization returns to sample efficiency from the method side. The representation
lesson comes first: if cost, fidelity, and rejected-space coverage are not
recorded, a later optimizer cannot know whether it is learning the design
space or merely collecting disconnected measurements.

## Architecture Descriptions as Boundary Objects

All of that recorded state has to live somewhere the loop and the architect can
both read, and that artifact, the architecture description, is a boundary
object. In the sense introduced by Star and Griesemer, a boundary object is
shared across communities while still supporting their different local uses
[@StarGriesemer1989BoundaryObjects]. It sits between human intent and tool action. It must be readable enough for architects to inspect, precise
enough for tools to execute, and structured enough for automated optimizers or methods to
modify without breaking the design contract.

At minimum, an architecture description should make the action contract
explicit: what is being described, what can change, what must not change, what
evidence can update the record, and which tools can consume it. For a
memory hierarchy, this may include cache sizes, associativity, replacement
policy, prefetching, coherence assumptions, bandwidth, latency, and workload
mix. For an accelerator or compute subsystem, it may include supported
operations, data layout, local storage, vector width, dataflow, quantization,
compiler/runtime assumptions, and fallback behavior.
For an optimizer-facing architecture description, the minimum is not only fields but
permissions: which fields are mutable, which are read-only constraints, which
tool observations can update them, and which violations trigger rejection or
escalation.

The important point is not that every representation must be one universal
schema. Different loops need different representations. A paper-reading loop,
a simulator-driven design-space exploration loop, an RTL-generation loop, and
a post-silicon telemetry loop should not have identical records. But they do
need explicit invariants. What fields must be present? Which fields can a
method change? Which fields are read-only constraints? Which assumptions
travel with a result? Which tool versions, seeds, and workload revisions are
required for replay?

Without those boundaries, a representation becomes a prompt-shaped anecdote.
It may sound plausible, but it cannot safely drive action.

## Unstructured Design Data and Its Cost

When those boundaries are left implicit, the missing structure does not stay
free. Architecture teams accumulate undocumented design state, the same kind of
hidden cost that software teams call technical debt when complex data
dependencies and implicit assumptions go unmanaged [@SculleyEtAl2015Hidden].
The cost appears whenever
important design state exists but is not captured in a durable, inspectable
form. It may live in shell scripts, simulator flags, spreadsheet formulas,
plotting notebooks, benchmark directories, issue threads, email, review
slides, or the memory of the person who knows why one candidate was rejected.
Some of this state is tacit rather than textual: what an experienced architect
chooses not to try, which proxy result they distrust, which corner case they
ask about in review, and which risk they refuse to delegate.

This gap is manageable when a small team manually coordinates the loop. It
becomes a technical failure when an AI system acts inside the loop. If a
constraint is implicit, the method may violate it. If a simulator flag is
hidden, the result may not be replayable. If rejected candidates are missing,
the search may rediscover known failures. If workload provenance is unclear,
the loop may optimize for the wrong distribution. If plots preserve only the
winning candidate, the evidence trail cannot explain why alternatives were
discarded.

::: {.callout-field-note title="The un-rerunnable result"}
An architecture team reports a strong design-space result, then asks an automated script to reproduce it six
months later to seed a new search. The winning configuration survives in a plot, but the simulator
version has moved, a default flag has changed, the workload trace has been
re-cut, and the script that generated the run lived on a laptop that has since
been reimaged. The number was real; the loop state that produced it was not recorded.
The fix is not human heroics at reproduction time. It is recording the tool version,
seed, flags, workload revision, and exact command as the run happens, so the
result stays auditable and actionable for the automation that inherits the design loop.
:::

To show where this missing information typically hides, @tbl-representation-debt gives common sources of undocumented
design state. The point is not to document everything for its own sake. The point is
to capture enough state that a loop can compare, replay, reject, and revise.

| Artifact | What it enables | What it often hides | Failure mode |
| --- | --- | --- | --- |
| Paper or plot | Claim, result, and comparison. | Tool flags, failed candidates, tuning history. | Reproduce only the story, not the loop. |
| Workload trace | Concrete input behavior and measurements. | Coverage, versioning, sampling policy, privacy filters. | Optimize for an unrepresentative slice. |
| Simulator config | Replayable model setting. | Defaults, unsupported states, calibration limits. | Trust a number outside its valid scope. |
| RTL or EDA report | Implementation-facing feedback. | Process assumptions, constraints, waived warnings. | Accept an artifact that cannot close. |
| Review notes | Human judgment and rationale. | Tacit assumptions and discarded alternatives. | Lose why a decision was made. |
| Rejected candidate | Search boundary and negative evidence. | Why it failed and at what fidelity. | Rediscover known dead ends. |

: Architecture artifacts become reusable loop data when they are representation records: Each artifact should carry enough provenance, assumptions, constraints, and validity information for a loop to act on it and for a reviewer to audit it. {#tbl-representation-debt tbl-colwidths="[22,27,25,18]"}

## QuArch as a Stress Test

The artifacts in @tbl-representation-debt are internal and often unstructured.
Public benchmarks sit at the opposite extreme, well structured but paper-bound.
QuArch, a question-answering benchmark that turns the architecture literature
into a structured, expert-validated evaluation object [@PrakashEtAl2025QuArch],
is a useful stress test for this chapter precisely because it exposes what that
public structure still leaves out. It bridges two representation layers,
architecture knowledge that can be asked about in text and architecture state
that must be carried by a loop before an automated optimizer can act. The later QuArch reasoning benchmark makes the
same point more explicit by organizing 2,671 expert-validated questions around
recall, analysis, design, and implementation competencies
[@PrakashEtAl2025QuArchReasoning]. QuArch can ask whether a model recalls
concepts, tracks architectural relationships, reasons over published claims,
and avoids obvious domain mistakes. That is valuable. A field cannot build
credible AI-assisted systems if those systems lack basic architectural knowledge.

@fig-quarch-boundary-test shows why that achievement is necessary but not
sufficient: paper-derived questions test one layer of architecture data, while
action and rejection require loop-state records that papers often omit.

![QuArch is a boundary test, not the whole data layer: Question-answering benchmarks can test architectural knowledge from papers, but Architecture 2.0 also needs loop records: tool configurations, failed runs, constraints, provenance, rejections, and review notes.](images/F5b-quarch-boundary-test){#fig-quarch-boundary-test width="100%" fig-alt="Two-panel diagram showing a paper-knowledge layer with concept recall, published relationships, and paper-level reasoning separated from a loop-state layer with tool configs, constraints, failed runs, provenance, rejections, and review notes."}

As this boundary test highlights, the limit of paper-derived datasets like QuArch is that papers preserve
accepted claims far better than they preserve design-loop state. They rarely
contain every simulator configuration, rejected candidate, failed run, hidden
constraint, calibration choice, or review argument. A model that answers
questions over papers may know what a concept means and still lack the state
needed to act inside a design loop. It may summarize a memory-system paper,
but it does not necessarily know which candidates failed, which simulator
flags were decisive, which workload slices were excluded, or which result
would cause a human architect to reject the next proposal.

The lesson is not that question-answering datasets are insufficient and
therefore unimportant. The lesson is that they occupy one layer. They help
represent architectural knowledge. Architecture 2.0 also needs representations
of experiments, tools, constraints, provenance, and negative traces. A reader
should see QuArch as one example of bootstrapping the data layer, not as the
whole data layer.

## Toward Architecture World Models

Representation records what the loop knows; the world model, the second half of
the pairing, is what turns that record into predicted consequences. The
world-model idea becomes architecture-specific when it is tied to tool
behavior, cost, constraints, invalid-action rules, uncertainty, and decision
policies.

This distinction matters. A simulator configuration is part of the
representation. The simulator's behavior, scope, calibration, and failure
modes are part of the world model. A table of candidate parameters is
representation. A surrogate that predicts latency or energy from those
parameters is a world model. A set of design rules, expert heuristics, or
physical constraints can also act as a world model.

@fig-architecture-world-model gives the basic structure. A
representation record contains workload traces, architecture descriptions,
tool configurations, logs, constraints, and objectives. A world model contains
state, action spaces, dynamics, costs, constraints, invalid-action rules,
uncertainty, and decision policies. Tools return feedback; evidence updates
both the representation and the world model.

![A world model connects artifacts to valid architectural action: A representation record captures what the loop can read, compare, and replay; a world model captures what the loop believes actions will change. Feedback becomes reusable only when provenance, coverage, and negative traces are recorded.](images/F5-architecture-world-model){#fig-architecture-world-model width="100%" fig-alt="Loop diagram showing representation records, world models, tool feedback, evidence, provenance, coverage, and negative traces connected to valid architectural action."}

For the lighthouse prompt, a small world model might be as simple as
@tbl-xr-world-model-sketch. It is not a full simulator. It is the part of the
loop's belief that says which actions are meaningful, what they are expected to
change, and what evidence can overturn the prediction.

| World-model field | XRBench/RISC-V sketch |
| --- | --- |
| State | Workload slice, frame deadline, software path, candidate compute organization, memory traffic, and power envelope. |
| Legal action | Change vector width, local memory size, CPU/accelerator partition, or data layout inside the declared software contract. |
| Predicted transition | Estimate latency, memory traffic, energy, area pressure, and compiler/runtime feasibility. |
| Uncertainty and calibration | State whether the estimate comes from an analytic proxy, calibrated simulator, prior measurements, or expert rule. |
| Invalid-action rule | Reject candidates that break software compatibility, exceed the action bounds, fail correctness, or lack provenance. |
| Escalation trigger | Move to stronger evidence when a candidate nears the 3\ W target, misses the frame deadline, or wins only under a weak proxy. |

: An architecture world model is a scoped belief about action and consequence: Even a small sketch should name state, legal actions, predicted outcomes, uncertainty, invalid actions, and escalation triggers. {#tbl-xr-world-model-sketch tbl-colwidths="[24,66]"}

The type of world model matters only through the loop contract it supports: what
actions it can evaluate, what uncertainty it reports, what invalid moves it
rejects, when it escalates fidelity, and which decisions remain human-owned. A
simulator-backed world model uses a tool as the transition and feedback
mechanism. A learned surrogate world model predicts outcomes from prior
evaluations. A symbolic or constraint-based world model encodes invalid
configurations, design rules, or physical limits. A hybrid world model combines
these pieces: a simulator for selected candidates, a learned predictor for cheap
screening, a rule system for invalid actions, and an escalation rule that routes
high-commitment decisions out to human review.

No world model is automatically credible. Each has a scope. Each has
uncertainty. Each can be wrong under distribution shift[^fn-distribution-shift-c04], new workloads,
different software stacks, tool changes, or higher-fidelity evaluation. The
goal is not to pretend the world model is truth. The goal is to make its
assumptions explicit enough that the loop can decide when to trust it, when to
escalate fidelity, and when to reject its advice. The lighthouse prompt makes
that discipline concrete. An analytic proxy predicts that a wider-vector
candidate meets the 3\ W envelope, but the margin to the envelope is smaller
than the proxy's known error band, so the escalation trigger from
@tbl-xr-world-model-sketch fires. A calibrated simulator then shows the
candidate misses the frame deadline on the real XRBench slice, and the architect
records the rejection with its fidelity level and reason. The prediction, the
escalation, and the rejection are all part of the world model, and each is
auditable: an automated optimizer acted on the belief, and a human could see why it was
overturned.

::: {.callout-architect-checkpoint title="Architect Checkpoint: Escalate or Reject"}
When the world model proposes a candidate whose margin of safety is smaller than the model's known error band, the loop must pause. The architect decides whether to escalate to a higher-fidelity tool (e.g., a cycle-level simulator) or reject the candidate outright based on risk. This gate ensures the optimizer does not commit to decisions based on uncalibrated proxy estimates.
:::

## Provenance, Coverage, and Negative Traces

Knowing when to reject the world model's advice depends on records most teams
are quick to discard. The most distinctive architecture data may be the data
the field usually throws away[^fn-negative-venues-c04]. Published work tends to preserve accepted artifacts. Design loops
also need rejected alternatives. A failed simulator run, invalid configuration,
proxy win that fails at higher fidelity, abandoned floorplan, or
unsupported-software path is not merely noise. It shows the loop where the
boundary lies.

> **Negative traces.** Negative traces are recorded failed, rejected, invalid,
> or abandoned candidates together with the reason they did not support the
> claim. They matter because a loop that records only winners cannot inform the
> next method, reviewer, or architect which assumptions, tools, workloads, or
> regions of the design space were already ruled out.

Negative traces matter because architecture action spaces are full of invalid
or misleading moves. A generated RTL fragment may be syntactically plausible
but fail timing or violate an interface. A design-space search may find a
candidate that looks good under a proxy but fails under a better power model.
A benchmark result may improve because the workload slice is too narrow. A
chiplet partition may appear modular but introduce unacceptable latency,
thermal coupling, test complexity, or supply-chain risk.

@tbl-negative-traces turns this point into a data schema.
The purpose is to record what failed, what boundary it exposed, and how that
evidence should change the next action in the loop.

| Negative trace | What it records | What the loop learns |
| --- | --- | --- |
| Synthesis violation | Constraints, process, parameters, failing paths. | Exclude this macro or parameter combination. |
| Unroutable netlist | Placement, density, pin layout, congestion map. | Add congestion-aware spacing or reshape the action space. |
| Proxy win that fails fidelity | Cheap metric improves, but stronger evaluation rejects it. | Calibrate proxies and require sensitivity checks. |
| Tool failure or crash | Simulator, synthesis, compiler, or harness cannot complete. | Separate design failure from environment failure. |
| Coverage gap | Workload, input, scenario, or architecture class was not represented. | Mark the evidence boundary before committing. |
| Rejected design rationale | Human review rejects a candidate for risk, maintainability, schedule, or integration. | Preserve architect judgment as training and audit data. |

: Negative traces are architecture data: Failed builds, invalid candidates, missed constraints, and rejected alternatives define the boundary of the design space and should be preserved rather than discarded. {#tbl-negative-traces tbl-colwidths="[26,32,32]"}

Negative traces require provenance. A failed result without context is not very
useful. The minimum reusable record includes the candidate identifier, workload
slice, software stack, tool version, seed, parameters, constraints, fidelity
level, failure reason, coverage boundary, and decision owner. The loop also
needs coverage: what part of the design space, workload space, or evidence
regime does this trace represent? Without provenance and coverage, negative
traces become a pile of anecdotes. With them, they become architecture data.

## When a Representation Becomes Actionable

A representation becomes actionable when it can safely support loop operations.
It should define valid actions, expose relevant observations, carry constraints
and objectives, record provenance, support replay, preserve uncertainty,
separate feedback from evidence, and record what rejects a candidate. It should
also say what remains a human decision.

This is a higher bar than asking whether a model can read it. A representation
that can be summarized may still be useless for design. A representation that can be
searched may still hide invalid actions. A representation that produces a
score may still lack provenance. A representation that captures winning
results but not rejected alternatives may give the loop a biased view of the
space.

The same test applies to abstractions. A useful Architecture 2.0 abstraction
does not merely hide detail or provide nicer names. It creates a
surface where valid actions, feedback, rejection, replay, or review can happen
earlier, cheaper, or with clearer authority. An abstraction that cannot return
feedback is merely notation; it may help people talk, but it has not
yet made the loop more capable.

For the lighthouse prompt, an actionable representation would not merely
contain the prompt text. It would include the XRBench scenario, workload
metadata, architecture parameters, software assumptions, power and process
constraints, tool configurations, candidate set, feedback budget, evidence
regime, negative traces, and rejection authority. Only then can the loop ask a
bounded question: which candidate should be evaluated next, which evidence is
strong enough, and which decision still belongs to the architect?

::: {#pri-make-legible .callout-design-principle title="Make architecture work legible to the automated loop"}
A representation earns trust only when it records provenance, assumptions,
costs, failures, and negative traces, not only the successful endpoints. What
the loop cannot see, it cannot reason about, and what the human architect cannot see, they cannot safely reject.
:::

@sec-architecture-environments-tool-interfaces takes the next step. Once state is represented, tools can become
environments. They define what actions are legal, what feedback is returned,
how expensive evaluation is, and what evidence a loop can produce.

## Open research questions

The gap between public architecture knowledge and actionable loop state leaves several unsettled research directions for the community to explore. Solving these requires moving beyond static data to dynamic, fidelity-aware representations.

1. How do we standardize schemas for auditable automated actions?
   While we established that representations must sit between human intent and tool action (see "Architecture Descriptions as Boundary Objects"), we do not yet have canonical formats for optimizer proposals that guarantee a human architect can independently replay, debug, and reject them using only the attached loop-state records.

2. Can a world model autonomously manage its own fidelity escalation?
   Building on the escalation triggers sketched in @tbl-xr-world-model-sketch, future research must determine if an agent can reliably learn when its proxy metrics are breaking down and automatically route high-risk candidate evaluations to slower, high-fidelity simulators before hitting a hard human checkpoint.

3. What is the formal boundary for benchmark overfitting in AI-driven design?
   As emphasized in "Sample Cost Is Architecture Data," workload provenance is critical loop state. However, we lack mathematical methods to detect when an automated optimizer has overfit to a specific phase behavior or input distribution, risking silent failures under the distribution shifts mentioned in our world model discussion.

4. How do we train models explicitly on negative architecture traces?
   We established in "Provenance, Coverage, and Negative Traces" that rejected candidates and invalid actions define the design boundary (@tbl-negative-traces). Yet, it remains an open question how to construct loss functions or preference-optimization pipelines that teach generative models to actively avoid the specific failure boundaries exposed by these negative records.

## What to carry forward
- Reader test: Could an automated optimizer replay both the winning and the rejected
  candidates six months later, compare the evidence boundaries, see who could
  reject the result, and read what commitment the evidence supports?
- Next loop state: Once that state exists, tools can become environments that
  act on it and return interpretable feedback. That is what representation buys
  in Architecture 2.0: constrained automated action under human-auditable
  authority.

[^fn-agent-framework-c04]: **Agent framework**: A software structure that defines how autonomous systems perceive their environment, reason, and take actions to achieve goals.
[^fn-world-model-c04]: **World model (origin)**: The concept of a "world model" in artificial intelligence was popularized by Ha and Schmidhuber [@HaSchmidhuber2018WorldModels], demonstrating that agents can learn to make decisions entirely within an internal, simulated representation of their environment.
[^fn-pretraining-c04]: **Pretraining**: The computationally intensive initial phase of training a large machine learning model on a massive, general dataset before fine-tuning it for specific tasks.
[^fn-domain-adaptation-c04]: **Domain adaptation**: A machine learning technique where a model trained on one data distribution is adjusted to perform well on a different, specific target domain [@PanYang2010TransferLearning].
[^fn-pretraining-c04-2]: **Domain-continued pretraining**: Further training a foundational model on a large corpus of domain-specific text to improve its specialized vocabulary and understanding.
[^fn-squad-and-glue-c04]: **SQuAD and GLUE**: Standard benchmark datasets used to evaluate the performance of natural language processing models, where SQuAD is the Stanford Question Answering Dataset [@RajpurkarEtAl2016SQuAD] and GLUE is the General Language Understanding Evaluation [@WangEtAl2018GLUE].
[^fn-distribution-shift-c04]: **Distribution shift**: A situation where the data a model encounters during deployment differs significantly from the data it was trained on, often degrading performance [@QuinoneroCandelaEtAl2009DatasetShift].
[^fn-negative-venues-c04]: **Venues for negative results**: The wider computing-systems community has begun to build places to publish exactly these records, such as the NOPE workshop (Negative results, Opportunities, Perspectives, and Experiences) held with ASPLOS. The field needs more of them, so that failed runs, rejected candidates, and the assumptions behind them accumulate as shared evidence instead of being discarded before publication.
# Tools as Architecture Environments {#sec-architecture-environments-tool-interfaces}

```{=latex}
\abstract*{Architecture 2.0 requires tools to become environments for AI-assisted architecture loops: explicit places where automated systems and human reviewers can take design actions, observe feedback, log costs and constraints, and reject invalid or unsupported candidates. This chapter treats ISA boundaries, compiler IRs, memory models, simulator APIs, profilers, RTL flows, EDA handoffs, runtimes, benchmarks, and telemetry systems as part of the research object, not background implementation detail.}
```

::: {.callout-crux}
What turns a tool flow into an environment a generative model can act in and a
reviewer can trust?
:::

@sec-data-representations-world-models argued that a loop can only act on what it represents. This chapter
asks where the loop acts. In Architecture 1.0, tools often sit behind the
architect: simulators, scripts, compilers, profilers, spreadsheets, RTL flows,
EDA tools, dashboards, and deployment logs are the means by which a human
expert gathers evidence. In Architecture 2.0, those same tools must become
explicit environments when they sit inside AI-assisted design loops. They
define what actions are legal, what observations are returned, how expensive
feedback is, which assumptions are baked in, what state is logged, what can
reject a candidate, and what commitment the environment can support before the
loop spends more effort.

> **Architecture environment.** An architecture environment is the tool-facing
> part of the loop contract made executable: it specifies the legal actions,
> observations, feedback costs, assumptions, logged state, provenance,
> rejection authority, and commitment boundaries for the tools a design loop
> acts through.

To keep these boundaries clear, we must use the tool vocabulary carefully. A **tool** performs an operation. A **wrapper**
calls that tool. An **environment contract** states what actions are legal, what
observations return, what costs and failures mean, and what evidence is logged.
A **harness** is the maintained runnable object around that contract: workloads,
versions, scripts, provenance, invalid-action records, and review state.

This shift from simple wrappers to formal environment contracts is easy to understate. A tool wrapper is not plumbing. It is a
research claim about the architecture problem. It decides which parts of the
design space are visible, which constraints are enforceable, which metrics are
trusted, which failures are recorded, and which actions are silently
impossible. A weak environment can make a strong method look useful by hiding
the hard cases. A disciplined environment can make a modest method valuable by
making the task bounded, repeatable, and rejectable.

The same contract is what makes comparison meaningful. Two AI-assisted methods
can be compared only when they act under compatible workload definitions, action
schemas, feedback budgets, invalid-action rules, provenance records, and
commitment boundaries. Otherwise a result may compare private worlds rather than
architecture methods.

The lighthouse prompt makes the point concrete. "Design a low-power,
64-bit RISC-V-based compute subsystem for an XRBench real-time mobile XR
workload under a 3\ W, 3\ nm-class low-power mobile envelope" is not one call
to one tool. It needs a workload harness, software stack, ISA and vector
assumptions, candidate architecture representation, simulator or estimator,
power model, compiler/runtime interface, validity checks, provenance log, and
a way to record rejected alternatives. If any of those pieces are implicit,
the prompt is not yet an Architecture 2.0 loop. It is only a sentence.

::: {.callout-learning-objectives}
After this chapter you can turn a tool path into a reviewable environment
contract. That means you can:

- turn a tool into an environment with an explicit action, observation, cost, rejection, and commitment contract;
- read a result by naming the environment that produced it;
- explain why environment contracts make AI-method and paper comparisons meaningful;
- reason about feedback latency and fidelity as an economy of evidence;
- detect proxy mismatch and proxy gaming, simulators included, before they mislead the loop.
:::

## Tools Shape the Research Question

Computer architects have always used tools to reason quantitatively about
systems. Simulators, analytic models, profilers, compilers, RTL generators,
EDA flows, and measurement systems make design spaces tractable. They also
shape the questions that can be asked. A simulator with a particular memory
model makes some cache questions natural and others awkward. A compiler pass
that exposes one schedule representation and hides another constrains what an
optimizer can change. An EDA flow that returns timing and power after hours of
work makes feedback precious. A runtime telemetry system that reports
aggregate utilization but not per-request interference makes some deployment
claims difficult to support.
When tools are used by a human expert, some of these limits can remain tacit. For an AI-assisted
loop, tacit limits become hidden state: the loop can act safely only on
constraints, costs, and rejection rules the environment exposes.

The usual way to describe these tacit boundaries is to say that tools have limitations. That is true,
but too weak. Tools do not merely limit architecture work; they define its
observable world. They decide what state exists for the loop, what actions can
be applied to that state, and what feedback comes back. The classic
quantitative tradition in computer architecture emphasizes measurement,
abstraction, and careful comparison [@HennessyPatterson2017QuantitativeApproach].
Architecture 2.0 keeps that tradition, but it asks for one more layer of
explicitness: the tool interface itself must be part of the design object.

This level of explicitness matters because generative and learning-based methods are literal about
interfaces. A human architect can sometimes infer that a simulator result is
out of distribution, that a benchmark run used a stale configuration, or that
a reported improvement is not meaningful because the compiler changed. A
method acting through an environment will not infer those facts unless the
environment represents them. The environment must expose enough state for
useful action and enough constraints for safe rejection.

The right question is therefore not, "Which tool did the paper use?" The
better question is, "What environment did the loop define?" That question
forces the paper or project to name its workload distribution, action schema,
observation schema, feedback latency, validity constraints, cost model,
provenance record, and rejection authority. Once those are visible, method claims
become easier to compare.

## Interfaces Are Action Boundaries

To translate these environments into practice, what makes a tool's action and observation schema concrete is the interface it
exposes. Architecture is often described as the boundary between hardware and
software.
For Architecture 2.0, that statement has an operational meaning: interfaces
are where actions become legal or illegal, observations become meaningful or
misleading, and evidence becomes portable or trapped inside one tool script.
An ISA, compiler IR, Domain-Specific Language (DSL) like SLICC for cache coherence, memory model, accelerator runtime, simulator API, benchmark harness, EDA handoff, or telemetry schema is not just a convenience for implementation. It defines what a loop can change and what can reject the change. Crucially, AI agents must interface with these DSLs; emitting monolithic C++ or raw RTL defeats the modularity required for a human architect to review and maintain the logic.

This is why tool interfaces belong in the architecture argument rather than in
an appendix. A generator that emits a schedule must know the schedule
language. A search method that changes memory hierarchy parameters must know
which combinations the simulator accepts and which violate a software-visible
contract. A critique system that reads a synthesis report must know which
warnings are fatal, which are informational, and which require a higher-fidelity
check. The interface is the boundary where method capability meets
architectural validity.

@tbl-architecture-interface-boundaries lists the interfaces that a
credible loop often has to expose. The table is not a complete taxonomy. Its
claim is that every interface has two jobs: it makes some actions possible,
and it defines what evidence those actions can produce. If either side is
hidden, an automated optimizer can appear capable while acting outside the architecture
problem the human intended to solve.

| Interface | What it makes actionable | Evidence it makes interpretable | Failure if hidden |
| --- | --- | --- | --- |
| ISA and vector contract | Instructions, registers, vector length, exceptions, privilege, and binary compatibility. | Correct execution, portability, software-visible behavior, and compatibility tests. | The loop proposes a microarchitecture that software cannot legally target. |
| Compiler IR and schedule representation | Lowering choices, tiling, fusion, layout, vectorization, and target-specific code generation. | Compiler success, generated code, performance counters, and optimization provenance. | Performance is attributed to hardware while the software contract changed. |
| Memory and coherence model | Ordering, sharing, cacheability, consistency, DMA, and synchronization assumptions. | Correctness tests, contention behavior, latency, bandwidth, and race or ordering failures. | A candidate looks fast because it violated the program's memory assumptions. |
| Accelerator or runtime API | Invocation, data movement, synchronization, library calls, queues, and resource ownership. | End-to-end latency, overhead, utilization, portability, and software integration cost. | Specialized hardware is efficient in isolation but unusable in the system. |
| Simulator or environment API | Legal parameters, workload inputs, observations, errors, seeds, and fidelity levels. | Comparable runs, replayable experiments, invalid-action records, and feedback cost. | The method optimizes simulator quirks or incomparable configurations. |
| EDA handoff and constraints | RTL, clocks, floorplan hints, timing constraints, power intent, physical limits, and signoff checks. | Timing, area, power, congestion, rule violations, and implementation feasibility. | A candidate survives architectural simulation but fails physical reality. |
| Benchmark harness | Inputs, versions, metrics, splits, data-leakage rules, and submission constraints. | Coverage, reproducibility, benchmark validity, and claim scope. | The loop overfits a stale or leaky benchmark slice. |
| Telemetry and deployment schema | Live workload mix, service-level objectives (SLOs), counters, interference, rollout state, and drift signals. | Field behavior, regressions, rollback triggers, and post-deployment calibration. | Production evidence is rich but too confounded to support the architecture claim. |

: Architecture interfaces define action and evidence boundaries: Each interface tells the loop what can be changed, what can be observed, what feedback is meaningful, and what can reject an invalid action. {#tbl-architecture-interface-boundaries tbl-colwidths="[20,25,25,20]"}

The EDA handoff row is worth making concrete, because it is where a wrapper does
the most work. Validity comes in two tiers, and honest environments separate
them. **Schema legality** is cheap and checkable up front, asking whether the
parameters, clocks, and interfaces are well formed. **Physical feasibility** is
late and expensive, because routability, timing closure, congestion, and IR drop
often surface only at synthesis or place-and-route. A late failure must map back
to the earlier action that caused it, not read as a contract violation.

Wrapping a commercial flow as an environment is therefore not a thin API. The
wrapper has to emit tool-specific scripts, parse unstructured reports, survive
timeouts and run-to-run nondeterminism, and attach the fidelity or confidence
label itself, because the tool emits metrics, warnings, and logs, not a fidelity
level. To stay auditable, its provenance record must carry more than a bare
number. It records the tool and host version, thread count, license state,
run-to-run variance, warnings and waivers, and a hash of the report the number
came from. Two "identical" runs that differ on any of these are not comparable,
and a loop that hides the difference will trust a result it should have rejected.

::: {.callout-lighthouse title="One prompt, many interfaces"}
Context. The lighthouse request crosses multiple interfaces at once, so no
single simulator API or wrapper is the environment.

In the Lighthouse prompt. "64-bit RISC-V-based" is an ISA and ABI/software
contract. The fragment "vector-capable CPU, accelerator, or SoC block" is an
action boundary over compute organization and integration. "XRBench-class
real-time mobile XR workload" fixes the workload harness and quality-of-service
target. "3\ W TDP target in a 3\ nm-class LP mobile process" invokes power and
physical-design constraints.

Boundary. When the optimizer proposes a SoC block instead of an isolated accelerator, it changes the action space. The environment must now expose memory attachment, coherence, interrupts, DMA, runtime ownership, verification scope, and the evidence needed to show that the subsystem works in the larger system, otherwise the loop will optimize blindly.

Takeaway. The environment for this prompt is a bundle of coherent
interfaces. An AI-assisted loop can change vector width, local memory, data layout, or
accelerator interface only inside contracts that can reject
software-incompatible, physically implausible, or integration-breaking
candidates.
:::

In practice, concrete tools instantiate this bundle of interfaces at different fidelity levels. The point
is not that Architecture 2.0 requires one canonical simulator or one vendor
flow. The point is that a loop must say which environment it is acting in, what
that environment can observe, and what authority its feedback has.
@tbl-environment-instances gives a compact set of examples.

| Environment instance | Action boundary | Feedback and evidence | Loop lesson |
| --- | --- | --- | --- |
| gem5-style cycle or full-system simulation [@BinkertEtAl2011Gem5] | Core, cache, memory-system, ISA, and workload configuration. | Statistics, traces, timing-model behavior, simulator warnings, and scoped performance comparisons. | Strong for controlled DSE; bounded by model fidelity and configuration state. |
| Verilator-style compiled RTL simulation [@Veripool2026Verilator] | RTL modules, test benches, assertions, generated C++/SystemC models, and debug hooks. | Functional behavior, waveform/debug evidence, assertion failures, and implementation-adjacent traces. | Moves closer to implementation but narrows throughput and increases debug cost. |
| FireSim-style FPGA-accelerated simulation [@KarandikarEtAl2018FireSim] | RTL target, workload image, network model, FPGA mapping, and runtime configuration. | Faster cycle-exact feedback, workload-scale behavior, instrumented counters, and deployment-like experiments. | Speed changes sample economics, but setup and observability become part of the evidence. |
| Synthesis, place-and-route, and signoff flow [@MirhoseiniEtAl2021GraphPlacement; @SemiconductorIndustryAssociation2026ChipDesign; @BauerEtAl2020SemiconductorDesignManufacturing] | RTL, constraints, floorplan hints, clocks, power intent, libraries, and process assumptions. | Area, timing, power, congestion, rule violations, waived warnings, and closure failures. | High-fidelity samples are scarce; use them as rejection gates, not blind search targets. |

: Concrete tools instantiate the environment contract: A credible loop should name the simulator, RTL flow, emulation path, EDA stage, or deployment harness it is acting through, because each one exposes different actions, feedback, cost, and rejection authority. {#tbl-environment-instances tbl-colwidths="[22,24,26,18]"}

For each row, the Architecture 2.0 object is not the tool name but the
maintained action/observation record: workload version, legal edits, failed
runs, waivers, escalation gate, and human owner.

In practice these environments are rarely used in isolation. Open frameworks
integrate them. Chipyard, an open-source framework for generating and evaluating
RISC-V systems-on-chip, wraps a configuration system, Chisel-based RTL
generators such as the Rocket and BOOM cores, and a FIRRTL compiler path
together with the simulation, synthesis, and FPGA-emulation
backends the table lists, so one configuration can be carried reproducibly from a
generated design to each evaluation path [@chipyard].
@fig-chipyard-framework shows that integration.
For an AI-assisted loop, the useful property is not the framework name but where the
loop actually runs. The automated optimizer acts at the configuration boundary, editing one
configuration under a set of legal actions; each backend, whether simulation,
synthesis, or FPGA emulation, returns a receipt; and those receipts, together
with invalid-action logs, escalation thresholds, and human decision points, are
the loop contract that keeps a generated configuration from becoming an unowned
commitment.

![An integrated environment ties the backends together: A reproducible SoC generation framework connects a configuration system, RTL generators, and a compiler to simulation, synthesis, and FPGA-emulation backends, so one configuration reaches every evaluation path.](images/F6b-chipyard-framework){#fig-chipyard-framework width="100%" fig-alt="Flow diagram in which a configuration system feeds Chisel RTL generators (Rocket, BOOM, Hwacha) and a FIRRTL compiler, which fan out to RTL simulation, VLSI synthesis, and FPGA emulation backends."}

However, even the broad categories in @tbl-environment-instances hide internal ladders of fidelity. Post-synthesis timing, for
example, is often a useful surrogate for post-route timing, but routing
congestion, IR drop, clocking, and signoff checks can still reject a candidate
that looked acceptable at synthesis. The lesson is not that every loop must
begin with the strongest tool. It is that the loop must know which feedback is
a proxy and which later check has authority to overturn it.
For an AI-assisted loop, that later authority is what decides whether a candidate
earns another sample, an escalation, or termination.

Physical-design environments make this staged contract particularly visible. A loop should
not report "EDA feedback" as if all tool stages had the same authority.
@tbl-eda-stage-contract separates common stages by what they can and cannot
reject.

| EDA stage | Feedback returned | What it can reject | What it cannot prove alone |
| --- | --- | --- | --- |
| Logic synthesis | Mapped gates, area proxy, timing estimates, constraint warnings, and early power estimates. | Nonsynthesizable RTL, impossible constraints, obvious area/timing problems. | Routability, final timing, IR drop, clocking, and post-layout power. |
| Floorplanning and placement | Cell locations, utilization, congestion hints, timing pressure, and macro or memory placement effects. | Floorplans that create severe congestion, timing pressure, or integration problems. | Final routed timing, signoff power, manufacturability, and workload-level benefit. |
| Clock, routing, and power closure | Routed timing, clock behavior, congestion, design-rule checks, power integrity, and closure failures. | Candidates whose physical effects invalidate earlier architecture estimates. | Product commitment without verification, workload coverage, and architecture review. |
| Signoff and review | Tool signoff reports, waivers, residual risks, review decisions, and ownership records. | Unsupported claims, unacceptable waived warnings, and evidence gaps before commitment. | Generality beyond the stated workload, process, tool version, and design context. |

: EDA feedback has stage-specific authority: From logic synthesis through
signoff, each physical-design stage returns different evidence and should be
allowed to reject different claims. {#tbl-eda-stage-contract tbl-colwidths="[18,26,25,21]"}

This arrangement is not hypothetical. Some commercial physical-implementation
flows already treat synthesis and place-and-route as a search environment: tool
directives and floorplan parameters become actions, full tool runs become
transitions, and reports become observations about power, performance, area, and
closure [@Synopsys2023DSOai; @Cadence2021Cerebrus]. The durable point is not
which vendor leads, since the products will be renamed and replaced. It is that
an EDA flow becomes an environment only when those directives are an action
schema, reports are observations with provenance, closure and signoff are
rejection authorities, and the architect owns the gates the loop may not cross.

## The Architecture Environment Abstraction

To formalize these interfaces across different tools, we need an abstraction. The environment has an executable core, but it is not only software. It receives
a proposed action, checks whether that action is meaningful, calls one or more
tools, collects observations, logs provenance, and returns feedback that can
become evidence. It can also enforce or record declarative interface contracts:
ISA rules, memory models, telemetry schemas, benchmark rules, and EDA
constraints. @fig-environment-tool-interface shows the basic shape.

![A tool becomes an environment when its contract is explicit: A credible environment defines workload state, legal actions, observations, constraints, cost, provenance, feedback, invalid-action semantics, and rejection paths.](images/F6-environment-tool-interface){#fig-environment-tool-interface width="100%" fig-alt="Diagram of a tool wrapper becoming an architecture environment by exposing workload state, legal actions, observations, costs, provenance, feedback, and rejection paths."}

The figure is a loop contract, not a software architecture diagram. Each
component is useful only after the environment names the action it permits, the
feedback it returns, and the rejection authority attached to that feedback. That
is why two projects can use the same simulator but define different architecture
environments.

Fundamentally, this abstraction can be described as a contract. The contract does not require
one software framework or one programming language. It requires that the loop
make a small set of obligations explicit. @tbl-environment-contract
lists the main fields.

| Field | What it defines | Question it answers |
| --- | --- | --- |
| Workload distribution | Inputs, traces, benchmark versions, software stack, and operating scenarios. | What behavior is the design supposed to serve? |
| Action schema | Parameters, edits, configurations, generated artifacts, or commands the loop may propose. | What can the method actually change? |
| Observation schema | Metrics, traces, logs, reports, errors, and artifacts returned after an action. | What can the loop observe after acting? |
| Constraints and validity | Type checks, feasibility rules, physical limits, software compatibility, and invalid-action handling. | What makes a candidate illegal before performance is considered? |
| Feedback budget | Cost, latency, fidelity, determinism, and sample limits for each source of feedback. | How much evidence can the loop afford? |
| Provenance record | Tool versions, seeds, inputs, configuration files, assumptions, and artifact hashes. | Could a human replay or audit the result? |
| Rejection authority | Conditions that stop, revise, or escalate a candidate. | What can say no? |

: An environment contract makes tool use auditable: The loop should state its action schema, observations, costs, failures, provenance, and human-review boundaries before methods operate inside it. {#tbl-environment-contract tbl-colwidths="[22,32,34]"}

The contract is deliberately broader than reinforcement learning terminology.
Actions, observations, and rewards are useful terms, but architecture work
also needs constraints, invalid-action semantics, provenance, and human
decision points. A loop that proposes a cache size, vector width, chiplet
partition, compiler flag, or RTL edit needs to know not only whether a score
improved, but whether the candidate is legal, reproducible, comparable, and
worth committing to a higher-fidelity stage.

Applying this contract to the lighthouse prompt, the environment might expose actions such as
changing vector width, local memory size, issue width, cache configuration,
accelerator interface, or data layout. It might return observations such as
latency, throughput, estimated power, memory traffic, area proxy, simulator
warnings, compiler failures, and rejected workloads. It should also return
cost: how long the run took, which fidelity level was used, and how much
confidence the loop should place in the feedback. Without that cost and
provenance, the loop cannot reason about sample efficiency or evidence.

## ArchGym as a Worked Example

ArchGym, which frames architecture design as a gymnasium for
machine-learning-assisted design where automated methods interact with architecture
environments through defined interfaces [@KrishnanEtAl2023ArchGym], makes the
environment idea concrete in the architecture domain. The name is
deliberate. It borrows from OpenAI Gym, which standardized the agent-environment
interface in reinforcement learning. Just as one learning algorithm can drive
many Gym environments, an ArchGym user can swap a memory-controller simulator for
an accelerator simulator while keeping the same optimization or learning method
intact, which is exactly the composability a shared environment is supposed to
buy. The
Architecture 2.0 gymnasium essay makes the same broader argument: the field
needs data-centric environments where architecture tasks, feedback, and
evaluation are exposed systematically [@ReddiYazdanbakhsh2023Gymnasium].

For our purposes, the important lesson is not that every project should use ArchGym literally.
The lesson is that a shared environment changes the research question. Instead
of asking whether one optimizer beat another under a private script, the
community can ask which task was defined, which action space was exposed, what
feedback was available, what workloads were used, and which tools or methods
were compared under the same conditions. That makes method claims less
anecdotal.
The comparison is credible only when every AI-assisted system acts against the same
represented state, receives the same feedback records, and accepts the same
invalid-action, escalation, and human-review rules.

@tbl-archgym-mini-contract reads an ArchGym-style environment as a
mini-contract.

| Contract field | ArchGym-style instance |
| --- | --- |
| Task | Search or tune a bounded architecture design space under a declared workload and metric. |
| Action space | Architecture parameters, simulator knobs, or mapping choices the automated method is allowed to change. |
| Observation and reward | Metrics returned by the simulator or tool path, with the reward derived from those observations. |
| Workload and tool path | Benchmark inputs, simulator configuration, and versioned evaluation scripts. |
| Invalid-action behavior | Rules for rejected parameters, failed runs, timeouts, or unsupported configurations. |
| Feedback cost | Approximate turnaround and sample budget for each evaluation regime. |
| Rejection and commitment boundary | Independent checks that can reject a result and the strongest claim level the environment can support. |
| Limits | Simplified simulators, cleaner action spaces, and missing industrial constraints can bound what the result proves. |

: A worked environment example is a contract, not only a benchmark: ArchGym is useful for Architecture 2.0 because it makes the task, action space, feedback, comparison setting, and limits discussable. {#tbl-archgym-mini-contract tbl-colwidths="[24,66]"}

ArchGym also shows why the environment chapter cannot be collapsed into the
methods chapter. Once an environment is defined, many methods can interact
with it: Bayesian optimization, reinforcement learning, evolutionary search[^fn-evolutionary-search-c05],
surrogate-guided exploration[^fn-surrogate-guided-exploration-c05], random search, heuristic search, or a human
designer using the environment as an instrumented assistant. The environment
is the common ground on which method comparisons become meaningful.

At the same time, ArchGym should not be treated as if it solves the whole
Architecture 2.0 problem. A gym can still use simplified simulators. It may
not include proprietary physical-design constraints, confidential workloads,
tool-license behavior, workload drift, negative trace capture, or deployment
telemetry. Its action spaces may be cleaner than industrial design spaces. Its
feedback may be faster and more standardized than the feedback available in
late-stage silicon work. Those limitations are not reasons to dismiss the
environment pattern. They are reasons to make environment validity a first-class
concern.

## Interfaces Make Loops Composable

Validity is not the only reason to insist on an explicit interface. A single
tool wrapper can support one experiment. A disciplined interface can
support a research ecosystem. The difference is composability. If action
schemas, observation schemas, workloads, provenance records, and validity
rules are explicit, then generators, predictors, optimizers, critics,
verifiers, and human reviewers can be swapped or combined without rewriting
the whole loop.

This is how architecture environments can become community infrastructure. As
@sec-design-loop-no-longer-scales argued for benchmark governance, useful
infrastructure such as MLPerf does more than name workloads: it creates rules,
versions, metrics, submissions, and comparison conventions that help a community
interpret results [@MattsonEtAl2020MLPerf]. Benchmark governance governs
comparisons; environment governance must also govern what AI-assisted systems may try, which
actions are invalid, what feedback means, and what can stop the loop. A useful
environment should not merely publish a script; it should publish the contract
under which actions are legal, observations are valid, and evidence can be
compared.
Keeping those contracts valid after the first paper is the operating discipline
@sec-archops-operating-discipline develops.

This transition from single-use wrappers to shared community infrastructure is why our opening vocabulary reserved the word harness. A
wrapper calls a tool. A harness preserves the contract around the tool: task,
workload, action schema, observation schema, cost, provenance, invalid-action
semantics, negative traces, and review status. A multi-participant harness adds role
boundaries: which component may propose, which may execute, which may critique,
which may verify, and which human decision is required before escalation. The
distinction matters because a wrapper can automate one experiment, but a
harness can accumulate reusable knowledge about a design space.

A minimal implementation receipt for such a harness might include:

> task identifier; workload version; input distribution; action fields;
> read-only constraints; tool commands; observation fields; fidelity level;
> runtime cost; random seed; tool versions; generated artifacts; failure status;
> rejection reason; and human decision.

That list is intentionally mundane. Mundane records are what make loops
auditable. If a method proposes an architecture candidate, the environment
should preserve not only the winning score but also the command that produced
it, the workload revision, the tool version, the failed alternatives, the
warnings, and the conditions under which the candidate would be rejected.

Ultimately, this focus on composability also changes how we interpret AI-assisted systems. A compound
design system may have a planner, code generator, simulator caller, surrogate
model, evidence critic, and human reviewer. Those components can coordinate
only if the environment gives them a shared state representation and stable
interfaces. If those components are implemented as several agents, the need for
an environment contract does not shrink; it grows. The harness has to record
which component read which state, which action it took, which feedback it used,
and which gate could reject its output. Without that, an "agent" is merely a
wrapper around a pile of scripts. With it, the loop can become an inspectable
system.

## Feedback Latency and Fidelity

Once an environment is structured to support these composable agents, the hardest design choice is often not the action schema. It is
the feedback regime. Architecture feedback ranges from cheap and weak to slow
and authoritative. A simple analytic proxy may return in milliseconds. A
cycle-level simulation may take minutes or hours, because a detailed simulator
typically runs many orders of magnitude slower than the hardware it models, so
seconds of target execution become hours of wall-clock time. Synthesis, place
and route, or signoff of a single block are commonly hours-to-days jobs.
Hardware-in-the-loop, deployment telemetry, and silicon evidence may arrive
only after substantial commitment.

This is why more capable AI does not remove the environment problem. In many
architecture loops, the model call is fast and the feedback is slow. A method
may propose hundreds of candidates before a simulator, compiler, synthesis
flow, verification run, or human review can return decision-grade evidence.
The environment therefore becomes the pacing item: it must decide which actions
are worth spending feedback on, which cheap checks can reject early, and when
the loop should escalate to a stronger but scarcer source of evidence.

::: {.callout-architect-checkpoint title="The Escalation Gate"}
When an AI method proposes a candidate, do not automatically grant it a high-fidelity evaluation. The environment must enforce an escalation gate that asks:

- Did this candidate survive all cheap proxy and validity checks?
- Is the potential improvement worth the cost of a scarce simulator or synthesis sample?
- If the high-fidelity check fails, can the environment map that failure back to a specific tool action?
:::

This dynamic creates an economy of evidence. Cheap feedback buys breadth and pruning;
expensive feedback buys stronger rejection authority. @fig-fidelity-cost-confidence
shows the basic pressure: as feedback moves toward implementation and
deployment, the loop usually spends more time per sample, gains less freedom to
explore, and needs clearer justification for every action it takes. The ranges
are representative rather than universal. A real project should replace them
with its own source receipts; they are illustrative bands, not universal
empirical claims. In the early regimes, the horizontal axis mostly means tool or
measurement turnaround; near prototype, silicon, and deployment, it also
includes setup, queueing, fabrication, rollout, and commitment delay.

This economy is the multi-fidelity setting studied across computational
science, where cheap, lower-fidelity models are combined with scarce,
high-fidelity ones to keep optimization, inference, and uncertainty
quantification[^fn-uncertainty-quantification-c05] affordable [@PeherstorferWillcoxGunzburger2018Multifidelity].
Architecture 2.0 inherits that economy and adds two architecture-specific
requirements: each fidelity level must carry its own rejection authority, and a
move to a higher level crosses a commitment boundary, not merely a more accurate number.

```{python}
#| label: fig-fidelity-cost-confidence
#| fig-cap: |
#|   Feedback fidelity changes the economics of search and commitment: Low-cost feedback can screen many candidates, but implementation-adjacent feedback is scarce and more authoritative. The vertical ordering reflects rejection authority more than strict latency; the point is the shrinking sample budget, not the exact wall-clock value for any particular project.
#| out-width: "92%"
#| fig-alt: "Horizontal range plot comparing feedback regimes from cheap proxies to silicon deployment, showing increasing latency and rejection authority with shrinking sample budgets."

import matplotlib.pyplot as plt
from _python.arch2_plots import COLORS, add_note_box, apply_style, draw_range_rows, row_axis, top_log_axis

rows = [
    {"display_label": "analytic proxy / surrogate", "display_note": "thousands to millions of checks", "low_seconds": 0.001, "high_seconds": 1, "right_label": "prune / screen", "color": COLORS["blue"]},
    {"display_label": "trace / profile / replay", "display_note": "tens to thousands of slices", "low_seconds": 1, "high_seconds": 3600, "right_label": "workload state", "color": COLORS["green"]},
    {"display_label": "cycle-level simulation", "display_note": "tens to hundreds of comparisons", "low_seconds": 60, "high_seconds": 86400, "right_label": "scoped DSE", "color": COLORS["orange"]},
    {"display_label": "compiler / runtime measurement", "display_note": "many local measurements; fewer portable claims", "low_seconds": 1, "high_seconds": 3600, "right_label": "software path", "color": COLORS["purple"]},
    {"display_label": "RTL / synthesis / physical feedback", "display_note": "handfuls to tens of scarce samples", "low_seconds": 3600, "high_seconds": 1_209_600, "right_label": "reject / gate", "color": COLORS["red"]},
    {"display_label": "prototype / silicon / deployment", "display_note": "few high-commitment samples plus telemetry", "low_seconds": 604_800, "high_seconds": 31_536_000, "right_label": "commit / calibrate", "color": COLORS["red"]},
]

apply_style()
fig, ax = plt.subplots(figsize=(4.85, 3.25))
fig.subplots_adjust(left=0.39, right=0.77, top=0.86, bottom=0.16)

row_axis(ax, len(rows))
top_log_axis(
    ax,
    xlim=(5e-4, 7e7),
    xticks=[1e-3, 1, 3600, 604800, 31536000],
    xticklabels=["1 ms", "1 s", "1 h", "1 wk", "1 yr"],
    xlabel="representative turnaround or commitment latency",
)
draw_range_rows(ax, rows, low_key="low_seconds", high_key="high_seconds", label_x=-0.86, right_x=1.03, label_fontsize=6.5, note_fontsize=5.3, right_fontsize=5.9)
add_note_box(fig, "Representative ranges only; sample budgets shrink as rejection authority rises.", xywh=(0.13, 0.035, 0.74, 0.085), fontsize=5.5)

plt.show()
plt.close(fig)
```

This economic pressure can also be expressed as a practical design checklist.
@tbl-feedback-latency-fidelity extends the sample-cost regimes of
@sec-data-representations-world-models (@tbl-sample-cost-regimes) from what to
record toward what each regime can reject,
how many samples the loop can plausibly afford, and what method behavior that
economics permits. A loop that confuses those regimes can search quickly and
still learn the wrong lesson.

```{=latex}
\FloatBarrier
```

| Feedback regime | Cost / latency intuition | Sample budget | What can reject | Method implication |
| --- | --- | --- | --- | --- |
| Analytic proxy or learned surrogate | Milliseconds to seconds; low direct cost but high model-risk exposure. | Thousands to millions of candidate checks. | Obvious invalidity, dominated regions, sensitivity failures, or proxy-calibration failures. | Use for pruning, active learning, and broad search, not final commitment. |
| Trace, profile, or replay | Seconds to hours depending on capture, replay, and privacy filtering. | Tens to thousands of slices or scenarios. | Coverage gaps, stale workload versions, leakage, or mismatch to intended deployment. | Use for workload state, clustering, and targeted tests. |
| Cycle-level simulation | Minutes to days depending on model detail and target workload. | Tens to hundreds of scoped architecture comparisons. | Simulator configuration errors, unsupported states, calibration gaps, and sensitivity checks. | Use staged design-space exploration with replay and escalation. |
| Compiler/runtime measurement | Compilation, build, profiling: seconds to hours; target execution, replay, or autotuning: minutes to days. | Many local measurements, fewer portable claims. | Correctness tests, portability checks, and end-to-end software-path evidence. | Use autotuning or generation only with tests and provenance attached. |
| RTL, synthesis, or physical feedback | Hours to weeks when timing, power, congestion, or signoff constraints enter. | Handfuls to tens of scarce high-fidelity samples. | Timing, power, area, congestion, design-rule checking, formal, or waived-warning review. | Use filters, surrogates, and human gates before spending samples. |
| Prototype, silicon, or deployment telemetry | High setup cost; weeks to years when field evidence or silicon commitment is required. | Few high-commitment measurements plus ongoing telemetry. | Field behavior, reliability, rollback policy, incident review, and accountable human decision. | Use for calibration, validation, and drift monitoring, not blind exploration. |

: Feedback regimes create evidence economics: A method should match the latency, sample budget, rejection authority, and commitment level of the feedback it receives. Representative ranges are project-dependent and should be replaced by local source receipts in a real loop. {#tbl-feedback-latency-fidelity tbl-colwidths="[17,19,17,22,17]"}

However, this table must be read with a fidelity-risk rule: lower-fidelity
feedback can prune and prioritize, but it can also be gamed or contradicted.
When a proxy says "yes" and a stronger environment says "no," the loop should
record the mismatch instead of treating it as noise. The simulator-mismatch
discussion below returns to that failure mode.

Compiler and runtime feedback carry their own version of this same risk. A
hardware candidate can look weak because the schedule, tiling, vectorization,
layout, or runtime path is poor, not because the architecture is poor. That is
a false negative created by the software side of the environment. For the
lighthouse prompt, "vector-capable" therefore cannot mean only that an ISA
feature exists; the loop must also expose whether the compiler and runtime can
generate a credible path to use it.

Ultimately, this fidelity regime structure drives method choice. If feedback is cheap, broad search
or online adaptation may be reasonable. If feedback is expensive, the loop
needs sample efficiency, priors, surrogates, active learning[^fn-active-learning-c05], staged gates, or
stronger human filtering. If feedback is high commitment, the loop should
become more conservative: use AI to organize evidence, critique assumptions,
and narrow the search, not to make unsupported final decisions.

The environment should therefore expose feedback budget as a first-class
object: a result should report which fidelity level produced a comparison and
at what cost, not only that candidate A beat candidate B. When that feedback is
strong enough to count as evidence, and what provenance, uncertainty, and human
decision that requires, is the bridge from this chapter to
@sec-feedback-verification-trust, which treats it in full.

```{=latex}
\FloatBarrier
```

## Proxy Gaming and the Simulator Case

Because low-fidelity feedback can mislead a loop, an architecture environment must also defend itself against its own
abstractions. Simulators, analytical models, profilers, and compiler cost
models are not neutral oracles. They encode workload choices, warm-up rules,
timing models, memory-system assumptions, compiler defaults, branch predictor
state, cache initialization, interconnect models, and sampling choices. A
method that searches aggressively can discover weaknesses in those assumptions
just as easily as it can discover a good architecture candidate.

When the proxy is a simulator, **proxy mismatch**, the divergence between what a
cheap stand-in metric rewards and what the true objective needs, takes a
specific form: a gap
between the behavior an environment reports and the behavior that would matter at
the next stronger fidelity level, such as a more detailed simulator, synthesis,
physical design, emulation, silicon, or deployment. The failure mode is not
merely an inaccurate number. It is a loop that learns the wrong lesson. A
mapping optimizer may exploit a memory model that omits contention. A compiler
autotuner may win by relying on a backend assumption that changes under a
different target. A hardware generator may improve a cycle-level metric while
creating timing, congestion, or verification problems that the current
environment cannot see. A workload harness may reward one benchmark version
while hiding drift in the software stack.
A run that does not crash is not the same as hardware validity; the environment has
to define which illegal states, unsupported configurations, and silent
out-of-model behaviors it can actually reject.

::: {.callout-failure-mode title="When the tool becomes the target"}
A common failure pattern is not that the tool is useless; it is that the loop
learns exactly what the tool rewards. This is a local instance of proxy
mismatch, the architecture version of what machine-learning safety calls
specification gaming or reward hacking [@AmodeiEtAl2016ConcreteProblems]: a
candidate can improve a proxy by choosing an unsupported parameter
corner, relying on a stale workload slice, or shifting cost into a
compiler/runtime path the current harness does not measure. The environment
should make that failure visible through invalid-action checks, baseline replay,
sensitivity tests, and escalation to a stronger feedback source.
@sec-feedback-verification-trust treats proxy mismatch and its calibration
defenses in full.
:::

Environment design should therefore include red-team checks for the feedback
source itself. A simulator-backed loop should record warm-up policy, execution-
versus trace-driven mode, random seeds, sampled regions, versioned workloads,
configuration files, and unsupported states. It should also include rejection
tests that look for proxy gaming: cross-checks against another model, sanity
constraints on bandwidth and latency, sensitivity studies, invalid-action
logs, baseline replay, and escalation to stronger fidelity when the result is
surprising or high commitment. The goal is not to distrust simulation. The
goal is to make the simulator's authority explicit.

## Building Environments for New Subfields

Making that authority explicit is also the first move in building an
environment from scratch. A useful Architecture 2.0 environment for an
AI-assisted loop can start small: one bounded task where an automated tool or method can
propose actions, receive observations, hit explicit invalid-action rules, and
leave rejection reasons for review. The point is not to
build a universal hardware-design platform. The point is to choose a bounded
task where actions, observations, constraints, and rejection can be stated
cleanly.

To construct this bounded task, the recipe is straightforward.

1. Define the task in architectural language: workload characterization,
   cache exploration, accelerator parameter search, compiler/runtime tuning,
   chiplet partitioning, reliability analysis, or design-review critique.
2. Choose the representation the loop will read and write: configuration
   file, architecture description, graph, trace record, report, RTL fragment,
   test bench, or design-loop card.
3. Define the action schema: which fields can change, which are read-only,
   which combinations are legal, and which changes require human approval.
4. Wrap the tool path: simulator, compiler, profiler, RTL flow, EDA stage,
   runtime system, benchmark harness, or telemetry pipeline.
5. Define observations and feedback: metrics, traces, logs, warnings,
   errors, generated artifacts, cost, and fidelity level.
6. Define invalid-action semantics: illegal parameter, noncompilable
   artifact, nonsynthesizable design, violated constraint, timeout, simulator
   crash, or unsupported workload.
7. Log provenance and negative traces: tool versions, seeds, workload
   versions, failed candidates, rejected alternatives, and reasons for rejection.
8. State the human decision rule: what the architect reviews, what can be
   accepted automatically, and what must escalate.

Once built, the readiness test for this environment is simple. Could a second method, student, or research group
act inside the same harness without private knowledge from the original author?
Could a rejected candidate remain understandable six months later after tool
versions, workload revisions, and scripts have changed? If the answer is no,
the project may still contain a useful wrapper, but it has not yet produced a
durable Architecture 2.0 environment.

This eight-step recipe is intentionally more operational than inspirational. It is what
keeps Architecture 2.0 from becoming prompt-to-chip rhetoric. The first useful
environment for a new subfield is often narrow: a bounded workload, a small
action space, a clear simulator wrapper, and a disciplined log of failures.
That is enough to show the loop what it can try, what it can observe, and
what evidence matters.

Applying this operational recipe, the lighthouse prompt suggests a good starting point. Instead of trying to
build an end-to-end processor designer, start with an XRBench workload slice
and a small set of candidate architectural knobs: vector width, local memory,
cache size, data layout, or accelerator interface. Define which candidates are
invalid, which feedback is cheap, which feedback is expensive, and what
evidence would be needed to move from proxy exploration to simulator or
synthesis-backed claims. That is a real Architecture 2.0 environment even if
it is far from a complete chip-design system.

The same abstraction scales down as readily as it scales up. A single hardware
prefetcher makes a perfectly good environment: the actions are prefetch depth
and pattern, the cheap feedback is cache hit rate and memory bandwidth from a
cycle-level simulator, and the rejection rule is any configuration that breaches
a bandwidth or correctness bound. The environment idea is not tied to the size
of the artifact; it is tied to having legal actions, observable feedback, and
something that can say no.
It is complete only after it names the workload trace, simulator version, failed
configurations, proxy limits, and the point at which a human escalates from
hit-rate evidence to correctness or traffic review.

::: {#pri-tools-environments .callout-design-principle title="Turn tools into environments"}
A tool wrapper is credible only when it defines legal actions, observations,
costs, invalid states, and rejection paths. A command that returns a number is
not yet an environment a loop can act in.
:::

## Environment Validity and Operating Discipline {#sec-archops-operating-discipline}

An environment is useful only if it preserves the semantics of the
architectural question. If the workload is wrong, the action space omits the
important decision, the simulator hides a constraint, the proxy is
uncalibrated, or the logging drops failed candidates, the loop may become more
efficient at producing weak evidence.

To maintain this semantic link, environment validity relies on several layers. The workload layer asks whether the
inputs, distributions, and software stack match the intended use. The action
layer asks whether the loop can change the right architectural variables
without violating hidden constraints. The observation layer asks whether the
returned metrics are meaningful for the claim. The fidelity layer asks whether
the feedback is strong enough for the commitment being made. The provenance
layer asks whether the result can be replayed or audited. The rejection layer
asks what can stop a candidate when it is illegal, unsupported, misleading, or
insufficiently evidenced.

::: {.callout-architect-checkpoint title="The Environment Trust Gate"}
Before trusting an environment's verdict on an AI-generated candidate, confirm:

- the workload, action space, and observations still match the architecture question the loop was intended to solve;
- the feedback fidelity is strong enough for the commitment at stake;
- versions, assumptions, and rejected candidates proposed by the generative method are recorded;
- a rejection authority can stop an illegal, unsupported, or under-evidenced candidate;
- another team could deploy an automated optimizer in this harness without private knowledge.
:::

Operating discipline, the architecture counterpart of MLOps[^fn-mlops-c05], is the practice of maintaining those layers over time.
Workloads drift. Tool versions change. Compiler behavior changes. Benchmarks
gain new rules. Models learn stale assumptions. A one-time environment can
support a paper; a maintained environment can support a field. That is why the
environment should record versions, assumptions, invalid actions, rejected
candidates, and changes in the workload distribution.

::: {#pri-maintain-environment .callout-design-principle title="Maintain the environment, don't just build it"}
A design-loop environment is not built once; it is maintained. Workloads drift,
tools change, benchmarks gain rules, and models learn stale assumptions. Keep
the loop valid by versioning workloads and tools, preserving provenance and
negative traces, monitoring drift, and maintaining architect-owned rejection
gates.
:::

This distinction between building and maintaining matters because a one-time environment and a maintained
one look identical on the first run and diverge completely by the tenth; the
maintenance burden is what turns a one-off script into shared infrastructure.

@tbl-archops-operating-discipline states the maintenance work in operational
terms. The table is intentionally prosaic because the discipline succeeds only when
ordinary drift becomes visible before it invalidates evidence.

| Drift source | What to record | Failure if ignored | Operating response |
| --- | --- | --- | --- |
| Workload and benchmark updates | Versions, scenarios, excluded inputs, telemetry shifts, and coverage changes. | A loop keeps optimizing a stale or unrepresentative slice. | Re-run coverage checks and weaken or invalidate affected claims. |
| Tool and model changes | Simulator, compiler, EDA, model, prompt, policy, seed, and configuration versions. | Results become incomparable across runs without a clear cause. | Treat version changes as evidence events and preserve old receipts. |
| Action-space changes | New knobs, deprecated knobs, invalid combinations, and permission boundaries. | A method proposes actions the environment no longer supports. | Update validity checks and record invalid-action traces. |
| Evidence and rejection rules | Fidelity labels, escalation thresholds, signoff gates, waivers, and reviewer decisions. | A proxy keeps authority after the commitment level has risen. | Recalibrate evidence levels and require higher-fidelity review. |
| Human ownership | Decision owner, review date, redaction boundary, and escalation path. | Accountability disappears into scripts, tools, or automated systems. | Keep commitment decisions explicit and auditable. |

: Maintaining the environment preserves loop validity over time: The operating discipline is to
version workloads, tools, actions, evidence rules, and ownership so that drift
does not silently change what a loop result means. {#tbl-archops-operating-discipline tbl-colwidths="[18,25,25,22]"}

To summarize, this chapter's main claim is simple. Tools become architecture environments
when they expose actions, observations, costs, constraints, provenance,
feedback, rejection, and commitment boundaries. Once that happens,
@sec-methods-generation-prediction-optimization can ask which methods belong
inside the loop. Without it, method choice floats free of the architecture
problem. With it, generation, prediction, optimization, critique, and
verification become roles inside a credible, comparable, and reviewable design
system whose commitments remain owned by the architect. Maintaining the
environment is what keeps that design system reviewable after the first run.

## Open research questions

The concepts in this chapter establish the foundation for AI-assisted architecture environments, but several frontiers remain as unsettled research directions. The following questions push beyond simply defining environments to asking how they might become autonomous, transferable, and self-governing.

1. Can agents infer their own environment contracts?
   While @tbl-environment-contract outlines the necessary fields for a human to explicitly specify an environment, pushing into new territory requires asking if AI can automatically deduce legal actions, constraints, and rejection authorities directly from legacy tool errors, warnings, and undocumented simulator logs.
2. How do we transfer negative evidence across environment boundaries?
   Building on the need to maintain invalid-action logs and provenance (@sec-archops-operating-discipline), a major challenge is how to port the "dark matter" of failed runs across different toolchains or technology nodes. Research must determine how a candidate rejected by a high-fidelity physical-design flow becomes reusable, actionable evidence for a fast simulator evaluating a different target.
3. Can we build dynamic, mathematically verifiable escalation policies?
   As shown in the economy of evidence (@tbl-feedback-latency-fidelity) and the "Escalation Gate" checkpoint, environments currently rely on static, human-defined rules to promote candidates from cheap proxies to expensive tools. Future research must explore how to dynamically quantify proxy-mismatch risk, triggering high-fidelity evaluation or human review only when the mathematical confidence of a surrogate model falls below a certified threshold.
4. How do we automate the recertification of architectural claims?
   @sec-archops-operating-discipline highlights that workloads and tools inevitably drift, requiring ongoing maintenance to preserve environment validity. The next frontier is autonomous environment governance: designing systems that can detect when a tool update or workload shift invalidates a previous baseline, and autonomously spin up AI agents to recertify, weaken, or reject past architectural claims without human intervention.

## What to carry forward
- Reader test: Could another method act in the same harness without private
  knowledge from the original author, judged by loop conditions rather than
  fashion?
- Next loop state: Once the environment defines what action and feedback mean,
  @sec-methods-generation-prediction-optimization can ask which methods belong
  inside the loop.

[^fn-evolutionary-search-c05]: **Evolutionary search**: In this chapter, a way to propose candidate actions by mutation, crossover, and selection, useful only when the environment can reject invalid or weak candidates.
[^fn-surrogate-guided-exploration-c05]: **Surrogate-guided exploration**: In this chapter, using a fast predictor to screen candidate actions while preserving the stronger feedback needed to reject proxy wins.
[^fn-uncertainty-quantification-c05]: **Uncertainty quantification**: In this chapter, recording where an environment's feedback is uncertain enough to force escalation rather than commitment.
[^fn-active-learning-c05]: **Active learning**: In this chapter, a policy for choosing which scarce simulator, synthesis, human, or deployment feedback event to spend next, with the choice logged as part of the evidence ledger [@Settles2009ActiveLearning].
[^fn-mlops-c05]: **MLOps**: In this chapter, the operating discipline for deployed learning systems that motivates similar versioning, monitoring, drift, rollback, and ownership records in Architecture 2.0 loops.
# Method Roles: Generate, Predict, Optimize {#sec-methods-generation-prediction-optimization}

```{=latex}
\abstract*{Architecture 2.0 needs a method-selection discipline for AI-assisted and agentic architecture loops, not a catalog of algorithms. Generation, prediction, optimization, critique, repair, verification, explanation, and coordination are roles inside a design loop. Which role matters depends on the task, representation, environment, feedback budget, evidence burden, and cost of being wrong.}
```

::: {.callout-crux}
Which role should an AI method play in the loop, and what feedback would make
its output worth trusting?
:::

@sec-architecture-environments-tool-interfaces defined the environment: the place where actions are taken and
feedback is observed. This chapter asks which methods belong inside that
environment. The answer is not a ranking of current models or automation frameworks.
It is a discipline for matching method roles to architecture work.
The forcing function is that AI systems can now draft, call tools, revise
artifacts, and recommend next actions, so the loop must say what each action is
allowed to mean.

The distinction matters. A model that can generate plausible schedules,
configuration files, code fragments, RTL snippets, or design prose may be
useful for drafting alternatives, but weak for choosing among them. A
surrogate may predict latency or energy well inside a calibrated accelerator
design region, but fail outside the sampled space. Bayesian optimization may
spend scarce simulator or synthesis evaluations carefully, but only if the
action space and objective are well formed. Reinforcement learning may be
attractive for placement, scheduling, or adaptive control, but dangerous when
invalid actions are common and feedback is delayed. A critic may be more
valuable than a generator when the urgent problem is exposing missing workload
evidence, not proposing more candidates.

Architecture 2.0 therefore treats methods as roles in a compound design
system. A credible loop might include a generator that proposes candidates, a
predictor that estimates behavior, an optimizer that selects the next
experiment, a critic that challenges assumptions, a repair method that revises
invalid artifacts, a verifier that checks constraints, an explanation role that
makes evidence legible, a coordinator that routes state among those roles, and a
human architect who decides whether the evidence is strong enough to proceed.
The method question is not "Which AI system is best?" It is "Which role is
needed, what feedback can support it, and what evidence would make its output
credible?"

Machine learning for architecture did not begin with recent generative methods. A useful
historical shorthand is prediction, optimization, and generation. Prediction
appears in regression models, learned surrogates, and calibrated performance
or power estimators. Optimization appears in Bayesian optimization, autotuning,
reinforcement learning, and search over compiler, mapping, placement, or
architecture parameters. Generation now appears in natural-language-to-code,
RTL, test, configuration, and design-report artifacts. The shorthand is useful
because it gives proper credit to earlier work. It is also incomplete. The
Architecture 2.0 question is how these roles compose with critique, repair,
verification, explanation, provenance, negative traces, and human rejection
authority inside one explicit loop.

::: {.callout-learning-objectives}
After this chapter you can turn "we used AI method X" into the method-role view of
the design-loop card.
That means you can:

- match an AI method role (generate, predict, optimize, critique, repair, verify,
  explain, or coordinate) to an architecture task;
- distinguish role composition from stronger evidence when several automated methods
  participate;
- state an AI method claim as object, action, feedback fidelity, rejection condition, commitment boundary, and decision owner;
- assess hardware awareness as a staged capability, not the use of hardware vocabulary;
- decide when critique, repair, or verification is more valuable than generating more candidates;
- choose an AI method by loop conditions rather than by fashion.
:::

## Match the Method to the Architecture Task

The first step is to name the architecture task. Design-space exploration,
workload characterization, benchmark construction, code generation, RTL
repair, compiler/runtime tuning, accelerator search, chiplet partitioning,
physical-design assistance, and evidence critique are not the same problem.
They expose different state, allow different actions, tolerate different
errors, and require different feedback.

This is why environment work such as ArchGym, the worked example of
@sec-architecture-environments-tool-interfaces, matters here: it makes method
comparisons meaningful by defining tasks, actions, observations, workloads,
and feedback [@KrishnanEtAl2023ArchGym]. But even a shared environment
does not decide which method role is appropriate. The role depends on what
the loop is trying to accomplish.

@fig-method-role-map shows the chapter's working map. The same
architecture loop can contain several method roles, but each role has a
different claim and a different evidence requirement.

![Method roles are useful only inside a represented loop: Generation, prediction, optimization, critique, repair, verification, explanation, and coordination each need explicit state, feedback, and rejection.](images/F7-method-role-map){#fig-method-role-map width="100%" fig-alt="Role map showing generation, prediction, optimization, critique, repair, verification, explanation, and coordination as bounded method roles inside a represented architecture loop."}

Read the figure as a role map, not as a claim that every loop needs every role.
A loop can use generation for breadth, prediction for cheap ranking,
optimization for sample allocation, critique for missing assumptions, repair for
invalid artifacts, verification for independent rejection, and explanation for
reviewable evidence. Coordination is the routing role that keeps those actions
attached to shared state and authority boundaries. The method selection question
is which role the current loop can support with feedback.

@tbl-method-role-discipline gives the checklist form. Read each row as a
review prompt: what is the role doing, what evidence supports it, and what
failure mode should the loop be prepared to reject?

| Role | Architecture use | Evidence needed | Failure mode |
| --- | --- | --- | --- |
| Generate | Propose configs, specs, code, RTL fragments, test benches, design reviews, or hypotheses. | Validity checks, constraints, provenance, and human review. | Plausible but invalid candidates. |
| Predict | Estimate performance, energy, area, latency, reliability, or cost before full evaluation. | Calibration, uncertainty, coverage, and held-out checks. | Confident extrapolation outside support. |
| Optimize | Choose the next candidate or region of the space to evaluate. | Objective, constraints, feedback budget, and stopping rule. | Gaming the proxy or missing the real tradeoff. |
| Critique/repair | Find weak assumptions, missing evidence, invalid actions, or broken artifacts. | Access to artifacts, claims, evidence, and rejection authority. | Polished explanations without authority to reject. |
| Verify | Check constraints, invariants, tests, tool outputs, and evidence ledgers. | Independent checks, provenance, and escalation rules. | Treating one tool pass as final truth. |
| Explain | Make tradeoffs, failures, uncertainty, and rejected alternatives legible to a reviewer. | Traceable evidence, assumptions, contrast cases, and stated limits. | Convincing story without provenance or support. |
| Coordinate | Route state, tasks, tool calls, and evidence among role-specific tools or autonomous systems. | Shared state schema, authority boundaries, logs, and stop or escalation rules. | Hidden delegation, duplicated authority, or consensus without independent rejection. |

: Each method role needs different evidence: Generation, prediction, optimization, critique, repair, verification, explanation, and coordination make different claims and therefore require different rejection checks. {#tbl-method-role-discipline tbl-colwidths="[18,28,25,19]"}

The discipline behind the table is simple. A method claim is incomplete until
it names the architecture object being changed or estimated, the interface
through which the action is legal, the feedback fidelity that supports the
claim, the condition that can reject it, and the commitment level and decision
owner the evidence can support.

::: {.callout-engineer-move title="State every AI method claim concretely"}
Write the AI method claim as a sentence: this method's role acts on this architecture object
through this interface, receives this feedback at this fidelity, can be rejected
by this evidence, and supports only this commitment level owned by this named
decision owner.
:::

@tbl-method-object-discipline gives concrete examples. The same
method family can be reasonable or unreasonable depending on which object it
touches and what can say no. A generator that proposes benchmark questions is
different from one that proposes RTL. A predictor that ranks early simulator
configurations is different from one that claims final power. An optimizer
that chooses the next cheap proxy run is different from one that commits a
physical-design change.

| Role | Object to name | Feedback to require | Rejection condition |
| --- | --- | --- | --- |
| Generate | Workload variant, simulator config, tensor schedule, kernel, RTL fragment, EDA constraint, or design-loop card. | Parser, compiler, simulator, test harness, constraint checker, or human review. | Invalid syntax, unsupported action, wrong output, violated constraint, or missing provenance. |
| Predict | Latency, energy, area, memory traffic, timing risk, thermal behavior, queueing delay, or deployment impact. | Calibration data, uncertainty, coverage region, held-out checks, and fidelity label. | Out-of-support query, counterexample, proxy mismatch, or uncalibrated extrapolation. |
| Optimize | Next design point, parameter region, schedule, dataflow, mapping, placement move, or experiment allocation. | Objective, constraints, feedback budget, cost model, and stopping rule. | Proxy gaming, infeasible candidate, lost Pareto tradeoff, or exhausted evidence budget. |
| Critique/repair | Benchmark claim, simulator log, configuration file, test bench, evidence ledger entry, evidence table, or rejected alternative. | Access to artifact provenance, claims, assumptions, and comparison baseline. | Missing workload coverage, stale tool version, unsupported conclusion, or unresolved failure. |
| Verify | Invariant, interface contract, numerical tolerance, synthesis constraint, regression result, or evidence ledger. | Independent checks, replayable commands, tool logs, and escalation record. | Failed check, inconsistent evidence, weak fidelity, or architect refusal to commit. |
| Explain | Tradeoff, failure, rejected candidate, model uncertainty, or tool warning that a reader must understand. | Traceable evidence, assumptions, contrast with alternatives, and limits of the explanation. | Explanation without provenance, unsupported causal story, or hidden uncertainty. |

: Method claims need object discipline: A result is more credible, comparable, and reviewable when it states whether the method acted on prompts, code, traces, configs, RTL, reports, or decisions and what evidence can reject that action. Comparability requires matching object, action, feedback, rejection, and commitment fields. {#tbl-method-object-discipline tbl-colwidths="[16,25,25,24]"}

## Hardware Awareness as Staged Capability

Naming the architecture object a method touches raises a prior question:
whether the method actually understands the hardware behind that object, or
only borrows its terms. The staged view that follows makes the crux's second
half concrete for hardware: the level of hardware awareness a method can be
held to is set by the level of feedback that can reject its output. Hardware
awareness is not the same as using hardware vocabulary. A generated
proposal can mention caches, vector units, power targets, or a process node and
still be unaware of the architectural consequences of those terms.

> **Hardware awareness.** In this chapter, hardware awareness means that a
> method or AI-assisted system can represent hardware-relevant constraints, act within a valid
> hardware/software design space, obtain feedback from appropriate tools or
> measurements, and expose evidence that can reject its own output.

This definition matters because Architecture 2.0 methods will often generate
or revise artifacts near the hardware/software boundary: kernels, compiler
settings, accelerator configurations, RTL fragments, memory-system choices,
placement constraints, or design reports. Hardware-aware neural architecture
search[^fn-neural-architecture-search-c06] already shows the value of putting latency, energy, memory footprint,
and target-device cost into the search problem
[@BenmezianeEtAl2021HardwareAwareNAS]. Architecture 2.0 uses a broader
version of the same discipline: the question is not whether an artifact sounds
hardware-aware, but what level of hardware-aware action and evidence the loop
can support.

@fig-hardware-awareness-ladder gives the working capability map. The levels
are cumulative as an assessment vocabulary, but they are not a claim that every
system improves along one monotone axis. A tool wrapper may compile and profile
without having a strong performance model. A calibrated surrogate may estimate
uncertainty without directly controlling a tool. The staging is useful because
it forces the reader to ask which capability a method actually has, which
capability it lacks, and what the loop is allowed to do with the result.

Vocabulary awareness is useful, but it only names the objects. Constraint
awareness applies declared budgets and limits such as power, area, latency,
memory, precision, reliability, and process assumptions. Performance-model
awareness reasons about the mechanisms that drive cost: data movement,
locality, bandwidth, occupancy, parallelism, pipelines, and communication.
Here, "performance model" means a cheap analytical, learned, or surrogate
estimator used before live tool execution.
Tool and environment awareness connects those mechanisms to compilers,
profilers, simulators, synthesis reports, and failed runs; a simulator such as
gem5 can itself be a tool environment when the loop invokes it, records
configurations and outputs, and treats its result as feedback rather than as an
abstract ranking. Evidence awareness
adds calibration, uncertainty, proxy mismatch[^fn-proxy-mismatch-c06], fidelity, and negative traces.
Commitment-boundary awareness is the highest level because the loop can state
what the method may recommend, what must be escalated, and why the architect
still owns the commitment.

::: {.callout-architect-checkpoint title="The Escalation Boundary"}
When the method reaches the limit of its evidence fidelity or encounters a constraint it cannot safely resolve, it must escalate to the architect. The decision gate here relies on the AI loop's ability to clearly state its uncertainty and preserve negative traces, allowing the human architect to make the final commitment.
:::

Functional correctness is cross-cutting, not optional. Once a loop changes an
executable or synthesizable artifact, tests, reference outputs, formal checks,
type or interface checks, synthesis constraints, numerical tolerances, or
expert review must be able to reject it before performance claims matter.

![Hardware awareness is a staged capability: The assessment is not whether a method can mention hardware terms, but what it can safely change, what feedback supports the change, and what independent mechanism can reject it.](images/F7b-hardware-awareness-ladder){#fig-hardware-awareness-ladder width="100%" fig-alt="Stepped ladder of hardware awareness levels from vocabulary awareness to commitment-boundary awareness, with stronger evidence required at higher levels."}

The ladder is deliberately behavioral. A method that only uses hardware words is
at the vocabulary level. The assessment rises only when the loop can show valid
actions, constraint handling, tool feedback, calibration evidence, and a clear
architect-owned commitment boundary.

@tbl-hardware-awareness-assessment makes the assessment explicit.
Each level should be judged by what the method may change, what feedback
supports that change, and what can reject it.

| Capability | What it may change | Feedback needed | Rejection authority |
| --- | --- | --- | --- |
| Vocabulary | Terms in prompts, reports, or design notes. | Human review of meaning and misuse. | Architect rejects fluent but empty claims. |
| Constraint | Candidate fields within declared budgets or limits. | Bounds, static checks, invalid-action filters, and feasibility rules. | Constraint violation or illegal action. |
| Performance model | Rankings, estimates, or parameter choices inside model support. | Calibration, sensitivity, residuals, and held-out checks. | Model miss, counterexample, or out-of-support query. |
| Tool/environment | Code, configs, kernels, traces, or tool-invoked candidates. | Compile, run, profile, simulate, synthesize, and log tool outcomes. | Failed test, tool error, profile regression, or invalid artifact. |
| Evidence and calibration | Confidence, evidence strength, and escalation recommendations. | Multi-fidelity comparison, uncertainty, provenance, and negative traces. | Proxy mismatch, weak provenance, or fidelity failure. |
| Commitment boundary | Recommend, explain, or escalate within stated limits. | Evidence ledger, rollback cost, risk, and review context. | Human architect or independent verification refuses commitment. |

: Hardware awareness should be assessed by behavior, not vocabulary: The loop must show whether a method can represent constraints, take valid actions, obtain feedback, expose evidence, and reject its own output. {#tbl-hardware-awareness-assessment tbl-colwidths="[18,24,27,21]"}

The table is still too abstract unless each level has a falsifiable test.
@tbl-hardware-awareness-tests gives the reviewer version. A method should not
claim a higher level unless it can pass the observable test for that level in
the current loop.

| Claimed level | Reviewer test | Evidence to attach |
| --- | --- | --- |
| Vocabulary | Can the method use architecture terms without changing their meaning? | Human review notes or corrected definitions. |
| Constraint | Does it reject illegal parameter combinations before scoring them? | Constraint logs, invalid-action traces, and rejected examples. |
| Performance model | Does it state the calibrated range and fail or escalate outside it? | Calibration plot, held-out error, sensitivity result, or uncertainty record. |
| Tool/environment | Can it run the tool path and preserve both successes and failures? | Commands, versions, seeds, logs, failed runs, and replay instructions. |
| Evidence and calibration | Can it explain why one feedback source is strong enough for one claim and too weak for another? | Fidelity labels, proxy-mismatch examples, and escalation thresholds. |
| Commitment boundary | Can it recommend or escalate without pretending to own the decision? | A shareable evidence ledger, review note, residual risk, and named decision owner. |

: A hardware-awareness claim should be falsifiable: Reviewers should ask for
observable tests, not only fluent hardware language. {#tbl-hardware-awareness-tests tbl-colwidths="[20,38,32]"}

The level label is not the claim. The claim is the method-role view the loop
can actually support on the design-loop card: object, interface, feedback
fidelity, rejection rule, commitment boundary, and decision owner.

A kernel-generation loop that can compile, test, and profile generated kernels
has tool awareness. It does not automatically have evidence awareness unless
the loop records numerical correctness, speedup distributions, portability,
rejected candidates, and proxy mismatch. A design-space generative method that can propose
accelerator parameters has constraint awareness only if invalid actions are
blocked or rejected. It reaches commitment-boundary awareness only if the loop
can connect workload intent, hardware resource limits, compiler/runtime
assumptions, fidelity gates, and human decision points into one accountable
loop.

```{=latex}
\FloatBarrier
```

## Generation: Proposing Candidates and Artifacts

With hardware awareness established, we can examine specific method roles. Generation is the most visible AI role because fluent artifacts are easy to
demonstrate and easy to overtrust. A method can draft an architecture
description, propose a simulator
configuration, generate code, produce a test bench, write a design-review
summary, suggest a memory hierarchy, sketch an accelerator interface, or
enumerate hypotheses about a workload. In the lighthouse example, generation
might propose a set of candidate vector widths, local memory sizes, data
layouts, or CPU/accelerator partitions for the XRBench workload.

The danger is to mistake candidate generation for design. Generated artifacts
are useful when they expand the set of possibilities, expose alternatives, or
accelerate tedious translation. They are not credible merely because they are
well formed. The loop still needs validity checks, tool execution, evidence,
rejected alternatives, and human decision.

A generated RTL fragment, parameter set, or benchmark question is a proposal.
Generation earns its place only when it feeds a loop that can test, reject,
compare, and revise. Furthermore, candidate generation extends beyond writing direct code; for hardware, searching the High-Level Synthesis (HLS) pragma space (e.g., pipeline depths, unroll factors) is often a richer, more verifiable generative target than raw RTL synthesis. Similarly, for spatial architectures (like tensor accelerators), the AI loop must explicitly manipulate *dataflow*—the spatial and temporal unrolling of operations—as a primary structural contract, not just a scalar hyperparameter.

::: {.callout-failure-mode title="Treating AI generation as design"}
It is tempting to treat a fluent AI-generated artifact, an RTL fragment, a config,
a benchmark question, as a result. It is not. An AI-generated artifact is a
proposal; it becomes a result only after the AI-assisted loop tests it, prices its evidence,
compares it against a baseline, and an architect accepts the commitment.
AI generation that is not embedded in a loop that can reject it is demonstration,
not design.
:::

The strongest near-term use of generation may be breadth. It can propose
candidate decompositions, list assumptions, create alternative experiment
plans, translate design intent into structured records, or draft the first
version of a design-loop card (@sec-appendix-b-design-loop-card gives the full card and rubric). Those outputs are valuable because they give
the architect more structured material to inspect. They become dangerous only
when the loop treats them as decisions.

Kernel generation is a useful concrete case because it isolates the software
and code-generation facet of the lighthouse prompt. The XRBench subsystem only
matters if kernels, libraries, runtime paths, and target-specific code can be
generated, checked, and maintained. KernelBench asks whether language
models can generate correct and efficient GPU kernels for PyTorch workloads
[@OuyangEtAl2025KernelBench]. The Architecture 2.0 lesson is not that
kernel generation solves hardware/software co-design. It is that generation
becomes meaningful only when it is embedded in a harness that can compile,
run, test, profile, compare against a baseline, reject wrong outputs, and
preserve negative traces. Follow-on kernel-generation benchmarks make the
lesson sharper: multi-platform settings expose backend and portability
contracts [@WenEtAl2025MultiKernelBench], while category-aware analyses
show that correctness, task structure, numerical contracts, and efficiency can
diverge [@WangEtAl2026KernelBenchX]. That is precisely why generation is
a role in a loop, not the loop itself. @sec-loop-patterns-across-stack makes the
point quantitative: the loop is rejection-bound, and candidate count does not
enter its throughput bound at all, so generating more proposals cannot speed a
loop whose cheap, independent rejection coverage stays fixed.
The transferable object is the harness contract: target platform, correctness
oracle, numerical tolerance, baseline, failed kernels, portability boundary, and
the rejection rule that stops a fast but wrong artifact.

The same discipline appears closer to hardware. Chip-Chat reports a
conversational loop in which a language model drafts Verilog, open-source
simulation and synthesis tools check it, the resulting errors are fed back for
revision, and a small processor design is carried as far as fabrication
[@BlockloveEtAl2023ChipChat; @ThakurEtAl2023VeriGen; @HeEtAl2024LLM4EDA]. The interesting part is not that a model produced
Verilog. It is that the loop could support a bounded, reviewable commitment
because a parser, a simulator, and a synthesis flow could each reject a draft,
and a human stayed in the conversation to decide when a candidate was good
enough to commit.
Generation supplied breadth; the environment and the architect supplied the
authority to reject.

## Prediction: Estimating Behavior before Full Evaluation

While generation supplies candidate breadth, prediction is central because architecture feedback is expensive. Long before
recent foundation models, architects used statistical and machine-learning
models to reduce the cost of exploring large design spaces. Regression models
for microarchitectural performance and power, and predictive modeling for
large architectural design spaces, are part of this lineage
[@LeeBrooks2006RegressionModeling; @IpekEtAl2006PredictiveDSE].
Architecture 2.0 uses that lineage only when the predictor exposes what an
agentic loop needs: the support region, uncertainty, calibration source,
escalation trigger, and decision owner.

The prediction role is not limited to performance. A predictor might estimate
energy, area, latency, reliability, queueing behavior, memory traffic,
thermal behavior, compile time, implementation feasibility, or deployment
impact. It might be a regression model, a learned surrogate, a calibrated
analytic model, a simulator-backed approximation, or a hybrid that combines
domain structure with data.
In an agentic loop, a predictor is not an oracle; it is a gate that decides
whether the system may prune, defer, escalate, or ask for stronger feedback.

Some of these targets are harder to pin down than others. A single-kernel
latency can be a fairly clean estimate, while deployment impact compounds power,
thermal behavior, and reliability over the life of a design, so it resists any
single-point prediction.

The key requirement is uncertainty. A point estimate is useful only if the
loop understands where it is valid. Has the predictor seen similar workload
regions? Does it extrapolate across a new memory behavior, vector width, or
technology assumption? Does it report confidence? Is it calibrated against a
higher-fidelity source? Does it preserve enough provenance to explain why a
candidate was trusted?

There is a rigorous way to make this concrete when the assumptions are
appropriate. Conformal prediction can wrap a surrogate, regardless of its
internals, so that it emits calibrated prediction sets: intervals that contain
the true value with a user-chosen probability under an exchangeability[^fn-exchangeability-c06]
assumption [@AngelopoulosBates2021Conformal]. Architecture loops must audit
that assumption because workloads, tools, and process corners are often not
exchangeable. Still, the pattern is useful. It converts "report confidence"
from a slogan into an operation. The predictor writes an interval, calibration
receipt, and support-region label into the loop state; the environment may use
that record only to prune, escalate, or defer, not to make an unowned
commitment. The guarantee does not require assuming any particular error
distribution for the surrogate, which is
useful for architecture surrogates with awkward error shapes. But it still
depends on the calibration assumption being meaningful; under distribution
shift, the interval is a diagnostic that should trigger scrutiny rather than a
promise that the proxy is safe.

For the lighthouse prompt, a predictor could help screen candidate compute
subsystems before full simulation or synthesis. But the evidence burden
depends on the decision. A rough predictor may be enough to discard obviously
bad candidates. It is not enough to claim that a design meets a 3\ W target on
a 3\ nm-class low-power mobile process. The stronger the commitment, the
stronger the calibration and fidelity requirement.

## Optimization: Learning the Design Space

Once candidates are generated and their behavior predicted, the loop must decide what to evaluate next. Optimization is often framed as search: find the best point under an
objective. Architecture needs a richer formulation. The useful goal is to
learn the design space well enough to make a defensible decision under
limited feedback. That may mean finding a Pareto region[^fn-pareto-region-c06], identifying a
constraint boundary, understanding a sensitivity, ruling out a class of
candidates, or deciding which expensive experiment is worth running next.

Optimization methods are useful here when they make the loop's sampling policy
representable and rejectable. Bayesian optimization is attractive for
Architecture 2.0 because it was built for expensive black-box functions and sequential experimentation
[@JonesSchonlauWelch1998EGO; @SnoekLarochelleAdams2012BayesianOptimization].
It encourages the loop to trade off exploration and exploitation, to reason
about uncertainty, and to spend evaluations where they are likely to matter.
Those properties align naturally with architecture settings where simulator,
synthesis, or measurement runs are costly.
In Architecture 2.0, the policy that picks the next sample, the **acquisition
policy**, is itself a logged action proposal:
it must name the candidate, the fidelity level, the expected decision value, and
the condition under which the sample will be rejected or escalated.
For an AI-assisted system, optimization is therefore not autonomous selection of the best
design; it is an auditable policy for spending scarce feedback.

Reinforcement learning is attractive when the problem is sequential: placement
decisions, scheduling policies, adaptive control, or multi-stage design flows.
The chip-floorplanning literature gives a prominent, and contested, example of
posing a chip design subproblem as a learning problem
[@MirhoseiniEtAl2021GraphPlacement]. @sec-feedback-verification-trust discusses
the later baseline and reproducibility challenge. The important lesson for this
chapter is not that every architecture task should become RL. It is that method
choice depends on state, action, transition, feedback, and commitment structure.

A narrower example shows what happens when the design space is bounded tightly
enough that the environment can supply real rejection authority. PrefixRL casts the design of parallel-prefix
arithmetic circuits, such as adders, as a reinforcement-learning problem with
logic synthesis in the loop, so every proposed circuit is scored by an actual
synthesis run rather than a hand-built proxy [@RoyEtAl2021PrefixRL]. The
important receipt is that each candidate was a bounded circuit object,
evaluated by a synthesis-backed environment, and rejected or advanced by
evidence stronger than a hand-built proxy.
The contrast with the placement dispute is the lesson, not the leaderboard: the
same method family is contested when its reward is a fast proxy and defensible
when a bounded action space lets a high-fidelity instrument reject every
candidate. Method choice is inseparable from what the environment can verify.

Autotuning and compiler optimization provide another useful precedent. For example, deep reinforcement learning has been successfully applied to discover faster sorting algorithms from assembly instructions [@MankowitzEtAl2023AlphaDev] and to navigate complex high-level synthesis phase orderings [@HajAliEtAl2020AutoPhase]. General
program-autotuning frameworks such as OpenTuner [@AnselEtAl2014OpenTuner], and
tensor-program optimizers such as AutoTVM and Ansor, share a loop structure
worth naming: a learned cost model proposes promising candidates, the loop
compiles and measures the strongest of them on real hardware, and those
measurements correct the cost model for the next round
[@ChenEtAl2018AutoTVM; @ZhengEtAl2020Ansor]. That is an active-learning loop
running in production: the cheap proxy is never trusted alone, because
high-fidelity feedback continually re-grounds it. These systems are not
identical to microarchitecture design, but they are lighthouse facets rather
than unrelated detours. Floorplanning stresses high-commitment physical feedback; autotuning
stresses the compiler/runtime path that makes specialization usable. Both
illustrate a durable pattern: a method is
powerful when it is embedded in an environment that exposes legal actions,
measures feedback, updates a cost model, and records results.
For Architecture 2.0, the transferable pattern is the record: candidate
schedule, compiler/runtime version, measurement context, failed variants,
cost-model update, and the human-owned boundary on what the measurement can
prove.

The optimizer should therefore be evaluated by what it learns and what it can
explain, not only by its best score. Did it discover a robust region? Did it
identify a proxy mismatch? Did it spend high-fidelity evaluations carefully?
Did it preserve rejected alternatives? Did it show why one candidate was
chosen over another? If the answer is no, the loop may have optimized a
number without improving architectural understanding.

## Sample Efficiency under Expensive Feedback

Whether an optimizer spends its scarce high-fidelity evaluations carefully is
itself the problem of sample efficiency[^fn-sample-efficiency-c06], which is one of the reasons architecture is a hard AI domain.
Many AI settings assume abundant feedback. Architecture often has the
opposite shape: a small number of high-fidelity runs, a larger number of
medium-fidelity simulations, many cheap proxies, and a long tail of hidden
costs such as expert review, tool setup, debugging, and license availability.

@fig-evidence-gap turns that mismatch into a count-scale picture. The upper
rows reuse the design-space anchors from @sec-design-loop-no-longer-scales: the
12,960-state slice computed there, the accelerator DSE scale of MAESTRO, an analytic model for
evaluating DNN dataflows, AutoTVM-style operator tuning spaces, and the core
mapspace expression of Timeloop, a mapping and evaluation framework
[@KwonEtAl2019MAESTRO; @ChenEtAl2018AutoTVM; @ParasharEtAl2019Timeloop]. The
lower rows reuse the representative feedback budgets from @sec-architecture-environments-tool-interfaces. These
counts are not identical scientific quantities. The point is the scale
mismatch: high-fidelity architecture evidence can touch only a tiny slice of
the plausible candidate space, so methods must decide what can be screened by
proxies, what should be escalated, and what rejected regions must be recorded.

```{python}
#| label: fig-evidence-gap
#| fig-cap: |
#|   Architecture methods face an evidence gap: Design spaces can contain orders of magnitude more candidates than a loop can afford to test at stronger feedback levels. The plot compares counts only as scale intuition: source-backed or transparent design-space anchors above the divider, representative sample-budget ranges below it.
#| out-width: "100%"
#| fig-alt: "Log-scale comparison of large design-space candidate counts against much smaller affordable feedback sample budgets, highlighting an evidence gap."

import matplotlib.pyplot as plt
from _python.arch2_plots import COLORS, add_note_box, apply_style, draw_range_rows, top_log_axis

rows = [
    {"display_label": "12,960-state slice", "display_note": "before corners/workloads", "count_low": 12_960, "count_high": 12_960, "right_label": "~1.3e4", "color": COLORS["orange"]},
    {"display_label": "MAESTRO accelerator DSE", "display_note": "reported candidate search scale", "count_low": 480_000_000, "count_high": 480_000_000, "right_label": "480M", "color": COLORS["orange"]},
    {"display_label": "AutoTVM operator tuning", "display_note": "reported order-of-billions space", "count_low": 1_000_000_000, "count_high": 1_000_000_000, "right_label": "~1B", "color": COLORS["orange"]},
    {"display_label": "Timeloop mapspace core", "display_note": "lower bound before factor choices", "count_low": 2_600_000_000_000_000_000, "count_high": 2_600_000_000_000_000_000, "right_label": ">2e18", "color": COLORS["orange"]},
    {"display_label": "cheap proxy screening", "display_note": "representative affordable checks", "count_low": 100_000, "count_high": 1_000_000, "right_label": "1e5-1e6", "color": COLORS["blue"]},
    {"display_label": "cycle-level comparisons", "display_note": "representative scoped runs", "count_low": 10, "count_high": 100, "right_label": "10-100", "color": COLORS["blue"]},
    {"display_label": "RTL / physical feedback", "display_note": "scarce high-fidelity samples", "count_low": 3, "count_high": 20, "right_label": "3-20", "color": COLORS["blue"]},
    {"display_label": "silicon / deployment checks", "display_note": "few high-commitment samples", "count_low": 1, "count_high": 5, "right_label": "1-5", "color": COLORS["blue"]},
]

apply_style()
fig, ax = plt.subplots(figsize=(5.35, 2.95))
fig.subplots_adjust(left=0.38, right=0.85, top=0.82, bottom=0.27)

y_positions = [0.35, 1.35, 2.35, 3.35, 5.80, 6.80, 7.80, 8.80]
ax.set_ylim(-1.05, y_positions[-1] + 0.65)
ax.invert_yaxis()
ax.set_yticks([])
top_log_axis(
    ax,
    xlim=(0.8, 1e19),
    xticks=[1, 1e2, 1e4, 1e6, 1e9, 1e12, 1e15, 1e18],
    xticklabels=["1", r"$10^2$", r"$10^4$", r"$10^6$", r"$10^9$", r"$10^{12}$", r"$10^{15}$", r"$10^{18}$"],
    xlabel="count scale: candidates or affordable samples",
    tick_fontsize=6.0,
)

ax.axhline(4.45, color="#AAB4BF", linewidth=0.65, linestyle="--", zorder=0)
ax.text(-0.88, -0.55, "design-space anchors", transform=ax.get_yaxis_transform(), ha="left", va="center", fontsize=5.8, fontweight="bold", color="#8C5A1F", clip_on=False)
ax.text(-0.88, 5.10, "affordable feedback budgets", transform=ax.get_yaxis_transform(), ha="left", va="center", fontsize=5.8, fontweight="bold", color=COLORS["note_text"], clip_on=False)

draw_range_rows(ax, rows, low_key="count_low", high_key="count_high", label_x=-0.82, right_x=1.04, label_fontsize=6.15, right_fontsize=5.85, y_positions=y_positions, show_notes=False)
add_note_box(fig, "Counts are comparable only as scale intuition;\nhigh-fidelity evidence samples a tiny slice.", xywh=(0.12, 0.035, 0.76, 0.10), fontsize=5.4)

plt.show()
plt.close(fig)
```

@sec-data-representations-world-models treated sample cost as data the representation must carry. Here the
same idea becomes a method-selection criterion. A sample is any feedback event
that changes what the loop believes: a simulator result, tool warning, failed
run, synthesis report, benchmark measurement, expert rejection, or
higher-fidelity validation. The loop should not maximize sample count. It
should spend feedback where decision value per unit cost is highest:
$$
V_{\mathrm{sample}} \approx \frac{\Delta D}{C_{\mathrm{sample}}},
$$
where $\Delta D$ denotes the change in decision confidence, rejected-space
coverage, or evidence strength produced by that sample. Neither term is
directly measurable; the relation is a way to rank candidate experiments by
what they would resolve, not a number to compute and literally optimize.

This heuristic has a rigorous counterpart. Bayesian optimization makes the
choice of the next sample an explicit acquisition function (a rule that scores
each candidate next-sample) over a surrogate's posterior (its current
probability estimate over outcomes), and GP-UCB (Gaussian Process Upper
Confidence Bound) gives that choice a no-regret guarantee[^fn-no-regret-guarantee-c06] under stated
assumptions, so the loop can defend why it sampled where it did rather than
appealing to intuition [@SrinivasEtAl2010GPUCB]. Multi-fidelity Bayesian
optimization goes one step further and treats the fidelity level itself as a
decision variable: it chooses not only which candidate to evaluate but whether
to spend a cheap proxy or an expensive simulation on it, exactly the choice the
fidelity ladder poses [@KandasamyEtAl2017MultiFidelityBO]. The architecture
loop usually needs the contract more than the proof apparatus: what rule chose
the sample, what assumptions made that rule legal, what evidence came back, and
what threshold forced escalation. The loop still has to record the acquisition
rule, fidelity choice, assumptions, rejected alternatives, and escalation
threshold, or the optimizer becomes another opaque source of candidates.

> **Fidelity ladder.** A fidelity ladder is the ordered set of feedback levels
> a loop can climb, from cheap proxies through simulation, synthesis, physical
> feedback, deployment, or silicon evidence, with higher levels usually costing
> more but carrying stronger rejection authority.

@tbl-sample-efficiency-regimes gives a simple way to think about
the regimes. The numbers are illustrative, not prescriptions. The point is
that method choice changes when feedback is measured in milliseconds,
minutes, hours, weeks, or silicon cycles.
The fidelity ladder is therefore a budget discipline: cheap levels buy breadth,
and expensive levels buy rejection authority.

| Regime | Typical setting | Method implication | Evidence discipline |
| --- | --- | --- | --- |
| Many cheap proxy runs | Analytic models, rough estimators, compiler hints. | Broad search, candidate generation, surrogate pretraining. | Track proxy validity and avoid overfitting the cheap metric. |
| Hundreds of simulations | Simulator-backed DSE or workload sweeps. | Bayesian optimization, active learning, transfer, sensitivity analysis. | Record seeds, configs, workloads, and failed runs. |
| Tens of expensive tool runs | Synthesis, physical design, emulation, or hardware-in-the-loop. | Strong priors, staged gates, human filtering, small candidate sets. | Require calibration and explicit rejection authority. |
| Few high-commitment checks | Silicon, deployment, fleet experiments, or customer workloads. | Critique, evidence organization, conservative recommendations. | Human decision and audit trail dominate. |

: Feedback regime should drive method choice: Cheap proxies, moderate simulations, expensive EDA, and scarce high-commitment checks reward different mixtures of generation, prediction, optimization, critique, and verification. {#tbl-sample-efficiency-regimes tbl-colwidths="[18,24,26,22]"}

This is where negative traces matter. Failed simulations, invalid candidates,
timeouts, rejected configurations, and proxy mismatches are not noise to be
discarded. They are information about the boundary of the design space. A
sample-efficient loop should learn from what failed, not only from the points
that produced clean plots.

Sample efficiency also depends on representation. If the environment logs
only final scores, the method cannot reuse much. If it records workload
metadata, candidate structure, tool warnings, failure reasons, and fidelity
level, then each sample contributes more. @sec-data-representations-world-models and @sec-architecture-environments-tool-interfaces are therefore
not preliminaries to methods. They determine whether methods can learn.

## Critique, Repair, and Explanation

Beyond generating, predicting, and optimizing, loops often need to evaluate existing artifacts rather than propose new ones. Critique may be the most underrated method role in Architecture 2.0. Many
loops do not need a generative method to invent a new design. They need a system that can
read a proposed design, identify missing assumptions, check whether evidence
matches claims, compare alternatives, find invalid actions, repair artifacts,
or explain a tradeoff for review.

This role is especially attractive because it can operate against existing
human artifacts. A critic can inspect a design-space report, simulator log,
configuration file, benchmark description, or paper draft. It can ask whether
the workload matches the claim, whether the metric is a proxy for the real
objective, whether rejected candidates are missing, whether tool versions are
recorded, or whether a table proves less than the prose claims.

Question-answering resources such as QuArch point toward one piece of this
problem: making architecture knowledge accessible to automated optimizers and reviewers
[@PrakashEtAl2025QuArch]. But critique requires more than answering
questions from papers. It needs the loop state that papers often omit:
assumptions, tool settings, negative traces, evidence ledgers, and human
decisions.

This makes critique a throughput role, not merely a review convenience. In a
rejection-bound loop, a critic that catches a missing workload record, unsupported
proxy claim, stale tool version, or invalid action before an expensive run can
improve the loop more than another generator. It raises the rate at which weak
claims are rejected safely.

Repair is the constructive side of critique. A method can propose a corrected
configuration, fix a malformed constraint or tool-syntax error, patch a test
bench, regenerate a plot with the right workload metadata, or produce a clearer
design-loop card. Repair addresses malformed artifacts; it must not relax a
timing, power, interface, or signoff constraint the design actually violates,
because that constraint is a rejection authority, not a broken input. Loosening
one requires explicit architect review and a recorded waiver. Explanation then
becomes the interface to the architect: why a candidate was rejected, why
evidence is insufficient, or why one region of the space is worth more expensive
evaluation.

::: {.callout-architect-checkpoint title="Constraint Waivers"}
An automated method may repair malformed artifacts but must never relax a design constraint without explicit architect review. The decision gate here requires the AI loop to explain the violation and wait for a human-recorded waiver before proceeding.
:::

Verification, the remaining checking role, deliberately gets its own chapter:
@sec-feedback-verification-trust develops it as the family of rejection
authorities a loop needs, not as one more method to pick.

## Choosing a Method under Constraints

With these distinct roles defined, a good method choice should survive a design review. The reviewer should be
able to ask: What task is this method serving? What representation does it
read and write? What environment does it act in? What feedback can it afford?
What evidence would support its output? What can reject it? What happens if
it is wrong?

@tbl-method-selection-matrix is a compact decision matrix. It is
not meant to produce an automatic answer. It is meant to prevent method
selection from being driven by fashion.

| Question | If the answer is favorable | If the answer is unfavorable |
| --- | --- | --- |
| Is the task bounded? | Use stronger automation inside the boundary. | First decompose the task or keep the method advisory. |
| Does the loop need more candidates? | Use generation for breadth, with validity checks attached. | Prefer critique, verification, evidence organization, or better rejection tests. |
| Are actions validatable? | Let the environment reject illegal candidates. | Use generation only with strict human/tool review. |
| Is feedback cheap enough? | Search, active learning, or online adaptation may be useful. | Use priors, surrogates, staged gates, and critique. |
| Is uncertainty visible? | Prediction can guide exploration. | Avoid treating point estimates as evidence. |
| Is the commitment reversible? | Higher autonomy may be acceptable. | Require stronger evidence and human decision. |
| Is provenance recorded? | Claims can be replayed and audited. | Do not make strong comparative claims. |

: Method selection follows loop conditions: The right method posture depends on action validity, feedback cost, fidelity, rollback cost, and rejection authority, not on whether a technique is fashionable. {#tbl-method-selection-matrix tbl-colwidths="[20,31,31]"}

The matrix also clarifies why the same method may be appropriate in one
architecture loop and inappropriate in another. A generator may be acceptable
for drafting candidate simulator configs but not for committing a physical
design change. A surrogate may be useful for ranking early candidates but not
for final power claims. An RL policy may be reasonable in a reversible
runtime-control loop but not in a high-commitment design decision without
strong rejection authority.

::: {.callout-lighthouse title="Screen under the power envelope"}
Context. For the lighthouse design loop, the prompt is an AI method-selection
problem, not a request for more candidates.

In the Lighthouse prompt. The AI-assisted loop must choose among vector widths,
local-memory sizes, data layouts, and the "vector-capable CPU, accelerator, or
SoC block" partition for the "XRBench-class real-time mobile XR workload" while
respecting the "3\ W TDP target" and preserving a path to a "design-space report
with evidence and rejected alternatives."

Method role. Use AI generation to propose bounded candidates only if needed,
AI prediction to screen candidates with calibrated intervals, and AI optimization to
spend scarce simulator, compiler and runtime, synthesis, or verification runs
where they resolve the decision.

Takeaway. An AI surrogate may reject obviously bad points, but it cannot by
itself claim that a design meets a 3\ W target in a 3\ nm-class low-power mobile
process. The loop must escalate whenever the interval straddles the power or latency bound, or
when the win depends on a weak proxy for memory traffic, software reachability,
physical feasibility, or correctness.
:::

A useful Architecture 2.0 paper should be able to write the method choice as a
sentence: we use this method in this role because the task has this action
space, this feedback budget, this evidence burden, and this rejection authority.
If that sentence cannot be written, the method choice is probably floating above
the architecture problem.

The same rule covers multi-participant implementations. Splitting work across a planner,
generator, predictor, critic, verifier, and evidence writer may improve
throughput, specialization, or coverage, but it does not itself strengthen the
claim. The loop still has to say which participant owns which role, what shared state
they read and write, which actions are legal for each, which outputs require
independent rejection, and where authority returns to the architect. More participants
without that role contract only multiply unreviewable state transitions.

::: {#pri-match-methods .callout-design-principle title="Match methods to roles"}
Do not choose a method until the loop has named the bottleneck it is supposed to
relieve. Generation, prediction, optimization, critique, repair, verification,
explanation, and coordination are different jobs with different evidence
standards; a method earns trust only through the role the loop needs.
:::

## Why No Single Algorithm Wins

Architecture 2.0 should not age around one algorithm family. The field will
continue to change: models will improve, automation frameworks will change, tools
will expose new interfaces, and benchmarks will evolve. A durable book
should therefore encourage method discipline rather than method fashion.

The stable idea is that methods earn trust by their role in the loop. They
must match the task, representation, environment, feedback budget, fidelity
ladder, evidence standard, and commitment level. They should preserve negative
traces, expose uncertainty, and make rejection possible. They should help
architects learn the design space, not merely search it harder.

This chapter completes the core loop components: representation, environment,
and method. The next question is when loop feedback becomes decision-relevant
evidence. Once a loop can act and choose methods, how do we know whether its
feedback is evidence? @sec-feedback-verification-trust answers that question by
making fidelity, verification, rejection, and trust explicit.

## Open research questions

The discipline of assigning specific roles to AI methods exposes several unsettled research directions. Resolving these challenges will require moving beyond static benchmarks to evaluate how AI-assisted systems perform inside dynamic, resource-constrained architecture loops.

1. How can we empirically validate AI role contracts?
   Building on the role mappings in the "Match the Method to the Architecture Task" section, we need public corpora of loop traces that can prove whether a generator, predictor, or critic actually stayed within its commitment boundary. Research must determine what logging structures are sufficient to definitively audit an AI-assisted system's decision-making over time.
2. How do we learn continuously from heterogeneous failures?
   While the "Sample Efficiency under Expensive Feedback" section establishes the fidelity ladder, it remains unclear how an optimizer should mathematically update its priors from a mix of cheap tool warnings, proxy mismatches, and rare silicon failures. New active-learning methods must synthesize this negative trace data without blurring the boundary between proxy screening and evidence.
3. What constitutes a definitive rejection test suite?
   Moving beyond the assessment framework in the "Hardware Awareness as Staged Capability" section, the community lacks standardized test suites designed explicitly to reject an automated optimizer's unsupported predictions or invalid actions. We need formal mechanisms that map the passing of a specific environment's test suite to the maximum architectural commitment that suite is allowed to authorize.
4. How should loops dynamically reallocate method roles?
   The decision value heuristic introduced in the "Sample Efficiency under Expensive Feedback" section assumes the loop knows which method role to invoke next. Future research must design dynamic coordinators that automatically shift computational resources—for example, pivoting from generation for breadth to critique for depth—based on the remaining evidence budget and the cost of the next simulation.

## What to carry forward
- Reader test: Can you write one sentence explaining why this AI method belongs
  in this role for this AI-assisted loop?
- Next loop state: Once models and methods can act, the next question is whether their
  feedback becomes evidence strong enough to support trust.

[^fn-neural-architecture-search-c06]: **Neural architecture search (NAS)**: In this chapter, a cautionary adjacent field where search only becomes reusable when the search space, data, training budget, evaluation rule, and rejected alternatives are recorded.
[^fn-proxy-mismatch-c06]: **Proxy mismatch**: When a cheap stand-in metric diverges from the true objective it estimates, so optimizing the proxy stops improving the real goal; it is an instance of Goodhart's Law (when a measure becomes a target, it ceases to be a good measure), treated in full in @sec-feedback-verification-trust.
[^fn-exchangeability-c06]: **Exchangeability**: A statistical property where the joint probability distribution of a sequence of random variables is invariant to their permutation; it is a weaker assumption than independent and identically distributed (i.i.d.).
[^fn-pareto-region-c06]: **Pareto region**: The set of optimal solutions in a multi-objective design space where no single objective can be improved without degrading at least one other objective.
[^fn-sample-efficiency-c06]: **Sample efficiency**: In this chapter, the amount of decision-relevant evidence a loop gains per scarce feedback event, including failed runs and expert rejections, not just successful simulations.
[^fn-no-regret-guarantee-c06]: **No-regret guarantee**: In this chapter, a formal promise about a sampling rule under stated assumptions; useful only when the loop records whether those assumptions apply.
# Feedback, Evidence, and Trust {#sec-feedback-verification-trust}

```{=latex}
\abstract*{Architecture 2.0 does not ask architects to trust an AI-assisted system. It asks them to design loops in which claims become credible through feedback budgets, feedback regimes, evidence ledgers, rejection authority, security boundaries, and commitment boundaries. Trust is therefore not a property of a model's tone, confidence, or generated report. It is an engineered property of the loop.}
```

::: {.callout-crux}
How much should we believe a loop's AI-assisted result, and what evidence can
reject it before we commit?
:::

@sec-methods-generation-prediction-optimization treated methods as roles inside a design loop. This chapter asks
when the outputs of that loop should be believed. The answer is deliberately
conservative: an Architecture 2.0 result is credible only when the feedback
supporting it has been turned into evidence, the evidence can be audited, an
independent authority can reject the result, and the commitment boundary matches
the cost of being wrong.

This distinction between generated output and verified evidence is central to the book. A model can generate a plausible
architecture description. A search method can find a strong proxy score. A
surrogate can rank candidates. A tool-using agent[^fn-tool-using-agent-c07] can call simulators and
summarize results. None of those actions creates trust by itself. Trust
begins when the loop records what was measured, why it was relevant, how much
it cost, what assumptions it used, where the feedback is weak, which
alternatives failed, and what can say no.

The lighthouse prompt makes this need for evidence concrete. A proposed low-power 64-bit RISC-V
compute subsystem for XRBench under a 3\ W, 3\ nm-class low-power mobile
envelope might look reasonable under an analytic proxy, promising under
simulation, and broken under synthesis or timing. It might meet performance
while missing an energy or thermal target. It might pass a benchmark but fail
a real deployment scenario. Architecture 2.0 therefore needs an evidence
discipline that is as explicit as its representations, environments, and
methods. At the center of that discipline is verification, used here more
broadly than its usual formal-methods sense.

> **Verification.** Verification is used broadly in this chapter. It includes
> formal methods when formal properties are available, but it also includes type
> checks, interface checks, regression tests, baseline replay, simulator
> cross-checks, synthesis constraints, physical-design warnings, security
> review, workload coverage, and expert design review. The common requirement is
> independence: the check should be able to reject the claim, not merely restate
> the method's output.

Verification is therefore a family of rejection authorities, not a single tool
category. @tbl-verification-authorities gives a compact taxonomy for reading a
claim.
Inside AI-assisted loops, these authorities are not generic quality checks; they
define which generated state transitions may continue, be revised, or be
blocked.

| Verification authority | Typical evidence | What it can reject |
| --- | --- | --- |
| Syntax and interface checks | Parsers, type checks, API checks, ISA or ABI conformance, and schema validation. | Artifacts that cannot legally enter the loop. |
| Functional checks | Unit tests, reference outputs, assertions, simulation traces, and regression suites. | Candidates that compute the wrong behavior before performance matters. |
| Model and workload checks | Baseline replay, sensitivity studies, calibration, coverage, and drift tests. | Proxy wins outside the represented workload or calibrated support. |
| Implementation checks | Synthesis, timing, area, power, congestion, design-rule checks, and physical warnings. | Architecture candidates that fail implementation-adjacent reality. |
| Operational checks | SLOs, canary rollouts, rollback, telemetry, reliability, security, and incident review. | Claims that do not survive deployment conditions or policy boundaries. |
| Expert review | Design review, waived-warning review, risk acceptance, and commitment decision. | Results whose evidence is too weak for the proposed commitment. |

: Verification names who or what can say no: A credible claim should state
which independent authority can reject syntax, function, model support,
implementation feasibility, deployment behavior, or final commitment. {#tbl-verification-authorities tbl-colwidths="[21,36,33]"}

Inside an Architecture 2.0 loop, each check is bound to a represented state
field, a legal action, and a commitment boundary: it says which action may
continue, which state update is invalid, and when the loop must revise or
escalate.

To put these rejection authorities into practice, read the chapter as a sequence of review records rather than as separate trust
concepts. Each record answers a different question about the same claim;
@tbl-trust-record-map is the chapter's map. Two further sections, on proxy
mismatch and on confidentiality boundaries, defend the evidence ledger and the
trust checklist against gamed metrics and hidden evidence.

| Review record | Role in the loop | Reviewer question |
| --- | --- | --- |
| Feedback budget ledger | Records what feedback the loop can afford and what each source costs. | What evidence can the loop realistically buy? |
| Evidence ledger | Turns feedback into claim support with fidelity, provenance, uncertainty, and negative traces. | What supports or weakens the claim? |
| Commitment ladder | Matches evidence requirements to rollback cost, blast radius, and ownership. | How far may this claim go? |
| Rejection authority | Names the independent check that can say no. | What can stop a plausible but unsupported result? |
| Trust checklist | Combines claim, feedback, fidelity, provenance, confidentiality, rejection, and decision ownership. | Is the loop asking for a level of belief it has earned? |

: Trust review uses a family of records: The feedback budget ledger, evidence
ledger, commitment ladder, rejection authority, and trust checklist are not
separate paperwork. They are views of one question: whether a loop has enough
evidence and independent rejection to support the commitment it asks for.
{#tbl-trust-record-map tbl-colwidths="[22,37,31]"}

::: {.callout-learning-objectives}
After this chapter you can write or review the trust checklist for an
AI-assisted loop output.
That means you can:

- turn feedback into evidence through fidelity, provenance, and an evidence ledger;
- map the chapter's review records: feedback budget, evidence ledger, commitment ladder, rejection authority, and trust checklist;
- set escalation thresholds and commitment boundaries by reversibility and blast radius;
- name what can reject a result, and why rejection authority must be independent;
- review a claim with the trust checklist instead of by its tone.
:::

## Feedback Budget Ledger and Feedback Economics

@sec-architecture-environments-tool-interfaces used feedback regimes to design
environments, and @sec-methods-generation-prediction-optimization used them to
choose method roles. This chapter uses the same economics for trust:
escalation, rejection, and commitment.

In any loop, the first barrier to establishing this trust is economic. Feedback is not free, uniform, or
automatically useful. An architecture loop may have thousands of cheap proxy
evaluations, hundreds of simulations, tens of synthesis or physical-design
runs, a few emulation opportunities, and almost no chances to learn from
silicon or deployment mistakes. It may also have scarce human review time,
limited tool licenses, long queue delays, confidential workloads, and
organizational deadlines. These limits shape which methods are appropriate and
how much autonomy is acceptable.

This is why a loop needs a feedback budget ledger: a record of which
evaluations, measurements, tool runs, human reviews, and deployment signals are
available, what they cost, how long they take, how reversible they are, and
what level of decision they can support. The ledger is not
accounting bureaucracy. It is the object that tells the method what kind of
learning is possible. A Bayesian optimizer, reinforcement-learning policy[^fn-policy-c07],
surrogate model, critic[^fn-critic-c07], or tool-using agent should behave differently when a
feedback source takes milliseconds versus days, when a failed action is
reversible versus costly, and when the signal is a rough proxy versus a
signoff report. @tbl-feedback-budget-ledger gives the working
form.

| Budget item | What to record | Why it matters |
| --- | --- | --- |
| Latency and cost | Runtime, queue time, dollar cost, tool hours, license limits, and human review time. | Determines whether the loop should search broadly, sample carefully, or mostly critique. |
| Signal quality | Fidelity level, metric definition, noise, determinism, coverage, and uncertainty. | Separates raw feedback from decision-grade evidence. |
| Sample budget | Number of possible runs at each fidelity, including failed runs and invalid candidates. | Forces sample-efficient methods and preserves negative traces. |
| Reversibility | Whether the action can be undone cheaply, re-run, patched, or rolled back. | Connects autonomy to risk. Reversible actions can tolerate weaker evidence than irreversible commitments. |
| Commitment and rejection | Claim level supported, gate triggered, escalation required, and decision owner. | Keeps feedback comparable across claims by tying each source to what it can reject or commit. |
| Scarce attention | Expert review, debugging effort, validation bandwidth, security review, and integration time. | Prevents the loop from outsourcing cost to people whose time is the real bottleneck. |

: Feedback budgets make learning economics explicit: The ledger records what feedback is available, what it costs, what evidence it can support, and when scarce human attention or irreversible action should limit automation. {#tbl-feedback-budget-ledger tbl-colwidths="[22,34,32]"}

Beyond just tracking costs, the ledger also changes what a result means. A method that finds a good point
after 10,000 cheap proxy evaluations has learned something different from a
method that selects three candidates for expensive synthesis. A loop that
records failures, timeouts, warnings, rejected candidates, and review notes
has more evidence than a loop that records only the winning score. This is
the connection to sample efficiency from @sec-methods-generation-prediction-optimization: sample efficiency is not
only about using fewer evaluations. It is about making each evaluation carry
more architectural information.

To make that discipline concrete, we can write the feedback
budget and sample value explicitly:

$$
B = \sum_i n_i \cdot c_i,
\qquad
V_i \approx \frac{\Delta \mathrm{Conf}(d \mid e_i)}{c_i}.
$$

This notation is a review prompt, not a universal evidence metric. Here, $n_i$
is the number of evaluations of feedback type $i$, $c_i$ is
the cost of one such evaluation, $B$ is the total feedback budget, $e_i$
is the evidence produced by that evaluation, $\Delta \mathrm{Conf}(d
\mid e_i)$ is the change in confidence for the decision $d$, and $V_i$ is the
resulting decision value of one such evaluation. It is the per-feedback-type
form of the sample-value rule from
@sec-methods-generation-prediction-optimization; ordinal confidence changes or
decision-relevance labels are often more honest than unjustified numeric
confidence. The notation is a question the loop designer must answer before
each stage: will another simulation, synthesis run, expert review, or
deployment experiment change a decision enough to justify its cost? @sec-running-the-loop
makes the question concrete, spending the proxy budget freely, the cycle-level
budget carefully, and a high-fidelity power check only on the surviving
candidate.
The unit being priced is not just another evaluation; it is a rejectable loop
transition: state before, legal action, feedback source, rejection gate, and next
state if the gate fails.

## Fidelity Ladders and Evidence Ledgers

Feedback becomes evidence only when it is tied to fidelity, provenance,
uncertainty, and a decision. A simulator result is feedback. It becomes
evidence when the workload, simulator version, configuration, random seed,
assumptions, metric definition, failure status, and acceptance criterion are
recorded. A synthesis report is feedback. It becomes evidence when the
technology assumptions, constraints, tool versions, warnings, and comparison
baseline are explicit.

> **Feedback regime.** A feedback regime is a class of checks at a particular
> fidelity, cost, and commitment level, from cheap proxies to high-commitment
> verification, deployment, or silicon evidence.

To structure this transition from feedback to evidence, each rung of the fidelity ladder from
@sec-methods-generation-prediction-optimization is a feedback regime: the
ladder names the ordered levels a loop can climb, and the regime names the
class of checks at one level. The evidence ledger records which rung produced
which entry.

This idea of tracking evidence across regimes is not new to engineering. Safety-critical fields formalize it as an
**assurance case**: a structured argument that links a top-level claim to
sub-claims, assumptions, and supporting evidence, often written in Goal
Structuring Notation[^fn-goal-structuring-notation-c07] so that each inference and the evidence under it are
explicit and reviewable [@Kelly2004GSN]. An Architecture 2.0 evidence ledger is
an assurance case for a design decision that moves across feedback regimes: it
states what is claimed, at what fidelity, on what evidence, and what could reject
it. Naming the lineage helps, because that field already catalogs how such
arguments fail: unstated
assumptions, evidence that does not support the claimed scope, and confidence
that outruns the proof.

For Architecture 2.0, @fig-evidence-chain-rejection-gates shows the working model. A
claim should move through a chain of increasingly costly feedback sources,
with a rejection gate and evidence ledger entry at each stage.

![Evidence ledgers turn feedback into trust: A claim becomes more credible only as it moves through staged feedback sources, records provenance and uncertainty, and gives each stage authority to reject, revise, or escalate the result before the commitment boundary rises.](images/F9-evidence-chain-rejection-gates){#fig-evidence-chain-rejection-gates width="100%" fig-alt="Staged evidence ledger diagram showing feedback sources, provenance, uncertainty, rejection gates, revision, escalation, and rising commitment boundaries."}

Crucially, the figure changes the meaning of trust. Trust is not a model property or a
single score. It is a staged loop property: a claim becomes more credible only
when each feedback regime records what it saw, what it cannot support, what
would reject it, and what commitment boundary it is allowed to cross.

However, moving up the fidelity ladder is not a simple ranking from false to true. Higher fidelity is not
automatically truth if the wrong workload, objective, constraints, or baseline
were used. A detailed physical-design result can still answer the wrong
architecture question. A deployment signal can still be confounded by a
software change. A benchmark can still be too narrow. The purpose of the
feedback-regime view is therefore not to worship expensive tools. It is to make
the path from weak feedback to stronger evidence explicit.

Returning to the lighthouse prompt, low-fidelity feedback may be useful for eliminating
obviously infeasible vector widths, memory sizes, or accelerator partitions.
Simulation may then test workload behavior and data movement. Synthesis or
emulation may expose timing, area, or power problems. Deployment-like traces
or silicon evidence may reveal workload drift or integration effects. At each
stage, the loop should ask whether the earlier conclusion survived, changed,
or should be rejected.

This framing is consistent with the quantitative tradition in computer
architecture, where measurement, abstraction, and careful comparison are
central [@HennessyPatterson2017QuantitativeApproach]. Architecture 2.0
adds a loop-level requirement: the evidence ledger itself must be represented
so that a compound method system and a human reviewer can inspect it.

## Commitment Levels and Reversibility

An evidence ledger shows how strong the support for a claim is; how strong that
support needs to be is a separate question, and trust requirements should rise
with commitment. A loop that generates a
candidate simulator configuration can tolerate more automation than a loop
that changes RTL, partitions a chiplet boundary, selects a package interface,
or recommends a deployment policy. The difference is not whether AI is
involved. The difference is rollback cost, blast radius (how far a wrong change
can propagate), and who bears the
consequence when the loop is wrong.

@tbl-commitment-ladder gives a commitment-level view. The exact
ordering will vary across organizations, but the pattern is stable.
Reversible exploration can use lighter evidence, while irreversible or
high-blast-radius decisions require stronger evidence, independent rejection,
and human ownership. The trigger for moving between these levels is the
escalation threshold.

> **Escalation threshold.** An escalation threshold is the stated condition
> under which a loop must stop relying on its current feedback source and move
> to stronger evidence, independent review, or explicit human approval.

The architect owns these thresholds because they depend on consequences, not
only on model confidence. A proxy win may be enough to keep exploring. It is
not enough to change a subsystem interface, waive a verification concern, or
commit to a power claim. The loop should therefore state in advance which
events force escalation: uncertainty outside the calibrated range, a benchmark
coverage gap, a failed tool check, a security boundary, a high rollback cost,
or a decision that would affect another team or product.

::: {.callout-architect-checkpoint title="The Escalation Threshold Check"}
Who owns the escalation threshold when a generator's confidence outruns its evidence? The architect must define the exact conditions, such as a proxy win outside calibrated ranges, a security boundary, or a high-blast-radius commitment, that force an AI loop to stop relying on a generator and seek stronger evidence or human review.
:::

| Commitment | Example actions | Required discipline | Automation stance |
| --- | --- | --- | --- |
| Exploratory | Generate hypotheses, configs, candidate questions, or design cards. | Basic validity checks and provenance. | Broad assistance acceptable. |
| Experimental | Run simulator sweeps, tune compiler flags, select candidates for deeper study. | Workload versions, seeds, baseline, rejected candidates, and uncertainty. | Automation with review. |
| Implementation | Change RTL, generators, tool constraints, tests, or runtime interfaces. | Tool checks, regression tests, synthesis or integration evidence. | Bounded automation plus rejection gates. |
| Integration | Change subsystem interfaces, chiplet boundaries, memory contracts, or product-facing policies. | Cross-tool checks, compatibility, security, and explicit escalation. | Advisory or human-approved. |
| Irreversible | Mask-level choices, committed signoff decisions, fleet-wide rollouts, or customer-visible deployments. | Independent evidence ledger, rejection authority, audit trail, and accountable human decision. | Commitment boundary dominates. |

: Commitment level should govern autonomy: Reversible exploration can tolerate lighter evidence, while interface changes, product policies, signoff decisions, and deployments require stronger evidence, independent rejection, and explicit human ownership. {#tbl-commitment-ladder tbl-colwidths="[20,28,24,18]"}

This commitment structure keeps Architecture 2.0 from making a naive autonomy argument.
Autonomy is not a virtue by itself. A loop may be highly automated for
low-commitment exploration and deliberately conservative for high-commitment
decisions. In fact, some of the most valuable near-term systems may not be
systems that make final design choices. They may be systems that narrow a
space, identify contradictions, preserve evidence, and prepare the human
architect to make a better decision.

::: {#pri-escalate-commitment .callout-design-principle title="Escalate with commitment"}
In an AI-assisted loop, evidence requirements should rise with rollback cost, blast radius, and the
independence of the rejection authority. The cheaper a decision is to undo, the
more autonomy an automated optimizer can have; the harder it is to undo, the stronger and more
independent the check must be to overrule the generator's confidence.
:::

## Rejection Authority

If commitment levels determine the cost of being wrong, rejection authority is
how the loop prevents those errors from propagating. A credible loop needs
something with authority to say no. The rejecting
authority might be a type checker, parser, simulator, formal tool, regression
test, synthesis flow, cross-tool comparison, signoff rule, deployment signal,
security policy, benchmark governance rule, or expert reviewer. What matters
is that rejection is part of the loop interface, not an afterthought.

Beyond preventing errors, rejection authority is also the lever that controls loop speed. A loop speeds
up only as cheap, independent rejectors discharge a larger fraction of
commitments before expensive escalation. Generation does not help if it only
adds candidates that no trusted check can reject. Rejection authority is
therefore not a safeguard bolted onto a loop that already works. It is the
resource that sets how fast the loop can run.

::: {.callout-architect-checkpoint title="The Rejection Authority Check"}
When a generative model or optimizer proposes a "winning" candidate, does the loop name at least one independent authority that can say no? Trusting an AI-assisted loop requires proving the generator cannot grade its own work. The loop must expose a simulator, constraint checker, or formal tool with the authority to reject a candidate before treating it as an architectural commitment.
:::

To function effectively, this rejection authority has three parts. First, the loop must know which check is
being applied. Second, the loop must know what happens after rejection. Third,
the loop must record the rejection as evidence. A simulator crash, failed
build, invalid constraint, timing miss, benchmark violation, or expert
objection is not merely an inconvenience. It is information about the boundary
of the design space.

We can write this commitment review compactly as:
$$
\mathrm{Commit}_k(x) =
\begin{cases}
1, & \mathrm{valid}(x) \land E_k(x) \ge \tau_k \land
\rho_k(x) \le \rho_{\max,k}, \\
0, & \text{otherwise}.
\end{cases}
$$
This is not an algorithm that makes the decision for the architect. It is a
discipline for refusing unsupported commitment. Here, $x$ is the candidate,
$k$ is the commitment level, $\mathrm{valid}(x)$ is legality alone (the
candidate breaks no declared contract), $E_k(x)$ is the
sufficiency of the evidence at that level, $\tau_k$ is the evidence threshold,
$\rho_k(x)$ is the residual risk, and $\rho_{\max,k}$ is the risk the
architect or organization is willing to tolerate. Evidence and risk are written
as scalars only for compactness; in practice each is the per-gate checklist the
commitment ladder names. The thresholds are policy
and judgment choices, not magic constants learned by the method. If validity,
evidence, or residual risk fails, the loop should reject, revise, or escalate
instead of silently turning output into commitment. @sec-running-the-loop runs this rule on
the lighthouse prompt and shows how a candidate can fail on validity, evidence,
or residual risk even when another metric looks promising.

The commitment ladder (@tbl-commitment-ladder) turns $\tau_k$ from a symbol into
a rule the loop can enforce. Read each level's required discipline as its
acceptance condition, and make the failure explicit: when a required item is
missing, the loop does not commit at that level. It either downgrades the
claim to the highest level whose evidence is actually present, escalates to
the feedback the missing item names, or rejects the candidate. An exploratory
claim missing a baseline stays exploratory; an implementation claim missing
synthesis evidence or an independent rejector drops back to experimental until
that evidence exists; an irreversible claim missing an accountable human decision
is not made. That is the whole point of writing $\tau_k$ down per level: a missing cell forces rejection or escalation, never silent commitment. And when a claim is
meant to be comparable across teams rather than only reviewable, these
thresholds cannot stay local judgment calls; a shared benchmark protocol has to
fix them, or the claim is contrastable but not comparable.

::: {.callout-lighthouse title="Validity is a contract, not a score"}
Context. The commitment rule above does not ask whether an AI-generated candidate sounds
promising. It asks whether the candidate is legal for the commitment level the
generative method is about to claim.

In the Lighthouse prompt. A generative method's candidate for the "64-bit RISC-V-based compute
subsystem" is valid only if it stays inside the declared ISA/software contract,
can plausibly serve the "XRBench-class real-time mobile XR workload," and has
not crossed the "3\ W TDP target" or hidden an invalid memory or SoC-interface
assumption at the evidence level being used.

Rejection gate. ISA compatibility, workload validity, memory/interface
legality, power, deadline, and evidence fidelity are gates, not advisory
metrics for the generator to optimize.

Takeaway. If any gate is unsupported, the loop should force the generative method to reject, revise, or
escalate rather than turn a plausible subsystem into a commitment.
:::

Once a check fails, the response to rejection should be explicit. A candidate may be discarded. A
representation may need a new field. An environment may need a validity check.
A method may need a smaller action space. A workload may need a better
coverage definition. A claim may need to be weakened. A human architect may
need to escalate the decision. Without this response path, rejection becomes a
log message rather than a learning signal.

This rejection authority also protects against polished but unsupported outputs.
Tool-using agents can generate convincing summaries, plots, design reports,
and review notes. Those artifacts are useful only if the loop can still reject
them. In architecture, a beautiful explanation cannot overrule a failed
timing check, an invalid workload, a missing baseline, or a security boundary.
A deployed version of this independence appears at fleet scale in
@sec-loop-patterns-across-stack: during an instruction-set migration, build,
test, sanitizers, and a production monitor evict regressions automatically,
regardless of how confident the automated repair tool was.

The independence requirement grows sharper as verification itself becomes
AI-assisted. Machine-learning-assisted verification tools, such as Cadence
Verisium for triaging failures, ranking likely root causes, and directing
coverage, can be valuable [@Cadence2022Verisium]. But they move part of the
rejection authority into a learned system, which forces a recursive version of
this chapter's question: is the authority that can reject a design independent
of the system that produced it, or has the loop quietly made the generator and
its judge the same model? AI-assisted verification can share failure modes with
generation, so a rejection authority that shares the generator's
blind spots is not an independent gate. It is a second opinion from the same
witness.

The same rule applies when rejection is split across components. A generator,
critic, verifier, and summarizer may be separate components in an implementation,
but they do not become independent merely by having different prompts or names.
Independence depends on what they share: training data, model family, objective,
tool path, evidence source, or human instruction. A loop that asks several
correlated components to agree has created consensus, not rejection authority,
unless some gate can fail in a way the generator cannot simply explain away.

## Proxy Mismatch, Metric Gaming, and Calibration

The failure an independent rejection authority most often has to catch is proxy mismatch. A loop optimizes the measurement
it can see, while the architect cares about a broader objective. IPC may
improve while energy, area, or tail latency worsens. A simulator metric may
improve while synthesis exposes timing or power problems. A benchmark result
may improve while the real workload distribution changes. A Pareto frontier
may look convincing because all points were evaluated under the same flawed
proxy. An automated optimizer may appear capable because it overfits the evaluation loop,
not because it understands the architecture problem.

Two distinct failure modes hide within this proxy mismatch, and they need different cures. A proxy can simply be
miscalibrated or too narrow, mis-estimating the objective even when nothing is
pushing on it; a better-fitted or wider-coverage proxy helps. Or a method can
actively exploit the proxy's blind spots, driving toward exactly what it fails to
penalize; here a better proxy is not enough, and only an independent rejection
authority can catch the win.

This is not a new problem created by AI. Benchmarks, simulators, cost models,
and design rules have always been approximations. What changes in Architecture
2.0 is the speed and persistence with which a method can exploit the
approximation. A human may notice that a score is improving for the wrong
reason. A search method may happily continue. A compound system may even
produce a persuasive narrative for a proxy win unless the loop asks for
calibration and counterevidence.

::: {.callout-failure-mode title="The AI-generated win that vanished at signoff"}
An AI-generated configuration leads the design-space study for weeks on a cycle-level model:
better IPC, lower modeled energy, a clean Pareto point. At synthesis the lead
evaporates, because the model never charged for the timing and congestion the
winning structure creates. The automated optimizer exploited a gap in the proxy. The cheap fix is a rule written
before the search starts: an AI-generated cycle-level win is a reason to escalate, never a
reason to commit.
:::

To prevent this vanishing win, calibration acts as an escalation contract: it defines where a generative method may
use a proxy to rank candidates, where it must escalate, and what stronger
evidence can reject a proxy win. Prediction models used in
architecture have long needed validation against held-out data[^fn-held-out-data-c07], higher-fidelity
measurements, or carefully designed experiments
[@LeeBrooks2006RegressionModeling; @IpekEtAl2006PredictiveDSE]. The same
principle applies to AI-assisted loops. If a loop claims a candidate satisfies the
3\ W lighthouse envelope, the evidence must show how the power estimate was
calibrated, what workload region it covers, what uncertainty remains, and what
higher-fidelity result could overturn the claim.

::: {.callout-architect-checkpoint title="The Calibration Gate Check"}
Does the loop know when a generator's proxy is no longer trustworthy? A proxy win is only evidence if the loop can prove the AI-generated candidate falls within the proxy's calibrated support region. If it falls outside, the loop must escalate to a higher-fidelity check rather than trusting the uncalibrated prediction.
:::

Beyond model calibration, benchmark governance also matters because benchmark rules are part of the
loop's evidence contract. If those rules are hidden or stale, automated optimizers can
optimize version quirks, protocol gaps, or unowned metrics while appearing to
make progress. As @sec-design-loop-no-longer-scales and
@sec-loop-patterns-across-stack show, a benchmark becomes community
infrastructure only when it defines rules, versions, and submission practices
that make results interpretable across a changing field. Architecture 2.0 needs
a similar instinct for design loops: define the evaluation contract, preserve
provenance, track versions, and treat benchmark changes as part of the evidence
story.

## Security, IP, and Confidentiality Boundaries

Calibration, provenance, and benchmark governance make a claim accurate, but a
claim whose evidence cannot be exposed cannot be fully believed. Confidentiality
is therefore part of the same machinery of graded belief and rejection as
fidelity and provenance, not a separate compliance concern: evidence that must
stay private still has to be auditable enough to grade the claim and to reject
it, otherwise a loop can hide an unsupportable result behind a claim of
confidentiality. Architecture state is
often sensitive: RTL, design specifications, process assumptions, timing
constraints, floorplans, tool logs, customer workloads, proprietary traces,
compiler settings, design reviews, and deployment telemetry can all reveal
valuable or restricted information.

This need for auditable privacy has a direct technical consequence. Security boundaries are part of the
environment and evidence design. A loop must define what data can leave an
organization, what must remain local, what can be summarized, which artifacts
can be shared publicly, which logs should be redacted, and which generative methods or
tools can access each class of information. The trust question is not only
whether the method is accurate. It is whether the loop preserves the
constraints under which architecture work actually happens.
The failure mode is not only leakage; it is a generative method producing a claim from
evidence it cannot expose, audit, or legally reuse.

::: {.callout-architect-checkpoint title="The Confidentiality Boundary Check"}
Can the AI model's evidence be audited without violating security or IP boundaries? If a generative method produces a claim using confidential data that cannot be exposed to the rejection authority, the loop cannot trust the claim. The architect must explicitly define which AI tools can access which data classes, and how private evidence can be verified.
:::

For shared community infrastructure, this means the field should distinguish between
public artifacts and private state. Public benchmarks, datasets, papers, and
gym environments can help bootstrap shared progress. Private workloads,
proprietary RTL, product traces, and process-specific assumptions often cannot
be released. Architecture 2.0 should support both. The design-loop card,
environment contract, and evidence checklist should let a project describe
what kind of evidence exists without forcing disclosure of sensitive material.
That record should include a data-access and evidence-scope field: what private
state was used, what public proxy cannot support, which generative methods or tools may
access each artifact, and who owns disclosure exceptions.

The practical rule for AI-assisted systems is therefore simple. Do not make confidentiality invisible. If a
claim depends on private data, say what class of data supports it, what
auditing is possible, what cannot be disclosed, and what public proxy would be
insufficient. That is more honest than pretending every architecture loop can
be reproduced from public web data.

## Evidence Disputes and the Trust Checklist

Once accuracy and confidentiality are both handled, trust still has to survive
disagreement, and evidence disputes are inevitable. One group may claim that a learning-based
method improves a design flow. Another may argue that the baseline, workload,
constraint set, tool version, or evaluation protocol was incomplete. A company
may have private evidence that cannot be released. A paper may report a strong
result but omit negative traces. A benchmark may reward behavior that matters
less in deployment. These disputes should not be treated as distractions from
Architecture 2.0. They are part of the field learning how to assign trust.

While the specifics vary, the anatomy of an evidence dispute is stable:

> claim; proxy; fidelity level; assumptions; workload coverage; provenance;
> counterevidence; rejection authority; and final human decision.

@fig-evidence-dispute-anatomy makes that anatomy visible. A dispute is not
resolved by confidence; it is resolved by exposing which part of the evidence
packet can support, weaken, reject, or escalate the claim.

![Evidence disputes become tractable when the review axes are explicit: A contested architecture claim should expose its feedback, fidelity, provenance, baselines, counterevidence, rejection authority, and human decision path before it asks readers to trust the result.](images/F9b-evidence-dispute-anatomy){#fig-evidence-dispute-anatomy width="100%" fig-alt="Flow diagram showing a contested claim feeding an evidence packet with feedback, fidelity, provenance, counterevidence, and rejection authority, then ending in accept, reject, or escalate decisions."}

In recent years, learned chip placement has become the field's most public worked example of this
anatomy. A 2021 result reported that a reinforcement-learning method produced
floorplans competitive with human experts in far less time
[@MirhoseiniEtAl2021GraphPlacement]. Independent groups then disputed the claim
on exactly the axes above: the baselines, the released code, and the
reproducibility of the protocol [@ChengEtAl2023AssessmentRL]. The point here is
not to adjudicate that dispute. The point is that the disagreement was never
about whether the model ran; it was about provenance, baselines, and what
evidence could reject the result. One constructive response
has been to build reproducible, end-to-end benchmarks that score placement by
final power, performance, and area rather than an intermediate proxy
[@WangEtAl2025ChiPBench]. That is the anatomy doing its work: a contested claim
becomes tractable once the loop's evidence, baselines, and rejection authority are
made explicit.
For Architecture 2.0, the reusable lesson is not the controversy itself; it is
that a loop claiming placement quality must expose represented floorplan state,
legal move/action space, workload and PPA records, baseline receipts, rejected
alternatives, and the independent authority that can block commitment.

To make this dispute anatomy practical, @tbl-trust-checklist turns it into a checklist. It is
intended for reading papers, reviewing internal tools, evaluating student
projects, and deciding whether an AI-assisted loop is ready for a more
expensive commitment.

| Question | What a credible answer contains | Warning sign |
| --- | --- | --- |
| What output is being trusted? | Candidate, ranking, report, code/RTL change, or commitment recommendation, with generator and method role named. | The result is described only as an AI improvement. |
| What is the claim? | A bounded architecture task, objective, workload, and commitment level. | Vague claims of automation or improvement. |
| What loop state and action contract are exposed? | State fields, legal actions, tool or environment APIs, invalid transitions, and replay receipts. | The loop can act through hidden state or unlogged tool semantics. |
| What feedback supports it? | Metrics, tool outputs, logs, reviews, and negative traces tied to a feedback budget. | Only the winning score is shown. |
| What is the fidelity? | Proxy, simulation, synthesis, emulation, signoff, deployment, or silicon level stated explicitly. | Treating all measurements as equivalent. |
| What is the provenance? | Workload versions, tool versions, configs, seeds, constraints, assumptions, and baselines. | Hidden scripts or unstated defaults. |
| What is the security or confidentiality boundary? | Data classes, access rules, redaction limits, public proxy limits, and an audit path. | Private evidence is treated as invisible or unverifiable. |
| What can reject it? | Tests, formal checks, simulators, signoff rules, deployment signals, or expert review. | No independent authority can say no. |
| Who commits? | A named human or process accepts, rejects, escalates, or revises the artifact. | The loop silently turns output into decision. |

: Trust is a checklist, not a tone judgment: A credible Architecture 2.0 claim states its task, feedback, fidelity, provenance, confidentiality boundary, rejection authority, and commitment boundary before it asks the reader to believe the result. {#tbl-trust-checklist tbl-colwidths="[24,38,26]"}

This checklist gives the book one of its practical tests. A paper, tool, or
project does not need to solve the whole lighthouse prompt to be valuable. It
does need to say where it sits in the loop, what evidence it produces, what it
cannot prove, and what can reject it. That is how Architecture 2.0 can remain
ambitious without becoming credulous.

The next chapter puts this discipline to work. It runs one loop end to end on
the lighthouse prompt: generating candidates, escalating from proxy to
simulation-stage evidence, rejecting on the power envelope, and stopping at an
honest commitment level. The chapter after that generalizes the single loop into
the patterns that recur across the stack, where the same ontology applies but
the task, representation, environment, method role, feedback budget, evidence
burden, and commitment level all change.

## Open research questions

The mechanisms of trust and verification presented in this chapter establish a foundation, but turning them into robust, automated systems exposes several unsettled research directions.

1. How do we enforce evidence ledgers across disjoint tools?
   Building on the "Fidelity Ladders and Evidence Ledgers" and "Commitment Levels and Reversibility" sections, tracking provenance continuously across proprietary synthesis tools, fragmented simulators, and manual reviews remains unsolved. Research must design invariants that can reliably bind disparate multi-fidelity traces into a unified claim that guarantees a loop cannot exceed its authorized commitment level.
2. How can loops autonomously detect proxy exploitation?
   The "Proxy Mismatch, Metric Gaming, and Calibration" section relies on escalation when a proxy is gamed, yet identifying when a generated candidate drifts outside a simulator's calibrated support region is largely a manual process. Future work must define algorithms that allow a loop to dynamically estimate its own calibration boundaries and automatically trigger the escalation threshold.
3. How do we quantify reviewer independence in multi-agent systems?
   As emphasized in the "Rejection Authority" section, an AI verifier that shares training data, objectives, or failure modes with a generator provides consensus, not an independent check. We need new audit protocols that can mathematically or empirically measure the correlation between AI-assisted rejectors and generators to ensure a rejector is truly qualified to say no.
4. How do we stress-test the trust machinery itself?
   While the "Evidence Disputes and the Trust Checklist" section shows how to review a single claim, evaluating the robustness of the overarching feedback loop requires new experimental designs. Researchers must construct adversarial environments—injecting hidden workload shifts, flawed baselines, and deceptive proxies—to rigorously measure false commitment rates, escalation costs, and the true efficacy of human veto authority.

## What to carry forward
- Reader test: What evidence would overturn the AI model's result, and who or what has
  authority to reject it?
- Next loop state: Once trust can be evaluated for an AI-assisted claim, the next step
  is to run a complete loop and inspect the residue it leaves behind.

[^fn-tool-using-agent-c07]: **Tool-using agent**: an AI system that can programmatically invoke external software tools or APIs to solve tasks.
[^fn-policy-c07]: **Policy**: in reinforcement learning, a function that maps an agent's state to a chosen action.
[^fn-critic-c07]: **Critic**: in this book, the critique method role of @sec-methods-generation-prediction-optimization, a component that challenges assumptions, evidence, or claims inside the loop; reinforcement learning uses the same word more narrowly for a learned estimator of expected future returns.
[^fn-goal-structuring-notation-c07]: **Goal Structuring Notation (GSN)**: a graphical argumentation notation used in safety-critical engineering to formally document the elements of an assurance case.
[^fn-held-out-data-c07]: **Held-out data**: a subset of a dataset reserved during model training, used exclusively to test the model's ability to generalize to unseen inputs.
# Running the Lighthouse Loop {#sec-running-the-loop}

```{=latex}
\abstract*{The previous chapters built the parts of an Architecture 2.0 loop: representation, environment, method roles, feedback budgets, evidence ledgers, and rejection authority. This chapter runs one AI-assisted architecture loop, end to end, on the lighthouse prompt. The point is not the specific numbers, which are illustrative; it is to watch a loop instantiate candidates, predict, escalate, reject, and stop at an honest commitment boundary.}
```

::: {.callout-crux}
How does an AI-assisted loop convert the lighthouse prompt into one bounded,
rejectable turn rather than a one-shot design answer?
:::

The previous chapters have described what a credible loop must contain. They
have not yet shown one turn. This chapter does that. It takes the lighthouse
prompt, bounds it to a task small enough to run, and walks the loop through
candidate instantiation, prediction, escalation, rejection, and commitment.
Every number here is illustrative and generated in code, not measured; the
lesson is the shape of the loop, not the values. The numbers are constructed to
be inspectable, not XRBench measurements, gem5 results, or synthesis estimates;
replace them with local source receipts before using this pattern for an
empirical claim. The
demonstration that this shape holds on real, deployed hardware comes in
@sec-loop-patterns-across-stack, where the same generate, screen, escalate,
reject, and commit sequence runs on a production fleet migration with measured
results. Here the goal is to make the shape itself legible.

Bounding the task comes first. "Design a low-power XR compute subsystem" is not
a loop; it is a wish. This chapter narrows the task to one XRBench-class[^fn-xrbench-class-c08]
workload slice. The loop chooses among three compute organizations under a 3\ W
power envelope and an 8\ ms per-frame deadline, the frame budget the slice
fixes for its real-time display pipeline, then returns the
surviving candidate with its evidence and its rejected alternatives. The
candidates are a vector CPU extension, an accelerator deliberately left loosely
coupled as a stress case, and a shared-memory SoC block. The loose accelerator is not the only
accelerator realization allowed by the prompt; it is included so interface and
data-movement costs have somewhere to show up. That is enough to make the loop
turn.
The worked example is therefore not a DSE recipe; it is a trace of what an
AI-assisted architecture loop may propose, what feedback it may trust, and what
residue it must leave for a human owner.

To ground this trace, @tbl-active-lighthouse-slice states the active slice of the lighthouse prompt.
Everything outside the slice is not ignored; it is explicitly deferred to the
next evidence stage.

| Loop field | Active slice in this chapter |
| --- | --- |
| Workload | One XRBench-class mobile-XR slice with a real-time frame deadline; a real loop would also record workload ID, input schema, scenario labels, coverage limits, distribution assumptions, provenance, and validity checks. |
| Baseline | A bounded comparison among three compute organizations, not a full product baseline. |
| ISA/software assumption | All candidates remain within a 64-bit RISC-V-compatible software path; compiler/runtime feasibility is deferred. |
| Design space | Vector CPU extension, deliberately loose accelerator stress case, or shared-memory SoC block; no cache, chiplet, voltage, compiler-policy search, or full tightly coupled accelerator search yet. |
| Legal actions | Instantiate the three candidate organization records with prompt, generator/search version, candidate IDs, invalid-action records, and selection rule; run the proxy screen, escalate all candidates to the simulation-stage estimate because the proxy has no final rejection authority, reject only on declared deadline/power gates, and advance a survivor only to RTL-level study; changing workload scope or claiming implementation readiness is outside this turn. |
| Physical envelope | 3\ W power envelope and 8\ ms per-frame deadline; process and thermal assumptions are placeholders for the next stage. |
| Excluded evidence | No RTL, timing, area, thermal, physical-design, deployment, silicon, or carbon-footprint evidence. |

: A worked loop starts by declaring its slice: The chapter exercises one small loop turn from the lighthouse prompt, while recording which obligations remain outside the current evidence boundary. {#tbl-active-lighthouse-slice tbl-colwidths="[24,66]"}

::: {.callout-learning-objectives}
After this chapter you can turn a broad prompt into one bounded, rejectable AI-assisted loop
turn and read the receipt it leaves. That means you can:

- instantiate and run an AI design-loop card on a concrete prompt, not merely fill it in;
- recognize proxy mismatch when the loop's cheapest winner fails at higher fidelity;
- apply the commitment rule to stop the AI loop at an honest evidence level;
- read the residue an AI-assisted loop leaves: evidence ledger, negative traces, and the next evidence the human decision needs.
:::

## Round One: Generate and Screen on a Proxy

The four rounds that follow are not four turns. They are the four beats of one
turn: generate and screen, escalate, reject, and commit.

![The AI-Assisted Architecture Loop: The four beats of a single design-loop turn. A generative method searches for candidates, a proxy screens them, stronger simulation tests the survivors against physical constraints, and the architect reviews the evidence to make a bounded commitment.](images/F8-loop-beat){#fig-loop-beat width="100%" fig-alt="Sequence diagram showing Generation/Search, Proxy Screen, Escalation to Simulation, Rejection, and Human Commitment."}

The loop begins cheaply. A generative model or search method proposes the
three organizations in a bounded candidate schema, and an **analytic proxy**, an
operation-count or datapath-only estimate that counts arithmetic but not the
traffic needed to feed it, estimates latency and energy per frame in
milliseconds and millijoules. The proxy is fast and ignores most data movement,
input-distribution variation, locality, runtime behavior, and coverage labels,
so it flatters designs that keep arithmetic local. At this fidelity the loosely
coupled accelerator looks best. It posts the lowest energy and latency because
the proxy never charges it for moving data in and out.

Instead of demonstrating a full generative search to find these three organizations, this illustrative turn simply seeds the candidate records directly. A real run would store the
prompt, generator version, candidate IDs, invalid candidates, and selection
rule as part of the receipt.

Regardless of how candidates are generated, a proxy result is low-fidelity feedback that becomes evidence only for the
narrow action of deciding what to escalate. It is not evidence for an
implementation commitment until stronger feedback confirms the gate. Proxy
deadline or power concerns are warnings until stronger feedback confirms them.
The AI-assisted loop records the proxy ranking and escalates.

::: {.callout-architect-checkpoint title="The Escalation Gate"}
The automation's role: Rank candidates using the cheap proxy to prioritize the search space.
The human architect's role: Verify that proxy results only guide escalation and are not trusted as implementation commitments.
:::

## Round Two: Escalate to a Simulation-Stage Estimate

To advance beyond the proxy's blind spots, an illustrative **simulation-stage estimate** is the first stage that charges memory
*traffic*. The exact tool is not the lesson. This stage is a stronger environment
contract: it prices *data movement*, returns latency, energy, and power
observations with provenance and cost, and has authority to overturn proxy
rankings before commitment. Its power column is the frame energy divided by the
frame time, an average-power check against the 3\ W envelope. (Note that average power itself is merely a higher-level proxy; a true rejection gate must eventually include thermal transients, as chips melt from peak power, not average power.) For highly regular spatial accelerators, analytical models like Timeloop are not just cheap proxies; they provide *authoritative* high-fidelity evidence for dataflow mapping, bridged to physical limits via component plugins like Accelergy. It stands in for this class of model: a dataflow analysis like
Timeloop [@ParasharEtAl2019Timeloop], a calibrated pre-RTL estimator like
Aladdin [@ShaoEtAl2014Aladdin], or a cycle-accurate simulator such as gem5
[@BinkertEtAl2011Gem5] or FPGA-accelerated FireSim [@KarandikarEtAl2018FireSim].
Furthermore, this simulation-stage estimate must model the compiler. A candidate is only valid if the compiler can actually target it efficiently; hardware search is meaningless if the software stack cannot discover the data paths.

It is
slower and scarcer than the proxy. In this toy turn all three candidates are
escalated because proxy feedback has no final rejection authority. The result
is the central lesson of the chapter: the candidate that wins the cheap screen
does not survive the stage that charges *data movement*. @tbl-worked-loop runs
the comparison.

```{python}
#| output: asis
#| echo: false

candidates = [
    {"name": "Vector CPU extension",        "proxy_lat": 7.6, "proxy_e": 22, "sim_lat": 9.5, "sim_e": 24},
    {"name": "Loosely coupled accelerator", "proxy_lat": 4.5, "proxy_e": 12, "sim_lat": 8.8, "sim_e": 28},
    {"name": "Shared-memory SoC block",     "proxy_lat": 6.0, "proxy_e": 16, "sim_lat": 6.5, "sim_e": 18},
]
for c in candidates:
    # average power over the frame: energy (mJ) / time (ms) = W
    c["power"] = c["sim_e"] / c["sim_lat"]
deadline_ms = 8.0
power_budget_w = 3.0


def verdict(c):
    failures = []
    if c["sim_lat"] > deadline_ms:
        failures.append("misses 8 ms deadline")
    if c["power"] > power_budget_w:
        failures.append("over 3 W envelope")
    if failures:
        return "rejected: " + "; ".join(failures)
    return "survives to RTL study"


proxy_pick = min(candidates, key=lambda c: c["proxy_e"])["name"]
survivors = [c for c in candidates if verdict(c).startswith("survives")]
survivor = min(survivors, key=lambda c: c["sim_e"])["name"] if survivors else "none"

lines = [
    "| Candidate | Proxy lat / energy | Sim lat / energy | Avg power | Verdict |",
    "|:--|:--|:--|:--|:--|",
]
for c in candidates:
    lines.append(
        f"| {c['name']} | {c['proxy_lat']:.1f} ms / {c['proxy_e']} mJ "
        f"| {c['sim_lat']:.1f} ms / {c['sim_e']} mJ | {c['power']:.1f} W | {verdict(c)} |"
    )
lines.append("")
lines.append(
    ": One loop turning on the lighthouse prompt: the lowest-energy candidate "
    f"at proxy fidelity is the {proxy_pick.lower()}, but an illustrative simulation-stage estimate and the "
    f"{deadline_ms:.0f} ms / {power_budget_w:.0f} W gates reject it, and the {survivor.lower()} is the only "
    f"candidate that clears both the {deadline_ms:.0f} ms deadline and the power "
    "envelope. Values are illustrative and computed in the chunk; average power is frame energy over frame time. {#tbl-worked-loop}"
)
print("\n".join(lines))
```

As the results show, the accelerator that won on the proxy collapses under the simulation-stage
estimate. Once data
movement is charged, its energy rises above every alternative and its latency
loses most of its lead. The shared-memory SoC block absorbs the same charge
with little damage because its traffic stays inside the on-chip hierarchy it
shares with the CPU, so the proxy's blind spot was never subsidizing it; the
vector extension, which also keeps data local, fails instead on raw throughput
against the deadline. This is **proxy mismatch** made concrete: the loop was
optimizing the *measurement* it could see, not the *objective* it cared about. The proxy optimizes arithmetic, but the true simulation-stage rejection gate prices communication. The
failed candidate is not deleted. It is recorded as a **negative trace**, with the
fidelity level at which the proxy win disappeared, so a later loop does not
rediscover it. @fig-proxy-mirage shows the reorder.

```{python}
#| label: fig-proxy-mirage
#| fig-cap: |
#|   The proxy ranking is a mirage: the candidate with the lowest proxy energy, the loosely coupled accelerator, becomes the worst once the simulation-stage estimate charges data movement, and the 8\ ms / 3\ W gates reject it. The shared-memory SoC block, second on the proxy, is the only organization that clears both the real-time deadline and the power envelope. The energy values are the same illustrative, computed numbers as @tbl-worked-loop.
#| out-width: "82%"
#| fig-alt: "Grouped comparison plot showing that proxy energy ranking reverses when an illustrative simulation-stage estimate and power constraints are applied."

import matplotlib.pyplot as plt
from _python.arch2_plots import COLORS, add_note_box, apply_style

apply_style()

line_colors = {
    "Vector CPU extension": COLORS["blue"],
    "Loosely coupled accelerator": COLORS["orange"],
    "Shared-memory SoC block": COLORS["green"],
}

fig, ax = plt.subplots(figsize=(4.8, 2.95))
fig.subplots_adjust(left=0.13, right=0.64, top=0.91, bottom=0.30)

for c in candidates:
    v = verdict(c)
    ax.plot(
        [0, 1], [c["proxy_e"], c["sim_e"]],
        marker="o", color=line_colors[c["name"]], linewidth=1.9,
        markersize=5, markerfacecolor="#F8FAFC", markeredgewidth=1.2,
        clip_on=False, label=c["name"],
    )
    misses = []
    if "deadline" in v:
        misses.append(f"{c['sim_lat']:.1f} ms")
    if "envelope" in v:
        misses.append(f"{c['power']:.1f} W")
    short = "rejected: " + " + ".join(misses) if misses else "survives"
    vcolor = COLORS["purple"] if short == "survives" else COLORS["red"]
    ax.text(1.03, c["sim_e"], short, ha="left", va="center", fontsize=6.4, fontweight="bold", color=vcolor)

ax.set_xlim(0, 1)
ax.set_ylim(8, 32)
ax.set_xticks([0, 1])
ax.set_xticklabels(["proxy estimate", "simulation-stage estimate"], fontsize=7)
ax.set_ylabel("energy per frame (mJ)", fontsize=7)
ax.tick_params(axis="y", labelsize=6.3)
for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)
ax.legend(loc="upper left", fontsize=5.9, frameon=False, handlelength=1.4)
add_note_box(
    fig,
    "Lowest proxy energy is not best end-to-end; interface and data movement reorder the ranking.",
    xywh=(0.11, 0.035, 0.78, 0.10),
    fontsize=5.6,
)

plt.show()
plt.close(fig)
```

To document this shift in ranking, @tbl-worked-loop-ledger shows the evidence ledger left behind. The exact schema of the candidate record depends on the environment, but it must be machine-readable (e.g., JSON or YAML) to allow autonomous auditing. For example, a YAML evidence ledger entry might look like this:
```yaml
candidate_id: xr_soc_v4_2
status: REJECTED
rejection_gate: proxy_mismatch_communication_power
proxy_estimates:
  compute_energy_mJ: 4.2
  latency_ms: 6.1
simulation_estimates:
  total_energy_mJ: 28.5  # Failed: excessive NOC traffic
```
Read the first
two rows as feedback stages and the third as the record those stages leave; the
columns are the ledger schema: the feedback source, its fidelity and budget,
what it supported, the gate it could reject on, its provenance limit, and the
next evidence required. The ledger is what makes the toy loop auditable rather
than merely ranked.

| Stage | Feedback source | Fidelity and budget | Support | Rejection gate | Provenance / limit | Next evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Proxy screen | Operation-count or datapath-only estimate. | Three cheap evaluations; ignores most data movement. | Ranks the accelerator first on proxy energy. | No final rejection; only warnings. | Illustrative constants in this chapter. | Escalate all candidates to stronger feedback. |
| Simulation-stage estimate | Illustrative memory-aware estimate plus simple power check. | Three scarce illustrative checks; still no RTL or physical feedback. | Shared-memory SoC block clears both gates. | 8\ ms deadline and 3\ W envelope. | Hard-coded values; not XRBench, gem5, synthesis, silicon data, workload trace IDs, scenario coverage labels, or input-distribution receipts. | RTL, timing, area, thermal, and compiler/runtime checks. |
| Negative traces | Recorded failed alternatives. | Two rejected candidates. | Failure reasons are preserved. | 8\ ms deadline and 3\ W envelope; proxy mismatch is recorded as diagnostic context. | Candidate IDs and reasons only; no logs attached, and no evidence that another workload distribution would preserve the same rejection. | Prevent rediscovery and guide the next search. |

: The evidence ledger records stages, not only the winner: The reusable result is the sequence of feedback, support, rejection gates, limits, and next evidence. {#tbl-worked-loop-ledger tbl-colwidths="[13,16,17,14,13,14,13]"}

## Round Three: Reject on the Envelope

Beyond simply reordering candidates, the simulation-stage estimate also exposes harder gates. The loosely coupled
accelerator does not merely lose on energy; in this constructed diagnosis, its
symptoms point to one cause the next evidence stage would have to verify.
Reaching the accelerator means moving data across an *interface* to off-chip or
distant memory, and that *traffic* is expensive on every axis at once. In that diagnosis it
stalls the datapath, so the illustrative latency estimate misses the 8\ ms
deadline; it pays off-chip access energy, so per-frame energy climbs above every
alternative; and it keeps the memory subsystem busy rather than idle, so average
power crosses the 3\ W envelope. These are *constraints*, not just metrics, so no
local proxy advantage rescues it. The rejection is the **commitment rule** from the
trust chapter doing its work: a candidate advances only if it is valid, its
evidence clears the threshold for the stage, and its residual risk is
acceptable.

::: {.callout-architect-checkpoint title="The Rejection Gate"}
The automation's role: Test candidates against the simulation-stage constraints (e.g., 8 ms deadline, 3 W power envelope) and reject those that fail.
The human architect's role: Ensure the automation's rejection criteria match the physical and product constraints, and accept the negative traces produced.
:::

::: {.callout-lighthouse title="Price the interface before believing the proposed accelerator"}
Context. This worked AI-assisted loop deliberately includes a loosely coupled
accelerator as a stressed integration variant, even though the full prompt also
allows a tighter accelerator path.

In the Lighthouse prompt. The "64-bit RISC-V-based" software path, the
"XRBench-class real-time mobile XR workload" slice, the 8\ ms frame deadline
the slice fixes,
and the "3\ W TDP target" are fixed. The AI loop varies the "vector-capable CPU,
accelerator, or SoC block" choice and its interface cost.

Deferred evidence. Compiler and runtime, RTL, thermal, physical-design, and
verification and reliability evidence are deferred to the next stage.

Takeaway. In the Lighthouse loop, a proposed accelerator is not a faster box attached
to the side; it is an interface, memory-system, software-path, and power claim.
Once *data movement* across that *interface* misses the deadline and crosses the
envelope, the local *arithmetic* win the automation found no longer matters.
:::

## Round Four: Commit at an Honest Level

With the rejection gates applied, one candidate survives the deadline and the envelope. It is tempting to call
that a result. It is not, yet. The evidence behind it is a simulation-stage
estimate standing in for cycle-level and power feedback, which supports an
experimental commitment, not an implementation or a tapeout. The architect's
decision is therefore bounded: advance the surviving organization to an RTL
study where synthesis, timing, and a stronger power estimate can confirm or
reject it, and hold the other two as recorded negative traces.

Stopping at this honest boundary is the difference between an answer and a defensible AI-assisted loop turn. The result
is a **replay receipt**: the surviving state, the evidence that supports it, the
actions and alternatives rejected, the commitment boundary, and the next
evidence a human owner requires.

::: {.callout-architect-checkpoint title="The Commitment Gate"}
The automation's role: Provide the surviving candidate alongside a replay receipt, evidence ledger, and negative traces.
The human architect's role: Accept the evidence boundary and authorize advancing the surviving candidate to RTL study, or demand stronger evidence before committing.
:::

::: {#pri-honest-evidence .callout-design-principle title="Stop at an honest evidence level"}
An AI-assisted loop should report what its evidence supports, what it rejected, and what would
overturn the decision, then stop there. The honest commitment level, not the
most optimistic one a generative model might claim, is the result.
:::

To capture this commitment, @tbl-worked-loop-card records that residue as a filled design-loop card. The
entries are intentionally terse. A real project would attach logs, scripts,
trace identifiers, and power-model receipts, but the first test is whether the
loop can state what it did and what would reject it.

| Card field | Lighthouse loop entry |
| --- | --- |
| Intent | Explore a low-power mobile-XR compute organization that can meet a real-time deadline under a 3\ W envelope. |
| Task | Compare three bounded compute organizations for one XRBench-class workload slice. |
| Design space | Choose among vector CPU extension, deliberately loose accelerator stress case, and shared-memory SoC block; leave cache, voltage, chiplet, compiler-policy, full tightly coupled accelerator search, and RTL edits outside this turn. |
| Representation | Candidate ID, candidate record, legal action taken, workload slice ID/coverage label, proxy and simulation observations, uncertainty/provenance limits, deadline, power envelope, and verdict. |
| Environment | Analytic proxy followed by an illustrative simulation-stage estimate standing in for cycle-level feedback and a simple power-envelope check. |
| Method role | Seed candidates, predict cheap proxy scores, escalate all candidates because the proxy has no final rejection authority, and critique proxy wins against stronger feedback. |
| Feedback budget | Three cheap proxy evaluations and three illustrative simulation/power checks; no RTL, timing, thermal, or silicon evidence yet. |
| Evidence | The shared-memory SoC block is the only candidate that clears the 8\ ms deadline and 3\ W envelope in the illustrative run. |
| Negative traces | The vector CPU extension misses the latency deadline; the loosely coupled accelerator misses the latency deadline and exceeds the power envelope after the illustrative estimate exposes data movement. |
| Rejection authority | Deadline check, power-envelope check, ML compiler mapping (e.g., XLA/MLIR), and the stronger estimate that can overturn the proxy ranking. |
| Commitment boundary / would overturn | Advance only to RTL-level study; implementation commitment would require synthesis, timing, area, thermal, compiler/runtime, and stronger power evidence. |
| Human decision | Advance the shared-memory SoC block to RTL-level study and keep the other two candidates as negative traces. |

: The worked loop leaves a filled card, not just a winning row: The card
records the bounded task, evidence ledger, negative traces, rejection authority,
and human decision that another architect would need before continuing the
loop. {#tbl-worked-loop-card tbl-colwidths="[22,66]"}

Alongside the summary card, a real version of the same loop should also leave a replay receipt. The receipt
does not have to expose proprietary data, but it should preserve enough
structure that a reviewer can tell what was run, what failed, and what would
need to be rerun. @tbl-loop-replay-receipt gives the minimum shape.

| Receipt item | Example contents for this loop |
| --- | --- |
| `README.md` | Task slice, claim boundary, non-goals, and human decision owner. |
| `inputs/` | Workload IDs, benchmark version, scenario metadata, input-distribution summary, coverage labels, trace provenance, workload-level rejection conditions, and redaction notes. |
| `prompts/` | Prompt slice, model/tool versions, role assignments if multiple models act, generator/search configuration, invalid proposals, selection rule, and human overrides or approvals. |
| `candidates/` | Candidate IDs, configuration records, invalid-action records, and rejected alternatives. |
| `runs/proxy/` | Proxy model version, constants, scripts, logs, and cheap-screen results. |
| `runs/sim/` | Simulator or stronger-feedback configuration, seeds, logs, metrics, warnings, and failures. |
| `evidence/` | Evidence ledger, fidelity labels, uncertainty, baseline, and sensitivity notes. |
| `decisions/` | Architect review note, escalation rule, commitment level, and next evidence required. |

: A loop result should leave a replay receipt: The useful artifact is not
only the winning candidate but the runnable or reviewable residue that explains
inputs, candidates, runs, evidence, failures, and decisions. {#tbl-loop-replay-receipt tbl-colwidths="[24,64]"}

@fig-loop-receipt-bundle shows the receipt as a bundle rather than a single
result row: the winner matters only because the surrounding artifacts explain
what supported it, what failed, and what decision remains open.

![A loop receipt is the reviewable residue of one turn: The reusable artifact is not the winning candidate alone, but the task boundary, inputs, candidate records, proxy and stronger runs, evidence ledger, and decision record that let another architect continue or reject the loop.](images/F9c-loop-receipt-bundle){#fig-loop-receipt-bundle width="100%" fig-alt="Directory-style diagram showing a loop receipt bundle with README, inputs, candidates, proxy runs, simulation runs, evidence, and decisions."}


## What the Loop Leaves Behind

Ultimately, the residue of one turn is the reusable artifact.

::: {.callout-evidence-packet title="What one AI-assisted loop turn leaves behind"}
The evidence packet for this turn is the filled design-loop card and replay
receipt above: it exposes the task boundary, evidence level, negative traces,
rejection authority, commitment boundary, and next evidence owner. Another
architect can read that residue and reconstruct why the surviving candidate
advanced, why the others did not, and what would overturn the decision.
:::

Producing this reviewable residue is the test the rest of the book has been building toward. The reader
should now be able to take a new project and do three things: name the loop,
judge whether its evidence matches its commitment level, and state what remains
a human decision. The next chapter generalizes this single worked loop into the
patterns that recur across the stack, from fast software loops to
high-commitment silicon-facing work.

When you run your own loop, the review test is deliberately narrow: is the task
bounded enough that a candidate can actually be rejected; when a cheap proxy and
a stronger check disagree, which one has authority; and at what commitment level
does the evidence actually let the loop stop?

## Open research questions

The worked example in this chapter demonstrates a bounded, rejectable turn, but automating this process at scale exposes several unsettled research directions. Resolving these challenges requires moving beyond manual intervention toward robust, data-driven automation.

1. How do we train models to learn an optimal escalation policy?
   Future AI loops need learned policies to dynamically allocate fixed feedback budgets. Research must define the multi-fidelity training datasets and state schemas required for an autonomous system to decide when to advance, reject, or request stronger checks without exceeding honest commitment boundaries.

2. Can we predict proxy ranking reversals before they occur?
   Methods are needed to identify when cheap proxies are actively misleading rather than waiting for a simulation stage to catch them. Research should explore training automated methods to proactively recognize architectural blind spots—such as hidden data movement or interface costs—before running expensive memory-aware verification.

3. What is the mathematical structure of a zero-knowledge replay receipt?
   Sharing evidence across organizational boundaries currently risks leaking proprietary workload and baseline data. We need privacy-preserving formulations of the replay receipt that allow external tools and reviewers to audit candidate lineage, fidelity, and rejection reasons without exposing the underlying IP.

4. How do we build a dynamic, context-aware negative trace corpus?
   The mechanism for recording a failure on the power envelope leaves open how to safely reuse that failure in future loops. Future work must design protocols that differentiate "failed this slice" from "universally bad," allowing an automated optimizer to resuscitate stale rejections when constraints, workloads, or software stacks fundamentally change.

## What to carry forward
- Reader test: Could another architect reconstruct why the surviving candidate
  advanced and what would overturn it?
- Next loop state: @sec-loop-patterns-across-stack turns this worked AI-assisted loop into
  stack-wide patterns.

[^fn-xrbench-class-c08]: **XRBench-class**: XRBench is a mobile and extended-reality benchmark suite [@KwonEtAl2023XRBench]. This chapter uses "XRBench-class" to mean a workload slice modeled on that benchmark family, not measured XRBench results.
# Loop Patterns Across the Stack {#sec-loop-patterns-across-stack}

```{=latex}
\abstract*{The Architecture 2.0 ontology is useful only if it changes how architects read real work. This chapter applies the same loop card across workload characterization, fast software loops, architecture design-space exploration, domain-specific architecture and code generation, hardware/software co-design, deployed systems, and high-commitment RTL or physical-design flows. It is a taxonomy of AI-assisted method posture, not a taxonomy of architecture tasks. The point is not that all loops should become equally autonomous. The point is that each loop has a different feedback budget, commitment boundary, evidence burden, and rejection authority.}
```

::: {.callout-crux}
How should the AI's role and the loop contract change as feedback gets more
expensive and commitments get harder to reverse across the stack?
:::

The previous chapters built the components of an Architecture 2.0 loop, and
@sec-running-the-loop ran one bounded turn of it on the lighthouse prompt. This
chapter asks whether that loop travels. If the framework only describes one
kind of design-space-exploration loop,
it is too narrow. If it describes everything in the same way, it is too vague.
The useful middle ground is a set of loop patterns.

> **Loop pattern.** A loop pattern is a recurring shape of AI-assisted
> architecture work in which a generative method or automated optimizer acts on represented state under
> a characteristic feedback budget, evidence burden, rejection authority, and
> commitment level.

Workload characterization has one pattern. Fast compiler and runtime tuning
has another. Accelerator, memory, interconnect, and chiplet exploration has
another. Domain-specific architecture and code generation has another because
local hardware efficiency only matters if the software path can reach it.
Co-design across compute, memory, network, and power has another. Fleet and
serving systems have another. RTL, physical design, and signoff have another.
The ontology is the same, but the evidence burden changes.

This distinction protects the book from two mistakes. The first mistake is to
pretend that every architecture task can be automated like a fast software
loop. The second is to become so conservative that Architecture 2.0 is only a
new name for old design review. The right question is more precise. Given this
task, representation, environment, feedback budget, and commitment level, what
method roles are useful, what evidence is credible, and what can reject the
result?

::: {.callout-learning-objectives}
After this chapter you can choose the AI-assisted loop pattern before choosing the AI method.
That means you can:

- classify an architecture task by its AI-assisted loop pattern and operating regime;
- compare cases with the same card fields instead of treating them as isolated anecdotes;
- name the cheap independent rejection authority and the human audit point for generative proposals;
- match the AI method posture and rejection authority to feedback cost and reversibility;
- state the unsupported claim boundary before the AI method overclaims.
:::

## A Template for Reading the Cases

The cases in this chapter are read through one card schema. The card asks for
intent, task, design space, representation, environment, method role, feedback
budget, evidence, negative traces, rejection authority, commitment boundary,
and human decision. This keeps the chapter from becoming a list of examples.
It also lets the reader compare loops that otherwise look unrelated. The
lighthouse prompt remains the spine:
when a separate benchmark, tool, or paper appears, it is used as a controlled
slice of the prompt (workload coverage, code generation, architecture search,
deployment feedback, or high-commitment physical evidence), not as a competing
running example. The co-design pattern also carries the measured
fleet-migration demonstration promised in @sec-running-the-loop.

Keep one rule in view as the cases become more technical. A loop does not scale
because it can produce more candidates. It scales when the card can name a cheap,
independent, trusted way to reject or clear a larger fraction of proposed
commitments. The end of the chapter writes that rule as a bound, but the cases
are the intuition for it.

@fig-loop-pattern-spectrum gives the chapter's spectrum. The
boxes are not a maturity scale. Fast software loops are not better than
high-commitment loops, and high-commitment loops are not more important than
workload loops. They are different operating regimes for the same ontology.

![Loop patterns share an ontology but not a commitment level: Feedback latency, commitment cost, rejection authority, and acceptable autonomy change across loop patterns.](images/F10-loop-pattern-spectrum){#fig-loop-pattern-spectrum width="100%" fig-alt="Spectrum diagram comparing loop patterns across the stack by feedback latency, commitment cost, rejection authority, and acceptable autonomy."}

The figure should be read horizontally, not as a maturity ladder. A fast
software loop may allow more automation because feedback is cheap and rollback
is easy. A silicon-facing loop may use the same ontology but demands stronger
evidence, independent rejection, and a tighter commitment boundary.

@tbl-loop-patterns is the compact comparison. The purpose is not to
classify every paper perfectly. It is to force an Architecture 2.0 project to
name its operating regime before choosing methods or making trust claims.
Read the method column as an agency contract: what an assistant, optimizer,
critic, or repair tool may do before independent evidence or a human owner can
reject it.

| Loop pattern | Feedback and evidence | Useful method posture | Rejection and commitment |
| --- | --- | --- | --- |
| Workload and benchmark | Traces, benchmark versions, coverage, drift, and governance. | Generate, cluster, summarize, and test workload questions. | Reject through coverage gaps, leakage, or irrelevant metrics. |
| Fast software | Unit tests, compiler/runtime results, telemetry, and quick rollback. | Higher automation for bounded search, tuning, and repair. | Reject with tests, performance regressions, or deployment guards. |
| Architecture DSE and specialization | Simulators, proxies, surrogates, compiler/runtime paths, constraints, and Pareto evidence. | Generate candidates, predict, optimize, critique, and preserve negative traces. | Reject invalid actions, proxy mismatch, software incompatibility, or weak evidence. |
| Domain-specific architecture and code generation | Kernels, compiler IRs, libraries, runtimes, generated code, interface costs, and maintainability evidence. | Generate mappings, tune schedules, explain portability limits, and critique software-path gaps. | Reject local hardware wins that fail correctness, portability, interface cost, or deployment maintenance. |
| Co-design | Cross-layer models, workload traces, topology, memory, network, power, and thermal feedback. | Coordinate methods across layers and expose tradeoffs. | Reject single-layer wins that fail system objectives. |
| Systems and fleet | Deployment telemetry, canaries, drift, isolation, and operational constraints. | Adapt, monitor, critique, and revise policy under guardrails. | Reject with SLOs, safety policies, rollback, and human review. |
| RTL and physical | Formal checks, regressions, synthesis, timing, power, layout, signoff, and review. | Narrow search, organize evidence, critique, and repair bounded artifacts. | Reject with tool flows, signoff, and accountable architect-owned commitment. |

: Different loop patterns need different evidence postures: Workload, software, design-space, code-generation, co-design, fleet, and RTL/physical-design loops use the same fields but differ in feedback latency, rejection authority, rollback cost, and commitment boundary. {#tbl-loop-patterns tbl-colwidths="[17,26,25,22]"}

The cases that follow should be read through the same three questions. First,
what are the physical constraints and rollback costs? A compiler flag, a
runtime policy, an RTL edit, a chiplet boundary, and a fleet deployment do not
carry the same blast radius (the scope of what a wrong change can damage). Second, what is the action-observation mapping?
The loop should say what it can change and what tool, trace, log, or
measurement it receives in return. Third, what are the rejection gates and
human audit points? A case is not credible because it uses an advanced method.
It is credible when the allowed actions, feedback source, evidence burden,
and rejection authority match the commitment being made.

For a new project, choose the loop pattern before choosing the method.
@tbl-loop-pattern-decision gives the decision procedure.

| If the bottleneck is... | Start with this loop pattern | First loop artifact or evidence ledger to build | Do not claim yet |
| --- | --- | --- | --- |
| Unknown workload coverage, stale benchmarks, or unclear scenario boundaries. | Workload and benchmark. | Versioned workload packet with coverage, gaps, and drift notes. | A general architecture win. |
| Fast code, compiler, runtime, or kernel feedback. | Fast software. | Testable code path with correctness, profiling, and rollback evidence. | Hardware/system superiority from a local speedup. |
| Many candidate architecture knobs under scarce simulation. | Architecture DSE and specialization. | Candidate records, action schema, proxy calibration, and rejected regions. | Implementation readiness. |
| Local hardware efficiency gated by software path, code generation, or interface cost. | Domain-specific architecture and code generation. | Executable software-path packet with kernels, IR/runtime path, interface-cost model, tests, and portability checks. | End-to-end architecture win. |
| Cross-layer tradeoffs across workload, compiler, memory, network, power, or deployment. | Co-design. | Interface map that names layer owners, changed assumptions, and rejection gates. | A single-layer optimum as a system result. |
| Live or deployment-like behavior, SLOs, canaries, or drift. | Systems and fleet. | Guarded telemetry packet with rollback and policy constraints. | Clean causal evidence without controls. |
| RTL, generators, physical design, signoff, or silicon-facing decisions. | RTL and physical. | Evidence ledger with tool-stage gates, waivers, and accountable review. | Autonomous commitment. |

: Choose the loop pattern before choosing the method: The first loop artifact
should match the bottleneck and prevent the loop from overclaiming beyond its
evidence. {#tbl-loop-pattern-decision tbl-colwidths="[26,18,30,16]"}

## Workload Characterization and Benchmark Construction

Workload characterization is not a prelude to architecture work. It is
architecture work. The workload defines what behavior matters, which metrics
are meaningful, which software stack is assumed, and which design choices can
be justified. Classic workload-characterization work made this concrete by
measuring program behavior, comparing benchmark suites, and separating
inherent workload properties from artifacts of a particular machine
[@HosteEeckhout2007MICA]. In Architecture 2.0, that lineage becomes loop
state. Trace collection, benchmark construction, workload generation,
clustering, summarization, coverage analysis, drift detection, and explicit
questions about what the benchmark does not represent are all loop state.

The lighthouse prompt makes this concrete. "XRBench-class real-time mobile XR
workload" is not a magic input string. XRBench gives the loop a benchmark anchor
[@KwonEtAl2023XRBench], but the architecture question still depends on
which XR workloads, models, devices, frame-rate targets, latency constraints,
memory behaviors, and software paths are represented. A loop that optimizes
one benchmark point may miss the distribution that a real mobile XR subsystem
must serve.
For an AI-assisted loop, the workload arrives as a packet, not a name. This packet includes scenario
labels, device class, trace provenance, input distributions, excluded cases,
coverage gaps, and rejection conditions.

MLPerf is the standing example; @sec-design-loop-no-longer-scales treated it as
maintained community infrastructure with versions, rules, and submission
practices [@MattsonEtAl2020MLPerf]. The point to carry into a loop pattern is not another benchmark history. The
loop-pattern lesson is that a benchmark is a living agreement about what evidence should
count. A workload loop should therefore record benchmark version, workload
source, coverage claims, known gaps, leakage risks, and the conditions under
which a result should not generalize.

@tbl-workload-characterization-20 makes the reframe explicit. The
left column is still necessary: representative workloads, profiles, benchmark
construction, and performance comparison remain central to architecture. The
right columns state what changes when an automated optimizer is allowed to act
inside the loop. The workload must become represented state, and the loop must
know what evidence can reject a candidate that only wins a stale, narrow, or
leaky workload slice.

| Architecture 1.0 meaning | Architecture 2.0 meaning | Loop state required | Failure if missing |
| --- | --- | --- | --- |
| Select representative workloads or benchmark suites. | Define the versioned workload distribution the loop is allowed to optimize over. | Scenario metadata, input distributions, versions, provenance, and inclusion/exclusion rationale. | The loop optimizes one stale or convenient slice and reports a false win. |
| Profile behavior: locality, branch behavior, memory traffic, bandwidth, latency, energy, and phase behavior. | Expose workload features that can drive prediction, search, critique, and active test selection. | Feature schema, measurement provenance, tool configuration, uncertainty, and known blind spots. | A predictor learns a proxy that does not survive another phase, input, or fidelity level. |
| Compare architectures under a fixed benchmark. | Maintain an evidence ledger across workload variants, candidate designs, and fidelity levels. | Candidate IDs, workload IDs, simulator/tool versions, feedback cost, accepted results, and rejected results. | Design-space results cannot be audited or reused by another loop. |
| Build or curate benchmarks for community comparison. | Define an environment contract: valid tasks, inputs, actions, metrics, leakage rules, and rejection checks. | Benchmark harness, validity checks, metric definitions, seeds, test splits, and update policy. | The loop overfits benchmark artifacts or takes actions outside the intended task. |
| Explain why a workload matters. | Make workload intent, deployment context, and drift explicit enough for a human to accept or reject decisions. | Use-case assumptions, deployment constraints, quality-of-service targets, telemetry hooks, and review notes. | The loop produces a plausible result for the wrong product or deployment regime. |
| Summarize results for a paper. | Preserve workload evidence as reusable architecture data. | Evidence ledger, negative traces, failed runs, rejected alternatives, and rationale for final claims. | The next loop repeats invalid experiments or loses why prior choices were rejected. |

: Workload characterization becomes represented loop state: Classic profiling and benchmark construction remain necessary, but an Architecture 2.0 loop must also record versions, provenance, coverage, rejection conditions, and failure traces. {#tbl-workload-characterization-20 tbl-colwidths="[20,26,25,20]"}

The method roles in this loop are often not glamorous. A useful tool might
cluster traces, generate candidate benchmark questions, identify missing
coverage, compare workload versions, or critique whether a paper's workload
supports its claim. Those roles are valuable because they improve the question
the architecture loop is answering.

Read as a loop card, the pattern is compact: the task is workload definition;
the representation is versioned traces, metadata, and coverage notes; the
environment is a benchmark harness with update rules; the method posture is
clustering, summarization, generation of missing cases, and critique; the
rejection authority is coverage, leakage, drift, or irrelevant metrics; the
commitment boundary is whether a design claim may generalize beyond the measured
slice.

## Fast Software Loops

Moving from workload definition to code generation, fast software loops sit near the low-commitment end of the spectrum. Compiler
flags, kernels, library implementations, runtime policies, configuration
settings, and small code repairs can often be evaluated quickly and rolled
back. Feedback may come from unit tests, microbenchmarks, integration tests,
profilers, telemetry, or canary deployment[^fn-canary-deployment-c09].

This is the regime where stronger automation is often plausible. Autotuning
systems and learned tensor-program optimizers[^fn-tensor-program-optimizers-c09] show how search spaces, cost
models, measurements, and scheduling can be combined to improve software
performance across targets
[@ChenEtAl2018AutoTVM; @ZhengEtAl2020Ansor]. An Architecture 2.0 loop can
learn from that pattern without pretending that all hardware design is equally
reversible.

Kernel-generation benchmarks make the same point in a current form.
KernelBench evaluates whether models can produce GPU kernels that are both
correct and faster than a baseline [@OuyangEtAl2025KernelBench]. This is
a fast software loop because correctness tests, compilation, profiling, and
microbenchmark feedback are close to the generated artifact. It also touches
hardware/software co-design because performance depends on memory layout,
parallelism, numerical precision, backend behavior, and target-specific
hardware resources. Multi-platform kernel-generation work makes that bridge
explicit by separating the core benchmark from target backends
[@WenEtAl2025MultiKernelBench].
For an automated optimizer, the benchmark object needs more than a prompt and a score: kernel
IDs, input-shape distributions, correctness oracles, target metadata,
compile/profile failure traces, and rejected variants.

Read as a loop card, the task is bounded code generation or tuning; the
representation is source code, compiler IR, tests, target metadata, and
profiling output; the environment is the compiler/runtime/profiler path; the
method posture can be more automated because feedback is cheap; the rejection
authority is correctness, compilation, portability, performance regression, and
deployment maintainability; the commitment boundary arrives when a local kernel
change becomes part of a larger software or hardware contract.

The reason autonomy can be higher here is not that the task is easy. It is
that failures are often observable, bounded, and reversible. A generated
kernel can be tested. A compiler flag can be reverted. A runtime policy can be
canaried. A regression can be caught by a benchmark or deployment guard.
Because rejection is close to the action, the loop can iterate quickly.

::: {.callout-failure-mode title="Fast feedback is not complete truth"}
Treating fast feedback as complete truth is the trap for the optimizer. An AI-generated kernel that
wins on one input size may regress another. An AI-proposed runtime policy that improves
average latency may worsen tail latency. Even in fast AI-assisted loops, the
card still needs workload coverage, rejection authority, and a human decision
when the AI's change affects a larger system.
:::

## Architecture Loops: Accelerators, Memory, and Chiplets

Moving beyond software, architecture design-space exploration represents the canonical middle case in terms of commitment and feedback cost. The loop
may explore accelerator organization, vector width, cache hierarchy, local
memory, interconnect, chiplet partitioning, and package assumptions. It may
also choose how work is divided across CPUs, accelerators, and SoC blocks.
Feedback is slower than software tests and less definitive than silicon.
Actions can be invalid. Proxies can lie. The space is too large for exhaustive
enumeration.

This is where the Architecture 2.0 framework feels most natural. The task is
bounded but rich. The representation must expose architectural state. The
environment must define legal actions and observations. Methods can generate
candidates, predict behavior, optimize evaluations, critique assumptions, and
preserve negative traces. ArchGym, an OpenAI Gym-based framework, is one example of making such loops more
explicit for machine-learning-assisted architecture design
[@KrishnanEtAl2023ArchGym]; predictive design-space-exploration work
shows that data-driven modeling has a longer architecture lineage
[@IpekEtAl2006PredictiveDSE]. Transferable frameworks such as Apollo go a step
further, training a surrogate on an architecture dataset and carrying the same
search across different design spaces [@yazdanbakhsh2021apollo].
That dataset has to be treated as a loop artifact, not a generic training set. Its
design-space schema, sampled-region coverage, tool versions, invalid-action
labels, rejected regions, and proxy-fidelity calibration determine what a generative method
may infer from it.

Chiplets raise the stakes because they turn partitioning and interfaces into
legal actions inside the loop. A UCIe-class interface should be represented as
an environment contract that specifies what may be split across dies, what
bandwidth/latency/power/thermal feedback tools return, which package and
software assumptions are fixed, and which candidates must escalate or be
rejected when interface evidence is missing [@UCIeConsortium2026Spec].

::: {.callout-lighthouse title="The subsystem choice is an integration choice"}
Context. In an AI-assisted architecture DSE loop, "CPU extension," "accelerator," and
"SoC block" are not interchangeable labels for the AI to explore.

In the Lighthouse prompt. "64-bit RISC-V-based compute subsystem" and
"vector-capable CPU, accelerator, or SoC block" ask where the "XRBench-class
real-time mobile XR workload" lives relative to the core, memory hierarchy,
interconnect, compiler/runtime path, and product boundary. If the optimizer proposes a vector extension, it
changes the CPU contract; if it proposes a tightly coupled accelerator, it changes the invocation,
sharing, and memory-attachment contract.

Integration boundary. The method may still test a looser accelerator variant,
but the loop environment must make the coupling assumption explicit so the optimizer cannot silently break integration contracts.

::: {.callout-architect-checkpoint title="The Cross-Layer Rejection Gate"}
When an optimizer tunes a candidate architecture against a local proxy (like core area), the architect must enforce cross-layer boundaries. Does the loop environment automatically reject candidates that only win by silently pushing complexity into memory traffic, compiler support, verification, or SoC integration?
:::
:::

Read as a loop card, the task is architecture search; the representation is
candidate parameters, workload state, constraints, tool configurations, and
prior rejected regions; the environment is a simulator, mapper, compiler path,
or staged DSE harness; the method posture is generation, prediction,
optimization, and critique; the rejection authority is invalid actions,
simulator mismatch, power or software incompatibility, and weak Pareto evidence;
the commitment boundary is escalation to stronger feedback.

## Domain-Specific Architecture and Code Generation

When architecture search narrows to a specific problem, domain-specific architecture is often presented as an efficiency story. If the
domain is narrower, the hardware can be more efficient. That statement is
true but incomplete. A domain is not one knob. It can be a kernel family, a
model family, a data type, a memory-access pattern, a programming model, a
deployment regime, a latency envelope, a product vertical, or an ecosystem of
libraries and tools. The golden-age argument for specialization
[@HennessyPatterson2019GoldenAge] therefore creates a loop-design
question: which part of the domain is stable enough to specialize, and which
part must remain programmable?

Use Amdahl here as a loop-contract check, not as an architecture refresher. The
represented state is end-to-end workload fraction and offload granularity, the
legal action is a specialization/interface choice, and the rejection rule is
that a local speedup fails unless measured interface and software overheads
still leave an end-to-end win.
Every architect knows Amdahl's law [@Amdahl1967ValiditySingleProcessor], so
restating it adds little. What follows is not a restatement but a relabeling of
its variables: the version that matters here is the one that prices the interface. Hill and Marty re-derived the law for the multicore era to show
how its lesson shifts when the substrate changes
[@HillMarty2008AmdahlMulticore], and LogCA, an analytical model for hardware accelerators, models the accelerator case
directly: it makes offload latency, per-invocation overhead, and operation
granularity first-class terms alongside the raw acceleration
[@AltafWood2017LogCA]. The compact form used here keeps those costs visible:
$$
S_{\mathrm{system}} \le
\frac{1}{(1-f) + f/s + \epsilon_{\mathrm{interface}} +
\epsilon_{\mathrm{software}}}.
$$
Here, $f$ is the fraction of the end-to-end workload that the specialized
mechanism can improve, $s$ is its local speedup, and the $\epsilon$ terms
stand for the interface and software overheads that the LogCA-style model makes
visible, expressed, like $f$ and $f/s$, as fractions of the baseline time so
the terms share units. The reading is the one LogCA emphasizes: a design pays for specialization only when
the accelerated work is large enough, and coarse enough per invocation, to
amortize the cost of reaching the accelerator. A dramatic local speedup can
still fail as an architecture result if the stable domain fraction is small,
the interface is expensive, or the software path cannot keep up. This same form
returns at the end of the chapter, lifted from one accelerator's speedup to the
throughput of the entire design loop (@sec-the-rejection-bound).
For an AI-assisted loop, this equation is a rejection contract. A proposed
specialization is not credible unless the method also carries interface,
software-path, and end-to-end evidence.

@fig-logca-breakeven uses a simplified LogCA-style calculation
[@AltafWood2017LogCA]. End-to-end speedup is not a property of the accelerator
alone. It rises with the work amortized per offload, and only after that
granularity clears a break-even point set by offload latency and overhead. A
tightly coupled unit breaks even at small granularity; an off-chip module may
need thousands of operations per call before offload is worth doing at all.

```{python}
#| label: fig-logca-breakeven
#| fig-cap: |
#|   The interface sets a break-even granularity: In a simplified LogCA-style model [@AltafWood2017LogCA], end-to-end speedup rises with the work amortized per offload only after it clears a break-even granularity set by offload latency and overhead, then saturates at the accelerator's peak acceleration. The farther the accelerator sits from the host, the larger the granularity needed before offload even breaks even. Curves are illustrative; the lesson is the break-even cliff, not the exact values.
#| out-width: "100%"
#| fig-alt: "Line plot showing offload speedup curves that rise only after enough work is amortized to overcome interface latency and overhead."

import matplotlib.pyplot as plt
from _python.arch2_plots import COLORS, add_note_box, apply_style

apply_style()

A = 100.0  # peak acceleration (asymptote)
g = [10 ** (6 * i / 399) for i in range(400)]

curves = [
    {"label": "tightly coupled accelerator", "ovh": 2.0, "color": COLORS["orange"]},
    {"label": "shared-memory SoC block", "ovh": 40.0, "color": COLORS["green"]},
    {"label": "off-chip / discrete module", "ovh": 1500.0, "color": COLORS["red"]},
]


def speedup(gran, ovh):
    # LogCA: Speedup(g) = C*g / (o + L + C*g/A), with C = 1, beta = 1, (o + L) = ovh
    return gran / (ovh + gran / A)


fig, ax = plt.subplots(figsize=(5.25, 3.12))
fig.subplots_adjust(left=0.12, right=0.86, top=0.82, bottom=0.28)

ax.axhline(A, color=COLORS["ink"], linewidth=0.8, linestyle=(0, (4, 3)), zorder=1)
ax.text(1.35, A * 1.08, "peak acceleration A", ha="left", va="bottom", fontsize=6.2, color=COLORS["ink"])
ax.axhline(1.0, color=COLORS["muted"], linewidth=0.7, zorder=1)
ax.text(7.5e5, 1.10, "break-even", ha="right", va="bottom", fontsize=6.0, color=COLORS["muted"])

ax.axhspan(0.25, 1.0, color="#F2D9D9", alpha=0.35, zorder=0)
ax.text(1.5, 0.38, "offload loses", ha="left", va="center", fontsize=6.0, color=COLORS["red"], fontstyle="italic")

for c in curves:
    s = [speedup(x, c["ovh"]) for x in g]
    ax.plot(g, s, color=c["color"], linewidth=1.9, zorder=3, label=c["label"])
    g1 = c["ovh"] / (1.0 - 1.0 / A)
    ax.scatter([g1], [1.0], marker="o", s=22, facecolor=COLORS["note_fill"], edgecolor=c["color"], linewidth=1.3, zorder=4, clip_on=False)

ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlim(1, 1e6)
ax.set_ylim(0.25, 150)
ax.set_xlabel("operation granularity  (work amortized per offload)", fontsize=7)
ax.set_ylabel("end-to-end speedup", fontsize=7)
ax.set_yticks([0.3, 1, 3, 10, 30, 100])
ax.set_yticklabels(["0.3x", "1x", "3x", "10x", "30x", "100x"], fontsize=6.4)
ax.tick_params(axis="both", length=2.5, width=0.6, pad=2, labelsize=6.4)
ax.grid(axis="both", color=COLORS["grid"], linewidth=0.5, zorder=0)

for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)
ax.spines["left"].set_color(COLORS["ink"])
ax.spines["bottom"].set_color(COLORS["ink"])

legend = ax.legend(
    loc="lower left",
    bbox_to_anchor=(0.0, 1.02),
    fontsize=6.0,
    frameon=True,
    facecolor="white",
    edgecolor="white",
    framealpha=0.92,
    handlelength=1.6,
    borderpad=0.15,
    labelspacing=0.3,
    ncol=1,
)
for text in legend.get_texts():
    text.set_color(COLORS["ink"])

add_note_box(
    fig,
    "Simplified LogCA-style view: the farther the accelerator sits from the host, the larger the granularity needed before offload breaks even.",
    xywh=(0.10, 0.03, 0.80, 0.11),
    fontsize=5.5,
)

plt.show()
plt.close(fig)
```

@fig-domain-specificity-shapes should be read as a checklist
rather than a taxonomy. Before a loop proposes a domain-specific block, it
should say what shape of domain it is using and what that choice implies for
representation, action space, evidence, and maintenance. A benchmark name is
not enough. Two workloads in the same named domain may have different memory
behavior, precision contracts, software interfaces, or deployment drift.
The kernel family, precision contract, data-movement
pattern, software interface, drift risk, and test coverage determine which optimizer actions are legal and which
claims a loop must reject.

![Domain specificity has many shapes: A domain-specific architecture is not specialized for a label; it is specialized for a bundle of kernel, precision, data-movement, interface, deployment, drift, and verification constraints. The loop must represent the shape it is claiming to exploit.](images/F10a-domain-specificity-shapes){#fig-domain-specificity-shapes width="100%" fig-alt="Multi-shape diagram showing that domain specificity can arise from kernels, precision, data movement, interfaces, deployment constraints, drift, and verification needs."}

If the domain shape determines what to build, the software path is the loop's narrow waist. Halide-style algorithm/schedule
separation, AutoTVM/Ansor-style measured schedules, and MLIR-style multi-level
compiler representations matter here because they turn software reachability
into represented state, legal mapping actions, compiler feedback, and rejection
evidence for specialized hardware claims
[@RaganKelleyEtAl2017HalideCACM; @ChenEtAl2018AutoTVM; @ZhengEtAl2020Ansor; @LattnerEtAl2020MLIR].

@fig-codegen-narrow-waist makes the implication architectural. Code generation is the narrow waist of specialization. Above the waist are
domain intent and workload distributions. Below the waist are hardware
mechanisms, tool feedback, profiling, simulation, and deployment evidence. The
waist itself contains the programming model, compiler IR, libraries, runtimes,
and generated code that let the workload reach the machine.

![Specialized hardware needs a code-generation waist: Domain-specific architecture claims must pass through executable software paths and be checked with correctness, performance, portability, and maintainability evidence.](images/F10b-codegen-narrow-waist){#fig-codegen-narrow-waist width="92%" fig-alt="Narrow-waist diagram showing programming models, compiler representations, libraries, runtimes, and generated code connecting specialized hardware to evidence checks."}

Generative methods may help at this waist, but only inside a represented loop.
Kernel-generation benchmarks are encouraging precisely because they keep
correctness tests, compilation, profiling, and target-specific behavior close
to the generated artifact [@OuyangEtAl2025KernelBench; @WenEtAl2025MultiKernelBench].
For architecture, the same discipline must extend beyond one kernel. The loop
needs workload semantics, data layout, scheduling constraints, backend
capabilities, correctness tests, portability limits, and rejection authority. The
architectural question is not only whether a specialized block is efficient.
It is whether the hardware/software interface can keep that efficiency usable
as workloads, models, compilers, and products change.

Read as a loop card, the task is not "generate code" in isolation. It is to keep
a domain-specific hardware claim executable. The representation includes domain
shape, kernel family, compiler IR, runtime interface, data layout, and
maintenance evidence. The feedback budget is split. Kernel and schedule feedback
is cheap and reversible, so a method may tune aggressively at that level, while
the hardware-interface commitment it implies is expensive and hard to undo, so
the loop must hold that layer behind independent evidence. The rejection
authority is correctness, portability, interface cost, workload drift, and
end-to-end system measurement. The commitment boundary is the point where a
cheap kernel-level win gets read as a hardware-interface decision, which only
end-to-end measurement and a human owner may cross.

::: {.callout-architect-checkpoint title="The Hardware-Interface Commitment Gate"}
When the optimizer tunes a kernel aggressively, it often implies a hardware-interface commitment. The architect must explicitly define the commitment boundary where a cheap kernel-level win proposed by the model gets evaluated as an expensive hardware-interface decision, requiring end-to-end measurement and human sign-off.
:::

::: {.callout-failure-mode title="The accelerator that won in isolation"}
An AI-generated specialized block posts a large kernel-level speedup and looks like a clear
win. In the full system the gain mostly disappears: the compiler cannot
generate code that keeps the unit busy, data movement to and from the block
dominates, and only a hand-written kernel ever reached the headline number. The
AI's hardware proposal was not wrong; the loop measured the wrong thing. This is the lesson
the LogCA-style model makes visible. Price the interface and the software path before believing
a local speedup, and reject the AI's candidate until a compiler-generated,
end-to-end measurement survives.
:::

## Co-Design Loops: Compute, Memory, Network, and Power

While domain-specific loops focus on vertical execution, co-design loops test the oldest claim in this book. Architecture is not only a
layer below software but the place where software behavior, hardware
mechanisms, physical constraints, and system
objectives meet. A single-layer optimization can therefore be locally correct
and globally wrong.

Consider a dataflow choice that reduces compute cycles but increases memory
traffic, a topology change that improves one collective while worsening
another, a cache change that improves average performance but increases tail
latency, or a rack-level policy that saves power while violating service
quality. The loop must represent more than one layer because the objective
lives across layers.

Energy and warehouse-scale coupling matter here because they give the loop cheap
rejectors for cross-layer claims. Data movement, memory locality, network
contention, power and thermal headroom, and deployment policy can all invalidate
a local compute win before expensive implementation evidence is gathered
[@Horowitz2014Energy; @BarrosoHolzleRanganathan2019DatacenterAsComputer].

An Architecture 2.0 co-design loop therefore needs richer representations, such as
workload phase behavior, data movement, memory locality, network behavior,
power and thermal constraints, compiler/runtime choices, and deployment
policy. The useful method roles are coordination and critique as much as
search. The loop should ask which layer changed, which objective improved,
which objective worsened, and which evidence would reject a single-layer win.
In an AI-assisted co-design loop, coordination means naming which layer the
automated optimizer may touch, which layer supplies independent feedback, and which owner
accepts the cross-layer tradeoff.

::: {.callout-architect-checkpoint title="The Cross-Layer Ownership Gate"}
Before an optimizer acts in a co-design loop, the architect must explicitly name which layer the optimizer may touch, which layer supplies independent feedback, and which human owner holds the authority to accept the cross-layer tradeoff.
:::

Warehouse-scale computing itself, read as a loop card, is a cross-layer
co-design pattern. The task is useful work per constrained resource; the representation is
workload, software, hardware, network, power, cooling, and operations state; the
environment combines models, traces, deployment measurements, and operational
rules; and the rejection authority is a system objective that a local win violates.

Many Architecture 2.0 loops are even less static than this summary suggests.
In early accelerator, compiler, runtime, or system-interface work, the hardware
target and the software path may both be changing. The loop is then not merely
searching a fixed space; it is managing hardware/software co-evolution. A new
instruction, tensor unit, scratchpad policy, data layout, or runtime interface
changes what software can express, while compiler, kernel, and workload
feedback changes which hardware feature is worth keeping. The evidence ledger
has to record that co-evolution by tracking what hardware state existed when the software
was generated, which examples or optimization rules were available, which
correctness checks and performance measurements returned, and which hardware
or software assumption was revised after rejection.

The durable lesson is not that code generation solves architecture. It is that
software feedback can become part of architecture evidence when the loop keeps
the hardware target, code path, tests, performance counters, rejected variants,
and decision owner tied together. Without that record, a strong generated
kernel or library path may only prove that one software artifact matched one
hardware snapshot.

@fig-hardware-software-coevolution shows the loop discipline this requires. The
hardware side and software side may both change, so the evidence ledger must
record the versions, measurements, failures, and rejected variants that connect
them. Otherwise, the loop cannot say whether the architecture improved or only
whether one generated path happened to work.

![Hardware and software co-evolve through shared evidence: Early architecture work often changes the hardware target and the software path at the same time. The loop becomes credible when the hardware snapshot, software artifact, tests, metrics, rejected variants, and decision owner are recorded together.](images/F10c-hardware-software-coevolution){#fig-hardware-software-coevolution width="100%" fig-alt="Two-lane diagram showing hardware target state and software path state evolving together through a shared evidence ledger, rejection gate, and architect decision path."}

Google's warehouse-scale migration from x86 to Arm is a deployed instance of
this discipline [@ChristopherEtAl2025ISAMigration]. Moving a production fleet
that runs services such as Gmail and BigQuery onto a new instruction set is
co-evolution at scale. The hardware target changes and tens of thousands of
applications must follow. The reported effort analyzed more than 38,000
migration commits and wrapped part of the software change in an AI-assisted
build-and-test repair loop, accepting a candidate fix only when the build and
the test suite pass, and letting a fleet monitor automatically evict jobs that
crash-loop or run slow on the new target. Authority sits with the instruments,
not the generator. Build, test, sanitizers that expose memory-model differences
between the two ISAs, and the production monitor that rejects regressions and
preserves the evicted cases as negative traces for offline debugging. The repair
tool resolves only a minority of failures on its own, roughly a third of broken
tests without tuning, and the hardest changes stay with the application owners
who know the code. The model behind the loop will age; the structure, a
represented migration loop with instrument-held rejection authority and
human-owned exceptions, is the part worth keeping.

When read through the same card, the migration case is not mainly an Arm story.
It is a loop-contract story. @tbl-isa-migration-loop-card summarizes the
reusable fields.

| Card field | Migration reading |
| --- | --- |
| Task | Move production services across an ISA boundary while preserving build, test, and rollout behavior. |
| Representation | Migration commits, build targets, tests, sanitizer findings, service ownership, and evicted production cases. |
| Environment | Build-and-test repair loop plus production monitoring on the new target. |
| Method role | Propose bounded software repairs and route failures toward owners. |
| Cheap independent rejector | Build failures, test failures, sanitizer failures, crash loops, slow jobs, and monitor-triggered evictions. |
| Commitment boundary | Automated repair can clear only the failures its instruments settle; application owners keep the exceptions. |

: ISA migration as a loop card: The reusable lesson is the structure of the
migration loop, which requires represented state, independent rejection, preserved failures, and
human-owned exceptions. {#tbl-isa-migration-loop-card tbl-colwidths="[24,66]"}

The most instructive result is what the evidence overturned. Going in, the team
and the application owners expected the work to be dominated by low-level
architectural differences like floating-point drift, concurrency, and
platform-specific intrinsics. The recorded evidence showed otherwise. Most of
the effort was tests that encoded x86-specific assumptions, build and release
systems, and configuration rollout. Unaided architectural intuition mispredicted
where the work actually was. That is the case for a represented, evidence-bearing
loop in a single sentence. The loop found the work the experts did not expect.

::: {.callout-lighthouse title="Migration evidence shows what ISA claims owe"}
Context. The ISA migration case shows why the lighthouse phrase "64-bit
RISC-V" is not only a hardware target for the optimizer to select.

In the Lighthouse prompt. If the model chooses a "64-bit RISC-V-based" path for the
"compute subsystem", it means the AI-assisted loop owes evidence for generated code, ABI
and memory-model assumptions, compiler/runtime behavior, library support, tests,
and deployment rollout, not just an instruction encoding.

Boundary. The migration case is not the same target, but it reveals the kind
of software-contract evidence a RISC-V subsystem claim would eventually need.
Build, test, sanitizers, production monitors, and application owners become
rejection authorities for the AI's ISA choice.

Takeaway. ISA decisions proposed by an automated optimizer are credible only when the loop can show what
software actually survives the contract and what remains a human-owned
exception.
:::

## Systems Loops: Runtime, Serving, and Datacenter Policy

Moving from design and migration to active operation, systems loops evaluate architecture choices in deployed or deployment-like
contexts. They include scheduling, serving, admission control, memory
allocation, power management, placement, rollout policy, fleet telemetry, and
performance isolation. Their feedback can be richer than simulation because it
comes from real systems. It can also be noisier, more confounded, more
privacy-sensitive, and harder to reproduce.
The deployment-facing benchmark lesson from the workload-pattern discussion
still applies here. Evaluation has scenarios, latency constraints, power
envelopes, and system rules, not only a single accuracy or throughput number.
Fleet loops add another layer, consisting of live telemetry, canary policy, rollback, and
operational review.
For automated optimizers acting inside these loops, telemetry is governed data. The schema, cohort
provenance, canary labels, privacy filters, drift detectors, rollback triggers,
and preserved failure traces define what the loop may trust.

The design-loop card changes accordingly. The representation must include
operational state, workload drift, service-level objectives[^fn-service-level-objectives-c09], resource
contention, customer or user constraints, and rollback mechanisms. The
environment may be a simulator, test cluster, replay harness, staging system,
or production system with guardrails. The method may adapt policy, detect
drift, summarize telemetry, or propose a controlled experiment.
For an AI-assisted system, the legal actions should be enumerated narrowly, such as adjusting
a scheduler weight, proposing a canary, changing an admission threshold, or
selecting a replay cohort, and every action should name the telemetry feedback,
rollback trigger, and human owner that can stop it.

The rejection authority is often operational. A service-level objective, a
canary guard, an alert, a safety policy, a privacy constraint, or a human
operator can stop a rollout. Crucially, in a modern datacenter, this fleet-level rejection authority must tightly govern network congestion and tail latency SLAs, not merely average throughput or node-level power limits. This makes systems loops different from pure
software loops. They may be reversible, but reversibility is not free. A bad
policy can waste power, violate latency targets, create interference, or
damage user experience before it is rolled back.

::: {.callout-architect-checkpoint title="The Operational Rejection Gate"}
In AI-assisted systems loops, reversibility is not free. The architect must ensure that the AI's proposed policy changes are gated by an operational rejection authority, such as a canary guard or SLO monitor, that can automatically stop a bad rollout before it wastes power or damages user experience.
:::

This pattern is important for Architecture 2.0 because architecture is
increasingly evaluated through deployed behavior. A design that looks strong
under a static benchmark may face different workload mixes, model versions,
traffic patterns, or fleet policies. The loop must therefore connect
architecture evidence to system evidence without pretending that production
telemetry is a clean oracle.

Read as a loop card, the task is guarded adaptation or policy revision; the
representation is operational state, workload drift, SLOs, resource contention,
and rollout state; the environment is a replay harness, staging system, or
production system with guardrails; the method posture is monitoring, critique,
controlled experimentation, and conservative adaptation; the rejection authority
is SLO violation, safety or privacy policy, rollback, and human operations
review.

## High-Commitment Loops: RTL, Physical Design, and Verification

At the furthest end of the spectrum from software, high-commitment loops stress-test the framework. RTL changes,
generator-level edits, physical design, timing closure, layout, power
analysis, formal verification, signoff, and silicon-facing decisions are
expensive to evaluate and costly to get wrong. Feedback is delayed. Tool
flows are complex. Evidence must survive independent checks. The human
commitment level is high.

For the lighthouse prompt, this is the point where a candidate subsystem stops
being a plausible design-space result and starts making claims that must
survive RTL checks, physical constraints, power analysis, verification, and
integration review.

This does not mean Architecture 2.0 is irrelevant. It means the method posture
should change. In high-commitment loops, the most valuable roles may be
critique, search narrowing, evidence organization, bounded repair, test
generation, report summarization, and inconsistency detection. A system that
finds missing assumptions, organizes tool evidence, explains why a candidate
failed, or narrows a physical-design search space may be more useful than one
that claims to make final autonomous decisions.

Learning-assisted chip placement is a prominent, and disputed, example of a
design subflow being formulated as a learning problem
[@MirhoseiniEtAl2021GraphPlacement]. @sec-feedback-verification-trust discusses
the later baseline and reproducibility challenge. The Architecture 2.0 lesson is
not that all physical design should be handed to an automated optimizer. It is that even when
learning methods help, the loop still needs tool constraints, baselines,
provenance, rejection authority, and human commitment.

The regime also has public success reports, and they sharpen the same lesson
rather than contradict it. Vendor-reported reinforcement-learning systems have
searched the physical-implementation flow for commercial tapeouts at scale
[@Synopsys2023DSOai], and peer-reviewed work on reinforcement learning over a
bounded circuit space produced arithmetic units that shipped in GPU silicon
[@RoyEtAl2021PrefixRL].
Reported results in this space are not uniformly settled. Some ML-for-physical-design
claims have had their baselines and reproducibility publicly debated, which is
precisely why the loop's evidence and gates, not the headline, are what earn trust.
What makes these loops credible is not the method alone; it is that outputs are
routed through independent tool checks and signoff gates before commitment, with
the exact gate depending on the flow and source. They also surface the
architect's economic question. A search that costs many machine-hours per block
is justified only when the result is amortized. A generated circuit instantiated
across every shipped unit of a high-volume part repays its search cost in a way
that a one-off block never could. The high-commitment regime therefore rewards
methods whose cost amortizes over many uses and whose outputs survive
independent checks.
The inspectable loop record matters more than the success label. The initial design
state, allowed flow knobs, tool versions, failed candidates, signoff checks,
waivers, escalation points, and the accountable commitment owner must travel
with the result.

The rejection authorities in this regime are strong. They include parsers, type checks,
regression suites, formal tools, synthesis, timing, power analysis, layout
rules, signoff flows, integration review, and expert judgment. A candidate
that fails here is not a near miss to be explained away. It is evidence that
the loop must revise its representation, action space, method, or claim.

Read as a loop card, the task is bounded RTL, generator, or physical-design
improvement; the representation is implementation state, constraints, tests,
tool reports, waivers, and review decisions; the environment is a staged tool
flow with scarce high-fidelity samples; the method posture is narrowing,
critique, bounded repair, evidence organization, and test generation; the
rejection authority is independent tool and expert review; the commitment
boundary remains architect-owned.

## The Loop Is Rejection-Bound {#sec-the-rejection-bound}

These loop families look different on the surface, yet they succeed and fail for
the same reason. Architects instinctively treat a slow design loop as
*generation-bound*, as if the fix were to propose more candidates faster. It is
not. Just as a kernel can be memory-bound rather than compute-bound, a design
loop is *rejection-bound*. Its throughput is set by how fast trusted, independent
rejection can be applied, not by how fast candidates can be produced. That reason
can be written down. The interface speedup form
used earlier for accelerators lifts cleanly from one block to the whole loop.
There it priced the cost of reaching an accelerator. Lifted one level, it prices
the cost of reaching a decision. The resulting bound measures how much useful
design progress the loop makes per commitment once the cost of trusted feedback
is paid.

Keep Amdahl's $f$, but raise what it counts. It is no longer the fraction of
computation that an accelerator speeds. It is the fraction of design commitments
that a cheap, independent, trusted rejection authority can discharge without
escalating to expensive feedback or human judgment. This is rejection authority
(@sec-feedback-verification-trust) in its
algebraic role; this section uses rejector only as shorthand for the authority
that applies the check. Take the slow loop that checks every commitment at full
fidelity as the baseline. Introduce a cheap rejection authority that clears a
fraction $f$ of commitments at a small fraction of that cost, and the loop's
throughput obeys
$$
S_{\mathrm{loop}} \le
\frac{1}{(1-f) + f \cdot (c_{\mathrm{cheap}}/c_{\mathrm{hi}}) +
\epsilon_{\mathrm{escalate}}}.
$$
Here $f$ is the fraction of commitments a cheap, independent, trusted instrument
can settle without escalating by catching a violation and rejecting it, or clearing it at
the commitment level the stage is deciding. Rejection is what such an instrument
does most reliably, and acceptance is only ever as strong as the check and the
commitment behind it. A green test suite is enough to accept a code fix, but not
to certify a tapeout. The commitments that need a stronger acceptance than the
cheap instrument can give fall in $(1-f)$, the irreducible part that only
higher-fidelity feedback or human judgment can clear.

The ratio
$c_{\mathrm{cheap}}/c_{\mathrm{hi}}$ is the cost of a cheap check relative to a
high-fidelity one, and $\epsilon_{\mathrm{escalate}}$ is the escalation overhead, defined as
the rate at which the cheap rejection authority defers times the cost of each
climb up the fidelity ladder, expressed relative to $c_{\mathrm{hi}}$. The form
charges the cheap check only on the commitments it settles; a rejection
authority that must screen every candidate pays $c_{\mathrm{cheap}}$ on all of
them, which only lowers
$S_{\mathrm{loop}}$ further, so the relation is written as an upper bound, with
equality in the idealized case where triage and escalation overheads vanish.

The form is Amdahl's law as LogCA prices it
[@Amdahl1967ValiditySingleProcessor; @AltafWood2017LogCA]. The cheap rejection
authority's local speedup is just $c_{\mathrm{hi}}/c_{\mathrm{cheap}}$, so the
middle term is exactly Amdahl's $f/s$, and escalation overhead plays the role
the interface cost played for the accelerator. The form is borrowed and
credited. What is new is what the variables name and what they rule out.

What they rule out is the thing most easily mistaken for progress. Candidate
count does not appear in the bound. That much is nearly a tautology, since
$S_{\mathrm{loop}}$ is a per-commitment ratio and the candidate count divides
out. Candidate count still sets the loop's total load and wall-clock; what it
cannot move is the per-commitment throughput $S_{\mathrm{loop}}$, which improves
only when rejection coverage, rejection cost, or escalation overhead improves. The substantive claim is that generation and rejection are ordinarily
independent levers. Proposing more designs raises the candidate count but not
$f$, so a loop can multiply its proposals by a thousand and move
$S_{\mathrm{loop}}$ not at all. The one way out is a generator good enough to
propose only obviously-good or obviously-rejectable candidates, which would raise
$f$ itself, a better rejector wearing a generator's clothes. Short of that, the
bound exposes only three levers, which are to raise $f$, lower the cost ratio, or lower
escalation overhead.

A paper that tests the bound would need loop-turn traces, not only faster
generators. Each candidate commitment would be labeled rejected, cleared, or
escalated; cheap-check and high-fidelity costs would be measured; independence
between generator and rejection authority would be tested; and false-pass or
false-reject rates would bound the strongest claim the cheap authority can
support. Without those labels, $f$ is only rhetoric.

::: {.callout-engineer-move title="Measuring the rejection bound"}
To estimate $f$ for a real AI-assisted loop rather than assert it, fix a protocol before the run.

- Commitment unit. State what one commitment is (an AI candidate accepted for the
  next fidelity stage, an RTL change merged, a signoff waiver), so $f$ is a rate
  over comparable events.
- Outcome labels. Label every AI candidate commitment `cleared`, `rejected`,
  `escalated`, or `waived`, and reserve `false pass` and `false reject` for
  outcomes overturned later.
- Costs. Record the cheap-check cost $c_{\mathrm{cheap}}$ and the high-fidelity
  cost $c_{\mathrm{hi}}$ actually paid, not list prices.
- Independence. Disclose whether the rejector shares data, model, or authorship
  with the AI generator; a rejector that does is not independent, and $f$ is inflated.
- False-reject audit. Periodically escalate a random sample of rejected
  candidates to higher fidelity. The fraction that would have cleared estimates the
  false-reject rate and bounds how aggressive the cheap authority may safely be.

Without this protocol, $f$ is a story about the AI-assisted loop, not a measurement of it.
:::

::: {#pri-rejection-bound .callout-design-principle title="The loop is rejection-bound, not generation-bound"}
An AI-assisted design loop's throughput is bounded by its rejection capacity, not the AI's
generation capacity. AI candidate count is absent from the bound. The loop speeds up
only when a cheap, independent, trusted rejector discharges a larger fraction of
AI-proposed commitments, when trusted feedback gets cheaper relative to high-fidelity
evidence, or when escalation gets cheaper. The loop scales as far as its
cheapest independent rejector, and no further.
:::

Three readings follow, and each was argued qualitatively in an earlier chapter.
First, generation is not the constraint. Cheap generation raises the candidate
count, which the bound ignores, and it does not raise $f$. This is
@sec-methods-generation-prediction-optimization restated as algebra, where a
generated artifact is a proposal and the loop speeds up only when something can
cheaply and independently reject it. Second, independence is load-bearing, not
decorative. Only a rejector that does not share the generator's blind spots
counts toward $f$. A cheap check coupled to the generator inflates the apparent
$f$ while real escapes survive, which is the failure
@sec-feedback-verification-trust warns against when a learned judge and a learned
generator quietly become the same witness. The honest $f$ counts only what a
cheap, independent, trusted instrument settles on its own. Third, $(1-f)$ is a floor. The
commitments that only silicon, deployment, or a human can settle set a ceiling on
loop throughput that no amount of cheap, abundant generation removes. It is
Amdahl's serial fraction, written for the design loop.

The bound is not only a way to talk; its variables are estimable on a real loop.
The fleet ISA migration earlier in this chapter gives one reading. Turned on the
broken-test repair slice the migration left behind, the automated repair tool
proposed fixes, and the cheap, independent instruments (build, test, sanitizers
that expose memory-model differences, and the production monitor) settled
roughly a third of those commitments without a human; the rest escalated to the
engineers who owned the code. That is an $f$ of about $0.3$, with a $(1-f)$ floor of
human-owned commitments, the shape the bound predicts. Progress tracked
the fraction the cheap, independent instruments could settle without a human, not
the number of fixes proposed. This estimates $f$ for that repair slice, not the
entire migration loop. One measured point is not a validated law, but it shows
the variables can be read off a deployed loop rather than only defined on paper.

The bound also makes the scissors gap of @sec-design-loop-no-longer-scales
computable. The gap widens precisely when one blade, the rate of proposals and
evidence demands, races ahead while the other blade, the rate at which trusted
feedback can reject, stays fixed. In these terms the gap is the regime where
candidate count climbs while $f$ does not, and the bound says throughput is flat
in exactly that direction. The loop families walked through this chapter are
operating points on the same curve. Fast software loops sit near high $f$, cheap
feedback, and low escalation, so they run quickly. High-commitment RTL and
physical-design loops sit near low $f$, expensive feedback, and high escalation,
which is why the method posture there shifts away from autonomous action toward
critique, evidence organization, and rejection. The bound derives that advice
rather than asserting it.

## What Transfers across Loops

Across all of these loops, the same ontology and the same bound transfer. Each
loop has a task, a representation, an environment, method roles, feedback,
evidence, rejection, and human decision. Each loop can preserve negative traces.
Each loop can be reviewed with the design-loop card. Each loop can fail by hiding
assumptions, optimizing a proxy, omitting provenance, or letting an output become
a decision too early.

What changes is the operating regime, which the rejection-bound relation gives
a compact way to name using the value of $f$, the cost ratio between cheap and
high-fidelity feedback, and the escalation overhead. Feedback latency changes. Reversibility changes. Action
validity changes. Data availability changes. Security and IP constraints change.
The cost of being wrong changes. Rejection authority changes. The acceptable
level of autonomy changes.

::: {#pri-change-autonomy .callout-design-principle title="Change autonomy with loop pattern"}
Autonomy is a property of the AI-assisted loop contract, not the AI model. Let the optimizer take more autonomous
action only where feedback is cheap, rollback is easy, and independent rejection
can stop bad actions. As commitments become expensive, irreversible, or
system-wide, shift the AI-assisted loop toward critique, evidence organization, rejection,
and human approval.
:::

This is the practical reason to keep this chapter in the book. It prevents
Architecture 2.0 from becoming either an abstract ontology or a paper survey.
The reader should be able to take a new project and ask these questions. Which loop pattern
is this? What feedback can it afford? What representation does it need? What
method roles are safe and useful? What can reject the result? What decision
must remain with the architect?

The next chapter turns that last question back toward professional judgment.
Once the loop can be described, instrumented, acted on, and checked, what does
the architect still own?

### Open research questions

The loop patterns outlined in this chapter define operating regimes, but operationalizing them across an entire discipline exposes several unsettled research directions. The following questions push beyond classifying loops to ask how their evidence and boundaries can be formalized at scale:

1. How do we construct a unified, cross-layer evidence corpus that outlives any single project?
   Building on the need for evidence ledgers in the Workload Characterization and Benchmark Construction section, the field needs a standardized schema to carry state from simulation to fleet deployment. This pushes beyond maintaining a local ledger to creating open, queryable databases of negative traces and rejected variants that future AI-assisted systems can learn from across the entire stack.

2. How do we empirically certify the false-pass rates of cheap rejection authorities?
   The throughput bound introduced in @sec-the-rejection-bound depends on the fraction $f$ of commitments a cheap rejector can settle. However, we have no systematic way to certify these instruments. Research must develop stress-testing methodologies to measure exactly when fast software loops or compiler checks silently pass system-breaking bugs that only expensive RTL simulation or fleet telemetry would catch.

3. Can we dynamically assign AI method postures based on real-time escalation costs?
   While @tbl-loop-patterns maps static method roles to specific loop patterns, future systems could dynamically shift an agent from a generator to a critic or repair tool based on observed feedback latency. This requires building matched task suites across the spectrum of loops to train AI models to recognize when their action space has become too risky, autonomously downshifting their own autonomy.

4. How do we formalize the expiration of architectural evidence across loop boundaries?
   As demonstrated by the co-evolution of hardware and software in @fig-hardware-software-coevolution, assumptions change rapidly. We need to define formal evidence-transfer protocols that can automatically invalidate architectural claims when a downstream dependency—like a compiler path or workload distribution—drifts, preventing AI-assisted systems from composing systems out of stale, incompatible proofs.

## What to carry forward
- Reader test: Which AI-assisted loop pattern are you in, and what cheap, independent
  check can actually reject the automated optimizer's result?
- Next loop state: Once AI-assisted loop patterns can be compared, the next question is
  what the architect still owns across all of them when delegating to AI.

[^fn-canary-deployment-c09]: **Canary deployment**: a controlled, partial rollout used to detect regressions before a system-wide release.
[^fn-tensor-program-optimizers-c09]: **Tensor-program optimizers**: methods that automate the search for efficient execution schedules of tensor operations on target hardware.
[^fn-service-level-objectives-c09]: **Service-level objectives (SLOs)**: target values for system reliability and performance, commonly used to manage operational tradeoffs [@BeyerEtAl2016SRE].
# What the Architect Owns {#sec-what-architect-owns}

```{=latex}
\abstract*{Architecture 2.0 changes the architect's work, but it does not remove the architect from the loop. This chapter returns to the opening moonshot and asks what remains nondelegable when AI-assisted systems, models, tools, and environments can participate in architecture work. The architect owns intent, abstraction, representation, evidence standards, rejection authority, accountability, and the final commitment; the field must build the shared infrastructure that makes those responsibilities comparable.}
```

::: {.callout-crux}
When automated participants, tools, and architecture environments can act inside the loop, what
stays the architect's to own, and what must the field share so ownership can be
compared?
:::

To answer those questions, consider the lighthouse prompt that opened the book. It
asked for a low-power, 64-bit RISC-V-based compute subsystem for real-time mobile
XR under a 3\ W target in a 3\ nm-class low-power mobile process. At the start of
the book, that prompt was a provocation.
It looked like a request for a future hardware foundation model[^fn-hardware-foundation-model-c10].
At this point, it should read differently. The prompt is not powerful because it is
short. It is powerful because it exposes a missing design loop.

That loop includes workload definition, architecture representation, tool
interfaces, compound method roles, feedback budgets, evidence ledgers,
rejection authority, and human decisions. It also exposes the central conclusion
of Architecture 2.0: AI systems do not eliminate the computer architect. They
change what the architect must own.

The architect's responsibility moves upward. Instead of owning every step of
manual artifact construction, the architect owns the framing of the problem,
the abstractions that make it tractable, the representations that make it
legible, the evidence standards that make it believable, the rejection authority
that makes it safe to use, and the commitment behind the final
decision. This is why Architecture 2.0 is not simply an automation story. It
is a responsibility story about loops in which AI-assisted systems can act but cannot own
the commitment.

That responsibility is sharper in hardware than in software. A generative model
or an automated optimizer does not sign a tapeout check, and unlike a software
defect that an overnight update can patch, a hardware bug ships in silicon,
where a respin costs millions of dollars and months of schedule. The architect
therefore has to own the commitment gate explicitly: the job shifts from
crafting the artifact by hand to standing behind the evidence that justifies
committing it, without ceasing to own the artifact's consequences.

::: {.callout-learning-objectives}
After this chapter you can draw the architect-owned commitment boundary for a
loop. That means you can:

- name which architecture responsibilities remain human-owned when automated tools act inside the loop;
- decide which state, evidence, rejection authority, and workload records a loop must expose before delegation is credible;
- answer the strongest objections to Architecture 2.0 without treating automation as ownership;
- identify the community infrastructure the field still needs for comparable, evidence-bearing loops;
- state why every field of the design-loop card ultimately resolves to an accountable human owner.
:::

## Return to the Moonshot

Return to the lighthouse prompt:

> Design a low-power, 64-bit RISC-V-based compute subsystem for an
> XRBench-class real-time mobile XR workload. Realize it as a vector-capable
> CPU, accelerator, or SoC block under a 3\ W TDP target in a 3\ nm-class LP
> mobile process, and return a design-space report with evidence and rejected
> alternatives.

::: {.callout-lighthouse title="The prompt hides interface contracts"}
Context. The opening request is not a single hardware specification. It
bundles workload, software, architecture, technology, and evidence obligations
that must be made explicit before an automated participant can act on them.

In the Lighthouse prompt. "XRBench-class real-time mobile XR workload"
creates an obligation to specify a workload distribution, quality-of-experience
target, benchmark version, traces, and software stack. For an automated system, this workload
obligation has to be represented as machine-readable data: scenario labels, trace
provenance, coverage limits, excluded cases, quality-of-experience labels, and
out-of-distribution rejection conditions. "64-bit RISC-V-based" means the AI loop
needs access to correct compiler toolchains, simulators, and instruction semantics,
rather than just generating text that looks like RISC-V. The fragment "vector-capable CPU,
accelerator, or SoC block" defines the system's allowed action space: the loop
must be given explicit rules about which integration paths it can explore and
which interfaces are fixed.

Evidence boundary. "3\ W TDP target" and "3\ nm-class LP mobile process"
create power, thermal, and physical-design constraints; an optimizer evaluating
candidates must not confuse a fast proxy average-power estimate with the sustained
thermal or signoff evidence required for a final commitment.

Takeaway. The architect-owned work is deciding which contracts are fixed,
which are exposed as actions to the automated tool, and which have enough evidence to support a
human commitment.
:::

![The Commitment Ladder: The evidence standard must rise as the cost of being wrong increases. A fast generative screen requires low evidence; a final silicon tapeout requires physical design closure. Each rung represents an architect-owned escalation threshold.](images/F10-commitment-ladder){#fig-commitment-ladder width="100%" fig-alt="Diagram of a ladder climbing through Design Space Report, RTL, Verified Implementation, and Tapeout-ready Design, with cost-of-being-wrong increasing."}

The requested deliverable also matters. A design-space report is different
from RTL. RTL is different from a verified implementation. A verified
implementation is completely different from a physically routable, timing-closed tapeout. (Logical correctness in RTL tells us nothing about whether power delivery, thermal bounds, and wire routing can physically close.) Each step changes the
evidence standard. The same prompt can support a brainstorming loop, a
research prototype, a simulator-backed design-space exploration, or a
high-commitment implementation loop. Treating all of those deliverables as
the same is one of the fastest ways to overclaim.

To avoid this overclaiming, the framework developed here turns the prompt into a
set of explicit questions:
What task is being solved? What representation is available? What world model
does the loop assume? What tools can the system act on? What method roles are
allowed? What feedback is affordable? What evidence would make the result
credible? What alternatives were rejected? Who can stop the loop? Who is
accountable for the decision?

Together, those questions define the part of
the design space the architect exposes to methods, tools, and AI-assisted systems. Choosing
what to expose is an architectural act. Expose too little and the loop cannot
find useful alternatives. Expose too much without constraints, evidence, and
rejection authority, and the loop can optimize the wrong object or cross a
commitment boundary before anyone understands what happened.

::: {.callout-architect-checkpoint title="The Exposure Gate"}
When defining an AI-loop's environment, check the boundary of exposed actions. Have you provided explicit constraints, evidence checks, and rejection authority for every knob the automated optimizer can turn? If not, it may optimize an invalid metric and cross a commitment boundary unnoticed.
:::

Enforcing those boundaries marks the shift from prompt to loop. The prompt
motivates the work. The loop makes the work inspectable.

The phrase *prompt-to-loop* is deliberately more durable than prompt-to-chip.
Prompt-to-chip asks whether a system can produce an impressive final artifact
from a sentence. Prompt-to-loop asks whether it can preserve the task, state,
tools, evidence, rejected alternatives, and human decision boundary that make the
next architectural commitment believable. The second question remains important
even after today's models and tools are obsolete.

## Nondelegable Architectural Responsibilities

Even the most explicitly defined, inspectable loop still leaves work the architect
cannot hand off, and nondelegable does not mean unaided. An architect can use
models, AI-assisted systems,
search procedures, simulators, compilers, profilers, EDA tools, benchmarks,
and critics. The point is narrower and more important. The architect cannot
transfer responsibility for the architectural judgment itself into a model.
Nor does responsibility become distributed simply because several automated participants divide
the work. Splitting a loop across these tools can make delegation more effective, but
it also creates more places where authority can become ambiguous. The architect
still has to decide which roles may act, which system or tool can stop another,
which evidence crosses an escalation threshold, and who owns the commitment when
the tools disagree or all agree for the wrong reason.

::: {.callout-architect-checkpoint title="The Multi-Agent Authority Gate"}
When splitting an architecture task across multiple automated participants, trace the rejection authority. Which system or tool is allowed to halt the process? What evidence crosses an escalation threshold back to a human? You must ensure that adding more participants does not diffuse final accountability.
:::

Because authority must not diffuse, the architect's responsibility becomes more
explicitly full-stack as automated tools enter the loop. A future architect may not be
only a CPU architect, accelerator
architect, compiler specialist, or physical-design expert. The nondelegable
work is composition across those boundaries: deciding which hardware knobs to
expose, which software contracts must remain stable, which workload scenarios
matter, which tool feedback has authority, and which deployment consequences
are acceptable. Automated systems can help operate pieces of the stack, but the architect
owns the decisions that connect those pieces into a defensible system
claim.

@fig-architect-owned-boundary separates assistable loop work from
the commitments the architect must own. Automated methods may help represent state, generate
candidates, evaluate proxies, call tools, critique results, summarize
evidence, and preserve provenance. Those are substantial contributions. But
they do not decide what problem matters, which abstraction is legitimate, what
evidence is enough, which failure is acceptable, when to reject a result, or
who answers for the consequences. An automated optimizer might tune a core's thermal profile,
for instance, but the architect owns the call if that profile melts the package
or breaks the product's safety certification. That line separates work a loop may assist from the commitments the architect
still owns: intent, abstraction, evidence standards, rejection authority,
deployment risk, and responsibility for consequences. It is the boundary the
rest of this chapter defends.

Read the figure as an ownership boundary: the loop can automate work inside the
boundary, but only the architect can accept the risk of crossing it.

![The architect owns the boundary of the loop: AI systems can assist many operations inside an Architecture 2.0 loop, but intent, abstraction, representation, evidence standards, rejection authority, accountability, and field-building remain architect-owned responsibilities.](images/F11-architect-owned-boundary){#fig-architect-owned-boundary width="100%" fig-alt="Boundary diagram showing which loop responsibilities can be assisted by AI systems and which remain owned by the architect."}

@tbl-architect-responsibilities turns this claim into a practical
review object. It is not meant to romanticize human judgment. Human judgment
can be biased, inconsistent, and incomplete. The reason it remains central is
that architecture decisions bind technical artifacts to organizational,
economic, ethical, and deployment consequences. A model can help reason about
those consequences, and a tool-using system can help surface them, but neither
owns them when the loop crosses a commitment boundary.

| Responsibility | Why it cannot be delegated | How AI can assist |
| --- | --- | --- |
| Intent and constraints | The loop must serve a real architectural objective, not merely an available benchmark or proxy. | Elicit missing constraints, surface conflicts, and compare formulations. |
| Abstraction and representation | The encoded state determines what the loop can see, optimize, ignore, or falsely simplify. | Translate artifacts, organize traces, find gaps, and suggest structured schemas. |
| Evidence standard | A result is useful only if the evidence matches the commitment level and cost of being wrong. | Build evidence ledgers, track provenance, estimate uncertainty, and summarize rejected runs. |
| Escalation thresholds | The moment when proxy evidence is no longer enough depends on risk, reversibility, blast radius, and organizational context. | Detect threshold crossings, surface missing evidence, and route decisions to review. |
| Rejection and commitment | Someone must decide when a candidate is invalid, too risky, insufficiently supported, or ready to use. | Critique assumptions, flag rule violations, and compare alternatives. |
| Accountability and boundaries | Architecture choices affect users, teams, IP, security, cost, reliability, and long-lived systems. | Maintain audit trails, identify policy conflicts, and make tradeoffs explicit. |

: Architect-owned responsibilities become explicit loop obligations: The architect must define intent, abstraction, constraints, evidence standards, rejection authority, escalation rules, and final commitment even when methods automate pieces of the loop. {#tbl-architect-responsibilities tbl-colwidths="[22,36,32]"}

Those responsibilities become easier to review when they are attached to
ordinary artifacts. @tbl-architect-owned-artifacts regroups them into the
concrete records a team can inspect: it surfaces environment and action
authority as its own row and folds escalation into the evidence standard and
accountability into rejection and commitment.

| Architect-owned responsibility | Inspectable artifact |
| --- | --- |
| Intent and constraints | Problem statement, non-goals, workload slice, hard constraints, and decision owner. |
| Abstraction and representation | Architecture schema, exposed design space, assumptions, hidden-state list, and redaction boundary. |
| Environment and action authority | Tool contract, legal actions, invalid-action rules, cost model, and provenance requirements. |
| Evidence standard | Fidelity ladder, calibration record, evidence ledger, and escalation threshold. |
| Rejection and commitment | Rejected-alternative log, review note, waiver record, commitment level, and rollback or next-evidence plan. |

: Architect-owned work should leave inspectable artifacts: Intent,
representation, environment authority, evidence standards, and commitment
decisions should be review records, not only expert intuition. {#tbl-architect-owned-artifacts tbl-colwidths="[30,58]"}

This boundary also clarifies the word **agentic**[^fn-agentic-system-c10]. The book is not arguing
that every architecture loop should become autonomous. Agentic systems are
useful because they can act inside represented loops: call tools, maintain
state, revise plans, use feedback, and coordinate method roles. But action is
not ownership. As loops become more capable, the architect's responsibility is
not reduced; it becomes more explicit.

::: {.callout-architect-checkpoint title="The Ownership Test"}
If an AI-assisted design loop proposes an invalid artifact, the review record must show who is accountable. Can you trace who defined the intent, who accepted the abstraction, who trusted the evidence, who had authority to reject the result, and who accepted the final commitment? If those human names disappear, the loop has not become more advanced; it has only hidden the architecture decision.
:::

## The Strongest Objections

This insistence on explicit human ownership is a strong stance, and a field-defining
claim should survive its sharpest critics, so it is worth stating the strongest
objections plainly.

The first objection is that Architecture 2.0 is just good experimental
methodology with new names. Provenance, baselines, rejection criteria, and
held-out validation[^fn-held-out-validation-c10] are not new; careful architects have always done them. The
response concedes the lineage and locates the difference. What changes is who
acts inside the loop and how fast. When a human runs the loop, tacit judgment
supplies the missing rigor: the architect remembers why a workload was excluded
or distrusts a proxy on instinct. When a method runs the loop at machine speed,
that tacit layer no longer makes the loop reviewable unless it is recorded, so
the discipline must be made explicit and machine-readable. Architecture 2.0 is
the claim that the methodology must become an engineered object, not a craft,
once automated tools participate. The book borrows
established forms deliberately: the evidence ledger is an assurance case
[@Kelly2004GSN], a discipline already mandatory in safety-critical domains such
as automotive functional safety, where a safety case must argue that a design
meets its requirements before it ships [@ISO2018Iso26262]; the fidelity ladder is
multi-fidelity modeling[^fn-multi-fidelity-modeling-c10] [@PeherstorferWillcoxGunzburger2018Multifidelity].
Naming the lineage is the point, not a weakness.

The second objection is that AI for systems design is overhyped, and the most
cited result, learned chip placement, is contested. That is true, and this book
treats it as evidence rather than embarrassment. The placement dispute in
@sec-feedback-verification-trust is exactly why the field needs reproducible, end-to-end benchmarks and
explicit rejection authority. An honest framework predicts that some flagship
results will not survive scrutiny; its value is a standard that makes the
difference visible.

The third objection is that the design-loop card is process bureaucracy that
will not survive a deadline. The card is not a mandatory form; it is a
diagnostic for loops where tools or automated participants can advance candidates faster than
reviewers can reconstruct the evidence. A team under deadline can fill it in a
few minutes and learn whether
its result rests on a proxy nobody validated or a baseline nobody documented.
The cost of skipping that check is paid later, at higher commitment, where it is
most expensive. The card earns its place only when it is shorter than the
mistake it prevents.

The fourth objection is that the framework is too conservative, preserving human
authority when the goal is to deploy more capable AI systems. Architecture 2.0
does not oppose automation; it places automation where it can be inspected,
rejected, and improved. A loop can be highly automated in low-commitment
exploration and deliberately conservative near signoff. The design principle is
not less automation. It is evidence-matched automation.

None of these objections is fatal, but each sharpens the claim. Architecture
2.0 is not the assertion that AI will design chips. It is the narrower, more
defensible claim that the design loop must become explicit enough to act on,
judge, and trust.

## Community Infrastructure for Architecture 2.0

Making the loop explicit within a single team is a start, but individual practice
is not enough to move a field. The ownership test names who
owned each decision inside one loop, but those names can only be compared across
loops when the field shares a record format that carries them. Agentic
architecture work becomes a field only when loops, not just artifacts, can be
compared, reproduced, criticized, taught, and extended. Architecture 2.0 therefore needs
community infrastructure, not only better private loops.

The infrastructure does not have to expose proprietary designs or internal
company data. It can start with shared conventions: design-loop cards,
paper-facing claim-card views, environment schemas, provenance records,
benchmark versions, negative traces, source records, tool-interface
descriptions, and review rubrics. These are small artifacts, but they change
what the community can ask of a claim. They let reviewers ask not only "What
result did you get?" but also "What loop produced it? What feedback did it use?
What did it reject? What evidence supports the decision?"

Providing a useful answer to those questions does not require raw design
disclosure. It requires a redacted evidence ledger: a small public record that
names the loop well enough for another group to
understand what was attempted, what was observed, what was rejected, and what
kind of commitment the evidence can support. @tbl-public-evidence-ledger gives
the minimum version. Anything less makes the claim hard to compare; anything
more may be impossible to share.

| Field | Public record | Why it matters |
| --- | --- | --- |
| Task and workload class | Workload family, scenario, benchmark or trace version, and excluded cases. | Prevents a result from being read as broader than the task that produced it. |
| Action-observation interface | What the loop could change, what it could observe, and which tools or environments returned feedback. | Makes the exposed design space inspectable. |
| Tool and model versions | Simulator, compiler, EDA flow, benchmark, model, and prompt or policy versions when they affect the result. | Makes drift and reproduction failures diagnosable. |
| Accepted and rejected candidates | A compact list of advanced candidates, rejected candidates, and the rule or evidence that separated them. | Turns negative traces into reusable evidence. |
| Evidence stages | Proxy, simulation, compiler/runtime, RTL, physical, silicon, or deployment feedback used, with fidelity limits. | Shows whether the evidence matches the claimed commitment. |
| Redaction and ownership | What was hidden, why it was hidden, and who owned the final decision. | Keeps IP boundaries explicit without hiding accountability. |

: A public evidence ledger should expose the loop, not the proprietary design: The minimum useful record names the task, interface, versions, candidates, evidence stages, redaction boundary, and accountable decision owner. {#tbl-public-evidence-ledger tbl-colwidths="[22,34,34]"}

A redacted record has a failure condition. If redaction hides the workload
class, action-observation interface, evidence stage, or decision owner, the
record may still provide context, but it should not be treated as comparable
loop evidence.

::: {.callout-architect-checkpoint title="The Redaction and Comparison Gate"}
Before publishing or sharing a redacted loop record, verify its failure condition: does it hide the workload class, action-observation interface, evidence stage, or decision owner? If any of these are missing, the record can provide context but cannot be treated as comparable evidence for an AI-mediated claim.
:::

When evaluating new benchmarks against this standard, read them by the loop fields
they expose, not by their names. ArchGym and QuArch, met earlier, contribute
environment/action interfaces
and question-to-evidence review tasks. Two further examples fill fields the
book has not yet seen instantiated: CircuitNet, an open dataset of
physical-design flow records, contributes design-flow data, and ChiPBench, the
end-to-end placement benchmark that grew out of the placement dispute
(@sec-feedback-verification-trust), contributes final power-performance-area
rejection against proxy wins
[@KrishnanEtAl2023ArchGym; @PrakashEtAl2025QuArch; @PrakashEtAl2025QuArchReasoning; @ChaiEtAl2022CircuitNet; @WangEtAl2025ChiPBench].
The common test is whether an AI-mediated architecture claim can show what
state it used, what it changed, what feedback it received, what failed, and who
owned the commitment.

The missing pieces are just as important. Architecture work rarely preserves
negative traces: failed runs, rejected candidates, invalid configurations,
stale benchmarks, bad proxies, tool errors, and ideas that were ruled out by
expert judgment. Yet these traces are exactly what an AI-assisted design loop
needs to learn from the field's failures rather than rediscover them. A
community that records only successful artifacts gives future systems a
distorted view of architecture practice.

Community infrastructure should also respect privacy and IP boundaries. The
goal is not to force every organization to publish internal traces. The goal
is to build schemas, examples, synthetic tasks, open benchmarks, redacted
records, and review artifacts that make credible loop design discussable.
That is how Architecture 2.0 can become a research area rather than a set of
private demos.

## Open research questions

Building this shared infrastructure and navigating the transition to AI-assisted architecture introduces several unsettled research directions that extend beyond the current capabilities of the field. For architect-owned work, the community must answer the following:

1. How can we formally verify redacted loop integrity? 
   Building on the public evidence ledger introduced in @tbl-public-evidence-ledger, we must explore whether cryptographic techniques like zero-knowledge proofs can guarantee that an automated optimizer's reported constraints and evidence ladder are authentic without leaking the underlying proprietary design IP.
2. Can models generalize from federated negative traces?
   While this chapter argues for treating rejected alternatives as evidence, it remains an open question how to train future methods on a shared corpus of negative traces across disparate organizations so that an AI loop can anticipate failures in a new domain while respecting the redaction and comparison gate.
3. Can evidence gates be synthesized dynamically under uncertainty?
   Expanding on the escalation rules and review artifacts detailed in @tbl-architect-responsibilities, future research must determine if environments can automatically generate and enforce context-aware rejection thresholds when an automated system encounters novel workloads, dynamically adjusting when human stop authority is invoked.
4. How is human accountability preserved across continuous drift?
   As introduced in the long-horizon challenge tasks (@fig-long-horizon-task-timeline), it is unclear how to securely re-verify the "named human owner" across asynchronous drift events (such as silent model updates or compiler changes) when the original decision maker is unavailable, necessitating new frameworks for long-term algorithmic liability.

## Long-Horizon Challenge Tasks

To answer these open questions, the field needs realistic evaluations. Short
demonstrations are useful for tool development, but they are too small
to define the field. A model that writes a plausible RTL fragment, proposes a
cache configuration, or summarizes a paper may be helpful without changing the
architecture loop. The harder question is whether an AI-mediated system can
participate in architecture work over the time scale on which architecture
decisions actually mature: days, weeks, months, tool versions, workload
updates, rejected alternatives, and design reviews.

> **Long-horizon architecture task.** A long-horizon architecture task is a
> challenge in which a method or AI-assisted system must maintain design state across
> multiple steps, act through valid tools or interfaces, gather feedback at
> appropriate fidelities, preserve rejected alternatives, expose uncertainty, and
> support a human architectural commitment over an extended design interval.

@fig-long-horizon-task-timeline shows the target shape. The task is long horizon
because the state, actions, evidence, rejections, and human commitment have to
survive across revisions, not because the prompt is longer.

![Long-horizon architecture tasks test the loop across time: A credible challenge preserves design state, acts through valid interfaces, gathers feedback at appropriate fidelity, records rejection or repair, and leaves a human able to accept, reject, or escalate the next commitment.](images/F11b-long-horizon-task-timeline){#fig-long-horizon-task-timeline width="100%" fig-alt="Timeline diagram showing a task slice, state memory, valid action, feedback, reject or repair step, and human commitment connected across a persistent loop record."}

This framing changes what the community should ask for. The canonical
challenge is not prompt-to-chip. It is prompt-to-loop: can a system preserve
enough state, evidence, and rejection history that an architect can trust the
next commitment? @tbl-long-horizon-challenges sketches a starting set of tasks.
The success criterion is whether the loop leaves a named human able to accept,
reject, or escalate that next commitment.
Each row names the paper object: a corpus or task source, the loop
representation or environment to build, the evidence and rejection gate to test,
and the commitment boundary the task may authorize.

| Challenge task | Corpus or task source | Representation / environment | Evidence and rejection gate | Commitment boundary |
| --- | --- | --- | --- | --- |
| Design-loop memory | Multi-step DSE traces, notebooks, and review decisions. | Replayable candidate records with assumptions, tool outputs, failures, decisions, and timestamps. | Reviewer reconstructs why each candidate advanced, changed, or was rejected. | Supports the next exploration decision, not implementation readiness. |
| Workload drift tracking | Benchmark or trace-family versions plus affected conclusions. | Workload-version monitor with coverage, stale assumptions, and revalidation actions. | Drift detector weakens or invalidates claims whose workload support changed. | Maintains or withdraws a bounded workload claim. |
| Evidence-aware generation | Candidate proposals paired with predicted benefit and feedback costs. | Generator constrained by an evidence-gate policy and escalation rule. | Cheapest independent rejection test catches unsupported proposals before expensive checks. | Suggests next evidence to spend, not final design commitment. |
| Paper-to-loop reproduction | Published claims, missing artifacts, assumed settings, and negative traces. | Paper-to-loop reproduction packet with task, environment, evidence, and falsification needs. | Independent reviewer states what would reproduce, weaken, or refute the claim. | Makes the paper auditable, not automatically reproducible. |
| Simulator trust calibration | Proxy and higher-fidelity runs across workload slices and tool versions. | Proxy-calibration record with support region, observed errors, and invalidation cases. | Escalation gate rejects proxy wins outside calibrated support. | Authorizes proxy screening inside the support region only. |
| Cross-stack co-design | Workload, compiler, mapping, memory, accelerator, runtime, and deployment changes. | Co-design card with layer owners, interface contracts, and changed assumptions. | Interface and system-objective gates reject local wins that break another layer. | Supports a bounded cross-layer claim with named owners. |
| Negative-trace corpus | Failed mappings, invalid RTL, bad floorplans, stale benchmarks, and misleading proxy wins. | Redacted failure corpus with trigger, evidence, rejected fix, redaction boundary, and reusable lesson. | Reuse test shows whether a new loop avoids or reopens the old failure correctly. | Treats rejected alternatives as evidence, not universal design rules. |
| Design-review assistant | Design-review notes, risks, missing evidence, sensitivity checks, and rejected alternatives. | Review packet organized by design-loop card fields and human decision owner. | Human veto and evidence-gap checks reject unsupported recommendations. | Improves review judgment without owning the commitment. |

: Long-horizon challenges should test architecture loops, not single prompts: The field needs tasks that reward memory, valid action, feedback, rejection, evidence, and architect-owned commitment across time. {#tbl-long-horizon-challenges tbl-colwidths="[15,21,22,23,19]"}

These challenges also give Architecture 2.0 a way to remain architecture
centric. A generic AI benchmark can reward answer fluency. A long-horizon
architecture challenge should reward state, interfaces, feedback economics,
evidence quality, and rejection. That is where the computer architecture
community has something specific to contribute.

## From Capability to Standard

Building those capabilities is one thing; turning one into a shared field
standard is another, and that path is gradual. The standard is not a governance
process for its own sake; it is a shared loop contract. Automated systems need comparable
action spaces, feedback contracts, workload/data boundaries, rejection logs,
leakage controls, and named human commitment owners so that a claim can be
inspected across labs without pretending every lab uses the same tools.

That progression should not be rushed. Premature standardization can freeze
weak tasks, reward narrow metrics, and encourage benchmark gaming. But the
opposite failure is also real. If every project defines its own task, wrapper,
metric, and evidence standard, the field cannot accumulate knowledge. The
right target is not a single universal benchmark. It is a family of
interfaces, cards, tasks, and evidence conventions that make claims comparable
without pretending all architecture work is the same.

A credible standard should make six things visible: the task/workload state,
the legal actions and observations, the versioned tools/models/data, the
evidence and rejected alternatives, the leakage/redaction boundary, and the
accountable human or gate that can stop or accept a commitment.

Architecture 2.0 will likely mature unevenly. Fast software loops may
standardize earlier than RTL and physical-design loops. Workload and benchmark
loops may become more public than industrial signoff loops. That unevenness is
acceptable. What matters is that the field learns how to name the loop and
state its evidence burden.

Different communities can start at different leverage points. @tbl-role-agenda
states the first useful artifact each group can contribute without waiting for a
complete field standard.

| Community | First useful artifact | Evidence or rejection obligation | First shared task |
| --- | --- | --- | --- |
| Practicing architects | A design-loop card attached to a design review or DSE report. | Name the workload, exposed design space, evidence stages, rejected alternatives, and decision owner. | Compare two candidate loops for the same design question. |
| ML researchers | A method report that states action space, observation space, training data, leakage risks, and failure cases. | Show what the method can reject, not only what it can generate. | Reproduce or stress-test an architecture claim with explicit missing evidence. |
| EDA and tool researchers | An environment contract for a simulator, compiler, or physical-design flow. | State legal actions, feedback latency, fidelity limits, provenance, and invalid actions. | Build a benchmark where proxy wins must survive a stronger tool check. |
| Systems researchers | A workload and deployment evidence ledger. | Track software stack, runtime policy, operating point, and drift. | Show when a local optimization stops supporting the end-to-end claim. |
| Authors and reviewers | An Architecture Claim Card attached to a paper claim. | Separate generated candidates from supported decisions. | Convert a result into task, representation, environment, method role, evidence, rejection, and commitment fields. |

: Architecture 2.0 needs role-specific starting points: The field can mature through small artifacts that make loops reviewable before any single benchmark becomes canonical. {#tbl-role-agenda tbl-colwidths="[18,28,30,24]"}

For a team that wants to start immediately, the minimum useful target is one
credible loop packet, not a process program. @tbl-minimum-credible-loop-packet
turns the field agenda into three artifacts a reviewer can inspect.

| Packet component | What to attach | Evidence that it worked |
| --- | --- | --- |
| Claim packet | A design-loop card for one active design review, DSE result, or paper discussion. | The team can name the task, exposed design space, evidence, rejected alternatives, commitment boundary, and decision owner. |
| Environment packet | One tool path wrapped as an environment contract with logged runs and invalid-action records. | A second person can replay or audit at least one successful run and one failed run. |
| Evidence packet | One shared evidence ledger or negative-trace format for a recurring architecture decision. | Future reviews reuse prior failures instead of rediscovering them, and claims state their commitment level. |

: Architecture 2.0 adoption starts with one credible loop packet: The first
goal is a repeatable artifact that makes one architecture decision easier to
inspect, reject, and improve. {#tbl-minimum-credible-loop-packet tbl-colwidths="[20,42,28]"}

## Loop Invariants as Review Checks

A first packet is where adoption starts; the design principles are how any loop,
including that packet, gets checked. Each chapter has contributed one such
principle, and together they test whether an AI-mediated loop has represented
workloads and state, bounded its actions, preserved provenance, gathered
evidence, rejected candidates, and assigned ownership. They are more useful than
a list of fashionable tools because they give reviewers, authors, and builders a
stable way to inspect new work.
@tbl-architecture-20-design-principles collects those principles as review
checks and pairs each one with the design challenge it leaves behind.

| Principle | Where it comes from | Design challenge to keep in mind |
| --- | --- | --- |
| Design the loop, not only the artifact. | @sec-moonshot | A prompt or generated artifact is not enough; the loop must expose state, action, feedback, rejection, and decision. |
| Treat feedback as the bottleneck. | @sec-design-loop-no-longer-scales | More candidates do not help if the loop cannot evaluate, reject, and justify them. |
| State the claim as a review object. | @sec-architecture-20-ontology | A result should name workload, baseline, design space, objective, constraints, evidence, rejection rule, and decision owner. |
| Make architecture work legible. | @sec-data-representations-world-models | Data must include provenance, assumptions, costs, failures, and negative traces, not only successful endpoints. |
| Turn tools into environments. | @sec-architecture-environments-tool-interfaces | A wrapper is credible only when it defines legal actions, observations, costs, invalid states, and rejection paths. |
| Match methods to roles. | @sec-methods-generation-prediction-optimization | A method should be chosen for the loop bottleneck it relieves, not for its reputation. |
| Escalate with commitment. | @sec-feedback-verification-trust | Evidence requirements should rise with rollback cost, blast radius, and independence of rejection authority. |
| Stop at an honest evidence level. | @sec-running-the-loop | A loop should report what its evidence supports, what it rejected, and what would overturn the decision. |
| The loop is rejection-bound, not generation-bound. | @sec-loop-patterns-across-stack | Fast software loops, co-design loops, systems loops, and silicon-facing loops scale only as far as their cheap independent rejectors. |
| Keep a human accountable. | @sec-what-architect-owns | A named owner must explain what was accepted, rejected, waived, and what would force revision. |

: Architecture 2.0 design principles are review checks: Each principle asks whether the loop has made enough of the architecture problem explicit for another architect to inspect, reject, reproduce, or extend it. {#tbl-architecture-20-design-principles tbl-colwidths="[24,20,46]"}

These principles are deliberately phrased as checks, not slogans. A reader
reviewing a paper can ask which principle is visible and which is missing. A
researcher building a tool can ask which principle the tool makes easier to
practice. A program committee, artifact committee, or internal review group can
apply the same checks to a new paper, environment, or design-review packet.

These principles also change what counts as a mature research contribution.
When the architect's work moves toward setting evidence standards, exercising
rejection authority, and judging what to trust under automation, papers should
make those obligations inspectable rather than treating them as process details
outside the contribution.

## Beyond the Current Loop

Mastering those review skills is what carries an architect past the current loop,
and the horizon beyond this book is not another autonomy level. It is the moment
when loops begin to improve their own representations, propose new tasks,
repair tool interfaces, organize negative traces, and recalibrate evidence
standards. That possibility is powerful, but it does not change the core
obligation. A loop that can adapt can also adapt toward benchmark gaming,
hidden failures, tool overfitting, or biased traces.

This matters most because the design target no longer holds still. When software
is continuously regenerated and retrained, as @sec-design-loop-no-longer-scales
argued and @sec-loop-patterns-across-stack showed at fleet scale, a specific
artifact ages as the workload it served moves on. The artifact remains the thing
committed at a point in time; the loop is the durable discipline for deciding
whether that commitment is still supported. What remains stable is how intent
is bounded, evidence is demanded, candidates are rejected, and commitment is
decided as the target moves.

The durable way to read emerging design assistants is therefore not by their
feature lists, which will change, but by the partition of design autonomy:
which decisions a human still makes, which decisions the loop may make within
stated bounds, and which decisions the loop is never allowed to make alone
[@ReddiYazdanbakhsh2025Architecture20]. That partition, not the autonomy label,
is what the architect must keep designing.

## The Architect's Standing Obligation

Designing that partition does not require a new instrument, because the
operational checklist already exists. The trust checklist in @sec-feedback-verification-trust and
the design-loop card and rubric in @sec-appendix-b-design-loop-card give it for a single claim and
for a whole project, and this chapter does not reprint them. The closing point
is narrower and harder to delegate: accountability. Every field on that card
ultimately resolves to a person who answers for the commitment. The card makes
the loop visible; the architect decides what the visible loop is allowed to do,
and owns the consequences when it is wrong.

That bar is intentionally modest. It does not claim that every Architecture 2.0
project must solve every problem in the field. It asks for something more basic
and more durable: make the loop visible, then keep a human accountable for it.
Once the loop is visible, the community can critique it, improve it, compare
it, reproduce it, and build on it.

That is the promise of Architecture 2.0. The field does not need to wait for a
single model that designs a computer from a sentence. It can start by changing
the unit of architectural practice: from isolated artifacts to represented,
instrumented, evidence-bearing design loops. The architect still owns the
judgment. The opportunity is to build loops worthy of that judgment.

::: {#pri-human-accountable .callout-design-principle title="Keep a human accountable"}
Every commitment needs a named human owner. The loop can make intent,
abstraction, evidence standards, rejection authority, and risk inspectable, but a
person must still be able to explain what was accepted, what was rejected, what
was waived, and what would force revision.
:::

## What to carry forward
- Public agenda: Build evidence ledgers, long-horizon loop challenges,
  environment contracts, design-loop cards, and negative-trace corpora that let
  the field compare loops rather than admire isolated demos.
- Reader test: If the loop is wrong, who can explain what happened, what
  should have rejected it, and who accepted the commitment?
- Standing obligation: Make the loop visible enough that the community can
  critique, compare, reproduce, and improve it.

## Final Thoughts: Engineering Discipline in a Fast-Moving Field

When this book opened with the lighthouse prompt---asking a generative method to generate an entire XR subsystem from a text description---it may have sounded like a prediction that the human architect's job was ending. The framework developed across these chapters argues the exact opposite. 

The tools, models, and automated systems driving this shift are changing at breakneck speed, and any catalog of today's capabilities will quickly become obsolete. Because this transition is a massive work in progress, the one durable anchor is engineering discipline. We are crossing the threshold from *artifact scarcity* to *commitment scarcity*. When generating a plausible accelerator or floorplan becomes fast and cheap, the bottleneck shifts to the loop that produced it. 

Architecture 2.0 is not about trusting machines more. It is about building loops that earn our trust. The AI-assisted system can generate, predict, and optimize, but only the human architect can accept the risk and sign their name to the final commitment. The task ahead is not to wait for an AI that can design a computer from a single sentence. It is to enforce the engineering discipline, the evidence standards, and the rejection boundaries that make those AI-assisted claims credible. The loop is now the architecture.

[^fn-hardware-foundation-model-c10]: **Hardware foundation model**: a foundation model is a large-scale machine learning model trained on a vast quantity of data that can be adapted to a wide range of downstream tasks; a hardware foundation model would apply this approach to hardware design representations.
[^fn-agentic-system-c10]: **Agentic system**: an AI system capable of pursuing complex goals over time, making its own decisions about which tools to use and what steps to take next.
[^fn-held-out-validation-c10]: **Held-out validation**: in machine learning, the practice of reserving a portion of the dataset during training exclusively for evaluating a model's performance on unseen data.
[^fn-multi-fidelity-modeling-c10]: **Multi-fidelity modeling**: an optimization technique that combines cheap, low-accuracy simulations with expensive, high-accuracy simulations to explore a design space efficiently.
