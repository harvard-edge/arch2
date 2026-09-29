# Architecture 2.0 Data & Empirical Provenance Hub

This directory holds the datasets, measurement harnesses, and reproduction scripts behind the quantitative figures and tables in *Architecture 2.0* and on the public data page (`www/data.qmd`).

---

## 1. Layout

```
data/
├── README.md                                 # This file
├── scrapers/                                 # Measurement harnesses and miners
│   ├── mine_hardware_ast_complexity_real.py  # Study 02: pyslang concrete syntax trees on pinned commits
│   ├── run_openroad_gcd_placement_seed_pilot.py # Study 06: OpenROAD placement seed pilot (20 seeds, Docker)
│   ├── mine_verilog_eval_mutation_pilot.py   # Study 08: VerilogEval mutation pilot (Icarus, Yosys)
│   └── mine_*.py                             # Other miners feeding chapter datasets
├── datasets/                                 # Chapter datasets and plotting scripts; provenance in provenance.yml
│   ├── README.md                             # Per-dataset methodology and sources
│   ├── provenance.yml                        # Audit record for datasets that feed book figures
│   ├── hardware_ast_complexity_measured.csv  # Study 02 data, N=1,513 module declarations
│   └── chapter*-*.csv                        # Chapter datasets
├── studies/                                  # Self-contained measured studies behind www/data.qmd
│   ├── 02-ast-complexity-cliff/
│   ├── 06-eda-seed-dispersion/
│   ├── 08-testbench-vacuity-and-judge-bias/  # Executed VerilogEval mutation pilot
│   └── ai_systolic_array_study/              # Recorded SCALE-Sim study used in Chapters 5 and 7
├── notebooks/                                # marimo notebooks that recompute Studies 02 and 06
└── processed/                                # Processed corpora and intermediate tables
```

Generated values are not kept in this repository. On 29 September 2026 the former
`data/synthetic/` quarantine and five website studies (errata, MLPerf software
dividend, Tiny Tapeout, hardware CVE tax, foundry cost and R&D) were deleted after
value-by-value checks against their primary sources failed. See
`data/studies/README.md` for what each check found.

---

## 2. Reproduction

```bash
# Study 02: re-parse the pinned corpora and redraw the figure
python3 data/scrapers/mine_hardware_ast_complexity_real.py
python3 data/studies/02-ast-complexity-cliff/plot_ast_complexity_measured.py

# Study 06: needs Docker, about 20 minutes
python3 data/scrapers/run_openroad_gcd_placement_seed_pilot.py
python3 data/studies/06-eda-seed-dispersion/plot_placement_seed_pilot.py

# Study 08: needs iverilog, vvp, yosys and a pinned VerilogEval checkout
python3 data/scrapers/mine_verilog_eval_mutation_pilot.py --corpus <verilog-eval checkout>
python3 data/studies/08-testbench-vacuity-and-judge-bias/plot_verilog_eval_mutation_pilot.py

# Provenance checks
python3 data/validate_provenance.py
python3 data/validate_figure_provenance.py
```
