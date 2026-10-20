"""Audited digital Liberty models for a retained mapped SKY130 HD netlist.

Power pins remain explicit ports. Their digital models assume nominal ideal
supplies; they do not simulate power loss, analog effects, delays, or UDP X
propagation. No functional-output blackbox is permitted in the used hierarchy.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re


_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*\Z")
_SCAN = re.compile(r'"(?:\\.|[^"\\])*"|(?P<kind>[A-Za-z_][A-Za-z0-9_]*)\s*\(')
_COMMENTS = re.compile(r'"(?:\\.|[^"\\])*"|/\*.*?\*/|//[^\n]*', re.S)
_PHYSICAL = re.compile(r"sky130_(?:fd|ef)_sc_hd__(?:fill|decap|tapvpwrvgnd)_[0-9]+\Z")
_DIODE = re.compile(r"sky130_fd_sc_hd__diode_[0-9]+\Z")
_CANONICAL_PG = ("VGND", "VNB", "VPB", "VPWR")
_TAP_LEF_SCHEMA = {
    "master": "sky130_fd_sc_hd__tapvpwrvgnd_1",
    "path": "/foss/pdks/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef",
    "sha256": "3a3ea4e9d0973402702764d897659e52fe3d413eb48c306cd811de40a75264fa",
    "macro_sha256": "750b228c4f51ebd37ad309b0f3397747136775c0f98bb25cef1c2bc8984a8313",
    "pin_uses": {"VGND": "GROUND", "VPWR": "POWER"},
}


def _physical_pg_pins(master, cells):
    """Use Liberty declarations first; the exact absent tap uses its pinned LEF.

    The LEF tap has two INOUT pins, including the nwell/pwell geometry. Its
    powered physical netlist therefore has no separate VPB/VNB connections.
    This is a master declaration, never a guess from an incomplete instance.
    Other four-rail physical models retain all four required connections.
    """
    actual = cells.get(master, {}).get("pg_pins", {})
    if actual:
        return set(actual)
    if master == _TAP_LEF_SCHEMA["master"]:
        return set(_TAP_LEF_SCHEMA["pin_uses"])
    return set(_CANONICAL_PG)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _end(text, start, opening, closing):
    depth = 0
    quoted = escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if not depth:
                return index
    raise ValueError("Unbalanced Liberty group")


def _groups(text):
    """Direct child groups; nested timing tables and quoted braces are skipped."""
    cursor = 0
    while match := _SCAN.search(text, cursor):
        if match.group("kind") is None:
            cursor = match.end()
            continue
        start = match.end() - 1
        end = _end(text, start, "(", ")")
        brace = end + 1
        while brace < len(text) and text[brace].isspace():
            brace += 1
        if brace < len(text) and text[brace] == "{":
            close = _end(text, brace, "{", "}")
            yield match.group("kind"), text[start + 1:end], text[brace + 1:close]
            cursor = close + 1
        else:
            cursor = end + 1


def _value(text, name):
    match = re.search(r"(?:^|[;\n])\s*" + re.escape(name) + r"\s*:\s*(\"(?:\\.|[^\"\\])*\"|[^;]+)\s*;", text)
    if match is None:
        return None
    value = match.group(1).strip()
    return json.loads(value) if value.startswith('"') else value


def _name(argument):
    argument = argument.strip()
    value = json.loads(argument) if argument.startswith('"') else argument
    if not isinstance(value, str) or not _NAME.fullmatch(value):
        raise ValueError(f"Unsupported Liberty identifier: {value!r}")
    return value


def inspect_liberty(path):
    """Extract actual digital/PG pins and sequential declarations, never timing."""
    text = _COMMENTS.sub(lambda m: m.group(0) if m.group(0).startswith('"') else " ", Path(path).read_text())
    libraries = [body for kind, _, body in _groups(text) if kind == "library"]
    if len(libraries) != 1:
        raise ValueError("Expected one Liberty library")
    cells = {}
    for kind, argument, body in _groups(libraries[0]):
        if kind != "cell":
            continue
        name = _name(argument)
        if name in cells:
            raise ValueError(f"Repeated Liberty cell {name}")
        pins, pg, sequential = {}, {}, []
        for child, args, contents in _groups(body):
            if child == "pin":
                pins[_name(args)] = {"direction": _value(contents, "direction"), "function": _value(contents, "function")}
            elif child == "pg_pin":
                pg[_name(args)] = {"pg_type": _value(contents, "pg_type"), "voltage_name": _value(contents, "voltage_name")}
            elif child in ("ff", "latch", "ff_bank", "latch_bank"):
                sequential.append({"kind": child, "state_arguments": args.strip(), **{key: _value(contents, key) for key in ("clocked_on", "next_state", "clear", "preset", "data_in", "enable")}})
        cells[name] = {"pins": pins, "pg_pins": pg, "sequential": sequential}
    if not cells:
        raise ValueError("Liberty has no cells")
    return cells


def _quote(path):
    text = str(Path(path).resolve())
    if "\n" in text or "\r" in text:
        raise ValueError("Newlines are not allowed in Yosys paths")
    return json.dumps(text)


def write_model_script(liberty_path, netlist_path, output_dir, *, top, physical_only_cells=None, power_ports=None):
    """Write a Yosys normalization plan. Run it, then validate_model_audit(plan).

    ``physical_only_cells`` maps recognized no-output masters to their allowed
    input-only digital pins: [] for fill/decap/tap and ['DIODE'] for diodes.
    With power_ports, validation traces exact rail aliases and writes a
    separate simulation_source_path with nominal supply ties and the original
    digital top interface. The function never runs tools or changes inputs.
    """
    if not _NAME.fullmatch(top):
        raise ValueError("Invalid top module")
    if power_ports is not None and (not isinstance(power_ports, dict) or not power_ports
            or any(not isinstance(pin, str) or not _NAME.fullmatch(pin) or type(value) is not int or value not in (0, 1) for pin, value in power_ports.items())
            or set(power_ports.values()) != {0, 1}):
        raise ValueError("Declare named one-bit nominal power and ground ports")
    liberty = Path(liberty_path).resolve(strict=True)
    netlist = Path(netlist_path).resolve(strict=True)
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=False)
    cells = inspect_liberty(liberty)
    physical = dict(physical_only_cells or {})
    all_pg = {pin for cell in cells.values() for pin in cell["pg_pins"]}
    for master, pins in physical.items():
        expected = [] if _PHYSICAL.fullmatch(master) else ["DIODE"] if _DIODE.fullmatch(master) else None
        if expected is None or pins != expected:
            raise ValueError(f"Unrecognized no-output physical cell/pins: {master}")
        if any(pin not in all_pg for pin in _CANONICAL_PG):
            raise ValueError("Physical-only cell supply pins lack Liberty PG provenance")
        if master in cells:
            actual = cells[master]["pins"]
            if set(actual) != set(pins) or any(actual[pin]["direction"] != "input" for pin in pins):
                raise ValueError(f"Physical override would discard a digital output: {master}")
    stub_lines = []
    for master, pins in sorted(physical.items()):
        power = sorted(_physical_pg_pins(master, cells))
        declarations = [f"input {pin}" for pin in pins] + [f"inout {pin}" for pin in power]
        stub_lines.append(f"module {master}({', '.join(declarations)}); endmodule")
    stubs = output / "physical-only.v"
    stubs.write_text("\n".join(stub_lines) + "\n")
    audit = output / "model-audit.json"
    normalized = output / "normalized.v"
    simulation = normalized if power_ports is None else output / "simulation.v"
    script = output / "models.ys"
    commands = [f"read_liberty -ignore_miss_func {_quote(liberty)}"]
    for master, data in sorted(cells.items()):
        for pin in sorted(data["pg_pins"]):
            # A skipped missing-function module remains absent; hierarchy-check
            # rejects it if instantiated. No replacement logic is invented.
            commands.append(f"add -inout {pin} 1 {master}")
    if physical:
        commands.append(f"read_verilog -noblackbox -overwrite {_quote(stubs)}")
    # Preserve the full hierarchy/rail audit before removing unused flattened
    # aliases. Public cell-internal names otherwise inflate the simulator's AST
    # without adding digital behavior; the final check still rejects bad logic.
    commands.extend([f"read_verilog -sv {_quote(netlist)}", f"hierarchy -check -top {top}", "proc", f"write_json {_quote(audit)}", "flatten", "opt_clean -purge", "check -assert", f"write_verilog -noattr {_quote(normalized)}"])
    script.write_text("\n".join(commands) + "\n")
    metadata_path = output / "model-metadata.json"
    pg_sources = {master: _TAP_LEF_SCHEMA for master in physical if master not in cells and master == _TAP_LEF_SCHEMA["master"]}
    metadata = {"schema": "nanochip-pinned-liberty-digital-models/v0", "top": top, "liberty_path": str(liberty), "liberty_sha256": _sha(liberty), "netlist_path": str(netlist), "netlist_sha256": _sha(netlist), "cells": cells, "physical_only_cells": physical, "physical_only_pg_sources": pg_sources, "script_path": str(script), "script_sha256": _sha(script), "audit_path": str(audit), "normalized_path": str(normalized), "physical_models_sha256": _sha(stubs), "audit_required": True, "power_ports": power_ports, "simulation_source_path": str(simulation),
                "assumptions": ["Ideal nominally powered supplies; explicit PG connections retained as ports, without analog power behavior", "Liberty Boolean/FF/latch functions; zero delays; no four-state UDP or power-loss correspondence claim", "Recognized fill/decap/tap/diode physical cells have no digital outputs", "Every used functional cell must survive hierarchy/check and independent audit; imported missing-function cells are never silently substituted"], "physical_only_missing_liberty": sorted(set(physical)-set(cells))}
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return {key: metadata[key] for key in ("script_path", "normalized_path", "simulation_source_path", "audit_path", "liberty_sha256", "netlist_sha256")} | {"model_metadata_path": str(metadata_path), "model_metadata_sha256": _sha(metadata_path)}


def _enabled(value):
    if isinstance(value, int):
        return value != 0
    value = str(value)
    return bool(value) and any(c != "0" for c in value)


def validate_model_audit(plan):
    """Reject used opaque logic, undeclared ports, and missing sequential models.

    Returns coverage information only after checking original input hashes and
    the retained hierarchy. The caller separately checks the tool return code.
    """
    if _sha(plan["model_metadata_path"]) != plan["model_metadata_sha256"]:
        raise ValueError("Model metadata changed")
    metadata = json.loads(Path(plan["model_metadata_path"]).read_text())
    for field in ("script_path", "normalized_path", "simulation_source_path", "audit_path", "liberty_sha256", "netlist_sha256"):
        if plan[field] != metadata[field]:
            raise ValueError(f"Model plan differs from audited metadata: {field}")
    for kind in ("liberty", "netlist", "script"):
        if _sha(metadata[f"{kind}_path"]) != metadata[f"{kind}_sha256"]:
            raise ValueError(f"Model {kind} input changed")
    modules = json.loads(Path(metadata["audit_path"]).read_text())["modules"]
    top = metadata["top"]
    if top not in modules:
        raise ValueError("Top missing from model audit")
    visited, counts, sequential = set(), Counter(), {}
    physical = metadata["physical_only_cells"]
    expected_sources = {master: _TAP_LEF_SCHEMA for master in physical if master not in metadata["cells"] and master == _TAP_LEF_SCHEMA["master"]}
    if metadata.get("physical_only_pg_sources", {}) != expected_sources:
        raise ValueError("Physical-only PG schema differs from its pinned master declaration")
    def visit(name):
        if name in visited:
            return
        visited.add(name)
        module = modules[name]
        opaque = any(_enabled(module.get("attributes", {}).get(key, 0)) for key in ("blackbox", "whitebox"))
        if name in physical:
            if any(port["direction"] == "output" for port in module["ports"].values()) or module.get("cells"):
                raise ValueError(f"Physical-only model has digital behavior: {name}")
            expected_pg = _physical_pg_pins(name, metadata["cells"])
            if set(module["ports"]) != set(physical[name]) | expected_pg:
                raise ValueError(f"Physical-only model pin mismatch: {name}")
        elif opaque:
            raise ValueError(f"Used functional cell is opaque: {name}")
        if name in metadata["cells"] and name not in physical:
            spec = metadata["cells"][name]
            if set(module["ports"]) != set(spec["pins"]) | set(spec["pg_pins"]):
                raise ValueError(f"Liberty digital/PG port mismatch: {name}")
            for pin, declaration in spec["pins"].items():
                if module["ports"][pin]["direction"] != declaration["direction"]:
                    raise ValueError(f"Liberty digital port direction mismatch: {name}/{pin}")
                if declaration["direction"] == "output" and not declaration["function"]:
                    raise ValueError(f"Output lacks Liberty function/state binding: {name}/{pin}")
            driven = {"0", "1"}
            for port in module["ports"].values():
                if port["direction"] in ("input", "inout"):
                    driven.update(port["bits"])
            for cell in module.get("cells", {}).values():
                for pin, direction in cell.get("port_directions", {}).items():
                    if direction in ("output", "inout"):
                        driven.update(cell["connections"][pin])
            for pin, port in module["ports"].items():
                if port["direction"] == "output" and any(bit not in driven for bit in port["bits"]):
                    raise ValueError(f"Undriven functional output: {name}/{pin}")
            for pin in spec["pg_pins"]:
                if module["ports"][pin]["direction"] != "inout":
                    raise ValueError(f"PG connection not retained: {name}/{pin}")
            types = [cell["type"] for cell in module.get("cells", {}).values()]
            for group in spec["sequential"]:
                kind = group["kind"]
                if kind not in ("ff", "latch"):
                    raise ValueError(f"Unsupported sequential bank: {name}")
                target = "DFF" if kind == "ff" else "LATCH"
                if not any(target in cell.upper() for cell in types):
                    raise ValueError(f"Missing {kind} functional implementation: {name}")
            if spec["sequential"]:
                sequential[name] = sorted(types)
        for cell in module.get("cells", {}).values():
            target = cell["type"]
            if target in modules:
                counts[target] += 1
                expected = modules[target]["ports"]
                if set(cell["connections"]) - set(expected):
                    raise ValueError(f"Unknown mapped-cell pin: {target}")
                # Every actual PG port must remain explicitly connected.
                pg = metadata["cells"].get(target, {}).get("pg_pins", {})
                if set(pg) - set(cell["connections"]):
                    raise ValueError(f"Unconnected PG port: {target}")
                visit(target)
            elif not target.startswith("$"):
                raise ValueError(f"Unmodeled functional instance: {target}")
    visit(top)
    power_audit = None
    if metadata["power_ports"] is not None:
        power_audit = _audit_power_rails(metadata, modules)
        _write_power_wrapper(metadata, modules[top]["ports"])
    result = {"status": "pass", "used_module_types": sorted(visited), "module_instance_counts": dict(sorted(counts.items())), "sequential_models": sequential, "power_connections_retained": True, "functional_blackboxes": 0, "physical_only_pg_sources": expected_sources, "assumptions": metadata["assumptions"], "audit_sha256": _sha(metadata["audit_path"]), "normalized_sha256": _sha(metadata["normalized_path"]), "power_rail_audit": power_audit, "simulation_source_path": metadata["simulation_source_path"], "simulation_source_sha256": _sha(metadata["simulation_source_path"]), "power_ports": metadata["power_ports"]}
    return result


def _audit_power_rails(metadata, modules):
    """Trace exact nominal rail aliases through every retained instance."""
    top = metadata["top"]
    ports = modules[top]["ports"]
    powers = metadata["power_ports"]
    inouts = {name for name, port in ports.items() if port["direction"] == "inout"}
    if inouts != set(powers):
        raise ValueError("Unknown, missing, or non-inout top PG ports")
    rails = {}
    for pin, value in powers.items():
        bits = ports[pin]["bits"]
        if len(bits) != 1 or type(bits[0]) is not int:
            raise ValueError(f"Top PG port is not a one-bit net: {pin}")
        bit = bits[0]
        if bit in rails and rails[bit] != value:
            raise ValueError("Nominal power and ground rails are shorted")
        rails[bit] = value
    kinds = {"primary_power": 1, "nwell": 1, "primary_ground": 0, "pwell": 0}
    canonical = {"VPWR": 1, "VPB": 1, "VGND": 0, "VNB": 0}
    checked = Counter()
    instances = 0
    def resolve(bit, values):
        if bit in ("0", "1"):
            return int(bit)
        return values.get(bit)
    def visit(name, values, stack):
        nonlocal instances
        if name in stack:
            raise ValueError("Recursive model hierarchy")
        for instance, cell in modules[name].get("cells", {}).items():
            target = cell["type"]
            if target not in modules:
                continue
            instances += 1
            spec = metadata["cells"].get(target)
            if spec is not None:
                pins = spec["pg_pins"]
                expected = {}
                for pin, pg in pins.items():
                    if pg["pg_type"] not in kinds:
                        raise ValueError(f"Unknown used Liberty PG type: {target}/{pin}")
                    expected[pin] = kinds[pg["pg_type"]]
            elif target in metadata["physical_only_cells"]:
                expected = {pin: canonical[pin] for pin in _physical_pg_pins(target, metadata["cells"])}
            else:
                expected = {}
            for pin, value in expected.items():
                bits = cell["connections"].get(pin, [])
                if len(bits) != 1 or resolve(bits[0], values) is None:
                    raise ValueError(f"Unknown or unconnected PG rail: {name}/{instance}/{pin}")
                if resolve(bits[0], values) != value:
                    raise ValueError(f"Crossed PG rail: {name}/{instance}/{pin}")
                checked["power" if value else "ground"] += 1
            child_values = {}
            for pin, port in modules[target]["ports"].items():
                connections = cell["connections"].get(pin, [])
                for bit, connected in zip(port["bits"], connections):
                    value = resolve(connected, values)
                    if value is not None:
                        if bit in child_values and child_values[bit] != value:
                            raise ValueError(f"Shorted hierarchical PG rail: {target}/{pin}")
                        child_values[bit] = value
            visit(target, child_values, stack + (name,))
    visit(top, rails, ())
    return {"status": "pass", "top_power_ports": powers, "checked_connections": dict(checked),
            "hierarchical_instances": instances, "method": "Exact preflatten JSON bit aliases; Liberty primary_power/nwell=1, primary_ground/pwell=0; exact missing-Liberty tap uses its pinned LEF POWER/GROUND declaration", "unknown_or_crossed_rails": 0}


def _write_power_wrapper(metadata, ports):
    """Preserve normalized source and add a separately hashed supply wrapper."""
    top = metadata["top"]
    powers = metadata["power_ports"]
    inner = top + "__nominal_powered"
    normalized = Path(metadata["normalized_path"]).read_text()
    if re.search(r"\bmodule\s+" + re.escape(inner) + r"\b", normalized):
        raise ValueError("Nominal-supply inner module name already exists")
    renamed, count = re.subn(r"(^\s*module\s+)" + re.escape(top) + r"(?=\s*\()", lambda match: match.group(1) + inner, normalized, flags=re.M)
    if count != 1:
        raise ValueError("Normalized top module cannot be uniquely renamed")
    digital = [(pin, port) for pin, port in ports.items() if pin not in powers]
    declarations = []
    connections = []
    for pin, port in digital:
        if not _NAME.fullmatch(pin) or port["direction"] not in ("input", "output"):
            raise ValueError("Unsupported digital wrapper port")
        width = len(port["bits"])
        offset = port.get("offset", 0)
        high = offset + width - 1
        span = "" if width == 1 and offset == 0 else (f"[{offset}:{high}] " if port.get("upto", 0) else f"[{high}:{offset}] ")
        signed = "signed " if port.get("signed", 0) else ""
        declarations.append(f"    {port['direction']} wire {signed}{span}{pin}")
        connections.append(f".{pin}({pin})")
    supply_nets = {pin: "__nanochip_nominal_" + pin for pin in powers}
    if set(supply_nets.values()) & set(ports):
        raise ValueError("Nominal-supply net name collides with a top port")
    connections.extend(f".{pin}({supply_nets[pin]})" for pin in sorted(powers))
    wrapper = "\n// Derived nominal-supply wrapper; original benchmark ports preserved.\n"
    wrapper += f"module {top}(\n" + ",\n".join(declarations) + "\n);\n"
    wrapper += "".join(f"  supply{value} {supply_nets[pin]};\n" for pin, value in sorted(powers.items()))
    wrapper += f"  {inner} powered_instance (" + ", ".join(connections) + ");\nendmodule\n"
    Path(metadata["simulation_source_path"]).write_text(renamed + wrapper)
