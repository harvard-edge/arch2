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
- [Agentic Workflows & Search Methods](#agentic-workflows--search-methods)
- [Data Representations & Hardware Vocabularies](#data-representations--hardware-vocabularies)
- [Verification & Red-Teaming](#verification--red-teaming)

---

## Simulation & Execution Environments
*The "ground truth" verification gates that provide slow but highly accurate feedback.*

* **[gem5](https://www.gem5.org/)** - A modular platform for computer-system architecture research, encompassing system-level architecture as well as processor microarchitecture.
* **[FireSim](https://fires.im/)** - An open-source cycle-exact FPGA-accelerated scale-out computer system simulation platform.
* **[Verilator](https://www.veripool.org/verilator/)** - The fastest free Verilog HDL simulator, converting Verilog to C++/SystemC.

## Proxy Models & Surrogate Predictors
*Fast, lightweight models that approximate the simulator to accelerate the AI agent's search.*

* **[Apollo](https://github.com/harvard-edge/Apollo)** - An automated framework for fast, accurate, and transferable architecture design space exploration using surrogate models (Harvard).
* **[ArchGym](https://github.com/harvard-edge/ArchGym)** - An open-source gym environment for evaluating machine learning algorithms in computer architecture exploration (Harvard).
* **[MicroGrad (Arch)](https://github.com/karpathy/micrograd)** - (Placeholder for ML-based analytical models for power/area/timing).

## Agentic Workflows & Search Methods
*Frameworks that wrap LLMs, Reinforcement Learning, or Bayesian Search into autonomous hardware design loops.*

* **[AutoChip](https://github.com/shailja-thakur/AutoChip)** - Conversational hardware design using LLMs to generate Verilog from natural language specifications.
* **[ChipNeMo](https://arxiv.org/abs/2311.00176)** - Domain-adapted LLMs for chip design, trained by NVIDIA, demonstrating automated EDA script generation and bug analysis.
* **[VeriGen](https://arxiv.org/abs/2308.00708)** - A large language model customized for generating functional Verilog code.

## Data Representations & Hardware Vocabularies
*Tools that define the action space and state representation for AI agents.*

* **[Chisel](https://www.chisel-lang.org/)** - A hardware construction language embedded in Scala that provides high-level primitives for RTL generation.
* **[PyMTL3](https://github.com/pymtl/pymtl3)** - An open-source Python-based hardware generation and simulation framework.
* **[FIRRTL](https://github.com/chipsalliance/firrtl)** - A flexible intermediate representation for RTL, serving as the bridge between high-level generators and EDA tools.

## Verification & Red-Teaming
*Tools dedicated to aggressively testing and rejecting AI-generated claims.*

* **[CocoTB](https://github.com/cocotb/cocotb)** - A coroutine based cosimulation library for writing VHDL and Verilog testbenches in Python. Ideal for connecting LLM test-generators to simulators.
* **[SymbiYosys](https://symbiyosys.readthedocs.io/en/latest/)** - Front-end for Yosys-based formal verification flows, allowing agents to assert mathematical proofs against their generated RTL.
