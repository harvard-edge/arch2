# Open Silicon Democratization & The 3,000× Cost Collapse (1981–2026)

**Study ID:** `04-tinytapeout-democratization`
**Monograph Reference:** *Architecture 2.0: Autonomous AI, Accelerators, and the Future of Silicon Design*
**Canonical Directory:** `data/studies/04-tinytapeout-democratization/`

---

## 1. Executive Summary & Core Research Question

> **Research Question:** How have open-source PDKs, open EDA, and sub-tile multi-project multiplexing altered the economics and demographics of custom silicon design?

Examines the democratization of custom silicon prototyping across 27 Tiny Tapeout shuttle rounds (4,780+ designs) and quantifies the 45-year economic collapse from $150,000 mask sets to $50–$100 educational multi-project slots.

---

## 2. Visual Exhibits & Figure Gallery

![Open Silicon Democratization & The 3,000× Cost Collapse (1981–2026)](./fig-tinytapeout-democratization-census.png)



### Packaged Visual Asset Twins:
- **High-Resolution Raster (300 DPI):** [`fig-tinytapeout-democratization-census.png`](./fig-tinytapeout-democratization-census.png)
- **Vector PDF (LaTeX / Publication):** [`fig-tinytapeout-democratization-census.pdf`](./fig-tinytapeout-democratization-census.pdf)
- **Vector SVG (Web / Interactive):** [`fig-tinytapeout-democratization-census.svg`](./fig-tinytapeout-democratization-census.svg)

---

## 3. Core Architectural Insights & Empirical Findings

- **The 3,000x Prototyping Cost Collapse:** Custom silicon entry cost collapsed from $150,000 dedicated mask runs (1981 MOSIS) and $16,000–$85,000 commercial MPWs to $0 (Google Open MPW) and $50–$100 per slot in Tiny Tapeout.
- **Demographic Transformation:** Silicon design is no longer restricted to corporate fabless giants: 34% of taped-out designs originate from undergraduate courses, 21% from graduate students, 16% from open-source makers, and 15% from high school students (Hack Club).
- **Domain Diversification:** Shuttles have matured from toy digital logic (74% in TT01) to custom RISC-V CPUs (5.0%), systolic AI accelerators (4.8%), DSP synthesizers (3.3%), and 250 GHz BiCMOS RF designs (4.1%).

---

## 4. Packaged Datasets & Data Schema

### Primary Data Receipts:
- [`tinytapeout_democratization_census.csv`](./tinytapeout_democratization_census.csv)
- [`shuttle_cost_historical_collapse.csv`](./shuttle_cost_historical_collapse.csv)

### Data Dictionary:
| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `shuttle_id` | `string` | Shuttle round identifier (e.g. TT01, TT04, TT-IHP-25a, TT-SKY-26c) |
| `process_node` | `string` | Process technology node (SKY130, IHP SG13G2, GF180MCU) |
| `submission_deadline` | `date` | Shuttle closing deadline (YYYY-MM-DD) |
| `total_designs_submitted` | `integer` | Count of successfully routed and verified designs |
| `cumulative_designs` | `integer` | Cumulative design count across all historical shuttles |
| `undergrad_student_share_pct` | `float` | Share of submissions from undergraduate courses |
| `high_school_student_share_pct` | `float` | Share of submissions from K-12 / high school students |
| `maker_hobbyist_share_pct` | `float` | Share of submissions from open-source makers / demoscene |
| `cost_per_slot_usd` | `float` | Participant entry cost per design slot (USD) |
| `source_manifest_url` | `string` | Tiny Tapeout public API manifest endpoint |
| `extraction_timestamp` | `ISO-8601` | UTC timestamp of shuttle census extraction |

---

## 5. Methodology & Extraction Protocol

1. **Automated Extraction:** Data is extracted via [`../../scrapers/scrape_tinytapeout_census.py`](../../scrapers/scrape_tinytapeout_census.py) with full cryptographic provenance (source URLs, document accession numbers, commit SHAs, and SHA256 checksums).
2. **Standardization & Caching:** Raw files and API manifests are cached locally under `data/scrapers/.cache/` to ensure offline deterministic reproduction.
3. **Statistical Modeling & Aggregation:** Aggregations, regressions, and distributions are computed with double-precision floating-point arithmetic.
4. **Publication Rendering:** Plots are generated using standalone Python scripts with Matplotlib adhering strictly to Architecture 2.0 CMOS visual guidelines (declared typography, 300 DPI raster, colorblind-safe palettes, zero label collisions).

---

## 6. Primary Source Provenance & Literature Receipts

1. Tiny Tapeout Public API Submission Archives (TT01–TT26c), 2022–2026.
2. Efabless Open MPW & Google Sponsored Shuttle Manifests, 2020–2026.
3. Cohen & Tyree, *The MOSIS Service*, IEEE Transactions 1982; Pina, *MOSIS History*, 2001.

---

## 7. Reproduction Guide & Commands

To reproduce this study's dataset from raw sources and regenerate all vector/raster figures:

```bash
# 1. Navigate to this study directory
cd data/studies/04-tinytapeout-democratization

# 2. (Optional) Re-run the automated scraper from raw upstream documents
python3 ../../scrapers/scrape_tinytapeout_census.py

# 3. Regenerate all publication-quality vector and raster figures
python3 plot_tinytapeout_democratization.py
```

---

## 8. Slide Deck & Keynote Talking Points

- 🌍 **Democratizing Silicon:** Over 4,780 custom chips have been taped out by students and makers for $50–$100 per design.
- 📉 **3,000x Cost Drop:** The barrier to physical silicon has fallen from $150k dedicated mask runs to the price of a textbook.
- 🎓 **Undergrads Tape Out:** 34% of designs come from undergraduate courses; students now leave college with physical silicon tapeout experience.

---

## 9. Citation Information

If you use this dataset, methodology, or figure in your research, course materials, or talks, please cite:

### BibTeX:
```bibtex
@misc{arch2_tinytapeout_census_2026,
  author       = {Reddi, Vijay Janapa and Contributors},
  title        = {Open Silicon Democratization and 45-Year Fabrication Cost Collapse Census},
  howpublished = {\url{https://arch2.mlsysbook.ai}},
  year         = {2026},
  url          = {https://arch2.mlsysbook.ai}
}
```

### Plain Text:
> Reddi, V. J., et al. (2026). *Open Silicon Democratization & The 3,000× Cost Collapse (1981–2026)*. In **Architecture 2.0: Autonomous AI, Accelerators, and the Future of Silicon Design**. Harvard University & Edge AI Foundation. Available at: `https://arch2.mlsysbook.ai`
