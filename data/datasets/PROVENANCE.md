# Provenance notes for the chapter wishlist datasets

`ch1_data.csv` through `ch12_data.csv` are the small per-chapter datasets behind
the `plot_ch*.png` figures. This file describes what each one is meant to hold.

> **Read this before citing anything below.** These twelve files carry no
> per-row provenance columns and no `#` provenance headers, so the descriptions
> here are the only record of where a value came from, and they are not
> independently checkable. Several entries below describe modeled or illustrative
> series rather than mined measurements, and they say so. Only `ch1_data.csv` has
> been audited (2026-09-09). The other eleven have not.

1. **Chapter 1 (Productivity Asymmetry):** `ch1_data.csv` holds Pass@1 for five
   public code models on software and hardware description tasks. **The specific
   benchmarks behind each value are not recorded in the file**, so the earlier
   attribution to SWE-Bench, HumanEval, VerilogEval and RTLLM cannot be verified
   and has been withdrawn. Two of the five models are closed, and their token
   counts are undisclosed estimates. See the file's own header.
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

Plotting is handled by `plot_all_wishlist.py` using `book.mplstyle`.

There is no generation script. This section previously named
`generate_all_wishlist.py`, which does not exist anywhere in the repository, so
these datasets cannot be regenerated or traced to a mining step. It also claimed
the pipeline guarantees "zero visual hallucination", which no plotting script can
guarantee and which the 2026-09-09 audit disproved for other figures in this
directory. Both claims are removed rather than restated.
