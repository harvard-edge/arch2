"""Composite evidence checks use fixtures, never fabricated physical results."""

from dataclasses import replace
import json
from pathlib import Path
import shutil

import pytest

from nanochip.laboratory import design_experiment as experiment
from nanochip.laboratory.contracts import Action, Artifact, CheckResult, ContractError, RunReceipt, file_sha256
from nanochip.laboratory.design_changes import design_change_task


def candidate(tmp_path):
    task = design_change_task()
    task = replace(task, specification=dict(task.specification,
        physical_inputs={name:file_sha256(path) for name,path in experiment._physical_inputs().items()},
        budgets=dict(check_timeout=120, physical_timeout=900, cores=1)))
    item = experiment.PhysicalDesignMaterializer().materialize(task, Action("stream_quantized_row"), tmp_path)
    return task, item


@pytest.mark.parametrize("status, expected_execution, expected_check", [
    ("unavailable", "not_run", "not_run"),
    ("timeout", "timeout", "not_run"),
    ("build_failed", "error", "not_run"),
    ("check_failed", "success", "fail"),
])
def test_differential_failures_retain_execution_class_and_skip_physical(tmp_path, monkeypatch,
                                                                      status, expected_execution, expected_check):
    task, item = candidate(tmp_path)

    class FunctionalFixture:
        def __init__(self, *args): pass
        def evaluate(self, task, candidate):
            output = Path(candidate.root).parent / "fixture-functional"
            output.mkdir()
            shutil.copyfile(Path(candidate.root) / "msh_deq.v", output / "candidate.v")
            return RunReceipt(task.task_id, candidate.digest, "fresh", "success", "unit-test fixture", "1",
                checks=(CheckResult("dequant_vectors", "pass", "block:msh_deq"),),
                output_root=str(output), output_artifacts=(Artifact.from_file(output, "candidate.v"),))

    def differential_fixture(source, output, timeout):
        output.mkdir()
        result = dict(mode="fresh", source_sha256=file_sha256(source), reference_sha256=task.specification["source_sha256"],
            checker_sha256=task.specification["transformer_sha256"], status=status, ok=False,
            simulation=dict(returncode=1, timed_out=status == "timeout"), output_artifacts=[])
        (output / "receipt.json").write_text(json.dumps(result))
        return result

    def forbidden_physical(*args, **kwargs):
        pytest.fail("Physical flow must not run without completed passing differential checks")

    monkeypatch.setattr(experiment, "VerilatorBackend", FunctionalFixture)
    monkeypatch.setattr(experiment, "run_design_checks", differential_fixture)
    monkeypatch.setattr(experiment.flow, "OpenRoadBackend", forbidden_physical)
    receipt = experiment.FunctionalPhysicalBackend().evaluate(task, item)
    assert receipt.execution_status == expected_execution
    assert next(c for c in receipt.checks if c.name == "sequential_rtl_differential").status == expected_check
    assert json.loads((tmp_path / "execution-link.json").read_text())["physical_run"] is False


@pytest.mark.parametrize("name", list(experiment._physical_inputs()))
def test_physical_input_must_be_manifested_even_when_bytes_exist(tmp_path, name):
    task, item = candidate(tmp_path)
    missing = replace(item, artifacts=tuple(a for a in item.artifacts if a.path != name))
    assert (Path(missing.root) / name).exists()
    with pytest.raises(ContractError, match="manifested candidate"):
        experiment.FunctionalPhysicalBackend().evaluate(task, missing)


def fake_checkpoint(tmp_path):
    root = tmp_path / "fixture-checkpoint"
    root.mkdir()
    for name in experiment.CHECKPOINT_FILES:
        (root / name).write_text("unit-test fixture, not model weights")
    return root


class FixtureProposer:
    def __init__(self, root):
        self.root, self.predictions = root, []
    def propose(self, task, history, budget):
        self.predictions.append(dict(action="stream_quantized_row",
            checkpoint_sha256=file_sha256(self.root / "checkpoint.pt")))
        return Action("stream_quantized_row")


def test_unfinished_student_cannot_fall_back_or_claim_changed_source(tmp_path, monkeypatch):
    from nanochip.laboratory.exercises.student_design import transform
    monkeypatch.setattr(experiment, "design_proposer", FixtureProposer)
    result = experiment.run_design_experiment(fake_checkpoint(tmp_path), tmp_path / "run", transformer=transform)
    assert result["source_changed"] is False
    assert result["complete_design_eligible"] is False
    assert result["campaign"]["observations"][0]["status"] == "materialization_error"
    assert "NotImplementedError" in result["campaign"]["observations"][0]["details"]
    assert not list((tmp_path / "run").rglob("msh_deq.v"))
    task = json.loads((tmp_path / "run/task.json").read_text())
    assert set(task["specification"]["checkpoint_artifacts"]) == set(experiment.CHECKPOINT_FILES)
    required = {(r["name"], r["scope"]) for r in task["required_checks"]}
    assert {("electrical_constraints", "block:msh_deq"), ("postroute_antenna", "block:msh_deq"),
            ("rtl_netlist_correspondence", "block:msh_deq"), ("checked_gds", "accelerator:msh_chip_top")} <= required


@pytest.mark.parametrize("name", ["config.json", "tokenizer.json", "training.json"])
def test_checkpoint_semantics_cannot_change_after_task_binding(tmp_path, monkeypatch, name):
    def tampered_loader(root):
        (root / name).write_text("tampered semantic binding")
        return FixtureProposer(root)
    monkeypatch.setattr(experiment, "design_proposer", tampered_loader)
    with pytest.raises(ContractError, match="Checkpoint configuration"):
        experiment.run_design_experiment(fake_checkpoint(tmp_path), tmp_path / "run")
