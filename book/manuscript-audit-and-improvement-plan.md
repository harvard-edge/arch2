# Architecture 2.0 Manuscript Audit and Improvement Plan

## Status

This document records the next content milestone for *Architecture 2.0*. The
working baseline is commit `e9bb837e`. The manuscript remains unchanged while
the read-only audits run. Proposed structural or substantive changes return to
the author for review before they enter a chapter.

The milestone focuses on content, technical grounding, narrative flow,
research questions, and explanatory visuals. It does not begin a page-budget,
layout, slide-deck, or production-polish pass.

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

### Proposed Primary Placement

The model should first appear in Chapter 2 after the discussion of evaluation
and verification capacity and before the chapter turns to where assistance
might help.

That placement lets the chapter proceed in this order:

1. modern architecture work creates more alternatives and more expensive
   checks;
2. every checking stage has finite capacity;
3. faster candidate production can overload the remaining stages;
4. useful assistance must relieve the actual bottleneck rather than merely
   create more work.

Chapter 5 can reuse the diagnosis in the method-selection guide. Chapter 7 can
add false acceptance, false rejection, check scope, and correlated failures.
Chapter 10 can use time and total cost per supported decision as evaluation
metrics. The complete explanation should not be repeated in every chapter.

### First-Order Model

Let:

- \(g\) be the candidate-generation rate;
- \(p_i\) be the fraction of candidates that survive checking stage \(i\);
- \(c_i\) be the parallel capacity at stage \(i\), such as machines, tool
  licenses, or review slots;
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

Finite expected queueing delay requires:

\[
\lambda_i < \mu_i
\]

at every stage. Equality is not an adequate operating target in a stochastic
system because small variations can create a growing delay. The corresponding
upper bound on the input rate is:

\[
g <
\min_i
\left(
\frac{\mu_i}
{\prod_{j=1}^{i-1} p_j}
\right).
\]

If all stages remain stable, the expected rate of fully qualified candidates
after \(m\) stages is:

\[
q =
g \times \prod_{i=1}^{m} p_i.
\]

A supported architecture decision may require several qualified alternatives,
a matched baseline, and architect review. Therefore, \(q\) is an upper bound
on candidate qualification rather than a direct claim about decision
throughput.

### Checked Illustrative Example

Consider three stages:

| **Stage** | **Capacity** | **Survival fraction** |
| --- | ---: | ---: |
| Cheap legality and syntax checks | \(120\) candidates/hour | \(0.25\) |
| Simulation and software evaluation | \(12\) candidates/hour | \(0.10\) |
| Implementation and verification | \(0.5\) candidates/hour | \(0.50\) |

The maximum candidate-generation rate allowed by each stage is:

| **Stage constraint** | **Maximum input rate** |
| --- | ---: |
| Legality checks | \(120\) candidates/hour |
| Simulation | \(12 / 0.25 = 48\) candidates/hour |
| Implementation and verification | \(0.5 / (0.25 \times 0.10) = 20\) candidates/hour |

Implementation and verification form the bottleneck. A rate of \(20\)
candidates/hour would operate that stage at full utilization, so the example
instead uses \(g = 16\) candidates/hour, which gives the bottleneck 80 percent
utilization.

The resulting offered loads are:

| **Stage** | **Calculation** | **Offered load** | **Utilization** |
| --- | --- | ---: | ---: |
| Legality checks | \(16\) | \(16\)/hour | \(16/120 = 13.3\%\) |
| Simulation | \(16 \times 0.25\) | \(4\)/hour | \(4/12 = 33.3\%\) |
| Implementation and verification | \(16 \times 0.25 \times 0.10\) | \(0.4\)/hour | \(0.4/0.5 = 80\%\) |

The fully qualified output rate is:

\[
16 \times 0.25 \times 0.10 \times 0.50
= 0.20
\]

qualified candidates/hour, or one qualified candidate every five hours on
average. If a decision requires two fully checked alternatives, the resulting
upper bound is one comparison every ten hours before architect review and
other decision costs.

Increasing generation to \(60\) candidates/hour would not increase supported
decision throughput. Simulation would receive \(60 \times 0.25 = 15\)
candidates/hour despite having capacity for only \(12\). Even when simulation
is saturated, its output would offer approximately
\(12 \times 0.10 = 1.2\) candidates/hour to an implementation stage that can
process only \(0.5\). Both queues would grow.

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
| 2. Why assistance | Explain the compounding pressures and where assistance might help | Historical build-up, technology scaling, evaluation and verification capacity, capacity model, transition to AI assistance |
| 3. Life cycle | Explain how to organize AI-assisted design and why each stage exists | Tacit knowledge, progressive introduction of the stages, iteration and stopping, avoiding process bureaucracy |
| 4. Data, knowledge, and representation | Explain how architecture data is collected and represented and why it is distinctive | Data as intervention, sample cost, failures and censoring, exact and learned representations, embeddings, current project state |
| 5. Methods | Teach when and how to use prediction, generation, optimization, conventional methods, or combinations | Concrete methods, roles versus families, bottleneck-driven decision guide, feedback cost, no fixed ordering |
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

### Expert Review Lenses

Each chapter receives fresh, independent reviews from:

- a computer architect;
- an EDA, physical-design, and verification expert;
- an ML systems researcher; and
- a research advisor and pedagogy reviewer.

Chapter-specific secondary lenses should be added where needed:

- data engineering and representation learning for Chapter 4;
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

Aim for two to four themes and roughly five to eight questions per chapter.
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
- the review lens; and
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

## Milestones and Approval Gates

### Milestone 0. Baseline and Inventory

- Record the clean baseline commit.
- Inventory all chapters, sections, figures, tables, callouts, research
  questions, citations, and existing quantitative data.
- Compare the working manuscript with the local `dev` version and repository
  history where earlier material may have been lost.
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
- Replace gratuitous directional instructions.
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
- whether the candidate-capacity model belongs wholly in Chapter 2 or should
  split one concept and one application across Chapters 2 and 5; and
- whether the foundation-model figure should be one two-panel figure or two
  separate figures.

## Deferred Work

The following work begins only after content acceptance:

- page-budget reconciliation;
- PDF layout and page-flow polish;
- final typography and float placement;
- a full presentation deck;
- production packaging; and
- broad website adaptation.

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
