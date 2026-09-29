# Architecture 2.0 Teaching Labs: Reading Map and Exercises

Companion exercises for *Architecture 2.0: Principles of AI-Native System and Chip Design*, by Vijay Janapa Reddi.

**Audience:** graduate students, researchers, and engineers reading the book alongside a course or a reading group.

---

## What These Labs Are

The four labs are exercises for reasoning about design loops. They are not measurements. Each lab mixes values computed by a tool or model with values the lab author wrote into the script, and [README.md](README.md#2-what-is-computed-and-what-is-authored) lists which is which for every lab. When a lab prints a slack, a cycle count, a wirelength, or a gate-equivalent area, check that table before drawing any conclusion from it.

The labs are useful for practicing the moves the book teaches. A reader can ask what the tool actually returned, which values are fixtures, what a fair comparison would require, and what the output could and could not support. Treating a lab's printed "signoff PASS" as evidence would be exactly the mistake the book warns against.

---

## 1. Setup

### Docker

```bash
./arch2 docker build
./arch2 docker demo
./arch2 docker lab 02
```

### Local Python

```bash
pip install rich typer scalesim numpy scipy matplotlib pyyaml
./arch2 tutorial --hero       # guided walkthrough of Loop B
./arch2 tutorial --explore    # parameter sweeps over bitwidth and frequency
./arch2 lab run 01            # run one lab directly
```

Without Yosys, Icarus Verilog, SCALE-Sim, or a RISC-V cross-compiler installed, the labs fall back to analytical models and say so in their printed provenance.

---

## 2. Chapter Reading Map

The book has eleven chapters. Not every chapter has a matching lab, and the labs are optional throughout.

| Chapter | Suggested lab activity | Question to bring to the lab |
| :--- | :--- | :--- |
| **The Architecture Moonshot** | `./arch2 tutorial --hero` | Which of the three modes corresponds to point assistance, to optimization inside a frozen container, and to a move across an abstraction boundary? Who chose that move in the lab? |
| **Compounding Pressures and Scaling Limits** | Lab 01 | Under the model's bandwidth limit, why does no array geometry escape the memory bound? |
| **The AI-Native Design Life Cycle** | `./arch2 tutorial --hero --presenter` | Map the walkthrough onto the six stages: Formulate, Explore, Implement, Evaluate, Interpret, and Commit. Which stages does the lab skip or script? |
| **Data, Knowledge, and Representation** | `./arch2 tutorial --explore`, Lab 02 | What does the carry-save representation change that a token-level edit to the naive RTL would not? |
| **Prediction, Generation, and Optimization** | Lab 02 with `--paradigm driven` | The `driven` slack comes from an authored logic depth. What tool output would be needed to make that comparison real? |
| **Execution Harnesses and Tool Isolation** | Inspect `labs/02-rtl-timing/results.json` | Which fields came from Yosys, and which from constants in `run.py`? What would a reviewer need to rerun the Yosys part? |
| **Verification, Feedback, and Learning** | Lab 02, then edit the carry-save RTL | Break the carry-save accumulator on purpose and watch the random-vector comparison fail. What would it miss that a formal equivalence check would catch? |
| **Pattern Transferability and Generalization** | Lab 03 | Does the lesson from the authored layouts depend on the congestion model's simplifications? What would have to hold for it to transfer to a real router? |
| **System Evaluation and Red-Teaming** | Lab 04, `./arch2 referee red-team` | Every cycle count in Lab 04 is a fixture. Design the matched-budget comparison that would test its claim. |
| **What the Architect Owns** | Review all four `results.json` files | Which of these outputs could support a commitment, and which could support none? |
| **Bootstrapping an AI-Native Ecosystem** | Lab 02 synthesis logs | What does an open standard-cell library make possible for a course, and what does it still leave unmeasured? |

---

## 3. Lab Exercises

### Lab 01: Systolic Array Geometry and the Memory Wall
* **Directory:** `labs/01-microarchitectural-sweep/`
* **Workload:** three XR matrix-multiplication layers in `workload/xr_gemm.csv`.
* **Constraint:** 1,024 processing elements and 4 words per cycle of off-chip bandwidth, set in `contract.yaml`.
* **Exercise:**
  1. Run `python3 labs/01-microarchitectural-sweep/run.py` and note whether the output came from SCALE-Sim or the analytical fallback.
  2. Change `interface_bandwidth_words_per_cycle` in `contract.yaml` and rerun. Watch how the memory-bound fraction of each candidate changes.
  3. Read the weight-stationary branch of `evaluate_systolic_array`. Its traffic reduction rests on the assumption that a 128 KiB buffer holds each layer's weights. Decide whether that assumption holds for these layer shapes.

### Lab 02: RTL Timing and Arithmetic Representation
* **Directory:** `labs/02-rtl-timing/`
* **Design:** a 32-bit accumulator at a 2.0 ns clock target on SkyWater SKY130 cells.
* **Exercise:**
  1. Synthesize the naive accumulator yourself: `yosys -p "read_verilog labs/02-rtl-timing/rtl/pe_accumulator_naive.v; synth -top pe_accumulator_naive; stat; ltp -noff"`.
  2. Compare the cell and flip-flop counts with the carry-save version. These come from Yosys.
  3. Find the slack calculation in `run.py`. It uses authored logic depths and per-stage delays, so the printed slack is illustrative. Sketch how you would replace it with a static timing analyzer run on the synthesized netlist.
  4. Run the random-vector comparison in `rtl/tb_pe_accumulator.v` through `iverilog` and `vvp`. It compares the two designs on 1,000 random inputs; it does not prove equivalence.

### Lab 03: Macro Placement and Routing Congestion
* **Directory:** `labs/03-physical-floorplan/`
* **Design:** a $1000 \times 1000\ \mu\text{m}$ tile with a compute core and four SRAM macros.
* **Exercise:**
  1. Run `python3 labs/03-physical-floorplan/run.py` and open the congestion maps in `results.png`.
  2. In `evaluate_layout`, find the per-mode HPWL values and pin-escape densities. Both are authored. Change the escape density and see how much of each mode's outcome it controls.
  3. The "DRC violations" count is the number of grid bins above 85 percent of a nominal capacity. List what a real design-rule check would add.

### Lab 04: Hardware–Software Co-Design
* **Directory:** `labs/04-hw-sw-codesign/`
* **Kernel:** an XR feature-point filter under a 50,000-cycle target and a 15,000 gate-equivalent ceiling.
* **Exercise:**
  1. Run `python3 labs/04-hw-sw-codesign/run.py`. If a RISC-V cross-compiler is installed, the script compiles the kernels and counts spills with `objdump`; compare that count with the spill cycles the script reports.
  2. Every cycle count and area figure in `evaluate_codesign` is a fixture. Write down the measurements you would need, and from which tools, to test the claim that the combined instruction and compiler change meets both budgets.

---

## 4. A Four-Week Reading Group Outline

* **Week 1:** The moonshot and the pressures chapters, with Lab 01.
* **Week 2:** The life cycle, representation, and methods chapters, with Lab 02.
* **Week 3:** The harness, verification, and transfer chapters, with Lab 03.
* **Week 4:** The evaluation, ownership, and ecosystem chapters, with Lab 04.

Each week, ask the same question of the lab that the book asks of any study. What did the tools return, what was supplied by hand, and what decision, if any, could the result support?
