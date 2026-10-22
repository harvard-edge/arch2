"""One visible proposal/materialization/execution/feedback loop."""

from dataclasses import asdict
from copy import deepcopy
from pathlib import Path
import time

from .contracts import (
    Action,
    Budget,
    CampaignRecord,
    ContractError,
    Cost,
    Observation,
    RunReceipt,
    Task,
    canonical_json,
)
from .evidence import assess, observation_event
from .interfaces import Backend, Materializer, Proposer, Recorder


def run_campaign(
    task: Task,
    proposer: Proposer,
    materializer: Materializer,
    backend: Backend,
    workspace: Path | str,
    recorder: Recorder | None = None,
) -> CampaignRecord:
    """Execute bounded attempts and return only the current campaign's history.

    Invalid actions consume proposals; materialization/backend failures consume
    attempts. Identity violations raise rather than becoming usable feedback.
    Backends must run exclusively from the declared candidate files and identify
    all inputs/settings/platform assets in that manifest.
    """
    root = Path(workspace)
    root.mkdir(parents=True, exist_ok=True)
    observations: list[Observation] = []
    proposals_used = attempts_used = 0
    stop_reason = "budget_exhausted"
    task_digest = task.digest

    def record(event: dict) -> None:
        if recorder is not None:
            recorder.append(event)

    def observe(observation: Observation) -> None:
        observations.append(observation)
        record(dict(observation_event(observation)))

    record({"event": "campaign_started", "task": asdict(task)})
    while proposals_used < task.max_proposals and attempts_used < task.max_attempts:
        budget = Budget(
            task.max_proposals - proposals_used, task.max_attempts - attempts_used
        )
        proposals_used += 1
        try:
            action = proposer.propose(task, deepcopy(tuple(observations)), budget)
        except ContractError:
            raise
        except Exception as exc:
            if task.digest != task_digest:
                raise ContractError(
                    "Proposer changed the frozen task before failing"
                ) from exc
            observe(
                Observation(
                    None,
                    None,
                    None,
                    "proposal_error",
                    details=f"{type(exc).__name__}: {exc}",
                )
            )
            continue
        if task.digest != task_digest:
            raise ContractError("Proposer changed the frozen task")
        if action is None:
            stop_reason = "proposer_stopped"
            break
        if not isinstance(action, Action):
            raise ContractError("Proposer must return an Action or None")
        record(
            {"event": "proposal", "action": asdict(action), "budget": asdict(budget)}
        )
        if action.name not in task.allowed_actions:
            observe(
                Observation(
                    action,
                    None,
                    None,
                    "invalid_action",
                    details="Action is outside the frozen task",
                )
            )
            continue
        attempts_used += 1
        action_json = canonical_json(asdict(action))
        attempt_root = root / f"attempt-{attempts_used:04d}"
        attempt_root.mkdir(exist_ok=False)
        try:
            candidate = materializer.materialize(task, action, attempt_root)
        except ContractError:
            raise
        except Exception as exc:
            if task.digest != task_digest:
                raise ContractError(
                    "Materializer changed the frozen task before failing"
                ) from exc
            if canonical_json(asdict(action)) != action_json:
                raise ContractError(
                    "Materializer changed the requested action before failing"
                ) from exc
            observe(
                Observation(
                    action,
                    None,
                    None,
                    "materialization_error",
                    details=f"{type(exc).__name__}: {exc}",
                )
            )
            continue
        if (
            candidate.task_id != task.task_id
            or canonical_json(asdict(candidate.action)) != action_json
        ):
            raise ContractError(
                "Materialized candidate does not implement the requested task/action"
            )
        if task.digest != task_digest or candidate.task_digest != task_digest:
            raise ContractError(
                "Materialized candidate does not match the frozen task specification"
            )
        if not Path(candidate.root).resolve().is_relative_to(attempt_root.resolve()):
            raise ContractError(
                "Candidate root must be inside its isolated attempt workspace"
            )
        candidate.validate_files()
        digest = candidate.digest
        record(
            {
                "event": "candidate",
                "candidate": asdict(candidate),
                "candidate_digest": digest,
            }
        )
        started = time.monotonic()
        try:
            receipt = backend.evaluate(task, candidate)
        except ContractError:
            raise
        except Exception as exc:
            receipt = RunReceipt(
                task.task_id,
                digest,
                "fresh",
                "error",
                type(backend).__name__,
                "unknown",
                cost=Cost(time.monotonic() - started),
                details=f"{type(exc).__name__}: {exc}",
            )
        if candidate.digest != digest:
            raise ContractError("Backend changed the candidate manifest")
        if task.digest != task_digest:
            raise ContractError("Backend changed the frozen task")
        candidate.validate_files()
        observe(assess(task, candidate, receipt))
    campaign = CampaignRecord(
        task.task_id, tuple(observations), proposals_used, attempts_used, stop_reason
    )
    record({"event": "campaign_finished", "campaign": asdict(campaign)})
    return campaign
