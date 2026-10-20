"""Collect actual dequantizer diagnostic decisions from constructed RTL faults.

Run ``python -m nanochip.laboratory.datasets.dequant_corpus OUTPUT``. Each
candidate is a private copy, freshly compiled by the existing bounded probe.
Labels implement a disclosed teaching policy, not a recovered design trace,
an optimal action, or evidence that a learner repairs RTL.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from ..contracts import Artifact, ContractError, file_sha256
from ..dequant_probe import run_probe


ACTIONS = ("inspect_numerics", "inspect_protocol", "inspect_build", "accept_block")
LABEL_ORIGIN = "hand_authored_diagnostic_policy_v1; not optimal actions or original Kimi reasoning"
DEFAULT_SOURCE = Path(__file__).resolve().parents[2] / "kpu/rtl/msh_deq.v"
INPUT_SCHEMA = "anonymous_dequant_observation_v1"


@dataclass(frozen=True)
class Case:
    template: str
    split: str
    old: str = ""
    new: str = ""


# Every fault is deliberately constructed here, never attributed to the author
# of the frozen RTL. A template and its descendants belong to only one split.
CASES = (
    Case("reference", "train"),
    Case("output_shift", "train", "{w_acc[17:0], 14'b0}", "{w_acc[18:0], 13'b0}"),
    Case("zero_addition", "train", "- $signed({2'b0, w_zb[3:0]})", "+ $signed({2'b0, w_zb[3:0]})"),
    Case("early_done", "train", "assign done   = (state == S_WR) && (wr_i == j_d - 16'd1);", "assign done = (state == S_WR) && (wr_i == j_d - 16'd2);"),
    Case("address_offset", "train", "assign y_addr = {6'b0, wr_i[7:2]};", "assign y_addr = {6'b0, wr_i[7:2]} + 12'd1;"),
    Case("syntax_token", "train", "endmodule", "constructed_invalid_token\nendmodule"),
    Case("saturation_removed", "dev", "w_ovf ? 32'h7FFFFFFF", "1'b0 ? 32'h7FFFFFFF"),
    Case("nibbles_exchanged", "dev", "wr_i[0] ? w_qb[7:4] : w_qb[3:0]", "wr_i[0] ? w_qb[3:0] : w_qb[7:4]"),
    Case("stream_never_ready", "dev", "|| (state == S_Q)) && emit_idle;", "|| (state == S_Q)) && 1'b0;"),
    Case("buffer_decode", "dev", "assign y_buf  = j_ybuf;", "assign y_buf = j_ybuf == 4'd3 ? 4'd0 : j_ybuf;"),
    Case("undeclared_net", "dev", "assign y_buf  = j_ybuf;", "assign y_buf = nonexistent_buffer_signal;"),
    Case("scale_sign_reversed", "test", "w_acc = w_qz * w_s;", "w_acc = -(w_qz * w_s);"),
    Case("group_boundary", "test", "(wr_i >= {8'b0, j_gsz})", "(wr_i > {8'b0, j_gsz})"),
    Case("done_suppressed", "test", "assign done   = (state == S_WR) && (wr_i == j_d - 16'd1);", "assign done = 1'b0;"),
    Case("top_module_missing", "test", "module msh_deq (", "module constructed_other_top ("),
)


def construct_candidate(source: str, case: Case) -> str:
    """Apply one auditable literal mutation to a copy, with anchor checking."""
    if not case.old:
        return source
    if source.count(case.old) != 1:
        raise ContractError(f"Fault template anchor must occur once: {case.template}")
    return source.replace(case.old, case.new, 1)


def observation_text(receipt: dict[str, Any], simulation_log: str = "", build_log: str = "") -> str:
    """Allowlist only evidence available after this one run, excluding identity.

    Do not pass raw compiler logs: their filenames and source lines reveal the
    constructed fault. Numeric mismatch tuples carry observed values only.
    """
    checks = receipt.get("checks", {})
    fields = ("rows_completed", "lanes_checked", "mismatches", "cycles",
              "stream_stall_cycles", "producer_bubble_cycles", "protocol_error")
    first = re.findall(r"mismatch row=(\d+) lane=(\d+) expected=(\d+) observed=(\d+)", simulation_log)
    observation = {
        "schema": INPUT_SCHEMA,
        "scope": "finite constructed dequantizer block vectors; no physical evidence",
        "status": receipt["status"],
        "build_returncode": receipt.get("build", {}).get("returncode"),
        "simulation_returncode": receipt.get("simulation", {}).get("returncode"),
        "timed_out": any(receipt.get(stage, {}).get("timed_out", False)
                         for stage in ("version_probe", "build", "simulation")),
        "compiler_diagnostics": [label for needle, label in (
            ("syntax error", "syntax_error"),
            ("Can't find definition", "unresolved_identifier"),
            ("Specified --top-module", "missing_top_module"),
        ) if needle in build_log],
        "checks": {key: checks.get(key) for key in fields},
        "first_mismatches": [dict(zip(("row", "lane", "expected", "observed"), map(int, item)))
                             for item in first[:3]],
    }
    return json.dumps(observation, sort_keys=True, separators=(",", ":"), allow_nan=False)


# Public name for live inference on receipts from the same harness. This does
# not execute the diagnostic action and does not apply an RTL repair.
serialize_observation = observation_text


def teaching_action(receipt: dict[str, Any]) -> str:
    """A curator policy for the next diagnostic activity, frozen before learning."""
    if receipt.get("ok") is True and receipt.get("status") == "passed":
        return "accept_block"
    if receipt.get("status") in ("unavailable", "tool_failed", "build_failed"):
        return "inspect_build"
    if receipt.get("checks", {}).get("protocol_error"):
        return "inspect_protocol"
    if receipt.get("checks", {}).get("mismatches", 0) > 0:
        return "inspect_numerics"
    # Unclassified execution failures do not become numerical diagnoses.
    return "inspect_build"


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def collect_corpus(output_dir: Path, *, source_path: Path | None = None,
                   timeout_s: float = 120) -> dict[str, Any]:
    """Retain candidates, raw probe artifacts, hashes, labels, and measured costs.

    No cached results or fabricated successful runs are accepted. Missing tools
    remain failed receipts and the manifest explicitly reports that limitation.
    """
    source_path = Path(source_path or DEFAULT_SOURCE).resolve()
    source = source_path.read_text(encoding="utf-8")
    candidates = [construct_candidate(source, case) for case in CASES]
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise ValueError(f"corpus output directory must be empty: {output_dir}")
    records = []
    for index, (case, candidate_text) in enumerate(zip(CASES, candidates)):
        record_id = f"dequant-{index:03d}"
        case_dir = output_dir / record_id
        case_dir.mkdir()
        candidate = case_dir / "constructed.v"
        candidate.write_text(candidate_text, encoding="utf-8")
        receipt = run_probe(candidate, case_dir / "probe", timeout_s)
        simulation = case_dir / "probe/simulation.log"
        build_log = case_dir / "probe/build.log"
        receipt_path = case_dir / "probe/receipt.json"
        evidence_files = [p for p in (case_dir / "probe").iterdir() if p.is_file()]
        record = {
            "record_id": record_id, "group_id": f"dequant-template-{case.template}",
            "split": case.split,
            "input_text": observation_text(receipt, simulation.read_text() if simulation.exists() else "",
                                           build_log.read_text() if build_log.exists() else ""),
            "target_action": teaching_action(receipt),
            "source_receipt": {"path": str(receipt_path.relative_to(output_dir)),
                               "sha256": file_sha256(receipt_path)},
            "source_sha256": receipt["candidate_sha256"], "label_origin": LABEL_ORIGIN,
            "evidence_mode": "fresh", "construction": "reference" if not case.old else "constructed_fault",
            "fault_template": case.template,
            "lineage": {"common_base_sha256": file_sha256(source_path),
                        "mutation_parent": "common frozen reference",
                        "template_group": case.template, "literal_old": case.old, "literal_new": case.new},
            "cost": {"wall_seconds": receipt["total_elapsed_s"], "peak_memory_bytes": None},
            "evidence_artifacts": [{"path": str(path.relative_to(output_dir)),
                                    "sha256": file_sha256(path)} for path in sorted(evidence_files)],
        }
        records.append(record)
        print(f"{record_id}: {receipt['status']} ({receipt['total_elapsed_s']:.2f}s)", flush=True)
    record_file = output_dir / "records.jsonl"
    record_file.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in records), encoding="utf-8")
    seen: dict[str, set[str]] = {}
    for row in records:
        seen.setdefault(row["input_text"], set()).add(row["split"])
    manifest = {
        "schema_version": 1, "dataset_id": "nanochip-dequant-constructed-v1",
        "actions": list(ACTIONS), "label_origin": LABEL_ORIGIN,
        "records": {"path": "records.jsonl", "sha256": file_sha256(record_file)},
        "common_base": {"path": str(source_path), "sha256": file_sha256(source_path)},
        "collector_sha256": file_sha256(Path(__file__)),
        "counts": dict(Counter(row["split"] for row in records)),
        "action_counts": {split: dict(Counter(row["target_action"] for row in records if row["split"] == split))
                          for split in ("train", "dev", "test")},
        "total_wall_seconds": sum(row["cost"]["wall_seconds"] for row in records),
        "executed_builds": sum((output_dir / row["source_receipt"]["path"]).parent.joinpath("build.log").exists()
                               for row in records),
        "executed_simulations": sum((output_dir / row["source_receipt"]["path"]).parent.joinpath("simulation.log").exists()
                                    for row in records),
        "cross_split_duplicate_observations": sum(len(splits) > 1 for splits in seen.values()),
        "limits": [
            "15 deliberately constructed cases, one common RTL base and one finite vector suite",
            "Template groups are separate; common reference ancestry and workload are shared",
            "No passing reference examples in dev/test; accepted-observation copies would leak",
            "Hand-authored diagnostic labels are not optimal actions or original Kimi reasoning",
            "Only next diagnostic action prediction; no demonstrated RTL repair or GDS generation",
            "Small corpus cannot establish generalization to natural faults, designs, or workloads",
            "Peak memory not measured; elapsed time includes fresh build and simulation",
        ],
    }
    _write_json(output_dir / "manifest.json", manifest)
    load_corpus(output_dir / "manifest.json")
    return manifest


def load_corpus(manifest_path: Path | str) -> tuple[dict[str, Any], ...]:
    """Validate source/receipt linkage, observations, policy labels, and grouping."""
    manifest_path = Path(manifest_path)
    root = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("actions") != list(ACTIONS):
        raise ContractError("Unknown corpus schema or actions")
    records_artifact = Artifact(**manifest["records"])
    records_artifact.validate(root)
    records = tuple(json.loads(line) for line in records_artifact.resolve(root).read_text().splitlines() if line)
    groups: dict[str, str] = {}
    source_splits: dict[str, str] = {}
    observation_splits: dict[str, str] = {}
    identities: set[str] = set()
    for row in records:
        if row["record_id"] in identities or row["split"] not in ("train", "dev", "test"):
            raise ContractError("Duplicate record or unknown split")
        identities.add(row["record_id"])
        if row["label_origin"] != LABEL_ORIGIN or row["target_action"] not in ACTIONS:
            raise ContractError("Undisclosed labeling policy or unknown action")
        for key, index in ((row["group_id"], groups), (row["source_sha256"], source_splits),
                           (row["input_text"], observation_splits)):
            if key in index and index[key] != row["split"]:
                raise ContractError("Related or duplicate evidence crosses corpus partitions")
            index[key] = row["split"]
        receipt_artifact = Artifact(**row["source_receipt"])
        receipt_artifact.validate(root)
        receipt_path = receipt_artifact.resolve(root)
        receipt = json.loads(receipt_path.read_text())
        for artifact in row.get("evidence_artifacts", []):
            Artifact(**artifact).validate(root)
        if receipt.get("mode") != "fresh" or receipt["candidate_sha256"] != row["source_sha256"]:
            raise ContractError("Record does not match fresh source receipt")
        if file_sha256(receipt_path.parent / "candidate.v") != row["source_sha256"]:
            raise ContractError("Candidate snapshot changed")
        for field, name in (("bench_sha256", "dequant_tb.cpp"), ("vectors_sha256", "vectors.json"),
                            ("vector_text_sha256", "vectors.txt")):
            if file_sha256(receipt_path.parent / name) != receipt[field]:
                raise ContractError(f"Probe artifact changed: {name}")
        simulation = receipt_path.parent / "simulation.log"
        build_log = receipt_path.parent / "build.log"
        expected_input = observation_text(receipt, simulation.read_text() if simulation.exists() else "",
                                         build_log.read_text() if build_log.exists() else "")
        if row["input_text"] != expected_input or row["target_action"] != teaching_action(receipt):
            raise ContractError("Observation or teaching label does not match source receipt")
    if not records:
        raise ContractError("Corpus must contain records")
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()
    manifest = collect_corpus(args.output, source_path=args.source, timeout_s=args.timeout)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
