"""Pinned tool compatibility and bounded routed-repair integration.

Imports remain standard-library or sibling-only so copied flow assets work in
the bare pinned EDA image. This module does not require an installed Nanochip.
"""
from __future__ import annotations

import fnmatch
import csv
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Optional

from .cell_repair import write_drive_table
from .signal_graph import check_signal_reachability
from .signal_graph import _read_def, _read_lef, _identity_buffer, _physical_diode
from .cell_models import inspect_liberty


PINNED_SCRIPTS = {
    "antenna_repair.tcl": "3e2bb5c1bb74d047e57872d592d8c21ae3d4468b966dbdc6f293d383f9b2f3c3",
    "common/dpl.tcl": "36aab97b93b0468ca4f261df55ae6ec370c628318c105af1ea8769c5a9dcfcdb",
    "common/grt.tcl": "0c229ee43ec834205cb62b5b45d819351b01ac8f50a39bfb020ec3178e56e3f5",
    "repair_design_postgrt.tcl": "fc42121182c245ca85630bb3432f9d8a4bde994abc71fdb5b0786a3739b6bd0b",
}

WORKING_KEYS = (
    "NANOCHIP_SIGNAL_WORKING_TRANSITION",
    "NANOCHIP_SIGNAL_WORKING_CAPACITANCE",
    "NANOCHIP_SIGNAL_RESIDUAL_MAX_WIRE_LENGTH",
)


def working_repair_settings(config):
    """Admit the complete optional optimization policy, never acceptance changes."""
    supplied = [config.get(key) for key in WORKING_KEYS]
    if all(value is None for value in supplied):
        return None
    if any(value is None or isinstance(value, bool) for value in supplied):
        raise ValueError("Working repair targets must be supplied atomically")
    try:
        values = [Decimal(str(value)) for value in supplied]
        originals = [
            Decimal(str(config[key]))
            for key in (
                "MAX_TRANSITION_CONSTRAINT",
                "MAX_CAPACITANCE_CONSTRAINT",
                "GRT_DESIGN_REPAIR_MAX_WIRE_LENGTH",
            )
        ]
    except (KeyError, ArithmeticError, ValueError) as exc:
        raise ValueError("Invalid working repair target or original limit") from exc
    if any(not value.is_finite() or value <= 0 for value in values + originals):
        raise ValueError(
            "Working repair targets and original limits must be finite positive values"
        )
    if any(value >= original for value, original in zip(values, originals)):
        raise ValueError(
            "Working repair targets must be stricter than original limits/native wire bound"
        )
    return dict(zip(WORKING_KEYS, values))


def configure_working_environment(config, env):
    """Null config must clear ambient optional selectors in copied/native flows."""
    result = dict(env)
    values = working_repair_settings(config)
    for key in WORKING_KEYS:
        result.pop(key, None)
    if values is not None:
        result.update({key: str(value) for key, value in values.items()})
    return result


def prepare_route_assets(scripts, output):
    """Guard the measured upstream ordering and retain its exact derivation."""
    scripts, output = Path(scripts), Path(output)
    sources = []
    for relative, expected in PINNED_SCRIPTS.items():
        path = scripts / relative
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("Pinned routed-repair script differs: " + relative)
        retained = output / ("pinned-" + relative.replace("/", "-"))
        retained.write_bytes(data)
        sources.append(
            {"upstream": str(path), "retained": str(retained), "sha256": expected}
        )
    grt = (scripts / "common/grt.tcl").read_text()
    anchor = "set arg_list [list]\n"
    if grt.count(anchor) != 1:
        raise ValueError("Pinned global-routing configuration boundary differs")
    preamble = output / "routing-preamble.tcl"
    preamble.write_text(grt.split(anchor)[0])
    metadata = {
        "schema": "nanochip-routed-repair-compatibility/v1",
        "sources": sources,
        "preamble_sha256": hashlib.sha256(preamble.read_bytes()).hexdigest(),
        "change": "Keep native antenna legalization/incremental routes; omit obsolete outer mirroring/full global reroute",
        "ordering": "Optional Classic post-GRT timing repair precedes final owned antenna repair; no later full global route or mirroring",
        "parasitic_refresh": "Full placement recomputation clears pinned EST invalid bookkeeping, immediately replaced by full retained-route RC before decisions",
        "openroad_revision": "15af3a5c0",
        "limits": "All final antenna, electrical, timing, DRC, LVS and nine-corner coverage checks remain required",
    }
    (output / "route-compatibility.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )
    return str(preamble)


def repair_libraries(config):
    """Select the actual three nominal-RC PVT standard-cell libraries."""
    paths = []
    for corner in config["STA_CORNERS"]:
        if not corner.startswith("nom_"):
            continue
        matches = [
            str(path)
            for pattern, files in config["LIB"].items()
            if fnmatch.fnmatchcase(corner, pattern)
            for path in files
        ]
        if len(matches) != 1:
            raise ValueError(
                "Routed repair requires one matched standard-cell library per PVT"
            )
        paths.extend(matches)
    if len(paths) != 3 or len(set(paths)) != 3:
        raise ValueError("Routed repair requires all three distinct nominal-RC PVTs")
    return paths


def validate_repair_config(config):
    """Reject protection directives that owned edits do not yet implement.

    Applying native don't-touch settings alone would leave custom branching
    and explicit replacements able to bypass them. This bounded teaching
    profile therefore accepts only the established no-protection settings.
    """
    if config.get("RSZ_DONT_TOUCH_RX") not in (None, "$^"):
        raise ValueError(
            "Bounded routed repair does not support RSZ_DONT_TOUCH_RX protection"
        )
    protected = config.get("RSZ_DONT_TOUCH_LIST")
    if protected is not None and (
        not isinstance(protected, (list, tuple)) or len(protected)
    ):
        raise ValueError(
            "Bounded routed repair does not support RSZ_DONT_TOUCH_LIST protection"
        )
    working_repair_settings(config)


def merge_cell_lefs(paths, output):
    """Combine declared schemas for the Python reader, never native EDA.

    Per-file LEF headers and END LIBRARY markers remain byte-preserved. The
    strict schema parser consumes macro declarations across these boundaries.
    """
    if not paths:
        raise ValueError("Missing configured cell LEFs")
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("Schema merge destination already exists or is redirected")
    manifests, macros, classes, contents, seen = [], {}, {}, [], set()
    for value in paths:
        path = Path(value)
        if path.is_symlink() or not path.is_file() or path.resolve() in seen:
            raise ValueError("Repeated or nonregular configured cell LEF")
        seen.add(path.resolve())
        current, current_classes = _read_lef(path)
        if macros.keys() & current.keys():
            raise ValueError("Duplicate configured LEF macro")
        macros.update(current)
        classes.update(current_classes)
        data = path.read_bytes()
        contents.append(data)
        manifests.append(
            {"path": str(path), "sha256": hashlib.sha256(data).hexdigest()}
        )
    output.write_bytes(b"\n".join(contents))
    if _read_lef(output) != (macros, classes):
        raise ValueError("Merged cell LEF schema differs from configured inputs")
    return output, manifests


def audit_repair_phases(output, config, libraries):
    """Compose strict phase-wise reachability; do not invent a direct proof.

    A branch can legitimately serve a diode created in an earlier phase. Each
    phase preserves all its original loads, and byte-bound adjacent endpoints
    make those proofs transitive without weakening the unused-buffer rule.
    """
    output = Path(output)
    lef_path, lef_inputs = merge_cell_lefs(
        config["CELL_LEFS"], output / "configured-cells.merged.lef"
    )
    schemas = [inspect_liberty(path) for path in libraries]
    lef, classes = _read_lef(lef_path)
    rows = list(csv.DictReader((output / "phases.tsv").open(), delimiter="\t"))
    enabled = working_repair_settings(config) is not None
    prefix = [("native", "native")] + (
        [("cap", "cap"), ("slew", "slew")] if enabled else []
    )
    if not len(prefix) <= len(rows) <= len(prefix) + 3 * 2:
        raise ValueError("Missing or over-bound repair phases")
    expected = prefix + [
        (kind + str(cycle), kind)
        for cycle in range(3)
        for kind in ("electrical", "antenna")
    ]
    if [(r["phase"], r["kind"]) for r in rows] != expected[: len(rows)]:
        raise ValueError("Repair phases are missing, duplicated, or reordered")
    receipts, previous = [], None
    for index, row in enumerate(rows):
        phase, kind = row["phase"], row["kind"]
        if (index < len(prefix) and (phase, kind) != prefix[index]) or (
            index >= len(prefix)
            and (
                kind not in {"electrical", "antenna"}
                or re.fullmatch(kind + r"[0-2]", phase) is None
            )
        ):
            raise ValueError("Unexpected repair phase")
        if row["before"] != phase + ".before" or row["after"] != phase + ".after":
            raise ValueError("Unexpected repair checkpoint path")
        before_path, after_path = (
            output / (row[key] + ".def") for key in ("before", "after")
        )
        if previous is not None and previous.read_bytes() != before_path.read_bytes():
            raise ValueError("Repair phase chain has an unguarded DEF mutation")
        before, after = _read_def(before_path), _read_def(after_path)
        changes = {}
        for name, old in before.components.items():
            new = after.components.get(name)
            if new == old:
                continue
            if new is None or any(
                old not in s or new not in s or s[old] != s[new] for s in schemas
            ):
                raise ValueError(
                    "Master replacement lacks three-PVT logical/PG correspondence: "
                    + name
                )
            if any(s[old]["sequential"] for s in schemas):
                raise ValueError(
                    "Sequential master replacement is outside this repair policy: "
                    + name
                )
            if re.match(r"sky130_fd_sc_hd__(?:clkdlybuf|dlygate|dlymetal)", old):
                raise ValueError("Original intentional delay master changed: " + name)
            changes[name] = {"before": old, "after": new}
        if kind in {"electrical", "slew"}:
            recorded = list(
                csv.DictReader(
                    (output / (phase + ".resizes.tsv")).open(), delimiter="\t"
                )
            )
            explicit = {
                r["instance"]: {"before": r["before"], "after": r["after"]}
                for r in recorded
            }
            if (
                len(explicit) != len(recorded)
                or explicit != changes
                or any(r["return"] != "1" for r in recorded)
            ):
                raise ValueError(
                    "Electrical replacements differ from their exact successful-call record"
                )
            preflight = list(
                csv.DictReader(
                    (output / (phase + ".preflight.tsv")).open(), delimiter="\t"
                )
            )
            names, planned = set(), {}
            for item in preflight:
                name, old = item["instance"], item["master_before"]
                if name in names or before.components.get(name) != old:
                    raise ValueError("Duplicate or stale electrical preflight")
                names.add(name)
                pin = (name, item["output_pin"])
                net = before.pin_net.get(pin)
                if net != item["net"] or before.nets[net][0] != "SIGNAL":
                    raise ValueError(
                        "Electrical preflight driver/net differs from phase input"
                    )
                status = item["classification"]
                if status == "supported_slew_only":
                    if not item["master_proposed"]:
                        raise ValueError("Missing proposed supported master")
                    planned[name] = {"before": old, "after": item["master_proposed"]}
                elif status in {"unsupported_working_slew", "cap_net_excluded"}:
                    if item["master_proposed"] or after.components.get(name) != old:
                        raise ValueError(
                            "Skipped electrical preflight case was changed"
                        )
                else:
                    raise ValueError("Unknown electrical preflight outcome")
            if planned != changes:
                raise ValueError(
                    "Executed electrical changes differ from complete preflight"
                )
        if kind == "cap":
            targets = list(
                csv.DictReader((output / "cap.targets.tsv").open(), delimiter="\t")
            )
            nets, drivers = set(), set()
            expected_length = working_repair_settings(config)[
                WORKING_KEYS[2]
            ] * Decimal(".000001")
            for item in targets:
                net, driver = item["net"], item["driver"]
                pin = (driver, item["output_pin"])
                length = Decimal(item["max_length_meters"])
                if (
                    net in nets
                    or driver in drivers
                    or before.components.get(driver) != item["master_before"]
                    or before.pin_net.get(pin) != net
                    or before.nets[net][0] != "SIGNAL"
                    or item.get("computed_logic") != "X"
                    or not length.is_finite()
                    or length <= 0
                    or abs(length - expected_length)
                    > expected_length * Decimal(".0000001")
                ):
                    raise ValueError(
                        "Residual native target differs from configured phase input"
                    )
                endpoints = before.nets[net][1]
                outputs = [
                    p
                    for p in endpoints
                    if p[0] != "PIN"
                    and lef[before.components[p[0]]][p[1]]["direction"] == "OUTPUT"
                ]
                if (
                    any(p[0] == "PIN" for p in endpoints)
                    or outputs != [pin]
                    or re.fullmatch(
                        r"sky130_fd_sc_hd__(?:buf|clkbuf|inv|nand2)_[0-9]+",
                        item["master_before"],
                    )
                    is None
                ):
                    raise ValueError(
                        "Residual native target lacks its eligible unique internal driver"
                    )
                nets.add(net)
                drivers.add(driver)
            if len(targets) > 100 or not changes.keys() <= drivers:
                raise ValueError(
                    "Residual native repair exceeded its declared target scope"
                )
        added = {
            name: master
            for name, master in after.components.items()
            if name not in before.components
        }
        clock_diodes = {}
        buffer_masters = set()
        for name, master in added.items():
            if kind == "antenna":
                if master != "sky130_fd_sc_hd__diode_2":
                    raise ValueError("Antenna repair added an undeclared cell")
                for schema in schemas:
                    _physical_diode(master, schema, lef, classes)
                net = after.pin_net.get((name, "DIODE"))
                if net is None:
                    raise ValueError("Antenna diode has no physical input connection")
                if after.nets[net][0] == "CLOCK":
                    clock_diodes.setdefault(net, []).append(name + "/DIODE")
            else:
                if (
                    re.fullmatch(
                        r"sky130_fd_sc_hd__(?:buf|clkbuf)_(?:4|6|8|12|16)", master
                    )
                    is None
                ):
                    raise ValueError(
                        "Signal repair added an unsupported buffer master: " + master
                    )
                for schema in schemas:
                    _identity_buffer(master, schema, lef)
                buffer_masters.add(master)
        receipt = check_signal_reachability(
            before_path,
            after_path,
            lef_path=lef_path,
            liberty_path=libraries[0],
            added_buffer_masters=tuple(sorted(buffer_masters)),
            allowed_master_changes=changes,
            added_physical_masters=("sky130_fd_sc_hd__diode_2",)
            if kind == "antenna"
            else (),
            allowed_clock_diode_loads={
                net: tuple(sorted(pins)) for net, pins in clock_diodes.items()
            },
            output=output / (phase + ".reachability.json"),
        )
        receipts.append(
            {
                "phase": phase,
                "receipt": phase + ".reachability.json",
                "sha256": hashlib.sha256(
                    (output / (phase + ".reachability.json")).read_bytes()
                ).hexdigest(),
            }
        )
        previous = after_path
    if rows[-1]["kind"] != "antenna":
        raise ValueError("Final repair phase is not antenna-checked")
    emitted = output / (config["DESIGN_NAME"] + ".def")
    if previous.read_bytes() != emitted.read_bytes():
        raise ValueError("Emitted final DEF differs from audited final repair phase")
    boundary_checks = {}
    if enabled:
        measurements = list(csv.reader((output / "checks.tsv").open(), delimiter="\t"))
        required_corners = {c for c in config["STA_CORNERS"] if c.startswith("nom_")}
        for tag, bound in (
            ("original.initial", "native.before"),
            ("original.optimized", "slew.after"),
            ("original.final", rows[-1]["after"]),
        ):
            checks = [r for r in measurements if r and r[0] == tag]
            if len(checks) != 3 or {r[1] for r in checks} != required_corners:
                raise ValueError(
                    "Missing original-limit working-repair boundary checks"
                )
            for check in checks:
                values = [Decimal(v) for v in check[2:]]
                if (
                    len(values) != 5
                    or any(not v.is_finite() for v in values)
                    or any(v < 0 or v != v.to_integral_value() for v in values[2:])
                    or (
                        tag != "original.initial"
                        and (any(v < 0 for v in values[:2]) or any(values[2:]))
                    )
                ):
                    raise ValueError(
                        "Failed original-limit working-repair boundary checks"
                    )
            clean = all(
                all(Decimal(v) >= 0 for v in r[2:4])
                and not any(Decimal(v) for v in r[4:])
                for r in checks
            )
            boundary_checks[tag] = {
                "status": "pass" if clean else "violating_before_repair",
                "rows": checks,
            }
            if (output / (tag + ".def")).read_bytes() != (
                output / (bound + ".def")
            ).read_bytes():
                raise ValueError(
                    "Original-limit check is not bound to its exact repair boundary"
                )
    strict_report = output / (rows[-1]["phase"] + ".strict-antenna.rpt")
    if not strict_report.is_file() or strict_report.is_symlink():
        raise ValueError("Missing exact final strict antenna report")
    final = rows[-1]["after"]
    checks = [
        r
        for r in csv.reader((output / "checks.tsv").open(), delimiter="\t")
        if r and r[0] == final
    ]
    corners = [c for c in config["STA_CORNERS"] if c.startswith("nom_")]
    if len(checks) != 3 or {r[1] for r in checks} != set(corners):
        raise ValueError("Missing final three-PVT electrical/timing measurements")
    for row in checks:
        values = [float(x) for x in row[2:]]
        if (
            len(values) != 5
            or not all(math.isfinite(x) for x in values)
            or any(x < 0 for x in values[:2])
            or any(values[2:])
        ):
            raise ValueError("Final routed repair timing/electrical checks failed")
    caps = []
    limit = Decimal(str(config["MAX_CAPACITANCE_CONSTRAINT"]))
    for corner in corners:
        report = output / (final + "." + corner + ".clock-cap.rpt")
        match = re.search(
            r"Total capacitance:\s+([0-9.]+)(?:-([0-9.]+))?", report.read_text()
        )
        if match is None:
            raise ValueError("Missing supplemental clock-net capacitance")
        actual = max(Decimal(v) for v in match.groups() if v is not None)
        if not actual.is_finite() or actual > limit:
            raise ValueError(
                "Supplemental clock capacitance exceeds unchanged design bound"
            )
        caps.append(
            {
                "requested_corner": corner,
                "all_corner_max_pf": str(actual),
                "design_limit_pf": str(limit),
                "margin_pf": str(limit - actual),
                "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
            }
        )
    result = {
        "schema": "nanochip-routed-repair-audit/v1",
        "status": "pass",
        "eligible": False,
        "scope": "Phase-wise original-load correspondence and unextracted three-PVT checks; final extracted nine-corner/DRC/LVS/mapped workload checks remain mandatory",
        "direct_oldest_to_final_comparator_passed": False,
        "phase_receipts": receipts,
        "working_repair_settings": {
            k: str(v) for k, v in (working_repair_settings(config) or {}).items()
        },
        "initial_original_check_scope": "Pre-repair finite measurements; violations may be repaired, never inherited as final acceptance",
        "original_boundary_checks": boundary_checks,
        "configured_lefs": lef_inputs,
        "merged_lef_sha256": hashlib.sha256(lef_path.read_bytes()).hexdigest(),
        "libraries": [
            {"path": str(p), "sha256": hashlib.sha256(Path(p).read_bytes()).hexdigest()}
            for p in libraries
        ],
        "strict_antenna_report_sha256": hashlib.sha256(
            strict_report.read_bytes()
        ).hexdigest(),
        "drive_choices_sha256": hashlib.sha256(
            (output / "verified-drive-choices.json").read_bytes()
        ).hexdigest(),
        "clock_cap_scope": "Conservative all-corner native report range, not distinct per-PVT port-limit passes",
        "clock_cap": caps,
    }
    (output / "repair-audit.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    return result


def build_repair_step(OpenROAD):
    """Build the step only inside the pinned LibreLane runtime."""
    from librelane.steps import Step, StepError
    from librelane.config import Variable

    @Step.factory.register()
    class RoutedElectricalAntennaRepair(OpenROAD.RepairDesignPostGRT):
        id = "Nanochip.RoutedElectricalAntennaRepair"
        name = "Bounded Routed Electrical and Antenna Repair"
        config_vars = list(
            {
                v.name: v
                for v in OpenROAD.RepairDesignPostGRT.config_vars
                + OpenROAD.RepairAntennas.Steps[0].config_vars
            }.values()
        ) + [
            Variable(
                WORKING_KEYS[0],
                Optional[Decimal],
                "Optional SIGNAL working transition in ns; original acceptance remains unchanged.",
                default=None,
            ),
            Variable(
                WORKING_KEYS[1],
                Optional[Decimal],
                "Optional SIGNAL working capacitance in pF; original acceptance remains unchanged.",
                default=None,
            ),
            Variable(
                WORKING_KEYS[2],
                Optional[Decimal],
                "Optional residual SIGNAL wire bound in um, stricter than the native whole-design bound.",
                default=None,
            ),
        ]

        def prepare_env(self, env, state):
            return configure_working_environment(
                self.config, super().prepare_env(env, state)
            )

        def get_script_path(self):
            return str(Path(__file__).with_name("antenna_electrical_step.tcl"))

        def run(self, state_in, **kwargs):
            kwargs, env = self.extract_env(kwargs)
            try:
                validate_repair_config(self.config)
            except ValueError as exc:
                raise StepError(str(exc)) from exc
            output = Path(self.step_dir)
            scripts = Path(
                OpenROAD.RepairAntennas.Steps[0].get_script_path(self)
            ).parent
            libraries = repair_libraries(self.config)
            preamble = prepare_route_assets(scripts, output)
            choices = output / "verified-drive-choices.tcl"
            write_drive_table(libraries, choices)
            env.update(
                NANOCHIP_REPAIR_DIR=str(output),
                NANOCHIP_REPAIR_ASSETS=str(Path(__file__).parent),
                NANOCHIP_REPAIR_CHOICES=str(choices),
                NANOCHIP_ROUTING_PREAMBLE=preamble,
            )
            views, metrics = super().run(state_in, env=env, **kwargs)
            try:
                audit_repair_phases(output, self.config, libraries)
            except (ValueError, OSError, KeyError) as exc:
                raise StepError(
                    "Routed-repair evidence audit failed: " + str(exc)
                ) from exc
            return views, metrics

    class CompatibleRepairAntennas(OpenROAD.RepairAntennas):
        Steps = [RoutedElectricalAntennaRepair, OpenROAD.CheckAntennas]

    return CompatibleRepairAntennas
