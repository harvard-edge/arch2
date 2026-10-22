"""Explicit adapters for composing the cumulative course components.

These adapters deliberately delegate to the student's Lab 4--8 hooks. They do
not contain a reference implementation or silently substitute a baseline.
"""

from __future__ import annotations

from dataclasses import asdict, replace
from copy import deepcopy
import inspect
import json
from pathlib import Path
import struct
from typing import Any, Callable, Mapping, Sequence

from ..contracts import (
    Action,
    Artifact,
    Candidate,
    ContractError,
    RunReceipt,
    Task,
    canonical_json,
    file_sha256,
)


def _source(component: Any) -> str | None:
    path = getattr(component, "__file__", None)
    if path is None:
        try:
            target = (
                component
                if inspect.isfunction(component) or inspect.ismethod(component)
                else type(component)
            )
            path = inspect.getsourcefile(target)
        except (TypeError, OSError):
            path = None
    return str(Path(path).resolve()) if path else None


def _require(component: Any, *hooks: str) -> None:
    missing = [name for name in hooks if not callable(getattr(component, name, None))]
    if missing:
        raise ContractError(
            f"Course component is missing required hook(s): {', '.join(missing)}"
        )


class ReceiptAdapterBackend:
    """Route every fresh tool receipt through the active Lab 3 parser."""

    def __init__(self, backend: Any, component: Any):
        _require(component, "adapt_receipt")
        if not callable(getattr(backend, "evaluate", None)):
            raise ContractError("A measured backend is required")
        self.backend, self.component = backend, component

    def evaluate(self, task: Task, candidate: Candidate) -> RunReceipt:
        raw = asdict(self.backend.evaluate(task, candidate))
        immutable_raw = deepcopy(raw)
        receipt = self.component.adapt_receipt(raw, task, candidate)
        if not isinstance(receipt, RunReceipt):
            raise ContractError("Lab 3 receipt adapter must return a RunReceipt")
        if (
            receipt.task_id != task.task_id
            or receipt.candidate_digest != candidate.digest
        ):
            raise ContractError("Lab 3 adapter changed receipt identity")
        if asdict(receipt) != immutable_raw:
            raise ContractError(
                "Lab 3 adapter changed backend evidence while parsing the receipt"
            )
        return receipt

    def implementation_sources(self):
        source = _source(self.component)
        return (source,) if source else ()


class TrainingAdapter:
    """Adapt Lab 4's trainer to the cumulative campaign train/adapt contract."""

    name = "course_lab4_training_with_measured_feedback"

    def __init__(
        self,
        component: Any,
        model_io_contract: Any,
        *,
        base_checkpoint: str | Path,
        seed: int = 17,
        pretrain_steps: int = 120,
        adapt_steps: int = 80,
        max_seconds: float = 60,
    ):
        _require(component, "train", "build_model")
        self.component = component
        self.model_io_contract = model_io_contract
        self.base_checkpoint = Path(base_checkpoint).resolve(strict=True)
        self.seed, self.pretrain_steps, self.adapt_steps = (
            seed,
            pretrain_steps,
            adapt_steps,
        )
        self.max_seconds = max_seconds

    @staticmethod
    def _prior_records(base_checkpoint: Path) -> dict[str, Mapping]:
        try:
            previous = json.loads(
                (base_checkpoint / "training.json").read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError(
                "Lab 4 lineage needs the preceding checkpoint's training record"
            ) from exc
        rows = previous.get("training_records")
        if not isinstance(rows, list) or not rows:
            raise ContractError(
                "Lab 4 checkpoint does not retain its training-record lineage"
            )
        return {row["record_id"]: row for row in rows}

    @classmethod
    def _normalize_records(
        cls, records: Sequence[Mapping], base_checkpoint: Path
    ) -> list[dict]:
        """Keep copied campaign snapshots while replaying the exact checkpoint rows."""
        prior = cls._prior_records(base_checkpoint)
        normalized = []
        for value in records:
            row = deepcopy(dict(value))
            existing = prior.get(row.get("record_id"))
            if existing is None:
                normalized.append(row)
                continue
            snapshot = row.pop("original_source_receipt", None)
            receipt = row.get("source_receipt")
            try:
                Artifact(**receipt).validate(row["source_root"])
            except (KeyError, TypeError, ContractError) as exc:
                raise ContractError(
                    "Campaign copy of a prior Lab 4 source is not valid"
                ) from exc
            expected_snapshot = dict(
                root=existing["source_root"], **existing["source_receipt"]
            )
            if snapshot != expected_snapshot or receipt.get("sha256") != existing[
                "source_receipt"
            ].get("sha256"):
                raise ContractError(
                    "Campaign snapshot changed a prior Lab 4 source artifact"
                )
            original = dict(row)
            original["source_root"] = existing["source_root"]
            original["source_receipt"] = existing["source_receipt"]
            if original != existing:
                raise ContractError(
                    "Campaign replay changed a prior Lab 4 record's content or provenance"
                )
            Artifact(**existing["source_receipt"]).validate(existing["source_root"])
            normalized.append(deepcopy(dict(existing)))
        return normalized

    @classmethod
    def _verify_lineage(
        cls, metadata: Mapping, base_checkpoint: Path, output: Path
    ) -> None:
        expected_checkpoint = file_sha256(base_checkpoint / "checkpoint.pt")
        previous = json.loads(
            (base_checkpoint / "training.json").read_text(encoding="utf-8")
        )
        expected_parameters = previous.get("final_parameter_sha256")
        if (
            metadata.get("base_checkpoint_sha256") != expected_checkpoint
            or not expected_parameters
            or metadata.get("initial_parameter_sha256") != expected_parameters
            or not metadata.get("final_parameter_sha256")
        ):
            raise ContractError(
                "Lab 4 update did not initialize from the exact preceding checkpoint parameters"
            )
        try:
            saved = json.loads((output / "training.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError(
                "Lab 4 update did not retain its training-lineage record"
            ) from exc
        if (
            saved.get("base_checkpoint_sha256") != expected_checkpoint
            or saved.get("initial_parameter_sha256") != expected_parameters
            or saved.get("final_parameter_sha256")
            != metadata.get("final_parameter_sha256")
            or not isinstance(saved.get("training_records"), list)
        ):
            raise ContractError(
                "Saved Lab 4 training record does not preserve the declared checkpoint lineage"
            )
        saved_records = {row.get("record_id"): row for row in saved["training_records"]}
        if any(
            saved_records.get(row.get("record_id")) != row
            for row in cls._prior_records(base_checkpoint).values()
        ):
            raise ContractError(
                "Lab 4 update dropped or changed an existing training record"
            )

    def train(self, records: Sequence[Mapping], output: Path) -> Mapping:
        records = self._normalize_records(records, self.base_checkpoint)
        metadata = self.component.train(
            records,
            output,
            model_io_contract=self.model_io_contract,
            objective="pretrain",
            base_checkpoint=self.base_checkpoint,
            seed=self.seed,
            max_steps=self.pretrain_steps,
            max_seconds=self.max_seconds,
        )
        if (
            not isinstance(metadata, Mapping)
            or metadata.get("parameters_changed") is not True
        ):
            raise ContractError("Lab 4 training must report real parameter updates")
        self._verify_lineage(metadata, self.base_checkpoint, output)
        return dict(
            parameters_changed=True,
            base_checkpoint_sha256=metadata.get("base_checkpoint_sha256"),
            training=dict(metadata),
        )

    def adapt(
        self, records: Sequence[Mapping], base_checkpoint: Path, output: Path
    ) -> Mapping:
        text_rows = [row for row in records if "target_action" not in row]
        action_rows = [row for row in records if "target_action" in row]
        byte_budget = getattr(self.model_io_contract, "max_input_bytes", None)
        if type(byte_budget) is not int or byte_budget < 1:
            raise ContractError(
                "Lab 4 model contract must declare a positive UTF-8 byte budget"
            )
        text_rows = self._normalize_records(text_rows, base_checkpoint)
        segmented_rows, segment_count = [], 0
        for row in text_rows:
            text, chunks, current = row.get("input_text"), [], ""
            if not isinstance(text, str):
                raise ContractError("Lab 4 adaptation text must be a string")
            for char in text:
                if len(char.encode("utf-8")) > byte_budget:
                    raise ContractError(
                        "A UTF-8 character exceeds Lab 4's declared text segment budget"
                    )
                if current and len((current + char).encode("utf-8")) > byte_budget:
                    chunks.append(current)
                    current = ""
                current += char
            if current:
                chunks.append(current)
            if len(chunks) == 1:
                segmented_rows.append(dict(row))
                continue
            for index, chunk in enumerate(chunks):
                segmented_rows.append(
                    dict(
                        row,
                        input_text=chunk,
                        record_id=f"{row['record_id']}-segment-{index}",
                        segment_parent_record_id=row["record_id"],
                        segment_index=index,
                        segment_count=len(chunks),
                    )
                )
            segment_count += len(chunks)
        text_rows = segmented_rows
        phases, preceding = [], base_checkpoint
        if text_rows:
            destination = (
                output.with_name(output.name + "-pretrain") if action_rows else output
            )
            metadata = self.component.train(
                text_rows,
                destination,
                model_io_contract=self.model_io_contract,
                objective="pretrain",
                base_checkpoint=preceding,
                seed=self.seed,
                max_steps=self.adapt_steps,
                max_seconds=self.max_seconds,
            )
            self._verify_lineage(metadata, preceding, destination)
            phases.append(dict(kind="text", metadata=dict(metadata)))
            preceding = destination
        if action_rows:
            metadata = self.component.train(
                action_rows,
                output,
                model_io_contract=self.model_io_contract,
                objective="supervised",
                base_checkpoint=preceding,
                seed=self.seed,
                max_steps=self.adapt_steps,
                max_seconds=self.max_seconds,
            )
            self._verify_lineage(metadata, preceding, output)
            phases.append(dict(kind="action", metadata=dict(metadata)))
        if not phases or any(
            item["metadata"].get("parameters_changed") is not True for item in phases
        ):
            raise ContractError(
                "Lab 4 measured-feedback adaptation must update parameters"
            )
        return dict(
            parameters_changed=True,
            base_checkpoint_sha256=file_sha256(base_checkpoint / "checkpoint.pt"),
            phases=phases,
            text_segmentation=dict(
                max_utf8_bytes=byte_budget,
                segmented_record_count=segment_count,
                source_record_count=sum(
                    1 for row in records if "target_action" not in row
                ),
            ),
            steps_completed=sum(
                item["metadata"].get("steps_completed", 0) for item in phases
            ),
        )

    def proposer(self, checkpoint: Path, format_input: Callable):
        from ..models.language import LanguageProposer

        return LanguageProposer(
            checkpoint,
            format_input,
            model_io_contract=self.model_io_contract,
            model_factory=self.component.build_model,
        )

    def implementation_sources(self):
        source = _source(self.component)
        return (source,) if source else ()


class RepresentationAdapter:
    """Bind Lab 5's serialization and retrieval hooks to campaign boundaries."""

    def __init__(self, component: Any, model_io_contract: Any | None = None):
        _require(component, "serialize", "retrieve", "parse_action")
        self.component = component
        self.model_io_contract = model_io_contract
        self.last_context_selection: dict[str, Any] = {}

    def serialize(self, task: Task, history=(), context=()) -> str:
        from ..context import with_context

        text = self.component.serialize(task, history)
        if not isinstance(text, str) or not text:
            raise ContractError("Lab 5 serializer must return nonempty text")
        result = with_context(text, context)
        if not isinstance(result, str) or not result:
            raise ContractError(
                "Lab 5 representation plus context must remain nonempty"
            )
        if self.model_io_contract is not None:
            self.model_io_contract.validate_text(result)
        return result

    def retrieve(self, task: Task, history, allowed_sources, budget: int):
        # Keep the model's declared serialization unchanged, while giving the
        # retriever the full task vocabulary needed to find relevant evidence.
        base_text = self.component.serialize(task, history)
        query = base_text + "\n" + canonical_json(task.specification)
        if self.model_io_contract is not None:
            self.model_io_contract.validate_text(base_text)
        trusted_sources = deepcopy(tuple(allowed_sources))
        student_sources = deepcopy(trusted_sources)
        selected = self.component.retrieve(query, student_sources, limit=budget)
        from .checks import validate_student_context

        checked = validate_student_context(
            trusted_sources, selected, word_budget=budget
        )
        if self.model_io_contract is None:
            self.last_context_selection = {
                "selected": [item["source_id"] for item in checked],
                "omitted": [],
                "max_input_bytes": None,
            }
            return checked
        base_bytes = len(base_text.encode("utf-8"))
        max_bytes = self.model_io_contract.max_input_bytes
        selected_for_input, omitted = [], []

        def composed_size(context):
            if not context:
                return base_bytes
            excerpt_text = "\n".join(
                f"[{item['source_id']}] {item['text']}" for item in context
            )
            return len(
                (
                    "REFERENCE MATERIAL\n"
                    + excerpt_text
                    + "\nOBSERVATION\n"
                    + base_text
                ).encode("utf-8")
            )

        for item in checked:
            trial = [*selected_for_input, dict(item)]
            size = composed_size(trial)
            if size <= max_bytes:
                selected_for_input.append(
                    dict(
                        item,
                        selection="included_in_model_input",
                        composed_input_bytes=size,
                    )
                )
            else:
                omitted.append(
                    {
                        "source_id": item["source_id"],
                        "reason": "complete_composed_input_exceeds_model_byte_envelope",
                        "candidate_input_bytes": size,
                    }
                )
        final_size = composed_size(selected_for_input)
        self.last_context_selection = {
            "selected": [item["source_id"] for item in selected_for_input],
            "omitted": omitted,
            "base_input_bytes": base_bytes,
            "composed_input_bytes": final_size,
            "max_input_bytes": max_bytes,
        }
        return tuple(selected_for_input)

    def implementation_sources(self):
        source = _source(self.component)
        return (source,) if source else ()


class WeightCodecMaterializer:
    """Run Lab 2's codec on every real q4 tensor in each fresh core image."""

    def __init__(self, materializer: Any, component: Any):
        _require(component, "pack_int4", "unpack_int4")
        if not callable(getattr(materializer, "materialize", None)):
            raise ContractError("A candidate materializer is required")
        self.materializer, self.component = materializer, component

    def materialize(self, task: Task, action: Action, workspace: Path) -> Candidate:
        candidate = self.materializer.materialize(task, action, workspace)
        candidate.validate_files()
        root = Path(candidate.root).resolve()
        image_path = root / "reference" / "image.bin"
        if not image_path.is_file():
            raise ContractError(
                "Lab 2 codec needs the current task's materialized weight image"
            )
        source_image_sha256 = file_sha256(image_path)
        image = bytearray(image_path.read_bytes())
        header = struct.unpack_from("<32I", image, 0)
        tensor_count, descriptor_addr = header[22], header[23]
        from ..teaching_core.compiler_layout import tensor_layout
        from ..teaching_core.contract import CONFIG

        tensor_entries, _ = tensor_layout(CONFIG)
        if tensor_count != len(tensor_entries):
            raise ContractError(
                "Weight descriptor count differs from the frozen teaching-core layout"
            )
        reports = []
        for index, (name, expected_bytes, _tag) in enumerate(tensor_entries):
            _name_hash, address, nbytes, _aux = struct.unpack_from(
                "<IIII", image, descriptor_addr + 16 * index
            )
            if nbytes != expected_bytes or address + nbytes > len(image):
                raise ContractError(f"Packed weight descriptor is invalid for {name}")
            if name != "emb.q" and not name.endswith(".q"):
                continue
            packed_source = bytes(image[address : address + nbytes])
            nibbles = tuple(
                nibble
                for byte in packed_source
                for nibble in (byte & 15, (byte >> 4) & 15)
            )
            expected = bytes(
                nibbles[offset] | (nibbles[offset + 1] << 4)
                for offset in range(0, len(nibbles), 2)
            )
            student_packed = self.component.pack_int4(nibbles)
            if isinstance(student_packed, (list, tuple, bytearray)):
                student_packed = bytes(student_packed)
            if not isinstance(student_packed, bytes) or student_packed != expected:
                raise ContractError(
                    f"Lab 2 packed {name} differs from the independent nibble oracle"
                )
            unpacked = tuple(self.component.unpack_int4(student_packed))
            if unpacked != nibbles:
                raise ContractError(
                    f"Lab 2 unpacked {name} differs from the original task weights"
                )
            image[address : address + nbytes] = student_packed
            reports.append(
                {
                    "tensor": name,
                    "nibble_count": len(nibbles),
                    "packed_sha256": __import__("hashlib")
                    .sha256(student_packed)
                    .hexdigest(),
                    "oracle_match": True,
                    "unpack_match": True,
                }
            )
        if not reports:
            raise ContractError(
                "No q4 packed weights were found in the materialized image"
            )
        image_path.write_bytes(image)
        artifacts = tuple(
            Artifact.from_file(root, item.path) for item in candidate.artifacts
        )
        result = replace(candidate, artifacts=artifacts)
        result.validate_files()
        evidence = {
            "schema": "nanochip-course-weight-codec/v1",
            "task_digest": task.digest,
            "candidate_action": action.name,
            "candidate_digest_after_codec": result.digest,
            "source_weight_image_sha256": source_image_sha256,
            "materialized_weight_image_sha256": file_sha256(image_path),
            "student_component_sha256": file_sha256(_source(self.component)),
            "tensors": reports,
            "scope": "task-specific packed int4 bytes checked through Lab 2 and consumed by the same RTL candidate",
        }
        with (Path(workspace) / "lab2-weight-codec.json").open(
            "x", encoding="utf-8"
        ) as stream:
            json.dump(evidence, stream, sort_keys=True, indent=2, allow_nan=False)
            stream.write("\n")
        return result

    def implementation_sources(self):
        values = []
        for item in (self.materializer, self.component):
            values.extend(
                item.implementation_sources()
                if hasattr(item, "implementation_sources")
                else ((_source(item),) if _source(item) else ())
            )
        return tuple(dict.fromkeys(values))


class SearchPolicyAdapter:
    """Use Lab 6's predictor and chooser around a learned campaign proposal."""

    def __init__(self, component: Any):
        _require(component, "predict", "choose")
        self.component = component
        self.predictions: dict[str, Mapping] = {}

    def observe_candidate(self, task: Task, candidate: Candidate) -> Mapping:
        prediction = self.component.predict(task, candidate)
        if not isinstance(prediction, Mapping) or not isinstance(
            prediction.get("metrics"), Mapping
        ):
            raise ContractError("Lab 6 predictor must return a metrics mapping")
        for name, value in prediction["metrics"].items():
            if (
                not isinstance(name, str)
                or not isinstance(value, Mapping)
                or type(value.get("value")) not in (int, float)
                or type(value.get("uncertainty")) not in (int, float)
                or value["uncertainty"] < 0
                or not isinstance(value.get("unit"), str)
                or not value["unit"]
            ):
                raise ContractError(
                    "Lab 6 predictions need value, unit, and nonnegative uncertainty"
                )
        self.predictions[candidate.digest] = dict(prediction)
        return prediction

    def proposer(self, learned_proposer, parse_action):
        adapter = self

        class _Proposer:
            def propose(self, task, history, budget):
                learned = learned_proposer.propose(task, history, budget)
                ordered = []
                if isinstance(learned, Action):
                    parsed = parse_action(learned.name, task.allowed_actions)
                    if parsed not in task.allowed_actions:
                        raise ContractError("Lab 5 parser returned an illegal action")
                    ordered.append(Action(parsed))
                ordered.extend(
                    Action(name)
                    for name in task.allowed_actions
                    if name not in {action.name for action in ordered}
                )
                selected = adapter.component.choose(
                    task, tuple(ordered), history, budget
                )
                if selected is None:
                    return None
                if not isinstance(selected, Action) or selected not in ordered:
                    raise ContractError(
                        "Lab 6 search policy must select one proposed legal action"
                    )
                return selected

            def implementation_sources(self):
                return adapter.implementation_sources()

        return _Proposer()

    def implementation_sources(self):
        source = _source(self.component)
        return (source,) if source else ()


class ArchitectureMaterializer:
    """Apply Lab 7's transformation to the exact candidate being evaluated."""

    def __init__(self, materializer: Any, component: Any):
        _require(component, "transform")
        if not callable(getattr(materializer, "materialize", None)):
            raise ContractError("A candidate materializer is required")
        self.materializer, self.component = materializer, component

    def materialize(self, task: Task, action: Action, workspace: Path) -> Candidate:
        candidate = self.materializer.materialize(task, action, workspace)
        if not isinstance(candidate, Candidate) or candidate.task_digest != task.digest:
            raise ContractError(
                "Base materializer returned a candidate for another frozen task"
            )
        candidate.validate_files()
        root = Path(candidate.root).resolve()
        source = root / "core.v"
        if not source.is_file():
            raise ContractError("Lab 7 transform requires candidate core.v")
        transformed = self.component.transform(
            source.read_text(encoding="utf-8"), action
        )
        if not isinstance(transformed, str) or not transformed:
            raise ContractError("Lab 7 transform must return complete RTL source text")
        source.write_text(transformed, encoding="utf-8")
        artifacts = tuple(
            Artifact.from_file(root, item.path) for item in candidate.artifacts
        )
        result = replace(candidate, artifacts=artifacts)
        result.validate_files()
        return result

    def implementation_sources(self):
        values = []
        for item in (self.materializer, self.component):
            values.extend(
                item.implementation_sources()
                if hasattr(item, "implementation_sources")
                else ((_source(item),) if _source(item) else ())
            )
        return tuple(dict.fromkeys(values))


class PredictingMaterializer:
    """Record Lab 6 estimates for the same Lab 7 candidate sent to the target."""

    def __init__(
        self, materializer: ArchitectureMaterializer, search: SearchPolicyAdapter
    ):
        self.materializer, self.search = materializer, search

    def materialize(self, task: Task, action: Action, workspace: Path) -> Candidate:
        candidate = self.materializer.materialize(task, action, workspace)
        prediction = self.search.observe_candidate(task, candidate)
        evidence = {
            "schema": "nanochip-course-search-prediction/v1",
            "task_digest": task.digest,
            "candidate_digest": candidate.digest,
            "action": action.name,
            "prediction": prediction,
            "scope": "Lab 6 estimate for the exact Lab 7 transformed candidate; not measured evidence",
        }
        prediction_path = Path(workspace) / "lab6-prediction.json"
        with prediction_path.open("x", encoding="utf-8") as stream:
            json.dump(evidence, stream, sort_keys=True, indent=2, allow_nan=False)
            stream.write("\n")
        return candidate

    def implementation_sources(self):
        return tuple(
            dict.fromkeys(
                (
                    *self.materializer.implementation_sources(),
                    *self.search.implementation_sources(),
                )
            )
        )


def interpret_physical_receipt(
    component: Any, raw: Mapping[str, Any], candidate_core: str | Path
) -> Mapping:
    """Ask Lab 8 to interpret a receipt after binding its source manifest to RTL."""
    _require(component, "summarize_physical_receipt")
    digest = file_sha256(candidate_core)
    source_manifest = raw.get("source_manifest")
    if not isinstance(source_manifest, Sequence):
        raise ContractError("Lab 8 receipt needs a source manifest")
    if not any(
        item.get("path") == "core.v" and item.get("sha256") == digest
        for item in source_manifest
        if isinstance(item, Mapping)
    ):
        raise ContractError(
            "Lab 8 receipt does not bind the exact checked core.v source"
        )
    receipt_identity = raw.get("candidate_sha256")
    if not isinstance(receipt_identity, str) or not receipt_identity:
        raise ContractError("Lab 8 receipt has no candidate identity")
    immutable_raw = deepcopy(dict(raw))
    result = component.summarize_physical_receipt(
        deepcopy(immutable_raw), receipt_identity
    )
    if not isinstance(result, Mapping):
        raise ContractError(
            "Lab 8 physical interpreter must return a named check mapping"
        )
    if dict(raw) != immutable_raw:
        raise ContractError("Lab 8 physical interpreter mutated its retained receipt")
    expected_checks = list(immutable_raw.get("checks", ()))
    expected_pass = immutable_raw.get("ok") is True and all(
        item.get("status") == "pass" for item in expected_checks
    )
    if (
        result.get("candidate_sha256") != receipt_identity
        or result.get("checks") != expected_checks
        or result.get("all_required_passed") is not expected_pass
    ):
        raise ContractError(
            "Lab 8 physical interpreter changed named checks or their acceptance state"
        )
    return dict(
        candidate_core_sha256=digest,
        physical_candidate_sha256=receipt_identity,
        interpreted_checks=dict(result),
        acceptance_scope="physical receipt for the bound candidate only",
    )


def assess_reused_physical_acceptance(
    *,
    adapted_actions: Sequence[str],
    physical_action: str,
    candidate_config: str | Path,
    raw_receipt: Mapping[str, Any],
    interpreted: Mapping,
    receipt_sha256: str | None,
    adapted_winners: Sequence[Mapping[str, Any]],
    mapped_workload_receipt: Mapping[str, Any] | None = None,
) -> Mapping:
    """Reuse Lab 8 only when exact winner RTL/config and mapped-workload evidence match."""
    actions = sorted(set(adapted_actions))
    config_digest = file_sha256(candidate_config)
    same_action = bool(actions) and set(actions) == {physical_action}
    same_config = raw_receipt.get("config_sha256") == config_digest
    lab8_core_digest = interpreted.get("candidate_core_sha256")
    winner_cores = sorted(
        {str(item.get("core_sha256", "")) for item in adapted_winners}
    )
    winner_configs = sorted(
        {str(item.get("config_sha256", "")) for item in adapted_winners}
    )
    same_winner_core = bool(adapted_winners) and winner_cores == [lab8_core_digest]
    same_winner_config = bool(adapted_winners) and winner_configs == [config_digest]
    physical_passed = (
        interpreted.get("interpreted_checks", {}).get("all_required_passed") is True
    )
    mapped = mapped_workload_receipt
    mapped_case = next(
        (
            item
            for item in adapted_winners
            if isinstance(mapped, Mapping)
            and item.get("case_id") == mapped.get("case_id")
        ),
        None,
    )
    mapped_fields = (
        "task_digest",
        "candidate_digest",
        "core_sha256",
        "config_sha256",
        "program_sha256",
        "tables_sha256",
        "image_sha256",
    )
    mapped_passed = bool(
        isinstance(mapped, Mapping)
        and mapped.get("status") == "pass"
        and mapped.get("mode") == "fresh"
        and mapped.get("mapped_netlist_sha256")
        and mapped.get("functional_golden_sha256")
        and mapped.get("receipt_sha256")
        and mapped_case
        and all(mapped.get(key) == mapped_case.get(key) for key in mapped_fields)
    )
    reasons = []
    if not same_action:
        reasons.append(
            "adapted held-out winner action differs from the Lab 8 physically checked action"
        )
    if not same_config:
        reasons.append(
            "physical configuration digest differs from the Lab 8 checked candidate"
        )
    if not same_winner_core:
        reasons.append(
            "an adapted held-out winner has different RTL bytes from the Lab 8 candidate"
        )
    if not same_winner_config:
        reasons.append(
            "an adapted held-out winner has different physical configuration bytes from Lab 8"
        )
    if not physical_passed:
        reasons.append("Lab 8 required physical checks are not all passing")
    if not mapped_passed:
        reasons.append(
            "fresh mapped-netlist execution evidence for the held-out workload winner is absent or unresolved"
        )
    return {
        "status": "accepted_by_reused_lab8_evidence"
        if not reasons
        else "pending_final_physical",
        "adapted_heldout_best_actions": actions,
        "adapted_heldout_winner_artifacts": [dict(item) for item in adapted_winners],
        "lab8_physically_checked_action": physical_action,
        "lab8_candidate_core_sha256": interpreted.get("candidate_core_sha256"),
        "lab8_candidate_config_sha256": config_digest,
        "physical_receipt_sha256": receipt_sha256,
        "checks": {
            "same_winner_action": same_action,
            "same_winner_core": same_winner_core,
            "same_winner_configs": same_winner_config,
            "same_physical_config": same_config,
            "physical_checks_pass": physical_passed,
            "fresh_mapped_netlist_workload_pass": mapped_passed,
            "mapped_workload_case_id": mapped.get("case_id")
            if isinstance(mapped, Mapping)
            else None,
        },
        "reasons": reasons,
        "scope": "reuses prior physical result only for identical winner RTL/config; no fresh P&R claim",
    }


class CourseComposition:
    """Ready-to-pass cumulative adapters for ``run_learning_campaign``."""

    def __init__(
        self,
        *,
        training_component: Any,
        representation_component: Any,
        search_component: Any,
        architecture_component: Any,
        weight_component: Any,
        base_materializer: Any,
        model_io_contract: Any,
        base_checkpoint: str | Path,
        physical_component: Any | None = None,
        receipt_component: Any | None = None,
    ):
        self.training = TrainingAdapter(
            training_component, model_io_contract, base_checkpoint=base_checkpoint
        )
        self.representation = RepresentationAdapter(
            representation_component, model_io_contract
        )
        self.search = SearchPolicyAdapter(search_component)
        codec = WeightCodecMaterializer(base_materializer, weight_component)
        architecture = ArchitectureMaterializer(codec, architecture_component)
        self.materializer = PredictingMaterializer(architecture, self.search)
        self.physical_component = physical_component
        self.receipt_component = receipt_component

    @property
    def name(self) -> str:
        return self.training.name

    def train(self, records: Sequence[Mapping], output: Path) -> Mapping:
        return self.training.train(records, output)

    def adapt(
        self, records: Sequence[Mapping], base_checkpoint: Path, output: Path
    ) -> Mapping:
        return self.training.adapt(records, base_checkpoint, output)

    def serialize(self, task: Task, history=(), context=()) -> str:
        return self.representation.serialize(task, history, context)

    def retriever(self):
        adapter = self.representation

        class _Retriever:
            def build(self, task, history, allowed_sources, budget):
                return adapter.retrieve(task, history, allowed_sources, budget)

            def implementation_sources(self):
                return adapter.implementation_sources()

        return _Retriever()

    def proposer(self, checkpoint: Path, format_input: Callable):
        return self.search.proposer(
            self.training.proposer(checkpoint, format_input),
            self.representation.component.parse_action,
        )

    def implementation_sources(self):
        items = [
            *self.training.implementation_sources(),
            *self.representation.implementation_sources(),
            *self.search.implementation_sources(),
            *self.materializer.implementation_sources(),
        ]
        if self.physical_component is not None:
            source = _source(self.physical_component)
            if source:
                items.append(source)
        if self.receipt_component is not None:
            source = _source(self.receipt_component)
            if source:
                items.append(source)
        return tuple(dict.fromkeys(items))

    def interpret_physical(
        self, raw: Mapping[str, Any], candidate_core: str | Path
    ) -> Mapping:
        if self.physical_component is None:
            raise ContractError("Lab 8 physical receipt interpreter was not supplied")
        return interpret_physical_receipt(self.physical_component, raw, candidate_core)

    def provenance(self) -> Mapping[str, str]:
        values = {
            "training": self.training.component,
            "representation": self.representation.component,
            "search": self.search.component,
            "weight_codec": self.materializer.materializer.materializer.component,
            "architecture": self.materializer.materializer.component,
        }
        if self.physical_component is not None:
            values["physical"] = self.physical_component
        if self.receipt_component is not None:
            values["harness"] = self.receipt_component
        return {
            name: file_sha256(path)
            for name, component in values.items()
            if (path := _source(component)) and Path(path).is_file()
        }
