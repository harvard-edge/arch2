"""Actual RTL reset/restart and candidate checks using copied test fixtures."""

from pathlib import Path
from contextlib import contextmanager
import os
import shutil
import struct
from tempfile import TemporaryDirectory
import unittest

import numpy as np

from nanochip.laboratory.teaching_core import build_fixture, make_task, TeachingCoreMaterializer
from nanochip.laboratory.teaching_core.compiler import compile_program
from nanochip.laboratory.teaching_core.isa import DATA_BASE, Op, encode, program_bytes, signed
from nanochip.laboratory.teaching_core.rtl import BENCH, implementation_source, run_rtl
from nanochip.laboratory.contracts import Action, ContractError


@contextmanager
def _workspace(name):
    retained = os.environ.get("NANOCHIP_CORE_TEST_OUTPUT")
    if retained:
        path = Path(retained).resolve() / name
        path.mkdir(parents=True, exist_ok=False)
        yield str(path)
    else:
        with TemporaryDirectory() as tmp:
            yield tmp


class CoreMaterializationTests(unittest.TestCase):
    def test_actions_change_actual_rtl_and_preserve_program(self):
        with TemporaryDirectory() as tmp:
            task = make_task(seed=7, tokens=[0])
            one = TeachingCoreMaterializer().materialize(task, Action("serial_mul1"), Path(tmp) / "one")
            two = TeachingCoreMaterializer().materialize(task, Action("serial_mul2"), Path(tmp) / "two")
            self.assertNotEqual((Path(one.root) / "core.v").read_bytes(), (Path(two.root) / "core.v").read_bytes())
            for name in ("program.bin", "tables.bin", "reference/image.bin", "reference/goldens.npz"):
                self.assertEqual((Path(one.root) / name).read_bytes(), (Path(two.root) / name).read_bytes())
            one.validate_files(); two.validate_files()

    def test_invalid_action_parameters_are_rejected(self):
        with TemporaryDirectory() as tmp, self.assertRaises(ContractError):
            TeachingCoreMaterializer().materialize(make_task(), Action("serial_mul1", {"weaken_checks": True}), Path(tmp))

    def test_invalid_build_profile_is_rejected_before_output_creation(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "run"
            with self.assertRaisesRegex(ValueError, "build profile"):
                run_rtl("missing.v", "missing.bin", "missing.bin", "missing.bin",
                        output, build_profile="unchecked")
            self.assertFalse(output.exists())


@unittest.skipUnless(shutil.which("verilator"), "Local Verilator is required")
class ActualCoreRTLTests(unittest.TestCase):
    def test_all_integer_alu_operations_and_synchronous_scratch(self):
        cases = [
            (Op.ADD, -(1 << 62), 12345), (Op.SUB, -12345, 98765),
            (Op.MUL, -(1 << 50), (1 << 30) - 1), (Op.ASR, -987654321, 7),
            (Op.SHL, -17, 70), (Op.AND, -1, 0x12345678),
            (Op.OR, 0x12340000, 0x5678), (Op.XOR, -123, 0x123456),
            (Op.LT, -7, 9), (Op.EQ, -7, -7),
        ]
        operations = {
            Op.ADD: lambda a, b: a + b, Op.SUB: lambda a, b: a - b,
            Op.MUL: lambda a, b: a * b, Op.ASR: lambda a, b: a >> (b & 127),
            Op.SHL: lambda a, b: a << (b & 127), Op.AND: lambda a, b: a & b,
            Op.OR: lambda a, b: a | b, Op.XOR: lambda a, b: a ^ b,
            Op.LT: lambda a, b: int(a < b), Op.EQ: lambda a, b: int(a == b),
        }
        instructions = []
        expected = []
        for index, (op, a, b) in enumerate(cases):
            instructions.extend((encode(Op.LI, 1, imm=a), encode(Op.LI, 2, imm=b), encode(op, 3, 1, 2)))
            expected.append(signed(operations[op](a, b)))
            for word in range(4):
                instructions.extend((encode(Op.LI, 4, imm=word * 32), encode(Op.ASR, 5, 3, 4),
                                     encode(Op.LI, 6, imm=DATA_BASE + index * 16 + word * 4), encode(Op.STX, ra=6, rb=5)))
        # Store/read a signed scratch word through the actual synchronous port.
        instructions.extend((encode(Op.LI, 1, imm=3), encode(Op.LI, 2, imm=-1234567),
                             encode(Op.STS, ra=1, rb=2), encode(Op.LDS, 3, 1),
                             encode(Op.LI, 6, imm=DATA_BASE + len(cases) * 16), encode(Op.STX, ra=6, rb=3), encode(Op.HALT)))
        with _workspace("isa") as tmp:
            root = Path(tmp)
            (root / "program.bin").write_bytes(program_bytes(instructions))
            (root / "image.bin").write_bytes(bytes((len(cases) + 1) * 16))
            (root / "tables.bin").write_bytes(b"")
            (root / "core.v").write_text(implementation_source(2, 512))
            dumps = []
            for profile in ("rtl", "mapped"):
                with self.subTest(build_profile=profile):
                    output = root / profile
                    result = run_rtl(root / "core.v", root / "program.bin", root / "image.bin",
                                     root / "tables.bin", output, build_profile=profile)
                    self.assertTrue(result["ok"], result)
                    self.assertEqual(result["build_profile"], profile)
                    command = result["commands"][0]
                    self.assertEqual(command[command.index("-CFLAGS") + 1], "-O1" if profile == "mapped" else "-O3")
                    self.assertEqual("--output-groups" in command, profile == "mapped")
                    image = (output / "profile-00.bin").read_bytes()
                    dumps.append(image)
                    for index, value in enumerate(expected):
                        self.assertEqual(int.from_bytes(image[index*16:index*16+16], "little", signed=True), value)
                    self.assertEqual(struct.unpack_from("<i", image, len(cases)*16)[0], -1234567)
            self.assertEqual(dumps[0], dumps[1])

    def test_complete_same_dut_restart_and_midrun_reset(self):
        # Modify a TESTBENCH COPY only. The DUT/firmware/checker sources stay
        # frozen for simultaneous campaign and physical work.
        bench = BENCH.read_text()
        bench = bench.replace("bool started=false,completed=false,fault=false,held=false;",
                              "bool started=false,completed=false,fault=false,held=false; bool reset_done=false; int done_runs=0; std::vector<uint8_t> first_result;")
        bench = bench.replace("dut.clk=0; dut.rst_n=cycle>=16; dut.cmd_data=1;", """
            dut.clk=0; dut.rst_n=cycle>=16; dut.cmd_data=1;
            if(started && !reset_done && cycle-start>=3000000) {
                dut.rst_n=0; reset_done=true; started=false; held=false;
                pending.clear(); // External interface reset flushes pending reads.
            }
        """)
        bench = bench.replace("dut.cmd_valid=cycle>=16 && !started;", "dut.cmd_valid=dut.rst_n && !started;")
        bench = bench.replace("dut.mem_req_ready=random()%1000>=stall;", "dut.mem_req_ready=dut.rst_n && random()%1000>=stall;")
        original = "if(done) { completed=status==0x0000d0de; fault=!completed; completed_at=cycle; break; }"
        replacement = """if(done) {
            completed=status==0x0000d0de; fault=!completed; completed_at=cycle;
            if(fault) break;
            done_runs++;
            if(done_runs==1) {
                first_result.assign(memory.begin()+data_base,memory.begin()+data_base+image.size());
                started=false; completed=false; held=false; continue;
            }
            if(!reset_done || !std::equal(first_result.begin(),first_result.end(),memory.begin()+data_base)) errors++;
            std::cout<<"NANOCHIP_RESTART_PASS completed_runs="<<done_runs<<" reset="<<reset_done<<"\\n";
            break;
        }"""
        self.assertIn(original, bench)
        bench = bench.replace(original, replacement)
        with _workspace("restart") as tmp:
            root = Path(tmp)
            build_fixture(root / "reference", seed=19, tokens=[0, 1, 2, 3])
            compiled = compile_program(4)
            (root / "core.v").write_text(implementation_source(2, compiled.manifest["minimum_power_of_two_words"]))
            (root / "program.bin").write_bytes(compiled.program)
            (root / "tables.bin").write_bytes(compiled.tables)
            (root / "restart_tb.cpp").write_text(bench)
            result = run_rtl(root / "core.v", root / "program.bin", root / "reference/image.bin", root / "tables.bin", root / "run",
                             bench=root / "restart_tb.cpp", profiles=({"latency": 24, "stall_permille": 50, "reset_seed": 23, "jitter": 12},))
            self.assertTrue(result["ok"], result)
            self.assertIn("NANOCHIP_RESTART_PASS completed_runs=2 reset=1", (root / "run/profile-00.log").read_text())
            image = (root / "run/profile-00.bin").read_bytes()
            header = struct.unpack_from("<64I", image)
            actual = np.array([struct.unpack_from("<16i", image, header[25] + pos * header[30]) for pos in range(4)])
            with np.load(root / "reference/goldens.npz") as golden:
                np.testing.assert_array_equal(actual, golden["fixed_logits"])


if __name__ == "__main__":
    unittest.main()
