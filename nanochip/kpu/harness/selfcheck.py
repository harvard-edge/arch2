"""Harness self-check (frozen file). Proves the task is achievable end to
end at the data level:

  1. every tensor a chip needs is recoverable from the packed image bytes
     (descriptor table, int4 unpack, group dequant, tokens), and the
     reference run from IMAGE-RECOVERED tensors equals the golden run;
  2. a hypothetical good chip that writes int16-quantized versions of the
     golden logits (a deliberately coarse fixed-point rendering) plus the
     argmax and status parses back with cos >= 0.98 on every row —
     demonstrating the comparator and that the pass bar tolerates sane
     hardware numerics;
  3. a WRONG chip (shuffled logits) scores ~0 — the metric discriminates.

Run: python3 harness/selfcheck.py [--configs nano]
"""

import argparse
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from reference.config import CONFIGS                       # noqa: E402
from reference.gen_weights import gen_weights, gen_tokens, tensor_list  # noqa: E402
from reference.model import RefModel                       # noqa: E402
from harness.memmap import build_image, parse_result, fnv1a32, DONE_WORD  # noqa: E402
from harness.gen_golden import golden                      # noqa: E402
from harness.scoring import run_metrics, COS_PASS          # noqa: E402


def unpack_from_image(cfg, img: bytes):
    hdr = struct.unpack_from("<32I", img, 0)
    seq_len = hdr[19]
    n_tensors, desc_addr, tok_addr = hdr[22], hdr[23], hdr[24]
    entries = [struct.unpack_from("<IIII", img, desc_addr + 16 * i)
               for i in range(n_tensors)]
    w = {}
    for (name, shape, tag), (h, addr, nbytes, aux) in zip(tensor_list(cfg),
                                                          entries):
        assert h == fnv1a32(name), f"descriptor order mismatch at {name}"
        raw = img[addr:addr + nbytes]
        if tag in ("q4", "z8"):
            w[name] = np.frombuffer(raw, np.uint8).astype(np.int64).reshape(shape)
        else:
            w[name] = np.frombuffer(raw, "<i2").astype(np.int64).reshape(shape)
    tokens = np.frombuffer(img[tok_addr:tok_addr + 4 * seq_len],
                           "<u4").astype(np.int64)
    return w, tokens


def check_config(cname: str, seed: int):
    c = CONFIGS[cname]
    r = build_image(c, gen_weights(c, seed), gen_tokens(c, seed, 0))
    img, layout = r["image"], r["layout"]

    # (1) image round-trip: recovered tensors reproduce the golden exactly.
    # use_cache=False: this is an EXACT-equality check, and a golden cached
    # under a different BLAS/threading environment can differ in the last
    # ulps from an in-process recompute.
    w2, t2 = unpack_from_image(c, img)
    logits, am = RefModel(c, w2).forward_sequence(t2)
    g = golden(cname, seed, 0, use_cache=False)
    assert np.array_equal(logits, g["logits"]) and np.array_equal(am, g["argmax"]), \
        f"{cname}: image-recovered tensors do NOT reproduce the golden run"

    # (2) coarse-fixed-point chip writeback must clear the pass bar
    L = g["logits"].astype(np.float64)
    scale = 30000.0 / np.abs(L).max(axis=-1, keepdims=True)
    chip = np.round(L * scale).astype(np.int64)          # per-row int16-ish
    out = bytearray(layout["out_status_addr"] + 16 - layout["out_logits_addr"])
    stride = layout["stride"]
    for p in range(layout["seq_len"]):
        out[p * stride:p * stride + c.vocab * 4] = \
            chip[p].astype("<i4").tobytes()
    toff = layout["out_argmax_addr"] - layout["out_logits_addr"]
    am_chip = np.argmax(chip, axis=-1)
    out[toff:toff + 4 * layout["seq_len"]] = am_chip.astype("<u4").tobytes()
    soff = layout["out_status_addr"] - layout["out_logits_addr"]
    struct.pack_into("<I", out, soff, DONE_WORD)
    parsed = parse_result(c, layout, bytes(out))
    m = run_metrics(parsed["logits"], parsed["argmax"], g["logits"], g["argmax"])
    assert m["cos_min"] >= COS_PASS and m["argmax_agree"] >= 0.99, \
        f"{cname}: comparator rejects a sane fixed-point chip: {m}"

    # (3) wrong outputs must score ~0
    rng_rows = np.roll(parsed["logits"], 1, axis=1)      # shuffled logits
    m_bad = run_metrics(rng_rows, (parsed["argmax"] + 1) % c.vocab,
                        g["logits"], g["argmax"])
    assert m_bad["run_score"] < 0.05, f"{cname}: metric not discriminative: {m_bad}"

    print(f"[selfcheck] {cname}: OK (round-trip, comparator pass bar, "
          f"discrimination; good-chip cos_min={m['cos_min']:.5f})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", default="nano")
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    import json
    seed = a.seed or json.load(open(os.path.join(HERE, "seeds_public.json")))["seed"]
    for n in a.configs.split(","):
        check_config(n, seed)
    print("[selfcheck] all good — the task is achievable from the image alone")
