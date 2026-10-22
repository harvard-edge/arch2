"""Plan report-driven ECO experiments without changing historical receipts.

A plan is diagnostic evidence, never a successful physical implementation.
The caller must re-route, extract, and run the complete acceptance flow after
changing connectivity, placement, or cell sizes.
"""

from dataclasses import asdict
import json
from pathlib import Path
import shutil

from ..contracts import Artifact, ContractError, file_sha256
from .flow import IMAGE, PDK_REVISION, SCOPE, _json


def parse_antenna_report(raw: str) -> list[dict]:
    """Return only the particular sink pins marked violated by check_antennas."""
    net = pin = None
    failures = {}
    for line in raw.splitlines():
        if line.startswith("Net: "):
            net, pin = line.removeprefix("Net: ").strip(), None
        elif line.lstrip().startswith("Pin: "):
            pin = line.split("Pin:", 1)[1].strip().split()[0]
        elif "(VIOLATED)" in line:
            if not net or not pin:
                raise ContractError(
                    "Antenna violation has no associated net and sink pin"
                )
            failures[(net, pin)] = {"net": net, "pin": pin}
    return list(failures.values())


def parse_electrical_report(raw: str) -> dict[str, list[dict]]:
    sections = {"max slew": [], "max fanout": [], "max capacitance": []}
    section = None
    for line in raw.splitlines():
        if line.strip() in sections:
            section = line.strip()
        elif "(VIOLATED)" in line and section:
            fields = line.split()
            try:
                sections[section].append(
                    {
                        "pin": fields[0],
                        "limit": float(fields[1]),
                        "observed": float(fields[2]),
                    }
                )
            except (ValueError, IndexError) as exc:
                raise ContractError("Malformed electrical violation row") from exc
    return sections


def _tcl_list(values: list[str]) -> str:
    def quote(value):
        for original, escaped in (
            ("\\", "\\\\"),
            ('"', '\\"'),
            ("$", "\\$"),
            ("[", "\\["),
            ("]", "\\]"),
            ("\n", "\\n"),
            ("\r", "\\r"),
        ):
            value = value.replace(original, escaped)
        return '"' + value + '"'

    return "[list " + " ".join(quote(value) for value in values) + "]"


def plan_retained_repair(source: str | Path, output: str | Path) -> dict:
    """Freeze specific final-route failures and their raw inputs into a new plan."""
    source = Path(source).resolve(strict=True)
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(output)
    stages = source / "runs/physical"
    sta = sorted(stages.glob("*-openroad-stapostpnr"))
    routes = sorted(stages.glob("*-openroad-detailedrouting"))
    if len(sta) != 1 or len(routes) != 1:
        raise ContractError(
            "Exactly one completed final STA and detailed-routing stage is required"
        )
    route_index = int(routes[0].name.split("-", 1)[0])
    antenna = [
        p
        for p in stages.glob("*-openroad-checkantennas*")
        if int(p.name.split("-", 1)[0]) > route_index
    ]
    if len(antenna) != 1:
        raise ContractError("Exactly one final-route antenna report is required")
    config = json.loads((sta[0] / "config.json").read_text())
    electrical = {}
    artifacts = [
        sta[0] / "config.json",
        sta[0] / "state_out.json",
        routes[0] / "state_out.json",
    ]
    for corner in config["STA_CORNERS"]:
        report = sta[0] / corner / "checks.rpt"
        electrical[corner] = parse_electrical_report(report.read_text())
        artifacts.append(report)
    report = antenna[0] / "reports/antenna.rpt"
    pins = parse_antenna_report(report.read_text())
    artifacts.extend([report, antenna[0] / "state_out.json"])
    clock_drivers = sorted(
        {
            row["pin"]
            for corner in electrical.values()
            for category in ("max fanout", "max capacitance")
            for row in corner[category]
            if row["pin"].startswith("clkbuf")
        }
    )
    output.mkdir(parents=True)
    shutil.copyfile(Path(__file__).with_name("closure.tcl"), output / "closure.tcl")
    (output / "targets.tcl").write_text(
        "set NANOCHIP_CLOCK_DRIVER_PINS "
        + _tcl_list(clock_drivers)
        + "\n"
        + "set NANOCHIP_ANTENNA_SINK_PINS "
        + _tcl_list([item["pin"] for item in pins])
        + "\n"
    )
    plan = {
        "schema": "nanochip-routed-repair-plan/v1",
        "status": "planned",
        "eligible": False,
        "source_root": str(source),
        "image": IMAGE,
        "pdk_revision": PDK_REVISION,
        "design_name": config["DESIGN_NAME"],
        "scope": SCOPE
        if config["DESIGN_NAME"] == "msh_deq"
        else "design:" + config["DESIGN_NAME"],
        "clock_driver_pins": clock_drivers,
        "antenna_sinks": pins,
        "electrical_by_corner": electrical,
        "constraints": {
            key: config[key]
            for key in (
                "CLOCK_PERIOD",
                "MAX_TRANSITION_CONSTRAINT",
                "MAX_FANOUT_CONSTRAINT",
                "MAX_CAPACITANCE_CONSTRAINT",
                "STA_CORNERS",
            )
        },
        "inputs": [
            asdict(Artifact.from_file(source, str(path.relative_to(source))))
            for path in artifacts
        ],
        "repair_helper_sha256": file_sha256(output / "closure.tcl"),
        "repair_targets_sha256": file_sha256(output / "targets.tcl"),
        "required_after_repair": [
            "detailed_route",
            "extracted_nine_corner_electrical_and_timing",
            "constraint_coverage",
            "postroute_antenna",
            "magic_drc",
            "klayout_drc",
            "lvs",
            "rtl_netlist_correspondence",
        ],
        "boundary": "Report-driven experimental plan only. No acceptance or closure claim.",
    }
    _json(output / "plan.json", plan)
    return plan
