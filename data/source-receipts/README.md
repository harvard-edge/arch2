# Data Source Receipts & Empirical Provenance Guide

This directory contains the canonical data receipts, primary source transcriptions, and reproduction scripts behind all quantitative figures, tables, and empirical anchors across *Architecture 2.0*.

Every quantitative assertion in the book is backed by an inspectable CSV receipt in this directory, ensuring full reproducibility, transparent provenance, and clear separation between empirical observations and constructed models.

---

## 1. Directory Structure

```
data/source-receipts/
├── README.md                                # This provenance guide and methodology record
├── regenerate.py                            # Batch regeneration driver for upstream derived receipts
├── sources/                                 # Raw upstream primary datasets
│   ├── epoch-benchmarks.csv                 # Benchmark tracking from Epoch AI
│   ├── epoch-ml-hardware.csv                # Hardware scaling dataset from Epoch AI
│   ├── epoch-notable-models.csv             # Notable AI model compute from Epoch AI
│   ├── metr-time-horizon.yaml               # Task horizon evaluations from METR
│   ├── reuther-laics-2025.csv               # 2025 MIT Lincoln Lab AI Accelerator Survey
│   └── reuther-laics-editions/              # Historical annual editions (2019–2025)
├── chapter1-github-software-hardware-divide.csv  # The Stack v2 & OpenRTLSet code volume & funnel
├── chapter2-ai-accelerator-scaling-frontier.csv  # 14-year AI accelerator scaling (2012–2026)
├── chapter7-wilson-verification-scissors-gap.csv # 22-year Wilson / Siemens EDA verification survey
├── chapter9-mlperf-software-dividend.csv         # MLCommons MLPerf software vs. hardware scaling
├── plot_github_divide.py                    # Script generating fig-ch01-github-hardware-divide
├── plot_ai_accelerator_scaling.py           # Script generating fig-ch02-accelerator-scaling-frontier
├── plot_wilson_scissors.py                  # Script generating fig-ch07-wilson-verification-scissors
├── plot_mlperf_dividend.py                  # Script generating fig-ch09-mlperf-software-dividend
└── [other chapterN-*.csv receipts]          # Additional chapter-specific empirical receipts
```

---

## 2. Core Provenance Records & Methodologies

### 2.1 Chapter 1: The GitHub Software vs. Hardware Ecosystem Divide
* **Receipt:** `chapter1-github-software-hardware-divide.csv`
* **Plotting Script:** `plot_github_divide.py`
* **Generated Asset:** `book/contents/chapters/01-moonshot/images/fig-ch01-github-hardware-divide.{svg,pdf,png}`
* **Primary Sources:**
  1. *The Stack v2* (Lozhkov et al., 2024 / Software Heritage): Deduplicated public source code volume across 600+ languages. Extracted total volume (GB) and file counts for top software languages (JavaScript: 1,115 GB, 108.9M files; Java: 548 GB; C++: 354 GB; Python: 233 GB; C: 202 GB) versus all hardware HDLs combined (VHDL: 2.1 GB; SystemVerilog: 0.8 GB; Verilog: 0.7 GB; Chisel: 0.1 GB; Bluespec: 0.06 GB; total hardware $<3.8\text{ GB}$, $<0.2\%$ of public code).
  2. *OpenRTLSet* (Wang et al., IEEE ICLAD 2025): Mining pipeline attrition starting from 189,000 candidate repositories down to 12,000 synthesizable repos and 1,000 clean HLS repos.
  3. *VerilogEval* (Liu et al., 2023), *RTLLM* (Lu et al., 2024), and *Efabless Open MPW / HighTide* (2025): Hardware signoff funnel calibration measuring stage-by-stage attrition from raw public HDL (100%) through AST parsing (72.4%), open EDA elaboration in Icarus/Verilator (38.1%), logic synthesis in Yosys (18.0%), automated CI testbenches (7.2%), and clean tapeout signoff with DRC/LVS in OpenROAD (0.85%).
* **Methodology & Caveats:** Software language sizes reflect deduplicated content volume. The hardware quality funnel indexes relative pass rates across representative open-source benchmark evaluations.

---

### 2.2 Chapter 2: The 14-Year AI Accelerator Scaling Frontier (2012–2026)
* **Receipt:** `chapter2-ai-accelerator-scaling-frontier.csv`
* **Plotting Script:** `plot_ai_accelerator_scaling.py`
* **Generated Asset:** `book/contents/chapters/02-pressures/images/fig-ch02-accelerator-scaling-frontier.{svg,pdf,png}`
* **Primary Sources:**
  1. *NVIDIA Architectures:* Kepler K20X (GK110 Whitepaper 2012), Pascal P100 (Foley & Danskin, IEEE Micro 2017), Volta V100 (Choquette et al., IEEE Micro 2018), Ampere A100 (Choquette et al., IEEE Micro 2021), Hopper H100 (Choquette, IEEE Micro 2023), Blackwell B200 (NVIDIA Blackwell Architecture Whitepaper 2024, Hot Chips 36).
  2. *Google TPUs:* TPU v1 (Jouppi et al., ISCA 2017), TPU v2/v3 (Jouppi et al., CACM 2020), TPU v4 (Jouppi et al., ISCA 2023), TPU v5e/v5p (Google Cloud Architecture Guides 2023, Hot Chips 36), TPU v6e Trillium (Hot Chips 36, 2024).
  3. *AMD Instinct:* MI100 (2020), MI250X (Hot Chips 34, 2022), MI300X (Hot Chips 36, 2024).
  4. *Wafer-Scale & On-Chip SRAM:* Cerebras WSE-1/2/3 (Lie, Hot Chips 31/33/36, ISSCC 2020/2022/2024); Groq TSP / LPU v1 (Abts et al., ISCA 2020).
* **Computed Metrics:**
  - $\text{Arithmetic Ratio (Bytes/FLOP)} = \frac{\text{Memory Bandwidth (GB/s)}}{\text{Peak Compute (TFLOPS FP16/BF16/FP8/FP4)}}$
  - $\text{Operational Intensity (FLOPs/Byte)} = \frac{\text{Peak Compute}}{\text{Memory Bandwidth}} = \frac{1}{\text{Arithmetic Ratio}}$
* **Key Historical Findings:**
  - Monolithic die size hit the lithographic reticle limit ($\approx 858\text{ mm}^2$) between 2017 and 2022 (V100: $815\text{ mm}^2$, A100: $826\text{ mm}^2$, H100: $814\text{ mm}^2$), forcing the transition to 2.5D/3D chiplet integration (B200 dual-die: $1{,}628\text{ mm}^2$, MI300X: $1{,}017\text{ mm}^2$).
  - The arithmetic ratio for HBM-based GPUs/TPUs collapsed from $0.064\text{ Bytes/FLOP}$ (15.7 FLOPs/Byte on K20X) to $0.003\text{ Bytes/FLOP}$ ($>300\text{ FLOPs/Byte}$ on H100/B200 and $560\text{ FLOPs/Byte}$ on TPU v6e), creating the Operational Intensity Wall.
  - Architectures with massive on-chip SRAM (Groq TSP at $0.43\text{ Bytes/FLOP}$, Cerebras WSE at $0.17\text{--}0.90\text{ Bytes/FLOP}$) sustain higher byte-to-FLOP ratios by trading total parameter capacity for bandwidth.

---

### 2.3 Chapter 7: The 22-Year Functional Verification Scissors Gap (2002–2024)
* **Receipt:** `chapter7-wilson-verification-scissors-gap.csv`
* **Plotting Script:** `plot_wilson_scissors.py`
* **Generated Asset:** `book/contents/chapters/07-feedback/images/fig-ch07-wilson-verification-scissors.{svg,pdf,png}`
* **Primary Author & Institution:** Harry Foster (Chief Scientist, Siemens EDA / Mentor Graphics).
* **Primary Studies:**
  - Collett International Research (2002, 2004 studies).
  - Wilson Research Group / Mentor Graphics / Siemens EDA Biennial IC/ASIC Functional Verification Studies (2007, 2010, 2012, 2014 [DAC 2015], 2016 [DVCon 2017], 2018 [IEEE MTV], 2020, 2022, 2024 [Siemens Whitepaper WP-86424-D3]).
* **Key Empirical Metrics Tracked:**
  - *Project Schedule Share:* Average percentage of total IC/ASIC design project time spent in verification ($46\%$ in 2002 rising to $58\%$ in 2024; median consistently $50\text{--}60\%$).
  - *Staffing Ratio:* Ratio of peak verification engineers to design engineers ($0.62:1$ in 2007 expanding to $1.16:1$ in 2024 across the industry; reaching $3:1\text{--}5:1$ on complex heterogeneous SoCs).
  - *First-Pass Silicon Success Rate:* Percentage of projects achieving production silicon on spin 1 ($39\%$ in 2002 declining monotonically to an all-time low of $14\%$ in 2024; $86\%$ require respins).
  - *Root Causes of Respins (2024 Data):* Core logic/functional flaws ($48\%$), analog/mixed-signal integration ($43\%$ up from $24\%$ in 2012), clocking & CDC ($29\%$), timing closure ($23\%$), and firmware/HW-SW interactions ($21\%$).

---

### 2.4 Chapter 9: The Fixed-Silicon Software Dividend vs. Generational Hardware Steps
* **Receipt:** `chapter9-mlperf-software-dividend.csv`
* **Plotting Script:** `plot_mlperf_dividend.py`
* **Generated Asset:** `book/contents/chapters/09-patterns/images/fig-ch09-mlperf-software-dividend.{svg,pdf,png}`
* **Primary Source:** MLCommons MLPerf Training (v0.5–v4.1) and Inference (v0.5–v5.0) official peer-reviewed benchmark results (2018–2026).
* **Key Historical Comparisons:**
  - *Fixed-Hardware Software Dividend (Panel A):*
    - NVIDIA V100 (DGX-1, 8x V100, ResNet-50): $134.6\text{ min}$ in v0.5 (Dec 2018) $\to 58.0\text{ min}$ in v0.6 ($2.32\times$) $\to 35.2\text{ min}$ in v0.7 ($3.82\times$ speedup on identical physical silicon via DALI NVJPEG decode, NCCL ring optimizations, and dual-BNNorm residual fusion).
    - NVIDIA A100 (DGX A100, 8x A100, BERT-Large): $391.8\text{ min}$ in v0.7 (Jul 2020) $\to 169.2\text{ min}$ in v1.0 ($2.32\times$) $\to 145.4\text{ min}$ in v2.0 ($2.69\times$ in-place speedup via Fused MHA, Distributed LAMB, and full-iteration CUDA Graph capture in NCCL).
    - Google TPU v4 (4096-chip cluster, ResNet-50): $0.287\text{ min}$ in v1.0 $\to 0.191\text{ min}$ in v2.0 ($1.50\times$ speedup via XLA compiler fusions and dynamic optical circuit switching).
    - NVIDIA H100 (512x H100 cluster, GPT-3 175B): $71.4\text{ min}$ in v3.0 (Jun 2023) $\to 56.2\text{ min}$ in v4.0 ($1.27\times$) $\to 1.30\times$ per-GPU in v4.1 via FlashAttention-2, asynchronous TMA GEMMs, and DP-AllGather overlap.
    - NVIDIA H100 (8x H100, Llama 2 70B LoRA): $24.6\text{ min}$ in v4.0 (Jun 2024) $\to 19.5\text{ min}$ in v4.1 (Nov 2024, $+26\%$ speedup in 5 months).
  - *Generational Step-Functions vs. Software Expansion (Panel B):*
    - Traces initial debut throughput against mature software peak on BERT-Large across four GPU generations: Volta V100 ($1.0\times$), Ampere A100 ($1.23\times$ debut $\to 3.3\times$ mature), Hopper H100 ($7.8\times$ debut $\to 9.1\times$ mature), and Blackwell B200 ($19.0\times$ debut).

---

## 3. Reproduction Instructions

To regenerate all four canonical figures and verify their vector (SVG/PDF) and visual inspection (PNG) twin assets:

```bash
# Ensure dependencies are available (matplotlib, numpy, python >= 3.10)
python3 data/source-receipts/plot_github_divide.py
python3 data/source-receipts/plot_ai_accelerator_scaling.py
python3 data/source-receipts/plot_wilson_scissors.py
python3 data/source-receipts/plot_mlperf_dividend.py
```

To run the full automated validation suite across all prose, reference anchors, bibliography entries, and permissions records:

```bash
PYTHONPATH=. uv run --with typer --with rich --with pybtex --with jsonschema --with pyyaml python3 -m cli.arch2 validate all
```

---

## 4. Methodological Disclosures & Data Integrity

1. **Primary vs. Constructed Data:** Where figures depict conceptual causal relationships or constructed parametric models (e.g., LogCA break-even in `@fig-logca-breakeven`, rejection bounds in `@fig-rejection-bound-ceiling`, or SVA formal unroll scaling in `@fig-sva-bmc-coverage-depth`), the caption and accompanying prose explicitly disclose that values are constructed for inspectability.
2. **Provenance Traceability:** All empirical data receipts record exact primary citations, author names, conference/whitepaper publication venues, dates, and extraction parameters.
3. **No Unanchored Claims:** Every quantitative number cited in chapter body prose is directly grounded in these versioned CSV records.
