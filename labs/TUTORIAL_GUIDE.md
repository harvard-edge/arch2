# Architecture 2.0: Chapter-by-Chapter Curriculum & Laboratory Manual
## Hands-on Experimental Companion to *Principles of AI-Native System and Chip Design*
**Author:** Vijay Janapa Reddi
**Audience:** Graduate students, researchers, systems architects, and chip design engineers.

---

## The Pedagogical Philosophy: Physical Friction in Computer Architecture

In software engineering, if code compiles cleanly and passes unit tests, it is generally considered correct and shippable.
In computer architecture and silicon engineering, **hardware is not software: silicon cannot be negotiated with.**

Syntactically valid Verilog can produce a catastrophic timing violation. An optimal floorplan under Half-Perimeter Wirelength (HPWL) can produce an unroutable chip with dozens of short-circuits. Aggressive compiler loop unrolling can trigger thousands of cycles of register stack spills that choke the memory bus.

The purpose of this laboratory manual is to bridge the theoretical principles presented in the Synthesis Lecture monograph with empirical, reproducible friction in real open-source EDA tools (**Yosys**, **Icarus Verilog**, **SCALE-Sim**, **RISC-V GCC**, **QEMU**, and **2D RUDY**).

---

## 1. Quickstart: Containerized EDA Laboratory Environment

The entire laboratory suite runs inside a self-contained, reproducible Docker image containing all open-source toolchains, PDK models (SkyWater SKY130), and cycle simulators.

### Option 1: Docker (Recommended, Zero Host Dependencies)
```bash
# Pull and run the pre-built container image:
docker run -it -v $(pwd):/workspace ghcr.io/harvard-edge/arch2-workbench:latest

# Or build locally using the CLI driver:
./arch2 docker build
./arch2 docker demo
```

### Option 2: Local Python & EDA Suite
```bash
# 1. Install Python dependencies
pip install rich typer scalesim numpy scipy matplotlib

# 2. Run the interactive tutorial runner
./arch2 tutorial --hero

# 3. Explore parameter sensitivity sweeps
./arch2 tutorial --explore
```

---

## 2. Chapter-by-Chapter Laboratory Curriculum Map

| Chapter | Title & Core Theme | Hands-on Command | What the Learner Inspects & Runs | "Knobs to Turn" (Interactive Experiments) | Physical Law Demonstrated |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Ch 01: The Moonshot** | AI-Native Design & The 3 Paradigms | `./arch2 tutorial --hero` | Live 90-second 3-Act drama on 500 MHz PE accumulator in SKY130. | Press `[Enter]` to advance through Assisted (0/4), Driven (0/4), and Native (4/4). | Syntax $\neq$ Silicon: Open-loop LLM prompts fail physical timing signoff. |
| **Ch 02: Pressures** | The Memory Wall & Wire RC Limits | `./arch2 lab 01` | SCALE-Sim execution of Mobile XR matrix multiplication (`xr_gemm.csv`). | Modify DRAM bandwidth (4 vs 8 words/cyc) in `labs/01-microarchitectural-sweep/run.py`. | Amdahl's Memory Wall: Compute speedups stall when DRAM bandwidth saturates. |
| **Ch 03: Lifecycle** | The 6-Stage AI-Native Lifecycle | `./arch2 tutorial --hero --presenter` | Step through Intent $\to$ Form $\to$ Environment $\to$ Feedback $\to$ Co-Adapt $\to$ Verify. | Inspect speaker cues explaining why each stage requires physical verification. | The Closed-Loop Feedback Invariant: Feedback must cross abstraction layers. |
| **Ch 04: Representations** | Algebraic Forms vs. Tokenized RTL | `./arch2 tutorial --explore` | Compare 32-bit ripple carry vs. Redundant Carry-Save Arithmetic (CSA). | Toggle bitwidth from 16 to 128 bits: observe $O(N)$ vs $O(1)$ delay scaling. | Representation Gap: Token-level LLMs cannot mutate underlying arithmetic recurrences. |
| **Ch 05: Methods** | Local Search vs. Asymptotic Bounds | `./arch2 lab 02 --paradigm driven` | Multi-pass Yosys gate sizing and buffer insertion sweep. | Inspect diminishing returns table (Iter 1 $\to$ 25 stalling at $-72\text{ ps}$). | The Sizing Asymptote: Logical Effort intrinsic delay limit ($d = gh + p$). |
| **Ch 06: Environments** | Tool Variance & Structured Receipts | `./arch2 docker run -- yosys -version` | Structured `results.json` signoff execution records with tool provenance hashes. | Inspect `labs/02-rtl-timing/results.json` for WNS, TNS, and cell count breakdowns. | Determinism & Grounding: Autonomous loops require signoff-grade execution records. |
| **Ch 07: Feedback** | Anti-Reward-Hacking & Formal Gates | `./arch2 lab 02` | Automated 1,000-vector bit-exact simulation testbench (`iverilog + vvp`). | Mutate RTL to fake positive slack (`acc <= 0;`) and watch testbench fail. | Goodhart's Law for Silicon: Optimizers targeting slack alone will delete logic. |
| **Ch 08: The Loop** | Autonomous Pareto Search | `./arch2 lab 01 --visual` | 2D Pareto frontier of Cycle Latency vs. Off-Chip DRAM Traffic. | Inspect generated `labs/01-microarchitectural-sweep/results.png`. | Multi-Objective Non-Domination: Pareto fronts reveal hidden physical trade-offs. |
| **Ch 09: Patterns** | Dedicated Avenues & Pin Breakouts | `./arch2 lab 03` | 2D RUDY routing congestion heatmaps for macro floorplanning. | Toggle macro channel spacing (0 to 110 $\mu\text{m}$) in `labs/03-physical-floorplan/run.py`. | The Routing Corridor Pattern: Eliminating macro pin starvation beats raw HPWL. |
| **Ch 10: Evaluation** | The Proxy Metric Trap | `./arch2 lab 04` | RISC-V disassembly spill profiling (`riscv64-linux-gnu-gcc` + `objdump`). | Increase compiler unroll factor from 2 to 8: observe 32k cycle stack spill explosion. | The Proxy Metric Trap: Local compiler optimizations trigger memory subsystem thrashing. |
| **Ch 11: Ownership** | Verification Liability & Chicken Bits | `./arch2 lab 02` | Equivalence proof receipts comparing golden reference against co-adapted RTL. | Inspect `tb_pe_accumulator.v` mismatch counters and assertion logs. | Verification Authority: AI-generated silicon requires bit-exact bounded verification. |
| **Ch 12: Ecosystem** | Open Silicon & SkyWater SKY130 | `./arch2 lab 02` | Synthesis cell reports using real `sky130_fd_sc_hd` standard cell library. | Inspect cell area, DFF counts, and combinational gate distributions in Yosys logs. | The Open-Source EDA Revolution: Commodity compute and open PDKs democratize research. |

---

## 3. Detailed Laboratory Exercises

### Lab 01: Microarchitectural Exploration & The Memory Wall
* **Target Chapter:** Chapter 02 (Pressures) & Chapter 08 (The Loop)
* **Directory:** `labs/01-microarchitectural-sweep/`
* **Workload:** Mobile XR Matrix Multiplication ($128 \times 128 \times 128$ GEMM across Projection, Attention, and Head layers).
* **Physical Constraint:** $1,024$ Processing Elements (PEs), $4\text{ words/cycle}$ DRAM interface bandwidth (4.0 GB/s wearable envelope).
* **The Experiment:**
  1. Run the baseline sweep: `python3 labs/01-microarchitectural-sweep/run.py`
  2. Inspect the generated plot `results.png`.
  3. **Hands-on Knob:** Open `labs/01-microarchitectural-sweep/run.py`. Change `dram_bandwidth` from 4 to 8 words/cycle. Notice how the memory wall shifts, but Output Stationary still spends over 50% of runtime waiting for partial sum writebacks.
  4. **The "Aha!" Moment:** Switch dataflow to Weight Stationary (`WS`). DRAM traffic drops from 442k words to 162k words (a $2.73\times$ reduction), unlocking the compute array.

### Lab 02: RTL Timing Closure & Arithmetic Representation
* **Target Chapter:** Chapter 03 (Lifecycle), Chapter 04 (Representations), & Chapter 07 (Feedback)
* **Directory:** `labs/02-rtl-timing/`
* **Workload:** 32-bit Systolic PE Datapath Accumulator running at 500 MHz ($T_{clk} = 2.000\text{ ns}$) in SkyWater SKY130.
* **The Experiment:**
  1. Run the hero tutorial: `./arch2 tutorial --hero`
  2. Run the sensitivity exploration: `./arch2 tutorial --explore`
  3. **Hands-on Knob:** In `labs/02-rtl-timing/rtl/pe_accumulator_naive.v`, observe the circular addition:
     ```verilog
     acc_out <= acc_out + data_in; // 32-bit ripple carry chain in feedback loop!
     ```
  4. Synthesize with Yosys: `yosys -p "read_verilog labs/02-rtl-timing/rtl/pe_accumulator_naive.v; synth -top pe_accumulator_naive; stat; ltp -noff"`
  5. Observe the 32-stage logic depth and $-0.600\text{ ns}$ WNS violation.
  6. **The "Aha!" Moment:** Inspect `labs/02-rtl-timing/rtl/pe_accumulator_carry_save.v`. Notice how splitting `sum_reg` and `carry_reg` isolates each bit's addition to a single full adder. Logic depth collapses to 1 stage ($0.55\text{ ns}$ delay), giving $+1.450\text{ ns}$ of positive slack margin!
  7. Run the formal equivalence check: `iverilog -o tb labs/02-rtl-timing/tb/tb_pe_accumulator.v && vvp tb`
  8. Confirm that all 1,000 randomized vectors match bit-exact against the golden reference.

### Lab 03: Macro Placement & The Routing Congestion Paradox
* **Target Chapter:** Chapter 05 (Methods) & Chapter 09 (Patterns)
* **Directory:** `labs/03-physical-floorplan/`
* **Workload:** $1000 \times 1000\text{ }\mu\text{m}$ SkyWater SKY130 tile placing a central compute core and 4 SRAM blocks.
* **The Experiment:**
  1. Run the floorplan evaluator: `python3 labs/03-physical-floorplan/run.py`
  2. Inspect the generated 2D RUDY congestion heatmap `results.png`.
  3. **Hands-on Knob:** In `labs/03-physical-floorplan/run.py`, examine the AI-Driven placement: it minimizes wirelength ($\text{HPWL} = 7,820\text{ }\mu\text{m}$, $-37\%$), but packs SRAM pins facing inward into a $40\text{ }\mu\text{m}$ central channel.
  4. Notice that RUDY routing congestion is pegged at **100.0%** (unroutable, 2 DRC pin shorts).
  5. **The "Aha!" Moment:** Inspect the AI-Native solution: it rotates the SRAM pins outward and inserts **110 $\mu\text{m}$ dedicated routing avenues**. Even though HPWL slightly increases to $8,240\text{ }\mu\text{m}$, peak congestion collapses to **34.3%** with **0 DRC shorts**!

### Lab 04: HW/SW Co-Design & The Register Spilling Explosion
* **Target Chapter:** Chapter 04 (Representations) & Chapter 10 (Evaluation)
* **Directory:** `labs/04-hw-sw-codesign/`
* **Workload:** Real-time Mobile XR 2D Feature Point Filter ($256 \times 256$ frame) under $\le 50,000\text{ cycles}$ and $\le 15,000\text{ Gate Equivalents}$.
* **The Experiment:**
  1. Run the co-design profiler: `python3 labs/04-hw-sw-codesign/run.py`
  2. Inspect the cycle breakdown in `results.png`.
  3. **The Proxy Metric Trap:** Observe the AI-Driven approach: it applies `-funroll-loops` (unroll=8). Inner compute cycles drop, but live variable ranges exceed the 32 physical registers of RV32, forcing GCC to emit **32,000 cycles of stack spills** (`sw`/`lw` thrashing the cache). Total cycles: 92,000 (1.84x over budget).
  4. **The "Aha!" Moment:** Inspect the AI-Native co-design: a 4-way SIMD FMA datapath with hardware auto-post-increment addressing (`vdot4.postinc`). Pointer calculation cycles drop from 58k to 6k (-89.7%), and register spills drop from 45k to 10k, achieving **28,500 total cycles (5.09x speedup)** within 9,400 GE.

---

## 4. Four-Week University Course Syllabus Blueprint

This laboratory suite is turnkey and ready for adoption in graduate courses on Computer Architecture, VLSI Design, or AI Systems (e.g., CS/EE 200-level courses):

* **Week 1: Microarchitectural Search, Roofline Analysis, and Memory Walls**
  - Readings: Chapters 1, 2, and 8.
  - Lab: Lab 01 (Systolic Arrays). Students sweep aspect ratios, model DRAM stall cycles, and implement Weight Stationary dataflow.
* **Week 2: Logic Synthesis, Critical Paths, and Arithmetic Representations**
  - Readings: Chapters 3, 4, and 7.
  - Lab: Lab 02 (RTL Timing). Students synthesize ripple-carry vs. carry-save datapaths in Yosys, extract timing paths, and write formal equivalence testbenches.
* **Week 3: Physical Design, Placement Proxies, and Wire Congestion**
  - Readings: Chapters 5, 6, and 9.
  - Lab: Lab 03 (Physical Floorplanning). Students compute HPWL vs. 2D RUDY routing congestion, observe track starvation, and design dedicated routing avenues.
* **Week 4: Hardware-Software Co-Design, Compilers, and Silicon Budgets**
  - Readings: Chapters 10, 11, and 12.
  - Lab: Lab 04 (HW/SW Co-Design). Students profile instruction traces in RISC-V, detect register spill explosions, and co-design custom SIMD instructions with compiler lowering.

---

## 5. Summary: How the Workbench Proves the Thesis

| Dimension | AI-Assisted (Open-Loop) | AI-Driven (Single-Layer) | AI-Native (Cross-Layer) |
| :--- | :--- | :--- | :--- |
| **Methodology** | LLM Prompting | Automated Parameter Sweeps | Joint Cross-Domain Co-Adaptation |
| **Tool Feedback** | None (Text-only) | Local scalar metric (HPWL, Area) | Multidimensional physical signoff gates |
| **Physical Reality** | 0 / 4 Passed (0%) | 0 / 4 Passed (0%) | 4 / 4 Passed (100%) |
| **Durable Principle** | Hardware is not text. | Local search hits structural asymptotes. | Physics demands cross-layer co-adaptation. |
