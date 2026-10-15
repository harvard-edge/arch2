# Lab 06 — Stage 6: Commit (`06-commit`)

**Title:** *Signoff Governance, Proxy Gaps & The Design-Loop Card v2.0*
**Lifecycle Stage:** `6. Commit`
**Book Alignment:** Part IV — *Governance & Ecosystem* (Chapter 3: *The AI-Native Design Life Cycle*, Chapter 10: *System Evaluation and Red-Teaming*, Chapter 11: *What the Architect Owns*, Chapter 12: *Bootstrapping an AI-Native Ecosystem*)
**Target Artifact:** [`nanochip/cards/nano-kpu-study-card.yaml`](../../cards/nano-kpu-study-card.yaml), [`nanochip/cards/nano-kpu-study-card.md`](../../cards/nano-kpu-study-card.md), [`nanochip/cards/replay.py`](../../cards/replay.py), [`schemas/design-loop-card.v2.schema.json`](../../../schemas/design-loop-card.v2.schema.json)

---

## 1. What Breaks Without This Stage: Rubber-Stamping the Proxy

When an autonomous loop produces a green scoreboard—`pass = True`, `8,720.58 tok/s`, `3.610 mm^2`, `6.166 ns`—the most dangerous mistake an engineering organization can make is **conflating the evaluation proxy with physical reality**:

1. **The Wireload Proxy Gap:** Yosys/ABC estimates interconnect capacitance using a statistical lookup table (`WireLoad = "5K_hvratio_1_1"`) based purely on fanout count, with zero knowledge of 2D placement coordinates or routing congestion. A 1024-bit wide bus between `msh_gemv` and `qacc` SRAMs may easily close timing under a statistical wireload model while failing post-route SPEF static timing by several nanoseconds.
2. **The Blackboxed Macro Gap:** All 39 `msh_sram` and `msh_rom` macros (`9.47 Mbits`, `0.903 mm^2`) are synthesized against empty blackbox stubs (`harness/macros/msh_sram_bb.v`). Pre-layout STA terminates at the macro pins without accounting for real SRAM setup/hold times, clock-to-Q delays, or routing detours around 39 hard macro blockages.
3. **The Single-Corner Gap:** Timing is evaluated at a single nominal typical corner (`NangateOpenCellLibrary_typical.lib`) with ideal zero-skew clocks, omitting slow-slow (SS) setup corners, fast-fast (FF) hold corners after Clock-Tree Synthesis (CTS), and IR drop.
4. **Accountability Collapse:** As Chapter 11 (*What the Architect Owns*) argues, an AI model (`kimi-k3-autonomous-architect`) can **propose** candidates and **recommend** an outcome, but it cannot bear professional engineering liability or **commit** an organization to silicon fabrication.

---

## 2. How *Architecture 2.0* Implements Stage 6: The Design-Loop Card v2.0

To prevent proxy-to-purpose conflation and enforce accountable governance, `nanochip` packages the entire `nano-kpu` study into a machine-verified **Design-Loop Card v2.0** ([`nanochip/cards/nano-kpu-study-card.yaml`](../../cards/nano-kpu-study-card.yaml)):

- **Six Complete Profiles (`profiles`):** `context: complete`, `inspectability: complete`, `replay: complete`, `independent_review: complete`, `disclosure: complete`, `decision_rights: complete` (`profile_gaps: {}`).
- **Cryptographically Bound Evidence (`evidence.records` & `replay`):** Three JSON evidence packets (`nano-kpu-formulation-roofline.json`, `nano-kpu-implementation-sandwich.json`, `nano-kpu-evaluation-signoff.json`) and `replay.py` verified by SHA-256.
- **Explicit Non-Claims & Proxy Disclosures (`claims[*].non_claims` & `intent.risks`):** Every claim states what is *not* claimed (no post-layout DRC/LVS, no routed SPEF STA, no macro Liberty timing arcs).
- **Retained Negative Results (`failed_or_rejected`):** Preserves all 4 rejected intermediate turns (`Turn 1` shift/audit defect, `Turn 2` 96K-gate parallel demux & non-elastic stall, `Turn 3` FP16 bandwidth wall, and unbuffered `266.5 ns` wireload STA) so future architects do not repeat them.
- **Separated Decision Rights (`decision_rights`):**
  - `kimi-k3-autonomous-architect` (`model`): `propose`, `recommend`
  - `nano-kpu-frozen-harness` (`pipeline`): `execute`, `reject`
  - `arch2-signoff-architect` (`person`): `waive` (scoped to pre-layout benchmark proxy), `commit` (scoped to pre-layout RTL baseline; mandates physical P&R before tapeout).

---

## 3. Hands-On Exercises

### Exercise A — `--mode break` (Audit a Flawed "Rubber-Stamp" Tapeout Card)
```bash
python3 nanochip/labs/06-commit/lab.py --mode break
```
**What happens:** Evaluates a flawed "rubber-stamp" card that:
1. Claims full foundry tapeout readiness from pre-layout Yosys synthesis (ignoring blackbox macros, `5K_hvratio_1_1` statistical wireload, and single-corner STA),
2. Grants the `commit` and `reject` decision rights to the AI model (`kimi-k3`) with no independent review, and
3. Omits SHA-256 evidence hashes and rejected alternatives.

Runs both `./arch2 validate card` schema/semantic checks and the *Architecture 2.0* Proxy-Gap Governance Audit against the rubber-stamp card, catching every schema and signoff violation.

### Exercise B — `--mode verify` (Validate `nano-kpu-study-card.yaml` & Replay Evidence)
```bash
python3 nanochip/labs/06-commit/lab.py --mode verify
```
**What happens:** Executes `./arch2 validate card nanochip/cards/nano-kpu-study-card.yaml` and `python3 nanochip/cards/replay.py verify-all`, verifying zero schema/semantic findings, 100% SHA-256 evidence integrity, and printing the complete signed **Design-Loop Card v2.0** governance summary.

---

## 4. Socratic Reflection Questions

1. **Why Record `failed_or_rejected` Candidates in a Signoff Card? (Ch. 10 & Ch. 11):** Traditional hardware papers and datasheets report only the winning design. Why does `design-loop-card.v2.schema.json` require a `failed_or_rejected` array, and what specific engineering value do `reject-turn2-non-elastic-stall-and-demux` and `reject-turn3-fp16-bandwidth-wall` provide to the next team?
2. **Pre-Layout Commitment vs. Tapeout Commitment (Ch. 6 & Ch. 11):** Look at `accountable_decision.authorized_scope` and `reopen_conditions` in `nano-kpu-study-card.yaml`. What specific physical backend events in an OpenROAD flow would force the architect to **reopen** the design loop and route a return arrow back to Stage 2 (`Explore`)?
3. **Why Can an AI Model Hold `recommend` But Never `commit`? (Ch. 11):** In `nano-kpu-study-card.yaml`, `kimi-k3-autonomous-architect` holds `propose` and `recommend`, `nano-kpu-frozen-harness` holds `execute` and `reject`, and `arch2-signoff-architect` holds `waive` and `commit`. What breaks institutionally if the generator model (`propose`) is also allowed to hold `reject` or `commit`?
