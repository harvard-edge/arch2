"""Design-Loop Card validation and v1.1-to-v2 migration commands."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import unquote, urlsplit

import typer
from rich.console import Console


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in (
        here.parents[1],
        *here.parents,
        Path.cwd().resolve(),
        *Path.cwd().resolve().parents,
    ):
        if (candidate / "CITATION.cff").exists() and (candidate / "book").is_dir():
            return candidate
    return here.parents[1]


ROOT = _find_repo_root()
console = Console()

CARD_SCHEMA_VERSION = "2.0"
CARD_SCHEMA_PATHS = {
    "1.0": ROOT / "card" / "schemas" / "design-loop-card.v1.schema.json",
    "1.1": ROOT / "card" / "schemas" / "design-loop-card.v1.1.schema.json",
    "2.0": ROOT / "card" / "schemas" / "design-loop-card.v2.schema.json",
}
CARD_SCHEMA_PATH = CARD_SCHEMA_PATHS[CARD_SCHEMA_VERSION]


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    location: str
    message: str
    span: str | None = None
    replacement: str | None = None
    context: str | None = None

    @property
    def fixable(self) -> bool:
        return self.span is not None and self.replacement is not None

    def as_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "severity": self.severity,
            "code": self.code,
            "location": self.location,
            "message": self.message,
            "fixable": self.fixable,
        }
        match = re.match(r"^(?P<path>.+?):(?P<line>\d+)$", self.location)
        if match:
            record["path"] = match.group("path")
            record["line"] = int(match.group("line"))
        for key in ("span", "replacement", "context"):
            value = getattr(self, key)
            if value is not None:
                record[key] = value
        return record


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


from typing import Any, Mapping


MIGRATION_DRAFT_VERSION = "arch2-design-loop-card-migration-draft/v1"
SOURCE_VERSION = "1.1"
TARGET_VERSION = "2.0"


def _missing(target: str, reason: str) -> dict[str, str]:
    return {"target": target, "reason": reason}


def migrate_v1_1_to_v2_draft(document: Mapping[str, Any]) -> dict[str, Any]:
    """Map only v1.1 content with a direct v2 meaning.

    The result is deliberately a migration draft, not a schema-valid v2 card.
    Missing claim status, evidence status, replay validation, and decision rights
    require author input and are listed explicitly.
    """
    if document.get("schema_version") != SOURCE_VERSION:
        raise ValueError("migration accepts only design-loop card schema version '1.1'")
    source = document.get("design_loop_card")
    if not isinstance(source, Mapping):
        raise ValueError("design_loop_card must be a mapping")

    mapped: dict[str, Any] = {}
    missing: list[dict[str, str]] = []
    legacy_unmapped: dict[str, Any] = {}

    for field in ("card_id", "design_space"):
        if field in source:
            mapped[field] = deepcopy(source[field])

    intent = source.get("intent")
    if isinstance(intent, Mapping):
        mapped_intent = {
            key: deepcopy(intent[key])
            for key in (
                "objective",
                "constraints",
                "non_goals",
                "risks",
                "deployment_assumptions",
            )
            if key in intent
        }
        mapped["intent"] = mapped_intent
        claim_boundary = intent.get("claim_boundary")
        if isinstance(claim_boundary, Mapping):
            partial_claim: dict[str, Any] = {}
            if claim_boundary.get("claim"):
                partial_claim["statement"] = deepcopy(claim_boundary["claim"])
            if claim_boundary.get("non_claim"):
                partial_claim["non_claims"] = [deepcopy(claim_boundary["non_claim"])]
            mapped["claims"] = [partial_claim]
            for field in (
                "claim_id",
                "claim_type",
                "baseline_or_comparator",
                "outcome",
                "scope",
                "status",
                "evidence_refs",
            ):
                missing.append(
                    _missing(
                        f"design_loop_card.claims[0].{field}",
                        "v1.1 claim_boundary does not encode this v2 claim meaning",
                    )
                )
        else:
            mapped["claims"] = []
            missing.append(
                _missing(
                    "design_loop_card.claims",
                    "v2 requires at least one typed architectural claim",
                )
            )

    task = source.get("task")
    if isinstance(task, str):
        mapped["task"] = {"kind": task}
        missing.append(
            _missing(
                "design_loop_card.task.description",
                "v1.1 records only a closed task label, not a task description",
            )
        )

    representation = source.get("representation")
    if isinstance(representation, Mapping):
        mapped_representation = {
            key: deepcopy(representation[key])
            for key in ("state_schema_id", "reads", "writes", "uncertainties")
            if key in representation
        }
        if "ir_level" in representation:
            mapped_representation["abstraction"] = deepcopy(representation["ir_level"])
        mapped["representation"] = mapped_representation

    if isinstance(source.get("environment"), Mapping):
        mapped["environment"] = deepcopy(source["environment"])

    method_role = source.get("method_role")
    if isinstance(method_role, Mapping):
        actor_map = method_role.get("actor_map")
        if isinstance(actor_map, list):
            mapped_roles = []
            for index, actor in enumerate(actor_map):
                if not isinstance(actor, Mapping):
                    continue
                partial_role = {
                    key: deepcopy(actor[key])
                    for key in ("actor_id", "reads", "writes")
                    if key in actor
                }
                partial_role["x-arch2-legacy"] = {
                    key: deepcopy(actor[key])
                    for key in ("role", "authority")
                    if key in actor
                }
                mapped_roles.append(partial_role)
                for field in ("actor_type", "roles", "limitations"):
                    missing.append(
                        _missing(
                            f"design_loop_card.method_roles[{index}].{field}",
                            "v1.1 actor records do not encode this v2 field",
                        )
                    )
            mapped["method_roles"] = mapped_roles
        if "roles" in method_role:
            legacy_unmapped["method_role.roles"] = deepcopy(method_role["roles"])

    feedback = source.get("feedback_budget")
    if isinstance(feedback, Mapping):
        mapped_feedback = {
            key: deepcopy(feedback[key])
            for key in ("evaluations", "latency", "fidelity")
            if key in feedback
        }
        if "cost" in feedback:
            mapped_feedback["compute_or_tool_cost"] = deepcopy(feedback["cost"])
        model_cost = feedback.get("model_side_cost")
        if isinstance(model_cost, Mapping):
            for key in ("model_calls", "energy_or_carbon", "human_review"):
                if key in model_cost:
                    mapped_feedback[key] = deepcopy(model_cost[key])
            if "gpu_hours" in model_cost:
                legacy_unmapped["feedback_budget.model_side_cost.gpu_hours"] = deepcopy(
                    model_cost["gpu_hours"]
                )
        mapped["feedback_budget"] = mapped_feedback

    source_evidence = source.get("evidence")
    mapped_records: list[dict[str, Any]] = []
    if isinstance(source_evidence, Mapping):
        records = source_evidence.get("records")
        if isinstance(records, list):
            for index, record in enumerate(records):
                if not isinstance(record, Mapping):
                    continue
                partial_record = {
                    key: deepcopy(record[key])
                    for key in ("evidence_id", "kind")
                    if key in record
                }
                legacy = {
                    key: deepcopy(record[key])
                    for key in ("workload_id", "seed", "provenance")
                    if key in record
                }
                if legacy:
                    partial_record["x-arch2-legacy"] = legacy
                mapped_records.append(partial_record)
                for field in (
                    "producer",
                    "status",
                    "tool",
                    "inputs",
                    "outputs",
                    "scope",
                    "limitations",
                    "integrity",
                ):
                    missing.append(
                        _missing(
                            f"design_loop_card.evidence.records[{index}].{field}",
                            "v1.1 evidence does not encode this v2 meaning without interpretation",
                        )
                    )
        for key in (
            "baseline_id",
            "resource_or_sustainability_boundary",
            "telemetry_packet",
            "integrity_manifest",
        ):
            if key in source_evidence:
                legacy_unmapped[f"evidence.{key}"] = deepcopy(source_evidence[key])
    mapped["evidence"] = {"records": mapped_records}

    source_traces = source.get("negative_traces")
    mapped_traces: list[dict[str, Any]] = []
    if isinstance(source_traces, list):
        for index, trace in enumerate(source_traces):
            if not isinstance(trace, Mapping):
                continue
            partial_trace = {
                key: deepcopy(trace[key])
                for key in ("candidate_id", "stage", "reason")
                if key in trace
            }
            if "gate" in trace:
                partial_trace["x-arch2-legacy"] = {"gate": deepcopy(trace["gate"])}
            mapped_traces.append(partial_trace)
            for field in ("record_id", "kind", "evidence_refs"):
                missing.append(
                    _missing(
                        f"design_loop_card.failed_or_rejected[{index}].{field}",
                        "v1.1 negative traces do not encode this v2 meaning",
                    )
                )
    mapped["failed_or_rejected"] = mapped_traces

    disclosure = source.get("disclosure_boundary")
    if isinstance(disclosure, Mapping):
        mapped["disclosure"] = deepcopy(disclosure)

    human_decision = source.get("human_decision")
    if isinstance(human_decision, Mapping):
        partial_decision: dict[str, Any] = {}
        if "owner" in human_decision:
            partial_decision["holder_id"] = deepcopy(human_decision["owner"])
        if "authorizes" in human_decision:
            partial_decision["action"] = deepcopy(human_decision["authorizes"])
        mapped["accountable_decision"] = partial_decision
        for field in (
            "status",
            "rationale",
            "claim_refs",
            "authorized_scope",
            "reopen_conditions",
        ):
            missing.append(
                _missing(
                    f"design_loop_card.accountable_decision.{field}",
                    "v1.1 human_decision does not encode this v2 meaning",
                )
            )

    for field in (
        "conformance_level",
        "rejection_authority",
        "commitment_boundary",
    ):
        if field in source:
            legacy_unmapped[field] = deepcopy(source[field])

    missing.extend(
        [
            _missing(
                "design_loop_card.profiles",
                "cumulative v1.1 levels cannot establish independent v2 profile status",
            ),
            _missing(
                "design_loop_card.profile_gaps",
                "an author must record gaps for every partial v2 profile",
            ),
            _missing(
                "design_loop_card.gates",
                "v1.1 gate prose lacks typed category, criterion, result, authority, waiver rule, and evidence links",
            ),
            _missing(
                "design_loop_card.decision_rights",
                "v1.1 does not separately assign propose, execute, reject, waive, recommend, and commit rights",
            ),
            _missing(
                "design_loop_card.replay",
                "v1.1 replay pointers do not establish commands, environment, inputs, outputs, expected status, and validated hashes",
            ),
        ]
    )

    extension_fields = {
        key: deepcopy(value)
        for key, value in source.items()
        if isinstance(key, str) and key.startswith("x-")
    }
    if extension_fields:
        mapped.update(extension_fields)

    return {
        "migration_draft_version": MIGRATION_DRAFT_VERSION,
        "source_schema_version": SOURCE_VERSION,
        "target_schema_version": TARGET_VERSION,
        "status": "requires_author_input",
        "mapped_design_loop_card": mapped,
        "missing_semantics": missing,
        "legacy_unmapped": legacy_unmapped,
        "instructions": (
            "Resolve every missing_semantics entry, then place the completed mapping "
            "under schema_version '2.0' and design_loop_card and validate it."
        ),
    }


def _card_json_path(parts: Iterable[object]) -> str:
    path = "$"
    for part in parts:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}"
    return path


def _card_schema_message(
    error: object, card: object, *, expected_version: str | None = None
) -> str:
    message = str(getattr(error, "message", "invalid card"))
    validator = getattr(error, "validator", None)
    absolute_path = list(getattr(error, "absolute_path", []))

    if absolute_path == ["schema_version"] and validator == "const":
        return f"schema version does not match contract '{expected_version}'"

    if validator == "additionalProperties" and "'claim'" in message:
        return "unexpected top-level card field 'claim'; use intent.claim_boundary.claim and intent.claim_boundary.non_claim"

    if validator == "required" and isinstance(card, dict):
        loop_card = card.get("design_loop_card")
        level = (
            loop_card.get("conformance_level") if isinstance(loop_card, dict) else None
        )
        missing_match = re.search(r"'([^']+)' is a required property", message)
        if missing_match and isinstance(level, int):
            return (
                f"conformance level {level} requires "
                f"'{missing_match.group(1)}' at {_card_json_path(absolute_path)}"
            )

    return message


def _card_v2_semantic_findings(card: dict[str, Any], card_path: Path) -> list[Finding]:
    """Check v2 relationships and local integrity bindings JSON Schema cannot express."""
    findings: list[Finding] = []
    location = _relative(card_path)
    loop_card = card["design_loop_card"]

    def add(code: str, json_path: str, message: str) -> None:
        findings.append(Finding("error", code, f"{location}:{json_path}", message))

    def indexed_ids(
        records: list[dict[str, Any]], key: str, json_path: str
    ) -> set[str]:
        identifiers: set[str] = set()
        for index, record in enumerate(records):
            identifier = record[key]
            if identifier in identifiers:
                add(
                    "card-duplicate-id",
                    f"{json_path}[{index}].{key}",
                    f"duplicate {key} {identifier!r}",
                )
            identifiers.add(identifier)
        return identifiers

    evidence_records = loop_card["evidence"]["records"]
    claims = loop_card["claims"]
    gates = loop_card["gates"]
    rejected = loop_card["failed_or_rejected"]
    evidence_ids = indexed_ids(
        evidence_records, "evidence_id", "$.design_loop_card.evidence.records"
    )
    claim_ids = indexed_ids(claims, "claim_id", "$.design_loop_card.claims")
    gate_ids = indexed_ids(gates, "gate_id", "$.design_loop_card.gates")
    indexed_ids(rejected, "record_id", "$.design_loop_card.failed_or_rejected")

    def check_refs(
        refs: list[str], known: set[str], json_path: str, label: str
    ) -> None:
        for index, reference in enumerate(refs):
            if reference not in known:
                add(
                    "card-unknown-reference",
                    f"{json_path}[{index}]",
                    f"unknown {label} reference {reference!r}",
                )

    for index, claim in enumerate(claims):
        check_refs(
            claim["evidence_refs"],
            evidence_ids,
            f"$.design_loop_card.claims[{index}].evidence_refs",
            "evidence",
        )
    for index, gate in enumerate(gates):
        check_refs(
            gate["evidence_refs"],
            evidence_ids,
            f"$.design_loop_card.gates[{index}].evidence_refs",
            "evidence",
        )
    for index, record in enumerate(rejected):
        check_refs(
            record["evidence_refs"],
            evidence_ids,
            f"$.design_loop_card.failed_or_rejected[{index}].evidence_refs",
            "evidence",
        )
        gate_ref = record.get("gate_ref")
        if gate_ref is not None and gate_ref not in gate_ids:
            add(
                "card-unknown-reference",
                f"$.design_loop_card.failed_or_rejected[{index}].gate_ref",
                f"unknown gate reference {gate_ref!r}",
            )

    recommendation = loop_card.get("recommendation")
    if recommendation:
        check_refs(
            recommendation["claim_refs"],
            claim_ids,
            "$.design_loop_card.recommendation.claim_refs",
            "claim",
        )
    decision_record = loop_card["accountable_decision"]
    check_refs(
        decision_record["claim_refs"],
        claim_ids,
        "$.design_loop_card.accountable_decision.claim_refs",
        "claim",
    )
    review = loop_card.get("independent_review")
    if review:
        check_refs(
            review["claim_refs"],
            claim_ids,
            "$.design_loop_card.independent_review.claim_refs",
            "claim",
        )
        check_refs(
            review["evidence_refs"],
            evidence_ids,
            "$.design_loop_card.independent_review.evidence_refs",
            "evidence",
        )

    rights = {
        (right["holder_id"], right["action"]) for right in loop_card["decision_rights"]
    }
    if loop_card["profiles"]["decision_rights"] == "complete":
        for index, gate in enumerate(gates):
            if (gate["authority_id"], "reject") not in rights:
                add(
                    "card-decision-right",
                    f"$.design_loop_card.gates[{index}].authority_id",
                    "gate authority must hold a declared reject right",
                )
            waiver = gate["waiver_rule"]
            if waiver["allowed"] and (waiver["authority_id"], "waive") not in rights:
                add(
                    "card-decision-right",
                    f"$.design_loop_card.gates[{index}].waiver_rule.authority_id",
                    "waiver authority must hold a declared waive right",
                )
        if (
            recommendation
            and (recommendation["recommender_id"], "recommend") not in rights
        ):
            add(
                "card-decision-right",
                "$.design_loop_card.recommendation.recommender_id",
                "recommender must hold a declared recommend right",
            )
        if (decision_record["holder_id"], "commit") not in rights:
            add(
                "card-decision-right",
                "$.design_loop_card.accountable_decision.holder_id",
                "decision holder must hold a declared commit right",
            )

    def verify_local_artifact(raw_uri: str, digest: str, json_path: str) -> None:
        parsed = urlsplit(raw_uri)
        if parsed.scheme or parsed.netloc:
            return
        if parsed.query or parsed.fragment:
            add(
                "card-artifact-uri",
                json_path,
                "local artifact URI must not contain a query or fragment",
            )
            return
        base = card_path.parent.resolve()
        target = (base / unquote(parsed.path)).resolve()
        try:
            target.relative_to(base)
        except ValueError:
            add(
                "card-artifact-escape",
                json_path,
                "local artifact URI escapes the card directory",
            )
            return
        if not target.is_file():
            add(
                "card-artifact-missing",
                json_path,
                f"local artifact does not exist: {raw_uri}",
            )
            return
        observed = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
        if observed != digest:
            add(
                "card-artifact-hash",
                json_path,
                f"SHA-256 mismatch for {raw_uri!r}: declared {digest}, observed {observed}",
            )

    for record_index, record in enumerate(evidence_records):
        for collection in ("inputs", "outputs"):
            for artifact_index, artifact in enumerate(record[collection]):
                sha256 = artifact["integrity"].get("sha256")
                if sha256:
                    verify_local_artifact(
                        artifact["uri"],
                        sha256,
                        (
                            "$.design_loop_card.evidence.records"
                            f"[{record_index}].{collection}[{artifact_index}].uri"
                        ),
                    )

    replay = loop_card.get("replay")
    if replay:
        replay_artifacts = [("environment_binding", replay["environment_binding"])]
        replay_artifacts.extend(
            (f"inputs[{index}]", artifact)
            for index, artifact in enumerate(replay["inputs"])
        )
        replay_artifacts.extend(
            (f"outputs[{index}]", artifact)
            for index, artifact in enumerate(replay["outputs"])
        )
        for suffix, artifact in replay_artifacts:
            verify_local_artifact(
                artifact["uri"],
                artifact["sha256"],
                f"$.design_loop_card.replay.{suffix}.uri",
            )

    return findings


def card_validation_findings(
    card_path: Path,
    *,
    schema_path: Path | None = None,
) -> list[Finding]:
    """Validate a YAML or JSON card against the canonical versioned contract."""
    location = _relative(card_path)
    if not card_path.exists():
        return [Finding("error", "card-missing", location, "card file does not exist")]

    try:
        if card_path.suffix.lower() == ".json":
            card = json.loads(card_path.read_text(encoding="utf-8"))
        elif card_path.suffix.lower() in {".yaml", ".yml"}:
            try:
                import yaml
            except ImportError:
                return [
                    Finding(
                        "error",
                        "missing-yaml",
                        "python",
                        "PyYAML is required to validate YAML design-loop cards",
                    )
                ]
            card = yaml.safe_load(card_path.read_text(encoding="utf-8"))
        else:
            return [
                Finding(
                    "error",
                    "card-file-type",
                    location,
                    "design-loop cards must use a .yaml, .yml, or .json extension",
                )
            ]
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [Finding("error", "card-parse", location, str(exc))]
    except Exception as exc:
        # PyYAML's parser exception is intentionally caught without importing it
        # at module load time, so JSON validation does not require PyYAML.
        return [Finding("error", "card-parse", location, str(exc))]

    if not isinstance(card, dict):
        return [
            Finding(
                "error",
                "card-document-type",
                location,
                "card document must be a mapping/object",
            )
        ]

    declared_version = card.get("schema_version")
    if schema_path is None:
        if (
            not isinstance(declared_version, str)
            or declared_version not in CARD_SCHEMA_PATHS
        ):
            supported = ", ".join(f"'{version}'" for version in CARD_SCHEMA_PATHS)
            return [
                Finding(
                    "error",
                    "card-schema-version",
                    f"{location}:$.schema_version",
                    f"unsupported schema version {declared_version!r}; supported versions are {supported}",
                )
            ]
        schema_path = CARD_SCHEMA_PATHS[declared_version]

    if not schema_path.exists():
        return [
            Finding(
                "error",
                "card-schema-missing",
                _relative(schema_path),
                "canonical design-loop card schema does not exist",
            )
        ]

    try:
        from jsonschema import Draft202012Validator, FormatChecker
        from jsonschema.exceptions import SchemaError
        from referencing import Registry, Resource
    except ImportError:
        return [
            Finding(
                "error",
                "missing-jsonschema",
                "python",
                "jsonschema is required to validate design-loop cards",
            )
        ]

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, UnicodeError, json.JSONDecodeError, SchemaError) as exc:
        return [
            Finding(
                "error",
                "card-schema-invalid",
                _relative(schema_path),
                str(exc),
            )
        ]

    registry = Registry()
    known_schema_paths = set(CARD_SCHEMA_PATHS.values()) | {schema_path}
    for known_path in known_schema_paths:
        if not known_path.exists():
            continue
        known_schema = json.loads(known_path.read_text(encoding="utf-8"))
        schema_id = known_schema.get("$id")
        if schema_id:
            registry = registry.with_resource(
                schema_id, Resource.from_contents(known_schema)
            )

    validator = Draft202012Validator(
        schema, registry=registry, format_checker=FormatChecker()
    )
    expected_version = (
        schema.get("properties", {}).get("schema_version", {}).get("const")
    )
    errors = sorted(
        validator.iter_errors(card),
        key=lambda error: (
            list(error.absolute_path),
            list(error.absolute_schema_path),
            error.message,
        ),
    )
    findings = [
        Finding(
            "error",
            "card-schema",
            f"{location}:{_card_json_path(error.absolute_path)}",
            _card_schema_message(error, card, expected_version=expected_version),
        )
        for error in errors
    ]
    if not findings and declared_version == "2.0":
        findings.extend(_card_v2_semantic_findings(card, card_path))
    return findings


def run_card_check(card_path: Path) -> None:
    findings = card_validation_findings(card_path)
    if not findings:
        console.print(
            f"[green]passed[/green] design-loop card ({_relative(card_path)})"
        )
        return
    for finding in findings:
        console.print(
            f"{finding.severity} [{finding.code}] {finding.location}: {finding.message}",
            markup=False,
            soft_wrap=True,
        )
    raise typer.Exit(1)


def register_card_commands(
    validate_app: typer.Typer, migrate_app: typer.Typer
) -> tuple[Any, Any]:
    @validate_app.command("card")
    def validate_card(
        card: Path = typer.Argument(
            ...,
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
            help="YAML or JSON design-loop card to validate.",
        ),
    ) -> None:
        """Validate a versioned design-loop card and its declared profiles."""
        run_card_check(card)

    @migrate_app.command("card")
    def migrate_card(
        source: Path = typer.Argument(
            ...,
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
            help="Version 1.1 YAML or JSON design-loop card.",
        ),
        output: Path
        | None = typer.Option(
            None,
            "--output",
            "-o",
            help="Migration-draft path; defaults beside the source card.",
        ),
    ) -> None:
        """Map v1.1 fields to a non-inventive v2 migration draft."""
        try:
            if source.suffix.lower() == ".json":
                document = json.loads(source.read_text(encoding="utf-8"))
            elif source.suffix.lower() in {".yaml", ".yml"}:
                import yaml

                document = yaml.safe_load(source.read_text(encoding="utf-8"))
            else:
                raise ValueError(
                    "source card must use a .yaml, .yml, or .json extension"
                )
            if not isinstance(document, dict):
                raise ValueError("source card must contain a mapping/object")
            draft = migrate_v1_1_to_v2_draft(document)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            console.print(f"[red]failed[/red] migration: {exc}")
            raise typer.Exit(1) from exc

        target = output or source.with_name(f"{source.stem}.v2-migration-draft.yaml")
        target = target.expanduser().resolve()
        if target.exists():
            console.print(
                f"[red]failed[/red] migration: output already exists: {target}"
            )
            raise typer.Exit(1)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            import yaml

            target.write_text(
                yaml.safe_dump(draft, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
        except OSError as exc:
            console.print(f"[red]failed[/red] migration: {exc}")
            raise typer.Exit(1) from exc
        console.print(
            "[yellow]migration draft requires author input[/yellow] "
            f"({len(draft['missing_semantics'])} missing semantics): {target}"
        )

    return validate_card, migrate_card
