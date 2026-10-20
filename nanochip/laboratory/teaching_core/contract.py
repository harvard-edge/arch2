"""Proposed complete teaching geometry, separated from frozen upstream nano."""

from dataclasses import asdict, dataclass
import math


@dataclass(frozen=True)
class TeachingConfig:
    name: str = "nanochip-teaching-v0"
    d_model: int = 8
    n_layers: int = 2
    layer_pattern: str = "LF"
    n_heads: int = 2
    mla_dk: int = 4
    mla_dr: int = 4
    mla_dv: int = 4
    mla_dc: int = 8
    kda_heads: int = 2
    kda_dim: int = 4
    conv_kernel: int = 4
    n_experts: int = 4
    top_k: int = 2
    n_shared: int = 1
    d_ff: int = 8
    attn_res_block: int = 2
    vocab: int = 16
    max_seq: int = 4
    group_size: int = 4
    seq_lens: tuple = (4, 2)
    timeout_cycles: int = 300_000_000
    wall_secs: int = 120


CONFIG = TeachingConfig()


def contract() -> dict:
    c = CONFIG
    kda_layers = c.layer_pattern.count("L")
    mla_layers = c.layer_pattern.count("F")
    state_words = {
        "kda_recurrent_state": kda_layers * c.kda_heads * c.kda_dim * c.kda_dim,
        "preconv_history": kda_layers * 3 * (c.conv_kernel - 1) * c.kda_heads * c.kda_dim,
        "mla_expanded_k_cache": mla_layers * c.max_seq * c.n_heads * (c.mla_dk + c.mla_dr),
        "mla_expanded_v_cache": mla_layers * c.max_seq * c.n_heads * c.mla_dv,
        "residual_snapshots": math.ceil(c.n_layers / c.attn_res_block) * c.d_model,
    }
    return {
        "schema": "nanochip-complete-teaching-core/v0", "status": "functional_prototype",
        "top": "nanochip_teaching_core", "scope": "accelerator:nanochip_teaching_core",
        "configuration": asdict(c), "all_workload_operations_required": True,
        "operations": ["int4_embedding_dequantization", "grouped_int4_gemv", "rmsnorm",
                       "l2norm", "silu", "sigmoid", "exp", "reciprocal", "rsqrt",
                       "causal_depthwise_convolution", "kda_decay_delta_updated_readout",
                       "mla_causal_softmax_attention", "stable_top2_bias_corrected_selection",
                       "renormalized_unbiased_router_weights", "shared_and_routed_swiglu",
                       "attention_residual_softmax_mixing", "untied_lm_head", "stable_argmax"],
        "numerical_contract": {
            "floating_reference": "frozen kpu/reference/model.py with teaching geometry",
            "integer_reference": "frozen kpu/rtl/selfmodel/fxmodel.py with same packed image",
            "activation_bits": 32, "activation_fraction_bits": 26,
            "kda_state_fraction_bits": 27, "weight_bits": 4,
            "rounding": "upstream rshift: arithmetic shift after adding half-unit",
            "saturation": "upstream operation boundaries, signed int32",
            "rtl_gate": "exact logits/argmax and selected intermediate states versus integer reference",
            "float_gate": {"minimum_per_row_cosine": 0.98, "minimum_near_tie_argmax_agreement": 0.99,
                           "argmax_near_tie_tolerance": "0.01 times reference row standard deviation"},
            "nonlinear_realization": "exact upstream tables fetched by the core from explicit external memory",
        },
        "architecture_proposal": {
            "execution": "serialized microprogrammed datapath; no host-computed activations",
            "external_interface": "upstream valid/ready command and 128-bit aligned memory port",
            "weights": "external packed int4/scales/zeros and small parameters; canonical upstream descriptors",
            "program": "shape-derived external microcode fetched and executed by the core; runtime data-dependent expert dispatch",
            "arithmetic": "shared signed multiply/accumulate with explicit wide reductions and sequential normalization",
            "onchip_memory": "bounded realized state/workspace/control storage; no unresolved blackboxes",
            "external_memory": "packed weights, tokens, outputs, immutable nonlinear tables, and shape-derived program",
            "tradeoff": "serialized external instruction/table fetch increases cycles/traffic to reduce on-chip storage",
            "physical_memory_options": ["small mapped standard-cell memories", "compatible SRAM views plus checked wrappers"],
        },
        "persistent_and_snapshot_storage": {"word_bits": 32, "regions_words": state_words,
                                             "total_words": sum(state_words.values()),
                                             "total_bits": sum(state_words.values()) * 32,
                                             "excludes": "temporary vectors, instructions, scalar registers, nonlinear tables, weights"},
        "acceptance": ["all tokens through both layers with carried recurrent/conv/KV state",
                       "exact implementation-versus-integer-reference workload results",
                       "independent float-reference numerical comparison",
                       "new weights/tokens change results without rebuilding datapath",
                       "expert choices arise from runtime scores; no prerecorded answer table",
                       "reset independence and memory backpressure/latency stress",
                       "all state/program/table memories realized in implementation",
                       "source/netlist/layout correspondence and declared physical checks",
                       "complete checked GDS, including realized memories"],
        "rtl_implemented": True, "physical_execution": False, "complete_core_ready": False,
    }
