"""Small, inspectable records for candidate-specific laboratory experiments.

These contracts describe execution evidence. They do not implement an RTL
transformation, model trainer, simulator, or physical design flow.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Literal, Mapping


EvidenceMode = Literal["fresh", "cached", "replay", "fixture"]
ExecutionStatus = Literal["success", "error", "timeout", "not_run"]
CheckStatus = Literal["pass", "fail", "unresolved", "not_run"]


class ContractError(ValueError):
    """An artifact or receipt violates the experiment's identity contract."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def file_sha256(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class Action:
    name: str
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ContractError("An action needs a name")
        canonical_json(dict(self.parameters))


@dataclass(frozen=True)
class CheckRequirement:
    name: str
    scope: str


@dataclass(frozen=True)
class Task:
    task_id: str
    allowed_actions: tuple[str, ...]
    required_checks: tuple[CheckRequirement, ...]
    max_proposals: int = 6
    max_attempts: int = 2
    specification: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.task_id or not self.allowed_actions or not self.required_checks:
            raise ContractError("Task identity, allowed actions, and required checks are required")
        if self.max_proposals < 0 or self.max_attempts < 0:
            raise ContractError("Budgets cannot be negative")
        keys = [(check.name, check.scope) for check in self.required_checks]
        if len(set(keys)) != len(keys) or any(not all(key) for key in keys):
            raise ContractError("Required checks need distinct, nonempty names and scopes")
        if len(set(self.allowed_actions)) != len(self.allowed_actions):
            raise ContractError("Allowed action names must be distinct")
        canonical_json(dict(self.specification))

    @property
    def digest(self) -> str:
        """Identity includes the specification and the frozen evaluation rules."""
        return hashlib.sha256(canonical_json(asdict(self)).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Artifact:
    """A file relative to a candidate root, or a separately declared output root."""

    path: str
    sha256: str

    def __post_init__(self) -> None:
        path = Path(self.path)
        if not self.path or path.is_absolute() or ".." in path.parts:
            raise ContractError("Artifact paths must stay relative to their root")
        if len(self.sha256) != 64 or any(c not in "0123456789abcdef" for c in self.sha256):
            raise ContractError("Artifact SHA-256 must be 64 lowercase hexadecimal characters")

    @classmethod
    def from_file(cls, root: Path | str, path: str) -> Artifact:
        artifact = cls(path, "0" * 64)
        return cls(path, file_sha256(artifact.resolve(root)))

    def resolve(self, root: Path | str) -> Path:
        root_path = Path(root).resolve()
        target = (root_path / self.path).resolve()
        if not target.is_relative_to(root_path):
            raise ContractError(f"Artifact escapes its root: {self.path}")
        return target

    def validate(self, root: Path | str) -> None:
        try:
            actual = file_sha256(self.resolve(root))
        except OSError as exc:
            raise ContractError(f"Artifact is unavailable: {self.path}") from exc
        if actual != self.sha256:
            raise ContractError(f"Artifact content changed: {self.path}")


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    task_id: str
    root: str
    action: Action
    artifacts: tuple[Artifact, ...]
    parent_id: str | None = None
    task_digest: str = ""

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.task_id or not self.artifacts:
            raise ContractError("A candidate needs identities and a nonempty artifact manifest")
        paths = [artifact.path for artifact in self.artifacts]
        if len(set(paths)) != len(paths):
            raise ContractError("Candidate artifact paths must be distinct")

    @property
    def digest(self) -> str:
        manifest = {
            "task_id": self.task_id,
            "task_digest": self.task_digest,
            "action": asdict(self.action),
            "parent_id": self.parent_id,
            "artifacts": [asdict(item) for item in sorted(self.artifacts, key=lambda a: a.path)],
        }
        return hashlib.sha256(canonical_json(manifest).encode("utf-8")).hexdigest()

    def validate_files(self) -> None:
        for artifact in self.artifacts:
            artifact.validate(self.root)


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: CheckStatus
    scope: str
    details: str = ""

    def __post_init__(self) -> None:
        if self.status not in ("pass", "fail", "unresolved", "not_run"):
            raise ContractError(f"Unknown check status: {self.status}")
        if not self.name or not self.scope:
            raise ContractError("A check needs a name and scope")


@dataclass(frozen=True)
class Metric:
    value: float
    unit: str
    scope: str

    def __post_init__(self) -> None:
        if not math.isfinite(self.value) or not self.unit or not self.scope:
            raise ContractError("Metrics need finite values, units, and explicit scope")


@dataclass(frozen=True)
class Cost:
    wall_seconds: float = 0.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.wall_seconds) or self.wall_seconds < 0:
            raise ContractError("Wall time must be finite and nonnegative")


@dataclass(frozen=True)
class RunReceipt:
    task_id: str
    candidate_digest: str
    mode: EvidenceMode
    execution_status: ExecutionStatus
    tool: str
    tool_version: str
    checks: tuple[CheckResult, ...] = ()
    metrics: Mapping[str, Metric] = field(default_factory=dict)
    cost: Cost = field(default_factory=Cost)
    details: str = ""
    output_root: str | None = None
    output_artifacts: tuple[Artifact, ...] = ()

    def __post_init__(self) -> None:
        if self.mode not in ("fresh", "cached", "replay", "fixture"):
            raise ContractError(f"Unknown evidence mode: {self.mode}")
        if self.execution_status not in ("success", "error", "timeout", "not_run"):
            raise ContractError(f"Unknown execution status: {self.execution_status}")
        if not self.task_id or not self.candidate_digest or not self.tool or not self.tool_version:
            raise ContractError("Receipts need task/candidate and tool/version identities")
        keys = [(check.name, check.scope) for check in self.checks]
        if len(set(keys)) != len(keys):
            raise ContractError("A receipt cannot contain duplicate checks at the same scope")
        if self.output_artifacts and self.output_root is None:
            raise ContractError("Output artifacts need an explicit root")


@dataclass(frozen=True)
class Observation:
    action: Action | None
    candidate_id: str | None
    candidate_digest: str | None
    status: str
    checks: tuple[CheckResult, ...] = ()
    eligible: bool = False
    receipt: RunReceipt | None = None
    details: str = ""


@dataclass(frozen=True)
class Budget:
    proposals_remaining: int
    attempts_remaining: int


@dataclass(frozen=True)
class CampaignRecord:
    task_id: str
    observations: tuple[Observation, ...]
    proposals_used: int
    attempts_used: int
    stop_reason: str


@dataclass(frozen=True)
class TrainingRecord:
    """Future training boundary; no learner implementation is implied."""

    dataset_id: str
    split: Literal["train"]
    base_model_id: str
    tokenizer_id: str
    checkpoint: Artifact
    checkpoint_root: str
    cost: Cost = field(default_factory=Cost)
