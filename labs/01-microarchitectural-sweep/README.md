# Micro-Loop A: Systolic Array Microarchitectural Search and the Memory Wall

## 1. Conceptual Focus

This micro-loop answers the foundational question of AI in computer architecture: **Are we doing AI-native architecture here, or are we just doing AI-assisted or AI-driven optimization?**

Using cycle-accurate 2D systolic matrix accelerator simulation (`SCALE-Sim v3.0.0`), this exercise demonstrates how automated design searches hit an optimization plateau when confined to a single abstraction layer, and how cross-layer reasoning overcomes it.

---

## 2. Workload & Technology Constraints

* **Target Workload:** Mobile XR Matrix Multiplication kernel ($128 \times 128 \times 128$ GEMM).
* **Hardware Budget:** Fixed silicon compute budget of $1,024$ Processing Elements (PEs) and $128\text{ kB}$ on-chip SRAM per buffer.
* **Interface Constraint:** Mobile LPDDR interface providing $4\text{ words/cycle}$ peak off-chip DRAM bandwidth.

---

## 3. Paradigm Comparison

### Level 1: AI-Assisted Architecture (Open-Loop Prompting)
* **Mechanism:** An LLM generates an isolated array aspect ratio ($16 \times 64$ Output Stationary) based solely on high-level prompt text.
* **Limitation:** The workflow is strictly open-loop. The model has no visibility into downstream memory traffic. A human architect must manually launch the simulator, inspect stall cycles, and diagnose why the array spends $78\%$ of its time waiting for memory ($136,192$ execution cycles).

### Level 2: AI-Driven Optimization (Single-Layer Parameter Sweep)
* **Mechanism:** An automated optimization algorithm (Bayesian optimization, grid search, or reinforcement learning) sweeps PE aspect ratios ($8 \times 128$, $16 \times 64$, $32 \times 32$, $64 \times 16$, $128 \times 8$) under a fixed Output Stationary dataflow.
* **Limitation:** The optimizer successfully identifies the compute-optimal square array ($32 \times 32$, requiring only $32,768$ compute cycles). However, overall performance hits a hard physical ceiling at $110,592$ effective cycles because off-chip DRAM bandwidth saturates. The optimizer cannot escape this bottleneck because its search formulation is trapped within a single layer: it can only tune array geometry, not the underlying memory dataflow.

### Level 3: AI-Native System Design (Cross-Layer Closed-Loop Co-Adaptation)
* **Mechanism:** The closed-loop agent continuously inspects multidimensional physical evidence: both compute cycle utilization and off-chip memory traffic traces.
* **Cross-Layer Action:** Recognizing that DRAM bandwidth is the governing bottleneck, the system reframes the problem across architectural boundaries: it transitions execution dataflow from **Output Stationary** to **Weight Stationary**, pinning stationary weights in PE registers and restructuring on-chip double-buffering.
* **Signoff Outcome:** Off-chip DRAM access traffic plummets by $2.73\times$ (from $442\text{k}$ to $162\text{k}$ words). Effective execution time collapses from $110,592$ to $40,448$ cycles ($2.73\times$ speedup), passing all performance and energy signoff gates.

---

## 4. Anti-Reward-Hacking Guarantee

| Aspect | Description |
| :--- | :--- |
| **Naive / Hacked Proxy Metric** | Minimizing raw compute cycles ($T_{\text{comp}}$) or maximizing theoretical MAC throughput without memory modeling. |
| **Hidden Physical Failure** | Severe memory starvation: PEs remain idle $78\%$ of the time waiting for DRAM word fills across narrow memory interfaces. |
| **Grounded Signoff Gate** | **Joint Compute-Memory Roofline:** $T_{\text{effective}} = \max(T_{\text{comp}}, \lceil \text{DRAM\_Words} / \text{Bandwidth} \rceil)$. Designs are evaluated on actual wall-clock execution cycles. |
| **Toolchain Provenance** | Powered by `SCALE-Sim v3.0.0` with cycle-accurate DRAM access tracing and verified double-buffering accounting. |

---

## 5. Execution & Verification

### Running inside Docker (Recommended)
```bash
./arch2 docker lab 01
```

### Running on Host Python
```bash
python3 labs/01-microarchitectural-sweep/run.py
```

### Artifacts Generated
* `results.json`: Complete execution record with compute cycles, memory cycles, DRAM traffic, and signoff status.
* `results.png`: Visual diagnostic plot contrasting the AI-driven parameter plateau against the AI-native memory wall relief.
