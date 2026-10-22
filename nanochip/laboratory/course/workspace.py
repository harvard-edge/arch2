"""Persistent student workspaces and evidence-backed course progress."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
from types import ModuleType
from typing import Any, Mapping, Sequence

from ..contracts import ContractError, canonical_json, file_sha256
from .registry import LABS, get_lab

COURSE_SCHEMA = "nanochip-cumulative-course/v1"


def _json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(
            json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n"
        )


def _tree_hash(path: Path) -> str:
    if path.is_file():
        return file_sha256(path)
    entries = []
    for item in sorted(path.rglob("*")):
        if item.is_file():
            entries.append((item.relative_to(path).as_posix(), file_sha256(item)))
    return hashlib.sha256(canonical_json(entries).encode("utf-8")).hexdigest()


def init_workspace(path: str | Path, *, mode: str = "student") -> dict[str, Any]:
    """Create a new workspace with explicit, fail-fast student modules."""
    if mode not in ("student", "instructor"):
        raise ContractError("Workspace mode must be student or instructor")
    root = Path(path).resolve()
    root.mkdir(parents=True, exist_ok=False)
    (root / "labs").mkdir()
    (root / "runs").mkdir()
    course_readme = Path(__file__).with_name("README.md")
    if course_readme.is_file():
        shutil.copyfile(course_readme, root / "README.md")
    starter_root = Path(__file__).with_name("starters")
    files = []
    for lab in LABS:
        source = starter_root / lab.student_file
        destination = root / "labs" / lab.student_file
        shutil.copyfile(source, destination)
        files.append(
            {
                "path": destination.relative_to(root).as_posix(),
                "sha256": file_sha256(destination),
            }
        )
    manifest = {
        "schema": COURSE_SCHEMA,
        "course_id": "nanochip-cumulative-v1",
        "mode": mode,
        "labs": [asdict(lab) for lab in LABS],
        "student_components": files,
        "progress_path": "progress.jsonl",
        "statement": "Progress records require executed checks and retained artifacts; they are not completion checkboxes.",
    }
    _json(root / "course.json", manifest)
    (root / "progress.jsonl").touch(exist_ok=False)
    return manifest


def load_student_component(workspace: str | Path, lab_number: int) -> ModuleType:
    """Load exactly the student's module; an incomplete hook is never replaced."""
    lab = get_lab(lab_number)
    root = Path(workspace).resolve()
    manifest = json.loads((root / "course.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != COURSE_SCHEMA:
        raise ContractError("Unknown course workspace schema")
    path = root / "labs" / lab.student_file
    if not path.is_file():
        raise ContractError(f"Student component is missing: {path}")
    if not path.resolve().is_relative_to(root):
        raise ContractError("Student module escapes the workspace")
    source = path.read_bytes()
    source_hash = hashlib.sha256(source).hexdigest()
    name = f"nanochip_course_student_lab_{lab_number}_{source_hash[:12]}"
    module = ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    try:
        exec(compile(source, str(path), "exec"), module.__dict__)
    except Exception as exc:
        raise ContractError(f"Student component failed to load: {exc}") from exc
    module.__loaded_source_sha256__ = source_hash
    return module


def record_lab_result(
    workspace: str | Path,
    lab_number: int,
    *,
    mode: str,
    outputs: Sequence[str | Path],
    checks: Sequence[Mapping[str, Any]],
    inputs: Mapping[str, str] | None = None,
    details: str = "",
    executed_implementation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Append a run receipt, retaining failed attempts without marking them complete."""
    lab = get_lab(lab_number)
    if mode not in ("student", "instructor"):
        raise ContractError("Run mode must be student or instructor")
    root = Path(workspace).resolve()
    manifest_path = root / "course.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != COURSE_SCHEMA:
        raise ContractError("Unknown course workspace schema")
    if manifest.get("mode") == "student" and mode == "instructor":
        # Recovery runs are allowed, but the artifact records which code ran.
        pass
    if not checks:
        raise ContractError("A lab result needs at least one integration check")
    normalized_checks = []
    for check in checks:
        row = dict(check)
        if row.get("status") not in ("pass", "fail", "unresolved", "not_run"):
            raise ContractError(
                "Course checks need an explicit pass/fail/unresolved/not_run status"
            )
        if not isinstance(row.get("name"), str) or not row["name"]:
            raise ContractError("Course checks need names")
        normalized_checks.append(row)
    if all(item["status"] == "pass" for item in normalized_checks):
        required = lab.integration_check
        if not any(
            item["name"] == required and item["status"] == "pass"
            for item in normalized_checks
        ):
            raise ContractError(
                f"A passing run must include the declared integration check: {required}"
            )
    output_rows = []
    resolved_outputs = []
    for item in outputs:
        path = Path(item).resolve()
        if not path.is_relative_to(root) or not path.exists():
            raise ContractError("Retained outputs must exist inside the workspace")
        if path.is_dir() and not any(path.iterdir()):
            raise ContractError("A retained course output directory cannot be empty")
        resolved_outputs.append(path)
        output_rows.append(
            {"path": path.relative_to(root).as_posix(), "sha256": _tree_hash(path)}
        )
    if all(item["status"] == "pass" for item in normalized_checks):
        # Artifact paths are relative to the attempt directory; find the attempt
        # root from the retained output whose path is named attempt-NNN.
        attempt_roots = [
            path for path in resolved_outputs if path.name.startswith("attempt-")
        ]
        if len(attempt_roots) != 1:
            raise ContractError(
                "A completed lab must retain one unique attempt directory"
            )
        evidence_path = (attempt_roots[0] / lab.artifact).resolve()
        if (
            not evidence_path.is_relative_to(attempt_roots[0])
            or not evidence_path.exists()
        ):
            raise ContractError(
                f"Completed lab is missing its declared artifact: {lab.artifact}"
            )
        if evidence_path.is_dir() and not any(evidence_path.iterdir()):
            raise ContractError("Declared lab artifact directory is empty")
    student_file = root / "labs" / lab.student_file
    if executed_implementation is not None:
        implementation = dict(executed_implementation)
    elif mode == "student":
        if not student_file.is_file():
            raise ContractError("Student component file is missing")
        implementation = {
            "path": student_file.relative_to(root).as_posix(),
            "sha256": file_sha256(student_file),
        }
    else:
        ref = Path(__file__).with_name("reference") / lab.student_file
        implementation = (
            {"path": str(ref), "sha256": file_sha256(ref)}
            if ref.is_file()
            else {
                "path": "existing-reference-not-yet-bound",
                "sha256": None,
            }
        )
    event = {
        "schema": "nanochip-course-run/v1",
        "lab": lab_number,
        "title": lab.title,
        "mode": mode,
        "status": "complete"
        if all(item["status"] == "pass" for item in normalized_checks)
        else "incomplete",
        "implementation": implementation,
        "inputs": dict(inputs or {}),
        "outputs": output_rows,
        "checks": normalized_checks,
        "details": details,
    }
    event["run_digest"] = hashlib.sha256(
        canonical_json(event).encode("utf-8")
    ).hexdigest()
    progress_path = root / "progress.jsonl"
    with progress_path.open("a", encoding="utf-8") as stream:
        stream.write(canonical_json(event) + "\n")
    return event


def course_status(workspace: str | Path) -> dict[str, Any]:
    """Summarize latest lab evidence and mark downstream records stale on input drift."""
    root = Path(workspace).resolve()
    manifest = json.loads((root / "course.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != COURSE_SCHEMA:
        raise ContractError("Unknown course workspace schema")
    path = root / manifest.get("progress_path", "progress.jsonl")
    events = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    latest: dict[int, dict[str, Any]] = {}
    for event in events:
        lab_number = event.get("lab")
        get_lab(lab_number)
        latest[lab_number] = event
    states = []
    resolved_status: dict[int, str] = {}
    for lab in LABS:
        event = latest.get(lab.number)
        state = "not_started"
        if event:
            state = event.get("status", "incomplete")
            digest_payload = {
                key: value for key, value in event.items() if key != "run_digest"
            }
            if hashlib.sha256(
                canonical_json(digest_payload).encode("utf-8")
            ).hexdigest() != event.get("run_digest"):
                state = "stale"
            if event.get("status") == "complete":
                for artifact in event.get("outputs", []):
                    artifact_path = root / artifact["path"]
                    if (
                        not artifact_path.exists()
                        or _tree_hash(artifact_path) != artifact["sha256"]
                    ):
                        state = "stale"
                        break
                implementation = event.get("implementation", {})
                if event.get("mode") == "student":
                    implementation_path = root / implementation.get("path", "")
                else:
                    implementation_path = Path(implementation.get("path", ""))
                if implementation.get("sha256") is not None and (
                    not implementation_path.is_file()
                    or file_sha256(implementation_path) != implementation["sha256"]
                ):
                    state = "stale"
                for upstream in lab.upstream:
                    parent = latest.get(upstream)
                    expected = (event.get("inputs") or {}).get(f"lab{upstream:02d}")
                    if (
                        not parent
                        or resolved_status.get(upstream) != "complete"
                        or expected != parent.get("run_digest")
                    ):
                        state = "stale"
                        break
        resolved_status[lab.number] = state
        states.append(
            {
                "lab": lab.number,
                "title": lab.title,
                "status": state,
                "run_digest": event.get("run_digest") if event else None,
                "outputs": event.get("outputs", []) if event else [],
            }
        )
    complete = all(item["status"] == "complete" for item in states)
    return {
        "schema": COURSE_SCHEMA,
        "workspace": str(root),
        "labs": states,
        "course_complete": complete,
        "run_count": len(events),
    }
