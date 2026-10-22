from ...contracts import canonical_json
from ...context import KeywordContext
from ...contracts import ContractError


def serialize(task, history):
    spec = task.specification
    config = spec["target"]["configuration"]
    checks = tuple(requirement.name for requirement in task.required_checks)
    observations = {}
    for item in history:
        if item.action is None or item.action.name not in task.allowed_actions:
            raise ContractError("History contains no legal action identity")
        metric = item.receipt.metrics.get("cycles") if item.receipt else None
        failed_mask = sum(
            1 << checks.index(check.name)
            for check in item.checks
            if check.status != "pass" and check.name in checks
        )
        action_index = task.allowed_actions.index(item.action.name)
        previous = observations.get(action_index, [0, 0, None, 0])
        observations[action_index] = [
            previous[0] + 1,
            previous[1] + int(bool(item.eligible)),
            int(metric.value) if metric else None,
            failed_mask,
        ]
    payload = {
        "schema": "nanochip.course.task_json/v3",
        "w": [
            config["d_model"],
            config["n_layers"],
            config["n_experts"],
            config["top_k"],
        ],
        "x": [
            spec["token_count"],
            spec["seed"],
            spec["prompt_index"],
            spec.get("tokens"),
        ],
        "a": list(task.allowed_actions),
        # One row per action: [action_index, observations, eligible_count,
        # latest_cycles, latest_failed_check_bitset]. This retains measured
        # feedback while keeping the public byte contract independent of the
        # number or verbosity of historical receipts.
        "h": [[index, *observations[index]] for index in sorted(observations)],
    }
    return canonical_json(payload)


from ...models.language import LanguageProposer


def retrieve(query, documents, *, limit):
    return KeywordContext().retrieve(query, documents, max_words=limit)


def parse_action(text, allowed_actions):
    if not isinstance(text, str) or not text.strip() or "\n" in text or "\r" in text:
        raise ContractError("Expected one action name on one line")
    action = text.strip()
    if action not in tuple(allowed_actions):
        raise ContractError("Model output is not a legal action")
    return action
