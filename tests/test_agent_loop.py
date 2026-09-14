from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from labs.referee import PhysicalVerificationReferee
from labs.model_drivers import (
    ReferenceDriver,
    create_model_driver,
    list_available_models,
)


class AgentLoopAndRefereeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.referee = PhysicalVerificationReferee(clock_period_ns=2.000)

    def test_referee_catches_stuck_at_zero_reward_hack(self) -> None:
        cheat_v = """
        module pe_accumulator_cheat (
            input wire clk, input wire rst_n, input wire valid_in,
            input wire [31:0] data_in, output wire [31:0] acc_out
        );
            assign acc_out = 32'd0;
        endmodule
        """
        receipt = self.referee.evaluate_verilog_code(
            cheat_v, "pe_accumulator_cheat", iteration=1
        )
        self.assertEqual(receipt.status, "FAIL")
        self.assertTrue(receipt.reward_hack_detected)
        self.assertEqual(receipt.slack, -999.0)
        self.assertIn("STUCK_AT_ZERO", receipt.verification_status)

    def test_referee_catches_pipeline_latency_drift(self) -> None:
        pipe_cheat_v = """
        module pe_accumulator_pipe_cheat (
            input wire clk, input wire rst_n, input wire valid_in,
            input wire [31:0] data_in, output reg [31:0] acc_out
        );
            reg [31:0] d_pipe;
            reg [31:0] acc;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    d_pipe <= 0;
                    acc <= 0;
                    acc_out <= 0;
                end else if (valid_in) begin
                    d_pipe <= data_in;
                    acc <= acc + d_pipe;
                    acc_out <= acc;
                end
            end
        endmodule
        """
        receipt = self.referee.evaluate_verilog_code(
            pipe_cheat_v, "pe_accumulator_pipe_cheat", iteration=1
        )
        self.assertEqual(receipt.status, "FAIL")
        self.assertIn("FAIL", receipt.verification_status)
        self.assertEqual(receipt.slack, -999.0)

    def test_referee_validates_carry_save_accumulator(self) -> None:
        csa_path = (
            ROOT / "labs" / "02-rtl-timing" / "rtl" / "pe_accumulator_carry_save.v"
        )
        csa_v = csa_path.read_text(encoding="utf-8")
        receipt = self.referee.evaluate_verilog_code(
            csa_v, "pe_accumulator_carry_save", iteration=3
        )
        self.assertEqual(receipt.status, "PASS")
        self.assertFalse(receipt.reward_hack_detected)
        self.assertGreater(receipt.slack, 0.0)
        self.assertIn("Bit-Exact Invariant Confirmed", receipt.verification_status)

    def test_model_drivers_factory_and_listing(self) -> None:
        models = list_available_models()
        self.assertGreaterEqual(len(models), 4)
        model_ids = [m["id"] for m in models]
        self.assertIn("reference", model_ids)
        self.assertIn("gpt-4o", model_ids)

        driver = create_model_driver("reference")
        self.assertIsInstance(driver, ReferenceDriver)
        p1 = driver.propose_turn(1, {}, [])
        self.assertEqual(p1.turn_number, 1)
        self.assertIn("pe_accumulator_naive", p1.proposed_action)

    def test_cli_agent_run_execution(self) -> None:
        cli_py = ROOT / "cli" / "arch2.py"
        res = subprocess.run(
            [
                sys.executable,
                str(cli_py),
                "agent",
                "run",
                "--model",
                "reference",
                "--width",
                "80",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"agent run failed: {res.stderr}")
        self.assertIn("CLOSED-LOOP OPTIMIZATION TRAJECTORY CONVERGENCE", res.stdout)
        self.assertIn("SIGNED OFF", res.stdout)


if __name__ == "__main__":
    unittest.main()
