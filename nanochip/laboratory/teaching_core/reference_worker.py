"""Isolated legacy-import bridge, invoked by fixtures.build_fixture only."""

import hashlib
import json
from pathlib import Path
import sys

import numpy as np


def main():
    sys.dont_write_bytecode = True
    package = Path(__file__).resolve().parent
    root = package.parents[2]
    kpu = root / "nanochip/kpu"
    # This worker's sibling rtl.py is an adapter, not the frozen rtl namespace.
    # Remove the script directory before importing the legacy selfmodel.
    sys.path = [p for p in sys.path if Path(p or ".").resolve() != package]
    sys.path.insert(0, str(kpu))
    from reference.config import ModelConfig
    from reference.gen_weights import gen_weights, gen_tokens, tensor_list
    from reference.model import RefModel
    from harness.memmap import build_image
    from rtl.selfmodel.fxmodel import FxModel
    from harness.scoring import row_cosines, ARGMAX_TIE_REL, ARGMAX_PASS, COS_PASS

    output = Path(sys.argv[1])
    seed, prompt = map(int, sys.argv[2:4])
    target = json.loads((output / "contract.json").read_text())
    cfg = ModelConfig(**target["configuration"])
    weights = gen_weights(cfg, seed)
    requested_tokens = json.loads((output / "request.json").read_text())["tokens"]
    tokens = gen_tokens(cfg, seed, prompt) if requested_tokens is None else np.asarray(requested_tokens, np.int64)
    packed = build_image(cfg, weights, tokens)
    (output / "image.bin").write_bytes(packed["image"])
    floating = RefModel(cfg, weights)
    floating.dump = {}
    float_logits, float_argmax = floating.forward_sequence(tokens)
    fixed_dump = {}
    integer = FxModel(packed["image"], dump=fixed_dump)
    fixed_result = integer.run()
    if isinstance(fixed_result, tuple):
        fixed_logits, fixed_argmax = fixed_result
    else:
        fixed_logits = fixed_result
        fixed_argmax = np.argmax(fixed_logits, axis=-1)
    fixed_logits = np.asarray(fixed_logits)
    cosine = row_cosines(fixed_logits, float_logits)
    floating64 = float_logits.astype(np.float64)
    chosen = floating64[np.arange(len(tokens)), np.asarray(fixed_argmax, np.int64)]
    near_tie_agree = chosen >= floating64.max(axis=1) - ARGMAX_TIE_REL * floating64.std(axis=1)
    near_tie_rate = float(near_tie_agree.mean())
    np.savez(output / "goldens.npz", tokens=tokens, float_logits=float_logits,
             float_argmax=float_argmax, fixed_logits=fixed_logits, fixed_argmax=fixed_argmax)
    np.savez(output / "float_intermediates.npz", **floating.dump)
    np.savez(output / "fixed_intermediates.npz", **fixed_dump)
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    sources = [kpu / p for p in ("reference/config.py", "reference/model.py", "reference/gen_weights.py",
               "reference/prng.py", "harness/memmap.py", "harness/scoring.py", "rtl/selfmodel/fxmodel.py", "rtl/selfmodel/fxluts.py")]
    sources += sorted((kpu / "rtl/roms").glob("*.hex"))
    sources += [package / "contract.py", package / "fixtures.py", package / "reference_worker.py"]
    receipt = {
        "schema": "nanochip-teaching-core-reference/v0", "scope": "software-reference:complete-teaching-workload",
        "seed": seed, "prompt_index": prompt, "tokens": tokens.tolist(),
        "status": "pass" if np.all(cosine >= COS_PASS) and near_tie_rate >= ARGMAX_PASS else "fail",
        "per_row_cosine": cosine.tolist(),
        "float_fixed_argmax_agreement": (np.asarray(float_argmax) == np.asarray(fixed_argmax)).tolist(),
        "near_tie_argmax_agreement": near_tie_agree.tolist(), "near_tie_argmax_rate": near_tie_rate,
        "numerical_thresholds": {"cosine": COS_PASS, "argmax_agreement": ARGMAX_PASS, "tie_relative_std": ARGMAX_TIE_REL},
        "layout": packed["layout"], "tensor_count": len(tensor_list(cfg)),
        "tensor_bytes": sum(int(np.asarray(weights[nm]).size) * (1 if tag in ("q4", "z8") else 2) for nm, _, tag in tensor_list(cfg)),
        "source_artifacts": [{"path": str(p.relative_to(root)), "sha256": sha(p)} for p in sources],
        "outputs": [{"path": p.name, "sha256": sha(p)} for p in sorted(output.iterdir()) if p.is_file()],
        "rtl_execution": False, "physical_execution": False, "complete_core_ready": False,
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: receipt[k] for k in ("status", "tensor_count", "tensor_bytes", "per_row_cosine", "float_fixed_argmax_agreement")}))


if __name__ == "__main__":
    main()
