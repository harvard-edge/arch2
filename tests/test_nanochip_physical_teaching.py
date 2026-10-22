"""Constructed fixtures exercise composition guards, never actual physical claims."""

from dataclasses import replace
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from nanochip.laboratory.contracts import (
    Action,
    Artifact,
    Candidate,
    CheckResult,
    ContractError,
    RunReceipt,
    file_sha256,
)
from nanochip.laboratory.physical import teaching


def fixture(tmp_path):
    task = teaching.make_physical_task()
    root = tmp_path / "candidate"
    root.mkdir()
    (root / "core.v").write_text(
        "// constructed fixture only\nmodule nanochip_teaching_core; endmodule\n"
    )
    (root / "physical-config.json").write_text(json.dumps(teaching.DEFAULT_CONFIG))
    candidate = Candidate(
        "serial_mul1",
        task.task_id,
        str(root),
        Action("serial_mul1"),
        tuple(
            Artifact.from_file(root, name)
            for name in ("core.v", "physical-config.json")
        ),
        task_digest=task.digest,
    )
    return task, candidate


def functional(candidate, *, fail=False):
    root = Path(candidate.root).parent / "functional-fixture"
    root.mkdir()
    (root / "core.v").write_bytes((Path(candidate.root) / "core.v").read_bytes())
    return RunReceipt(
        candidate.task_id,
        candidate.digest,
        "fresh",
        "success",
        "fixture",
        "fixture",
        checks=tuple(
            CheckResult(name, "fail" if fail and index == 0 else "pass", teaching.SCOPE)
            for index, name in enumerate(teaching.CHECKS)
        ),
        output_root=str(root),
        output_artifacts=(Artifact.from_file(root, "core.v"),),
    )


def test_physical_requirements_are_complete_and_at_the_exact_core_scope():
    task = teaching.make_physical_task()
    required = {(item.name, item.scope) for item in task.required_checks}
    assert {(name, teaching.SCOPE) for name in teaching.PHYSICAL_CHECKS} <= required
    assert task.specification["physical"]["configuration"]["CLOCK_PERIOD"] == 100
    backend = teaching.TeachingCorePhysicalBackend()
    assert (
        task.specification["physical"]["physical_timeout"]
        == backend.physical_timeout
        == 14400
    )
    assert (
        task.specification["physical"]["correspondence_timeout"]
        == backend.correspondence_timeout
        == 3600
    )


def test_task_configuration_cannot_mutate_the_profile_used_by_other_tasks():
    task = teaching.make_physical_task()
    task.specification["physical"]["configuration"]["CLOCK_PERIOD"] = 999
    task.specification["physical"]["configuration"]["VERILOG_FILES"].append(
        "dir::other.v"
    )
    other = teaching.make_physical_task()
    assert other.specification["physical"]["configuration"]["CLOCK_PERIOD"] == 100
    assert other.specification["physical"]["configuration"]["VERILOG_FILES"] == [
        "dir::core.v"
    ]


def test_materializer_and_physical_task_use_the_same_shared_profile(tmp_path):
    from nanochip.laboratory.teaching_core.backend import (
        TeachingCoreMaterializer,
        default_physical_config,
    )

    task = teaching.make_physical_task()
    candidate = TeachingCoreMaterializer().materialize(
        task, Action("serial_mul2"), tmp_path
    )
    expected = default_physical_config()
    assert (
        json.loads((Path(candidate.root) / "physical-config.json").read_text())
        == expected
    )
    assert task.specification["physical"]["configuration"] == expected
    assert expected["SYNTH_STRATEGY"] == "AREA 3"
    assert expected["meta"]["flow"] == "NanochipClockRepair"
    expected["meta"]["flow"] = "modified"
    assert default_physical_config()["meta"]["flow"] == "NanochipClockRepair"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"physical_timeout": float("nan")},
        {"check_timeout": 0},
        {"correspondence_timeout": -1},
        {"cores": True},
        {"cores": 9},
    ],
)
def test_invalid_budgets_are_rejected_before_workload_or_eda(kwargs):
    with pytest.raises(ValueError):
        teaching.make_physical_task(**kwargs)
    with pytest.raises(ValueError):
        teaching.TeachingCorePhysicalBackend(**kwargs)


def test_functional_failure_prevents_eda_and_keeps_physical_checks_not_run(tmp_path):
    task, candidate = fixture(tmp_path)
    result = functional(candidate, fail=True)
    with patch.object(
        teaching.TeachingCoreBackend, "evaluate", return_value=result
    ), patch.object(teaching.flow, "run_physical_design") as physical:
        receipt = teaching.TeachingCorePhysicalBackend().evaluate(task, candidate)
    physical.assert_not_called()
    assert all(
        check.status == "not_run"
        for check in receipt.checks
        if check.name in teaching.PHYSICAL_CHECKS
    )


def test_backend_rejects_task_without_physical_obligations_before_tools(tmp_path):
    task, candidate = fixture(tmp_path)
    task = replace(
        task,
        required_checks=tuple(
            check
            for check in task.required_checks
            if check.name not in teaching.PHYSICAL_CHECKS
        ),
    )
    candidate = replace(candidate, task_digest=task.digest)
    with pytest.raises(ContractError, match="require every"):
        teaching.TeachingCorePhysicalBackend().evaluate(task, candidate)


@pytest.mark.parametrize("runtime_mode", ["docker", "native"])
def test_physical_result_keeps_electrical_failure_and_unresolved_correspondence(
    tmp_path, runtime_mode
):
    task, candidate = fixture(tmp_path)
    result = functional(candidate)

    def execute(sources, output, **kwargs):
        output.mkdir()
        (output / "core.v").write_bytes(sources["core.v"].read_bytes())
        (output / "config.json").write_bytes(Path(kwargs["config"]).read_bytes())
        (output / "receipt.json").write_text("constructed fixture")
        return {
            "status": "completed",
            "config_sha256": file_sha256(output / "config.json"),
            "checks": [
                {
                    "name": name,
                    "scope": teaching.SCOPE,
                    "status": "fail" if name == "electrical_constraints" else "pass",
                    "details": "constructed fixture",
                }
                for name in teaching.PHYSICAL_CHECKS
                if name != "rtl_netlist_correspondence"
            ],
            "artifacts": [],
            "stages": {},
        }

    with patch.object(
        teaching.TeachingCoreBackend, "evaluate", return_value=result
    ), patch.object(
        teaching.flow, "run_physical_design", side_effect=execute
    ) as physical, patch.object(
        teaching, "run_correspondence", wraps=teaching.run_correspondence
    ) as proof:
        receipt = teaching.TeachingCorePhysicalBackend(mode=runtime_mode).evaluate(
            task, candidate
        )
    assert physical.call_args.kwargs["mode"] == runtime_mode
    assert proof.call_args.kwargs["mode"] == runtime_mode
    statuses = {check.name: check.status for check in receipt.checks}
    assert statuses["electrical_constraints"] == "fail"
    assert statuses["rtl_netlist_correspondence"] == "unresolved"
    assert all(check.scope == teaching.SCOPE for check in receipt.checks)
    link = json.loads((tmp_path / "execution-link.json").read_text())
    assert (
        link["candidate_source_sha256"]
        == link["functional_source_sha256"]
        == link["physical_source_sha256"]
    )
