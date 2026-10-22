import json
import tempfile
import unittest
from pathlib import Path

from nanochip.laboratory.contracts import Artifact, ContractError
from nanochip.laboratory.data import load_dataset, training_records


class DatasetBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def entry(self, name, group, split, mode="fresh"):
        path = self.root / (name + ".json")
        path.write_text(json.dumps({"name": name, "mode": mode}))
        artifact = Artifact.from_file(self.root, path.name)
        return dict(
            record_id=name,
            group_id=group,
            split=split,
            evidence_mode=mode,
            construction="constructed_fault",
            source="unit-test-only",
            receipt=dict(path=artifact.path, sha256=artifact.sha256),
        )

    def manifest(self, rows):
        path = self.root / "dataset.json"
        path.write_text(
            json.dumps(dict(schema_version=1, dataset_id="test", records=rows))
        )
        return path

    def test_learner_only_receives_training_rows(self):
        path = self.manifest(
            [self.entry("a", "one", "train"), self.entry("b", "two", "test")]
        )
        self.assertEqual([r.record_id for r in training_records(path)], ["a"])

    def test_group_leakage_rejected_before_filtering(self):
        path = self.manifest(
            [self.entry("a", "one", "train"), self.entry("b", "one", "test")]
        )
        with self.assertRaises(ContractError):
            training_records(path)

    def test_replay_cannot_be_relabelled_fresh(self):
        row = self.entry("a", "one", "train", mode="replay")
        row["evidence_mode"] = "fresh"
        with self.assertRaises(ContractError):
            training_records(self.manifest([row]))

    def test_tampered_source_is_rejected(self):
        row = self.entry("a", "one", "train")
        (self.root / "a.json").write_text('{"mode": "fresh", "changed": true}')
        with self.assertRaises(ContractError):
            training_records(self.manifest([row]))

    def test_duplicate_receipt_cannot_cross_splits(self):
        a = self.entry("a", "one", "train")
        b = dict(a, record_id="b", group_id="two", split="test")
        with self.assertRaises(ContractError):
            load_dataset(self.manifest([a, b]), split="train")


if __name__ == "__main__":
    unittest.main()
