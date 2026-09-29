# Datasets

Analysis-ready data backing the book's figures. Provenance for every dataset that
feeds a figure is recorded in `provenance.yml` (schema `arch2-provenance/v1`, the
same keys as `data/studies/*/provenance.yml`).

> **Audited 2026-09-09.** 244 published claims across 17 datasets were checked by a
> blind-derive / diff / adversarial-refute pass. 125 were flagged, all 125 were sent
> to a skeptic, and 98 survived: 15 blockers, 33 material, the rest minor. Every
> surviving finding is recorded in `provenance.yml` with a file and line.
>
> **All 15 blockers are fixed** (marked `status: FIXED 2026-09-09` in
> `provenance.yml`). The 83 material, minor and low findings remain open and are
> recorded there for a later pass.

## Validator limits

`validate_figure_provenance.py` accepts a script that names its CSV as a string
literal even when the script never opens it, so a pass is not proof that a figure
reads its data. Two plotting scripts that did this (`plot_mlperf_dividend.py`,
`plot_foundry_wafer_cost_and_rd_wall.py`) were deleted on 29 September 2026 with
their datasets.

## 1. Directory Structure

```
data/datasets/
├── README.md                                # This provenance guide and methodology record
├── regenerate.py                            # Batch regeneration driver for upstream derived datasets
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
├── plot_ai_accelerator_scaling.py           # Script generating fig-ch02-accelerator-scaling-frontier
├── plot_wilson_scissors.py                  # Script generating fig-ch07-wilson-verification-scissors
└── [other chapterN-*.csv datasets]          # Additional chapter-specific empirical datasets
```

---

## 2. Core Provenance Records & Methodologies

### 2.1 Chapter datasets

Each chapter dataset carries its sources in its header or in a per-row citation
column, and each dataset that feeds a book figure has a record in `provenance.yml`.
Numbers are not restated here, because a restated number drifts from the file it
came from. Read the CSV and its `provenance.yml` entry.

### 2.2 Track 2: Benchmark Reference RTL vs. Production-Oriented Open RTL
* **Datasets:** `hardware_ast_complexity_measured.csv` ($N = 1{,}513$ parsed module declarations), `hardware_ast_complexity_measured_sources.csv` (per-repository provenance)
* **Miner:** `data/scrapers/mine_hardware_ast_complexity_real.py` (clones and verifies pinned checkouts, parses with `pyslang` 11.0.0)
* **Plotting Script:** `data/studies/02-ast-complexity-cliff/plot_ast_complexity_measured.py`
* **Reproduction:** `data/studies/02-ast-complexity-cliff/REPRODUCE.md`
* **Generated Assets:**
  - `data/studies/02-ast-complexity-cliff/fig_ast_complexity_measured.{svg,pdf,png}`
  - `book/contents/chapters/04-representations/images/fig-ch04-ast-complexity-cliff.{svg,pdf,png}`
* **Primary Sources (full 40-character commits, verified after checkout):**
  1. *AI benchmark reference RTL:* `VerilogEval` (Liu et al., 2023, NVlabs/verilog-eval, `c498220d0a52248f8e3fdffe279075215bde2da6`), `RTLLM` (Lu et al., 2024, hkust-zhiyao/RTLLM, `51ed553d0ffd32797a1a0a13e051656bf302c81f`).
  2. *Production-oriented open RTL:* `OpenTitan` (lowRISC/opentitan, `e3f3234aa3772760cdf40e79a8ae4471b6b02213`), `CV32E40P` (openhwgroup/cv32e40p, `6033d2b1be3295ec774d17ac4cf226faacfdeb08`), `VeeR EH1` (chipsalliance/Cores-SweRV, `d04b1c7ae675a63dc4307cacfd10547ec937b928`), `BlackParrot` (black-parrot/black-parrot, `f91010f654a5dfd00f83dbe25dbda482218d540b`).
* **Key Empirical Metrics Tracked:**
  - *Source-complexity gap:* $6.70\times$ module-weighted median concrete syntax nodes (median $168$ for benchmark reference RTL vs. $1{,}125$ for production-oriented RTL) and $6.19\times$ on clean lines of code ($16$ vs. $99$).
  - *Sensitivity, both reported:* $4.77\times$ restricted to files parsed without diagnostics, and $4.27\times$ weighting each repository equally rather than each module. The pooled figure is not offered as a universal ratio.
  - *Internal hierarchy:* no VerilogEval module instantiates another module in the corpus; RTLLM reaches a uniquely defined local child in $16\%$ of modules (max internal depth $5$); production repositories reach one in $45\%$ to $63\%$ of modules (max internal depth $13$). Depth follows only unambiguously resolved child names, so it is a lower bound.
  - *Clocking:* multiple clock-like event signals in $5.1\%$ of production modules vs. $0.5\%$ of benchmark modules. Lexical indicator only; not a verified clock domain and not a verified crossing.
* **Superseded:** `hardware_ast_complexity_gap.csv` claimed $175.3\times$ from hand-typed literal tables and placeholder commit SHAs. The file and its generator were deleted on 2026-09-29.

### 2.3 Track 4.1: Physical Design Seed Dispersion in OpenROAD
* **Source data:** `openroad_gcd_placement_seed_pilot.csv` ($N = 20$ measured placement runs on GCD Nangate45)
* **Measurement Harness:** `data/scrapers/run_openroad_gcd_placement_seed_pilot.py`
* **Plotting Script:** `data/studies/06-eda-seed-dispersion/plot_openroad_gcd_placement_seed_pilot.py`
* **Generated Assets:**
  - `data/studies/06-eda-seed-dispersion/openroad_gcd_placement_seed_pilot.{png,pdf,svg}`
* **Primary Sources:**
  1. *Toolchain:* OpenROAD-flow-scripts commit `8359fde`, run in the official ORFS container pinned by SHA-256 digest (recorded in `openroad_gcd_placement_seed_pilot_summary.json`).
  2. *Standard Cell Library:* Nangate45 (45nm OpenCellLibrary).
  3. *Benchmark Design:* `gcd` (Greatest Common Divisor coprocessor, Nangate45).
* **Key Empirical Metrics Measured:**
  - *Setup Slack Dispersion:* Setup slack span of $3.83\%$ across twenty random placement seeds on frozen floorplan and RTL.
  - *Instance Area Invariance:* Detailed placement instance area moves only $0.84\%$ over the same runs.
* **Note on Predecessor:** An earlier seed-dispersion dataset was generated by a noise function rather than measured. It and its generator were deleted on 2026-09-29.

---

## 3. Reproduction Instructions

Each chapter dataset's generating or plotting script is named in its section above
and in `provenance.yml`. The measured studies reproduce as follows:

```bash
python3 data/scrapers/mine_hardware_ast_complexity_real.py
python3 data/studies/02-ast-complexity-cliff/plot_ast_complexity_measured.py
python3 data/scrapers/run_openroad_gcd_placement_seed_pilot.py   # needs Docker
python3 data/studies/06-eda-seed-dispersion/plot_placement_seed_pilot.py
```

---

## 4. Methodological Disclosures & Data Integrity

1. **Primary vs. Constructed Data:** Where figures depict conceptual causal relationships or constructed parametric models (e.g., LogCA break-even in `@fig-logca-breakeven`, rejection bounds in `@fig-rejection-bound-ceiling`, or SVA formal unroll scaling in `@fig-sva-bmc-coverage-depth`), the caption and accompanying prose explicitly disclose that values are constructed for inspectability.
2. **Provenance Traceability:** All empirical data datasets record exact primary citations, author names, conference/whitepaper publication venues, dates, and extraction parameters.
3. **Deleted, not quarantined:** A dataset whose values cannot be traced to a retained measurement or an openable primary source is deleted, with the figure and prose that relied on it. The deletions of 29 September 2026 are listed in `data/studies/README.md`.
