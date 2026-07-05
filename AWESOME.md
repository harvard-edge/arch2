# Awesome Architecture 2.0 [![Awesome](https://awesome.re/badge.svg)](https://awesome.re)

A curated list of awesome tools, simulators, proxies, and agentic workflows that enable **Architecture 2.0**—the shift toward fully automated, AI-driven hardware design loops.

This is the living catalog accompanying the book [*Architecture 2.0: Designing the Loops that Design the Chips*](https://arch2.mlsysbook.ai).

## 🚀 How to Contribute
If you have built an open-source tool, surrogate model, or agentic loop, **we want it here!**
Please use our [Submit a Tool Form](https://github.com/harvard-edge/architecture20/issues/new/choose) to get your tool added to the catalog. We ask that you describe your tool using the Architecture 2.0 framework (What is the Action Space? What is the Feedback?).

---

## Contents
- [Simulation & Execution Environments](#simulation--execution-environments)
- [Proxy Models & Surrogate Predictors](#proxy-models--surrogate-predictors)
- [Agentic Workflows & Generators](#agentic-workflows--generators)
- [Data Representations & Hardware Vocabularies](#data-representations--hardware-vocabularies)
- [Verification & Red-Teaming](#verification--red-teaming)
- [Benchmarks & Datasets](#benchmarks--datasets)
- [Physical Design & EDA](#physical-design--eda)

---

## Simulation & Execution Environments
*The "ground truth" verification gates that provide slow but highly accurate feedback.*

| Tool | Description |
| :--- | :--- |
| **[gem5](https://www.gem5.org/)** | Modular computer-system simulator for architecture feedback needing workload execution and reproducible state. |
| **[FireSim](https://fires.im/)** | FPGA-accelerated full-system simulation for when the loop needs stronger hardware/software feedback than a proxy can provide. |
| **[Chipyard](https://chipyard.readthedocs.io/)** | Integrated framework for generating and evaluating hardware systems, connecting generators, RTL, and simulation. |
| **[Verilator](https://www.veripool.org/verilator/)** | The fastest free Verilog HDL simulator, converting Verilog to C++/SystemC. |

## Proxy Models & Surrogate Predictors
*Fast, lightweight models that approximate the simulator to accelerate the AI agent's search.*

| Tool | Description |
| :--- | :--- |
| **[Apollo](https://github.com/harvard-edge/Apollo)** | An automated framework for fast, accurate, and transferable architecture design space exploration using surrogate models. |
| **[MAESTRO](https://github.com/maestro-project/maestro)** | Analytical cost model for DNN dataflows and tiling; a fast-feedback model for dataflow exploration. |
| **[Accelergy](https://github.com/Accelergy-Project/accelergy)** | Energy-estimation infrastructure for accelerators, providing an explicit energy feedback source. |
| **[Timeloop](https://github.com/NVlabs/timeloop)** | Mapping and modeling tool for tensor workloads on accelerator architectures. |

## Agentic Workflows & Generators
*Frameworks that wrap LLMs, Reinforcement Learning, or Bayesian Search into autonomous hardware design loops.*

| Tool | Description |
| :--- | :--- |
| **[ArchGym](https://github.com/srivatsankrishnan/oss-arch-gym)** | Open-source gym environment for evaluating machine learning algorithms in computer architecture exploration. |
| **[AutoChip](https://github.com/shailja-thakur/AutoChip)** | Conversational hardware design using LLMs to generate Verilog from natural language specifications. |
| **[ChipNeMo](https://arxiv.org/abs/2311.00176)** | Domain-adapted LLMs for chip design, demonstrating automated EDA script generation and bug analysis. |
| **[VeriGen](https://arxiv.org/abs/2308.00708)** | A large language model customized for generating functional Verilog code. |

## Data Representations & Hardware Vocabularies
*Tools that define the action space and state representation for AI agents.*

| Tool | Description |
| :--- | :--- |
| **[Chisel](https://www.chisel-lang.org/)** | A hardware construction language embedded in Scala that provides high-level primitives for RTL generation. |
| **[PyMTL3](https://github.com/pymtl/pymtl3)** | An open-source Python-based hardware generation and simulation framework. |
| **[FIRRTL](https://github.com/chipsalliance/firrtl)** | A flexible intermediate representation for RTL, serving as the bridge between high-level generators and EDA tools. |

## Verification & Red-Teaming
*Tools dedicated to aggressively testing and rejecting AI-generated claims.*

| Tool | Description |
| :--- | :--- |
| **[CocoTB](https://github.com/cocotb/cocotb)** | A coroutine-based cosimulation library for writing VHDL and Verilog testbenches in Python. |
| **[SymbiYosys](https://symbiyosys.readthedocs.io/en/latest/)** | Front-end for Yosys-based formal verification flows, allowing agents to assert mathematical proofs against their generated RTL. |

## Benchmarks & Datasets
*Standardized tasks for evaluating the performance of Architecture 2.0 loops.*

| Tool | Description |
| :--- | :--- |
| **[CVDP Benchmark](https://github.com/NVlabs/cvdp_benchmark)** | Comprehensive Verilog Design Problems for RTL design and verification. Crucial for loops involving HDL generation and test harnesses. |
| **[QuArch](https://quarch.ai/)** | Architecture question-answering and reasoning benchmark to test if a model can reason over architecture concepts. |
| **[VerilogEval](https://github.com/NVlabs/verilog-eval)** | Specification-to-RTL and Verilog code-generation benchmark with executable checks. |
| **[KernelBench](https://github.com/ScalingIntelligence/KernelBench)** | GPU-kernel generation benchmark with correctness and performance evaluation. |
| **[CircuitNet](https://github.com/circuitnet/CircuitNet)** | VLSI CAD dataset for machine-learning applications in EDA. |

## Physical Design & EDA
*Tools for physical-design feedback, timing/area/power evidence, and signoff-adjacent rejection.*

| Tool | Description |
| :--- | :--- |
| **[OpenROAD](https://theopenroadproject.org/)** | Open-source RTL-to-GDS flow for loops that need physical-design feedback and evidence. |
| **[ChiPBench](https://openreview.net/forum?id=gDkQ5iesrI)** | Benchmark focused on end-to-end physical-design impact for AI chip placement. |
