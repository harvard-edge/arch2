"""Real interruption must stop tools that create their own process sessions."""

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

from nanochip.laboratory.physical import flow


def _running(pid):
    result = subprocess.run(
        ["ps", "-p", str(pid), "-o", "stat="],
        capture_output=True, text=True, timeout=5,
    )
    return bool(result.stdout.strip()) and not result.stdout.strip().startswith("Z")


@pytest.mark.skipif(os.name != "posix", reason="Physical tools use POSIX process sessions")
@pytest.mark.parametrize("interruption", ["signal", "timeout"])
def test_execute_stops_child_and_detached_grandchild(tmp_path, interruption):
    child_pid = tmp_path / "child.pid"
    grandchild_pid = tmp_path / "grandchild.pid"
    grandchild_code = (
        "import os,time; from pathlib import Path; "
        f"Path({str(grandchild_pid)!r}).write_text(str(os.getpid())); time.sleep(60)"
    )
    child_code = (
        "import os,subprocess,sys,time; from pathlib import Path; "
        f"Path({str(child_pid)!r}).write_text(str(os.getpid())); "
        f"subprocess.Popen([sys.executable,'-c',{grandchild_code!r}],start_new_session=True); "
        "time.sleep(60)"
    )
    deadline = 1 if interruption == "timeout" else 15
    parent_code = (
        "import json,subprocess,sys; from nanochip.laboratory.physical.flow import _execute\n"
        f"with open({str(tmp_path / 'tool.log')!r},'w') as stream:\n"
        " try:\n"
        f"  _execute([sys.executable,'-c',{child_code!r}],stream,{deadline})\n"
        " except (KeyboardInterrupt,subprocess.TimeoutExpired) as error:\n"
        "  print(json.dumps({'propagated':type(error).__name__}),flush=True)\n"
        " else:\n"
        "  raise RuntimeError('Expected interruption did not propagate')\n"
    )
    parent = subprocess.Popen(
        [sys.executable, "-c", parent_code], cwd=Path(__file__).resolve().parents[1],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True,
    )
    owned = []
    try:
        until = time.monotonic() + 5
        while not grandchild_pid.exists() and parent.poll() is None and time.monotonic() < until:
            time.sleep(0.02)
        assert child_pid.exists() and grandchild_pid.exists(), "Probe children must actually execute"
        owned = [int(child_pid.read_text()), int(grandchild_pid.read_text())]
        if interruption == "signal":
            parent.send_signal(signal.SIGINT)
        stdout, stderr = parent.communicate(timeout=10)
        assert parent.returncode == 0, stderr
        expected = "KeyboardInterrupt" if interruption == "signal" else "TimeoutExpired"
        assert json.loads(stdout) == {"propagated": expected}
        until = time.monotonic() + 2
        while any(_running(pid) for pid in owned) and time.monotonic() < until:
            time.sleep(0.02)
        assert not any(_running(pid) for pid in owned), "Interrupted tools must not remain running"
    finally:
        for pid in owned:
            if _running(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        if parent.poll() is None:
            os.killpg(parent.pid, signal.SIGKILL)
        parent.communicate(timeout=5)


def test_interrupted_physical_flow_removes_its_container_and_retains_failure(tmp_path, monkeypatch):
    source = tmp_path / "core.v"
    source.write_text("module core(input clk); endmodule\n")
    commands = []

    def execute(args, stream, timeout, **kwargs):
        commands.append(args)
        if args[1:2] == ["run"]:
            stream.write("partial physical tool output\n")
            stream.flush()
            raise KeyboardInterrupt
        return 0

    monkeypatch.setattr(flow.shutil, "which", lambda name: "/test/docker")
    monkeypatch.setattr(flow, "_execute", execute)
    output = tmp_path / "run"
    with pytest.raises(KeyboardInterrupt):
        flow.run_physical_design({"core.v": source}, output,
                                 config={"DESIGN_NAME": "core", "VERILOG_FILES": ["dir::core.v"]},
                                 scope="test:core", boundary="constructed lifecycle test", mode="docker")
    launched = next(command for command in commands if command[1:2] == ["run"])
    name = launched[launched.index("--name") + 1]
    assert commands[-1] == ["/test/docker", "rm", "-f", name]
    receipt = json.loads((output / "receipt.json").read_text())
    assert receipt["status"] == "interrupted" and receipt["ok"] is False
    assert receipt["cleanup_returncode"] == 0 and receipt["elapsed_s"] > 0
    assert (output / "flow.log").read_text() == "partial physical tool output\n"
    assert "flow.log" in {item["path"] for item in receipt["artifacts"]}
    assert all(check["status"] != "pass" for check in receipt["checks"])


def test_interrupted_coverage_retains_partial_receipt_and_removes_container(tmp_path, monkeypatch):
    stage = tmp_path / "runs/physical/01-openroad-stapostpnr"
    stage.mkdir(parents=True)
    corner = "nom_tt_025C_1v80"
    (stage / corner).mkdir()
    (stage / corner / "_env_1.tcl").write_text("# constructed environment\n")
    inputs = {}
    for name in ("nl", "pnl", "sdc", "spef"):
        path = tmp_path / (name + ".input")
        path.write_text("constructed input\n")
        inputs[name] = str(path)
    inputs["spef"] = {"*": inputs["spef"]}
    (stage / "state_in.json").write_text(json.dumps(inputs))
    (stage / "state_out.json").write_text(json.dumps({"metrics": {}}))
    (stage / "config.json").write_text(json.dumps({
        "STA_CORNERS": [corner], "DESIGN_NAME": "core", "LIB": {"*": ["/foss/constructed.lib"]},
    }))
    launched, cleaned = [], []

    def execute(args, stream, timeout, **kwargs):
        launched.append(args)
        stream.write("partial timing output\n")
        stream.flush()
        raise KeyboardInterrupt

    def cleanup(args, **kwargs):
        cleaned.append(args)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(flow, "_execute", execute)
    monkeypatch.setattr(flow.subprocess, "run", cleanup)
    with pytest.raises(KeyboardInterrupt):
        flow.run_coverage(tmp_path, mode="docker")
    name = launched[0][launched[0].index("--name") + 1]
    assert cleaned == [["docker", "rm", "-f", name]]
    receipt = json.loads((tmp_path / "coverage-receipt.json").read_text())
    assert receipt["status"] == "interrupted"
    assert receipt["corners"][0]["status"] == "interrupted"
    assert receipt["corners"][0]["cleanup_returncode"] == 0
    assert receipt["commands"][-1] == cleaned[0]


@pytest.mark.skipif(os.name != "posix", reason="RTL tools use POSIX process sessions")
def test_rtl_interrupt_stops_compiler_group_and_retains_partial_receipt(tmp_path):
    """Exercise the actual runner with a deliberately sleeping compiler fixture."""
    tool_pid, child_pid = tmp_path / "tool.pid", tmp_path / "child.pid"
    child_code = ("import os,time; from pathlib import Path; "
                  f"Path({str(child_pid)!r}).write_text(str(os.getpid())); time.sleep(60)")
    tool = tmp_path / "verilator"
    tool.write_text(
        f"#!{sys.executable}\nimport os,subprocess,sys,time\nfrom pathlib import Path\n"
        "if '--version' in sys.argv:\n print('constructed lifecycle fixture'); raise SystemExit(0)\n"
        f"Path({str(tool_pid)!r}).write_text(str(os.getpid()))\n"
        f"subprocess.Popen([sys.executable,'-c',{child_code!r}])\n"
        "print('partial compiler output',flush=True)\ntime.sleep(60)\n"
    )
    tool.chmod(0o755)
    inputs = []
    for name in ("source.v", "program.bin", "image.bin", "tables.bin", "bench.cpp"):
        path = tmp_path / name
        path.write_text("constructed lifecycle fixture\n")
        inputs.append(path)
    output = tmp_path / "run"
    parent_code = (
        "from nanochip.laboratory.teaching_core.rtl import run_rtl\n"
        "try:\n"
        f" run_rtl({str(inputs[0])!r},{str(inputs[1])!r},{str(inputs[2])!r},{str(inputs[3])!r},"
        f"{str(output)!r},bench={str(inputs[4])!r},timeout_s=30)\n"
        "except KeyboardInterrupt:\n print('interrupted',flush=True)\n"
        "else:\n raise RuntimeError('Expected SIGINT')\n"
    )
    env = dict(os.environ, PATH=str(tmp_path) + os.pathsep + os.environ.get("PATH", ""))
    parent = subprocess.Popen([sys.executable, "-c", parent_code], env=env,
                              cwd=Path(__file__).resolve().parents[1], start_new_session=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    owned = []
    try:
        until = time.monotonic() + 5
        while not child_pid.exists() and parent.poll() is None and time.monotonic() < until:
            time.sleep(0.02)
        assert tool_pid.exists() and child_pid.exists()
        owned = [int(tool_pid.read_text()), int(child_pid.read_text())]
        parent.send_signal(signal.SIGINT)
        stdout, stderr = parent.communicate(timeout=10)
        assert parent.returncode == 0, stderr
        assert stdout.strip() == "interrupted"
        receipt = json.loads((output / "receipt.json").read_text())
        assert receipt["status"] == "interrupted" and receipt["ok"] is False
        assert receipt["profiles"] == []
        assert (output / "interrupted-command.log").read_text() == "partial compiler output\n"
        assert "interrupted-command.log" in {item["path"] for item in receipt["outputs"]}
        until = time.monotonic() + 2
        while any(_running(pid) for pid in owned) and time.monotonic() < until:
            time.sleep(0.02)
        assert not any(_running(pid) for pid in owned)
    finally:
        for pid in owned:
            if _running(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        if parent.poll() is None:
            os.killpg(parent.pid, signal.SIGKILL)
        parent.communicate(timeout=5)
