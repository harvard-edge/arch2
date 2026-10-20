#!/usr/bin/env python3
"""Extract and reconcile Ibex regression summary and failure records."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "raw/ibex-opentitan-latest-report.html"
DEFAULT_OUT = ROOT / "derived"


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class ReportParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None
        self.pre = False
        self.pre_text = ""
        self.pres = []
        self.h2 = False
        self.h2_text = ""
        self.headings = []
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table":
            self.table = []
        elif tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = ""
        elif tag == "pre":
            self.pre = True
            self.pre_text = ""
        elif tag == "h2":
            self.h2 = True
            self.h2_text = ""
        elif tag == "a" and attrs.get("href"):
            self.hrefs.append(attrs["href"])

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.row is not None and self.cell is not None:
            self.row.append(self.cell.strip())
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            if self.table is not None:
                self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None
        elif tag == "pre" and self.pre:
            self.pres.append(self.pre_text)
            self.pre = False
        elif tag == "h2" and self.h2:
            self.headings.append(self.h2_text.strip())
            self.h2 = False

    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data
        if self.pre:
            self.pre_text += data
        if self.h2:
            self.h2_text += data


def to_int(value: str) -> int:
    return int(value.replace(",", ""))


def parse_failure(block: str):
    lines = [line.rstrip() for line in block.splitlines()]
    nonempty = [line.strip() for line in lines if line.strip()]
    if not nonempty:
        raise ValueError("Empty failure detail block")
    run_id = nonempty[0]
    match = re.fullmatch(r"(.+)\.(\d+)", run_id)
    if not match:
        raise ValueError(f"Unexpected failure run identity: {run_id!r}")
    test_name, seed = match.group(1), match.group(2)
    marker = next(
        (
            line.strip()
            for line in nonempty
            if line.strip().startswith("[FAILED]")
            or line.strip().startswith("[FAILURE]")
        ),
        "",
    )
    primary_lines = [
        line.strip()
        for line in nonempty
        if re.search(r"\[E\].*\bUVM_(?:FATAL|ERROR)\b", line)
    ]
    primary = primary_lines[0] if primary_lines else marker
    if "UVM_FATAL" in primary:
        signature = "UVM_FATAL"
    elif "UVM_ERROR" in primary:
        signature = "UVM_ERROR"
    elif marker.startswith("[FAILURE]") and "timeout" in marker.lower():
        signature = "simulation ended due to timeout (explicit report message)"
    elif "error seen in" in marker:
        signature = "log error marker; cause not parsed"
    elif marker:
        signature = marker.split(":", 1)[0]
    else:
        signature = "no parsed signature"
    return {
        "run_id": run_id,
        "test_name": test_name,
        "seed": seed,
        "detail_status": "reported nonpassing run",
        "failure_marker": marker,
        "failure_signature": signature,
        "primary_diagnostic": primary,
        "primary_error_lines": "\n".join(primary_lines),
        "raw_detail": block.strip(),
    }


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--outdir", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    source = args.input.read_bytes()
    parser = ReportParser()
    parser.feed(source.decode("utf-8", "replace"))

    # Select the named summary table, then parse every row until its Total row.
    summary_headers = ["Test Name", "Passing", "Total", "Pass Rate"]
    summary_table = next(
        (table for table in parser.tables if summary_headers in table), None
    )
    if summary_table is None:
        raise SystemExit("Could not find the report's test summary table")
    header_index = summary_table.index(summary_headers)
    data_rows = []
    total_row = None
    for row in summary_table[header_index + 1 :]:
        if not row:
            continue
        if row[0] == "Total":
            if len(row) != 4:
                raise SystemExit(f"Malformed Total row: {row}")
            total_row = row
            break
        if len(row) != 4 or not row[0]:
            raise SystemExit(f"Malformed primary summary row: {row}")
        try:
            passing_runs = to_int(row[1])
            total_runs = to_int(row[2])
            reported_pct = float(row[3].split("%", 1)[0])
        except (ValueError, IndexError) as exc:
            raise SystemExit(f"Malformed primary summary row: {row}: {exc}")
        if (
            passing_runs < 0
            or total_runs < passing_runs
            or (total_runs == 0 and passing_runs != 0)
        ):
            raise SystemExit(f"Invalid run counts in primary summary row: {row}")
        data_rows.append(
            {
                "test_name": row[0],
                "passing_runs": passing_runs,
                "total_runs": total_runs,
                "reported_pass_rate_pct": reported_pct,
            }
        )
    if not data_rows or total_row is None:
        raise SystemExit("Primary summary table has no test rows or Total row")
    names = [row["test_name"] for row in data_rows]
    if len(names) != len(set(names)):
        raise SystemExit("Duplicate test name in primary summary table")
    for row in data_rows:
        row["nonpassing_runs"] = row["total_runs"] - row["passing_runs"]
        row["calculated_pass_rate_pct"] = (
            round(100 * row["passing_runs"] / row["total_runs"], 4)
            if row["total_runs"]
            else None
        )
        if (
            row["total_runs"]
            and abs(row["reported_pass_rate_pct"] - row["calculated_pass_rate_pct"])
            > 0.051
        ):
            raise SystemExit(
                f"Published pass percentage does not round from counts: {row['test_name']}"
            )

    reported_passes = to_int(total_row[1])
    reported_total = to_int(total_row[2])
    total_details = [parse_failure(b) for b in parser.pres]
    details_by_test = Counter(d["test_name"] for d in total_details)
    summary_failures = {r["test_name"]: r["nonpassing_runs"] for r in data_rows}
    mismatches = {
        name: {
            "summary_nonpassing_runs": summary_failures.get(name, 0),
            "failure_detail_blocks": details_by_test.get(name, 0),
        }
        for name in sorted(set(summary_failures) | set(details_by_test))
        if summary_failures.get(name, 0) != details_by_test.get(name, 0)
    }
    run_ids = [d["run_id"] for d in total_details]
    duplicate_run_ids = sorted(
        run_id for run_id, count in Counter(run_ids).items() if count > 1
    )
    sum_passes = sum(r["passing_runs"] for r in data_rows)
    sum_total = sum(r["total_runs"] for r in data_rows)
    sum_failures = sum(r["nonpassing_runs"] for r in data_rows)
    if sum_passes != reported_passes or sum_total != reported_total:
        raise SystemExit(
            f"Per-test totals do not reconcile to report Total row: {sum_passes}/{sum_total} vs {reported_passes}/{reported_total}"
        )
    if sum_failures != len(total_details) or mismatches or duplicate_run_ids:
        raise SystemExit(
            f"Failure details do not reconcile: summary failures={sum_failures}, detail blocks={len(total_details)}, per-test mismatches={mismatches}, duplicate run ids={duplicate_run_ids}"
        )

    coverage_headers = [
        "Functional",
        "Block",
        "Branch",
        "Statement",
        "Expression",
        "Toggle",
        "FSM",
        "Assertion",
    ]
    coverage_table = next(
        (table for table in parser.tables if coverage_headers in table), None
    )
    coverage_row = None
    if coverage_table is not None:
        coverage_idx = coverage_table.index(coverage_headers)
        if coverage_idx + 1 < len(coverage_table):
            coverage_row = coverage_table[coverage_idx + 1]
    coverage_names = [
        "functional",
        "block",
        "branch",
        "statement",
        "expression",
        "toggle",
        "fsm",
        "assertion",
    ]
    coverage = []
    if coverage_row:
        coverage = [
            {
                "coverage_measure": name,
                "reported_pct": float(value.rstrip("%")),
                "unit": "percentage reported by HTML",
                "population_semantics": "not specified in this report",
            }
            for name, value in zip(coverage_names, coverage_row)
        ]

    text = source.decode("utf-8", "replace")
    run_time = re.search(r"Date/Time run:\s*([^<]+)", text)
    commit = re.search(r"/tree/([0-9a-f]{40})", text)
    json_input = ROOT / "raw/ibex-opentitan-latest-report.json"
    json_crosscheck = {"available": False}
    if json_input.exists():
        machine_report = json.loads(json_input.read_text(encoding="utf-8"))
        machine_rows = machine_report.get("results", {}).get("unmapped_tests", [])
        machine_map = {item.get("name"): item for item in machine_rows}
        if len(machine_map) != len(machine_rows):
            raise SystemExit("Duplicate test name in machine-readable report")
        html_map = {row["test_name"]: row for row in data_rows}
        differences = []
        for name in sorted(set(html_map) | set(machine_map)):
            html_row = html_map.get(name)
            json_row = machine_map.get(name)
            if (
                html_row is None
                or json_row is None
                or html_row["passing_runs"] != json_row.get("passing_runs")
                or html_row["total_runs"] != json_row.get("total_runs")
            ):
                differences.append(name)
        if differences:
            raise SystemExit(
                f"HTML summary and machine-readable report.json differ for: {differences}"
            )
        json_crosscheck = {
            "available": True,
            "matches_html_per_test_counts": True,
            "json_sha256": sha256(json_input.read_bytes()),
            "note": "Both artifacts come from the same report pipeline; this is a format cross-check, not an independent run.",
        }
    args.outdir.mkdir(parents=True, exist_ok=True)
    write_csv(
        args.outdir / "test_summary.csv",
        data_rows,
        [
            "test_name",
            "passing_runs",
            "nonpassing_runs",
            "total_runs",
            "reported_pass_rate_pct",
            "calculated_pass_rate_pct",
        ],
    )
    write_csv(
        args.outdir / "failure_details.csv",
        total_details,
        [
            "run_id",
            "test_name",
            "seed",
            "detail_status",
            "failure_signature",
            "failure_marker",
            "primary_diagnostic",
            "primary_error_lines",
            "raw_detail",
        ],
    )
    write_csv(
        args.outdir / "coverage_summary.csv",
        coverage,
        ["coverage_measure", "reported_pct", "unit", "population_semantics"],
    )
    report = {
        "extracted_utc": datetime.now(timezone.utc).isoformat(),
        "input_path": str(args.input.relative_to(ROOT))
        if args.input.is_relative_to(ROOT)
        else str(args.input),
        "input_sha256": sha256(source),
        "report_run_time_text": run_time.group(1).strip() if run_time else None,
        "ibex_commit": commit.group(1) if commit else None,
        "observation_unit": "one reported test-run record; the failure-detail identifier is test_name.seed. The 1,530 denominator is this report's records, not all scheduled/build/generator attempts.",
        "counts": {
            "test_rows": len(data_rows),
            "all_passing_test_groups": sum(
                r["nonpassing_runs"] == 0 for r in data_rows
            ),
            "test_groups_with_nonpasses": sum(
                r["nonpassing_runs"] > 0 for r in data_rows
            ),
            "reported_passes": reported_passes,
            "reported_total_runs": reported_total,
            "reported_nonpassing_runs": reported_total - reported_passes,
            "aggregate_pass_rate_pct": round(100 * reported_passes / reported_total, 2),
            "failure_detail_blocks": len(total_details),
            "unique_failure_run_ids": len(set(run_ids)),
        },
        "reconciliation": {
            "per_test_and_total_counts_match": True,
            "nonpassing_runs_equal_failure_detail_blocks": True,
            "per_test_failures_equal_detail_blocks": True,
            "duplicate_failure_run_ids": duplicate_run_ids,
            "per_test_mismatches": mismatches,
        },
        "failure_signatures_are_descriptive_only": True,
        "failure_signature_counts": dict(
            Counter(d["failure_signature"] for d in total_details)
        ),
        "failure_signature_note": "Signature buckets record literal UVM_FATAL/UVM_ERROR markers or an unparsed log marker. They are descriptive extraction aids, not root-cause classifications.",
        "missing_observations": {
            "individual passing run IDs": "not published in this HTML",
            "CI job ID": "not published",
            "immutable upstream report URL": "not exposed; source URL is latest",
            "failure categories/root causes": "not assigned; diagnostic excerpts are raw reported simulator/log messages",
            "run configuration and seed policy": "not stated in this HTML; consult repository and CI workflow separately",
        },
        "coverage": coverage,
        "machine_readable_crosscheck": json_crosscheck,
    }
    (args.outdir / "extraction_audit.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    failure_json = {"counts": report["counts"], "records": total_details}
    (args.outdir / "failure_details.json").write_text(
        json.dumps(failure_json, indent=2) + "\n", encoding="utf-8"
    )
    print(args.outdir / "test_summary.csv")
    print(args.outdir / "failure_details.csv")
    print(args.outdir / "coverage_summary.csv")
    print(args.outdir / "extraction_audit.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
