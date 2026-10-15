"""Nanochip engine package: 6-stage Architecture 2.0 loop, roofline calculator, referees, and proposers."""

from .lifecycle import (
    CANONICAL_STAGES,
    STAGE_SHORT_NAMES,
    CommitRecord,
    EvaluationRecord,
    ExecutionRecord,
    FormulationRecord,
    InterpretationRecord,
    ProposalRecord,
    TurnTrajectory,
)
from .proposers import SUPPORTED_PROPOSERS, NanochipProposer, resolve_proposer
from .referees import (
    audit_verilog_file,
    check_deq_bit_exactness,
    check_frozen_integrity,
    run_kpu_evaluate,
    synthesize_module_yosys,
)
from .roofline import compute_tensor_breakdown, evaluate_rooflines


def __getattr__(name: str):
    if name == "NanochipLoopRunner":
        from .runner import NanochipLoopRunner

        return NanochipLoopRunner
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
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
