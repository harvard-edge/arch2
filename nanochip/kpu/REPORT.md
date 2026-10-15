# Moonshot `nano-kpu` Architectural Report (`msh_chip_top`)

## 1. Executive Summary

`msh_chip_top` implements a complete, self-configuring, bit-exact hardware accelerator for the `nano` configuration of the Moonshot hybrid text architecture: repeating `[KDA, MLA]` token-mixer blocks (Kimi Delta Attention linear attention with per-channel decay and causal depthwise convolution in Layer 0, followed by NoPE Multi-head Latent Attention in Layer 1), fine-grained sigmoid-routed Mixture-of-Experts (MoE) MLPs with 8 routed experts (`top_k=2`) and 1 shared expert per layer, block-2 attention-residual mixing, RMSNorm with 1-centered offsets, and untied INT4 group-quantized embedding and LM head.

Across the public `nano` evaluation suite (`seed=20260706`, `seq_lens=(48, 16)`, `group_size=128`), the design achieves:
- **Throughput (`nano` long run, `seq_len=48`):** `550,420` total cycles = **`11,467.083 cycles/token`** (**`8,720.61 tokens/s`** at the 100 MHz target clock; **`2,180.15x`** speedup over the `4.0 tok/s` baseline).
- **Analytical Performance Model Accuracy:** Predicted `11,200.0 cycles/token` vs. measured `11,467.1 cycles/token` (**`2.33%` relative error**).
- **Numerical Fidelity (`reference/model.py` float32 golden):** Minimum row cosine similarity `cos_min = 1.0000` on both `seq_len=48` (`run 0`) and `seq_len=16` (`run 1`), with `100.0%` (`1.0000`) pooled argmax agreement.
- **Bit-Exact C-Model Verification (`rtl/selfmodel/fxmodel.py`):** `all_match = True` (`0` differing int32 logits across all `48 x 512` and `16 x 512` output positions).
- **Hardware Realism & Chaos Resilience:**
  - `check_integrity.py`: `OK` (`0` modified frozen harness files)
  - `audit.py`: `OK` (`0` hard violations, `8` informational ROM `$readmemh` flags, all storage mapped to `msh_sram`/`msh_rom` macros)
  - `verilator --lint-only -Wall`: `0` errors, `1` warning (`<= 40` gate)
  - `randreset` (`+verilator+rand+reset+2`): `byte_identical = True`
  - `2x DRAM latency sweep` (`lat_base` doubled from `24` to `48` cycles): `elasticity = 1.0091` (`177,591 -> 179,211` cycles on `seq_len=16`, `< 1%` sensitivity).

---

## 2. Analytical Performance Model (`perf-model`)

```json perf-model
{
  "cycles_per_token": {
    "nano": 11200
  }
}
```

### 2.1 Bandwidth Roofline & Byte Accounting (`nano`)

For the `nano` configuration (`d_model=64`, `n_layers=2`, `layer_pattern="LF"`, `n_heads=2`, `mla_dk=32`, `mla_dr=16`, `mla_dv=32`, `mla_dc=128`, `kda_heads=2`, `kda_dim=32`, `conv_kernel=4`, `n_experts=8`, `top_k=2`, `n_shared=1`, `d_ff=32`, `vocab=512`, `group_size=128`):

1. **Ideal Uncached Active Weight Stream (`active_weight_bytes`):**
   - **Dense weights + small parameters (`floor_weight_bytes`):** `62,216 B` per token (includes all KDA/MLA projections, router weights, shared expert weights, small `p16` norms/biases/convs, and the untied `64 x 512` LM head).
   - **Active routed MoE experts (`n_layers * top_k = 4` active expert evaluations/token):** Each expert (`g`, `u`, `d` projections of shape `64x32` and `32x64` in INT4 + `s16` + `z8`) occupies `3,464 B`, totaling `4 * 3,464 = 13,856 B` per token.
   - **Token embedding row (`emb_row`):** `64 / 2 + 1 * 3 = 35 B` (`q4` + `s16` + `z8`).
   - **Total uncached active bytes/token:** `76,112 B/token`.
   - At the harness DRAM port ceiling of `16 B/cycle`, the uncached INT4 roofline is:
     $$\text{Roofline Beats/Token} = \left\lceil \frac{76,112}{16} \right\rceil = 4,757 \text{ cycles/token} \quad (228,336 \text{ cycles for } T=48).$$
   - By contrast, streaming uncompressed FP16 weights (`304,448 B/token`) would require at least `19,028 cycles/token` (`5,255 tok/s` ceiling at 100 MHz), making `>8,000 tok/s` physically impossible without Layer 3 INT4 hardware-algorithm co-design.

2. **On-Chip Residency Optimizations in `msh_chip_top`:**
   - **Small parameter residency (`WBUF`):** All `1,970` `int16` small parameters (`3,940 B`) are walked once at startup into `msh_wbuf` (`2048 x 16b`), eliminating per-token DRAM fetches for RMSNorm, conv kernels, KDA `A`/`dtb`, and residual-mix vectors.
   - **LM-Head Scale/Zero Residency (`HS`/`HZ`) & `head.q` Shadow Buffer (`u_hqbuf`):** The untied LM head (`head.q` = `16,384 B`, `head.s` = `1,024 B`, `head.z` = `512 B`) is token-independent. `head.s` and `head.z` are preloaded at startup into `msh_hsz`. During the first token's head GEMV, `msh_fetch` diverts the `1,024` `head.q` beats (`TG_HQ`, `16 KiB`) into an on-chip `512 x 256b` shadow SRAM (`u_hqbuf`). On tokens `1..T-1`, `msh_gemv` drains `u_hqbuf` directly at **2 beats/cycle (`32 B/cycle`)** via `hq_pop2` without touching DRAM.
   - **Net DRAM Beats (`seq_len=48`):** This reduces actual DRAM read traffic from `4,757` beats/token to **`3,429.19 read beats/token`** (`164,601` read beats + `6,193` write beats across 48 tokens = **`56,931.333 B/token`** total DRAM traffic, comfortably above the dense protocol floor while saving `~18 KiB/token` of off-chip weight re-streaming).

### 2.2 Cycle Breakdown per Token (`11,200` Predicted vs. `11,467.1` Measured)

Because `msh_seq` serializes engine dispatches (`deq`, `vec`, `gemv`, `kda`, `mla`) while `msh_fetch` prefetches weight segments autonomously across the 24-cycle DRAM latency pipe, the steady-state per-token cycle count is the sum of serialized engine execution and non-overlapped stream drain:

| Subsystem / Phase | Analytical Cycles / Token | Architectural Determinants |
|---|---:|---|
| **1. Embedding Dequant (`msh_deq`)** | `110` | 3 segments (`s`, `z`, `q`), byte-serial intake (`1 B/cyc` to avoid 16-way demux area bloat) + 16-word `Y` writeout (`64` lanes). |
| **2. Layer 0 (`KDA`) Projections (`msh_gemv` x9)** | `2,180` | 9 INT4 GEMVs (`q, k, v, b, f1, f2, g1, g2, o`), streamed from DRAM with fused `sum(q-z)x = sum(qx) - z*sum(x)` dequant and 16-lane fold pipeline. |
| **3. Layer 0 `KDA` Recurrence & Conv (`msh_vec` + `msh_kda`)** | `1,640` | 3x causal `V_CONV` (`K=4` + SiLU), 2x `V_L2NORM`, `V_PREALPHA` + `V_ALPHA`, `msh_kda` 2-head `32x32` software-pipelined `pass1`/`pass2` delta rule (`4 rows/cyc`), `onorm` + `V_MULZ`. |
| **4. Layer 1 (`MLA`) Projections (`msh_gemv` x7)** | `2,260` | 7 INT4 GEMVs (`wc` `64->128`, `knorm`, `wq_c`, `wq_r`, `wk_c`, `wk_r`, `wv`, `o`), streamed through the 256-beat FIFO + dual-parity `qacc` SRAMs. |
| **5. Layer 1 `MLA` KV-Cache Attention (`msh_mla`)** | `780` | Parallel `K`/`V` cache write at `pos`, `ST_ATT` (`4 dims/cyc` over `t=0..pos`, average `pos=23.5` on `T=48`), `expneg` LUT, `recip` LUT, `ST_CTX` (`4 dims/cyc`). |
| **6. MoE Blocks (`L0` + `L1`, router + shared + top-2 experts)** | `2,790` | Per layer: `router` GEMV + `V_SIG` + `V_TOPK` (`E=8, k=2`) + 3x3 GEMVs (`shared` + 2 routed experts, `g/u/d`) + `V_SILU`/`V_MULZ`/`V_MACW`. |
| **7. Residual Mixing (`res_attn`, `res_mlp`, `res_out`) & Norms** | `520` | `V_RMSNORM` (25-cycle exact divider + sumsq + apply), `V_DOT`, `V_SMIX` softmax mixture across block snapshots. |
| **8. LM Head GEMV (`head`, `64 -> 512`) & Logits/Argmax Writeback** | `620` | Drains `u_hqbuf` at `32 B/cyc` (`2-beat` intake + `a_pair` dual-chunk MACs into even/odd `qacc` banks) + 32-block fold + `128`-beat `LG` to DRAM writeout. |
| **9. Startup Amortization (`HDR` + `DESC` + `WBUF` + `HS/HZ` + `ST_CLEAR`)** | `300` | ~`14,400` startup/reset-clear cycles (`msh_vec` `13,824`-cycle conv-history clear + `msh_seq` descriptor/param walk) amortized over `T=48` tokens. |
| **Total Analytical Prediction** | **`11,200.0`** | **Measured on `nano` (`T=48`): `11,467.083` cycles/token (`+267.1` cyc/tok = `2.33%` error, from DRAM jitter `--lat-jitter=12` & segment tail flushes).** |

---

## 3. Microarchitectural Co-Design Highlights

### 3.1 Algebraic Zero-Point Fold & Dual-Parity Accumulators (`msh_gemv.v`)
Rather than expanding INT4 weights to FP16/INT16 in memory or inserting per-MAC subtractors, `msh_gemv` factors the asymmetric group dequantization algebraically:
$$\sum_{k \in g} (q_{k,c} - z_{g,c}) \, x_k = \left(\sum_{k \in g} q_{k,c} \, x_k\right) - z_{g,c} \sum_{k \in g} x_k$$
- During the `S_RUN` MAC phase, 16-column chunks compute unsigned nibble products $q_{\text{lo}} x_{2r} + q_{\text{hi}} x_{2r+1}$ and accumulate scalar `xsum` ($\sum x_k$) once per row.
- To support **2-chunk/cycle pair issue (`a_pair`)** without dual-port SRAM area overhead, the `1024`-bit group accumulator `qacc` is partitioned into two single-port `msh_sram` banks by column-word parity (`u_qacc_a` for even 16-column blocks `col[4]==0`, `u_qacc_b` for odd blocks `col[4]==1`), each equipped with a 1-entry write-to-read forwarding bypass (`qwA_fwd` / `qwB_fwd`) to hide the 1-cycle synchronous SRAM read latency on back-to-back rows.
- At the end of each quantization group (`S_FOLD`), a 4-stage pipeline (`F1a -> F1b -> F2 -> F3`) applies $s_{g,c} \cdot (\text{qacc}_c - z_{g,c} \cdot \text{xsum})$ across all 16 lanes in a single cycle.

### 3.2 Byte-Serial `msh_deq.v` Intake (Eliminating 96K Gates of Parallel Demuxes)
In `msh_deq.v` (lines 63–65), early exploration of 16-way parallel byte-stream demultiplexing (`for (b=0; b<16; b++) qrow_v[8*(pos+b) +: 8] <= ...`) synthesized to **16 parallel variable-index 1024-bit byte demux trees** (~96K gates, exploding logic area and unbuffered wireload delay). Because embedding dequantization transfers only `35 B` per token (`32 B` `q`, `2 B` `s`, `1 B` `z`), switching `msh_deq` to a **1-byte/cycle shift-register beat emitter (`beat_r >> 8`)** costs `< 35` cycles/token (< `0.3%` runtime) while collapsing `msh_deq` down to **2,756 cells (`3,407.7 um^2` in Nangate45, `1.224 ns` critical path)**.

### 3.3 Latency-Elastic Credit-Tracked Prefetch (`msh_fetch.v`)
`msh_fetch` decouples the 24-cycle minimum DRAM latency (plus up to 24 cycles of jitter and 5% request stalls on short stress runs) from the execution engines using:
- A **64-entry First-Word-Fall-Through (FWFT) segment queue** (`sq_addr_v`, `sq_len_v`, `sq_tag_v`) fed ahead by `msh_seq`.
- A **256-beat (`4 KiB`) credit-tracked response FIFO** mapped onto two `msh_sram` macros (`u_fifo_data` `128 x 256b` + `u_fifo_meta` `128 x 32b`).
- Reads issue whenever `(wr_ptr - rd_ptr) < 256`, guaranteeing pre-allocated response slots so `mem_rsp_ready` is permanently tied high (`1'b1`) and never drops a beat.
- When base DRAM latency is doubled from `24` to `48` cycles (`do_latency_sweep`), total cycles on `nano` short run increase by only **`0.91%`** (`elasticity = 1.0091`).

### 3.4 Reset Robustness (`+verilator+rand+reset+2`)
Every control register is explicitly reset under `rst_n`, and all stateful SRAMs that are read before full overwrite (`msh_fetch` FIFO macros, `msh_vec` causal conv history, `msh_kda` recurrent state `S`, and `msh_mla` `K`/`V` caches) run deterministic hardware clear sweeps (`clr_active` / `ST_CLEAR` / `S_CLR`) immediately after reset while holding `ready` low. Accumulator SRAMs (`qacc`, `acc64`) use `set-on-first-row/group` semantics (`b1dA_set`, `f1_g0`), ensuring **100% byte-identical output** under randomized initial flop and SRAM states.
