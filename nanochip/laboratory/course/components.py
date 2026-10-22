"""Reference components that students replace in the cumulative course."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import math
from typing import Any

from ..contracts import (
    Action,
    Artifact,
    Candidate,
    CheckResult,
    Cost,
    ContractError,
    Metric,
    RunReceipt,
    Task,
)


def split_by_group(
    records: Sequence[Mapping[str, Any]],
    *,
    seed: str,
    fractions: Mapping[str, float] | None = None,
) -> tuple[dict[str, Any], ...]:
    """Assign complete experiment groups to deterministic data partitions."""
    if not records or not isinstance(seed, str) or not seed:
        raise ContractError("Nonempty records and an explicit seed are required")
    ratios = dict(fractions or {"train": 0.6, "dev": 0.2, "test": 0.2})
    if set(ratios) != {"train", "dev", "test"}:
        raise ContractError("Fractions must declare train, dev, and test")
    if any(
        type(value) not in (int, float) or not math.isfinite(value) or value <= 0
        for value in ratios.values()
    ) or not math.isclose(sum(ratios.values()), 1.0):
        raise ContractError("Split fractions must be finite, positive, and sum to one")
    group_rows: dict[str, list[int]] = {}
    for index, row in enumerate(records):
        record_id, group_id = row.get("record_id"), row.get("group_id")
        if not isinstance(record_id, str) or not record_id.strip():
            raise ContractError("Every record needs a nonempty record_id")
        if not isinstance(group_id, str) or not group_id.strip():
            raise ContractError("Every record needs a nonempty group_id")
        group_rows.setdefault(group_id, []).append(index)
    if len(group_rows) < 3:
        raise ContractError(
            "At least three independent groups are needed for three splits"
        )

    source_split = {}
    for group_id, indices in group_rows.items():
        partitions = {
            records[index].get("original_split", "train") for index in indices
        }
        if len(partitions) != 1 or next(iter(partitions)) not in (
            "train",
            "dev",
            "development",
            "test",
        ):
            raise ContractError(
                "Related records need one valid original_split assignment"
            )
        source_split[group_id] = next(iter(partitions))
    movable = [group for group in group_rows if source_split[group] == "train"]
    if not movable:
        raise ContractError("At least one original training group is required")
    ordered_groups = sorted(
        movable,
        key=lambda group: hashlib.sha256(f"{seed}\0{group}".encode("utf-8")).digest(),
    )
    weights = [ratios[name] for name in ("train", "dev", "test")]
    cuts = (weights[0], weights[0] + weights[1])
    count = len(ordered_groups)
    assignment: dict[str, str] = {
        group: ("dev" if source_split[group] == "development" else source_split[group])
        for group in group_rows
        if source_split[group] in ("dev", "development", "test")
    }
    for rank, group_id in enumerate(ordered_groups):
        # Midpoint allocation avoids placing a group exactly on a split edge.
        position = (rank + 0.5) / count
        split = (
            "train" if position < cuts[0] else "dev" if position < cuts[1] else "test"
        )
        assignment[group_id] = split
    # A small corpus can otherwise leave one partition empty. Move the final
    # group from the largest occupied partition while preserving group unity.
    for missing in ("train", "dev", "test"):
        if missing not in assignment.values():
            counts = {
                name: list(assignment.values()).count(name)
                for name in ("train", "dev", "test")
            }
            movable_assigned = [
                group for group in ordered_groups if group in assignment
            ]
            donor = max(
                (assignment[group] for group in movable_assigned),
                key=lambda name: counts[name],
            )
            move = next(
                group
                for group in reversed(ordered_groups)
                if assignment.get(group) == donor
            )
            assignment[move] = missing
    return tuple(dict(row, split=assignment[row["group_id"]]) for row in records)


def validate_group_splits(records: Sequence[Mapping[str, Any]]) -> None:
    """Reject missing identities, duplicate records, and group leakage."""
    seen_ids: set[str] = set()
    group_split: dict[str, str] = {}
    allowed = {"train", "dev", "test"}
    for row in records:
        record_id, group_id, split = (
            row.get("record_id"),
            row.get("group_id"),
            row.get("split"),
        )
        if (
            not isinstance(record_id, str)
            or not record_id.strip()
            or not isinstance(group_id, str)
            or not group_id.strip()
        ):
            raise ContractError("Records need record and group identities")
        if record_id in seen_ids:
            raise ContractError("Duplicate record identity")
        seen_ids.add(record_id)
        if split not in allowed:
            raise ContractError("Every record must belong to train, dev, or test")
        previous = group_split.setdefault(group_id, split)
        if previous != split:
            raise ContractError("Related records cross data partitions")
    if not seen_ids or set(group_split.values()) != allowed:
        raise ContractError("Every split must contain at least one experiment group")


def pack_int4(values: Sequence[int]) -> bytes:
    """Pack unsigned four-bit values in low-nibble-first order."""
    if not values or len(values) % 2:
        raise ContractError("Packed int4 values must be nonempty and have even length")
    if any(type(value) is not int or not 0 <= value <= 15 for value in values):
        raise ContractError("Each int4 value must be an integer from 0 through 15")
    return bytes(
        values[index] | (values[index + 1] << 4) for index in range(0, len(values), 2)
    )


def unpack_int4(packed: bytes | bytearray | Sequence[int]) -> tuple[int, ...]:
    """Unpack bytes into low nibble, then high nibble, for each byte."""
    if not packed:
        raise ContractError("Packed int4 data must be nonempty")
    if any(type(value) is not int or not 0 <= value <= 255 for value in packed):
        raise ContractError("Packed storage must contain unsigned bytes")
    output: list[int] = []
    for byte in packed:
        output.extend((byte & 0x0F, (byte >> 4) & 0x0F))
    return tuple(output)


def adapt_receipt(
    raw: Mapping[str, Any], task: Task, candidate: Candidate
) -> RunReceipt:
    """Parse and identity-check one serialized receipt before scoring it."""
    if not isinstance(raw, Mapping):
        raise ContractError("Receipt must be an object")
    if (
        raw.get("task_id") != task.task_id
        or raw.get("candidate_digest") != candidate.digest
    ):
        raise ContractError("Receipt task or candidate identity does not match")
    if candidate.task_id != task.task_id or candidate.task_digest != task.digest:
        raise ContractError("Candidate does not belong to this frozen task")
    try:
        checks = tuple(CheckResult(**item) for item in raw.get("checks", ()))
        metrics = {
            name: value if isinstance(value, Metric) else Metric(**value)
            for name, value in raw.get("metrics", {}).items()
        }
        cost_raw = raw.get("cost", {})
        cost = cost_raw if isinstance(cost_raw, Cost) else Cost(**cost_raw)
        receipt = RunReceipt(
            task_id=raw["task_id"],
            candidate_digest=raw["candidate_digest"],
            mode=raw["mode"],
            execution_status=raw["execution_status"],
            tool=raw["tool"],
            tool_version=raw["tool_version"],
            checks=checks,
            metrics=metrics,
            cost=cost,
            details=raw.get("details", ""),
            output_root=raw.get("output_root"),
            output_artifacts=tuple(
                value if isinstance(value, Artifact) else Artifact(**value)
                for value in raw.get("output_artifacts", ())
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError(f"Receipt is incomplete or invalid: {exc}") from exc
    return receipt


def summarize_cost(receipts: Sequence[RunReceipt]) -> dict[str, Any]:
    """Aggregate only recorded wall time and keep evidence states separate."""
    if not receipts:
        raise ContractError("At least one receipt is required for a cost summary")
    rows = [
        {
            "task_id": receipt.task_id,
            "candidate_digest": receipt.candidate_digest,
            "mode": receipt.mode,
            "execution_status": receipt.execution_status,
            "wall_seconds": receipt.cost.wall_seconds,
        }
        for receipt in receipts
    ]
    return {
        "scope": "recorded wall time only; excludes unrecorded setup and human time",
        "total_wall_seconds": sum(row["wall_seconds"] for row in rows),
        "fresh_wall_seconds": sum(
            row["wall_seconds"] for row in rows if row["mode"] == "fresh"
        ),
        "rows": rows,
    }


class FirstUntriedSearch:
    """A transparent budgeted baseline that tries each legal action once."""

    def choose(self, task: Task, proposals: Sequence[Action], history, budget):
        if budget.proposals_remaining <= 0 or budget.attempts_remaining <= 0:
            return None
        legal = [action for action in proposals if action.name in task.allowed_actions]
        tried = {item.action.name for item in history if item.action is not None}
        return next((action for action in legal if action.name not in tried), None)


def search_to_proposer(
    policy: FirstUntriedSearch, proposal_factory, task_actions: Sequence[Action]
):
    """Adapt the shared SearchPolicy boundary to the campaign Proposer API."""
    from ..contracts import Budget

    class _Proposer:
        def propose(self, task, history, budget: Budget):
            proposals = (
                proposal_factory(task, history) if proposal_factory else task_actions
            )
            return policy.choose(task, proposals, history, budget)

    return _Proposer()
