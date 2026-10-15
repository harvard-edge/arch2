# Lab 04 — Stage 4: Evaluate (`04-evaluate`)

**Title:** *Adversarial Referees, Chaos Testing & Silicon Synthesis*
**Lifecycle Stage:** `4. Evaluate`
**Book Alignment:** Part II — *Loop Mechanics* (Chapter 5: *Prediction, Generation, and Optimization*, Chapter 6: *Execution Harnesses and Tool Isolation*)
**Target Artifact:** [`nanochip/kpu/harness/audit.py`](../../kpu/harness/audit.py), [`nanochip/kpu/harness/tb/tb_main.cpp`](../../kpu/harness/tb/tb_main.cpp), [`nanochip/kpu/harness/synth_tech.ys`](../../kpu/harness/synth_tech.ys), [`nanochip/kpu/rtl/msh_deq.v`](../../kpu/rtl/msh_deq.v), [`nanochip/kpu/rtl/msh_fetch.v`](../../kpu/rtl/msh_fetch.v)

---

## 1. What Breaks Without This Stage: Simulation-Only Escapes & Synthesis Blindness

A conventional RTL testbench checks whether a module produces the right outputs on a single deterministic happy-path simulation. Against an autonomous AI coding agent, happy-path simulation is dangerously porous:

1. **Simulation-Only System-Task Escapes:** Verilog includes file I/O and C-binding constructs (`$fopen`, `$fread`, `import "DPI-C"`, `$readmemh("/tmp/golden.hex")`) that compile cleanly in Verilator and pass functional simulation in 0 cycles, while synthesizing to empty wires! Or an agent may redefine `module msh_sram` with an asynchronous zero-latency read port to bypass the 1-cycle registered macro timing.
2. **Zero-Initialized Flip-Flop & Rigid Pipeline Assumptions:** In a naive simulator, unreset registers start at `0`, and DRAM responses arrive at a fixed 24-cycle cadence. Real silicon wakes up in random metastability, and real memory controllers experience refresh stalls and bank conflicts.
3. **Combinational Mux Bloat & Unbuffered Wireload Distortion:**
   - When unpacking a 16-byte DRAM beat at an arbitrary byte offset (`ws_shift`), a naive RTL generator writes a **16-way parallel variable-index byte demux**, consuming **+96,000 gates** inside a tiny embedding gather unit (`msh_deq.v` line 65)!
   - Worse, if you run Yosys/ABC static timing (`stime,-c`) on a mapped netlist *without* fanout buffering (`buffer;upsize;dnsize`), the `5K_hvratio_1_1` wireload model charges enormous capacitive delay to high-fanout reset and control nets—reporting **`266,514.91 ps` (`266.5 ns`)** on `msh_deq` alone (and **`5,084 ns`** on the full chip) when the true buffered critical path is **`1,478.99 ps` (`1.479 ns`)**!

---

## 2. How Kimi K3's `nano-kpu` Implements Stage 4

`nanochip/kpu/harness/evaluate.py` orchestrates a multi-layered **Adversarial Referee Pipeline**:

1. **Static RTL Cheat Auditor (`harness/audit.py`):**
   - Strips comments and scans every file in `rtl/filelist.f` for forbidden PLI/DPI/file tasks (`$fopen`, `$fread`, `$system`, `$random`, `DPI`), any `$readmemh` path outside `rtl/roms/`, and any redefinition of `module msh_sram` or `module msh_rom`.
2. **Chaos Verification (`do_randreset` & `do_latency_sweep`):**
   - **Random Reset (`+verilator+rand+reset+2`):** Re-runs the short sequence with every flip-flop initialized to a seeded pseudo-random bit pattern and verifies that the emitted memory image is **100% byte-identical** to the standard run.
   - **$2\times$ DRAM Latency Sweep (`24 -> 48` cycles):** Doubles base memory read latency under 5% random request back-pressure (`--stall-permille=50`). Because `msh_fetch.v` uses a **256-deep credit-tracked FIFO**, cycles increase by only **`4.57%`** (`195,420 -> 204,352` cycles, `elasticity = 1.0457`) instead of stalling to $2.0\times$.
3. **Two-Pass Snapshot Yosys/ABC Nangate45 Flow (`harness/synth_tech.ys`):**
   - **Pass 1 (`design -save preabc` $\rightarrow$ `map` $\rightarrow$ `stat -liberty`):** Measures clean pre-buffer standard-cell logic area (`18,331.39 um^2` on `msh_deq`, `2.707 mm^2` full-chip).
   - **Pass 2 (`design -load preabc` $\rightarrow$ `map;topo;buffer;upsize;dnsize;topo;stime,-c`):** Inserts fanout buffers and sizes gates before static timing analysis, collapsing `msh_deq` delay from `266,514.91 ps` (unbuffered) to **`1,478.99 ps`** (buffered) and full-chip critical path to **`6.166 ns`**.

---

## 3. Hands-On Exercises

### Exercise A — `--mode break` (Run the 3 Adversarial Referee Stress Tests)
```bash
python3 nanochip/labs/04-evaluate/lab.py --mode break
```
**What happens:** Executes all three adversarial Stage 4 checks:
- **(a) Static Cheat Audit (`audit.py`):** Scans a rogue Verilog snippet containing `$fread`, `$readmemh("/tmp/weights.hex")`, and `module msh_sram` and shows all 3 hard violations caught immediately.
- **(b) Chaos & Elasticity Stress (`randreset` + `2x DRAM latency`):** Compares a rigid non-elastic 1-outstanding-request FSM (`elasticity ~ 1.88x` stall degradation + random-reset divergence on uninitialized accumulators) against Kimi K3's credit-tracked `msh_fetch.v` + set-on-first-write `qacc` (`elasticity = 1.0457x`, byte-identical `randreset`).
- **(c) Real Yosys Nangate45 Synthesis (`msh_deq.v`):** Runs live `yosys` synthesis on `nanochip/kpu/rtl/msh_deq.v` to measure the exact **180.2x wireload delay distortion** (`266,514.91 ps` unbuffered vs. `1,478.99 ps` buffered) alongside the **+96,000-gate penalty** of a naive 16-way parallel byte demux vs. Kimi K3's byte-serial intake (`18,331.39 um^2`, `11,888` gates).

### Exercise B — `--mode verify` (Execute Real `audit.py`, `verilator --lint-only`, and `yosys` Synthesis)
```bash
python3 nanochip/labs/04-evaluate/lab.py --mode verify
```
**What happens:** Runs live `nanochip/kpu/harness/audit.py`, live `verilator --lint-only -Wall`, and live `yosys` Nangate45 synthesis on `rtl/msh_deq.v`, then displays the complete full-chip Stage 4 evaluation scoreboard.

---

## 4. Socratic Reflection Questions

1. **Why Two-Pass `design -save preabc` in `synth_tech.ys`? (Ch. 6):** Read the header comment in `nanochip/kpu/harness/synth_tech.ys` (lines 7–20). Why does `synth_tech.ys` save a snapshot before the first `abc` call, report area on Pass 1, and reload `preabc` before running `buffer;upsize;dnsize;topo;stime,-c` in Pass 2? What happens if you call `abc` a second time without `design -load preabc`?
2. **Byte-Serial Intake vs. 16-Way Parallel Demux in `msh_deq.v` (Ch. 5 & Ch. 6):** Look at lines 63–66 of `nanochip/kpu/rtl/msh_deq.v`: *"one variable-index byte demux instead of 16 parallel ones — the demuxes were 96K gates of the module."* Why was sacrificing 15 bytes/cycle of intake bandwidth inside `msh_deq` completely free for end-to-end token throughput, yet transformative for chip area?
3. **Set-on-First-Write vs. Resetting SRAM Arrays (Ch. 6 & Ch. 7):** Why does `msh_gemv.v` (line 71) use set-on-first-write semantics (`g == 0` or first row of a group) for its `qacc` and `acc64` SRAM macros instead of clearing them on `rst_n`, and how does `+verilator+rand+reset+2` prove this is safe?
