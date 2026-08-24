# Architecture 2.0 Data & Empirical Provenance Hub

This directory houses the empirical data infrastructure, automated scrapers, primary source receipts, and reproduction engines backing all quantitative analyses, figures, and tables in *Architecture 2.0*.

---

## 1. Subsystem Architecture

```
data/
├── README.md                          # This master data & provenance hub
├── scrapers/                          # Automated data collection, AST analysis & PDF extraction pipelines
│   ├── scrape_intel_amd_errata.py     # Parses Intel & AMD processor errata specification updates
│   ├── mine_hardware_ast_complexity.py# Static AST & CDC complexity analyzer (Pyverilog/CIRCT/cloc)
│   ├── mine_mlperf_software_dividend.py# Historical MLCommons scraper & inference kernel telemetry
│   └── scrape_tinytapeout_census.py   # Tiny Tapeout API & Open MPW longitudinal census scraper
├── source-receipts/                   # Canonical versioned CSV receipts & publication plotting scripts
│   ├── README.md                      # Detailed methodology, citation index, and mathematical derivations
│   ├── regenerate.py                  # Batch driver for derived datasets
│   ├── granular_processor_errata_taxonomy.csv # N=1,771 itemized processor errata dataset
│   ├── hardware_ast_complexity_gap.csv# N=550 hardware module AST complexity gap dataset
│   ├── mlperf_longitudinal_software_dividend.csv # MLCommons fixed-silicon software dividend (2018–2026)
│   ├── inference_kernel_fragmentation.csv # Custom kernel proliferation across vLLM, SGLang, TRT-LLM
│   ├── tinytapeout_democratization_census.csv # 27 shuttle rounds, 4,780+ custom taped-out designs
│   ├── shuttle_cost_historical_collapse.csv # 45-year silicon fabrication cost collapse (1981–2026)
│   └── plot_*.py                      # Publication plotting scripts producing vector SVG/PDF/PNG assets
└── processed/                         # Processed corpora and intermediate database tables
    └── corpus-pilot/                  # Architectural corpus analytics
```

---

## 2. Core Provenance & Verification Principles

Every dataset in this repository adheres to three non-negotiable empirical invariants:

1. **Cryptographic Integrity & Attribution:** Every CSV file includes a structured metadata header specifying:
   - Primary source URLs and official document IDs (e.g., Intel Spec Update IDs, AMD Revision Guides, MLCommons result links, GitHub commit SHAs).
   - Extraction timestamps (ISO 8601 UTC).
   - Toolchain versions and environment parameters.
   - SHA256 hashes of source documents.
2. **Deterministic Reproducibility:** Every figure and CSV can be re-extracted and regenerated from scratch using the standalone scripts in `data/scrapers/` and `data/source-receipts/`.
3. **Strict Separation of Empirical vs. Parametric Data:** Real-world measurements (e.g., processor errata, AST depths, MLPerf throughputs, Tiny Tapeout submissions) are strictly quarantined in dedicated source receipt CSVs. Parametric/constructed models used for conceptual illustrations are explicitly disclosed as constructed.

---

## 3. Master One-Command Regeneration & Audit

To execute all scrapers, verify dataset integrity, and regenerate all publication figures across the monograph:

```bash
# Step 1: Run all data collection scrapers
python3 data/scrapers/scrape_intel_amd_errata.py
python3 data/scrapers/mine_hardware_ast_complexity.py
python3 data/scrapers/mine_mlperf_software_dividend.py
python3 data/scrapers/scrape_tinytapeout_census.py

# Step 2: Regenerate all publication figures
python3 data/source-receipts/plot_github_divide.py
python3 data/source-receipts/plot_ai_accelerator_scaling.py
python3 data/source-receipts/plot_wilson_scissors.py
python3 data/source-receipts/plot_mlperf_dividend.py
python3 data/source-receipts/plot_mlperf_software_dividend_extended.py
python3 data/source-receipts/plot_ast_complexity_cliff.py
python3 data/source-receipts/plot_tinytapeout_democratization.py
python3 data/source-receipts/plot_errata_subsystem_sunburst_and_decay.py

# Step 3: Run repository-wide quality & precommit audit
python3 cli/arch2.py check precommit
```
