# The AI Benchmark Mirage vs. Physical Silicon AST Complexity

**Study ID:** `02-ast-complexity-cliff`
**Monograph Reference:** *Architecture 2.0: Autonomous AI, Accelerators, and the Future of Silicon Design*
**Canonical Directory:** `data/studies/02-ast-complexity-cliff/`

---

## 1. Executive Summary & Core Research Question

> **Research Question:** How large is the gap between synthetic hardware benchmarks evaluated by AI models and production physical silicon designs?

Measures the structural scale and hierarchy disparity between academic AI hardware generation benchmarks (VerilogEval, RTLLM, VeriGen) and production open-source silicon IP (OpenTitan, SonicBOOM, SweRV, CV32E40P, BlackParrot).

---

## 2. Visual Exhibits & Figure Gallery

![The AI Benchmark Mirage vs. Physical Silicon AST Complexity](./fig_ast_complexity_cliff.png)



### Packaged Visual Asset Twins:
- **High-Resolution Raster (300 DPI):** [`fig_ast_complexity_cliff.png`](./fig_ast_complexity_cliff.png)
- **Vector PDF (LaTeX / Publication):** [`fig_ast_complexity_cliff.pdf`](./fig_ast_complexity_cliff.pdf)
- **Vector SVG (Web / Interactive):** [`fig_ast_complexity_cliff.svg`](./fig_ast_complexity_cliff.svg)

---

## 3. Core Architectural Insights & Empirical Findings

- **The 175x AST Node Gap:** AI benchmarks evaluate leaf modules with a median of 73 AST nodes (<100 LoC), whereas production silicon IP modules average 12,800 AST nodes (4,400 LoC) and SoC top-levels exceed 448,000 AST nodes (175.3x structural disparity).
- **The CDC & Clock Void:** 99.7% of AI benchmark circuits are single-clock with 0.0 clock-domain crossings (CDCs). Real silicon IP operates across 2–12 asynchronous clock domains and features up to 86 CDC synchronizers.
- **Hierarchy Flattening:** AI benchmarks feature 100% flat (depth=1) leaf expressions, whereas production processors have 5–10 levels of nested structural submodule hierarchy.

---

## 4. Packaged Datasets & Data Schema

### Primary Data Receipts:
- [`hardware_ast_complexity_gap.csv`](./hardware_ast_complexity_gap.csv)

### Data Dictionary:
| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `design_name` | `string` | Module or circuit name (e.g. fsm_shift_reg, boom_core, opentitan_top) |
| `corpus_category` | `string` | Corpus class ('AI Synthetic Benchmark' vs. 'Production Silicon RTL') |
| `clean_loc` | `integer` | Clean lines of Verilog/SystemVerilog code (excluding comments/blanks) |
| `ast_nodes` | `integer` | Abstract syntax tree node count parsed via Pyverilog / CIRCT |
| `hierarchy_depth` | `integer` | Maximum structural submodule nesting depth |
| `clock_domains` | `integer` | Number of distinct asynchronous clock domains |
| `cdc_crossings` | `integer` | Number of clock-domain crossing (CDC) synchronizers |
| `sequential_state_bits` | `integer` | Total register/flip-flop sequential state bit count (log2 state space) |
| `source_repo` | `string` | Upstream GitHub repository name and commit SHA |
| `extraction_timestamp` | `ISO-8601` | UTC timestamp of automated AST analysis |

---

## 5. Methodology & Extraction Protocol

1. **Automated Extraction:** Data is extracted via [`../../scrapers/mine_hardware_ast_complexity.py`](../../scrapers/mine_hardware_ast_complexity.py) with full cryptographic provenance (source URLs, document accession numbers, commit SHAs, and SHA256 checksums).
2. **Standardization & Caching:** Raw files and API manifests are cached locally under `data/scrapers/.cache/` to ensure offline deterministic reproduction.
3. **Statistical Modeling & Aggregation:** Aggregations, regressions, and distributions are computed with double-precision floating-point arithmetic.
4. **Publication Rendering:** Plots are generated using standalone Python scripts with Matplotlib adhering strictly to Architecture 2.0 CMOS visual guidelines (declared typography, 300 DPI raster, colorblind-safe palettes, zero label collisions).

---

## 6. Primary Source Provenance & Literature Receipts

1. Liu et al., *VerilogEval: Evaluating Large Language Models for Verilog Code Generation*, IEEE/ACM ICCAD 2023.
2. Lu et al., *RTLLM: An Open-Source Benchmark for RTL Generation Using LLMs*, IEEE TCAD 2024.
3. lowRISC OpenTitan Earl Grey SoC (commit 2f4e8b91a0), 2026.
4. UC Berkeley SonicBOOM RISC-V Out-of-Order Core (commit 4e7d3a82c1), 2026.

---

## 7. Reproduction Guide & Commands

To reproduce this study's dataset from raw sources and regenerate all vector/raster figures:

```bash
# 1. Navigate to this study directory
cd data/studies/02-ast-complexity-cliff

# 2. (Optional) Re-run the automated scraper from raw upstream documents
python3 ../../scrapers/mine_hardware_ast_complexity.py

# 3. Regenerate all publication-quality vector and raster figures
python3 plot_ast_complexity_cliff.py
```

---

## 8. Slide Deck & Keynote Talking Points

- 🎯 **The 175x Reality Gap:** Today's AI benchmarks test toy arithmetic snippets, not real hardware. Production chips are 175x larger in AST scale.
- ⚡ **The Missing Clocks:** 99.7% of LLM benchmarks test single-clock designs with zero CDCs; real silicon requires multi-clock asynchronous synchronization.
- 🏗️ **Hierarchy Matters:** AI models must generate deep, multi-level structural hierarchies rather than flat 50-line leaf functions.

---

## 9. Citation Information

If you use this dataset, methodology, or figure in your research, course materials, or talks, please cite:

### BibTeX:
```bibtex
@misc{arch2_ast_complexity_gap_2026,
  author       = {Reddi, Vijay Janapa and Contributors},
  title        = {Physical Silicon AST and Clock-Domain Crossing Complexity Gap Dataset},
  howpublished = {\url{https://arch2.mlsysbook.ai}},
  year         = {2026},
  url          = {https://arch2.mlsysbook.ai}
}
```

### Plain Text:
> Reddi, V. J., et al. (2026). *The AI Benchmark Mirage vs. Physical Silicon AST Complexity*. In **Architecture 2.0: Autonomous AI, Accelerators, and the Future of Silicon Design**. Harvard University & Edge AI Foundation. Available at: `https://arch2.mlsysbook.ai`
