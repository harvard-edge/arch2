# Provenance — Study 02, RTL Source Complexity

**Evidence class:** Measured, fully reproducible
**Dataset status:** Verified
**Figure status:** Verified, no hardcoded values
**Last independently verified:** 2026-09-09

## The claim this study supports

The RTL used to benchmark AI hardware generation is an order of magnitude simpler
than production RTL, and structurally flat where production designs are deeply
hierarchical. A pass rate on VerilogEval or RTLLM therefore does not predict
behavior on real designs.

## Where the data comes from

Six open-source repositories, cloned at pinned commits and parsed with a
SystemVerilog front end. Two are AI hardware benchmarks, four are
production-oriented open silicon.

| Corpus | Category | Repository | Pinned commit |
| --- | --- | --- | --- |
| VerilogEval | Benchmark | NVlabs/verilog-eval | `c498220d0a52248f8e3fdffe279075215bde2da6` |
| RTLLM | Benchmark | hkust-zhiyao/RTLLM | `51ed553d0ffd32797a1a0a13e051656bf302c81f` |
| OpenTitan | Production | lowRISC/opentitan | `e3f3234aa3772760cdf40e79a8ae4471b6b02213` |
| CV32E40P | Production | openhwgroup/cv32e40p | `6033d2b1be3295ec774d17ac4cf226faacfdeb08` |
| VeeR EL2 | Production | chipsalliance/Cores-SweRV | `d04b1c7ae675a63dc4307cacfd10547ec937b928` |
| BlackParrot | Production | black-parrot/black-parrot | `f91010f654a5dfd00f83dbe25dbda482218d540b` |

Per-row provenance columns: `repository_url`, `repository_commit`, `source_path`,
`source_sha256`. Every one of the 1,513 module rows records the exact file it was
parsed from and that file's content hash.

## How it was measured

```bash
pip install -r data/studies/02-ast-complexity-cliff/requirements.txt
python3 data/scrapers/mine_hardware_ast_complexity_real.py
```

Cold-clones all six corpora at their pinned commits and parses every module
declaration with pyslang 11.0.0, counting concrete syntax nodes, syntax depth,
instantiation edges and clock-like event signals. No EDA license, no container, and
no network access beyond the six clones. Runs in roughly eight minutes.

## What is verified, and how

Recomputed from the raw CSV on 2026-09-09:

| Quantity | Claimed | Recomputed |
| --- | ---: | ---: |
| Modules parsed | 1,513 | 1,513 |
| Benchmark median syntax nodes | 168 | 168 |
| Production median syntax nodes | 1,125 | 1,125 |
| Ratio | 6.70x | 6.6964x |

All six pinned commits were resolved against the GitHub API on 2026-09-09 and
return HTTP 200 (`chipsalliance/Cores-SweRV` returns 301, a repository rename, and
resolves). The measurement reproduces byte-for-byte across all 1,513 rows except
`extraction_timestamp`, verified on Python 3.11.15 against a run recorded under
3.12.13.

Sensitivity checks narrow but do not eliminate the gap: 4.77x restricted to
diagnostic-free files, 4.27x under equal repository weighting.

## What is NOT verified

Nothing material. This is the only study in the set with no open defect.

## Known defects

None. This study replaced a withdrawn predecessor that claimed a 175.3x gap from
hand-typed literal tables and placeholder commit hashes. The direction of that claim
survived; the magnitude was overstated by more than an order of magnitude.

## Files

| File | Role |
| --- | --- |
| `hardware_ast_complexity_measured.csv` | Primary receipt, 1,513 module rows |
| `hardware_ast_complexity_measured_sources.csv` | The six corpora and their commits |
| `hardware_ast_complexity_measured_summary.json` | Derived aggregates |
| `plot_ast_complexity_measured.py` | Figure generator, fully data-driven |
| `REPRODUCE.md` | Step-by-step reproduction |
| `requirements.txt` | Pinned dependencies |
