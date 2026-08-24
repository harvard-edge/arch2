# Open Silicon Democratization & The 3,000× Cost Collapse (1981–2026)

**Study ID:** `04-tinytapeout-democratization`
**Reference:** *Architecture 2.0: Principles of AI-Native System and Chip Design*
**Website:** [https://arch2.mlsysbook.ai](https://arch2.mlsysbook.ai)

---

## 1. Overview & Research Question

> **Research Question:** How significantly have multi-project wafer (MPW) multiplexing and open PDKs lowered the financial and educational barriers to physical silicon fabrication?

This study analyzes 4,780+ custom silicon designs submitted across 27 Tiny Tapeout and Open MPW shuttles (2022–2026), tracing 45 years of historical fabrication entry costs from 1981 to 2026.

---

## 2. Visual Exhibits

![Open Silicon Democratization and 3,000x Prototyping Cost Collapse](./fig-tinytapeout-democratization-census.png)

- **Raster (300 DPI):** [`fig-tinytapeout-democratization-census.png`](./fig-tinytapeout-democratization-census.png)
- **Vector PDF:** [`fig-tinytapeout-democratization-census.pdf`](./fig-tinytapeout-democratization-census.pdf)
- **Vector SVG:** [`fig-tinytapeout-democratization-census.svg`](./fig-tinytapeout-democratization-census.svg)

---

## 3. Empirical Findings

- **Fabrication Cost Collapse:** Prototyping entry cost fell from $150,000 for dedicated mask runs (1981 MOSIS) to $50–$100 for fine-grain multiplexed tile slots on open PDKs (Tiny Tapeout), establishing a **$3,000\times$ entry cost collapse**.
- **Census Volume:** 4,780+ designs fabricated across 27 shuttle rounds spanning SkyWater SKY130 (130nm CMOS), IHP SG13G2 (130nm BiCMOS), and GlobalFoundries GF180MCU.
- **Participant Profiles:** 34% undergraduate students, 21% graduate researchers, 15% high school students, 18% open-source hobbyists, and 12% academic/startup teams.

---

## 4. Packaged Datasets & Schema

### Primary Data Files
- [`tinytapeout_democratization_census.csv`](./tinytapeout_democratization_census.csv)
- [`shuttle_cost_historical_collapse.csv`](./shuttle_cost_historical_collapse.csv)

### Data Dictionary
| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `shuttle_id` | `string` | Official shuttle identifier (e.g. TT01, TT04, TT08, TT-IHP-25a) |
| `pdk_technology` | `string` | Foundry process design kit (SKY130, SG13G2, GF180MCU) |
| `tapeout_year` | `integer` | Silicon submission year (2022–2026) |
| `total_submissions` | `integer` | Verified design blocks accepted on multi-project wafer |
| `undergrad_pct` | `float` | Percentage of designs submitted by undergraduate students |
| `high_school_pct` | `float` | Percentage of designs submitted by secondary students |
| `entry_cost_usd` | `float` | Direct participant cost per fabricated hardware block |

---

## 5. Primary Sources

1. Tiny Tapeout, *Public Multi-Project Wafer Submission Manifests (TT01–TT26c)*, 2022–2026.
2. Efabless Corporation, *Open MPW Shuttle Archives and ChipIgnite Data*, 2020–2026.
3. DARPA / MOSIS, *Historical Multi-Project Wafer Service Pricing Archives (1981–2000)*.

---

## 6. Reproduction

```bash
cd data/studies/04-tinytapeout-democratization
python3 plot_tinytapeout_democratization.py
```

---

## 7. Citation

```bibtex
@book{arch2_2026,
  author    = {Reddi, Vijay Janapa},
  title     = {Architecture 2.0: Principles of AI-Native System and Chip Design},
  year      = {2026},
  publisher = {Morgan \& Claypool},
  url       = {https://arch2.mlsysbook.ai}
}
```

> Reddi, V. J. (2026). *Architecture 2.0: Principles of AI-Native System and Chip Design*. Morgan & Claypool. Available at: `https://arch2.mlsysbook.ai`
