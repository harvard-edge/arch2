# Architecture 2.0 Author Review Notes

**Review date:** July 29, 2026
**Current scope:** Front matter, preface, Chapter 1, and Chapter 2
**Editorial status:** Feedback collection. Except for the title-page build date,
none of the observations below have been applied to the manuscript.

This document preserves feedback from the author's first continuous skim of the
revised book. It separates observations from proposed editorial directions so
that a local comment does not silently become a book-wide rule.

## Status Key

- **Resolved:** A focused correction has already been made and verified.
- **Confirmed defect:** The current source or rendered PDF contains a concrete
  error.
- **Likely direction:** The feedback identifies a persuasive editorial
  direction, subject to review in the full chapter.
- **Open question:** The idea needs comparison against the rest of the book,
  technical sources, or publication constraints before a decision.
- **Later chapter:** The idea is valuable but probably belongs outside the
  chapter currently under review.

## Review Method

The current pass is for collection, not piecemeal rewriting.

1. Complete an author skim and collect observations in chapter-sized batches.
2. Separate book-wide decisions from local chapter changes.
3. Resolve global terminology, audience, cross-reference, callout, acronym, and
   front-matter conventions.
4. Review each chapter against its unique purpose before editing it.
5. Commit each coherent chapter or book-wide pass separately.
6. Revise the preface after the chapters stabilize because the preface promises
   what the finished book delivers.
7. Finish with a continuous reader pass and a rendered PDF review.

## Resolved Production Note

### Title-Page Date

**Author observation.** The PDF title page carried a stale fixed date.

**Resolution.** The Quarto metadata now uses the build date. The rebuilt PDF
shows July 29, 2026, and future builds will update the date automatically.

## Front Matter and Preface

### Development-Process Material

**Author observation.** Material explaining how the book is being written has
been useful in talks and on the website, but it does not need to appear in the
PDF.

**Likely direction.** Keep the extended development-process explanation on the
website. Retain only a short formal disclosure in the PDF if required by
Springer, academic policy, or publication practice.

### Part-Opening Pages

**Author observation.** Each named part currently opens on a mostly empty page.
The page could include a few words explaining what that part accomplishes.

**Likely direction.** Add one or two restrained italicized sentences to each
part-opening page. Each statement should explain the intellectual movement of
the part rather than summarize its chapter titles or introduce another
mini-preface.

### From Prompt or Specification to Implementation

**Author observation.** "From spec to chip" may be a useful phrase, but a prompt
is not a specification. The book should not collapse those concepts.

**Editorial assessment.** The distinction is foundational. A request or prompt
is one interface into the design process. Design intent, requirements,
constraints, specifications, architecture models, implementation artifacts,
and verified results have different meanings and authority.

**Open question.** Compare several formulations before selecting a recurring
phrase:

- *Intent to implementation* is the most technically inclusive.
- *Specification to silicon* is memorable and can describe a hardware path,
  but it does not cover the full software and system scope of the book.
- *Spec to chip* is concise but risks narrowing the book and overstating what a
  prompt supplies.

The terminology review should also examine how prior design-automation and EDA
literature describes these transformations.

### Intent, HLS, and Logic Synthesis

**Author observation.** The preface may need a clear account of how intent
becomes an implementation. A concise or memorable expression would help.

**Editorial assessment.** Technical precision matters more than rhyme.
High-level synthesis does not transform unrestricted architecture intent
directly into hardware, and logic synthesis does not begin with intent. A
defensible sequence is:

> Design intent → requirements and constraints → architecture and behavioral
> descriptions → RTL or HLS output → logic and physical implementation →
> verified system

This sequence should acknowledge hardware-software partitioning and the
software path rather than present implementation as a hardware-only descent.

### Citations in the Preface

**Author observation.** References in the preface feel unusual and make the
opening heavier than necessary.

**Likely direction.** Keep only citations needed to support an important factual
claim. Move detailed cases, quantitative evidence, and literature positioning
into the chapters. The preface should establish the thesis and reader promise
without becoming a miniature literature review.

### Chapter References in the Preface

**Author observation.** Isolated references to Chapter 3, Chapter 8, and other
specific chapters make the preface feel less self-contained.

**Likely direction.** Explain the necessary concept locally. Reserve systematic
chapter navigation for a concise book-organization passage. Avoid occasional
"as Chapter 7 explains" references when the other chapters are not introduced
the same way.

### Explaining the Synthesis

**Author observation.** The lecture should make clear that it synthesizes ideas
from adjacent fields. The current table of established disciplines may give the
inventory too much visual weight.

**Editorial assessment.** The preface should demonstrate synthesis rather than
merely catalogue sources. Architecture supplies questions, tradeoffs, and
decisions. Machine learning supplies learned representations and methods.
Electronic design automation supplies executable transformations and physical
measurements. Experimental science, statistics, software engineering, systems
safety, benchmarking, and control contribute particular checks and reasoning
practices.

**Likely direction.** Replace most or all of the table with a short causal
explanation of why no single field is sufficient. AI-assisted design connects
work across boundaries, so the relevant standards of architecture, ML, EDA,
software, experimentation, and verification must meet.

### Three-Field Figure

**Author observation.** The figure connecting computer architecture, machine
learning, and EDA is valuable and belongs in the preface. It may be possible to
improve it.

**Likely direction.** Preserve the figure and strengthen its explanatory role.
Consider naming what each field contributes or which validity test it imposes.
Do not add so many circles or adjacent disciplines that the central relationship
becomes unreadable.

### Prefatory Figure Numbering

**Author observation.** Figure 0.1 and Figure 0.2 look awkward in the preface.

**Open question.** Investigate prefatory numbering such as Figure P.1 and P.2.
If the Springer and Quarto machinery makes that fragile, unnumbered prefatory
figures may be preferable to hard-coded numbering. Do not move the three-field
figure out of the preface merely to avoid the numbering issue.

### Audience and Reading Paths

**Author observation.** "One book, four entry points" feels promotional or
tacky. "AI Strategist" and "Chief Architect" weaken the technical register.
"ML Researcher" and "Computer Architect" are more credible.

**Likely direction.** Remove the slogan or use a neutral heading such as
"Reading Paths" or "Who This Book Is For." Describe readers by the technical
problem they need to understand rather than by inflated titles. Candidate
groups include:

- computer architects, EDA researchers, and systems researchers;
- ML researchers entering system and chip design;
- graduate students entering the intersection;
- technical engineering leaders evaluating AI-assisted workflows.

The book does not need exactly four personas.

## Book-Wide Language and Presentation

### Overuse of "Bounded Study"

**Author observation.** The manuscript returns to "bounded study" too often and
appears overly committed to the phrase.

**Editorial assessment.** The concept is useful when scope, stopping conditions,
permitted changes, or decision boundaries are doing real work. It should not be
the universal name for every architecture activity.

**Likely direction.** Audit every occurrence. Use ordinary terms such as
*study*, *analysis*, *experiment*, *comparison*, or *design effort* unless the
boundary itself matters. Preserve the deeper treatment for the lifecycle and
complete-study chapters.

### Acronym Expansion

**Author observation.** DRC appears without first being expanded. Other
acronyms may have the same problem.

**Confirmed defect.** The first relevant occurrence should read "design rule
checking (DRC)" or "design rule check (DRC)," depending on the local grammatical
role.

**Likely direction.** Run a book-wide acronym audit after the structural review.
Expand an acronym at first use in each chapter that readers may encounter
independently. Avoid creating an acronym such as MCML if "multicore and
multinode" appears only once.

### Cross-Chapter References

**Author observation.** Occasional phrases such as "as Chapter 7 details" sound
arbitrary when the book does not systematically refer to every chapter that
way.

**Likely direction.** Prefer a self-contained explanation or a conceptual
forward reference such as "the later feedback discussion." Retain numbered
cross-references when they materially help navigation, but establish a
consistent policy.

### Lighthouse Callouts

**Author observation.** Lighthouse callouts were intended as a self-contained
secondary thread. Readers should be able to skip them and still follow the main
argument, or read them together to see how the book's ideas apply to the running
example.

**Likely direction.** Audit every Lighthouse callout with a skip test:

- The main prose remains coherent without the callout.
- The callout introduces no essential definition or causal step.
- The callout grounds the local concept in Lighthouse.
- The sequence of Lighthouse callouts forms a coherent secondary narrative.

Apply this as a book-wide editorial contract rather than as a Chapter 2-only
fix. Each useful callout should advance the running example by introducing a
new question, constraint, representation, method choice, tool interaction,
check, result, or decision. It should not merely repeat the surrounding chapter
in XR language. Aim for continuity across the book, but do not force a callout
into a chapter or section where Lighthouse adds no explanatory value.

### Design Principles

**Author observation.** The book needs a clear definition of a design principle.
Some chapters may earn more than one. Students should be able to scan the
principles as a coherent narrative, possibly through a consolidated appendix.

**Existing rule.** A design principle is a durable rule that a reader can carry
into a different architecture problem after the chapter details fade. Each
numbered chapter has one primary principle. Supporting principles are allowed
when they are reusable beyond the local paragraph. A slogan, summary, example,
or checkpoint does not qualify.

**Likely direction.**

- Keep each primary principle in the conclusion where the chapter earns it.
- Allow supporting principles by need rather than quota.
- Audit the eleven primary principles as one sequence for overlap, omissions,
  and narrative progression.
- Consider a back-matter "Design Principles" reference that gathers the primary
  principles without removing them from their chapters.

The emerging progression is:

1. Set the architectural ambition.
2. Diagnose the work limiting progress.
3. Organize the study.
4. Represent the design correctly.
5. Choose methods according to their checks.
6. Preserve what tools actually ran.
7. Qualify feedback and verification.
8. Close the complete study.
9. Transfer only what remains valid.
10. Evaluate results, processes, and failures.
11. Preserve architectural judgment and responsibility.

## Chapter 1: The Moonshot

### Chapter Purpose

Chapter 1 should establish the moonshot for AI-assisted system and chip design.
It should state a bold complete-system target, explain why that target forces
the important questions into view, and introduce Lighthouse as the concrete
test without trying to perform the detailed diagnosis owned by Chapter 2.

### The 500 W Value

**Author observation.** The figure stating that frequency stalls while power
keeps climbing reaches 500 W, but the provenance and meaning of that endpoint
are unclear.

**High-priority quantitative audit.** Determine whether 500 W is an observed
frontier value, a projection, an extrapolation, an illustrative endpoint, or an
axis choice. If it is not directly supported, label it honestly or remove it.
The prose and caption must distinguish frontier observations from a universal
processor trend.

### Missing Bridge to AI

**Author observation.** The paragraph stating that the pressure does not make AI
strictly necessary arrives before the text has established why AI might help.
The transition appears to assume the proposed answer.

**Likely direction.** Add a short bridge:

1. Existing architecture and EDA automation delivered substantial gains.
2. Cross-stack complexity and evaluation cost now constrain further progress.
3. AI can generate candidates, predict expensive outcomes, guide search,
   operate tools, retrieve context, and organize results.
4. Those capabilities make AI worth testing but do not make it automatically
   necessary or superior.

Chapter 1 should establish plausibility. Chapter 2 should explain the pressures
and bottlenecks in depth.

### Establishing the Moonshot

**Author observation.** Section 1.1 may be better titled "Moonshot" or "The
Moonshot" rather than "Lighthouse Moonshot." The chapter should establish why
engineering fields use moonshots and why architecture needs a step-function
target before presenting Lighthouse.

**Editorial assessment.** Define the term operationally rather than as
inspirational language. A moonshot is a concrete outcome that current practice
cannot deliver, requires a step change in capability, and has explicit success
conditions.

**Likely direction.** Use a small number of carefully sourced historical
examples if they clarify the pattern. Avoid the universal or promotional claim
that every architect needs a moonshot. A stronger formulation is that the field
needs a target large enough to expose what a complete AI-assisted design process
must do.

### AI as Design Automation

**Author observation.** The first introduction of AI could present it as a form
of design automation that can be used in several ways.

**Editorial assessment.** This framing is useful with one qualification. AI
extends the design-automation repertoire, but it is not merely another automatic
implementation tool and does not replace EDA. Its possible roles include
generation, prediction, optimization, tool operation, interpretation,
retrieval, and connection across representations.

### Architecture 1.0 and Architecture 2.0

**Author observation.** Table 1.1 may become one of the book's most important
and most frequently cited artifacts. It needs unusually careful review.

**High-priority conceptual audit.** Do not caricature conventional computer
architecture. Traditional practice already uses models, automation, iteration,
verification, data, and cross-layer reasoning. Candidate distinctions to test
include:

- AI can participate in more stages of architecture work.
- AI can connect and transform more representations.
- Candidate production and analysis can occur at a different rate and scale.
- Explicit comparison, checks, and responsibility become more important rather
  than less important.
- The complete AI-assisted process must be evaluated, not only the generated
  artifact.

Audit every row for historical fairness, durability, and whether it states a
genuinely meaningful distinction.

### Defining a Generator

**Author observation.** The first use of *generator* should explain what the
book means.

**Likely wording.** A generator proposes a candidate artifact, such as code, an
architecture description, a test, or a tool configuration. This definition
should distinguish the role from prediction, optimization, criticism, and
verification.

### Referring to the Lighthouse Prompt

**Author observation.** "The prompt occupies only a few lines" would be clearer
as "The prompt in Figure 1.2 occupies only a few lines."

**Likely direction.** Move the cross-reference beside the noun when it reduces
search effort for the reader, even if a trailing reference is technically
correct.

### Software and Efficiency

**Author observation.** Efficiency discussion should name software's role.

**Likely direction.** Connect hardware efficiency to compiler transformations,
mapping, runtime behavior, workload structure, scheduling, and software
adaptation. The Lighthouse target should not imply that hardware capability
alone determines system-level efficiency.

### Awkward Sentence Opening

**Author observation.** The sentence beginning with language similar to "begin
outside architecture with the result that sets the form" reads strangely.

**Open question.** Locate the exact sentence during the Chapter 1 edit and
rewrite it in direct technical prose. One dictated phrase surrounding this note
was unclear and should not be interpreted without the page in view.

### Formal Verification and Proof Systems

**Author observation.** Later verification discussions could consider Lean and
other formal systems, possibly with multiple verifiers checking generated work.

**Later chapter.** Treat this as a research direction for Chapters 7 and 10.
Distinguish industrial hardware formal methods, model checking, equivalence
checking, assertion-based verification, SMT-backed analysis, and proof
assistants such as Lean. Do not imply that Lean replaces established RTL
signoff.

A broad field question is whether AI-assisted design can produce
machine-checkable claims or proof obligations alongside generated artifacts,
and whether independent verification systems can make those claims easier to
trust.

### Research Questions

**Author observation.** The Chapter 1 and Chapter 11 questions are useful but
too specific. These chapters should ask broader, field-oriented questions.

**Likely direction.** Chapter 1 should establish the research ambition of
AI-assisted system and chip design. Chapter 11 should ask about architectural
judgment, authority, responsibility, and professional practice. Move narrow
method, estimator, or workflow questions into the chapters that teach those
subjects.

### Positive Presentation Signal

**Author observation.** The italicized, topic-oriented presentation was
particularly effective and should be preserved or recovered where appropriate.

**Open question.** Match this note to the exact rendered element during the
page-level review before turning it into a general style rule.

## Chapter 2: Why Assistance Might Be Useful

### Chapter Purpose

Chapter 2 should explain what has changed in architecture work that makes new
forms of assistance worth considering. Its central argument is that hardware,
software, physical, evaluation, verification, and review pressures compound.
The work required to settle a design question can grow faster than the capacity
to examine and close it.

The chapter should motivate the opportunity for assistance without choosing
detailed methods, which is Chapter 5's job, or prescribing the lifecycle, which
is Chapter 3's job.

### "Theme-Based Architecture"

**Author observation.** A review described the preamble or abstract material as
following a "theme-based architecture," but the phrase is unclear.

**Editorial assessment.** At most, it means that the chapter is organized by
themes rather than chronology. It is not actionable reader-facing language and
does not explain why the current opening works.

### Preamble and Range

**Author observation.** The introductory material jumps into the claim that
computer architecture advanced through feedback without first setting the
range. It may need substantial rewriting or removal.

**Likely direction.** Rewrite the opening so it states:

1. what has become harder about architecture work;
2. why the pressures compound rather than form an independent list;
3. what historical transformations teach about responding to complexity;
4. why AI is one candidate extension of design automation rather than a
   predetermined answer.

Keep the detailed Lighthouse prompt out of the preamble. One sentence can
promise a later application.

### Learning Objectives

**Author observation.** The learning objectives may no longer reflect the
chapter's intended job.

**Likely direction.** Revisit them after restructuring. Candidate capabilities
include:

- explaining how architecture work accumulated coupled complexity;
- distinguishing design-space size from the ability to evaluate and close a
  decision;
- recognizing the work that limits progress;
- explaining why different bottlenecks call for different forms of assistance;
- judging whether assistance reduces total work or shifts it downstream.

The current objective about defining a work-item class and observation window
may be too operational if that detailed material moves elsewhere.

### Historical Transformations

**Author observation.** The chapter could use computing history, including
VLSI, to show moments when a transformative approach became necessary.

**Editorial assessment.** Much of the material is already present, including
System/360, Mead-Conway, logic synthesis, benchmarking, and CUDA. The table
currently hides the unifying argument.

**Likely direction.** Explain the pattern:

> When architecture work became too complex to coordinate informally, the
> field introduced a new abstraction, shared representation, tool path,
> benchmark, or check.

Select examples because they demonstrate that pattern, not to create a general
history of computing.

### Raising the Level of Abstraction

**Author observation.** Chapter 2 might conclude its historical discussion by
explaining that architecture has often responded to increasing complexity by
raising the level of abstraction.

**Editorial assessment.** This is the right historical pattern with an
important qualification. Raising abstraction worked when the field also built
interfaces, transformations, tools, and checks that kept higher-level decisions
connected to implementation. An abstraction that hides physical consequences
without providing a way to recover and test them does not solve the
architecture problem.

**Likely direction.** Use this point near the end of the historical section and
return to it when introducing AI. AI may let designers express requests at a
higher level and may help translate among representations, but the resulting
artifacts still need executable tool paths and implementation-level checks.
The durable pattern is therefore:

> Raise the level at which designers express decisions while strengthening the
> tools and checks that connect those decisions to implementation.

This framing connects Mead-Conway methods, hardware-description languages,
logic synthesis, compiler abstractions, and modern AI assistance without
claiming that AI is automatically the next successful abstraction.

### Sections 2.1, 2.2, and 2.3

**Author observation.** Sections 2.1 and 2.2 appear to be making an interesting
point, but their thread is difficult to follow. Section 2.3 becomes clearer
because it directly explains scaling hardware and the sources of complexity.

**Editorial diagnosis.**

- Section 2.1 contains useful historical material without establishing why the
  reader needs it.
- Section 2.2 introduces the fair-comparison and TAO/TAOS arguments before the
  chapter's organizing progression is clear.
- Section 2.3 begins the chapter the reader expected from the title.

**Likely direction.** Reorganize and rewrite 2.1 and 2.2 rather than discard
their ideas. Use Section 2.3 and the software section as the chapter's strongest
current backbone.

### Bringing AI into Section 2.1

**Author observation.** AI appears too early in the historical and complexity
discussion.

**Likely direction.** Diagnose the pressure before introducing the response.
The historical section should establish what prior abstractions and automation
accomplished. A later section should explain where AI might reduce specific
work. Avoid inserting a miniature AI solution into every hardware-complexity
subsection.

### Specialization Spectrum

**Author observation.** The specialization discussion would benefit from a
classical spectrum running from a general-purpose CPU to specialized
accelerators and domain-specific systems.

**Likely direction.** Consider a simple visual:

> General-purpose CPU → vector or SIMD processor → GPU or programmable
> accelerator → domain-specific accelerator → fixed-function hardware

Possible accompanying dimensions include flexibility, potential efficiency,
dependence on workload assumptions, software obligation, and verification
burden. Do not imply that all systems occupy one perfectly ordered line.

### Historical Evolution Figure

**Author observation.** An earlier Chapter 1 figure used a staircase to explain
the evolution of design automation and was visually useful.

**Editorial context.** The earlier automation-ladder timeline was removed
because ladder and rung language implied a simple maturity hierarchy and
conflicted with the desired plain framing.

**Open question.** Recover the valuable historical sequence as a timeline of
transformative abstractions, interfaces, and checks rather than as a staircase
or maturity ladder.

### A Visual for Compounding Complexity

**Author observation.** The chapter may need a memorable visual showing
increasing system scale and increasing competing considerations.

**Open question.** Prefer a causal or structural diagram over an invented
quantitative trend. Possible visual jobs include:

- showing how the definition of "the computer" expands from core to chip,
  package, software stack, and warehouse-scale system;
- showing how each layer introduces new interactions and evaluation
  obligations;
- showing that candidate-production capacity and examination capacity do not
  necessarily grow together.

### The Software Contract

**Author observation.** The software section reads well. Modern examples such
as the CUDA stack, collective optimizations, and NVIDIA SHARP may strengthen it.

**Likely direction.** Use one carefully sourced example to show that the
executable software path can extend through:

> compiler → runtime → libraries → collective communication → network fabric
> → deployment controls

Do not turn the section into a vendor-product inventory. Verify the precise
NVIDIA terminology and source before adding an example.

### A Consolidated Lighthouse Section

**Author observation.** XR and subsystem concepts are distributed throughout
the chapter. A later section could gather them and show what the complete
Lighthouse prompt means after the general pressures have been explained.

**Likely direction.** Preserve sparse optional Lighthouse callouts, then
consider a short synthesis section near the end. It should connect hardware
scale, specialization, software evolution, physical limits, evaluation cost,
and verification without repeating every callout.

### Figure 2.10 Newline

**Author observation.** The 71 percent label visibly contains a literal `/n` or
newline escape.

**Confirmed defect.** The plotting source renders
`71%\\nsoftware + verification + IP qualification` literally. Correct the
Matplotlib string during the Chapter 2 editing pass and re-render the figure.

### Figure 2.11 and the Scissors

**Author observation.** The scissors argument is compelling. The figure might
be stronger if it reached further into history and showed an inversion or
crossing point.

**Editorial assessment.** Figure 2.11 is currently conceptual. Its horizontal
axis represents increasing project scope and results, not historical time, and
its shaded region is not a measured backlog.

**Open question.** Consider a two-panel visual:

- a historical design-productivity gap grounded in ITRS or another primary
  source;
- the modern generalized gap between work produced and the capacity to
  evaluate, verify, and review it.

Do not merge measured historical data and a conceptual modern diagram into one
apparently empirical curve.

### Placement of the Scissors Argument

**Author observation.** The paragraph around the scissors may be strong enough
for the introduction.

**Likely direction.** Foreshadow the scissors in the introduction, but keep the
full explanation after the hardware, software, physical, evaluation, and
verification pressures have accumulated. The argument is more convincing once
the chapter has earned it.

### The Queue as a Distinct Section

**Author observation.** The passage beginning with a growing evaluation or
review queue forms a natural, self-contained transition.

**Likely direction.** Consider giving it a subsection that explicitly connects
compounding complexity to workflow bottlenecks. It currently sits inside a long
diagnostic section even though it performs a new conceptual job.

### Diagnosing One Work-Item Class

**Author observation.** The detailed work-item-class diagnosis appears to come
from nowhere.

**Editorial assessment.** The chapter moves from a field-scale complexity
argument into a fifteen-day operational observation without explaining why that
level of procedure belongs here.

**Open question.**

- Keep the general categories of limiting work in Chapter 2.
- Keep the principle that teams should diagnose the bottleneck before applying
  AI.
- Consider moving the detailed observation-window procedure to Chapter 3,
  Chapter 8, or an appendix.

### AI Roles

**Author observation.** "Different problems call for different AI roles" may
sound more formal than necessary. The intended point is that AI can help in
different ways depending on the problem.

**Likely wording.**

> Different bottlenecks call for different forms of assistance.

This phrasing keeps Chapter 2 focused on the work that needs help and leaves the
formal role and method taxonomy to Chapter 5.

### Research Questions

**Author observation.** The current questions are too specific for a chapter
whose purpose is to establish why AI might be useful. Questions about learned
physical estimators belong in later technical chapters.

**Likely direction.** Candidate Chapter 2 questions include:

- How can a project determine which part of architecture work is limiting
  progress?
- When does AI reduce total engineering work rather than shift it into
  evaluation or review?
- What abstractions and interfaces are needed when hardware and software
  decisions can no longer be evaluated separately?
- How should an AI-assisted process be compared with a conventional process at
  comparable total cost?
- When does faster candidate production make architecture work harder to
  finish?

Move estimator-, method-, environment-, and verifier-specific questions to the
chapters that teach those subjects.

## Proposed Chapter 2 Argument

A candidate structure to test after feedback collection is:

1. Set the range of the present complexity problem.
2. Show how earlier architecture transitions introduced new abstractions,
   representations, tools, and checks.
3. Explain the current discontinuity in what a fair comparison must carry.
4. Walk through hardware scale, specialization, and composition.
5. Establish software as part of the architecture contract.
6. Add physical, evaluation, and verification limits.
7. Bring the pressures together through the scissors.
8. Diagnose where work is accumulating without overdeveloping a procedure.
9. Explain how different bottlenecks admit different forms of assistance.
10. Reconnect the complete argument through Lighthouse.
11. Close with broad field-level research questions.

This structure is provisional. It records the current editorial hypothesis and
does not authorize a rewrite until the remaining chapter feedback has been
collected.

## Chapter 3: Structuring AI-Assisted Design Work

### Chapter Purpose

Chapter 3 should answer the question that follows naturally from Chapter 2:

> If AI might help with system and chip design, how should architects organize
> the work so that it is systematic, reviewable, and repairable rather than an
> ad hoc collection of models, prompts, scripts, and tools?

The chapter should give a complete high-level life cycle. A technically
oriented leader who stops after Chapter 3 should still understand why structure
is needed, what the stages are, what each stage accomplishes, where feedback
returns, and which responsibilities remain with the team.

### Why the Current Opening Is Hard to Follow

**Author observation.** The chapter appears to follow Chapter 2, but its
opening flow is difficult to understand. It begins with a separate technical
problem, while the six-stage life cycle that seems to be the chapter's main
idea appears much later.

**Editorial diagnosis.** The current opening spends several paragraphs
distinguishing Chapter 2's finalist-package review queue from a separate cache
comparison. It then introduces a bounded study, an architectural claim, a large
study contract, an ontology chain, and multiple figures before presenting the
six stages.

The distinctions are technically careful but narratively expensive. The reader
must understand too many structural objects before seeing the organizing idea
that makes them useful. The opening also inherits a detailed operational
diagnosis from Chapter 2 that may itself move elsewhere.

**Likely direction.** Remove the separate-problem disclaimer from the opening.
Begin with the general need for a disciplined AI-assisted design life cycle.
Introduce the six-stage overview early. Use the Lighthouse cache comparison
later as one application of that life cycle rather than as the reason the
chapter exists.

### Why AI Makes Structure More Important

**Author observation.** The chapter needs a new early section that motivates
why applying AI requires a systematic approach. It should explain why teams
cannot simply assemble prompts, models, scripts, and tools ad hoc.

**Editorial assessment.** AI does not create every lifecycle problem, but it
amplifies several existing ones:

- Candidate artifacts and analyses can be produced faster than teams can
  evaluate them.
- Model behavior depends on training data, retrieved context, prompt state,
  tool state, and versioned inputs that may change independently.
- Probabilistic or learned outputs can vary even when the apparent request is
  unchanged.
- A model can optimize a local metric while exploiting an incomplete
  simulator, proxy, or tool interface.
- AI-assisted work may cross architecture, software, RTL, verification, and
  physical-design boundaries before any one person sees the complete chain.
- Hardware errors can survive into expensive and difficult-to-repair
  implementation stages.
- Multiple people, tools, and agents need explicit handoffs, checks, stopping
  conditions, and decision authority.

The chapter should present lifecycle structure as a way to localize failure,
preserve the design question, coordinate handoffs, and determine what a result
supports. It should not present lifecycle management as administrative process
for its own sake.

### Lessons to Synthesize from Adjacent Fields

**Author observation.** The chapter should draw on relevant ideas beyond the
papers or examples already familiar to the author. It should synthesize lessons
that help explain why disciplined AI-assisted work matters.

**Editorial direction.** Candidate traditions to investigate and synthesize
include:

- **Systems engineering:** Requirements, implementation, verification, and
  validation remain connected rather than becoming independent activities. The
  useful lesson from V-model thinking is the pairing of design decisions with
  corresponding checks, not a rigid waterfall schedule.
- **Experimental science:** A claim, comparator, conditions, measurements, and
  observations are separated so that an experiment can fail informatively.
- **Decision analysis and operations research:** The decision, alternatives,
  objectives, constraints, uncertainty, and value of additional information
  are declared before choosing a search method.
- **Software engineering and MLOps:** Versioned state, tests, reproducible
  environments, monitoring, and repair paths matter because code, data, models,
  and deployment conditions change at different rates.
- **Safety and assurance engineering:** A favorable result does not grant its
  own authority. Independent checks and named responsibility connect technical
  evidence to consequential action.
- **EDA and signoff practice:** Increasing fidelity, implementation checks, and
  signoff stages keep high-level choices connected to physical consequences.

The chapter should not become a survey or a table of borrowed methodologies.
It should extract a small number of common requirements for AI-assisted
architecture work:

1. preserve the question and intended decision;
2. make the current state and allowed changes explicit;
3. distinguish candidate production from valid execution;
4. match every important claim with an appropriate check;
5. retain failures and uncertainty rather than only successful outputs;
6. route inadequate work back to the place that can repair it;
7. keep decision authority explicit.

Primary sources should be selected only after this conceptual role is settled.

### Introduce the Six-Stage Life Cycle Early

**Author observation.** Formulate, Explore, Implement, Evaluate, Explain, and
Review and Decide appear too late. They seem to be the chapter's main teaching
device and should come much earlier.

**Likely direction.** After motivating why structure is necessary, show the
complete six-stage life cycle:

1. **Formulate** the question, comparison, constraints, and intended decision.
2. **Explore** legal alternatives within the declared space.
3. **Implement** or otherwise make a selected alternative executable in the
   relevant environment.
4. **Evaluate** valid tool returns against the declared checks.
5. **Explain** whether the proposed mechanism accounts for the result.
6. **Review and Decide** what the cumulative work supports, what needs repair,
   or why the effort should stop.

The first life-cycle figure should appear beside this overview. The chapter can
then explain why the stages are separated, when they can be combined, and how
feedback returns to the stage that owns an inadequate output.

### Audit the Stage Names

**Open question.** The current meaning of *Implement* is narrower than many
architecture readers will expect. In the chapter it means turning a candidate
into an executable tool request and confirming that the requested work ran. It
does not necessarily mean implementing RTL or committing a design to silicon.

Before revising the chapter, test whether the name can be defined clearly
enough or whether a term such as *Realize* or *Execute* would reduce confusion.
Do not rename the stage casually because the six-stage vocabulary recurs across
the manuscript and visual system.

### Structure Before the Detailed Contract

**Author observation.** The chapter should first explain how to think about the
life cycle, then show how the Lighthouse scenario is structured within it.

**Likely direction.** Move the detailed cache-study contract after the reader
has seen the full lifecycle. The contract can then instantiate Formulate rather
than appearing to define the whole chapter.

The current material on questions, comparators, scope, constraints,
measurements, budgets, stopping conditions, and exclusions remains valuable.
Its role becomes clearer when the reader understands which stage produces it
and how later stages consume it.

### Reduce the Number of Competing Structural Objects

**Editorial diagnosis.** The current first half introduces several related
objects in quick succession:

- bounded architecture study;
- architectural claim;
- study contract;
- ontology chain;
- six-stage life cycle;
- design loop;
- cumulative study record;
- design-loop card.

Each object can be useful, but their relationships are not immediately obvious.
The chapter should identify one primary map and reveal the supporting objects
only when the lifecycle needs them.

**Likely direction.**

- Use the six-stage life cycle as the chapter's primary organizing map.
- Treat the contract as Formulate's output.
- Treat the architectural claim as one component of that contract.
- Treat the represented state, methods, environments, and checks as
  capabilities that support stages rather than as a competing lifecycle.
- Treat iteration as a possible return within the life cycle.
- Treat the cumulative record as what survives the stages and handoffs.
- Treat the compact card as an index into that record, not as another framework.

Audit whether the ontology-chain and structured-layer figures remain necessary
once a single primary map is established. Preserve any figure that performs a
distinct explanatory job, but avoid asking the reader to reconcile several
nearly equivalent diagrams.

### Big-Picture Completeness

**Author observation.** Chapter 3 should not merely preview later chapters.
Nevertheless, a reader who stops here should understand the full approach.

**Likely direction.** Give the chapter a self-contained systems view. The
life-cycle stages rely on several persistent capabilities:

- represented design state and permitted changes;
- methods for generation, prediction, optimization, or conventional analysis;
- executable environments and tool interfaces;
- measurement, feedback, and independent checks;
- cumulative records, review, and decision authority.

Later chapters can deepen each capability without Chapter 3 reading as a table
of contents. A useful summary figure could place the six-stage lifecycle above
or inside these supporting capabilities. It should communicate the complete
operating model without naming chapter numbers.

### Handoffs Among People, Tools, and Agents

**Author observation.** One way to test the lifecycle is to imagine that its
work is handed to different people or agents. The team should still be able to
coordinate and understand what each participant must produce.

**Editorial assessment.** This is a powerful motivation for the stage
contracts. A handoff is safe only when the next participant knows:

- what question is being answered;
- which state and versions are authoritative;
- what changes are allowed;
- what input it receives;
- what output it must produce;
- which checks determine whether that output is adequate;
- where failures should return;
- what the output does and does not authorize.

The same logic applies to human teams, automated tools, and AI agents. Avoid
framing the lifecycle as a multi-agent architecture alone. The durable point is
that explicit handoffs let heterogeneous participants cooperate without
silently changing the problem.

### Lighthouse as an Application

**Likely direction.** After the life cycle and its supporting capabilities are
clear, apply them to one Lighthouse question. The cache example can show how a
broad product intent becomes a formulated comparison and then moves through
the six stages.

The example should no longer be introduced as a separate technical problem
whose lack of connection to Chapter 2 requires several disclaimers. It is one
concrete application of the general structure. Lighthouse callouts should
continue to pass the book-wide skip test and advance the secondary narrative.

### Candidate Chapter 3 Flow

A candidate structure to test after feedback collection is:

1. **Why AI-assisted design needs a life cycle.** Establish the risks of ad hoc
   assembly and the lessons synthesized from adjacent fields.
2. **The complete six-stage life cycle.** Show Formulate through Review and
   Decide immediately.
3. **Why the stages are distinct.** Explain outputs, checks, repair paths, and
   when adjacent stages can be combined.
4. **Formulating the Lighthouse study.** Introduce the contract and
   architectural claim as outputs of Formulate.
5. **Lighthouse through the life cycle.** Walk the same question across all six
   stages without pretending that later measurements have already been run.
6. **A record that survives handoff.** Explain the cumulative record and the
   compact card.
7. **The complete operating model.** Connect represented state, methods,
   environments, checks, records, and authority to the stages without turning
   the section into a preview of chapter numbers.
8. **Open field-level questions and conclusion.**

This structure should be judged against the final Chapter 2 revision. Chapter
3 should inherit Chapter 2's motivation without depending on a detailed queue
example that a reader must remember.

## Chapter 4: Building Architecture Data and Representations

### Chapter Purpose

Chapter 4 should answer a practical question:

> What data does AI-assisted architecture need, where can that data come from,
> what does each sample cost, how should it be curated, and how can the result
> be represented so that a model can learn from it and act on a design?

The chapter should begin with the data problem. Architecture data is
heterogeneous, expensive to acquire, difficult to label, often proprietary,
strongly dependent on tools and conditions, and biased toward successful
designs. The chapter should explain how to build useful datasets from those
sources before asking how current project knowledge is maintained.

### Why the Current Chapter Does Not Land

**Author observation.** The current opening begins with Chapter 3's cache-sizing
study and a section titled "From a Declared Study to a Represented Problem."
That assumes too much continuity and does not establish the chapter's own
purpose. Terms such as *architectural observation* and *study contract* sound
foreign to practicing architects and obscure the data question.

**Editorial diagnosis.** The current revision changed the center of the
chapter. The `dev` version was organized around:

- architectural knowledge;
- sources and datasets;
- the cost of acquiring a data sample;
- knowledge ingestion;
- representations and encodings;
- project state;
- cost models and world models;
- drift and provenance;
- semantic handoffs.

The current version is organized around:

- turning a declared study into a represented problem;
- identifying which source controls each field;
- maintaining current project state;
- recording history, authority, freshness, and permitted changes;
- exposing representation limits.

Much of the current material is useful, but it answers a narrower state-
management question. That question displaced the intended teaching about
building datasets, sample cost, ingestion, curation, encodings, and learned
knowledge.

**Likely direction.** Restore data acquisition and dataset construction as the
chapter's primary spine. Retain the strongest current material on source
conditions, failures, provenance, freshness, and legal changes as requirements
for a usable architecture dataset or project representation. Do not discard the
current chapter wholesale, but do not allow its state-management vocabulary to
define the chapter.

### A Standalone Opening

**Author observation.** Chapter 4 opens Part II and should stand on its own
while still building on the earlier argument. It should not begin by assuming
that the reader remembers a cache study or a detailed Chapter 3 contract.

**Likely direction.** Open with a general statement:

- AI systems learn from data and from the forms in which that data is
  presented.
- Architecture does not have an ImageNet-like supply of cheap, independent,
  consistently labeled samples.
- Useful data is distributed across specifications, software, RTL, traces,
  simulators, EDA flows, prototypes, silicon, failed runs, and engineering
  decisions.
- A data point has meaning only with the design, workload, software, tool,
  conditions, and property that produced it.
- Building that data infrastructure is therefore an architecture and systems
  problem, not only a model-training problem.

The Lighthouse example can appear later to make the sources and pipeline
concrete. It should not be needed to understand the opening.

### Historical Motivation

**Author observation.** The chapter may benefit from a short history of how
other fields built the datasets and shared tasks that enabled rapid progress.
The existing ImageNet discussion is a useful starting point.

**Editorial assessment.** Chapter 4 earns a historical opening because its
subject is data infrastructure. The history should teach a specific lesson,
not merely claim that large datasets produce breakthroughs.

Candidate cases to investigate include:

- ImageNet as a combination of a curated dataset, label structure, task, and
  evaluation protocol;
- large text and code corpora that enabled broad pretraining while introducing
  contamination, licensing, and provenance problems;
- scientific databases whose shared schemas made results comparable;
- architecture and EDA benchmarks, traces, contests, and open tool flows that
  enabled particular forms of comparison without becoming general training
  corpora.

The chapter should ask what the architecture equivalent would require and why
it is harder to build. Do not add a historical prologue to every chapter by
default. Use one here because it motivates the chapter's central engineering
task.

### Foundation Models

**Author observation.** The book says that AI might be applied to architecture
but does not clearly explain whether the intended mechanism is a foundation
model that can be adapted to downstream design tasks. Foundation models are
changing other fields and should appear somewhere in the book.

**Editorial assessment.** The book should explain foundation models, but it
should not equate all AI-assisted architecture with foundation models. Useful
architecture methods also include specialized predictors, surrogate models,
Bayesian optimization, reinforcement learning, retrieval systems, program
synthesis, and conventional analysis.

A foundation model is broadly pretrained on diverse data and then adapted,
conditioned, or connected to tools for downstream tasks. It does not
automatically understand a new architecture project, its private state, or its
physical constraints.

**Likely direction.**

- Introduce foundation models briefly when Chapter 1 first establishes the
  modern AI opportunity.
- Use Chapter 4 to explain the data, modalities, adaptation, retrieval, and
  project context such models would require.
- Use Chapter 5 to compare foundation-model-based methods with other prediction,
  generation, and optimization approaches.

Before writing this material, perform a focused primary-source review of the
term, its established definition, multimodal and code-model adaptation, and
current hardware or EDA foundation-model efforts. Avoid buzzword-driven claims
or the assumption that one universal chip model is the inevitable goal.

### What Counts as Architecture Data

**Likely direction.** Organize the chapter's sources in familiar engineering
terms:

- papers, manuals, standards, and specifications;
- software, compilers, runtimes, libraries, and tests;
- architecture models, configuration files, and parameter sweeps;
- RTL, typed intermediate representations, netlists, and physical constraints;
- workload traces, profiles, counters, and field telemetry;
- simulator, synthesis, timing, power, placement, routing, and verification
  results;
- FPGA, emulation, prototype, post-silicon, and fleet measurements;
- failed runs, rejected alternatives, waivers, review notes, and decisions.

For each source, explain:

- what it can teach;
- what it omits;
- how it is obtained;
- what it costs;
- what conditions give it meaning;
- whether it is public, proprietary, licensed, or privacy-sensitive.

The current source table and observation-source figure can contribute to this
section after their terminology and visual style are revised.

### Restoring the Cost of a Sample

**Author observation.** The chapter appears to have lost the earlier emphasis
on the cost of obtaining one architecture sample.

**Comparison against `Arch2/dev`.** The material was not completely deleted,
but it was demoted and reframed. The current chapter still includes:

- BOOM-Explorer evaluations taking roughly six to fourteen hours;
- distinctions among analytical, trace-driven, cycle-level, RTL, FPGA,
  emulation, and silicon sources;
- execution time, queue time, compute, memory, license, and human-work
  acquisition fields;
- the warning that equal row counts do not imply equal acquisition cost.

The `dev` chapter made the subject explicit through:

- a section titled "Weighing Data Sample Costs";
- a fidelity-and-volume pyramid;
- a table comparing sample-cost regimes;
- the incompatibility between data-hungry learning and expensive RTL or EDA
  feedback;
- active-learning and multi-fidelity approaches;
- the distinction between cheap synthetic data and scarce high-fidelity data.

**Likely direction.** Restore a visible section on sample economics. Combine
the `dev` chapter's clear data-building argument with the current chapter's
stronger sourcing, BOOM-Explorer example, and acquisition records.

The section should teach:

- one simulator call, synthesis run, physical-design run, or silicon
  measurement is not one interchangeable "sample";
- fidelity, workload coverage, tool cost, license use, setup, failure
  diagnosis, and expert review all contribute to acquisition cost;
- sample cost determines which learning and optimization methods are feasible;
- cheap data can map broad regions while scarce high-fidelity data checks
  boundaries and important candidates;
- failed and timed-out runs consume budget and should not disappear from the
  dataset.

### Building the Dataset

**Author observation.** The intended chapter should explain where data comes
from, how it is aggregated, cleaned, curated, and made useful. Examples include
gem5 logs and other simulator or EDA outputs.

**Editorial diagnosis.** The current chapter discusses source authority,
provenance, failure retention, contamination, and compatible conditions, but it
does not present them as one understandable dataset-construction pipeline.

**Likely direction.** Introduce a concrete pipeline:

1. **Define the task and properties.** State what the dataset must help a model
   predict, generate, rank, retrieve, or explain.
2. **Identify sources.** Select specifications, code, traces, tool runs,
   failures, measurements, and decisions relevant to those properties.
3. **Acquire records.** Run tools or collect existing artifacts while recording
   design, workload, software, configuration, tool version, seed, fidelity,
   status, and cost.
4. **Parse and normalize.** Convert heterogeneous reports into stable fields
   without discarding the original artifacts.
5. **Clean and qualify.** Detect malformed runs, stale inputs, empty outputs,
   inconsistent units, duplicated candidates, and incomparable conditions.
6. **Retain negative data.** Preserve failed, timed-out, censored, unroutable,
   and rejected cases with reasons.
7. **Split and protect evaluation data.** Control design-family leakage,
   workload leakage, benchmark contamination, and dependencies among related
   runs.
8. **Version and govern.** Record provenance, licensing, access, privacy,
   ownership, and changes to schemas or source tools.
9. **Create model-facing forms.** Produce text, sequences, graphs, tensors,
   spatial structures, trajectories, or retrieval indexes suitable for the
   intended method.
10. **Feed new results back carefully.** Add later tool results only after
    checking their identity, conditions, and status.

This pipeline should be explained in prose before being summarized visually or
in a table.

### Use Plain Terms for Data Records

**Author observation.** *Architectural observation* is not a familiar term and
reads like invented framework language.

**Editorial assessment.** The underlying distinction is valuable. Architecture
data is often a conditional measurement or tool result rather than a universal
label. The coined term is not needed to teach that point.

**Likely direction.** Prefer familiar phrases such as:

- measurement;
- simulation result;
- tool result;
- run record;
- data sample;
- design example;
- evaluation result.

Then explain that every such data point must remain associated with the design,
workload, software, tool, configuration, conditions, property, and run status
that produced it.

### Define Representation Before Using It

**Author observation.** The chapter uses *representation* without first
teaching what the word means, where the idea comes from, or what an
architectural representation should encode.

**Editorial assessment.** The chapter currently moves among several meanings:

- an architecture artifact or model;
- current project state;
- a model-facing encoding;
- a learned feature space or embedding;
- a collection of linked project records.

Those meanings must be separated.

**Likely definitions to develop.**

> **Representation.** A representation is a chosen form for expressing some
> properties of an object while leaving other properties implicit or absent.
> The choice determines what a person, model, or tool can inspect and change.

> **Architectural representation.** An architectural representation encodes a
> system's relevant structure, behavior, parameters, interfaces, software and
> workload relationships, constraints, and physical assumptions at a chosen
> level of abstraction.

> **Learned representation.** A learned representation is an internal set of
> features or embeddings acquired from data because they help a model perform
> one or more tasks.

The exact wording and intellectual history need a focused source review. A
footnote may help, but the main distinction belongs in the prose because it is
central to the chapter.

### Connect Architectural and Learned Representations

**Author observation.** The discussion should use the ML meaning of
representation and explain how data becomes embeddings or other model-facing
forms.

**Editorial assessment and pushback.** The chapter needs the ML lens, but it
should not use that lens alone. Computer architecture already relies on
explicit representations such as ISAs, block diagrams, performance models,
HDL, typed IRs, dependency graphs, traces, netlists, and floorplans. Learned
embeddings do not replace these tool-facing forms.

The distinctive synthesis is the connection:

> Raw architecture sources → qualified dataset → explicit architecture
> representation → learned representation or retrieval index → model output →
> executable architecture artifact → tool feedback

The chapter should explain where information can be lost at every translation.
A vector embedding may preserve statistical similarity while omitting a hard
legality constraint. A netlist preserves connectivity but may omit the design
intent that makes one connection preferable. A workload trace preserves
observed events while omitting behavior outside its capture policy.

### What an Architectural Representation Must Capture

**Likely direction.** Explain the requirements before cataloguing encodings.
Depending on the task, an architectural representation may need to capture:

- hierarchy, components, and connectivity;
- parameters and legal values;
- interfaces and protocols;
- workload and software behavior;
- mappings from software to hardware;
- timing, power, area, thermal, reliability, and security constraints;
- implementation state and physical assumptions;
- changes the method is permitted to make;
- relationships among versions and derived artifacts;
- uncertainty, unavailable information, and known blind spots;
- provenance linking a model-facing value back to its source.

No one representation needs to encode everything. It must preserve the
properties that can change the intended task or invalidate its result.

### Representation Forms

After defining the purpose, compare useful forms:

- natural language and retrieved documents;
- tables and parameter schemas;
- sequences and execution traces;
- graphs for hierarchy, connectivity, and dependencies;
- spatial tensors or grids for floorplans and physical data;
- typed intermediate representations for executable structure;
- multimodal combinations linking text, code, graphs, traces, and tool results;
- learned embeddings for retrieval, prediction, or generation.

Table 4.6's idea that a representation makes some properties explicit and
others difficult to express is valuable. It should follow the definition and
requirements rather than serve as the reader's first explanation of the term.

### Data, Knowledge, State, and Representation

**Editorial direction.** Explicitly distinguish four objects that the current
chapter partially collapses:

- **Dataset:** A collection of examples assembled for training, tuning,
  retrieval, or evaluation.
- **Knowledge source:** A specification, document, codebase, prior result, or
  other source from which relevant information can be obtained.
- **Current project state:** The authoritative design, software, workload,
  constraints, and unresolved conditions for the project now.
- **Representation:** The form in which selected properties of those objects
  are exposed to a person, model, or tool.

Model parameters, embeddings, retrieval indexes, and in-context information
then have distinct relationships to those four objects. The current chapter's
authority and freshness material can survive here after the distinction is
clear.

### Useful Current Material to Preserve

The current Chapter 4 contains valuable material that should not be lost in a
dataset-first rewrite:

- public architecture datasets support different tasks and often omit live
  project context;
- benchmark contamination can invalidate evaluation;
- failed, censored, and rejected runs reveal important boundaries;
- BOOM-Explorer makes high-fidelity acquisition cost concrete;
- source conditions determine whether two results are comparable;
- workload traces represent a sampled population, not all behavior;
- encodings shape neighborhood and search geometry;
- graphs, spatial forms, typed IRs, and schemas expose different properties;
- design state, generated artifacts, and dependent constraints can drift apart;
- rejected work and project history remain useful only under recorded
  conditions;
- provenance and cross-layer mappings help trace lower-level failures back to
  higher-level choices;
- known unknowns and blind spots should remain visible.

These ideas should support dataset construction and representation rather than
replace them as the chapter's central narrative.

### Material to Reconsider or Move

- The opening cache-study dependency should be removed.
- The detailed *study contract* language should not organize Chapter 4.
- *Architectural observation* should be replaced with ordinary engineering
  language.
- The current authority table may be retained in a smaller role after data,
  knowledge, state, and representation are distinguished.
- World models and method selection should be coordinated with Chapter 5 to
  avoid duplication.
- Operational execution and environment details should remain primarily in
  Chapter 6.
- Measurement interpretation and evaluation validity should remain primarily
  in Chapters 7 and 10.

### Figure 4.1 Visual Style

**Author observation.** Figure 4.1 uses rounded boxes, while the established
book figure style uses square rectangular corners.

**Confirmed defect.** The SVG contains rounded-corner `rx` attributes on the
question, selector, source group, source cards, and output record. This is
inconsistent with the current visual system.

**Likely direction.** Do not spend time merely restyling the existing figure
until the chapter structure is settled. It may be replaced or substantially
revised as a sources-to-dataset pipeline. Any retained boxes should follow the
established square-corner style.

### Candidate Chapter 4 Figures

The chapter may need two foundational visuals:

1. **Architecture data pipeline.** Sources flow through acquisition, parsing,
   qualification, curation, representation, model use, tool feedback, and
   controlled update.
2. **Data cost and fidelity.** Analytical models, traces, simulation, RTL and
   EDA, FPGA or emulation, silicon, and field data differ in cost, coverage,
   observability, and volume without forming one universal ranking for every
   property.

A third visual may connect explicit architecture representations to learned
representations and executable tool artifacts. Add it only if the first two do
not already make that relationship clear.

### Candidate Chapter 4 Flow

A candidate structure to test after feedback collection is:

1. **Why architecture needs a data strategy.** Explain why architecture data is
   different and why useful AI depends on deliberate data construction.
2. **What counts as architecture data.** Survey sources and the properties each
   can supply.
3. **What one sample costs.** Restore data economics, fidelity, coverage, and
   acquisition budgets.
4. **Building the dataset.** Cover acquisition, parsing, cleaning, failed runs,
   splits, contamination, versioning, governance, and controlled updates.
5. **From data to representation.** Define representation, architectural
   representation, learned representation, and the translation among them.
6. **Choosing an encoding.** Compare text, schemas, sequences, graphs, spatial
   forms, typed IRs, multimodal forms, and embeddings.
7. **Foundation models and project knowledge.** Explain pretraining, retrieval,
   adaptation, current project state, authority, and freshness without
   presenting foundation models as the only approach.
8. **A Lighthouse data and representation example.** Assemble the relevant
   sources, costs, dataset records, explicit state, and model-facing encoding.
9. **What the next method receives.** Hand Chapter 5 a well-defined data and
   representation problem without selecting the method in advance.
10. **Broad research questions and conclusion.**

This is a recovery-oriented structure. It should be compared carefully with
both the current chapter and `Arch2/dev` before any prose is changed. The goal
is to restore the intended data chapter while preserving later improvements in
source quality, quantitative grounding, failure retention, and provenance.
