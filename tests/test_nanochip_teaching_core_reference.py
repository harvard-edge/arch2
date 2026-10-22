"""Complete geometry/reference checks. These do not execute teaching-core RTL."""

import importlib.util
import json
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest

from nanochip.laboratory.teaching_core import build_fixture, contract


@unittest.skipUnless(
    importlib.util.find_spec("numpy"),
    "NumPy is required for frozen numerical references",
)
class TeachingCoreReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def fixture(self, name, **kwargs):
        receipt = build_fixture(self.root / name, **kwargs)
        self.assertEqual(receipt["status"], "pass", receipt)
        import numpy as np

        with np.load(self.root / name / "goldens.npz") as arrays:
            golden = {k: arrays[k].copy() for k in arrays.files}
        return receipt, golden

    def test_complete_geometry_runs_both_reference_models(self):
        receipt, arrays = self.fixture("complete", seed=1)
        cfg = contract()["configuration"]
        self.assertEqual(
            arrays["fixed_logits"].shape, (cfg["seq_lens"][0], cfg["vocab"])
        )
        self.assertTrue(all(receipt["float_fixed_argmax_agreement"]))
        self.assertFalse(receipt["rtl_execution"])
        self.assertFalse(receipt["physical_execution"])
        self.assertFalse(receipt["complete_core_ready"])
        header = struct.unpack_from(
            "<64I", (self.root / "complete/image.bin").read_bytes()
        )
        self.assertEqual(header[2], cfg["n_layers"])
        self.assertEqual(header[3], cfg["d_model"])
        self.assertEqual(header[12], cfg["n_experts"])
        self.assertEqual(header[13], cfg["top_k"])

    def test_prefix_causality_and_context_sensitivity(self):
        import numpy as np

        _, full = self.fixture("full", tokens=[0, 1, 2, 3])
        _, prefix = self.fixture("prefix", tokens=[0, 1])
        _, other = self.fixture("other", tokens=[3, 2, 1, 3])
        np.testing.assert_array_equal(full["fixed_logits"][:2], prefix["fixed_logits"])
        self.assertFalse(
            np.array_equal(full["fixed_logits"][-1], other["fixed_logits"][-1])
        )

    def test_seed_changes_weights_and_complete_result(self):
        import numpy as np

        _, first = self.fixture("first", seed=1, tokens=[0, 1, 2, 3])
        _, second = self.fixture("second", seed=7, tokens=[0, 1, 2, 3])
        self.assertNotEqual(
            (self.root / "first/image.bin").read_bytes(),
            (self.root / "second/image.bin").read_bytes(),
        )
        self.assertFalse(np.array_equal(first["fixed_logits"], second["fixed_logits"]))

    def test_existing_output_and_bad_tokens_are_rejected(self):
        with self.assertRaises(FileExistsError):
            build_fixture(self.root)
        for tokens in ([], [16], [True], [0] * 5):
            with self.subTest(tokens=tokens), self.assertRaises(ValueError):
                build_fixture(self.root / "invalid", tokens=tokens)


if __name__ == "__main__":
    unittest.main()
