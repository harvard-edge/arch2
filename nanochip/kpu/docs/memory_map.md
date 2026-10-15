# Memory Image Layout (version 1)

Built by `harness/memmap.py::build_image` (normative). Little-endian
throughout. All regions start 16-byte aligned. Addresses are byte addresses
in the external memory the testbench preloads.

## Header (address 0, 256 bytes, uint32 words)

| word | field | word | field |
|---|---|---|---|
| 0 | magic `0x4B444143` ("KDAC") | 16 | `attn_res_block` (residual-mix block size) |
| 1 | version = 1 | 17 | `vocab` |
| 2 | `n_layers` | 18 | `max_seq` |
| 3 | `d_model` | 19 | `seq_len` (tokens in this run) |
| 4 | `n_heads` (MLA) | 20 | `group_size` (int4 quant) |
| 5 | `mla_dk` | 21 | layer-type bitmap (bit i = 1 → layer i MLA, 0 → KDA) |
| 6 | `mla_dr` | 22 | `n_tensors` (descriptor count) |
| 7 | `mla_dv` | 23 | descriptor table address |
| 8 | `mla_dc` | 24 | token sequence address |
| 9 | `kda_heads` | 25 | output logits address |
| 10 | `kda_dim` | 26 | output argmax address |
| 11 | `conv_kernel` (= 4) | 27 | output status address |
| 12 | `n_experts` | 28 | scratch address |
| 13 | `top_k` | 29 | scratch bytes |
| 14 | `n_shared` (= 1) | 30 | logit row stride bytes (= align16(vocab·4)) |
| 15 | `d_ff` (per expert) | 31 | `n_positions` (= seq_len) |

Words 32–63 are zero (reserved).

## Descriptor table

`n_tensors` entries of 16 bytes: `{uint32 name_hash, uint32 addr,
uint32 nbytes, uint32 aux}`.

* Order is **fixed and canonical**: exactly
  `reference/gen_weights.py::tensor_list` order. Per matmul tensor the
  triple `.q` (packed int4), `.s` (scales int16 Q3.12), `.z` (zeros uint8)
  appears consecutively; small int16 params are single entries. Sequence:
  `emb.q/.s/.z`, then per layer
  `res_attn.norm.w`, `res_attn.proj`, `norm1.w`,
  the token-mixer tensors
  (MLA: `mla.wc/wq_c/wq_r/wk_c/wk_r/wv/o` triples + `mla.knorm.w`;
  KDA: `kda.q/k/v/b/f1/f2/g1/g2/o` triples + `kda.qconv`, `kda.kconv`,
  `kda.vconv`, `kda.A`, `kda.dtb`, `kda.onorm.w`),
  `res_mlp.norm.w`, `res_mlp.proj`, `norm2.w`,
  then the MoE block: `moe.router` triple, `moe.bias`,
  `moe.shared.g/.u/.d` triples, and `moe.e0` … `moe.e{E-1}` as `.g/.u/.d`
  triples — **9 consecutive descriptor entries per expert**, so expert j's
  entries sit at a fixed stride from `moe.e0`'s;
  finally `res_out.norm.w`, `res_out.proj`, `final_norm.w`, and the
  `head.q/.s/.z` triple last.
* `aux` = fan_in for `.q` entries (convenience/sanity), 0 otherwise.
* `name_hash` = FNV-1a-32 of the tensor name (sanity only; order suffices).

Formats and dequantization: `docs/quantization.md`. Standard `.q` tensors
are `[fan_in/2, fan_out]` row-major (fan_out fastest); `emb.q` is
token-major `[vocab, d_model/2]`.

## Tokens / outputs / scratch

* Token sequence: `seq_len` uint32 ids (teacher-forced input).
* Logits out: `seq_len` rows, row p at `logits_addr + p·stride`; the first
  `vocab·4` bytes of a row are int32 logits in vocab order (your scale;
  per-row consistency is all that cosine needs).
* Argmax out: `seq_len` uint32 ids (lowest-index tie break).
* Status out: 16-byte block; word 0 must become `0x600DD00D`, written last.
* Scratch: yours (KV cache, KDA state, conv history, spills);
  zero-initialized; never inspected. The attention-residual snapshots are
  per position and need no cross-token storage.
