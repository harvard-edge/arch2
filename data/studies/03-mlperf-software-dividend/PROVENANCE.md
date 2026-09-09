# Provenance — Study 03, Fixed-Silicon Software Dividend

**Evidence class:** Transcribed from published benchmark results, with citation
**Dataset status:** Verified for the headline, weak per-row linking
**Figure status:** Panel A and Panel B are hardcoded, see Known defects
**Last independently verified:** 2026-09-09

## The claim this study supports

A large fraction of realized performance arrives after tapeout. On identical, frozen
silicon, maturing software and compilers extract up to 3.82x additional throughput.
Over the same period the handwritten custom kernel code needed to obtain it grows
sharply, which is the cost side of the same phenomenon.

## Where the data comes from

Two receipts. MLCommons submission results from 2018 to 2026, and release-by-release
kernel line counts from four open-source inference engines.

| Receipt | Rows | Source |
| --- | ---: | --- |
| `mlperf_longitudinal_software_dividend.csv` | 35 | MLCommons Training and Inference rounds |
| `inference_kernel_fragmentation.csv` | 30 | vLLM, TensorRT-LLM, SGLang, TGI tagged releases |

The kernel receipt has strong provenance: every row carries `git_commit`,
`github_repo_url` and `version_tag` pointing at a specific tagged release. The
MLPerf receipt carries `submission_id` and `software_stack_version` per row.

## How it was collected

```bash
python3 data/scrapers/mine_mlperf_software_dividend.py
```

## What is verified, and how

Recomputed from the raw CSVs on 2026-09-09:

| Quantity | Claimed | Recomputed |
| --- | ---: | ---: |
| Peak in-place dividend | 3.82x | 3.82x |
| TensorRT-LLM custom kernel LOC, 2026 | 341,800 | 341,800 |
| SGLang custom kernel LOC, 2026 | 195,000 | 195,000 |

## What is NOT verified

The MLPerf throughput values have not been reconciled against MLCommons' own
published result tables. The `result_url` column points at round-level landing
pages rather than individual submissions, and those URLs currently do not resolve
because MLCommons restructured its site. Confirming any single number requires
going to the `mlcommons/training_results_*` repositories by submission id. This is
the weakest per-row provenance among the surviving studies.

## Known defects

1. **The "82x kernel proliferation" claim is not supported.** Recomputed per-engine
   growth from first to last release is vLLM 48.71x, SGLang 43.14x, TGI 23.39x,
   TensorRT-LLM 8.11x. No engine grows 82x, and 82 does not appear in the
   `custom_kernel_loc_growth_factor` column at all. The figure asserts it as an
   annotation at `plot_mlperf_software_dividend_extended.py:411`. Replace it with
   the real per-engine range, roughly 8x to 49x.
2. **The throughput trajectory panel is hardcoded.** Twelve in-script literal arrays
   at lines 66 to 79 and 243 to 244 (`v100_t`, `a100_t`, `h100_t`, `hw_base`,
   `sw_peak`) supply every plotted coordinate. The script opens the CSV but does not
   plot from it. The 3.82x endpoint happens to match the data; the curve does not
   come from it.
3. **Round-level URLs.** See "What is NOT verified" above. Replace `result_url` with
   per-submission links or drop the column and rely on `submission_id`.

## Files

| File | Role |
| --- | --- |
| `mlperf_longitudinal_software_dividend.csv` | MLPerf receipt, 35 rows |
| `inference_kernel_fragmentation.csv` | Kernel LOC receipt, 30 rows |
| `plot_mlperf_software_dividend_extended.py` | Figure generator, see defects 1 and 2 |
| `../../scrapers/mine_mlperf_software_dividend.py` | Miner |
