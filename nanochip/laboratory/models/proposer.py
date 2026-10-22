"""Compose a saved sequence decoder with the existing Proposer protocol."""

from pathlib import Path
from typing import Callable

from ..contracts import Action, Budget, ContractError, Observation, Task
from ..model_io import ModelIOContract
from .sequence import load_model


class LearnedProposer:
    """The caller supplies the exact corpus serializer; there is no hidden rule.

    A decoded stop action ends the run. An invalid input/output raises an
    explicit error; no conventional proposer is consulted.
    """

    def __init__(
        self,
        checkpoint_dir: str | Path,
        format_input: Callable[[Task, tuple[Observation, ...]], str],
        *,
        stop_action: str = "stop",
        model_io_contract: ModelIOContract | None = None,
    ):
        self.decoder = load_model(
            checkpoint_dir, expected_model_io_contract=model_io_contract
        )
        self.decoder.require_input_contract(model_io_contract)
        self.model_io_contract = model_io_contract
        self.format_input = format_input
        self.stop_action = stop_action
        self.predictions: list[dict] = []

    def propose(
        self, task: Task, history: tuple[Observation, ...], budget: Budget
    ) -> Action | None:
        if budget.proposals_remaining <= 0:
            return None
        allowed = [
            action
            for action in self.decoder.actions
            if action in task.allowed_actions or action == self.stop_action
        ]
        if not allowed:
            raise ContractError("Task and checkpoint share no legal action")
        prediction = self.decoder.predict(
            self.format_input(task, history),
            allowed_actions=allowed,
            model_io_contract=self.model_io_contract,
        )
        self.predictions.append(prediction)
        return (
            None
            if prediction["action"] == self.stop_action
            else Action(prediction["action"])
        )
