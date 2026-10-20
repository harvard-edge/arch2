"""Reject unsuccessful Magic execution even when its output path exists."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from nanochip.laboratory.physical.magic_flow import (
    LEF_COMPLETE, build_magic_exit_step, build_write_lef_step, validate_lef_completion,
)


VALID_LEF = "VERSION 5.7 ;\nMACRO core\n CLASS BLOCK ;\nEND core\nEND LIBRARY\n"


class NativePatternWriteLEF:
    """Retain the pinned producer's unchecked-exit and exists-only behavior."""
    outputs = ["lef"]

    def __init__(self, root, *, exit_code=0, lef=VALID_LEF, marker=True):
        self.step_dir = str(root)
        self.config = {"DESIGN_NAME": "core"}
        self.exit_code, self.lef, self.marker = exit_code, lef, marker

    def get_script_path(self):
        return str(Path(self.step_dir) / "lef.tcl")

    def run_subprocess(self, command, *, check):
        completed = subprocess.run(command, check=check, capture_output=True)
        return {"returncode": completed.returncode,
                "log_path": str(Path(self.step_dir) / "magic-writelef.log")}

    def run(self, state_in, **kwargs):
        self.get_script_path()
        root = Path(self.step_dir)
        (root / "core.lef").write_text(self.lef)
        (root / "magic-writelef.log").write_text(LEF_COMPLETE + "\n" if self.marker else "Writing LEF output\n")
        program = ("import os,signal; os.kill(os.getpid(), signal.SIGKILL)" if self.exit_code == -9
                   else "import sys; sys.exit(" + str(self.exit_code) + ")")
        self.run_subprocess([sys.executable, "-c", program], check=kwargs.get("check", False))
        return {"lef": root / "core.lef"}, {"unrelated_metric": 7}


class MagicFlowTests(unittest.TestCase):
    def test_shared_exit_check_rejects_failed_process_with_existing_output(self):
        checked = build_magic_exit_step(NativePatternWriteLEF, step_error=RuntimeError)
        for code in (1, 137, -9):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                with self.assertRaises(subprocess.CalledProcessError):
                    checked(root, exit_code=code).run(None, check=False)
                self.assertTrue((root / "core.lef").is_file())

    def test_shared_exit_check_preserves_native_metrics_and_views(self):
        checked = build_magic_exit_step(NativePatternWriteLEF, step_error=RuntimeError)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            views, metrics = checked(root).run(None, check=False)
            self.assertEqual(views, {"lef": root / "core.lef"})
            # A nonzero native metric must remain nonzero after successful
            # process completion; exit status is not physical acceptance.
            self.assertEqual(metrics, {"unrelated_metric": 7})

    def test_completion_rejects_empty_truncated_wrong_top_and_missing_marker(self):
        cases = [
            ("", True),
            ("MACRO core\n", True),
            ("MACRO other\nEND other\nEND LIBRARY\n", True),
            ("MACRO core\nEND core\n", True),
            ("END core\nMACRO core\nEND LIBRARY\n", True),
            (VALID_LEF + "MACRO trailing\n", True),
            (VALID_LEF.replace("END core", "END core\nEND core"), True),
            (VALID_LEF, False),
        ]
        for lef, marker in cases:
            with self.subTest(lef=lef, marker=marker), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "out.lef").write_text(lef)
                (root / "run.log").write_text(LEF_COMPLETE if marker else "")
                with self.assertRaises(ValueError):
                    validate_lef_completion(root / "out.lef", root / "run.log", "core", root)

    def test_redirected_output_and_duplicate_completion_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); step = root / "step"; step.mkdir()
            (root / "outside.lef").write_text(VALID_LEF)
            (step / "redirect.lef").symlink_to(root / "outside.lef")
            (step / "run.log").write_text(LEF_COMPLETE + "\n")
            for path in (root / "outside.lef", step / "redirect.lef"):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    validate_lef_completion(path, step / "run.log", "core", step)
            (step / "local.lef").write_text(VALID_LEF)
            (step / "run.log").write_text((LEF_COMPLETE + "\n") * 2)
            with self.assertRaises(ValueError):
                validate_lef_completion(step / "local.lef", step / "run.log", "core", step)

    def test_real_nonzero_child_exit_cannot_be_suppressed_by_magic_default(self):
        checked = build_write_lef_step(SimpleNamespace(WriteLEF=NativePatternWriteLEF), step_error=RuntimeError)
        for code in (1, 137, -9):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                # Exercise a real child exit through the producer's check=False
                # path; a complete-looking artifact still cannot make it pass.
                with patch.object(checked, "get_script_path", return_value="pinned-script"):
                    with self.assertRaises(subprocess.CalledProcessError):
                        checked(root, exit_code=code).run(None, check=False)
                receipt = json.loads((root / "nanochip-lef-producer.json").read_text())
                self.assertEqual(receipt["status"], "error")
                self.assertEqual(receipt["returncode"], code)

    def test_zero_exit_with_empty_output_fails_before_view_is_returned(self):
        checked = build_write_lef_step(SimpleNamespace(WriteLEF=NativePatternWriteLEF), step_error=RuntimeError)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(checked, "get_script_path", return_value="pinned-script"):
                with self.assertRaisesRegex(ValueError, "empty LEF"):
                    checked(root, lef="").run(None)
            receipt = json.loads((root / "nanochip-lef-producer.json").read_text())
            self.assertEqual(receipt["status"], "error")
            self.assertEqual(receipt["invocations"][0]["returncode"], 0)

    def test_success_preserves_views_and_metrics_and_binds_evidence(self):
        checked = build_write_lef_step(SimpleNamespace(WriteLEF=NativePatternWriteLEF), step_error=RuntimeError)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(checked, "get_script_path", return_value="pinned-script"):
                views, metrics = checked(root).run(None)
            self.assertEqual(views, {"lef": root / "core.lef"})
            self.assertEqual(metrics, {"unrelated_metric": 7})
            receipt = json.loads((root / "nanochip-lef-producer.json").read_text())
            self.assertEqual(receipt["status"], "pass")
            self.assertEqual(receipt["returncode"], 0)
            self.assertEqual(receipt["output"]["completion_markers"], 1)
            self.assertEqual(len(receipt["output"]["lef_sha256"]), 64)

    def test_changed_upstream_script_is_rejected_before_child_runs(self):
        checked = build_write_lef_step(SimpleNamespace(WriteLEF=NativePatternWriteLEF), step_error=RuntimeError)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / "lef.tcl").write_text("puts changed\n")
            with self.assertRaisesRegex(RuntimeError, "script identity"):
                checked(root).run(None)
            self.assertFalse((root / "core.lef").exists())
            self.assertEqual(json.loads((root / "nanochip-lef-producer.json").read_text())["status"], "error")


if __name__ == "__main__":
    unittest.main()
