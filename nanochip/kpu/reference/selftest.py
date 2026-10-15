"""Self-test: run the float32 reference on nano, print health
stats, and check the platform-robust fingerprint (argmax sequence) against
frozen values in harness/golden_digests.json."""

import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from reference.config import CONFIGS                  # noqa: E402
from reference.gen_weights import gen_weights, gen_tokens  # noqa: E402
from reference.model import RefModel                  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DIGEST_FILE = os.path.join(HERE, "..", "harness", "golden_digests.json")


def run_cfg(name: str, seed: int, prompt_idx: int = 0, stats: bool = False):
    import hashlib
    c = CONFIGS[name]
    m = RefModel(c, gen_weights(c, seed))
    t0 = time.time()
    logits, am = m.forward_sequence(gen_tokens(c, seed, prompt_idx))
    dt = time.time() - t0
    fp = hashlib.sha256(am.astype("<i4").tobytes()).hexdigest()
    if stats:
        lr = float(np.sqrt((logits.astype(np.float64) ** 2).mean()))
        print(f"  logits rms={lr:.4g} finite={np.isfinite(logits).all()} "
              f"rows={logits.shape} uniq_argmax={len(set(am.tolist()))}/{len(am)}")
    print(f"[{name}] seed={seed} argmax_sha={fp[:16]}.. ({dt:.1f}s)")
    return fp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", default="nano")
    ap.add_argument("--seed", type=int, default=20260706)
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--freeze", action="store_true",
                    help="write fingerprints to harness/golden_digests.json")
    args = ap.parse_args()

    digs = {}
    for name in args.configs.split(","):
        digs[name] = run_cfg(name, args.seed, stats=args.stats)

    if args.freeze:
        cur = {}
        if os.path.exists(DIGEST_FILE):
            cur = json.load(open(DIGEST_FILE))
        cur.setdefault(str(args.seed), {}).update(digs)
        json.dump(cur, open(DIGEST_FILE, "w"), indent=2)
        print(f"froze fingerprints -> {DIGEST_FILE}")
    elif os.path.exists(DIGEST_FILE):
        cur = json.load(open(DIGEST_FILE)).get(str(args.seed), {})
        for k, v in digs.items():
            if k in cur and cur[k] != v:
                print(f"FINGERPRINT MISMATCH: {k} argmax sequence changed "
                      f"(reference drift or unusual BLAS?)", file=sys.stderr)
                sys.exit(1)
        print("fingerprints match frozen values.")


if __name__ == "__main__":
    main()
