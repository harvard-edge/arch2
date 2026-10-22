"""Check a student mapper, then simulate the actual upstream memory interface."""

from __future__ import annotations

import importlib.util
import json
import math
import os
from pathlib import Path
import random
import re
import shutil
import signal
import subprocess
import tempfile
import time

from . import mapping, reference
from .inventory import KPU, PACKAGE, sha256


def check_mapping(mapper=mapping, instructor=reference) -> dict:
    """Exhaust all wrapper input addresses and lane masks; return first mismatch."""
    cases = 0
    for function, count in (("word_address", 1 << 14), ("byte_strobes", 1 << 4)):
        for value in range(count):
            expected = getattr(instructor, function)(value)
            try:
                actual = getattr(mapper, function)(value)
            except Exception as exc:
                return {
                    "status": "fail",
                    "function": function,
                    "input": value,
                    "expected": expected,
                    "error": str(exc),
                    "cases_checked": cases,
                }
            cases += 1
            if type(actual) is not int or actual != expected:
                return {
                    "status": "fail",
                    "function": function,
                    "input": value,
                    "expected": expected,
                    "actual": actual,
                    "cases_checked": cases,
                }
    return {
        "status": "pass",
        "cases_checked": cases,
        "scope": "XBUF input bit mapping, including aliases; not workload address legality",
    }


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _vectors(path: Path, mapper, instructor=reference, rng_seed: int = 7) -> dict:
    """Independent software scoreboard, with old-data read before byte writes."""
    memory = [None] * (1 << 9)
    rows = []
    comparisons = 0

    def append(we, wa, wd, mask, a, b, compare=True):
        nonlocal comparisons
        old_a, old_b = memory[mapper.word_address(a)], memory[mapper.word_address(b)]
        if compare and (old_a is None or old_b is None):
            raise ValueError("Exercise attempted to compare uninitialized data")
        if we:
            dest = mapper.word_address(wa)
            old = memory[dest]
            if old is None and mask != 0xF:
                raise ValueError("Partial write before initialization")
            memory[dest] = instructor.masked_write(
                old or 0, wd, mapper.byte_strobes(mask), 128
            )
        rows.append(
            f"{we:x} {wa:x} {wd:x} {mask:x} {a:x} {b:x} {int(compare):x} {(old_a or 0):x} {(old_b or 0):x}\n"
        )
        comparisons += int(compare)

    # Initialize every physical location through the wrapper's legal packed
    # buffer/word positions. No comparison uses an unwritten location.
    for word in range(len(memory)):
        logical = ((word >> 5) << 9) | (word & 0x1F)
        value = sum(((word + byte) & 0xFF) << (byte * 8) for byte in range(16))
        append(1, logical, value, 0xF, 0, 0, False)
    for address in range(1 << 14):
        # Exercise both copies and the discarded address bits.
        append(0, 0, 0, 0, address, address ^ ((1 << 14) - 1))
    # All masks, simultaneous reads/writes, address aliases, and deterministic
    # varied traffic. Compare the output before applying each write.
    rng = random.Random(rng_seed)
    for mask in range(1 << 4):
        address = rng.randrange(1 << 14)
        append(1, address, rng.getrandbits(128), mask, address, address ^ (1 << 13))
        append(0, 0, 0, 0, address, address)
    for _ in range(256):
        wa, a, b = (rng.randrange(1 << 14) for _ in range(3))
        append(rng.randrange(2), wa, rng.getrandbits(128), rng.randrange(1 << 4), a, b)
    path.write_text("".join(rows))
    return {
        "cycles": len(rows),
        "checked_cycles": comparisons,
        "rng_seed": rng_seed,
        "initialization": "explicit full writes before comparisons",
    }


def run_memory_check(output: str | Path | None = None, timeout_s: float = 60) -> dict:
    """Execute a bounded local Verilator check; optionally retain a new output dir.

    Copied sources, vectors, command logs, source hashes, and a JSON receipt
    bind the exercised mapper and RTL. No installation, network, or EDA
    physical flow runs. Temporary mode embeds the logs in its returned receipt.
    """
    if (
        type(timeout_s) not in (int, float)
        or not math.isfinite(timeout_s)
        or timeout_s <= 0
    ):
        raise ValueError("Use a positive finite wall-time budget")
    if output is None:
        with tempfile.TemporaryDirectory(prefix="nanochip-memory-check-") as tmp:
            return _run(Path(tmp), timeout_s, retained=False)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    return _run(output, timeout_s, retained=True)


def _run(output: Path, timeout_s: float, retained: bool) -> dict:
    started = time.monotonic()
    result = {
        "schema": "nanochip-memory-exercise/v1",
        "status": "unavailable",
        "ok": False,
        "scope": "behavioral SRAM contract and frozen XBUF wrapper; no core or physical claim",
        "retained": retained,
        "output_root": str(output) if retained else None,
        "timeout_s": timeout_s,
        "commands": [],
        "complete_core_ready": False,
    }
    originals = [
        KPU / "rtl/msh_mem.v",
        KPU / "harness/macros/msh_sram.v",
        PACKAGE / "memory_tb.sv",
        PACKAGE / "mapping.py",
        PACKAGE / "reference.py",
    ]
    for source in originals:
        shutil.copyfile(source, output / source.name)
    result["inputs"] = [
        {"path": p.name, "sha256": sha256(output / p.name)} for p in originals
    ]
    result["runner_sha256"] = sha256(Path(__file__))
    tool = shutil.which("verilator")
    try:
        mapper = _load(output / "mapping.py", "nanochip_checked_mapper")
        instructor = _load(output / "reference.py", "nanochip_checked_reference")
        result["mapping"] = check_mapping(mapper, instructor)
        if result["mapping"]["status"] != "pass":
            result["status"] = "fail"
        elif tool is None:
            result[
                "details"
            ] = "Local Verilator is unavailable; no behavioral pass claimed"
        else:
            result["vectors"] = _vectors(
                output / "xbuf_vectors.hex", mapper, instructor
            )
            result["inputs"].append(
                {
                    "path": "xbuf_vectors.hex",
                    "sha256": sha256(output / "xbuf_vectors.hex"),
                }
            )
            result["tool"] = subprocess.run(
                [tool, "--version"],
                capture_output=True,
                text=True,
                check=True,
                timeout=min(10, timeout_s),
            ).stdout.strip()
            commands = [
                [
                    tool,
                    "--binary",
                    "--timing",
                    "-Wno-fatal",
                    "--top-module",
                    "memory_tb",
                    "-j",
                    "1",
                    "--Mdir",
                    str(output / "obj"),
                    str(output / "memory_tb.sv"),
                    str(output / "msh_mem.v"),
                    str(output / "msh_sram.v"),
                ],
                [str(output / "obj/Vmemory_tb")],
            ]
            for name, command in zip(("compile", "simulate"), commands):
                result["commands"].append(command)
                remaining = timeout_s - (time.monotonic() - started)
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(command, timeout_s)
                # Kill the compiler's complete process group on timeout,
                # including any make/C++ children spawned by Verilator.
                process = subprocess.Popen(
                    command,
                    cwd=output,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                try:
                    log, _ = process.communicate(timeout=remaining)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    partial, _ = process.communicate()
                    (output / (name + ".log")).write_text(partial)
                    result[name] = {
                        "returncode": process.returncode,
                        "log": name + ".log",
                        "log_sha256": sha256(output / (name + ".log")),
                    }
                    if not retained:
                        result[name]["log_text"] = partial
                    raise
                (output / (name + ".log")).write_text(log)
                result[name] = {
                    "returncode": process.returncode,
                    "log": name + ".log",
                    "log_sha256": sha256(output / (name + ".log")),
                }
                if not retained:
                    result[name]["log_text"] = log
                if process.returncode:
                    result["status"] = "fail"
                    break
            else:
                markers = re.findall(
                    r"^NANOCHIP_MEMORY_PASS cycles=(\d+) comparisons=(\d+)$", log, re.M
                )
                expected = (
                    str(result["vectors"]["cycles"]),
                    str(result["vectors"]["checked_cycles"]),
                )
                result["status"] = "pass" if markers == [expected] else "unresolved"
                result["ok"] = result["status"] == "pass"
    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
    except (
        OSError,
        ValueError,
        SyntaxError,
        ImportError,
        AttributeError,
        subprocess.CalledProcessError,
    ) as exc:
        result.update(status="error", details=str(exc))
    result["elapsed_s"] = time.monotonic() - started
    if any(sha256(output / p["path"]) != p["sha256"] for p in result["inputs"]):
        result.update(
            status="error",
            ok=False,
            details="Checked source or vector changed during execution",
        )
    (output / "receipt.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    return result
