# Real-World Silicon Errata & Defect Archaeology (2016–2026)

**Study ID:** `01-silicon-errata-archaeology`
**Reference:** *Architecture 2.0: Principles of AI-Native System and Chip Design*
**Website:** [https://arch2.mlsysbook.ai](https://arch2.mlsysbook.ai)

---

## 1. Overview & Research Question

> **Research Question:** Where do actual hardware bugs occur in production commercial silicon, and how do they resolve across the processor stepping lifecycle?

This study classifies 1,771 itemized hardware errata across 19 commercial Intel and AMD CPU families (14nm to 3nm), measuring bug concentration across functional execution units versus subsystem interfaces.

---

## 2. Visual Exhibits

![Real-World Silicon Errata & Defect Archaeology (2016–2026)](./fig-errata-subsystem-sunburst-and-decay.png)

- **Raster (300 DPI):** [`fig-errata-subsystem-sunburst-and-decay.png`](./fig-errata-subsystem-sunburst-and-decay.png)
- **Vector PDF:** [`fig-errata-subsystem-sunburst-and-decay.pdf`](./fig-errata-subsystem-sunburst-and-decay.pdf)
- **Vector SVG:** [`fig-errata-subsystem-sunburst-and-decay.svg`](./fig-errata-subsystem-sunburst-and-decay.svg)

---

## 3. Empirical Findings

- **Subsystem Seam Concentration:** Integer ALU defects account for <1.8% of post-silicon escapes (all arithmetic/FP/vector = 6.8%). Over 93.2% of defects concentrate at subsystem integration seams: Memory Hierarchy (31.3%), PCIe/CXL Platform IO (16.5%), Virtualization/MMU (16.1%), Debug/PMU (13.9%), and Power/DVFS (6.6%).
- **Stepping Decay:** 66.4% of lifetime defects emerge on initial A0 silicon, decaying exponentially across subsequent revisions ($\lambda = 1.12$, $t_{1/2} \approx 0.62$ steppings).
- **Containment:** In production volume silicon, 66.2% of errata are documented as operational risk waivers ('No Fix') and 33.8% are mitigated via microcode chicken-bits (18.9%) and OS workarounds (14.9%). Zero defects in mass production are resolved via mask respins.

---

## 4. Packaged Datasets & Schema

### Primary Data Files
- [`granular_processor_errata_taxonomy.csv`](./granular_processor_errata_taxonomy.csv)
- [`hardware_errata_longitudinal_summary.csv`](./hardware_errata_longitudinal_summary.csv)

### Data Dictionary
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

## 5. Primary Sources

1. Intel Corporation, *Intel Xeon Scalable Processor Family Specification Updates* (Broadwell-EP through Emerald Rapids, Meteor Lake, Lunar Lake, Arrow Lake, Doc IDs 334165 through 834774), 2016–2026.
2. Advanced Micro Devices (AMD), *AMD EPYC Processor Family Revision Guides* (Zen 1 Naples through Zen 5 Turin, Doc IDs 55449 through 58730), 2017–2026.

---

## 6. Reproduction

```bash
cd data/studies/01-silicon-errata-archaeology
python3 plot_errata_subsystem_sunburst_and_decay.py
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
