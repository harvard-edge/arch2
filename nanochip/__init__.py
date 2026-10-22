"""Nanochip: a cumulative laboratory for AI-native architecture."""


def __getattr__(name: str):
    # Import the historical workbench only when it is requested. The new
    # laboratory contracts and CLI do not require NumPy or the old harness.
    if name in __all__ and name != "__version__":
        from . import engine

        value = getattr(engine, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__version__ = "0.1.0a0"

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
