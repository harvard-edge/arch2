# Architecture 2.0: The Grounded Micro-Loops Workbench

Welcome to the hands-on workbench for *Architecture 2.0: Principles of AI-Native System and Chip Design*.

This directory provides concrete, runnable engineering examples that answer a foundational question of the discipline: **Are we doing AI-native architecture here, or are we just doing AI-assisted or AI-driven optimization?**

---

## The Two-Tier Architecture

To make progress without getting lost in industrial CAD complexity, Architecture 2.0 separates the engineering landscape into two tiers:

1. **Tier 2: The 2030 Moonshot Horizon (Macro-Loop):**
   The grand ambition introduced in Chapter 01: an autonomous cross-domain system capable of synthesizing an entire multi-die SoC from high-level intent down to physical signoff within a 3 W thermal budget.
2. **Tier 1: Grounded Micro-Loops (The Architect's Workbench):**
   The accessible, lightweight loops provided in this directory. These loops operate across one or two tightly coupled abstractions, execute in seconds on a standard workstation, and use machine-readable contracts to govern search, evidence generation, and signoff.

---

## Three Paradigms of AI in Computer Architecture

Every micro-loop in this workbench demonstrates three distinct operational paradigms on the exact same design task:

| Paradigm | Interaction Model | Search Space Scope | Feedback Loop |
| :--- | :--- | :--- | :--- |
| **Level 1: AI-Assisted** | Human in the loop | Isolated point suggestion (code, config) | Open-loop (human manually inspects and re-prompts) |
| **Level 2: AI-Driven** | Automated optimizer | Parameter search within a single abstraction | Closed-loop within a fixed, immutable formulation |
| **Level 3: AI-Native** | Cross-domain co-design | Re-architects across abstraction boundaries | Closed-loop driven by physical and simulation evidence |

---

## The Four Grounded Micro-Loops

```
labs/
├── 01-microarchitectural-sweep/   # Micro-Loop A: Array geometry, SCALE-Sim, and the memory wall
├── 02-rtl-timing/                 # Micro-Loop B: RTL generation, synthesis, and carry-save retiming
├── 03-physical-floorplan/         # Micro-Loop C: Macro placement, routing congestion, and pin orientation
└── 04-hw-sw-codesign/             # Micro-Loop D: Custom instructions, compiler lowering, and area limits
```

### 1. [Micro-Loop A: Systolic Array Search & The Memory Wall](01-microarchitectural-sweep/)
* **Focus:** Microarchitecture and memory traffic.
* **Demonstration:** Evaluates 2D systolic matrix accelerators under a 1,024-PE budget on mobile XR GEMM workloads. Demonstrates how AI-driven parameter sweeps hit a performance ceiling due to DRAM bandwidth saturation, while AI-native co-adaptation detects the bottleneck and switches dataflow (Output Stationary to Weight Stationary) to slash memory traffic.
* **Quick Run:** `python3 01-microarchitectural-sweep/run.py`

### 2. [Micro-Loop B: RTL Generation, Synthesis & Timing Closure](02-rtl-timing/)
* **Focus:** RTL microarchitecture, synthesis, and static timing analysis.
* **Demonstration:** Targets a 500 MHz (2.0 ns period) accumulator datapath. Shows how naive RTL fails setup timing, how synthesis tuning alone cannot break circular carry loops, and how AI-native systems refactor the microarchitecture into redundant carry-save arithmetic verified by automated formal equivalence checks.
* **Quick Run:** `python3 02-rtl-timing/run.py`

### 3. [Micro-Loop C: Physical Design & Routing Congestion](03-physical-floorplan/)
* **Focus:** Macro placement, routing channels, and DRC signoff.
* **Demonstration:** Places memory macros and compute logic on a $1000 \times 1000\ \mu\text{m}$ tile. Shows how single-objective wirelength optimizers create severe routing congestion hotspots, and how AI-native loops ingest congestion heatmaps to re-orient macro pins and repartition memory banking.
* **Quick Run:** `python3 03-physical-floorplan/run.py`

### 4. [Micro-Loop D: Hardware-Software Co-Design & Instruction Specialization](04-hw-sw-codesign/)
* **Focus:** Custom ISA extensions, compiler unrolling, and area bounds.
* **Demonstration:** Accelerates an XR feature detection kernel under a 15,000 gate-equivalent area limit. Shows how scalar custom opcodes and compiler autotuning hit register spill bottlenecks, and how AI-native co-design pairs a 4-way SIMD FMA instruction with auto-increment addressing and matched compiler lowering to achieve a $5\times$ speedup.
* **Quick Run:** `python3 04-hw-sw-codesign/run.py`

---

## Related Repositories and Data

* **Empirical Chapter Studies:** Consolidated under [`data/studies/`](../data/studies/), including the full Chapter 08 SCALE-Sim reference study.
* **Design-Loop Cards & Contracts:** Located in [`examples/design-loop-cards/`](../examples/design-loop-cards/) and [`schemas/`](../schemas/).
