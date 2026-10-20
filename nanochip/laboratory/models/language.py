"""A small CPU byte language model, with real text pretraining and adaptation.

Every text byte contributes to pretraining loss. Supervised adaptation predicts
the bytes of a declared action after an architecture-state prompt. Inference
scores those same continuations; the harness still owns legal experiments and
required checks. Neither low text loss nor valid actions establish design benefit.
"""

from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path
import random
import time
from typing import Any, Callable, Mapping, Sequence

from ..contracts import Action, Budget, ContractError, Observation, Task, canonical_json, file_sha256
from ..model_io import ModelIOContract

PAD, BOS, EOS, BYTE_OFFSET = 0, 1, 2, 3
VOCAB_SIZE = BYTE_OFFSET + 256
ARCHITECTURE = "byte-gru-lm/v1"
CHECKPOINT_FILES = ("config.json", "tokenizer.json", "checkpoint.pt")


def _torch():
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("The byte language model requires installed CPU PyTorch") from exc
    return torch


@contextmanager
def _threads(torch):
    previous = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        yield
    finally:
        torch.set_num_threads(previous)


def build_model(config: Mapping[str, Any]):
    """Replaceable teaching model: byte embedding, one GRU, byte/EOS head."""
    torch = _torch()
    class ByteGRU(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.embedding = torch.nn.Embedding(VOCAB_SIZE, config["embedding_dim"], padding_idx=PAD)
            self.recurrent = torch.nn.GRU(config["embedding_dim"], config["hidden_dim"], batch_first=True)
            self.head = torch.nn.Linear(config["hidden_dim"], VOCAB_SIZE)

        def forward(self, tokens, hidden=None):
            states, hidden = self.recurrent(self.embedding(tokens), hidden)
            return self.head(states), hidden
    return ByteGRU().cpu()


def _hash(value):
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _parameters(model):
    digest = hashlib.sha256()
    for name, value in sorted(model.state_dict().items()):
        digest.update(name.encode("utf-8"))
        digest.update(value.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def _records(records, contract, objective, *, training=False):
    if objective not in ("pretrain", "supervised"):
        raise ContractError("Language objective must be pretrain or supervised")
    rows = [dict(row) for row in records]
    if not rows:
        raise ContractError("Language data must be nonempty")
    seen = set()
    groups = {}
    for row in rows:
        required = ("record_id", "group_id", "split", "original_split", "input_text",
                    "source_sha256", "label_origin", "data_origin")
        if any(not isinstance(row.get(key), str) or not row[key].strip() for key in required):
            raise ContractError("Language records need identities, text, split, origin, and provenance")
        if row["record_id"] in seen:
            raise ContractError("Duplicate language record identity")
        seen.add(row["record_id"])
        if row["split"] not in ("train", "dev", "test") or row["original_split"] not in ("train", "dev", "test", "development"):
            raise ContractError("Unknown language data partition")
        if training and (row["split"] != "train" or row["original_split"] == "test"):
            raise ContractError("Parameter updates require designated train records; final test cannot be retagged")
        if row["group_id"] in groups and groups[row["group_id"]] != row["split"]:
            raise ContractError("A language source group crosses partitions")
        groups[row["group_id"]] = row["split"]
        if row["data_origin"] not in ("repository_documentation", "constructed", "measured"):
            raise ContractError("Unknown language data origin")
        digest = row["source_sha256"]
        receipt = row.get("source_receipt")
        if (len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest)
                or not isinstance(receipt, Mapping) or not isinstance(receipt.get("path"), str)
                or not receipt["path"] or not isinstance(receipt.get("sha256"), str)
                or len(receipt["sha256"]) != 64
                or any(c not in "0123456789abcdef" for c in receipt["sha256"])):
            raise ContractError("Language records need source and receipt SHA-256 identities")
        if row.get("model_io_contract_sha256", contract.digest) != contract.digest:
            raise ContractError("Language record representation differs from the model input contract")
        contract.validate_text(row["input_text"])
        if objective == "supervised" and row.get("target_action") not in contract.actions:
            raise ContractError("Supervised language target is outside the frozen action vocabulary")
    return rows


def _tokens(text):
    return [BYTE_OFFSET + byte for byte in text.encode("utf-8")]


def _sequence(row, objective):
    prompt = _tokens(row["input_text"])
    if objective == "pretrain":
        return [BOS] + prompt, prompt + [EOS]
    completion = _tokens(row["target_action"]) + [EOS]
    # At the final prompt byte, predict the first completion byte.
    return [BOS] + prompt + completion[:-1], [-100] * len(prompt) + completion


def _batch(rows, objective, torch):
    examples = [_sequence(row, objective) for row in rows]
    width = max(len(x) for x, _ in examples)
    x = torch.full((len(rows), width), PAD, dtype=torch.long)
    y = torch.full((len(rows), width), -100, dtype=torch.long)
    for index, (inputs, targets) in enumerate(examples):
        x[index, :len(inputs)] = torch.tensor(inputs)
        y[index, :len(targets)] = torch.tensor(targets)
    return x, y


def _loss(model, rows, objective, torch):
    total, tokens = 0.0, 0
    model.eval()
    with torch.no_grad():
        for offset in range(0, len(rows), 8):
            x, y = _batch(rows[offset:offset + 8], objective, torch)
            logits, _ = model(x)
            total += float(torch.nn.functional.cross_entropy(
                logits.flatten(0, 1), y.flatten(), ignore_index=-100, reduction="sum"))
            tokens += int((y != -100).sum())
    return total / tokens, tokens


def train(records: Sequence[Mapping[str, Any]], output_dir: str | Path, *,
          model_io_contract: ModelIOContract, objective: str = "pretrain",
          base_checkpoint: str | Path | None = None, seed: int = 0,
          max_steps: int = 200, max_seconds: float = 60, batch_size: int = 8,
          embedding_dim: int = 24, hidden_dim: int = 48, learning_rate: float = .003,
          model_factory: Callable | None = None, architecture_id: str = ARCHITECTURE) -> dict:
    """Pretrain from initialization or update a saved language model on train data.

    Supervised rows predict action strings, not private reasoning. Measured
    outcome records require validation by their evidence loader before admission.
    No held-out metric controls stopping. A replacement model factory must return
    (logits, hidden) and accompany a declared architecture identity on save/load.
    """
    started = time.perf_counter()
    if not isinstance(model_io_contract, ModelIOContract):
        raise ContractError("Language training requires a declared ModelIOContract")
    rows = _records(records, model_io_contract, objective, training=True)
    if (type(max_steps) is not int or not 1 <= max_steps <= 10000
            or type(batch_size) is not int or not 1 <= batch_size <= 64
            or not math.isfinite(max_seconds) or not 0 < max_seconds <= 300
            or not math.isfinite(learning_rate) or not 0 < learning_rate <= 1
            or type(embedding_dim) is not int or not 1 <= embedding_dim <= 128
            or type(hidden_dim) is not int or not 1 <= hidden_dim <= 256):
        raise ContractError("Language training needs bounded positive steps, time, batch, dimensions, and learning rate")
    if not isinstance(architecture_id, str) or not architecture_id.strip():
        raise ContractError("Replacement language models need an architecture identity")
    if architecture_id != ARCHITECTURE and model_factory is None:
        raise ContractError("Unknown architecture requires an explicit model factory")
    root = Path(output_dir)
    if root.exists():
        raise ContractError("Language training output must be a new directory")
    base = load_model(base_checkpoint, expected_model_io_contract=model_io_contract,
                      model_factory=model_factory) if base_checkpoint is not None else None
    config = dict(schema_version=1, architecture=architecture_id, vocab_size=VOCAB_SIZE,
                  embedding_dim=embedding_dim, hidden_dim=hidden_dim,
                  model_io_contract=model_io_contract.to_dict())
    if base is not None:
        if base.config["architecture"] != architecture_id:
            raise ContractError("Adaptation cannot change the language model architecture")
        config = dict(base.config)
    torch = _torch()
    with _threads(torch), torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        model = base.model if base is not None else (model_factory or build_model)(config)
        ancestors = list(base.metadata["training_records"]) if base is not None else []
        # Training may replay an existing example with unchanged provenance.
        prior = {row["record_id"]: row for row in ancestors}
        for row in rows:
            if row["record_id"] in prior and row != prior[row["record_id"]]:
                raise ContractError("Adaptation changed an existing training record's content/provenance")
        initial_sha = _parameters(model)
        initial_loss, loss_tokens = _loss(model, rows, objective, torch)
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        sampler = random.Random(seed)
        losses = []
        deadline = started + max_seconds * .9
        optimization_started = time.perf_counter()
        for _ in range(max_steps):
            if time.perf_counter() >= deadline:
                break
            selected = sampler.sample(rows, min(batch_size, len(rows)))
            x, y = _batch(selected, objective, torch)
            model.train()
            optimizer.zero_grad(set_to_none=True)
            logits, _ = model(x)
            loss = torch.nn.functional.cross_entropy(logits.flatten(0, 1), y.flatten(), ignore_index=-100)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1)
            optimizer.step()
            losses.append(float(loss.detach()))
        optimization_seconds = time.perf_counter() - optimization_started
        if not losses:
            raise ContractError("Language training budget expired before a parameter update")
        final_loss, _ = _loss(model, rows, objective, torch)
        final_sha = _parameters(model)
        tokenizer = dict(schema_version=1, encoding="utf-8-bytes", byte_offset=BYTE_OFFSET,
                         pad=PAD, bos=BOS, eos=EOS, vocab_size=VOCAB_SIZE)
        root.mkdir(parents=True)
        model.eval()
        torch.save(model.state_dict(), root / "checkpoint.pt")
        for name, value in (("config.json", config), ("tokenizer.json", tokenizer)):
            (root / name).write_text(json.dumps(value, indent=2) + "\n")
        training_records = list(prior.values()) + [row for row in rows if row["record_id"] not in prior]
        metadata = dict(schema_version=1, model_scope="byte language model; no architecture benefit claim",
            objective=objective, loss_scope="all text bytes and EOS" if objective == "pretrain" else "action continuation bytes and EOS",
            seed=seed, device="cpu", threads=torch.get_num_threads(), torch_version=torch.__version__,
            max_steps=max_steps, steps_completed=len(losses), max_seconds=max_seconds,
            batch_size=batch_size, learning_rate=learning_rate, optimizer="Adam", step_losses=losses,
            initial_loss=initial_loss, final_loss=final_loss, loss_tokens=loss_tokens,
            initial_parameter_sha256=initial_sha, final_parameter_sha256=final_sha,
            parameters_changed=initial_sha != final_sha,
            parameter_count=sum(p.numel() for p in model.parameters()),
            base_checkpoint_sha256=base.checkpoint_sha256 if base is not None else None,
            model_io_contract_sha256=model_io_contract.digest, input_truncation=False,
            dataset_sha256=_hash(rows), training_records=training_records,
            implementation_sha256=file_sha256(__file__),
            update_record_ids=[row["record_id"] for row in rows],
            data_origin_counts={origin: sum(row["data_origin"] == origin for row in rows)
                                for origin in sorted({row["data_origin"] for row in rows})},
            optimization_seconds=optimization_seconds,
            artifacts={name: file_sha256(root / name) for name in CHECKPOINT_FILES})
    metadata["total_wall_seconds"] = time.perf_counter() - started
    metadata["budget_exceeded"] = metadata["total_wall_seconds"] > max_seconds
    (root / "training.json").write_text(json.dumps(metadata, indent=2, allow_nan=False) + "\n")
    return metadata


class ByteLanguageModel:
    def __init__(self, model, config, metadata):
        self.model, self.config, self.metadata = model, config, metadata
        self.model_io_contract = ModelIOContract.from_dict(config["model_io_contract"])
        self.actions = list(self.model_io_contract.actions)
        self.checkpoint_sha256 = metadata["artifacts"]["checkpoint.pt"]

    def predict(self, input_text: str, *, model_io_contract: ModelIOContract,
                allowed_actions: Sequence[str] | None = None) -> dict:
        """Score complete action+EOS continuations under the frozen byte model.

        Scores are summed log probabilities, including EOS. The normalized values
        are probabilities conditional on this finite continuation set, rather than
        calibrated probabilities of architectural success.
        """
        self.model_io_contract.require_match(model_io_contract)
        self.model_io_contract.validate_text(input_text)
        allowed = self.actions if allowed_actions is None else list(allowed_actions)
        if not allowed or len(set(allowed)) != len(allowed) or any(a not in self.actions for a in allowed):
            raise ContractError("Language inference needs a distinct nonempty subset of legal actions")
        torch = _torch()
        started = time.perf_counter()
        scores = []
        self.model.eval()
        with _threads(torch), torch.no_grad():
            for action in allowed:
                row = dict(input_text=input_text, target_action=action)
                x, y = _batch([row], "supervised", torch)
                logits, _ = self.model(x)
                nll = torch.nn.functional.cross_entropy(logits.flatten(0, 1), y.flatten(),
                                                        ignore_index=-100, reduction="sum")
                scores.append(-float(nll))
            probabilities = torch.softmax(torch.tensor(scores, dtype=torch.float64), dim=0).tolist()
        selected = max(range(len(allowed)), key=lambda index: scores[index])
        return dict(action=allowed[selected], action_probabilities=dict(zip(allowed, probabilities)),
                    continuation_log_probabilities=dict(zip(allowed, scores)),
                    scoring="sum byte and EOS log probabilities; normalized over permitted continuations",
                    checkpoint_sha256=self.checkpoint_sha256,
                    model_io_contract_sha256=self.model_io_contract.digest,
                    wall_seconds=time.perf_counter() - started)

    def evaluate(self, records, *, model_io_contract: ModelIOContract, objective: str | None = None):
        self.model_io_contract.require_match(model_io_contract)
        objective = objective or self.metadata["objective"]
        rows = _records(records, model_io_contract, objective)
        if any(row["split"] == "train" for row in rows) or len({row["split"] for row in rows}) != 1:
            raise ContractError("Language evaluation requires one held-out dev or test partition")
        ancestors = self.metadata["training_records"]
        keys = ("record_id", "group_id", "source_sha256", "input_text")
        forbidden = {key: {row[key] for row in ancestors} for key in keys}
        receipts = {row["source_receipt"]["sha256"] for row in ancestors}
        for row in rows:
            if (any(row[key] in forbidden[key] for key in keys)
                    or row["source_receipt"]["sha256"] in receipts):
                raise ContractError("Held-out language data overlaps training lineage by group, receipt, source, ID, or text")
        torch = _torch()
        with _threads(torch):
            nll, count = _loss(self.model, rows, objective, torch)
        predictions = ([dict(record_id=row["record_id"], target_action=row["target_action"],
                            **self.predict(row["input_text"], model_io_contract=model_io_contract)) for row in rows]
                       if objective == "supervised" else [])
        training_counts = Counter(row["target_action"] for row in ancestors if "target_action" in row)
        majority = (max(self.actions, key=lambda action: training_counts[action])
                    if training_counts else None)
        targets = Counter(row["target_action"] for row in rows) if predictions else Counter()
        predicted = Counter(row["action"] for row in predictions)
        correct = Counter(row["target_action"] for row in predictions if row["action"] == row["target_action"])
        return dict(schema_version=1, split=rows[0]["split"], objective=objective,
                    record_count=len(rows), loss_tokens=count, byte_next_token_nll=nll,
                    byte_perplexity=math.exp(nll) if nll < 700 else None,
                    exact_action_accuracy=(sum(p["action"] == p["target_action"] for p in predictions) / len(predictions)
                                           if predictions else None), predictions=predictions,
                    training_majority_action=majority if predictions else None,
                    training_majority_action_accuracy=(sum(row["target_action"] == majority for row in rows) / len(rows)
                                                       if predictions and majority is not None else None),
                    target_action_counts=dict(targets), predicted_action_counts=dict(predicted),
                    per_action_accuracy={action: correct[action] / targets[action] if targets[action] else None
                                         for action in self.actions} if predictions else {},
                    checkpoint_sha256=self.checkpoint_sha256,
                    model_io_contract_sha256=self.model_io_contract.digest,
                    scope="held-out text/action diagnostics; no design benefit or transfer claim")


def load_model(checkpoint_dir: str | Path, *, expected_model_io_contract: ModelIOContract | None = None,
               model_factory: Callable | None = None) -> ByteLanguageModel:
    root = Path(checkpoint_dir)
    metadata = json.loads((root / "training.json").read_text())
    for name in CHECKPOINT_FILES:
        if file_sha256(root / name) != metadata["artifacts"][name]:
            raise ContractError(f"Language checkpoint artifact content changed: {name}")
    config = json.loads((root / "config.json").read_text())
    tokenizer = json.loads((root / "tokenizer.json").read_text())
    contract = ModelIOContract.from_dict(config["model_io_contract"])
    if expected_model_io_contract is not None:
        contract.require_match(expected_model_io_contract)
    if (config.get("schema_version") != 1 or config.get("vocab_size") != VOCAB_SIZE
            or tokenizer != dict(schema_version=1, encoding="utf-8-bytes", byte_offset=BYTE_OFFSET,
                                 pad=PAD, bos=BOS, eos=EOS, vocab_size=VOCAB_SIZE)
            or metadata.get("model_io_contract_sha256") != contract.digest):
        raise ContractError("Unsupported language model/tokenizer or representation identity")
    if config.get("architecture") != ARCHITECTURE and model_factory is None:
        raise ContractError("Unknown language architecture requires its explicit model factory")
    torch = _torch()
    with _threads(torch), torch.random.fork_rng(devices=[]):
        model = (model_factory or build_model)(config)
        model.load_state_dict(torch.load(root / "checkpoint.pt", map_location="cpu", weights_only=True))
        model.eval()
    return ByteLanguageModel(model, config, metadata)


class LanguageProposer:
    """Adapt scored byte continuations to the shared candidate/tool harness."""
    def __init__(self, checkpoint_dir, format_input, *, model_io_contract: ModelIOContract,
                 stop_action="stop", model_factory: Callable | None = None):
        self.decoder = load_model(checkpoint_dir, expected_model_io_contract=model_io_contract,
                                  model_factory=model_factory)
        self.model_io_contract, self.format_input, self.stop_action = model_io_contract, format_input, stop_action
        self.predictions = []

    def propose(self, task: Task, history: tuple[Observation, ...], budget: Budget):
        if budget.proposals_remaining <= 0:
            return None
        allowed = [a for a in self.decoder.actions if a in task.allowed_actions or a == self.stop_action]
        prediction = self.decoder.predict(self.format_input(task, history), model_io_contract=self.model_io_contract,
                                          allowed_actions=allowed)
        self.predictions.append(prediction)
        return None if prediction["action"] == self.stop_action else Action(prediction["action"])
