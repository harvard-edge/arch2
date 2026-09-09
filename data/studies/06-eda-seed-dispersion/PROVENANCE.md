# Provenance — Study 06, Placement Seed Dispersion

**Evidence class:** Measured, we ran it
**Dataset status:** Pilot verified. A withdrawn synthetic file is still in this directory
**Figure status:** Pilot figure verified. A withdrawn figure is still in this directory
**Last independently verified:** 2026-09-09

## The claim this study supports

The physical design tools an automated loop would optimize against are not
deterministic. Holding the design and the floorplan fixed and varying only the
placement seed moves timing by several percent, so a single tool run is a sample from
a distribution rather than a measurement of a design point.

## Where the data comes from

Twenty OpenROAD runs that we executed. This is the only study in the set that is a
first-party experiment rather than a mining or transcription exercise.

| Field | Value |
| --- | --- |
| Design | GCD |
| PDK | Nangate45 |
| Flow | OpenROAD-flow-scripts, pinned at commit `8359fde` |
| Container | pinned by SHA-256 digest |
| Target | `place` |
| Runs | 20, single-threaded |
| Variable | `GPL_RANDOM_SEED` only |
| Outcome | 20 of 20 passed |

Per-run provenance columns: `floorplan_odb_sha256`, `placement_odb_sha256`,
`globalplace_json_sha256`, `detailedplace_json_sha256`, `stdout_receipt`,
`docker_returncode`, `wall_time_seconds`. Raw tool output is retained under
`raw-openroad-placement-pilot/`.

## How it was run

```bash
python3 data/scrapers/run_openroad_gcd_placement_seed_pilot.py
```

Needs Docker. Pulls the pinned ORFS image by digest and runs twenty seeds
single-threaded. Roughly twenty minutes on a laptop. Everything it touches is open
source, so this is reproducible without an EDA license.

## What is verified, and how

Recomputed from the raw CSV on 2026-09-09:

| Quantity | Claimed | Recomputed |
| --- | ---: | ---: |
| Runs, all passing | 20 | 20 |
| Distinct floorplan hashes | 1 | 1 |
| Distinct placement hashes | 20 | 20 |
| Distinct seed values | 20 | 20 |
| Instance area spread | 0.84% | 0.835% |
| Setup slack spread | 3.83% | 3.836% |

The single floorplan hash across all twenty runs is the control that makes this
result meaningful: it proves the twenty runs really did start from an identical
placement problem, and that only the seed varied.

## What is NOT verified

The twenty Docker runs have not been re-executed from scratch in this audit. The
retained raw JSON and stdout under `raw-openroad-placement-pilot/` were inspected and
match the CSV.

The result is one design on one PDK at one flow stage. It demonstrates that
nondeterminism exists and bounds it for this case. It does not establish a general
magnitude across designs, nodes, or full flows, and should not be cited as if it did.

## Known defects

1. **Withdrawn synthetic data is still in this directory.** The September 2026
   quarantine removed `eda_seed_dispersion_qor_lottery.csv` from
   `data/source-receipts/` and from `www/`, but not from here. This directory still
   contains that CSV, its generator output `eda_seed_dispersion_distribution.{png,svg,pdf}`,
   and `plot_eda_seed_dispersion_distribution.py`. That file was produced by a
   `_gaussian_noise()` helper while its header named pinned OpenROAD, Yosys and
   OpenSTA versions that were never invoked. **It must be removed from this study
   package.** Any claim of "3.2% to 7.8% seed dispersion" or a "±2.22% 1-sigma"
   figure traces to that file and must not be used. The measured numbers are 0.84%
   and 3.83%, above.
2. **`data/validate_provenance.py` does not scan `data/studies/`.** That is why
   defect 1 survived the quarantine. See the repository-level provenance README.

## Files

| File | Role |
| --- | --- |
| `openroad_gcd_placement_seed_pilot.csv` | Primary receipt, 20 measured runs |
| `openroad_gcd_placement_seed_pilot_summary.json` | Derived aggregates |
| `raw-openroad-placement-pilot/` | Retained raw tool output |
| `plot_openroad_gcd_placement_seed_pilot.py` | Figure generator, fully data-driven |
| `MEASURED-PILOT.md` | Run notes |
| `eda_seed_dispersion_qor_lottery.csv` | **WITHDRAWN, remove, see defect 1** |
| `plot_eda_seed_dispersion_distribution.py` | **WITHDRAWN, remove, see defect 1** |
