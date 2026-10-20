#!/usr/bin/env python3
"""Derive project-level community feedback counts from a retained TT06 snapshot."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import sys


STATUSES = ("working", "partial", "broken")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "snapshot", nargs="?", type=pathlib.Path, default=pathlib.Path(__file__).parent
    )
    args = parser.parse_args()
    root = args.snapshot.resolve()
    raw = root / "raw"
    source_manifest = json.loads((root / "source_manifest.json").read_text())
    manifest = json.loads((root / "capture-manifest.json").read_text())
    source_files = source_manifest.get("files", [])
    capture_files = {row["path"]: row for row in manifest.get("responses", [])}
    if not source_files or set(capture_files) != {
        row.get("path") for row in source_files
    }:
        raise SystemExit(
            "Source and capture manifests disagree; refusing offline extraction"
        )
    for row in source_files:
        path = root / row["path"]
        if not path.is_file():
            raise SystemExit(
                f"Missing frozen source {row['path']}; run collector.py to recover by pinned hash"
            )
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if (
            actual != row["sha256"]
            or capture_files[row["path"]]["sha256"] != row["sha256"]
        ):
            raise SystemExit(f"Frozen source hash mismatch: {row['path']}")
    index_bytes = (raw / "tt06-index.json").read_bytes()
    index = json.loads(index_bytes)
    aggregate = json.loads((raw / "all-shuttles-feedback.json").read_bytes())
    expected = manifest["population"]["indexed_macro_rows"]
    if len(index["projects"]) != expected or index["id"] != "tt06":
        raise SystemExit(
            "Snapshot and capture manifest population disagree; refusing extraction"
        )

    aggregate_working = {
        (item["shuttle"], item["macro"]): int(item["working"])
        for item in aggregate
        if item.get("shuttle") == "tt06"
    }
    rows = []
    feedback_rows = []
    errors = []
    for project in index["projects"]:
        macro = project["macro"]
        macro_key = hashlib.sha256(macro.encode("utf-8")).hexdigest()
        path = raw / "feedback" / f"{macro_key}.json"
        try:
            feedback = json.loads(path.read_bytes())
            if not isinstance(feedback, list):
                raise ValueError("API response is not a JSON list")
            if any(item.get("status") not in STATUSES for item in feedback):
                raise ValueError("API response has an unrecognized status")
            counts = {
                status: sum(item.get("status") == status for item in feedback)
                for status in STATUSES
            }
            working_from_detail = counts["working"]
            working_from_page_api = aggregate_working.get(("tt06", macro), 0)
            rows.append(
                {
                    "shuttle": "tt06",
                    "macro": macro,
                    "address": project.get("address", ""),
                    "title": project.get("title", ""),
                    "author": project.get("author", ""),
                    "repo": project.get("repo", ""),
                    "submitted_commit": project.get("commit", ""),
                    "feedback_records": len(feedback),
                    "working_records": counts["working"],
                    "partial_records": counts["partial"],
                    "broken_records": counts["broken"],
                    "report_presence": "feedback returned"
                    if feedback
                    else "no public feedback returned (physical state unknown)",
                    "site_working_count": working_from_page_api,
                    "working_count_consistent": working_from_detail
                    == working_from_page_api,
                }
            )
            for ordinal, item in enumerate(feedback, start=1):
                feedback_rows.append(
                    {
                        "shuttle": "tt06",
                        "macro": macro,
                        "feedback_ordinal_in_response": ordinal,
                        "status": item["status"],
                        "user": item.get("user", ""),
                        "owner_flag": item.get("owner", ""),
                        "feedback_text_present": bool(item.get("feedback")),
                        "link": item.get("link") or "",
                        "report_timestamp": "not exposed in API schema",
                        "chip_die_or_board_id": "not exposed in API schema",
                        "test_conditions": "not exposed in API schema",
                        "measured_values": "not exposed in API schema",
                    }
                )
        except Exception as exc:
            errors.append({"macro": macro, "error": str(exc)})
    if errors or len(rows) != expected:
        (root / "extraction-errors.json").write_text(
            json.dumps(errors, indent=2) + "\n"
        )
        raise SystemExit(
            f"Extraction incomplete ({len(rows)}/{expected}); see extraction-errors.json"
        )

    rows.sort(key=lambda row: (row["address"], row["macro"]))
    csv_path = root / "project-feedback.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    feedback_csv_path = root / "feedback-records.csv"
    feedback_fields = [
        "shuttle",
        "macro",
        "feedback_ordinal_in_response",
        "status",
        "user",
        "owner_flag",
        "feedback_text_present",
        "link",
        "report_timestamp",
        "chip_die_or_board_id",
        "test_conditions",
        "measured_values",
    ]
    with feedback_csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=feedback_fields)
        writer.writeheader()
        writer.writerows(
            sorted(
                feedback_rows,
                key=lambda row: (row["macro"], row["feedback_ordinal_in_response"]),
            )
        )

    summary = {
        "shuttle": "tt06",
        "population_macro_rows": len(rows),
        "macro_ids_unique": len({row["macro"] for row in rows}),
        "macros_with_any_public_feedback": sum(
            row["feedback_records"] > 0 for row in rows
        ),
        "macros_without_public_feedback": sum(
            row["feedback_records"] == 0 for row in rows
        ),
        "macro_feedback_presence_fraction": sum(
            row["feedback_records"] > 0 for row in rows
        )
        / len(rows),
        "macro_feedback_presence_percent": 100
        * sum(row["feedback_records"] > 0 for row in rows)
        / len(rows),
        "community_feedback_records": sum(row["feedback_records"] for row in rows),
        "feedback_records_by_status": {
            status: sum(row[f"{status}_records"] for row in rows) for status in STATUSES
        },
        "macros_by_any_feedback_status": {
            status: sum(row[f"{status}_records"] > 0 for row in rows)
            for status in STATUSES
        },
        "site_api_working_count_matches_detail_api_for_all_macros": all(
            row["working_count_consistent"] for row in rows
        ),
        "feedback_record_rows": len(feedback_rows),
        "feedback_records_with_nonempty_link": sum(
            bool(row["link"]) for row in feedback_rows
        ),
        "unique_nonempty_link_urls": len(
            {row["link"] for row in feedback_rows if row["link"]}
        ),
        "feedback_record_rows_sha256": hashlib.sha256(
            feedback_csv_path.read_bytes()
        ).hexdigest(),
        "unknowns": [
            "No public feedback returned does not establish whether a macro was tested or how it functioned.",
            "The API has no structured report timestamp, chip/die/board identity, test-condition, or measured-value fields; free text and optional links may contain such details but were not normalized or followed.",
            "Working/partial/broken are community-entered labels, not independent silicon-validation outcomes.",
        ],
    }
    summary["project_feedback_csv_sha256"] = hashlib.sha256(
        csv_path.read_bytes()
    ).hexdigest()
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    print(f"Generated: {csv_path}")
    print(f"Generated: {root / 'summary.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
