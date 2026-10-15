# Attribution, Provenance, and Intellectual Credit (`nanochip`)

This document states the provenance, licensing, and intellectual division of labor between **Moonshot AI's `nano-kpu` artifact** and the ***Architecture 2.0* (`nanochip`) pedagogical curriculum and governance study**.

---

## 1. Primary Credit: Moonshot AI and Kimi K3 (`MoonshotAI/nano-kpu`)

The silicon design, golden reference model, fixed-point C-model twin, and verification/synthesis harness located under [`nanochip/kpu/`](kpu/) originate from the open-source repository released by **Moonshot AI**:

- **Upstream Repository:** [`https://github.com/MoonshotAI/nano-kpu`](https://github.com/MoonshotAI/nano-kpu)
- **Authors / Creators:** Moonshot AI and the **Kimi K3** autonomous model
- **License:** Apache License 2.0 (preserved verbatim in [`nanochip/kpu/LICENSE`](kpu/LICENSE))
- **Integrity Guarantee:** Every frozen upstream specification, reference, and harness file listed in [`nanochip/kpu/harness/manifest.json`](kpu/harness/manifest.json) (35 files) is preserved unmodified and verified via SHA-256 checksums by `python3 nanochip/kpu/harness/check_integrity.py`.

### What Moonshot AI and Kimi K3 Built

In a landmark 48-hour autonomous engineering run, **Kimi K3** designed and implemented a complete, synthesizable hybrid-attention Mixture-of-Experts (MoE) inference processor (`msh_chip_top`) from scratch, together with Moonshot AI's rigorous evaluation harness:

1. **Full-Chip Synthesizable RTL (`nanochip/kpu/rtl/`):**
   - Ten hand-structured Verilog-2005 modules (~10,000 lines of clean, human-readable RTL) implementing **Kimi Delta Attention (KDA)** linear attention with per-channel decay and kernel-4 causal depthwise convolutions, **NoPE Multi-Head Latent Attention (MLA)** with compressed KV latent ($d_c = 128$), **sigmoid-routed MoE** (8 SwiGLU experts, top-2 routed + 1 shared expert), and **attention-residual mixing**.
   - Hardware microarchitecture featuring an elastic 256-deep credit-tracked DRAM fetch engine (`msh_fetch.v`), a 16-KB token-independent LM-head shadow buffer (`hq`), a dual-parity-banked INT4 fused-dequant GEMV engine (`msh_gemv.v`) applying zero-point folding $\sum_k (q_k - z) x_k = \sum_k q_k x_k - z \sum_k x_k$, a byte-serial embedding dequantizer (`msh_deq.v`), and an 80-bit exact sum-of-squares RMSNorm/L2Norm vector engine (`msh_vec.v`).
   - Synthesizes to **1.46M logic cells** (`2.707 mm^2` mapped logic in Nangate45 plus `0.903 mm^2` across 39 `msh_sram`/`msh_rom` macro instances = `3.610 mm^2` total area within a `4.0 mm^2` budget), closing pre-layout static timing at **`6.166 ns`** (`162.2 MHz` estimated $f_{\max}$ against a `10.0 ns` / `100 MHz` target) and accelerating decode throughput from **`4.0 tok/s` to `8,720.6 tok/s`** (`11,467.1 cycles/token`, a **2,180x** speedup over baseline).

2. **Multi-Fidelity Reference and Self-Model Stack (`nanochip/kpu/reference/` and `nanochip/kpu/rtl/selfmodel/`):**
   - Normative `float32` mathematical specification (`reference/model.py`), splitmix64 deterministic weight/token generator (`reference/gen_weights.py`), and platform-independent fingerprint test (`reference/selftest.py`).
   - Bit-exact integer/fixed-point Python golden model (`rtl/selfmodel/fxmodel.py` and `fxluts.py`) that mirrors every RTL register, Q-format shift (`Q4.26`, `Q4.27`, `Q8.37`), and piece-wise linear LUT interpolation bit-for-bit.

3. **Adversarial Evaluation Harness (`nanochip/kpu/harness/`):**
   - Cryptographic manifest locking (`check_integrity.py`), static RTL cheat auditing (`audit.py`), Verilator C++ testbench with 16 B/cycle DRAM bandwidth limiting, deterministic jitter, and back-pressure (`tb/tb_main.cpp`), random-reset state-poisoning (`+verilator+rand+reset+2`), $2\times$ DRAM latency elasticity sweeps (`24 -> 48` cycles), and two-pass Yosys/ABC Nangate45 synthesis (`synth_area.ys`, `synth_tech.ys`, `synth_netlist.ys`).

---

## 2. What *Architecture 2.0* (`nanochip`) Adds

While `MoonshotAI/nano-kpu` provides the extraordinary engineering artifact, most observers inspect `rtl/` and miss the deeper methodological lesson. ***Architecture 2.0: Principles of AI-Native System and Chip Design*** (by Vijay Janapa Reddi) contributes the theoretical framework, pedagogical curriculum, diagnostic reconstruction, and formal governance layer built around `nano-kpu`:

| Contribution Layer | Upstream `MoonshotAI/nano-kpu` (`nanochip/kpu/`) | *Architecture 2.0* Companion (`nanochip/labs/`, `nanochip/cards/`, `cli/`) |
| :--- | :--- | :--- |
| **Core Artifact** | Frozen 10-module Verilog chip (`msh_chip_top`), `fxmodel.py`, and `harness/evaluate.py` | Preserved 100% intact and SHA-256 verified via `check_integrity.py` |
| **Theoretical Framework** | Implicit engineering discipline inside `TASK_SPEC.md` and `evaluate.py` | Explicit mapping onto the **6-Stage AI-Native Design Life Cycle** (`1. Formulate -> 2. Explore -> 3. Implement -> 4. Evaluate -> 5. Interpret -> 6. Commit`) across Chapters 1–12 |
| **Failure & Return-Arrow Reconstruction** | Final passing commit state | Reconstructs the **intermediate failure modes** (reward-hacking budgets, impossible FP16 roofline claims, 1-bit shift/zero-point drift, 96K-gate parallel demux bloat, $2\times$ latency stall deadlocks) and routes each failure along the **Three Return Arrows** (`-> Implement`, `-> Explore`, `-> Formulate`) |
| **Physical Signoff & Proxy-Gap Audit** | Pre-layout Yosys/ABC synthesis with blackbox SRAM/ROM stubs | Formal audit of the **Proxy-to-Purpose Gap** (Chapter 7 & Chapter 10): statistical `5K_hvratio_1_1` wireload vs. routed metal RC parasitics, unbuffered `266.5 ns` vs. buffered `1.479 ns` fanout trees, blackbox macro timing arcs, and multi-PDK comparison (Nangate45 vs. SkyWater SKY130) |
| **Pedagogical Curriculum** | Benchmark specification (`docs/TASK_SPEC.md`) | **Six Progressive Hands-On Labs** (`01-formulate` through `06-commit`), each with runnable `--mode break` (unguarded failure injection) and `--mode verify` (harness enforcement) receipts |
| **Governance & Auditability** | `build/score.json` measurement report | **Design-Loop Card v2.0** (`nanochip/cards/nano-kpu-study-card.yaml`), binding claims, SHA-256 evidence packets, predeclared rejection gates, replay verification, and human vs. AI decision rights |

---

## 3. Open-Source EDA and PDK Ecosystem Credit

Both `MoonshotAI/nano-kpu` and the *Architecture 2.0* `nanochip` curriculum stand on the shoulders of the open-source Electronic Design Automation (EDA) and silicon foundations community:

- **Verilator** ([verilator.org](https://www.verilator.org), LGPL-3.0 / Artistic-2.0): Cycle-accurate Verilog/SystemVerilog compilation, static lint gating (`--lint-only -Wall`), and 2-state randomized reset verification (`+verilator+rand+reset+2`).
- **Yosys Open SYnthesis Suite** ([yosyshq.net/yosys](https://yosyshq.net/yosys/), ISC License, Claire Xenia Wolf et al.): RTL elaboration, memory macro discipline checks (`$mem_v2` vs. `msh_sram`/`msh_rom`), NAND2-equivalent (NE) cell accounting, and liberty technology mapping.
- **Berkeley ABC** ([github.com/berkeley-abc/abc](https://github.com/berkeley-abc/abc), MIT License, Alan Mishchenko et al.): AIG structural hashing (`strash`), sequential retiming (`dretime`), technology mapping (`map`), fanout buffering/sizing (`buffer;upsize;dnsize`), and topological static timing analysis (`stime,-c`).
- **The OpenROAD Project & Nangate45 Open Cell Library** ([theopenroadproject.org](https://theopenroadproject.org), BSD-3-Clause / Apache-2.0): Open-source 45nm educational standard-cell library (`NangateOpenCellLibrary_typical.lib`) used as the technology-anchored timing and area baseline.
- **Google & SkyWater Technology Foundry (`SKY130` PDK)** ([github.com/google/skywater-pdk](https://github.com/google/skywater-pdk), Apache-2.0): Open-source manufacturable 130nm process design kit (`sky130_fd_sc_hd__tt_025C_1v80.lib`) used in *Architecture 2.0* cross-technology sensitivity and signoff proxy analyses.

---

## 4. How to Cite

When referencing the `nano-kpu` hardware design, benchmark harness, or Kimi K3 autonomous chip design demonstration, please cite **Moonshot AI**:

```bibtex
@misc{moonshot2026nanokpu,
  author       = {{Moonshot AI}},
  title        = {{nano-kpu}: A Nano-Scale Hybrid-Attention {MoE} Inference Chip Designed by {Kimi K3}},
  year         = {2026},
  howpublished = {\url{https://github.com/MoonshotAI/nano-kpu}},
  note         = {Apache-2.0 License}
}
```

When referencing the **6-Stage AI-Native Design Life Cycle**, the **Three Return Arrows**, the **Design-Loop Card v2.0** governance specification, or the **`nanochip` 6-Lab Pedagogical Curriculum**, please cite ***Architecture 2.0***:

```bibtex
@book{reddi2026arch2,
  author    = {Vijay Janapa Reddi},
  title     = {Architecture 2.0: Principles of {AI}-Native System and Chip Design},
  series    = {Synthesis Lectures on Computer Architecture},
  publisher = {Springer Nature},
  year      = {2026},
  url       = {https://arch2.mlsysbook.ai}
}
```

---

## 5. Directory Ownership and License Summary

| Path | Origin | License | Modification Policy |
| :--- | :--- | :--- | :--- |
| `nanochip/kpu/*` | Moonshot AI (`MoonshotAI/nano-kpu`) | Apache-2.0 | **FROZEN** — 35 core files locked by SHA-256 in `harness/manifest.json`; verified by `check_integrity.py` |
| `nanochip/README.md`, `nanochip/CREDIT.md` | *Architecture 2.0* Companion | Apache-2.0 / CC-BY-4.0 | Pedagogical documentation and attribution |
| `nanochip/labs/01-formulate` .. `06-commit` | *Architecture 2.0* Companion | Apache-2.0 | Runnable 6-stage curriculum labs (`--mode break`, `--mode verify`, `--mode summary`) |
| `nanochip/cards/*` | *Architecture 2.0* Companion | Apache-2.0 | Design-Loop Card v2.0 (`nano-kpu-study-card.yaml`), replay verifier, and SHA-256 evidence packets |
