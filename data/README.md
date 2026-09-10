# Architecture 2.0 Data & Empirical Provenance Hub

This directory houses the empirical data infrastructure, automated scrapers, primary source datasets, and reproduction engines backing all quantitative analyses, figures, and tables in *Architecture 2.0*.

---

## 1. Subsystem Architecture

```
data/
├── README.md                                 # This master data & provenance hub
├── scrapers/                                 # Automated data collection, AST analysis & PDF extraction pipelines
│   ├── scrape_intel_amd_errata.py            # Track 1.1: Parses Intel & AMD processor errata specification updates
│   ├── mine_hardware_ast_complexity_real.py  # Track 2.1: pyslang AST complexity parser on pinned commits
│   ├── mine_mlperf_software_dividend.py      # Track 3.1 & 3.2: Historical MLCommons scraper & inference kernel telemetry
│   ├── scrape_tinytapeout_census.py          # Track 6.1: Tiny Tapeout API & Open MPW longitudinal census scraper
│   ├── mine_hardware_security_cves.py        # Track 1.5: Microarchitectural hardware security CVEs & mitigation taxes
│   ├── run_openroad_gcd_placement_seed_pilot.py # Track 4.1: OpenROAD placement seed dispersion pilot (20 seeds)
│   └── mine_sec_edgar_semiconductor_rd.py    # Track 5.2: SEC EDGAR 10-K R&D financial filings & wafer pricing miner
├── datasets/                          # Canonical versioned CSV datasets & publication plotting scripts
│   ├── README.md                             # Detailed methodology, citation index, and mathematical derivations
│   ├── regenerate.py                         # Batch driver for derived datasets
│   ├── granular_processor_errata_taxonomy.csv# N=1,771 itemized processor errata dataset (Track 1)
│   ├── hardware_ast_complexity_measured.csv  # N=1,513 parsed RTL module declarations, pyslang 11.0.0 (Track 2)
│   ├── mlperf_longitudinal_software_dividend.csv # MLCommons fixed-silicon software dividend 2018–2026 (Track 3)
│   ├── inference_kernel_fragmentation.csv    # Custom kernel proliferation across vLLM, SGLang, TRT-LLM (Track 3)
│   ├── tinytapeout_democratization_census.csv# 27 shuttle rounds, 4,780+ custom taped-out designs (Track 6)
│   ├── shuttle_cost_historical_collapse.csv  # 45-year silicon fabrication cost collapse 1981–2026 (Track 6)
│   ├── hardware_security_cve_mitigation_tax.csv # 8-year microarchitectural CVE derating dataset (Track 1.5)
│   ├── openroad_gcd_placement_seed_pilot.csv # N=20 measured OpenROAD Nangate45 placement runs (Track 4.1)
│   ├── sec_edgar_semiconductor_rd_economics.csv # N=189 firm-year financial records (Track 5.2)
│   ├── chapter7-testbench-vacuity-mutation.csv # Transcribed mutation kill rates (Herdt et al., ASPDAC 2021)
│   └── plot_*.py                             # Publication plotting scripts producing vector SVG/PDF/PNG assets
├── synthetic/                         # Quarantined synthetic datasets and generators (NOT measurements)
│   ├── README.md                             # Traceability ledger for quarantined synthetic artifacts
│   └── SYNTHETIC-*.csv
└── processed/                                # Processed corpora and intermediate database tables
    └── corpus-pilot/                         # Architectural corpus analytics
```

---

## 2. Master One-Command Regeneration & Audit

To execute measured data pipelines, verify dataset integrity, and regenerate publication figures:

```bash
# Step 1: Run data collection and measurement scripts
python3 data/scrapers/scrape_intel_amd_errata.py
python3 data/scrapers/mine_hardware_ast_complexity_real.py
python3 data/scrapers/mine_mlperf_software_dividend.py
python3 data/scrapers/scrape_tinytapeout_census.py
python3 data/scrapers/mine_hardware_security_cves.py
python3 data/scrapers/mine_sec_edgar_semiconductor_rd.py

# Step 2: Regenerate all publication figures
python3 data/datasets/plot_github_divide.py
python3 data/datasets/plot_ai_accelerator_scaling.py
python3 data/datasets/plot_wilson_scissors.py
python3 data/datasets/plot_mlperf_dividend.py
python3 data/datasets/plot_mlperf_software_dividend_extended.py
python3 data/studies/02-ast-complexity-cliff/plot_ast_complexity_measured.py
python3 data/datasets/plot_tinytapeout_democratization.py
python3 data/datasets/plot_errata_subsystem_sunburst_and_decay.py
python3 data/datasets/plot_hardware_cve_performance_tax.py
python3 data/datasets/plot_foundry_wafer_cost_and_rd_wall.py
python3 data/datasets/plot_eda_seed_dispersion_distribution.py
python3 data/datasets/plot_testbench_vacuity_and_judge_bias.py

# Step 3: Run repository-wide quality & precommit audit
python3 cli/arch2.py check precommit
```
