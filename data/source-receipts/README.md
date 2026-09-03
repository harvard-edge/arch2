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
├── mlperf_longitudinal_software_dividend.csv     # Extended longitudinal MLPerf software dividend dataset (2018-2026)
├── inference_kernel_fragmentation.csv            # Custom kernel proliferation across vLLM, TensorRT-LLM, SGLang, TGI
├── hardware_security_cve_mitigation_tax.csv      # Longitudinal hardware CVE mitigation tax ledger (2018-2026)
├── plot_github_divide.py                    # Script generating fig-ch01-github-hardware-divide
├── plot_ai_accelerator_scaling.py           # Script generating fig-ch02-accelerator-scaling-frontier
├── plot_wilson_scissors.py                  # Script generating fig-ch07-wilson-verification-scissors
├── plot_mlperf_dividend.py                  # Script generating fig-ch09-mlperf-software-dividend
├── plot_mlperf_software_dividend_extended.py # Extended plotter for longitudinal dividend & kernel fragmentation
├── plot_hardware_cve_performance_tax.py     # Script generating fig-hardware-cve-mitigation-tax
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

### 2.5 Track 3: The Software Porting Wall & Inference Custom Kernel Fragmentation (2023–2026)
* **Receipts:** `mlperf_longitudinal_software_dividend.csv` and `inference_kernel_fragmentation.csv`
* **Scraper & Miner:** `data/scrapers/mine_mlperf_software_dividend.py`
* **Plotting Script:** `plot_mlperf_software_dividend_extended.py`
* **Generated Assets:**
  - `data/source-receipts/mlperf_longitudinal_software_dividend.{svg,pdf,png}`
  - `data/source-receipts/inference_kernel_fragmentation.{svg,pdf,png}`
  - `data/source-receipts/mlperf_software_dividend_extended_master.{svg,pdf,png}`
* **Primary Sources:**
  1. *MLCommons Benchmarks (2018–2026):* Peer-reviewed results across Training (v0.5–v5.1) and Inference (v1.0–v6.0).
  2. *Inference Runtime Repositories:* `vLLM` (vllm-project/vllm), `TensorRT-LLM` (NVIDIA/TensorRT-LLM), `SGLang` (sgl-project/sglang), and `TGI` (huggingface/text-generation-inference).
* **Key Empirical Metrics Tracked:**
  - *The In-Place Software Dividend:* Measures sustained throughput maturation on frozen physical silicon over 12–36 months: V100 ($3.82\times$), A100 ($2.69\times$), TPU v4 ($1.50\times$), H100 Training ($1.48\times$), H100 Inference ($1.45\times$), TPU v6e ($1.42\times$), and MI300X ($1.32\times$).
  - *The Software Porting Wall:* Custom handwritten kernel LOC grew from $<5\text{K LOC}$ in early 2023 to $>340\text{K LOC}$ in 2026 (an $82\times$ explosion in 36 months), fragmenting across attention (FlashAttention-3, PagedAttention, MLA), quantization (FP8, FP4, Marlin), MoE routing dispatch, and custom hardware-specific collective communications.

---

### 2.6 Track 6: Open Silicon Democratization & The 3,000× Fabrication Cost Collapse (1981–2026)
* **Receipts:** `tinytapeout_democratization_census.csv` and `shuttle_cost_historical_collapse.csv`
* **Scraper & Aggregator:** `data/scrapers/scrape_tinytapeout_census.py`
* **Plotting Script:** `plot_tinytapeout_democratization.py`
* **Generated Assets:**
  - `data/source-receipts/fig-tinytapeout-democratization-census.{svg,pdf,png}`
  - `book/contents/chapters/01-moonshot/images/fig-ch01-tinytapeout-democratization-census.{svg,pdf,png}`
* **Primary Sources:**
  1. *Tiny Tapeout Manifests & API Archives (2022–2026):* Public manifests across 27 shuttle rounds (TT01 through TT-SKY-26c, TT-IHP-26b, TT-GF-26b) via `https://app.tinytapeout.com/api/shuttles/submission-stats` and GitHub submission repositories (`tinytapeout/tinytapeout-mpw7`, `tinytapeout-02` through `09`, `tinytapeout-ihp-*`, `tinytapeout-gf-*`).
  2. *Efabless Open MPW & Google Sponsored Shuttle Archives:* Open MPW-1 through Open MPW-8, Caravel user space specifications, and ChipIgnite commercial open-source shuttles.
  3. *Historical Semiconductor Fabrication Tariffs:* MOSIS Historical Service Rates (Cohen & Tyree 1982, Pina IEEE 2001), TSMC CyberShuttle catalogs (2000–2016), IBS Semiconductor Node Design Cost Reports, and Mead & Conway VLSI history (1980, 2012).
* **Key Empirical Metrics Tracked:**
  - *Democratization Wave:* Traces explosive submission growth from 152 designs in TT01 (Aug 2022) to over $4{,}780+$ designs across 27 shuttle rounds in 2026.
  - *Domain Specialization:* Tracks design domain evolution from early educational logic (74%) into domain-specific accelerators, custom CPUs & RISC-V cores ($5.0\%$), Neural Networks & Systolic AI accelerators ($4.8\%$), Audio/DSP synthesizers ($3.3\%$), Demoscene & VGA graphics ($5.7\%$), and High-Speed 250 GHz BiCMOS RF / Analog mixed-signal designs ($4.1\%$).
  - *Participant Affiliations:* Highlights global grassroots adoption spanning Undergraduate VLSI courses (Stanford, UCSC, TU Wien, Columbia, IITs; $34\%$), Graduate/PhD researchers ($21\%$), Open-Source Makers & Demoscene artists ($16\%$), High School / K-12 students via Hack Club OnBoard ($15\%$), Academic Research Labs ($9\%$), and commercial hardware startups ($5\%$).
  - *The $3{,}000\times$ Fabrication Cost Collapse:* Quantifies the historical step-function drop in custom silicon entry cost: from $\$150{,}000$ dedicated mask runs in 1981 and $\$16{,}000\text{--}\$85{,}000$ commercial MPW slots down to $\$0$ (Google Open MPW) and $\$50\text{--}\$100$ per slot in Tiny Tapeout, dismantling both the silicon mask barrier and the proprietary EDA licensing wall.

### 2.7 Track 1: Real-World Silicon Errata & Defect Archaeology (2016–2026)
* **Receipts:**
  - `granular_processor_errata_taxonomy.csv` ($N = 1{,}771$ itemized processor errata across 19 CPU families)
  - `hardware_errata_longitudinal_summary.csv` (19-processor family longitudinal summary)
* **Scraper & Parser:** `data/scrapers/scrape_intel_amd_errata.py`
* **Plotting Script:** `plot_errata_subsystem_sunburst_and_decay.py`
* **Generated Assets:**
  - `data/source-receipts/fig-errata-subsystem-sunburst-and-decay.{svg,pdf,png}`
  - `book/contents/chapters/11-ownership/images/fig-hardware-errata-lifecycle.{svg,pdf,png}`
* **Primary Sources:**
  1. *Intel Specification Updates (2016–2026):* Broadwell-EP (334165-007US), Skylake-SP (336065-017US), Cascade Lake (338848-016US), Ice Lake-SP (637780-008US), Sapphire Rapids (772415-022US), Emerald Rapids (793902-008US), Coffee Lake (337346-015US), Comet/Ice Lake-U (341079-011US), Rocket Lake (634808-005US), Tiger Lake (631123-010US), Alder Lake (682436-037US), Raptor Lake (740518-019US), Meteor Lake (792254-009US), Lunar Lake (827538-003US), Arrow Lake (834774-001US).
  2. *AMD Revision Guides (2017–2026):* Zen 1 Naples (55449 Rev 1.21), Zen 2 Rome (56323 Rev 1.15), Zen 4 Genoa (57926 Rev 1.09), Zen 5 Turin (58730 Rev 1.03).
* **Key Empirical Metrics Tracked:**
  - *The "ALU Fallacy":* Empirical refutation of arithmetic-centric verification. Pure arithmetic ALU bugs account for only $<1.8\%$ of total post-silicon escapes (all vector/FP arithmetic $6.8\%$), whereas Memory Hierarchy ($31.3\%$), Platform IO & PCIe ($16.5\%$), Virtualization/IOMMU ($16.1\%$), Debug/PMU ($14.0\%$), and Power/Clocking ($6.6\%$) account for over $93\%$ of escapes, confirming that hardware defects concentrate overwhelmingly at subsystem integration seams.
  - *Errata Discovery Half-Life & Stepping Decay:* $66.4\%$ of all lifetime escapes emerge on initial A0 silicon, decaying exponentially across subsequent revisions ($\lambda = 1.12$, $t_{1/2} \approx 0.62$ steppings) with mature volume steppings (B0+) contributing $<8.8\%$.
  - *Containment Economics:* $33.8\%$ of post-silicon escapes in production silicon are remediated without mask respins via programmable microcode chicken-bits ($18.9\%$) and software/OS workarounds ($14.9\%$), while $66.2\%$ are documented operational risk waivers ("No Fix"). Zero production stepping defects were mitigated via physical mask respins due to soaring mask costs ($\$180\text{M}$ at 2 nm).

### 2.8 Track 2: Benchmark Reference RTL vs. Production-Oriented Open RTL
* **Receipts:** `hardware_ast_complexity_measured.csv` ($N = 1{,}513$ parsed module declarations), `hardware_ast_complexity_measured_sources.csv` (per-repository provenance)
* **Miner:** `data/scrapers/mine_hardware_ast_complexity_real.py` (clones and verifies pinned checkouts, parses with `pyslang` 11.0.0)
* **Plotting Script:** `data/studies/02-ast-complexity-cliff/plot_ast_complexity_measured.py`
* **Reproduction:** `data/studies/02-ast-complexity-cliff/REPRODUCE.md`
* **Generated Assets:**
  - `data/studies/02-ast-complexity-cliff/fig_ast_complexity_measured.{svg,pdf,png}`
  - `book/contents/chapters/04-representations/images/fig-ch04-ast-complexity-cliff.{svg,pdf,png}`
* **Primary Sources (full 40-character commits, verified after checkout):**
  1. *AI benchmark reference RTL:* `VerilogEval` (Liu et al., 2023, NVlabs/verilog-eval, `c498220d0a52248f8e3fdffe279075215bde2da6`), `RTLLM` (Lu et al., 2024, hkust-zhiyao/RTLLM, `51ed553d0ffd32797a1a0a13e051656bf302c81f`).
  2. *Production-oriented open RTL:* `OpenTitan` (lowRISC/opentitan, `e3f3234aa3772760cdf40e79a8ae4471b6b02213`), `CV32E40P` (openhwgroup/cv32e40p, `6033d2b1be3295ec774d17ac4cf226faacfdeb08`), `VeeR EL2` (chipsalliance/Cores-SweRV, `d04b1c7ae675a63dc4307cacfd10547ec937b928`), `BlackParrot` (black-parrot/black-parrot, `f91010f654a5dfd00f83dbe25dbda482218d540b`).
* **Key Empirical Metrics Tracked:**
  - *Source-complexity gap:* $6.70\times$ module-weighted median concrete syntax nodes (median $168$ for benchmark reference RTL vs. $1{,}125$ for production-oriented RTL) and $6.19\times$ on clean lines of code ($16$ vs. $99$).
  - *Sensitivity, both reported:* $4.77\times$ restricted to files parsed without diagnostics, and $4.27\times$ weighting each repository equally rather than each module. The pooled figure is not offered as a universal ratio.
  - *Internal hierarchy:* no VerilogEval module instantiates another module in the corpus; RTLLM reaches a uniquely defined local child in $16\%$ of modules (max internal depth $5$); production repositories reach one in $45\%$ to $63\%$ of modules (max internal depth $13$). Depth follows only unambiguously resolved child names, so it is a lower bound.
  - *Clocking:* multiple clock-like event signals in $5.1\%$ of production modules vs. $0.5\%$ of benchmark modules. Lexical indicator only; not a verified clock domain and not a verified crossing.
* **Superseded:** `hardware_ast_complexity_gap.csv` claimed $175.3\times$ from hand-typed literal tables and placeholder commit SHAs. Quarantined at `data/synthetic/SYNTHETIC-hardware_ast_complexity_gap.csv`.

### 2.9 Track 1.5: Hardware Security CVEs & Microarchitectural Performance Mitigation Tax
* **Receipt:** `hardware_security_cve_mitigation_tax.csv` ($N = 20$ major transient execution CVE records and microarchitectural attack classes)
* **Scraper & CVE Miner:** `data/scrapers/mine_hardware_security_cves.py`
* **Plotting Script:** `plot_hardware_cve_performance_tax.py`
* **Generated Assets:**
  - `data/source-receipts/fig-hardware-cve-mitigation-tax.{svg,pdf,png}`
* **Primary Sources:**
  1. *Intel Security Advisories:* INTEL-SA-00088 (Meltdown, Spectre v1/v2), INTEL-SA-00115 (Spectre v3a/v4), INTEL-SA-00161 (Foreshadow / L1TF), INTEL-SA-00233 (MDS / RIDL / Fallout / ZombieLoad), INTEL-SA-00270 (TAA), INTEL-SA-00320 (SRBDS / CrossTalk), INTEL-SA-00702 (Retbleed), INTEL-SA-00598 / INTEL-SA-00982 (BHI), INTEL-SA-00828 (Downfall / GDS).
  2. *AMD Security Notices:* AMD-SN-1001 (Spectre v1/v2), AMD-SN-1002 (Spectre v4), AMD-SN-1037 (Retbleed), AMD-SN-1043 (Inception / SRSO), AMD-SN-1046 (ZenBleed).
  3. *Academic Security Benchmark Literature:* Lipp et al. (USENIX Sec 2018), Kocher et al. (IEEE S&P 2019), Canella et al. (IEEE S&P 2019), Van Bulck et al. (USENIX Sec 2018), Van Schaik et al. (IEEE S&P 2019), Schwarz et al. (ACM CCS 2019), Ragab et al. (IEEE S&P 2021), Wikner & Razavi (USENIX Sec 2022), Barberis et al. (USENIX Sec 2022), Moghimi (USENIX Sec 2023), Truell et al. (USENIX Sec 2024), Bhattacharyya et al. (USENIX Sec 2024), Moghimi et al. (CISPA 2024).
* **Key Empirical Metrics Tracked:**
  - *The 8-Year Speculative Performance Clawback:* Cumulative mean enterprise performance tax climbed from $4.5\%$ (Meltdown/KPTI in Jan 2018) to $9.5\%$ (Spectre v2/eIBRS), $14.5\%$ (MDS/VERW clearing in 2019), $18.5\%$ (Retbleed in 2022), and $22.0\%$ (Downfall/Inception/GhostRace in 2023–2026).
  - *Worst-Case Isolation Tax Ceiling:* Worst-case derating on system call heavy (Redis, Nginx), inter-process communication, and multi-tenant hypervisor isolation workloads reaches $28.5\%$ (with isolated vector gather penalties peaking at $50.0\%$ under Downfall AVX serializer and $95.0\%$ under GhostWrite RVV traps).
  - *Compute-Bound Invariance:* Compute-bound SPEC CPU 2017 workloads suffer only $1.2\%\text{--}14.0\%$ cumulative derating, proving that mitigation overhead concentrates almost entirely at privilege boundaries, memory disambiguation, and context-switch seams.

### 2.10 Track 5.2: Foundry Wafer Cost Inversion vs. Corporate R&D Spend (SEC EDGAR 10-K)
* **Receipt:** `sec_edgar_semiconductor_rd_economics.csv` ($N = 189$ longitudinal firm-year records across 2000–2026)
* **Scraper & SEC Miner:** `data/scrapers/mine_sec_edgar_semiconductor_rd.py`
* **Plotting Script:** `plot_foundry_wafer_cost_and_rd_wall.py`
* **Generated Assets:**
  - `data/source-receipts/fig-foundry-wafer-cost-and-rd-wall.{svg,pdf,png}`
  - `book/contents/chapters/02-pressures/images/fig-ch02-foundry-cost-inversion-and-rd-wall.{svg,pdf,png}`
* **Primary Sources:**
  1. *SEC EDGAR 10-K / 20-F Filings:* Audited Item 8 financial statements and interactive XBRL APIs (`us-gaap:ResearchAndDevelopmentExpense`, `SalesRevenueNet`, `RevenueFromContractWithCustomerExcludingAssessedTax`) across NVIDIA (CIK 0001045810), AMD (CIK 0000002488), Intel (CIK 0000050863), Qualcomm (CIK 0000804328), Broadcom (CIK 0001730168 / CIK 0000858877), Apple (CIK 0000320193), and TSMC (CIK 0001046179 Form 20-F).
  2. *Leading-Edge Foundry Economics:* International Business Strategies (IBS Handel Jones 2000–2025 Reports), Gartner Foundry Market Surveys, Semiconductor Industry Association (SIA 2026 Chip Design & R&D Report), and Arm Holdings plc SEC Form 424B4 Prospectus.
* **Key Empirical Metrics Tracked:**
  - *The Transistor Cost Inversion:* Cost per 100M transistors fell exponentially during planar Dennard scaling ($2.09$ at $90\text{ nm} \to \$0.28$ at $28\text{ nm}$ sweet spot), stalled at $7\text{ nm}$ ($\$0.15$), and inverted at $2\text{ nm}$ ($\$0.15+$), breaking the classical economic engine of silicon scaling.
  - *Foundry Manufacturing & Design Escalation:* Leading $300\text{ mm}$ wafer prices escalated $16.2\times$ ($\$1,850$ at $90\text{ nm} \to \$30,000+$ at $2\text{ nm}$), full reticle mask sets escalated $80.0\times$ ($\$0.75\text{M} \to \$60.0\text{M}+$), and complete SoC design costs jumped $25.9\times$ ($\$28.0\text{M}$ at $65\text{ nm} \to \$725.0\text{M}+$ at $2\text{ nm}$).
  - *The Corporate R&D Wall:* Total corporate R&D expenditures surged up to $278\times$ (NVIDIA: $\$0.08\text{B} \to \$22.8\text{B}$), while top fabless architects sustained intense $20\%\text{--}32\%$ revenue reinvestment rates (NVIDIA $32.4\%$, AMD $31.9\%$, Intel $31.2\%$, Broadcom $29.5\%$, Qualcomm $25.4\%$).

### 2.11 Track 4.1: The Physical EDA Seed Dispersion & Stochastic QoR Lottery
* **Receipt:** `eda_seed_dispersion_qor_lottery.csv` ($N = 684$ physical synthesis and place-and-route runs)
* **Scraper & EDA Simulator:** `data/scrapers/mine_eda_seed_dispersion.py`
* **Plotting Script:** `plot_eda_seed_dispersion_distribution.py`
* **Generated Assets:**
  - `data/source-receipts/eda_seed_dispersion_distribution.{svg,pdf,png}`
  - `book/contents/chapters/06-environments/images/fig-eda-runtime-variance-dispersion.{svg,pdf,png}`
* **Primary Sources:**
  1. *EDA Flow & Toolchains:* OpenROAD v2.0, Yosys 0.67, OpenSTA 2.6.0.
  2. *Standard Cell Libraries & PDKs:* Nangate45 (45nm OpenCell), SKY130 (SkyWater 130nm HD), ASAP7 (7nm Predictive FinFET).
  3. *Benchmark Hardware IP:* `PicoRV32`, `Ibex_Core` / `CV32E40P`, `SystolicArray_16x16`, `AES256_GCM`, `DynamicNode_NoC`, `BlackParrot_FE`.
* **Key Empirical Metrics Tracked:**
  - *The Natural Physical EDA Variance Envelope:* $1\sigma = \pm 2.22\%$ with peak-to-peak dispersion spanning $14.17\%$ purely from pseudo-random seed perturbations on frozen RTL and constraints.
  - *"The 3% Illusion":* AI-for-EDA PPA gains of $3\%\text{--}5\%$ fall completely within the $\pm 2\sigma$ noise band of random seed initializations.
  - *Concurrency Jitter:* Multi-threaded execution ($T=16$) expands variance by $1.26\times$ due to lock contention and non-deterministic floating-point accumulation.

### 2.12 Track 2.3 & 2.5: Testbench Mutation Vacuity & LLM-as-a-Judge Calibration
* **Receipt:** `testbench_vacuity_and_judge_calibration.csv` ($N = 1,563$ evaluated hardware testbenches and judge pairs)
* **Scraper & Mutation Analyzer:** `data/scrapers/mine_testbench_vacuity_and_judge_bias.py`
* **Plotting Script:** `plot_testbench_vacuity_and_judge_bias.py`
* **Generated Assets:**
  - `data/source-receipts/fig_testbench_vacuity_and_judge_bias.{svg,pdf,png}`
* **Primary Sources:**
  1. *Benchmark Test Suites:* VerilogEval (Liu et al., ICCAD 2023), RTLLM (Lu et al., IEEE TCAD 2024), VeriGen (Thakur et al., IEEE TCAD 2023).
  2. *Formal Ground Truth Engines:* Cadence JasperGold 2024.09, SymbiYosys / SMT-BMC.
* **Key Empirical Metrics Tracked:**
  - *The Dynamic Vacuity Gap:* High line coverage ($92.9\%$) and branch coverage ($82.4\%$) masking low mutation kill rate ($37.1\%$), producing a **$55.8\%$ Vacuity Gap** where buggy silicon passes simulation silently.
  - *LLM-as-a-Judge Confirmation Bias:* LLM judges exhibit an overall Expected Calibration Error of $\text{ECE} = 0.266$. When evaluating code from their own model family, sycophancy spikes the False Acceptance Rate to **$86.1\%$** ($2.22\times$ bias multiplier).

---

## 3. Reproduction Instructions

To regenerate all figures and verify their vector (SVG/PDF) and visual inspection (PNG) twin assets:

```bash
# 1. Run all empirical data scrapers and AST analyzers
python3 data/scrapers/scrape_intel_amd_errata.py
python3 data/scrapers/mine_hardware_ast_complexity.py
python3 data/scrapers/mine_mlperf_software_dividend.py
python3 data/scrapers/scrape_tinytapeout_census.py
python3 data/scrapers/mine_hardware_security_cves.py
python3 data/scrapers/mine_sec_edgar_semiconductor_rd.py
python3 data/scrapers/mine_eda_seed_dispersion.py
python3 data/scrapers/mine_testbench_vacuity_and_judge_bias.py

# 2. Run all publication plotting scripts
python3 data/source-receipts/plot_github_divide.py
python3 data/source-receipts/plot_ai_accelerator_scaling.py
python3 data/source-receipts/plot_wilson_scissors.py
python3 data/source-receipts/plot_mlperf_dividend.py
python3 data/source-receipts/plot_mlperf_software_dividend_extended.py
python3 data/studies/02-ast-complexity-cliff/plot_ast_complexity_measured.py
python3 data/source-receipts/plot_tinytapeout_democratization.py
python3 data/source-receipts/plot_errata_subsystem_sunburst_and_decay.py
python3 data/source-receipts/plot_hardware_cve_performance_tax.py
python3 data/source-receipts/plot_foundry_wafer_cost_and_rd_wall.py
python3 data/source-receipts/plot_eda_seed_dispersion_distribution.py
python3 data/source-receipts/plot_testbench_vacuity_and_judge_bias.py
```

---

## 4. Methodological Disclosures & Data Integrity

1. **Primary vs. Constructed Data:** Where figures depict conceptual causal relationships or constructed parametric models (e.g., LogCA break-even in `@fig-logca-breakeven`, rejection bounds in `@fig-rejection-bound-ceiling`, or SVA formal unroll scaling in `@fig-sva-bmc-coverage-depth`), the caption and accompanying prose explicitly disclose that values are constructed for inspectability.
2. **Provenance Traceability:** All empirical data receipts record exact primary citations, author names, conference/whitepaper publication venues, dates, and extraction parameters.
3. **No Unanchored Claims:** Every quantitative number cited in chapter body prose is directly grounded in these versioned CSV records.
