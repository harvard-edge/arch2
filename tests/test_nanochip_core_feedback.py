"""Teaching-fault provenance and evidence-dependent control, without fake RTL claims."""

from dataclasses import asdict, replace
import json
import struct
from pathlib import Path

import pytest

from nanochip.laboratory.contracts import (
    Action, Artifact, Budget, Candidate, CheckResult, ContractError, Observation, RunReceipt, file_sha256,
)
from nanochip.laboratory.exercises import core_feedback as exercise


def observed(*, status="success", check_status="fail", scope=exercise.SCOPE, mode="fresh", action=exercise.FAULT):
    check = CheckResult("exact_integer_logits", check_status, scope)
    receipt = RunReceipt("fixture", "fixture", mode, status, "constructed policy fixture", "1", checks=(check,))
    return Observation(Action(action), "fixture", "fixture", status, (check,), False, receipt)


def test_visible_failure_changes_action_but_equal_turn_count_without_evidence_does_not():
    policy, budget = exercise.CoreFeedbackPolicy(), Budget(3, 2)
    assert policy.propose(None, (), budget) == Action(exercise.FAULT)
    history = (observed(),)
    assert policy.propose(None, history, budget) == Action(exercise.REPAIR)
    assert exercise.HiddenFeedbackPolicy().propose(None, history, budget) is None


@pytest.mark.parametrize("fields", [dict(status="error"), dict(status="timeout"), dict(status="not_run"),
    dict(check_status="pass"), dict(check_status="unresolved"), dict(check_status="not_run"),
    dict(scope="block:msh_deq"), dict(mode="cached"), dict(mode="fixture"), dict(action=exercise.REPAIR)])
def test_nonpassing_execution_wrong_scope_or_unresolved_checks_never_trigger_restoration(fields):
    assert exercise.CoreFeedbackPolicy().propose(None, (observed(**fields),), Budget(2, 1)) is None


def task():
    base = exercise.make_task(seed=7, tokens=[1])
    source = Path(exercise.__file__).resolve()
    return replace(base, allowed_actions=exercise.ACTIONS,
        specification=dict(base.specification, source_artifacts=dict(base.specification["source_artifacts"],
            **{str(source.relative_to(exercise.ROOT)): file_sha256(source)})))


class FixtureCoreMaterializer:
    """Only a composition fixture. No tool or usable core is produced here."""

    def materialize(self, task, action, workspace):
        assert task.allowed_actions == exercise.CORE_ACTIONS
        assert action == Action("serial_mul2")
        root = workspace / "candidate"
        root.mkdir(parents=True)
        (root / "core.v").write_text("fixture RTL text, not executable\n" + exercise.ANCHOR + "\n")
        (root / "task.json").write_text(json.dumps(asdict(task)))
        (root / "reference").mkdir()
        header = [0] * 64
        header[17], header[19], header[25] = 16, 1, struct.calcsize("<64I")
        header[26], header[27] = struct.calcsize("<64I") + 64, struct.calcsize("<64I") + 68
        (root / "reference/image.bin").write_bytes(struct.pack("<64I", *header) + bytes(72))
        (root / "program.json").write_text(json.dumps(dict(data_base=1 << 20)))
        return Candidate(action.name, task.task_id, str(root), action,
            tuple(Artifact.from_file(root, str(path.relative_to(root))) for path in sorted(root.rglob("*"))
                  if path.is_file()), task_digest=task.digest)


@pytest.mark.parametrize("action", exercise.ACTIONS)
def test_materializer_records_explicit_mapping_and_private_single_site_mutation(tmp_path, monkeypatch, action):
    monkeypatch.setattr(exercise, "TeachingCoreMaterializer", FixtureCoreMaterializer)
    item = exercise.CoreFaultMaterializer().materialize(task(), Action(action), tmp_path)
    item.validate_files()
    assert item.action == Action(action) and item.task_digest == task().digest
    root = Path(item.root)
    source = (root / "core.v").read_text()
    assert ("store_value ^" in source) is (action == exercise.FAULT)
    assert (root / "reference-core.v").read_text().count(exercise.ANCHOR) == 1
    assert json.loads((root / "task.json").read_text())["allowed_actions"] == list(exercise.ACTIONS)
    assert json.loads((root / "canonical-materialization-task.json").read_text())["allowed_actions"] == list(exercise.CORE_ACTIONS)
    provenance = json.loads((root / "teaching-transformation.json").read_text())
    assert provenance["canonical_action"] == "serial_mul2"
    assert "author-constructed" in provenance["provenance"]
    assert "no model checkpoint" in provenance["policy"]
    assert bool((root / "change.diff").read_text()) is (action == exercise.FAULT)


def test_unknown_teaching_action_has_no_reference_fallback(tmp_path):
    with pytest.raises(ContractError, match="two declared teaching actions"):
        exercise.CoreFaultMaterializer().materialize(task(), Action("invented_repair"), tmp_path)
    assert not list(tmp_path.iterdir())


def test_fault_transformation_source_is_frozen_before_materialization(tmp_path):
    frozen = task()
    relative = str(Path(exercise.__file__).resolve().relative_to(exercise.ROOT))
    frozen = replace(frozen, specification=dict(frozen.specification,
        source_artifacts=dict(frozen.specification["source_artifacts"], **{relative: "0" * 64})))
    with pytest.raises(ContractError, match="transformation changed"):
        exercise.CoreFaultMaterializer().materialize(frozen, Action(exercise.FAULT), tmp_path)


@pytest.mark.parametrize("bad", ["multiple_tokens", "overlaps_status", "outside_image"])
def test_fault_range_cannot_cover_status_or_unvalidated_multi_token_layout(tmp_path, bad):
    root = tmp_path / "candidate"
    (root / "reference").mkdir(parents=True)
    header = [0] * 64
    header[17], header[19], header[25] = 16, 1, struct.calcsize("<64I")
    header[26], header[27] = header[25] + 64, header[25] + 68
    if bad == "multiple_tokens":
        header[19] = 2
    elif bad == "overlaps_status":
        header[27] = header[25]
    else:
        header[25] += 1024
    (root / "reference/image.bin").write_bytes(struct.pack("<64I", *header) + bytes(72))
    (root / "program.json").write_text(json.dumps(dict(data_base=1 << 20)))
    with pytest.raises(ContractError, match="isolated logit output region"):
        exercise._logit_range(root)


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), True])
def test_invalid_timeout_creates_no_partial_output(tmp_path, timeout):
    with pytest.raises(ContractError):
        exercise.run_core_feedback(tmp_path / "run", timeout=timeout)
    assert not (tmp_path / "run").exists()
