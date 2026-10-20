# Historical Nanochip workbench

This document preserves the earlier forensic walkthrough of the frozen upstream
nano-KPU study and its six-stage lifecycle labs. Its numeric claims, terminology,
and quotations retain their original scope. The study uses a pre-layout
Nangate45 synthesis proxy with blackboxed memories; its headline speedup and
walkthrough runtimes are not results for the current complete-core physical flow
or cumulative student course.

The archived description below is retained with its original claims. Local
links and the checkout-specific command context have been adjusted for this
location. Start with the [current Nanochip README](../README.md) and
[system guide](SYSTEM_GUIDE.md) for the complete-workload path, nine cumulative
labs, measured results, and remaining physical checks.

## Archived workbench description

> *"Inside a loop, with a simulator to check against, agents act like architects. Outside it, they are confidently wrong. The loop is the variable."*
>
> *"Everyone looking at `nano-kpu` stares at `rtl/`. They are looking at the wrong directory. The revolution is `harness/`—and how the 6-stage loop forces an AI agent to co-design math, memory, and silicon together."*

Welcome to **`nanochip`**, the flagship hands-on laboratory and governance workbench for ***Architecture 2.0: Principles of AI-Native System and Chip Design***.

Built around **Moonshot AI's `nano-kpu`** ([`nanochip/kpu/`](../kpu/) — see [`CREDIT.md`](../CREDIT.md) for full attribution), `nanochip` provides a forensic, reproducible dissection of how **Kimi K3** operated inside a human-engineered evaluation harness to co-design a **1.46-million-cell hybrid-attention Mixture-of-Experts (MoE) inference accelerator (`msh_chip_top`)** across 5 stack layers in 48 hours.

Instead of treating AI-native hardware design as "prompting an LLM to write Verilog" or celebrating an unexamined headline speedup, `nanochip` teaches you **how to engineer, audit, and govern the automated 6-stage design loop itself**:
1. **Formulate (`01-formulate`):** Applying multi-step quantitative domain reasoning (`QuArch`) to determine when a target requires Layer 3 cross-stack co-design, and locking the cryptographic specification boundary (`manifest.json`).
2. **Explore (`02-explore`):** Pruning physically impossible proposals in milliseconds via conservation-of-bytes rooflines and Little's Law queue bounds before invoking expensive cycle simulators (`AgentDSE`).
3. **Implement (`03-implement`):** Co-designing block-quantized numerics (`INT4 group-128`), software schedules, and RTL across a bit-exact **Representation Sandwich** (`float32` $\leftrightarrow$ `Q4.26 fxmodel.py` $\leftrightarrow$ `rtl/`).
4. **Evaluate (`04-evaluate`):** Closing the `ArchEval` L3-to-L1 gap by chaining AST structural audits (`audit.py`), randomized-reset and $2\times$ DRAM-latency chaos testbenches, and two-pass Yosys/ABC `Nangate45` synthesis.
5. **Interpret (`05-interpret`):** Running counterfactual ablations, routing multi-modal failures along the three diagnostic return arrows (`Implement`, `Explore`, `Formulate`), and charging **joules and simulator calls per verified outcome** (`MLPerf Agents`).
6. **Commit (`06-commit`):** Auditing baseline denominators, disclosing pre-layout physical proxy gaps against post-route reality, and signing the machine-checkable **Design-Loop Card v2.0** as the accountable human architect.

---

## Forensic Dissection of the `2,180×` Headline (`4.0 tok/s` $\rightarrow$ `8,720.6 tok/s`)

A core principle of *Architecture 2.0* (Chapter 10) and `MLPerf` is that **no speedup ratio is meaningful until you audit both its baseline denominator and its physical signoff boundary**:

| Metric / Boundary | Raw Headline Claim | Forensic Architectural Audit (What You Verify in `nanochip`) |
| :--- | :--- | :--- |
| **Baseline Denominator (`4.0 tok/s`)** | "`4.0 tok/s` baseline $\rightarrow$ `8,720.6 tok/s` (**2,180×**)" | `4.0 tok/s` (`25,000,000 cyc/tok` at `100 MHz`) is an unpipelined scalar FP32 sequential loop used as a functional correctness anchor, **not** a matched hardware baseline. |
| **Physics Roofline Comparator** | Unstated in headline point claims | Over the `16 B/cycle` DRAM port at `100 MHz`, uncompressed **FP16** (`304,448 B/tok`) hits an unbreakable conservation-of-bytes wall at **`19,028 cyc/tok` (`5,255.4 tok/s` max)**. Reaching `8,720.6 tok/s` (`11,467.1 cyc/tok`) required **Layer 3 `INT4 group-128` co-design** (`76,109 B/tok` $\rightarrow$ `4,757 cyc/tok` floor, achieving **41.5% of theoretical pin bandwidth** and matching the `11,200 cyc/tok` pre-committed model within **2.33%**). |
| **Physical Signoff Scope** | "`1.46M` cells, `3.61 mm²`, `100 MHz` timing closed" | Evaluated via **pre-layout Yosys/ABC topological synthesis** (`Nangate45` nominal library with statistical `5K_hvratio_1_1` wireload and **39 blackboxed `msh_sram`/`msh_rom` macros**). It is a **qualified pre-layout architectural baseline**, *not* post-route GDSII with extracted SPEF RC parasitics, multi-corner PVT STA, or antenna signoff. |
| **Statistical Scope (`n = 1`)** | 48-hour autonomous Kimi K3 run | Represents a **single recorded workflow trajectory (`n = 1` study record)** audited for harness mechanics and artifact validity, not a multi-seed statistical benchmark of the underlying model. |

---

## How `nanochip` Fits Into the *Architecture 2.0* Three-Tier Vehicle Hierarchy

Computer architecture spans **12 coupled layers across Node and Fleet** (Model, Numerics, Compiler/Kernels, Runtime/Memory, Accelerator, Package/Silicon + Scheduling, Parallelism, Interconnect, Storage/Reliability, Power/Cooling, Site/Grid). To teach both cross-stack breadth and hands-on loop depth without drowning students in a fragmented "simulator zoo," *Architecture 2.0* organizes its vehicles into three tiers:

| Tier | Vehicle | Stack Scope & Fidelity | Pedagogical Role in *Architecture 2.0* |
| :--- | :--- | :--- | :--- |
| **Tier 1: The 2030 North Star** | **Lighthouse Mobile XR Subsystem** (Book Ch. 1, 3, 9, 11) | **Full 8-Domain System** (`RV64GCV` + NPU + LPDDR5 + UCIe, `3 W` TDP, `120 FPS`, `3 nm-class` thermal/power/NOC co-design) | Keeps all 8 coupled system domains visible; illustrates a frontier problem that no automated loop can solve end-to-end at Layer 3 today. |
| **Tier 2: The Flagship Executed Loop Workbench** | **`nanochip` (`MoonshotAI/nano-kpu`)** (This directory: Labs 01–06) | **5-Layer Node Vertical Slice** (`Model`: KDA+MLA+MoE $\rightarrow$ `Numerics`: INT4+Q4.26 $\rightarrow$ `Schedule`: `msh_ctrl` $\rightarrow$ `Memory`: `hq` shadow cache + parity banks + 256-credit FIFO $\rightarrow$ `Silicon`: 10 RTL modules in Nangate45) | Walks **all 6 lifecycle stages end-to-end on one real, runnable system** in under 2 minutes on a laptop, stopping honestly at the pre-layout proxy boundary. |
| **Tier 3: Diagnostic Probes & Node-to-Fleet Sightlines** | **Book Studies (`ai_systolic_array_study`, `ai_cache_study`), `wakeword-rv32` (SKY130 Post-Route), & ETHZ Benchmarks** | **Post-Route GDSII & Fleet Scale** (`wakeword-rv32` SKY130 OpenROAD post-route `met1` antenna wall; `QuArch`; `AgentDSE` on `ChampSim/Timeloop`; `SWE-fficiency` & `Hawkeye`; `ArchEval` on `ASTRA-sim` 16-node all-to-all; `MLPerf Power` 512-GPU interconnect energy wall) | Paired via a **Cross-Stack Sightline** in every lab so students see how the exact same 6-stage loop laws govern CPU caches, GPU kernels, post-route DRC/antenna signoff, and datacenter fleet interconnects. |

---

## Quickstart Commands

Run these historical workbench commands from the repository root, the directory
containing `arch2` and `nanochip/`. Their paths are relative to that root, even
when this document is opened from `nanochip/docs/`. For the current construction
course, use the [cumulative student guide](../laboratory/course/README.md).

```bash
# 1. Interactive guided walkthrough of the 6-stage nano-kpu design loop
./arch2 tutorial

# 2. List all 6 progressive lifecycle labs and their physical contracts
./arch2 lab list

# 3. Execute all 6 progressive labs (verifies --mode verify, --mode break, and --mode challenge --auto)
./arch2 lab run all
# (or run directly via Python: python3 nanochip/labs/run_all.py)

# 4. Run an individual lab in interactive "Architect's Seat" challenge mode!
python3 nanochip/labs/02-explore/lab.py --mode challenge

# 5. Launch the live Architecture 2.0 X-Ray Cockpit (Terminal or Web UI)
./arch2 cockpit

# 6. Validate the publication-grade Design-Loop Card v2.0 and SHA-256 evidence packets
./arch2 validate card nanochip/cards/nano-kpu-study-card.yaml
```

Every lab supports **four execution modes**:
- `--mode break`: Observe the unguarded agent fail, cheat, or hallucinate (*"Outside the loop, confidently wrong"*).
- `--mode challenge`: **Interactive Architect's Seat** — type in your own quantitative bound, parameter configuration, or return-arrow routing decision and watch the live referee test your engineering judgment (pass `--auto` for non-interactive CI grading).
- `--mode verify`: Run the full reference referee harness against `nanochip/kpu/`.
- `--mode summary --json`: Emit machine-readable JSON receipts and Cross-Stack Sightlines.

---

## Mapping the 6 Labs to the Loop, Classical H&P Skills, and Cross-Stack Sightlines

Each lab in [`nanochip/labs/`](../labs/) corresponds to one canonical stage of the **Architecture 2.0 Life Cycle** (Chapter 3 & Chapter 12 `@tbl-classical-to-ai-native-skills`):

| Lab & Stage | Classical H&P Foundation | `--mode break` (Outside the Loop) | `--mode challenge` (Interactive Student Hook) | `--mode verify` (Inside the Loop) | Cross-Stack Sightline (Node to Fleet) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **[`01-formulate`](../labs/01-formulate/)**<br/>*1. Formulate* | Workload characterization, byte reuse & specification contracts | Unguarded agent reward-hacks `resource_budgets.json` (`25 MHz`, `COS_PASS=0.50`); caught by SHA-256 guard. | Compute max bytes/weight (`<=1.31 B`) to prove why Layer 2 FP16 fails and classify `C` vs. $\Theta$. | Verifies all 35 frozen hashes in `manifest.json` and emits the formal `FormulationRecord`. | **`QuArch` & Lighthouse XR:** Why `84–91%` recall fails when `34–73%` multi-step coupling reasoning is needed to frame a 3 W XR or MoE contract. |
| **[`02-explore`](../labs/02-explore/)**<br/>*2. Explore* | Iron Law, Roofline bounds, Amdahl's Law & Little's Law | LLM claims `20,000 tok/s` in FP16 over `16 B/cyc` DRAM, violating the `19,028 cyc/tok` (`5,255 tok/s`) byte floor. | Choose weight precision, size the fetch FIFO via Little's Law (`L = \lambda W`), and place a cycle bet. | Computes byte-traffic rooflines across FP32/FP16/INT4 and checks the `11,200 cyc/tok` `perf-model`. | **`AgentDSE` & `MLPerf Power`:** Cutting simulator calls $37\text{--}500\times$ with bottleneck telemetry; why scaling Llama 2 70B from 8 to 512 GPUs costs $3.9\times$ more energy (`12 -> 46 MJ`) on the interconnect roofline. |
| **[`03-implement`](../labs/03-implement/)**<br/>*3. Implement* | Computer arithmetic (`Q4.26`), kernel schedules & datapath design | 1-bit shift bug (`<< 13` vs. `<< 14`) has `1.000000` isolated cosine yet ruins end-to-end accuracy (`0.41`). | Align the `Q4.26` shift (`<< 14`) and algebraic zero-point fold ($\sum qx - z\sum x$) to reach 0 ULP at Row 0. | Verifies the two-boundary Representation Sandwich (`float32` $\leftrightarrow$ `fxmodel.py` $\leftrightarrow$ `rtl/`). | **`SWE-fficiency` & `Hawkeye`:** Why unguided coding agents take $2.3\times$ hot-spot shortcuts vs. $20.5\times$ expert data-representation redesigns (`>68%` in unedited functions). |
| **[`04-evaluate`](../labs/04-evaluate/)**<br/>*4. Evaluate* | Verification, pipelining hazards & static timing analysis (STA) | Catches `$fread` escape, $2\times$ DRAM latency rigid stall (`1.88x`), and 16-way parallel demux (`+96K` gates, `266.5 ns`). | Predict parallel vs. byte-serial demux area/delay (`ArchEval` L3) and configure the 3 orthogonal counter-screens. | Runs real `audit.py`, `verilator --lint-only`, and two-pass `yosys` Nangate45 synthesis (`18,331 um²`, `1.48 ns`). | **`ArchEval` (L1 vs. L3) & `ASTRA-sim`:** Why agents without a simulator miss by `81–99%` median error (and $42\times$ worse on 16-node all-to-all fleet collectives). |
| **[`05-interpret`](../labs/05-interpret/)**<br/>*5. Interpret* | Experimental attribution, memory banking & cost accounting | Blind retry loop feeds bit bugs, $2\times$ latency stalls, and bandwidth walls into one prompt (wasting 42 sims). | Route the 4 failure turns along Return Arrows `Implement`, `Explore`, or `Formulate` and audit trajectory joules. | Runs the **Causal Credit Router** across all 4 turns and emits the **`MLPerf Agents` Energy/Cost Ledger**. | **`AgentDSE` Ablations & `MLPerf Agents`:** Why *"MPKI is a proxy for miss rate, not IPC,"* and why stochastic computers are measured in **joules and simulator calls per verified outcome**. |
| **[`06-commit`](../labs/06-commit/)**<br/>*6. Commit* | Benchmarking rigor, post-route signoff & human governance | Defuses a "rubber-stamp" card claiming commercial tapeout readiness and AI self-certification (`holder_type: model`). | Audit the `2,180×` baseline denominator, flag the 4 pre-layout proxy gaps, and enforce human signoff authority. | Validates `nano-kpu-study-card.yaml` against `design-loop-card.v2.schema.json` and SHA-256 replay packets. | **`wakeword-rv32` SKY130 Post-Route & `MLPerf`:** How a pre-layout winner hits `3 met1` antenna violations after OpenROAD detailed routing, forcing a `REVISE` disposition. |

---

## Directory Layout

```text
nanochip/
├── README.md                  # This curriculum guide and forensic architectural overview
├── CREDIT.md                  # Academic & engineering credit to Moonshot AI (Kimi K3) & open EDA
├── kpu/                       # Frozen upstream MoonshotAI/nano-kpu repository (35 SHA-256 locked files)
│   ├── docs/                  # Normative task specification, architecture, interface, quantization
│   ├── reference/             # Float32 golden model (model.py), weight generator, selftest.py
│   ├── rtl/                   # Kimi K3's 10 Verilog modules (msh_chip_top .. msh_vec) + selfmodel/fxmodel.py
│   └── harness/               # Evaluation engine (evaluate.py, audit.py, check_integrity.py, synth_*.ys, tb/)
├── engine/                    # Executable 6-stage lifecycle records, roofline model, and real tool referees
├── trajectories/              # Reconstructed 5-turn trajectory receipts & Verilog failure/breakthrough variants
├── cockpit/                   # Interactive dark-mode X-Ray Web & Terminal Cockpit + SVG loop diagram
├── labs/                      # The 6 Progressive Architecture 2.0 Lifecycle Labs (break / challenge / verify)
│   ├── run_all.py             # Master runner executing all 6 labs and emitting workbench_summary.json
│   ├── 01-formulate/          # Stage 1: Epistemic Coupling (QuArch) & Cryptographic Contract Boundary
│   ├── 02-explore/            # Stage 2: Conservation-of-Bytes Roofline & Little's Law Queue Sizing
│   ├── 03-implement/          # Stage 3: The Multi-Fidelity Representation Sandwich (float32 ↔ fxmodel ↔ RTL)
│   ├── 04-evaluate/           # Stage 4: Adversarial Referees, Chaos Testing & Nangate45 Silicon Synthesis
│   ├── 05-interpret/          # Stage 5: Causal Credit Router, Return Arrows & Trajectory Energy Ledger
│   └── 06-commit/             # Stage 6: Baseline Dissection, Proxy Gaps & Design-Loop Card v2.0
└── cards/                     # Formal Governance & Auditability Artifacts
    ├── nano-kpu-study-card.yaml   # Schema v2.0 Design-Loop Card (all 6 profiles complete)
    ├── nano-kpu-study-card.md     # Human-readable companion audit report
    ├── replay.py                  # Deterministic verifier for bound evidence packets
    ├── replay-environment.json    # Pinned toolchain & manifest environment binding
    └── evidence/                  # SHA-256 bound evidence packets for claims, gates, and rejected turns
```
