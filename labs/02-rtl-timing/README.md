# Micro-Loop B: RTL Generation, Synthesis, and Timing Closure

## Conceptual Focus

This micro-loop answers the central question: **Are we doing AI-native architecture here, or are we just doing AI-assisted or AI-driven optimization?**

Focusing on an arithmetic processing element (PE) accumulator datapath targeting a 500 MHz clock (2.0 ns clock period), this exercise compares three operational paradigms:

1. **AI-Assisted Architecture (Level 1):**
   * **Mechanism:** A foundation model drafts single-cycle accumulator RTL (`pe_accumulator_naive.v`) with a 32-bit addition directly in the register feedback loop.
   * **Limitation:** Static timing analysis reports a critical path of 2.60 ns (-0.60 ns setup slack violation) caused by the 32-stage ripple carry chain. The workflow is open-loop: human intervention is required to discover the timing defect.

2. **AI-Driven Optimization (Level 2):**
   * **Mechanism:** An automated EDA script tunes synthesis parameters (effort levels, gate sizing, flattening, and logic restructuring) while keeping the generated RTL unchanged.
   * **Limitation:** Although gate sizing improves delay from 2.60 ns to 2.07 ns, the circuit still violates timing (-0.072 ns slack). The synthesis tool cannot close timing because the circular carry-propagation dependency inside the single-cycle register loop is an architectural barrier that boolean synthesis cannot break.

3. **AI-Native System Design (Level 3):**
   * **Mechanism:** The closed loop ingests the negative slack timing report, diagnoses the circular carry chain as the bottleneck, and refactors the RTL microarchitecture.
   * **Cross-layer Adaptation:** The system transforms the integer adder into a redundant Carry-Save Accumulator (CSA) datapath (`pe_accumulator_carry_save.v`), reducing feedback logic depth from 32 stages to a single full-adder delay (0.55 ns total delay, +1.45 ns positive setup slack).
   * **Automated Correctness Gate:** To ensure the structural refactor introduces zero functional regression, the loop runs an automated formal/functional equivalence check across 1,000 verification vectors before qualifying the design.

---

## Directory Contents

* `contract.yaml`: Machine-readable contract with clock target (500 MHz / 2.0 ns), gate budgets, and formal checks.
* `rtl/pe_accumulator_naive.v`: Baseline single-cycle accumulator with ripple carry chain.
* `rtl/pe_accumulator_retimed.v`: Two-stage pipelined accumulator with pipeline latency.
* `rtl/pe_accumulator_carry_save.v`: Redundant carry-save accumulator with single-gate feedback delay.
* `run.py`: Executable Python evaluation script running timing analysis, equivalence verification, and reporting.
* `results.json`: Output metrics and signoff dispositions.

---

## How to Run

From this directory, run:

```bash
python3 run.py
```
