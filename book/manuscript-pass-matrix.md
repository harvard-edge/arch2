# Architecture 2.0 Pass-Based Execution Matrix

## Status

This checklist reorganizes the detailed findings in
`manuscript-audit-and-improvement-plan.md` into repeatable editorial passes.
The current planning baseline is commit `840adab9`. The author approved the
Pass 0 decisions on 2026-08-03. Manuscript work may now proceed through the
ordered passes below.

The detailed plan remains the source for individual findings, candidate models,
and reviewer rationale. This file owns execution order, pass boundaries,
chapter assignments, approval gates, and completion status.

## Standard Loop for Every Book-Wide Pass

Each pass has one narrow question. Do not ask a chapter reviewer to “improve the
chapter” generally.

1. **Write the pass brief.** State the acceptance test, protected material,
   non-goals, and exact output format.
2. **Audit chapters independently.** Assign one fresh reviewer to each chapter.
   Reviewers report findings and protected strengths; they do not edit.
3. **Reconcile centrally.** Compare findings across chapters, remove mechanical
   recommendations, resolve terminology and ownership conflicts, and identify
   decisions that require the author.
4. **Author sign-off.** Approve, reject, or revise the consolidated change set.
5. **Implement by chapter.** Give each accepted chapter change to one dedicated
   editor. No two editors change the same chapter concurrently.
6. **Recheck independently.** A fresh reviewer tests only the pass contract and
   confirms that the edit did not damage chapter flow or technical meaning.
7. **Inspect the seams.** Check adjacent chapter boundaries and any shared
   terminology, callout, citation, or visual conventions affected by the pass.
8. **Commit the coherent pass.** Preserve a reversible checkpoint and update
   the matrices below.

Repeat a pass only when the recheck finds a new consequential defect. Two
consecutive reviews that produce no new high-priority finding constitute
practical saturation. Do not polish indefinitely.

## Pass Order

| Pass | Book-wide question | Per-chapter output | Sign-off gate |
|---|---|---|---|
| 0. Decisions and structure | Are the three parts, chapter jobs, section order, and shared terminology settled enough for local work? | Structural exceptions and unresolved decisions only | Author approves the book and section structure |
| 1. Chapter shell | Does each chapter open independently, establish its problem before the learning objectives, use useful section titles, orient H3 groups, and close on its own job? | Opening, objective, hierarchy, title, and conclusion findings | Chapter shells approved before technical rewriting |
| 2. Technical depth and architecture grounding | Does every section teach the necessary architecture, EDA, ML-systems, software, formal-methods, or organizational mechanism at the right depth? | Missing mechanisms, generic material, adjacent-field lessons, conventional alternatives, and architecture examples | Technical content approved chapter by chapter |
| 3. Lighthouse continuity | Does the Lighthouse ground the chapter without becoming a cache-only parallel narrative or a burden of study identifiers? | Callout/prose decisions and one obligation-coverage entry per chapter | Book-wide Lighthouse map approved |
| 4. Characteristic pitfalls | Does the chapter explain what commonly goes wrong and the architecture consequence without manufacturing a quota? | Pitfalls to retain in prose, promote to a failure-mode callout, or remove | No forced one-per-chapter pattern; each retained pitfall earns its place |
| 5. Design principles | Has the chapter earned a durable rule that transfers to a different architecture problem? | Primary, supporting, or miscast classification plus proposed wording | Author approves the complete principle set |
| 6. Open questions | Are the themes and questions clear, technically consequential, and capable of supporting a strong research paper? | Two or three themes, candidate questions, first experiment, measurable outcome, and venue-fit rationale | Author selects the final questions |
| 7. Literature, citations, and footnotes | Are claims supported locally, adjacent-field lessons traced to primary sources, and unfamiliar ML or formal concepts taught without citation clutter? | Missing support, mismatched citation, unnecessary repetition, and footnote recommendation | All consequential evidence gaps resolved or explicitly left open |
| 8. Figures, tables, listings, and cross-references | Does every artifact teach faster than prose, use the book's visual conventions, and receive enough explanation in the text? | Keep, revise, move, replace, or remove decision for every artifact | Media program approved before visual production work |
| 9. Narrative and microflow | Does the chapter build section by section and paragraph by paragraph in a natural architecture voice? | Section seams, paragraph windows, undefined terms, repetition, and anti-template findings | Fresh readers recover the intended claim without the outline |
| 10. Appendices and front/back matter | Do supporting materials extend the settled body rather than repeat or overpromise it? | Keep, revise, repurpose, or remove recommendation | Appendix and front/back matter jobs approved |
| 11. Whole-book reconciliation | Do the three parts, chapter seams, broad-to-technical-to-broad arc, terminology, media balance, and late-book depth hold together? | Book-level blockers only | Content lock; validation and no-layout review build may begin |

## Book-Wide Pass Checklist by Chapter

Use `☐` for not started, `◐` for in progress, `✓` for approved and committed,
and `—` only when the pass genuinely does not apply.

| Chapter | Shell | Technical | Lighthouse | Pitfalls | Principles | Questions |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 1. Moonshot | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| 2. Why assistance may help | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| 3. Life cycle | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| 4. Data, knowledge, and representation | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| 5. Prediction, generation, and optimization | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| 6. Tool-connected environments | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| 7. Verification, feedback, and learning | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| 8. Running the loop | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| 9. Transfer and generalization | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| 10. Evaluation and red teaming | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| 11. The architect's role | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |

| Chapter | Citations | Media | Microflow | Final recheck |
|---|:---:|:---:|:---:|:---:|
| 1. Moonshot | ☐ | ☐ | ☐ | ☐ |
| 2. Why assistance may help | ☐ | ☐ | ☐ | ☐ |
| 3. Life cycle | ☐ | ☐ | ☐ | ☐ |
| 4. Data, knowledge, and representation | ☐ | ☐ | ☐ | ☐ |
| 5. Prediction, generation, and optimization | ☐ | ☐ | ☐ | ☐ |
| 6. Tool-connected environments | ☐ | ☐ | ☐ | ☐ |
| 7. Verification, feedback, and learning | ☐ | ☐ | ☐ | ☐ |
| 8. Running the loop | ☐ | ☐ | ☐ | ☐ |
| 9. Transfer and generalization | ☐ | ☐ | ☐ | ☐ |
| 10. Evaluation and red teaming | ☐ | ☐ | ☐ | ☐ |
| 11. The architect's role | ☐ | ☐ | ☐ | ☐ |

## Cross-Chapter Contracts

### Chapter openings

- Chapter 1 may introduce the Lighthouse because the Lighthouse establishes the
  moonshot.
- Chapters 2–11 should establish their own problem before the learning
  objectives without concrete Lighthouse candidates or study identifiers.
- The opening should build the reader's need for the chapter rather than
  preview every section.

### Section hierarchy and titles

- Numbered section titles state a subject or claim; they do not ask questions.
- An H2 followed immediately by an H3 is a defect unless the parent contains a
  real orientation explaining the decomposition.
- A lone H3 normally folds into its parent or becomes an H2.
- Titles use ordinary architecture language and avoid generic guide, map,
  handoff, economics, ledger, routing, or framework language when a concrete
  engineering object can be named.

### Lighthouse

- Brief grounding references may remain in body prose.
- Detailed candidates, identifiers, settings, and worked applications belong
  in a Lighthouse callout or dedicated application section.
- A callout states the relevant context, use of assistance, and required checks
  in a compact form. It does not become a wall of text.
- The full Lighthouse spans workload, software, compiler, ISA,
  microarchitecture, memory, interconnect, SoC integration, physical limits,
  reliability, security, and verification. The cache study is one narrow
  decision, not the moonshot itself.
- Chapter 8 preserves the prospective cache record and the separate executed
  array study. It does not invent an executed Lighthouse result.

### Design principles

- Each numbered chapter should have one primary design principle earned by its
  body.
- A supporting principle remains only when it is independently transferable and
  does not compete with the primary principle.
- Classify every existing principle as primary, supporting, or miscast before
  rewriting any of them.
- Use a short principle name, one or more bold actionable statements, and
  concise explanation. Do not force the same number of statements in every
  chapter.
- The complete set should read as a coherent progression when extracted from
  the chapters.

### Characteristic pitfalls

- Place a short `Common Pitfalls` section near the end of a chapter, after the
  core technical argument and before `Open Questions` and the conclusion, when
  the chapter has distinctive failures worth retrieving.
- Do not manufacture weak pitfalls merely to satisfy symmetry. Keep a failure
  in the body when it advances the mechanism better than an end section would.
- A pitfall must name the architecture consequence, not merely advise caution.

### Open questions

- Use a small number of thematic bold labels rather than subsection clutter.
- Each question is followed by enough explanation to suggest a first experiment,
  evidence, baseline, and meaningful outcome.
- Chapter 1 opens the field, Chapters 2–10 become progressively technical, and
  Chapter 11 widens back to the field and the architect's role.
- Deduplicate questions centrally after the chapter-level pass.

### Figures, tables, and listings

- Ordinary SVG boxes have sharp rectangular corners. Protected brand assets are
  not restyled.
- Connectors do not cross boxes or labels, and arrows land unambiguously.
- The prose introduces the relationship, interprets the artifact, and states
  the inference. Captions do not carry the entire explanation.
- Avoid empty announcements such as “Figure X shows” and mechanical reading
  directions.
- Bold the first table column only when it is genuinely a row-label or
  definition column, not in a comparison or matrix.
- Retain a listing only when code or pseudocode teaches a reusable interface or
  state distinction more clearly than prose and a figure.

### Architecture grounding and adjacent fields

- Begin with the architecture problem and mechanism, then borrow the relevant
  lesson from ML, formal methods, software systems, safety, or organizations.
- State which failure motivated the borrowed practice and which parts do or do
  not transfer to architecture.
- Avoid generic primers. Link or footnote background that an architecture
  reader needs but that the chapter does not own.
- Preserve conventional algorithms, tools, formal methods, and no-AI approaches
  as credible alternatives.

## Chapter-Specific Work

### Chapter 1: The Moonshot

- Build excitement gradually before the Lighthouse request.
- Clarify the desired complete capability and the optional role of an
  architecture foundation model without implying autonomous prompt-to-chip
  generation.
- Review the hierarchy around the artifact-versus-result material.
- Keep the open questions broad and field-forming.
- Recover a foundation-model visual only if it replaces weaker material and
  remains durable.

### Chapter 2: Why Architecture Work Is Getting Harder

- Develop hardware scale and specialization first, then software complexity,
  and place warehouse-scale computing afterward as the system-level synthesis.
- Expand warehouse-scale computing as the system-level synthesis of hardware,
  software, networking, power, cooling, deployment, and operation.
- Separate the two closely placed specialization figures by teaching job.
- Keep the candidate-versus-evaluation-capacity argument qualitative; Chapter 5
  owns the analytical model.

### Chapter 3: The AI-Assisted Design Life Cycle

- Give each lifecycle responsibility an architecture question, expected output,
  characteristic failure, and handoff.
- Give the design-loop card a dedicated H2 and motivate it as a compact index
  into existing engineering artifacts rather than a new administrative schema.
- Motivate reviewable records through relevant lessons from experiment tracking,
  model and dataset documentation, safety cases, reproducibility, and engineering
  change control without creating another administrative schema.
- Explain that stages may repeat, branch, or run concurrently.

### Chapter 4: Architecture Data, Knowledge, and Representation

- Keep the chapter architecture-specific rather than teaching generic data
  engineering.
- Cover acquisition cost, interventions, missing and failed runs, censoring,
  leakage, contamination, coverage, freshness, licensing, private data, and
  synthetic-data limits.
- Distinguish source observations, explicit architecture representations, and
  learned representations. Embeddings are one learned form, not the definition
  of representation.
- Investigate a sourced data-volume comparison without inventing a ratio.
- Use QuArch and prior slides only as source-discovery prompts until primary
  evidence is recovered.

### Chapter 5: Prediction, Generation, and Optimization

- Teach selection from the limiting work: missing construction, expensive
  estimation, scarce evaluation, inadequate checking, or no need for an added
  method.
- Explain how methods compose without imposing a universal order.
- Retain direct tools, strong conventional methods, and no added method as valid
  choices.
- Decide whether the existing selection figure and composition table are enough;
  do not add a Venn diagram by default.
- Keep the capacity model here if the distributed placement is approved.
- Repair the macro-placement figure's connector geometry.

### Chapter 6: Tool-Connected Design Environments

- Smooth the memorable “A tool command is not an environment” opening.
- Replace the question-form Section 6.1 title.
- Make the tool spectrum and its differences in fidelity, state, latency, cost,
  licensing, failure, and returned artifacts explicit.
- Decide whether Listing 6.1 remains, shrinks, or moves to an appendix.
- Teach environment identity in plain language before exposing Lighthouse codes.
- Keep cost ownership focused on what the environment can observe and retain.

### Chapter 7: Verification, Feedback, and Learning

- Keep verification, feedback, and learning distinct: qualify the signal,
  connect it to an action, and decide what changes or persists.
- Distinguish formal support from statistical confidence and explain actionable
  uncertainty in architecture terms.
- Separate plausible explanations from mechanisms tested by counterfactuals,
  ablations, or stronger checks.
- Repair the stacked headings in the proxy/explanation section.
- Investigate qualification for a defined task and risk class without adopting
  “AI-certified tool” prematurely.

### Chapter 8: Running the Design Loop

- Preserve the prospective Lighthouse cache record and retained array execution
  as separate evidence.
- Strengthen the causal order from frozen comparison through chronology,
  results, mechanism test, coverage limits, and stopping.
- Keep every failure, tie, omitted measurement, and unsupported explanation
  visible.
- Defer a fully runnable open companion study until after the text stabilizes.

### Chapter 9: Transfer and Generalization

- Teach what transfers, what adapts, and what must be re-established when the
  workload, software, hardware, tools, process, or deployment changes.
- Borrow shift, robustness, MLOps, and configuration-management lessons only
  when they change an architecture claim or required check.
- Preserve the five-step transfer test as the primary spine and avoid another
  pattern catalog.

### Chapter 10: Evaluation and Red Teaming

- Keep component task performance, architecture result, and complete-system
  value separate.
- Preserve the four-part metric spine: architecture result, decision quality,
  total cost, and reliability.
- Ensure task performance, system performance, cost, generalization,
  reliability, verification, validation, and interpretation are all visible
  without adding a competing taxonomy.
- Evaluate and red-team AI-assisted systems, matched alternatives, returned
  designs, benchmarks, tools, feedback, faults, and recovery.
- Do not add more metric frameworks unless review exposes a missing judgment.

### Chapter 11: The Architect's Role

- Grant strong AI capability and still define the architect's positive technical
  contribution.
- Keep problem framing, abstraction, cross-layer tradeoffs, interpretation,
  commitment authority, organizational responsibility, and residual risk
  distinct.
- End with broad field questions and the book's canonical closing principle.
- Return to the Lighthouse without claiming the complete moonshot was executed.

## Appendices

### Appendix A: Reviewer checklist

- Define its job as a portable external review instrument, not another project
  schema or authorization mechanism.
- Consolidate duplicate checks, replace binary pass/fail where conditional or
  unresolved status is needed, improve cost and ownership order, and simplify
  process language.
- Consider compact failure signs only where they improve the reviewer function.
- Add a clear inbound handoff from Chapter 10 after the body stabilizes.

### Appendix B: Positioning map

- Remove Appendix B from the rendered book for now while preserving its source
  until the body and literature synthesis stabilize. Reintroduce only a compact,
  evidence-backed positioning map with a clear body handoff; do not turn it into
  a second survey.

### Capacity-model appendix decision

- Keep the compact capacity model in Chapter 5 as its primary teaching home.
- Defer an extended derivation, worksheet, and new appendix until the main
  explanation proves useful. Do not insert that material into Appendix A or B.

## Approved Pass 0 Decisions

1. Use three parts with short opening blurbs: *Ambition and Need* (Chapters
   1–2), *Technical Foundations* (Chapters 3–7), and *Operation, Evaluation,
   and Responsibility* (Chapters 8–11).
2. Use the book-wide Lighthouse policy above. Brief grounding references may
   remain in prose; detailed studies and settings belong in callouts or a
   dedicated application section.
3. Place earned pitfalls near the end of the chapter without forcing weak or
   repetitive material into every chapter.
4. Keep one primary design principle per numbered chapter. Retain supporting
   principles only when independently useful, and collect the final set in a
   compact back-matter summary after the body stabilizes.
5. In Chapter 2, develop hardware scale and specialization, then software
   complexity, then warehouse-scale computing as the system synthesis.
6. Give the Chapter 3 design-loop card a dedicated H2 with the limited role
   stated above.
7. Use `Open Questions` as the recurring closing-section name.
8. Teach the compact capacity model in Chapter 5 and defer an extended appendix.
9. Remove Listing 6.1 from the Chapter 6 body for now. Preserve its conceptual
   lesson in prose or a smaller artifact rather than moving the listing into an
   appendix by default.
10. Keep and refine Appendix A as a portable reviewer checklist. Remove Appendix
    B from the rendered book for now while preserving its source for possible
    later reuse.
