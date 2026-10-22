"""Resource supervision preserves command behavior without requiring Docker."""
import importlib.util
import json
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest


SCRIPT = (
    Path(__file__).resolve().parents[1] / "nanochip/containers/capture_resources.py"
)


@pytest.mark.parametrize("code", [0, 7])
def test_child_argv_output_and_exit_status_are_preserved(tmp_path, code):
    report = tmp_path / "resources.json"
    argument = "literal $(never-execute) ; with spaces"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(report),
            "--",
            sys.executable,
            "-c",
            "import sys; print(sys.argv[1]); sys.exit(int(sys.argv[2]))",
            argument,
            str(code),
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == code
    assert result.stdout == argument + "\n"
    receipt = json.loads(report.read_text())
    assert receipt["child_returncode"] == code
    assert receipt["child_elapsed_s"] >= 0
    assert receipt["resources"]["peak_status"] in ("available", "unavailable")


def test_interrupt_reaches_child_and_its_exit_status_is_retained(tmp_path):
    report, ready, interrupted = (
        tmp_path / name for name in ("resources.json", "ready", "interrupted")
    )
    child = (
        "import pathlib,signal,sys,time; "
        "signal.signal(signal.SIGINT, lambda *args: "
        "(pathlib.Path(sys.argv[2]).write_text('received'), sys.exit(23))); "
        "pathlib.Path(sys.argv[1]).write_text('ready'); time.sleep(30)"
    )
    process = subprocess.Popen(
        [
            sys.executable,
            str(SCRIPT),
            str(report),
            "--",
            sys.executable,
            "-c",
            child,
            str(ready),
            str(interrupted),
        ]
    )
    try:
        deadline = time.monotonic() + 5
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert ready.exists()
        process.send_signal(signal.SIGINT)
        assert process.wait(timeout=5) == 23
        assert interrupted.read_text() == "received"
        assert json.loads(report.read_text())["forwarded_signals"] == [signal.SIGINT]
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


@pytest.mark.parametrize("signum", [signal.SIGTERM, signal.SIGKILL])
def test_signal_terminated_child_preserves_signal_status(tmp_path, signum):
    report = tmp_path / "resources.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(report),
            "--",
            sys.executable,
            "-c",
            "import os,sys; os.kill(os.getpid(), int(sys.argv[1]))",
            str(signum),
        ],
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == -signum
    assert json.loads(report.read_text())["child_returncode"] == -signum


def test_unreadable_cgroup_never_invents_peak(tmp_path):
    spec = importlib.util.spec_from_file_location("nanochip_resource_capture", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    resource = module.snapshot(tmp_path)
    assert resource["peak_status"] == "unavailable"
    assert resource["peak_memory_bytes"] is None
    (tmp_path / "cgroup.controllers").write_text("cpu memory")
    (tmp_path / "memory.peak").write_text("123456")
    resource = module.snapshot(tmp_path)
    assert resource["version"] == 2
    assert resource["peak_status"] == "available"
    assert resource["peak_memory_bytes"] == 123456
