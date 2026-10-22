"""Learn a narrow RTL action preference from disclosed, constructed tasks.

This is author-constructed instruction imitation, not an RTL language model,
measured optimal-PPA labels, or evidence of architectural benefit. The two
actions concern one representation change: consume a packed four-bit row in
ascending order by reading its low nibble and shifting right after each write,
or keep indexed access. A separate candidate/check/tool flow must establish
correctness and physical consequences for any emitted action.

The input is a compact direct serialization of semantic workload facts. The
curator rule below creates training labels only; inference is exclusively the
saved byte-GRU decoder through the shared ``LearnedProposer`` protocol. Both
actions remain available. No target description is inserted into training.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .contracts import ContractError, Task, canonical_json, file_sha256
from .model_io import ModelIOContract
from .models import LearnedProposer, load_model, train


ACTIONS = ("stream_quantized_row", "retain_indexed_read")
INPUT_SCHEMA = "packed_row_semantics_v1"
DESIGN_MODEL_IO = ModelIOContract(
    INPUT_SCHEMA, 1, "nanochip.design_input.v1", ACTIONS, 128
)
LABEL_ORIGIN = "author_constructed_legality_and_engineering_preference_v1; not measured optimal PPA"
SCOPE = "constructed packed-four-bit-row action imitation; no architectural or physical benefit claim"
FEATURE_KEYS = (
    "row_values",
    "quant_bits",
    "reload_per_row",
    "access_order",
    "index_step",
    "start_index",
    "passes",
    "revisit",
)
# Predeclared workload conditions. Distinct row lengths and repeated-access
# counts separate partitions; these are still related constructed task families,
# not independent real-world workloads. No validation-driven model selection.
PARTITIONS = {
    "train": {"row_values": (8, 24, 48, 96), "extra_passes": 2, "skip_step": 2},
    "dev": {"row_values": (12, 40, 80), "extra_passes": 3, "skip_step": 3},
    "test": {"row_values": (20, 56, 112), "extra_passes": 4, "skip_step": 5},
}


def _features(task: Task | Mapping[str, Any]) -> dict[str, Any]:
    source = task.specification if isinstance(task, Task) else task
    source = source.get("design_features", source)
    if not isinstance(source, Mapping) or any(
        key not in source for key in FEATURE_KEYS
    ):
        raise ContractError("Design tasks require all declared design_features")
    values = {key: source[key] for key in FEATURE_KEYS}
    for key in ("row_values", "quant_bits", "index_step", "start_index", "passes"):
        if type(values[key]) is not int:
            raise ContractError(f"Design feature {key} must be an integer")
    if (
        values["row_values"] < 1
        or values["quant_bits"] != 4
        or values["passes"] < 1
        or values["index_step"] < 1
        or not 0 <= values["start_index"] < values["row_values"]
    ):
        raise ContractError(
            "Design features require a valid packed four-bit row access"
        )
    if values["access_order"] not in ("ascending", "descending", "permuted"):
        raise ContractError("Unknown row access order")
    if any(type(values[key]) is not bool for key in ("reload_per_row", "revisit")):
        raise ContractError("Row reload and revisit features must be explicit booleans")
    return values


def design_input(task: Task | Mapping[str, Any], history=()) -> str:
    """Serialize only directly declared facts, without identity, labels, or rules.

    ``Task.specification['design_features']`` uses FEATURE_KEYS. History is
    deliberately unused: this first-action model has no feedback vocabulary.
    The short suffix retains informative facts for the small recurrent model.
    """
    f = _features(task)
    return (
        f"n={f['row_values']};q={f['quant_bits']};load={int(f['reload_per_row'])};"
        f"order={f['access_order']};step={f['index_step']};start={f['start_index']};"
        f"passes={f['passes']};reuse={int(f['revisit'])}"
    )


def _instructional_label(features: Mapping[str, Any]) -> str:
    """Curator preference only; never consulted by a loaded proposer."""
    return (
        ACTIONS[0]
        if features["access_order"] == "ascending"
        and features["index_step"] == 1
        and features["start_index"] == 0
        and features["passes"] == 1
        and not features["revisit"]
        and features["reload_per_row"]
        else ACTIONS[1]
    )


def _write(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def collect_design_examples(output_dir: str | Path) -> dict[str, Any]:
    """Write constructed descriptions, source receipts, and a frozen manifest.

    Each row length contributes one positive and seven negative examples.
    Positive examples are intentionally repeated across four row lengths and
    not padded to balance classes; the report includes the majority baseline.
    No synthesis, simulation, target inspection, or external dataset is implied.
    Existing nonempty output directories are rejected.
    """
    root = Path(output_dir).resolve()
    if root.exists() and any(root.iterdir()):
        raise ContractError("Design corpus output must be absent or empty")
    root.mkdir(parents=True, exist_ok=True)
    (root / "cases").mkdir()
    records = []
    for split, conditions in PARTITIONS.items():
        for n in conditions["row_values"]:
            base = dict(
                row_values=n,
                quant_bits=4,
                reload_per_row=True,
                access_order="ascending",
                index_step=1,
                start_index=0,
                passes=1,
                revisit=False,
            )
            variants = (
                {},
                {"access_order": "descending", "start_index": n - 1},
                {"access_order": "permuted"},
                {"index_step": conditions["skip_step"]},
                {"start_index": n // 2},
                {"passes": conditions["extra_passes"]},
                {"revisit": True},
                {"reload_per_row": False},
            )
            for variation in variants:
                features = base | variation
                index = len(records)
                source = {
                    "schema": INPUT_SCHEMA,
                    "construction": "author-constructed semantic workload; no measured design trace",
                    "description": (
                        f"Consume a packed row of {n} four-bit values. The declared access "
                        "order, step, initial index, rereads, pass count, and row reload "
                        "describe the required behavior, not its preferred implementation."
                    ),
                    "design_features": features,
                }
                relative = f"cases/{index:03d}.json"
                _write(root / relative, source)
                digest = file_sha256(root / relative)
                records.append(
                    dict(
                        record_id=f"design-{index:03d}",
                        group_id=f"row-condition-{n}",
                        split=split,
                        original_split=split,
                        input_text=design_input(features),
                        target_action=_instructional_label(features),
                        source_receipt={"path": relative, "sha256": digest},
                        source_sha256=digest,
                        label_origin=LABEL_ORIGIN,
                    )
                )
    manifest = dict(
        schema_version=1,
        input_schema=INPUT_SCHEMA,
        scope=SCOPE,
        construction="author_constructed_semantic_tasks",
        label_origin=LABEL_ORIGIN,
        actions=list(ACTIONS),
        partitions=PARTITIONS,
        records=records,
        generator_sha256=file_sha256(__file__),
        split_policy="disjoint row-length conditions and disjoint repeated-pass/skip magnitudes",
        limitations=[
            "related synthetic families, not independent natural workloads",
            "labels encode a disclosed engineering heuristic, not measured optimal PPA",
            "no target observations or physical results in training",
        ],
        manifest_path=str(root / "manifest.json"),
    )
    _write(root / "manifest.json", manifest)
    return manifest


def _load_manifest(manifest: str | Path | Mapping[str, Any]) -> tuple[dict, Path]:
    path = Path(
        manifest["manifest_path"] if isinstance(manifest, Mapping) else manifest
    ).resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    if (
        data.get("schema_version") != 1
        or data.get("input_schema") != INPUT_SCHEMA
        or data.get("actions") != list(ACTIONS)
    ):
        raise ContractError("Unsupported design corpus schema or actions")
    groups: dict[str, str] = {}
    inputs: set[str] = set()
    for row in data["records"]:
        relative = Path(row["source_receipt"]["path"])
        source_path = (path.parent / relative).resolve()
        if relative.is_absolute() or not source_path.is_relative_to(path.parent):
            raise ContractError("Design source receipt escapes corpus")
        digest = file_sha256(source_path)
        if digest != row["source_sha256"] or digest != row["source_receipt"]["sha256"]:
            raise ContractError("Design source receipt content changed")
        source = json.loads(source_path.read_text(encoding="utf-8"))
        if (
            row["input_text"] != design_input(source)
            or row["label_origin"] != LABEL_ORIGIN
            or row["target_action"] != _instructional_label(_features(source))
        ):
            raise ContractError(
                "Design input/label differs from its disclosed source construction"
            )
        if row["split"] != row.get("original_split"):
            raise ContractError("Design corpus partition was reassigned")
        if row["group_id"] in groups and groups[row["group_id"]] != row["split"]:
            raise ContractError("Design workload group crosses partitions")
        groups[row["group_id"]] = row["split"]
        if row["input_text"] in inputs:
            raise ContractError("Design corpus repeats an exact input")
        inputs.add(row["input_text"])
    return data, path


def train_design_proposer(
    manifest: str | Path | Mapping[str, Any],
    output_dir: str | Path,
    *,
    seed: int = 17,
    max_steps: int = 360,
    max_seconds: float = 45.0,
) -> dict[str, Any]:
    """Freeze one CPU checkpoint, then report held-out imitation diagnostics.

    Train/dev/test are distinct declared workload conditions. Neither held-out
    accuracy nor an eventual target prediction selects updates, hyperparameters,
    stopping, or a checkpoint. The model is compatible with LearnedProposer
    using ``design_input``. Inference preserves the complete two-action set.
    """
    corpus, manifest_path = _load_manifest(manifest)
    root = Path(output_dir).resolve()
    if root.exists():
        raise ContractError("Design training output must be a new directory")
    split_rows = {
        split: [row for row in corpus["records"] if row["split"] == split]
        for split in ("train", "dev", "test")
    }
    if any(not rows for rows in split_rows.values()):
        raise ContractError("Design training requires all three predeclared partitions")
    # Freeze the constant comparator from original training frequencies, before
    # oversampling or examining held-out labels.
    train_counts = Counter(row["target_action"] for row in split_rows["train"])
    majority_action = max(ACTIONS, key=lambda action: train_counts[action])
    # Sampling repeats only train rows to counter the declared 1:7 imbalance.
    # Keep original identities in train metadata; class weights are implemented
    # by deterministic oversampling with explicitly marked replica provenance.
    training_rows = list(split_rows["train"])
    positive = [row for row in training_rows if row["target_action"] == ACTIONS[0]]
    for repeat in range(6):
        training_rows.extend(
            dict(
                row,
                record_id=f"{row['record_id']}-repeat-{repeat}",
                sampling_replica_of=row["record_id"],
            )
            for row in positive
        )
    training = train(
        training_rows,
        root / "checkpoint",
        seed=seed,
        max_steps=max_steps,
        max_seconds=max_seconds,
        action_vocabulary=ACTIONS,
        batch_size=16,
        learning_rate=0.008,
        max_input_bytes=128,
        embedding_dim=12,
        hidden_dim=40,
        model_io_contract=DESIGN_MODEL_IO,
    )
    frozen = file_sha256(root / "checkpoint/checkpoint.pt")
    decoder = load_model(
        root / "checkpoint", expected_model_io_contract=DESIGN_MODEL_IO
    )
    diagnostics = {
        split: decoder.evaluate(split_rows[split], model_io_contract=DESIGN_MODEL_IO)
        for split in ("dev", "test")
    }
    if file_sha256(root / "checkpoint/checkpoint.pt") != frozen:
        raise ContractError("Checkpoint changed during held-out evaluation")
    for split, values in diagnostics.items():
        count = Counter(row["target_action"] for row in split_rows[split])
        values["majority_action"] = majority_action
        values["majority_action_accuracy"] = count[majority_action] / sum(
            count.values()
        )
        values["class_counts"] = dict(count)
        values["per_action_accuracy"] = {
            action: sum(
                p["action"] == action
                for p in values["predictions"]
                if p["target_action"] == action
            )
            / count[action]
            for action in ACTIONS
        }
    report = dict(
        schema_version=1,
        scope=SCOPE,
        label_origin=LABEL_ORIGIN,
        checkpoint_dir=str(root / "checkpoint"),
        checkpoint_sha256=frozen,
        corpus_manifest_path=str(manifest_path),
        corpus_manifest_sha256=file_sha256(manifest_path),
        selection="single predeclared configuration; checkpoint frozen before dev/test and target",
        sampling="sevenfold positive train-row oversampling, no held-out updates",
        training=training,
        diagnostics=diagnostics,
        allowed_actions=list(ACTIONS),
        model_io_contract=DESIGN_MODEL_IO.to_dict(),
        inference="LearnedProposer(checkpoint_dir, design_input); no post-model action substitution",
    )
    _write(root / "report.json", report)
    return report


def design_proposer(checkpoint_dir: str | Path) -> LearnedProposer:
    """Return the shared learned proposer, requiring both actions on the task.

    The task factory/runner owns the declaration of both allowed actions. This
    wrapper rejects a vocabulary mismatch instead of silently masking a choice.
    """

    def complete_vocabulary_input(task, history):
        if not set(ACTIONS).issubset(task.allowed_actions):
            raise ContractError("Design inference must leave both actions available")
        return design_input(task, history)

    # Retained pre-contract checkpoints stay explicitly legacy/unbound. New
    # checkpoints must agree with the representation used by this adapter.
    recorded = load_model(checkpoint_dir).model_io_contract
    proposer = LearnedProposer(
        checkpoint_dir,
        complete_vocabulary_input,
        model_io_contract=DESIGN_MODEL_IO if recorded is not None else None,
    )
    if proposer.decoder.actions != list(ACTIONS):
        raise ContractError(
            "Design proposer requires the complete frozen two-action vocabulary"
        )
    return proposer
