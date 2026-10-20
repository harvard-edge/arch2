from __future__ import annotations

import importlib.util
import json
import shlex
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from urllib.parse import urlsplit

import pytest
import yaml

from cli.arch2 import ROOT


EXAMPLE_ROOT = ROOT / "card" / "examples"
PACKET_PATHS = sorted((EXAMPLE_ROOT / "evidence").glob("*.json"))
CARD_PATHS = [
    EXAMPLE_ROOT / "level-2-replayable.yaml",
    EXAMPLE_ROOT / "level-3-independent.yaml",
]


def _load_replay_module() -> ModuleType:
    module_path = EXAMPLE_ROOT / "replay.py"
    spec = importlib.util.spec_from_file_location("arch2_card_replay", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REPLAY = _load_replay_module()


def _load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_replay_source_uris_resolve_and_bind_card_records() -> None:
    for card_path in CARD_PATHS:
        document = yaml.safe_load(card_path.read_text(encoding="utf-8"))
        for record in document["design_loop_card"]["evidence"]["records"]:
            provenance = record["provenance"]
            parsed = urlsplit(provenance["source_uri"])
            assert not parsed.scheme
            assert not parsed.netloc
            packet_path = (card_path.parent / parsed.path).resolve()
            packet_path.relative_to(EXAMPLE_ROOT)
            assert packet_path.is_file()

            packet = _load_json(packet_path)
            assert packet["evidence_id"] == record["evidence_id"]
            assert packet["workload"]["workload_id"] == record["workload_id"]
            assert packet["parameter_hash"] == provenance["parameter_hash"]
            producer = packet["producer"]
            assert provenance["tool_version"] == (
                f"{producer['name']} {producer['version']}"
            )
            assert REPLAY.verify_packet(packet_path) == packet["results"]


@pytest.mark.parametrize("packet_path", PACKET_PATHS, ids=lambda path: path.stem)
def test_packet_integrity_binds_parameters_workload_and_implementation(
    packet_path: Path,
) -> None:
    packet = _load_json(packet_path)
    canonical_payload = REPLAY.canonical_json(packet["parameters"])
    assert packet["canonical_parameter_payload"] == canonical_payload
    assert packet["parameter_hash"] == REPLAY.sha256_bytes(
        canonical_payload.encode("utf-8")
    )

    workload = packet["workload"]
    workload_path = REPLAY.resolve_local_uri(packet_path, workload["source_uri"])
    assert workload_path.is_relative_to(EXAMPLE_ROOT)
    assert workload["sha256"] == REPLAY.sha256_file(workload_path)

    implementation = packet["producer"]["implementation"]
    implementation_path = REPLAY.resolve_local_uri(
        packet_path, implementation["source_uri"]
    )
    assert implementation_path == (EXAMPLE_ROOT / "replay.py").resolve()
    assert implementation["sha256"] == REPLAY.sha256_file(implementation_path)

    tampered_parameters = dict(packet["parameters"])
    tampered_parameters["array_rows"] += 1
    tampered_payload = REPLAY.canonical_json(tampered_parameters).encode("utf-8")
    assert REPLAY.sha256_bytes(tampered_payload) != packet["parameter_hash"]
    assert REPLAY.sha256_bytes(workload_path.read_bytes() + b"\n") != workload["sha256"]


@pytest.mark.parametrize("packet_path", PACKET_PATHS, ids=lambda path: path.stem)
def test_declared_replay_commands_are_reproducible(packet_path: Path) -> None:
    packet = _load_json(packet_path)
    commands = packet["commands"]
    working_directory = ROOT / commands["working_directory"]

    def run_declared(command_name: str) -> subprocess.CompletedProcess[str]:
        command = shlex.split(commands[command_name])
        assert command[0] == "python3"
        return subprocess.run(
            [sys.executable, *command[1:]],
            cwd=working_directory,
            check=False,
            capture_output=True,
            text=True,
        )

    first_render = run_declared("render")
    second_render = run_declared("render")
    assert first_render.returncode == 0, first_render.stderr
    assert second_render.returncode == 0, second_render.stderr
    assert first_render.stdout == second_render.stdout
    assert json.loads(first_render.stdout) == packet["results"]

    verification = run_declared("verify")
    assert verification.returncode == 0, verification.stderr
    assert verification.stdout == f"verified evidence/{packet_path.name}\n"


def test_replay_rejects_external_and_missing_uris() -> None:
    owner = EXAMPLE_ROOT / "evidence" / "packet.json"
    for uri in ("https://example.com/input.json", "../../outside.json", "missing.json"):
        with pytest.raises(REPLAY.ReplayError):
            REPLAY.resolve_local_uri(owner, uri)
