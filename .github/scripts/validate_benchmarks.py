#!/usr/bin/env python3
"""Validate www/benchmarks/*.yml against the JSON schema and index integrity."""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_DIR = ROOT / "www" / "benchmarks"
BENCHMARK_SCHEMA = ROOT / "www" / "schemas" / "benchmark.schema.json"
BENCHMARK_INDEX = ROOT / "www" / "benchmarks.yml"


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _normalize_dates(value: Any) -> Any:
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _normalize_dates(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_dates(item) for item in value]
    return value


def _schema_errors(path: Path, schema_path: Path) -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    document = _normalize_dates(_load_yaml(path))
    errors = sorted(
        validator.iter_errors(document),
        key=lambda error: (list(error.absolute_path), error.message),
    )
    rel = str(path.relative_to(ROOT))
    return [f"{rel}: {error.message}" for error in errors]


def _duplicate_errors(paths: list[Path], fields: tuple[str, ...]) -> list[str]:
    errors: list[str] = []
    for field in fields:
        seen: dict[str, Path] = {}
        for path in paths:
            doc = _load_yaml(path) or {}
            val = str(doc.get(field, "")).strip().lower()
            if not val:
                continue
            if val in seen:
                errors.append(
                    f"{path.relative_to(ROOT)}: duplicate {field} also used by {seen[val].relative_to(ROOT)}"
                )
            else:
                seen[val] = path
    return errors


def _expected_index(paths: list[Path]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in paths:
        item = _load_yaml(path) or {}
        item.setdefault("source_file", path.name)
        items.append(item)
    return sorted(
        items, key=lambda item: (item.get("order", 9999), item.get("title", ""))
    )


def validate() -> list[str]:
    paths = sorted(BENCHMARK_DIR.glob("*.yml"))
    errors: list[str] = []
    if not paths:
        errors.append("www/benchmarks: no source entries found")
        return errors
    for path in paths:
        errors.extend(_schema_errors(path, BENCHMARK_SCHEMA))
    errors.extend(_duplicate_errors(paths, ("title", "url")))
    if BENCHMARK_INDEX.exists():
        actual = _load_yaml(BENCHMARK_INDEX)
        expected = _expected_index(paths)
        if actual != expected:
            errors.append(
                f"{BENCHMARK_INDEX.relative_to(ROOT)}: generated index is stale; rebuild it"
            )
    else:
        errors.append(
            f"{BENCHMARK_INDEX.relative_to(ROOT)}: generated index is missing"
        )
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print(f"Benchmark validation FAILED ({len(errors)} problem(s)):")
        for err in errors:
            print(f"  - {err}")
        return 1
    paths = list(BENCHMARK_DIR.glob("*.yml"))
    print(f"Benchmark registry OK: {len(paths)} benchmarks validated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
