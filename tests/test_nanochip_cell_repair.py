import json
from pathlib import Path
import tempfile
import unittest

from nanochip.laboratory.physical.cell_repair import (
    equivalent_drive_table,
    write_drive_table,
)


def library(*, altered=False, sequential=False, extra_pin=False):
    cells = []
    for name, cap in (
        ("buf_1", ".1"),
        ("buf_2", ".2"),
        ("buf_4", ".4"),
        ("clkdlybuf4s25_1", ".1"),
        ("clkdlybuf4s25_2", ".2"),
    ):
        function = "!A" if altered and name == "buf_2" else "A"
        state = (
            'ff (IQ, IQN) { clocked_on : "A"; next_state : "A"; }'
            if sequential and name == "buf_2"
            else ""
        )
        extra = (
            "pin (B) { direction : input; }" if extra_pin and name == "buf_2" else ""
        )
        cells.append(
            f"""cell (sky130_fd_sc_hd__{name}) {{
            pg_pin (VPWR) {{ pg_type : primary_power; voltage_name : VPWR; }}
            pg_pin (VGND) {{ pg_type : primary_ground; voltage_name : VGND; }}
            pin (A) {{ direction : input; }}
            pin (X) {{ direction : output; function : "{function}"; max_capacitance : {cap}; }}
            {state} {extra}
        }}"""
        )
    return "library (test) {" + "\n".join(cells) + "}"


class CellRepairTests(unittest.TestCase):
    def build(self, root, **last):
        paths = []
        for index in range(3):
            path = root / f"corner-{index}.lib"
            path.write_text(library(**(last if index == 2 else {})))
            paths.append(path)
        return paths

    def test_verified_double_drive_and_delay_exclusion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self.build(root)
            plan = write_drive_table(paths, root / "choices.tcl")
            self.assertEqual(
                plan["table"],
                {
                    "sky130_fd_sc_hd__buf_1": "sky130_fd_sc_hd__buf_2",
                    "sky130_fd_sc_hd__buf_2": "sky130_fd_sc_hd__buf_4",
                },
            )
            self.assertFalse(plan["eligible"])
            self.assertEqual(json.loads((root / "choices.json").read_text()), plan)
            self.assertIn("cell_models.py", plan["sources"])

    def test_changed_function_pin_or_sequential_state_cannot_be_selected(self):
        for mutation in ({"altered": True}, {"extra_pin": True}, {"sequential": True}):
            with self.subTest(
                mutation=mutation
            ), tempfile.TemporaryDirectory() as directory:
                plan = equivalent_drive_table(self.build(Path(directory), **mutation))
                self.assertNotEqual(
                    plan["table"].get("sky130_fd_sc_hd__buf_1"),
                    "sky130_fd_sc_hd__buf_2",
                )
                self.assertNotIn("sky130_fd_sc_hd__buf_2", plan["table"])

    def test_missing_increased_output_limit_cannot_be_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self.build(root)
            paths[2].write_text(
                paths[2]
                .read_text()
                .replace("max_capacitance : .2", "max_capacitance : .1")
            )
            plan = equivalent_drive_table(paths)
            self.assertNotEqual(
                plan["table"].get("sky130_fd_sc_hd__buf_1"), "sky130_fd_sc_hd__buf_2"
            )

    def test_missing_or_repeated_corner_files_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.build(Path(directory))
            for invalid in (paths[:2], [paths[0]] * 3):
                with self.assertRaises(ValueError):
                    equivalent_drive_table(invalid)


if __name__ == "__main__":
    unittest.main()
