"""Exercise the user command path with real data, weights, and held-out records."""

import importlib.util
import json

import pytest

from nanochip.laboratory.__main__ import main
from nanochip.laboratory.model_io import ModelIOContract


def test_language_commands_preserve_partitions_and_checkpoint_lineage(tmp_path):
    if importlib.util.find_spec("torch") is None:
        pytest.skip("CPU PyTorch unavailable")
    corpus = tmp_path / "corpus"
    assert main(["language", "collect", "--output", str(corpus), "--max-text-bytes", "64"]) == 0
    manifest = corpus / "manifest.json"
    profile = tmp_path / "profile.json"
    assert main(["language", "profile", "--corpus", str(manifest), "--output", str(profile)]) == 0
    assert json.loads(profile.read_text())["split_counts"]["test"] > 0
    contract = ModelIOContract("cli-byte-language", 1, "cli-byte-language-v1",
                               ("serial_mul1", "serial_mul2"), 64)
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(contract.to_dict()))
    base, adapted = tmp_path / "base", tmp_path / "adapted"
    shared = ["--corpus", str(manifest), "--contract", str(contract_path)]
    assert main(["language", "train", *shared, "--output", str(base), "--steps", "2"]) == 0
    assert main(["language", "train", *shared, "--base", str(base),
                 "--output", str(adapted), "--steps", "2"]) == 0
    first = json.loads((base / "training.json").read_text())
    second = json.loads((adapted / "training.json").read_text())
    assert first["parameters_changed"] and second["parameters_changed"]
    assert second["base_checkpoint_sha256"] == first["artifacts"]["checkpoint.pt"]
    assert {row["split"] for row in second["training_records"]} == {"train"}
    evaluation = tmp_path / "evaluation.json"
    assert main(["language", "evaluate", *shared, "--checkpoint", str(adapted),
                 "--split", "test", "--output", str(evaluation)]) == 0
    assert json.loads(evaluation.read_text())["split"] == "test"
    input_path = tmp_path / "input.txt"
    input_path.write_text("Choose a multiplier architecture.")
    inference = tmp_path / "inference.json"
    assert main(["language", "infer", "--checkpoint", str(adapted), "--contract", str(contract_path),
                 "--input-file", str(input_path), "--output", str(inference)]) == 0
    assert json.loads(inference.read_text())["action"] in contract.actions
    # A user command cannot overwrite the preserved evaluation.
    assert main(["language", "evaluate", *shared, "--checkpoint", str(adapted),
                 "--output", str(evaluation)]) == 2


def test_cli_profiles_only_verified_corpus_bytes(tmp_path):
    corpus = tmp_path / "corpus"
    assert main(["language", "collect", "--output", str(corpus)]) == 0
    (corpus / "sources/architecture.md").write_text("unattributed replacement")
    output = tmp_path / "profile.json"
    assert main(["language", "profile", "--corpus", str(corpus / "manifest.json"),
                 "--output", str(output)]) == 2
    assert not output.exists()
