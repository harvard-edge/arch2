# Micro-Loop B: RTL Generation, Synthesis, and Timing Closure

## 1. Conceptual Focus

This micro-loop answers the foundational question of AI in computer architecture: **Are we doing AI-native architecture here, or are we just doing AI-assisted or AI-driven optimization?**

Using open-source logic synthesis (`Yosys 0.33+`) and Verilog simulation (`Icarus Verilog 12.0`), this exercise demonstrates why automated synthesis parameter tuning cannot overcome fundamental structural microarchitecture bottlenecks, and how AI-native systems close timing through algorithmic refactoring with automated formal equivalence guarantees.

---

## 2. Workload & Technology Constraints

* **Target Datapath:** 32-bit Arithmetic Processing Element (PE) Accumulator.
* **Target Frequency:** $500\text{ MHz}$ ($2.0\text{ ns}$ clock period).
* **Technology Node:** $130\text{nm}$ open-source standard cell library (nominal cell delay $\approx 72\text{--}75\text{ ps}$, setup margin $80\text{ ps}$, clock-to-Q $120\text{ ps}$).
* **Signoff Criteria:** Setup Worst Negative Slack $\text{WNS} \ge 0.0\text{ ns}$ and bit-exact functional equivalence.

---

## 3. Paradigm Comparison

### Level 1: AI-Assisted Architecture (Open-Loop RTL Drafting)
* **Mechanism:** A foundation model drafts single-cycle accumulator RTL (`pe_accumulator_naive.v`) with a 32-bit addition operator (`acc <= acc + in_val`) inside the synchronous register feedback loop.
* **Limitation:** The generated RTL contains a 32-stage ripple carry chain. Static timing analysis reports a critical path delay of $2.60\text{ ns}$, producing a severe timing violation ($\text{WNS} = -0.60\text{ ns}$). The workflow is open-loop: human intervention is required to discover the timing defect.

### Level 2: AI-Driven Optimization (Single-Layer Synthesis Sweep)
* **Mechanism:** An automated EDA script tunes synthesis flags (high effort levels, aggressive gate sizing, buffer insertion, and logic flattening) while leaving the generated RTL unchanged.
* **Limitation:** Gate sizing improves delay from $2.60\text{ ns}$ to $2.072\text{ ns}$, but still violates setup timing ($\text{WNS} = -0.072\text{ ns}$). Sizing and buffering hit a physical limit: the circular carry-propagation dependency inside the single-cycle register loop is an architectural barrier that boolean synthesis cannot break.

### Level 3: AI-Native System Design (Closed-Loop Architectural Refactoring)
* **Mechanism:** The closed-loop agent ingests the negative slack timing report, identifies the 32-stage carry chain as the root cause, and refactors the microarchitecture.
* **Cross-Layer Action:** The system transforms the two's-complement adder into a **Redundant Carry-Save Accumulator** (`pe_accumulator_carry_save.v`). By storing accumulated values in redundant (Sum, Carry) vector pairs, the loop feedback path requires only a single 1-bit full adder stage.
* **Signoff Outcome:** Logic depth collapses from 32 stages to 1 stage. Datapath delay drops to $0.55\text{ ns}$, achieving a robust positive setup slack of $\text{WNS} = +1.45\text{ ns}$ ($72.5\%$ timing headroom).
* **Correctness Proof:** To guarantee that the redundant arithmetic introduces zero functional drift, the loop automatically launches an automated testbench (`tb_pe_accumulator.v`) executing 1,000 randomized 32-bit test vectors through `iverilog` and `vvp`, proving $100\%$ bit-exact equivalence.

---

## 4. Anti-Reward-Hacking Guarantee

| Aspect | Description |
| :--- | :--- |
| **Naive / Hacked Proxy Metric** | Optimizing setup slack ($\text{WNS}$) or frequency without verifying functional correctness or formal equivalence. |
| **Hidden Physical Failure** | Silent arithmetic corruption: an agent might truncate bits, drop carry logic, or pipeline registers without updating interface latencies, corrupting downstream calculations. |
| **Grounded Signoff Gate** | **Two-Key Signoff Gate:** A design must achieve BOTH positive setup slack ($\text{WNS} \ge 0.0\text{ ps}$) AND pass $1,000/1,000$ randomized verification vectors via `iverilog + vvp`. |
| **Toolchain Provenance** | Real logic synthesis executed via `Yosys 0.33+` (counting cells, DFFs, and topological path depth) and simulation via `Icarus Verilog 12.0`. |

---

## 5. Execution & Verification

### Running inside Docker (Recommended)
```bash
./arch2 docker lab 02
```

### Running on Host Python
```bash
python3 labs/02-rtl-timing/run.py
```

### Artifacts Generated
* `results.json`: Detailed synthesis metrics (cell count, DFF count, datapath delay, setup slack, and equivalence proof status).
* `results.png`: Visual slack and logic depth progression chart across all three paradigms.
