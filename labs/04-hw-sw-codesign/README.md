# Micro-Loop D: Hardware-Software Co-Design and Instruction Specialization

## 1. Conceptual Focus

This micro-loop answers the foundational question of AI in computer architecture: **Are we doing AI-native architecture here, or are we just doing AI-assisted or AI-driven optimization?**

Using real RISC-V cross-compilation (`riscv64-linux-gnu-gcc 13.3+`), disassembly inspection (`objdump`), and cycle-accurate execution profiling, this exercise demonstrates why isolating software compilation from hardware datapath design leads to register file thrashing, and how AI-native co-adaptation achieves true system Pareto optimality.

---

## 2. Workload & Technology Constraints

* **Target Kernel:** Mobile XR Spatial Feature-Point Detection ($256 \times 256$ pixel matrix filter).
* **Hardware Area Ceiling:** Maximum datapath budget of $15,000\text{ Gate Equivalents (GE)}$.
* **Real-Time Latency Deadline:** Execution time $\le 50,000\text{ clock cycles}$ (to meet 120 FPS XR tracking requirements).
* **Baseline Architecture:** RV32/RV64 RISC-V core with 32 standard scalar integer registers.

---

## 3. Paradigm Comparison

### Level 1: AI-Assisted Architecture (Open-Loop Custom Opcode Drafting)
* **Mechanism:** An LLM inspects the C kernel and drafts an isolated custom scalar multiply-accumulate instruction (`custom.dot`) and an inline assembly wrapper.
* **Limitation:** While the custom arithmetic instruction executes quickly, total runtime remains sluggish at $145,000\text{ cycles}$ ($2.9\times$ over the deadline). The model overlooked that $71\%$ of runtime is spent calculating pixel memory addresses ($58,000\text{ cycles}$) and spilling temporary values ($45,000\text{ cycles}$). The workflow is open-loop: human intervention is needed to diagnose why the kernel is slow.

### Level 2: AI-Driven Optimization (Single-Layer Compiler Autotuning)
* **Mechanism:** A compiler autotuner (e.g. LLVM loop-opt, GCC `-O3` search) explores unrolling factors and software pipelining across the fixed scalar core.
* **Limitation:** The autotuner unrolls the inner loop by factor 8, cutting execution to $92,000\text{ cycles}$ ($1.58\times$ speedup). However, unrolling exhausts the 32 physical scalar registers, forcing the compiler to emit $32,000\text{ cycles}$ of stack memory spills and reloads (`sw`/`lw` instructions). The optimization hits a wall because the software compiler cannot alter hardware register files or addressing modes.

### Level 3: AI-Native System Design (Closed-Loop Hardware-Software Co-Design)
* **Mechanism:** The closed-loop agent ingests the cycle-accurate profile, diagnoses that pointer calculation and stack spilling are the dominant bottlenecks, and executes a joint co-adaptation:
  1. **Hardware Specialization:** Designs a 4-way packed SIMD FMA execution unit featuring **auto-post-increment addressing modes** (`vdot4.postinc v0, (a0)+, (a1)+`).
  2. **Matched Compiler Lowering:** Re-targets the compiler's loop vectorizer to emit the fused post-increment instruction directly.
  3. **Silicon Area Gatekeeper:** Confirms through logic synthesis that the expanded SIMD datapath consumes $9,400\text{ GE}$, staying well within the $15,000\text{ GE}$ envelope ($5,600\text{ GE}$ headroom).
* **Signoff Outcome:** Total execution collapses to $28,500\text{ cycles}$ ($3.23\times$ faster than AI-driven, $5.09\times$ faster than baseline), comfortably beating the $50,000$-cycle real-time budget.

---

## 4. Anti-Reward-Hacking Guarantee

| Aspect | Description |
| :--- | :--- |
| **Naive / Hacked Proxy Metric** | Minimizing arithmetic instruction count or claiming high IPC without accounting for address math or register spills. |
| **Hidden Physical Failure** | Severe register file exhaustion: unrolled loops exceed physical register limits, quietly generating thousands of stack memory read/write cycles that stall execution. |
| **Grounded Signoff Gate** | **Full-System Cycle & Area Accounting:** Total cycles are measured across compute, address arithmetic, and stack memory spills ($T_{\text{total}} = T_{\text{comp}} + T_{\text{addr}} + T_{\text{spill}}$) alongside physical gate area ($\le 15,000\text{ GE}$). |
| **Toolchain Provenance** | Real cross-compilation with `riscv64-linux-gnu-gcc 13.3+` and disassembly stack spill analysis via `objdump`. |

---

## 5. Execution & Verification

### Running inside Docker (Recommended)
```bash
./arch2 docker lab 04
```

### Running on Host Python
```bash
python3 labs/04-hw-sw-codesign/run.py
```

### Artifacts Generated
* `results.json`: Complete instruction mix (arithmetic, address math, register spills), cycle breakdowns, and gate-equivalent area.
* `results.png`: Stacked cycle breakdown bar chart and multi-objective Pareto trade-off plot.
