from __future__ import annotations

import os
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "publish-site.yml"
VALIDATE_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "validate.yml"
REPLAY_ASSETS = (
    "examples/design-loop-cards/array-study-v2.yaml",
    "examples/design-loop-cards/replay-environment.json",
    "examples/design-loop-cards/replay.py",
    "examples/design-loop-cards/workloads/illustrative-conv-layer-set-v1.json",
    "examples/design-loop-cards/evidence/illustrative-array-summary-16x16.json",
    "examples/design-loop-cards/evidence/illustrative-array-summary-32x8.json",
)
REGISTRY_SNAPSHOT = "tools/snapshots/registry-2026-07-14.yml"


def run_git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


class PublishSiteContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = yaml.safe_load(WORKFLOW_PATH.read_text())
        cls.validate_workflow = yaml.safe_load(VALIDATE_WORKFLOW_PATH.read_text())
        guard_steps = cls.workflow["jobs"]["publish_guard"]["steps"]
        cls.guard_script = next(
            step["run"]
            for step in guard_steps
            if step["name"] == "Authorize publish ref"
        )

    def test_replay_packet_assets_are_required_in_source_and_publish_payload(
        self,
    ) -> None:
        source_steps = self.validate_workflow["jobs"]["render"]["steps"]
        source_script = next(
            step["run"]
            for step in source_steps
            if step["name"] == "Validate public artifact sources"
        )
        publish_steps = self.workflow["jobs"]["build"]["steps"]
        publish_script = next(
            step["run"]
            for step in publish_steps
            if step["name"] == "Validate Pages payload"
        )

        for relative_path in REPLAY_ASSETS:
            self.assertIn(f"test -f {relative_path}", source_script)
            self.assertIn(f"test -f _site/{relative_path}", publish_script)
        self.assertNotIn("scale-sim-summary", source_script)
        self.assertNotIn("scale-sim-summary", publish_script)

    def test_frozen_registry_snapshot_is_required_in_source_and_publish_payload(
        self,
    ) -> None:
        source_steps = self.validate_workflow["jobs"]["render"]["steps"]
        source_script = next(
            step["run"]
            for step in source_steps
            if step["name"] == "Validate public artifact sources"
        )
        publish_steps = self.workflow["jobs"]["build"]["steps"]
        publish_script = next(
            step["run"]
            for step in publish_steps
            if step["name"] == "Validate Pages payload"
        )

        self.assertIn(f"test -f {REGISTRY_SNAPSHOT}", source_script)
        self.assertIn(f"test -f _site/{REGISTRY_SNAPSHOT}", publish_script)

    def run_guard(
        self, cwd: Path, ref: str, revision: str, **overrides: str
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update({"GITHUB_REF": ref, "GITHUB_SHA": revision})
        # Refusals are settled in one pass here; the real workflow waits out
        # the gap between the tag push and the main push.
        environment.setdefault("PUBLISH_GUARD_MAIN_WAIT_ATTEMPTS", "1")
        environment.setdefault("PUBLISH_GUARD_MAIN_WAIT_SECONDS", "0")
        environment.update(overrides)
        return subprocess.run(
            ["bash", "-c", self.guard_script],
            cwd=cwd,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )

    def make_repository(self, root: Path) -> tuple[Path, str, str]:
        origin = root / "origin.git"
        seed = root / "seed"
        runner = root / "runner"
        run_git(root, "init", "--bare", str(origin))
        run_git(root, "init", "--initial-branch=main", str(seed))
        run_git(seed, "config", "user.name", "Contract Test")
        run_git(seed, "config", "user.email", "contract@example.com")
        (seed / "release.txt").write_text("main\n")
        run_git(seed, "add", "release.txt")
        run_git(seed, "commit", "-m", "main release")
        main_revision = run_git(seed, "rev-parse", "HEAD")
        run_git(seed, "tag", "v1.2.3")
        run_git(seed, "remote", "add", "origin", str(origin))
        run_git(seed, "push", "origin", "main", "v1.2.3")

        run_git(seed, "switch", "--orphan", "unmerged")
        (seed / "unmerged.txt").write_text("unmerged\n")
        run_git(seed, "add", "unmerged.txt")
        run_git(seed, "commit", "-m", "unmerged release")
        unmerged_revision = run_git(seed, "rev-parse", "HEAD")
        run_git(seed, "tag", "v2.0.0")
        run_git(seed, "push", "origin", "v2.0.0")

        run_git(root, "clone", str(origin), str(runner))
        run_git(runner, "fetch", "--tags", "origin")
        return runner, main_revision, unmerged_revision

    def test_guard_is_a_direct_dependency_of_every_publish_job(self) -> None:
        jobs = self.workflow["jobs"]
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})
        self.assertEqual(jobs["publish_guard"]["permissions"], {"contents": "read"})
        for job_name, job in jobs.items():
            if job_name == "publish_guard":
                continue
            needs = job.get("needs", [])
            if isinstance(needs, str):
                needs = [needs]
            self.assertIn("publish_guard", needs, job_name)

        for job_name, job in jobs.items():
            if job_name == "deploy":
                continue
            permissions = job.get("permissions", self.workflow["permissions"])
            self.assertTrue(
                all(access == "read" for access in permissions.values()), job_name
            )
        self.assertEqual(
            jobs["deploy"]["permissions"],
            {"contents": "read", "id-token": "write", "pages": "write"},
        )

    def test_guard_contains_tag_identity_fetch_and_ancestry_checks(self) -> None:
        self.assertIn(r"^refs/tags/v[0-9]+\.[0-9]+\.[0-9]+$", self.guard_script)
        self.assertIn("${GITHUB_REF}^{commit}", self.guard_script)
        self.assertIn("${GITHUB_SHA}^{commit}", self.guard_script)
        self.assertIn("+refs/heads/main:refs/remotes/origin/main", self.guard_script)
        self.assertIn("git merge-base --is-ancestor", self.guard_script)

    def test_main_and_ancestor_stable_tag_are_authorized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner, main_revision, _ = self.make_repository(root)

            main_result = self.run_guard(runner, "refs/heads/main", main_revision)
            self.assertEqual(main_result.returncode, 0, main_result.stderr)

            run_git(runner, "update-ref", "-d", "refs/remotes/origin/main")
            tag_result = self.run_guard(runner, "refs/tags/v1.2.3", main_revision)
            self.assertEqual(tag_result.returncode, 0, tag_result.stderr)
            self.assertEqual(
                run_git(runner, "rev-parse", "refs/remotes/origin/main"),
                main_revision,
            )

    def test_non_stable_and_non_main_refs_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner, main_revision, _ = self.make_repository(root)
            for ref in (
                "refs/heads/dev",
                "refs/tags/v1.2",
                "refs/tags/v1.2.3-rc.1",
                "refs/tags/release-v1.2.3",
            ):
                with self.subTest(ref=ref):
                    result = self.run_guard(runner, ref, main_revision)
                    self.assertNotEqual(result.returncode, 0)

    def test_guard_waits_for_the_main_push_that_follows_a_release_tag(self) -> None:
        """A release tag that lands moments before its main push still publishes."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner, main_revision, unmerged_revision = self.make_repository(root)

            # Reproduce the race: origin/main still points at the previous
            # release when the tag event arrives, and catches up mid-wait.
            origin = root / "origin.git"
            run_git(origin, "update-ref", "refs/heads/main", unmerged_revision)

            def advance_main_after_first_attempt() -> None:
                time.sleep(1)
                run_git(origin, "update-ref", "refs/heads/main", main_revision)

            catch_up = threading.Thread(target=advance_main_after_first_attempt)
            catch_up.start()
            try:
                result = self.run_guard(
                    runner,
                    "refs/tags/v1.2.3",
                    main_revision,
                    PUBLISH_GUARD_MAIN_WAIT_ATTEMPTS="6",
                    PUBLISH_GUARD_MAIN_WAIT_SECONDS="1",
                )
            finally:
                catch_up.join()

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Authorized stable release tag", result.stdout)

    def test_stable_tag_outside_main_history_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner, _, unmerged_revision = self.make_repository(root)
            result = self.run_guard(runner, "refs/tags/v2.0.0", unmerged_revision)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not an ancestor", result.stderr)


if __name__ == "__main__":
    unittest.main()
