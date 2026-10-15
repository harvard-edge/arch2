"""Nanochip: Closed-loop Architecture 2.0 research engine for Moonshot AI's Kimi K3 nano-kpu."""

from .engine import (
    CANONICAL_STAGES,
    STAGE_SHORT_NAMES,
    CommitRecord,
    EvaluationRecord,
    ExecutionRecord,
    FormulationRecord,
    InterpretationRecord,
    NanochipProposer,
    ProposalRecord,
    SUPPORTED_PROPOSERS,
    TurnTrajectory,
    audit_verilog_file,
    check_deq_bit_exactness,
    check_frozen_integrity,
    compute_tensor_breakdown,
    evaluate_rooflines,
    resolve_proposer,
    run_kpu_evaluate,
    synthesize_module_yosys,
)


def __getattr__(name: str):
    if name == "NanochipLoopRunner":
        from .engine.runner import NanochipLoopRunner

        return NanochipLoopRunner
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__version__ = "2.0.0"

__all__ = [
    "__version__",
    "CANONICAL_STAGES",
    "STAGE_SHORT_NAMES",
    "FormulationRecord",
    "ProposalRecord",
    "ExecutionRecord",
    "EvaluationRecord",
    "InterpretationRecord",
    "CommitRecord",
    "TurnTrajectory",
    "SUPPORTED_PROPOSERS",
    "NanochipProposer",
    "resolve_proposer",
    "check_frozen_integrity",
    "audit_verilog_file",
    "check_deq_bit_exactness",
    "synthesize_module_yosys",
    "run_kpu_evaluate",
    "compute_tensor_breakdown",
    "evaluate_rooflines",
    "NanochipLoopRunner",
]
