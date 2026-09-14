from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
LABS_DIR = ROOT / "labs"


def _import_module_from_path(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MicroLoopWorkbenchTests(unittest.TestCase):
    def test_micro_loop_contracts_are_valid(self) -> None:
        subdirs = [
            "01-microarchitectural-sweep",
            "02-rtl-timing",
            "03-physical-floorplan",
            "04-hw-sw-codesign",
        ]
        for sub in subdirs:
            contract_file = LABS_DIR / sub / "contract.yaml"
            self.assertTrue(
                contract_file.is_file(), f"Missing contract: {contract_file}"
            )
            data = yaml.safe_load(contract_file.read_text(encoding="utf-8"))
            self.assertEqual(data.get("contract_version"), "2.0")
            self.assertIn("study_id", data)
            self.assertIn("constraints", data)
            self.assertIn("modes", data)
            self.assertIn("assisted", data["modes"])
            self.assertIn("driven", data["modes"])
            self.assertIn("native", data["modes"])

    def test_micro_loop_a_runs_and_distinguishes_paradigms(self) -> None:
        loop_a_py = LABS_DIR / "01-microarchitectural-sweep" / "run.py"
        mod = _import_module_from_path(loop_a_py, "loop_a_runner")
        workload = mod.load_workload(
            LABS_DIR / "01-microarchitectural-sweep" / "workload" / "xr_gemm.csv"
        )
        contract = yaml.safe_load(
            (LABS_DIR / "01-microarchitectural-sweep" / "contract.yaml").read_text(
                encoding="utf-8"
            )
        )

        assisted = mod.run_assisted_mode(workload, contract)
        driven = mod.run_driven_mode(workload, contract)
        native = mod.run_native_mode(workload, contract)

        self.assertEqual(assisted["mode"], "AI-Assisted")
        self.assertEqual(driven["mode"], "AI-Driven")
        self.assertEqual(native["mode"], "AI-Native")

        # Verify AI-Native slashes off-chip memory traffic compared to Output Stationary
        self.assertLess(
            native["best_candidate"]["total_dram_traffic"],
            driven["best_candidate"]["total_dram_traffic"],
        )

    def test_micro_loop_b_timing_and_formal_equivalence(self) -> None:
        loop_b_py = LABS_DIR / "02-rtl-timing" / "run.py"
        mod = _import_module_from_path(loop_b_py, "loop_b_runner")

        assisted = mod.simulate_timing("pe_accumulator_naive")
        driven = mod.simulate_timing("pe_accumulator_naive_tuned")
        native = mod.simulate_timing("pe_accumulator_carry_save")

        self.assertFalse(assisted["timing_passed"])
        self.assertFalse(driven["timing_passed"])
        self.assertTrue(native["timing_passed"])
        self.assertGreater(native["slack_ns"], 0.0)

        # Verify formal/functional equivalence matches golden reference
        self.assertTrue(mod.verify_equivalence(200))

    def test_micro_loop_c_floorplan_signoff(self) -> None:
        loop_c_py = LABS_DIR / "03-physical-floorplan" / "run.py"
        mod = _import_module_from_path(loop_c_py, "loop_c_runner")

        assisted = mod.evaluate_floorplan("assisted_draft")
        driven = mod.evaluate_floorplan("driven_hpwl_optimized")
        native = mod.evaluate_floorplan("native_cross_layer_placed")

        self.assertFalse(assisted["signoff_passed"])
        self.assertFalse(driven["signoff_passed"])
        self.assertTrue(native["signoff_passed"])
        self.assertEqual(native["drc_violations"], 0)
        self.assertLessEqual(native["peak_congestion_pct"], 85.0)

    def test_micro_loop_d_codesign_speedup(self) -> None:
        loop_d_py = LABS_DIR / "04-hw-sw-codesign" / "run.py"
        mod = _import_module_from_path(loop_d_py, "loop_d_runner")

        assisted = mod.evaluate_codesign("assisted_scalar_opcode")
        driven = mod.evaluate_codesign("driven_compiler_autotuned")
        native = mod.evaluate_codesign("native_joint_codesigned")

        self.assertFalse(assisted["signoff_passed"])
        self.assertFalse(driven["signoff_passed"])
        self.assertTrue(native["signoff_passed"])
        self.assertTrue(native["cycle_target_met"])
        self.assertTrue(native["area_target_met"])
        self.assertLess(native["total_cycles"], driven["total_cycles"])

    def test_master_run_all_and_plots(self) -> None:
        import subprocess
        import sys

        run_all_py = LABS_DIR / "run_all.py"
        res = subprocess.run(
            [sys.executable, str(run_all_py)], capture_output=True, text=True
        )
        self.assertEqual(res.returncode, 0, f"run_all.py failed: {res.stderr}")

        summary_file = LABS_DIR / "workbench_summary.json"
        self.assertTrue(summary_file.is_file())

        for sub in (
            "01-microarchitectural-sweep",
            "02-rtl-timing",
            "03-physical-floorplan",
            "04-hw-sw-codesign",
        ):
            plot_file = LABS_DIR / sub / "results.png"
            self.assertTrue(plot_file.is_file(), f"Missing plot: {plot_file}")
            self.assertGreater(
                plot_file.stat().st_size,
                5000,
                f"Plot {plot_file} is suspiciously small",
            )

    def test_cli_lab_subcommands(self) -> None:
        import subprocess
        import sys

        cli_py = ROOT / "cli" / "arch2.py"
        res_list = subprocess.run(
            [sys.executable, str(cli_py), "lab", "list"], capture_output=True, text=True
        )
        self.assertEqual(res_list.returncode, 0)
        self.assertIn("Micro-Loop A", res_list.stdout)
        self.assertIn("Micro-Loop D", res_list.stdout)

        res_run = subprocess.run(
            [sys.executable, str(cli_py), "lab", "run", "01", "--no-visual"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_run.returncode, 0)


if __name__ == "__main__":
    unittest.main()
