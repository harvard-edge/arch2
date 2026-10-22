"""Bounded DEF connectivity check for the Nanochip signal-repair step.

Supports the emitted, unrouted COMPONENTS/PINS/NETS grammar, not general DEF.
Only declared new identity buffers may be contracted. An explicit CTS mode
allows new clock buffers and net names while preserving original clock roots.
SPECIALNETS, power
connections, placement, timing, analog behavior, and sequential equivalence
belong to separate checks. This is not final mapped-workload correspondence.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

from .cell_models import inspect_liberty


class SignalGraphError(ValueError):
    """The supported input contract or connectivity invariant failed."""


def _require(condition, message):
    if not condition:
        raise SignalGraphError(message)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _section(text, name):
    starts = list(re.finditer(rf"^{name}\s+(\d+)\s*;", text, re.M))
    ends = list(re.finditer(rf"^END {name}\s*$", text, re.M))
    _require(len(starts) == len(ends) == 1, f"Expected one {name} section")
    start, end = starts[0], ends[0]
    _require(end.start() > start.end(), f"Invalid {name} section order")
    body = text[start.end() : end.start()]
    rows = re.findall(r"^\s*-\s+(\S+)\s+(.*?);", body, re.M | re.S)
    remainder = re.sub(r"^\s*-\s+\S+\s+.*?;", "", body, flags=re.M | re.S)
    _require(not remainder.strip(), f"Unsupported {name} statement")
    _require(len(rows) == int(start.group(1)), f"Declared {name} count mismatch")
    _require(len({name for name, _ in rows}) == len(rows), f"Duplicate {name} name")
    return rows


def _one(pattern, body, label):
    values = re.findall(pattern, body)
    _require(len(values) == 1, f"Expected one {label}")
    return values[0]


@dataclass
class _Design:
    components: dict
    ports: dict
    nets: dict
    pin_net: dict
    nondefault_rules: dict
    clock_ndr: dict


def _read_def(path):
    text = Path(path).read_text()
    _require(
        not re.search(r"^\s*#", text, re.M),
        "Comments are outside supported DEF grammar",
    )
    nondefault_rules = {}
    if re.search(r"^(?:NONDEFAULTRULES\s|END NONDEFAULTRULES\s*$)", text, re.M):
        for name, body in _section(text, "NONDEFAULTRULES"):
            layers = re.findall(
                r"\+\s+LAYER\s+(\S+)\s+WIDTH\s+(\d+)\s+SPACING\s+(\d+)", body
            )
            remaining = re.sub(
                r"\+\s+LAYER\s+\S+\s+WIDTH\s+\d+\s+SPACING\s+\d+", "", body
            )
            _require(
                bool(layers) and not remaining.strip(),
                f"Unsupported NONDEFAULTRULE declaration: {name}",
            )
            _require(
                len({layer for layer, _, _ in layers}) == len(layers),
                f"Duplicate NONDEFAULTRULE layer: {name}",
            )
            _require(
                all(
                    int(width) > 0 and int(spacing) > 0 for _, width, spacing in layers
                ),
                f"NONDEFAULTRULE width/spacing must be positive: {name}",
            )
            nondefault_rules[name] = {
                layer: {"width_dbu": int(width), "spacing_dbu": int(spacing)}
                for layer, width, spacing in layers
            }
    components = {}
    for name, body in _section(text, "COMPONENTS"):
        _require(bool(body.split()), f"Missing component master: {name}")
        components[name] = body.split()[0]
    ports = {}
    for name, body in _section(text, "PINS"):
        direction = _one(r"\+\s+DIRECTION\s+(\S+)", body, "port direction")
        use = _one(r"\+\s+USE\s+(\S+)", body, "port use")
        _require(
            use in {"SIGNAL", "CLOCK", "POWER", "GROUND"},
            f"Unsupported port use: {name}/{use}",
        )
        permitted = {"INPUT", "OUTPUT"} if use in {"SIGNAL", "CLOCK"} else {"INOUT"}
        _require(
            direction in permitted, f"Unsupported port direction: {name}/{direction}"
        )
        ports[name] = {
            "direction": direction,
            "use": use,
            "net": _one(r"\+\s+NET\s+(\S+)", body, "port net"),
        }
    nets, pin_net, clock_ndr = {}, {}, {}
    for name, body in _section(text, "NETS"):
        pins = re.findall(r"\(\s+(\S+)\s+(\S+)\s+\)", body)
        tail = re.sub(r"\(\s+\S+\s+\S+\s+\)", "", body).strip()
        attributes = re.fullmatch(
            r"\+\s+USE\s+(SIGNAL|CLOCK)(?:\s+\+\s+NONDEFAULTRULE\s+(\S+))?", tail
        )
        _require(
            attributes is not None,
            f"Unsupported NETS attributes or routed grammar: {name}",
        )
        typ, ndr = attributes.groups()
        if ndr is not None:
            _require(
                typ == "CLOCK",
                f"Only CLOCK NONDEFAULTRULE references are supported: {name}",
            )
            _require(
                ndr in nondefault_rules,
                f"Undeclared CLOCK NONDEFAULTRULE: {name}/{ndr}",
            )
            clock_ndr[name] = ndr
        _require(bool(pins), f"Net has no endpoints: {name}")
        for pin in pins:
            _require(pin not in pin_net, f"Repeated endpoint: {pin}")
            _require(
                pin[0] in components or (pin[0] == "PIN" and pin[1] in ports),
                f"Unknown endpoint: {pin}",
            )
            pin_net[pin] = name
        nets[name] = (typ, pins)
    for name, port in ports.items():
        if port["use"] in {"POWER", "GROUND"}:
            _require(("PIN", name) not in pin_net, f"PG port in regular NETS: {name}")
        else:
            _require(
                pin_net.get(("PIN", name)) == port["net"],
                f"Port NET binding mismatch: {name}",
            )
    return _Design(components, ports, nets, pin_net, nondefault_rules, clock_ndr)


def _read_lef(path):
    """Read macro pin direction/use declarations; geometry is out of scope."""
    macros, classes, macro, pin = {}, {}, None, None
    for line in Path(path).read_text().splitlines():
        tokens = line.strip().split()
        if not tokens:
            continue
        if tokens[0] == "MACRO":
            _require(
                macro is None and len(tokens) == 2, "Unsupported LEF macro nesting"
            )
            macro = tokens[1]
            _require(macro not in macros, f"Duplicate LEF macro: {macro}")
            macros[macro] = {}
        elif tokens[0] == "CLASS" and macro is not None and pin is None:
            _require(
                macro not in classes and tokens[-1] == ";",
                f"Unsupported LEF class: {macro}",
            )
            classes[macro] = " ".join(tokens[1:-1])
        elif tokens[0] == "PIN" and macro is not None:
            _require(pin is None and len(tokens) == 2, "Unsupported LEF pin nesting")
            pin = tokens[1]
            _require(pin not in macros[macro], f"Duplicate LEF pin: {macro}/{pin}")
            macros[macro][pin] = {}
        elif tokens[0] in {"DIRECTION", "USE"} and pin is not None:
            key = tokens[0].lower()
            _require(
                key not in macros[macro][pin],
                f"Duplicate LEF pin attribute: {macro}/{pin}/{key}",
            )
            macros[macro][pin][key] = tokens[1]
        elif tokens[0] == "END" and len(tokens) == 2:
            if tokens[1] == pin:
                pin = None
            elif tokens[1] == macro:
                _require(pin is None, "Unclosed LEF pin")
                macro = None
    _require(
        macro is None and pin is None and bool(macros), "Incomplete LEF declarations"
    )
    return macros, classes


def _signature(master, cells, lef):
    _require(master in cells and master in lef, f"Missing Liberty/LEF master: {master}")
    cell = cells[master]
    _require(
        not cell["sequential"],
        f"Sequential master replacement is unsupported: {master}",
    )
    pins = {}
    for name, declaration in cell["pins"].items():
        direction = declaration["direction"]
        _require(
            direction in {"input", "output"},
            f"Unsupported Liberty interface: {master}/{name}",
        )
        _require(
            lef[master].get(name, {}).get("direction", "").lower() == direction,
            f"Liberty/LEF pin direction mismatch: {master}/{name}",
        )
        function = declaration["function"]
        if direction == "output":
            _require(
                isinstance(function, str) and bool(function.strip()),
                f"Missing Boolean function: {master}/{name}",
            )
        pins[name] = (
            direction,
            re.sub(r"\s+", "", function) if function is not None else None,
        )
    logical_lef = {
        name
        for name, value in lef[master].items()
        if value.get("use") not in {"POWER", "GROUND"}
    }
    _require(
        logical_lef == set(pins),
        f"Liberty/LEF logical pin interface mismatch: {master}",
    )
    return {"pins": pins, "pg_pins": cell["pg_pins"]}


def _identity_buffer(master, cells, lef):
    signature = _signature(master, cells, lef)
    inputs = [
        name
        for name, (direction, _) in signature["pins"].items()
        if direction == "input"
    ]
    outputs = [
        name
        for name, (direction, _) in signature["pins"].items()
        if direction == "output"
    ]
    _require(
        len(inputs) == len(outputs) == 1,
        f"Added master is not a simple buffer: {master}",
    )
    function = signature["pins"][outputs[0]][1]
    _require(
        re.fullmatch(r"\(*" + re.escape(inputs[0]) + r"\)*", function) is not None
        and function.count("(") == function.count(")"),
        f"Added master is not an identity buffer: {master}",
    )
    return inputs[0], outputs[0]


def _physical_diode(master, cells, lef, classes):
    _require(
        master == "sky130_fd_sc_hd__diode_2",
        f"Unrecognized added physical master: {master}",
    )
    _require(
        classes.get(master) == "CORE ANTENNACELL",
        f"Added physical master is not a LEF antenna cell: {master}",
    )
    signature = _signature(master, cells, lef)
    _require(
        signature["pins"] == {"DIODE": ("input", None)},
        f"Added physical master must be input-only without Boolean outputs: {master}",
    )
    _require(
        set(signature["pg_pins"]) == {"VPWR", "VGND", "VPB", "VNB"},
        f"Added diode has an unexpected declared PG interface: {master}",
    )
    return signature


def _clock_dummy_interface(master, cells, lef):
    signature = _signature(master, cells, lef)
    inputs = [
        p for p, (direction, _) in signature["pins"].items() if direction == "input"
    ]
    outputs = [
        p for p, (direction, _) in signature["pins"].items() if direction == "output"
    ]
    _require(
        len(inputs) == len(outputs) == 1,
        f"CLOCK dummy must have one input and one output: {master}",
    )
    function = signature["pins"][outputs[0]][1]
    _require(
        signature["pins"][inputs[0]][1] is None
        and re.fullmatch(r"\(*!?" + re.escape(inputs[0]) + r"\)*", function) is not None
        and function.count("(") == function.count(")"),
        f"CLOCK dummy must be a simple buffer or inverter: {master}",
    )
    return inputs[0], outputs[0], signature


def _special_endpoints(path):
    """Conservatively scan endpoint pairs, including wildcard pins, in SPECIALNETS.

    This validates section counts/names but does not interpret route geometry.
    A coordinate pair matching a logical endpoint also fails closed.
    """
    text = Path(path).read_text()
    if not re.search(r"^(?:SPECIALNETS\s|END SPECIALNETS\s*$)", text, re.M):
        return set()
    return {
        tuple(pin)
        for _, body in _section(text, "SPECIALNETS")
        for pin in re.findall(r"\(\s*(\S+)\s+(\S+)\s*\)", body)
    }


def check_signal_reachability(
    before_def,
    after_def,
    *,
    lef_path,
    liberty_path,
    added_buffer_masters=("sky130_fd_sc_hd__buf_4",),
    allowed_master_changes=None,
    added_buffer_overrides=None,
    added_physical_masters=(),
    allowed_clock_diode_loads=None,
    clock_tree_buffer_masters=(),
    clock_dummy_loads=None,
    output=None,
):
    """Bind every original SIGNAL load to its original driver after buffer insertion.

    Master-change exceptions bind exact instance/before/after names and identical
    combinational logical declarations. They are not arbitrary Boolean rewrites.
    Added-buffer overrides bind exact newly created instance names. Every supplied
    instance exception must be consumed. Exact optional antenna-diode masters
    may add input-only physical loads; they may never drive functional logic.
    CLOCK additions require an exact net-to-new-diode-endpoint allowance, while
    every original clock net and endpoint remains unchanged.
    Alternatively, explicit clock_tree_buffer_masters permits new verified
    noninverting buffers and renamed CLOCK nets. Each original CLOCK load must
    retain its exact original source through those new buffers. Original clock
    cells cannot be removed; resizing still needs an exact master exception.
    This mode does not admit new CLOCK diode loads or clock inverters.
    Native dummy loads need clock_dummy_loads entries with exact instance,
    master, input_pin and CLOCK net. Only single-input/output combinational
    buffers/inverters qualify, and every logical output must be absent from
    both NETS and SPECIALNETS. Dummies are loads, never contracted transport.
    Output hashes bind inputs and this checker.
    """
    before, after = _read_def(before_def), _read_def(after_def)
    lef, classes = _read_lef(lef_path)
    cells = inspect_liberty(liberty_path)
    allowed = dict(allowed_master_changes or {})
    overrides = dict(added_buffer_overrides or {})
    _require(set(before.ports) == set(after.ports), "Original port names changed")
    _require(
        all(
            (before.ports[p]["direction"], before.ports[p]["use"])
            == (after.ports[p]["direction"], after.ports[p]["use"])
            for p in before.ports
        ),
        "Original port direction/use changed",
    )
    _require(
        set(before.components) <= set(after.components), "Original instance removed"
    )
    changes = {}
    for name, master in before.components.items():
        actual = after.components[name]
        if actual != master:
            _require(
                allowed.get(name) == {"before": master, "after": actual},
                f"Unlisted original master change: {name}",
            )
            _require(
                _signature(master, cells, lef) == _signature(actual, cells, lef),
                f"Original master functions/interfaces differ: {name}",
            )
            changes[name] = {"before": master, "after": actual}
    _require(
        set(changes) == set(allowed), "Unused or mismatched original-master exception"
    )
    added = {
        name: master
        for name, master in after.components.items()
        if name not in before.components
    }
    _require(set(overrides) <= set(added), "Unused added-buffer override")
    buffers, physical, clock_buffers = {}, {}, {}
    defaults = set(added_buffer_masters)
    physical_masters = set(added_physical_masters)
    clock_defaults = set(clock_tree_buffer_masters)
    dummy_allowances = dict(clock_dummy_loads or {})
    _require(
        not dummy_allowances or bool(clock_defaults),
        "CLOCK dummy allowances require explicit CTS mode",
    )
    _require(
        not (defaults | clock_defaults).intersection(physical_masters),
        "Physical and buffer master allowances overlap",
    )
    _require(
        not clock_defaults or not allowed_clock_diode_loads,
        "CTS rebuild mode cannot also admit CLOCK diode additions",
    )
    clock_interfaces = {
        master: _identity_buffer(master, cells, lef) for master in clock_defaults
    }
    _require(
        set(dummy_allowances) <= set(added), "Unused CLOCK dummy instance allowance"
    )
    _require(
        not set(dummy_allowances).intersection(overrides),
        "CLOCK dummy cannot use a SIGNAL buffer override",
    )
    special_pins = _special_endpoints(after_def) if dummy_allowances else set()
    dummy_schemas = {}
    for name, allowance in dummy_allowances.items():
        _require(
            isinstance(name, str)
            and isinstance(allowance, dict)
            and set(allowance) == {"master", "input_pin", "net"}
            and all(
                isinstance(value, str) and bool(value) for value in allowance.values()
            ),
            f"Invalid exact CLOCK dummy allowance: {name}",
        )
        master = added[name]
        _require(master == allowance["master"], f"CLOCK dummy master mismatch: {name}")
        input_pin, output_pin, schema = _clock_dummy_interface(master, cells, lef)
        _require(
            input_pin == allowance["input_pin"], f"CLOCK dummy input mismatch: {name}"
        )
        net = after.pin_net.get((name, input_pin))
        _require(
            net == allowance["net"]
            and net in after.nets
            and after.nets[net][0] == "CLOCK",
            f"CLOCK dummy input must connect to its declared CLOCK net: {name}",
        )
        _require(
            (name, output_pin) not in after.pin_net,
            f"CLOCK dummy output is connected: {name}",
        )
        _require(
            all(
                (name, pin) not in special_pins and ("*", pin) not in special_pins
                for pin in schema["pins"]
            ),
            f"CLOCK dummy logical pin in SPECIALNETS: {name}",
        )
        dummy_schemas[master] = schema
    physical_schemas = {
        master: _physical_diode(master, cells, lef, classes)
        for master in physical_masters
    }
    for name, master in added.items():
        if name in dummy_allowances:
            continue
        if master in physical_masters and name not in overrides:
            physical[name] = master
            continue
        if master in clock_defaults:
            interface = clock_interfaces[master]
            endpoints = [(name, pin) for pin in interface]
            kinds = [
                after.nets[after.pin_net[pin]][0] if pin in after.pin_net else None
                for pin in endpoints
            ]
            if kinds == ["CLOCK", "CLOCK"]:
                _require(
                    name not in overrides,
                    f"CLOCK buffer cannot use a SIGNAL override: {name}",
                )
                clock_buffers[name] = interface
                continue
            _require(
                kinds == ["SIGNAL", "SIGNAL"],
                f"Added CLOCK buffer pins must be connected within one net type: {name}",
            )
        if name in overrides:
            _require(
                master == overrides[name], f"Added-buffer override mismatch: {name}"
            )
        else:
            _require(master in defaults, f"Unlisted added master: {name}/{master}")
        buffers[name] = _identity_buffer(master, cells, lef)
    before_clocks = {
        n: sorted(pins) for n, (typ, pins) in before.nets.items() if typ == "CLOCK"
    }
    after_clocks = {
        n: sorted(pins) for n, (typ, pins) in after.nets.items() if typ == "CLOCK"
    }
    clock_allowances = {}
    for net, entries in dict(allowed_clock_diode_loads or {}).items():
        _require(
            isinstance(net, str) and net in before_clocks,
            f"CLOCK allowance is not an existing clock net: {net}",
        )
        _require(
            isinstance(entries, (list, tuple)) and bool(entries),
            f"CLOCK diode allowance needs explicit endpoints: {net}",
        )
        _require(
            all(isinstance(entry, str) and "/" in entry for entry in entries),
            f"Invalid CLOCK diode endpoint: {net}",
        )
        pins = [tuple(entry.rsplit("/", 1)) for entry in entries]
        _require(len(set(pins)) == len(pins), f"Duplicate CLOCK diode allowance: {net}")
        for instance, pin in pins:
            _require(
                instance in physical and pin == "DIODE",
                f"CLOCK allowance is not a newly added verified diode input: {instance}/{pin}",
            )
        clock_allowances[net] = set(pins)
    clock_additions = {}
    if not clock_defaults:
        _require(
            set(before_clocks) == set(after_clocks),
            "CLOCK connectivity changed: net names/types differ",
        )
        for net, old_pins in before_clocks.items():
            old_pins, new_pins = set(old_pins), set(after_clocks[net])
            _require(
                old_pins <= new_pins,
                f"CLOCK connectivity changed: original endpoint removed or moved: {net}",
            )
            extra = new_pins - old_pins
            if extra:
                clock_additions[net] = extra
        _require(
            clock_additions == clock_allowances,
            "CLOCK connectivity changed: added diode map does not match exact allowance",
        )
    surviving_original_pins = {pin for pin in after.pin_net if pin[0] not in added}
    _require(
        set(before.pin_net) == surviving_original_pins,
        "Original signal/clock endpoint lost or added",
    )

    def direction(design, pin):
        if pin[0] == "PIN":
            return "OUTPUT" if design.ports[pin[1]]["direction"] == "INPUT" else "INPUT"
        master = design.components[pin[0]]
        value = lef.get(master, {}).get(pin[1], {})
        _require(
            value.get("use") not in {"POWER", "GROUND"},
            f"PG endpoint in regular NETS: {pin}",
        )
        result = value.get("direction")
        _require(
            result in {"INPUT", "OUTPUT"},
            f"Unsupported or unknown signal pin direction: {pin}",
        )
        return result

    for design in (before, after):
        for _, pins in design.nets.values():
            for pin in pins:
                direction(design, pin)

    clock_loads_checked, clock_sources = 0, set()
    if clock_defaults:
        original_clock_pins = {pin for pins in before_clocks.values() for pin in pins}
        final_clock_pins = {
            pin
            for pins in after_clocks.values()
            for pin in pins
            if pin[0] not in clock_buffers and pin[0] not in dummy_allowances
        }
        _require(
            original_clock_pins == final_clock_pins,
            "Original CLOCK endpoint lost, added, or crossed net type",
        )

        def clock_drivers(design, clocks):
            result = {}
            for net, pins in clocks.items():
                outputs = [pin for pin in pins if direction(design, pin) == "OUTPUT"]
                _require(
                    len(outputs) == 1,
                    f"CLOCK net needs one driver: {net} ({len(outputs)})",
                )
                result[net] = outputs[0]
            return result

        old_clock_drivers = clock_drivers(before, before_clocks)
        new_clock_drivers = clock_drivers(after, after_clocks)
        clock_roots, clock_paths = {}, {}

        def clock_root(net):
            chain, visiting, current = [], set(), net
            while current not in clock_roots:
                _require(
                    current not in visiting, f"Added CLOCK-buffer cycle: {current}"
                )
                visiting.add(current)
                _require(
                    current in new_clock_drivers,
                    f"CLOCK path crossed a non-CLOCK net: {current}",
                )
                driver = new_clock_drivers[current]
                if driver[0] not in clock_buffers:
                    clock_roots[current], clock_paths[current] = driver, frozenset()
                    break
                name = driver[0]
                input_pin, output_pin = clock_buffers[name]
                _require(
                    driver[1] == output_pin,
                    f"Invalid added CLOCK buffer output: {driver}",
                )
                chain.append((current, name))
                current = after.pin_net[(name, input_pin)]
            root, traversed = clock_roots[current], clock_paths[current]
            for item, name in reversed(chain):
                traversed = traversed | {name}
                clock_roots[item], clock_paths[item] = root, traversed
            return clock_roots[net]

        used_clock_buffers = set()
        for net, pins in before_clocks.items():
            clock_sources.add(old_clock_drivers[net])
            for pin in pins:
                if direction(before, pin) == "INPUT":
                    final_net = after.pin_net[pin]
                    _require(
                        clock_root(final_net) == old_clock_drivers[net],
                        f"Original CLOCK driver-to-load reachability changed: {pin}",
                    )
                    used_clock_buffers.update(clock_paths[final_net])
                    clock_loads_checked += 1
        for net in new_clock_drivers:
            clock_root(net)
        _require(
            used_clock_buffers == set(clock_buffers),
            "Added CLOCK buffer reaches no original CLOCK load",
        )

    def drivers(design):
        result = {}
        for net, (typ, pins) in design.nets.items():
            if typ != "SIGNAL":
                continue
            outputs = [pin for pin in pins if direction(design, pin) == "OUTPUT"]
            _require(
                len(outputs) == 1,
                f"SIGNAL net needs one driver: {net} ({len(outputs)})",
            )
            result[net] = outputs[0]
        return result

    before_drivers, after_drivers = drivers(before), drivers(after)
    roots, paths = {}, {}

    def original_driver(net):
        if net in roots:
            return roots[net]
        chain, visiting = [], set()
        current = net
        while current not in roots:
            _require(current not in visiting, f"Added-buffer cycle: {current}")
            visiting.add(current)
            _require(
                current in after_drivers,
                f"Signal path crossed a non-SIGNAL net: {current}",
            )
            driver = after_drivers[current]
            if driver[0] not in buffers:
                roots[current], paths[current] = driver, frozenset()
                break
            name = driver[0]
            input_pin, output_pin = buffers[name]
            _require(driver[1] == output_pin, f"Invalid added buffer output: {driver}")
            _require(
                (name, input_pin) in after.pin_net,
                f"Added buffer input disconnected: {name}",
            )
            chain.append((current, name))
            current = after.pin_net[(name, input_pin)]
        root, traversed = roots[current], paths[current]
        for item, name in reversed(chain):
            traversed = traversed | {name}
            roots[item], paths[item] = root, traversed
        return roots[net]

    loads_checked, used_buffers = 0, set()
    for net, (typ, pins) in before.nets.items():
        if typ != "SIGNAL":
            continue
        for pin in pins:
            if direction(before, pin) != "INPUT":
                continue
            after_net = after.pin_net[pin]
            _require(
                original_driver(after_net) == before_drivers[net],
                f"Original driver-to-load reachability changed: {pin}",
            )
            used_buffers.update(paths[after_net])
            loads_checked += 1
    for net in after_drivers:
        original_driver(net)
    for name, (input_pin, output_pin) in buffers.items():
        _require(
            (name, output_pin) in after.pin_net,
            f"Added buffer output disconnected: {name}",
        )
        _require(
            name in used_buffers,
            f"Added buffer reaches no original SIGNAL load: {name}",
        )
    for name, master in physical.items():
        for pin in physical_schemas[master]["pins"]:
            endpoint = (name, pin)
            _require(
                endpoint in after.pin_net,
                f"Added diode input disconnected: {name}/{pin}",
            )
            net = after.pin_net[endpoint]
            _require(
                after.nets[net][0] == "SIGNAL"
                or endpoint in clock_allowances.get(net, set()),
                f"Added diode input is not on SIGNAL or an explicitly allowed CLOCK net: {name}/{pin}",
            )
    inputs = {
        "before_def": before_def,
        "after_def": after_def,
        "lef": lef_path,
        "liberty": liberty_path,
        "checker": __file__,
        "liberty_parser": Path(__file__).with_name("cell_models.py"),
    }
    receipt = {
        "schema": "nanochip-signal-reachability/v1",
        "status": "pass",
        "eligible": False,
        "scope": (
            "Original SIGNAL driver/load connectivity; original CLOCK sources/loads through declared new identity buffers, permitting net renaming and exact native dummy loads"
            if clock_defaults
            else "Original SIGNAL driver/load connectivity through declared identity buffers; original CLOCK nets/endpoints preserved, optional exact input-only antenna loads"
        ),
        "limitations": [
            "Bounded emitted unrouted DEF grammar, not a general DEF parser",
            "SPECIALNETS and PG connections require the separate PG audit",
            "No timing, analog, sequential-equivalence, or final mapped-workload claim",
        ],
        "original_signal_nets": len(before_drivers),
        "original_signal_loads_checked": loads_checked,
        "all_original_pins_preserved": len(before.pin_net),
        "added_noninverting_buffers": len(buffers),
        "original_master_changes": changes,
        "added_buffer_overrides": overrides,
        "added_buffer_masters": sorted(defaults),
        "clock_connectivity_identical": before_clocks == after_clocks,
        "original_clock_connectivity_preserved": True,
        "clock_check_mode": "new_noninverting_buffer_reachability"
        if clock_defaults
        else "exact_original_nets",
        "clock_tree_buffer_masters": sorted(clock_defaults),
        "added_clock_buffers": len(clock_buffers),
        "added_clock_buffer_counts": {
            master: sum(after.components[name] == master for name in clock_buffers)
            for master in sorted(clock_defaults)
        },
        "original_clock_loads_checked": clock_loads_checked if clock_defaults else None,
        "original_clock_sources": sorted(
            f"{instance}/{pin}" for instance, pin in clock_sources
        )
        if clock_defaults
        else None,
        "clock_dummy_loads": dummy_allowances,
        "added_clock_dummy_loads": len(dummy_allowances),
        "added_clock_dummy_counts": {
            master: sum(
                value["master"] == master for value in dummy_allowances.values()
            )
            for master in sorted(dummy_schemas)
        },
        "verified_clock_dummy_schemas": dummy_schemas,
        "clock_dummy_outputs_absent_from_regular_and_special_nets": bool(
            dummy_allowances
        ),
        "routing_rule_metadata": {
            "scope": "Parsed CLOCK NDR declarations/references bound to raw DEF hashes; no physical rule, routing, congestion, or timing claim",
            "before": {
                "declared_rules": before.nondefault_rules,
                "clock_net_rules": before.clock_ndr,
            },
            "after": {
                "declared_rules": after.nondefault_rules,
                "clock_net_rules": after.clock_ndr,
            },
        },
        "added_clock_diode_loads": {
            net: sorted(f"{instance}/{pin}" for instance, pin in pins)
            for net, pins in sorted(clock_additions.items())
        },
        "added_physical_masters": sorted(physical_masters),
        "added_physical_cell_counts": {
            master: sum(value == master for value in physical.values())
            for master in sorted(physical_masters)
        },
        "added_physical_cells": len(physical),
        "verified_physical_schemas": physical_schemas,
        "inputs": {
            key: {"path": str(Path(path).resolve()), "sha256": _sha(path)}
            for key, path in inputs.items()
        },
    }
    if output is not None:
        target = Path(output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt
