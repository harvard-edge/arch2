"""Dataset membership and evidence validation, before any learning begins.

This module does not turn a receipt into an optimal-action label. A curator
must provide labels separately and explain how they were obtained.
"""

from dataclasses import dataclass
from pathlib import Path
import json
from typing import Literal

from .contracts import Artifact, ContractError

Split = Literal["train", "dev", "test"]


@dataclass(frozen=True)
class DatasetEntry:
    record_id: str
    group_id: str
    split: Split
    evidence_mode: str
    construction: str
    source: str
    receipt: Artifact


def load_dataset(
    manifest_path: Path | str, *, split: Split
) -> tuple[DatasetEntry, ...]:
    """Validate the entire manifest before selecting an allowed partition.

    Related candidates/conditions must share a curator-assigned group. This
    validates separation of those declarations; it cannot detect undisclosed
    semantic duplicates. Fixture/replay entries cannot supply empirical labels.
    """
    if split not in ("train", "dev", "test"):
        raise ContractError("Choose exactly one of train, dev, or test")
    path = Path(manifest_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or not payload.get("dataset_id"):
        raise ContractError("Dataset needs schema_version=1 and a dataset_id")
    rows = payload.get("records")
    if not isinstance(rows, list) or not rows:
        raise ContractError("Dataset must contain records")
    groups: dict[str, str] = {}
    receipts: dict[str, str] = {}
    record_ids: set[str] = set()
    entries: list[DatasetEntry] = []
    for row in rows:
        try:
            entry = DatasetEntry(
                row["record_id"],
                row["group_id"],
                row["split"],
                row["evidence_mode"],
                row["construction"],
                row["source"],
                Artifact(**row["receipt"]),
            )
        except (KeyError, TypeError) as exc:
            raise ContractError("Dataset record is incomplete") from exc
        if not all(
            isinstance(value, str) and value.strip()
            for value in (
                entry.record_id,
                entry.group_id,
                entry.source,
            )
        ):
            raise ContractError("Records need nonempty identity, group, and source")
        if entry.record_id in record_ids:
            raise ContractError("Duplicate dataset record identity")
        record_ids.add(entry.record_id)
        if entry.split not in ("train", "dev", "test"):
            raise ContractError("Unknown dataset partition")
        if entry.evidence_mode != "fresh":
            raise ContractError("Empirical datasets require fresh execution receipts")
        if entry.construction not in ("constructed_fault", "reference", "natural"):
            raise ContractError(
                "Disclose whether a case is constructed or naturally encountered"
            )
        for key, index in ((entry.group_id, groups), (entry.receipt.sha256, receipts)):
            if key in index and index[key] != entry.split:
                raise ContractError(
                    "Related or duplicated evidence crosses dataset partitions"
                )
            index[key] = entry.split
        entry.receipt.validate(path.parent)
        receipt = json.loads(
            entry.receipt.resolve(path.parent).read_text(encoding="utf-8")
        )
        if receipt.get("mode") != "fresh":
            raise ContractError("Receipt origin contradicts the dataset declaration")
        entries.append(entry)
    return tuple(entry for entry in entries if entry.split == split)


def training_records(manifest_path: Path | str) -> tuple[DatasetEntry, ...]:
    """The learner path exposes only the training partition."""
    return load_dataset(manifest_path, split="train")
