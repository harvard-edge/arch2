# Loop A: Systolic Array Geometry and the Memory Wall

A teaching lab, not a measurement. See [../README.md](../README.md#2-what-is-computed-and-what-is-authored) for what the labs compute and what is authored.

## 1. The Question

A fixed budget of 1,024 processing elements has to run three XR matrix-multiplication layers through a narrow off-chip interface. Does reshaping the array help, or is the limit somewhere the array's shape cannot reach?

## 2. Workload and Constraints

* **Workload:** `workload/xr_gemm.csv`, three layers (projection $128 \times 128 \times 256$, attention tile $64 \times 192 \times 128$, head $32 \times 128 \times 192$).
* **Budget:** 1,024 processing elements, a 128 KiB on-chip buffer, and 4 words per cycle of off-chip bandwidth (`contract.yaml`).

## 3. What the Script Does

The evaluator (`evaluate_systolic_array`) computes compute cycles, DRAM traffic, and effective cycles, $T_{\text{effective}} = \max(T_{\text{comp}}, T_{\text{dram}})$, for each candidate. It uses SCALE-Sim when the package is installed and an analytical roofline model otherwise. The committed `results.json` came from the analytical model.

| Mode | Candidates | Chosen by |
| :--- | :--- | :--- |
| `assisted` | One $16 \times 64$ output-stationary array | Written into the script. No model runs. |
| `driven` | Five aspect ratios from $8 \times 128$ to $128 \times 8$, output-stationary | A sweep over a fixed list. |
| `native` | The same five aspect ratios under weight-stationary dataflow | A scripted rule: if the output-stationary baseline is memory-bound, switch dataflow. |

In the committed run, every output-stationary candidate is memory-bound on every layer, so no geometry in the sweep removes the bottleneck. The weight-stationary branch assumes the 128 KiB buffer holds each layer's weights, which cuts modeled DRAM reads. The resulting cycle counts are outputs of that model under that assumption, not measurements of hardware.

## 4. Things to Try

* Change `interface_bandwidth_words_per_cycle` in `contract.yaml` and watch which candidates stay memory-bound.
* Check whether the 128 KiB weight-buffer assumption actually holds for each layer's weight matrix.
* Install SCALE-Sim and compare its cycle counts with the analytical model's.

## 5. Running

```bash
./arch2 docker lab 01                              # inside the workbench container
python3 labs/01-microarchitectural-sweep/run.py    # on the host
```

Outputs: `results.json` (per-candidate cycles and traffic) and `results.png`.
