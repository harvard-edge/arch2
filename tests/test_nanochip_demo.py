"""Composition contracts; fixtures do not claim real RTL or physical results."""

from dataclasses import replace
import json
from pathlib import Path
import shutil

import pytest

from nanochip.laboratory import demo
from nanochip.laboratory.contracts import Action, Artifact, CheckResult, ContractError, RunReceipt, file_sha256
from nanochip.laboratory.design_changes import DesignChangeMaterializer, design_change_task


def _candidate(tmp_path):
    task = design_change_task()
    task = replace(task, specification=dict(task.specification, check_timeout=30))
    return task, DesignChangeMaterializer().materialize(task, Action("stream_quantized_row"), tmp_path)


def _functional_fixture(monkeypatch, *, mismatched_source=False, numerical="pass"):
    class Backend:
        def __init__(self, timeout):
            pass

        def evaluate(self, task, candidate):
            root = Path(candidate.root).parent / "fixture-numerical"
            root.mkdir()
            shutil.copyfile(Path(candidate.root) / "msh_deq.v", root / "candidate.v")
            if mismatched_source:
                (root / "candidate.v").write_text("wrong RTL fixture")
            return RunReceipt(task.task_id, candidate.digest, "fresh", "success", "test fixture", "1",
                checks=(CheckResult("dequant_vectors", numerical, demo.BLOCK_SCOPE),),
                output_root=str(root), output_artifacts=(Artifact.from_file(root, "candidate.v"),))

    monkeypatch.setattr(demo, "VerilatorBackend", Backend)


def _differential_fixture(monkeypatch, task, *, status="passed", wrong_identity=False):
    def check(source, output, timeout):
        output.mkdir()
        result = dict(mode="fresh", source_sha256="0" * 64 if wrong_identity else file_sha256(source),
            reference_sha256=task.specification["source_sha256"],
            checker_sha256=task.specification["transformer_sha256"], status=status,
            ok=status == "passed", output_artifacts=[],
            simulation=dict(returncode=0 if status == "passed" else 1, timed_out=status == "timeout"))
        (output / "receipt.json").write_text(json.dumps(result))
        return result

    monkeypatch.setattr(demo.design_changes, "run_design_checks", check)


@pytest.mark.parametrize("status, execution, check", [
    ("passed", "success", "pass"),
    ("check_failed", "success", "fail"),
    ("timeout", "timeout", "not_run"),
    ("unavailable", "not_run", "not_run"),
    ("build_failed", "error", "not_run"),
])
def test_finite_adapter_retains_failures_and_never_runs_physical(tmp_path, monkeypatch, status, execution, check):
    task, candidate = _candidate(tmp_path)
    _functional_fixture(monkeypatch)
    _differential_fixture(monkeypatch, task, status=status)
    receipt = demo.FunctionalDesignBackend(30).evaluate(task, candidate)
    assert receipt.execution_status == execution
    assert receipt.checks[-1].status == check
    assert receipt.checks[-1].scope == demo.BLOCK_SCOPE
    assert not any(c.name == "gds_generated" for c in receipt.checks)
    for artifact in receipt.output_artifacts:
        artifact.validate(receipt.output_root)
    link = json.loads((tmp_path / "execution-link.json").read_text())
    assert link["physical_run"] is False
    assert link["source_sha256"] == link["functional_source_sha256"] == link["differential_source_sha256"]


@pytest.mark.parametrize("mismatch", ["numerical", "differential"])
def test_candidate_identity_mismatch_propagates(tmp_path, monkeypatch, mismatch):
    task, candidate = _candidate(tmp_path)
    _functional_fixture(monkeypatch, mismatched_source=mismatch == "numerical")
    _differential_fixture(monkeypatch, task, wrong_identity=mismatch == "differential")
    with pytest.raises(ContractError, match="different RTL|another source"):
        demo.FunctionalDesignBackend(30).evaluate(task, candidate)


def test_numerical_mismatch_is_preserved_even_if_differential_passes(tmp_path, monkeypatch):
    task, candidate = _candidate(tmp_path)
    _functional_fixture(monkeypatch, numerical="fail")
    _differential_fixture(monkeypatch, task)
    receipt = demo.FunctionalDesignBackend(30).evaluate(task, candidate)
    assert [(c.name, c.status) for c in receipt.checks] == [
        ("dequant_vectors", "fail"), ("sequential_rtl_differential", "pass")]


def _fake_checkpoint(tmp_path):
    root = tmp_path / "fixture-checkpoint"
    root.mkdir()
    for name in demo.CHECKPOINT_FILES:
        (root / name).write_text("fixture only, not model weights")
    return root


class _Proposer:
    def __init__(self, root):
        self.root, self.predictions = root, []

    def propose(self, task, history, budget):
        self.predictions.append(dict(action="retain_indexed_read",
            checkpoint_sha256=file_sha256(self.root / "checkpoint.pt")))
        return Action("retain_indexed_read")


def test_unfinished_student_is_visible_and_never_replaced(tmp_path, monkeypatch):
    from nanochip.laboratory.exercises.student_design import transform
    monkeypatch.setattr(demo.design_learning, "design_proposer", _Proposer)
    result = demo._functional_design(_fake_checkpoint(tmp_path), tmp_path / "run", transformer=transform, timeout=30)
    observation = result["campaign"]["observations"][0]
    assert observation["status"] == "materialization_error"
    assert "NotImplementedError" in observation["details"]
    assert result["complete_design_eligible"] is False
    assert result["predictions"][0]["action"] == "retain_indexed_read"
    assert not list((tmp_path / "run").rglob("msh_deq.v"))
    assert demo._completed(result, physical=False) is False


@pytest.mark.parametrize("name", demo.CHECKPOINT_FILES)
def test_loaded_checkpoint_semantics_are_frozen(tmp_path, monkeypatch, name):
    def tampering_loader(root):
        (root / name).write_text("tampered fixture")
        return _Proposer(root)
    monkeypatch.setattr(demo.design_learning, "design_proposer", tampering_loader)
    with pytest.raises(ContractError, match="checkpoint changed"):
        demo._functional_design(_fake_checkpoint(tmp_path), tmp_path / "run", transformer=None, timeout=30)


def test_completion_is_explicitly_scoped_and_gds_alone_never_means_closure():
    checks = [dict(name=name, scope=demo.BLOCK_SCOPE, status="pass")
              for name in ("dequant_vectors", "sequential_rtl_differential", "gds_generated")]
    checks.append(dict(name="checked_gds", scope=demo.CORE_SCOPE, status="unresolved"))
    result = dict(campaign=dict(observations=[dict(status="success", checks=checks)]))
    assert demo._completed(result, physical=False) is True
    assert demo._completed(result, physical=True) is False
    checks[0]["scope"] = demo.CORE_SCOPE
    assert demo._completed(result, physical=False) is False


def test_unfinished_training_cannot_claim_demo_completion():
    with pytest.raises(ContractError, match="partial training"):
        demo._require_updates(dict(steps_completed=299, parameters_changed=True), 300)


@pytest.mark.parametrize("status,scope,expected", [
    ("pass", "diagnostic:msh_deq", True), ("fail", "diagnostic:msh_deq", False),
    ("not_run", "diagnostic:msh_deq", False), ("pass", demo.BLOCK_SCOPE, False)])
def test_diagnostic_completion_requires_the_executed_scoped_request(status, scope, expected):
    result = dict(campaign=dict(observations=[dict(status="success", checks=[
        dict(name="diagnostic_request", scope=scope, status=status)])]))
    assert demo._diagnostic_completed(result) is expected
    result["campaign"]["observations"] = []
    assert demo._diagnostic_completed(result) is False


def test_model_serializer_drift_after_checkpoint_binding_fails(tmp_path, monkeypatch):
    original = demo.file_sha256
    changed = False

    def loader(root):
        nonlocal changed
        changed = True
        return _Proposer(root)

    def digest(path):
        if changed and Path(path).name == "design_learning.py":
            return "0" * 64
        return original(path)

    monkeypatch.setattr(demo.design_learning, "design_proposer", loader)
    monkeypatch.setattr(demo, "file_sha256", digest)
    with pytest.raises(ContractError, match="serializer changed"):
        demo._functional_design(_fake_checkpoint(tmp_path), tmp_path / "run", transformer=None, timeout=30)


def test_contract_failure_writes_stage_receipt_and_propagates(tmp_path, monkeypatch):
    def broken_collector(*args, **kwargs):
        raise ContractError("evidence identity mismatch fixture")
    monkeypatch.setattr(demo, "collect_corpus", broken_collector)
    with pytest.raises(ContractError, match="evidence identity"):
        demo.run_demo(tmp_path / "run")
    failure = json.loads((tmp_path / "run/failure.json").read_text())
    assert failure["status"] == "failed" and failure["stage"] == "collection"
    assert failure["error_type"] == "ContractError"
    assert not (tmp_path / "run/report.json").exists()


@pytest.mark.parametrize("kwargs", [dict(physical="yes"), dict(check_timeout=float("nan")),
    dict(check_timeout=True), dict(cores=0), dict(cores=True)])
def test_invalid_budgets_fail_before_output_creation(tmp_path, kwargs):
    with pytest.raises(ContractError):
        demo.run_demo(tmp_path / "run", **kwargs)
    assert not (tmp_path / "run").exists()


def _pipeline_fixture(monkeypatch, *, failed_check=False):
    """Minimal local composition fixtures, explicitly not retained evidence."""
    def emit(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))

    def collect(output, **kwargs):
        emit(output / "manifest.json", {"fixture": True})

    def learning(manifest, output):
        value = dict(saved_model_inference_record_id="fixture-row",
                     learning_effect=dict(held_out_accuracy_change=0.0))
        emit(output / "report.json", value)
        for name in ("base", "adapted"):
            emit(output / name / "checkpoint.pt", {"fixture": True})
        return value

    def diagnose(manifest, record, output, **kwargs):
        value = dict(predictions=[], campaign=dict(observations=[dict(status="success", checks=[
            dict(name="diagnostic_request", scope="diagnostic:msh_deq", status="pass")])]))
        emit(output / "diagnosis.json", value)
        return value

    def design_collection(output):
        emit(output / "manifest.json", {"fixture": True})
        return {}

    def design_training(manifest, output, **kwargs):
        value = dict(training=dict(steps_completed=360, parameters_changed=True))
        emit(output / "report.json", value)
        emit(output / "checkpoint/checkpoint.pt", {"fixture": True})
        return value

    def execution(checkpoint, output, **kwargs):
        checks = [dict(name=name, scope=demo.BLOCK_SCOPE,
                       status="fail" if failed_check and name == "dequant_vectors" else "pass")
                  for name in ("dequant_vectors", "sequential_rtl_differential")]
        value = dict(complete_design_eligible=False, predictions=[dict(action="retain_indexed_read")],
            campaign=dict(observations=[dict(status="success", checks=checks)]))
        emit(output / "design-experiment.json", value)
        (output / "attempts").mkdir()
        return value

    monkeypatch.setattr(demo, "collect_corpus", collect)
    monkeypatch.setattr(demo, "_learn_diagnostics", learning)
    monkeypatch.setattr(demo, "diagnose", diagnose)
    monkeypatch.setattr(demo.design_learning, "collect_design_examples", design_collection)
    monkeypatch.setattr(demo.design_learning, "train_design_proposer", design_training)
    return execution


@pytest.mark.parametrize("failed_check", [False, True])
def test_demo_reports_scoped_completion_and_retains_failed_checks(tmp_path, monkeypatch, failed_check):
    execution = _pipeline_fixture(monkeypatch, failed_check=failed_check)
    monkeypatch.setattr(demo, "_functional_design", execution)
    monkeypatch.setattr(demo, "run_design_experiment", lambda *a, **k: pytest.fail("Default must not start physical work"))
    report = demo.run_demo(tmp_path / "run")
    assert report["success"] is not failed_check
    assert report["status"] == ("engineering_failed" if failed_check else "completed")
    assert report["physical_requested"] is False
    assert report["design"]["complete_design_eligible"] is False
    assert report["design"]["selected_action"] == "retain_indexed_read"
    assert report["design"]["source_changed"] is False
    assert "A generated GDS" in (tmp_path / "run/report.md").read_text()
    for artifact in report["artifacts"].values():
        assert file_sha256(artifact["path"]) == artifact["sha256"]


def test_physical_mode_delegates_once_to_existing_exact_candidate_composition(tmp_path, monkeypatch):
    fixture = _pipeline_fixture(monkeypatch)
    calls = []
    sentinel_transformer = object()

    def execute(checkpoint, output, **kwargs):
        calls.append((checkpoint, kwargs))
        return fixture(checkpoint, output, **kwargs)

    monkeypatch.setattr(demo, "run_design_experiment", execute)
    monkeypatch.setattr(demo, "_functional_design", lambda *a, **k: pytest.fail("No earlier separate model action"))
    report = demo.run_demo(tmp_path / "run", physical=True, transformer=sentinel_transformer)
    assert len(calls) == 1
    assert calls[0][0] == tmp_path / "run/design/learning/checkpoint"
    assert calls[0][1]["transformer"] is sentinel_transformer
    # Fixture has no physical checks: delegated execution cannot imply closure.
    assert report["physical_requested"] is True and report["success"] is False
