#!/usr/bin/env python3
"""Render and verify the self-contained design-loop-card replay packets."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shlex
import sys
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import unquote, urlsplit


EXAMPLE_ROOT = Path(__file__).resolve().parent
PACKET_VERSION = "1.0"
PRODUCER_NAME = "Architecture 2.0 illustrative array estimator"
PRODUCER_VERSION = "1.0.0"
PARAMETER_KEYS = {
    "array_columns",
    "array_rows",
    "candidate_id",
    "dataflow",
    "sram_capacity_kib",
}


class ReplayError(ValueError):
    """Raised when a replay packet is incomplete or fails integrity checks."""


def canonical_json(value: Any) -> str:
    """Return the exact UTF-8 JSON text used for parameter digests."""
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def sha256_bytes(payload: bytes) -> str:
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def resolve_local_uri(owner: Path, raw_uri: str) -> Path:
    """Resolve a packet URI while keeping it inside the example directory."""
    parsed = urlsplit(raw_uri)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        raise ReplayError(f"replay URI must be a plain relative path: {raw_uri!r}")
    target = (owner.parent / unquote(parsed.path)).resolve()
    try:
        target.relative_to(EXAMPLE_ROOT)
    except ValueError as exc:
        raise ReplayError(
            f"replay URI escapes the example directory: {raw_uri!r}"
        ) from exc
    if not target.is_file():
        raise ReplayError(f"replay URI does not resolve to a file: {raw_uri!r}")
    return target


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReplayError(f"{field} must be an object")
    return value


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ReplayError(f"{field} must be a positive integer")
    return value


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReplayError(f"cannot read JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReplayError(f"{path} must contain a JSON object")
    return value


def load_workload(packet_path: Path, packet: Mapping[str, Any]) -> dict[str, Any]:
    declaration = _require_mapping(packet.get("workload"), "workload")
    source_uri = declaration.get("source_uri")
    if not isinstance(source_uri, str) or not source_uri:
        raise ReplayError("workload.source_uri must be a nonempty relative path")
    workload_path = resolve_local_uri(packet_path, source_uri)
    expected_hash = declaration.get("sha256")
    observed_hash = sha256_file(workload_path)
    if expected_hash != observed_hash:
        raise ReplayError(
            f"workload hash mismatch: declared {expected_hash!r}, observed {observed_hash!r}"
        )

    workload = load_json(workload_path)
    if declaration.get("workload_id") != workload.get("workload_id"):
        raise ReplayError("packet workload_id does not match the resolved workload")
    layers = workload.get("layers")
    if not isinstance(layers, list) or not layers:
        raise ReplayError("workload.layers must be a nonempty array")

    layer_ids: set[str] = set()
    for index, layer_value in enumerate(layers):
        layer = _require_mapping(layer_value, f"workload.layers[{index}]")
        layer_id = layer.get("layer_id")
        if not isinstance(layer_id, str) or not layer_id:
            raise ReplayError(f"workload.layers[{index}].layer_id must be nonempty")
        if layer_id in layer_ids:
            raise ReplayError(f"duplicate workload layer_id: {layer_id}")
        layer_ids.add(layer_id)
        for dimension in ("m", "n", "k"):
            _positive_int(layer.get(dimension), f"workload.layers[{index}].{dimension}")
    return workload


def render_results(
    parameters: Mapping[str, Any], workload: Mapping[str, Any]
) -> dict[str, Any]:
    """Run the documented deterministic pipeline-fill estimator."""
    if set(parameters) != PARAMETER_KEYS:
        missing = sorted(PARAMETER_KEYS - set(parameters))
        unknown = sorted(set(parameters) - PARAMETER_KEYS)
        raise ReplayError(
            f"parameter keys differ; missing={missing}, unknown={unknown}"
        )

    rows = _positive_int(parameters.get("array_rows"), "parameters.array_rows")
    columns = _positive_int(parameters.get("array_columns"), "parameters.array_columns")
    _positive_int(parameters.get("sram_capacity_kib"), "parameters.sram_capacity_kib")
    if parameters.get("dataflow") != "output-stationary":
        raise ReplayError("parameters.dataflow must be 'output-stationary'")
    candidate_id = parameters.get("candidate_id")
    if not isinstance(candidate_id, str) or not candidate_id:
        raise ReplayError("parameters.candidate_id must be nonempty")

    layer_results: list[dict[str, Any]] = []
    total_cycles = 0
    total_macs = 0
    for layer_value in workload["layers"]:
        layer = _require_mapping(layer_value, "workload layer")
        m = _positive_int(layer.get("m"), "workload layer m")
        n = _positive_int(layer.get("n"), "workload layer n")
        k = _positive_int(layer.get("k"), "workload layer k")
        row_tiles = math.ceil(m / rows)
        column_tiles = math.ceil(n / columns)
        pipeline_cycles_per_tile = k + rows + columns - 2
        cycles = row_tiles * column_tiles * pipeline_cycles_per_tile
        useful_macs = m * n * k
        utilization = round(100 * useful_macs / (cycles * rows * columns), 6)
        total_cycles += cycles
        total_macs += useful_macs
        layer_results.append(
            {
                "column_tiles": column_tiles,
                "estimated_cycles": cycles,
                "layer_id": layer["layer_id"],
                "pe_utilization_percent": utilization,
                "row_tiles": row_tiles,
                "useful_macs": useful_macs,
            }
        )

    return {
        "aggregate": {
            "estimated_cycles": total_cycles,
            "pe_utilization_percent": round(
                100 * total_macs / (total_cycles * rows * columns), 6
            ),
            "useful_macs": total_macs,
        },
        "candidate_id": candidate_id,
        "layers": layer_results,
        "workload_id": workload["workload_id"],
    }


def expected_commands(packet_path: Path) -> dict[str, str]:
    try:
        relative_packet = packet_path.resolve().relative_to(EXAMPLE_ROOT).as_posix()
    except ValueError as exc:
        raise ReplayError(f"packet is outside {EXAMPLE_ROOT}: {packet_path}") from exc
    quoted_packet = shlex.quote(relative_packet)
    return {
        "render": f"python3 replay.py render {quoted_packet}",
        "verify": f"python3 replay.py verify {quoted_packet}",
        "working_directory": "card/examples",
    }


def replay_packet(
    packet_path: Path, *, verify_recorded_results: bool
) -> dict[str, Any]:
    packet_path = packet_path.resolve()
    packet = load_json(packet_path)
    if packet.get("packet_version") != PACKET_VERSION:
        raise ReplayError(
            f"unsupported packet_version: {packet.get('packet_version')!r}"
        )

    producer = _require_mapping(packet.get("producer"), "producer")
    if (
        producer.get("name") != PRODUCER_NAME
        or producer.get("version") != PRODUCER_VERSION
    ):
        raise ReplayError("packet producer does not match this replay implementation")
    implementation = _require_mapping(
        producer.get("implementation"), "producer.implementation"
    )
    implementation_uri = implementation.get("source_uri")
    if not isinstance(implementation_uri, str) or not implementation_uri:
        raise ReplayError("producer.implementation.source_uri must be nonempty")
    implementation_path = resolve_local_uri(packet_path, implementation_uri)
    if implementation_path != Path(__file__).resolve():
        raise ReplayError("packet resolves to a different replay implementation")
    implementation_hash = sha256_file(implementation_path)
    if implementation.get("sha256") != implementation_hash:
        raise ReplayError(
            "implementation hash mismatch: "
            f"declared {implementation.get('sha256')!r}, observed {implementation_hash!r}"
        )

    parameters = _require_mapping(packet.get("parameters"), "parameters")
    canonical_payload = canonical_json(parameters)
    if packet.get("canonical_parameter_payload") != canonical_payload:
        raise ReplayError("canonical_parameter_payload does not match parameters")
    observed_parameter_hash = sha256_bytes(canonical_payload.encode("utf-8"))
    if packet.get("parameter_hash") != observed_parameter_hash:
        raise ReplayError(
            "parameter hash mismatch: "
            f"declared {packet.get('parameter_hash')!r}, "
            f"observed {observed_parameter_hash!r}"
        )

    workload = load_workload(packet_path, packet)
    if packet.get("candidate_id") != parameters.get("candidate_id"):
        raise ReplayError("packet candidate_id does not match parameters")
    if packet.get("workload", {}).get("workload_id") != workload.get("workload_id"):
        raise ReplayError("packet workload_id does not match workload input")
    if packet.get("commands") != expected_commands(packet_path):
        raise ReplayError("packet commands do not match its resolved path")

    results = render_results(parameters, workload)
    if verify_recorded_results and packet.get("results") != results:
        raise ReplayError("recorded results do not match deterministic replay")
    return results


def render_packet(packet_path: Path) -> dict[str, Any]:
    return replay_packet(packet_path, verify_recorded_results=False)


def verify_packet(packet_path: Path) -> dict[str, Any]:
    return replay_packet(packet_path, verify_recorded_results=True)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("render", "verify"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("packet", type=Path)
    subparsers.add_parser("verify-all")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.command == "verify-all":
            packets = sorted((EXAMPLE_ROOT / "evidence").glob("*.json"))
            if not packets:
                raise ReplayError("no replay packets found")
            for packet in packets:
                verify_packet(packet)
                print(f"verified {packet.relative_to(EXAMPLE_ROOT)}")
            return 0

        packet_path = args.packet
        if not packet_path.is_absolute():
            packet_path = Path.cwd() / packet_path
        if args.command == "render":
            results = render_packet(packet_path)
            print(json.dumps(results, indent=2, sort_keys=True))
        else:
            verify_packet(packet_path)
            print(f"verified {packet_path.resolve().relative_to(EXAMPLE_ROOT)}")
        return 0
    except (ReplayError, OSError) as exc:
        print(f"replay error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
