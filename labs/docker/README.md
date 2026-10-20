# Containerized Architecture 2.0 EDA Workbench

This directory houses the Docker configuration for the **Architecture 2.0 Grounded Workbench**, providing a fully reproducible, self-contained open-source Electronic Design Automation (EDA) and computer architecture simulation environment.

---

## Why Containerization?

Modern computer architecture research and automated agentic design workflows suffer from **toolchain drift**, brittle host dependencies, and non-reproducible software-hardware configurations.

To eliminate these barriers and prevent synthetic "fake" results, the workbench packages the exact open-source EDA toolchain inside an Ubuntu 24.04 LTS container:

| Tool / Package | Version | Purpose in Workbench | Grounded Micro-Loop |
| :--- | :--- | :--- | :--- |
| **Yosys** | 0.33+ | Open-source RTL synthesis, cell mapping, and gate-level netlist generation | Micro-Loop B (RTL Timing) |
| **Icarus Verilog (`iverilog` / `vvp`)** | 12.0+ | IEEE-1364 Verilog simulation and bit-exact functional equivalence verification | Micro-Loop B (RTL Timing) |
| **RISC-V GNU Toolchain (`gcc-riscv64`)** | 13.3+ | Bare-metal and Linux RISC-V cross-compilation with custom opcode assembly support | Micro-Loop D (HW/SW Co-Design) |
| **QEMU User Emulation (`qemu-user-static`)**| 8.2+ | User-space cycle and instruction execution emulation for RV64GC binaries | Micro-Loop D (HW/SW Co-Design) |
| **SCALE-Sim** | v3.0.0 | Cycle-accurate 2D systolic CNN/GEMM accelerator simulator with DRAM access tracing | Micro-Loop A (Microarchitecture) |
| **Python 3 Scientific Stack** | 3.12+ | NumPy, SciPy, Pandas, Matplotlib, PyYAML, Rich, and Click | All Loops |

---

## Quickstart: Running with Docker

You can use either the `./arch2` repository CLI or standard `docker compose` commands.

### 1. Build the Docker Image

```bash
# Using the Arch2 CLI
./arch2 docker build

# Or using Docker Compose
docker compose build
```

This compiles the `arch2-workbench:latest` image with all synthesis, simulation, and compilation binaries pre-configured.

### 2. Run the Full Interactive Demonstration

```bash
# Using the Arch2 CLI
./arch2 docker demo

# Or using Docker Compose
docker compose run --rm workbench python3 labs/demo.py
```

### 3. Run Individual Micro-Loops

Execute any specific micro-loop inside the container:

```bash
# Run Micro-Loop A (Systolic Array & Memory Wall)
./arch2 docker lab 01

# Run Micro-Loop B (RTL Synthesis & Carry-Save Retiming)
./arch2 docker lab 02

# Run Micro-Loop C (Physical Macro Placement & RUDY Routing)
./arch2 docker lab 03

# Run Micro-Loop D (Hardware-Software Co-Design & SIMD ISA)
./arch2 docker lab 04

# Run all micro-loops sequentially
./arch2 docker lab all
```

### 4. Interactive Container Shell

To inspect tool binaries, run custom synthesis scripts, or verify compiler outputs interactively:

```bash
# Open an interactive bash session inside the container
./arch2 docker run -- /bin/bash

# Inside the container:
root@arch2-workbench:/workspace# yosys -version
root@arch2-workbench:/workspace# iverilog -v
root@arch2-workbench:/workspace# riscv64-linux-gnu-gcc --version
root@arch2-workbench:/workspace# python3 -c "import scalesim; print('SCALE-Sim ready')"
```

---

## Volume Mounting & Workspace Isolation

The Docker environment mounts the host repository directory to `/workspace` inside the container (`-v $(pwd):/workspace`). Any generated reports (`results.json`), waveforms, or plots (`results.png`) are written directly to your local filesystem with zero data loss upon container exit.
