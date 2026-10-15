# Chip Interface & Testbench Contract

Top module `msh_chip_top`, port list exactly as in the provided stub.
Single clock `clk`, active-low reset `rst_n` (released after 16 cycles).
Driver: `harness/tb/tb_main.cpp` (normative).

## Command / response streams

Standard valid/ready handshake (transfer when both high at posedge).

* `cmd_data[31:0]` — the TB sends one `RUN = 0x0000_0001` after reset and
  nothing else. `cmd_valid` stays high until you accept.
* `rsp_data[31:0]` — send `DONE = 0x0000_D0DE` exactly when the run is
  complete (after the status-word write has been accepted by the memory
  port). The TB's `rsp_ready` is always high. Cycle counting stops at DONE.

## Memory port

One request channel, one read-response channel.

* Request: `mem_req_valid/ready`, `mem_req_write`, `mem_req_addr[35:0]`
  (byte address, must be 16-byte aligned), `mem_req_wdata[127:0]`,
  `mem_req_wstrb[15:0]` (byte enables, writes only).
* `mem_req_ready` may deassert on any cycle (hold your request until it
  is accepted); peak throughput is one 16-byte beat per cycle. On
  performance-measured (long) runs, ready stays high — the sustained
  bandwidth for the roofline is the full 16 B/cycle; short runs apply
  ~5% pseudo-random back-pressure as a protocol stress. Misaligned or
  out-of-range requests increment an error counter (any error ⇒ the run
  cannot PASS) and reads return zeros.
* Reads: responses arrive **in order**, each **at least 24 cycles** after
  acceptance (per-request latency varies — a deterministic pseudo-random
  jitter seeded per run; delivery is monotonic, so back-to-back requests
  still drain at one beat per cycle), on
  `mem_rsp_valid/mem_rsp_rdata[127:0]`; hold your `mem_rsp_ready` low to
  stall (data waits for you). Any number of requests may be in flight.
  Do NOT bake the constant 24 into your control: designs must be
  latency-elastic. This is tested: the evaluation re-runs the nano
  short run with the base latency doubled (TB `--lat-base=48`) and
  reports `elasticity = cycles(48)/cycles(24)` for realism review —
  a design that keeps reads in flight sits near 1.0.
* Writes are posted (no acknowledgement). Ordering follows acceptance
  order.
* Byte lanes: `mem_rsp_rdata[8*i+7 : 8*i]` is the byte at `addr + i`
  (little-endian); `mem_req_wstrb[i]` enables `wdata[8*i+7:8*i]` → `addr+i`.
* Weight-stream floor (normative, checked per run): the DENSE tensors —
  everything except the data-dependent routed experts and embedding rows
  (`reference/gen_weights.py::floor_weight_bytes`) — participate in every
  position's forward pass, so a clean run must read at least
  `floor_weight_bytes` from memory: `read_beats × 16 ≥ floor_weight_bytes`.
  Fewer read beats is treated as a protocol violation (the run cannot
  PASS). The floor is deliberately conservative for MoE — an honest design
  also reads its selected experts, which the roofline (not the floor)
  prices.

## On-chip storage (SRAM macro)

All storage beyond individual flip-flops (KV cache, KDA state, conv
histories, buffers, ...) MUST be instantiated as the harness-provided
macro `msh_sram` — inferred memories (`reg [W-1:0] mem [0:D-1]` arrays)
are rejected: the evaluation fails the `macros_only` gate if any `$mem_v2`
survives synthesis. The macro file is injected by the harness; do NOT
redefine `msh_sram` or list it in `rtl/filelist.f`.

`msh_sram #(.DEPTH(D), .WIDTH(W))` — 1 write port + 1 read port, single
clock, per-byte write enables, SYNCHRONOUS read: `rdata` is valid the
cycle after `re`/`raddr` are sampled; a same-cycle read+write to one
address returns the old data. `WIDTH` must be a multiple of 8.

Macro instances are priced from their parameters at ~1 Mbit/mm²
(N45 high-density 6T + periphery): `DEPTH×WIDTH` bits count toward both
the SRAM capacity budget and the area budget
(`harness/resource_budgets.json`). The
macro interface is fully synchronous, so it cuts combinational paths;
its internal access is assumed to meet the target clock.

## Constant lookup tables (ROM macro)

Constant LUTs (activation tables, fixed coefficient ROMs, ...) MUST be
instantiated as the harness-provided read-only macro `msh_rom` — the
`macros_only` gate bans inferred memories, and a constant table is not a
writable SRAM, so without it the only option is to expand the table into
a combinational mux tree: that bloats gate count and gives the table
index a fanout in the thousands (a timing disaster). The macro file is
injected by the harness; do NOT redefine `msh_rom` or list it in
`rtl/filelist.f`.

`msh_rom #(.DEPTH(D), .WIDTH(W), .INIT_FILE("rtl/roms/<name>.hex"))` —
TWO asynchronous read ports (`raddr1`/`rdata1`, `raddr2`/`rdata2`):
`rdata = mem[raddr]` combinationally, so one lookup can fetch `tab[idx]`
and `tab[idx+1]` in the same cycle (e.g. for linear interpolation).
Contents load at time 0 via `$readmemh` from a hex file under
`rtl/roms/` (the only path the audit allows `$readmem` to reference);
`WIDTH` must be a multiple of 8.

`msh_rom` is priced exactly like `msh_sram`: `DEPTH×WIDTH` bits at
~1 Mbit/mm² count toward both the SRAM capacity budget and the area
budget, and instances are recognized as macro storage (not design
`$mem_v2`) by the `macros_only` gate.

## Run protocol

1. TB preloads the image (`docs/memory_map.md`) and asserts RUN.
2. Chip reads the header, self-configures, streams weights as it pleases,
   and processes the token sequence causally (teacher-forced decode: the
   MLA KV cache, KDA state and conv histories must be maintained across
   positions; expert selection happens per token from the router scores).
3. Chip writes one logits row + one argmax id per position (any order, any
   time), then the status word **last**, then raises DONE.
4. TB dumps the output region; the harness compares per-row cosine
   similarity and argmax agreement against the float32 reference.

Timeouts: nano cycle budget (`reference/config.py::timeout_cycles`)
and wall-clock budgets. On cycle timeout the TB still dumps memory —
already-written rows earn partial credit — but the run cannot PASS and
earns no performance/energy credit.

Timing profiles (normative in `harness/evaluate.py`): long runs use
`--lat-jitter=12 --stall-permille=0` (bandwidth preserved); short runs use
`--lat-jitter=24 --stall-permille=50`. Jitter/stall streams are seeded
deterministically per (seed, config, prompt), so every run is exactly
reproducible.

Reset: `rst_n` is the only initialization your design may rely on. The
evaluation re-simulates the nano short run with all flops
initialized to pseudo-random values (`+verilator+rand+reset+2`); outputs
must be byte-identical to the zero-init runs (real silicon does not power
up to zeros). See `harness/evaluate.py` hard gates.

## Metrics the TB reports

`cycles` (RUN→DONE), `read_beats`, `write_beats`, `addr_errors`,
`timeout`, `stall_cycles`, and the timing profile used. Cycles feed the
roofline performance score; `read_beats + write_beats` feed the
bandwidth-energy score E (data movement is the batch-1 energy proxy); and
they feed realism review (a design claiming fewer read beats than the
dense int4 stream it must consume will be noticed).
