"""Shared constants for the Architecture 2.0 benchmark portal."""

import os
import re

BENCHMARKS_PATH = os.environ.get("ARCH2_BENCHMARK_INDEX", "www/benchmarks.yml")
BENCHMARKS_DIR = os.environ.get("ARCH2_BENCHMARK_REGISTRY", "www/benchmarks")
BENCHMARKS_SCHEMA = "www/schemas/benchmark.schema.json"

ALLOWED_BENCHMARK_CATEGORIES = [
    "Specification-to-RTL",
    "Verification & Bug Localization",
    "Physical Design & EDA Surrogates",
    "Autonomous DSE & Co-Design",
    "Kernel Autotuning & Synthesis",
    "Benchmark Health & Red-Teaming",
    "End-to-End Silicon Flows",
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
