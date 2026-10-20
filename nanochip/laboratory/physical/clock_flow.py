"""Manifested Classic extension for bounded clock/electrical/antenna repair.

Importing this module does not require LibreLane. The executable entrypoint
registers clock repair and replaces the incompatible antenna wrapper, retaining
all final verification obligations. Optional post-GRT timing repair precedes
the final owned antenna repair so it cannot discard repaired route guides.
"""

import hashlib
import importlib
import json
import math
import os
from decimal import Decimal
from pathlib import Path
import sys
import types
from typing import Optional
import uuid


PROFILE = "NanochipClockRepair"
STEP_ID = "Nanochip.ClockFanoutRepair"
CLOCK_BRANCH_CELLS = tuple("sky130_fd_sc_hd__clkbuf_" + str(drive) for drive in (2, 4, 8, 16))
FLOW_FILES = ("clock_flow.py", "clock_repair.tcl", "clock_repair_step.tcl",
              "repair_flow.py", "electrical_repair.tcl", "antenna_electrical_step.tcl",
              "cell_repair.py", "signal_graph.py", "cell_models.py", "magic_flow.py", "klayout_flow.py")


def load_flow_helper(name):
    """Import sibling helpers from this frozen directory, including standalone use.

    The host Docker adapter copies these files without installing Nanochip in
    the tool image. A private namespace keeps relative parser imports within
    that exact asset set and separates two staged runs in the same interpreter.
    Producer/task manifests bind the expected file hashes separately.
    """
    if name not in {"repair_flow", "cell_repair", "signal_graph", "cell_models", "magic_flow", "klayout_flow"}:
        raise ValueError("Unknown physical flow helper")
    directory = Path(__file__).resolve().parent
    for filename in FLOW_FILES:
        path = directory / filename
        if not path.is_file() or path.is_symlink() or path.resolve().parent != directory:
            raise ValueError("Incomplete or redirected physical flow assets: " + filename)
    namespace = "_nanochip_physical_assets_" + hashlib.sha256(str(directory).encode()).hexdigest()[:20]
    if namespace not in sys.modules:
        package = types.ModuleType(namespace)
        package.__path__ = [str(directory)]
        sys.modules[namespace] = package
    module = importlib.import_module(namespace + "." + name)
    if Path(module.__file__).resolve().parent != directory:
        raise ValueError("Physical helper escaped its frozen asset directory")
    return module
MIDPNR_SCRIPT_SHA256 = "56dfd083ad0675d5ece8750172032ee623c4feff7799b1f42feb2a56a23b67d0"
MIDPNR_OLD_BRANCH = "} elseif { [rsz::check_corner_wire_cap] } {\n        estimate_parasitics -placement\n    }"
MIDPNR_NEW_BRANCH = "} else {\n        estimate_parasitics -placement\n    }"
SKEW_BLOCK_START = 'puts "%OL_CREATE_REPORT skew.min.rpt"'
SKEW_BLOCK_END = 'puts "%OL_CREATE_REPORT ws.min.rpt"'
SKEW_BLOCK_SHA256 = "18fcbb5cd6c6d0070fcc8c59900854b8100bf0530ecd7426abec158d9d18bbd7"
SKEW_REASON = ("Optional whole-register fanout clock-skew diagnostics omitted after measured 266.122532s nominal STA; "
               "propagated-clock path checks, setup/hold/electrical metrics and complete corner coverage remain mandatory")
DRT_SCRIPT_SHA256 = "d343af602b32a82512ee568e590af33c7669df4fe65413e6d488c2164b88352b"
DRT_OLD_COMMAND = "detailed_route\\\n    -bottom_routing_layer $min_layer\\\n    -top_routing_layer $max_layer\\\n"
DRT_NEW_COMMAND = ('set_routing_layers -signal "$min_layer-$max_layer" -clock "$min_layer-$max_layer"\n'
                   'detailed_route\\\n')


def derive_drt_script(upstream, output):
    """Map removed routing-layer flags to their current API, with equal bounds."""
    upstream, output = Path(upstream), Path(output)
    data = upstream.read_bytes()
    if hashlib.sha256(data).hexdigest() != DRT_SCRIPT_SHA256 or data.decode().count(DRT_OLD_COMMAND) != 1:
        raise ValueError("Pinned detailed-routing script identity or layer branch differs")
    output.write_text(data.decode().replace(DRT_OLD_COMMAND, DRT_NEW_COMMAND))
    output.with_suffix(".json").write_text(json.dumps({"schema": "nanochip-drt-api-compatibility/v1",
        "upstream_path": str(upstream), "upstream_sha256": DRT_SCRIPT_SHA256,
        "derived_path": str(output), "derived_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "change": "Map bottom/top routing flags to set_routing_layers for signal and clock; identical resolved layer bounds",
        "preserved": "Routing layer bounds, seed, optimization iterations, DRC reporting and final checks"}, indent=2, sort_keys=True) + "\n")
    return str(output)


def bounded_drt_threads(configured, budget):
    if budget is None or not budget.isdigit() or not 1 <= int(budget) <= 8:
        raise ValueError("Detailed routing requires the declared NANOCHIP_PHYSICAL_CORES budget")
    if configured is not None and (type(configured) is not int or configured < 1):
        raise ValueError("Detailed routing thread setting must be a positive integer")
    return min(configured or int(budget), int(budget))


def derive_midpnr_script(upstream, output):
    """Derive the pinned corner producer with disclosed reporting changes.

    The preceding set_rc.tcl establishes wire RC. OpenROAD then either uses
    actual global routes, or estimates placement parasitics directly. The
    latter operation is required after buffering invalidates old routes.
    """
    upstream, output = Path(upstream), Path(output)
    data = upstream.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != MIDPNR_SCRIPT_SHA256:
        raise ValueError("Pinned mid-PnR STA script identity differs")
    original = data.decode()
    if original.count(MIDPNR_OLD_BRANCH) != 1:
        raise ValueError("Pinned mid-PnR STA branch differs")
    derived = original.replace(MIDPNR_OLD_BRANCH, MIDPNR_NEW_BRANCH)
    if original.count(SKEW_BLOCK_START) != 1 or original.count(SKEW_BLOCK_END) != 1:
        raise ValueError("Pinned optional clock-skew report boundaries differ")
    start, end = original.index(SKEW_BLOCK_START), original.index(SKEW_BLOCK_END)
    block = original[start:end]
    if hashlib.sha256(block.encode()).hexdigest() != SKEW_BLOCK_SHA256:
        raise ValueError("Pinned optional clock-skew report block differs")
    derived = derived.replace(block, 'puts "NANOCHIP_CLOCK_SKEW_DIAGNOSTICS=not_computed"\n\n')
    # Several final STA corners request the same script concurrently. Publish
    # complete immutable content atomically rather than expose a truncated file.
    temporary = output.with_name(output.name + "." + uuid.uuid4().hex)
    temporary.write_text(derived)
    temporary.replace(output)
    metadata = {"schema": "nanochip-corner-sta-profile/v2", "upstream_path": str(upstream),
                "upstream_sha256": digest, "derived_path": str(output),
                "derived_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                "parasitic_change": "Use placement parasitics when global routes are absent",
                "clock_skew_diagnostics": {"status": "not_computed", "reason": SKEW_REASON,
                    "upstream_block_sha256": SKEW_BLOCK_SHA256,
                    "opensta_revision": "857316ff001b2a8dbbdc5996944d08a6d38c87ab",
                    "algorithm_source": "https://raw.githubusercontent.com/The-OpenROAD-Project/OpenSTA/857316ff001b2a8dbbdc5996944d08a6d38c87ab/search/ClkSkew.cc"},
                "preserved": "All setup/hold/full clock-expanded path reports, violation enumeration, electrical checks, constraints and corner coverage"}
    temporary = output.with_name(output.name + "." + uuid.uuid4().hex)
    temporary.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    temporary.replace(output.with_suffix(".json"))
    return str(output)


def invalidate_inherited_skew(inherited, updates):
    """Explicit null invalidates old diagnostic values; it never means zero."""
    result = dict(updates)
    result.update({key: None for key in set(inherited) | set(updates) if key.startswith("clock__skew__")})
    return result


def replace_step_family(step, replacements):
    """Include LibreLane's already-normalized repeated step subclasses."""
    for original, replacement in replacements:
        if issubclass(step, original):
            return replacement.with_id(step.id)
    return step


def branch_counts(loads: int, *, limit=10, group_size=8) -> list[int]:
    """Number of noninverting buffers at each newly inserted clock level."""
    if type(loads) is not int or loads < 0 or type(limit) is not int or limit < 2:
        raise ValueError("Use nonnegative integer loads and a fanout limit >=2")
    if type(group_size) is not int or not 2 <= group_size <= min(8, limit):
        raise ValueError("Clock groups must contain 2..min(8,limit) sinks")
    result = []
    while loads > limit:
        loads = (loads + group_size - 1) // group_size
        result.append(loads)
    return result


def validate_clock_repair_config(config):
    """Validate the optional working target without altering signoff limits.

    The clock-buffer family is independently verified against the pinned
    platform's actual libraries; arbitrary one-input cells are not accepted.
    Native reproduction and all physical checks remain separate obligations.
    """
    master = config.get("NANOCHIP_CLOCK_BRANCH_CELL", CLOCK_BRANCH_CELLS[1])
    if master not in CLOCK_BRANCH_CELLS:
        raise ValueError("Clock branching requires a verified noninverting clkbuf_2/4/8/16 master")
    value = config.get("NANOCHIP_CLOCK_WORKING_PIN_CAPACITANCE")
    if value is not None:
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            raise ValueError("Clock working pin capacitance must be a positive finite pF number or null")
        try:
            valid = math.isfinite(value) and value > 0
        except (ValueError, OverflowError):
            valid = False
        if not valid:
            raise ValueError("Clock working pin capacitance must be a positive finite pF number or null")


def register_flow():
    """Register the extension inside the exact pinned LibreLane runtime."""
    from librelane.config import Variable
    from librelane.flows import Flow
    from librelane.flows.classic import Classic
    from librelane.steps import KLayout, Magic, OpenROAD, Step, StepError
    from librelane.steps.openroad import ResizerStep, dpl_variables

    @Step.factory.register()
    class ClockFanoutRepair(ResizerStep):
        id = STEP_ID
        name = "Repair Clock Fanout After CTS"
        config_vars = OpenROAD.ResizerTimingPostCTS.config_vars + [
            Variable("NANOCHIP_CLOCK_BRANCH_SIZE", int,
                     "Maximum actual sinks per added noninverting clock branch; acceptance limits remain unchanged.", default=8),
            Variable("NANOCHIP_CLOCK_BRANCH_CELL", str,
                     "Verified noninverting clkbuf_2/4/8/16 master for internal clock branches.", default=CLOCK_BRANCH_CELLS[1]),
            Variable("NANOCHIP_CLOCK_WORKING_PIN_CAPACITANCE", Optional[Decimal],
                     "Optional positive finite intrinsic CLOCK pin-load target in pF across every loaded corner; does not replace final total-capacitance acceptance.", default=None),
            Variable("NANOCHIP_CLOCK_BUFFER_INPUTS", bool,
                     "Add a noninverting small-input-capacitance buffer before each CTS input root.", default=False),
            Variable("NANOCHIP_POST_CTS_HOLD_REPAIR", bool,
                     "Run electrical and hold repair after clock branching; final acceptance stays unchanged.", default=False),
        ]

        def get_script_path(self):
            return str(Path(__file__).with_name("clock_repair_step.tcl"))

        def prepare_env(self, env, state):
            env = super().prepare_env(env, state)
            # The pinned base skips null config values, retaining any ambient
            # environment entry. Null must disable this config-bound selector.
            if self.config.get("NANOCHIP_CLOCK_WORKING_PIN_CAPACITANCE") is None:
                env.pop("NANOCHIP_CLOCK_WORKING_PIN_CAPACITANCE", None)
            return env

        def run(self, state_in, **kwargs):
            try:
                validate_clock_repair_config(self.config)
            except ValueError as exc:
                raise StepError(str(exc)) from exc
            return super().run(state_in, **kwargs)

    class CornerReporting:
        def get_script_path(self):
            return derive_midpnr_script(super().get_script_path(),
                                       Path(self.step_dir) / "corner-placement-compat.tcl")

        def run(self, state_in, **kwargs):
            views, metrics = super().run(state_in, **kwargs)
            return views, invalidate_inherited_skew(state_in.metrics, metrics)

    class CompatibleSTAMidPNR(CornerReporting, OpenROAD.STAMidPNR):
        pass

    class CompatibleSTAPrePNR(CornerReporting, OpenROAD.STAPrePNR):
        pass

    class CompatibleSTAPostPNR(CornerReporting, OpenROAD.STAPostPNR):
        pass

    class CompatibleDetailedRouting(OpenROAD.DetailedRouting):
        def get_script_path(self):
            return derive_drt_script(super().get_script_path(), Path(self.step_dir) / "drt-layer-api-compat.tcl")

        def run(self, state_in, **kwargs):
            kwargs, env = self.extract_env(kwargs)
            env["DRT_THREADS"] = str(bounded_drt_threads(self.config["DRT_THREADS"], os.environ.get("NANOCHIP_PHYSICAL_CORES")))
            return super().run(state_in, env=env, **kwargs)

        def prepare_env(self, env, state):
            env = super().prepare_env(env, state)
            env["DRT_THREADS"] = str(bounded_drt_threads(self.config["DRT_THREADS"], os.environ.get("NANOCHIP_PHYSICAL_CORES")))
            return env

    CompatibleRepairAntennas = load_flow_helper("repair_flow").build_repair_step(OpenROAD)
    magic_helper = load_flow_helper("magic_flow")
    CheckedWriteLEF = magic_helper.build_write_lef_step(Magic, step_error=StepError)
    CheckedMagicStreamOut = magic_helper.build_magic_exit_step(Magic.StreamOut, step_error=StepError)
    CheckedMagicDRC = magic_helper.build_magic_exit_step(Magic.DRC, step_error=StepError)
    CheckedMagicSpiceExtraction = magic_helper.build_magic_exit_step(Magic.SpiceExtraction, step_error=StepError)

    CheckedKLayoutDRC = load_flow_helper("klayout_flow").build_klayout_drc_step(KLayout.DRC, step_error=StepError)

    # Classic normalizes repeated steps with with_id(), creating subclasses.
    # Match their family, and preserve each normalized id. Post must precede
    # Pre because the pinned Post class is itself a Pre subclass.
    replacements = ((OpenROAD.STAPostPNR, CompatibleSTAPostPNR), (OpenROAD.STAMidPNR, CompatibleSTAMidPNR),
                    (OpenROAD.STAPrePNR, CompatibleSTAPrePNR), (OpenROAD.DetailedRouting, CompatibleDetailedRouting),
                    (OpenROAD.RepairAntennas, CompatibleRepairAntennas),
                    (Magic.WriteLEF, CheckedWriteLEF), (Magic.StreamOut, CheckedMagicStreamOut),
                    (Magic.DRC, CheckedMagicDRC), (Magic.SpiceExtraction, CheckedMagicSpiceExtraction),
                    (KLayout.DRC, CheckedKLayoutDRC))

    @Flow.factory.register()
    class NanochipClockRepair(Classic):
        Steps = list(Classic.Steps)
        Steps = [replace_step_family(step, replacements) for step in Steps]
        # Optional timing repair can legalize and fully reroute. Keep that
        # original Classic step before the final owned antenna repair so it
        # cannot discard antenna jumpers afterward, even when explicitly enabled.
        timing = [step for step in Steps if issubclass(step, OpenROAD.ResizerTimingPostGRT)]
        Steps = [step for step in Steps if not issubclass(step, OpenROAD.ResizerTimingPostGRT)]
        antenna_index = next(i for i, step in enumerate(Steps) if issubclass(step, OpenROAD.RepairAntennas))
        Steps[antenna_index:antenna_index] = timing
        Steps.insert(Steps.index(OpenROAD.CTS) + 1, ClockFanoutRepair)

    return NanochipClockRepair


if __name__ == "__main__":
    register_flow()
    from librelane.__main__ import cli
    cli()
