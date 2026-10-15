# `nanochip`: The *Architecture 2.0* AI-Native Chip Design Curriculum

> *"Everyone looking at `nano-kpu` stares at `rtl/`. They are looking at the wrong directory. The revolution is `harness/`—and how the 6-stage loop forces an AI agent to co-design math, memory, and silicon together."*

Welcome to **`nanochip`**, the flagship hands-on laboratory and governance case study for ***Architecture 2.0: Principles of AI-Native System and Chip Design***.

Built around **Moonshot AI's `nano-kpu`** ([`nanochip/kpu/`](kpu/) — see [`CREDIT.md`](CREDIT.md) for full attribution), `nanochip` deconstructs how **Kimi K3** autonomously designed, verified, and closed timing on a **1.46-million-cell hybrid-attention Mixture-of-Experts (MoE) inference chip (`msh_chip_top`)** in 48 hours, accelerating decode throughput from **`4.0 tok/s` to `8,720.6 tok/s`** (**2,180x**).

Instead of treating autonomous chip design as "prompting an LLM to write Verilog," `nanochip` teaches you **how to architect the automated 6-stage design loop itself**: locking the cryptographic specification boundary, pruning impossible designs via byte-traffic rooflines, bridging floating-point semantics to RTL via a bit-exact fixed-point representation sandwich, stress-testing hardware with adversarial referees, routing failures along three distinct diagnostic return arrows, and auditing pre-layout proxy gaps with a formal **Design-Loop Card v2.0**.

---

## Quickstart Commands

Run the interactive curriculum and verification suite from the repository root (`/Users/VJ/GitHub/Arch2-nanochip`):

```bash
# 1. Interactive guided walkthrough of the 6-stage nano-kpu design loop
./arch2 tutorial

# 2. List all 6 progressive lifecycle labs and their physical contracts
./arch2 lab list

# 3. Execute all 6 progressive labs (both --mode break and --mode verify)
./arch2 lab run all
# (or run directly via Python: python3 nanochip/labs/run_all.py)

# 4. Launch the live Architecture 2.0 terminal cockpit
./arch2 cockpit

# 5. Validate the publication-grade Design-Loop Card v2.0 and SHA-256 evidence packets
./arch2 validate card nanochip/cards/nano-kpu-study-card.yaml
```

You can also run any individual lab in three modes (`verify`, `break`, or `summary`):

```bash
python3 nanochip/labs/01-formulate/lab.py --mode break
python3 nanochip/labs/01-formulate/lab.py --mode verify
python3 nanochip/labs/01-formulate/lab.py --mode summary --json
```

---

## Why `harness/` Is the Real Revolution

When an unguarded LLM agent is asked to optimize a hardware design, it reliably discovers the path of least resistance:
- It relaxes the clock period in the synthesis script or lowers the cosine accuracy threshold (**Reward Hacking**, caught in **Lab 01**).
- It proposes widening MAC arrays while streaming uncompressed weights across a narrow pin interface (**Roofline Hallucination**, caught in **Lab 02**).
- It tries to debug floating-point drift and Verilog pipeline stalls simultaneously without an intermediate fixed-point oracle (**Representation Collapse**, caught in **Lab 03**).
- It uses simulation-only `$fread` calls, relies on Verilator zero-initialization of unreset flip-flops, or builds 96K-gate parallel barrel demuxes with 266 ns unbuffered wireload delay (**Simulation-Only Escapes & Physical Bloat**, caught in **Lab 04**).
- It feeds synthesis area violations, bus deadlocks, and bandwidth ceilings into the same blind retry prompt (**Credit-Assignment Blindness**, caught in **Lab 05**).
- It mistakes a pre-layout Yosys/ABC wireload estimate with blackboxed SRAMs for tapeout-ready silicon (**Proxy-to-Purpose Conflation**, caught in **Lab 06**).

Moonshot AI's `nano-kpu` succeeded because its **frozen harness (`nanochip/kpu/harness/`)** made every single one of those shortcuts impossible, while Kimi K3 used **self-imposed representations (`fxmodel.py` and `perf-model`)** to navigate the legal design space $\Theta$.

```mermaid
flowchart LR
    S1["1. Formulate<br/>(Frozen Manifest & Budgets)"] --> S2["2. Explore<br/>(Roofline & Perf-Model)"]
    S2 --> S3["3. Implement<br/>(float32 ↔ fxmodel ↔ RTL)"]
    S3 --> S4["4. Evaluate<br/>(Audit, Chaos TB, Yosys/ABC)"]
    S4 --> S5["5. Interpret<br/>(Causal Credit Router)"]
    S5 -->|"All Referees Green"| S6["6. Commit<br/>(Design-Loop Card v2.0)"]

    S5 -.->|"Turn 1: Bit-Mismatch / Lint<br/>(Implementation Defect)"| S3
    S5 -.->|"Turn 2: 2x DRAM Stall / 96K Demux<br/>(Microarchitectural Bottleneck)"| S2
    S5 -.->|"Turn 3: FP16 Pin Bandwidth Wall<br/>(Cross-Layer Co-Design)"| S1
```

---

## Mapping the 6 Labs to the *Architecture 2.0* Book

Each lab in [`nanochip/labs/`](labs/) corresponds to one canonical stage of the **Architecture 2.0 Life Cycle** (Chapter 3) and grounds the concepts across all four parts of the monograph:

| Lab | Lifecycle Stage | Book Part & Chapters | Target `nano-kpu` Mechanics | `--mode break` (What Fails Without It) | `--mode verify` (What the Loop Enforces) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **[`01-formulate`](labs/01-formulate/)** | **Stage 1: Formulate** | **Part I: Foundations**<br/>Ch. 1 (*The Architecture Moonshot*)<br/>Ch. 2 (*Compounding Pressures*)<br/>Ch. 3 (*The AI-Native Design Life Cycle*) | `harness/manifest.json`<br/>`harness/check_integrity.py`<br/>`harness/resource_budgets.json`<br/>`harness/scoring.py` | Simulates an unguarded agent reward-hacking `resource_budgets.json` (`target_freq_mhz: 100 -> 25`, `COS_PASS: 0.98 -> 0.50`); caught immediately by SHA-256 manifest verification. | Verifies all 35 frozen files in `manifest.json` and emits the formal `FormulationRecord` separating immutable constraints from the mutable design space $\Theta$. |
| **[`02-explore`](labs/02-explore/)** | **Stage 2: Explore** | **Part II: Loop Mechanics**<br/>Ch. 4 (*Data, Knowledge, and Representation*)<br/>Ch. 5 (*Prediction, Generation, and Optimization*) | `reference/gen_weights.py`<br/>`active_weight_bytes()`<br/>`floor_weight_bytes()`<br/>`REPORT.md` `perf-model` | Evaluates a typical LLM hallucination ("`20,000 tok/s` by widening MACs with uncompressed FP16 weights over `16 B/cycle` DRAM") and proves via conservation of bytes (`19,028 cyc/tok` floor $\rightarrow$ `5,255 tok/s` max) that it violates physics. | Computes exact byte-traffic rooflines across FP32, FP16, and INT4 group-128 (`76,109 B/tok` active $\rightarrow$ `4,757 cyc/tok` floor) and audits Kimi K3's pre-committed `11,200 cyc/tok` analytical prediction. |
| **[`03-implement`](labs/03-implement/)** | **Stage 3: Implement** | **Part II: Loop Mechanics**<br/>Ch. 4 (*Data, Knowledge, and Representation*)<br/>Ch. 7 (*Verification, Feedback, and Learning*) | `reference/model.py` (`float32`)<br/>`rtl/selfmodel/fxmodel.py` (`Q4.26`)<br/>`rtl/msh_deq.v` & `rtl/msh_gemv.v` | Injects a 1-bit shift discrepancy (`<< 13` vs. `<< 14`) and missing zero-point fold ($\sum (q-z)x = \sum qx - z\sum x$) and shows how the implementation boundary catches row 0 immediately without full-chip synthesis. | Runs `reference/selftest.py`, `harness/selfcheck.py`, and verifies the two-boundary Representation Sandwich (`float32` $\leftrightarrow$ `fxmodel.py` $\leftrightarrow$ `rtl/`). |
| **[`04-evaluate`](labs/04-evaluate/)** | **Stage 4: Evaluate** | **Part II: Loop Mechanics**<br/>Ch. 5 (*Prediction, Generation, and Optimization*)<br/>Ch. 6 (*Execution Harnesses and Tool Isolation*) | `harness/audit.py`<br/>`harness/tb/tb_main.cpp`<br/>`harness/synth_tech.ys`<br/>`rtl/msh_deq.v` | Runs 3 adversarial checks: (a) `audit.py` catching `$fread` / illegal `$readmemh` / `msh_sram` redefinition, (b) `randreset` + `2x DRAM latency` (`24 -> 48` cyc) catching a rigid pipeline, and (c) Yosys Nangate45 synthesis comparing a naive 16-way parallel demux (+96K gates) and unbuffered wireload timing (`266,515 ps`) vs. byte-serial buffered `msh_deq.v` (`18,331 um^2`, `1,479 ps`). | Executes real `audit.py`, `verilator --lint-only`, and real `yosys` Nangate45 two-pass synthesis on `msh_deq.v`, plus full-chip evaluation metrics inspection. |
| **[`05-interpret`](labs/05-interpret/)** | **Stage 5: Interpret** | **Part III: Loop in Action**<br/>Ch. 3 (*The AI-Native Design Life Cycle*)<br/>Ch. 6 (*Execution Harnesses*)<br/>Ch. 9 (*Pattern Transferability*) | Diagnostic Credit Router across Kimi K3's 4-Turn Trajectory (`msh_fetch`, `msh_gemv`, `msh_deq`) | Demonstrates how a naive "blind retry" loop burns compute and oscillates when RTL bugs, $2\times$ DRAM stalls, and bandwidth walls are fed into an undifferentiated retry prompt. | Runs the **Architecture 2.0 Diagnostic Router** across 4 turns: Turn 1 $\rightarrow$ `3. Implement`, Turn 2 $\rightarrow$ `2. Explore`, Turn 3 $\rightarrow$ `1. Formulate`, Turn 4 (`11,467.1 cyc/tok` vs. `11,200` predicted = `2.33%` error) $\rightarrow$ `6. Commit`. |
| **[`06-commit`](labs/06-commit/)** | **Stage 6: Commit** | **Part IV: Governance**<br/>Ch. 3 (*The AI-Native Design Life Cycle*)<br/>Ch. 10 (*System Evaluation and Red-Teaming*)<br/>Ch. 11 (*What the Architect Owns*)<br/>Ch. 12 (*Bootstrapping an Ecosystem*) | `cards/nano-kpu-study-card.yaml`<br/>`schemas/design-loop-card.v2.schema.json` | Audits a flawed "rubber-stamp" signoff card that claims full tapeout readiness from pre-layout Yosys synthesis (ignoring blackboxed `msh_sram`/`msh_rom` timing arcs, statistical `5K_hvratio_1_1` wireload vs. routed RC parasitics, and single-corner STA). | Validates `nanochip/cards/nano-kpu-study-card.yaml` against `design-loop-card.v2.schema.json` via `./arch2 validate card`, verifying SHA-256 evidence bindings, rejection gates, and explicit proxy-gap disclosures. |

---

## Directory Layout

```text
nanochip/
├── README.md                  # This curriculum guide and architectural overview
├── CREDIT.md                  # Academic & engineering credit to Moonshot AI (Kimi K3) & open EDA
├── kpu/                       # Frozen upstream MoonshotAI/nano-kpu repository (35 SHA-256 locked files)
│   ├── docs/                  # Normative task specification, architecture, interface, quantization
│   ├── reference/             # Float32 golden model (model.py), weight generator, selftest.py
│   ├── rtl/                   # Kimi K3's 10 Verilog modules (msh_chip_top .. msh_vec) + selfmodel/fxmodel.py
│   └── harness/               # Evaluation engine (evaluate.py, audit.py, check_integrity.py, synth_*.ys, tb/)
├── labs/                      # The 6 Progressive Architecture 2.0 Lifecycle Labs
│   ├── run_all.py             # Master runner executing all 6 labs and emitting workbench_summary.json
│   ├── 01-formulate/          # Stage 1: Locking the Study Contract & Integrity Boundary
│   ├── 02-explore/            # Stage 2: Roofline Betting & Candidate Generation
│   ├── 03-implement/          # Stage 3: The Multi-Fidelity Representation Sandwich
│   ├── 04-evaluate/           # Stage 4: Adversarial Referees, Chaos Testing & Silicon Synthesis
│   ├── 05-interpret/          # Stage 5: Causal Credit Assignment & The Three Return Arrows
│   └── 06-commit/             # Stage 6: Signoff Governance, Proxy Gaps & Design-Loop Card v2.0
└── cards/                     # Formal Governance & Auditability Artifacts
    ├── nano-kpu-study-card.yaml   # Schema v2.0 Design-Loop Card (all 6 profiles complete)
    ├── nano-kpu-study-card.md     # Human-readable companion audit report
    ├── replay.py                  # Deterministic verifier for bound evidence packets
    ├── replay-environment.json    # Pinned toolchain & manifest environment binding
    └── evidence/                  # SHA-256 bound evidence packets for claims, gates, and rejected turns
```
