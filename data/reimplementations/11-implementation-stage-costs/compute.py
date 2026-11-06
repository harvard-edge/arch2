#!/usr/bin/env python3
"""Spec 11: implementation stage costs, computed from raw inputs only.

Run from this folder: python3 compute.py
Writes result.json. Durations are held as integer milliseconds so sums are exact.
"""
import gzip
import hashlib
import io
import json
import platform
import re
import sys
import tarfile
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "inputs/data/studies/20-implementation-stage-costs/raw"
SUBSET = RAW / "run-records-subset.tar.gz"
JOB = RAW / "design-job.json"
LOG = RAW / "job-113223652131.log.gz"
INDEX = RAW / "artifact-index.tsv"

OUTER_DIR = re.compile(r"^(\d+)-(.+)$")
RUNTIME = re.compile(r"^(\d{2}):(\d{2}):(\d{2})\.(\d{3})$")
LOG_LINE = re.compile(r"^﻿?(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.(\d{7})Z(?: (.*))?$")
RECORD_START = re.compile(r"^\[\d{2}:\d{2}:\d{2}\] \[([A-Z])\] (.*)$")
RUNNING = re.compile(r"^Running '[^']+' at")
SKIP_WORD = re.compile(r"\b(skipping|skipped)\b", re.IGNORECASE)
PREFIXED_SUMMARY = re.compile(r"^\[[A-Za-z]+\.[A-Za-z]+\]")

DETAILED_ROUTING_SLUG = "openroad-detailedrouting"
RUN_TEST = "Run Test"
PROSE_RANK_2_TO_5 = ["magic-writelef", "magic-streamout", "klayout-drc", "magic-drc"]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_runtime(text, member):
    match = RUNTIME.match(text)
    if match is None:
        raise SystemExit(f"STOP: {member} is not HH:MM:SS.mmm: {text!r}")
    h, m, s, ms = (int(g) for g in match.groups())
    return (h * 3600 + m * 60 + s) * 1000 + ms


def api_time(stamp):
    return datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def api_seconds(start, end):
    delta = (api_time(end) - api_time(start)).total_seconds()
    if delta != int(delta):
        raise SystemExit(f"STOP: API delta not whole seconds: {start} {end}")
    return int(delta)


def load_index():
    rows = {}
    lines = INDEX.read_text().splitlines()
    if lines[0].split("\t") != ["path", "file_size", "compress_size", "crc32"]:
        raise SystemExit(f"STOP: unexpected index header {lines[0]!r}")
    for line in lines[1:]:
        path, size, _, crc = line.split("\t")
        rows[path] = (int(size), crc.lower())
    return rows


def load_subset():
    members = {}
    with tarfile.open(SUBSET, "r:gz") as tar:
        for member in tar.getmembers():
            if member.isfile():
                members[member.name] = tar.extractfile(member).read()
    return members


def classify_runtime_paths(paths):
    """Sort runtime.txt paths into outer, nested, and unclassified."""
    outer, nested, other = [], [], []
    for path in sorted(paths):
        parts = path.split("/")
        if parts[-1] != "runtime.txt":
            continue
        if len(parts) == 2 and OUTER_DIR.match(parts[0]):
            outer.append(path)
        elif len(parts) == 3 and OUTER_DIR.match(parts[0]):
            nested.append(path)
        else:
            other.append(path)
    return outer, nested, other


def parse_log():
    """Return log lines as (epoch seconds as a fraction-free int pair, text)."""
    with gzip.open(LOG, "rt", encoding="utf-8", newline="\n") as handle:
        raw = handle.read().split("\n")
    parsed, unparsed = [], 0
    for line in raw:
        if line == "":
            continue
        match = LOG_LINE.match(line.rstrip("\r"))
        if match is None:
            unparsed += 1
            continue
        whole = int(api_time(match.group(1) + "Z").timestamp())
        ticks = whole * 10_000_000 + int(match.group(2))
        parsed.append((ticks, match.group(3) or ""))
    return parsed, unparsed


def find_run_test_span(lines):
    """Locate Run Test by the group that invokes librelane.

    The log carries no step names, only `##[group]Run <first line of script>`.
    Returns indices of the first line of Run Test and of the next step.
    """
    starts = [i for i, (_, text) in enumerate(lines) if text.startswith("##[group]Run ")]
    hits = []
    for pos, start in enumerate(starts):
        end = starts[pos + 1] if pos + 1 < len(starts) else len(lines)
        block = "\n".join(text for _, text in lines[start:end])
        if "python3 -m librelane" in block and "--run-tag" in block:
            hits.append((start, end))
    if len(hits) != 1:
        raise SystemExit(f"STOP: expected one Run Test block in the log, found {len(hits)}")
    return hits[0]


def flow_records(lines):
    """Join wrapped flow-log lines into (level, text) records."""
    records = []
    for _, text in lines:
        start = RECORD_START.match(text)
        if start:
            records.append([start.group(1), start.group(2).rstrip()])
        elif records and text.startswith(" "):
            records[-1][1] += "\n" + text.strip()
        # Lines that fit neither shape (group headers, env dump) carry no flow record.
    return records


def log_declared_skips(lines, run_dir_tag, outer_dirs):
    """Outer steps whose own body logged that it skipped its work."""
    current, skipped, seen, unmatched = None, {}, set(), 0
    for level, text in flow_records(lines):
        flat = re.sub(r"\s+", "", text)
        if RUNNING.match(text):
            match = re.search(re.escape(run_dir_tag) + r"/(\d+-[^/']+)", flat)
            if match is None or match.group(1) not in outer_dirs:
                unmatched += 1
                current = None
                continue
            current = match.group(1)
            seen.add(current)
            continue
        one_line = " ".join(text.split())
        if current is None or level not in ("I", "W") or not SKIP_WORD.search(one_line):
            continue
        if "sequential.py" in one_line:  # gating of a different step, which has no directory
            continue
        if "for layer" in one_line:  # tool warning about one layer, not about the step
            continue
        if PREFIXED_SUMMARY.match(one_line):  # end-of-flow digest of earlier warnings
            continue
        skipped.setdefault(current, []).append(one_line)
    return skipped, seen, unmatched


def main():
    started = time.perf_counter()
    index = load_index()
    subset = load_subset()

    # Confirm the subset against the index before using any byte of it.
    crc_bad, size_bad, not_in_index = [], [], []
    for path, data in subset.items():
        if path not in index:
            not_in_index.append(path)
            continue
        size, crc = index[path]
        if len(data) != size:
            size_bad.append(path)
        if f"{zlib.crc32(data):08x}" != crc:
            crc_bad.append(path)
    if crc_bad or size_bad or not_in_index:
        raise SystemExit(f"STOP: subset vs index: {crc_bad} {size_bad} {not_in_index}")

    outer_paths, nested_paths, other_paths = classify_runtime_paths(subset)
    ix_outer, ix_nested, ix_other = classify_runtime_paths(index)
    if (outer_paths, nested_paths) != (ix_outer, ix_nested) or other_paths or ix_other:
        raise SystemExit("STOP: runtime.txt sets differ between subset and index")
    top_level_names = sorted({p.split("/")[0] for p in index})
    numbered = [n for n in top_level_names if OUTER_DIR.match(n)]
    outer_dirs = [p.split("/")[0] for p in outer_paths]
    numbered_without_runtime = sorted(set(numbered) - set(outer_dirs))
    not_steps = [n for n in top_level_names if not OUTER_DIR.match(n)]

    steps = []
    for path in outer_paths:
        directory = path.split("/")[0]
        number, slug = OUTER_DIR.match(directory).groups()
        steps.append({
            "step_dir": directory,
            "nn": int(number),
            "slug": slug,
            "ms": parse_runtime(subset[path].decode("ascii"), path),
        })
    if len({s["nn"] for s in steps}) != len(steps):
        raise SystemExit("STOP: duplicate NN among outer steps")
    nested_ms = {p: parse_runtime(subset[p].decode("ascii"), p) for p in nested_paths}

    job = json.loads(JOB.read_text())
    run_test_rows = [s for s in job["steps"] if s["name"] == RUN_TEST]
    if len(run_test_rows) != 1:
        raise SystemExit(f"STOP: {len(run_test_rows)} steps named {RUN_TEST}")
    run_test = run_test_rows[0]
    position = job["steps"].index(run_test)
    next_step = job["steps"][position + 1]
    job_s = api_seconds(job["started_at"], job["completed_at"])
    run_test_api = api_seconds(run_test["started_at"], run_test["completed_at"])
    run_test_api_next = api_seconds(run_test["started_at"], next_step["started_at"])
    outside = [s["name"] for s in job["steps"] if s["name"] != RUN_TEST]
    outside_ran = [s["name"] for s in job["steps"]
                   if s["name"] != RUN_TEST and s["conclusion"] != "skipped"]
    outside_durations = {s["name"]: api_seconds(s["started_at"], s["completed_at"])
                         for s in job["steps"] if s["name"] != RUN_TEST}

    lines, unparsed = parse_log()
    first, after = find_run_test_span(lines)
    run_test_log_s = (lines[after][0] - lines[first][0]) / 10_000_000
    last_line_s = (lines[after - 1][0] - lines[first][0]) / 10_000_000
    log_start_second = datetime.fromtimestamp(lines[first][0] // 10_000_000, timezone.utc)
    log_next_second = datetime.fromtimestamp(lines[after][0] // 10_000_000, timezone.utc)

    run_dir_tag = None
    for _, text in lines[first:after]:
        if text.strip().startswith("--run-tag") or "--run-tag " in text:
            run_dir_tag = re.sub(r"\x1b\[[0-9;]*m", "", text).split("--run-tag")[1].split()[0].rstrip("\\")
            break
    if run_dir_tag is None:
        raise SystemExit("STOP: no --run-tag in Run Test block")
    skipped_log, log_seen, log_unmatched = log_declared_skips(
        lines[first:after], run_dir_tag, set(outer_dirs))

    step_sets = {
        "all_outer": ("Spec definition: every outer runtime.txt.", lambda s: True),
        "excl_zero_ms": ("Drop outer steps recorded as 00:00:00.000.", lambda s: s["ms"] > 0),
        "excl_log_skip": ("Drop outer steps whose own flow-log block says the step skipped its work.",
                          lambda s: s["step_dir"] not in skipped_log),
    }
    boundaries = {
        "api_completed_at": ("Spec definition: Run Test ends at its API completed_at.", run_test_api),
        "api_next_step_started": ("Run Test ends at the next step's API started_at.", run_test_api_next),
        "log_subsecond": ("Run Test ends at the first log line of the next step; "
                          "nested_ok uses run_test_log_s.", run_test_log_s),
    }

    ranked_all = sorted(steps, key=lambda s: (-s["ms"], s["nn"]))
    rank_slugs = [s["slug"] for s in ranked_all]
    order_listed = rank_slugs[1:5] == PROSE_RANK_2_TO_5
    order_grouped = (set(rank_slugs[1:3]) == set(PROSE_RANK_2_TO_5[:2])
                     and set(rank_slugs[3:5]) == set(PROSE_RANK_2_TO_5[2:]))

    routing = [s for s in steps if s["slug"] == DETAILED_ROUTING_SLUG]
    if len(routing) != 1:
        raise SystemExit(f"STOP: {len(routing)} steps with slug {DETAILED_ROUTING_SLUG}")

    readings = []
    for set_name, (set_text, keep) in step_sets.items():
        kept = [s for s in steps if keep(s)]
        ranked = sorted(kept, key=lambda s: (-s["ms"], s["nn"]))
        total_ms = sum(s["ms"] for s in kept)
        remainder_ms = sum(s["ms"] for s in ranked[6:])
        for bound_name, (bound_text, run_test_end) in boundaries.items():
            readings.append({
                "reading": f"{set_name}__{bound_name}",
                "is_spec_definition": set_name == "all_outer" and bound_name == "api_completed_at",
                "description": f"{set_text} {bound_text}",
                "n_outer_steps": len(kept),
                "n_nested_excluded": len(nested_paths),
                "sum_steps_s": total_ms / 1000,
                "detailed_routing_s": routing[0]["ms"] / 1000,
                "top_steps": [{"step_dir": s["step_dir"], "seconds": s["ms"] / 1000}
                              for s in ranked[:6]],
                "remainder_s": remainder_ms / 1000,
                "run_test_s": run_test_api if bound_name == "api_completed_at" else
                              run_test_api_next if bound_name == "api_next_step_started" else
                              run_test_api,
                "job_s": job_s,
                "run_test_log_s": run_test_log_s,
                "job_over_steps": job_s * 1000 / total_ms,
                "nested_ok": total_ms / 1000 <= run_test_end <= job_s,
                "job_steps_outside_run_test": outside,
            })

    result = {
        "readings": readings,
        "checks": {
            "subset_members_checked_against_index": len(subset),
            "subset_crc_or_size_mismatches": 0,
            "index_runtime_outer": len(ix_outer),
            "index_runtime_nested": len(ix_nested),
            "numbered_top_level_without_runtime": numbered_without_runtime,
            "top_level_entries_not_steps": not_steps,
            "nested_runtime_ms_by_path": nested_ms,
            "prose_order_rank_2_to_5_listed": order_listed,
            "prose_order_rank_2_to_5_grouped": order_grouped,
            "rank_1_is_detailed_routing": rank_slugs[0] == DETAILED_ROUTING_SLUG,
            "rank_2_to_5_slugs": rank_slugs[1:5],
            "run_test_log_minus_api_s": run_test_log_s - run_test_api,
            "run_test_log_within_0p2s": abs(run_test_log_s - run_test_api) <= 0.2,
            "run_test_log_last_line_s": last_line_s,
            "log_start_second_matches_api": log_start_second.strftime("%Y-%m-%dT%H:%M:%SZ") == run_test["started_at"],
            "log_next_step_second_matches_api": log_next_second.strftime("%Y-%m-%dT%H:%M:%SZ") == next_step["started_at"],
            "next_step_after_run_test": next_step["name"],
            "log_lines_without_timestamp": unparsed,
            "log_outer_steps_seen_running": len(log_seen),
            "log_running_records_unattributed": log_unmatched,
            "outer_steps_never_seen_running_in_log": sorted(set(outer_dirs) - log_seen),
            "zero_ms_steps": [s["step_dir"] for s in steps if s["ms"] == 0],
            "log_skip_steps": skipped_log,
            "job_steps_outside_run_test_not_skipped": outside_ran,
            "outside_step_api_seconds": outside_durations,
            "outside_step_api_seconds_sum": sum(outside_durations.values()),
            "first_step_start_to_last_step_end_s": api_seconds(
                job["steps"][0]["started_at"], job["steps"][-1]["completed_at"]),
        },
        "manifest": {
            "command": "python3 compute.py",
            "python": platform.python_version(),
            "platform": sys.platform,
            "compute_py_sha256": sha256(Path(__file__).resolve()),
            "inputs_sha256": {p.name: sha256(p) for p in (SUBSET, JOB, LOG, INDEX)},
            "elapsed_s": round(time.perf_counter() - started, 3),
        },
    }
    (HERE / "result.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
