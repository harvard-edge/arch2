"""Deferred Chapter 8 energy-sensitivity draft.

This calculation was removed from the printed chapter during the 2026-07-28
stabilization pass. SCALE-Sim 3.0.0 reports one-byte interface words for this
study, while the Horowitz anchors used here are per 64-bit DRAM access.
Publishing the multiplication below would therefore mix incompatible units.
It can be reconsidered only after a memory-system mapping defines transaction
width, burst packing, coalescing, and the applicable technology model.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = (
    ROOT
    / "labs"
    / "examples"
    / "ai_systolic_array_study"
    / "recorded"
    / "reference"
    / "study_results.json"
)

runs = {}


def collect(obj):
    if isinstance(obj, dict):
        if obj.get("candidate_id") and "metrics" in obj:
            runs[obj["candidate_id"]] = obj["metrics"]
        for value in obj.values():
            collect(value)
    elif isinstance(obj, list):
        for value in obj:
            collect(value)


collect(json.loads(RESULT.read_text(encoding="utf-8")))
baseline = runs["conventional_baseline_32x32"]["dram_accesses"]
candidate = runs["heuristic_16x64"]["dram_accesses"]
extra_words = candidate - baseline

# These values are intentionally retained only as the rejected draft.
low_microjoules = extra_words * 1300e-12 * 1e6
high_microjoules = extra_words * 2600e-12 * 1e6
low_milliwatts_at_90_hz = extra_words * 1300e-12 * 90 * 1e3
high_milliwatts_at_90_hz = extra_words * 2600e-12 * 90 * 1e3

print(
    {
        "baseline_modeled_word_accesses": baseline,
        "candidate_modeled_word_accesses": candidate,
        "ratio": candidate / baseline,
        "rejected_64_bit_anchor_calculation": {
            "microjoules": [low_microjoules, high_microjoules],
            "milliwatts_at_90_hz": [
                low_milliwatts_at_90_hz,
                high_milliwatts_at_90_hz,
            ],
        },
    }
)
