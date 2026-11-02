# The unamortized offload wall: measured break-even on one host

**Study ID:** `offload-break-even` (candidate for `data/studies/`)
**Reference:** *Architecture 2.0*, Chapter 2, "the unamortized offload wall"
**Status:** measured pilot, one host, three runs, 2026-11-02. Not integrated; nothing under `Arch2/` was changed.

## Research question

At what problem size does handing a matrix product to an accelerator beat an
optimized host doing it in place, and how do transfers and batching move that
crossover? The claim the figure needs to carry: the accelerator has a fixed
launch cost that no small problem can amortize, moving operands adds a second
fixed cost, and batching many small problems into one launch pays that cost
once instead of many times.

## Measurement

FP32 `n x n` products, `n` in {16, 24, 32, 48, 64, 96, 128, 192, 256, 384,
512, 768, 1024, 1536, 2048, 3072}. Six arms, two panels:

| Panel | Arm | What is timed |
|---|---|---|
| (a) one product | `cpu_single` | `torch.matmul(A, B)` on the host (Apple Accelerate BLAS, 6 intra-op threads) |
| (a) | `mps_resident` | `torch.matmul(Ad, Bd)` with operands already on MPS, then `torch.mps.synchronize()` |
| (a) | `mps_copy` | `A.to('mps')`, `B.to('mps')`, matmul, `.cpu()`, synchronize |
| (b) sixteen products | `cpu_bmm` | `torch.bmm` on the host over a `(16, n, n)` batch |
| (b) | `mps_16_launch` | sixteen separate `torch.matmul` launches on resident operands, one synchronize after the sixteenth |
| (b) | `mps_bmm` | one `torch.bmm` launch on resident operands, synchronize |

Per `(arm, n)`: 5 warmup calls, then 31 timed repetitions with
`time.perf_counter()`; every repetition is kept in `raw/`. The six arms are
shuffled per `n` (order recorded) to spread thermal drift across arms. The
whole sweep ran three times as three fresh processes about a minute apart
(50 s, 63 s, 61 s of measurement each), so run-to-run dispersion is measured
rather than assumed. Output allocation is inside the timed region for every arm.

Host: Apple M5 Max (12 performance + 6 efficiency cores, 64 GiB unified
memory), macOS 26.4, Python 3.14.4, PyTorch 2.11.0 with `BLAS_INFO=accelerate`
and MPS available, `torch.get_num_threads() == 6`, on AC power, no thermal
warning recorded. Full state per run in `raw/run-<k>.host.json`.

## Results (every number below is printed by `reproduce.py`)

Pooled medians over the three runs (93 samples per cell), seconds:

```
  n         cpu_single  mps_resident      mps_copy       cpu_bmm mps_16_launch       mps_bmm
     16      9.160e-07     1.877e-04     5.295e-04     1.392e-05     5.713e-04     1.827e-04
     64      1.291e-06     1.737e-04     5.202e-04     2.088e-05     5.668e-04     1.765e-04
    256      2.283e-05     1.947e-04     5.523e-04     3.935e-04     9.370e-04     3.520e-04
    512      1.845e-04     2.238e-04     6.847e-04     3.849e-03     1.316e-03     9.524e-04
    768      4.859e-04     2.684e-04     6.803e-04     9.623e-03     1.551e-03     1.235e-03
   1024      1.285e-03     3.252e-04     9.777e-04     2.489e-02     2.736e-03     2.533e-03
   2048      1.223e-02     3.623e-03     2.630e-03     1.887e-01     5.094e-02     2.258e-02
   3072      5.057e-02     4.330e-03     7.204e-03     6.594e-01     1.564e-01     1.583e-01
```
(The full 16-row table, per run and pooled, with quartiles, is `medians.csv`.)

### Crossovers

First grid `n` at which the MPS arm's median beats the CPU arm's median, and
whether it stays ahead at every larger `n`.

| MPS arm | vs | pooled crossover | stays ahead | per-run crossover (1, 2, 3) | stable across runs |
|---|---|---|---|---|---|
| `mps_resident` | `cpu_single` | 768 | yes | 768, 1024, 768 | no |
| `mps_copy` | `cpu_single` | 1024 | yes | 1024, 1024, 768 (run 3 does not stay ahead) | no |
| `mps_16_launch` | `cpu_bmm` | 384 | yes | 384, 384, 384 | yes |
| `mps_bmm` | `cpu_bmm` | 256 | yes | 256, 256, 256 | yes |

Both panel (b) crossovers are stable. Both panel (a) crossovers sit on a knife
edge where the two arms are within a factor of two of each other, and the
run-to-run dispersion of a 31-sample median at those sizes is of that same
order (next section), so each moved by one grid step in one of three runs.
Speedups at the pooled crossover are modest: CPU/MPS = 1.81x (`mps_resident`
at 768), 1.31x (`mps_copy` at 1024), 1.73x (`mps_16_launch` at 384),
1.12x (`mps_bmm` at 256). At 3072 the resident single product is 11.7x
faster than the host (pooled medians 5.057e-2 / 4.330e-3).

### Launch floor and batching

Resident launch floor (median of all samples with `n <= 256`):
`mps_resident` 1.824e-4 s pooled (IQR 3.09e-5 s; per run 1.552e-4,
1.877e-4, 1.888e-4). `mps_bmm` 1.928e-4 s pooled. `mps_16_launch` 5.960e-4 s
pooled (per run 4.194e-4, 6.135e-4, 7.118e-4).

Sixteen launches cost 3.21x one batched launch for `n <= 256` (pooled median
of the per-`n` ratios; range 2.66x at `n = 256` to 3.55x at `n = 128`; per-run
medians 2.59x, 3.24x, 3.38x). Sixteen launches do not cost sixteen times one
launch: submissions pipeline, and only one round trip is paid.

### Non-monotone points

Grid points where the median is lower than at the previous size, per run:

- Recurring in all three runs: `mps_resident@64`, `mps_copy@64`,
  `mps_16_launch@32`, `mps_16_launch@64`, `cpu_bmm@32`. All are in the flat
  floor region, with pooled drops of 0.9 to 7.8 percent; they are floor jitter,
  not a trend.
- Not recurring, `n >= 384`: `mps_16_launch@384` (runs 2 and 3; pooled drop
  26.2 percent: sixteen launches at 384 are cheaper than at 256 in those runs),
  `mps_copy@768` (runs 1 and 2), `mps_resident@384` (run 3), `@512` (run 2),
  `@768` (run 3), `@1024` (run 2), `mps_copy@2048` (run 2; pooled drop
  21.4 percent), `mps_bmm@512` (run 2).
- The pilot's non-monotone point, batched MPS at `n = 1536`, did not recur in
  any run.

### Run-to-run dispersion

The three runs are three process invocations a minute apart, and the MPS
arms fall into two regimes. At small `n`, run 1 sits about half the launch
cost of runs 2 and 3 (`mps_16_launch` at 192: 4.48e-4 vs 8.59e-4 and
8.72e-4 s; `mps_bmm` at 256: 1.90e-4 vs 3.67e-4 and 3.62e-4 s). At
`n = 2048`, `mps_resident` is 1.354e-3 s in run 1 but 4.092e-3 and
3.623e-3 s in runs 2 and 3, slower per flop than at 3072 in those runs; and
`mps_copy` at 1536 is 1.338e-3 s in run 1 but 3.658e-3 and 3.410e-3 s in
runs 2 and 3. The CPU arm had one slow episode: `cpu_single` at 768 in run 3,
median 1.056e-3 s with IQR 6.37e-4 to 1.77e-3 s, against 4.79e-4 and
4.83e-4 s in runs 1 and 2; that episode is what moves the copy arm's crossover
to 768 in run 3.

At the pooled crossover sizes, the spread of the three per-run medians as a
fraction of the pooled median: `mps_resident` at 768, 105.2 percent (CPU arm
118.7 percent); `mps_copy` at 1024, 75.9 percent (CPU 11.3 percent);
`mps_16_launch` at 384, 40.3 percent (CPU 4.9 percent); `mps_bmm` at 256,
50.1 percent (CPU 13.8 percent). The worst spread anywhere is 210.8 percent
(`mps_bmm` at `n = 16`). Within-run IQRs are far tighter (for example
`mps_resident` at 768: 3.4e-5, 4.4e-5, 5.8e-5 s in the three runs). The
dispersion is between processes, not within one; a figure drawn from one run
would understate it.

### Pilot findings, confirmed or refuted

| Pilot claim | This study |
|---|---|
| resident matmul beats CPU from 768 | confirmed pooled and in runs 1 and 3; run 2 gives 1024 |
| including copies, from 1024 | confirmed pooled and in runs 1 and 2; run 3 gives 768 during a CPU slow episode and falls back behind at 1024 |
| sixteen launches beat CPU from 512 | refuted: 384 in all three runs |
| one batched launch from 192 | refuted: 256 in all three runs (at 192 pooled `mps_bmm` 2.544e-4 s vs `cpu_bmm` 1.569e-4 s) |
| resident floor 1.7e-4 to 1.9e-4 s | confirmed: 1.824e-4 s pooled, 1.55e-4 to 1.89e-4 per run |
| non-monotone point at 1536 batched | not reproduced in any run |

## Claim boundary

One laptop, one session, one dtype, one BLAS. Unified memory: the copy arm
measures an in-DRAM copy between CPU-visible and MPS-visible buffers plus
synchronization, not a discrete-link transfer, so the copy penalty here is a
lower bound on what a discrete accelerator pays. The host arm is optimized
vendor BLAS; a naive host loop would move every crossover to smaller `n`. No
overlap of transfer and compute was attempted. The grid is coarse between
powers of two, so a crossover "at 768" means between 512 and 768. See
`provenance.yml` for the full caveat list.

## Files

```
README.md          this file
collect.py         one run = one process; writes raw/run-<k>.csv and raw/run-<k>.host.json
reproduce.py       stdlib only; recomputes everything from raw/ into summary.json and medians.csv
provenance.yml     evidence class, host, software, commands, caveats
summary.json       crossovers, launch floor, launch ratio, non-monotone flags, dispersion
medians.csv        per (run | pooled) x arm x n: n_samples, median, q1, q3, iqr, min, max
raw/run-<k>.csv    2976 rows each: run_id, n, panel, arm, arm_order, rep, seconds
raw/run-<k>.host.json, raw/run-<k>.log
sha256-manifest.txt
```

## Reproduce

```bash
cd <this folder>
for k in 1 2 3; do python3 collect.py --run-id $k; sleep 5; done   # ~3 min on an M5 Max
python3 reproduce.py
```
