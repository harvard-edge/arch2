"""End-to-end software checks for shape-only microcode and independent ISA VM."""
import json
from pathlib import Path
import struct
import tempfile
import unittest

import numpy as np

from nanochip.laboratory.teaching_core.compiler import CompiledProgram, compile_program
from nanochip.laboratory.teaching_core.fixtures import build_fixture
from nanochip.laboratory.teaching_core.interpreter import execute
from nanochip.laboratory.teaching_core.isa import (
    DATA_BASE,
    TABLE_BASE,
    Op,
    encode,
    program_bytes,
)


class CompleteTeachingCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.long = compile_program(4)
        cls.short = compile_program(2)

    def test_static_memory_and_firmware_bounds(self):
        self.assertLess(len(self.long.program), DATA_BASE)
        self.assertEqual(
            self.long.required_words, self.long.manifest["static_high_water_words"]
        )
        self.assertLessEqual(self.long.required_words, 512)
        self.assertEqual(self.long.manifest["minimum_power_of_two_words"], 512)
        self.assertEqual(self.long.program, compile_program(4).program)
        self.assertEqual(self.long.tables, self.short.tables)
        self.assertEqual(len(self.long.program), len(self.short.program))
        regions = list(self.long.table_regions.values())
        for a, b in zip(regions, regions[1:]):
            self.assertLessEqual(a["address"] + 8 * a["entries"], b["address"])
        self.assertEqual(regions[0]["address"], TABLE_BASE)

    def test_complete_workloads_exact_against_frozen_integer(self):
        with tempfile.TemporaryDirectory() as tmp:
            for seed, tokens, program in [
                (1, None, self.long),
                (7, [3, 3, 1, 15], self.long),
                (29, [15, 0], self.short),
                (5, [4], compile_program(1)),
                (9, [2, 6, 2], compile_program(3)),
            ]:
                dest = Path(tmp) / str(seed)
                receipt = build_fixture(
                    dest,
                    seed=seed,
                    prompt_index=0 if program.token_count == 4 else 1,
                    tokens=tokens,
                )
                image = (dest / "image.bin").read_bytes()
                result = execute(program, image)
                golden = np.load(dest / "goldens.npz")
                np.testing.assert_array_equal(result.logits, golden["fixed_logits"])
                np.testing.assert_array_equal(result.argmax, golden["fixed_argmax"])
                intermediate = np.load(dest / "fixed_intermediates.npz")
                np.testing.assert_array_equal(
                    np.asarray(result.observations["L0.kda_core"]) / (1 << 26),
                    intermediate["kda_core"],
                )
                np.testing.assert_array_equal(
                    np.asarray(result.observations["L1.mla_ctx"]) / (1 << 26),
                    intermediate["mla_ctx"],
                )
                for li in range(2):
                    np.testing.assert_array_equal(
                        np.asarray(result.observations[f"L{li}.layer_out"]) / (1 << 26),
                        intermediate["layer_out"][li::2],
                    )
                    np.testing.assert_array_equal(
                        result.observations[f"L{li}.moe_indices"],
                        intermediate["moe_sel"][li::2, 0],
                    )
                    np.testing.assert_array_equal(
                        np.asarray(result.observations[f"L{li}.moe_weights"])
                        / (1 << 26),
                        intermediate["moe_sel"][li::2, 1],
                    )
                status_addr = receipt["layout"]["out_status_addr"]
                self.assertEqual(
                    struct.unpack_from("<I", result.image, status_addr)[0], 0x600DD00D
                )
                # Fresh execute must reconstruct state despite prior workload.
                repeated = execute(program, image)
                self.assertEqual(result.image, repeated.image)
                self.assertGreater(result.external_reads, 0)
                self.assertEqual(
                    program.program, compile_program(program.token_count).program
                )

    def test_runtime_router_ties_use_lowest_indices_and_unbiased_weights(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "input"
            build_fixture(dest, seed=11)
            image = bytearray((dest / "image.bin").read_bytes())
            for descriptor in self.long.manifest["tensor_descriptors"]:
                if descriptor["name"].endswith(
                    ("moe.router.q", "moe.router.z", "moe.bias")
                ):
                    d = descriptor["descriptor_address"] - DATA_BASE
                    _, address, size, _ = struct.unpack_from("<4I", image, d)
                    image[address : address + size] = bytes(size)
            result = execute(self.long, image)
            expected = (round(2.828 * (1 << 26)) + 1) // 2
            for li in range(2):
                self.assertEqual(
                    result.observations[f"L{li}.moe_indices"], [[0, 1]] * 4
                )
                self.assertEqual(
                    result.observations[f"L{li}.moe_weights"],
                    [[expected, expected]] * 4,
                )
            self.assertEqual(result.image, execute(self.long, result.image).image)

    def test_interpreter_reads_instruction_stream_not_host_operators(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "input"
            build_fixture(dest, seed=3)
            image = (dest / "image.bin").read_bytes()
            # Tiny ISA program writes a genuine calculated signed result to logits.
            out = struct.unpack_from("<I", image, 25 * 4)[0] + DATA_BASE
            ins = [
                encode(Op.LI, rd=0, imm=-7),
                encode(Op.LI, rd=1, imm=9),
                encode(Op.MUL, rd=2, ra=0, rb=1),
                encode(Op.LI, rd=3, imm=out),
                encode(Op.STX, ra=3, rb=2),
                encode(Op.HALT),
            ]
            p = CompiledProgram(program_bytes(ins), b"", 1, {})
            self.assertEqual(execute(p, image).logits[0][0], -63)
            p = CompiledProgram(
                program_bytes(
                    [encode(Op.LI, rd=0), encode(Op.LDS, rd=1, ra=0), encode(Op.HALT)]
                ),
                b"",
                1,
                {},
            )
            with self.assertRaisesRegex(RuntimeError, "Uninitialized scratch"):
                execute(p, image)

    def test_rejects_invalid_length(self):
        for n in (0, 5, True):
            with self.assertRaises(ValueError):
                compile_program(n)


if __name__ == "__main__":
    unittest.main()
