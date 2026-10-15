#!/usr/bin/env python3
"""Deterministic replay and evidence packet verifier for the nano-kpu Design-Loop Card v2.0."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KPU_ROOT = HERE.parent / "kpu"
if str(KPU_ROOT) not in sys.path:
    sys.path.insert(0, str(KPU_ROOT))

from harness.audit import check as audit_check  # noqa: E402
from harness.check_integrity import check as integrity_check  # noqa: E402
from harness.gen_golden import golden  # noqa: E402
from harness.memmap import build_image  # noqa: E402
from harness.scoring import run_metrics  # noqa: E402
from reference.config import CONFIGS  # noqa: E402
from reference.gen_weights import (  # noqa: E402
    active_weight_bytes,
    floor_weight_bytes,
    gen_tokens,
    gen_weights,
)
from rtl.selfmodel.fxmodel import FxModel  # noqa: E402


def sha256_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def verify_all() -> int:
    # 1. Verify frozen upstream manifest
    integ = integrity_check()
    if not integ.get("ok"):
        print(
            f"[FAIL] Frozen manifest modified: {integ.get('modified')}", file=sys.stderr
        )
        return 1

    # 2. Verify static RTL audit
    aud = audit_check()
    if not aud.get("ok"):
        print(
            f"[FAIL] Static RTL audit hard violations: {aud.get('hard')}",
            file=sys.stderr,
        )
        return 1

    # 3. Recompute roofline and check against packet 1
    cfg = CONFIGS["nano"]
    act_b = active_weight_bytes(cfg)
    flr_b = floor_weight_bytes(cfg)
    pkt1_path = HERE / "evidence" / "nano-kpu-formulation-roofline.json"
    pkt1 = json.loads(pkt1_path.read_text(encoding="utf-8"))
    rf_int4 = pkt1["roofline_analysis"]["int4_group128_codesign"]
    assert act_b == rf_int4["active_bytes_per_token"], (act_b, rf_int4)
    assert flr_b == rf_int4["dense_floor_bytes_per_token"], (flr_b, rf_int4)
    assert (act_b + 15) // 16 == rf_int4["min_dram_cycles_per_token"]

    # 4. Recompute FxModel vs float32 golden and check against packet 2
    seed = 20260706
    img_bundle = build_image(cfg, gen_weights(cfg, seed), gen_tokens(cfg, seed, 0))
    fx_logits, fx_argmax = FxModel(img_bundle["image"]).run()
    g = golden("nano", seed, 0)
    met = run_metrics(fx_logits, fx_argmax, g["logits"], g["argmax"])
    pkt2_path = HERE / "evidence" / "nano-kpu-implementation-sandwich.json"
    pkt2 = json.loads(pkt2_path.read_text(encoding="utf-8"))
    assert (
        abs(
            met["cos_min"]
            - pkt2["spec_boundary_float32_to_fxmodel"]["run0_seq_len_48"]["cos_min"]
        )
        < 1e-6
    )
    assert (
        met["argmax_hits"]
        == pkt2["spec_boundary_float32_to_fxmodel"]["run0_seq_len_48"]["argmax_hits"]
    )

    # 5. Verify packet 3 signoff metrics
    pkt3_path = HERE / "evidence" / "nano-kpu-evaluation-signoff.json"
    pkt3 = json.loads(pkt3_path.read_text(encoding="utf-8"))
    assert pkt3["referee_gates"]["integrity_ok"] is True
    assert pkt3["referee_gates"]["audit_ok"] is True
    assert (
        pkt3["synthesis_metrics_nangate45"]["total_area_mm2"]
        <= pkt3["synthesis_metrics_nangate45"]["area_budget_mm2"]
    )
    assert (
        pkt3["synthesis_metrics_nangate45"]["critical_path_ns"]
        <= pkt3["synthesis_metrics_nangate45"]["target_period_ns"]
    )

    print(
        json.dumps(
            {
                "status": "replay_verified",
                "frozen_files_verified": len(
                    json.loads((KPU_ROOT / "harness" / "manifest.json").read_text())[
                        "files"
                    ]
                ),
                "active_weight_bytes": act_b,
                "fxmodel_cos_min": round(met["cos_min"], 8),
                "packets": {
                    pkt1_path.name: sha256_file(pkt1_path),
                    pkt2_path.name: sha256_file(pkt2_path),
                    pkt3_path.name: sha256_file(pkt3_path),
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verify-all"
    if cmd not in ("verify-all", "--verify"):
        print(f"Usage: {sys.argv[0]} verify-all", file=sys.stderr)
        sys.exit(2)
    sys.exit(verify_all())
