# The Software Porting Wall & Fixed-Silicon Software Dividend (2018–2026)

**Study ID:** `03-mlperf-software-dividend`
**Reference:** *Architecture 2.0: Principles of AI-Native System and Chip Design*
**Website:** [https://arch2.mlsysbook.ai](https://arch2.mlsysbook.ai)

---

## 1. Overview & Research Question

> **Research Question:** How much performance improvement comes from software stack optimization on fixed hardware, and how rapidly are custom handwritten kernels proliferating?

This study tracks longitudinal throughput on fixed hardware platforms across 8 years of MLCommons MLPerf benchmarks, alongside source code metrics across leading open-source LLM inference engines.

---

## 2. Visual Exhibits

![Fixed-Silicon Software Dividend & Software Porting Wall](./mlperf_software_dividend_extended_master.png)

- **Raster (300 DPI):** [`mlperf_software_dividend_extended_master.png`](./mlperf_software_dividend_extended_master.png)
- **Vector PDF:** [`mlperf_software_dividend_extended_master.pdf`](./mlperf_software_dividend_extended_master.pdf)
- **Vector SVG:** [`mlperf_software_dividend_extended_master.svg`](./mlperf_software_dividend_extended_master.svg)

---

## 3. Empirical Findings

- **In-Place Software Dividend:** On identical, frozen physical silicon, mature compiler and runtime optimizations deliver substantial throughput gains: NVIDIA V100 gained **$3.82\times$** over 19 months (ResNet-50), A100 gained **$2.69\times$** over 23 months (BERT-Large), Google TPU v4 gained **$1.50\times$** over 12 months, and H100 gained **$1.48\times$** over 36 months.
- **Kernel Code Proliferation:** Custom handwritten CUDA/Triton/CUTLASS kernel code across serving engines expanded **$82\times$** in 36 months (TensorRT-LLM reached 341.8k LOC in 2026).
- **Template Complexity:** NVIDIA CUTLASS architecture template code grew $48.7\times$ (4.2k to 207.7k LOC), while inline PTX assembly expanded $60.4\times$.

---

## 4. Packaged Datasets & Schema

### Primary Data Files
- [`mlperf_longitudinal_software_dividend.csv`](./mlperf_longitudinal_software_dividend.csv)
- [`inference_kernel_fragmentation.csv`](./inference_kernel_fragmentation.csv)

### Data Dictionary
| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `hardware_platform` | `string` | Target silicon architecture (NVIDIA V100, A100, H100, TPU v4, MI300X) |
| `mlperf_round` | `string` | MLCommons official submission round identifier (e.g. v0.5, v2.0, v5.1) |
| `benchmark_workload` | `string` | Standardized workload task (ResNet-50, BERT-Large, Llama-70B) |
| `software_stack_summary` | `string` | Key runtime and compiler versions (CUDA, cuDNN, PyTorch, Triton) |
| `metric_value` | `float` | Official primary metric (Time to train in minutes or tokens/sec) |
| `software_speedup_factor`| `float` | In-place speedup normalized to debut round baseline ($1.0\times$) |
| `mlperf_submission_id` | `string` | Official MLCommons submission ID with audit verification |

---

## 5. Primary Sources

1. MLCommons, *MLPerf Training and Inference Benchmark Results Repository* (Rounds v0.5 through v5.1), 2018–2026.
2. NVIDIA, *CUTLASS: Fast Linear Algebra in CUDA C++ Repository*, 2019–2026.
3. OpenAI, *Triton Language and Compiler Repository*, 2021–2026.
4. vLLM, TensorRT-LLM, and SGLang Open-Source Repositories, 2023–2026.

---

## 6. Reproduction

```bash
cd data/studies/03-mlperf-software-dividend
python3 plot_mlperf_software_dividend_extended.py
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
