#!/usr/bin/env python3
"""Check resume compatibility against the released pilot records, without Docker.

Run from any directory with:
    python3 data/studies/06-eda-seed-dispersion/test_pilot_resume.py
"""

from __future__ import annotations

import contextlib
import copy
import csv
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

STUDY_DIR = Path(__file__).resolve().parent
RUNNER_PATH = (
    STUDY_DIR.parents[1] / "scrapers" / "run_openroad_gcd_placement_seed_pilot.py"
)
SPEC = importlib.util.spec_from_file_location("placement_seed_runner", RUNNER_PATH)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
RELEASED_CSV = STUDY_DIR / "openroad_gcd_placement_seed_pilot.csv"
RELEASED_SUMMARY = STUDY_DIR / "openroad_gcd_placement_seed_pilot_summary.json"


class PilotResumeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = runner.read_csv_rows(RELEASED_CSV)

    def test_released_rows_round_trip_without_changes(self) -> None:
        self.assertEqual(len(self.rows), 20)
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "pilot.csv"
            with mock.patch.object(runner, "CSV_PATH", destination):
                runner.write_csv(self.rows)
            self.assertEqual(destination.read_bytes(), RELEASED_CSV.read_bytes())

    def test_legacy_stdout_alias_is_accepted_and_conflicts_are_rejected(self) -> None:
        legacy = copy.deepcopy(self.rows)
        for row in legacy:
            row["stdout_dataset"] = row.pop("stdout_receipt")
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "legacy.csv"
            with source.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(legacy[0]))
                writer.writeheader()
                writer.writerows(legacy)
            self.assertEqual(runner.read_csv_rows(source), self.rows)

            conflicting = dict(self.rows[0], stdout_dataset="different-log.txt")
            with source.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(conflicting))
                writer.writeheader()
                writer.writerow(conflicting)
            with self.assertRaisesRegex(ValueError, "Conflicting stdout paths"):
                runner.read_csv_rows(source)

    def test_missing_build_artifacts_preserve_recorded_hashes(self) -> None:
        original = copy.deepcopy(self.rows)
        with tempfile.TemporaryDirectory() as directory:
            runner.refresh_retained_artifacts(self.rows, Path(directory) / "flow")
        self.assertEqual(self.rows, original)

    def test_conflicting_build_output_cannot_overwrite_retained_metrics(self) -> None:
        row = self.rows[0]
        original = copy.deepcopy(row)
        filename = "openroad_gcd_placement_seed_01.globalplace.json"
        retained_bytes = (
            STUDY_DIR / "raw-openroad-placement-pilot" / filename
        ).read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            flow = root / "flow"
            log_dir = flow / "logs" / "nangate45" / "gcd" / row["variant"]
            log_dir.mkdir(parents=True)
            (log_dir / "3_3_place_gp.json").write_text("{}\n", encoding="utf-8")
            raw_dir = root / "raw"
            raw_dir.mkdir()
            retained = raw_dir / filename
            retained.write_bytes(retained_bytes)
            with mock.patch.object(runner, "RAW_DIR", raw_dir):
                with self.assertRaisesRegex(ValueError, "differs from the recorded"):
                    runner.refresh_retained_artifacts([row], flow)
            self.assertEqual(retained.read_bytes(), retained_bytes)
        self.assertEqual(row, original)

    def test_completed_resume_preserves_csv_and_historical_execution_summary(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            csv_path = root / "pilot.csv"
            summary_path = root / "summary.json"
            csv_path.write_bytes(RELEASED_CSV.read_bytes())
            summary_path.write_bytes(RELEASED_SUMMARY.read_bytes())
            args = SimpleNamespace(
                orfs=root / "orfs",
                start_seed=1,
                end_seed=20,
                timeout_seconds=600,
                resume=True,
                full_flow_smoke_only=False,
            )
            prohibited = {
                name: mock.Mock(side_effect=AssertionError(f"Unexpected {name}"))
                for name in (
                    "run",
                    "refresh_retained_artifacts",
                    "write_csv",
                    "write_summary",
                )
            }
            with (
                mock.patch.multiple(
                    runner,
                    CSV_PATH=csv_path,
                    SUMMARY_PATH=summary_path,
                    RAW_DIR=root / "raw",
                    parse_args=lambda: args,
                    git_commit=lambda path: runner.ORFS_COMMIT,
                    require_clean_tracked_checkout=lambda path: None,
                    docker_metadata=lambda: {},
                    **prohibited,
                ),
                mock.patch.object(
                    runner.shutil, "which", return_value="/unused/docker"
                ),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(runner.main(), 0)
            for operation in prohibited.values():
                operation.assert_not_called()
            self.assertEqual(csv_path.read_bytes(), RELEASED_CSV.read_bytes())
            self.assertEqual(summary_path.read_bytes(), RELEASED_SUMMARY.read_bytes())


if __name__ == "__main__":
    unittest.main()
