"""Contract tests use explicit test doubles, not architecture measurements."""

from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from nanochip.laboratory import (
    Action,
    Artifact,
    Candidate,
    CheckRequirement,
    CheckResult,
    ContractError,
    Cost,
    JsonlRecorder,
    Metric,
    RunReceipt,
    Task,
    assess,
    run_campaign,
)


FUNCTIONAL = CheckRequirement("functional", "complete-test-design")
PHYSICAL = CheckRequirement("physical", "complete-test-design")


def task(**kwargs):
    return Task("contract-test-v1", ("write",), (FUNCTIONAL, PHYSICAL), **kwargs)


def candidate(root, experiment=None, action=None):
    experiment = experiment or task()
    action = action or Action("write", {"contents": "correct"})
    Path(root).mkdir(parents=True, exist_ok=True)
    (Path(root) / "source.txt").write_text(
        action.parameters["contents"], encoding="utf-8"
    )
    return Candidate(
        "unit-candidate",
        experiment.task_id,
        str(root),
        action,
        (Artifact.from_file(root, "source.txt"),),
        task_digest=experiment.digest,
    )


def receipt(item, **kwargs):
    checks = (
        CheckResult("functional", "pass", FUNCTIONAL.scope),
        CheckResult("physical", "pass", PHYSICAL.scope),
    )
    values = dict(
        task_id=item.task_id,
        candidate_digest=item.digest,
        mode="fresh",
        execution_status="success",
        tool="unit-test-double",
        tool_version="1",
        checks=checks,
        cost=Cost(0.01),
    )
    values.update(kwargs)
    return RunReceipt(**values)


class Materializer:
    def materialize(self, experiment, action, workspace):
        return candidate(workspace, experiment, action)


class RepeatingProposer:
    def propose(self, experiment, history, budget):
        return Action("write", {"contents": "correct"})


class PassingBackend:
    def evaluate(self, experiment, item):
        return receipt(item)


class LaboratoryContractTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_missing_physical_check_is_unresolved_and_ineligible(self):
        item = candidate(self.root)
        observed = assess(
            task(),
            item,
            receipt(
                item, checks=(CheckResult("functional", "pass", FUNCTIONAL.scope),)
            ),
        )
        self.assertFalse(observed.eligible)
        self.assertEqual(observed.checks[1].status, "unresolved")

    def test_local_scope_cannot_satisfy_complete_design_requirement(self):
        item = candidate(self.root)
        observed = assess(
            task(),
            item,
            receipt(item, checks=(CheckResult("physical", "pass", "one-block"),)),
        )
        self.assertEqual(observed.checks[1].status, "unresolved")
        self.assertFalse(observed.eligible)

    def test_unrun_and_nonfresh_receipts_never_qualify(self):
        item = candidate(self.root)
        for mode in ("fixture", "replay", "cached"):
            with self.subTest(mode=mode):
                self.assertFalse(
                    assess(task(), item, receipt(item, mode=mode)).eligible
                )
        for status in ("not_run", "timeout", "error"):
            with self.subTest(status=status):
                self.assertFalse(
                    assess(
                        task(), item, receipt(item, execution_status=status)
                    ).eligible
                )

    def test_wrong_candidate_receipt_is_rejected(self):
        item = candidate(self.root)
        with self.assertRaisesRegex(ContractError, "different candidate"):
            assess(task(), item, receipt(item, candidate_digest="wrong-candidate"))

    def test_changed_task_with_same_name_is_rejected(self):
        item = candidate(self.root)
        changed = replace(task(), specification={"clock_ns": 2})
        with self.assertRaisesRegex(ContractError, "different task specification"):
            assess(changed, item, receipt(item))

    def test_source_tamper_is_rejected_before_execution(self):
        class TamperingMaterializer(Materializer):
            def materialize(self, experiment, action, workspace):
                item = super().materialize(experiment, action, workspace)
                (workspace / "source.txt").write_text("tampered", encoding="utf-8")
                return item

        class MustNotRun:
            def evaluate(self, experiment, item):
                self.fail("Backend must not receive changed source")

        with self.assertRaisesRegex(ContractError, "content changed"):
            run_campaign(
                task(),
                RepeatingProposer(),
                TamperingMaterializer(),
                MustNotRun(),
                self.root,
            )

    def test_backend_source_tamper_is_rejected_after_execution(self):
        class TamperingBackend:
            def evaluate(self, experiment, item):
                original = receipt(item)
                (Path(item.root) / "source.txt").write_text(
                    "tampered", encoding="utf-8"
                )
                return original

        with self.assertRaisesRegex(ContractError, "content changed"):
            run_campaign(
                task(),
                RepeatingProposer(),
                Materializer(),
                TamperingBackend(),
                self.root,
            )

    def test_fresh_feedback_changes_next_action_and_candidate_artifact(self):
        class FeedbackProposer:
            def propose(self, experiment, history, budget):
                contents = "broken" if not history else "correct"
                if history:
                    assert history[-1].checks[0].status == "fail"
                    assert budget.attempts_remaining == 1
                return Action("write", {"contents": contents})

        class FileBackend:
            def evaluate(self, experiment, item):
                text = (Path(item.root) / "source.txt").read_text(encoding="utf-8")
                return receipt(
                    item,
                    checks=(
                        CheckResult(
                            "functional",
                            "pass" if text == "correct" else "fail",
                            FUNCTIONAL.scope,
                        ),
                        CheckResult("physical", "pass", PHYSICAL.scope),
                    ),
                    metrics={
                        "input_bytes": Metric(len(text), "bytes", "unit-test-input")
                    },
                )

        output = run_campaign(
            task(), FeedbackProposer(), Materializer(), FileBackend(), self.root
        )
        first, second = output.observations
        self.assertNotEqual(first.candidate_digest, second.candidate_digest)
        self.assertEqual(first.action.parameters["contents"], "broken")
        self.assertFalse(first.eligible)
        self.assertTrue(second.eligible)
        self.assertEqual(output.attempts_used, 2)

    def test_backend_exception_is_recorded_as_error_and_consumes_attempt(self):
        class FailingBackend:
            def evaluate(self, experiment, item):
                raise RuntimeError("tool unavailable")

        output = run_campaign(
            task(max_attempts=1),
            RepeatingProposer(),
            Materializer(),
            FailingBackend(),
            self.root,
        )
        self.assertEqual(output.attempts_used, 1)
        self.assertEqual(output.observations[0].status, "error")
        self.assertFalse(output.observations[0].eligible)
        self.assertTrue(
            all(check.status == "unresolved" for check in output.observations[0].checks)
        )

    def test_invalid_proposals_consume_proposal_budget_only(self):
        class InvalidProposer:
            def propose(self, experiment, history, budget):
                return Action("change-evaluator")

        output = run_campaign(
            task(max_proposals=2),
            InvalidProposer(),
            Materializer(),
            PassingBackend(),
            self.root,
        )
        self.assertEqual(output.proposals_used, 2)
        self.assertEqual(output.attempts_used, 0)
        self.assertEqual(
            [item.status for item in output.observations], ["invalid_action"] * 2
        )

    def test_materialization_failures_are_feedback_and_consume_attempts(self):
        class FailingMaterializer:
            def materialize(self, experiment, action, workspace):
                raise RuntimeError("cannot build")

        output = run_campaign(
            task(),
            RepeatingProposer(),
            FailingMaterializer(),
            PassingBackend(),
            self.root,
        )
        self.assertEqual(output.attempts_used, 2)
        self.assertTrue(
            all(item.status == "materialization_error" for item in output.observations)
        )

    def test_failed_proposer_cannot_change_the_task(self):
        class MutatingProposer:
            def propose(self, experiment, history, budget):
                experiment.specification["clock_ns"] = 99
                raise RuntimeError("failure after mutation")

        with self.assertRaisesRegex(ContractError, "frozen task before failing"):
            run_campaign(
                task(specification={"clock_ns": 2}),
                MutatingProposer(),
                Materializer(),
                PassingBackend(),
                self.root,
            )

    def test_failed_materializer_cannot_change_task_or_action(self):
        for mutate_task in (True, False):

            class MutatingMaterializer:
                def materialize(self, experiment, action, workspace):
                    if mutate_task:
                        experiment.specification["clock_ns"] = 99
                    else:
                        action.parameters["contents"] = "changed"
                    raise RuntimeError("failure after mutation")

            with self.subTest(mutate_task=mutate_task), self.assertRaises(
                ContractError
            ):
                run_campaign(
                    task(specification={"clock_ns": 2}),
                    RepeatingProposer(),
                    MutatingMaterializer(),
                    PassingBackend(),
                    self.root / str(mutate_task),
                )

    def test_recorded_events_include_manifest_status_scope_mode_and_cost(self):
        log = self.root / "events.jsonl"
        output = run_campaign(
            task(max_attempts=1),
            RepeatingProposer(),
            Materializer(),
            PassingBackend(),
            self.root / "run",
            JsonlRecorder(log),
        )
        events = [
            json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(
            [event["event"] for event in events],
            [
                "campaign_started",
                "proposal",
                "candidate",
                "observation",
                "campaign_finished",
            ],
        )
        recorded = events[3]["observation"]
        self.assertEqual(
            recorded["candidate_digest"], output.observations[0].candidate_digest
        )
        self.assertEqual(recorded["receipt"]["mode"], "fresh")
        self.assertEqual(recorded["checks"][0]["scope"], FUNCTIONAL.scope)
        self.assertEqual(recorded["receipt"]["cost"]["wall_seconds"], 0.01)

    def test_artifact_cannot_escape_its_root(self):
        with self.assertRaises(ContractError):
            Artifact("../source.txt", "0" * 64)
        outside = self.root / "outside.txt"
        outside.write_text("private", encoding="utf-8")
        inside = self.root / "candidate"
        inside.mkdir()
        (inside / "link.txt").symlink_to(outside)
        with self.assertRaisesRegex(ContractError, "escapes"):
            Artifact.from_file(inside, "link.txt")


if __name__ == "__main__":
    unittest.main()
