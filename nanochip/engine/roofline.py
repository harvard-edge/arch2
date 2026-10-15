"""Executable analytical DRAM bandwidth and cycle roofline calculator for nano-kpu.

Imports `nanochip/kpu/reference/config.py` and `gen_weights.py` directly to compute:
  1. Per-token active weight bytes across data formats:
     - Packed INT4 group-128 (`q4` + `s16` + `z8` + `p16`): 76,112 B/token
     - Uncompressed FP16 (`4x` INT4 stream):               304,448 B/token
     - Uncompressed FP32 (`8x` INT4 stream):               608,896 B/token
  2. Minimum DRAM beats/token at `16 B/cycle` (`100 MHz` target clock):
     - INT4 group-128 uncached floor: 4,757 cycles/token (21,021.65 tok/s ceiling)
     - Uncompressed FP16 floor:      19,028 cycles/token (5,255.41 tok/s ceiling)
     - Uncompressed FP32 floor:      38,056 cycles/token (2,627.71 tok/s ceiling)
  3. Physical conservation proof for Stage 5 (Interpret):
     Any Layer 2 (hardware-only) proposal that streams uncompressed FP16 weights over
     the frozen `16 B/cycle` DRAM port cannot achieve `> 8,000 tok/s` (`<= 12,500`
     cycles/token at 100 MHz), because `19,028 > 12,500` by `6,528 cycles/token`
     (`+52.2%` over budget before a single MAC, KV-cache access, or KDA recurrence
     executes). Therefore, Stage 5 (Interpret) MUST route the return arrow to
     `1. Formulate` to unlock Layer 3 (Hardware-Algorithm Co-Design: fused INT4
     group-128 dequantization + algebraic zero-point folding + on-chip `head.q`
     shadow residency).
"""

from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import asdict, dataclass
from typing import Any, Dict

HERE = os.path.dirname(os.path.abspath(__file__))
KPU_ROOT = os.path.abspath(os.path.join(HERE, "..", "kpu"))
if KPU_ROOT not in sys.path:
    sys.path.insert(0, KPU_ROOT)

from reference.config import CONFIGS, ModelConfig  # noqa: E402
from reference.gen_weights import (  # noqa: E402
    _entry_bytes,
    active_weight_bytes,
    floor_weight_bytes,
    tensor_list,
)

DRAM_PORT_BYTES_PER_CYCLE = 16
TARGET_CLOCK_MHZ = 100.0
TARGET_PERIOD_NS = 10.0


@dataclass
class FormatRoofline:
    format_name: str
    active_bytes_per_token: int
    min_dram_beats_per_token: int
    roofline_cycles_seq48: int
    max_tokens_per_sec_100mhz: float
    can_meet_8000_tok_s: bool
    deficit_cycles_vs_8000_tok_s: int


def compute_tensor_breakdown(cfg: ModelConfig | None = None) -> Dict[str, Any]:
    """Break down the nano tensor list into dense, expert, embedding, and head bytes."""
    c = cfg or CONFIGS["nano"]
    g = min(c.group_size, c.d_model)
    ng_e = (c.d_model + g - 1) // g
    emb_row_bytes = c.d_model // 2 + ng_e * 3

    dense_bytes = 0
    small_p16_bytes = 0
    head_q_bytes = 0
    head_sz_bytes = 0
    single_expert_bytes = 0
    total_all_experts_bytes = 0
    emb_table_bytes = 0

    for name, shape, tag in tensor_list(c):
        b = _entry_bytes(shape, tag)
        if name.startswith("emb."):
            emb_table_bytes += b
            continue
        if ".moe.e" in name:
            total_all_experts_bytes += b
            if name.startswith("L0.moe.e0."):
                single_expert_bytes += b
            continue
        dense_bytes += b
        if tag == "p16":
            small_p16_bytes += b
        if name == "head.q":
            head_q_bytes += b
        elif name in ("head.s", "head.z"):
            head_sz_bytes += b

    active_routed_expert_bytes = c.n_layers * c.top_k * single_expert_bytes
    active_int4_raw = active_weight_bytes(c)
    active_int4_beats = (
        active_int4_raw + DRAM_PORT_BYTES_PER_CYCLE - 1
    ) // DRAM_PORT_BYTES_PER_CYCLE
    active_int4_aligned = active_int4_beats * DRAM_PORT_BYTES_PER_CYCLE
    floor_int4 = floor_weight_bytes(c)

    # With startup WBUF residency (small_p16_bytes), HS/HZ residency (head_sz_bytes),
    # and first-token shadow buffer residency for head.q (head_q_bytes amortized over seq_len):
    seq_len_long = c.seq_lens[0]
    streamed_per_token_steady = (
        active_int4_raw - small_p16_bytes - head_sz_bytes - head_q_bytes
    )

    return {
        "config": c.name,
        "d_model": c.d_model,
        "n_layers": c.n_layers,
        "layer_pattern": c.layer_pattern,
        "n_experts": c.n_experts,
        "top_k": c.top_k,
        "group_size": c.group_size,
        "seq_len_long": seq_len_long,
        "seq_len_short": c.seq_lens[1],
        "dense_floor_bytes": floor_int4,
        "single_expert_bytes": single_expert_bytes,
        "active_routed_experts_bytes_per_token": active_routed_expert_bytes,
        "all_routed_experts_bytes": total_all_experts_bytes,
        "embedding_row_bytes": emb_row_bytes,
        "embedding_table_bytes": emb_table_bytes,
        "small_p16_resident_wbuf_bytes": small_p16_bytes,
        "head_q_shadow_sram_bytes": head_q_bytes,
        "head_sz_resident_bytes": head_sz_bytes,
        "active_weight_bytes_int4_raw": active_int4_raw,
        "active_weight_bytes_int4": active_int4_aligned,
        "steady_state_streamed_bytes_with_hq_shadow": streamed_per_token_steady,
    }


def evaluate_rooflines(
    target_tokens_per_sec: float = 8000.0,
    clock_mhz: float = TARGET_CLOCK_MHZ,
    port_bytes_per_cycle: int = DRAM_PORT_BYTES_PER_CYCLE,
) -> Dict[str, Any]:
    """Compute INT4 vs FP16 vs FP32 bandwidth rooflines and check physical feasibility."""
    c = CONFIGS["nano"]
    breakdown = compute_tensor_breakdown(c)
    int4_bytes = breakdown["active_weight_bytes_int4"]  # 76,112 B (4,757 x 16B beats)
    fp16_bytes = int4_bytes * 4  # 304,448 B (19,028 x 16B beats)
    fp32_bytes = int4_bytes * 8  # 608,896 B (38,056 x 16B beats)

    cycle_budget_for_target = int(
        (clock_mhz * 1e6) // target_tokens_per_sec
    )  # 12,500 cyc

    formats: Dict[str, FormatRoofline] = {}
    for label, b_per_tok in [
        ("int4_group128", int4_bytes),
        ("fp16_uncompressed", fp16_bytes),
        ("fp32_uncompressed", fp32_bytes),
    ]:
        beats = (b_per_tok + port_bytes_per_cycle - 1) // port_bytes_per_cycle
        roof_seq48 = beats * c.seq_lens[0]
        max_tps = round((clock_mhz * 1e6) / beats, 2)
        feasible = beats <= cycle_budget_for_target
        deficit = max(0, beats - cycle_budget_for_target)
        formats[label] = FormatRoofline(
            format_name=label,
            active_bytes_per_token=b_per_tok,
            min_dram_beats_per_token=beats,
            roofline_cycles_seq48=roof_seq48,
            max_tokens_per_sec_100mhz=max_tps,
            can_meet_8000_tok_s=feasible,
            deficit_cycles_vs_8000_tok_s=deficit,
        )

    # Layer 2 hardware-only best case (FP16 stream + serialized compute overlap)
    fp16_floor = formats["fp16_uncompressed"].min_dram_beats_per_token
    int4_floor = formats["int4_group128"].min_dram_beats_per_token

    return {
        "clock_mhz": clock_mhz,
        "dram_port_bytes_per_cycle": port_bytes_per_cycle,
        "dram_peak_bandwidth_gbps": round(
            clock_mhz * 1e6 * port_bytes_per_cycle / 1e9, 3
        ),
        "target_tokens_per_sec": target_tokens_per_sec,
        "max_cycles_per_token_for_target": cycle_budget_for_target,
        "tensor_breakdown": breakdown,
        "rooflines": {k: asdict(v) for k, v in formats.items()},
        "co_design_proof": {
            "layer2_fp16_min_cycles_per_token": fp16_floor,
            "layer2_fp16_max_tokens_per_sec": formats[
                "fp16_uncompressed"
            ].max_tokens_per_sec_100mhz,
            "layer3_int4_min_cycles_per_token": int4_floor,
            "layer3_int4_max_tokens_per_sec": formats[
                "int4_group128"
            ].max_tokens_per_sec_100mhz,
            "kimi_k3_predicted_cycles_per_token": 11200.0,
            "kimi_k3_measured_cycles_per_token": 11467.083,
            "kimi_k3_measured_tokens_per_sec": 8720.613,
            "fp16_violates_8000_tok_s_by_cycles": fp16_floor - cycle_budget_for_target,
            "return_arrow_required": "1. Formulate",
            "conclusion": (
                f"Streaming uncompressed FP16 weights requires a minimum of {fp16_floor:,} "
                f"DRAM cycles/token ({fp16_bytes:,} B @ {port_bytes_per_cycle} B/cycle), capping "
                f"throughput at {formats['fp16_uncompressed'].max_tokens_per_sec_100mhz:,.2f} tok/s "
                f"at {clock_mhz:.0f} MHz. Achieving >= {target_tokens_per_sec:,.0f} tok/s "
                f"(<= {cycle_budget_for_target:,} cycles/token) is physically impossible in "
                f"Layer 2 hardware alone and requires routing Stage 5 (Interpret) back to "
                f"Stage 1 (Formulate) to unlock Layer 3 INT4 group-128 co-design "
                f"({int4_bytes:,} B/token, {int4_floor:,} minimum DRAM cycles/token)."
            ),
        },
    }


def main():
    report = evaluate_rooflines()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
