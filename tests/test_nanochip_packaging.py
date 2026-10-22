"""Exercise the installed artifact, including resources absent from Python imports."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest

from nanochip.laboratory.physical.clock_flow import FLOW_FILES


def _runtime_selector():
    path = (
        Path(__file__).resolve().parents[1]
        / "nanochip/containers/select_full_runtime.py"
    )
    spec = importlib.util.spec_from_file_location("nanochip_runtime_selector", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "architecture,machine,requirements,constraints",
    [
        ("arm64", "aarch64", "requirements-full.lock", "full-runtime-constraints.txt"),
        (
            "amd64",
            "x86_64",
            "requirements-full-amd64.lock",
            "full-runtime-constraints-amd64.txt",
        ),
    ],
)
def test_full_runtime_selects_verified_platform_locks(
    tmp_path, architecture, machine, requirements, constraints
):
    selector = _runtime_selector()
    source = Path(__file__).resolve().parents[1] / "nanochip/containers"
    locks = tmp_path / "locks"
    locks.mkdir()
    for name in (
        "requirements-full.lock",
        "requirements-full-amd64.lock",
        "full-runtime-constraints.txt",
        "full-runtime-constraints-amd64.txt",
    ):
        shutil.copyfile(source / name, locks / name)
    receipt = selector.select(tmp_path, architecture, machine)
    for effective, selected in (
        ("requirements-full.lock", requirements),
        ("full-runtime-constraints.txt", constraints),
    ):
        assert (tmp_path / effective).read_bytes() == (source / selected).read_bytes()
        assert (
            receipt["effective_files"][effective]["sha256"]
            == hashlib.sha256((source / selected).read_bytes()).hexdigest()
        )
    assert receipt["physical_base_index"] == selector.BASE_INDEX
    assert (
        receipt["physical_platform_image"] == selector.PLATFORMS[architecture]["image"]
    )
    assert json.loads((tmp_path / "platform.json").read_text()) == receipt


@pytest.mark.parametrize(
    "architecture,machine", [("", "aarch64"), ("armv7", "armv7l"), ("amd64", "aarch64")]
)
def test_full_runtime_rejects_unsupported_or_mismatched_platform(
    tmp_path, architecture, machine
):
    marker = tmp_path / "requirements-full.lock"
    marker.write_text("preserve existing lock")
    with pytest.raises(ValueError):
        _runtime_selector().select(tmp_path, architecture, machine)
    assert marker.read_text() == "preserve existing lock"
    assert not (tmp_path / "platform.json").exists()


def test_offline_wheel_and_isolated_console_script(tmp_path):
    if any(importlib.util.find_spec(name) is None for name in ("setuptools", "wheel")):
        pytest.skip("offline packaging check requires installed setuptools and wheel")
    source = Path(__file__).resolve().parents[1] / "nanochip"
    stage = tmp_path / "source"
    shutil.copytree(
        source,
        stage,
        ignore=shutil.ignore_patterns(
            "__pycache__",
            "*.pyc",
            "*.egg-info",
            "build",
            "dist",
            ".claude",
            ".git",
            "local-check",
        ),
    )
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    build = subprocess.run(
        [
            sys.executable,
            "-c",
            "from setuptools import build_meta; "
            f"build_meta.build_wheel({str(wheels)!r})",
        ],
        cwd=stage,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    (wheel,) = wheels.glob("*.whl")
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        if importlib.util.find_spec("tomllib") is not None:
            spec = importlib.util.spec_from_file_location(
                "nanochip_packaging_snapshot", stage / "containers/snapshot_runtime.py"
            )
            snapshot = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(snapshot)
            closure = snapshot.inventory(stage)
            package_files = {
                name.removeprefix("nanochip/")
                for name in names
                if name.startswith("nanochip/") and not name.endswith("/")
            }
            assert package_files == set(closure["wheel_files"])
            for name in closure["wheel_files"]:
                assert (
                    hashlib.sha256(archive.read(f"nanochip/{name}")).hexdigest()
                    == closure["files"][name]
                )
        manifest = json.loads(archive.read("nanochip/kpu/harness/manifest.json"))
        for name, digest in manifest["files"].items():
            assert (
                hashlib.sha256(archive.read(f"nanochip/kpu/{name}")).hexdigest()
                == digest
            )
        for name in FLOW_FILES:
            assert (
                archive.read(f"nanochip/laboratory/physical/{name}")
                == (source / "laboratory" / "physical" / name).read_bytes()
            )
        for path in (stage / "laboratory/physical").glob("*.tcl"):
            assert (
                archive.read(f"nanochip/laboratory/physical/{path.name}")
                == path.read_bytes()
            )
        for name in (
            "nanochip/laboratory/assets/dequant_tb.cpp",
            "nanochip/laboratory/physical/config.json",
            "nanochip/laboratory/physical/coverage.tcl",
            "nanochip/laboratory/physical/closure.tcl",
            "nanochip/laboratory/physical/signal_graph.py",
            "nanochip/laboratory/physical/cell_repair.py",
            "nanochip/laboratory/teaching_core/backend.py",
            "nanochip/laboratory/teaching_target/target.json",
            "nanochip/laboratory/teaching_target/memory_tb.sv",
            "nanochip/laboratory/teaching_core/core.v",
            "nanochip/laboratory/teaching_core/core_tb.cpp",
            "nanochip/laboratory/course/workspace.py",
            "nanochip/laboratory/course/README.md",
            "nanochip/laboratory/course/starters/__init__.py",
            "nanochip/laboratory/course/reference/__init__.py",
            "nanochip/laboratory/launch.py",
            "nanochip/trajectories/variants/msh_deq_bad_shift.v",
            "nanochip/kpu/rtl/msh_deq.v",
            "nanochip/kpu/LICENSE",
        ):
            assert name in names
        assert not any(
            part in name
            for name in names
            for part in (
                "__pycache__",
                ".claude",
                "PROJECT_PLAN",
                "CAPSTONE_PLAN",
                "book/",
                "nanochip/docs/",
                "local-check/",
                ".pt",
                ".gds",
                ".pdf",
            )
        )
        metadata = archive.read(
            next(name for name in names if name.endswith(".dist-info/METADATA"))
        ).decode()
        assert 'Requires-Dist: torch<3,>=2.6; extra == "learning"' in metadata
        assert 'Requires-Dist: numpy<3,>=1.26; extra == "learning"' in metadata

    venv = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True, timeout=60)
    bindir = venv / ("Scripts" if os.name == "nt" else "bin")
    python = bindir / ("python.exe" if os.name == "nt" else "python")
    console = bindir / ("nanochip.exe" if os.name == "nt" else "nanochip")
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in ("PYTHONPATH", "PYTHONHOME")
    }
    install = subprocess.run(
        [str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert install.returncode == 0, install.stdout + install.stderr
    result = subprocess.run(
        [str(console), "labs"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "9. Evaluate and improve the system" in result.stdout
    workspace = tmp_path / "course-workspace"
    course = subprocess.run(
        [str(console), "course", "init", str(workspace), "--mode", "student"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert course.returncode == 0, course.stdout + course.stderr
    assert (workspace / "README.md").is_file()
    assert any((workspace / "labs").glob("*.py"))
    check = subprocess.run(
        [
            str(python),
            "-I",
            "-c",
            "import importlib.util, importlib.metadata, nanochip; "
            "from nanochip.laboratory.adapters import starter_task; "
            "from nanochip.laboratory.context import specification_sources; "
            "from nanochip.laboratory.teaching_target.inventory import KPU, SNAPSHOT; "
            "from nanochip.laboratory.launch import LaunchRequest; "
            "assert importlib.util.find_spec('torch') is None; "
            "assert importlib.util.find_spec('numpy') is None; "
            "assert importlib.metadata.version('nanochip') == nanochip.__version__; "
            "assert starter_task().allowed_actions; assert specification_sources(); "
            "assert SNAPSHOT.is_file(); assert (KPU / 'rtl/msh_mem.v').is_file(); "
            f"assert {str(source.parent)!r} not in str(nanochip.__file__)",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert check.returncode == 0, check.stdout + check.stderr
