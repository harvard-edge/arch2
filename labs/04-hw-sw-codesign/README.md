# Loop D: Hardware–Software Co-Design

A teaching lab, not a measurement. See [../README.md](../README.md#2-what-is-computed-and-what-is-authored) for what the labs compute and what is authored.

## 1. The Question

A custom arithmetic instruction speeds up the multiply, but the kernel still spends its time computing addresses and spilling registers. When does a change have to span the instruction set and the compiler together?

## 2. Kernel and Budgets

* **Kernel:** an XR feature-point filter over a $256 \times 256$ frame (`workload/`).
* **Budgets:** at most 50,000 cycles and at most 15,000 gate equivalents of added datapath area (`contract.yaml`).

## 3. What the Script Does

Every cycle count (compute, address calculation, and register spills) and every gate-equivalent area figure is written into `evaluate_codesign` in `run.py`. They are illustrative fixtures chosen to show the mechanism. The `signoff_passed` field only checks those fixtures against the two budgets.

When a RISC-V cross-compiler is installed, the script also compiles the C kernels, counts stack spills in the disassembly with `objdump`, and, if QEMU is present, runs the compiled program. Those tool runs are real, but they do not feed the reported cycle counts or area.

| Mode | Change | Numbers |
| :--- | :--- | :--- |
| `assisted` | One scalar custom instruction | Authored cycles and area. |
| `driven` | Compiler unrolling on unchanged hardware | Authored cycles and area. |
| `native` | Packed SIMD instruction with post-increment addressing, plus matching compiler lowering | Authored cycles and area. |

## 4. Things to Try

* Compare the spill count `objdump` reports with the spill cycles the script prints.
* Write down which measurements, from which tools (an instruction-set simulator or RTL simulation for cycles, synthesis for area), would be needed to test the claim that the `native` change meets both budgets.

## 5. Running

```bash
./arch2 docker lab 04
python3 labs/04-hw-sw-codesign/run.py
```

Outputs: `results.json` (authored cycle and area breakdown, plus compiler and QEMU status) and `results.png`.
