# Goal: one lab per chapter, a complete internalization sequence

## The goal I am working to

Ship **ten runnable labs, one per book chapter**, that walk a learner through the
Architecture 2.0 loop from prompt to owned commitment, so a reader finishes each
chapter by *doing* the chapter's idea, being wrong about it, and reconciling the
surprise. The labs share one lighthouse prompt and one engine, run on a laptop,
and every result is honest (tool-produced or sourced, never a rigged gate).

Definition of done: each chapter has a marimo notebook that (a) runs end to end on
a laptop, (b) makes the learner commit a prediction before revealing evidence,
(c) produces or audits a receipt, and (d) is validated headless.

## The decision: one lab per chapter, varied in form

Not every chapter has honest computational content, and forcing a simulator onto
an argument chapter would rig the lab. So the ten labs vary in form. Every
chapter still gets exactly one.

| Lab | Chapter | Form | The chapter's idea, made doable |
| --- | --- | --- | --- |
| **01** | Ch1 Moonshot | reasoning (no sim) | Turn the lighthouse prompt into a loop card; a prompt is not a claim. |
| **02** | Ch2 Scissors gap | data (no sim) | Compute a real generation-vs-rejection ratio from sourced numbers; feel "rejection-bound." |
| **03** | Ch3 Framework | audit (no sim) | Score loop records for reviewability; fill the card fields. |
| **04** | Ch4 Representations | light sim | What state must a receipt carry to be replayable? Provenance, negative traces. |
| **05** | Ch6 Environments | sim | Turn SCALE-Sim into an environment: legal actions, observations, invalid actions, provenance. |
| **06** | Ch5 Methods | sim | **Proxy vs Evidence (anchor)** — the proxy overstates 16x; the tool measures 7.5x. *(built)* |
| **07** | Ch7 Trust | sim + adversarial | Fidelity ladder via injected noise, rejection authority, multi-objective, **red-team the sim's idealized memory**. |
| **08** | Ch8 Running the loop | sim capstone | Two-turn full loop, complete receipt, graded by the judgment rubric. |
| **09** | Ch9 Patterns | light sim | The same loop at different feedback costs; method posture changes. |
| **10** | Ch11 Ownership | audit (no sim) | Redact a negative trace to share; **audit AlphaChip with the card** (also the book's demonstration). |

Build cost is concentrated in the four full-sim labs (05–08), which share the
existing `arch2_labs` engine. The reasoning labs (01, 02, 03, 10) need no
simulator and are cheap and robust. This is honest, covers every chapter, and
matches the reviewers' "one new concept per lab, vary the form" guidance.

## Cross-cutting contract (every lab)

- Retrieval-question unlock (active retrieval), not a passive recap.
- Prediction lock with **confidence + a reason**; score calibration, not just
  correctness. An "unlock anyway" escape stamps `skipped_predictions: true`.
- Run/audit real evidence; reconcile the surprise; name the mechanism.
- Structured commitment gates the receipt; free-text rationale optional; an
  over-commitment (RTL/product on weak evidence) is blocked.
- Ships a seed capsule so a learner can drop in at any lab.
- Honest gates only: silicon budget and deadline are hard; utilization and
  roofline are diagnostics. Estimate assumptions are sourced in every receipt.
- Explicit marimo cells; small pure helpers only, no cell-generator framework.

## Build order (I work top-down, verifying each headless)

1. **01, 02, 10** — the no-sim reasoning labs (cheap, cover the argument chapters). *(this pass)*
2. **08 Capstone** — two-turn loop + judgment rubric (reuses the engine).
3. **07 Trust** — the red-team exploit (uses SCALE-Sim's idealized-memory finding).
4. **05 Environment**, **04 Representations**, **09 Patterns**, **03 Framework**.
5. A `labs/notebooks/` index + a shared seed/golden-fixture pass.
6. Wire the corrected Lab 06 numbers back into the book's Chapter 8.

## Status

- Engine hardened to honest gates; validator overreach removed; tests green (5).
- **6 of 10 labs built and headless-validated:** 01 (Prompt to Card), 02
  (Scissors Gap), 06 (Proxy vs Evidence, anchor), 07 (Earned Trust + red-team),
  08 (Capstone + judgment rubric), 10 (Own the Commitment / AlphaChip audit).
  Index at `notebooks/README.md`. The MVP spine (01, 06, 08) is complete.
- All export cleanly; reveals gated behind a committed prediction; the red-team
  and judgment-rubric ideas from the Codex/Gemini review are built into 07 and 08.
- **Next:** the mid-spine labs 03 (Score a Claim), 05 (Environment Contract),
  04 (Represent & Replay), 09 (Same Loop, Different Costs); then wire Lab 06's
  corrected numbers into the book's Chapter 8.
