# Architecture 2.0: The Grounded Micro-Loops Workbench

Welcome to the hands-on engineering testbed for *Architecture 2.0: Principles of AI-Native System and Chip Design*.

> 📖 **Curriculum & Lab Manual:** See [**TUTORIAL_GUIDE.md**](TUTORIAL_GUIDE.md) for the complete 12-chapter hands-on curriculum map, university course syllabus, and interactive parameter sensitivity exercises.

This workbench provides concrete, fully grounded, executable demonstrations that answer a foundational question of modern computer architecture: **Are we doing AI-native architecture here, or are we just doing AI-assisted or AI-driven optimization?**

---

## 1. The Three Paradigms of AI in Computer Architecture

Every micro-loop in this workbench compares three operational paradigms on the exact same workload and technology constraints:

| Operational Dimension | Level 1: AI-Assisted (Point Task) | Level 2: AI-Driven (Parameterized Sweep) | Level 3: AI-Native (Cross-Layer Co-Design) |
| :--- | :--- | :--- | :--- |
| **Input Contract** | Human task query inside frozen architecture | Workload + PPA targets + Parameterized design space $\Theta$ | Workload intent + PPA limits + Correctness contract |
| **Degrees of Freedom** | Localized syntax, snippet, or scalar prediction | Parameter vector $\theta \in \Theta$ (capacities, unroll knobs, coords) | Joint structural synthesis across abstraction layers |
| **Fixed Boundary** | Entire system architecture, microarchitecture, interfaces | Structural topology, arithmetic representation, interfaces | External workload requirements and physical signoff gates |
| **Control Model** | Human-in-the-loop prompt / tool interaction | Automated optimizer / RL agent / sweep script | Closed-loop autonomous system engine |
| **Feedback Loop** | Open-loop (human inspects logs, diagnoses, repairs) | Closed-loop within an immutable formulation | Closed-loop governed by physical signoff evidence |
| **Response to Bottlenecks**| Blind to downstream physics (fails silently) | Hits optimization plateau / physical wall | Reframes problem across architectural layers |
| **Physical Signoff Rate** | **0% (0 / 4 Passed)** | **0% (0 / 4 Passed)** | **100% (4 / 4 Passed)** |

---

## 2. Anti-Reward-Hacking & Physical Grounding Guarantees

In autonomous design search, **reward hacking** occurs whenever an optimization agent exploits flaws or simplifications in a proxy objective function to maximize its reward score without delivering a physically viable, signoff-clean chip:

$$\text{Goodhart's Law for Hardware Design: } \text{When a proxy metric becomes the target, it ceases to be a good metric.}$$

The Grounded Micro-Loops Workbench enforces **strict, multidimensional Pareto gates** backed by real open-source EDA tools (Yosys, Icarus Verilog, RISC-V GCC, QEMU, SCALE-Sim) to prevent any simulated shortcuts or reward hacking:

| Micro-Loop | Naive / Hacked Proxy Metric | Hidden Physical Penalty | Grounded Signoff Gate (Workbench Enforcement) | Toolchain Provenance |
| :--- | :--- | :--- | :--- | :--- |
| **Loop A: Microarchitecture** | Compute cycles or theoretical peak MACs/s | Off-chip DRAM interface saturation ($78\%$ stall time) | Joint Roofline Latency: $T_{\text{effective}} = \max(T_{\text{comp}}, T_{\text{dram}})$ | `SCALE-Sim v3.0.0` (Cycle-accurate DRAM access traces) |
| **Loop B: RTL & Synthesis** | Target clock frequency / positive slack | Logic depth violation, carry ripple, functional corruption | Boolean Logic Depth + Bit-Exact Formal Verification (1,000 randomized vectors) | `Yosys 0.33+` (RTL synthesis) & `iverilog` + `vvp` (Formal/functional equivalence) |
| **Loop C: Physical Design** | Half-Perimeter Wirelength (HPWL) minimization | Routing track saturation and pin-escape shorts ($>85\%$ density) | 2D RUDY Routing Congestion Heatmap + Design Rule Check ($0$ DRC shorts allowed) | Physics-Grounded Track Capacity & RUDY Router (Metal 3/4 130nm pitch) |
| **Loop D: HW/SW Co-Design** | Scalar instruction speedup or loop unrolling | Register file exhaustion and stack thrashing ($32,000$ spill cycles) | End-to-End Execution Profile (ALU + Address Math + Spills) + Area Gate ($\le 15,000\text{ GE}$) | `riscv64-linux-gnu-gcc 13.3+` & `objdump` (Disassembly spill profiling) |

---

## 3. The Four Grounded Micro-Loops

```
labs/
├── 01-microarchitectural-sweep/   # Micro-Loop A: Systolic array geometry & the memory wall
├── 02-rtl-timing/                 # Micro-Loop B: RTL generation, synthesis, & carry-save retiming
├── 03-physical-floorplan/         # Micro-Loop C: Macro placement, RUDY congestion, & pin breakout
├── 04-hw-sw-codesign/             # Micro-Loop D: Custom ISA extensions, compiler spills, & area limits
├── notebooks/                     # Interactive Marimo and Google Colab notebooks
│   ├── workbench.py               # Reactive Marimo notebook with dynamic parameter sliders
│   └── workbench.ipynb            # Synced Jupyter / Google Colab notebook
├── demo.py                        # Master console interactive demonstration
├── run_all.py                     # Non-interactive CLI runner for automated CI
└── workbench_summary.json         # Structured machine-readable results across all loops
```

### [Micro-Loop A: Systolic Array Search & The Memory Wall](01-microarchitectural-sweep/)
* **Domain:** Microarchitecture & Memory Hierarchy.
* **Workload:** Mobile XR Matrix Multiplication ($128 \times 128 \times 128$ GEMM).
* **Workstation Hardware Budget:** $1,024$ Processing Elements (PEs), $4\text{ words/cycle}$ LPDDR memory bandwidth.
* **Why Baselines Fail:**
  * *AI-Assisted:* Proposes an unbalanced $16 \times 64$ Output Stationary array based on generic prompt text; stalls for $136,192$ cycles because DRAM cannot feed it.
  * *AI-Driven:* Sweeps aspect ratios from $8 \times 128$ to $128 \times 8$. Finds the compute-optimal $32 \times 32$ square array ($32,768$ compute cycles), but hits an insurmountable DRAM bandwidth ceiling of $110,592$ effective cycles. The optimizer is trapped because its action space is restricted to geometry.
* **AI-Native Breakthrough:** Crosses architectural abstraction layers: detects the memory stall signature and switches dataflow to **Weight Stationary**, pinning weights on-chip to slash off-chip DRAM traffic by $2.73\times$ ($442\text{k}$ down to $162\text{k}$ words) and cutting runtime to $40,448$ cycles ($2.73\times$ end-to-end speedup).

### [Micro-Loop B: RTL Generation, Synthesis & Timing Closure](02-rtl-timing/)
* **Domain:** RTL Microarchitecture, Logic Synthesis, and Static Timing Analysis (STA).
* **Workload:** Processing Element (PE) accumulator datapath targeting $500\text{ MHz}$ ($2.0\text{ ns}$ cycle period) in $130\text{nm}$.
* **Why Baselines Fail:**
  * *AI-Assisted:* Drafts syntactically clean single-cycle Verilog (`pe_accumulator_naive.v`) with a 32-bit addition directly in the register feedback loop. Logic depth is 32 full adder stages, yielding $2.60\text{ ns}$ delay ($-600\text{ ps}$ setup violation).
  * *AI-Driven:* Sweeps boolean synthesis flags (high effort, aggressive gate sizing, flattening). Sizing marginally reduces gate delay from $2.60\text{ ns}$ to $2.072\text{ ns}$, but still violates timing ($-72\text{ ps}$ slack). Boolean logic synthesis cannot eliminate the circular carry-propagation dependency across the 32-bit register feedback loop.
* **AI-Native Breakthrough:** Couples physical timing analysis directly to algorithmic refactoring: transforms standard two's-complement arithmetic into a **Redundant Carry-Save Accumulator** (`pe_accumulator_carry_save.v`). This collapses feedback logic depth from 32 stages to a single full-adder delay ($0.55\text{ ns}$ total delay, $+1.45\text{ ns}$ positive slack). An automated formal equivalence testbench (`tb_pe_accumulator.v`) exercises 1,000 randomized vectors through `iverilog` and `vvp` to prove bit-exact correctness.

### [Micro-Loop C: Physical Floorplanning & Routing Congestion](03-physical-floorplan/)
* **Domain:** Physical Design, Macro Placement, and Routing Routability.
* **Workload:** On-chip accelerator tile ($1000 \times 1000\ \mu\text{m}$) placing standard compute core and 4 memory macros.
* **Why Baselines Fail:**
  * *AI-Assisted:* Proposes uncoordinated $(x,y)$ coordinates. High half-perimeter wirelength ($\text{HPWL} = 12,400\ \mu\text{m}$) and acute track overflow ($94.2\%$ peak congestion) trigger 18 DRC shorts.
  * *AI-Driven:* Minimizes wirelength using single-objective optimization. Successfully compresses HPWL to $7,820\ \mu\text{m}$ ($-36.9\%$), but packs macros tightly around the compute core with inward-facing pin clusters. This creates severe routing track starvation ($91.8\%$ peak congestion, exceeding the $85\%$ physical DRC threshold) and causes 12 DRC shorts.
* **AI-Native Breakthrough:** Ingests the 2D RUDY routing congestion heatmap. Rather than continuing to push geometric coordinates, it reframes the physical interface: it **rotates macro pin orientations outward** and provisions **dedicated $110\ \mu\text{m}$ routing corridors**. Peak congestion drops to $64.5\%$ and DRC shorts drop to exactly zero ($0$ violations), achieving DRC-clean tapeout signoff.

### [Micro-Loop D: Hardware-Software Co-Design & Instruction Specialization](04-hw-sw-codesign/)
* **Domain:** Instruction Set Architecture (ISA), Compiler Optimization, and Hardware Area Limits.
* **Workload:** Mobile XR perception feature-point detection filter under a strict real-time deadline ($\le 50,000\text{ cycles}$) and silicon area budget ($\le 15,000\text{ Gate Equivalents}$).
* **Why Baselines Fail:**
  * *AI-Assisted:* Drafts an isolated scalar custom multiply-accumulate instruction (`custom.dot`). While the arithmetic calculation is fast, address math ($58,000\text{ cycles}$) and register spills ($45,000\text{ cycles}$) dominate total runtime ($145,000\text{ cycles}$ total, $2.9\times$ over budget).
  * *AI-Driven:* Uses compiler autotuning (aggressive loop unrolling with unroll factor 8 and software pipelining) on fixed hardware. Unrolling exhausts the 32 physical scalar registers, forcing $32,000\text{ cycles}$ of stack memory thrashing ($92,000\text{ cycles}$ total, still $1.84\times$ over budget).
* **AI-Native Breakthrough:** Simultaneously co-designs across hardware and compiler abstractions:
  1. **Hardware:** Implements a 4-way packed SIMD FMA execution unit with integrated **auto-post-increment memory addressing**.
  2. **Compiler:** Implements a matched lowering pass converting array accesses into post-increment vector primitives.
  3. **Area Signoff:** Verifies datapath area ($9,400\text{ GE}$) against the $15,000\text{ GE}$ ceiling ($5,600\text{ GE}$ headroom).
  Total execution collapses to $28,500\text{ cycles}$ ($5.09\times$ overall speedup), meeting all timing and area budgets.

---

## 4. Choose Your Entrypoint

The workbench supports three seamless execution modes depending on your workflow:

### Option A: The Containerized EDA Workbench (Docker)

Recommended for researchers requiring the fully verified, bit-exact open-source EDA suite without managing local tools.

```bash
# 1. Build the self-contained EDA container
./arch2 docker build

# 2. Run the interactive master demonstration
./arch2 docker demo

# 3. Run individual micro-loops inside Docker
./arch2 docker lab 01    # Micro-Loop A
./arch2 docker lab 02    # Micro-Loop B (runs real Yosys + Icarus Verilog)
./arch2 docker lab 03    # Micro-Loop C
./arch2 docker lab 04    # Micro-Loop D (runs real RISC-V GCC + QEMU)
```

*(See [`docker/README.md`](../docker/README.md) for full Docker details).*

### Option B: One-Click Cloud Execution (Google Colab)

Run the entire workbench inside a free, cloud-hosted Linux virtual machine with pre-installed toolchains:

1. Open [`labs/notebooks/workbench.ipynb`](notebooks/workbench.ipynb) directly in Google Colab.
2. Run the first initialization cell:
   ```bash
   !apt-get update -qq && apt-get install -y yosys iverilog gcc-riscv64-linux-gnu qemu-user-static
   !pip install scalesim rich
   !git clone https://github.com/harvard-edge/arch2.git /content/arch2
   %cd /content/arch2
   !python3 labs/demo.py
   ```
3. Use the reactive widgets to explore trade-off spaces in real time.

### Option C: In-Browser Reactive App (Marimo & WebAssembly)

Run the interactive Marimo notebook locally or directly in your browser without installing Python:

* **In-Browser WebAssembly:** Visit the [Architecture 2.0 Web Companion](https://harvard-edge.github.io/arch2/workbench.html) to launch the zero-install client-side WebAssembly application.
* **Local Marimo Server:**
  ```bash
  pip install marimo scalesim rich
  marimo edit labs/notebooks/workbench.py
  ```

---

## 5. Automated Verification & Testing

Every micro-loop is validated by automated unit tests and schema validators:

```bash
# Run the full test suite
python3 -m unittest discover tests

# Verify precommit constraints and data provenance
./arch2 check precommit
```
