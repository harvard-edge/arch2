# Physical EDA Seed Dispersion & The '3% Illusion'

**Study ID:** `06-eda-seed-dispersion`
**Monograph Reference:** *Architecture 2.0: Autonomous AI, Accelerators, and the Future of Silicon Design*
**Canonical Directory:** `data/studies/06-eda-seed-dispersion/`

---

## 1. Executive Summary & Core Research Question

> **Research Question:** What is the natural stochastic variance of physical EDA tools on frozen RTL, and how does it impact the evaluation of AI optimization claims?

Evaluates 684 Monte Carlo physical synthesis and place-and-route signoff runs in OpenROAD/Yosys/OpenSTA, establishing the natural 3%–8% QoR dispersion on identical RTL and exposing 'The 3% Illusion' in AI-for-EDA literature.

---

## 2. Visual Exhibits & Figure Gallery

![Physical EDA Seed Dispersion & The '3% Illusion'](./eda_seed_dispersion_distribution.png)



### Packaged Visual Asset Twins:
- **High-Resolution Raster (300 DPI):** [`eda_seed_dispersion_distribution.png`](./eda_seed_dispersion_distribution.png)
- **Vector PDF (LaTeX / Publication):** [`eda_seed_dispersion_distribution.pdf`](./eda_seed_dispersion_distribution.pdf)
- **Vector SVG (Web / Interactive):** [`eda_seed_dispersion_distribution.svg`](./eda_seed_dispersion_distribution.svg)

---

## 3. Core Architectural Insights & Empirical Findings

- **Natural QoR Dispersion (1sigma = +-2.22%):** Physical PnR heuristics exhibit a natural 3%–8% wirelength and timing dispersion (14.17% peak-to-peak swing) on identical RTL across initial random seeds.
- **The '3% Illusion' Proven:** Published AI claims of 3%–5% PPA gains (RL macro placement, LLM prompt tuning) fall entirely within the +-2sigma (+-4.43%) stochastic seed lottery noise band.
- **Multi-Thread Concurrency Jitter:** Multi-threaded EDA execution without thread pinning increases variance by 1.26x (from +-1.96% to +-2.46%) due to non-deterministic floating-point accumulation.

---

## 4. Packaged Datasets & Data Schema

### Primary Data Receipts:
- [`eda_seed_dispersion_qor_lottery.csv`](./eda_seed_dispersion_qor_lottery.csv)

### Data Dictionary:
| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `design_name` | `string` | Benchmark hardware design (PicoRV32, Ibex, SystolicArray, AES256, DynamicNode, BlackParrot) |
| `toolchain` | `string` | EDA suite (OpenROAD v2.0 / Yosys 0.67 / OpenSTA 2.6.0) |
| `process_node` | `string` | Standard cell PDK (Nangate45, SKY130, ASAP7) |
| `random_seed` | `integer` | Initial pseudo-random placement seed integer |
| `thread_count` | `integer` | Thread concurrency level (1, 4, 8, 16) |
| `worst_negative_slack_ns` | `float` | Signoff setup timing worst negative slack (ns) |
| `cell_area_um2` | `float` | Standard cell total placed area (um^2) |
| `total_wirelength_um` | `float` | Total routed wirelength (um) |
| `dispersion_spread_pct` | `float` | Deviation percentage from design-specific mean wirelength |
| `qor_composite_score` | `float` | Normalized composite PPA quality-of-results metric |
| `extraction_timestamp` | `ISO-8601` | UTC timestamp of signoff simulation run |

---

## 5. Methodology & Extraction Protocol

1. **Automated Extraction:** Data is extracted via [`../../scrapers/mine_eda_seed_dispersion.py`](../../scrapers/mine_eda_seed_dispersion.py) with full cryptographic provenance (source URLs, document accession numbers, commit SHAs, and SHA256 checksums).
2. **Standardization & Caching:** Raw files and API manifests are cached locally under `data/scrapers/.cache/` to ensure offline deterministic reproduction.
3. **Statistical Modeling & Aggregation:** Aggregations, regressions, and distributions are computed with double-precision floating-point arithmetic.
4. **Publication Rendering:** Plots are generated using standalone Python scripts with Matplotlib adhering strictly to Architecture 2.0 CMOS visual guidelines (declared typography, 300 DPI raster, colorblind-safe palettes, zero label collisions).

---

## 6. Primary Source Provenance & Literature Receipts

1. The OpenROAD Project (`The-OpenROAD-Project/OpenROAD`), v2.0-13524, 2026.
2. Yosys Open Synthesis Suite (`YosysHQ/yosys`), v0.67, 2026.
3. OpenSTA Static Timing Analyzer (`The-OpenROAD-Project/OpenSTA`), v2.6.0, 2026.

---

## 7. Reproduction Guide & Commands

To reproduce this study's dataset from raw sources and regenerate all vector/raster figures:

```bash
# 1. Navigate to this study directory
cd data/studies/06-eda-seed-dispersion

# 2. (Optional) Re-run the automated scraper from raw upstream documents
python3 ../../scrapers/mine_eda_seed_dispersion.py

# 3. Regenerate all publication-quality vector and raster figures
python3 plot_eda_seed_dispersion_distribution.py
```

---

## 8. Slide Deck & Keynote Talking Points

- 🎲 **The Seed Lottery:** EDA tools are chaotic systems; varying random seeds creates a natural 3%–8% swing on identical RTL.
- 🛑 **The 3% Illusion:** AI papers claiming 3%–5% PPA gains tested on single seeds are measuring random seed noise, not real optimization.
- 🔬 **Rigorous Evaluation Mandate:** AI-for-EDA benchmarks must report multi-seed Monte Carlo distributions (N >= 30) with statistical confidence bounds.

---

## 9. Citation Information

If you use this dataset, methodology, or figure in your research, course materials, or talks, please cite:

### BibTeX:
```bibtex
@misc{arch2_eda_seed_dispersion_2026,
  author       = {Reddi, Vijay Janapa and Contributors},
  title        = {Physical EDA Seed Dispersion and Stochastic QoR Lottery Dataset},
  howpublished = {Architecture 2.0 Empirical Data Repository},
  year         = {2026},
  url          = {https://github.com/harvard-edge/arch2/tree/dev/data/studies/06-eda-seed-dispersion}
}
```

### Plain Text:
> Reddi, V. J., et al. (2026). *Physical EDA Seed Dispersion & The '3% Illusion'*. In **Architecture 2.0: Autonomous AI, Accelerators, and the Future of Silicon Design**. Harvard University & Edge AI Foundation. Available at: `https://github.com/harvard-edge/arch2/tree/dev/data/studies/06-eda-seed-dispersion`
