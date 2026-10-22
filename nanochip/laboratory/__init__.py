"""Nanochip's modular laboratory core; no empirical backend is implied."""

from .contracts import (
    Action,
    Artifact,
    Budget,
    CampaignRecord,
    Candidate,
    CheckRequirement,
    CheckResult,
    ContractError,
    Cost,
    Metric,
    Observation,
    RunReceipt,
    Task,
    TrainingRecord,
    file_sha256,
)
from .evidence import JsonlRecorder, assess
from .runner import run_campaign

__all__ = [
    "Action",
    "Artifact",
    "Budget",
    "CampaignRecord",
    "Candidate",
    "CheckRequirement",
    "CheckResult",
    "ContractError",
    "Cost",
    "Metric",
    "Observation",
    "RunReceipt",
    "Task",
    "TrainingRecord",
    "file_sha256",
    "JsonlRecorder",
    "assess",
    "run_campaign",
]
