"""Check source drift, incomplete inventories, mapping errors, and actual RTL."""

from copy import deepcopy
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from nanochip.laboratory.teaching_target import check_mapping, run_memory_check, validate_target
from nanochip.laboratory.teaching_target import mapping
from nanochip.laboratory.teaching_target.inventory import PACKAGE, SNAPSHOT, _modules


class MappingTests(unittest.TestCase):
    def test_inferred_storage_cannot_be_omitted_from_inventory(self):
        fixture = "module \\msh_chip_top\n  memory width 8 size 4 \\hidden\nend\n"
        with self.assertRaisesRegex(ValueError, "Uninventoried inferred memory"):
            _modules(fixture)

    def test_student_mapping_matches_instructor_for_every_input(self):
        self.assertEqual(check_mapping()["status"], "pass")

    def test_contiguous_address_bug_is_localized(self):
        bad = SimpleNamespace(word_address=lambda a: a & ((1 << 9) - 1), byte_strobes=mapping.byte_strobes)
        result = check_mapping(bad)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["function"], "word_address")
        self.assertNotEqual(result["actual"], result["expected"])

    def test_lane_strobe_bug_is_localized(self):
        bad = SimpleNamespace(word_address=mapping.word_address, byte_strobes=lambda m: m)
        self.assertEqual(check_mapping(bad)["function"], "byte_strobes")

    def test_noninteger_and_out_of_range_inputs_are_rejected(self):
        for function, limit in ((mapping.word_address, 1 << 14), (mapping.byte_strobes, 1 << 4)):
            for value in (-1, limit, True, 1.0):
                with self.subTest(function=function.__name__, value=value), self.assertRaises(ValueError):
                    function(value)

    def test_missing_verilator_is_unavailable_not_pass(self):
        with patch("nanochip.laboratory.teaching_target.exercise.shutil.which", return_value=None):
            result = run_memory_check()
        self.assertEqual(result["status"], "unavailable")
        self.assertFalse(result["ok"])

    def test_output_is_never_overwritten(self):
        with TemporaryDirectory() as tmp, self.assertRaises(FileExistsError):
            run_memory_check(tmp)

    def test_broken_student_source_produces_error_receipt(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "package"
            source.mkdir()
            for name in ("mapping.py", "reference.py", "memory_tb.sv"):
                shutil.copyfile(PACKAGE / name, source / name)
            (source / "mapping.py").write_text("def broken(:\n")
            with patch("nanochip.laboratory.teaching_target.exercise.PACKAGE", source):
                result = run_memory_check(Path(tmp) / "run")
            self.assertEqual(result["status"], "error")
            self.assertFalse(result["ok"])
            self.assertTrue((Path(tmp) / "run/receipt.json").is_file())

    def test_invalid_budget_is_rejected(self):
        for budget in (False, 0, -1, float("nan")):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                run_memory_check(timeout_s=budget)

    @unittest.skipUnless(shutil.which("verilator"), "Local Verilator not installed")
    def test_actual_frozen_memory_wrapper_and_contract(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "run"
            result = run_memory_check(out)
            self.assertEqual(result["status"], "pass", result)
            self.assertTrue(result["ok"])
            self.assertGreater(result["vectors"]["checked_cycles"], 0)
            self.assertFalse(result["complete_core_ready"])
            self.assertEqual(json.loads((out / "receipt.json").read_text()), result)
            self.assertTrue((out / "simulate.log").is_file())


@unittest.skipUnless(shutil.which("yosys"), "Local Yosys not installed")
class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.target = json.loads(SNAPSHOT.read_text())

    def test_snapshot_matches_fresh_source_elaboration(self):
        result = validate_target(self.target)
        self.assertEqual(result["status"], "pass")
        self.assertFalse(result["complete_core_ready"])

    def test_missing_memory_is_not_hidden_by_adjusted_totals(self):
        bad = deepcopy(self.target)
        removed = bad["memories"].pop()
        bad["totals"][removed["kind"] + "_instances"] -= 1
        bad["totals"][removed["kind"] + "_bits"] -= removed["capacity_bits"]
        bad["totals"]["all_memory_bits"] -= removed["capacity_bits"]
        with self.assertRaisesRegex(ValueError, "freshly elaborated"):
            validate_target(bad)

    def test_source_identity_and_geometry_changes_are_rejected(self):
        for key in ("source_artifacts", "memories"):
            bad = deepcopy(self.target)
            if key == "source_artifacts":
                bad[key][0]["sha256"] = "0" * 64
            else:
                bad[key][0]["depth_words"] += 1
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "freshly elaborated"):
                validate_target(bad)


if __name__ == "__main__":
    unittest.main()
