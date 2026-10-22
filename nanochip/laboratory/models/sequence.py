"""Editable, bounded CPU training for observation -> action -> end sequences.

Input bytes are context only: next-token loss is applied to the action token
and end token. Atomic action tokens give an explicit finite output grammar.
Inference masks the logits to that grammar, rather than repairing a model's
answer with a conventional policy. This small corpus/model exercise does not
establish language competence or an architecture advantage.
"""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path
import random
import time
from typing import Any, Mapping, Sequence

from ..contracts import ContractError, canonical_json, file_sha256
from ..model_io import ModelIOContract

PAD, BOS, SEP, EOS = 0, 1, 2, 3
BYTE_OFFSET, ACTION_OFFSET = 4, 260


def _torch():
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "The optional sequence decoder requires an installed CPU PyTorch"
        ) from exc
    return torch


@contextmanager
def _cpu_threads(torch):
    previous = torch.get_num_threads()
    torch.set_num_threads(min(2, previous))
    try:
        yield
    finally:
        torch.set_num_threads(previous)


def build_model(config: Mapping[str, Any]):
    """The whole trainable model: byte/action embedding, one GRU, linear head."""
    torch = _torch()

    class ActionGRU(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.embedding = torch.nn.Embedding(
                config["vocab_size"], config["embedding_dim"], padding_idx=PAD
            )
            self.recurrent = torch.nn.GRU(
                config["embedding_dim"], config["hidden_dim"], batch_first=True
            )
            self.head = torch.nn.Linear(config["hidden_dim"], config["vocab_size"])

        def forward(self, tokens, hidden=None):
            states, hidden = self.recurrent(self.embedding(tokens), hidden)
            return self.head(states), hidden

    return ActionGRU().cpu()


def _validate_records(
    records: Sequence[Mapping[str, Any]], *, split: str | None = None
):
    rows = [dict(row) for row in records]
    if not rows:
        raise ContractError("A nonempty sequence dataset is required")
    required = (
        "record_id",
        "group_id",
        "split",
        "input_text",
        "target_action",
        "source_sha256",
        "label_origin",
    )
    ids: set[str] = set()
    for row in rows:
        if any(
            not isinstance(row.get(key), str) or not row[key].strip()
            for key in required
        ):
            raise ContractError(
                "Sequence records need nonempty identity, split, text, label, and provenance"
            )
        if row["record_id"] in ids:
            raise ContractError("Duplicate sequence record identity")
        ids.add(row["record_id"])
        if row["split"] not in ("train", "dev", "test"):
            raise ContractError("Unknown sequence partition")
        if split is not None and row["split"] != split:
            raise ContractError(
                f"Parameter updates accept only explicitly assigned {split} records"
            )
        if split == "train" and row.get("original_split") == "test":
            raise ContractError(
                "Final-test evidence cannot be reassigned for parameter updates"
            )
        receipt = row.get("source_receipt")
        if not (
            isinstance(receipt, str)
            and receipt.strip()
            or isinstance(receipt, Mapping)
            and isinstance(receipt.get("path"), str)
            and receipt["path"].strip()
            and isinstance(receipt.get("sha256"), str)
            and len(receipt["sha256"]) == 64
            and all(char in "0123456789abcdef" for char in receipt["sha256"])
        ):
            raise ContractError("A sequence record needs its source receipt identity")
        digest = row["source_sha256"]
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ContractError("Sequence source_sha256 must be a lowercase SHA-256")
    return rows


def _receipt_identity(row):
    receipt = row["source_receipt"]
    return receipt["sha256"] if isinstance(receipt, Mapping) else receipt


def _encode_input(text: str, max_input_bytes: int) -> list[int]:
    data = text.encode("utf-8")
    if len(data) > max_input_bytes:
        raise ContractError(
            f"Input has {len(data)} UTF-8 bytes; configured maximum is {max_input_bytes}; no truncation applied"
        )
    return [BOS] + [BYTE_OFFSET + byte for byte in data] + [SEP]


def _batch(rows, config, action_ids, torch):
    sequences, labels = [], []
    for row in rows:
        prompt = _encode_input(row["input_text"], config["max_input_bytes"])
        action = action_ids[row["target_action"]]
        # At SEP predict action; at action predict EOS. Prompt positions have no loss.
        sequences.append(prompt + [action])
        labels.append([-100] * (len(prompt) - 1) + [action, EOS])
    width = max(map(len, sequences))
    x = torch.full((len(rows), width), PAD, dtype=torch.long)
    y = torch.full((len(rows), width), -100, dtype=torch.long)
    for index, (sequence, target) in enumerate(zip(sequences, labels)):
        x[index, : len(sequence)] = torch.tensor(sequence)
        y[index, : len(target)] = torch.tensor(target)
    return x, y


def _parameter_sha256(model) -> str:
    digest = hashlib.sha256()
    for name, value in sorted(model.state_dict().items()):
        digest.update(name.encode())
        digest.update(value.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def _loss(model, rows, config, actions, torch) -> float:
    model.eval()
    total, count = 0.0, 0
    with torch.no_grad():
        for offset in range(0, len(rows), 16):
            batch = rows[offset : offset + 16]
            x, y = _batch(batch, config, actions, torch)
            logits, _ = model(x)
            value = torch.nn.functional.cross_entropy(
                logits.flatten(0, 1), y.flatten(), ignore_index=-100
            )
            total += float(value) * len(batch)
            count += len(batch)
    return total / count


def train(
    records: Sequence[Mapping[str, Any]],
    output_dir: str | Path,
    *,
    seed: int = 0,
    max_steps: int = 300,
    max_seconds: float = 30.0,
    batch_size: int = 16,
    learning_rate: float = 0.01,
    action_vocabulary: Sequence[str] | None = None,
    base_checkpoint: str | Path | None = None,
    max_input_bytes: int | None = None,
    embedding_dim: int = 16,
    hidden_dim: int = 32,
    model_io_contract: ModelIOContract | None = None,
) -> dict[str, Any]:
    """Train only designated train rows and save a new, inspectable checkpoint.

    Adaptation uses base_checkpoint's weights, tokenizer, and architecture. It
    cannot change the action vocabulary. Dataset admission/receipt validation
    belongs to the corpus loader; this function retains its provenance fields.
    No validation or final-test outcomes influence gradient updates or stopping.
    The wall budget bounds optimization; measured total also includes import,
    initialization, loss measurements, serialization, and thread restoration.
    A declared model_io_contract binds representation semantics into the saved
    config. Adaptation inherits that declaration and cannot reinterpret it.
    Omission on fresh training explicitly creates a legacy unbound checkpoint.
    """
    started = time.perf_counter()
    rows = _validate_records(records, split="train")
    if (
        type(max_steps) is not int
        or not 1 <= max_steps <= 10000
        or type(batch_size) is not int
        or not 1 <= batch_size <= 128
        or not math.isfinite(max_seconds)
        or not 0 < max_seconds <= 300
        or not math.isfinite(learning_rate)
        or not 0 < learning_rate <= 1
    ):
        raise ContractError(
            "Training requires bounded positive steps, seconds, batch size, and learning rate"
        )
    destination = Path(output_dir)
    if destination.exists():
        raise ContractError("Training output must be a new directory")
    if model_io_contract is not None and not isinstance(
        model_io_contract, ModelIOContract
    ):
        raise ContractError("model_io_contract must be a ModelIOContract")
    base = load_model(base_checkpoint) if base_checkpoint is not None else None
    if base is not None:
        if base.model_io_contract is not None:
            if model_io_contract is not None:
                base.model_io_contract.require_match(model_io_contract)
            model_io_contract = base.model_io_contract
        elif model_io_contract is not None:
            raise ContractError(
                "An unbound legacy checkpoint cannot acquire a representation contract through adaptation"
            )
    if model_io_contract is not None:
        if (
            action_vocabulary is not None
            and tuple(action_vocabulary) != model_io_contract.actions
        ):
            raise ContractError(
                "Action vocabulary differs from the model input contract"
            )
        if (
            max_input_bytes is not None
            and max_input_bytes != model_io_contract.max_input_bytes
        ):
            raise ContractError(
                "Input byte limit differs from the model input contract"
            )
        action_vocabulary = model_io_contract.actions
        max_input_bytes = model_io_contract.max_input_bytes
        for row in rows:
            model_io_contract.validate_text(row["input_text"])
    if max_input_bytes is None:
        max_input_bytes = base.config["max_input_bytes"] if base is not None else 2048
    actions = (
        list(action_vocabulary)
        if action_vocabulary is not None
        else sorted({row["target_action"] for row in rows})
    )
    if (
        not actions
        or len(set(actions)) != len(actions)
        or any(not isinstance(action, str) or not action.strip() for action in actions)
    ):
        raise ContractError("Action vocabulary must contain distinct nonempty strings")
    if any(row["target_action"] not in actions for row in rows):
        raise ContractError("A training target is outside the frozen action vocabulary")
    if not (
        type(max_input_bytes) is int
        and 1 <= max_input_bytes <= 8192
        and type(embedding_dim) is int
        and 1 <= embedding_dim <= 128
        and type(hidden_dim) is int
        and 1 <= hidden_dim <= 256
    ):
        raise ContractError(
            "Model dimensions/input length exceed this CPU teaching implementation's limits"
        )
    config = dict(
        schema_version=1,
        architecture="byte-gru-action-decoder",
        embedding_dim=embedding_dim,
        hidden_dim=hidden_dim,
        max_input_bytes=max_input_bytes,
        vocab_size=ACTION_OFFSET + len(actions),
    )
    if model_io_contract is not None:
        config["model_io_contract"] = model_io_contract.to_dict()
    base_hash = None
    ancestor_rows = []
    torch = _torch()
    thread_count = min(2, torch.get_num_threads())
    with _cpu_threads(torch), torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        if base is None:
            model = build_model(config)
        else:
            if action_vocabulary is not None and actions != base.actions:
                raise ContractError("Adaptation must retain the base action vocabulary")
            config, actions, model = dict(base.config), list(base.actions), base.model
            base_hash = base.checkpoint_sha256
            ancestor_rows = base.metadata["training_records"]
        action_ids = {
            action: ACTION_OFFSET + index for index, action in enumerate(actions)
        }
        if any(row["target_action"] not in action_ids for row in rows):
            raise ContractError(
                "Adaptation target is outside the base action vocabulary"
            )
        for row in rows:
            _encode_input(row["input_text"], config["max_input_bytes"])
        initial_sha = _parameter_sha256(model)
        initial_loss = _loss(model, rows, config, action_ids, torch)
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        generator = random.Random(seed)
        losses = []
        optimization_started = time.perf_counter()
        # Reserve a little of the requested total for measurements/serialization.
        deadline = started + max_seconds * 0.9
        for step in range(max_steps):
            if time.perf_counter() >= deadline:
                break
            selected = generator.sample(rows, min(batch_size, len(rows)))
            x, y = _batch(selected, config, action_ids, torch)
            model.train()
            optimizer.zero_grad(set_to_none=True)
            logits, _ = model(x)
            loss = torch.nn.functional.cross_entropy(
                logits.flatten(0, 1), y.flatten(), ignore_index=-100
            )
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            losses.append(float(loss.detach()))
        optimization_seconds = time.perf_counter() - optimization_started
        if not losses:
            raise ContractError(
                "Budget expired before any parameter update; no checkpoint produced"
            )
        final_loss = _loss(model, rows, config, action_ids, torch)
        final_sha = _parameter_sha256(model)
        model.eval()
        destination.mkdir(parents=True)
        torch.save(model.state_dict(), destination / "checkpoint.pt")
        tokenizer = dict(
            schema_version=1,
            encoding="utf-8-bytes",
            pad=PAD,
            bos=BOS,
            separator=SEP,
            eos=EOS,
            byte_offset=BYTE_OFFSET,
            action_offset=ACTION_OFFSET,
            actions=actions,
        )
        for name, payload in (("config.json", config), ("tokenizer.json", tokenizer)):
            (destination / name).write_text(
                json.dumps(payload, indent=2) + "\n", encoding="utf-8"
            )
        metadata = dict(
            schema_version=1,
            model_scope="tiny structured-action sequence decoder; no general language claim",
            seed=seed,
            torch_version=torch.__version__,
            device="cpu",
            threads=thread_count,
            max_steps=max_steps,
            steps_completed=len(losses),
            max_seconds=max_seconds,
            batch_size=batch_size,
            learning_rate=learning_rate,
            optimizer="Adam",
            loss="masked action and EOS next-token cross entropy",
            initial_loss=initial_loss,
            final_loss=final_loss,
            step_losses=losses,
            parameter_count=sum(parameter.numel() for parameter in model.parameters()),
            initial_parameter_sha256=initial_sha,
            final_parameter_sha256=final_sha,
            parameters_changed=initial_sha != final_sha,
            base_checkpoint_sha256=base_hash,
            optimization_seconds=optimization_seconds,
            training_records=ancestor_rows + rows,
            update_record_ids=[row["record_id"] for row in rows],
            training_record_ids=[row["record_id"] for row in ancestor_rows + rows],
            training_group_ids=sorted(
                {row["group_id"] for row in ancestor_rows + rows}
            ),
            training_source_sha256=sorted(
                {row["source_sha256"] for row in ancestor_rows + rows}
            ),
            dataset_sha256=hashlib.sha256(canonical_json(rows).encode()).hexdigest(),
            input_bytes_max_observed=max(
                len(row["input_text"].encode()) for row in rows
            ),
            input_truncation=False,
            actions=actions,
            compatibility_mode="bound"
            if model_io_contract is not None
            else "legacy_unbound",
            model_io_contract_sha256=model_io_contract.digest
            if model_io_contract is not None
            else None,
            artifacts={
                name: file_sha256(destination / name)
                for name in ("checkpoint.pt", "config.json", "tokenizer.json")
            },
        )
    metadata["total_wall_seconds"] = time.perf_counter() - started
    metadata["budget_exceeded"] = metadata["total_wall_seconds"] > max_seconds
    (destination / "training.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    return metadata


class TinyActionDecoder:
    """Loaded model with explicit grammar, input limit, and no policy fallback."""

    def __init__(self, model, config, actions, metadata, checkpoint_sha256):
        self.model, self.config, self.actions = model, config, actions
        self.metadata, self.checkpoint_sha256 = metadata, checkpoint_sha256
        self.model_io_contract = (
            ModelIOContract.from_dict(config["model_io_contract"])
            if "model_io_contract" in config
            else None
        )
        self.compatibility_mode = (
            "bound" if self.model_io_contract is not None else "legacy_unbound"
        )

    def require_input_contract(self, supplied: ModelIOContract | None) -> None:
        """Unbound legacy input cannot masquerade as a declared representation."""
        if self.model_io_contract is not None:
            self.model_io_contract.require_match(supplied)
        elif supplied is not None:
            raise ContractError(
                "Legacy unbound checkpoint has no model input contract to match"
            )

    def parse_tokens(
        self, tokens: Sequence[int], *, allowed_actions: Sequence[str] | None = None
    ) -> str:
        if (
            len(tokens) != 2
            or tokens[1] != EOS
            or not ACTION_OFFSET <= tokens[0] < ACTION_OFFSET + len(self.actions)
        ):
            raise ContractError(
                "Generated sequence is not exactly one action token followed by EOS"
            )
        action = self.actions[tokens[0] - ACTION_OFFSET]
        if allowed_actions is not None and action not in allowed_actions:
            raise ContractError("Generated action is forbidden by this task")
        return action

    def predict(
        self,
        input_text: str,
        *,
        allowed_actions: Sequence[str] | None = None,
        model_io_contract: ModelIOContract | None = None,
    ) -> dict[str, Any]:
        self.require_input_contract(model_io_contract)
        if self.model_io_contract is not None:
            self.model_io_contract.validate_text(input_text)
        allowed = self.actions if allowed_actions is None else list(allowed_actions)
        if not allowed or any(action not in self.actions for action in allowed):
            raise ContractError(
                "Inference needs a nonempty subset of the checkpoint's action vocabulary"
            )
        prompt = _encode_input(input_text, self.config["max_input_bytes"])
        torch = _torch()
        started = time.perf_counter()
        with _cpu_threads(torch), torch.no_grad():
            self.model.eval()
            logits, hidden = self.model(torch.tensor([prompt], dtype=torch.long))
            first = logits[0, -1]
            legal_ids = [
                ACTION_OFFSET + self.actions.index(action) for action in allowed
            ]
            scores = first[legal_ids]
            chosen = legal_ids[int(scores.argmax())]
            # The second production is EOS. Record what unconstrained generation
            # would have done at both positions as a separate syntax diagnostic.
            ending, _ = self.model(torch.tensor([[chosen]], dtype=torch.long), hidden)
            raw_tokens = [int(first.argmax()), int(ending[0, -1].argmax())]
            tokens = [chosen, EOS]
            action = self.parse_tokens(tokens, allowed_actions=allowed)
            try:
                self.parse_tokens(raw_tokens, allowed_actions=allowed)
                raw_valid = True
            except ContractError:
                raw_valid = False
            probabilities = torch.softmax(scores, dim=0).tolist()
        return dict(
            action=action,
            token_ids=tokens,
            constrained=True,
            raw_token_ids=raw_tokens,
            raw_valid=raw_valid,
            action_probabilities=dict(zip(allowed, probabilities)),
            checkpoint_sha256=self.checkpoint_sha256,
            compatibility_mode=self.compatibility_mode,
            model_io_contract_sha256=self.model_io_contract.digest
            if self.model_io_contract is not None
            else None,
            wall_seconds=time.perf_counter() - started,
        )

    def evaluate(
        self,
        records: Sequence[Mapping[str, Any]],
        *,
        model_io_contract: ModelIOContract | None = None,
    ) -> dict[str, Any]:
        return evaluate(self, records, model_io_contract=model_io_contract)


def load_model(
    checkpoint_dir: str | Path,
    *,
    expected_model_io_contract: ModelIOContract | None = None,
) -> TinyActionDecoder:
    """Verify saved artifact identities and load tensors with weights_only=True."""
    root = Path(checkpoint_dir)
    metadata = json.loads((root / "training.json").read_text(encoding="utf-8"))
    for name in ("config.json", "tokenizer.json", "checkpoint.pt"):
        if file_sha256(root / name) != metadata["artifacts"][name]:
            raise ContractError(f"Checkpoint artifact content changed: {name}")
    config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    tokenizer = json.loads((root / "tokenizer.json").read_text(encoding="utf-8"))
    if (
        config.get("schema_version") != 1
        or config.get("architecture") != "byte-gru-action-decoder"
        or tokenizer.get("encoding") != "utf-8-bytes"
        or tokenizer.get("action_offset") != ACTION_OFFSET
        or config["vocab_size"] != ACTION_OFFSET + len(tokenizer["actions"])
    ):
        raise ContractError("Unsupported sequence model or tokenizer")
    contract = (
        ModelIOContract.from_dict(config["model_io_contract"])
        if "model_io_contract" in config
        else None
    )
    if contract is not None:
        if (
            list(contract.actions) != tokenizer["actions"]
            or contract.max_input_bytes != config["max_input_bytes"]
            or metadata.get("compatibility_mode") != "bound"
            or metadata.get("model_io_contract_sha256") != contract.digest
        ):
            raise ContractError(
                "Checkpoint model input contract differs from saved model/tokenizer metadata"
            )
        if expected_model_io_contract is not None:
            contract.require_match(expected_model_io_contract)
    elif (
        metadata.get("compatibility_mode", "legacy_unbound") != "legacy_unbound"
        or metadata.get("model_io_contract_sha256") is not None
        or expected_model_io_contract is not None
    ):
        raise ContractError(
            "Legacy unbound checkpoint has no model input contract to match"
        )
    torch = _torch()
    with _cpu_threads(torch), torch.random.fork_rng(devices=[]):
        model = build_model(config)
        model.load_state_dict(
            torch.load(root / "checkpoint.pt", map_location="cpu", weights_only=True)
        )
        model.eval()
    return TinyActionDecoder(
        model,
        config,
        tokenizer["actions"],
        metadata,
        metadata["artifacts"]["checkpoint.pt"],
    )


def evaluate(
    decoder: TinyActionDecoder,
    records: Sequence[Mapping[str, Any]],
    *,
    model_io_contract: ModelIOContract | None = None,
) -> dict[str, Any]:
    """Report held-out action/syntax diagnostics, with no updates or selection.

    Reused declared groups, record IDs, receipt hashes, or exact inputs are
    rejected. Undisclosed semantic duplicates still require a corpus audit.
    """
    decoder.require_input_contract(model_io_contract)
    rows = _validate_records(records)
    training = decoder.metadata["training_records"]
    forbidden = {
        key: {row[key] for row in training}
        for key in ("record_id", "group_id", "source_sha256", "input_text")
    }
    used_receipts = {_receipt_identity(row) for row in training}
    if any(row["split"] == "train" for row in rows):
        raise ContractError("Held-out evaluation requires dev or test records")
    if len({row["split"] for row in rows}) != 1:
        raise ContractError("Evaluate dev and final test partitions separately")
    for row in rows:
        if decoder.model_io_contract is not None:
            decoder.model_io_contract.validate_text(row["input_text"])
        if (
            any(row[key] in values for key, values in forbidden.items())
            or _receipt_identity(row) in used_receipts
        ):
            raise ContractError(
                "Held-out evaluation overlaps training identity, group, receipt, or exact input"
            )
        if row["target_action"] not in decoder.actions:
            raise ContractError(
                "Held-out target is outside the frozen action vocabulary"
            )
    torch = _torch()
    with _cpu_threads(torch):
        loss = _loss(
            decoder.model,
            rows,
            decoder.config,
            {action: ACTION_OFFSET + i for i, action in enumerate(decoder.actions)},
            torch,
        )
    results = []
    for row in rows:
        prediction = decoder.predict(
            row["input_text"], model_io_contract=model_io_contract
        )
        results.append(
            dict(
                record_id=row["record_id"],
                group_id=row["group_id"],
                target_action=row["target_action"],
                **prediction,
            )
        )
    return dict(
        schema_version=1,
        split=rows[0]["split"],
        record_count=len(rows),
        group_count=len({row["group_id"] for row in rows}),
        masked_next_token_loss=loss,
        exact_action_accuracy=sum(
            row["action"] == row["target_action"] for row in results
        )
        / len(results),
        constrained_valid_rate=1.0,
        raw_valid_rate=sum(row["raw_valid"] for row in results) / len(results),
        checkpoint_sha256=decoder.checkpoint_sha256,
        predictions=results,
        compatibility_mode=decoder.compatibility_mode,
        model_io_contract_sha256=decoder.model_io_contract.digest
        if decoder.model_io_contract is not None
        else None,
        scope="diagnostic action imitation; not independent evidence of design advantage",
    )
