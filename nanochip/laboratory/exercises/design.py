"""Check a student transformation with the common materializer and tools."""

from dataclasses import asdict, replace
import inspect
import json
from pathlib import Path

from ..adapters import VerilatorBackend
from ..contracts import Action, file_sha256
from ..design_changes import (
    DesignChangeMaterializer,
    design_change_task,
    run_design_checks,
)


def check_design(output: Path, *, transformer=None, timeout=120) -> dict:
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    task = design_change_task()
    extension = Path(inspect.getsourcefile(transformer)) if transformer else None
    task = replace(
        task,
        specification=dict(
            task.specification,
            extension_sha256=file_sha256(extension) if extension else None,
        ),
    )
    materializer = DesignChangeMaterializer(transformer=transformer)
    # Both branches must conform before launching either expensive checker.
    # A transformer that always streams has no valid reference action.
    reference = materializer.materialize(
        task, Action("retain_indexed_read"), output / "retain"
    )
    reference.validate_files()
    candidate = materializer.materialize(task, Action("stream_quantized_row"), output)
    candidate.validate_files()
    functional = VerilatorBackend(timeout).evaluate(task, candidate)
    differential = None
    if functional.execution_status == "success" and all(
        c.status == "pass" for c in functional.checks
    ):
        differential = run_design_checks(
            Path(candidate.root) / "msh_deq.v", output / "differential", timeout
        )
    candidate.validate_files()
    result = dict(
        scope="student transformation checks; no physical execution or model inference",
        action_conformance={
            "retain_indexed_read": "pass",
            "stream_quantized_row": "pass",
        },
        reference_candidate=asdict(reference),
        candidate=asdict(candidate),
        candidate_sha256=file_sha256(Path(candidate.root) / "msh_deq.v"),
        functional=asdict(functional),
        differential=differential,
        ok=bool(differential and differential["ok"]),
        physical_run=False,
    )
    (output / "student-design-check.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    return result
