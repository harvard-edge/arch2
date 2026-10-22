"""Run an unchanged argv and retain this container's cgroup resource counters."""

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def _read(root, name, *, integer=False):
    try:
        value = (root / name).read_text().strip()
        return {"status": "available", "value": int(value) if integer else value}
    except (OSError, ValueError) as exc:
        return {"status": "unavailable", "reason": str(exc)}


def snapshot(root=Path("/sys/fs/cgroup")):
    # Docker exposes this container's cgroup as the mount root in its cgroup
    # namespace. Never traverse /proc, the host hierarchy, or sibling cgroups.
    if (root / "cgroup.controllers").is_file():
        files = {
            name: _read(
                root,
                name,
                integer=name in ("memory.peak", "memory.current", "pids.peak"),
            )
            for name in (
                "memory.peak",
                "memory.current",
                "memory.max",
                "memory.events",
                "cpu.stat",
                "cpu.max",
                "pids.peak",
            )
        }
        peak = files["memory.peak"]
        return {
            "version": 2,
            "root": str(root),
            "files": files,
            "peak_memory_bytes": peak.get("value"),
            "peak_status": peak["status"],
        }
    peak = _read(root / "memory", "memory.max_usage_in_bytes", integer=True)
    return {
        "version": 1 if peak["status"] == "available" else None,
        "root": str(root),
        "files": {"memory/memory.max_usage_in_bytes": peak},
        "peak_memory_bytes": peak.get("value"),
        "peak_status": peak["status"],
    }


def run(command, output):
    started = time.monotonic()
    process = subprocess.Popen(command, start_new_session=True)
    forwarded = []
    previous = {}

    def forward(signum, frame):
        forwarded.append(signum)
        try:
            os.killpg(process.pid, signum)
        except ProcessLookupError:
            pass

    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        previous[signum] = signal.signal(signum, forward)
    try:
        code = process.wait()
        report = {
            "schema": "nanochip-container-resources/v1",
            "status": "captured",
            "child_returncode": code,
            "child_elapsed_s": time.monotonic() - started,
            "forwarded_signals": forwarded,
            "measurement": "own container cgroup, including supervisor and all descendants; final snapshot after child exit",
            "resources": snapshot(),
        }
        try:
            with Path(output).open("x", encoding="utf-8") as stream:
                json.dump(report, stream, indent=2, allow_nan=False)
                stream.write("\n")
        except (OSError, ValueError) as exc:
            print(f"Nanochip resource receipt unavailable: {exc}", file=sys.stderr)
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("provide a child command after --")
    code = run(command, args.output)
    if code < 0:
        signum = -code
        if signum not in (signal.SIGKILL, signal.SIGSTOP):
            signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)
        # Linux PID 1 can ignore a signal whose action was restored to default.
        return 128 + signum
    return code


if __name__ == "__main__":
    raise SystemExit(main())
