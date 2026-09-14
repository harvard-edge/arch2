"""Architecture 2.0: Base Verification Referee & Structured Physical Receipt.
==========================================================================
Defines the shared data contracts and base class for all physical referees.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PhysicalReceipt:
    """Structured signoff receipt returned by EDA toolchain and verification referees."""

    iteration: int
    paradigm: str
    headline: str
    target_metric: str
    achieved_value: float
    unit: str
    limit_value: float
    slack: float
    status: str  # PASS or FAIL
    tool_provenance: str
    verification_status: str
    diagnostics: List[str] = field(default_factory=list)
    cell_count: int = 0
    logic_depth: int = 0
    reward_hack_detected: bool = False
    cheat_id: Optional[str] = None
    loop: str = "B"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert receipt to dictionary for JSON serialization."""
        return {
            "iteration": self.iteration,
            "paradigm": self.paradigm,
            "headline": self.headline,
            "target_metric": self.target_metric,
            "achieved_value": self.achieved_value,
            "unit": self.unit,
            "limit_value": self.limit_value,
            "slack": self.slack,
            "status": self.status,
            "tool_provenance": self.tool_provenance,
            "verification_status": self.verification_status,
            "diagnostics": self.diagnostics,
            "cell_count": self.cell_count,
            "logic_depth": self.logic_depth,
            "reward_hack_detected": self.reward_hack_detected,
            "cheat_id": self.cheat_id,
            "loop": self.loop,
            "metadata": self.metadata,
        }


class BaseReferee(ABC):
    """Abstract base class for domain-specific physical verification referees."""

    @abstractmethod
    def evaluate(self, candidate: Any, **kwargs: Any) -> PhysicalReceipt:
        """Evaluates a candidate solution against hard physical invariants."""
        raise NotImplementedError
