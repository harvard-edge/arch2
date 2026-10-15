# nano-kpu

This repo contains the RTL design of a nano-scale hybrid-architecture
inference chip, which was designed and implemented fully by Kimi-K3, plus its
functional-simulation and performance (timing/area) test flow. The model is a
hybrid-attention MoE transformer: **KDA (Kimi Delta Attention) linear
attention**, **NoPE multi-head latent attention (MLA)**, **sigmoid-routed MoE
(top-2 routed experts + one shared expert)**, and **attention-residual
mixing**, with int4 group-128 weights and teacher-forced token-by-token
decode.

*Disclaimer: This is a demonstration of Kimi K3, not an official project by Moonshot AI.*

## Layout

```
rtl/            chip RTL (top module: msh_chip_top; filelist.f = compile manifest)
  ├── roms/     LUT init hex (sigmoid/alpha/expneg/rsqrt/recip) + generator notes
  └── selfmodel/  bit-exact Python fixed-point model (simulation aid)
reference/      float32 golden reference model (correctness judge; goldens are
                recomputed at evaluation time)
harness/        functional simulation + performance evaluation flow
  ├── evaluate.py   main entry: correctness (cos/argmax) + cycles/token + throughput
  ├── tb/           Verilator C++ testbench (16 B/cycle DRAM port model)
  ├── macros/       msh_sram / msh_rom macro models (sim injection + synth blackbox)
  ├── synth_area.ys / synth_tech.ys / synth_netlist.ys
  │                 performance scripts: yosys area/NE, Nangate45 mapped timing,
  │                 gate-level netlist
  ├── lib/          cell libraries (fetched at setup time, not bundled)
  └── scoring.py / audit.py / memmap.py / check_integrity.py ...
                    scoring.py = correctness judgment + synthesis metric helpers
                    (NE/latch/lint thresholds; no scoring)
docs/           specifications (architecture / interface / memory_map /
                quantization / TASK_SPEC)
weights/        weight format notes
Makefile        unified entry points
```

## Setup

Run once after cloning:

```bash
bash scripts/setup_env.sh      # or: make setup
source scripts/kpu-env.sh      # put the toolchain env on PATH
```

The script is conda-centric and idempotent:

1. **Conda** — uses an existing conda if present, otherwise bootstraps
   Miniconda into `~/miniconda3` (no root needed).
2. **Dedicated env `nano-kpu`** — created from conda-forge with
   **Verilator 5.x** (baseline 5.050), **yosys >= 0.64** and
   **python 3.12 + numpy**. It never touches an existing base env.
3. **`scripts/kpu-env.sh`** — a generated PATH file; source it (or open a
   new shell) so `verilator` / `yosys` / `python3` resolve to the env.
4. **Nangate45 cell library** — `NangateOpenCellLibrary_typical.lib` is
   downloaded from OpenROAD-flow-scripts (pinned by commit and SHA-256)
   into `harness/lib/`. It is deliberately not bundled; synthesis needs
   it, simulation does not.

Prerequisites: bash, `curl` or `wget`, and network access to
repo.anaconda.com (or mirrors) and raw.githubusercontent.com. On failure
the script exits non-zero with a specific message — fix and re-run.

## Quick start

Dependencies: Verilator 5, yosys (for synthesis), python3 + numpy.

```bash
bash scripts/setup_env.sh                  # first time only: toolchain env + cell library
source scripts/kpu-env.sh                  # put the toolchain env on PATH
python3 harness/evaluate.py --quick        # functional sim (short sequence, minutes)
python3 harness/evaluate.py                # full evaluation (sim + timing/area synthesis, hours)
python3 harness/evaluate.py --skip-synth   # functional + randreset + latency, no synthesis
make synth                                 # area + timing flow only (no sim)
make lint / audit / selftest               # individual checks
```

Note: the `rtl/selfmodel/run.sh` contract uses whatever `python3` is on PATH;
it needs numpy.

## Protocol & measurement essentials (see docs/)

- Interface: command stream (`RUN 0x1` -> `DONE 0xD0DE`) + 128-bit DRAM port
  (in-order reads, >=24-cycle latency, posted writes) + a self-describing memory
  image (header + descriptor table).
- Correctness: per-row logits cosine >= 0.98 and pooled argmax >= 0.99 against
  the float32 reference.
- Throughput: `cycles_per_token = long-run simulated cycles / seq_len`,
  `tokens/s = clock / cpt`.
- Storage rule: all arrays beyond flip-flops go through the `msh_sram`/`msh_rom`
  macros; macro bits are priced at ~1 Mbit/mm2 and count toward the area budget.

**Measurement methodology.** For fast turnaround, area and timing are measured
at the **synthesis stage** — pre-layout estimates from yosys/abc mapping and
static timing, **not** validated through backend place & route. To keep
results comparable across designs, they are produced with a **fixed, frozen
synthesis parameterization**; the flow deliberately does **not** search for
design-specific optima, so reported numbers are a conservative, reproducible
baseline — not the best achievable QoR, and not sign-off values.

## License & third-party assets

This repository is released under the Apache License 2.0 (see `LICENSE`).

The **Nangate45 standard-cell library** (`NangateOpenCellLibrary_typical.lib`)
is **not distributed with this repository**. It is fetched at setup time by
`scripts/setup_env.sh` from
[The-OpenROAD-Project/OpenROAD-flow-scripts](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts)
(`flow/platforms/nangate45/lib/`).
