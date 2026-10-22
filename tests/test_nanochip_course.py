import json
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nanochip.laboratory.contracts import (
    Action,
    Artifact,
    Candidate,
    CheckResult,
    CheckRequirement,
    ContractError,
    Cost,
    RunReceipt,
    Task,
)
from nanochip.laboratory.course import (
    LABS,
    LabExecutionError,
    course_status,
    init_workspace,
    load_student_component,
    run_lab,
)
from nanochip.laboratory.course.checks import run_lab02, run_lab03, run_lab06
from nanochip.laboratory.course import checks as course_checks
from nanochip.laboratory.course.components import (
    FirstUntriedSearch,
    adapt_receipt,
    pack_int4,
    split_by_group,
    summarize_cost,
    unpack_int4,
    validate_group_splits,
)
from nanochip.laboratory.course.reference.lab03_harness import (
    adapt_receipt as reference_adapter,
)


class NanochipCourseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def _records(self, root: Path, count=15):
        root.mkdir(parents=True, exist_ok=True)
        rows = []
        for index in range(count):
            candidate_hash = f"{index:064x}"
            receipt_path = root / f"receipt-{index:02d}.json"
            receipt_path.write_text(
                json.dumps({"mode": "fresh", "candidate_sha256": candidate_hash})
            )
            receipt = Artifact.from_file(root, receipt_path.name)
            rows.append(
                {
                    "record_id": f"r-{index:02d}",
                    "group_id": f"family-{index:02d}",
                    "split": "train",
                    "evidence_mode": "fresh",
                    "construction": "constructed_fault",
                    "input_text": f"fault workload {index}",
                    "source_sha256": candidate_hash,
                    "source_receipt": {"path": receipt.path, "sha256": receipt.sha256},
                    "target_action": "rule-label",
                }
            )
        path = root / "records.jsonl"
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        return path, rows

    def test_nine_labs_are_ordered_and_require_prior_artifacts(self):
        self.assertEqual([item.number for item in LABS], list(range(1, 10)))
        self.assertIn(1, LABS[1].upstream)
        manifest = init_workspace(self.root / "student")
        self.assertEqual(len(manifest["student_components"]), 9)
        self.assertTrue((self.root / "student" / "README.md").is_file())
        self.assertEqual(course_status(self.root / "student")["course_complete"], False)
        with self.assertRaises(ContractError):
            run_lab(
                self.root / "student",
                2,
                mode="instructor",
                inputs={"values": (1, 2, 3, 4)},
            )

    def test_student_starter_fails_explicitly_without_reference_fallback(self):
        workspace = self.root / "student"
        init_workspace(workspace)
        records, _ = self._records(self.root / "input")
        with self.assertRaises(LabExecutionError):
            run_lab(workspace, 1, mode="student", inputs={"records_path": records})
        state = course_status(workspace)
        self.assertEqual(state["labs"][0]["status"], "incomplete")
        self.assertEqual(state["labs"][1]["status"], "not_started")
        attempts = list((workspace / "runs/lab01").glob("attempt-*/failure.json"))
        self.assertEqual(len(attempts), 1)

    def test_keyboard_interrupt_records_incomplete_attempt_and_retry_keeps_upstream(
        self,
    ):
        workspace = self.root / "recovery"
        init_workspace(workspace)
        records_path, _ = self._records(self.root / "records", count=15)
        (workspace / "labs/lab01_data.py").write_text(
            "def split_records(records, *, seed, fractions=None):\n"
            "    groups = list(dict.fromkeys(row['group_id'] for row in records))\n"
            "    assignment = {group: ('train' if index < 9 else 'dev' if index < 12 else 'test')\n"
            "                  for index, group in enumerate(groups)}\n"
            "    return tuple(dict(row, split=assignment[row['group_id']]) for row in records)\n"
        )
        lab1 = run_lab(
            workspace, 1, mode="student", inputs={"records_path": records_path}
        )

        lab2_path = workspace / "labs/lab02_representation.py"
        lab2_path.write_text(
            "def pack_int4(values):\n"
            "    raise KeyboardInterrupt('controlled recovery test')\n"
            "def unpack_int4(packed):\n"
            "    return tuple(n for byte in packed for n in (byte & 15, byte >> 4))\n"
        )
        with self.assertRaisesRegex(KeyboardInterrupt, "controlled recovery test"):
            run_lab(workspace, 2, mode="student")

        attempt1 = workspace / "runs/lab02/attempt-001"
        start = json.loads((attempt1 / "start.json").read_text())
        interruption = json.loads((attempt1 / "interruption.json").read_text())
        progress = [
            json.loads(line)
            for line in (workspace / "progress.jsonl").read_text().splitlines()
        ]
        self.assertEqual(
            start["implementation"]["sha256"], interruption["implementation"]["sha256"]
        )
        self.assertEqual(start["inputs"]["lab01"], lab1["run_digest"])
        self.assertEqual(interruption["inputs"]["lab01"], lab1["run_digest"])
        self.assertEqual(progress[-1]["lab"], 2)
        self.assertEqual(progress[-1]["status"], "incomplete")
        self.assertEqual(progress[-1]["outputs"][0]["path"], "runs/lab02/attempt-001")
        self.assertEqual(course_status(workspace)["labs"][0]["status"], "complete")

        lab2_path.write_text(
            "def pack_int4(values):\n"
            "    return bytes(values[i] | (values[i + 1] << 4) for i in range(0, len(values), 2))\n"
            "def unpack_int4(packed):\n"
            "    return tuple(n for byte in packed for n in (byte & 15, (byte >> 4) & 15))\n"
        )
        lab2 = run_lab(workspace, 2, mode="student")
        self.assertEqual(lab2["status"], "complete")
        self.assertEqual(lab2["outputs"][0]["path"], "runs/lab02/attempt-002")
        self.assertTrue((attempt1 / "interruption.json").is_file())
        self.assertTrue(
            (
                workspace / "runs/lab02/attempt-002/representation/int4-vectors.json"
            ).is_file()
        )
        status = course_status(workspace)
        self.assertEqual(status["labs"][0]["status"], "complete")
        self.assertEqual(status["labs"][1]["status"], "complete")

    def test_run_all_only_classifies_declared_unresolved_physical_checks_as_pending(
        self,
    ):
        from nanochip.laboratory.course import __main__ as course_cli

        def invoke(lab_number, check_name, check_status):
            workspace = self.root / f"cli-{lab_number}-{check_status}-{check_name}"
            init_workspace(workspace)
            event = {
                "lab": lab_number,
                "status": "incomplete",
                "checks": [{"name": check_name, "status": check_status}],
            }

            def fake_run_lab(_workspace, number, **_kwargs):
                if number == lab_number:
                    raise LabExecutionError("controlled check result", event=event)
                return {
                    "lab": number,
                    "status": "complete",
                    "run_digest": f"lab-{number}",
                }

            stdout, stderr = StringIO(), StringIO()
            with patch.object(course_cli, "run_lab", side_effect=fake_run_lab):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    code = course_cli.main(
                        [
                            "run-all",
                            "--workspace",
                            str(workspace),
                            "--through",
                            str(lab_number),
                        ]
                    )
            return code, stdout.getvalue(), stderr.getvalue()

        failed_code, failed_out, failed_err = invoke(
            8, "physical_receipt_binds_checked_source", "fail"
        )
        self.assertEqual(failed_code, 1)
        self.assertEqual(json.loads(failed_err)["status"], "incomplete")
        self.assertNotIn("pending_final_physical", failed_out + failed_err)

        nonphysical_pending_code, nonphysical_pending_out, _ = invoke(
            9, "heldout_comparison_and_cost_report", "unresolved"
        )
        self.assertEqual(nonphysical_pending_code, 1)
        self.assertNotIn("pending_final_physical", nonphysical_pending_out)

        physical_pending_code, physical_pending_out, _ = invoke(
            9, "final_physical_acceptance_for_adapted_winner", "unresolved"
        )
        self.assertEqual(physical_pending_code, 2)
        self.assertEqual(
            json.loads(physical_pending_out)["status"], "pending_final_physical"
        )

    def test_course_cli_accepts_and_forwards_shared_runtime_controls(self):
        from nanochip.laboratory.course import __main__ as course_cli

        run_args = course_cli._parser().parse_args(
            ["run", "--workspace", str(self.root / "student"), "--lab", "8"]
        )
        self.assertEqual(
            (
                run_args.timeout_s,
                run_args.physical_timeout_s,
                run_args.correspondence_timeout_s,
                run_args.cores,
                run_args.physical_mode,
            ),
            (180, 14400, 3600, 1, None),
        )
        all_args = course_cli._parser().parse_args(
            [
                "run-all",
                "--workspace",
                str(self.root / "student"),
                "--correspondence-timeout",
                "77",
                "--cores",
                "3",
                "--physical-mode",
                "native",
            ]
        )
        self.assertEqual(
            (all_args.correspondence_timeout_s, all_args.cores, all_args.physical_mode),
            (77, 3, "native"),
        )
        self.assertEqual(all_args.physical_timeout_s, 14400)

        workspace = self.root / "control-forwarding"
        init_workspace(workspace)
        captured = {}

        def fake_run_lab(_workspace, _lab, **kwargs):
            captured.update(kwargs)
            return {"status": "complete", "lab": 1, "run_digest": "test"}

        with patch.object(course_cli, "run_lab", side_effect=fake_run_lab):
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                code = course_cli.main(
                    [
                        "run",
                        "--workspace",
                        str(workspace),
                        "--lab",
                        "1",
                        "--timeout-s",
                        "71",
                        "--physical-timeout-s",
                        "811",
                        "--correspondence-timeout-s",
                        "43",
                        "--cores",
                        "2",
                        "--physical-mode",
                        "docker",
                    ]
                )
        self.assertEqual(code, 0)
        self.assertEqual(
            captured["inputs"],
            {
                "timeout_s": 71.0,
                "physical_timeout_s": 811.0,
                "correspondence_timeout": 43.0,
                "cores": 2,
                "physical_mode": "docker",
            },
        )

    def test_lab9_cli_resource_controls_override_campaign_config_only_for_matching_keys(
        self,
    ):
        from nanochip.laboratory.course.api import _lab9_campaign_config

        configured = {
            "cores": 8,
            "physical_mode": "docker",
            "candidate_budget": 4,
            "check_timeout": 12,
            "context_words": 8,
        }
        merged = _lab9_campaign_config(
            {
                "campaign_config": configured,
                "timeout_s": 71,
                "correspondence_timeout": 43,
                "cores": 2,
                "physical_mode": "native",
            }
        )
        self.assertEqual(
            merged,
            {
                "cores": 2,
                "physical_mode": "native",
                "candidate_budget": 4,
                "check_timeout": 71,
                "correspondence_timeout": 43,
                "context_words": 8,
            },
        )
        self.assertEqual(configured["cores"], 8)

        preserved = _lab9_campaign_config(
            {
                "campaign_config": {
                    "cores": 3,
                    "correspondence_timeout": 1234,
                    "physical_mode": "native",
                    "candidate_budget": 5,
                }
            }
        )
        self.assertEqual(
            preserved,
            {
                "cores": 3,
                "correspondence_timeout": 1234,
                "physical_mode": "native",
                "candidate_budget": 5,
                "check_timeout": 180,
            },
        )
        defaults = _lab9_campaign_config({"campaign_config": {"candidate_budget": 5}})
        self.assertEqual(
            defaults,
            {
                "candidate_budget": 5,
                "check_timeout": 180,
                "correspondence_timeout": 3600,
                "cores": 1,
                "physical_mode": None,
            },
        )

    def test_lab8_freezes_same_correspondence_budget_into_task_and_backend(self):
        from nanochip.laboratory.physical import teaching

        task = object()
        with patch.object(
            teaching, "make_physical_task", return_value=task
        ) as make_task, patch.object(
            teaching, "TeachingCorePhysicalBackend", return_value=object()
        ) as make_backend:
            physical_task, backend = course_checks._physical_task_backend(
                seed=2,
                prompt_index=1,
                split="development",
                tokens=[1, 2],
                check_timeout=71,
                physical_timeout=811,
                correspondence_timeout=43,
                cores=2,
                mode="native",
            )
        self.assertIs(physical_task, task)
        self.assertEqual(
            make_task.call_args.kwargs,
            {
                "seed": 2,
                "prompt_index": 1,
                "split": "development",
                "tokens": [1, 2],
                "check_timeout": 71,
                "physical_timeout": 811,
                "cores": 2,
                "correspondence_timeout": 43,
            },
        )
        self.assertEqual(
            make_backend.call_args.kwargs,
            {
                "check_timeout": 71,
                "physical_timeout": 811,
                "cores": 2,
                "correspondence_timeout": 43,
                "mode": "native",
            },
        )

    def test_lab8_complete_core_physical_default_is_declared_14400_second_budget(self):
        import inspect
        from nanochip.laboratory.course.checks import run_lab08

        self.assertEqual(
            inspect.signature(run_lab08).parameters["timeout_s"].default, 14400
        )
        self.assertEqual(
            inspect.signature(run_lab08).parameters["correspondence_timeout"].default,
            3600,
        )

    def test_lab9_emits_pending_human_architect_disposition_template(self):
        from nanochip.laboratory.course.checks import _architect_review_template

        winner = {
            "case_id": "test-case",
            "task_digest": "task-digest",
            "candidate_digest": "candidate-digest",
            "action": "serial_mul2",
            "candidate_root": str(self.root / "candidate"),
            "core_sha256": "1" * 64,
            "config_sha256": "2" * 64,
            "program_sha256": "3" * 64,
            "tables_sha256": "4" * 64,
            "image_sha256": "5" * 64,
            "golden_sha256": "6" * 64,
        }
        template = _architect_review_template(
            comparison_artifact={"path": "comparison.json", "sha256": "a" * 64},
            adapted_winners=[winner],
            physical_output=None,
            physical_candidate_core=None,
            physical_candidate_config=None,
            mapped_receipt_path=None,
            final_acceptance={
                "status": "pending_final_physical",
                "reasons": ["winner is not physically accepted"],
            },
        )
        self.assertEqual(template["status"], "pending_review")
        self.assertIsNone(template["disposition"])
        self.assertEqual(
            template["allowed_dispositions"], ["accept", "revise", "reject"]
        )
        self.assertEqual(
            template["reviewer"], {"name": None, "role": None, "reviewed_at_utc": None}
        )
        self.assertEqual(template["comparison_evidence"]["sha256"], "a" * 64)
        self.assertEqual(
            template["selected_candidate_evidence"][0]["candidate_digest"],
            "candidate-digest",
        )
        self.assertIn(
            "winner is not physically accepted", template["residual_limitations"]
        )
        self.assertIn("does not constitute approval", template["scope"])

    def test_student_module_loader_executes_new_bytes_even_when_mtime_and_size_repeat(
        self,
    ):
        workspace = self.root / "student"
        init_workspace(workspace)
        path = workspace / "labs/lab01_data.py"
        path.write_text("value = 1\n")
        original = path.stat()
        self.assertEqual(load_student_component(workspace, 1).value, 1)
        path.write_text("value = 2\n")
        os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns))
        self.assertEqual(path.stat().st_size, original.st_size)
        self.assertEqual(load_student_component(workspace, 1).value, 2)

    def test_instructor_data_output_feeds_next_lab_and_student_edit_stales_it(self):
        workspace = self.root / "student"
        init_workspace(workspace)
        records, rows = self._records(self.root / "input")
        student_file = workspace / "labs/lab01_data.py"
        student_file.write_text(
            "def split_records(records, *, seed, fractions=None):\n"
            "    groups = list(dict.fromkeys(row['group_id'] for row in records))\n"
            "    ordered = sorted(groups)\n"
            "    n = len(ordered)\n"
            "    cuts = (int(n * 0.6), int(n * 0.8))\n"
            "    assignment = {group: ('train' if i < cuts[0] else 'dev' if i < cuts[1] else 'test')\n"
            "                  for i, group in enumerate(ordered)}\n"
            "    return tuple(dict(row, split=assignment[row['group_id']]) for row in records)\n"
        )
        first = run_lab(workspace, 1, mode="student", inputs={"records_path": records})
        first_path = workspace / first["outputs"][0]["path"]
        saved = json.loads((first_path / "data" / "split-manifest.json").read_text())
        self.assertEqual(saved["record_counts"], {"train": 9, "dev": 3, "test": 3})
        second = run_lab(workspace, 2, mode="instructor")
        self.assertEqual(second["inputs"]["lab01"], first["run_digest"])
        self.assertIn("weight_image_sha256", second["inputs"])
        self.assertTrue(course_status(workspace)["labs"][1]["status"] == "complete")
        component_path = workspace / "labs/lab01_data.py"
        component_path.write_text(
            component_path.read_text() + "\n# changed student implementation\n"
        )
        state = course_status(workspace)
        self.assertEqual(state["labs"][0]["status"], "stale")
        self.assertEqual(state["labs"][1]["status"], "stale")

    def test_instructor_cli_foundation_builds_its_own_corpus_weights_and_task(self):
        workspace = self.root / "automatic"
        init_workspace(workspace, mode="instructor")
        first = run_lab(workspace, 1, mode="instructor")
        second = run_lab(workspace, 2, mode="instructor")
        third = run_lab(workspace, 3, mode="instructor")
        self.assertEqual(
            [first["status"], second["status"], third["status"]],
            ["complete", "complete", "complete"],
        )
        self.assertIn("generated_corpus_manifest", first["inputs"])
        self.assertIn("weight_fixture_receipt_sha256", second["inputs"])
        self.assertTrue(
            (workspace / third["outputs"][0]["path"] / "baseline-candidate").is_dir()
        )

    def test_group_split_preserves_lineage_and_fails_on_leakage(self):
        _, rows = self._records(self.root / "records", count=15)
        first = split_by_group(rows, seed="seed-1")
        second = split_by_group(rows, seed="seed-1")
        self.assertEqual(first, second)
        self.assertEqual(
            [row["record_id"] for row in first], [row["record_id"] for row in rows]
        )
        self.assertEqual({row["split"] for row in first}, {"train", "dev", "test"})
        bad = [
            dict(row, split="train" if row["record_id"] == "r-00" else "test")
            for row in first
        ]
        # Give two records a shared group to model related runs being separated.
        bad[1]["group_id"] = bad[0]["group_id"]
        with self.assertRaises(ContractError):
            validate_group_splits(bad)

    def test_lab1_rejects_in_place_nested_receipt_mutation(self):
        records_path, rows = self._records(self.root / "records", count=15)

        def malicious(records, *, seed, fractions=None):
            records[0]["source_receipt"]["sha256"] = "0" * 64
            return tuple(
                dict(
                    row, split="train" if index < 9 else "dev" if index < 12 else "test"
                )
                for index, row in enumerate(records)
            )

        with self.assertRaises(ContractError) as error:
            course_checks.run_lab01(
                malicious, records_path, self.root / "mutation", seed="test"
            )
        self.assertIn("changed a record", str(error.exception))

    def test_int4_check_compares_student_code_to_separate_oracle(self):
        result = run_lab02(
            pack_int4,
            unpack_int4,
            (0, 15, 2, 13, 4, 11),
            self.root / "int4",
            source_identity="executed-weight-fixture-hash",
        )
        self.assertEqual(result["status"], "pass")
        self.assertEqual(unpack_int4(pack_int4((0, 15, 2, 13))), (0, 15, 2, 13))
        with self.assertRaises(ContractError):
            run_lab02(
                lambda values: bytes(reversed(pack_int4(values))),
                unpack_int4,
                (0, 15, 2, 13),
                self.root / "bad-int4",
                source_identity="negative-control",
            )

    def test_unresolved_physical_check_stays_pending_instead_of_becoming_failure_or_pass(
        self,
    ):
        self.assertEqual(
            course_checks._physical_acceptance_status(
                {
                    "all_required_passed": False,
                    "checks": [
                        {"name": "rtl_netlist_correspondence", "status": "unresolved"}
                    ],
                }
            ),
            "unresolved",
        )
        self.assertEqual(
            course_checks._physical_acceptance_status(
                {
                    "all_required_passed": False,
                    "checks": [{"name": "timing", "status": "fail"}],
                }
            ),
            "fail",
        )

    def test_receipt_adapter_keeps_tool_error_and_wrong_scope_ineligible(self):
        task = Task("test-task", ("keep",), (CheckRequirement("golden", "block"),))
        candidate_root = self.root / "candidate"
        candidate_root.mkdir()
        source = candidate_root / "design.txt"
        source.write_text("fixed candidate")
        candidate = Candidate(
            "c0",
            task.task_id,
            str(candidate_root),
            Action("keep"),
            (Artifact.from_file(candidate_root, source.name),),
            task_digest=task.digest,
        )
        check = {"name": "golden", "status": "pass", "scope": "block"}
        raw = {
            "task_id": task.task_id,
            "candidate_digest": candidate.digest,
            "mode": "fixture",
            "execution_status": "success",
            "tool": "fixture",
            "tool_version": "1",
            "checks": [check],
            "metrics": {},
            "cost": {"wall_seconds": 0.0},
        }
        receipt = adapt_receipt(raw, task, candidate)
        summary = summarize_cost((receipt,))
        self.assertEqual(summary["fresh_wall_seconds"], 0.0)
        raw["candidate_digest"] = "0" * 64
        with self.assertRaises(ContractError):
            reference_adapter(raw, task, candidate)

    def test_search_policy_runs_distinct_actions_through_shared_runner(self):
        result = run_lab06(FirstUntriedSearch(), self.root / "search")
        self.assertEqual(result["status"], "pass")
        events = [
            json.loads(line)
            for line in (self.root / "search/events.jsonl").read_text().splitlines()
        ]
        proposals = [
            event["action"]["name"] for event in events if event["event"] == "proposal"
        ]
        self.assertEqual(proposals, ["candidate_a", "candidate_b"])
        campaign = result["campaign"]["campaign"]
        self.assertFalse(any(item["eligible"] for item in campaign["observations"]))

    def test_training_checkpoint_action_and_harness_are_connected(self):
        import importlib.util

        if importlib.util.find_spec("torch") is None:
            self.skipTest("CPU PyTorch unavailable")
        from nanochip.laboratory.course.reference import lab04_train, lab05_inference
        from nanochip.laboratory.model_io import ModelIOContract
        from nanochip.laboratory.contracts import file_sha256

        source = self.root / "source.md"
        source.write_text(
            "The model reads a prompt and chooses an action.\n", encoding="utf-8"
        )
        source_sha = file_sha256(source)
        records = self.root / "records.jsonl"
        rows = [
            {
                "record_id": f"doc-{index}",
                "group_id": f"group-{index}",
                "split": "train",
                "original_split": "train",
                "input_text": f"workload detail {index}",
                "source_sha256": source_sha,
                "source_receipt": {"path": "source.md", "sha256": source_sha},
                "source_root": str(self.root),
                "label_origin": "unlabeled text; next-byte prediction",
                "data_origin": "repository_documentation",
            }
            for index in range(3)
        ]
        records.write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )
        contract = ModelIOContract(
            "course-test", 1, "utf8-line", ("read", "compute"), 180
        )
        trained = course_checks.run_lab04(
            lab04_train,
            records,
            contract.to_dict(),
            self.root / "trained",
            budget={"max_steps": 1, "max_seconds": 15, "seed": 7},
        )
        self.assertEqual(trained["check"]["status"], "pass")

        class FixtureMaterializer:
            def materialize(self, task, action, workspace):
                candidate_root = Path(workspace) / "candidate"
                candidate_root.mkdir()
                (candidate_root / "action.json").write_text(
                    json.dumps({"action": action.name})
                )
                return Candidate(
                    action.name,
                    task.task_id,
                    str(candidate_root),
                    action,
                    (Artifact.from_file(candidate_root, "action.json"),),
                    task_digest=task.digest,
                )

        class FixtureBackend:
            def evaluate(self, task, candidate):
                return RunReceipt(
                    task.task_id,
                    candidate.digest,
                    "fixture",
                    "success",
                    "test",
                    "1",
                    checks=(CheckResult("candidate_identity", "pass", "fixture"),),
                    cost=Cost(0),
                )

        task = Task(
            "test-inference",
            contract.actions,
            (CheckRequirement("candidate_identity", "fixture"),),
        )
        inferred = course_checks.run_lab05(
            lab05_inference,
            self.root / "trained/checkpoint",
            contract.to_dict(),
            "workload detail",
            self.root / "inferred",
            documents=[],
            model_factory=lab04_train.build_model,
            task=task,
            materializer=FixtureMaterializer(),
            backend=FixtureBackend(),
            receipt_adapter=type(
                "ReceiptAdapter", (), {"adapt_receipt": staticmethod(reference_adapter)}
            ),
        )
        self.assertEqual(inferred["check"]["status"], "pass")
        self.assertIn(inferred["report"]["action"], contract.actions)
        observation = inferred["report"]["harness_campaign"]["observations"][0]
        self.assertFalse(observation["eligible"])

    def test_documentation_corpus_is_snapshotted_by_lab1_split(self):
        from nanochip.laboratory.course.checks import run_lab01
        from nanochip.laboratory.course.reference import lab01_data
        from nanochip.laboratory.language_data import collect_language_corpus

        corpus = collect_language_corpus(self.root / "corpus", max_text_bytes=512)
        records = self.root / "language-records.jsonl"
        records.write_text(
            "".join(json.dumps(row) + "\n" for row in corpus["records"]),
            encoding="utf-8",
        )
        result = run_lab01(
            lab01_data.split_records,
            records,
            self.root / "split",
            seed="student-course-test",
        )
        self.assertEqual(result["check"]["status"], "pass")
        rows = [
            json.loads(line)
            for line in (self.root / "split/records.jsonl").read_text().splitlines()
        ]
        self.assertEqual(len(rows), len(corpus["records"]))
        self.assertTrue(
            all(
                Path(row["source_root"]).is_relative_to((self.root / "split").resolve())
                for row in rows
            )
        )

    def test_lab5_retrieval_guards_reject_forged_mutated_and_overbudget_context(self):
        import hashlib
        from nanochip.laboratory.course.checks import validate_student_context

        source_text = "alpha beta gamma delta"
        source = {
            "source_id": "approved-doc",
            "partition": "specification",
            "text": source_text,
            "text_sha256": hashlib.sha256(source_text.encode()).hexdigest(),
            "source": "/docs/spec.md",
            "file_sha256": "a" * 64,
        }

        def excerpt(source_id, text):
            return {
                "source_id": source_id,
                "partition": source["partition"],
                "text": text,
                "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "source": source["source"],
                "file_sha256": source["file_sha256"],
            }

        valid = validate_student_context(
            (source,), (excerpt("approved-doc", "alpha beta"),), word_budget=2
        )
        self.assertEqual(valid[0]["text"], "alpha beta")
        with self.assertRaises(ContractError):
            validate_student_context(
                (source,), (excerpt("forged-doc", "alpha beta"),), word_budget=2
            )
        with self.assertRaises(ContractError):
            validate_student_context(
                (source,), (excerpt("approved-doc", "alpha forged"),), word_budget=2
            )
        with self.assertRaises(ContractError):
            validate_student_context(
                (source,), (excerpt("approved-doc", "alpha beta gamma"),), word_budget=2
            )


if __name__ == "__main__":
    unittest.main()
