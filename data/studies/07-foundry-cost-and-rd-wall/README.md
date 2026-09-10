# Foundry Wafer Cost Inversion vs. Corporate R&D Spend (SEC EDGAR 10-K)

**Study ID:** `07-foundry-cost-and-rd-wall`
**Reference:** *Architecture 2.0: Principles of AI-Native System and Chip Design*
**Website:** [https://arch2.mlsysbook.ai](https://arch2.mlsysbook.ai)

---

## 1. Overview & Research Question

> **Research Question:** How significantly have leading-edge foundry wafer prices and mask set costs escalated from 90nm to 2nm, and how is this reflected in corporate semiconductor R&D expenditures?

This study tracks 25 years of audited financial 10-K filings across 7 major semiconductor corporations ($N=189$ annual records) alongside TSMC, IBS, and Gartner foundry contract pricing.

---

## 2. Visual Exhibits

![Foundry Wafer Cost Inversion vs. Corporate R&D Spend](./fig-foundry-wafer-cost-and-rd-wall.png)

- **Raster (300 DPI):** [`fig-foundry-wafer-cost-and-rd-wall.png`](./fig-foundry-wafer-cost-and-rd-wall.png)
- **Vector PDF:** [`fig-foundry-wafer-cost-and-rd-wall.pdf`](./fig-foundry-wafer-cost-and-rd-wall.pdf)
- **Vector SVG:** [`fig-foundry-wafer-cost-and-rd-wall.svg`](./fig-foundry-wafer-cost-and-rd-wall.svg)

---

## 3. Empirical Findings

- **Transistor Cost Inversion:** Cost per 100M transistors fell from $2.09 (90nm) to $0.28 (28nm planar sweet spot), but stalled at 7nm ($0.152) and inverted upwards at 2nm ($>\$0.152$), as 300mm wafer prices surged **$16.2\times$** ($1,850 to $30,000) and mask sets reached $60M.
- **SoC Design Costs:** Leading 2nm SoC design costs reached **$725M**, with software development, verification, and IP qualification consuming 71% ($514.8M) of the total budget (Arm Holdings plc Form 424B4 / IBS).
- **Corporate R&D Growth:** Audited annual R&D spend surged across the industry: NVIDIA expanded from $81.6M in FY2000 to $18.5B in FY2025 ($227\times$ audited surge) and $22.8B in FY2026 guidance ($278\times$), with semiconductor firms allocating up to 32% of revenue to R&D.

---

## 4. Packaged Datasets & Schema

### Primary Data Files
- [`sec_edgar_semiconductor_rd_economics.csv`](./sec_edgar_semiconductor_rd_economics.csv) (audited financial filings 2000–2025 and 2026 guidance estimates)
- [`foundry_node_economics_timeline.csv`](./foundry_node_economics_timeline.csv) (process node wafer pricing, transistor density, and SoC design costs from 90nm to 2nm)

### Data Dictionaries

#### Corporate R&D Financials (`sec_edgar_semiconductor_rd_economics.csv`)
| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `fiscal_year` | `integer` | Fiscal accounting year (2000–2026) |
| `company_ticker` | `string` | US stock exchange ticker symbol |
| `company_name` | `string` | Corporation name (NVIDIA, AMD, Intel, TSMC, Broadcom, etc.) |
| `annual_revenue_usd_billion`| `float` | Audited GAAP net revenue in billions USD (2000-2025; 2026 guidance) |
| `rd_expense_usd_billion` | `float` | Audited research and development expense in billions USD |
| `rd_intensity_pct` | `float` | Percentage of annual revenue reinvested into R&D |
| `leading_process_node_nm` | `integer` | Leading process node in volume production (nm) |
| `sec_form` | `string` | SEC form type (10-K or 20-F) |
| `sec_accession_number` | `string` | SEC EDGAR formal filing accession number |
| `filing_url` | `string` | Direct URL to SEC EDGAR filing |
| `source_type` | `string` | Categorization (Audited SEC 10-K vs. Consensus Forecast) |

#### Foundry Node Economics (`foundry_node_economics_timeline.csv`)
| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `process_node` | `string` | Semiconductor process node (e.g. 90 nm, 28 nm, 2 nm) |
| `introduction_year` | `integer` | Year of commercial volume introduction |
| `wafer_cost_usd` | `float` | Average contract price per 300mm wafer (USD) |
| `transistor_density_m_tr_mm2` | `float` | Logic transistor density (Million Transistors per mm²) |
| `cost_per_100m_transistors_usd` | `float` | Normalized cost per 100M transistors (USD) |
| `design_cost_per_soc_usd_million` | `float` | Total estimated leading-edge SoC design cost ($M USD) |
| `source_citation` | `string` | Literature and disclosure sources (TSMC IEDM, IBS, Arm) |

---

## 5. Primary Sources

1. US Securities and Exchange Commission (SEC), *EDGAR 10-K and 20-F Annual Filings (2000–2026)*.
2. International Business Strategies (IBS), *Semiconductor Node Cost Models (Handel Jones)*, 2004–2025.
3. Arm Holdings plc, *Form 424B4 Prospectus*, US SEC, September 2023.
4. Semiconductor Industry Association (SIA), *Chip Design and R&D*, 2026.

---

## 6. Reproduction

```bash
cd data/studies/07-foundry-cost-and-rd-wall
python3 plot_foundry_wafer_cost_and_rd_wall.py
```

---

## 7. Citation

```bibtex
@book{reddi2026architecture2,
  author    = {Vijay Janapa Reddi},
  title     = {Architecture 2.0: Principles of AI-Native System and Chip Design},
  year      = {2026},
  url       = {https://arch2.mlsysbook.ai}
}
```

> Vijay Janapa Reddi. *Architecture 2.0: Principles of AI-Native System and Chip Design* (2026). Available at: `https://arch2.mlsysbook.ai`
