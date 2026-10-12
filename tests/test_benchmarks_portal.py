from __future__ import annotations

import sys
from pathlib import Path
import yaml
import pytest

from tools.validate_registries import ROOT, _load_yaml

BENCHMARK_DIR = ROOT / "www" / "benchmarks"
BENCHMARK_SCHEMA = ROOT / "www" / "schemas" / "benchmark.schema.json"
BENCHMARK_INDEX = ROOT / "www" / "benchmarks.yml"

SCRIPTS_DIR = ROOT / ".github" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from validate_benchmarks import validate
from benchmark_common import ALLOWED_BENCHMARK_CATEGORIES


def test_benchmark_registry_validates_cleanly() -> None:
    errors = validate()
    assert errors == []


def test_every_benchmark_has_required_fields() -> None:
    benchmarks = list(BENCHMARK_DIR.glob("*.yml"))
    assert len(benchmarks) >= 20
    for path in benchmarks:
        doc = _load_yaml(path)
        assert doc.get("title"), f"{path} missing title"
        assert doc.get("url"), f"{path} missing url"
        assert doc.get("description"), f"{path} missing description"
        assert doc.get("primary_metric"), f"{path} missing primary_metric"
        assert doc.get("categories"), f"{path} missing categories"
        assert doc["categories"][0] in ALLOWED_BENCHMARK_CATEGORIES
        assert doc.get("hardware_domains"), f"{path} missing hardware_domains"
        assert doc.get("artifact_availability"), f"{path} missing artifact_availability"
