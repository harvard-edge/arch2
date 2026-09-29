# Loop B: RTL Timing and Arithmetic Representation

A teaching lab, not a measurement. See [../README.md](../README.md#2-what-is-computed-and-what-is-authored) for what the labs compute and what is authored.

## 1. The Question

A 32-bit accumulator that adds its input to its own register output in one cycle keeps the whole carry chain inside the feedback loop. Can synthesis settings fix that, or does the arithmetic representation have to change?

## 2. Design and Constraints

* **Designs:** `rtl/pe_accumulator_naive.v` (two's-complement accumulator) and `rtl/pe_accumulator_carry_save.v` (redundant sum and carry registers).
* **Target:** a 2.0 ns clock period (500 MHz), synthesized onto SkyWater SKY130 `sky130_fd_sc_hd` cells (`tech/`).

## 3. What the Script Does

* **Yosys synthesis (tool output).** When Yosys is installed, the script synthesizes each design and reports cell count, flip-flop count, and cell area from Yosys's `stat` output. The carry-save design uses more cells and roughly twice the flip-flops.
* **Random-vector comparison (tool output).** When Icarus Verilog is installed, `rtl/tb_pe_accumulator.v` drives both designs with 1,000 random inputs and compares their outputs. Agreement on those vectors is a simulation check. It is not a formal equivalence proof.
* **Slack (illustrative).** Every slack value is computed in `run.py` as `clock period - (logic depth x per-stage delay + clock-to-Q + setup)` from logic depths and per-stage delays written into the script. No static timing analyzer runs. The `driven` mode reuses the naive RTL and assigns it an authored logic depth of 26 to stand in for a synthesis-settings sweep.

| Mode | Design | Where its numbers come from |
| :--- | :--- | :--- |
| `assisted` | Naive accumulator | Cell counts from Yosys; slack illustrative. |
| `driven` | Naive accumulator, authored "sweep" depth | Cell counts from Yosys; slack illustrative. |
| `native` | Carry-save accumulator | Cell counts from Yosys; slack illustrative; 1,000-vector comparison from Icarus Verilog. |

## 4. Things to Try

* Run Yosys yourself: `yosys -p "read_verilog rtl/pe_accumulator_naive.v; synth -top pe_accumulator_naive; stat; ltp -noff"`.
* Replace the slack model with a static timing analysis of the synthesized netlist, and see whether the ordering of the three modes survives.
* Break the carry-save RTL and confirm the random-vector comparison catches it. Then think of a bug it would miss.

## 5. Running

```bash
./arch2 docker lab 02
python3 labs/02-rtl-timing/run.py
```

Outputs: `results.json` (cell counts, area, illustrative slack, and comparison status) and `results.png`.
