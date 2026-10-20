"""Fail-closed assessment and a transparent JSON-lines event recorder."""

from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from .contracts import Candidate, CheckResult, ContractError, Observation, RunReceipt, Task, canonical_json


def assess(task: Task, candidate: Candidate, receipt: RunReceipt) -> Observation:
    """Only successful fresh execution with every required scoped check can qualify.

    Cached receipts remain inspectable, but v0 does not validate cache lineage and
    therefore cannot use them to establish fresh experiment eligibility.
    """
    if receipt.task_id != task.task_id or candidate.task_id != task.task_id:
        raise ContractError("Receipt, candidate, and task identities disagree")
    if candidate.task_digest != task.digest:
        raise ContractError("Candidate belongs to a different task specification")
    if receipt.candidate_digest != candidate.digest:
        raise ContractError("Receipt belongs to a different candidate manifest")
    candidate.validate_files()
    for artifact in receipt.output_artifacts:
        artifact.validate(receipt.output_root or "")
    returned = {(item.name, item.scope): item for item in receipt.checks}
    required = tuple(
        returned.get(
            (item.name, item.scope),
            CheckResult(item.name, "unresolved", item.scope, "Required check has no result"),
        )
        for item in task.required_checks
    )
    eligible = (
        receipt.mode == "fresh"
        and receipt.execution_status == "success"
        and all(item.status == "pass" for item in required)
    )
    return Observation(
        action=candidate.action,
        candidate_id=candidate.candidate_id,
        candidate_digest=candidate.digest,
        status=receipt.execution_status,
        checks=required,
        eligible=eligible,
        receipt=receipt,
        details=receipt.details,
    )


class JsonlRecorder:
    """Append events without overwriting a previous run's evidence."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: Mapping[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(canonical_json(dict(event)) + "\n")


def observation_event(observation: Observation) -> Mapping[str, Any]:
    return {"event": "observation", "observation": asdict(observation)}
