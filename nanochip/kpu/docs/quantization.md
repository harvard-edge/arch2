# Numerics & Weight Format

Normative code: `reference/model.py` (dequant + float32 math). This page
is the readable companion.

## The freedom rule

The reference computes in float32. Your chip does NOT have to: any internal
representation (fixed point, block floating point, fp16, LUT-approximated
nonlinearities of your chosen resolution) is legal as long as the emitted
logits clear the cosine/argmax bars (`harness/scoring.py`). Choosing formats is
the design problem — precision costs area and cycle time, sloppiness costs
correctness. Two things are NOT free:

* the **input** format — weights arrive int4-packed as specified below and
  scales/zeros/params as integers; your chip must consume these bytes;
* the **output** format — int32 logits rows (any per-row scale, cosine is
  scale-invariant) and uint32 argmax ids.

## Int4 weight format (AWQ/GPTQ-style)

Standard matmul tensors `<t>` come as three arrays (see
`docs/memory_map.md` for placement):

```
<t>.q : uint8 [fan_in/2, fan_out]   packed along fan_in:
        byte at row r, col c holds w[2r,c] in bits[3:0], w[2r+1,c] in bits[7:4]
<t>.s : int16 [ceil(fan_in/g), fan_out]   scales, Q3.12 (value = s * 2^-12)
<t>.z : uint8 [ceil(fan_in/g), fan_out]   zero points, 0..15
g = min(group_size, fan_in)        # group_size = header word 20.
                                   # Public nano uses 128; hidden evaluation
                                   # may use 64 or 128. Read the header —
                                   # do not hardcode 128.

w[k,c] = (q[k,c] - z[k//g, c]) * s[k//g, c] * 2^-12      (float32 in the ref)
```

Every routed expert, the shared expert, the router, all KDA/MLA
projections and the LM head `head` use this layout. The embedding `emb`
is **token-major** so a row lookup is one contiguous burst: `emb.q` is
uint8 `[vocab, d_model/2]` (packed along d_model within each token row),
and groups run along d_model per row: `emb.s`/`emb.z` are
`[vocab, ceil(d_model/g)]`.
`w[t,i] = (q[t,i] - z[t,i//g]) * s[t,i//g] * 2^-12`. The LM head is
**untied** — a separate standard-layout tensor (`head`, fan_in = d_model,
fan_out = vocab).

Why int4 matters: batch-1 decode is **bandwidth-bound**. The memory port
moves 16 B/cycle; the packed weights are the dominant traffic. MoE changes
the accounting: the per-token ACTIVE stream (dense tensors + top_k routed
experts per layer + one embedding row; `reference/gen_weights.py::
active_weight_bytes`) is what the roofline prices — nano is about 0.073 MiB
per token if uncached. The performance roofline
assumes the active int4 stream flows **once** per token with dequant fused
into the datapath — a design that expands weights to a wider format in
external memory pays double bandwidth and cannot reach it.

## Small parameters (int16 fixed point)

| params | format | dequant |
|---|---|---|
| `norm1/norm2/final_norm/knorm/onorm` and residual-mix `*.norm.w` offsets | Q2.13 | `1 + v·2^-13` (1-centered gain) |
| `kda.{q,k,v}conv` (depthwise kernels), `kda.dtb` (dt_bias), residual-mix `*.proj`, `moe.bias` (score-correction) | Q4.11 | `v·2^-11` |
| `kda.A` (= exp(A_log), positive, per head) | unsigned Q8.8 | `v·2^-8` |

## Reference nonlinearities (what you are approximating)

`silu(x) = x·sigmoid(x)` (convs, SwiGLU), `sigmoid` (beta, KDA output
gate, router scores), the KDA decay `alpha = exp(-5·sigmoid(·))` (a
bounded 1-D function — LUT-friendly), `softmax` with max-subtraction
(attention and residual mixing), RMSNorm with `eps = 1e-5`, L2-norm with
`eps = 1e-6`, and the top-k renormalization divide. How you realize them
(LUT size, interpolation, iteration count) is your call — validate against
the per-layer dumps and the final cosine. No frozen numeric artifacts ship
with this task; any ROM you use needs a disclosed generator (see
harness/audit.py, R1.4).

## Error-budget intuition (non-normative)

cos ≥ 0.98 alone tolerates ~20 % relative logits error — very loose. The
binding constraints in practice are (a) **argmax agreement ≥ 0.99** (top-1
margins are fractions of the logit RMS ≈ 1.0, so systematic per-row error
must stay small), and (b) **error compounding** through the layers and two
kinds of recurrent state that never forget (KDA's decayed state and the
MLA KV cache), plus a router whose top-k selection quantizes hidden-state
error into discrete expert choices. Aim well above the bar at layer level;
watch the long-sequence run specifically.
