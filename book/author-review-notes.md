# Architecture 2.0 Author Review Notes

**Review dates:** July 29–31, 2026
**Current scope:** Front matter, preface, and Chapters 1 through 11
**Editorial status:** Master feedback record. Some focused corrections have
already been made on the working branch, but observations in this document are
not automatically approved manuscript changes.

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

### Literature Packets Before Substantive Revision

**Author direction.** The book should synthesize established and current work,
not rely on remembered examples followed by citations added after the prose is
written.

**Editorial direction.** Before revising a chapter, assemble a focused source
packet for that chapter. The packet should contain:

- foundational work that established the chapter's central ideas;
- representative architecture, systems, EDA, software, and ML work that shows
  how those ideas are used;
- current work that changes what can reasonably be claimed;
- critical or negative results that expose limitations;
- benchmarks, datasets, and tools that make the field measurable;
- a short mapping from each source to the concept, example, figure, or claim it
  might support.

This is not a requirement to cite every relevant paper or turn the book into a
survey catalogue. The aim is to identify the intellectual foundations, compare
approaches fairly, and then distill what an architect needs to know. Primary
sources should carry technical claims wherever possible. Surveys may help find
the field, but they should not replace reading the work on which a chapter's
main conclusions depend.

The packet should be created before prose changes begin and kept separate from
the reader-facing narrative. A chapter earns space for a paper only when the
paper helps establish a durable idea, a revealing comparison, a quantitative
anchor, or an important limitation.

Run this as a dedicated research-and-synthesis exercise for every chapter:

1. Restate the chapter's unique question and the concepts it must establish.
2. Search broadly enough to identify the relevant fields, then narrow to
   foundational and representative primary sources.
3. Assemble and read the source packet, including systems that disagree,
   expose limitations, or solve the problem differently.
4. Compare the systems by the design choices that matter to the chapter rather
   than summarizing one paper at a time.
5. Distill the recurring principles, conditional choices, quantitative
   anchors, and open problems.
6. Revise the chapter from that synthesis, then check every major claim and
   example against the sources.

The output should read as the book's perspective on the field, not as a
chronological literature review.

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

### Section-Scale Reader-Flow Audit

**Author direction.** The final prose pass must test whether a reader can follow
the reasoning within each section. It is not enough to smooth sentences or
remove awkward wording. Paragraphs must form a necessary sequence, transitions
must name the connection when it is not obvious, and the section must deliver
the point promised by its heading.

**Editorial method.** Review one section at a time, with enough context to read
the chapter opening, the preceding section's conclusion, and the following
section's opening. For each section, have a fresh reader produce a short
reasoning map before proposing edits:

1. the question the section answers;
2. the claim or teaching job of each paragraph;
3. why each paragraph follows from the previous one;
4. what each figure, table, example, or callout contributes;
5. the conclusion the reader should carry forward; and
6. any point at which the reader must infer an unstated connection.

The reviewer should flag missing premises, abrupt topic changes, repeated
claims, premature detail, unsupported conclusions, and paragraphs that belong
elsewhere. It should not rewrite merely to create stylistic variation.

After the reasoning problems are corrected, run a separate prose-craft pass for
plain professional language, sentence rhythm, unnecessary signposting,
template-like openings, inflated abstractions, and other patterns that make the
text sound machine-written. A final chapter-level stitch pass should then check
section order and transitions without reopening sound section-level arguments.

**Placement in the queue.** Run this after citation and technical-grounding
corrections, because those corrections can change the local argument, and
before the final figure/table balance and continuous whole-book reading pass.
Pilot the method on one known rough section in Chapter 1 and one later chapter
before scaling it across the manuscript.

### The First Numbered Section Must Provide a Clean Entry

**Author direction.** A chapter can have a strong unnumbered opening and still
lose the reader when Section x.1 begins. The first numbered section must not
immediately unload a taxonomy, large table, framework, or long list of terms.

**Book-wide test.** During the section-scale reader-flow audit, examine every
Section x.1 separately. It should:

1. begin with a concrete question, situation, or distinction that follows
   naturally from the chapter opening;
2. establish why the first concept is needed before naming its full structure;
3. introduce distinctions in the order the reader needs them;
4. delay comprehensive tables until the prose has given the reader a reason to
   use them; and
5. end with a clear result that creates the need for Section x.2.

This is a conceptual-onboarding test, not a requirement that every first
section use the same rhetorical template.

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

### Chapter Opening as an Unnumbered Abstract

**Author observation.** The prose between the chapter title and Section 1.1
needs a clear and consistent purpose. Similar opening material appears in every
chapter, but it is not always functioning as a coherent introduction.

**Editorial assessment.** Keep this material unnumbered. A numbered
"Preamble" or "Abstract" would add another level to the chapter and make the
opening feel like a separate section. Instead, treat the unnumbered opening as
a chapter abstract with four jobs:

1. orient a reader who enters the chapter directly;
2. state the chapter's central question and why it matters now;
3. define the chapter's boundary without depending heavily on the previous
   chapter; and
4. preview what the reader will be able to understand or do by the end.

This convention should apply book-wide. The opening should not summarize every
section, introduce detailed evidence prematurely, or carry an argument that
belongs in Section x.1.

### Learning Objectives Need Reader-Level Outcomes

**Author observation.** The current learning objectives do not read as useful
learning objectives from the reader's point of view.

**High-priority editorial pass.** Rewrite the objectives after the chapter's
micro-flow is settled. Each objective should name a durable capability a
student, researcher, or practitioner gains from the chapter. Avoid using the
objectives as a contents list. For Chapter 1, the outcomes should center on
explaining the moonshot, unpacking a compact design request into a system and
chip design problem, distinguishing generated artifacts from supported
architecture results, and stating how progress toward the moonshot should be
judged.

### Section 1.1 Micro-Flow

**Author observation.** The opening discussion moves too quickly from AI
methods to scarce data and then to inference cost. Although each point matters,
the causal connection between the paragraphs is difficult to follow.

**Likely direction.** Run a sentence- and paragraph-level flow pass rather than
adding more facts. Establish the progression explicitly:

1. the field is *starting to apply* AI across architecture design tasks;
2. the relevant methods have different capabilities and roles;
3. architecture imposes domain-specific limits, beginning with scarce,
   expensive, and proprietary data; and
4. assistance also consumes resources, so its value depends on the total work
   and checking cost it changes.

Each paragraph should earn the next one. The prose should not preview the data,
methods, and evaluation chapters so densely that the moonshot disappears.
Change "The field is now applying AI" to "The field is starting to apply AI"
to avoid overstating maturity.

### Smoother Qualification of the Lighthouse Prompt

**Author observation.** "The prompt does not imply a single model or
invocation" is technically useful but arrives abruptly.

**Likely direction.** Connect it to the preceding explanation with a short
qualification such as "It is important to note that this prompt does not imply
a single model or invocation." Preserve the substantive point that Lighthouse
requires a coordinated design capability rather than one fluent response.

### Section 1.6 Transition into Efficiency

**Author observation.** The efficiency section begins abruptly and its
connection to the preceding XR discussion is unclear. Language that assumes
"the AI process can proceed" also sounds awkward.

**Likely direction.** Begin from the architecture question already raised by
Lighthouse. The XR target is useful because its latency, energy, thermal,
software, and physical constraints force the proposed assistance to improve a
real system result rather than merely produce more artifacts. From there,
explain why the cost of the AI-assisted process must be included in the
efficiency claim. Do not introduce AI overhead as an unrelated caveat.

### Book-Organization Sentence

**Author observation.** "The rest of the book is ordered by what each chapter
equips the design loop with, and it closes on who owns what the loop produces"
feels dropped into the surrounding argument.

**Open question.** Do not create a new section for a single navigation
sentence. Either integrate a brief roadmap into the unnumbered chapter opening
or place a concise "How the Book Proceeds" passage near the end of Chapter 1
only if readers genuinely need it. The roadmap should describe the intellectual
progression, not force every chapter into design-loop terminology.

### HTML Mathematics Escaping

**Confirmed defect.** At least one HTML rendering exposes literal LaTeX
delimiters around powers of ten, including the accelerator and SoC design-space
range. The PDF and HTML paths are not interpreting the same source form.

**Likely direction.** Locate the generated label or inline expression and use a
Quarto-compatible math form that renders in both formats. Include representative
powers, units, superscripts, and inline equations in the final HTML/PDF
cross-format audit rather than treating this as an isolated visual correction.

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

### Public, Web, and Community Data

**Author addendum.** Chapter 4 should consider sources beyond data generated by
one local tool flow. Public code, specifications, design repositories, web
material, benchmarks, and community contributions may help build an
architecture dataset. The chapter should explain both how such material is
collected and why collecting it is difficult.

**Likely direction.** Add public and community acquisition to the data-source
discussion. Candidate sources include:

- open RTL and hardware repositories;
- compiler, runtime, and kernel repositories;
- public issue trackers, patches, review discussions, and test failures;
- standards, manuals, papers, and technical reports;
- published benchmark suites and their associated artifacts;
- existing architecture and EDA datasets;
- contributed examples or annotations from domain experts;
- synthetic examples produced by generators or tools;
- simulator, synthesis, and verification runs produced specifically to fill
  gaps in the dataset.

The chapter should then explain the data-engineering work required to make
these sources useful:

- determine licensing, redistribution rights, privacy, and proprietary
  boundaries before collection;
- preserve the original source and revision;
- parse heterogeneous formats and normalize units and identifiers;
- remove exact and near duplicates without erasing meaningful design variants;
- connect natural-language descriptions to the correct code, constraints,
  tests, and tool results;
- distinguish complete designs from fragments, tutorials, generated examples,
  abandoned projects, and unverified code;
- detect contamination between training, retrieval, and evaluation material;
- split by project and design family rather than randomly splitting closely
  related files;
- record missing tests, weak labels, stale dependencies, and unknown tool
  conditions rather than converting them into clean-looking examples;
- use expert review selectively where only an architect, verification engineer,
  compiler engineer, or physical designer can qualify the record.

**Important pushback.** Web scale is not the same as architecture ground truth.
A large collection of Verilog files may help a model learn syntax and common
structure, but most files do not come with trustworthy specifications,
testbenches, synthesis conditions, timing constraints, physical results, or
proof of correctness. Community labels are also expensive when the question
requires domain expertise or a licensed tool flow. Public data may be valuable
for pretraining, retrieval, and candidate construction while remaining
insufficient for claims about function, power, timing, routability, or silicon
behavior.

This distinction is a useful architecture-specific lesson. Dataset building is
not only collection and cleaning. It is the work of connecting each example to
the property it can actually teach and the conditions under which that property
was established.

## Chapter 5: Choosing and Combining Methods

### Chapter Purpose

Chapter 5 should teach a student or practicing architect how to choose methods
for an AI-assisted design problem. The chapter's core families are prediction,
generation, and optimization. It should explain concrete techniques within
each family, what engineering job each technique can perform, what information
and feedback it needs, when it is a poor fit, and how multiple methods may be
combined.

The reader should leave able to answer:

- What am I trying to produce, estimate, or select?
- Is an added AI or statistical method needed at all?
- Which family fits the problem?
- Which concrete method within that family fits the artifact, data, design
  space, and evaluation budget?
- What feedback will the method receive?
- What simpler baseline should it be compared against?
- How should prediction, generation, and optimization interact in this
  particular problem?

The durable lesson is method fit, not a ranking of fashionable models.

### Section 5.1 Starts Too Fast

**Author observation.** Section 5.1 moves rapidly from the distinction among
engineering roles, method families, techniques, and system composition into
two dense tables and eight roles. The ideas may be individually useful, but
the reader has not yet been given a sufficiently gradual reason for needing
all of them.

**Editorial assessment.** This is a reasoning-flow problem rather than a
request for lighter wording. The section currently asks the reader to absorb
the smallest-sufficient-approach principle, four decision layers, eight roles,
their outputs and handoffs, conventional versus learned techniques, direct
tool use, foundation models, retrieval, and agents before the method-selection
problem has been made concrete.

**Likely direction.** Rebuild the entry methodically:

1. Begin with one familiar architecture task and show why "choose an AI model"
   is the wrong first question.
2. Establish the smallest-sufficient-approach principle through that example.
3. Introduce the distinction between the engineering job and the method used
   to perform it.
4. Add technique and system composition only after the first distinction is
   secure.
5. Decide whether all eight roles are necessary at this point. If they are,
   introduce them in meaningful groups and move the comprehensive handoff
   table after the prose has established those groups.
6. Preserve the useful claim that roles and method families form a
   many-to-many relationship.

The revision should not merely insert transition sentences between the two
tables. It should determine the minimum conceptual sequence a reader needs
before those tables become useful.

### Why the Current Opening Is Too Dependent on Earlier Chapters

**Author observation.** Chapter 5 begins by carrying forward the review queue,
the cache comparison, the represented identifier `XR-L2-CAP-A`, and other
details from Chapters 2 through 4. The chapters should build on one another,
but Chapter 5 should not require the reader to reconstruct those earlier local
examples before understanding its subject.

**Confirmed diagnosis.** The current opening spends several paragraphs
distinguishing the Chapter 2 review problem from the Chapter 4 cache study
before it states the method lesson. This makes the chapter read like a
continuation of one project record rather than the book's general treatment of
method choice.

**Likely direction.** Open with the general decision. Architecture offers many
possible methods, from analytical models and regression to LLMs, diffusion
models, Bayesian optimization, reinforcement learning, evolutionary search,
and mathematical solvers. The architect's problem is not to use all of them.
It is to identify the work that needs help, understand the available data and
feedback, and select the simplest method that fits.

The Lighthouse can return later as a worked application. It should demonstrate
the framework rather than supply the premises needed to understand it.

### The Current Chapter Is Concrete in Uneven Ways

**Editorial assessment.** Chapter 5 is not uniformly abstract. Its
optimization section already names and compares enumeration, random search,
deterministic heuristics, Bayesian optimization, evolutionary search,
reinforcement learning, mathematical programming, constraint solving, and
program search. It also uses AutoTVM, Ansor, ArchGym, AlphaChip, and PrefixRL as
examples.

Generation and prediction are less explicit:

- the generation section says *token-based models* instead of clearly
  introducing LLMs and other autoregressive code models;
- it mentions graph or spatial models and cites diffusion placement, but does
  not give students a clean map of generative choices;
- the prediction section refers to regression, graph models, learned
  surrogates, transition models, and world models, but does not compare the
  concrete predictive techniques a student might select;
- the method-choice tables emphasize inputs, outputs, checks, and costs but do
  not yet provide enough technical guidance on the algorithms themselves.

This imbalance likely explains why the chapter feels more concrete than
Chapter 4 while still stopping short of the promised methods chapter.

### Recover Technical Specificity from `Arch2/dev`

**Comparison against `Arch2/dev`.** The earlier chapter more directly named:

- large language models for textual artifacts such as RTL and compiler scripts;
- constrained decoding for syntax or schema restrictions;
- diffusion models for spatial artifacts such as placement;
- regression models and learned surrogates;
- graph neural networks for graph-structured circuit and netlist problems;
- physics-informed models;
- Gaussian processes, random forests, and tree-structured models for
  prediction-guided search;
- Bayesian and multi-objective optimization;
- evolutionary search, reinforcement learning, and constraint-based search.

Some of that specificity should return. The earlier chapter also carried a
large taxonomy of critique, repair, verification, coordination, trust, and
multi-agent organization. That material should not be restored wholesale.
Chapter 5 needs enough discussion of roles to distinguish the job from the
method, but Chapters 6 through 8 are better homes for environments, feedback,
verification, and loop operation.

### Separate Engineering Roles from Method Families

The current chapter makes a useful distinction that should be retained and
simplified.

- A **role** is the engineering job to be done, such as proposing an artifact,
  estimating a consequence, selecting an experiment, repairing a failure, or
  checking a property.
- A **method family** describes the main operation, such as generation,
  prediction, or optimization.
- A **concrete method** is the technique used to perform that operation, such
  as an LLM, regression model, graph neural network, Gaussian process,
  evolutionary algorithm, or solver.
- A **system** may combine methods, tools, data, and human decisions to perform
  several roles.

A method can perform more than one role, and one role can be implemented by
several methods. An LLM may generate RTL, propose tests, retrieve context, or
explain a failure. A graph neural network may predict congestion or help rank
placement candidates. Bayesian optimization combines a predictor with a
selection rule. The distinction should help the reader make choices, not
become another large taxonomy.

### Make Generation Concrete

The generation section should explain representative choices and the artifact
forms to which they are suited:

- templates, grammars, rules, and program synthesis for structured or
  precisely constrained artifacts;
- autoregressive language and code models, including LLMs, for specifications,
  RTL, tests, scripts, compiler code, and other sequential text;
- retrieval-augmented generation when project documents, code, or known
  patterns must be supplied at use time;
- graph-generative methods for netlists, connectivity, and other relational
  structures;
- diffusion or other spatial generative models for placement, floorplans, and
  spatial design objects;
- hybrid generators that combine learned proposals with deterministic
  construction, constraint solving, compilation, or repair.

The chapter should not merely list these methods. It should compare:

- what artifact is generated;
- what training or context data is required;
- which constraints can be enforced during construction;
- which properties remain impossible to establish without external tools;
- how many attempts and tool calls are likely to be consumed;
- when a conventional generator, compiler, library, or template is stronger
  than a learned model.

LLM-based RTL work, including VerilogEval and RTLLM, can show why syntax,
function, and quality of result are different goals. Diffusion placement can
show why a spatial artifact may call for a different inductive bias than
token-by-token generation. These examples should teach selection principles,
not serve as a leaderboard of current models.

### Make Prediction Concrete

Prediction should begin from a familiar architecture problem. Detailed
simulation, synthesis, placement, timing, or silicon measurement is expensive,
so a cheaper model estimates a consequence before every candidate receives the
full evaluation.

Representative choices to compare include:

- analytical and mechanistic cost models;
- linear, polynomial, and regularized regression;
- decision trees, random forests, and gradient-boosted trees;
- Gaussian processes when uncertainty and sample-efficient sequential
  evaluation matter;
- neural networks for large nonlinear datasets;
- graph neural networks for netlists, dependency graphs, and other structured
  design objects;
- sequence and transformer models for traces, programs, and time-dependent
  behavior;
- hybrid models that add learned corrections to analytical or simulator-based
  estimates;
- transition and world models for problems in which actions change the state
  on which later choices depend.

Students need guidance about choosing among these options. Data volume, feature
form, dimensionality, smoothness, interpretability, uncertainty, extrapolation,
training cost, and intended use all matter. A simple regression may be the
right answer when the relationship is stable and data is scarce. A graph model
may be justified when connectivity carries information that a flat feature
vector discards. A world model is justified only when modeling state evolution
adds value over scoring candidates independently.

The chapter should also distinguish several uses of a prediction:

- estimating a numerical value;
- ranking candidates;
- rejecting clearly poor candidates;
- predicting whether a constraint is likely to be violated;
- selecting where to spend a high-fidelity evaluation;
- modeling a state transition for a sequential decision.

The evaluation measure must follow the use. Average prediction error is not
enough when the real job is preserving the best candidates or avoiding false
acceptance near a hard limit.

### Keep World Models, but Put Them in the Right Place

**Author question.** Why should world models not appear in the chapter?

**Editorial judgment.** They should appear. A world model is a useful example
of a predictive method for sequential design work. It predicts how a represented
state changes after an action, possibly allowing a method to reason ahead
without invoking the full environment at every step.

It should not become a fourth family beside prediction, generation, and
optimization. It is a kind of predictive or transition model that can support
planning and optimization. The chapter should explain:

- what the state and action are;
- which transition or consequence is predicted;
- how prediction errors accumulate across multiple steps;
- when the real environment must replace the model;
- why a static surrogate is often sufficient for a one-step or
  candidate-independent problem.

This treatment preserves the idea without letting a fashionable term reorganize
the chapter.

### Make Optimization Concrete

The current optimization section provides a strong starting point. It should
retain the comparison among:

- enumeration and parameter sweeps;
- random search and domain-specific heuristics;
- mathematical programming and constraint solving;
- Bayesian optimization and active learning;
- evolutionary and population-based search;
- multi-objective optimization and Pareto analysis;
- reinforcement learning for genuinely sequential decisions;
- differentiable optimization when objectives and representations support it.

The key addition is to connect each method more clearly to problem structure.
Is the space small, continuous, discrete, mixed, graph-structured, or
sequential? Are evaluations parallel or sequential? Is there a trustworthy
surrogate? Are legality constraints executable? Does each action change later
choices? Are multiple objectives genuinely in tension?

Simple baselines are part of the method lesson. A learned optimizer should be
compared with enumeration where possible, random search under the same sample
budget, and a domain heuristic when architecture knowledge supplies one.

### Do Not Prescribe One Prediction–Generation–Optimization Order

**Author direction.** The chapter should explain the flow among prediction,
generation, and optimization and how a practitioner moves from one to another.

**Editorial judgment and pushback.** There is no universal order. The most
useful teaching device is a conditional flow based on the missing capability
and the cost of feedback:

1. If useful candidates or artifacts do not exist, generation may construct
   them.
2. If candidates exist but direct evaluation is expensive, prediction may
   estimate or rank their consequences.
3. If the legal space is larger than the evaluation budget, optimization may
   decide which candidates or experiments to try.
4. If the space is small and evaluation is affordable, direct tools,
   enumeration, or a classical solver may be better than any learned method.
5. If actions change future states, an optimizer may use a transition or world
   model for planning.

These conditions produce several valid flows:

- a generator proposes and a real tool checks;
- a predictor screens existing candidates before direct evaluation;
- an optimizer selects candidates using direct feedback with no learned
  predictor;
- an optimizer uses a predictor as a surrogate;
- a predictor guides generation toward promising regions;
- a generator expands the space, a predictor screens it, and an optimizer
  allocates scarce evaluations;
- tool feedback updates the predictor, generator, or search policy for another
  iteration.

Prediction may precede generation by conditioning it, follow generation by
screening its output, or sit inside optimization as a surrogate. Optimization
may control generation or select only among already existing candidates. Any
of the three may be absent. A triangle or decision map would communicate this
better than a linear pipeline.

### Connect Chapters 4 and 5 Without Making Either Dependent on the Other

Chapter 4 should establish where architecture data comes from, what it costs,
how a dataset is built, and how the relevant object is represented. Chapter 5
should then ask what can responsibly be done with the available data and
representation.

That relationship should not become a rigid handoff. Some generation can use
pretrained models, retrieval, rules, or tools without training a new model on
the Chapter 4 dataset. Some optimization needs only an executable objective
and direct feedback. Some classical methods need no learned representation.
Conversely, a rich dataset does not justify a complex method if direct
calculation or a simple model solves the problem.

The shared questions are:

- What information exists?
- In what form?
- How expensive is new feedback?
- What output is needed?
- Which method's assumptions match those conditions?

### Literature Foundation for Chapter 5

The Chapter 5 source packet should be organized around questions rather than
paper names.

**Prediction and surrogate modeling**

- early predictive architecture design-space exploration;
- regression modeling for microarchitectural performance and power;
- graph and spatial models for EDA consequences;
- uncertainty, calibration, and support limits;
- multi-fidelity and active-learning approaches under costly simulation or
  tool feedback.

The current citations to Ipek and colleagues and Lee and Brooks provide useful
historical anchors. They make the cost of simulation and the value of simple
predictive models concrete.

**Generation**

- program synthesis and constrained generation;
- LLM-based RTL, test, compiler, and kernel generation;
- VerilogEval, RTLLM, and related benchmarks that distinguish syntax,
  function, and design quality;
- graph and diffusion methods for spatial or relational design artifacts;
- tool-assisted generation and repair.

**Optimization and combinations**

- Bayesian optimization for expensive black-box evaluation;
- random and evolutionary search;
- multi-objective methods;
- reinforcement learning for sequential design decisions;
- AutoTVM and Ansor as systems that combine candidate construction, learned
  cost models, search, compilation, and measurement;
- ArchGym as evidence that no one optimizer wins across all architecture
  environments and budgets.

**World models and planning**

- foundational world-model and model-based control work;
- architecture or EDA cases in which state transitions matter;
- negative results or comparisons showing when static surrogates and direct
  feedback are sufficient.

The survey should deliberately include classical methods and strong baselines.
Otherwise, the chapter will teach students how to choose among AI techniques
without teaching them when AI is unnecessary.

### Candidate Chapter 5 Figures and Tables

1. **Method-choice triangle or map.** Prediction, generation, and optimization
   occupy three corners. Common systems lie inside or on edges according to the
   jobs they combine. Direct tools, analytical models, and solvers sit outside
   the triangle as valid alternatives rather than lower stages.
2. **Conditional method-choice flow.** Start from the needed output, available
   candidates, evaluation cost, design-space size, and sequential structure.
   End at a justified family or at no added method.
3. **Worked system decomposition.** Show how a system such as Ansor separates
   program construction, cost prediction, evolutionary selection, compilation,
   and hardware measurement. The point is to make the relationships concrete,
   not to recommend that exact stack.
4. **Method comparison table.** Compare representative methods by artifact or
   input form, data requirement, feedback cost, useful output, uncertainty,
   strong fit, and common mismatch.

The chapter already contains useful figures on the generation funnel,
prediction support, Bayesian optimization, and sequential placement. The
revision should decide whether each contributes to the chapter's selection
argument and remove duplication before adding more.

### Candidate Chapter 5 Flow

1. **The method-choice problem.** Many methods exist; the architect needs a
   disciplined way to decide which one, if any, fits.
2. **Roles, families, and concrete techniques.** Distinguish the engineering
   job, prediction/generation/optimization, and the implementation without
   building a large role taxonomy.
3. **What determines fit.** Use the needed output, artifact form, available
   data, legal design space, evaluation cost, uncertainty, and review budget.
4. **Generation.** Compare concrete generative approaches and the artifacts
   they suit.
5. **Prediction.** Compare concrete predictors, surrogates, transition models,
   and their intended uses.
6. **Optimization.** Compare search, solvers, Bayesian methods, evolutionary
   methods, and reinforcement learning by problem structure.
7. **Combining methods.** Explain valid conditional flows and why no universal
   sequence exists.
8. **Worked examples from the literature.** Decompose a small number of systems
   that reveal different combinations.
9. **Lighthouse method decision.** Apply the guidance to the recurring problem
   without requiring the reader to remember project identifiers.
10. **Broad research questions and conclusion.**

### Research Questions

The research questions should remain at the chapter's level:

- How can a practitioner predict which method family will repay its data,
  tuning, tool, and review cost before running a full study?
- How should methods be compared when they use different numbers and
  fidelities of architecture evaluations?
- When does a learned representation or model generalize across designs,
  workloads, tools, and process assumptions?
- How can generation preserve useful diversity while satisfying hard
  architectural and physical constraints?
- How should a system decide when to trust a surrogate and when to spend a
  high-fidelity evaluation?
- What problem properties make a sequential method or world model preferable
  to direct search or a static predictor?
- How should prediction, generation, optimization, and deterministic tools be
  composed without hiding which component produced a result or which check
  rejected it?

These questions are broad enough to define the field while remaining anchored
in method selection.

## Chapter 6: Building Environments Around Architecture Tools

### Chapter Purpose

Chapter 6 should teach what an environment is and how to build one around the
tools used in architecture, software, verification, and chip design. The
chapter should explain the parts of an environment, the interfaces among them,
what happens while work is running, and how results return to a person or
method.

The reader should leave able to answer:

- What is the difference among a tool, simulator, wrapper, harness, and
  environment?
- Which design and software state must be set up before a run?
- Which interfaces must be standardized, and what does that standardization
  buy?
- How are actions translated into tool-specific commands without changing
  their meaning?
- What must the runtime do about queues, parallel jobs, retries, resets,
  checkpoints, caches, licenses, and failures?
- Which state can a method observe, which actions may it request, and which
  results come back?
- How does the environment retain enough information to reproduce, compare,
  and diagnose its runs?
- Where does environment execution end and feedback or verification begin?

The durable lesson is that an environment is an engineered system around the
tools. It is not simply a simulator, shell command, or Python `step()` function.

### The Current First Section Is a Strong Starting Point

**Author observation.** Section 6.1 is useful because it distinguishes an
environment, wrapper, and harness.

**Editorial assessment.** Preserve this distinction:

- A **tool** performs a particular operation, model, analysis, transformation,
  or check.
- A **simulator** is one kind of tool. It models selected behavior at a stated
  level of abstraction and fidelity.
- A **wrapper** adapts one tool to a usable interface. It validates inputs,
  translates them into the tool's form, invokes the tool, and parses what came
  back.
- A **harness** coordinates runs and records what happened across tools,
  candidates, failures, retries, and costs.
- An **environment** is the complete tool-connected system exposed to the
  person or method. It includes the available state, permitted actions, tools,
  runtime, and returned observations.

The current example showing that a successful shell exit does not prove which
candidate, workload, model, or configuration was evaluated is concrete and
worth retaining. The example establishes why a wrapper and harness are needed
without inventing a new conceptual framework.

### Remove "Execution Contract" as the Organizing Idea

**Author observation.** *Execution contract* reads like another invented or
buzzword-heavy term.

**Editorial assessment.** The underlying engineering requirements are valid.
Before running a tool, a project must know:

- what design and software are being evaluated;
- which fields may change;
- which tool and version will run;
- which inputs and conditions it receives;
- which outputs are expected;
- what the run may cost;
- how failure, timeout, retry, reset, and cancellation work;
- what files and results will be retained.

Those requirements do not need a special name. They can be taught as the
environment's setup, interface, runtime policy, and result record. The large
current table called an *execution contract* should become either:

- a short table titled "What an environment must define before a run"; or
- four smaller examples placed in the corresponding setup, interface, runtime,
  and result sections.

The second option will probably read better. It avoids placing a large table
near the beginning and lets each requirement appear where the reader learns
why it matters.

### A Four-Part Environment Model

The author's proposed structure is a strong organizing model.

#### 1. Setup

The setup establishes everything on which a run depends:

- design revision and generated artifacts;
- software, compiler, runtime, libraries, and input data;
- workload and measurement interval;
- tool versions, models, process libraries, and configuration files;
- environment variables, seeds, host or container image, and permissions;
- licenses, compute, memory, storage, and time limits;
- clean starting state, reusable state, and unavailable dependencies.

This is more than installation. It ensures that a requested run refers to a
specific hardware–software system under identifiable conditions. Chipyard and
FireSim are useful examples because their productivity comes partly from
packaging compatible hardware, software, build, deployment, and simulation
elements rather than exposing a simulator alone.

#### 2. Interfaces and Tool Adapters

The interfaces define what a method can read, what it may request, and what each
tool returns. A wrapper adapts those common needs to a specific simulator,
compiler, EDA shell, formal engine, profiler, or measurement platform.

The chapter should explain:

- accepted inputs, parameter types, units, legal values, and dependencies;
- available actions and operations;
- capability discovery, including what the tool does not model or check;
- exact translation from a common request to tool-specific files, flags, or
  scripts;
- returned metrics, artifacts, warnings, and error classes;
- versioning and extension points when a tool exposes information that the
  shared interface does not.

The goal is not to make every tool appear identical. It is to standardize the
parts that allow methods, tools, and experiments to connect without private
glue code or ambiguous meanings.

A concrete interface may need common operations such as:

- inspect the available state and tool capabilities;
- validate a proposed action without running it;
- submit work and receive an attempt identifier;
- poll progress and obtain partial results;
- cancel work;
- reset to a known state;
- resume from a named checkpoint where the tool supports it;
- collect the final status, artifacts, metrics, warnings, and realized cost.

The exact operation names are not important. The chapter should teach why the
operations are needed and how their semantics remain stable across wrapper and
tool versions. Capability discovery, unit conventions, idempotent submission,
and schema evolution deserve explicit treatment because a method should not
have to guess whether an operation was duplicated or whether a field silently
changed meaning.

#### 3. Runtime and Orchestration

The runtime manages work after a request is accepted:

- dependency ordering across compilation, simulation, synthesis, verification,
  and physical design;
- parallel and asynchronous jobs;
- queue, scheduler, and license state;
- progress and partial results;
- timeouts, cancellation, retries, and escalation;
- clean resets, checkpointing, and caching;
- resource and tool-call budgets;
- isolation of generated code and tool scripts;
- recovery after tool, host, storage, or parser failures.

This section should retain the current chapter's important observation that
architecture and EDA tools are slow, stateful, and asynchronous. A clean
`reset()` and `step()` interface is useful, but it hides queues, licenses,
working directories, checkpoints, and returns that may arrive hours later.

The runtime should make those conditions visible without forcing every method
to reimplement scheduling and failure recovery.

Setup readiness should be a first-class runtime state. Before scheduling
expensive work, the environment should be able to report whether required
inputs, tools, licenses, storage, credentials, and compatible model or library
views are available. A setup failure is different from a candidate failure and
should be visible before possible.

#### 4. State, Observations, and Returned Results

The environment makes selected state observable and returns what happened:

- current candidate and fixed system context;
- queued, running, completed, cancelled, failed, and timed-out work;
- raw logs and artifacts;
- parsed metrics with units and conditions;
- warnings and output that the parser did not recognize;
- partial results and stages that never ran;
- realized runtime, compute, storage, license, and tool-call cost;
- links among the request, generated artifacts, tool invocation, and returned
  results.

This creates the information needed for a method to choose another action and
for an architect to diagnose the run. It does not by itself establish that a
metric is accurate, a comparison is fair, or a candidate is acceptable. Those
questions lead into Chapter 7.

### State, Action, Observation, and Feedback

**Author suggestion.** A state–observation–action loop may help organize the
interface and the returned feedback.

**Editorial judgment.** This is useful if the terms are kept precise and the
chapter does not force every architecture tool into a reinforcement-learning
formulation.

- **State** is the relevant internal condition of the design, software, tools,
  runtime, and outstanding work.
- **Observation** is the part of that state and its returned results exposed to
  the person or method.
- **Action** is a permitted request to change an artifact, invoke a tool, or
  perform another operation.
- **Feedback** is information from the returned result used to revise a model,
  choose another action, reject a proposal, or increase confidence.

The distinction between state and observation matters. A wrapper may expose a
summary of an EDA database without exposing every internal object. A queued job
is part of runtime state even though no design metric has returned. A partial
placement report is an observation even though routing and signoff have not
run.

The environment supplies observations and records where they came from.
Chapter 7 should determine how those observations become useful feedback,
which checks are independent, and what confidence they support. Chapter 6
should not call every scalar a reward or every failed run negative design
feedback.

Gymnasium's distinction between task termination and truncation transfers
usefully. A design task may reach its declared stopping condition, while an
attempt can also end because of a timeout, quota, cancellation, scheduler
eviction, or lost license. Those outcomes should not carry the same meaning.

### Why Standard Interfaces Matter

The chapter should make the benefit of standardization explicit. A useful
interface can:

- allow several methods to operate against the same tool or benchmark;
- allow one method to operate across several compatible environments;
- compare algorithms under the same actions, observations, workloads, and
  evaluation budget;
- replace or upgrade a tool adapter without rewriting the entire method;
- collect data in a consistent form across runs and fidelities;
- make failures, costs, and unavailable results visible;
- let researchers reproduce and extend previous experiments;
- reduce the amount of private, task-specific glue needed to enter the field.

OpenAI Gym and Gymnasium demonstrate how a small common interface can separate
algorithms from environments. CompilerGym applies that idea to real compiler
optimization tasks and adds datasets, fault tolerance, and reproducibility
checks. ArchGym connects several architecture simulators to search methods
through a common interface and budget. MLPerf shows a different benefit:
standard workloads, rules, and harness behavior make measurements comparable
across otherwise different systems.

MLPerf also provides a useful boundary among the system being tested, the
harness that drives it, and the checker that determines whether the result
meets the benchmark condition. Chapter 6 can use that separation without
importing MLPerf's entire benchmark policy into an architecture environment.

These examples support a durable conclusion. Standardization is most useful at
the boundary between a method and the engineering system it acts on.

### Do Not Force One Universal Hardware Interface

**Editorial pushback.** Standardization should not erase the meaning and
fidelity of individual tools.

A cycle-level simulator, compiler, RTL simulator, synthesis tool, router,
formal checker, FPGA prototype, and silicon measurement platform do not return
interchangeable observations. Their actions, failure modes, runtime, and
claims differ.

A practical environment needs:

- a small common core for identity, actions, lifecycle state, results, cost,
  errors, and provenance;
- tool-specific schemas for capabilities, inputs, outputs, units, warnings,
  and constraints;
- an explicit way to ask what a tool supports;
- refusal when a request cannot be represented without changing its meaning.

This is closer to a family of compatible interfaces than one universal API.
The principle should be semantic consistency, not identical JSON fields for
every tool.

### Multi-Tool and Multi-Fidelity Environments

Architecture work usually crosses several tools. One candidate may require:

- a compiler and runtime build;
- functional or ISA simulation;
- a performance model or cycle-level simulation;
- RTL generation and simulation;
- synthesis, placement, routing, timing, and power analysis;
- FPGA or emulation runs;
- measurements on hardware.

The environment should preserve one candidate's identity as artifacts branch
and change across those paths. It should also expose what each stage can and
cannot establish. A synthesis estimate must not appear to be a signoff result,
and a functional simulator must not return an implied timing conclusion.

The current Chapter 6 contains valuable material on:

- artifact identity across compilation, RTL, and physical tools;
- staged EDA results;
- multi-tool dependencies;
- tool throughput and evaluation cost;
- queues, retries, resets, checkpoints, and caches;
- partial output and parser failures.

These points should be retained, but organized as environment design elements
rather than as a detailed execution record for one cache study.

### Reproducibility and Reuse

The current chapter records versions, hashes, parent artifacts, resets, and
cached results, but it should more directly teach the differences among:

- **Replay:** rerunning the same recorded commands and inputs.
- **Repeatability:** obtaining sufficiently consistent results in the same
  environment under the same declared conditions.
- **Reproduction:** rebuilding or rerunning the work in a meaningfully
  independent environment.
- **Reuse:** using a prior artifact, checkpoint, or result because all
  conditions on which it depends still match.

A content hash identifies bytes. It does not prove that a build is reproducible
or that two artifacts are functionally equivalent. A replay can reproduce the
same configuration mistake. A cached result is safe only when every input on
which it depends, including workload, software, tools, models, flags, and
relevant hidden state, still matches.

The chapter should show a simple rerun procedure and explain which sources of
nondeterminism must be measured rather than assumed away. It should also
distinguish estimated cost used to plan a run from realized cost recorded after
the attempt.

### Failure Is Part of the Interface

The current failure taxonomy contains an important lesson. The environment
must distinguish:

- an invalid request that never reached the tool;
- missing or inconsistent setup;
- infrastructure, host, storage, queue, or license failure;
- tool failure;
- timeout or cancellation;
- missing, stale, partial, or unparseable output;
- a completed return that reports a design violation.

Collapsing these into *success* and *failure* can cause a method to learn the
behavior of a cluster or wrapper instead of the design space. At the same time,
the chapter should be careful not to infer architectural infeasibility merely
because the same tool failed repeatedly. A fixed resource limit, wrapper
defect, or unsupported case may reproduce just as reliably.

Use familiar engineering language such as status, error, warning, retry,
timeout, and incomplete result. Avoid turning the taxonomy into a new named
framework.

Reset should also be distinguished from restart. Restarting a process does not
necessarily restore a known design, tool database, cache, seed, or working
directory. A reset must identify which state was restored, discarded, or
retained.

### Parsing and Observability

Architecture tools often return text reports, databases, logs, waveforms, and
generated files rather than one clean value. A wrapper should provide
structured results without discarding the original artifacts or unfamiliar
warnings.

The chapter should explain:

- why raw output alone is difficult for both people and automated methods;
- why a parser must retain units, tool stage, conditions, and missing fields;
- why a zero exit status is not enough;
- why recognized fields and unclassified output should both survive;
- how large results can be summarized hierarchically while remaining
  inspectable;
- how parser versions and schema changes affect old records.

Avoid phrases from the earlier `dev` chapter such as *telemetry wall* and
*log-to-semantic parser*. Ordinary terms such as tool-output parser, structured
summary, raw log, and unrecognized warning communicate the same ideas.

### Comparison with `Arch2/dev`

The earlier `dev` chapter offered several useful subjects:

- the mismatch between a synchronous `step()` call and slow, stateful EDA
  tools;
- multi-fidelity architecture environments;
- stage-specific EDA outputs;
- a read/action/return interface;
- standardized hardware representations and interfaces;
- tool-output parsing;
- orchestration across tool graphs;
- process isolation, timeouts, and recovery;
- Chipyard as a full-system example;
- artifact identity and reproducibility.

It also relied heavily on coined or dramatic language:

- *human–API mismatch*;
- *semantic gap*;
- *three-path interface*;
- *safe-by-construction action space*;
- *telemetry wall*;
- *log-to-semantic parsers*;
- *environment contract*;
- a broad claim that an architecture environment should act like a database
  query planner.

The current chapter removed much of that language and strengthened
statefulness, failure handling, and attempt accounting. It then overcorrected
by centering another coined object, the *execution contract*, and by turning the
Lighthouse cache study into the chapter's main organizing example.

The revision should combine the best parts:

- the current chapter's precise environment/wrapper/harness distinction,
  asynchronous runtime, failure handling, cost accounting, and exact tool
  translation;
- the `dev` chapter's broader discussion of interfaces, full-system
  environments, multiple fidelities, tool-output parsing, and standardized
  representations;
- a new four-part structure using setup, interfaces, runtime, and returned
  observations.

### Frameworks and Papers to Study

The dedicated Chapter 6 source packet should include several kinds of systems.

**Standard environment interfaces**

- OpenAI Gym and Gymnasium for the separation between algorithm and
  environment, action and observation spaces, reset, termination, and
  interoperability;
- CompilerGym for adapting production compilers, exposing multiple
  observations and rewards, handling faults, and finding reproducibility
  defects;
- ArchGym for connecting architecture simulators to several search methods and
  comparing them under controlled evaluation budgets.

**Architecture and chip-design platforms**

- gem5 for modular simulation and configurable architecture models;
- Chipyard for connecting generators, software, simulation, FPGA, and VLSI
  flows;
- FireSim for packaging and scaling full-system FPGA-accelerated simulation;
- OpenROAD for an integrated, reproducible RTL-to-GDS flow;
- Hammer and modular flow generators for separating common flow structure from
  tool- and technology-specific adapters;
- representative commercial-style EDA flows for stateful shells, licenses,
  long runtimes, staged results, and proprietary data.

**Autotuning and search systems**

- AutoTVM and Ansor for the relationship among candidate construction, cost
  models, search, compilation, and target measurement;
- architecture design-space systems that combine analytical models,
  simulators, learned methods, and high-fidelity checks.

**Benchmark and workflow harnesses**

- MLPerf and MLHarness for workload definitions, rules, system descriptions,
  submission interfaces, and comparable measurements;
- workflow systems such as Snakemake and Nextflow where their handling of
  dependency graphs, caching, retries, and distributed execution provides a
  genuinely transferable lesson.

**Tool-using AI systems**

- ChatEDA and more recent tool-interactive EDA systems;
- InterCode and similar executable tool environments for iterative actions,
  observations, reset, and isolation;
- hardware-agent benchmarks that pin repositories, toolchains, tests, and
  runtime environments;
- negative or comparative studies that separate model capability from harness
  and environment design.

**Provenance and packaging**

- established provenance models such as W3C PROV for the minimal relationships
  among artifacts, activities, and actors;
- ReproZip and related packaging work for capturing data dependencies,
  libraries, configuration, and replay procedures.

These sources can help the chapter use established concepts without turning
provenance into a new author-specific vocabulary. Provenance shows where an
artifact came from; it does not prove the result is valid or reproducible.

The purpose is not to name every framework in the finished chapter. It is to
identify recurring design choices and work backward to the principles that
generalize.

### Recurring Patterns to Test in the Literature

The source review should determine how consistently the following patterns
appear:

- separate the method from the environment through a stable interface;
- define legal actions and meaningful observations;
- expose tool capabilities and fidelity limits;
- package the full hardware–software setup, not only the central simulator;
- keep workload, design, software, tool, and condition identities together;
- make execution asynchronous when tools are slow;
- distinguish infrastructure failure from candidate results;
- retain raw artifacts alongside structured summaries;
- control evaluation count, runtime, compute, licenses, and storage;
- support clean reset, caching, checkpointing, and reproducible replay;
- preserve candidate identity across several tools and transformed artifacts;
- provide simple extension points for new tools and methods;
- avoid letting the harness silently change the problem being studied.

These are hypotheses for the source review, not conclusions to impose on the
literature.

### Candidate Chapter 6 Figures and Tables

1. **Anatomy of an architecture environment.** Show setup and design state
   feeding standardized interfaces, wrappers around several tools, a runtime
   that schedules them, and observations returning through the harness.
2. **State, action, and observation across time.** Show asynchronous jobs,
   partial results, completion, and failure rather than a single instantaneous
   `step()`.
3. **One candidate across several tools.** Connect software, simulation, RTL,
   EDA, and hardware paths while preserving candidate and condition identity.
4. **Interface comparison table.** Compare Gymnasium, CompilerGym, ArchGym,
   Chipyard/FireSim, and MLPerf by what they standardize and what remains
   domain-specific.
5. **Failure and result table.** Keep a compact version of the current failure
   taxonomy if it materially helps the reader decide what the runtime should
   return.

The current interface, artifact-identity, and multi-tool figures should be
audited against these jobs before adding new visuals.

### Candidate Chapter 6 Flow

1. **What an environment is.** Distinguish tools, simulators, wrappers,
   harnesses, and environments.
2. **Why architecture needs engineered environments.** Explain heterogeneous
   tools, full-system state, cost, long runtimes, failures, and proprietary
   constraints.
3. **Setup.** Establish hardware, software, workload, tools, resources, and
   clean state.
4. **Interfaces and wrappers.** Define actions, observations, capabilities,
   exact translation, and standardization.
5. **Runtime and orchestration.** Cover dependencies, asynchronous execution,
   queues, licenses, budgets, retries, reset, checkpoints, caching, and
   isolation.
6. **Observations and returned results.** Cover raw and structured output,
   partial results, status, cost, and provenance.
7. **Multi-tool and multi-fidelity environments.** Preserve one candidate
   across compiler, simulator, EDA, FPGA, and hardware paths.
8. **Patterns from existing systems.** Distill a small number of concrete
   frameworks rather than presenting a catalogue.
9. **Lighthouse environment.** Apply the component model without returning to
   large project identifiers and a contract table.
10. **A practical design recipe.** Inventory tools and dependencies, establish
    setup readiness, define capabilities and interfaces, adapt each tool,
    isolate and run work, expose lifecycle operations, parse results, retain
    cost and provenance, and fault-test the harness.
11. **What Chapter 7 receives.** Hand forward observations, failures, costs,
    and tool results whose meaning and confidence still need to be assessed.
12. **Broad research questions and conclusion.**

### Research Questions

The chapter's research questions should remain at the level of environment
design:

- Which parts of an architecture environment can be standardized across
  simulators, compilers, EDA tools, prototypes, and silicon?
- How should an interface expose capability and fidelity so a method cannot
  request or infer properties the tool does not support?
- How can a runtime schedule expensive, asynchronous tool calls while sharing
  licenses and computing resources with human engineers?
- What state must be reset, versioned, or retained so that repeated runs remain
  comparable?
- How should environments distinguish infrastructure, wrapper, tool, and
  candidate failures when the immediate symptoms are similar?
- How can large, heterogeneous tool outputs be summarized for automated use
  without hiding unfamiliar warnings or important detail?
- What makes an environment reusable across methods while remaining faithful
  to domain-specific tool semantics?
- How much observed performance difference comes from the method, and how much
  comes from the wrapper, harness, tool configuration, or runtime?

These questions make the environment itself a serious systems and architecture
research subject without inventing a private vocabulary for it.

## Preliminary Structure Checkpoint: Chapters 6 through 11

This checkpoint records the author's evolving view of the final part of the
book. It is not yet a detailed review of Chapters 7 through 11.

### Two Meanings of Execution

The word *execution* currently risks joining two different subjects:

1. **Tool execution.** How an environment sets up, invokes, monitors, and
   records compilers, simulators, EDA tools, prototypes, and measurements.
   This belongs in Chapter 6.
2. **Design-loop execution.** How a team repeatedly proposes, evaluates,
   revises, allocates effort, decides when to escalate, and eventually stops.
   This belongs in Chapter 8.

Chapter 7 sits between them. It explains what the returned observations mean,
how they become feedback, which checks provide confidence, and how results can
support learning or revision.

Keeping these meanings separate avoids turning Chapter 6 into the entire
design loop or reducing feedback and verification to a runtime callback.

### Recommended Sequence

The current conceptual sequence remains strong:

| Chapter | Unique job |
| --- | --- |
| **6. Environments** | Build the tool-connected system that can execute work and return identifiable results. |
| **7. Feedback, Verification, and Learning** | Determine how results become useful feedback, how properties are checked, and how confidence is gained. |
| **8. Running the Design Loop** | Operate the iterative process across people, methods, environments, feedback, budgets, and stopping decisions. |
| **9. General Patterns Across Design Problems** | Identify what transfers across architecture problems and what remains problem-specific. |
| **10. Evaluation and Red Teaming** | Evaluate the resulting designs and the AI-assisted system or process that produced them. |
| **11. The Architect's Role** | Explain what architects own when more proposal, analysis, and tool operation can be automated. |

This order creates a progression from machinery, to meaning, to repeated
operation, to generalization, to evaluation, and finally to professional
responsibility.

### Chapter 7 Should Not Become "Running the Loop"

**Author thought.** With data, methods, and environments established, Chapter 7
might cover execution or the execution loop.

**Editorial pushback.** Preserve Chapter 7 as the feedback and verification
chapter. Verification is a central architecture problem and deserves a full
conceptual treatment:

- what an observation actually measures;
- whether the property was checked independently;
- how functional, performance, power, timing, physical, security, and system
  checks differ;
- where formal verification fits;
- how failures guide repair or another experiment;
- how repeated feedback supports learning;
- how confidence grows and where it remains incomplete.

If this material is folded into loop operation, the book risks teaching how to
run an automated process without teaching why its returned results deserve
belief.

Chapter 8 can then show how feedback is used while the loop runs: which action
comes next, which result causes revision, when a method changes, how budgets
are allocated, and when the team stops.

### Chapter 9 Needs a Clear Meaning of "Design Problem"

Chapter 9 should generalize patterns across several kinds of work, such as:

- microarchitecture configuration;
- hardware–software partitioning;
- compiler and runtime mapping;
- RTL and verification work;
- physical design;
- system configuration and deployment.

The purpose is not to claim that one loop or method solves all of them. It is
to ask which structures recur: expensive feedback, mixed discrete and
continuous choices, proxy objectives, multiple fidelities, constrained actions,
tool-dependent observations, cross-layer interactions, and human decisions.

### Chapter 10 Has Two Evaluation Subjects

**Author direction.** After the loop produces a design or recommendation,
Chapter 10 must explain what to evaluate about both the result and the AI
system or agent.

This distinction should organize the chapter.

**The design or recommendation**

- correctness and specification compliance;
- performance, power, area, cost, and other architecture objectives;
- robustness across workloads, corners, configurations, and failures;
- physical feasibility, security, reliability, and maintainability;
- improvement relative to appropriate baselines and alternatives;
- uncertainty and limits on the claim.

**The AI-assisted system and process**

- task success and failure rate;
- quality relative to a human, heuristic, solver, compiler, or other baseline;
- generalization across designs, workloads, tools, and unseen conditions;
- number and fidelity of simulator, tool, prototype, or hardware calls;
- model calls, tokens, runtime, compute, licenses, and monetary cost;
- sample efficiency and time to a usable result;
- invalid actions, broken artifacts, retries, and recovery;
- human review, intervention, and correction effort;
- calibration, robustness, security, backdoors, contamination, and red-team
  behavior;
- reproducibility and sensitivity to the harness or environment;
- ablations that identify which method, tool, data source, or feedback
  mechanism produced the improvement.

The chapter should distinguish three questions:

1. Did the process produce a good design?
2. Was the process itself effective and economical?
3. Did the AI component contribute beyond the existing tools, baselines, and
   human effort?

This prevents a strong final design from hiding an ineffective agent and
prevents a high agent task score from substituting for a useful architecture
result.

### Chapter 11 Should Emerge from the Earlier Boundaries

The final chapter should become easier once Chapters 6 through 10 are stable.
Its argument should follow from the responsibilities that could not be
delegated in the earlier chapters:

- framing the architecture question;
- deciding which constraints and tradeoffs matter;
- choosing what must be represented and measured;
- selecting methods and tools;
- judging whether feedback supports a claim;
- deciding when the loop should continue, change, or stop;
- accepting responsibility for the recommendation and its consequences.

Chapter 11 should synthesize these responsibilities rather than introduce a
new framework at the end of the book.

## July 30–31 Continuous-Read Feedback

This section records feedback from the continuous review of the rebuilt PDF and
HTML edition. It supplements the chapter notes above. Repeated observations are
kept here when the later reading sharpened the general lesson or identified a
specific rendered defect.

### Editorial Judgment, Not Mechanical Agreement

**Author direction.** The editor should continue to push back when a suggested
change would weaken the book, repeat material, overfit one local example, or
make the lecture age quickly. Author comments are observations and seeds for
reasoning, not instructions to accept without review.

**Editorial implication.** For every material proposal:

1. restate the reader problem that prompted it;
2. test it against the chapter's unique job and the book-wide argument;
3. compare it with the smallest repair that would solve the problem;
4. identify any repetition, scope expansion, or durability risk; and
5. record whether the proposal is accepted, modified, deferred, or rejected,
   with a brief reason.

### Chapter Openings and the Unnumbered Preamble

**Author observation.** The prose after the guiding question functions like a
spoken introduction to the chapter. Some openings, especially Chapter 1, feel
rushed. Chapter 2 is a useful positive example because it takes several
paragraphs to establish the problem, connect the pressures, and create the need
for the first numbered section.

**Author observation.** Chapter 4 makes the structural question especially
visible. Its unnumbered opening provides a useful introduction, while Section
4.1 begins directly with the technical material. This raises three possible
forms:

1. keep the introduction unnumbered after the guiding question;
2. merge it into Section x.1; or
3. make it an explicit numbered overview section.

**Open decision.** Do not change this book-wide structure piecemeal. Compare
the three forms across all chapters first.

**Current editorial recommendation.** Keep the opening unnumbered. It is the
chapter's abstract-like spoken introduction, while Section x.1 begins the
argument. Making every opening an “Overview” section would add mechanical
headings and renumber the chapter without adding intellectual structure.
Merging it into Section x.1 would often blur the distinction between orienting
the reader and developing the first technical claim. The opening should be
long enough to perform its job, but three or four paragraphs are a useful
diagnostic rather than a quota.

Each chapter opening should:

1. orient a reader who enters the chapter directly;
2. state the practical or intellectual pressure;
3. explain the chapter's governing distinction;
4. establish why the first numbered section is the necessary next move; and
5. avoid revealing the chapter's entire taxonomy or worked result.

The opening should not depend strongly on the previous chapter. The book should
build naturally, but every chapter needs enough local context to stand on its
own.

### Section Hierarchy and Singleton Subsections

**Author observation.** An H2 section that contains only one H3 subsection
often looks structurally artificial. Section 3.8.1, “A Record Another Architect
Can Review,” is one example.

**Likely direction.** Audit the full heading tree. When an H2 contains only one
H3:

- promote the H3 to H2 if it carries an independent teaching job;
- fold the H3 into its parent when it is merely the parent's continuation; or
- retain it only when the heading provides genuine navigation, is referenced
  elsewhere, or preserves a parallel structure that readers use.

This should be a structural judgment, not a blanket linter rule. A singleton
subsection is a warning signal, not automatically an error.

### Cross-Chapter Development Without Dependency

**Author thought.** Chapter 3 may need to say that later chapters develop
different parts of the life cycle. The chapter should still deliver the full
high-level picture so a reader who stops there understands the approach.

**Likely direction.** Add one restrained statement in the Chapter 3 opening or
conclusion that the life cycle is the organizing structure that later chapters
develop. Avoid attaching a chapter number to every stage or inserting uneven
phrases such as “Chapter 4 explains this” throughout the body. If explicit
navigation is useful, place one balanced map in a single location.

### New Artifacts Must Respect Existing Architecture Practice

**Author observation.** Terms such as *study record* and *design-loop card* can
make experienced architects skeptical. They may sound like new administrative
objects even though existing teams already keep related information in issue
trackers, experiment dashboards, design documents, version-control systems,
review packets, and tool databases.

**Book-wide lesson.** Whenever the lecture introduces a named artifact,
framework, role, or record:

1. acknowledge the existing practice it builds on;
2. explain the gap that existing practice does not reliably close;
3. state whether the proposed object is a new artifact, a common view over
   existing artifacts, or only a teaching abstraction;
4. avoid implying that every organization needs another form or database; and
5. give a concrete example of how it could map onto tools architects already
   use.

For Chapter 3, the likely framing is that the card is a compact index or review
view over existing project artifacts. It should not become the life cycle
itself or prescribe a universal project-management format.

### Research-Question Structure

**Author observation.** The current open-research-question sections make the
theme labels and the questions visually difficult to distinguish. The
questions can also become long and convoluted.

**Author direction.** A reader should be able to identify a question quickly,
understand why it matters, and see a credible path toward a top-tier systems,
architecture, EDA, or ML paper. Chapter 1 should open broad field questions.
The middle chapters should become more technical and precise. Chapter 11
should widen again to the implications for the field.

**Likely presentation.**

- Keep each theme as a short bold lead followed by one framing sentence.
- Present the questions as bullets beneath the theme.
- Begin each bullet with the question in bold.
- Keep the explanation in regular text. It should name the technical tension,
  possible experimental handle, or condition that makes the problem
  nontrivial.
- Use more than one question only when the theme genuinely contains distinct,
  paper-sized problems.

Bullets provide the hierarchy, so italics are probably unnecessary. The
formatting can be refined later; the intellectual quality and readability of
the questions come first.

**Open naming question.** “Open Questions” may be cleaner than “Open Research
Questions.” Decide once for the whole book after checking whether the shorter
heading still signals the intended research level.

### Figures and Tables Must Carry an Argument

**Author direction.** A figure or table should never be dropped into the
chapter and left for the reader to decode. The surrounding prose should explain
the comparison, relationship, or trend that matters and state what the reader
should take away. Avoid formulaic instructions such as “read the table from
left to right” unless the reading order itself is genuinely important.

**Book-wide audit.** For every figure and table, check:

1. why it appears at that point in the argument;
2. what visual relationship the reader should notice;
3. whether the prose interprets that relationship without narrating every
   decorative detail;
4. whether the caption states the main claim rather than merely naming the
   contents;
5. whether the visual duplicates nearby prose or another visual; and
6. whether its visual weight is appropriate for the section.

### Figure Geometry and Visual Consistency

**Confirmed defects and author observations.**

- Connectors must not run through boxes, labels, or other connectors.
- Arrowheads should meet box edges cleanly rather than stop short or sit inside
  a box.
- A figure should not repeat a large internal title when the caption and
  surrounding section already supply the title. Figure 1.4's “Reusable learning
  supports a larger architecture design system” is one example.
- Some generated figures use strongly rounded boxes while the established
  diagrams use clean rectangles. Figure 4.2 exposes the inconsistency.
- All generated SVGs need a complete audit, not isolated repairs to the figures
  noticed during skimming.

**Current editorial recommendation.** Use clean rectangular architectural
blocks as the default. A small, consistent corner radius may distinguish a
secondary callout or state, but large rounded “application card” shapes should
not become a competing visual language. Preserve semantic group boundaries and
accessibility metadata even when visible titles are removed.

### Figure 2.10 Newline Defect

**Confirmed defect.** A literal `/n` or escaped newline appears in the rendered
Chapter 2 figure label. Check both source strings and the rendered PDF and HTML
output after correction.

### Figure 2.13 Scissors

**Author observation.** The figure says that design work can outpace the
capacity to examine it, but the current lines begin after they have already
diverged. The prose calls the relationship “the scissors,” while the visual
does not clearly show the blades crossing.

**Likely direction.** Extend the curves far enough back to show an initial
regime in which evaluation capacity can absorb the arriving work, the
crossover, and the widening post-crossover gap. Do this only as a conceptual
model, not as a claim that an uncited historical crossing occurred at a
particular date.

### Chapter 1 Continuous-Read Notes

**Chapter purpose.** Chapter 1 must open the space and establish the moonshot.
It should invite the field into the broad problem rather than begin at the
technical specificity expected in the middle chapters.

**Learning objectives.** The current objectives do not consistently read as
capabilities the reader will gain. Rewrite them from the reader's point of view
and avoid dense inventories of internal vocabulary.

**Section 1.1 micro-flow.** The opening paragraphs move too quickly among the
fact that the field is starting to apply AI, architecture data scarcity, AI
cost, and the Lighthouse prompt. The reader must infer the connection among
these claims. Rebuild the paragraph sequence so each paragraph creates the need
for the next.

**Wording correction.** Prefer “The field is starting to apply AI to the design
processes...” over “The field is now applying AI...” The stronger formulation
overstates the maturity and prevalence of the transition.

**Data paragraph.** The contrast with software data and the implications for
architecture arrive too abruptly. Explain why architecture data is scarce,
costly, heterogeneous, or closely held before drawing consequences for learned
methods.

**AI cost paragraph.** Connect inference cost, simulation cost, and evaluation
capacity to the moonshot rather than presenting them as an independent warning.

**Prompt qualification.** Replace the abrupt opening “The prompt does not imply
a single...” with a smoother signpost such as “It is important to note that the
prompt does not imply a single...” or an equally natural sentence.

**Section 1.6.** The transition into efficiency is rough. Explain why the XR
example makes efficiency part of the architecture problem and why any
AI-assisted process must justify its own cost. Do not begin with an awkward
assumption that the AI process can proceed.

**Book organization.** “The rest of the book is ordered by what each chapter
equips the design loop with...” arrives abruptly. Either give book organization
its own short, deliberate passage or remove the sentence.

**Overused terminology.** Continue the book-wide audit of “bounded study.”
Use *study* unless the boundary itself is the point.

**Chapter opening.** The unnumbered introduction feels rushed compared with
Chapter 2. Expand it only to perform the opening functions described above, not
to preview the whole book.

### Chapter 2 Continuous-Read Notes

**Positive model.** The Chapter 2 opening is a useful model for pacing and
causal progression. Preserve its strengths without forcing every chapter into
the same paragraph template.

**Sections 2.1 and 2.2.** The prose in Section 2.1 is individually strong, but
the destination of the section is not yet clear to the reader. Sections 2.1 and
2.2 operate at a macro level, while Section 2.3 begins the detailed diagnosis.
Make that progression explicit. Section 2.1 should establish how architecture
has historically absorbed complexity through abstractions, interfaces,
benchmarks, tools, and shared checks. Section 2.2 should then show why the
technology conditions that supported earlier progress have changed. Together
they should create the need for the hardware, software, physical, evaluation,
and verification pressures that follow.

This does not necessarily require moving the sections. A clearer section title,
a sharper opening claim, and a closing bridge may be enough. The repair should
make the two macro sections feel like the premise of the detailed argument
rather than a separate history essay.

**Wafer-scale and warehouse-scale systems.** These two topics feel rushed
relative to the size of the systems and the importance of the boundary change
they represent. Consider whether the current “Hardware Scale, Specialization,
and Composition” section is carrying two different arguments:

1. complexity grows within a chip and package through microarchitecture,
   specialization, SoCs, and chiplets; and
2. the boundary of the computer expands beyond the package through wafer-scale
   fabrics and warehouse-scale systems.

One candidate structure would let “Scale Creates Large Search Spaces” conclude
the first argument after SoC and chiplet composition, then introduce a new H2
for the expansion beyond the package, with wafer-scale and warehouse-scale
systems as its two H3 subsections. This is preferable to promoting each topic to
an isolated H2 unless each earns enough material to carry a complete section.
The revision must remain a synthesis of why these scales change architecture
work, not become a short survey of two large fields.

**Wafer-scale memory.** Investigate whether distributed SRAM capacity,
bandwidth, placement, repair, and communication provide a useful concrete
example of why wafer-scale architecture cannot be understood from peak compute
alone. Add it only if primary literature supports a durable architectural
lesson and it connects to the section's argument.

**Dangling short paragraphs.** The two short paragraphs before the Bulldozer
war story look detached from the surrounding argument. The first observation
about inexpensive energy proxies likely belongs with the preceding
multifidelity paragraph. The observation about optimizing the wrong term should
either become the bridge into the Bulldozer example or join that example's
setup. Run a book-wide audit for one- and two-sentence paragraphs that are
visually and logically orphaned. Short paragraphs are valuable when they land a
deliberate point; they should not result from incomplete paragraph stitching.

**Positive presentation signal.** Preserve the Bulldozer treatment. Its
claim-gap-lesson progression is concrete, technically legible, and shows why an
easy-to-count specification may fail to predict workload value.

**Evaluation-capacity plot.** Compare Section 2.5.2 against the local `dev`
version and earlier history to identify the semiconductor-data plot the author
remembers. Determine whether it was removed, replaced by the current
verification-demand or design-cost plots, or still exists but renders poorly.
Restore it only after confirming its source, unique teaching job, and
relationship to the surrounding plots.

**Design-cost label rendering.** The 7 nm bar currently renders
“$249M\ncomposition not stated” as a single malformed label in at least one
output. Correct the line-break handling and inspect both PDF and HTML. Also
verify that the bar has sufficient height and label space at final publication
size.

**Figure defects.** Fix and verify the newline rendering in Figure 2.10. Revise
Figure 2.13 so the conceptual crossing that creates the “scissors” is visible.

**Research-question presentation.** The Chapter 2 page makes the hierarchy
problem especially clear. Theme labels, questions, and explanations need
distinct visual roles.

### Chapter 3 Continuous-Read Notes

**Life cycle as book structure.** Chapter 3 should say, at a high level, that
the life cycle supplies a structure that later chapters develop. It must still
explain the complete high-level life cycle and why a systematic approach is
needed.

**Cards and records.** The discussion around Section 3.8.1 needs to anticipate
the architect's objection that teams already maintain records in established
tools. Explain what the proposed view adds and whether it indexes rather than
replaces those artifacts.

**Heading hierarchy.** Decide whether Section 3.8.1 should become its own H2 or
be folded into Section 3.8. Do not preserve a lone H3 merely because the
current draft created one.

### Chapter 4 Continuous-Read Notes

**Opening structure.** Chapter 4 demonstrates why the unnumbered preamble may
be valuable. It introduces the chapter before Section 4.1 enters the technical
argument. Use this example in the book-wide opening-structure decision.

**Figure style.** Figure 4.2 uses rounded boxes that do not match the clean
rectangular style elsewhere. Include it in the full SVG shape and geometry
audit.

**Dataset quality needs an ML literature foundation.** Chapter 4 should draw
on established machine-learning research showing how dataset errors,
contamination, duplication, label noise, selection bias, and distribution
shift can destabilize an evaluation or create a misleading result. Examples
should include test-set contamination or leakage and empirical audits that
found substantial errors in widely used datasets. Locate and read the primary
papers before selecting examples; do not rely on remembered paper names or
secondhand summaries.

The chapter should translate those findings into architecture-specific failure
modes rather than teach a generic data-engineering unit. Candidate translations
to investigate include:

- train and evaluation sets that contain revisions or derivatives of the same
  RTL, IP block, workload, or design family;
- many simulator rows that look like independent samples but share one model,
  configuration, workload phase, or generation procedure;
- failed, partial, or invalid tool runs parsed as legitimate measurements;
- stale workloads, software, process assumptions, libraries, or tool versions;
- mismatched units, configurations, baselines, or fidelity levels;
- hidden selection effects caused by recording successful runs more reliably
  than rejected or failed runs; and
- benchmark leakage through public design artifacts, documentation, or prior
  generated solutions.

The durable lesson should be that architecture data inherit the assumptions and
failure modes of the process that produced them. Dataset size does not repair
correlated samples, invalid measurements, hidden provenance, or a contaminated
evaluation.

**Representation needs a precise vocabulary.** Define *representation* before
using it as a chapter-wide organizing term. Machine-learning literature uses
the word for several related but distinct objects:

1. the explicit encoding supplied to a method;
2. features selected or constructed from the source;
3. a learned internal or latent representation, including an embedding; and
4. a representation whose geometry or structure supports a downstream task.

Architecture uses explicit representations of its own, including
specifications, ISAs, graphs, netlists, RTL, traces, parameter vectors,
analytical models, and tool reports. These are not automatically learned
representations, and converting them into tokens or vectors does not guarantee
that the relationships needed for an architecture decision remain visible.

The chapter should distinguish:

- the architecture object or source artifact;
- its machine-readable encoding;
- any selected features or learned embedding;
- the project knowledge or state connected to it; and
- the downstream task and check for which the representation is adequate.

Use modifiers such as *architectural representation*, *input encoding*,
*feature representation*, and *learned representation* whenever the unmodified
word would be ambiguous. Do not force the chapter to use “representation”
exactly as one ML subfield does; build a precise bridge between architecture and
ML usage.

**Preserve blind spots and unknowns.** A useful representation should not only
make selected properties convenient for a model. It should also preserve or
expose validity conditions, missing information, provenance, and known blind
spots so that a downstream user can tell what the representation cannot
support.

**Positive presentation signal.** Preserve the teaching job of Table 4.5,
“Knowledge Objects Preserve Different Facts.” It helps readers see that
different objects retain different kinds of information rather than implying
that one universal representation is sufficient.

**Research packet required before revision.** Assemble a focused Chapter 4
packet covering dataset documentation, dataset audits and errors, leakage and
contamination, distribution shift, representation learning, graph and
multimodal representations, and architecture-specific datasets. For each
source, record the precise lesson that transfers to architecture, the
conditions under which it transfers, and the architecture example that would
make the lesson concrete. The result should remain an architecture chapter,
not a summary of ML data practice.

**Licensing needs visible treatment.** Licensing currently appears in several
paragraphs, examples, and the dataset checklist, but the reader should not have
to assemble the issue from scattered references. Give access, licensing, and
redistribution a named, visible passage near the sources or dataset-building
discussion. It should explain how licenses and contractual restrictions affect
what may be collected, used for training, redistributed, published as a
benchmark, or retained in a project.

The architecture-specific discussion should distinguish public code licenses,
RTL and IP restrictions, foundry process design kit (PDK) terms, EDA tool and
report restrictions, workload and trace access, and the rights attached to
derived or generated artifacts. Keep the treatment technically useful and
source-backed without presenting legal advice. This probably warrants a named
H3 or a substantial callout, not a new chapter-level H2.

### Chapter 5 Continuous-Read Notes

**Section 5.1.** The section moves too abruptly from roles and feedback budgets
to “eight fundamental roles.” Rebuild the conceptual entry so the reader first
understands why roles are a separate axis from prediction, generation, and
optimization. This observation should inform the audit of every Section x.1,
not only Chapter 5.

**The opening sentence assumes its comparison.** “Approach selection begins
with a simpler question than which technique to use” does not say what approach
is being selected, and *simpler* asks the reader to accept a comparison that
has not been established. State the engineering context and the actual
question directly. A candidate direction is:

> Selecting an approach for an architecture study begins by asking what work is
> limiting progress and whether the represented problem can be settled
> directly.

This is clearer than calling the question simpler. Audit book-wide uses of
*simple*, *simpler*, *obvious*, *clear*, and similar comparative judgments.
Each should either name the basis of the comparison or be replaced by the
substantive claim.

**Roles should not become anthropomorphic job titles.** Existing engineering
teams provide useful evidence for decomposing work into proposal, screening,
search, critique, repair, checking, explanation, and coordination. The chapter
should acknowledge those precedents. It should not imply that an AI-assisted
system must imitate a human organization or assign one agent to each familiar
job.

The durable distinction is between externally inspectable engineering
functions and the internal organization used to perform them. An agent or
multi-agent system may discover a different internal procedure, combine
several functions, or reorganize them dynamically. That freedom is acceptable
when its inputs, outputs, permitted actions, costs, checks, and responsibility
boundaries remain visible. The method should preserve engineering invariants
without prescribing an agent's internal reasoning process.

**Literature grounding for roles and compositions.** Build a source packet that
tests whether recent architecture, EDA, software-engineering, tool-using-agent,
and multi-agent systems actually exhibit recurring functional roles or
compositions. Use the papers to support or challenge the proposed taxonomy, not
merely to attach citations to eight author-defined labels. Look for evidence
about:

- functional specialization versus one general controller;
- planner, proposer, critic, checker, repair, and tool-execution patterns;
- centralized versus distributed coordination;
- learned versus conventional components in one system;
- where human review remains part of the composition; and
- systems whose internal discovery process does not mirror a human team.

The chapter should report patterns that survive comparison across systems and
should say when the evidence is still too immature to support a fixed taxonomy.

**Section 5.1 needs a full reader-flow pass.** The content is useful, but the
writing quality and pacing drop after the opening. The section moves among the
smallest sufficient approach, four decision layers, eight roles, two large
tables, and method-family distinctions faster than a new reader can build the
relationships. Map the teaching job of every paragraph and table, introduce
one distinction at a time, and decide whether both tables are needed at their
current size and location.

**Section 5.2.1 does not introduce its procedure.** “A Conditional Selection
Guide” begins with “Use the following sequence before selecting a learned
method,” but it does not first explain what decision the sequence supports,
why the order matters, or what result the reader should have at the end. Give
the guide a short motivating setup, define its output, and walk through one
architecture example before or alongside the full sequence. Read it as a
graduate student attempting to use the guide, not as its author scanning a
completed framework.

**Section titles need a plain-language audit.** “Result Economics and Feedback
Budgets” sounds coined and abstract rather than like language an architect
would naturally use. The material is important, but the title weakens it.
Candidate directions include “Counting the Full Cost of a Method” or “Method
Cost and Evaluation Capacity.” Select a title only after the section's exact
teaching job is clear.

Do not automatically demote or fold this material into a deeper subsection.
Total method cost and limited evaluation capacity are central to method choice
and may deserve their own H3. The structural problem may be the name and
transition rather than the section's existence. Avoid creating an H4 merely to
hide an awkward H3.

**Section 5.7.1 is too dense at entry.** “Constrained Generation and Compiler
Tuning” reaches a large table before establishing the design situation,
comparison, or reason for the table. Add a narrative setup that explains the
two construction paths, what must be held constant, and what the table lets the
reader compare. Then determine whether the table should remain whole, be
reduced, or follow a short worked example.

**Open questions inherit the quality drop.** The Chapter 5 research agenda
should ask technically precise, paper-sized questions about method selection,
composition, support, cost, and checks. It should not restate the chapter's
taxonomy in dense language. Apply the book-wide theme-and-bullets format and
test each question with a fresh reader.

### Chapter 6 Continuous-Read Notes

**The chapter is too table-heavy in places.** Chapter 6 currently uses tables
for attempt accounting, failure and recovery classes, returns from EDA stages,
tool classes, the Lighthouse run specification, and the Lighthouse run report.
Several are individually defensible, but their cumulative weight makes parts of
the chapter feel like a sequence of schemas rather than a developing
engineering argument.

**Section 6.8 is a positive internal benchmark.** “Multi-Tool and
Multi-Fidelity Environments” gives the reader enough narrative to understand
why the comparison matters, then uses a table to compare genuinely parallel
tool classes, and returns to prose to interpret the result. Preserve that
pattern.

**Required table audit.** For every Chapter 6 table, determine:

1. which comparison or retrieval task requires rows and columns;
2. what the reader must understand before encountering it;
3. whether the prose explains the governing distinction before the table;
4. whether every row is necessary to the main argument;
5. whether some fields belong in a compact list, example, appendix, or
   downloadable artifact instead;
6. what conclusion the prose draws after the table; and
7. whether two nearby tables are encoding related information that should be
   taught through one narrative sequence.

Do not convert tables mechanically into paragraphs. Keep a table when readers
need to compare several items across stable dimensions. Replace or reduce it
when the material is sequential, causal, illustrative, or better explained
through one concrete run.

**Likely pressure points.** The large failure-class table, the detailed
Lighthouse run specification, and the attempt-level run report deserve special
review because each contains substantial prose inside cells. The short
EDA-stage table may be teachable in prose or a smaller figure. The multi-tool
table is more naturally tabular because its rows share a stable comparison
schema.

**Narrative standard.** A table should arrive only after the reader understands
the question it answers. The paragraph following it should explain the
architectural consequence rather than restate the rows. Maintain enough prose
between tables that the chapter advances as an argument about environments,
not as a catalog of record formats.

### Chapter 7 Continuous-Read Notes

**The chapter's purpose is not yet obvious enough.** A reader can follow the
local move from a tool return to interpretation, but the chapter does not state
its complete teaching job sharply enough. Chapter 7 should teach an architect
how to turn a returned signal into qualified feedback that can support a
bounded claim or a justified change.

A candidate one-sentence contract is:

> Chapter 7 shows how to bind a tool return to the design and conditions that
> produced it, determine which property it addresses, compare it fairly, state
> its uncertainty and scope, and update only the object the result actually
> implicates.

This separates Chapter 7 from its neighbors. Chapter 6 establishes what ran and
what returned. Chapter 7 establishes what that return means and what it can
support. Chapter 8 uses qualified feedback while running a complete study.
Chapter 9 asks what survives when the problem changes. Chapter 10 evaluates the
complete result and process.

**Figure 7.1 is the right conceptual spine.** “A Tool Return Gains Meaning in
Stages” captures the chapter's unique movement:

1. preserve the execution return and lineage;
2. qualify a returned field as a measurement or another typed result;
3. construct a matched comparison;
4. interpret the comparison for one named property and scope; and
5. route the supported update, non-update, or reopening.

Use this progression to audit the section order and remove material that does
not help the reader perform one of these moves.

**Current section jobs to test.**

- **7.1, From Tool Return to Feedback:** Establish why execution status and
  interpretation are different, then introduce the staged qualification path.
- **7.2, Sources of Feedback:** Explain why human review, tools, learned
  methods, and deployed systems return signals with different latency,
  locality, coverage, and failure modes. The section should serve later
  qualification rather than remain a general taxonomy.
- **7.3, Qualifying Empirical Measurements:** Teach what turns a numerical
  field into a usable architecture measurement, including identity, quantity,
  unit, conditions, extraction status, variability, error, and recoverable
  source.
- **7.4, Formal Verification and Its Scope:** Distinguish proof,
  counterexample, bounded-only, and inconclusive outcomes, and show how
  property, model, assumptions, bounds, fairness, and vacuity limit the claim.
- **7.5, Making Measurements Comparable:** Teach matched baselines,
  decision-relevant differences, uncertainty, confounding, and selection
  effects.
- **7.6, Testing Explanations and Proxies:** Separate an observed outcome from
  its proposed mechanism and determine when a proxy remains adequate for the
  stronger property.
- **7.7, Scope, Uncertainty, and Assurance:** Show that checks cover different
  properties, may share failure modes, and should grow with the consequence
  and reversibility of the intended use.
- **7.8, Feedback That Changes the Work:** Route the result to the environment,
  representation, method, study, model, design, or project record. Preserve a
  valid “no change” outcome and define when prior support must be reopened.

**Technical-depth test.** The current chapter already contains substantial
technical material, including empirical uncertainty, formal verification,
vacuity, matched comparisons, proxy mismatch, confounding, correlated checks,
waivers, and reopening conditions. The main risk is not superficiality alone.
It is that these topics read as several adjacent mini-lectures rather than one
architecture discipline.

Each section should therefore answer three questions:

1. Which architecture mistake does this distinction prevent?
2. What exact record, comparison, property, or check would an architect use?
3. What stronger conclusion does the result still fail to support?

Use concrete architecture returns such as simulator statistics, timing slack,
power estimates, formal counterexamples, physical-rule violations, RTL
equivalence results, and post-silicon telemetry. Do not add generic statistical
or ML terminology unless it changes how an architect interprets one of those
returns.

**Verification should remain the center of gravity.** The chapter must explain
that generation is not the hard end of the problem. A plausible artifact still
needs property-specific checks, and no one check establishes general
correctness. Formal verification belongs here as one powerful class of
property-specific evidence, not as a universal replacement for simulation,
implementation, measurement, or review.

**Learning needs a narrower meaning.** If the title retains “Learning,”
distinguish project learning from model training. A project can learn that a
candidate failed, that a comparison is unresolved, or that an assumption was
wrong without turning the return into training data. If this distinction is
not central enough to justify the title, consider whether “Feedback,
Verification, and Confidence” or “From Tool Returns to Supported Claims” states
the chapter's job more directly. Do not rename it until the section audit
confirms the intended center.

**Reader-flow pass required.** Have a fresh architecture reader summarize the
claim and resulting capability after every section. If the reader cannot say
how the section advances Figure 7.1's progression, revise the transition,
relocate the material, or reconsider whether it belongs in Chapter 7. The pass
should preserve technical depth while making the chapter's cumulative argument
visible.

### Dedicated Chapter-Prose Workflow

**Author direction.** Later chapters should receive the same writing attention
as the opening chapters. Chapter 5 shows that technically sound content can
still lose quality through rushed exposition, dense tables, abstract section
titles, and missing transitions.

**Proposed workflow.** Run a dedicated prose and reader-flow pass with fresh
subagents, one chapter at a time:

1. Give each chapter agent only the approved book north star, chapter purpose,
   section goals, relevant author feedback, and that chapter's source.
2. Ask the agent to produce a reasoning map before editing. It should identify
   the job of every section, the claim of every paragraph, and the purpose of
   every table or figure.
3. Use a separate reader agent to flag unclear assumptions, unexplained
   comparisons, dense entries, weak transitions, and language that sounds
   coined or machine-written.
4. Let a revision agent propose focused changes one section at a time. Do not
   authorize a wholesale chapter rewrite.
5. Have the main editor compare each proposal against the approved chapter
   architecture, technical sources, and neighboring chapters before accepting
   it.
6. Run a second fresh-reader pass on the revised section.
7. Finish with one book-wide title audit and one chapter-level stitch pass.

Parallelize chapter diagnosis and source research where outputs do not touch
the same files. Apply prose changes sequentially or in isolated worktrees so
that section transitions and chapter consistency remain under central review.
Subagents supply fresh attention; they do not replace editorial judgment.

### Verification Required After Editorial Changes

After the feedback is resolved into approved edits:

1. rebuild both PDF and HTML;
2. inspect the affected pages and representative neighboring pages;
3. verify heading hierarchy and cross-references;
4. inspect all changed SVGs at their final rendered size;
5. confirm that mathematical notation and escaped characters render correctly;
6. run the strict manuscript checks; and
7. commit coherent milestones separately so structural, prose, and visual
   changes can be reviewed or rolled back independently.
