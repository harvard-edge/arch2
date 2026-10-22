from ..components import FirstUntriedSearch
from ...contracts import ContractError


_SEARCH = FirstUntriedSearch()


def predict(task, candidate):
    """Return a declared geometric cycle estimate, explicitly not a measurement."""
    if (
        candidate.task_id != task.task_id
        or candidate.action.name not in task.allowed_actions
    ):
        raise ContractError("Predictor received a candidate outside this frozen task")
    width = task.specification["action_parameters"][candidate.action.name][
        "multiplier_bits_per_cycle"
    ]
    # Token count and multiplier width are observable workload/action features.
    # The scale is a rough baseline; the checker retains error against execution.
    estimate = task.specification["token_count"] * 1_000_000 / width
    return {
        "metrics": {
            "cycles": {
                "value": estimate,
                "unit": "cycles",
                "uncertainty": estimate * 0.75,
            }
        },
        "basis": "declared token count and multiplier width; rough baseline, not tool evidence",
    }


def choose(task, proposals, history, budget):
    return _SEARCH.choose(task, proposals, history, budget)
