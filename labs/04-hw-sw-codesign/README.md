# Micro-Loop D: Hardware-Software Co-Design and Instruction Specialization

## Conceptual Focus

This micro-loop answers the central question: **Are we doing AI-native architecture here, or are we just doing AI-assisted or AI-driven optimization?**

Focusing on accelerating an XR perception feature-point detection kernel on a RISC-V compute tile under a 15,000 gate-equivalent (GE) area envelope, this exercise compares three operational paradigms:

1. **AI-Assisted Architecture (Level 1):**
   * **Mechanism:** An LLM drafts a scalar custom multiply-accumulate instruction opcode and inline assembly wrapper.
   * **Limitation:** Total execution takes 145,000 cycles. Although the arithmetic compute is accelerated, scalar address arithmetic (58,000 cycles) and register spills (45,000 cycles) dominate execution. The workflow is open-loop: human intervention is needed to analyze why the kernel remains slow.

2. **AI-Driven Optimization (Level 2):**
   * **Mechanism:** A compiler autotuner explores loop unrolling factors, software pipelining, and instruction scheduling across fixed hardware.
   * **Limitation:** The autotuner reduces cycles from 145,000 to 92,000 ($1.58\times$ speedup). However, aggressive unrolling causes severe register pressure on the 32 scalar registers, forcing 32,000 cycles of stack spilling. The optimization hits a ceiling because the compiler cannot modify the underlying hardware register file or addressing modes.

3. **AI-Native System Design (Level 3):**
   * **Mechanism:** The closed loop ingests the cycle-accurate profile and identifies that $62\%$ of execution time is wasted on pointer arithmetic and register file spills.
   * **Cross-layer Adaptation:** The system jointly co-designs:
     1. A 4-way SIMD fused multiply-accumulate functional unit with auto-post-increment memory addressing.
     2. A custom compiler lowering pass that transforms the nested loops into the new SIMD instruction.
     3. An area gatekeeper verification confirming that the expanded datapath (9,400 GE) respects the 15,000 GE budget.
   * **Outcome:** Execution drops to 28,500 cycles ($3.23\times$ faster than AI-driven, $5.09\times$ faster than AI-assisted), clearing the 50,000-cycle real-time deadline.

---

## Directory Contents

* `contract.yaml`: Machine-readable contract defining kernel specifications, area limits, and cycle budgets.
* `run.py`: Standalone Python runner modeling execution cycles, address overhead, register spills, and gate area.
* `results.json`: Output metrics and signoff dispositions.

---

## How to Run

From this directory, run:

```bash
python3 run.py
```
