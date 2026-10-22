"""Behavior checks for the existing student-owned Proposer extension.

The observations below are constructed contract cases, never tool evidence.
Live execution uses the ordinary laboratory CLI, materializer, and backend.
"""

from dataclasses import dataclass
from typing import Callable

from ..adapters import BLOCK_SCOPE, CORE_SCOPE, starter_task
from ..contracts import Action, Budget, CheckResult, Observation
from ..interfaces import Proposer


@dataclass(frozen=True)
class PolicyCheck:
    name: str
    status: str
    details: str


def _observed(*checks: CheckResult, status: str = "success") -> tuple[Observation, ...]:
    return (
        Observation(
            Action("teaching_fault"),
            "constructed-case",
            None,
            status,
            checks=checks,
            eligible=False,
            details="Constructed exercise input; no simulator ran",
        ),
    )


def check_feedback(factory: Callable[[], Proposer]) -> tuple[PolicyCheck, ...]:
    """Check consequential decisions, including errors and scope confusion.

    A fresh policy is used for each case. There is no fallback or receipt
    generation. Passing these cases supports policy behavior on these inputs;
    it does not establish RTL correctness or complete-design eligibility.
    """
    cases = (
        ("start with the constructed fault", (), Action("teaching_fault")),
        (
            "respond to an observed block mismatch",
            _observed(CheckResult("dequant_vectors", "fail", BLOCK_SCOPE)),
            Action("reference"),
        ),
        (
            "stop on a tool error even if a failure field is present",
            _observed(
                CheckResult("dequant_vectors", "fail", BLOCK_SCOPE), status="error"
            ),
            None,
        ),
        (
            "stop after a passing block without accepting the whole accelerator",
            _observed(
                CheckResult("dequant_vectors", "pass", BLOCK_SCOPE),
                CheckResult("physical_drc", "unresolved", CORE_SCOPE),
            ),
            None,
        ),
        ("do not repair from a missing block check", _observed(), None),
        (
            "do not confuse another scope with the dequantizer",
            _observed(CheckResult("dequant_vectors", "fail", CORE_SCOPE)),
            None,
        ),
        (
            "do not treat unresolved evidence as a numerical failure",
            _observed(CheckResult("dequant_vectors", "unresolved", BLOCK_SCOPE)),
            None,
        ),
    )
    results = []
    for name, history, expected in cases:
        task = starter_task()
        before = task.digest
        try:
            actual = factory().propose(task, history, Budget(3, 2))
        except NotImplementedError as exc:
            results.append(PolicyCheck(name, "incomplete", str(exc)))
            break
        except Exception as exc:
            results.append(PolicyCheck(name, "fail", f"{type(exc).__name__}: {exc}"))
            continue
        if task.digest != before:
            results.append(PolicyCheck(name, "fail", "Policy changed the frozen task"))
        elif actual != expected:
            results.append(
                PolicyCheck(name, "fail", f"Expected {expected!r}; received {actual!r}")
            )
        else:
            results.append(PolicyCheck(name, "pass", "Constructed policy case only"))
    return tuple(results)
