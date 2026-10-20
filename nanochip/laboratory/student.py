"""Student-owned first component: turn tool feedback into the next action.

Implement StudentProposer.propose, then run the CLI with --policy student.
The reference implementation lives in adapters.py. The same Proposer protocol
will later accept the checkpoint trained in Labs 4 and 5.
"""

from .contracts import Action, Budget, Observation, Task


class StudentProposer:
    def propose(
        self, task: Task, history: tuple[Observation, ...], budget: Budget,
    ) -> Action | None:
        """Start with the teaching fault; use a failed numerical check to repair.

        Return None after a passing block check or on a tool error. Do not
        treat a missing physical result as a passing physical result. The
        runner, rather than this component, determines design eligibility.
        """
        raise NotImplementedError(
            "Implement StudentProposer.propose in nanochip/laboratory/student.py; "
            "use --policy reference to inspect the supplied checkpoint."
        )
