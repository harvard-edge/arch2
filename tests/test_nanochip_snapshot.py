"""Source-only snapshot closure tests: no Docker, training, or hardware tools."""
import importlib.util
import json
from pathlib import Path
import shutil

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "nanochip/containers/snapshot_runtime.py"


@pytest.fixture
def snapshot_tool():
    pytest.importorskip("tomllib")
    spec = importlib.util.spec_from_file_location("nanochip_snapshot_runtime", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "authored"
    files = {
        "pyproject.toml": '''[project]
name = "nanochip"
version = "0.1.0a0"
[tool.setuptools]
package-dir = {nanochip = "."}
packages = ["nanochip", "nanochip.laboratory", "nanochip.laboratory.physical", "nanochip.laboratory.teaching_core"]
[tool.setuptools.package-data]
"nanochip.laboratory.physical" = ["*.tcl"]
''',
        "__init__.py": "",
        "laboratory/__init__.py": "",
        "laboratory/physical/__init__.py": "",
        "laboratory/physical/signal_graph.py": "SCHEMA = 'graph/v1'\n",
        "laboratory/physical/signal_step.tcl": "puts repair\n",
        "laboratory/teaching_core/__init__.py": "",
        "laboratory/teaching_core/backend.py": "DEFAULT = {'flow': 'Classic'}\n",
        "containers/FullDockerfile": '''FROM example@sha256:pinned
COPY pyproject.toml __init__.py ./
COPY laboratory ./laboratory
COPY containers/entry.sh /entry.sh
''',
        "containers/FullDockerfile.dockerignore": "**/__pycache__\n",
        "containers/entry.sh": "#!/bin/sh\nexit 0\n",
        "containers/snapshot_runtime.py": SCRIPT.read_text(),
    }
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root


def test_snapshot_binds_python_tcl_profile_and_docker_inputs(snapshot_tool, source, tmp_path):
    (source / "book").mkdir()
    (source / "book/unrelated.qmd").write_text("unrelated fixture")
    (source / ".claude").mkdir()
    (source / ".claude/private.md").write_text("private fixture")
    output = tmp_path / "snapshot-root"
    manifest = snapshot_tool.create(source, output)
    frozen = output / "snapshot/nanochip"
    actual = snapshot_tool.verify(frozen, manifest)
    assert "laboratory/physical/signal_graph.py" in actual["wheel_files"]
    assert "laboratory/physical/signal_step.tcl" in actual["wheel_files"]
    assert "laboratory/teaching_core/backend.py" in actual["files"]
    assert "containers/entry.sh" in actual["files"]
    assert not (frozen / ".claude").exists() and not (frozen / "book").exists()
    assert json.loads(manifest.read_text()) == actual
    extra = frozen / "laboratory/physical/extra.cfg"
    extra.write_text("unmanifested COPY input")
    with pytest.raises(ValueError, match="unmanifested"):
        snapshot_tool.verify(frozen, manifest)


def test_new_tcl_assets_are_automatically_inventoried(snapshot_tool, source):
    path = source / "laboratory/physical/antenna_repair_step.tcl"
    before = snapshot_tool.inventory(source)
    path.write_text("puts authored-wrapper\n")
    after = snapshot_tool.inventory(source)
    assert path.relative_to(source).as_posix() not in before["files"]
    assert path.relative_to(source).as_posix() in after["wheel_files"]


def test_profile_change_and_nonempty_destination_are_rejected(snapshot_tool, source, tmp_path):
    output = tmp_path / "snapshot-root"
    manifest = snapshot_tool.create(source, output)
    with pytest.raises(FileExistsError):
        snapshot_tool.create(source, output)
    profile = output / "snapshot/nanochip/laboratory/teaching_core/backend.py"
    profile.write_text("DEFAULT = {'flow': 'Changed'}\n")
    with pytest.raises(ValueError, match="differs"):
        snapshot_tool.verify(output / "snapshot/nanochip", manifest)


def test_source_drift_preserves_partial_output_without_complete_manifest(snapshot_tool, source, tmp_path, monkeypatch):
    original = shutil.copy2
    changed = False
    def copy_and_change(src, dst):
        nonlocal changed
        result = original(src, dst)
        if not changed:
            changed = True
            (source / "laboratory/teaching_core/backend.py").write_text("CHANGED = True\n")
        return result
    monkeypatch.setattr(snapshot_tool.shutil, "copy2", copy_and_change)
    output = tmp_path / "partial"
    with pytest.raises(ValueError, match="changed"):
        snapshot_tool.create(source, output)
    assert output.exists() and not (output / "snapshot.json").exists()


@pytest.mark.parametrize("relative", [".claude/private.md", ".codex/private.md", ".gemini/private.md",
                                      "CLAUDE.md", "AGENTS.md", "GEMINI.md", "book/unrelated.qmd", "outputs/run.txt"])
def test_private_or_unrelated_docker_copy_input_is_refused(snapshot_tool, source, relative):
    path = source / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("private/unrelated fixture")
    recipe = source / "containers/FullDockerfile"
    recipe.write_text(recipe.read_text() + f"COPY {relative} /forbidden\n")
    with pytest.raises(ValueError, match="Unsafe|Private"):
        snapshot_tool.inventory(source)


def test_unlisted_package_and_uncontained_source_symlink_fail(snapshot_tool, source, tmp_path):
    extra = source / "laboratory/unlisted/module.py"
    extra.parent.mkdir()
    extra.write_text("unlisted namespace")
    with pytest.raises(ValueError, match="outside declared packages"):
        snapshot_tool.inventory(source)
    extra.unlink()
    outside = tmp_path / "outside.py"
    outside.write_text("external fixture")
    (source / "laboratory/physical/escape.py").symlink_to(outside)
    with pytest.raises(ValueError, match="contained"):
        snapshot_tool.inventory(source)


def test_current_runtime_inventory_covers_new_helpers_and_profile(snapshot_tool):
    source = SCRIPT.parents[1]
    manifest = snapshot_tool.inventory(source)
    for name in ("laboratory/physical/signal_graph.py", "laboratory/physical/cell_repair.py",
                 "laboratory/physical/cell_models.py", "laboratory/teaching_core/backend.py"):
        assert name in manifest["wheel_files"] and name in manifest["files"]
    for path in (source / "laboratory/physical").glob("*.tcl"):
        assert path.relative_to(source).as_posix() in manifest["wheel_files"]
