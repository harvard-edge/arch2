"""Canonical 6-stage Architecture 2.0 research lifecycle records for nanochip.

Implements the Chapter 3 closed-loop lifecycle:
  1. Formulate -> 2. Explore -> 3. Implement -> 4. Evaluate -> 5. Interpret -> 6. Commit

With explicit diagnostic return arrows from Stage 5 (Interpret):
  - Operational / Representation / Audit fault -> "3. Implement"
  - Architectural / Microarchitectural / Physical fault -> "2. Explore"
  - Formulation / Roofline / Layer boundary wall -> "1. Formulate"
  - All gates passed & analytical model corroborated -> "6. Commit"
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


CANONICAL_STAGES: List[str] = [
    "1. Formulate",
    "2. Explore",
    "3. Implement",
    "4. Evaluate",
    "5. Interpret",
    "6. Commit",
]

STAGE_SHORT_NAMES: List[str] = [
    "Formulate",
    "Explore",
    "Implement",
    "Evaluate",
    "Interpret",
    "Commit",
]

OperationalLayer = Literal[
    "Layer 1: Workload & Calibration",
    "Layer 2: Hardware Microarchitecture",
    "Layer 3: Cross-Stack Hardware-Algorithm Co-Design",
]

ReturnArrowTarget = Literal[
    "3. Implement",
    "2. Explore",
    "1. Formulate",
    "6. Commit",
]

CommitDecision = Literal[
    "ADVANCE",
    "REJECT",
    "REVISE_FORMULATION",
    "STOP",
]


class _RecordBase:
    """Shared dictionary/JSON serialization helpers for lifecycle dataclasses."""

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        field_names = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in data.items() if k in field_names}
        return cls(**filtered)


@dataclass
class FormulationRecord(_RecordBase):
    """Stage 1 (Formulate): Defines the research question, frozen contract, and legal space."""

    question: str
    baseline_metrics: Dict[str, Any]
    target_metrics: Dict[str, Any]
    frozen_contract_files: List[str]
    integrity_sha256_ok: bool
    operational_layer: str
    legal_design_space: List[str]
    non_goals: List[str]
    stage: str = "Formulate"
    turn_id: int = 0


@dataclass
class ProposalRecord(_RecordBase):
    """Stage 2 (Explore): Architectural hypothesis and pre-measurement analytical prediction."""

    turn_id: int
    operational_layer: str
    title: str
    hypothesis: str
    predicted_cycles_per_token: float
    predicted_tokens_per_sec: float
    predicted_area_mm2: float
    predicted_critical_path_ns: float
    files_touched: List[str]
    code_diff_summary: str
    stage: str = "Explore"
    code_snippet: str = ""


@dataclass
class ExecutionRecord(_RecordBase):
    """Stage 3 (Implement): Multi-representation sync and tool execution telemetry."""

    turn_id: int
    representations_synced: Dict[str, Any]
    tools_invoked: List[str]
    tool_wall_seconds: float
    operational_faults: List[str] = field(default_factory=list)
    stage: str = "Implement"
    variant_rtl_file: Optional[str] = None


@dataclass
class EvaluationRecord(_RecordBase):
    """Stage 4 (Evaluate): Multi-gate referee scorecard from Verilator, Yosys, and Python."""

    turn_id: int
    integrity_ok: bool
    audit_ok: bool
    audit_violations: List[str]
    lint_ok: bool
    lint_warnings: int
    selfmodel_cosine_min: float
    selfmodel_bit_exact: bool
    nominal_sim_ok: bool
    measured_cycles_per_token: float
    measured_tokens_per_sec: float
    dram_bytes_per_token: float
    roofline_cycles: int
    randreset_ok: bool
    latency_2x_elasticity: float
    synth_area_mm2: float
    synth_gate_count: int
    synth_critical_path_ns: float
    all_gates_passed: bool
    stage: str = "Evaluate"
    extra_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InterpretationRecord(_RecordBase):
    """Stage 5 (Interpret): Separates operational faults from architectural limits and routes return arrows."""

    turn_id: int
    prediction_vs_measurement_error_pct: float
    root_cause_category: str
    causal_diagnosis: str
    return_arrow_target: ReturnArrowTarget
    next_action_recommendation: str
    stage: str = "Interpret"


@dataclass
class CommitRecord(_RecordBase):
    """Stage 6 (Commit): Human-governed disposition, Design Loop Card update, and non-claims."""

    turn_id: int
    decision: CommitDecision
    reviewer: str
    rationale: str
    non_claims: List[str]
    design_loop_card_path: str
    stage: str = "Commit"


@dataclass
class TurnTrajectory(_RecordBase):
    """Complete 6-stage bundle for one turn of the nanochip Architecture 2.0 loop."""

    turn_id: int
    turn_slug: str
    turn_label: str
    summary_headline: str
    formulate: FormulationRecord
    explore: ProposalRecord
    implement: ExecutionRecord
    evaluate: EvaluationRecord
    interpret: InterpretationRecord
    commit: CommitRecord
    tool_receipts: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TurnTrajectory":
        return cls(
            turn_id=int(data["turn_id"]),
            turn_slug=str(data["turn_slug"]),
            turn_label=str(data["turn_label"]),
            summary_headline=str(data["summary_headline"]),
            formulate=FormulationRecord.from_dict(data["formulate"]),
            explore=ProposalRecord.from_dict(data["explore"]),
            implement=ExecutionRecord.from_dict(data["implement"]),
            evaluate=EvaluationRecord.from_dict(data["evaluate"]),
            interpret=InterpretationRecord.from_dict(data["interpret"]),
            commit=CommitRecord.from_dict(data["commit"]),
            tool_receipts=dict(data.get("tool_receipts", {})),
        )
