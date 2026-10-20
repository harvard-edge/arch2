"""Launch an already-cached full runtime; install, pull, and publish nothing.

The host needs Python's standard library and Docker. The full image runs tools
natively, sees one explicit workspace/output mount, and has no Docker socket or network.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import argparse
import csv
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import signal
import subprocess
import time
import uuid


FULL_IMAGE = "nanochip-local:full-0.1.0a0"
PHYSICAL_IMAGE = "hpretl/iic-osic-tools@sha256:ae380e2b0b96bd57b91f5864623ed488d00f78eaf58caf7f7d9d3754d315df38"
RUNTIME_LABEL = "full-native-v1"


def _architecture(value: str | None) -> str | None:
    return {"aarch64": "arm64", "arm64": "arm64", "x86_64": "amd64",
            "amd64": "amd64"}.get(value.lower(), value.lower()) if value else None


@dataclass(frozen=True)
class LaunchRequest:
    output: Path
    command: tuple[str, ...]
    image: str = FULL_IMAGE
    cores: int = 2
    memory: str = "7g"
    timeout_s: float = 21600
    uid: int | None = None
    gid: int | None = None
    workspace: Path | None = None


def _mount(path: Path) -> str:
    stream = io.StringIO()
    csv.writer(stream, lineterminator="").writerow(
        ("type=bind", f"source={path}", "target=/work"))
    return stream.getvalue()


def _validate(args: LaunchRequest):
    if type(args.cores) is not int or not 1 <= args.cores <= 8:
        raise ValueError("Use 1..8 CPU cores")
    if not isinstance(args.memory, str) or not re.fullmatch(r"[1-9][0-9]*[mg]", args.memory.lower()):
        raise ValueError("Memory must be a positive integer followed by m or g")
    if isinstance(args.timeout_s, bool) or not isinstance(args.timeout_s, (int, float)) or not math.isfinite(args.timeout_s) or args.timeout_s <= 0:
        raise ValueError("Use a positive finite launch timeout")
    if (not isinstance(args.command, (tuple, list)) or not args.command
            or any(not isinstance(item, str) or "\0" in item for item in args.command)):
        raise ValueError("command must be a nonempty sequence of Nanochip CLI arguments")
    if not isinstance(args.image, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/:@-]{0,511}", args.image):
        raise ValueError("Use a Docker image name or content identity")
    uid = args.uid if args.uid is not None else os.getuid()
    gid = args.gid if args.gid is not None else os.getgid()
    if any(type(value) is not int or value < 0 for value in (uid, gid)):
        raise ValueError("UID and GID must be nonnegative integers")
    requested_output = Path(args.output).expanduser()
    output = requested_output.resolve()
    if args.workspace is None:
        workspace = output
    else:
        workspace = Path(args.workspace).expanduser().resolve(strict=True)
        if not workspace.is_dir():
            raise ValueError("Workspace must be an existing directory")
        if not output.is_relative_to(workspace):
            raise ValueError("Output receipt directory must resolve inside the workspace")
    if requested_output.exists() or requested_output.is_symlink():
        raise FileExistsError(f"Output evidence already exists: {requested_output}")
    return output, workspace, uid, gid


def _stop(process, docker: str, name: str) -> dict:
    """Remove our named container, then reap the host client process group."""
    cleanup = {"command": [docker, "rm", "-f", name]}
    try:
        stopped = subprocess.run(cleanup["command"], capture_output=True, text=True, timeout=15)
        cleanup.update(returncode=stopped.returncode, stdout=stopped.stdout, stderr=stopped.stderr)
    except (OSError, subprocess.TimeoutExpired) as exc:
        cleanup["error"] = str(exc)
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=3)
    return cleanup


def _interrupt(process, docker: str, name: str, *, grace_s=5) -> dict:
    """Give only host Ctrl-C a bounded chance to flush inner receipts."""
    started = time.monotonic()
    graceful = {"command": [docker, "kill", "--signal", "SIGINT", name],
                "grace_limit_s": grace_s}
    try:
        sent = subprocess.run(graceful["command"], capture_output=True, text=True,
                              timeout=min(2, grace_s))
        graceful.update(returncode=sent.returncode, stdout=sent.stdout, stderr=sent.stderr)
        if sent.returncode == 0:
            process.wait(timeout=max(0, grace_s - (time.monotonic() - started)))
            graceful["elapsed_s"] = time.monotonic() - started
            return {"mode": "graceful", "graceful_interrupt": graceful,
                    "client_returncode": process.returncode, "container_auto_remove": True}
    except (OSError, subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
        graceful["error"] = str(exc)
    graceful["elapsed_s"] = time.monotonic() - started
    cleanup = _stop(process, docker, name)
    cleanup.update(mode="forced", graceful_interrupt=graceful)
    return cleanup


def launch(args: LaunchRequest) -> dict:
    """Run CLI arguments in a cached full image and retain a host receipt.

    The caller supplies inner CLI arguments, including paths beneath ``/work``;
    for example ``("demo", "--output", "/work/run", "--physical")``. The host
    ``output`` is a new receipt directory. With an existing ``workspace``, only
    that workspace is mounted and output must resolve inside it; otherwise the
    new output directory itself is mounted. Inner course files can therefore
    persist across launches while every launch keeps fresh receipts.
    An ``ok`` receipt means the command exited zero, not physical acceptance.
    """
    output, workspace, uid, gid = _validate(args)
    output.mkdir(parents=True, exist_ok=False)
    container_output = PurePosixPath("/work").joinpath(*output.relative_to(workspace).parts)
    container_resource = str(container_output / "container-resources.json")
    started = time.monotonic()
    result = dict(schema="nanochip-launch/v1", status="unavailable", ok=False,
                  requested_image=args.image, output_root=str(output),
                  workspace_root=str(workspace),
                  workspace_mapping=dict(host=str(workspace), container="/work"),
                  output_container_path=str(container_output),
                  container_resource_path=container_resource,
                  inner_command=list(args.command),
                  resources=dict(cores=args.cores, memory=args.memory.lower(), uid=uid, gid=gid,
                                 network="none", timeout_s=args.timeout_s),
                  start_timestamp=datetime.now(timezone.utc).isoformat())
    disk = shutil.disk_usage(output)
    memory_bytes = int(args.memory[:-1]) * (1024 ** (3 if args.memory[-1].lower() == "g" else 2))
    result["host"] = dict(system=platform.system(), release=platform.release(),
                          machine=platform.machine(), python=platform.python_version(),
                          output_disk_total_bytes=disk.total, output_disk_free_bytes=disk.free)
    result["resources"]["memory_limit_bytes"] = memory_bytes
    result["timing"] = {}
    docker = shutil.which("docker")
    process = None
    name = "nanochip-full-" + uuid.uuid4().hex[:12]
    try:
        if docker is None:
            result["details"] = "Docker CLI is unavailable; the launcher installs nothing"
        else:
            inspection_started = time.monotonic()
            inspect = subprocess.run([docker, "image", "inspect", args.image],
                                     capture_output=True, text=True, timeout=30)
            result["timing"]["image_inspect_s"] = time.monotonic() - inspection_started
            (output / "image-inspect.log").write_text(inspect.stderr, encoding="utf-8")
            if inspect.returncode:
                result["details"] = "Docker engine or cached image unavailable; the launcher never pulls"
                result["inspect_returncode"] = inspect.returncode
            else:
                metadata, = json.loads(inspect.stdout)
                identity = metadata["Id"]
                labels = metadata.get("Config", {}).get("Labels") or {}
                if not re.fullmatch(r"sha256:[0-9a-f]{64}", identity):
                    raise ValueError("Docker did not return an immutable image identity")
                if (labels.get("org.nanochip.runtime") != RUNTIME_LABEL
                        or labels.get("org.nanochip.physical-base") != PHYSICAL_IMAGE):
                    raise ValueError("Image is not a declared Nanochip full native runtime")
                result["image"] = dict(id=identity, repo_digests=metadata.get("RepoDigests", []),
                                       architecture=metadata.get("Architecture"), os=metadata.get("Os"),
                                       inspect_size_bytes=metadata.get("Size"),
                                       runtime=RUNTIME_LABEL, physical_base=PHYSICAL_IMAGE)
                inspection_started = time.monotonic()
                info = subprocess.run([docker, "info", "--format", "{{json .}}"],
                                      capture_output=True, text=True, timeout=15)
                result["timing"]["engine_inspect_s"] = time.monotonic() - inspection_started
                if info.returncode == 0:
                    engine = json.loads(info.stdout)
                    # Do not retain daemon proxies, account settings, or host socket paths.
                    result["engine"] = {key: engine.get(key) for key in (
                        "Architecture", "OSType", "OperatingSystem", "KernelVersion",
                        "NCPU", "MemTotal", "ServerVersion")}
                    image_arch = _architecture(metadata.get("Architecture"))
                    engine_arch = _architecture(engine.get("Architecture"))
                    result["architecture_relationship"] = (
                        "same_architecture" if image_arch == engine_arch else "different_architecture"
                    ) if image_arch and engine_arch else "unknown"
                    capacity = engine.get("MemTotal")
                    if isinstance(capacity, int) and capacity > 0:
                        result["resources"].update(engine_memory_bytes=capacity,
                            memory_capacity_ceiling_bytes=min(memory_bytes, capacity),
                            requested_limit_exceeds_engine_memory=memory_bytes > capacity)
                else:
                    result["engine"] = dict(status="unavailable", details=info.stderr.strip())
                    result["architecture_relationship"] = "unknown"
                (output / "image.json").write_text(json.dumps(result["image"], indent=2) + "\n", encoding="utf-8")
                command = [docker, "run", "--rm", "--pull=never", "--network", "none",
                           "--cgroupns", "private",
                           "--cpus", str(args.cores), "--memory", args.memory.lower(),
                           "--user", f"{uid}:{gid}", "--name", name,
                           "--workdir", "/work", "--mount", _mount(workspace),
                           "--env", f"NANOCHIP_RUNTIME_IMAGE_ID={identity}",
                           "--env", "NANOCHIP_CAPTURE_RESOURCES=1",
                           "--env", f"NANOCHIP_RESOURCE_RECEIPT={container_resource}",
                           identity, *args.command]
                result.update(command=command, container_name=name)
                with (output / "container.log").open("xb") as stream:
                    process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                               start_new_session=True)
                    process_started = time.monotonic()
                    try:
                        code = process.wait(timeout=args.timeout_s)
                        result["timing"]["command_wait_s"] = time.monotonic() - process_started
                        result.update(status="completed" if code == 0 else "error", ok=code == 0,
                                      returncode=code)
                    except subprocess.TimeoutExpired:
                        result["timing"]["command_wait_s"] = time.monotonic() - process_started
                        result.update(status="timeout", details="Declared command wall-time bound reached")
                        result["cleanup"] = _stop(process, docker, name)
                    except BaseException as exc:
                        result["timing"]["command_wait_s"] = time.monotonic() - process_started
                        result.update(status="interrupted", details="Host caller interrupted the command")
                        result["cleanup"] = (_interrupt(process, docker, name)
                                             if isinstance(exc, KeyboardInterrupt)
                                             else _stop(process, docker, name))
                        raise
    except (OSError, ValueError, TypeError, KeyError, subprocess.TimeoutExpired) as exc:
        result.update(status="error", details=str(exc))
    finally:
        if process is not None and process.poll() is None:
            result["cleanup"] = _stop(process, docker, name)
        resource_path = output / "container-resources.json"
        try:
            result["container_resources"] = json.loads(resource_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            result["container_resources"] = dict(status="unavailable", reason=str(exc),
                details="No final cgroup receipt; older images or killed supervisors may not retain one")
        result["elapsed_s"] = time.monotonic() - started
        result["end_timestamp"] = datetime.now(timezone.utc).isoformat()
        with (output / "launch.json").open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
            stream.write("\n")
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new receipt directory; must resolve inside --workspace if given")
    parser.add_argument("--workspace", type=Path, help="existing persistent directory to mount at /work")
    parser.add_argument("--image", default=FULL_IMAGE, help="already-cached full image; never pulled")
    parser.add_argument("--cores", type=int, default=2)
    parser.add_argument("--memory", default="7g", help="Docker memory cap; default 7g accommodates the observed isolated LEF run, not a proven minimum or final-profile success")
    parser.add_argument("--timeout", type=float, default=21600, help="outer wall budget in seconds; provisional allowance, not a runtime promise")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Nanochip arguments after --")
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("provide Nanochip CLI arguments after --")
    try:
        result = launch(LaunchRequest(args.output, tuple(command), image=args.image,
                                      cores=args.cores, memory=args.memory, timeout_s=args.timeout,
                                      workspace=args.workspace))
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result["ok"] else 1
