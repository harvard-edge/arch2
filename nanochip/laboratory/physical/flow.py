"""Run one immutable msh_deq snapshot; retain failed and partial executions."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import fnmatch
import json
import math
import os
import signal
from pathlib import Path
import platform
import re
import shutil
import subprocess
import time
import uuid
from collections.abc import Mapping

from ..contracts import Artifact, CheckResult, ContractError, Cost, Metric, RunReceipt, file_sha256

IMAGE = "hpretl/iic-osic-tools@sha256:ae380e2b0b96bd57b91f5864623ed488d00f78eaf58caf7f7d9d3754d315df38"
PDK_REVISION = "54435919abffb937387ec956209f9cf5fd2dfbee"
SCOPE = "block:msh_deq"
CONFIG = Path(__file__).with_name("config.json")
BOUNDARY = "msh_deq only, SKY130 HD, 100 ns clock. No complete accelerator, workload, RTL equivalence, manufacturing signoff, or tapeout claim."


def _json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _number(value):
    return type(value) in (float, int) and math.isfinite(value)


def collect_checks(output: Path, *, scope: str = SCOPE) -> tuple[list[dict], dict]:
    """Read only the executing stage's state, never inherited pre-route timing."""
    checks = []
    selected = {}
    run = output / "runs" / "physical"
    states = {}
    for path in sorted(run.glob("*/state_out.json")):
        stage = path.parent.name.split("-", 1)[-1]
        try:
            metrics = json.loads(path.read_text(), parse_constant=lambda token: token).get("metrics", {})
        except (OSError, ValueError, AttributeError):
            # A killed tool may leave an incomplete state. Retain its bytes,
            # but never promote malformed partial output to successful checks.
            metrics = {}
        states[stage] = (path, metrics if isinstance(metrics, dict) else {})
    gds_paths = list(run.glob("final/gds/*.gds"))
    gds_paths += list(run.glob("*-magic-streamout/*.gds"))
    gds_paths += list(run.glob("*-klayout-streamout/*.gds"))
    gds = [p for p in gds_paths if p.is_file() and p.stat().st_size > 0]
    checks.append(dict(name="gds_generated", status="pass" if gds else "not_run", scope=scope,
                       details="Retained GDS bytes; this check does not assert correctness: " + ", ".join(str(p.relative_to(output)) for p in gds)))
    route_path = states.get("openroad-detailedrouting", (None, {}))[0]
    route_index = int(route_path.parent.name.split("-", 1)[0]) if route_path else 10**9
    antenna_stage = next((name for name in reversed(states)
                          if name.startswith("openroad-checkantennas")
                          and int(states[name][0].parent.name.split("-", 1)[0]) > route_index),
                         "postroute-antenna-not-completed")
    requirements = {
        "postroute_antenna": (antenna_stage, ("route__antenna_violation__count",)),
        "detailed_route_drc": ("openroad-detailedrouting", ("route__drc_errors",)),
        "magic_drc": ("magic-drc", ("magic__drc_error__count",)),
        "klayout_drc": ("klayout-drc", ("klayout__drc_error__count",)),
        "physical_lvs": ("netgen-lvs", ("design__lvs_error__count",)),
        "routed_timing": ("openroad-stapostpnr", ("timing__setup_vio__count", "timing__hold_vio__count")),
        "electrical_constraints": ("openroad-stapostpnr", ("design__max_slew_violation__count", "design__max_cap_violation__count", "design__max_fanout_violation__count")),
    }
    for name, (stage, keys) in requirements.items():
        path, metrics = states.get(stage, (None, {}))
        values = {key: metrics.get(key) for key in keys}
        valid = all(_number(v) and v >= 0 for v in values.values())
        status = ("pass" if all(v == 0 for v in values.values()) else "fail") if valid else "unresolved"
        if name == "routed_timing":
            # Require bound coverage of every configured corner. A native
            # unconstrained count is diagnostic, not a substitute for check_setup.
            unconstrained = metrics.get("timing__unconstrained__count")
            coverage_pass = False
            coverage_path = output / "coverage-receipt.json"
            if path and coverage_path.is_file():
                try:
                    coverage = json.loads(coverage_path.read_text())
                    coverage_pass = (coverage.get("status") == "pass" and coverage.get("image") == IMAGE
                                     and coverage.get("postroute_state_sha256") == file_sha256(path)
                                     and coverage.get("expected_corners") == json.loads((path.parent / "config.json").read_text())["STA_CORNERS"]
                                     and coverage.get("expected_corners") == [c["corner"] for c in coverage["corners"]]
                                     and file_sha256(output / "coverage.tcl") == coverage["script_sha256"]
                                     and bool(coverage["input_artifacts"])
                                     and all(file_sha256(output / a["path"]) == a["sha256"] for a in coverage["input_artifacts"])
                                     and bool(coverage["corners"])
                                     and all(c["status"] == "pass" and file_sha256(output / c["log"]) == c["log_sha256"]
                                             and file_sha256(output / c["environment"]) == c["environment_sha256"]
                                             for c in coverage["corners"]))
                except (OSError, ValueError, KeyError, TypeError):
                    coverage_pass = False
            if status == "pass" and not coverage_pass:
                status = "unresolved"
            values["timing__unconstrained__count"] = unconstrained
            values["explicit_corner_coverage"] = coverage_pass
        checks.append(dict(name=name, status=status, scope=scope,
                           details=f"{path.relative_to(output) if path else 'stage not completed'}; {values}"))
        if path:
            selected[stage] = {"path": str(path.relative_to(output)), "metrics": metrics}
    # Whole physical DRC needs both independent deck checks; route DRC alone is narrower.
    drcs = [c for c in checks if c["name"] in ("magic_drc", "klayout_drc")]
    status = "pass" if all(c["status"] == "pass" for c in drcs) else (
        "fail" if any(c["status"] == "fail" for c in drcs) else "unresolved")
    checks.append(dict(name="physical_drc", status=status, scope=scope,
                       details="Magic and KLayout bundled SKY130 decks; no foundry signoff claim"))
    return checks, selected


def run_coverage(output: str | Path, timeout_s: float = 120, *, mode: str | None = None) -> dict:
    """Execute explicit STA constraint checks for every retained postroute corner.

    This writes a supplementary receipt, never overwrites the original flow
    receipt, and never treats a missing command return marker as success.
    """
    output = Path(output).resolve(strict=True)
    mode = _runtime_mode(mode)
    receipt_path = output / "coverage-receipt.json"
    if receipt_path.exists():
        raise FileExistsError(f"Coverage receipt already exists: {receipt_path}")
    stages = sorted((output / "runs/physical").glob("*-openroad-stapostpnr"))
    result = {"schema": "nanochip-constraint-coverage/v1", "status": "not_run", "image": IMAGE,
              "checks": [], "corners": [], "commands": [], "timeout_s": timeout_s, "runtime_mode": mode}
    started = time.monotonic()
    if len(stages) == 1 and (stages[0] / "state_out.json").is_file():
        config = json.loads((stages[0] / "config.json").read_text())
        expected = config["STA_CORNERS"]
        result["postroute_state_sha256"] = file_sha256(stages[0] / "state_out.json")
        result["expected_corners"] = expected
        state = json.loads((stages[0] / "state_in.json").read_text())
        inputs = []
        def retain(value):
            if isinstance(value, dict):
                for item in value.values():
                    retain(item)
            elif isinstance(value, str):
                relative = _retained_relative(output, value)
                inputs.append(asdict(Artifact.from_file(output, relative)))
        for key in ("nl", "pnl", "sdc", "spef"):
            retain(state.get(key))
        result["input_artifacts"] = inputs
        script = output / "coverage.tcl"
        shutil.copyfile(Path(__file__).with_name("coverage.tcl"), script)
        result["script_sha256"] = file_sha256(script)
        for corner in expected:
            envs = sorted((stages[0] / corner).glob("_env_*.tcl"))
            record = {"corner": corner, "status": "unresolved"}
            result["corners"].append(record)
            if len(envs) != 1:
                record["details"] = "Exactly one retained STA environment is required"
                continue
            remaining = timeout_s - (time.monotonic() - started)
            if remaining <= 0:
                record["details"] = "Coverage wall-time budget exhausted"
                continue
            name = "nanochip-coverage-" + uuid.uuid4().hex[:12]
            libs, missing_macros = _coverage_libraries(config, corner)
            spefs = [value for pattern, value in state["spef"].items() if fnmatch.fnmatch(corner, pattern)]
            if not libs or len(spefs) != 1 or missing_macros:
                record["details"] = "Coverage needs one top SPEF and liberty timing models for every macro at this corner: " + ", ".join(missing_macros)
                continue
            for lib in libs:
                if lib.startswith("/work/") or Path(lib).is_relative_to(output):
                    artifact = asdict(Artifact.from_file(output, _retained_relative(output, lib)))
                    if artifact not in inputs:
                        inputs.append(artifact)
            bindings = {"NANOCHIP_CORNER": corner, "NANOCHIP_LIBS": " ".join(libs), "NANOCHIP_TOP": config["DESIGN_NAME"],
                        "NANOCHIP_NETLIST": state["nl"], "NANOCHIP_SDC": state["sdc"], "NANOCHIP_SPEF": spefs[0]}
            record["bindings"] = bindings
            log_path = output / ("coverage-" + corner + ".log")
            command = ["docker", "run", "--rm", "--pull=never", "--network", "none", "--cpus", "1",
                       "--name", name, "--entrypoint", "/bin/bash", "-v", f"{output}:/work",
                       *[item for key, value in bindings.items() for item in ("-e", f"{key}={value}")], IMAGE, "-lc",
                       "sta -no_splash -exit /work/coverage.tcl"]
            if mode == "native":
                command = ["sta", "-no_splash", "-exit", str(script)]
            result["commands"].append(command)
            record.update(environment=str(envs[0].relative_to(output)), environment_sha256=file_sha256(envs[0]))
            try:
                with log_path.open("w") as stream:
                    native_env = dict(os.environ, **bindings) if mode == "native" else None
                    code = _execute(command, stream, remaining, env=native_env)
                raw = log_path.read_text()
                flags = re.findall(r"^NANOCHIP_CONSTRAINT_COVERAGE=([01])$", raw, re.MULTILINE)
                clocks = re.findall(r"^NANOCHIP_CLOCK_COUNT=([0-9]+)$", raw, re.MULTILINE)
                registers = re.findall(r"^NANOCHIP_REGISTER_COUNT=([0-9]+)$", raw, re.MULTILINE)
                explicit = len(flags) == len(clocks) == len(registers) == 1
                passed = explicit and code == 0 and flags[0] == "1" and int(clocks[0]) > 0 and int(registers[0]) > 0
                record.update(status="pass" if passed else "fail" if explicit else "unresolved", returncode=code,
                              clock_counts=clocks, register_counts=registers, check_returns=flags)
            except subprocess.TimeoutExpired:
                if mode == "docker":
                    subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
                record["details"] = "Coverage container killed at wall-time bound"
            except KeyboardInterrupt:
                # _execute stops native tools/the Docker client. A Docker
                # client exiting does not itself terminate its container.
                if mode == "docker":
                    cleanup = ["docker", "rm", "-f", name]
                    result["commands"].append(cleanup)
                    try:
                        code = subprocess.run(cleanup, capture_output=True, text=True, timeout=15).returncode
                        record["cleanup_returncode"] = code
                    except (OSError, subprocess.SubprocessError) as exc:
                        record["cleanup_error"] = str(exc)
                record.update(status="interrupted", details="Interrupted before coverage completed",
                              log=str(log_path.relative_to(output)), log_sha256=file_sha256(log_path))
                result.update(status="interrupted", elapsed_s=time.monotonic() - started)
                _json(receipt_path, result)
                raise
            except OSError as exc:
                record["details"] = str(exc)
            record.update(log=str(log_path.relative_to(output)), log_sha256=file_sha256(log_path))
        result["status"] = "pass" if result["corners"] and all(c["status"] == "pass" for c in result["corners"]) else (
            "fail" if any(c["status"] == "fail" for c in result["corners"]) else "unresolved")
    result["elapsed_s"] = time.monotonic() - started
    _json(receipt_path, result)
    return result


def _coverage_libraries(config: dict, corner: str) -> tuple[list[str], list[str]]:
    """Require every configured macro's liberty view; never time a black box."""
    def matching(views):
        if not isinstance(views, dict):
            return []
        return [path for pattern, paths in views.items() if fnmatch.fnmatch(corner, pattern)
                for path in ([paths] if isinstance(paths, str) else paths)]
    libs = matching(config.get("LIB", {}))
    libs.extend(config.get("EXTRA_LIBS") or [])
    missing = []
    for name, macro in (config.get("MACROS") or {}).items():
        views = matching(macro.get("lib", {}))
        if not views:
            missing.append(name)
        libs.extend(views)
    return list(dict.fromkeys(libs)), missing


def _runtime_mode(mode: str | None) -> str:
    value = mode or os.environ.get("NANOCHIP_PHYSICAL_MODE", "docker")
    if value not in ("docker", "native"):
        raise ValueError("Physical runtime mode must be docker or native")
    return value


def _retained_relative(output: Path, value: str) -> str:
    """Accept container paths or native paths only within this retained run."""
    if value.startswith("/work/"):
        path = output / value.removeprefix("/work/")
    elif "/runs/physical/" in value and not Path(value).is_relative_to(output):
        # Native receipts retain their container mount prefix; rebind the same
        # run-relative artifact when inspected from the host or a new mount.
        path = output / "runs/physical" / value.split("/runs/physical/", 1)[1]
    else:
        path = Path(value)
    return str(path.resolve(strict=True).relative_to(output.resolve(strict=True)))


def _execute(args, stream, timeout, *, env=None) -> int:
    """Kill the complete EDA subprocess tree at the wall-time bound."""
    process = subprocess.Popen(args, stdout=stream, stderr=subprocess.STDOUT,
                               env=env, start_new_session=True)
    try:
        return process.wait(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        # EDA wrappers can start new sessions of their own. Enumerate only
        # this process's descendants, then kill their owned groups as well.
        # Ctrl-C must not abandon the new-session tools after Python exits.
        try:
            rows = subprocess.run(["ps", "-eo", "pid=,ppid="], capture_output=True, text=True, timeout=5).stdout
            pairs = [tuple(map(int, row.split())) for row in rows.splitlines() if len(row.split()) == 2]
            owned = {process.pid}
            while additions := {pid for pid, parent in pairs if parent in owned} - owned:
                owned.update(additions)
            for pid in sorted(owned, reverse=True):
                try:
                    group = os.getpgid(pid)
                    if group in owned:
                        os.killpg(group, signal.SIGKILL)
                    else:
                        os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        except (OSError, subprocess.SubprocessError, ValueError):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait()
        raise


def _validate_design(sources: Mapping[str, str | Path], config: dict) -> dict[str, Path]:
    if not sources or not isinstance(config.get("DESIGN_NAME"), str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", config["DESIGN_NAME"]):
        raise ValueError("A named top module and manifested input files are required")
    retained = {}
    reserved = {"config.json", "runner.py", "coverage.tcl", "receipt.json", "source-manifest.json", "flow-assets", "checkpoint",
                "coverage-receipt.json", "flow.log", "docker.log", "image.json"}
    for name, source in sources.items():
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or str(path) != name or not path.parts or path.parts[0] in reserved or path.parts[0] == "runs":
            raise ValueError(f"Input path must be a safe run-relative filename: {name}")
        retained[name] = Path(source).resolve(strict=True)
        if not retained[name].is_file():
            raise ValueError(f"Input must be a regular file: {source}")
    def references(value):
        if isinstance(value, dict):
            for item in value.values():
                references(item)
        elif isinstance(value, list):
            for item in value:
                references(item)
        elif isinstance(value, str):
            if value.startswith("dir::"):
                pattern = value.removeprefix("dir::")
                if Path(pattern).is_absolute() or ".." in Path(pattern).parts or not any(fnmatch.fnmatch(name, pattern) or name.startswith(pattern.rstrip("/") + "/") for name in retained):
                    raise ValueError(f"Configuration references unmanifested input: {value}")
            elif value.startswith("/"):
                raise ValueError("Design configuration paths must use manifested dir:: inputs")
    references(config)
    if not config.get("VERILOG_FILES"):
        raise ValueError("VERILOG_FILES must identify the manifested RTL")
    return retained


def run_physical_design(sources: Mapping[str, str | Path], output: str | Path, *,
                        config: dict | str | Path, scope: str, boundary: str,
                        timeout_s: float = 900, cores: int = 1, mode: str | None = None,
                        stop_at: str | None = None, resume_from: str | Path | None = None) -> dict:
    """Implement one manifested design, retaining exact inputs and failed checks.

    Additional HDL, SDC, macro LEF/GDS/liberty/model files belong in ``sources``
    and are referenced with ``dir::relative/path`` in the LibreLane config.
    Native mode is for the pinned offline image and never invokes Docker.
    """
    if not math.isfinite(timeout_s) or timeout_s <= 0 or type(cores) is not int or not 1 <= cores <= 8:
        raise ValueError("Use a positive finite timeout and 1..8 CPU cores")
    if stop_at not in (None, "Yosys.Synthesis", "OpenROAD.Floorplan"):
        raise ValueError("Supported physical preflights stop at synthesis or floorplan")
    if not scope or not boundary:
        raise ValueError("Physical design scope and boundary must be explicit")
    mode = _runtime_mode(mode)
    config_path = None if isinstance(config, dict) else Path(config).resolve(strict=True)
    declared = dict(config) if isinstance(config, dict) else json.loads(config_path.read_text())
    from .clock_flow import FLOW_FILES, PROFILE
    profile = (declared.get("meta") or {}).get("flow") or "Classic"
    if profile not in ("Classic", PROFILE):
        raise ValueError("Supported physical profiles are Classic and NanochipClockRepair")
    if resume_from is not None and (profile != PROFILE or stop_at is not None):
        raise ValueError("CTS continuation requires the full clock-repair profile")
    retained = _validate_design(sources, declared)
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Output must be a new path: {output}")
    output.mkdir(parents=True)
    for name, source in retained.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    if config_path:
        shutil.copyfile(config_path, output / "config.json")
    else:
        _json(output / "config.json", declared)
    shutil.copyfile(Path(__file__), output / "runner.py")
    manifest = [asdict(Artifact.from_file(output, name)) for name in sorted(retained)]
    _json(output / "source-manifest.json", manifest)
    source_hash = file_sha256(output / "source-manifest.json")
    legacy = list(retained) == ["msh_deq.v"] and declared["DESIGN_NAME"] == "msh_deq"
    started = time.monotonic()
    result = dict(schema="nanochip-physical/v1", status="unavailable", ok=False,
                  image=IMAGE, pdk="sky130A", pdk_revision=PDK_REVISION, runtime_mode=mode,
                  runtime_image_id=os.environ.get("NANOCHIP_RUNTIME_IMAGE_ID") if mode == "native" else None,
                  flow_stop_at=stop_at, execution_root=str(output) if mode == "native" else "/work",
                  design_name=declared["DESIGN_NAME"], scope=scope, source_manifest=manifest,
                  source_manifest_sha256=source_hash,
                  candidate_sha256=file_sha256(output / "msh_deq.v") if legacy else source_hash,
                  candidate_hash_kind="single-source" if legacy else "source-manifest",
                  config_sha256=file_sha256(output / "config.json"),
                  runner_sha256=file_sha256(output / "runner.py"), cores=cores,
                  execution_mode="checkpoint_continuation" if resume_from is not None else "fresh",
                  flow_profile=profile, flow_assets=[], checkpoint=None,
                  timeout_s=timeout_s, start_timestamp=datetime.now(timezone.utc).isoformat(),
                  host_architecture=platform.machine(), boundary=boundary, commands=[])
    docker = shutil.which("docker") if mode == "docker" else None
    def command(args, logfile, timeout=30):
        result["commands"].append(args)
        with (output / logfile).open("w") as stream:
            return _execute(args, stream, timeout)
    active_container = None
    interrupted = False
    try:
        if profile == PROFILE:
            assets = output / "flow-assets"
            assets.mkdir()
            for name in FLOW_FILES:
                shutil.copyfile(Path(__file__).with_name(name), assets / name)
                item = asdict(Artifact.from_file(output, "flow-assets/" + name))
                item["source_path"] = "nanochip/laboratory/physical/" + name
                result["flow_assets"].append(item)
            _json(assets / "manifest.json", result["flow_assets"])
        if resume_from is not None:
            from .checkpoint import prepare_cts_checkpoint
            result["checkpoint"] = prepare_cts_checkpoint(resume_from, output,
                runtime_root=str(output) if mode == "native" else "/work", image=IMAGE, pdk_revision=PDK_REVISION)
        available = False
        if mode == "native":
            expected_pdk = Path(f"/foss/pdks/ciel/sky130/versions/{PDK_REVISION}/sky130A")
            if os.environ.get("NANOCHIP_PHYSICAL_IMAGE") != IMAGE:
                result["details"] = "Native execution requires the pinned NANOCHIP_PHYSICAL_IMAGE identity"
            elif Path("/foss/pdks/sky130A").resolve() != expected_pdk:
                result["details"] = "Native execution requires the exact pinned PDK revision"
            elif not all(shutil.which(tool) for tool in ("librelane", "openroad", "yosys", "sta")):
                result["details"] = "Native execution requires LibreLane, OpenROAD, Yosys, and STA on PATH"
            else:
                available = True
        elif not docker:
            result["details"] = "Docker CLI is unavailable; install/start Docker and provision the pinned image separately"
        elif command([docker, "info", "--format", "{{.ServerVersion}}"], "docker.log"):
            result["details"] = "Docker engine is unavailable; start Docker Desktop"
        elif command([docker, "image", "inspect", IMAGE], "image.json"):
            result["details"] = f"Pinned image is absent; provision {IMAGE} separately (runner never downloads)"
        else:
            available = True
        if available:
            design_dir = str(output) if mode == "native" else "/work"
            entrypoint = ["python3", design_dir + "/flow-assets/clock_flow.py"] if profile == PROFILE else ["librelane"]
            entrypoint = ["env", f"NANOCHIP_PHYSICAL_CORES={cores}", f"_OPENLANE_MAX_CORES={cores}", *entrypoint]
            flow_command = [*entrypoint, "--manual-pdk", "--pdk-root", "/foss/pdks", "--pdk", "sky130A",
                            "--scl", "sky130_fd_sc_hd", "--jobs", str(cores), "--flow", profile, "--run-tag", "physical",
                            "--design-dir", design_dir, design_dir + "/config.json"]
            if resume_from is not None:
                from .clock_flow import STEP_ID
                flow_command.extend(["--from", STEP_ID, "--with-initial-state", design_dir + "/checkpoint/state.json"])
            if stop_at:
                flow_command.extend(["--to", stop_at])
            if mode == "native":
                for tool, flag in (("librelane", "--version"), ("openroad", "-version"), ("yosys", "-V")):
                    command([tool, flag], tool + "-version.log")
                args = flow_command
            else:
                name = "nanochip-physical-" + uuid.uuid4().hex[:12]
                active_container = name
                # Shell text contains only fixed strings, validated CPU integer, and fixed container paths.
                script = ("set -e; test \"$(readlink -f /foss/pdks/sky130A)\" = "
                          f"/foss/pdks/ciel/sky130/versions/{PDK_REVISION}/sky130A; "
                          "librelane --version; openroad -version; yosys -V; " + " ".join(flow_command))
                args = [docker, "run", "--rm", "--pull=never", "--network", "none", "--cpus", str(cores),
                        "--name", name, "--entrypoint", "/bin/bash", "-v", f"{output}:/work", IMAGE, "-lc", script]
            try:
                remaining = timeout_s - (time.monotonic() - started)
                code = command(args, "flow.log", max(0.01, remaining))
                result.update(status="completed" if code == 0 else "error", returncode=code)
                active_container = None
            except subprocess.TimeoutExpired:
                if mode == "docker":
                    command([docker, "rm", "-f", name], "timeout-cleanup.log")
                    active_container = None
                result.update(status="timeout", details="EDA process tree killed at the declared wall-time bound")
            remaining = timeout_s - (time.monotonic() - started)
            if remaining > 1 and any((output / "runs/physical").glob("*-openroad-stapostpnr/state_out.json")):
                result["coverage"] = run_coverage(output, min(120, remaining), mode=mode)
            result["checks"], result["stages"] = collect_checks(output, scope=scope)
            result["ok"] = result["status"] == "completed" and all(c["status"] == "pass" for c in result["checks"])
    except (OSError, ValueError, ContractError, subprocess.TimeoutExpired) as exc:
        result.update(status="error", details=str(exc))
    except KeyboardInterrupt:
        interrupted = True
        result.update(status="interrupted", ok=False,
                      details="Interrupted; partial artifacts retained without design acceptance")
        if active_container is not None:
            try:
                result["cleanup_returncode"] = command(
                    [docker, "rm", "-f", active_container], "interruption-cleanup.log", 15)
            except (OSError, subprocess.SubprocessError) as exc:
                result["cleanup_error"] = str(exc)
        try:
            result["checks"], result["stages"] = collect_checks(output, scope=scope)
        except (OSError, ValueError, TypeError) as exc:
            result["partial_check_error"] = str(exc)
    result.setdefault("checks", [])
    result["elapsed_s"] = time.monotonic() - started
    result["end_timestamp"] = datetime.now(timezone.utc).isoformat()
    result["artifacts"] = [asdict(Artifact.from_file(output, str(p.relative_to(output))))
                           for p in sorted(output.rglob("*")) if p.is_file() and not p.is_symlink()]
    _json(output / "receipt.json", result)
    if interrupted:
        raise KeyboardInterrupt
    return result


def run_physical(rtl: str | Path, output: str | Path, timeout_s: float = 900, cores: int = 1,
                 *, mode: str | None = None) -> dict:
    """Backward-compatible msh_deq adapter; use run_physical_design for other tops."""
    return run_physical_design({"msh_deq.v": rtl}, output, config=CONFIG, scope=SCOPE, boundary=BOUNDARY,
                               timeout_s=timeout_s, cores=cores, mode=mode)


class OpenRoadBackend:
    """Same candidate/receipt boundary as the functional Verilator backend."""

    def __init__(self, timeout_s: float = 900, cores: int = 1):
        self.timeout_s, self.cores = timeout_s, cores

    def evaluate(self, task, candidate) -> RunReceipt:
        candidate.validate_files()
        if candidate.task_id != task.task_id or candidate.task_digest != task.digest:
            raise ContractError("Candidate belongs to a different task specification")
        sources = [a for a in candidate.artifacts if a.path == "msh_deq.v"]
        if len(sources) != 1:
            raise ContractError("Physical backend requires manifested msh_deq.v")
        out = Path(candidate.root).parent / ("physical-" + uuid.uuid4().hex[:12])
        result = run_physical(sources[0].resolve(candidate.root), out, self.timeout_s, self.cores)
        if result["candidate_sha256"] != sources[0].sha256:
            raise ContractError("Physical execution did not use the candidate source")
        candidate.validate_files()
        execution = {"completed": "success", "unavailable": "not_run", "timeout": "timeout"}.get(result["status"], "error")
        postroute = result.get("stages", {}).get("openroad-stapostpnr", {}).get("metrics", {})
        metrics = {}
        for name, key, unit in (
            ("postroute_setup_wns", "timing__setup__wns", "ns"),
            ("postroute_hold_wns", "timing__hold__wns", "ns"),
            ("postroute_setup_worst_slack", "timing__setup__ws", "ns"),
            ("postroute_hold_worst_slack", "timing__hold__ws", "ns"),
            ("postroute_instance_area", "design__instance__area", "um2"),
        ):
            if _number(postroute.get(key)):
                metrics[name] = Metric(postroute[key], unit, SCOPE)
        artifacts = tuple(Artifact.from_file(out, a["path"]) for a in result["artifacts"])
        artifacts += (Artifact.from_file(out, "receipt.json"),)
        return RunReceipt(task.task_id, candidate.digest, "fresh", execution,
                          "LibreLane/OpenROAD", IMAGE,
                          checks=tuple(CheckResult(**c) for c in result["checks"]),
                          metrics=metrics, cost=Cost(result["elapsed_s"]), details=BOUNDARY,
                          output_root=str(out), output_artifacts=artifacts)
