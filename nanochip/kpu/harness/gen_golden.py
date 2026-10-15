"""Golden vector generation with on-disk caching.

Goldens (float32 logits + argmax per position) are recomputed from the
reference — no golden file ships with the task. Cache key: (config, seed,
prompt index, group_size, seq_len), because the hidden evaluation may vary
group_size and stretch sequence lengths (see harness/evaluate.py). Note:
float32 goldens may differ in the last ulps across BLAS implementations;
the cosine-similarity comparator (pass bar 0.98) is insensitive to this by
construction.
"""

import hashlib
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from reference.config import CONFIGS                       # noqa: E402
from reference.gen_weights import gen_weights, gen_tokens  # noqa: E402
from reference.model import RefModel                       # noqa: E402

CACHE = os.path.join(HERE, ".cache")


def golden(cfg_name: str, seed: int, prompt_idx: int, cfg=None,
           use_cache=True):
    """dict(logits float32 [seq_len, vocab], argmax int64 [seq_len]).
    Pass `cfg` (a possibly group_size/seq_lens-modified ModelConfig) when
    evaluating a variant; defaults to CONFIGS[cfg_name]. use_cache=False
    forces a fresh recompute: cached goldens may differ in the last ulps
    from a recompute under a different BLAS/threading environment, so any
    EXACT-equality consumer (harness/selfcheck.py) must bypass the cache."""
    c = cfg if cfg is not None else CONFIGS[cfg_name]
    os.makedirs(CACHE, exist_ok=True)
    key = (f"golden_{cfg_name}_{seed}_{prompt_idx}"
           f"_g{c.group_size}_s{c.seq_lens[prompt_idx]}.npz")
    path = os.path.join(CACHE, key)
    if use_cache and os.path.exists(path):
        z = np.load(path)
        return {"logits": z["logits"], "argmax": z["argmax"]}
    m = RefModel(c, gen_weights(c, seed))
    logits, am = m.forward_sequence(gen_tokens(c, seed, prompt_idx))
    np.savez_compressed(path, logits=logits.astype(np.float32), argmax=am)
    return {"logits": logits.astype(np.float32), "argmax": am}


def golden_fingerprint(g) -> dict:
    """Platform-robust summary: argmax sequence hash + logits stats."""
    h = hashlib.sha256(g["argmax"].astype("<i4").tobytes()).hexdigest()
    return {"argmax_sha": h,
            "logit_rms": round(float(np.sqrt((g["logits"].astype(np.float64)
                                              ** 2).mean())), 4)}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--prompt", type=int, default=0)
    ap.add_argument("--dump", help="also write per-layer intermediates (npz) "
                                   "as a debugging aid")
    a = ap.parse_args()
    if a.dump:
        c = CONFIGS[a.config]
        m = RefModel(c, gen_weights(c, a.seed))
        m.dump = {}
        logits, am = m.forward_sequence(gen_tokens(c, a.seed, a.prompt))
        np.savez_compressed(a.dump, logits=logits, argmax=am,
                            **{k: v for k, v in m.dump.items()})
        print(f"wrote {a.dump} ({len(m.dump)} intermediate tensors)")
    else:
        g = golden(a.config, a.seed, a.prompt)
        fp = golden_fingerprint(g)
        print(f"{a.config} seed={a.seed} p={a.prompt} "
              f"argmax_sha={fp['argmax_sha'][:16]} "
              f"logit_rms={fp['logit_rms']} argmax[:8]={g['argmax'][:8].tolist()}")
