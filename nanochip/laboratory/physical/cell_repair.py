"""Conservative SKY130 equivalent-cell choices for bounded electrical repair.

This supplies choices, not acceptance. A larger numeric drive variant must
have the same full digital/PG schema at every supplied PVT and greater output
capacitance limits. Fresh physical timing/electrical checks remain binding.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from .cell_models import _COMMENTS, _groups, _name, _value, inspect_liberty


_DRIVE = re.compile(r"(sky130_fd_sc_hd__[A-Za-z0-9]+)_([0-9]+)\Z")
_DELAY = re.compile(r"sky130_fd_sc_hd__(?:clkdlybuf|dlygate|dlymetal)")


def _output_limits(path):
    text = _COMMENTS.sub(
        lambda match: match.group(0) if match.group(0).startswith('"') else " ",
        Path(path).read_text(),
    )
    libraries = [body for kind, _, body in _groups(text) if kind == "library"]
    if len(libraries) != 1:
        raise ValueError("Expected exactly one Liberty library")
    result = {}
    for kind, argument, body in _groups(libraries[0]):
        if kind != "cell":
            continue
        outputs = {}
        for child, args, contents in _groups(body):
            if child == "pin" and _value(contents, "direction") == "output":
                value = _value(contents, "max_capacitance")
                outputs[_name(args)] = float(value) if value is not None else None
        result[_name(argument)] = outputs
    return result


def equivalent_drive_table(liberty_paths):
    """Map supported masters to verified variants with at least double drive.

    Numeric suffixes are a declared SKY130 selection heuristic. They are never
    treated as a proof of timing. Sequential cells, delay cells, missing models,
    changed pin/function/PG schemas, and absent stronger variants are unsupported.
    """
    paths = [Path(path).resolve() for path in liberty_paths]
    if len(paths) != 3 or len(set(paths)) != 3:
        raise ValueError("Exactly three distinct PVT Liberty files are required")
    schemas = [inspect_liberty(path) for path in paths]
    limits = [_output_limits(path) for path in paths]
    names = set.intersection(*(set(schema) for schema in schemas))
    table = {}
    for master in sorted(names):
        match = _DRIVE.fullmatch(master)
        schema = schemas[0][master]
        if match is None or _DELAY.match(master) or schema["sequential"]:
            continue
        inputs = [
            pin for pin, info in schema["pins"].items() if info["direction"] == "input"
        ]
        outputs = [
            pin for pin, info in schema["pins"].items() if info["direction"] == "output"
        ]
        if (
            not inputs
            or len(outputs) != 1
            or any(
                info["direction"] not in {"input", "output"}
                for info in schema["pins"].values()
            )
        ):
            continue
        if any(schema != corner[master] for corner in schemas[1:]):
            continue
        output = outputs[0]
        if not schema["pins"][output]["function"]:
            continue
        minimum = max(1, int(match[2]) * 2)
        candidates = []
        for candidate in names:
            alternative = _DRIVE.fullmatch(candidate)
            if (
                alternative is None
                or alternative[1] != match[1]
                or int(alternative[2]) < minimum
            ):
                continue
            if any(corner[candidate] != schema for corner in schemas):
                continue
            old_caps = [corner[master].get(output) for corner in limits]
            new_caps = [corner[candidate].get(output) for corner in limits]
            if any(
                old is None or new is None or new <= old
                for old, new in zip(old_caps, new_caps)
            ):
                continue
            candidates.append((int(alternative[2]), candidate))
        if candidates:
            table[master] = min(candidates)[1]
    return {
        "schema": "nanochip-equivalent-drive-table/v1",
        "eligible": False,
        "selection": "Same family with at least doubled numeric drive label; identical digital/PG schema and increased output cap bound at all three PVTs",
        "limitations": "Candidate choices only; unsupported masters must fail explicitly; fresh full electrical/setup/hold checks determine acceptance",
        "libraries": [
            {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in paths
        ],
        "sources": {
            Path(__file__)
            .name: hashlib.sha256(Path(__file__).read_bytes())
            .hexdigest(),
            "cell_models.py": hashlib.sha256(
                Path(__file__).with_name("cell_models.py").read_bytes()
            ).hexdigest(),
        },
        "table": table,
    }


def write_drive_table(liberty_paths, output):
    """Retain a Tcl table and matching source/library identity metadata."""
    output = Path(output)
    plan = equivalent_drive_table(liberty_paths)
    rows = [f"    {{{old}}} {{{new}}}" for old, new in plan["table"].items()]
    output.write_text(
        "set ::nanochip_stronger_cells [dict create \\\n" + " \\\n".join(rows) + "]\n"
    )
    plan["tcl_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".json").write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n"
    )
    return plan
