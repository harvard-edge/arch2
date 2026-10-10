#!/usr/bin/env python3
"""Verify and replay this frozen study; never write to its historical records.

Verification uses only the standard library. Replay additionally requires
SCALE-Sim 3.0.0. This checks consistency, not authenticity of the model call.
"""
from __future__ import annotations

import argparse
import configparser
import contextlib
import csv
import hashlib
import importlib.metadata
import json
import platform
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

STUDY = "arch2_scale_ai_study_v1"
ROOT = Path(__file__).resolve().parent
# Only this frozen experiment is supported, not arbitrary new studies.
RUNS = {
    "model_baseline_32x32": ("model", 32, 32, "original"),
    "ai_wide_16x64": ("model", 16, 64, "original"),
    "ai_extreme_8x128": ("model", 8, 128, "original"),
    "ai_compact_32x16": ("model", 32, 16, "original"),
    "conventional_baseline_32x32": ("conventional", 32, 32, "original"),
    "heuristic_16x64": ("conventional", 16, 64, "original"),
    "heuristic_8x128": ("conventional", 8, 128, "original"),
    "heuristic_64x16": ("conventional", 64, 16, "original"),
    "probe_original_16x64": ("mechanism_probe", 16, 64, "original"),
    "probe_original_64x16": ("mechanism_probe", 64, 16, "original"),
    "probe_transposed_16x64": ("mechanism_probe", 16, 64, "transposed"),
    "probe_transposed_64x16": ("mechanism_probe", 64, 16, "transposed"),
}
COMPUTE = [
    "LayerID",
    "Total Cycles (incl. prefetch)",
    "Total Cycles",
    "Stall Cycles",
    "Overall Util %",
    "Mapping Efficiency %",
    "Compute Util %",
]
BANDWIDTH = ["LayerID"] + [
    f"Avg {operand} {memory} BW"
    for memory in ("SRAM", "DRAM")
    for operand in ("IFMAP", "FILTER", "OFMAP")
]
ACCESS = ["LayerID"] + [
    f"{memory} {operand} {field}"
    for memory in ("SRAM", "DRAM")
    for operand in ("IFMAP", "Filter", "OFMAP")
    for field in (
        "Start Cycle",
        "Stop Cycle",
        "Writes" if operand == "OFMAP" else "Reads",
    )
]
REPORTS = {
    "COMPUTE_REPORT.csv": COMPUTE,
    "BANDWIDTH_REPORT.csv": BANDWIDTH,
    "DETAILED_ACCESS_REPORT.csv": ACCESS,
}
PROMPT_HASH = "36e0167aa338c6b13087314b768e4f313a8b72ebce5d2c7b7bff5af968376971"
RECORDED_PROMPT_HASH = (
    "ec12df200a134532942ce0120bbb5694bc657c0e13cf88654631db42aa76fbca"
)
PROMPT_WARNING = (
    "The retained prompt differs from the recorded pre-call hash; "
    "verification/replay cannot recover or validate the original generation context."
)
# Python 3.11 vs 3.14 / NumPy changes produced <=2.14e-14 percentage-point
# differences in this diagnostic alone. No tolerance applies to cycle counts,
# access counts, Overall Util %, decision scores, or other report fields.
COMPUTE_UTIL_ABS_TOL = Decimal("1e-12")


class ReplayError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ReplayError(message)


def equal(actual, expected, label):
    """Require the exact structure, types and values, including integer types."""
    require(type(actual) is type(expected), f"{label}: type mismatch")
    if isinstance(expected, dict):
        require(actual.keys() == expected.keys(), f"{label}: fields mismatch")
        for key in expected:
            equal(actual[key], expected[key], f"{label}.{key}")
    elif isinstance(expected, list):
        require(len(actual) == len(expected), f"{label}: length mismatch")
        for i, (a, e) in enumerate(zip(actual, expected)):
            equal(a, e, f"{label}[{i}]")
    else:
        require(
            actual == expected, f"{label}: value mismatch ({actual!r} != {expected!r})"
        )


def _object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json(text):
    def reject(value):
        raise ReplayError(f"nonfinite JSON number: {value}")

    return json.loads(text, object_pairs_hook=_object, parse_constant=reject)


def read_json(path):
    return parse_json(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_file(root, relative):
    require(isinstance(relative, str), "file path must be a string")
    path = Path(relative)
    require(
        not path.is_absolute() and ".." not in path.parts, f"unsafe path: {relative}"
    )
    target = (root / path).resolve()
    require(
        target.is_relative_to(root.resolve()) and target.is_file(),
        f"missing or external file: {relative}",
    )
    return target


def report_rows(path):
    expected = REPORTS[path.name]
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [[cell.strip() for cell in row] for row in csv.reader(handle)]
    require(len(rows) == 4, f"{path}: expected header and exactly three layers")
    # SCALE-Sim 3.0.0 writes a trailing comma on every row.
    require(
        all(len(row) == len(expected) + 1 and row[-1] == "" for row in rows),
        f"{path}: malformed report columns",
    )
    equal(rows[0][:-1], expected, f"{path}: header")
    result = []
    for layer, row in enumerate(rows[1:]):
        record = dict(zip(expected, row[:-1]))
        for field, text in record.items():
            try:
                number = Decimal(text)
            except InvalidOperation as exc:
                raise ReplayError(f"{path}: nonnumeric {field}") from exc
            require(number.is_finite(), f"{path}: nonfinite {field}")
            if field == "LayerID" or ("%" not in field and " BW" not in field):
                require(
                    number == number.to_integral_value(), f"{path}: fractional {field}"
                )
        require(
            Decimal(record["LayerID"]) == layer,
            f"{path}: layer order/identity mismatch",
        )
        result.append(record)
    return result


def metrics(report_dir):
    compute = report_rows(report_dir / "COMPUTE_REPORT.csv")
    bandwidth = report_rows(report_dir / "BANDWIDTH_REPORT.csv")
    access = report_rows(report_dir / "DETAILED_ACCESS_REPORT.csv")

    def count(rows, *fields):
        return sum(int(Decimal(row[field])) for row in rows for field in fields)

    def mean(field):
        # Match Python 3.11's left-to-right summation in the historical runner;
        # Python 3.12 changed sum(float, ...) to a compensated algorithm.
        total = 0.0
        for row in compute:
            total += float(row[field])
        return total / 3

    result = {
        "total_cycles": count(compute, "Total Cycles"),
        "stall_cycles": count(compute, "Stall Cycles"),
        "min_layer_util_pct": min(float(row["Overall Util %"]) for row in compute),
        "avg_layer_util_pct": mean("Overall Util %"),
        "avg_mapping_efficiency_pct": mean("Mapping Efficiency %"),
        "avg_compute_util_pct": mean("Compute Util %"),
        "max_observed_dram_bw_words_per_cycle": max(
            float(row[field]) for row in bandwidth for field in BANDWIDTH[4:]
        ),
        "layers": compute,
    }
    for memory in ("dram", "sram"):
        result[f"{memory}_reads"] = count(
            access, f"{memory.upper()} IFMAP Reads", f"{memory.upper()} Filter Reads"
        )
        result[f"{memory}_writes"] = count(access, f"{memory.upper()} OFMAP Writes")
        result[f"{memory}_accesses"] = (
            result[f"{memory}_reads"] + result[f"{memory}_writes"]
        )
    require(result["avg_layer_util_pct"] > 0, "nonpositive mean utilization")
    return result


def report_dir(reference, candidate):
    return reference / "runs" / candidate / "scalesim-results" / candidate


def verify(root=ROOT):
    """Verify every archived hash, recompute metrics and check the retained outcome."""
    root = Path(root).resolve()
    reference = root / "recorded/reference"
    manifest = read_json(reference / "reference_manifest.json")
    equal(set(manifest), {"schema_version", "study_id", "files"}, "manifest fields")
    equal(manifest["schema_version"], "arch2-ai-study-reference/v1", "manifest version")
    equal(manifest["study_id"], STUDY, "manifest study")
    expected = {"evaluations.jsonl", "execution_provenance.json", "study_results.json"}
    for candidate in RUNS:
        expected.update(
            f"runs/{candidate}/inputs/{name}"
            for name in ("scale.cfg", "topology.csv", "layout.csv")
        )
        expected.update(
            f"runs/{candidate}/scalesim-results/{candidate}/{name}" for name in REPORTS
        )
    require(isinstance(manifest["files"], list), "manifest files must be a list")
    declared = set()
    for entry in manifest["files"]:
        equal(
            set(entry),
            {"path", "sha256", "size_bytes", "replay_stable"},
            "manifest entry",
        )
        name = entry["path"]
        require(name not in declared, f"duplicate manifest path: {name}")
        declared.add(name)
        path = local_file(reference, name)
        equal(path.stat().st_size, entry["size_bytes"], f"{name}: byte count")
        equal(sha256(path), entry["sha256"], f"{name}: SHA256")
        equal(
            entry["replay_stable"],
            name != "execution_provenance.json",
            f"{name}: stability",
        )
    equal(declared, expected, "manifest inventory (75 files)")
    actual = {
        path.relative_to(reference).as_posix()
        for path in reference.rglob("*")
        if path.is_file()
    }
    equal(actual, expected | {"reference_manifest.json"}, "reference inventory")

    provenance = read_json(root / "recorded/model/provenance.json")
    response_path = local_file(root, provenance["result"]["stored_output_path"])
    equal(
        sha256(response_path),
        provenance["result"]["stored_output_sha256"],
        "model response SHA256",
    )
    equal(
        response_path.stat().st_size,
        provenance["result"]["stored_output_bytes"],
        "model response bytes",
    )
    schema = local_file(root, provenance["request"]["output_schema_path"])
    equal(
        sha256(schema),
        provenance["request"]["output_schema_sha256"],
        "response schema SHA256",
    )
    equal(
        provenance["request"]["prompt_sha256"],
        RECORDED_PROMPT_HASH,
        "recorded prompt hash",
    )
    equal(
        sha256(local_file(root, provenance["request"]["prompt_path"])),
        PROMPT_HASH,
        "retained prompt (known historical mismatch)",
    )
    response = read_json(response_path)
    equal(response["schema_version"], "arch2-ai-proposal/v1", "model response version")
    equal(
        [
            (r["candidate_id"], r["array_rows"], r["array_cols"])
            for r in response["candidates"]
        ],
        [(cid, RUNS[cid][1], RUNS[cid][2]) for cid in RUNS if cid.startswith("ai_")],
        "model candidates",
    )

    result = read_json(reference / "study_results.json")
    equal(
        set(result),
        {
            "ai_contribution_claim",
            "architecture_outcome_claim",
            "budgets",
            "evaluations",
            "evidence_status",
            "freeze",
            "mechanism_claim",
            "model_interaction",
            "recommendation",
            "schema_version",
            "storage_policy",
            "study_id",
        },
        "result fields",
    )
    equal(result["schema_version"], "arch2-ai-study-results/v1", "result version")
    equal(result["study_id"], STUDY, "result study")
    records = result["evaluations"]
    equal(
        [r["candidate_id"] for r in records],
        list(RUNS),
        "twelve evaluations in recorded order",
    )
    jsonl = [
        parse_json(line)
        for line in (reference / "evaluations.jsonl").read_text().splitlines()
    ]
    equal(jsonl, records, "evaluation JSONL vs result")
    equal(
        result["budgets"],
        {
            "model_arm_scalesim_evaluations": 4,
            "conventional_arm_scalesim_evaluations": 4,
            "shared_mechanism_probe_evaluations": 4,
        },
        "budgets",
    )
    for name, relative in (
        ("workload_sha256", "workloads/xr_slice_gemm.csv"),
        ("transposed_workload_sha256", "workloads/xr_slice_gemm_transposed.csv"),
        ("layout_sha256", "layouts/default_layout.csv"),
    ):
        equal(
            sha256(local_file(root, relative)), result["freeze"][name], f"freeze.{name}"
        )
    for record in records:
        candidate = record["candidate_id"]
        arm, rows, cols, workload = RUNS[candidate]
        fields = {
            "arm",
            "array_cols",
            "array_rows",
            "candidate_id",
            "decision_score",
            "evaluation_id",
            "gate_result",
            "gates",
            "inputs",
            "metrics",
            "pe_count",
            "raw_outputs",
            "source",
            "status",
            "tool",
            "workload_id",
        }
        equal(
            set(record),
            fields | ({"disposition"} if arm != "mechanism_probe" else set()),
            "evaluation fields",
        )
        for field, value in {
            "arm": arm,
            "array_rows": rows,
            "array_cols": cols,
            "workload_id": workload,
            "evaluation_id": candidate,
            "pe_count": rows * cols,
            "status": "ok",
            "gate_result": "pass",
            "tool": {"name": "SCALE-Sim", "version": "3.0.0"},
        }.items():
            equal(record[field], value, f"{candidate}.{field}")

        def file_record(relative):
            return {"path": relative, "sha256": sha256(local_file(reference, relative))}

        equal(
            record["inputs"],
            {
                key: file_record(f"runs/{candidate}/inputs/{name}")
                for key, name in (
                    ("config", "scale.cfg"),
                    ("layout", "layout.csv"),
                    ("topology", "topology.csv"),
                )
            },
            f"{candidate}: input records",
        )
        equal(
            record["raw_outputs"],
            [
                file_record(f"runs/{candidate}/scalesim-results/{candidate}/{name}")
                for name in sorted(REPORTS)
            ],
            f"{candidate}: output records",
        )
        inputs = reference / "runs" / candidate / "inputs"
        config = configparser.ConfigParser()
        config.read(inputs / "scale.cfg")
        equal(config["general"]["run_name"], candidate, f"{candidate}: config run name")
        equal(
            config.getint("architecture_presets", "ArrayHeight"),
            rows,
            f"{candidate}: height",
        )
        equal(
            config.getint("architecture_presets", "ArrayWidth"),
            cols,
            f"{candidate}: width",
        )
        workload_file = (
            root
            / "workloads"
            / (
                "xr_slice_gemm_transposed.csv"
                if workload == "transposed"
                else "xr_slice_gemm.csv"
            )
        )
        equal(
            sha256(inputs / "topology.csv"),
            sha256(workload_file),
            f"{candidate}: workload",
        )
        equal(
            sha256(inputs / "layout.csv"),
            result["freeze"]["layout_sha256"],
            f"{candidate}: layout",
        )
        computed = metrics(report_dir(reference, candidate))
        equal(record["metrics"], computed, f"{candidate}: recomputed metrics")
        score = computed["total_cycles"] / (computed["avg_layer_util_pct"] / 100)
        equal(
            record["decision_score"], score, f"{candidate}: recomputed decision score"
        )
        equal(
            record["gates"],
            {
                "area_budget": {
                    "criterion": "pe_count <= 1024",
                    "observed": rows * cols,
                    "passed": rows * cols <= 1024,
                },
                "deadline": {
                    "criterion": "total_cycles <= 90000",
                    "observed": computed["total_cycles"],
                    "passed": computed["total_cycles"] <= 90000,
                },
            },
            f"{candidate}: gates",
        )
        require(
            all(gate["passed"] for gate in record["gates"].values()),
            f"{candidate}: gate_result is pass but a recomputed gate fails",
        )
    verify_outcome(result, response)
    return result


def verify_outcome(result, response):
    records = result["evaluations"]
    score = lambda r: r["decision_score"]
    improvement = lambda old, new: (old - new) / old * 100
    model = [r for r in records if r["arm"] == "model"]
    conventional = [r for r in records if r["arm"] == "conventional"]
    baseline = model[0]
    best = min(
        [r for r in model + conventional if "baseline" not in r["candidate_id"]],
        key=score,
    )
    architecture = result["architecture_outcome_claim"]
    for field, value in {
        "baseline_candidate_id": baseline["candidate_id"],
        "baseline_score": score(baseline),
        "best_candidate_id": best["candidate_id"],
        "best_score": score(best),
        "best_shape": [best["array_rows"], best["array_cols"]],
        "improvement_pct": improvement(score(baseline), score(best)),
        "status": "null_at_preregistered_margin",
    }.items():
        equal(architecture[field], value, f"architecture.{field}")
    require(
        architecture["improvement_pct"] < 1, "recorded null outcome no longer holds"
    )
    ai = result["ai_contribution_claim"]
    for arm, group in (("model", model), ("conventional", conventional)):
        best = min(group, key=score)
        for field, value in {
            "candidate_id": best["candidate_id"],
            "score": score(best),
            "shape": [best["array_rows"], best["array_cols"]],
        }.items():
            equal(ai[f"{arm}_best_{field}"], value, f"{arm} best {field}")
        for r in group:
            disposition = (
                "tied_best_in_arm_at_preregistered_margin"
                if abs(improvement(score(best), score(r))) < 1
                else "evaluated_and_dominated_in_arm"
            )
            equal(r["disposition"], disposition, f"{r['candidate_id']}: disposition")
    advantage = improvement(
        score(min(conventional, key=score)), score(min(model, key=score))
    )
    equal(ai["model_advantage_pct"], advantage, "model advantage")
    equal(ai["status"], "tie", "AI outcome")
    require(abs(advantage) < 1, "recorded tie no longer holds")
    mechanism = result["mechanism_claim"]
    for workload in ("original", "transposed"):
        pair = sorted(
            [
                r
                for r in records
                if r["arm"] == "mechanism_probe" and r["workload_id"] == workload
            ],
            key=score,
        )
        margin = improvement(score(pair[1]), score(pair[0]))
        require(margin >= 1, "mechanism probe no longer clears margin")
        equal(
            mechanism[f"observed_{workload}_winner"],
            f"{pair[0]['array_rows']}x{pair[0]['array_cols']}",
            "probe winner",
        )
        equal(mechanism[f"{workload}_margin_pct"], margin, "probe margin")
    equal(mechanism["predicted_original_winner"], "16x64", "original prediction")
    equal(mechanism["predicted_transposed_winner"], "64x16", "transposed prediction")
    equal(
        mechanism["falsifier"],
        response["discriminating_test"]["falsifier"],
        "recorded falsifier",
    )
    equal(mechanism["status"], "falsified", "mechanism outcome")
    require(
        mechanism["observed_transposed_winner"]
        != mechanism["predicted_transposed_winner"],
        "falsifier not met",
    )
    equal(
        result["recommendation"]["candidate_id"],
        baseline["candidate_id"],
        "retain baseline",
    )
    equal(
        result["recommendation"]["shape"],
        [baseline["array_rows"], baseline["array_cols"]],
        "recommendation.shape must match selected candidate",
    )
    equal(
        result["recommendation"]["accountable_decision_status"],
        "awaiting_author_confirmation",
        "historical decision status",
    )


def compare_reports(reference_dir, replay_dir):
    differences = 0
    for name in REPORTS:
        expected, observed = report_rows(reference_dir / name), report_rows(
            replay_dir / name
        )
        for layer, (old, new) in enumerate(zip(expected, observed)):
            for field in REPORTS[name]:
                a, b = Decimal(old[field]), Decimal(new[field])
                if a != b:
                    require(
                        field == "Compute Util %"
                        and abs(a - b) <= COMPUTE_UTIL_ABS_TOL,
                        f"{name} layer {layer} {field}: replay mismatch ({a} != {b})",
                    )
                    differences += 1
    return differences


def replay(root, output):
    root = Path(root).resolve()
    raw_output = Path(output).absolute()
    require(
        not raw_output.exists() and not raw_output.is_symlink(),
        "output must be a new directory; nothing will be overwritten",
    )
    output = raw_output.resolve()
    require(
        not output.is_relative_to(root),
        "output must be outside the retained study directory",
    )
    result = verify(root)
    require(
        importlib.metadata.version("scalesim") == "3.0.0",
        "replay requires SCALE-Sim 3.0.0",
    )
    from scalesim.scale_sim import scalesim

    output.mkdir(parents=True, exist_ok=False)
    (output / "runs").mkdir()
    summary = {
        "study_id": STUDY,
        "status": "running",
        "python": platform.python_version(),
        "scalesim": "3.0.0",
        "prompt_warning": PROMPT_WARNING,
        "runs": [],
    }
    try:
        for record in result["evaluations"]:
            candidate = record["candidate_id"]
            inputs = root / "recorded/reference/runs" / candidate / "inputs"
            with (output / f"{candidate}.log").open(
                "w"
            ) as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                simulator = scalesim(
                    save_disk_space=True,
                    verbose=False,
                    config=str(inputs / "scale.cfg"),
                    topology=str(inputs / "topology.csv"),
                    layout=str(inputs / "layout.csv"),
                    input_type_gemm=True,
                )
                simulator.run_scale(top_path=str(output / "runs" / candidate))
            destination = output / "runs" / candidate / candidate
            differences = compare_reports(
                report_dir(root / "recorded/reference", candidate), destination
            )
            computed = metrics(destination)
            equal(
                computed["total_cycles"] / (computed["avg_layer_util_pct"] / 100),
                record["decision_score"],
                f"{candidate}: replay score",
            )
            summary["runs"].append(
                {
                    "candidate_id": candidate,
                    "decision_score": record["decision_score"],
                    "compute_util_roundoff_cells": differences,
                }
            )
            print(f"matched {candidate}")
        summary["status"] = "matched"
    except Exception as exc:
        summary["status"] = "failed"
        summary["error"] = str(exc)
        raise
    finally:
        (output / "replay_summary.json").write_text(
            json.dumps(summary, indent=2) + "\n"
        )
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "verify",
        help="check archived hashes, raw metrics and study outcomes without simulation",
    )
    rerun = sub.add_parser(
        "replay",
        help="verify, then independently rerun all twelve retained SCALE-Sim inputs",
    )
    rerun.add_argument(
        "--output",
        required=True,
        type=Path,
        help="new directory outside the study; existing paths are refused",
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            verify()
            print(
                "Verified 75 archived file hashes, twelve evaluations, metrics and retained outcomes."
            )
        else:
            replay(ROOT, args.output)
            print(
                f"All twelve simulations match; report: {args.output / 'replay_summary.json'}"
            )
        print(f"Known limitation: {PROMPT_WARNING}")
        return 0
    except (
        ReplayError,
        OSError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
        configparser.Error,
        importlib.metadata.PackageNotFoundError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
