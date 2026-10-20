"""Build exact packed-image/software-golden fixtures in an isolated process."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from .contract import contract


def build_fixture(output: str | Path, seed: int = 1, prompt_index: int = 0, timeout_s: float = 120,
                  *, tokens: list[int] | None = None) -> dict:
    """Run both frozen numerical references; never label this as RTL evidence."""
    if type(seed) is not int or seed < 0:
        raise ValueError("Use a nonnegative integer seed")
    if type(prompt_index) is not int or prompt_index not in range(len(contract()["configuration"]["seq_lens"])):
        raise ValueError("Unknown teaching prompt index")
    cfg = contract()["configuration"]
    if tokens is not None and (not isinstance(tokens, list) or not 1 <= len(tokens) <= cfg["max_seq"]
                               or any(type(t) is not int or not 0 <= t < cfg["vocab"] for t in tokens)):
        raise ValueError("Tokens must be a nonempty in-vocabulary list within max_seq")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / "contract.json").write_text(json.dumps(contract(), indent=2, sort_keys=True) + "\n")
    (output / "request.json").write_text(json.dumps({"seed": seed, "prompt_index": prompt_index, "tokens": tokens}) + "\n")
    worker = Path(__file__).with_name("reference_worker.py")
    command = [sys.executable, "-B", str(worker), str(output), str(seed), str(prompt_index)]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    run = subprocess.run(command, text=True, capture_output=True, timeout=timeout_s, env=env)
    (output / "reference.log").write_text(run.stdout + run.stderr)
    if run.returncode:
        raise RuntimeError(f"Reference fixture failed; inspect {output / 'reference.log'}")
    receipt = json.loads((output / "receipt.json").read_text())
    receipt["command"] = command
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt
