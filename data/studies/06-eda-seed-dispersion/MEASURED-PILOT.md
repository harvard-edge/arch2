# Executed OpenROAD placement-seed pilot

This pilot replaces an earlier seed-dispersion file whose values came from a
noise function rather than a tool run. That file and its generator were deleted
on 29 September 2026.

## Evidence status

- All 20 runs execute the ORFS `gcd` design on Nangate45 from the exact ORFS
  commit and official container digest recorded in
  `openroad_gcd_placement_seed_pilot_summary.json`.
- The design and constraint source identifiers, ORFS commit, container digest, host architecture,
  thread count, fixed seeds, varied global-placement seed, tool return code,
  elapsed time, stage error counts, pre-placement database hash, placement
  database hash, and raw-stage JSON hashes are retained.
- Each seed has its complete stdout plus byte-for-byte copies of the ORFS
  global-placement and detailed-placement metric JSON in
  `raw-openroad-placement-pilot/`.
- Runs are serial and single-threaded. Only `GPL_RANDOM_SEED` changes from 1
  through 20; `GRT_SEED` and `OR_SEED` remain 1.
- All 20 rows record the same `2_floorplan.odb` input hash and distinct
  `3_place.odb` output hashes. The databases themselves are not packaged in
  this release; the recorded hashes cannot be independently checked against
  those original database files. Reproduction must rebuild the inputs from
  the pinned sources.

## Current measured result

All 20 placement runs complete with zero reported stage errors. At detailed
placement, instance area ranges from 825.664 to 832.580 µm² around a median of
827.393 µm², a peak-to-peak span of 0.84% of the median. Estimated setup WNS
ranges from -159.114 to -153.120 ps around a median of -156.548 ps, a 5.994 ps
span equal to 3.83% of the median magnitude. Estimated setup TNS spans 0.167 ns,
or 2.41% of its median magnitude.

These are descriptive results for one small design, one platform, one host, and
one placement flow. They are not a universal EDA-noise estimate.

## Full-flow boundary

An independently retained smoke-test metadata dataset records the same ORFS
commit, container digest, input hashes, fixed configuration, exact container
command, and complete stdout. That run completed placement, then the
linux/amd64 container failed at clock-tree synthesis with an illegal instruction
under ARM emulation.
This candidate therefore makes no post-CTS, routing, GDS, signoff, multi-PDK,
multi-design, thread, or operating-system claim. It cannot substantiate the
684-run and universal 2.22% claims made by the deleted synthetic file.

## Reproduction

Start Docker Desktop, provide an ORFS checkout at the commit recorded in the
summary, and pull the exact container digest. Then run:

```bash
python3 data/scrapers/run_openroad_gcd_placement_seed_pilot.py \
  --orfs data/scrapers/.cache/openroad-flow-scripts \
  --start-seed 1 \
  --end-seed 20
uv run --with matplotlib --with numpy \
  python data/studies/06-eda-seed-dispersion/plot_openroad_gcd_placement_seed_pilot.py
```

The runner clears only each explicitly named candidate flow variant before
execution. It refuses a tracked-dirty ORFS checkout and writes the aggregate
CSV and summary after every completed run.

With `--resume`, the runner accepts the released `stdout_receipt` column and
the earlier runner's `stdout_dataset` alias. Missing local build artifacts do
not erase recorded hashes, and conflicting artifacts are rejected. When all
requested seeds already have successful records, no evidence files are
rewritten. The summary's historical runner hash identifies the code used for
the recorded execution, not subsequent repairs to the runner.

The resume regression check uses copies of the released rows without running
Docker or modifying the pilot:

```bash
python3 data/studies/06-eda-seed-dispersion/test_pilot_resume.py
```
