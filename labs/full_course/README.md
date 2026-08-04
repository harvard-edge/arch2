# Architecture 2.0: The Full Workshop (Labs 00-11)

Welcome to the definitive **Architecture 2.0** workshop! This directory contains 12 interactive Jupyter Notebooks that map directly to the 11 chapters of the book.

These labs will take you from abstract constraints down to physical, cryptographically verifiable logic gates, teaching you how to build the modern AI-Hardware co-design loop.

## Prerequisites
To run this course locally, you need the following open-source toolchain installed:
1. **Python 3.8+** (with `jupyter`, `pandas`, `matplotlib`, `requests`, `pyyaml`)
2. **Ollama** (with the `gemma3:1b` model pulled locally via `ollama pull gemma3:1b`)
3. **Yosys** (for standard cell physical logic synthesis)
4. **SCALE-Sim** (Optional but recommended, for cycle-accurate proxy simulation. If missing, the notebooks will gracefully degrade to a fast mathematical proxy).

## Workshop Structure
You **MUST** run these notebooks sequentially. They share a continuous state file (`.arch2_state.json`) that passes your constraints, LLM generated JSON configurations, and physical synthesis counts down the pipeline.

### Module 1: The Foundations
*   `Lab_00_Introduction.ipynb`: The Roadmap.
*   `Lab_01_The_Moonshot.ipynb`: Flagging IP Contamination.
*   `Lab_02_The_Design_Loop.ipynb`: Simulating the Scissors Gap.
*   `Lab_03_The_Lifecycle.ipynb`: Environment Diagnostics.

### Module 2: The Loop
*   `Lab_04_Representations.ipynb`: Formalizing YAML Loop Cards.
*   `Lab_05_Methods.ipynb`: LLM Generation (The Mirage).
*   `Lab_06_Environments.ipynb`: SCALE-Sim Proxy Verification.
*   `Lab_07_Feedback.ipynb`: Autonomous EDA Failure Vectors.
*   `Lab_08_Running_The_Loop.ipynb`: Yosys Logic Synthesis.

### Module 3: Polish and Delivery
*   `Lab_09_Patterns.ipynb`: Parameterized Verilog Templates.
*   `Lab_10_Evaluation.ipynb`: Pareto Frontier Plotting.
*   `Lab_11_Ownership.ipynb`: Cryptographic Sign-off and Hashing.

## Getting Started
Open a terminal in this directory and launch Jupyter Notebook:
```bash
jupyter notebook
```
Then, open `Lab_00_Introduction.ipynb` to begin your journey!
