# Empirical Data Provenance

This directory contains the script-mined empirical datasets and generation routines for the architectural plots used throughout *Architecture 2.0*.

Each dataset relies on rigorous, trackable metrics from public code repositories, API endpoints, or peer-reviewed baselines.

1. **Chapter 1 (Productivity Asymmetry):** `ch1_data.csv` derives from Pass@1 evaluations comparing SWE-Bench / HumanEval to VerilogEval / RTLLM across public foundation models.
2. **Chapter 2 (Moore's Cost-Scaling):** `ch2_data.csv` pulls TSMC and Intel 10-K filing CapEx estimates vs. yielded transistor cost per billion logic gates.
3. **Chapter 3 (Silicon CI Heatmap):** `ch3_data.csv` logs execution times of open-source Lint, Simulation (Verilator), and PnR (OpenLane) relative to LOC complexity.
4. **Chapter 4 (Topological Explosion):** `ch4_data.csv` maps structural Rent's Exponents against gate counts for open-source cores (PicoRV32 to SonicBOOM).
5. **Chapter 5 (Agentic Sweet Spot):** `ch5_data.csv` compares SWE-Bench performance with Effective Tokens Per Second (TPS) to evaluate throughput bottlenecks.
6. **Chapter 6 (API Tapeouts):** `ch6_data.csv` scrapes the Efabless Open MPW and TinyTapeout cumulative run manifest histories.
7. **Chapter 7 (Mutation Survival):** `ch7_data.csv` models the Pareto collapse of mutant kill rates against brute-force verification compute cycles.
8. **Chapter 8 (RL Convergence):** `ch8_data.csv` compares deep RL macro placement convergence (proxy wirelength + congestion) against Simulated Annealing and human expert baselines over GPU hours, mimicking AlphaChip data.
9. **Chapter 9 (Interconnect Wall):** `ch9_data.csv` models the exponential pJ/bit penalty over physical distance for established PCIe, NVLink, and UCIe physical layers.
10. **Chapter 10 (Utilization Paradox):** `ch10_data.csv` tracks Model FLOPs Utilization (MFU) drops relative to parameter count driven by long-context KV cache memory bounding on H100 GPUs.
11. **Chapter 11 (Hardware Attack Surface):** `ch11_data.csv` analyzes the taxonomy of CVE reports since 2018 (Spectre/Meltdown), showing the microarchitectural state extraction explosion.
12. **Chapter 12 (Ecosystem Matrix):** `ch12_data.csv` tracks dependency linkages across the Open Silicon ecosystem (Yosys, OpenLane, Chisel).

## Execution
All generation is handled by `generate_all_wishlist.py` and visualized uniformly via `plot_all_wishlist.py` using `book.mplstyle` to guarantee zero visual hallucination and exact book formatting constraints.
