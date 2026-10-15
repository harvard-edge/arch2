# Model Architecture (what the chip computes)

The `nano` instance of the **Moonshot hybrid text stack**: one **KDA
(Kimi Delta Attention) linear-attention** layer followed by one **NoPE
multi-head latent attention (MLA)** layer, a **sigmoid-routed
mixture-of-experts MLP with one shared expert** in each layer, and
**attention-residual mixing** with block size 2. There is **no positional
encoding anywhere** — no RoPE tables exist in this task; position
information is carried by KDA's decaying state and causal convs. The
embedding and LM head are **untied**. Out of scope, by design: MTP heads
and the tokenizer — the chip consumes token ids.

Reference: `reference/model.py` (float32, normative). Constants not in the
image header: RMSNorm eps `1e-5`, L2-norm eps
`1e-6`, KDA gate lower bound `-5.0`, router scaling factor `2.828`.

## nano configuration at a glance

| item | value |
|---|---|
| layers | 2 (L0 = KDA, L1 = NoPE-MLA) |
| d_model | 64 |
| KDA | 2 heads × 32 dims, delta rule + per-channel decay, kernel-4 causal conv |
| MLA | 2 heads, dk 32 + dr 16 (shared) / dv 32, compressed KV latent dc = 128 |
| MoE (per layer) | 8 experts (SwiGLU, d_ff 32), top-2 routed + 1 shared |
| vocab | 512 (embedding and LM head untied) |
| weights | int4, group-128 (runtime group_size 64 or 128, read from the header) |
| total weights | ~238k parameters, ≈135.5 KB packed (≈62.2 KB dense + 55.3 KB experts + 17.9 KB embedding) |
| **max context** | **64 positions** (`max_seq`, announced in the image header; evaluation may stretch sequence lengths within [8, 64]) |

Per-token state: KDA recurrent state S (2 heads × 32×32 values, constant
size), the MLA KV latent cache (144 values per position — the only state
that grows with context length), conv history (3 taps), and per-position
res-mix snapshots (alive only within one token).

## Layer skeleton (attention-residual mixing)

Per token at position `pos`, teacher-forced over the given sequence
(1-based layer number `n = li + 1`, block size `B = attn_res_block`):

```
x = emb[token]                       # dequantized int4 row
blocks = []                          # per-POSITION snapshots, no cross-token state
for each layer li (type from header bitmap):
    boundary = (li % B == 0)
    prefix = x
    if boundary: blocks.append(x)
    mix_in = blocks[:-1] if boundary else blocks
    if mix_in:  x = res_mix(x, mix_in, res_attn_li)      # see below
    a = TokenMixer_li( RMSNorm(x, norm1) )
    prefix = a if boundary else prefix + a
    x = res_mix(prefix, blocks, res_mlp_li)
    m = MoE_li( RMSNorm(x, norm2) )
    x = prefix + m
x = res_mix(x, blocks, res_out)
logits = RMSNorm(x, final_norm) @ head               # untied LM head
argmax with lowest-index tie break
```

At block boundaries the running residual is snapshotted into `blocks` and
the prefix-sum **restarts** from the attention output; the past re-enters
through the mixtures. `res_mix(prefix, blocks, {norm, proj})` is a softmax
mixture over the candidates `blocks + [prefix]` (oldest snapshot first):

```
logit_n = < RMSNorm(v_n, norm.w) , proj >        # one scalar per candidate
p = softmax(logits);  out = sum_n p_n * v_n      # mixes the RAW candidates
```

## RMSNorm (1-centered offsets)

All norm weights ship as offsets around 1: `y = x / sqrt(mean(x²) + 1e-5)
· (1 + w)`.

## MLA layer (`layer_types` bit = 1; every 4th layer)

Dimensions: H = `n_heads`, dk = `mla_dk`, dr = `mla_dr`, dv = `mla_dv`,
dc = `mla_dc` (the compressed KV latent — note dc may exceed d_model).

1. Latent: `c = RMSNorm(x @ wc, knorm)`  (dc; normed once, shared by k/v).
2. Queries from x: `qc = x @ wq_c` → [H, dk], `qr = x @ wq_r` → [H, dr].
3. Keys/values: `kc = c @ wk_c` → [H, dk]; `kr = x @ wk_r` → [dr],
   **shared by all heads**; `v = c @ wv` → [H, dv].
4. Per head: `q_h = [qc_h, qr_h]`, `k_h = [kc_h, kr]` (dk+dr each).
   **Nothing is rotated** (NoPE) — the r-part is just extra channels.
5. `ctx_h = softmax(q_h·Kᵀ / sqrt(dk+dr)) · V` over all cached positions;
   concat heads → output projection → into the residual as `a`.

No QK-norm, no output gate. The KV cache holds k and v for all previous
positions (caching the latent `c` + `kr` instead and re-expanding is an
equivalent, smaller-footprint choice — the cache is yours).

## KDA layer (3 of every 4 layers)

Dimensions: H = `kda_heads`, dh = `kda_dim`, P = H·dh. The low-rank
projections have rank dh.

1. Projections from the normed input: `q = x@Wq`, `k = x@Wk`, `v = x@Wv`
   (P each), `beta_in = x@Wb` (H), decay input `f = (x@Wf1)@Wf2` (P, no
   activation between the two factors), output gate `z = (x@Wg1)@Wg2` (P).
2. **Separate causal depthwise convs (kernel 4)** on q, k and v over each
   stream's previous 3 *pre-conv* values (state you must keep), then SiLU.
3. Per head: L2-normalize q and k (`eps = 1e-6`).
4. Gates: `beta = sigmoid(beta_in)` per head; per-CHANNEL decay
   `alpha = exp( -5 · sigmoid( A_h · (f + dt_bias) ) )` with
   `A_h = exp(A_log)` shipped as unsigned Q8.8 per head, `dt_bias` per
   channel; alpha ∈ (e⁻⁵, 1), shape [H, dh].
5. **Delta rule** on state S (per head [dh, dh], zeros at sequence start;
   decay FIRST, readout from the UPDATED state):
   ```
   S   = diag(alpha_h) · S            # per-key-channel decay
   u   = v − k·S                      # prediction error
   S   = S + outer(beta·k, u)
   out = (q·S) / sqrt(dh)
   ```
6. Gated norm per head: `RMSNorm(out, onorm) · sigmoid(z_h)` (onorm weight
   shared across heads; the gate is a plain sigmoid, NOT SiLU), concat →
   output projection.

## MoE MLP (every layer)

E = `n_experts` experts of SwiGLU shape (d_model → d_ff → d_model), one
shared expert of the same shape, `top_k` routed:

```
s   = sigmoid(x @ router)                    # [E], router is bias-free
sel = top_k indices of (s + bias)            # score-correction bias biases
                                             # SELECTION only; stable ties
                                             # break to the lowest index
w   = s[sel] / sum(s[sel]) * 2.828           # renormalized raw scores
out = shared(x) + sum_i w_i * expert_sel[i](x)
```

`expert(x) = down( silu(gate(x)) ⊙ up(x) )`. The shared expert is always
on and unweighted. The score-correction `bias` ships as int16 Q4.11.

## Fidelity notes (non-normative)

* KDA is defined in its recurrent token-by-token form — the mathematical
  definition; chunked training kernels are an optimization of the same
  recurrence.
* Weights are synthetic (seeded int4). Correctness is always judged against
  `reference/model.py`, never against a trained checkpoint.
* Expert selection is part of the computation: the reference and the chip
  dequantize the same router weights, so an honest datapath reproduces the
  same top-k set; the near-tie logit forgiveness in scoring absorbs the
  rare borderline-router rounding case at the logits level.
* Teacher forcing (judge each step from an identical fed state) is what
  makes tolerance-based correctness well-posed — a free-running greedy
  decode would diverge at the first rounding difference. Your datapath is
  still a decoder datapath; only the token feed comes from the image
  instead of your own argmax.
