# Micro-Loop A: Systolic Array Microarchitectural Search and the Memory Wall

## Conceptual Focus

This micro-loop answers the central question: **Are we doing AI-native architecture here, or are we just doing AI-assisted or AI-driven optimization?**

Using a cycle-level analytical model of a 2D systolic matrix accelerator, this exercise compares three operational paradigms on the exact same workload:

1. **AI-Assisted Architecture (Level 1):**
   * **Mechanism:** An LLM or junior engineer generates an isolated candidate geometry (for example, a $16 \times 64$ Output Stationary array) based on a textual prompt.
   * **Limitation:** The loop is open. A human must manually inspect the candidate, launch the simulator, interpret results, and decide what to do next.

2. **AI-Driven Optimization (Level 2):**
   * **Mechanism:** An automated optimization algorithm (Bayesian optimization, reinforcement learning, or grid search) explores aspect ratios ($8 \times 128$ to $128 \times 8$) within a strictly fixed formulation (Output Stationary dataflow with a 1,024-PE budget).
   * **Limitation:** The search is closed-loop, but trapped inside a single abstraction layer. As the aspect ratio changes, performance quickly plateaus because DRAM interface bandwidth saturates. The optimizer cannot escape this bottleneck because its action space only permits modifying array dimensions.

3. **AI-Native System Design (Level 3):**
   * **Mechanism:** The closed loop inspects the multidimensional execution evidence (both compute cycles and DRAM read/write traffic).
   * **Cross-layer Adaptation:** Upon detecting that the DRAM memory wall is the governing bottleneck, the system reframes the problem across architectural boundaries: it changes the execution dataflow to Weight Stationary and reconfigures on-chip SRAM buffer allocation.
   * **Outcome:** Slashes off-chip memory traffic, demonstrating how automated reasoning across abstraction boundaries resolves bottlenecks that single-layer optimizers cannot address.

---

## Directory Contents

* `contract.yaml`: Machine-readable contract defining resource budgets, interface limits, and rejection checks.
* `workload/xr_gemm.csv`: Synthetic mobile XR GEMM benchmark kernels ($M \times K \times N$).
* `run.py`: Standalone, reproducible Python runner executing all three paradigms and printing comparative metrics.
* `results.json`: Generated execution records containing candidate metrics.

---

## How to Run

From this directory, run:

```bash
python3 run.py
```
