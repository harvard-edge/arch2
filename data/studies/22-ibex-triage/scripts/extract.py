#!/usr/bin/env python3
"""Extract test outcomes and explicit author mappings from preserved Ibex sources.

This is an offline parser. It does not infer root cause from log signatures.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SOURCE = HERE / "source"
sys.path.insert(0, str(HERE.parent))
from evidence_bundle import record_build, verify_sources


def csv_write(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def verify_source_manifest() -> None:
    shared_manifest = verify_sources(HERE)
    manifest_path = HERE / "source-manifest.csv"
    if not manifest_path.is_file():
        raise ValueError("Missing source-manifest.csv")
    with manifest_path.open(newline="", encoding="utf-8") as f:
        entries = list(csv.DictReader(f))
    if not entries:
        raise ValueError("Source manifest has no entries")
    json_entries = {item["path"]: item for item in shared_manifest["files"]}
    csv_entries = {entry["file"]: entry for entry in entries}
    if set(json_entries) != set(csv_entries):
        raise ValueError("JSON and CSV source manifests cover different paths")
    seen = set()
    for entry in entries:
        name = entry["file"]
        if name in seen:
            raise ValueError(f"Duplicate source manifest path: {name}")
        seen.add(name)
        if (
            json_entries[name]["sha256"] != entry["sha256"]
            or json_entries[name]["url"] != entry["source_url"]
        ):
            raise ValueError(f"JSON and CSV source manifest entries differ: {name}")
        path = HERE / name
        if not path.is_file():
            raise ValueError(f"Missing manifested source: {name}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != entry["sha256"]:
            raise ValueError(f"Source hash mismatch: {name}")


def read_summary(log: str):
    summary = log.split("# Details of failing tests", 1)[0]
    declared = re.search(r"([\d.]+)% PASS (\d+) PASSED, (\d+) FAILED", summary)
    if not declared:
        raise ValueError("Could not read declared regression summary")
    rows = []
    for line_no, line in enumerate(summary.splitlines(), 1):
        m = re.match(r"^(\S+):\s+(PASS|FAILED(?:\s+\{[^}]+\})?)\s*$", line)
        if not m:
            continue
        test_case, status_text = m.groups()
        test, seed = test_case.rsplit(".", 1)
        rows.append(
            {
                "test_case": test_case,
                "test": test,
                "seed": seed,
                "status": "PASS" if status_text == "PASS" else "FAIL",
                "status_marker": status_text,
                "summary_line": line_no,
            }
        )
    cases = [r["test_case"] for r in rows]
    if len(cases) != len(set(cases)):
        duplicates = sorted(c for c in set(cases) if cases.count(c) > 1)
        raise ValueError(f"Duplicate test_case in run summary: {duplicates}")
    return declared.groups(), rows


def detailed_blocks(log: str):
    part = log.split("# Details of failing tests", 1)[1].split(
        "# Details of passing tests", 1
    )[0]
    lines = part.splitlines()
    blocks = {}
    for i, line in enumerate(lines):
        m = re.match(r"^(riscv_[A-Za-z0-9_]+\.\d+)(?:\s+-\s+(.*))?$", line)
        if not m:
            continue
        case, heading = m.groups()
        j = i + 1
        while j < len(lines) and not re.match(
            r"^riscv_[A-Za-z0-9_]+\.\d+(?:\s+-\s+.*)?$", lines[j]
        ):
            j += 1
        if case in blocks:
            raise ValueError(f"Duplicate detailed failure block: {case}")
        blocks[case] = (heading or "", "\n".join(lines[i:j]))
    return blocks


def first_signature(block: str):
    for pat in (
        r"^\[E\]\s+\d+:\s+(.+)$",
        r"^\[FAILURE\]\s+(.+)$",
        r"^\[FAILED\]:\s+(.+)$",
    ):
        m = re.search(pat, block, re.M)
        if m:
            return m.group(1).strip()
    return ""


def explicit_issue_pairs(body: str):
    first_section = body.split("## Failures", 1)[1].split(
        "Failures in riscv_assorted_traps_interrupts_debug_test", 1
    )[0]
    second_section = body.rsplit("## Failures", 1)[1]
    pairs = []
    for run, section in (("first", first_section), ("second", second_section)):
        for line in section.splitlines():
            m = re.match(
                r"\s*-\s+(riscv_[A-Za-z0-9_]+\.\d+)\s+-\s+Signature\s+(\d+)\s*$", line
            )
            if m:
                pairs.append(
                    {"run": run, "test_case": m.group(1), "issue_signature": m.group(2)}
                )
    return pairs


def signatures(body: str):
    out = {}
    # The issue uses one ordered list of nine first-run explanations and one
    # ordered list of five second-run explanations, each with a quoted signature.
    for run, start, stop in (
        ("first", "## Failure explanations and associated signatures", "## Failures"),
        ("second", "## Signatures", "## Failures"),
    ):
        section = body.split(start, 1)[1].split(stop, 1)[0]
        matches = list(
            re.finditer(r"(?m)^\s*(\d+)\. (?:`([^`]+)`|([^\n]+))\s*$", section)
        )
        for idx, m in enumerate(matches):
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(section)
            text = section[m.end() : end].strip()
            out[(run, m.group(1))] = {
                "reported_signature": m.group(2) or m.group(3),
                "reported_explanation": text,
            }
    expected = {"first": 9, "second": 5}
    for run, count in expected.items():
        actual = [key for key in out if key[0] == run]
        if len(actual) != count:
            raise ValueError(
                f"Expected {count} {run}-run signatures, parsed {len(actual)}"
            )
        if any(not out[key]["reported_explanation"].strip() for key in actual):
            raise ValueError(f"Empty reported explanation in {run}-run signature table")
    return out


def main():
    verify_source_manifest()
    body = (SOURCE / "issue-2187-body.md").read_text(encoding="utf-8")
    run_info = {
        "first": ("regr-first.log", "1449ed5ea8f3d03127f7c3624e635e132830367d"),
        "second": ("regr-second.log", "3384bf4c421781a2f5129307b912ac586c784977"),
    }
    all_results, failures, run_summary = [], [], []
    by_run = {}
    for run, (filename, commit) in run_info.items():
        log = (SOURCE / filename).read_text(encoding="utf-8", errors="replace")
        declared, rows = read_summary(log)
        blocks = detailed_blocks(log)
        counts = Counter(r["status"] for r in rows)
        if (int(declared[1]), int(declared[2])) != (counts["PASS"], counts["FAIL"]):
            raise ValueError(f"Summary mismatch in {filename}: {declared} vs {counts}")
        if set(blocks) != {r["test_case"] for r in rows if r["status"] == "FAIL"}:
            raise ValueError(f"Failure detail coverage mismatch in {filename}")
        for row in rows:
            full = {"run": run, "commit": commit, **row, "source_log": filename}
            all_results.append(full)
            if row["status"] == "FAIL":
                heading, block = blocks[row["test_case"]]
                failures.append(
                    {
                        **full,
                        "detail_heading": heading,
                        "raw_failure_evidence": first_signature(block),
                        "detail_block_line_count": len(block.splitlines()),
                        "interpretation": "raw report evidence; no root-cause inference",
                    }
                )
        run_summary.append(
            {
                "run": run,
                "commit": commit,
                "source_log": filename,
                "declared_pass_percent": declared[0],
                "declared_passed": declared[1],
                "declared_failed": declared[2],
                "parsed_total": len(rows),
                "parsed_passed": counts["PASS"],
                "parsed_failed": counts["FAIL"],
                "all_failed_cases_have_detail_blocks": "yes",
            }
        )
        by_run[run] = rows

    sig = signatures(body)
    explicit_pairs = explicit_issue_pairs(body)
    pair_keys = [(p["run"], p["test_case"]) for p in explicit_pairs]
    if len(pair_keys) != len(set(pair_keys)):
        duplicates = sorted(k for k in set(pair_keys) if pair_keys.count(k) > 1)
        raise ValueError(f"Duplicate explicit issue mapping keys: {duplicates}")
    pair_rows = []
    for pair in explicit_pairs:
        run, num = pair["run"], pair["issue_signature"]
        detail = sig.get((run, num), {})
        if (
            not detail
            or not detail.get("reported_signature", "").strip()
            or not detail.get("reported_explanation", "").strip()
        ):
            raise ValueError(
                f"Explicit mapping lacks a reported signature/explanation: {pair}"
            )
        result = next(
            (r for r in by_run[run] if r["test_case"] == pair["test_case"]), None
        )
        if not result or result["status"] != "FAIL":
            raise ValueError(f"Issue explicit pair is not a failed case: {pair}")
        pair_rows.append(
            {
                **pair,
                "commit": run_info[run][1],
                "test": result["test"],
                "seed": result["seed"],
                "reported_signature": detail.get("reported_signature", ""),
                "reported_explanation": detail.get("reported_explanation", ""),
                "mapping_basis": "explicit issue bullet mapping",
                "root_cause_status": "issue-author diagnosis; not independently reproduced",
            }
        )

    # Four test families were expressly set aside from the first-run seed map
    # and were targeted in the second investigation. Counts here reconcile
    # each complete run without implying like-for-like seeds or causation.
    groups = [
        "riscv_assorted_traps_interrupts_debug_test",
        "riscv_pmp_basic_test",
        "riscv_pmp_out_of_bounds_test",
        "riscv_pmp_full_random_test",
    ]
    group_rows = []
    for group in groups:
        record = {
            "test_group": group,
            "first_run_issue_mapping": "expressly excluded from first-run seed map; second-run re-triage stated",
            "second_run_relation": "different seed range and commit; descriptive reconciliation only",
        }
        for run in ("first", "second"):
            vals = [r for r in by_run[run] if r["test"] == group]
            record[f"{run}_total"] = len(vals)
            record[f"{run}_passed"] = sum(r["status"] == "PASS" for r in vals)
            record[f"{run}_failed"] = sum(r["status"] == "FAIL" for r in vals)
        group_rows.append(record)

    csv_write(
        HERE / "run-results.csv",
        all_results,
        [
            "run",
            "commit",
            "test_case",
            "test",
            "seed",
            "status",
            "status_marker",
            "summary_line",
            "source_log",
        ],
    )
    csv_write(
        HERE / "failure-observations.csv",
        failures,
        [
            "run",
            "commit",
            "test_case",
            "test",
            "seed",
            "status",
            "status_marker",
            "summary_line",
            "source_log",
            "detail_heading",
            "raw_failure_evidence",
            "detail_block_line_count",
            "interpretation",
        ],
    )
    csv_write(
        HERE / "issue-explicit-mappings.csv",
        pair_rows,
        [
            "run",
            "commit",
            "test_case",
            "test",
            "seed",
            "issue_signature",
            "reported_signature",
            "reported_explanation",
            "mapping_basis",
            "root_cause_status",
        ],
    )
    csv_write(
        HERE / "retriaged-groups.csv",
        group_rows,
        [
            "test_group",
            "first_run_issue_mapping",
            "first_total",
            "first_passed",
            "first_failed",
            "second_total",
            "second_passed",
            "second_failed",
            "second_run_relation",
        ],
    )
    record_build(
        HERE,
        {
            "source_hashes_verified_before_extract": len(
                json.loads((HERE / "source_manifest.json").read_text(encoding="utf-8"))[
                    "files"
                ]
            ),
            "first_and_second_summaries_reconciled": True,
            "all_failure_detail_blocks_unique_and_covered": True,
            "explicit_issue_mappings_unique_and_explained": True,
            "signature_explanations_reconciled": True,
            "offline_extraction": True,
        },
        "Offline extraction from hash-verified public issue JSON and attached report bytes. The issue author's diagnosis is not an independent rerun or root-cause verification.",
    )
    print(
        f"Wrote {len(all_results)} test outcomes, {len(failures)} failure observations, {len(pair_rows)} explicit mappings, and {len(group_rows)} re-triaged group summaries"
    )


if __name__ == "__main__":
    main()
