"""Fresh copied-input Verilator execution for the complete teaching core."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time

PACKAGE = Path(__file__).resolve().parent
CORE = PACKAGE / "core.v"
BENCH = PACKAGE / "core_tb.cpp"


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def implementation_source(mul_bits: int = 1, scratch_words: int = 1024) -> str:
    if mul_bits not in (1, 2) or type(mul_bits) is not int:
        raise ValueError("Only one/two multiplier bits per cycle are implemented")
    if (
        type(scratch_words) is not int
        or scratch_words < 2
        or scratch_words & (scratch_words - 1)
    ):
        raise ValueError("Scratch capacity must be a power of two")
    source = CORE.read_text()
    source, mul_count = re.subn(
        r"parameter integer MUL_BITS = \d+",
        f"parameter integer MUL_BITS = {mul_bits}",
        source,
    )
    source, memory_count = re.subn(
        r"parameter integer SCRATCH_WORDS = \d+",
        f"parameter integer SCRATCH_WORDS = {scratch_words}",
        source,
    )
    if (mul_count, memory_count) != (1, 1):
        raise ValueError("RTL template parameters are ambiguous")
    return source


def _command(command, output, remaining):
    process = subprocess.Popen(
        command,
        cwd=output,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    try:
        log, _ = process.communicate(timeout=remaining)
        return process.returncode, log, False
    except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        log, _ = process.communicate()
        if isinstance(error, KeyboardInterrupt):
            (Path(output) / "interrupted-command.log").write_text(log)
            raise
        return process.returncode, log, True


def _build_command(tool, output, build_profile):
    """Keep the mapped netlist's large C++ units within a laptop build budget."""
    options = ["--output-groups", "0"] if build_profile == "mapped" else []
    optimization = "-O1" if build_profile == "mapped" else "-O3"
    return [
        tool,
        *options,
        "--cc",
        "--exe",
        "--build",
        "-j",
        "1",
        "-O3",
        "-CFLAGS",
        optimization,
        "--top-module",
        "nanochip_teaching_core",
        "-Wno-fatal",
        "--Mdir",
        str(output / "obj"),
        str(output / "core.v"),
        str(output / "core_tb.cpp"),
    ]


def run_rtl(
    source: str | Path,
    program: str | Path,
    image: str | Path,
    tables: str | Path,
    output: str | Path,
    *,
    bench: str | Path = BENCH,
    timeout_s: float = 180,
    max_cycles: int = 300_000_000,
    profiles: tuple[dict, ...] | None = None,
    build_profile: str = "rtl",
) -> dict:
    """Compile once and run fresh processes at each explicit memory/reset profile."""
    if (
        type(timeout_s) not in (float, int)
        or not math.isfinite(timeout_s)
        or timeout_s <= 0
    ):
        raise ValueError("Use a positive finite wall budget")
    if type(max_cycles) is not int or max_cycles <= 0:
        raise ValueError("Use a positive integer cycle budget")
    if build_profile not in ("rtl", "mapped"):
        raise ValueError("Use the rtl or mapped build profile")
    if profiles is None:
        profiles = ({"latency": 1, "stall_permille": 0, "reset_seed": 0, "jitter": 0},)
    if not profiles:
        raise ValueError("At least one explicit simulation profile is required")
    for profile in profiles:
        if set(profile) != {"latency", "stall_permille", "reset_seed", "jitter"} or any(
            type(v) is not int for v in profile.values()
        ):
            raise ValueError("Malformed memory/reset profile")
        if (
            profile["latency"] < 1
            or not 0 <= profile["stall_permille"] < 1000
            or profile["reset_seed"] < 0
            or profile["jitter"] < 0
        ):
            raise ValueError("Invalid memory/reset profile values")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    sources = {
        "core.v": Path(source),
        "core_tb.cpp": Path(bench),
        "program.bin": Path(program),
        "image.bin": Path(image),
        "tables.bin": Path(tables),
    }
    for name, path in sources.items():
        shutil.copyfile(path, output / name)
    result = {
        "schema": "nanochip-teaching-core-rtl/v0",
        "status": "unavailable",
        "ok": False,
        "inputs": [{"path": name, "sha256": _sha(output / name)} for name in sources],
        "runner_sha256": _sha(__file__),
        "commands": [],
        "profiles": [],
        "scope": "accelerator:nanochip_teaching_core",
        "physical_execution": False,
        "timeout_s": timeout_s,
        "max_cycles": max_cycles,
        "build_profile": build_profile,
    }
    tool = shutil.which("verilator")
    interrupted = None
    try:
        if tool is None:
            result["details"] = "Local Verilator is unavailable"
        else:
            version = subprocess.run(
                [tool, "--version"],
                text=True,
                capture_output=True,
                check=True,
                timeout=10,
            ).stdout.strip()
            result["tool_version"] = version
            (output / "version.log").write_text(version + "\n")
            command = _build_command(tool, output, build_profile)
            result["commands"].append(command)
            code, log, timed_out = _command(
                command, output, max(0.001, timeout_s - (time.monotonic() - started))
            )
            (output / "build.log").write_text(log)
            result["build"] = {"returncode": code, "timed_out": timed_out}
            if timed_out:
                result["status"] = "timeout"
            elif code:
                result["status"] = "error"
            else:
                result["status"] = "completed"
                for index, profile in enumerate(profiles):
                    name = f"profile-{index:02d}"
                    command = [
                        str(output / "obj/Vnanochip_teaching_core"),
                        str(output / "program.bin"),
                        str(output / "image.bin"),
                        str(output / "tables.bin"),
                        str(output / (name + ".bin")),
                        str(max_cycles),
                        *(
                            str(profile[k])
                            for k in (
                                "latency",
                                "stall_permille",
                                "reset_seed",
                                "jitter",
                            )
                        ),
                    ]
                    result["commands"].append(command)
                    code, log, timed_out = _command(
                        command,
                        output,
                        max(0.001, timeout_s - (time.monotonic() - started)),
                    )
                    (output / (name + ".log")).write_text(log)
                    record = {
                        "profile": profile,
                        "returncode": code,
                        "timed_out": timed_out,
                        "dump": name + ".bin",
                        "log": name + ".log",
                    }
                    markers = re.findall(r"^NANOCHIP_CORE_RESULT (.+)$", log, re.M)
                    if len(markers) == 1:
                        record["result"] = json.loads(markers[0])
                    result["profiles"].append(record)
                    if timed_out:
                        result["status"] = "timeout"
                        break
                    if code or record.get("result", {}).get("status") != "completed":
                        result["status"] = "error"
                        break
                result["ok"] = result["status"] == "completed" and len(
                    result["profiles"]
                ) == len(profiles)
    except KeyboardInterrupt as exc:
        interrupted = exc
        result.update(
            status="interrupted",
            ok=False,
            details="Tool process group stopped after keyboard interrupt",
        )
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        result.update(status="error", details=str(exc))
    if any(
        _sha(output / artifact["path"]) != artifact["sha256"]
        for artifact in result["inputs"]
    ):
        result.update(
            status="error", ok=False, details="Copied inputs changed during execution"
        )
    result["elapsed_s"] = time.monotonic() - started
    result["outputs"] = [
        {"path": str(p.relative_to(output)), "sha256": _sha(p)}
        for p in sorted(output.iterdir())
        if p.is_file()
    ]
    if (output / "obj/Vnanochip_teaching_core").is_file():
        result["outputs"].append(
            {
                "path": "obj/Vnanochip_teaching_core",
                "sha256": _sha(output / "obj/Vnanochip_teaching_core"),
            }
        )
    (output / "receipt.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    if interrupted is not None:
        raise interrupted
    return result
