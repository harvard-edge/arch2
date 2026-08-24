# Architecture 2.0: Empirical Studies & Publication Exhibits Catalog

This directory contains self-contained empirical study packages backing *Architecture 2.0*. Each folder contains complete datasets, standalone plotting scripts, publication figures, data schemas, reproduction recipes, and citation metadata.

---

## Master Study Catalog

| ID | Study Title | Primary Artifacts | Key Finding |
| :--- | :--- | :--- | :--- |
| [`01-silicon-errata-archaeology`](./01-silicon-errata-archaeology/) | **Real-World Silicon Errata & Defect Archaeology (2016–2026)** | [`README`](./01-silicon-errata-archaeology/README.md) · [`Data`](./01-silicon-errata-archaeology/granular_processor_errata_taxonomy.csv) · [`Plot`](./01-silicon-errata-archaeology/fig-errata-subsystem-sunburst-and-decay.png) | **The ALU Fallacy:** Pure integer ALU bugs account for <1.8% of post-silicon escapes (all arithmetic/FP/vector = 6.8%). ... |
| [`02-ast-complexity-cliff`](./02-ast-complexity-cliff/) | **The AI Benchmark Mirage vs. Physical Silicon AST Complexity** | [`README`](./02-ast-complexity-cliff/README.md) · [`Data`](./02-ast-complexity-cliff/hardware_ast_complexity_gap.csv) · [`Plot`](./02-ast-complexity-cliff/fig_ast_complexity_cliff.png) | **The 175x AST Node Gap:** AI benchmarks evaluate leaf modules with a median of 73 AST nodes (<100 LoC), whereas product... |
| [`03-mlperf-software-dividend`](./03-mlperf-software-dividend/) | **The Software Porting Wall & Fixed-Silicon Software Dividend (2018–2026)** | [`README`](./03-mlperf-software-dividend/README.md) · [`Data`](./03-mlperf-software-dividend/mlperf_longitudinal_software_dividend.csv) · [`Plot`](./03-mlperf-software-dividend/mlperf_software_dividend_extended_master.png) | **The In-Place Software Dividend:** Maturing software stacks deliver massive speedups on identical, frozen physical sili... |
| [`04-tinytapeout-democratization`](./04-tinytapeout-democratization/) | **Open Silicon Democratization & The 3,000× Cost Collapse (1981–2026)** | [`README`](./04-tinytapeout-democratization/README.md) · [`Data`](./04-tinytapeout-democratization/tinytapeout_democratization_census.csv) · [`Plot`](./04-tinytapeout-democratization/fig-tinytapeout-democratization-census.png) | **The 3,000x Prototyping Cost Collapse:** Custom silicon entry cost collapsed from $150,000 dedicated mask runs (1981 MO... |
| [`05-hardware-security-cve-tax`](./05-hardware-security-cve-tax/) | **Hardware Security CVEs & Microarchitectural Performance Mitigation Tax** | [`README`](./05-hardware-security-cve-tax/README.md) · [`Data`](./05-hardware-security-cve-tax/hardware_security_cve_mitigation_tax.csv) · [`Plot`](./05-hardware-security-cve-tax/fig-hardware-cve-mitigation-tax.png) | **The 22% Performance Clawback:** Cumulative hardware security mitigations (Meltdown, Spectre v2, MDS, Retbleed, Downfal... |
| [`06-eda-seed-dispersion`](./06-eda-seed-dispersion/) | **Physical EDA Seed Dispersion & The '3% Illusion'** | [`README`](./06-eda-seed-dispersion/README.md) · [`Data`](./06-eda-seed-dispersion/eda_seed_dispersion_qor_lottery.csv) · [`Plot`](./06-eda-seed-dispersion/eda_seed_dispersion_distribution.png) | **Natural QoR Dispersion (1sigma = +-2.22%):** Physical PnR heuristics exhibit a natural 3%–8% wirelength and timing dis... |
| [`07-foundry-cost-and-rd-wall`](./07-foundry-cost-and-rd-wall/) | **Foundry Wafer Cost Inversion vs. Corporate R&D Spend (SEC EDGAR 10-K)** | [`README`](./07-foundry-cost-and-rd-wall/README.md) · [`Data`](./07-foundry-cost-and-rd-wall/sec_edgar_semiconductor_rd_economics.csv) · [`Plot`](./07-foundry-cost-and-rd-wall/fig-foundry-wafer-cost-and-rd-wall.png) | **The Transistor Cost Inversion:** Cost per 100M transistors fell from $2.09 (90nm) to $0.28 (28nm sweet spot), but stal... |
| [`08-testbench-vacuity-and-judge-bias`](./08-testbench-vacuity-and-judge-bias/) | **Testbench Mutation Vacuity & LLM-as-a-Judge Calibration** | [`README`](./08-testbench-vacuity-and-judge-bias/README.md) · [`Data`](./08-testbench-vacuity-and-judge-bias/testbench_vacuity_and_judge_calibration.csv) · [`Plot`](./08-testbench-vacuity-and-judge-bias/fig_testbench_vacuity_and_judge_bias.png) | **The 55.8% Vacuity Gap:** AI-generated testbenches achieve >92% line coverage and >82% branch coverage, but achieve onl... |

---

## Reproduction Across All Studies

To re-run all plotting scripts across every individual study package:

```bash
for study in data/studies/*/; do
  if [ -d "$study" ]; then
    echo "Executing $study..."
    (cd "$study" && python3 plot_*.py)
  fi
done
```

---

## Citation

If you use these datasets, figures, or empirical findings in your research or teaching, please cite:

```bibtex
@book{reddi2026architecture2,
  author    = {Vijay Janapa Reddi},
  title     = {Architecture 2.0: Principles of AI-Native System and Chip Design},
  year      = {2026},
  url       = {https://arch2.mlsysbook.ai}
}
```

> Vijay Janapa Reddi. *Architecture 2.0: Principles of AI-Native System and Chip Design* (2026). Available at: `https://arch2.mlsysbook.ai`
