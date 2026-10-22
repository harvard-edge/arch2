"""Real staged helper imports and source guards, without EDA execution."""

from dataclasses import asdict
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from nanochip.laboratory.physical import clock_flow
from nanochip.laboratory.contracts import Action, ContractError, file_sha256


ASSETS = Path(clock_flow.__file__).parent


def stage_assets(path):
    path.mkdir()
    for name in clock_flow.FLOW_FILES:
        shutil.copyfile(ASSETS / name, path / name)
    return path


def isolated(program, *arguments, cwd):
    # A deliberately contaminated PYTHONPATH must have no effect. -S also
    # removes site packages, proving these copied helpers need no installation.
    env = dict(os.environ, PYTHONPATH=str(ASSETS.parents[2]))
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", program, *map(str, arguments)],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_copied_helpers_import_in_isolation_and_keep_each_directory_identity(tmp_path):
    first, second = [stage_assets(tmp_path / name) for name in ("first", "second")]
    program = """
import importlib.util, json, pathlib, runpy, sys
assert importlib.util.find_spec("nanochip") is None
roots = [pathlib.Path(p).resolve() for p in sys.argv[1:]]
rows = []
for root in roots:
    flow = runpy.run_path(str(root / "clock_flow.py"))
    repair = flow["load_flow_helper"]("repair_flow")
    cells = flow["load_flow_helper"]("cell_repair")
    graph = flow["load_flow_helper"]("signal_graph")
    parser = flow["load_flow_helper"]("cell_models")
    magic = flow["load_flow_helper"]("magic_flow")
    klayout = flow["load_flow_helper"]("klayout_flow")
    assert repair.write_drive_table is cells.write_drive_table
    assert repair.check_signal_reachability is graph.check_signal_reachability
    assert cells.inspect_liberty is graph.inspect_liberty is parser.inspect_liberty
    for module in (repair, cells, graph, parser, magic, klayout):
        assert pathlib.Path(module.__file__).resolve().parent == root
    assert flow["load_flow_helper"]("repair_flow") is repair
    rows.append(repair)
assert rows[0] is not rows[1]
assert rows[0].__package__ != rows[1].__package__
assert not any(name == "nanochip" or name.startswith("nanochip.") for name in sys.modules)
print(json.dumps({"roots": [str(p) for p in roots], "packages": [r.__package__ for r in rows]}))
"""
    receipt = json.loads(isolated(program, first, second, cwd=tmp_path))
    assert receipt["roots"] == [str(first), str(second)]


@pytest.mark.parametrize("name", clock_flow.FLOW_FILES)
def test_bootstrap_rejects_each_missing_asset_before_import(tmp_path, name):
    root = stage_assets(tmp_path / "assets")
    isolated(
        """
import pathlib, runpy, sys
root = pathlib.Path(sys.argv[1])
flow = runpy.run_path(str(root / "clock_flow.py"))
(root / sys.argv[2]).unlink()
try:
    flow["load_flow_helper"]("repair_flow")
except ValueError as error:
    assert "physical flow assets" in str(error)
else:
    raise AssertionError("Missing staged asset was accepted")
""",
        root,
        name,
        cwd=tmp_path,
    )


@pytest.mark.parametrize("redirect", ["symlink", "directory"])
def test_bootstrap_rejects_redirected_parser_asset(tmp_path, redirect):
    root = stage_assets(tmp_path / "assets")
    target = root / "cell_models.py"
    contents = target.read_bytes()
    target.unlink()
    if redirect == "symlink":
        outside = tmp_path / "outside.py"
        outside.write_bytes(contents)
        target.symlink_to(outside)
    else:
        target.mkdir()
    isolated(
        """
import pathlib, runpy, sys
flow = runpy.run_path(str(pathlib.Path(sys.argv[1]) / "clock_flow.py"))
try:
    flow["load_flow_helper"]("repair_flow")
except ValueError as error:
    assert "physical flow assets" in str(error)
else:
    raise AssertionError("Redirected staged parser was accepted")
""",
        root,
        cwd=tmp_path,
    )


@pytest.mark.parametrize("name", clock_flow.FLOW_FILES)
@pytest.mark.parametrize("damage", ["modified", "missing"])
def test_public_materializer_rejects_damaged_frozen_flow_source(
    tmp_path, monkeypatch, name, damage
):
    from nanochip.laboratory.physical import teaching
    from nanochip.laboratory.teaching_core import backend

    task = teaching.make_physical_task()
    source_root = tmp_path / "copied-sources"
    frozen = task.specification["source_artifacts"]
    for relative, digest in frozen.items():
        source = backend.ROOT / relative
        assert file_sha256(source) == digest
        target = source_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    relative = "nanochip/laboratory/physical/" + name
    assert relative in frozen, "Activated flow asset is absent from the frozen task"
    target = source_root / relative
    if damage == "modified":
        target.write_bytes(target.read_bytes() + b"\n# changed test fixture\n")
    else:
        target.unlink()
    monkeypatch.setattr(backend, "ROOT", source_root)
    output = tmp_path / "never-materialized"
    with pytest.raises((ContractError, FileNotFoundError)):
        backend.TeachingCoreMaterializer().materialize(
            task, Action("serial_mul1"), output
        )
    assert not output.exists(), "Source rejection must precede fixture generation"


@pytest.fixture
def copied_producer(tmp_path, monkeypatch):
    """Use the actual adapter's copy path; no tool or Docker execution occurs."""
    from nanochip.laboratory.physical import flow, teaching

    task = teaching.make_physical_task()
    source = tmp_path / "core.v"
    source.write_text(
        "// constructed dispatch fixture, not hardware evidence\n"
        "module nanochip_teaching_core; endmodule\n"
    )
    monkeypatch.setattr(flow.shutil, "which", lambda _: None)
    output = tmp_path / "producer"
    producer = flow.run_physical_design(
        {"core.v": source},
        output,
        config=task.specification["physical"]["configuration"],
        scope=teaching.SCOPE,
        boundary="Source-provenance fixture only; no EDA acceptance",
        mode="docker",
    )
    assert producer["status"] == "unavailable" and not producer["ok"]
    workload = tmp_path / "workload"
    workload.mkdir()
    (workload / "task.json").write_text(json.dumps(asdict(task)))
    return output, workload, producer


def actual_artifacts(root):
    return {
        str(path.relative_to(root)): file_sha256(path)
        for path in root.rglob("*")
        if path.is_file()
    }


def test_adapter_copies_complete_task_bound_asset_bytes(copied_producer):
    from nanochip.laboratory.physical import correspondence

    root, workload, producer = copied_producer
    frozen = json.loads((workload / "task.json").read_text())["specification"][
        "source_artifacts"
    ]
    for record in producer["flow_assets"]:
        assert (
            file_sha256(root / record["path"])
            == record["sha256"]
            == frozen[record["source_path"]]
        )
    correspondence._physical_provenance(
        root, workload, producer, actual_artifacts(root)
    )


@pytest.mark.parametrize("name", clock_flow.FLOW_FILES)
@pytest.mark.parametrize("damage", ["modified", "missing"])
def test_provenance_rejects_damaged_asset_even_with_updated_producer_digest(
    copied_producer, name, damage
):
    from nanochip.laboratory.physical import correspondence

    root, workload, producer = copied_producer
    (record,) = [
        item
        for item in producer["flow_assets"]
        if item["path"] == "flow-assets/" + name
    ]
    target = root / record["path"]
    if damage == "modified":
        target.write_bytes(target.read_bytes() + b"\n# changed staged test fixture\n")
        # A producer cannot make changed source acceptable by rehashing itself;
        # the independently frozen task must still match.
        record["sha256"] = file_sha256(target)
    else:
        target.unlink()
    with pytest.raises(ContractError, match="flow asset"):
        correspondence._physical_provenance(
            root, workload, producer, actual_artifacts(root)
        )
