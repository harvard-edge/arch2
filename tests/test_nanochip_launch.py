"""Real host subprocesses exercise the Docker boundary without a real engine."""

import csv
import json
import os
from pathlib import Path
import sys
import signal
import shlex
import subprocess
import time

import pytest

from nanochip.laboratory import launch as launcher


@pytest.fixture
def fake_docker(tmp_path, monkeypatch):
    helper = tmp_path / "docker-test"
    helper.write_text(f"#!{sys.executable}\n" + r'''
import csv, json, os, pathlib, signal, subprocess, sys, time
args = sys.argv[1:]
if args[:2] == ['image', 'inspect']:
    labels = {} if os.environ.get('NANOCHIP_FAKE_INVALID') else {
        'org.nanochip.runtime': 'full-native-v1',
        'org.nanochip.physical-base': 'PHYSICAL_BASE'}
    print(json.dumps([{'Id': 'sha256:' + 'a' * 64, 'RepoDigests': ['example@sha256:' + 'a' * 64],
                      'Architecture': 'arm64', 'Os': 'linux', 'Size': 12345,
                      'Config': {'Labels': labels}}]))
elif args[0] == 'info':
    print(json.dumps({'Architecture':'aarch64','OSType':'linux','OperatingSystem':'test engine',
                      'KernelVersion':'test','NCPU':2,'MemTotal':4*1024**3,'ServerVersion':'test',
                      'HttpProxy':'private daemon configuration'}))
elif args[0] == 'run':
    fields = next(csv.reader([args[args.index('--mount') + 1]]))
    root = pathlib.Path(next(x.removeprefix('source=') for x in fields if x.startswith('source=')))
    environment = dict(args[index + 1].split('=', 1) for index, value in enumerate(args) if value == '--env')
    resource = pathlib.PurePosixPath(environment.get('NANOCHIP_RESOURCE_RECEIPT', '/work/container-resources.json'))
    resource_path = root.joinpath(*resource.relative_to('/work').parts)
    receipt_root = resource_path.parent
    (receipt_root / 'command-proof.json').write_text(json.dumps(args))
    if os.environ.get('NANOCHIP_FAKE_CAPTURE'):
        resource_path.write_text(json.dumps({
            'status':'captured', 'resources':{'peak_status':'available','peak_memory_bytes':123456}}))
    if os.environ.get('NANOCHIP_FAKE_WORKSPACE'):
        if 'init' in args:
            (root / 'course/labs').mkdir(parents=True)
            (root / 'course/labs/student.py').write_text('starter source')
        elif '--lab' in args:
            (receipt_root / 'student-file-seen.txt').write_text((root / 'course/labs/student.py').read_text())
    if args[-1] == 'slow':
        pathlib.Path(__file__).with_suffix('.pid').write_text(str(os.getpid()))
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
        (root / 'worker.pid').write_text(str(child.pid))
        def stop(*unused):
            child.terminate()
            child.wait(timeout=2)
            sys.exit(130 if unused[0] == signal.SIGINT else 0)
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, signal.SIG_IGN if os.environ.get('NANOCHIP_FAKE_IGNORE_INTERRUPT') else stop)
        time.sleep(60)
    else:
        print('offline test command completed')
elif args[0] == 'kill':
    os.kill(int(pathlib.Path(__file__).with_suffix('.pid').read_text()), signal.SIGINT)
elif args[:2] != ['rm', '-f']:
    sys.exit(2)
'''.replace("PHYSICAL_BASE", launcher.PHYSICAL_IMAGE), encoding="utf-8")
    helper.chmod(0o755)
    monkeypatch.setattr(launcher.shutil, "which", lambda _: str(helper))
    return helper


def test_cached_tag_is_resolved_and_only_output_is_mounted(tmp_path, fake_docker):
    output = tmp_path / "output, with spaces"
    receipt = launcher.launch(launcher.LaunchRequest(
        output, ("demo", "--output", "/work/run"), uid=501, gid=20, memory="8g"))
    assert receipt["ok"] and receipt["status"] == "completed"
    command = json.loads((output / "command-proof.json").read_text())
    assert command[-4:] == ["sha256:" + "a" * 64, "demo", "--output", "/work/run"]
    assert command[command.index("--network") + 1] == "none"
    assert command[command.index("--memory") + 1] == "8g"
    assert command[command.index("--user") + 1] == "501:20"
    assert command.count("--mount") == 1
    assert "--pull=never" in command
    assert command[command.index("--cgroupns") + 1] == "private"
    assert "NANOCHIP_CAPTURE_RESOURCES=1" in command
    assert "NANOCHIP_RESOURCE_RECEIPT=/work/container-resources.json" in command
    assert not any("docker.sock" in item for item in command)
    assert receipt["architecture_relationship"] == "same_architecture"
    assert receipt["resources"]["memory_limit_bytes"] == 8 * 1024**3
    assert receipt["resources"]["requested_limit_exceeds_engine_memory"]
    assert receipt["resources"]["memory_capacity_ceiling_bytes"] == 4 * 1024**3
    assert receipt["host"]["output_disk_free_bytes"] > 0
    assert "HttpProxy" not in receipt["engine"]
    assert receipt["timing"]["command_wait_s"] >= 0
    assert receipt["container_resources"]["status"] == "unavailable"
    assert json.loads((output / "launch.json").read_text())["image"]["id"] == "sha256:" + "a" * 64


def test_timeout_cleans_container_and_client_process_group(tmp_path, fake_docker):
    output = tmp_path / "timeout"
    receipt = launcher.launch(launcher.LaunchRequest(output, ("slow",), timeout_s=0.3))
    assert receipt["status"] == "timeout" and not receipt["ok"]
    assert receipt["cleanup"]["command"][-1] == receipt["container_name"]
    assert receipt["cleanup"]["command"][1:3] == ["rm", "-f"]
    worker = int((output / "worker.pid").read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(worker, 0)


def test_final_container_resource_receipt_is_retained(tmp_path, fake_docker, monkeypatch):
    monkeypatch.setenv("NANOCHIP_FAKE_CAPTURE", "1")
    receipt = launcher.launch(launcher.LaunchRequest(tmp_path / "captured", ("doctor",)))
    assert receipt["ok"]
    assert receipt["container_resources"]["status"] == "captured"
    assert receipt["container_resources"]["resources"]["peak_memory_bytes"] == 123456


def test_repeated_workspace_launches_preserve_student_files_and_separate_receipts(tmp_path, fake_docker, monkeypatch, capsys):
    monkeypatch.setenv("NANOCHIP_FAKE_CAPTURE", "1")
    monkeypatch.setenv("NANOCHIP_FAKE_WORKSPACE", "1")
    workspace = tmp_path / "student work, with spaces"
    workspace.mkdir()
    first_output = workspace / "launches/init"
    assert launcher.main(["--workspace", str(workspace), "--output", str(first_output), "--",
                          "course", "init", "/work/course"]) == 0
    first = json.loads(capsys.readouterr().out)
    original_receipt = (first_output / "launch.json").read_bytes()
    student = workspace / "course/labs/student.py"
    student.write_text("student-authored edited source\n")
    second_output = workspace / "launches/lab01"
    second = launcher.launch(launcher.LaunchRequest(second_output,
        ("course", "run", "--workspace", "/work/course", "--lab", "1"), workspace=workspace))
    assert first["ok"] and second["ok"]
    for result, output, relative in ((first, first_output, "init"), (second, second_output, "lab01")):
        command = json.loads((output / "command-proof.json").read_text())
        assert command.count("--mount") == 1
        mount = next(csv.reader([command[command.index("--mount") + 1]]))
        assert f"source={workspace}" in mount and "target=/work" in mount
        assert result["workspace_root"] == str(workspace)
        assert result["workspace_mapping"] == {"host": str(workspace), "container": "/work"}
        assert result["output_container_path"] == f"/work/launches/{relative}"
        assert f"NANOCHIP_RESOURCE_RECEIPT=/work/launches/{relative}/container-resources.json" in command
        assert result["container_resources"]["status"] == "captured"
        assert (output / "container-resources.json").is_file()
    assert (second_output / "student-file-seen.txt").read_text() == student.read_text()
    assert (first_output / "launch.json").read_bytes() == original_receipt
    assert not (workspace / "container-resources.json").exists()


@pytest.mark.parametrize("kind", ["outside", "symlink_escape"])
def test_workspace_rejects_output_outside_resolved_mount_before_writes(tmp_path, fake_docker, kind):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside"
    if kind == "symlink_escape":
        (workspace / "escape").symlink_to(outside, target_is_directory=True)
        output = workspace / "escape/new-receipt"
    else:
        output = outside / "new-receipt"
    with pytest.raises(ValueError, match="inside the workspace"):
        launcher.launch(launcher.LaunchRequest(output, ("doctor",), workspace=workspace))
    assert not outside.exists()
    assert not (workspace / "launch.json").exists()


def test_workspace_and_output_symlinks_resolve_to_one_contained_mount(tmp_path, fake_docker, monkeypatch):
    monkeypatch.setenv("NANOCHIP_FAKE_CAPTURE", "1")
    workspace = tmp_path / "real-workspace"
    receipts = workspace / "real-launches"
    receipts.mkdir(parents=True)
    alias = tmp_path / "workspace-alias"
    alias.symlink_to(workspace, target_is_directory=True)
    (workspace / "launches").symlink_to(receipts, target_is_directory=True)
    result = launcher.launch(launcher.LaunchRequest(alias / "launches/one", ("doctor",), workspace=alias))
    assert result["ok"]
    assert result["workspace_root"] == str(workspace)
    assert result["output_root"] == str(receipts / "one")
    assert result["container_resource_path"] == "/work/real-launches/one/container-resources.json"
    assert (receipts / "one/container-resources.json").is_file()


@pytest.mark.parametrize("kind", ["missing", "file"])
def test_workspace_must_exist_as_directory_before_any_output_write(tmp_path, fake_docker, kind):
    workspace = tmp_path / "workspace"
    if kind == "file":
        workspace.write_text("preserve workspace file")
    with pytest.raises((FileNotFoundError, ValueError)):
        launcher.launch(launcher.LaunchRequest(workspace / "launches/one", ("doctor",), workspace=workspace))
    if kind == "file":
        assert workspace.read_text() == "preserve workspace file"
    else:
        assert not workspace.exists()


@pytest.mark.parametrize("symlink", [False, True])
def test_existing_workspace_evidence_or_dangling_output_symlink_is_preserved(tmp_path, symlink):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    output = workspace / "existing"
    if symlink:
        output.symlink_to(workspace / "future", target_is_directory=True)
    else:
        output.mkdir()
        (output / "keep").write_text("original evidence")
    with pytest.raises(FileExistsError):
        launcher.launch(launcher.LaunchRequest(output, ("doctor",), workspace=workspace))
    if symlink:
        assert output.is_symlink() and not (workspace / "future").exists()
    else:
        assert (output / "keep").read_text() == "original evidence"
        assert not (output / "launch.json").exists()


@pytest.mark.parametrize("configured", [False, True])
def test_entrypoint_resource_destination_is_one_literal_argument(tmp_path, configured):
    recorder = tmp_path / "record.py"
    recorder.write_text("import json,sys; print(json.dumps(sys.argv[1:]))\n")
    source = Path(__file__).resolve().parents[1] / "nanochip/containers/full-entrypoint.sh"
    entry = tmp_path / "entry.sh"
    entry.write_text(source.read_text().replace("source /etc/profile >/dev/null", ":")
        .replace("/opt/nanochip-venv/bin/python", shlex.quote(sys.executable))
        .replace("/opt/nanochip-runtime/capture_resources.py", shlex.quote(str(recorder))))
    marker = tmp_path / "never-created"
    destination = f"/work/launches/$(touch {marker}) ; literal/container-resources.json"
    environment = dict(os.environ, NANOCHIP_CAPTURE_RESOURCES="1")
    environment.pop("NANOCHIP_RESOURCE_RECEIPT", None)
    if configured:
        environment["NANOCHIP_RESOURCE_RECEIPT"] = destination
    result = subprocess.run(["bash", str(entry), "course", "status", "--workspace", "/work/course"],
                            env=environment, text=True, capture_output=True, timeout=5)
    assert result.returncode == 0, result.stderr
    arguments = json.loads(result.stdout)
    assert arguments == [destination if configured else "/work/container-resources.json", "--",
        sys.executable, "-I", "-B", "-m", "nanochip.laboratory", "course", "status", "--workspace", "/work/course"]
    assert not marker.exists()


@pytest.mark.parametrize("ignore_interrupt,mode", [(False, "graceful"), (True, "forced")])
def test_interrupt_grace_and_unresponsive_fallback(tmp_path, fake_docker, monkeypatch, ignore_interrupt, mode):
    if ignore_interrupt:
        monkeypatch.setenv("NANOCHIP_FAKE_IGNORE_INTERRUPT", "1")
    output = tmp_path / "interrupt"
    output.mkdir()
    process = subprocess.Popen([str(fake_docker), "run", "--mount", launcher._mount(output), "slow"],
                               start_new_session=True)
    try:
        deadline = time.monotonic() + 3
        while not (output / "worker.pid").exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert (output / "worker.pid").exists()
        time.sleep(0.03)
        result = launcher._interrupt(process, str(fake_docker), "owned-test-container", grace_s=0.3)
        assert result["mode"] == mode
        assert result["graceful_interrupt"]["command"][-2:] == ["SIGINT", "owned-test-container"]
        assert process.poll() is not None
        if not ignore_interrupt:
            assert result["client_returncode"] == 130
        worker = int((output / "worker.pid").read_text())
        with pytest.raises(ProcessLookupError):
            os.kill(worker, 0)
    finally:
        if process.poll() is None:
            launcher._stop(process, str(fake_docker), "owned-test-container")


def test_unavailable_docker_retains_an_explicit_receipt(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher.shutil, "which", lambda _: None)
    output = tmp_path / "missing"
    receipt = launcher.launch(launcher.LaunchRequest(output, ("doctor",)))
    assert receipt["status"] == "unavailable" and not receipt["ok"]
    assert receipt["resources"]["memory"] == "7g"
    assert receipt["resources"]["memory_limit_bytes"] == 7 * 1024**3
    assert (output / "launch.json").is_file()


def test_cli_forwards_arguments_after_separator(tmp_path, fake_docker, capsys):
    output = tmp_path / "cli"
    assert launcher.main(["--output", str(output), "--cores", "1", "--memory", "4g",
                          "--timeout", "30", "--", "doctor"]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["inner_command"] == ["doctor"]
    assert receipt["resources"]["cores"] == 1
    assert receipt["resources"]["timeout_s"] == 30


@pytest.mark.parametrize("interface", ["api", "cli"])
def test_default_budget_reaches_docker_without_becoming_a_measured_peak(tmp_path, fake_docker, monkeypatch, capsys, interface):
    monkeypatch.setenv("NANOCHIP_FAKE_CAPTURE", "1")
    output = tmp_path / "default-budget"
    if interface == "api":
        receipt = launcher.launch(launcher.LaunchRequest(output, ("doctor",)))
    else:
        assert launcher.main(["--output", str(output), "--", "doctor"]) == 0
        receipt = json.loads(capsys.readouterr().out)
    command = json.loads((output / "command-proof.json").read_text())
    assert command[command.index("--memory") + 1] == "7g"
    assert receipt["resources"]["memory_limit_bytes"] == 7 * 1024**3
    assert receipt["resources"]["timeout_s"] == 21600
    assert receipt["resources"]["requested_limit_exceeds_engine_memory"]
    assert receipt["resources"]["memory_capacity_ceiling_bytes"] == 4 * 1024**3
    assert receipt["container_resources"]["resources"]["peak_memory_bytes"] == 123456


def test_cli_requires_inner_command_before_creating_output(tmp_path):
    output = tmp_path / "no-command"
    with pytest.raises(SystemExit) as error:
        launcher.main(["--output", str(output), "--"])
    assert error.value.code == 2
    assert not output.exists()


def test_unrelated_image_is_rejected_before_execution(tmp_path, fake_docker, monkeypatch):
    monkeypatch.setenv("NANOCHIP_FAKE_INVALID", "1")
    output = tmp_path / "invalid-image"
    receipt = launcher.launch(launcher.LaunchRequest(output, ("doctor",)))
    assert receipt["status"] == "error"
    assert "not a declared Nanochip" in receipt["details"]
    assert not (output / "command-proof.json").exists()


def test_existing_output_is_preserved(tmp_path):
    marker = tmp_path / "keep"
    marker.write_text("existing evidence")
    with pytest.raises(FileExistsError):
        launcher.launch(launcher.LaunchRequest(tmp_path, ("doctor",)))
    assert marker.read_text() == "existing evidence"


@pytest.mark.parametrize("option", [dict(cores=0), dict(cores=True), dict(memory="--privileged"),
                                   dict(timeout_s=float("inf")), dict(command="doctor")])
def test_invalid_controls_have_no_filesystem_effect(tmp_path, option):
    output = tmp_path / "invalid"
    values = dict(output=output, command=("doctor",))
    values.update(option)
    with pytest.raises(ValueError):
        launcher.launch(launcher.LaunchRequest(**values))
    assert not output.exists()
