# Architecture 2.0 Manuscript Audit and Improvement Plan

## Status

This document records the next content milestone for *Architecture 2.0*. The
current clean checkpoint is commit `285a3f70`, which closes the eleven-chapter
semantic citation audit and its source corrections. The approved chapter and
section architecture is the working contract. The next milestone should
improve the current manuscript rather than rebuild it from a clean slate.
Proposed structural or substantive changes return to the author for review
before they enter a chapter.

The milestone focuses on content, technical grounding, narrative flow,
research questions, and explanatory visuals. It does not begin a page-budget,
layout, slide-deck, or production-polish pass.

The next execution goal has not started. This plan records its scope and order
so the author can review them first.

## North Star

*Architecture 2.0* should become the compact, durable introduction that
graduate students, researchers, and practitioners read to understand how AI can
assist system and chip design.

The book begins with architecture problems rather than AI products. It should
teach readers how to:

1. formulate a consequential design question;
2. understand where AI assistance may or may not help;
3. organize the design work;
4. build and represent the required data and project knowledge;
5. choose among conventional methods, prediction, generation, optimization, or
   combinations;
6. connect those methods to real design tools;
7. use feedback and verification to establish what a result supports;
8. run a complete study;
9. determine what transfers to a changed problem;
10. evaluate the architecture result and the contribution of AI separately;
    and
11. understand what architects and their organizations still decide and own.

The lecture should remain useful as models, agents, tools, and benchmarks
change. It should establish a small number of transferable principles rather
than become an encyclopedia or a catalog of current systems.

## Decisions Already Reached

### Terminology

- *AI-assisted system and chip design* names the engineering activity.
- *AI-assisted design system* provisionally names the complete mechanism used
  to perform that activity.
- *Architecture foundation model* names a broadly trained learned component
  that may supply reusable knowledge, representations, prediction, or
  generation.
- *Agent* or *controller* names a component that chooses actions, invokes
  tools, or revises a plan.
- The complete design system may contain one foundation model, several
  specialized models, or no foundation model.
- Do not use *foundation system* as a formal term unless the literature review
  establishes a recognized meaning that improves clarity.
- Do not use `PGO` for prediction, generation, and optimization. Compiler
  readers already associate that acronym with profile-guided optimization.
  Use the full names or *the three method families*.

The central terminology distinction belongs in Chapter 1 after the Lighthouse
request has exposed the full-stack design problem. It should not be
front-loaded into the preface or hidden in a footnote. Later chapters should
explain the components progressively rather than making Chapter 1 preview the
whole book.

### Method-Selection Guide

Chapter 5 should contain a pedagogical decision guide. It should begin with the
architecture bottleneck rather than assume a fixed order among prediction,
generation, and optimization.

The guide should ask:

1. What architecture decision must be made?
2. Which objectives, constraints, and comparisons determine that decision?
3. Can a conventional algorithm, solver, heuristic, compiler analysis,
   simulator, or formal method answer it adequately?
4. Is the limiting work candidate construction, outcome estimation, search and
   selection, evaluation capacity, verification, or missing information?
5. Does the proposed method have the required data, representation, feedback,
   support, and tool path?
6. What baseline and check could expose a bad result?
7. When should the work stop or conclude that AI is not useful?

The resulting branches should remain plain:

- Consider generation when constructing useful, legal candidates is the
  bottleneck.
- Consider prediction when obtaining outcomes from faithful tools is too
  expensive.
- Consider optimization when selecting among alternatives or allocating a
  limited evaluation budget is the bottleneck.
- Improve checks, measurement, and verification when confidence is the
  bottleneck.
- Use a conventional method or no AI when it reaches the required result more
  directly or reliably.
- Combine methods only when their distinct jobs and interfaces are clear.

The guide should not imply that every problem passes through the three method
families in one order.

## Candidate-to-Decision Capacity Model

### Purpose

AI can increase the rate at which design candidates are proposed without
increasing the rate at which candidates can be evaluated, verified, reviewed,
and converted into supported architecture decisions. A first-order capacity
model can make that bottleneck concrete.

The model is not a complete theory of architecture design. It does not
determine whether the team framed the right problem, represented the right
relationships, or selected the right objectives. It explains only how work
moves through a sequence of costly checks and where queues form.

### Placement Options and Current Recommendation

The model should be visible enough to become a reusable analytical lens without
forcing queueing theory into the book's opening. Four placements require
comparison:

1. a full treatment in Chapter 2, where evaluation and verification capacity
   first become explicit;
2. a full treatment in Chapter 3, where the life cycle exposes distinct stages,
   costs, and return paths;
3. a compact introduction in the main text with the derivation and extensions
   in an appendix; and
4. a distributed treatment that introduces one idea at a time and later
   reconnects them.

The current recommendation combines the third and fourth options:

- Chapter 1 states only that candidate-production rate and
  supported-decision rate are different.
- Chapter 2 establishes the qualitative mismatch between candidate production
  and evaluation or verification capacity. It should explain that assistance
  can relieve or worsen the active bottleneck without introducing the full
  derivation.
- Chapter 3 orients the reader to where candidate work, tool use, return paths,
  and stopping occur. It should state explicitly that life-cycle
  responsibilities are not serial queueing stations.
- Chapter 5 owns the analytical model inside its discussion of result economics
  and feedback budgets. The model gives the method-selection guide a
  quantitative bottleneck diagnosis.
- The Chapter 5 treatment includes the governing quantities, the load
  condition, and a small checked example. It should remain understandable
  without reading the appendix.
- Chapter 6 explains which run records are needed to estimate service time,
  retries, queueing, and resource contention.
- Chapter 7 connects capacity with check quality, uncertainty, and correlated
  failure.
- Chapter 8 uses observed counts and durations only if they reveal a real
  bottleneck in the worked study.
- Chapter 9 explains why capacities, routing, and observed survival fractions
  must be re-estimated after a problem changes.
- Chapter 10 uses time and total cost per supported decision as evaluation
  metrics.
- An appendix develops the derivation, measurement worksheet, parallel stages,
  branching and return paths, variable processing times, false acceptance and
  false rejection, sensitivity, and a more complete worked calculation.

The expert panel should pressure-test this placement before prose is drafted.
The complete derivation should not be repeated across chapters, and the
appendix should extend the argument rather than hold the only substantive
explanation.

### Relation to Design Methods and Checks

The capacity model describes functions in the design process rather than one
fixed AI pipeline:

- a generative or conventional method may produce candidates;
- a predictive or analytical method may estimate outcomes or screen
  candidates;
- an optimizer may select candidates or allocate a limited measurement budget;
- simulators, implementation tools, formal methods, tests, and reviewers check
  different properties; and
- the architect uses the qualified comparisons to make a decision.

These functions may appear in a different order, run in parallel, repeat, or be
absent. Verification is not a fourth learned-method family. It is the set of
checks that determines which claims a result can support.

### First-Order Model

Let:

- \(g\) be the candidate-generation rate;
- \(p_i\) be the observed or assumed conditional fraction of candidates that
  survive checking stage \(i\) among candidates that reach it;
- \(c_i\) be the number of parallel slots at stage \(i\), such as machines,
  tool licenses, or review slots;
- \(t_i\) be the mean processing time for one candidate at stage \(i\); and
- \(\mu_i\) be the processing capacity of stage \(i\).

The processing capacity is:

\[
\mu_i = \frac{c_i}{t_i}.
\]

The offered load at stage \(i\) is:

\[
\lambda_i =
g \times \prod_{j=1}^{i-1} p_j.
\]

The stage utilization is:

\[
\rho_i = \frac{\lambda_i}{\mu_i}.
\]

A first-order load check requires \(\rho_i < 1\) at every stage. This condition
is necessary for the simple model and is not a guarantee of finite expected
delay under arbitrary arrival and service distributions. Equality is not an
adequate operating target because small variations can create a growing delay.
The corresponding first-order upper bound on the input rate is:

\[
g <
\min_i
\left(
\frac{\mu_i}
{\prod_{j=1}^{i-1} p_j}
\right).
\]

If all stages remain within their load bounds, the expected finalist-output
rate after \(m\) stages is:

\[
q =
g \times \prod_{i=1}^{m} p_i.
\]

A supported architecture decision may require several finalists, a matched
baseline, additional checks, and architect review. Therefore, \(q\) is not
architecture-decision throughput or end-to-end latency. The product of the
survival fractions describes flow attrition and is not the probability that a
surviving candidate is correct.

### Checked Illustrative Example

Assume a system proposes \(g = 32\) candidates per day:

| **Stage** | **Parallel slots \(c_i\)** | **Mean service time \(t_i\)** | **Capacity \(\mu_i\)** | **Conditional survival \(p_i\)** |
| --- | ---: | ---: | ---: | ---: |
| Structural and legality screen | \(1\) | \(1\) minute | \(1{,}440\)/day | \(0.25\) |
| Cycle-level simulation | \(4\) | \(8\) hours | \(12\)/day | \(0.10\) |
| Implementation screening | \(1\) | \(24\) hours | \(1\)/day | \(0.50\) |

The first-order input-rate limits are:

| **Stage constraint** | **Calculation** | **Maximum input rate** |
| --- | ---: | ---: |
| Structural screen | \(1{,}440\) | \(1{,}440\)/day |
| Cycle-level simulation | \(12 / 0.25\) | \(48\)/day |
| Implementation screening | \(1 / (0.25 \times 0.10)\) | \(40\)/day |

Implementation screening forms the bottleneck. A rate of \(40\) candidates/day
would operate it at full utilization, so the example instead uses \(32\)
candidates/day and leaves 20 percent headroom at that stage.

The resulting offered loads are:

| **Stage** | **Calculation** | **Offered load** | **Utilization** |
| --- | --- | ---: | ---: |
| Structural screen | \(32\) | \(32\)/day | \(32/1{,}440 = 2.2\%\) |
| Cycle-level simulation | \(32 \times 0.25\) | \(8\)/day | \(8/12 = 66.7\%\) |
| Implementation screening | \(32 \times 0.25 \times 0.10\) | \(0.8\)/day | \(0.8/1 = 80\%\) |

The finalist-output rate is:

\[
32 \times 0.25 \times 0.10 \times 0.50
= 0.40
\]

finalists/day, or one finalist every 2.5 days in steady-state output. This does
not mean that one candidate's end-to-end turnaround is 2.5 days. The first
candidate already requires its screening, simulation, and implementation
service times before queueing delay. A supported decision still requires
comparison, verification, and review.

Increasing generation to \(60\) candidates/day would not increase supported
decision throughput. Simulation would receive \(60 \times 0.25 = 15\)
candidates/day despite having capacity for only \(12\). Even when simulation
is saturated, its output would offer approximately
\(12 \times 0.10 = 1.2\) candidates/day to an implementation stage that can
process only \(1\). Both queues would grow.

The eight-hour simulation and one-day implementation values are illustrative.
The literature and data audit should seek public runtime anchors, and the final
example should be generated from executable calculations rather than
hand-maintained derived values.

### Required Extensions and Limits

The chapter should explain the limits without burying the simple model:

- Parallel checks may form a network rather than a single linear sequence.
- A candidate may return to an earlier stage after revision.
- Processing times and survival fractions may vary by candidate.
- Shared licenses, machines, and reviewers create coupled queues.
- Early checks can reject good candidates as well as bad candidates.
- A method may optimize the proxy used for screening and exploit its blind
  spots.
- One architecture decision may require several qualified candidates and a
  common baseline.
- Check capacity does not replace judgment about objectives, tradeoffs, and
  residual risk.

The most important extension is the tradeoff between early rejection and false
rejection. A filter that improves throughput by discarding every unusual design
can eliminate the best candidate. Later chapters should connect capacity to
coverage, uncertainty, and decision quality.

### Runtime and Source Audit

Do not use one generic “simulation time.” Architecture studies use checks with
different setup costs, fidelities, parallelism, and reuse:

- analytical and learned estimates;
- trace-driven, event-driven, and cycle-level simulation;
- software compilation and execution;
- RTL simulation and formal analysis;
- synthesis, place and route, timing, power, and design-rule checks; and
- FPGA or silicon measurement.

Before the illustrative values enter the manuscript, assemble a source packet
for representative checks. Record:

| **Field** | **Why it matters** |
| --- | --- |
| Tool and version | Tool behavior and performance change over time. |
| Check or study performed | “Simulation” alone does not identify the work. |
| Workload, warm-up, and sample length | Runtime depends strongly on how much execution is modeled. |
| Model or implementation fidelity | A fast estimate and a detailed implementation answer different questions. |
| Host resources and parallel slots | Service time and total capacity are not the same quantity. |
| Setup, compile, and reuse assumptions | Cached artifacts can dominate comparisons. |
| Wall-clock time and compute consumption | Queue capacity and total resource cost need both. |
| Source and reproduction status | Public evidence must be distinguishable from an illustrative assumption. |

The main-text example may use rounded representative values once their
interpretive limits are explicit. The appendix should include at least one
source-backed scenario and a worksheet readers can replace with measurements
from their own environment.

The literature audit should also test whether the simple model should cite or
borrow from established work on queueing networks, heavy-traffic delay,
sequential experimental design, value of information, optimal computing-budget
allocation, computer experiments, multistage inspection, and common-cause
failure. These connections should sharpen the model without turning the
chapter into a queueing-theory survey.

### Figure Candidate

A candidate figure would show candidate proposals entering a sequence of
increasingly expensive checks. Each stage would display capacity, survival
fraction, and the offered load passed forward. A visible queue would appear at
the first overloaded stage. A second path would show how better screening,
prediction, prioritization, or increased tool capacity can relieve the
bottleneck.

The figure should be conceptual until the literature and data audit determines
whether a source-backed quantitative version is possible.

## Candidate Synthesis Lenses

The audit should test these ideas rather than insert them automatically.

### Candidate Abundance and Validation Scarcity

AI can make proposals abundant while measurement, verification, and architect
attention remain scarce. The useful quantity is not generated candidates per
hour. It is the time and total cost required to reach a supported architecture
decision.

### Two Design Spaces

Architecture work operates over both:

1. the design space of hardware, software, mapping, implementation, and system
   alternatives; and
2. the experimental design space of which candidate, workload, tool, fidelity,
   measurement, or check should receive the next unit of budget.

The second space connects architecture design to active learning, experimental
design, systems identification, and sequential decision-making. The lecture
should borrow only the principles needed to improve architecture work.

### Architecture Data Is Produced Through Interventions

Architecture data often exists because a team selected a design, workload,
tool, fidelity, and operating condition and then paid to run an experiment.
The selection policy shapes the dataset. Failed jobs, rejected candidates, and
unpublished designs may be censored or missing.

Chapter 4 should explain the resulting selection bias, uneven coverage, sample
cost, and feedback between a method and the data it later learns from without
becoming a generic data-engineering chapter.

### Learned Similarity and Exact Meaning

Learned representations can support similarity, retrieval, prediction, and
generation. Exact architecture facts such as units, hierarchy, connectivity,
ordering, interfaces, legality, and timing relationships still need forms that
tools and reviewers can check.

The durable lesson is to preserve exact design facts before adding learned
representations. Embeddings are one representation, not the definition of
representation.

### Different Sources of Authority

The audit should preserve four distinct contributions:

| **Source** | **Contribution** | **Cannot establish alone** |
| --- | --- | --- |
| Broadly trained model | Reusable prior knowledge, patterns, and learned representations | Current project facts or physical correctness |
| Current project state | Specifications, versions, constraints, workloads, and permitted changes | Measured behavior of a candidate |
| Tools and checks | Observed behavior, implementation results, proofs, and failures under stated conditions | Whether the tradeoff justifies commitment |
| Architect and organization | Interpretation, priorities, residual-risk judgment, and commitment | Permission to ignore unsupported technical claims |

This distinction should guide the Chapter 1 foundation-model figure and later
chapters. It should not become a new branded framework.

### Generalization of Claims

Chapter 9 should ask whether an architecture conclusion remains valid after
the workload, software, hardware, tools, process assumptions, or deployment
conditions change. Model transfer is only one part of that problem.

### Separate Evaluation of Outcome and Assistance

Chapter 10 should continue to evaluate:

1. whether the work produced a better architecture result; and
2. whether AI improved the result, reduced the total cost of reaching a
   comparable result, or both.

A sound architecture can emerge from an unhelpful AI workflow. An efficient AI
workflow can produce an inadequate architecture. The two judgments must remain
separate.

## Chapter and Section Audit

### Book-Level Question

The first audit asks whether the eleven chapters still form the right
cumulative argument:

> set the moonshot, explain why assistance is worth investigating, organize the
> work, build the data and representations, choose methods, create
> tool-connected environments, obtain trustworthy feedback, run the complete
> study, determine what generalizes, evaluate and red-team the complete system,
> and define the architect's role.

No chapter should enter detailed revision if its unique job or position remains
unresolved.

### Chapter Review Matrix

| **Chapter** | **Unique job** | **Special audit focus** |
| --- | --- | --- |
| 1. Moonshot | Establish the ambitious capability and expand the Lighthouse request into a full-stack architecture problem | Opening pace, prompt versus specification, foundation-model figure, terminology, broad research agenda |
| 2. Why assistance | Explain the compounding pressures and where assistance might help | Historical build-up, technology scaling, evaluation and verification scarcity, qualitative capacity mismatch, transition to AI assistance |
| 3. Life cycle | Explain how to organize AI-assisted design and why each stage exists | Tacit knowledge, progressive introduction of the stages, iteration and stopping, avoiding process bureaucracy |
| 4. Data, knowledge, and representation | Explain what an AI-assisted architecture process must know, why architectural data is difficult to produce, and how that data becomes usable knowledge and representations | Architecture-specific sources and interventions, sample cost, failures and censoring, exact and learned representations, embeddings, current project state |
| 5. Methods | Teach when and how to use prediction, generation, optimization, conventional methods, or combinations | Concrete methods, roles versus families, candidate-to-decision capacity model, bottleneck-driven decision guide, feedback cost, no fixed ordering |
| 6. Environments | Define what a tool-connected design environment must provide | Tool versus wrapper versus harness versus environment, state, interfaces, runtime, failures, cost, reproducibility |
| 7. Feedback | Explain how tool returns become qualified feedback and how checks change the work | Formal and empirical scope, uncertainty, proxy failure, independent checks, allocation of check capacity |
| 8. Complete study | Show the XR Lighthouse study operating end to end | Reproducible reasoning, honest failures, matched budgets, complete cost, stopping, sufficient technical detail |
| 9. Generalization | Explain what transfers, what adapts, and what must be re-established | Claim validity, distribution shift, versioned dependencies, robustness, avoiding a miscellaneous pattern list |
| 10. Evaluation | Evaluate the complete design system and red-team its assumptions | Architecture outcome, AI contribution, total cost, tool and simulation calls, reliability, attacks, benchmark health |
| 11. Architect's role | Explain what architects still contribute, decide, and own | Broad field implications, authority, residual risk, responsibility, forward-looking research agenda |

### Section-Level Questions

Every section receives an explicit audit:

1. What reader question opens the section?
2. What one teaching job must it perform?
3. Which two to five points establish that lesson?
4. What source, example, measurement, war story, figure, or table grounds it?
5. What belongs elsewhere?
6. Does the section explain difficult material before summarizing it?
7. What does the reader understand at the end that makes the next section
   necessary?

Each current section receives one status:

- **Complete.** It performs its intended job.
- **Partial.** It contains useful material but needs reframing or expansion.
- **Missing.** No current section performs a necessary job.
- **Move.** The material belongs elsewhere.
- **Combine.** Two sections substantially repeat the same work.
- **Remove.** The material does not advance a necessary chapter goal.

Surface keyword matches do not establish completion. Reviewers must read the
argument.

## Technical Grounding Audit

A section counts as technically grounded only when it provides:

- a clear architecture question;
- a concrete mechanism, example, or engineering consequence;
- support for factual, historical, and empirical claims;
- an explicit distinction among source-backed fact, author synthesis,
  inference, and speculation;
- realistic data, tool, fidelity, cost, implementation, and verification
  assumptions;
- a credible conventional alternative where one exists;
- stated limits and failure conditions; and
- enough detail for an architect to understand what would need to be built,
  measured, or checked.

Technical grounding is not citation density. A paragraph can contain several
citations and still fail to explain the mechanism. Another paragraph may
present a useful author synthesis without claiming that a source established
it.

### Expert Panel

Each chapter receives fresh, independent reviews from:

- a computer architect;
- an EDA, physical-design, and verification expert;
- an ML systems researcher; and
- a research advisor and pedagogy reviewer.

Chapter-specific secondary lenses should be added where needed:

- architecture measurement, data systems, and representation learning for
  Chapter 4;
- optimization and experimental design for Chapter 5;
- systems infrastructure for Chapter 6;
- formal methods, reliability, and safety for Chapter 7;
- experimental methodology for Chapter 8;
- MLOps, robustness, and configuration management for Chapter 9;
- benchmarking, security, and adversarial evaluation for Chapter 10; and
- organizations, responsibility, and human factors for Chapter 11.

Reviewers return structured findings rather than chapter rewrites. Every
finding must state:

1. what is already covered;
2. what is genuinely missing;
3. why the missing idea matters to the chapter's job;
4. the exact section where it belongs;
5. whether a short addition is sufficient or an author decision is required;
6. what literature, measurement, example, or visual would support it; and
7. what the reviewer deliberately left unchanged.

Major findings receive an independent skeptical review. A recommendation does
not enter the manuscript merely because one reviewer proposed it.

### Chapter 4 Boundary

Chapter 4 should not teach a generic data-engineering curriculum. Its
organizing question is:

> What makes architectural data difficult, and what must an architect do so
> that an AI-assisted design process can learn from it and act on it?

The chapter should begin with the properties of architecture work that create
the data problem:

- measurements are produced by deliberate tool runs and interventions rather
  than found as abundant independent examples;
- one sample may consume substantial simulator time, implementation time,
  licenses, machines, or engineer attention;
- workloads, tool versions, process assumptions, configurations, and design
  hierarchies give every observation a specific scope;
- failed, timed-out, censored, and rejected runs carry architectural
  information and cannot disappear from the record;
- related designs and workload derivatives create leakage that random
  train/test splits do not expose;
- fidelity varies from analytical estimates and learned surrogates to
  cycle-level simulation, implementation, formal checks, and silicon; and
- exact design meaning often lives in structured artifacts and relationships
  that a learned embedding alone does not preserve.

Data acquisition, cleaning, provenance, splitting, versioning, and
representation belong only where they answer one of those architecture
problems. Explain the minimum adjacent-field idea needed for an architecture
reader, apply it immediately to an architecture artifact or measurement, and
state the engineering consequence. Do not reproduce a general lesson on ETL
pipelines, data frames, storage systems, or generic model training.

An architecture student should leave with enough background to reason about
the problem, not with the impression that this chapter replaces a course in
data engineering or machine learning. When a standard technique needs fuller
treatment, use a brief explanation and point to an authoritative source such
as the relevant MLSysBook.ai chapter. The main text must remain understandable
without following the link.

The Chapter 4 review should therefore include two complementary readers:

1. an architect who tests whether every data concept is motivated by an
   architecture decision, tool, cost, or failure mode; and
2. an ML or data-systems reader who checks that the condensed explanation is
   technically sound and does not omit a prerequisite needed to understand the
   architecture consequence.

The chapter fails this boundary if it reads like a generic data-engineering
chapter with architecture examples substituted for ordinary datasets. It also
fails if it assumes that architecture readers already understand acquisition
bias, leakage, censored observations, learned representations, and embedding
limits.

## Research-Question Audit

### Reader Test

Each question should let a graduate student see the beginning of a serious
research project. A strong program committee should recognize the unresolved
problem and the possible contribution.

The private venue calibration should include:

- ISCA, MICRO, HPCA, ASPLOS, and IISWC for architecture and system questions;
- DAC, ICCAD, DATE, CAV, and FMCAD for EDA, implementation, and verification;
- NeurIPS, ICML, and MLSys for learning, representation, calibration,
  generalization, infrastructure, and evaluation; and
- PLDI and CGO where compiler or programming-system questions dominate.

Venue names should not appear beside questions in the manuscript.

### Required Tests

Every question should have:

- a specific unresolved gap;
- a plausible first experiment;
- a measurable or falsifiable outcome;
- novelty beyond routine engineering;
- clear ownership by the current chapter;
- no duplicate in another chapter;
- accessible wording; and
- one or two sentences explaining why the problem remains open.

Questions should open a research direction without turning into mini-proposals.

### Format

Research themes should not be `###` subsections. Use a standalone bold theme
label followed by two or three questions:

```markdown
**Building Architecture Datasets**

**How should an AI-assisted study allocate a limited data-acquisition
budget...?** Explanation of why the question remains open.

**How can failed and censored runs contribute useful training
information...?** Explanation of why the question remains open.
```

Aim for two or three themes and three to five questions per chapter.
If a theme supports only one strong question, merge it with another theme or
remove it rather than manufacture a weak second question.

The research agenda should open broadly in Chapter 1, become more technical
through the middle chapters, and widen again in Chapter 11.

## Narrative-Flow Audit

The narrative pass should test reader experience rather than merely search for
transition words.

### Chapter Openings

- Does the opening explain why the chapter exists before introducing its
  framework?
- Does it begin at a level the intended reader can enter?
- Does it stand on its own without depending heavily on the previous chapter?
- Does it build toward technical terminology rather than front-load it?
- Does it move steadily into the first section rather than abruptly changing
  subjects?

### Section Flow

- Does each section answer a question created by what came before?
- Are difficult ideas explained before a table, figure, taxonomy, or checklist
  summarizes them?
- Are examples introduced where they clarify a concept rather than where they
  interrupt it?
- Does each paragraph develop, support, qualify, or connect the section's
  point?
- Does the chapter deepen steadily rather than lose technical substance in its
  later sections?
- Does the conclusion recover the chapter's central argument and prepare the
  next chapter without simply listing headings?

### Fresh-Reader Strategy

Use two independent reading modes:

1. **Full-chapter readers** judge internal pace, progressive explanation, and
   section transitions.
2. **Boundary readers** receive only the end of one chapter and the beginning
   of the next. They judge whether the handoff is natural without being
   influenced by the full manuscript.

Detailed sentence polishing begins only after technical content and section
structure are accepted.

## Figure and Table Audit

### Explanatory Integration

Every figure and table should answer:

1. What question does it help the reader answer?
2. What claim does it teach?
3. Has the prose established the problem before the visual appears?
4. Does the prose explain the relationship that matters?
5. Does the caption state the takeaway and remain understandable on its own?
6. Are every number, source, and derivation traceable?
7. Would prose teach the point more clearly?
8. Does the visual arrive at the right moment in the chapter?

The current manuscript contains 25 directional instructions such as “read from
left to right” or “read from top to bottom.” Review each one individually.

- Retain a short spatial cue only when the visual has a genuinely non-obvious
  path, such as a life cycle whose return path runs in the opposite direction.
- Replace eye-movement instructions with an explanation of the relationship
  whenever possible.
- Do not ask readers to infer the value of a visual unaided.

For example, replace “Read each row from left to right” with an explanation
such as:

> Each row connects one phrase in the request to the decisions it leaves open
> and the checks that could reject a candidate. Together, the rows show why
> the prompt is a starting point rather than a specification.

### Comparison With the Local Dev Version

Create a complete visual inventory against the local `dev` checkout before
declaring that the current manuscript has the right visual support:

- figures present in `dev` but absent from the working manuscript;
- figures still present as files but no longer referenced;
- figures whose explanatory idea survived only as prose;
- figures that changed meaning, data, or scope;
- tables and listings removed or materially condensed; and
- visuals whose old concept remains useful even when the old execution or style
  should not return.

Do not restore a figure merely because it once existed. Classify each candidate
as:

- restore as-is;
- recover the idea and redraw;
- recover the data and replot;
- retain the current replacement;
- defer pending a source or permissions check; or
- leave removed.

The initial comparison identifies a small set of high-value candidates:

| **Candidate** | **Initial disposition** | **Reason** |
| --- | --- | --- |
| Dev Chapter 9 review-bottleneck figure | Recover the idea and redraw | It directly supports the candidate-to-decision capacity argument, but it should expand beyond human review to staged checks, survival fractions, and service capacity. |
| Dev Chapter 5 verification-lifecycle figure | Review for recovery | Its distinction among pass, repair, critique, and human escalation may clarify how checks affect the flow without treating verification as a single terminal stage. |
| Dev Chapter 6 cheap-to-expensive checking funnel | Review for recovery or replacement | A staged checking figure may help, but the old drug-discovery analogy should return only if it remains accurate and useful for architecture readers. |
| Dev Chapter 2 bottleneck causal loop | Review as a possible replacement | It may complement the scissors argument, but adding it beside the existing figure and diagnostic table would overload the section. |
| Dev Chapter 1 automation timeline | Retain only if it replaces the current progression figure | The two visuals perform substantially the same historical teaching job. |
| Dev Chapter 10 quantitative-looking concept plots | Leave removed unless supported by traceable data | Illustrative geometry should not be presented as measured evidence. |

The comparison also found materially different versions of shared figures in
Chapters 3, 4, 6, 7, 8, and 11. These require semantic comparison, not file
restoration. In several cases the current figure preserves distinctions that
the dev version collapses, such as separating a run's status from whether a
design is adopted.

The initial count also identifies where visual additions would be most risky:

| **Chapter** | **Current figures/tables/listings** | **Initial pacing concern** |
| --- | ---: | --- |
| 1 | 5 / 4 / 0 | Already full; a recovered history figure should replace rather than supplement. |
| 2 | 12 / 3 / 0 | Figure-heavy; test section-level clustering before adding anything. |
| 3 | 5 / 4 / 0 | Balanced by count; audit meaning and placement. |
| 4 | 4 / 10 / 0 | Table-heavy; inspect two dense clusters in the rendered flow. |
| 5 | 7 / 10 / 0 | Densest chapter; the capacity model may require replacing or consolidating an existing device. |
| 6 | 3 / 6 / 0 | Has room for one distinct argument figure if it earns the space. |
| 7 | 4 / 7 / 0 | A new figure should replace rather than simply supplement nearby material. |
| 8 | 4 / 7 / 0 | Similar balance to dev; judge by worked-study flow. |
| 9 | 5 / 6 / 0 | Do not restore the much denser dev figure set wholesale. |
| 10 | 3 / 8 / 0 | Table-heavy; prefer a strong replacement to an additional summary grid. |
| 11 | 2 / 5 / 0 | Tables already carry much of the argument; another opener is optional. |

Counts are a screening device, not a target. The rendered page and the
teaching job determine whether a chapter is balanced.

### Whole-Book Media Balance

Run a dedicated pass across figures, tables, listings, equations, and callouts.
The purpose is reader pacing rather than equal counts per chapter.

Check:

- whether a chapter opens with enough explanation before its first dense
  visual;
- whether several figures, tables, or listings arrive without prose between
  them;
- whether a long abstract stretch needs one clarifying example or visual;
- whether a table duplicates prose instead of improving comparison;
- whether a listing teaches a mechanism that prose alone cannot show;
- whether repeated callouts interrupt the main argument;
- whether each visual appears close to the passage that needs it;
- whether captions and surrounding prose divide the explanatory work cleanly;
  and
- whether the overall rhythm gives readers time to absorb one representation
  before the next appears.

Do not solve imbalance by adding decorative figures or deleting useful
technical material. The pass should improve explanatory pacing and the match
between the idea and its representation.

### Chapter 1 Foundation-Model Figure

Recover the earlier figure and its source material from repository history and
the talk slides. Preserve the useful idea rather than restoring an image
automatically.

The proposed durable figure should distinguish:

1. broad architecture data used to learn reusable knowledge;
2. an optional architecture foundation model adapted to several tasks;
3. current project facts and constraints;
4. specialized learned and conventional methods;
5. real tools and checks; and
6. architect interpretation and commitment.

The figure must not imply that one foundation model converts a prompt directly
into a correct chip. Approve the conceptual sketch and caption before drawing
the SVG.

### Quantitative Figure Search

Search for plots that clarify a durable claim and can be built from traceable
data. Candidate areas include:

- candidate production versus evaluation and verification capacity;
- public architecture-data attrition and sample cost;
- tool-call, simulation, implementation, and human-review cost;
- false acceptance and false rejection across staged checks;
- benchmark decay, contamination, or changing support;
- model or method performance under changed workloads, tools, or design
  conditions; and
- the difference between architecture-result quality and AI contribution.

Do not force one quantitative plot into every chapter. Reject a plot if its
data is weak, incomparable, proprietary, or likely to age without teaching a
durable principle.

### SVG and Visual-System Gate

Before drawing any new SVG:

1. read the complete project rules for figure invention, SVG layout, visual
   style, captions, and permissions;
2. approve a text sketch of the intellectual content;
3. reuse the established rectangular boxes, typography, colors, line weights,
   arrowheads, spacing, and alignment;
4. avoid introducing a second visual language for one figure;
5. render and inspect the result at publication size; and
6. verify that the prose and caption explain the accepted visual.

## Context-Preserving Review Process

The book-level editor should maintain only a compact working map:

- chapter goal;
- section jobs;
- accepted terminology;
- cross-chapter dependencies;
- approved changes; and
- open author decisions.

Each independent reviewer should receive:

- one complete chapter;
- that chapter's approved goal;
- its section map;
- the assigned panel role; and
- only the standards relevant to that review.

Reviewers should not receive the entire conversation, unrelated chapters, or
other reviewers' conclusions. Fresh readers should not know what earlier
readers thought was wrong.

The editor should synthesize structured findings and load only the exact
passages needed to resolve a finding. Cross-book audits should use compact
packets such as chapter openings and conclusions, section headings and
handoffs, research questions, and figure or table introductions.

This process protects fresh perspectives while keeping one editor responsible
for the book-wide argument and the seams between chapters.

### Expert Panel Review Process

Maintain one canonical expert-panel workflow for chapter-level technical
review. It should define:

- a stable core panel consisting of computer architecture, EDA and
  verification, ML systems, and research-advisor or pedagogy perspectives;
- rotating specialists within those areas when a chapter requires memory,
  interconnect, compilers, physical design, formal methods, data engineering,
  optimization, security, or organizations expertise;
- one fresh chapter read per reviewer;
- structured findings rather than automatic rewrites;
- an explicit statement of what the reviewer left unchanged;
- a skeptical review for consequential recommendations;
- an author triage gate before manuscript edits;
- separate narrative-flow and media-balance passes; and
- a compact handoff that lets the book-level editor preserve the larger
  argument without loading every review transcript.

The private review workflow implementation should have one owner for each job:
book architecture, chapter-level technical review, fresh-reader clarity,
narrative flow, manuscript-artifact balance, chapter development, and prose
editing. Overlapping implementations should route to that owner. Duplicate
instructions should be merged, and stale variants should be retired only after
confirming that no unique guardrail would be lost.

### Senior-to-Student Review Spiral

Review should progressively narrow its unit of attention. Each layer has a
different job and should receive only the context needed for that job.

1. **Book-level senior review.** Senior architecture, ML-systems, EDA and
   verification, systems, and pedagogy readers judge the thesis, chapter
   sequence, omissions, duplication, and whether the lecture establishes a
   useful perspective for the field.
2. **Chapter-level senior review.** Chapter-specific experts judge the
   chapter's technical substance, boundaries, reader capability, and place in
   the cumulative argument.
3. **Chapter-level fresh-reader review.** A graduate student or practitioner
   reads the complete chapter without seeing prior findings and reports what
   claim, method, and capability they actually derived.
4. **Section-level reader review.** A reader receives the section plus the end
   of the preceding section and beginning of the following section. The review
   tests orientation, teaching sequence, examples, transitions, and whether
   the section performs its assigned job.
5. **Paragraph-window review.** A reader examines contextual windows of two or
   three paragraphs and identifies missing reasoning steps, topic jumps,
   undefined terms, unsupported conclusions, and prose that merely announces
   an outline.
6. **Continuous student read.** After accepted repairs, a fresh student reads
   the chapter continuously and marks every point where they become confused,
   infer the wrong relationship, or must reread to recover the argument.

The spiral moves inward only after the broader layer is accepted. Paragraph
polish cannot repair a chapter with the wrong job, and a smooth section cannot
compensate for a missing technical concept.

Each review cycle follows one controlled path:

1. independent readers produce findings without editing manuscript files;
2. the book-level editor consolidates and adjudicates the findings against the
   approved chapter and section jobs;
3. one editor applies the accepted changes to a chapter;
4. a fresh reader checks the revised result without seeing the diagnosis;
5. the book-level editor inspects the diff and the chapter seams; and
6. the coherent milestone is committed before another layer begins.

Parallel agents are appropriate for independent reading, local `dev`
comparison, literature packets, artifact audits, and skeptical review. They
should not edit the same chapter concurrently. This division protects the
book-level editor's context and keeps independent reviewers fresh while
leaving one accountable editor for terminology, cross-chapter boundaries, and
narrative continuity.

The spiral is iterative rather than a one-time cascade. A section-level review
may reveal a chapter-level omission, and a continuous student read may expose
a book-level promise that was never paid. Such findings move back to the
appropriate broader layer before local polishing resumes.

## Tonight's Proposed Execution Plan

Tonight's goal should produce a content-lock candidate, not a final laid-out
book. The work proceeds in the following order.

### Stage 1. Freeze the Review Contract

- Update the compact chapter and section job packets from the approved plan.
- Record protected material, settled terminology, open author decisions, and
  explicit non-goals.
- Give every reviewer the same acceptance criteria without giving them prior
  diagnoses.

**Checkpoint:** The packets are internally consistent and do not reopen the
approved eleven-chapter sequence.

### Stage 2. Recover Before Rewriting

- Compare every current chapter with local `Arch2`/`dev` at the idea and
  explanatory-artifact level.
- Classify earlier material as retained, intentionally replaced, valuable and
  missing, redundant, or requiring author judgment.
- Pay special attention to explanations around figures and tables, historical
  framing, sample cost and data acquisition, concrete method descriptions,
  environment components, verification, and the technical depth of Chapters
  7 through 11.

**Checkpoint:** Produce one compact recovery matrix. Do not restore material
solely because it existed before.

### Stage 3. Review the Highest-Risk Chapters First

- Run independent chapter-level reviews for Chapters 4, 7, 8, 9, 10, and 11.
- Use Chapter 4's architecture-first boundary.
- Resolve Chapter 7's scope among feedback, verification, learning, drift, and
  supervision.
- Confirm that Chapter 8 is the detailed XR Lighthouse integration chapter.
- Test Chapters 9 through 11 for the late-book loss of technical depth.
- Adjudicate and implement accepted changes with one editor per chapter.

**Checkpoint:** Commit each coherent chapter revision separately, especially
Chapters 4, 7, and 8.

### Stage 4. Review and Repair the Remaining Chapters

- Apply the same review standard to Chapters 1, 2, 3, 5, and 6.
- Begin Chapter 5 with the three parked senior-review reports, adjudicating
  rather than automatically accepting them.
- Repair rushed openings, duplicated previews, and cross-chapter boundary
  problems without rebuilding chapters that already land.

**Checkpoint:** Every chapter performs its approved job and preserves valuable
existing material.

### Stage 5. Run the Reader Spiral

- Run complete-chapter fresh-reader reviews.
- Run section-level reviews with neighboring boundaries.
- Repair reasoning and teaching order before sentence rhythm.
- Run paragraph-window reviews only on sections that remain rough.
- Finish with continuous student reads of the revised chapters.

**Checkpoint:** Fresh readers recover each chapter's intended claim and reader
capability without seeing its outline or prior review reports.

### Stage 6. Audit Supporting Structures

- Revise research questions under two or three themes with three to five
  serious questions per chapter.
- Audit every figure, table, listing, equation, callout, war story, and
  Lighthouse use for explanatory value and pacing.
- Remove gratuitous eye-movement instructions.
- Identify quantitative figure opportunities, but do not invent data or begin
  a major visual redesign.
- Audit design principles and retain only principles earned by the chapter.

**Checkpoint:** Supporting structures advance the argument rather than
interrupting or decorating it.

### Stage 7. Whole-Book and Prose Pass

- Read chapter openings, conclusions, and boundaries as one sequence.
- Check that chapters stand alone while building naturally.
- Check learning objectives, terminology, acronyms, preambles, and repeated
  phrases.
- Run an anti-template prose pass only after content and flow are stable.
- Give Chapters 7 through 11 extra scrutiny rather than spending the strongest
  attention only on the opening chapters.

**Checkpoint:** The book has one recognizable technical voice without sounding
mechanically uniform.

### Stage 8. Content-Lock Report

- Produce a chapter-by-chapter matrix for chapter jobs, section jobs,
  technical grounding, flow, research questions, media, citations,
  Lighthouse use, war stories, and design principles.
- Mark each item complete, acceptable but improvable, blocking, or not
  applicable.
- Separate remaining quantitative, visual, layout, and production work into a
  later milestone.

**Checkpoint:** No unresolved chapter-level blocker, accidental deletion,
unsupported quantitative claim, or unexplained artifact remains.

The PDF build, page-level visual QA, slide deck, and major quantitative-plot
milestone begin only after this content-lock assessment.

## Milestones and Approval Gates

### Milestone 0. Baseline and Inventory

- Record the clean baseline commit.
- Inventory all chapters, sections, figures, tables, callouts, research
  questions, citations, and existing quantitative data.
- Compare the working manuscript with the local `dev` version and repository
  history where earlier material may have been lost.
- Produce a specific inventory of removed, unused, replaced, and materially
  changed figures, tables, and listings.
- Produce compact review packets.

**Gate:** Confirm that the inventory is complete before starting content
judgments.

### Milestone 1. Book and Chapter Architecture

- Verify the eleven-chapter sequence.
- Confirm the unique job, entry state, exit state, and handoff of every
  chapter.
- Identify unpaid book-wide promises, duplication, and missing capabilities.
- Revisit parked structural decisions without changing prose.

**Gate:** The author resolves any recommendation to retarget, merge, split,
move, or remove a chapter.

### Milestone 2. Section and Technical Depth

- Audit every section against its teaching job.
- Run the independent expert reviews.
- Identify missing technical concepts, weak mechanisms, unsupported claims,
  and material at the wrong altitude.
- Give Chapters 4 through 11 the same depth of review as Chapters 1 through 3.
- Compare useful material with the local `dev` version before declaring a gap.

**Gate:** Present one consolidated chapter-by-chapter report. Do not inject
proposed prose before author triage.

### Milestone 3. Terminology and Conceptual Models

- Resolve the final term for the complete AI-assisted design mechanism.
- Pressure-test the candidate-to-decision capacity model.
- Review the mathematical assumptions and illustrative calculation.
- Decide what Chapters 1 through 3 preview, what Chapter 5 must teach, what
  Chapters 6 through 10 reuse, and what the appendix extends.
- Decide whether the model earns a figure, a table, or both.
- Finalize the Chapter 5 method-selection guide.
- Determine which candidate synthesis lenses are already supported by the
  manuscript.

**Gate:** Approve the concepts and placements before drafting chapter prose or
SVGs.

### Milestone 4. Research Questions

- Generate and review a larger candidate pool for each chapter.
- Group questions under the right themes.
- Apply the publishability and venue-fit tests privately.
- Deduplicate across chapters.
- Convert theme subsections to bold labels.
- Preserve the broad-to-technical-to-broad book-wide progression.

**Gate:** The author selects the final themes and questions.

### Milestone 5. Narrative Flow

- Audit every chapter opening.
- Audit transitions between sections.
- Audit the handoff between adjacent chapters.
- Check progressive introduction of terminology.
- Identify rushed, front-loaded, repetitive, or under-explained passages.
- Perform paragraph-level smoothing only after structural findings are
  accepted.

**Gate:** Fresh readers should recover each chapter's intended claim and reader
capability from the body without seeing the opening summary or conclusion.

### Milestone 6. Figures, Tables, and Quantitative Grounding

- Audit every figure and table in context.
- Audit listings, equations, and callouts as part of the same reader-pacing
  pass.
- Replace gratuitous directional instructions.
- Compare the current visual program with local `dev` and recover useful
  concepts that were lost.
- Recover and redesign the Chapter 1 foundation-model figure.
- Propose the candidate-capacity figure.
- Identify missing conceptual and quantitative visuals.
- Verify data, calculations, captions, permissions, and explanatory prose.

**Gate:** Approve every new figure concept and data source before drawing or
integrating it.

### Milestone 7. Approved Content Changes

- Apply only accepted section and paragraph changes.
- Preserve untouched prose.
- Use the simplest professional architecture language.
- Avoid unfamiliar coined terms, branded frameworks, and current-product
  dependence.
- Keep the Lighthouse example concrete without forcing it into every section.
- Add only sourced, relevant war stories.

**Gate:** Review the diff after each chapter or coherent cross-book pass.

### Milestone 8. Re-Audit and Validation

- Re-run technical and skeptical reviews on changed passages.
- Re-run the narrative-flow and chapter-boundary checks.
- Verify citations and source support.
- Verify cross-references, figures, tables, footnotes, and research-question
  formatting.
- Run repository content checks and tests.
- Build and inspect the PDF only after the content milestone is accepted.

**Gate:** The manuscript should have no unresolved content blocker before
layout and production work begins.

## Commit Plan

Create a clean commit after each accepted major step:

1. baseline inventory and audit report;
2. terminology and conceptual-model decisions;
3. research-question restructuring;
4. accepted chapter-content changes, preferably one chapter or one coherent
   cross-book issue per commit;
5. narrative-flow improvements;
6. figure and table explanations;
7. new source-backed figures and data receipts;
8. final content validation.

Do not mix speculative drafts, generated review reports, and accepted
manuscript prose in one commit.

## Parked Author Decisions

The audit should revisit these items without changing them automatically:

- whether Chapter 1's large “An Artifact Is Not an Architecture Result”
  section needs a different hierarchy;
- whether “The Lighthouse Run Report” in Chapter 6 should become a primary
  section;
- whether Chapter 7 needs one concrete example of drift, suspension, refresh,
  and readmission;
- which phrasing should become Chapter 11's canonical closing design
  principle;
- which documented cases can support war stories in Chapters 4, 5, and 11;
- whether the candidate-capacity model should follow the current distributed
  recommendation with its main teaching home in Chapter 5 and its extensions
  in an appendix;
- whether the foundation-model figure should be one two-panel figure or two
  separate figures; and
- which existing expert-panel and editorial workflows should be merged,
  updated, or retired after their uncommitted drafts are reconciled.

## Deferred Work

The following work begins only after content acceptance:

- page-budget reconciliation;
- PDF layout and page-flow polish;
- final typography and float placement;
- a full presentation deck;
- production packaging; and
- broad website adaptation.

### Future empirical companion: one runnable architecture study

- Develop one canonical, publicly runnable study only after the current text
  content stabilizes. Package the pinned workload, software, architecture
  configuration, tool versions, execution scripts, checks, expected artifacts,
  and result records in a reproducible container or equivalent open bundle.
- The study should exercise the complete teaching path: formulate a decision,
  define the legal design space, build or select the data and representations,
  choose a conventional or AI-assisted method, invoke real tools, retain
  failures and costs, qualify the returned measurements, revise or stop, and
  state the supported architecture conclusion.
- Prefer a problem that can run with openly available tools and finish within a
  realistic teaching budget. A smaller cross-layer study that genuinely runs
  is more valuable than a nominally complete Lighthouse implementation whose
  physical or software claims cannot be checked.
- Keep the scope honest. The runnable study may instantiate part of the
  Lighthouse system without claiming to realize the full prompt-to-system
  moonshot.
- Treat the container, run records, and derived plots as a companion artifact,
  not as evidence until the exact released version has been executed and its
  results independently checked.

### Mining prior Architecture 2.0 talks

- Review the author's talk slides as a source-discovery and visual-idea corpus,
  not as manuscript-ready evidence.
- Candidate ideas to assess include increasing design-space complexity and chip
  cost; the expense and limited volume of cycle-level data; method selection
  under problem suitability, deployment constraints, and data availability;
  tool-connected environments; verification, generalization, reliability, and
  cost metrics; QuArch dataset construction and topic distribution; skills
  required of architecture agents; agents across the computing stack; and the
  architecture foundation-model question.
- For every candidate, recover the primary paper or underlying data, determine
  the chapter that owns the lesson, and decide whether prose, a table, a new
  source-backed plot, or no inclusion teaches it best.
- Do not reproduce slide screenshots or dense talk graphics directly. Redraw
  only the small number of concepts or quantitative results that survive source
  validation, manuscript scope, permissions, and the book's visual system.

## Author Feedback Queue: August 3, 2026

This queue records the current feedback before any manuscript edits begin. The
items should be reconciled as coherent chapter or book-wide decisions rather
than applied as isolated sentence changes.

### Chapter 2: sequence, pacing, and recurring elements

- Separate Figures 2.2 and 2.3 in the source narrative. They currently arrive
  too close together under the specialization discussion. Move a figure only
  when its new location gives it a clearer teaching job; do not add filler prose
  merely to create space.
- Rename *Wafer-Scale Systems* to *Wafer-Scale Computing*.
- Reconsider the chapter sequence so that wafer-scale computing closes the
  chip-side scale discussion, the chapter then develops design-space and
  software complexity, and warehouse-scale computing follows as the point at
  which hardware, software, networking, power, cooling, deployment, and
  operation must be understood together.
- Expand *Warehouse-Scale Computing and Distributed Systems*. It currently
  moves too quickly through a system scale that should synthesize the preceding
  sources of complexity. The expansion must remain relevant to the chapter's
  job: explaining why AI assistance may help as coupled architecture work
  becomes harder to inspect and settle.
- Re-audit the Chapter 2 open questions. Each theme and question should be
  immediately legible, architecture-centered, and concrete enough to suggest a
  credible research program. Choose the actor precisely—architect, research
  team, project, or system—instead of mechanically repeating *architecture
  team*.
- Repair the Chapter 2 design-principle callout so that it follows the same
  semantic structure as the rest of the book.

### Chapter 3: the Lighthouse teaching role

- Resolve the apparent inconsistency between Lighthouse callouts and ordinary
  body prose such as “For the XR study, Explore produces two candidates.” The
  reader should be able to tell why a Lighthouse detail is boxed in one place
  and embedded in the narrative in another.
- Decide the book-wide Lighthouse rule before revising Chapter 3. Apply the
  resulting rule to every chapter rather than fixing individual mentions in
  isolation.
- Consider promoting the design-loop card into a dedicated H2 section. The
  section must explain the card's job, why the normal collection of project
  artifacts does not by itself give another architect a compact account of the
  work, and how the card points into existing records rather than replacing
  project-management, version-control, experiment-tracking, or EDA systems.
- Ground the motivation for a reviewable design record in established practice
  from adjacent fields. Model cards, dataset documentation, experiment
  tracking, reproducibility records, safety cases, and engineering change
  control are candidate precedents to investigate, not a predetermined reading
  list. The synthesis should explain which failure each practice addressed and
  which parts transfer to architecture work.
- Strengthen the lightest life-cycle stage sections uniformly. For each stage,
  establish its architecture question, expected output, characteristic failure,
  and handoff to the next responsibility. Use the Lighthouse only when it adds
  a concrete architecture example rather than merely repeating the stage name.
- Consider an open question about allocating AI roles: when one component can
  perform several roles, when distinct components or agents should be assigned
  separate roles, and what evidence could compare those organizations. Place
  the final question in the chapter that owns role selection rather than adding
  it to Chapter 3 merely as a preview.

### Book-wide Lighthouse rule to approve

The working recommendation is:

- Body prose may make a brief Lighthouse reference when one sentence grounds
  the concept being taught and the paragraph remains understandable without
  the example.
- A Lighthouse callout should contain a self-contained application of the
  chapter's idea: the relevant design context, the concrete choice or artifact,
  what assistance does, and what remains to be measured or checked.
- Named study identifiers, candidate settings, multi-step worked details, and
  chapter-specific Lighthouse outputs belong in a callout or a dedicated
  Lighthouse application section, not scattered through ordinary prose.
- A callout should not be a wall of text. Use a small number of stable, bold
  semantic labels when they genuinely fit, provisionally *Context*, *Use of
  assistance*, and *Required checks*. Do not force every callout to have the
  same number of paragraphs.
- Ordinary prose should introduce or interpret the callout. It should not
  duplicate the callout's contents.
- The Lighthouse is an anchor for transfer and continuity, not a second
  narrative running beside the chapter.

### Book-wide Lighthouse coverage audit

- Audit the complete Lighthouse path across the manuscript. The compact XR
  request implicates the workload and application, software and compiler path,
  ISA and microarchitecture, memory hierarchy and interconnect, accelerator or
  SoC composition, physical limits, reliability, security, and verification.
- Do not let the cache-capacity study become a proxy for the entire moonshot.
  It may remain one deliberately narrow worked decision, but other chapters
  should select examples that expose the part of the stack they teach.
- Use architecture examples such as ISA or vector support, memory behavior,
  compiler/code generation, SoC interfaces, reliability, and verification only
  where they advance the local chapter argument. Do not force every subsystem
  into every chapter.
- Preserve traceability to the same workload, requirements, interfaces, and
  physical target across examples so that the Lighthouse remains one coherent
  system problem rather than a collection of unrelated anecdotes.
- Before implementation, produce a chapter-by-chapter coverage map showing
  which Lighthouse obligation each chapter develops, where the obligation is
  introduced, and whether it appears in prose, a callout, a figure, a table, or
  the worked study.

### Book-wide design-principle consistency

- Audit every design-principle callout after the content pass.
- Preserve one visual and semantic hierarchy: a short principle name followed
  by one or more bold, actionable statements with concise explanation.
- Do not force the same number of statements in every chapter. Consistency
  should make the principles recognizable and independently usable, not make
  them mechanically identical.
- Verify that every principle follows from the chapter, transfers beyond the
  Lighthouse example, and does not merely summarize the conclusion.

### Book-wide figure, table, listing, and cross-reference pass

- Inventory every conceptual SVG and identify ordinary boxes that use rounded
  corners. Convert them to sharp-corner rectangles unless a non-rectangular
  shape carries a specific meaning. Exclude protected brand assets named in the
  visual-system rules.
- Inspect shared SVG generators and templates before fixing individual assets;
  correct the shared source when one rule caused repeated rounded corners.
- Audit every figure, table, and listing in its local prose context. The prose
  must state the relationship, comparison, sequence, result, limitation, or
  inference that makes the object useful. A caption cannot carry that entire
  teaching job.
- Remove empty float announcements such as “Figure X shows” or “Table Y
  summarizes.” Lead with the architectural claim and let the cross-reference
  support it.
- Do not replace empty announcements with mechanical viewing instructions.
  Explain the content rather than telling the reader to look left, right, or
  top to bottom, except when spatial order itself is the substantive point.
- For a central figure, check the complete three-part integration: introduce
  the relationship before the figure, interpret the important relationships
  after it, and state the inference that carries into the next passage.
- Treat tables similarly: explain the comparison or reusable structure and the
  conclusion the reader should draw without narrating columns.
- Produce a findings ledger before editing. Record missing references, thin
  explanations, redundant prose, style violations, and figures or tables that
  do not earn their page space.

### Chapter 4: architecture data and learned representations

- Bring in durable lessons from important ML datasets and dataset research,
  but teach each lesson through an architecture failure or design need. Topics
  to investigate include documentation, label and metadata errors, leakage,
  contamination, dataset shift, licensing, private data, missing failures,
  and synthetic-data limits.
- Do not turn the chapter into a generic data-engineering tutorial. State the
  necessary ML practice compactly, then develop what changes when observations
  come from simulators, RTL, EDA tools, prototypes, silicon, workload traces,
  software, and restricted project records.
- Separate three concepts that the current prose may blur:
  1. a source artifact or observation, such as a trace, report, netlist, or
     simulation return;
  2. an explicit architecture representation, such as a schema, graph, typed
     intermediate form, feature vector, token sequence, or spatial encoding;
  3. a learned representation, including an embedding, that a model learns or
     adapts for retrieval, comparison, prediction, generation, or reasoning.
- Do not define *representation* as synonymous with *embedding*. Embeddings are
  one learned form; the architecture problem often requires explicit legal
  structure, units, provenance, interfaces, and invariants that a latent vector
  alone does not preserve.
- Revisit the quantitative contrast between the data available for general
  foundation models and the much smaller, fragmented, proprietary, and costly
  architecture corpora. Recover an earlier plot or construct a new one only if
  its quantities have traceable sources and the comparison is genuinely
  commensurate. Do not invent a dramatic volume ratio.
- Explain why the scarcity point matters beyond LLMs: it affects supervised
  predictors, generative methods, optimization, world models, evaluation, and
  transfer.
- Move dense Lighthouse identifiers and study-specific state, such as
  `XR-TRACE-A` and `SW-BASE-A`, under the approved Lighthouse treatment. The
  surrounding body should teach specification identity and provenance in plain
  language before exposing any identifier the reader must retain.

### Chapter 5: method choice and composition

- Repair the graph-placement figure's connector geometry. The action,
  next-state, terminal-evaluation, and reward paths must be visually distinct;
  connectors may not run through boxes, text, or one another, and every
  arrowhead must land unambiguously.
- Include Chapter 5 in the book-wide SVG connector audit. Check overlaps,
  arrow clearance, label clearance, missing connector shafts, and crossings in
  every figure rather than fixing only the reported diagram.
- Preserve the chapter's two different teaching jobs:
  1. choose a method by identifying the limiting architecture work;
  2. compose methods only when prediction, generation, optimization, direct
     tools, or conventional techniques perform distinct necessary jobs.
- Make the student-facing method-selection test unmistakable:
  generation addresses missing artifact construction; prediction addresses
  expensive or unavailable outcome estimation; optimization addresses
  selection or allocation under a large space or scarce evaluation budget;
  better checking is needed when evaluation or verification is limiting; and a
  conventional method or no added method remains a valid result.
- Do not add a Venn diagram by default. These method families are jobs that can
  appear in different orders and combinations, not three fixed sets of design
  problems. The existing conditional method-selection figure should own
  *when to choose*, and the method-organization table should own the valid
  combinations and the condition that keeps each minimal.
- If the visual audit finds that the interaction among method families remains
  hard to retrieve, consider a compact composition diagram centered on the
  architecture question, tool feedback, and required check. It should show
  possible paths such as generator-to-predictor screening,
  predictor-in-optimizer surrogate use, optimizer-controlled generation, and
  direct tool feedback. It must not imply a universal order or that all three
  methods are required.

### Chapter 6: tools become environments

- Keep the opening claim that a tool command is not an environment, but audit
  the next paragraphs for a smoother build from the familiar act of launching
  a tool to the state, identity, translation, scheduling, cost, return, and
  recovery responsibilities that the command does not supply.
- Replace the question-form Section 6.1 title. Section headings in the numbered
  chapters should state the section's claim or subject rather than ask a
  question. A candidate direction is *From Tool Commands to Architecture
  Environments*; select the final title during the title pass.
- Audit Lighthouse identifiers such as `XR-L2-CAP-A`, `SRAM-A`, `SIM-A`, and
  `PVT-A`. The body should first teach why candidate, workload, software,
  condition, model, and tool identities must remain distinct. Concrete codes
  belong in the Lighthouse application or retained run specification only when
  a later comparison actually requires them.
- Decide whether Listing 6.1 earns its space. It currently gives a long
  implementation-like account of request validation, admission, execution,
  cancellation, artifact inspection, parsing, and recording after the prose has
  already explained those responsibilities. Test three options: remove it;
  replace it with a much smaller conceptual sequence; or move implementation
  detail to an appendix. Retain a listing only if a student learns a reusable
  interface or state distinction more clearly from the pseudocode than from the
  surrounding prose and figures.
- Make the architecture-tool spectrum an explicit teaching object. Include
  analytical and trace-driven models, cycle-level and RTL simulation, formal
  methods, synthesis and physical-design tools, emulation or FPGA prototypes,
  and silicon measurements where relevant. Explain that these tools differ in
  observability, fidelity, latency, cost, state, failure semantics, licensing,
  and returned artifacts.
- Preserve the chapter's core insight: an environment may standardize requests,
  identity, execution control, and returned records, but it must not erase
  tool-specific meaning or imply that different tools provide interchangeable
  evidence.
- Divide the cost lesson across chapter jobs rather than repeating it. Chapter
  6 owns how tool time, queue time, retries, compute, storage, licenses, model
  calls, and human intervention are observed and retained. Chapter 5 uses those
  costs to choose a method, and Chapter 10 uses them to compare complete
  systems.
- Audit Chapter 6 tables by semantic class. Bold the first data column only for
  field or definition tables in which it is a genuine row label; keep it plain
  for comparisons and matrices. Apply one capitalization convention to sibling
  row labels and column headers, but do not use a mechanical sweep that changes
  technical identifiers or prose fragments.

### Chapter openings and subsection orientation

- Except where Chapter 1 introduces the Lighthouse as the moonshot itself,
  avoid concrete Lighthouse prompts, study identifiers, or candidate details in
  the chapter prose before the learning objectives. That opening should make the
  chapter's problem and reader need understandable on their own. Introduce the
  Lighthouse later where it can test or ground an idea the reader has met.
- Audit every H2 that contains H3 subsections. The H2 must contain enough
  orienting prose before the first H3 to explain the parent question, the
  relationship among its subsections, and why the decomposition is useful.
- Treat an H2 followed immediately by an H3 as a structural defect. Repair it
  by adding a real parent-level orientation, removing a redundant H3, or
  flattening the hierarchy—not by inserting a filler sentence.
- Continue the lone-H3 audit. A single child subsection usually means the child
  should be folded into its parent or promoted, unless the hierarchy carries a
  clear and exceptional teaching purpose.
- Run a plain-language pass for unfamiliar process phrases such as “unbounded
  absence claim.” Replace them with the architecture question, measurement
  limit, or unsupported conclusion they actually mean. Do not preserve coined
  language merely because it is used consistently.

### Chapter 7: verification, feedback, uncertainty, and learning

- Use an architecture, formal-methods, ML-systems, uncertainty-quantification,
  and pedagogy panel to assess the chapter before editing. Determine whether
  each section teaches a necessary technical distinction and whether an
  architect can use it.
- Repair the stacked headings at Section 7.6. The parent section on qualifying
  proxies and testing explanations needs an orientation before its first H3,
  or its hierarchy should be simplified.
- Keep formal verification distinct from statistical confidence. Explain what
  a proof, counterexample, bounded result, timeout, or `unknown` establishes
  under a declared model and assumptions, and what remains outside that scope.
- Develop uncertainty only where it changes an architecture action. Candidate
  topics to assess include measurement variation, model or surrogate error,
  distribution shift, incomplete coverage, calibration, confidence intervals,
  and uncertainty that should trigger stronger tools, more samples, review, or
  refusal to conclude.
- Borrow from explainability research carefully. Distinguish a plausible
  post-hoc explanation from mechanism evidence that survives a targeted test,
  counterfactual, ablation, or higher-fidelity check. Avoid importing generic
  explainability taxonomies that do not alter an architecture decision.
- Investigate the idea behind an “AI-certified tool,” but do not adopt that term
  prematurely. Certification or qualification is normally relative to an
  intended use, evidence standard, operating envelope, and consequence. A more
  durable question is what evidence qualifies an AI-assisted tool or component
  for a defined architecture task and risk class.
- If retained, distribute that qualification question across chapter jobs:
  Chapter 6 exposes the interface, state, and records needed for qualification;
  Chapter 7 determines what the returned evidence establishes; Chapter 10
  evaluates reliability and failure behavior; Chapter 11 owns authority to use
  the qualified system in an architecture commitment.

### Evaluation coverage: component task, architecture result, and complete system

- Audit whether the manuscript makes three evaluation objects immediately
  distinct:
  1. whether an AI or conventional component performs its assigned task;
  2. whether the resulting candidate improves the architecture under the
     declared workload, software, physical conditions, and checks; and
  3. whether the complete workflow reaches a supported decision more reliably
     or at lower total cost than a credible alternative.
- Map the familiar ML-systems dimensions into those objects without treating
  them as interchangeable:
  - task performance: prediction error, valid construction, search efficiency,
    tool-use success, or another role-specific measure;
  - system performance: architecture correctness, latency, throughput, power,
    energy, area, reliability, software behavior, and physical feasibility;
  - cost: data preparation, training or adaptation, model calls, tool runs,
    queue time, compute, memory, storage, licenses, failures, retries, and human
    setup, diagnosis, verification, and review;
  - generalization: performance under changed workloads, software, target
    hardware, tools, process conditions, and design spaces;
  - reliability: variation across repetitions, seeds, environments, attacks,
    faults, interruptions, recovery, and changed conditions;
  - interpretation and verification: whether the returned explanation or proof
    supports the architecture claim rather than merely accompanying a good
    score.
- Preserve chapter ownership. Chapter 7 qualifies returned measurements,
  checks, explanations, and uncertainty. Chapter 9 owns transfer to changed
  problems. Chapter 10 brings the dimensions together for complete-system
  evaluation and red teaming.
- Check whether Chapter 10's existing four-part metric map already makes this
  structure legible. Prefer strengthening its explanation or labels over
  introducing a competing five- or six-part framework.
- Use the slide's task/system/cost/generalization/reliability organization as a
  diagnostic lens and source-discovery prompt, not automatically as a new
  manuscript figure.

### Hold point

Do not implement these items until the author has reviewed the proposed
Chapter 2 order and the book-wide Lighthouse rule. Continue read-only audits
and collect conflicts or implications in this queue.

## Completion Criteria

The milestone is complete when:

- every chapter and section has a clear, unique teaching job;
- Chapters 4 through 11 retain the technical depth of the opening chapters;
- factual and empirical claims have appropriate support;
- author synthesis and speculation are clearly distinguished from established
  evidence;
- terminology is clear to architecture, EDA, ML, and systems readers;
- the candidate-capacity model and example are technically correct and placed
  where they help the argument;
- the method-selection guide is useful without prescribing a false universal
  order;
- research themes contain strong, publishable questions rather than
  miscellaneous prompts;
- figures and tables are introduced, explained, and interpreted without
  gratuitous eye-movement instructions;
- quantitative figures use traceable data and checked calculations;
- chapter openings, section transitions, and chapter handoffs read smoothly;
- the book remains compact and principled rather than encyclopedic; and
- all accepted changes are preserved in small, reversible commits.
