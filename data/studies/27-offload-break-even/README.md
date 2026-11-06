# The unamortized offload wall: measured break-even on one host

Reference: *Architecture 2.0*, chapter 2, `fig-ch02-offload-break-even`.

The study times FP32 `n x n` matrix products on the host CPU (vendor BLAS through
PyTorch) and on the Apple GPU through the PyTorch MPS backend, for the 16 sizes and six
arms defined in `collect.py`. All results are in `summary.json` and `medians.csv`, which
`reproduce.py` recomputes from the five declared runs, `raw/run-1.csv` through `raw/run-5.csv`. It stops if one is missing, and it reports any other `raw/run-*.csv` and leaves it out.

Host: Apple M5 Max, 64 GiB unified memory, macOS 26.4, PyTorch and Python as recorded per run in `raw/run-<k>.host.json`, battery power.
Each run records `hw.perflevel0` and `hw.perflevel1` core counts in `raw/run-<k>.host.json`.

    "$PY" collect.py --run-id <k>      # one fresh process per run
    python3 reproduce.py               # recompute summary.json and medians.csv (stdlib only)
    python3 plot.py                    # figure twins

`PY` must provide the Python and torch versions in `raw/run-<k>.host.json` (3.12.13 and
2.14.1). The receipts do not record an interpreter path. See `environment` in
`provenance.yml`; a `python3` that imports a different torch does not reproduce the
collection.

## History

An independent audit failed the first version. Its `mps_16_launch` arm waited once after
all sixteen launches, which queues work rather than paying a round trip per launch, and its
prose called consecutive processes independent. Those runs are kept in
`raw/superseded-shared-wait/`, with their own receipts (Python 3.14.4, torch 2.11.0). The
arm now waits for each launch, and five runs replaced the three, spaced about 45 s apart in
one session under Python 3.12.13 and torch 2.14.1.

## Limits

One machine, one session, one framework, FP32, on battery power with no thermal control.
Shared memory means the copy arm is an in-DRAM copy, so a transfer cost that grows with the
work across a discrete link is not exercised. No transfer and compute overlap is attempted.
