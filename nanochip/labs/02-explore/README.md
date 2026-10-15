# Lab 02 — Stage 2: Explore (`02-explore`)

**Title:** *Roofline Betting & Candidate Generation*
**Lifecycle Stage:** `2. Explore`
**Book Alignment:** Part II — *Loop Mechanics* (Chapter 4: *Data, Knowledge, and Representation*, Chapter 5: *Prediction, Generation, and Optimization*)
**Target Artifact:** [`nanochip/kpu/reference/gen_weights.py`](../../kpu/reference/gen_weights.py), [`nanochip/kpu/docs/quantization.md`](../../kpu/docs/quantization.md), [`nanochip/kpu/rtl/msh_fetch.v`](../../kpu/rtl/msh_fetch.v), [`nanochip/kpu/rtl/msh_gemv.v`](../../kpu/rtl/msh_gemv.v)

---

## 1. What Breaks Without This Stage: Roofline Hallucination

When you ask an unguarded LLM to *"design an accelerator that hits `20,000 tokens/sec` at `100 MHz` (`5,000 cycles/token`),"* its default instinct is **compute-centric hallucination**:
- *"Let's instantiate a 64-wide or 128-wide FP16 MAC array so matrix-vector multiplications finish in a few hundred cycles!"*
- Or: *"Let's dequantize INT4 weights to FP16 in a preprocessing pass and write them back to DRAM so the MAC unit stays simple!"*

Both proposals violate **Conservation of Bytes** on batch-1 autoregressive decode. Across a `16 B/cycle` (128-bit) external memory port running at `100 MHz` (`1.6 GB/s` peak pin bandwidth):
- The active per-token parameter footprint of `nano` (all dense KDA/MLA projections + shared expert + top-2 routed SwiGLU experts per layer + 1 embedding row) is **152,224 weights**.
- In **FP32** (`4 B/weight`), streaming those active weights once per token transfers **`608,896 B/tok`** $\rightarrow$ a minimum pin-bandwidth floor of **`38,056 cycles/tok`** (**max `2,627.7 tok/s`** even with infinite compute!).
- In **FP16** (`2 B/weight`), streaming those active weights transfers **`304,448 B/tok`** $\rightarrow$ a minimum pin-bandwidth floor of **`19,028 cycles/tok`** (**max `5,255.4 tok/s`** with zero compute overhead!).

As `docs/TASK_SPEC.md` warns:
> *"The int4$\rightarrow$dequant$\rightarrow$MAC pipeline: never write dequantized weights back to external memory — you'd double your bandwidth and lose the roofline race."*

Without a **Stage 2 (`Explore`) analytical filter**, an agent will spend hours generating, debugging, and synthesizing a wide-MAC FP16 datapath that is guaranteed by physics to miss the target by nearly $4\times$.

---

## 2. How Kimi K3's `nano-kpu` Implements Stage 2

1. **Exact Byte-Traffic Roofline Accounting (`reference/gen_weights.py`):**
   - `active_weight_bytes(nano)` sums every packed INT4 tensor (`0.5 B/elem`), group-128 scale (`int16`, `2 B`), group-128 zero-point (`uint8`, `1 B`), and small parameter (`int16`, `2 B`) touched by a single token: **`76,109 B/token`** (`76,112 B` 16B-aligned).
   - Dividing by `16 B/cycle` yields the theoretical uncached roofline floor: **`4,757 cycles/token`** (**`21,021.7 tok/s`** at `100 MHz`).
   - `floor_weight_bytes(nano)` computes the mandatory dense tensor bytes (`62,250 B/token` = `3,891` beats) that every valid run must read from DRAM, preventing an agent from faking completion without reading weights.

2. **On-Chip Residency Betting (`hq` Shadow Buffer in `msh_fetch.v`):**
   - Kimi K3 noticed that the untied LM head (`head.q`: $64 \times 512$ INT4 = `16,384 B`, or `16,096 B` amortized after initial fill across `seq_len=48`) is token-independent and invoked on every token.
   - By allocating a **16 KiB `hq` shadow buffer** in `msh_fetch.v` (`256 x 256b` `msh_sram`), `head.q` is fetched from DRAM **once per sequence** (`TG_HQ`) and re-read on-chip at **2 beats/cycle (`32 B/cycle`)**, saving ~`1,006 DRAM cycles/token` and lowering steady-state external DRAM reads to **`63,524.7 B/token`** (`3,842.2 read beats/token` across `seq_len=48`).

3. **Pre-Committed Analytical Cycle Model (`REPORT.md` `perf-model`):**
   - Before running final evaluation, the architect commits a ```json perf-model``` block predicting steady-state `cycles_per_token`:
     $$\text{Predicted } \text{CPT}_{\text{nano}} = 11,200 \text{ cycles/token}$$
   - Full-chip Verilator simulation measures **`11,467.125 cycles/token`** (`550,422` cycles / `48` tokens) — a **`2.33%` relative prediction error**, proving that Kimi K3's world model accurately captured DRAM streaming, dual-parity `qacc` MAC throughput, and engine serialization.

---

## 3. Hands-On Exercises

### Exercise A — `--mode break` (Refute the 20,000 tok/s FP16 Hallucination)
```bash
python3 nanochip/labs/02-explore/lab.py --mode break
```
**What happens:** Evaluates an unguarded LLM candidate proposing a 64-MAC FP16 engine claiming `20,000 tok/s` (`5,000 cyc/tok`) over the `16 B/cycle` memory port. The Stage 2 analytical referee computes the conservation-of-bytes lower bound (`304,448 B/tok / 16 B/cyc = 19,028 cyc/tok` $\rightarrow$ `5,255.4 tok/s` ceiling) and rejects the candidate in `< 10 ms` before Verilator or Yosys is ever invoked.

### Exercise B — `--mode verify` (Compute Exact Rooflines & Verify `perf-model`)
```bash
python3 nanochip/labs/02-explore/lab.py --mode verify
```
**What happens:** Calls `nanochip/kpu/reference/gen_weights.py` to break down `nano` tensor bytes by category (dense KDA, dense MLA, shared expert, top-2 routed experts, LM head, embedding row), compares FP32 vs. FP16 vs. INT4 group-128 vs. INT4 + `hq` shadow buffer rooflines, and verifies Kimi K3's `11,200 cyc/tok` analytical prediction against the `11,467.125 cyc/tok` RTL measurement (`2.33%` error).

---

## 4. Socratic Reflection Questions

1. **Why MoE Changes the Roofline Numerator (Ch. 4 & Ch. 5):** The total packed weight footprint of `nano` is `~135.5 KB`, yet `active_weight_bytes(nano)` is only `76,109 B` (`~74.3 KiB`). Which tensors account for the difference, and why does `evaluate.py` price the roofline against `active_weight_bytes` while policing protocol legality against `floor_weight_bytes` (`62,250 B`)?
2. **Why Cache `head.q` Instead of MoE Experts? (Ch. 5):** Given that `msh_chip_top` uses only `0.861 MiB` of its `4.0 MiB` SRAM budget, why did Kimi K3 dedicate a 16 KiB shadow buffer (`hq`) to `head.q` (`64 x 512`) first, and what happens to the area budget (`4.0 mm^2` at `1.0 Mbit/mm^2`) if you try to cache all weights on-chip?
3. **World-Model Calibration as an Anti-Goodhart Signal (Ch. 5 & Ch. 10):** Why does `TASK_SPEC.md` ask the architect to commit `{"cycles_per_token": {"nano": N}}` in git *before* running the measurement? What does a `2.33%` analytical-to-RTL error prove that a raw throughput number alone cannot?
