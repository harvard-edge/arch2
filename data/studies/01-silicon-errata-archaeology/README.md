# Real-World Silicon Errata & Defect Archaeology (2016–2026)

**Study ID:** `01-silicon-errata-archaeology`
**Monograph Reference:** *Architecture 2.0: Autonomous AI, Accelerators, and the Future of Silicon Design*
**Canonical Directory:** `data/studies/01-silicon-errata-archaeology/`

---

## 1. Executive Summary & Core Research Question

> **Research Question:** Where do actual hardware bugs occur in production commercial silicon, and how do they resolve across the processor stepping lifecycle?

Mines and classifies 1,771 itemized hardware errata across 19 commercial Intel and AMD CPU families, exposing the 'ALU Fallacy' (<1.8% integer ALU bugs vs. >93% memory/seam escapes) and proving the stepping decay half-life (t_1/2 ≈ 0.62 steppings).

---

## 2. Visual Exhibits & Figure Gallery

![Real-World Silicon Errata & Defect Archaeology (2016–2026)](./fig-errata-subsystem-sunburst-and-decay.png)



### Packaged Visual Asset Twins:
- **High-Resolution Raster (300 DPI):** [`fig-errata-subsystem-sunburst-and-decay.png`](./fig-errata-subsystem-sunburst-and-decay.png)
- **Vector PDF (LaTeX / Publication):** [`fig-errata-subsystem-sunburst-and-decay.pdf`](./fig-errata-subsystem-sunburst-and-decay.pdf)
- **Vector SVG (Web / Interactive):** [`fig-errata-subsystem-sunburst-and-decay.svg`](./fig-errata-subsystem-sunburst-and-decay.svg)

---

## 3. Core Architectural Insights & Empirical Findings

- **The ALU Fallacy:** Pure integer ALU bugs account for <1.8% of post-silicon escapes (all arithmetic/FP/vector = 6.8%). Over 93.2% of defects concentrate at subsystem integration seams: Memory Hierarchy (31.3%), PCIe/CXL Platform IO (16.5%), Virtualization/MMU (16.1%), Debug/PMU (13.9%), and Power/DVFS (6.6%).
- **Errata Discovery Half-Life:** 66.4% of lifetime defects emerge on initial A0 silicon, decaying exponentially across subsequent revisions (lambda = 1.12, t_1/2 ≈ 0.62 steppings). Mature volume ramp steppings contribute <8.8% of new errata.
- **Containment Economics:** Zero defects in production volume steppings are fixed via physical mask respins due to escalating mask costs ($180M at 2nm). Instead, 66.2% are documented as operational risk waivers ('No Fix') and 33.8% are mitigated via microcode chicken-bits (18.9%) and OS workarounds (14.9%).

---

## 4. Packaged Datasets & Data Schema

### Primary Data Receipts:
- [`granular_processor_errata_taxonomy.csv`](./granular_processor_errata_taxonomy.csv)
- [`hardware_errata_longitudinal_summary.csv`](./hardware_errata_longitudinal_summary.csv)

### Data Dictionary:
| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `processor_name` | `string` | Commercial processor family name (e.g. Sapphire Rapids, Zen 4 Genoa) |
| `vendor` | `string` | Hardware vendor ('Intel' or 'AMD') |
| `launch_year` | `integer` | Year of commercial silicon launch (2016–2026) |
| `erratum_id` | `string` | Vendor defect identifier (e.g. SKX102, BDX88, SPR042, ZN4-1305) |
| `title` | `string` | Official technical title from specification update document |
| `subsystem_category` | `string` | Microarchitectural category (Memory Hierarchy, PCIe/CXL, Virtualization/MMU, Debug/PMU, ALU, etc.) |
| `symptom` | `string` | Observable operational failure (Silent Data Corruption, System Hang, MCE, Crash) |
| `workaround_type` | `string` | Remediation mechanism (Microcode Patch, Doc Waiver/No Fix, BIOS/Firmware, OS Flag) |
| `status` | `string` | Resolution disposition ('No Fix Planned', 'Plan Fix') |
| `source_doc_id` | `string` | Vendor specification update document identifier (e.g. 772415-022US) |
| `source_doc_url` | `string` | Canonical public download URL for specification update PDF |
| `source_doc_sha256` | `string` | Cryptographic SHA256 hash of the source PDF specification update document |
| `extraction_timestamp` | `ISO-8601` | UTC timestamp of automated document extraction |

---

## 5. Methodology & Extraction Protocol

1. **Automated Extraction:** Data is extracted via [`../../scrapers/scrape_intel_amd_errata.py`](../../scrapers/scrape_intel_amd_errata.py) with full cryptographic provenance (source URLs, document accession numbers, commit SHAs, and SHA256 checksums).
2. **Standardization & Caching:** Raw files and API manifests are cached locally under `data/scrapers/.cache/` to ensure offline deterministic reproduction.
3. **Statistical Modeling & Aggregation:** Aggregations, regressions, and distributions are computed with double-precision floating-point arithmetic.
4. **Publication Rendering:** Plots are generated using standalone Python scripts with Matplotlib adhering strictly to Architecture 2.0 CMOS visual guidelines (declared typography, 300 DPI raster, colorblind-safe palettes, zero label collisions).

---

## 6. Primary Source Provenance & Literature Receipts

1. Intel Corporation, *Intel Xeon Scalable Processor Family Specification Updates* (Broadwell-EP through Emerald Rapids, Meteor Lake, Lunar Lake, Arrow Lake, Doc IDs 334165 through 834774), 2016–2026.
2. Advanced Micro Devices (AMD), *AMD EPYC Processor Family Revision Guides* (Zen 1 Naples through Zen 5 Turin, Doc IDs 55449 through 58730), 2017–2026.

---

## 7. Reproduction Guide & Commands

To reproduce this study's dataset from raw sources and regenerate all vector/raster figures:

```bash
# 1. Navigate to this study directory
cd data/studies/01-silicon-errata-archaeology

# 2. (Optional) Re-run the automated scraper from raw upstream documents
python3 ../../scrapers/scrape_intel_amd_errata.py

# 3. Regenerate all publication-quality vector and raster figures
python3 plot_errata_subsystem_sunburst_and_decay.py
```

---

## 8. Slide Deck & Keynote Talking Points

- 🛑 **The ALU Fallacy:** Stop benchmarking hardware AI agents solely on simple ALUs and adders. Over 93% of real processor escapes live in memory coherence, PCIe queues, and power management.
- 📉 **Stepping Decay:** Two-thirds of bugs are found on A0 silicon; by volume ramp (B0), discovery drops by an order of magnitude.
- 🔧 **Chicken-Bit Reality:** Hardware bugs in volume silicon are never fixed in silicon; they are patched via microcode chicken-bits and kernel workarounds.

---

## 9. Citation Information

If you use this dataset, methodology, or figure in your research, course materials, or talks, please cite:

### BibTeX:
```bibtex
@misc{arch2_silicon_errata_2026,
  author       = {Reddi, Vijay Janapa and Contributors},
  title        = {Real-World Silicon Errata and Defect Archaeology Dataset (2016--2026)},
  howpublished = {\url{https://arch2.mlsysbook.ai}},
  year         = {2026},
  url          = {https://arch2.mlsysbook.ai}
}
```

### Plain Text:
> Reddi, V. J., et al. (2026). *Real-World Silicon Errata & Defect Archaeology (2016–2026)*. In **Architecture 2.0: Autonomous AI, Accelerators, and the Future of Silicon Design**. Harvard University & Edge AI Foundation. Available at: `https://arch2.mlsysbook.ai`
