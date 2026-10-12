"""Shared constants for the Architecture 2.0 benchmark and workload portal."""

import os
import re

BENCHMARKS_PATH = os.environ.get("ARCH2_BENCHMARK_INDEX", "www/benchmarks.yml")
BENCHMARKS_DIR = os.environ.get("ARCH2_BENCHMARK_REGISTRY", "www/benchmarks")
BENCHMARKS_SCHEMA = "www/schemas/benchmark.schema.json"

ALLOWED_BENCHMARK_CATEGORIES = [
    "Target Workloads",
    "Kernel Autotuning",
    "RTL Generation",
    "Verification & Red-Teaming",
    "Physical Design & EDA",
    "Architecture DSE",
]

ALLOWED_AVAILABILITY = [
    "runnable",
    "benchmark_available",
    "dataset_available",
    "source_available",
    "paper_only",
    "unverified",
]


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "benchmark"
