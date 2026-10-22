"""Inspect attributed data, train a byte language model, and use its checkpoint."""

import argparse
import json
from pathlib import Path

from .contracts import ContractError, file_sha256
from .model_io import ModelIOContract


def _records(path, kind):
    from .language_data import (
        architecture_examples,
        load_language_corpus,
        measured_feedback_examples,
    )

    return {
        "documentation": load_language_corpus,
        "constructed": architecture_examples,
        "feedback": measured_feedback_examples,
    }[kind](path)


def _contract(path):
    return ModelIOContract.from_dict(json.loads(path.read_text(encoding="utf-8")))


def _save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
    print(f"Report: {path.resolve()}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser(
        "collect", help="snapshot upstream documents with whole-document splits"
    )
    collect.add_argument("--output", required=True, type=Path)
    collect.add_argument("--max-text-bytes", type=int, default=384)
    for name in ("profile", "train", "evaluate"):
        item = commands.add_parser(name)
        item.add_argument("--corpus", required=True, type=Path)
        item.add_argument(
            "--kind",
            choices=("documentation", "constructed", "feedback"),
            default="documentation",
        )
        item.add_argument(
            "--output",
            required=True,
            type=Path,
            help="new checkpoint directory for train; new JSON file otherwise",
        )
        if name != "profile":
            item.add_argument(
                "--contract",
                required=True,
                type=Path,
                help="explicit ModelIOContract JSON; must match a reused checkpoint",
            )
            item.add_argument(
                "--objective", choices=("pretrain", "supervised"), default=None
            )
        if name == "train":
            item.add_argument(
                "--base",
                type=Path,
                help="adapt this checkpoint instead of initializing a model",
            )
            item.add_argument("--steps", type=int, default=200)
            item.add_argument("--seconds", type=float, default=60)
            item.add_argument("--seed", type=int, default=0)
        elif name == "evaluate":
            item.add_argument("--checkpoint", required=True, type=Path)
            item.add_argument("--split", choices=("dev", "test"), default="test")
    infer = commands.add_parser(
        "infer", help="score complete legal action strings for one represented task"
    )
    infer.add_argument("--checkpoint", required=True, type=Path)
    infer.add_argument("--contract", required=True, type=Path)
    infer.add_argument("--input-file", required=True, type=Path)
    infer.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.output.exists():
        raise ContractError("Language output must be a new path")
    if args.command == "collect":
        from .language_data import collect_language_corpus

        result = collect_language_corpus(
            args.output, max_text_bytes=args.max_text_bytes
        )
        print(f"Corpus: {result['manifest_path']}")
        print(
            f"Records: {len(result['records'])}; source kind: repository documentation"
        )
        return 0
    if args.command == "infer":
        from .models.language import load_model

        contract = _contract(args.contract)
        model = load_model(args.checkpoint, expected_model_io_contract=contract)
        result = model.predict(
            args.input_file.read_text(encoding="utf-8"), model_io_contract=contract
        )
        result.update(
            input_sha256=file_sha256(args.input_file),
            scope="action proposal; no design has been executed by this command",
        )
        _save(args.output, result)
        print(f"Proposed action: {result['action']}")
        return 0
    rows = _records(args.corpus, args.kind)
    if args.command == "profile":
        from .datasets.characterize import profile_records

        result = profile_records(rows)
        result[
            "source_validation"
        ] = "Corpus loader verified source receipts before characterization"
        _save(args.output, result)
        print(json.dumps(result["split_counts"], sort_keys=True))
        return 0
    from .models.language import load_model, train

    contract = _contract(args.contract)
    objective = args.objective or (
        "pretrain" if args.kind == "documentation" else "supervised"
    )
    if args.command == "train":
        result = train(
            [row for row in rows if row["split"] == "train"],
            args.output,
            model_io_contract=contract,
            objective=objective,
            base_checkpoint=args.base,
            max_steps=args.steps,
            max_seconds=args.seconds,
            seed=args.seed,
        )
        print(
            json.dumps(
                {
                    key: result[key]
                    for key in (
                        "objective",
                        "steps_completed",
                        "parameters_changed",
                        "initial_loss",
                        "final_loss",
                        "base_checkpoint_sha256",
                        "total_wall_seconds",
                    )
                },
                indent=2,
            )
        )
        print(f"Checkpoint: {args.output.resolve()}")
    else:
        model = load_model(args.checkpoint, expected_model_io_contract=contract)
        result = model.evaluate(
            [row for row in rows if row["split"] == args.split],
            model_io_contract=contract,
            objective=objective,
        )
        _save(args.output, result)
        print(
            json.dumps(
                {
                    key: result[key]
                    for key in (
                        "split",
                        "record_count",
                        "byte_next_token_nll",
                        "exact_action_accuracy",
                        "training_majority_action_accuracy",
                        "scope",
                    )
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
