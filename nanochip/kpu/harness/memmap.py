"""Memory-image packer / result parser. Defines the chip-visible memory map
(normative together with docs/memory_map.md and docs/interface.md).
Image format version 1 (cosine-similarity evaluation, int4 weights,
teacher-forced sequences, MoE descriptor layout).

Layout (all regions 16-byte aligned, little-endian):
  header (256 B) | descriptor table | tensors | token sequence
  | output logits (zeroed) | output argmax | status | scratch
"""

import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from reference.config import ModelConfig            # noqa: E402
from reference.gen_weights import tensor_list       # noqa: E402
from reference.model import matmul_shapes           # noqa: E402
from reference.prng import fnv1a64                  # noqa: E402

MAGIC = 0x4B444143            # "KDAC"
VERSION = 1
HEADER_BYTES = 256
DONE_WORD = 0x600DD00D
MEM_LATENCY_MIN = 24    # minimum RAM read latency in cycles (normative;
                        # actual latency varies per request, in order)


def fnv1a32(s: str) -> int:
    return fnv1a64(s) & 0xFFFFFFFF


def _align16(n: int) -> int:
    return (n + 15) & ~15


def logit_row_stride(vocab: int) -> int:
    return _align16(vocab * 4)


def _tensor_bytes(arr, tag) -> bytes:
    a = np.asarray(arr, np.int64)
    if tag in ("q4", "z8"):
        return a.astype(np.uint8).tobytes()
    if tag == "s16":
        return a.astype("<i2").tobytes()
    if tag == "p16":
        return a.astype("<i2").tobytes()
    raise ValueError(tag)


def build_image(cfg: ModelConfig, weights: dict, tokens: np.ndarray) -> dict:
    """Returns {'image': bytes, 'layout': {...}}."""
    c = cfg
    seq_len = len(tokens)
    chunks = []
    cursor = HEADER_BYTES

    def put(data: bytes):
        nonlocal cursor
        addr = cursor
        chunks.append((addr, data))
        cursor = _align16(cursor + len(data))
        return addr

    # ---- descriptor table + tensors (canonical order) ----
    shapes = matmul_shapes(c)
    entries = []
    for name, shape, tag in tensor_list(c):
        data = _tensor_bytes(weights[name], tag)
        if tag == "q4":
            base = name[:-2]
            aux = c.d_model if base == "emb" else shapes[base][0]  # fan_in
        else:
            aux = 0
        entries.append((name, data, aux))
    desc_addr = cursor
    cursor = _align16(cursor + 16 * len(entries))
    tensor_addrs = {name: put(data) for name, data, _ in entries}
    desc = b"".join(struct.pack("<IIII", fnv1a32(nm), tensor_addrs[nm],
                                len(data), aux)
                    for nm, data, aux in entries)
    chunks.append((desc_addr, desc))

    # ---- tokens / outputs / scratch ----
    tokens_addr = put(np.asarray(tokens, np.int64).astype("<u4").tobytes())
    stride = logit_row_stride(c.vocab)
    out_logits_addr = put(b"\x00" * (seq_len * stride))
    out_argmax_addr = put(b"\x00" * (seq_len * 4))
    out_status_addr = put(b"\x00" * 16)
    kv_bytes = c.max_seq * c.n_heads * (c.mla_dk + c.mla_dr + c.mla_dv) * 2 \
        * c.layer_types.count("F")
    st_bytes = (c.kda_heads * c.kda_dim * c.kda_dim
                + 3 * (c.conv_kernel - 1) * c.kda_heads * c.kda_dim) * 4 \
        * c.layer_types.count("L")
    scratch_bytes = _align16(max(1 << 20, 8 * (kv_bytes + st_bytes)))
    scratch_addr = put(b"\x00" * scratch_bytes)

    # ---- header ----
    lt_bitmap = 0
    for i, t in enumerate(c.layer_types):
        if t == "F":
            lt_bitmap |= 1 << i
    hdr_words = [
        MAGIC, VERSION, c.n_layers, c.d_model, c.n_heads, c.mla_dk,
        c.mla_dr, c.mla_dv, c.mla_dc, c.kda_heads, c.kda_dim, c.conv_kernel,
        c.n_experts, c.top_k, c.n_shared, c.d_ff,
        c.attn_res_block, c.vocab, c.max_seq, seq_len, c.group_size,
        lt_bitmap, len(entries),
        desc_addr, tokens_addr, out_logits_addr, out_argmax_addr,
        out_status_addr, scratch_addr, scratch_bytes, stride, seq_len,
    ]
    hdr = struct.pack(f"<{len(hdr_words)}I", *hdr_words)
    hdr += b"\x00" * (HEADER_BYTES - len(hdr))
    chunks.append((0, hdr))

    img = bytearray(cursor)
    for addr, data in chunks:
        img[addr:addr + len(data)] = data
    layout = dict(out_logits_addr=out_logits_addr,
                  out_argmax_addr=out_argmax_addr,
                  out_status_addr=out_status_addr,
                  seq_len=seq_len, stride=stride,
                  image_bytes=len(img))
    return {"image": bytes(img), "layout": layout}


def parse_result(cfg: ModelConfig, layout: dict, result: bytes) -> dict:
    """result = dump of [out_logits_addr, out_status_addr+16). Returns
    logits int64 [seq_len, vocab], argmax int64 [seq_len], status word."""
    seq_len, stride = layout["seq_len"], layout["stride"]
    logits = np.zeros((seq_len, cfg.vocab), dtype=np.int64)
    for p in range(seq_len):
        logits[p] = np.frombuffer(result, dtype="<i4", count=cfg.vocab,
                                  offset=p * stride)
    toff = layout["out_argmax_addr"] - layout["out_logits_addr"]
    argmax = np.frombuffer(result, dtype="<u4", count=seq_len,
                           offset=toff).astype(np.int64)
    soff = layout["out_status_addr"] - layout["out_logits_addr"]
    status = struct.unpack_from("<I", result, soff)[0]
    return {"logits": logits, "argmax": argmax, "status": status}
