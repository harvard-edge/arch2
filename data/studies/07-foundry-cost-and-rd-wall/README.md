# Foundry Wafer Cost Inversion vs. Corporate R&D Spend (SEC EDGAR 10-K)

**Study ID:** `07-foundry-cost-and-rd-wall`
**Monograph Reference:** *Architecture 2.0: Autonomous AI, Accelerators, and the Future of Silicon Design*
**Canonical Directory:** `data/studies/07-foundry-cost-and-rd-wall/`

---

## 1. Executive Summary & Core Research Question

> **Research Question:** How have leading-edge foundry manufacturing costs and corporate R&D intensity escalated across semiconductor scaling nodes?

Tracks 25 years of SEC EDGAR 10-K corporate R&D filings across major semiconductor firms paired with leading-edge foundry wafer costs ($90nm -> 2nm), highlighting the transistor cost inversion and the $725M single-chip barrier.

---

## 2. Visual Exhibits & Figure Gallery

![Foundry Wafer Cost Inversion vs. Corporate R&D Spend (SEC EDGAR 10-K)](./fig-foundry-wafer-cost-and-rd-wall.png)



### Packaged Visual Asset Twins:
- **High-Resolution Raster (300 DPI):** [`fig-foundry-wafer-cost-and-rd-wall.png`](./fig-foundry-wafer-cost-and-rd-wall.png)
- **Vector PDF (LaTeX / Publication):** [`fig-foundry-wafer-cost-and-rd-wall.pdf`](./fig-foundry-wafer-cost-and-rd-wall.pdf)
- **Vector SVG (Web / Interactive):** [`fig-foundry-wafer-cost-and-rd-wall.svg`](./fig-foundry-wafer-cost-and-rd-wall.svg)

---

## 3. Core Architectural Insights & Empirical Findings

- **The Transistor Cost Inversion:** Cost per 100M transistors fell from $2.09 (90nm) to $0.28 (28nm sweet spot), but stalled at 7nm ($0.15) and inverted upwards at 2nm ($0.152+), breaking Moore's economic law.
- **The 16.2x Wafer Cost Surge:** 300mm wafer prices surged from $1,850 (90nm) to over $30,000 (2nm), while full reticle mask sets jumped 80x ($0.75M to $60M+) and total SoC design costs reached $725M.
- **The Corporate R&D Wall:** Corporate R&D spend escalated up to 278x (NVIDIA: $0.08B to $22.8B), with top fabless firms reinvesting 25%–32% of total annual gross revenue into engineering.

---

## 4. Packaged Datasets & Data Schema

### Primary Data Receipts:
- [`sec_edgar_semiconductor_rd_economics.csv`](./sec_edgar_semiconductor_rd_economics.csv)

### Data Dictionary:
| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `fiscal_year` | `integer` | Fiscal financial reporting year (2000–2026) |
| `company_ticker` | `string` | Stock ticker symbol (NVDA, AMD, INTC, QCOM, AVGO, AAPL, TSM) |
| `company_name` | `string` | Corporate legal entity name |
| `annual_revenue_usd_billion` | `float` | Audited total net revenue in billions USD |
| `rd_expense_usd_billion` | `float` | Audited research & development expense in billions USD |
| `rd_intensity_pct` | `float` | R&D intensity percentage (R&D Expense / Total Revenue * 100) |
| `leading_process_node_nm` | `integer` | Leading-edge volume commercial manufacturing node (nm) |
| `wafer_cost_usd` | `float` | Average contract manufacturing price per 300mm wafer (USD) |
| `full_reticle_mask_cost_usd_million` | `float` | Estimated full reticle mask set tooling cost (M USD) |
| `design_cost_per_soc_usd_million` | `float` | Total estimated SoC non-recurring engineering design cost (M USD) |
| `sec_accession_number` | `string` | SEC EDGAR filing accession number |
| `filing_url` | `string` | Direct SEC EDGAR HTML/XBRL filing link |
| `extraction_timestamp` | `ISO-8601` | UTC timestamp of SEC EDGAR financial extraction |

---

## 5. Methodology & Extraction Protocol

1. **Automated Extraction:** Data is extracted via [`../../scrapers/mine_sec_edgar_semiconductor_rd.py`](../../scrapers/mine_sec_edgar_semiconductor_rd.py) with full cryptographic provenance (source URLs, document accession numbers, commit SHAs, and SHA256 checksums).
2. **Standardization & Caching:** Raw files and API manifests are cached locally under `data/scrapers/.cache/` to ensure offline deterministic reproduction.
3. **Statistical Modeling & Aggregation:** Aggregations, regressions, and distributions are computed with double-precision floating-point arithmetic.
4. **Publication Rendering:** Plots are generated using standalone Python scripts with Matplotlib adhering strictly to Architecture 2.0 CMOS visual guidelines (declared typography, 300 DPI raster, colorblind-safe palettes, zero label collisions).

---

## 6. Primary Source Provenance & Literature Receipts

1. U.S. Securities and Exchange Commission (SEC) EDGAR 10-K & 20-F Filings (CIK 0001045810, 0000002488, 0000050863, 0000804328, 0001730168, 0000320193, 0001046179), 2000–2026.
2. International Business Strategies (IBS Handel Jones Reports), 2000–2025; Arm Holdings plc Form 424B4, 2023.

---

## 7. Reproduction Guide & Commands

To reproduce this study's dataset from raw sources and regenerate all vector/raster figures:

```bash
# 1. Navigate to this study directory
cd data/studies/07-foundry-cost-and-rd-wall

# 2. (Optional) Re-run the automated scraper from raw upstream documents
python3 ../../scrapers/mine_sec_edgar_semiconductor_rd.py

# 3. Regenerate all publication-quality vector and raster figures
python3 plot_foundry_wafer_cost_and_rd_wall.py
```

---

## 8. Slide Deck & Keynote Talking Points

- 💸 **The Free Lunch is Over:** Cost per transistor has officially inverted at 2nm; node shrinks no longer guarantee cheaper chips.
- 🚧 **The $725M Barrier:** Designing a leading 2nm SoC costs $725M. Without AI-driven autonomous design, startup innovation is suffocated.
- 📊 **25%+ R&D Redline:** Semiconductor firms spend up to a third of revenue purely on R&D to keep pace with manual design complexity.

---

## 9. Citation Information

If you use this dataset, methodology, or figure in your research, course materials, or talks, please cite:

### BibTeX:
```bibtex
@misc{arch2_foundry_economics_2026,
  author       = {Reddi, Vijay Janapa and Contributors},
  title        = {Semiconductor Corporate R&D Escalation and Foundry Node Cost Inversion Dataset (2000--2026)},
  howpublished = {\url{https://arch2.mlsysbook.ai}},
  year         = {2026},
  url          = {https://arch2.mlsysbook.ai}
}
```

### Plain Text:
> Reddi, V. J., et al. (2026). *Foundry Wafer Cost Inversion vs. Corporate R&D Spend (SEC EDGAR 10-K)*. In **Architecture 2.0: Autonomous AI, Accelerators, and the Future of Silicon Design**. Harvard University & Edge AI Foundation. Available at: `https://arch2.mlsysbook.ai`
