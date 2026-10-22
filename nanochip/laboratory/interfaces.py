"""Explicit extension boundaries; no discovery or registration framework."""

from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from .contracts import (
    Action,
    Budget,
    Candidate,
    Observation,
    RunReceipt,
    Task,
    TrainingRecord,
)


class Proposer(Protocol):
    def propose(
        self, task: Task, history: tuple[Observation, ...], budget: Budget
    ) -> Action | None:
        ...


class Materializer(Protocol):
    def materialize(self, task: Task, action: Action, workspace: Path) -> Candidate:
        ...


class Backend(Protocol):
    def evaluate(self, task: Task, candidate: Candidate) -> RunReceipt:
        ...


class Recorder(Protocol):
    def append(self, event: Mapping[str, Any]) -> None:
        ...


class ContextProvider(Protocol):
    """Sources must already be filtered to the campaign's permitted corpus."""

    def build(
        self,
        task: Task,
        history: tuple[Observation, ...],
        allowed_sources: Sequence[Mapping[str, Any]],
        budget: int,
    ) -> Sequence[Mapping[str, Any]]:
        ...


class Learner(Protocol):
    """A future learner accepts a versioned training dataset, never test outcomes."""

    def train(
        self,
        dataset: str | Path | Sequence[Mapping[str, Any]],
        model_id: str,
        budget: Mapping[str, Any],
    ) -> TrainingRecord:
        ...


class Predictor(Protocol):
    def predict(self, task: Task, candidate: Candidate) -> Mapping[str, Any]:
        ...


class SearchPolicy(Protocol):
    def choose(
        self,
        task: Task,
        proposals: Sequence[Action],
        history: tuple[Observation, ...],
        budget: Budget,
    ) -> Action | None:
        ...
