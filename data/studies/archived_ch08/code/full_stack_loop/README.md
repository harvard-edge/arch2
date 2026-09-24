# Architecture 2.0: Full Stack Exploration Loop

This directory contains a complete, executable demonstration of the closed-loop optimization workflow described in Chapter 8.

Unlike traditional methodologies that rely entirely on high-level Python proxies (like ScaleSim) for architectural exploration, this pipeline demonstrates the **full vertical slice**:
1. **Workload Definition**: We define a specific Deep Learning workload (e.g., $16 \times 16 \times 16$ GEMM).
2. **Generative RTL**: We use parameterized Verilog (`systolic_array.v`) to generate unique structural candidates based on the search space parameters ($R \times C$).
3. **Physical Synthesis Evaluation**: We feed every candidate array directly into the **Yosys** logic synthesizer. Yosys maps the RTL down to technology-independent gate primitives (NAND, NOR, DFF) to provide a physically grounded **Gate Count** (Area) measurement.
4. **Functional Evaluation**: We analytically evaluate the systolic latency for the given shape to produce a **Cycle Count** (Delay).
5. **Feedback Loop**: `arch_loop.py` aggregates these physical and functional metrics, calculating the Area-Delay Product (ADP) and identifying the absolute optimal physical topology.

## Running the Pipeline
Simply execute:
```bash
python3 arch_loop.py
```
You will watch the script autonomously generate Verilog wrappers, invoke Yosys, extract logic synthesis statistics, and optimize the hardware array shape.
