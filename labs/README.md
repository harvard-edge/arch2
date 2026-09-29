# Architecture 2.0 Teaching Labs

Companion teaching labs for *Architecture 2.0: Principles of AI-Native System and Chip Design*.

**Read this first.** These labs are exercises for reasoning about design loops. They are not measurements, and no number they print should be cited as evidence about a real design. Several outcomes are set by the lab author in the scripts rather than produced by a search or a tool, and the sections below say which ones.

For a chapter-by-chapter reading map and suggested exercises, see [TUTORIAL_GUIDE.md](TUTORIAL_GUIDE.md).

---

## 1. What Each Lab Compares

Each lab walks through one design problem three ways, using the same workload and constraints:

| Mode label in the scripts | What the script does | Where it sits in the book's terms |
| :--- | :--- | :--- |
| `assisted` | Evaluates one fixed candidate written into the script, with no feedback loop. | Point assistance (Layer 1). |
| `driven` | Sweeps parameters inside a fixed structure, such as array geometry or synthesis settings. | Closed-loop optimization inside a frozen container (Layer 2). |
| `native` | Applies a change that crosses an abstraction boundary, such as a dataflow switch or an arithmetic refactoring. | Illustrates a move an AI-native design system would need to make (Layer 3). The lab scripts the move; no system discovers it. |

The mode names are historical identifiers in the code and the result files. No language model runs inside `run.py`. The "drafted by an LLM" candidates are fixed inputs chosen by the lab author.

The book defines the three layers once, in the moonshot chapter; the table above only maps the lab modes onto them.

---

## 2. What Is Computed and What Is Authored

| Lab | Computed by a tool or model in the script | Set by the lab author (illustrative fixtures) |
| :--- | :--- | :--- |
| **01: Systolic array sweep** | Cycle counts and DRAM traffic for each candidate, from SCALE-Sim when it is installed and otherwise from an analytical roofline model, $T_{\text{effective}} = \max(T_{\text{comp}}, T_{\text{dram}})$. The committed `results.json` came from the analytical fallback. | The candidate list, the single `assisted` geometry, and the rule that triggers the switch to weight-stationary dataflow. |
| **02: RTL timing** | Cell counts, flip-flop counts, and cell area from Yosys synthesis onto SkyWater SKY130 cells. A 1,000-vector random simulation in Icarus Verilog comparing the naive and carry-save accumulators. | Every slack value. Slack is `clock period - (logic depth x per-stage delay + clock-to-Q + setup)`, using logic depths and per-stage delays written into `run.py`; no timing analyzer runs. The `driven` result reuses the naive RTL with an authored depth of 26. |
| **03: Floorplan congestion** | A simplified RUDY-style congestion grid from the authored macro boxes and pin positions. The "DRC violations" count is the number of grid bins above 85 percent of a nominal track capacity; it is not a design-rule check. | The three macro layouts, every HPWL value, and the pin-escape density assigned to each mode. |
| **04: HW/SW co-design** | Optionally, when a RISC-V cross-compiler is installed, the script compiles the C kernels, counts stack spills with `objdump`, and runs the result under QEMU. Those runs do not change the reported cycle counts. | Every cycle count (compute, address calculation, and spill cycles) and every gate-equivalent area figure. |

The four labs' `signoff_passed` fields report whether these illustrative values meet the lab's own thresholds. None of the labs runs physical signoff.

---

## 3. The Four Labs

```
labs/
├── 01-microarchitectural-sweep/   # Loop A: systolic array geometry, dataflow, and DRAM traffic
├── 02-rtl-timing/                 # Loop B: ripple-carry vs. carry-save accumulator
├── 03-physical-floorplan/         # Loop C: macro placement and a simplified congestion model
├── 04-hw-sw-codesign/             # Loop D: custom instructions, register spills, and area budget
├── notebooks/                     # Marimo and Jupyter versions of the exercises
├── demo.py                        # Interactive console walkthrough
├── run_all.py                     # Non-interactive runner used by CI
└── workbench_summary.json         # Collected outputs of the four labs
```

### [Loop A: Systolic Array Geometry and the Memory Wall](01-microarchitectural-sweep/)
* **Workload:** three XR matrix-multiplication layers from `workload/xr_gemm.csv` (projection $128 \times 128 \times 256$, attention tile $64 \times 192 \times 128$, head $32 \times 128 \times 192$).
* **Budget:** 1,024 processing elements and 4 words per cycle of off-chip bandwidth.
* **What to look at:** under output-stationary dataflow every geometry in the sweep is memory-bound, so reshaping the array cannot recover the lost cycles. Switching to weight-stationary dataflow under the model's 128 KiB buffer assumption cuts modeled DRAM traffic, and the cycle count follows. The exercise is about reading that bottleneck from the model's output, not about the specific ratio.

### [Loop B: RTL Timing and Arithmetic Representation](02-rtl-timing/)
* **Design:** a 32-bit accumulator at a 2.0 ns clock target, synthesized onto SKY130 cells.
* **What to look at:** the naive accumulator keeps a full carry chain inside the register feedback loop; the carry-save version moves carry propagation out of the loop at the cost of more cells and flip-flops (Yosys reports both). The slack figures are illustrative, as described above. The random-vector comparison is a simulation check, not a formal equivalence proof.

### [Loop C: Macro Placement and Routing Congestion](03-physical-floorplan/)
* **Design:** a $1000 \times 1000\ \mu\text{m}$ tile with a compute core and four SRAM macros.
* **What to look at:** a layout with low wirelength can still concentrate pin escapes in a few channels. Compare the congestion grids of the three authored layouts. The wirelength numbers are written into the script, and the congestion model is a teaching simplification, not a router.

### [Loop D: Hardware–Software Co-Design](04-hw-sw-codesign/)
* **Kernel:** an XR feature-point filter under a 50,000-cycle target and a 15,000 gate-equivalent area ceiling.
* **What to look at:** where cycles go when compute is fast but address arithmetic and register spills are not, and why a change to the instruction set and the compiler lowering together can address both. The cycle and area values are illustrative fixtures.

---

## 4. Running the Labs

### Docker

The container bundles Yosys, Icarus Verilog, a RISC-V cross-compiler, QEMU, and SCALE-Sim.

```bash
./arch2 docker build          # build the workbench image
./arch2 docker demo           # interactive walkthrough
./arch2 docker lab 01         # run one lab
./arch2 docker lab 02
./arch2 docker lab 03
./arch2 docker lab 04
```

See [`docker/README.md`](../docker/README.md) for details.

### Local Python

```bash
pip install scalesim rich numpy matplotlib pyyaml
python3 labs/01-microarchitectural-sweep/run.py
```

Without Yosys, Icarus Verilog, or SCALE-Sim on the path, the labs fall back to their analytical models, and the printed provenance says so.

### Notebooks

`labs/notebooks/workbench.py` (Marimo) and `labs/notebooks/workbench.ipynb` (Jupyter or Colab) expose the same exercises with adjustable parameters:

```bash
pip install marimo scalesim rich
marimo edit labs/notebooks/workbench.py
```

---

## 5. Tests

The lab tests check that the scripts run and that their outputs keep the documented structure. They do not validate the illustrative values.

```bash
pytest tests -q
./arch2 check precommit
```
