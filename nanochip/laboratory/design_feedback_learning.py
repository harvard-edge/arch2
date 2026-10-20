"""One frozen, matched update from verified physical-tool feedback.

One measured area preference is exploratory evidence, even when its selected
candidate fails acceptance checks. The comparison changes the label source on
the same represented input; it cannot establish physical generalization.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import inspect
import json
from pathlib import Path
import random
import shutil
import time
from typing import Any

from . import design_learning as design, model_io
from .contracts import ContractError, canonical_json, file_sha256
from .design_feedback_data import load_feedback
from .models import load_model, train
from .models import sequence, proposer


CHECKPOINT_FILES = ("checkpoint.pt", "config.json", "tokenizer.json", "training.json")
SCOPE = ("single measured-area exploratory preference; matched-update label-source ablation; "
         "not acceptance evidence or held-out physical generalization")


def _write(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _checkpoint_hashes(path: Path) -> dict[str, str]:
    return {name: file_sha256(path / name) for name in CHECKPOINT_FILES}


def _snapshot_file(source: Path, destination: Path) -> dict[str, str]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    digest = file_sha256(source)
    if file_sha256(destination) != digest:
        raise ContractError("Snapshot differs from its source")
    return dict(source_path=str(source), path=str(destination), sha256=digest)


def _protocol(*, max_steps: int = 120, max_seconds: float = 30.0) -> dict[str, Any]:
    return dict(schema_version=1, seed=19, max_steps=max_steps, max_seconds=max_seconds,
                learning_rate=0.001, batch_size=16, replay_positive_multiplier=7,
                feedback_replicas=8, order=["control", "adapted"],
                stopping="fixed final checkpoint after all predeclared steps; incomplete updates rejected",
                checkpoint_selection="none; no target prediction or validation-driven selection",
                actions=list(design.ACTIONS),
                comparison="identical inputs, replay, random seed and batch schedule; label-source ablation",
                evaluation="original dev/test only after both checkpoints are frozen; regression diagnostic",
                test_protocol=(max_steps != 120 or max_seconds != 30.0))


def _regression_diagnostics(checkpoints: dict[str, Path], corpus: dict) -> dict:
    diagnostics = {}
    for name, checkpoint in checkpoints.items():
        decoder = load_model(checkpoint)
        values = {}
        for split in ("dev", "test"):
            rows = [row for row in corpus["records"] if row["split"] == split]
            result = decoder.evaluate(rows, model_io_contract=(
                design.DESIGN_MODEL_IO if decoder.model_io_contract is not None else None))
            counts = Counter(row["target_action"] for row in rows)
            correct = Counter(prediction["target_action"] for prediction in result["predictions"]
                              if prediction["action"] == prediction["target_action"])
            result.update(class_counts={action: counts[action] for action in design.ACTIONS},
                          per_action_correct_counts={action: correct[action] for action in design.ACTIONS},
                          per_action_accuracy={action: correct[action] / counts[action]
                                               if counts[action] else None for action in design.ACTIONS},
                          interpretation="post-adaptation regression diagnostic on original constructed labels; "
                                         "not new physical generalization")
            values[split] = result
        diagnostics[name] = values
    return diagnostics


def adapt_from_feedback(base_checkpoint: Path, corpus_manifest: Path,
                        feedback_manifest: Path, output: Path) -> dict:
    """Freeze evidence and protocol, then run control and feedback updates once.

The public experiment has no tuning or stopping arguments. It always uses seed
19, 120 steps, 30 seconds per update, batch size 16, and learning rate 0.001.
Both actions remain available. This function never predicts a physical target
or chooses a design candidate.
    """
    return _adapt_from_feedback(base_checkpoint, corpus_manifest, feedback_manifest, output,
                                protocol=_protocol())


def _adapt_from_feedback(base_checkpoint: Path, corpus_manifest: Path,
                         feedback_manifest: Path, output: Path, *, protocol: dict) -> dict:
    """Internal harness permits short protocols in CPU unit tests only."""
    started = time.perf_counter()
    base_path, feedback_path, root = (Path(path).resolve()
                                      for path in (base_checkpoint, feedback_manifest, output))
    if root.exists():
        raise ContractError("Feedback adaptation output must be a new directory")
    if root.is_relative_to(base_path) or root.is_relative_to(feedback_path.parent):
        raise ContractError("Feedback adaptation output cannot be inside original evidence or checkpoint")
    corpus, corpus_path = design._load_manifest(corpus_manifest)
    if root.is_relative_to(corpus_path.parent):
        raise ContractError("Feedback adaptation output cannot be inside the original corpus")
    feedback = load_feedback(feedback_path)
    records = feedback.get("records", [])
    if len(records) != 1:
        raise ContractError("This frozen adaptation admits exactly one measured feedback example")
    feedback_row = dict(records[0])
    features = design._features(feedback["target_features"])
    represented_input = design.design_input(features)
    if (feedback_row.get("split") != "train" or feedback_row.get("original_split") in ("dev", "test")
            or feedback_row.get("input_text") != represented_input
            or feedback_row.get("target_action") != feedback.get("selected_action")
            or feedback_row.get("target_action") not in design.ACTIONS):
        raise ContractError("Feedback row must preserve its verified train assignment, input and selected action")
    train_rows = [dict(row) for row in corpus["records"] if row["split"] == "train"]
    if len(train_rows) != 32 or any(not any(row["split"] == split for row in corpus["records"])
                                    for split in ("dev", "test")):
        raise ContractError("Adaptation requires the original 32-row train corpus and dev/test partitions")
    held_out = [row for row in corpus["records"] if row["split"] in ("dev", "test")]
    for key in ("record_id", "group_id", "input_text", "source_sha256"):
        if feedback_row.get(key) in {row[key] for row in held_out}:
            raise ContractError("Measured feedback overlaps the original held-out corpus")
    replay = list(train_rows)
    positive = [row for row in train_rows if row["target_action"] == design.ACTIONS[0]]
    for repeat in range(6):
        replay.extend(dict(row, record_id=f"{row['record_id']}-repeat-{repeat}",
                           sampling_replica_of=row["record_id"]) for row in positive)
    if len(replay) != 56:
        raise ContractError("Original replay must have 56 rows with sevenfold positive oversampling")
    base_hashes = _checkpoint_hashes(base_path)
    base = load_model(base_path)
    if base.actions != list(design.ACTIONS):
        raise ContractError("Feedback adaptation requires both original actions")
    base_parameter_hash = sequence._parameter_sha256(base.model)
    if base_parameter_hash != base.metadata["final_parameter_sha256"]:
        raise ContractError("Base parameter hash differs from its training metadata")
    # Do not let a different corpus quietly replace the one that trained base.
    ancestors = base.metadata["training_records"]
    if ancestors != replay:
        raise ContractError("Base checkpoint must have exactly the disclosed original train replay")
    if protocol != _protocol(max_steps=protocol["max_steps"], max_seconds=protocol["max_seconds"]):
        raise ContractError("Protocol differs from the predeclared matched update")

    root.mkdir(parents=True)
    checkpoints = {"base": root / "base", "control": root / "control", "adapted": root / "adapted"}
    shutil.copytree(base_path, checkpoints["base"])
    snapshots = {"base_checkpoint": {name: dict(path=str(checkpoints["base"] / name), sha256=digest)
                                      for name, digest in base_hashes.items()},
                 "corpus_manifest": _snapshot_file(corpus_path, root / "evidence/corpus/manifest.json"),
                 "feedback_manifest": _snapshot_file(feedback_path, root / "evidence/feedback/manifest.json"),
                 "corpus_sources": [], "feedback_sources": [], "code": []}
    for row in corpus["records"]:
        relative = Path(row["source_receipt"]["path"])
        snapshots["corpus_sources"].append(_snapshot_file(corpus_path.parent / relative,
                                                          root / "evidence/corpus" / relative))
    replay = [dict(row, source_receipt=dict(path=str(root / "evidence/corpus" / row["source_receipt"]["path"]),
                                            sha256=row["source_sha256"])) for row in replay]
    evidence_receipt = feedback_row["source_receipt"]
    evidence_source = Path(evidence_receipt["path"])
    if not evidence_source.is_absolute():
        evidence_source = feedback_path.parent / evidence_source
    receipt_snapshot = _snapshot_file(evidence_source, root / "evidence/feedback/evidence.json")
    if receipt_snapshot["sha256"] != feedback_row["source_sha256"]:
        raise ContractError("Verified feedback receipt changed before snapshot")
    snapshots["feedback_sources"].append(receipt_snapshot)
    for source in feedback.get("source_files", []):
        if file_sha256(source["path"]) != source["sha256"]:
            raise ContractError("Feedback source changed before snapshot")
        snapshots["feedback_sources"].append(dict(source_path=source["path"], sha256=source["sha256"],
                                                   storage="hash-bound original artifact; retained by evidence manifest"))
    for copied in feedback.get("copied_evidence", []):
        relative = Path(copied["path"])
        snapshots["feedback_sources"].append(_snapshot_file(feedback_path.parent / relative,
                                                             root / "evidence/feedback" / relative))
    code_files = {Path(__file__).resolve(), Path(design.__file__).resolve(),
                  Path(sequence.__file__).resolve(), Path(proposer.__file__).resolve(),
                  Path(model_io.__file__).resolve(),
                  Path(inspect.getfile(load_feedback)).resolve()}
    for source in sorted(code_files):
        snapshots["code"].append(_snapshot_file(source, root / "source_code" / source.name))
    feedback_row["source_receipt"] = dict(path=receipt_snapshot["path"], sha256=receipt_snapshot["sha256"])
    constructed_source = dict(schema_version=1, construction="original author-constructed instructional label",
                              design_features=features, input_text=represented_input,
                              target_action=design._instructional_label(features),
                              label_origin=design.LABEL_ORIGIN,
                              scope="matched update comparator; no measured feedback label",
                              represented_feedback_manifest_sha256=file_sha256(feedback_path))
    constructed_path = root / "evidence/constructed_control.json"
    _write(constructed_path, constructed_source)
    control_row = dict(feedback_row, target_action=constructed_source["target_action"],
                       label_origin=design.LABEL_ORIGIN, source_sha256=file_sha256(constructed_path),
                       source_receipt=dict(path=str(constructed_path), sha256=file_sha256(constructed_path)))
    # Both branches retain the same row identities/order and represented inputs.
    updates = {}
    for name, row in (("control", control_row), ("adapted", feedback_row)):
        additions = [dict(row, record_id=f"{row['record_id']}-adaptation-{replica}",
                          sampling_replica_of=row["record_id"], adaptation_replica=replica)
                     for replica in range(8)]
        updates[name] = replay + additions
        _write(root / f"{name}_update_records.json", updates[name])
    if [row["input_text"] for row in updates["control"]] != [row["input_text"] for row in updates["adapted"]]:
        raise ContractError("Matched updates must have identical represented inputs")
    generator = random.Random(protocol["seed"])
    batch_schedule = [[row["record_id"] for row in generator.sample(updates["control"], protocol["batch_size"])]
                      for _ in range(protocol["max_steps"])]
    protocol = dict(protocol, base_parameter_sha256=base_parameter_hash,
                    snapshots=snapshots, constructed_control_sha256=file_sha256(constructed_path),
                    update_records_sha256={name: file_sha256(root / f"{name}_update_records.json")
                                           for name in updates},
                    input_schedule_sha256=_digest([row["input_text"] for row in updates["control"]]),
                    batch_record_ids=batch_schedule, batch_schedule_sha256=_digest(batch_schedule))
    protocol_path = root / "protocol.json"
    _write(protocol_path, protocol)
    protocol_hash = file_sha256(protocol_path)
    (root / "protocol.sha256").write_text(protocol_hash + "\n", encoding="utf-8")

    training = {}
    for name in ("control", "adapted"):
        if file_sha256(protocol_path) != protocol_hash:
            raise ContractError("Frozen protocol changed before parameter updates")
        training[name] = train(updates[name], checkpoints[name], seed=protocol["seed"],
                               max_steps=protocol["max_steps"], max_seconds=protocol["max_seconds"],
                               batch_size=protocol["batch_size"], learning_rate=protocol["learning_rate"],
                               base_checkpoint=checkpoints["base"], action_vocabulary=design.ACTIONS)
    for result in training.values():
        if (result["initial_parameter_sha256"] != base_parameter_hash
                or not result["parameters_changed"] or result["steps_completed"] != protocol["max_steps"]):
            raise ContractError("Matched updates require the same base parameters and every predeclared update step")
    if _checkpoint_hashes(base_path) != base_hashes or _checkpoint_hashes(checkpoints["base"]) != base_hashes:
        raise ContractError("Base checkpoint changed during adaptation")
    frozen = {name: _checkpoint_hashes(path) for name, path in checkpoints.items()}
    diagnostics = _regression_diagnostics(checkpoints, corpus)
    if any(_checkpoint_hashes(checkpoints[name]) != hashes for name, hashes in frozen.items()):
        raise ContractError("Checkpoint changed during regression diagnostics")
    if file_sha256(protocol_path) != protocol_hash:
        raise ContractError("Frozen protocol changed during adaptation")
    if ((root / "protocol.sha256").read_text(encoding="utf-8").strip() != protocol_hash
            or file_sha256(corpus_path) != snapshots["corpus_manifest"]["sha256"]
            or file_sha256(feedback_path) != snapshots["feedback_manifest"]["sha256"]
            or any(file_sha256(root / f"{name}_update_records.json") != digest
                   for name, digest in protocol["update_records_sha256"].items())):
        raise ContractError("Frozen adaptation evidence or update records changed")
    report = dict(schema_version=1, scope=SCOPE, checkpoints={name: str(path) for name, path in checkpoints.items()},
                  checkpoint_hashes=frozen, protocol_path=str(protocol_path), protocol_sha256=protocol_hash,
                  protocol=protocol, training=training, diagnostics=diagnostics, allowed_actions=list(design.ACTIONS),
                  lineage=dict(base_checkpoint_path=str(base_path), base_checkpoint_hashes=base_hashes,
                               base_parameter_sha256=base_parameter_hash, base_bytes_unchanged=True,
                               corpus_manifest_sha256=file_sha256(corpus_path),
                               feedback_manifest_sha256=file_sha256(feedback_path),
                               snapshots=snapshots),
                  update_counts=dict(original_train_rows=32, replay_rows=56, measured_examples=1,
                                     feedback_replicas=8, rows_per_update=64),
                  comparison="matched update label-source ablation; same inputs and batches; both final checkpoints retained",
                  selection="no target prediction, candidate selection, or checkpoint iteration",
                  cost=dict(total_wall_seconds=time.perf_counter() - started,
                            update_wall_seconds={name: values["total_wall_seconds"] for name, values in training.items()},
                            steps_per_update={name: values["steps_completed"] for name, values in training.items()}))
    _write(root / "report.json", report)
    return report
