# Task Specification

This document pins down deliverables, environment, and evaluation mechanics.
Deep-dive companions: `docs/architecture.md` (what to compute),
`docs/quantization.md` (weight format + numeric freedom),
`docs/interface.md` (bus protocol), `docs/memory_map.md` (image layout),
`harness/evaluate.py` and `harness/scoring.py` (metric formulas). The
arbiter of model semantics is `reference/model.py` — prose never overrides
it.

## 1. Deliverables

1. **RTL** under `rtl/`, listed in `rtl/filelist.f`, top module
   `msh_chip_top` with the exact port list of the provided stub
   (`rtl/msh_chip_top.v`). Language: Verilog-2005 or the SystemVerilog
   subset that BOTH Verilator 5 and Yosys 0.66 (`read_verilog -sv`) accept —
   synthesizability with the provided flow is part of the score.
   The RTL must be plain readable source: no vendor IP blobs, no
   pre-synthesized or machine-generated netlists checked in as "source",
   no encrypted/obfuscated modules.
2. **`REPORT.md`** at the task root.
3. **Git history.** Work in a git repository (if the task directory is not
   already one, run `git init && git add -A && git commit -m "pristine
   task"` before touching anything). Commit incrementally with coherent
   messages as you progress — the grader audits your final tree as a diff
   against the pristine state, and a clean history is scored under rubric
   R5. Keep `build/` and caches out of commits (`.gitignore` already
   covers them).
4. Optionally: your own tests/notes in a clearly named directory.
5. **Strongly recommended: a bit-exact self-reference model** at
   `rtl/selfmodel/run.sh` (it ships inside your `rtl/` deliverable; keep
   it OUT of `rtl/filelist.f` — it is not RTL). Contract:
   `bash rtl/selfmodel/run.sh <image.bin> <out.bin>` writes the int32
   logits your chip should produce for that image — little-endian,
   row-major `[seq_len, vocab]`, no padding. This is the industry C-model
   discipline with the roles merged: YOU choose the internal number
   formats (the float32 reference is the spec boundary, judged by
   cosine), but your RTL should match YOUR OWN fixed-point model
   **bit-exactly** (the implementation boundary). The harness runs it on
   every simulated nano workload and reports the comparison in
   `score.json` (R4 evidence). Python/numpy is available; helper code may
   live next to the script under `rtl/selfmodel/`.
6. Optionally, in `REPORT.md`: a ```json perf-model``` fenced block,
   `{"cycles_per_token": {"nano": N}}` — your analytical
   prediction of steady-state cycles per token on the long run. The
   harness compares it against measurement (R2/R3 evidence). Commit the
   prediction before you measure; the git history is the timestamp.

## 2. Functional requirement

For the `nano` evaluation config, one fixed RTL build (the harness compiles
your filelist once — no per-workload rebuilds or parameter overrides) must:

1. Read the image header at address 0 (`docs/memory_map.md`) and configure
   itself at run time.
2. Process the token sequence **teacher-forced and strictly causally**:
   position p may depend only on tokens 0..p. Maintain the MLA KV cache,
   the KDA recurrent state / conv histories, and compute each layer's
   top-k expert selection exactly as a decoder would — the evaluation
   feeds the tokens, but the datapath is a decoder datapath. The
   attention-residual snapshots are per position (no cross-token state).
3. Write, at the addresses given in the header: one int32 logits row per
   position (row stride = header word 30; any per-row scale — the
   comparator is cosine similarity), the per-position argmax token id
   (uint32, lowest-index tie break), then status `0x600D_D00D` as the LAST
   memory write, then DONE on the response stream.

Bounds your design must accommodate (the `nano` config):
d_model 64, 2 layers, vocab 512, max_seq 64, MLA 2 heads ×
(dk 32 + dr 16 / dv 32) on a dc 128 latent, KDA 2 heads × 32×32
state, 8 experts (top-2 + 1 shared, d_ff 32), conv kernel 4,
attention-residual block 2, int4 group size 128. Config details:
`reference/configs.json`.

## 3. Evaluation mechanics

* `make evaluate` = integrity check → automated audit → lint →
  verilate `rtl/` + frozen TB → simulate the `nano` config
  at two sequence lengths, in parallel
  (`--jobs`, default 4) → cosine/argmax comparison against freshly
  computed float32 goldens → reset-robustness re-runs (random initial
  state) and latency-elasticity re-runs (2× base latency) on nano →
  yosys netlist generation, area, and timing →
  self-model / perf-model comparisons
  (if provided) → constrained-throughput primary metric →
  `build/score.json`.
* Final grading uses `make evaluate` with an undisclosed seed. The public
  `TOTAL` is the primary throughput score: pass nano correctness and
  resource/timing gates, then maximize
  `tokens_per_sec = target_freq_hz / cycles_per_token`. Score-bearing
  throughput fields stay zero until the official gates pass, and legacy
  performance / bandwidth-energy components stay zero until the relevant
  configs pass correctness. The ungated cycle-derived estimate is retained
  only as `debug_raw_tokens_per_sec` for diagnosing cycle-count bugs; it is not
  a performance score, and designs that fail correctness get no performance
  credit. Debug-gated throughput ignores checks that were explicitly skipped by
  quick/ad-hoc commands and is provided only as an inner-loop aid after
  correctness is clean.
* `make quick` for the inner loop (nano short sequence, no synth).
  Ad-hoc spot checks are no substitute for `make evaluate` — the official
  run covers both layer types, both context lengths, and the recurrent state.
* Cycle counts: RUN acceptance → DONE, from the TB. The memory model
  enforces bandwidth (≤16 B/cycle) and a ≥24-cycle in-order read latency
  with deterministic per-request jitter; short runs additionally apply
  ~5% request back-pressure (protocol stress). Performance and
  bandwidth-energy are measured on the long runs under full sustained
  bandwidth; the rooflines derive from the ACTIVE quantized weight
  footprint (`reference/gen_weights.py::active_weight_bytes` — dense
  tensors + top-k experts per layer + one embedding row), and the
  weight-stream floor from the dense footprint (`floor_weight_bytes`).
  The primary metric uses the long run of `nano` under `make evaluate`;
  quick/ad-hoc config runs report nano as a debug proxy.
* Resource budgets are fixed in `harness/resource_budgets.json`: mapped
  standard-cell logic area (Nangate45), on-chip SRAM, DRAM port
  bandwidth, and target clock period. All on-chip storage beyond
  flip-flops must be instantiated as the `msh_sram` macro (see
  `docs/interface.md`); constant lookup tables must use the companion
  read-only `msh_rom` macro (`$readmemh` init from `rtl/roms/`, same
  pricing). Macro bits are priced at ~1 Mbit/mm^2 and count toward BOTH
  the area budget and the SRAM capacity budget, so the area envelope —
  not the nominal MiB figure — is what physically limits on-chip
  storage. The nano budget is 4 mm^2 standard-cell
  logic area, 4 MiB on-chip SRAM, 16 B/cycle DRAM port, and a fixed
  100 MHz / 10.0 ns target clock (`resource_budgets.json`). DRAM
  capacity is unlimited, but all off-chip
  traffic must use the testbench memory port. The public throughput target is
  20,000 tok/s, near the nano active-stream roofline at
  100 MHz / 16 B-per-cycle.
* The hidden seeds file may stretch sequence lengths (bounded by
  `max_seq`) and select int4 `group_size` 64 instead of 128. Both are in
  the image header (words 19/31 and 20). Hardcoding the public values is
  indistinguishable from correct behavior on the public set and fails on
  the hidden set — self-configure from the header.

## 4. Determinism & tolerance contract

* All "randomness" (weights, scales, zeros, tokens) is splitmix64-derived
  (`reference/prng.py`) from one seed. Public seed: 20260706
  (`harness/seeds_public.json`). Final grading: different seed, identical
  distributions (plus the group_size / sequence-length variation above).
  Memory-timing jitter is likewise seed-derived and reproducible.
* No frozen numeric artifacts ship with this task — there is no RoPE, and
  every nonlinearity is yours to approximate (with disclosed generators
  for any ROM tables; see harness/audit.py, R1.4).
* The float32 reference itself may wobble by ulps across BLAS libraries;
  the cosine comparator absorbs this by construction. The pass bar
  (cos ≥ 0.98 every row, argmax agreement ≥ 0.99) is chosen so that honest
  fixed-point datapaths clear it with margin: an int16 rendering of exact
  logits measures cos ≈ 1.000000; the argmax criterion is what demands real
  end-to-end precision. The bar is a gate, not a target: correctness
  credit keeps growing log-scaled in (1 − cos) up to 1 − cos ≤ 2e-5
  (harness/scoring.py), so precision margin above 0.98 is directly worth
  points — budget your internal formats accordingly.

## 5. Practical guidance (non-normative)

* Recommended loop: implement → `make lint` → `make quick` → bisect
  divergence with `harness/gen_golden.py --dump` per-layer intermediates →
  `make evaluate` to bank a score.
* Error compounds through the layers and across long contexts (the KDA
  state integrates everything before it, and router mis-selections are
  discrete). Per-layer cosine ≥ 0.999 against the dump is a good working
  bar; the dump also carries each layer's expert selection and
  residual-mix probabilities — check those first when a layer diverges.
* The int4→dequant→MAC pipeline: never write dequantized weights back to
  external memory — you'd double your bandwidth and lose the roofline race.
  Scales/zeros for a group can be fetched once per (group × out-column)
  tile. The MoE gather is descriptor arithmetic: expert j's nine
  descriptor entries sit at a fixed stride from `moe.e0`'s.
* KV cache, KDA state, and conv history can live on-chip or in the
  scratch region (header words 28/29); scratch is never inspected.
  Caching the MLA latent (dc + shared kr per position) instead of
  per-head k/v is an equivalent, much smaller cache — the choice is
  yours.
