#!/usr/bin/env python3
"""Extract stage wall times and subprocess telemetry from the retained run records.

The tracked subset and ZIP index are the durable input. When the upstream ZIP is
also present, its digest, member index, and subset bytes are checked against it.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import tarfile
import zipfile
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ARCHIVE_NAME = "raw/librelane-spm-ihp-sg13g2-run-37749124131-artifact-11539925672.zip"
ARCHIVE = ROOT / ARCHIVE_NAME
INDEX = ROOT / "raw/artifact-index.tsv"
SUBSET = ROOT / "raw/run-records-subset.tar.gz"
DURATION_RE = re.compile(r"^(\d+):(\d+):(\d+(?:\.\d+)?)$")
MEMORY_RE = re.compile(r"^([0-9.]+)(B|KiB|MiB|GiB|TiB)$")
STEP_RE = re.compile(r"^([0-9]{2})-(.+)$")


def seconds(value: str) -> float:
    match = DURATION_RE.fullmatch(value.strip())
    if not match:
        raise ValueError(f"Unsupported duration: {value!r}")
    hours, minutes, secs = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(secs)


def mib(value: str | None) -> float | None:
    if value is None:
        return None
    match = MEMORY_RE.fullmatch(value.strip())
    if not match:
        raise ValueError(f"Unsupported memory quantity: {value!r}")
    amount, unit = match.groups()
    factor = {
        "B": 1 / 2**20,
        "KiB": 1 / 2**10,
        "MiB": 1,
        "GiB": 2**10,
        "TiB": 2**20,
    }[unit]
    return float(amount) * factor


def load_index() -> dict[str, tuple[int, int, str]]:
    lines = INDEX.read_text(encoding="utf-8").splitlines()[1:]
    rows = [line.split("\t") for line in lines]
    index = {row[0]: (int(row[1]), int(row[2]), row[3]) for row in rows}
    assert len(index) == len(rows), "Duplicate ZIP paths"
    return index


def load_subset(index: dict[str, tuple[int, int, str]]) -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    with tarfile.open(SUBSET, "r:gz") as tar:
        for info in tar.getmembers():
            payload = tar.extractfile(info).read()
            size, _, crc = index[info.name]
            if len(payload) != size or f"{zlib.crc32(payload):08x}" != crc:
                raise ValueError(f"Retained record differs from index: {info.name}")
            members[info.name] = payload
    return members


def check_against_archive(
    index: dict[str, tuple[int, int, str]], members: dict[str, bytes]
) -> None:
    metadata = json.loads((ROOT / "raw/artifact-metadata.json").read_text())
    assert (
        metadata["digest"]
        == "sha256:" + hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    )
    with zipfile.ZipFile(ARCHIVE) as archive:
        listed = {
            m.filename: (m.file_size, m.compress_size, f"{m.CRC:08x}")
            for m in archive.infolist()
        }
        assert listed == index, "ZIP listing differs from retained index"
        for name, payload in members.items():
            assert archive.read(name) == payload, name


def main() -> None:
    manifest = json.loads((ROOT / "source_manifest.json").read_text())
    for receipt in manifest["files"]:
        if receipt["path"] == ARCHIVE_NAME and not ARCHIVE.exists():
            continue
        if (
            hashlib.sha256((ROOT / receipt["path"]).read_bytes()).hexdigest()
            != receipt["sha256"]
        ):
            raise ValueError(f"Source hash mismatch: {receipt['path']}")
    index = load_index()
    members = load_subset(index)
    if ARCHIVE.exists():
        check_against_archive(index, members)
    else:
        print(
            "Upstream ZIP absent: using the retained subset; ZIP digest and "
            "byte comparison skipped.",
            file=sys.stderr,
        )
    step_rows: dict[str, dict[str, object]] = {}
    process_rows: list[dict[str, object]] = []
    names = set(index)
    numbered_dirs = {
        n.split("/")[0] for n in names if STEP_RE.fullmatch(n.split("/")[0])
    }
    runtime_paths = sorted(
        name for name in names if re.fullmatch(r"[0-9]{2}-[^/]+/runtime\.txt", name)
    )
    runtimes = sorted(
        name for name in names if re.fullmatch(r"[0-9]{2}-.+/runtime\.txt", name)
    )
    assert len(numbered_dirs) == len(runtime_paths) == 78
    assert len(runtimes) == 80
    for name in runtime_paths:
        step_dir = name.split("/", 1)[0]
        match = STEP_RE.fullmatch(step_dir)
        if not match:
            continue
        step_id, step_name = match.groups()
        row: dict[str, object] = {
            "step_id": int(step_id),
            "step_name": step_name,
            "runtime_seconds": seconds(members[name].decode("utf-8")),
            "state_out_present": f"{step_dir}/state_out.json" in names,
            "process_stats_count": 0,
            "peak_rss_mib_max": None,
            "peak_vms_mib_max": None,
            "peak_cpu_percent_max": None,
            "process_stats_files": "",
        }
        step_rows[step_dir] = row

    for name in sorted(names):
        if not re.fullmatch(r"[0-9]{2}-.+/[^/]+\.process_stats\.json", name):
            continue
        step_dir, filename = name.split("/", 1)
        data = json.loads(members[name])
        timing = data.get("time", {})
        peak = data.get("peak_resources", {})
        average = data.get("avg_resources", {})
        proc = {
            "step_id": int(STEP_RE.fullmatch(step_dir).group(1)),
            "step_name": STEP_RE.fullmatch(step_dir).group(2),
            "process_stats_file": filename,
            "process_wall_seconds": seconds(timing["runtime"]),
            "cpu_user_seconds": seconds(timing["cpu_time_user"]),
            "cpu_system_seconds": seconds(timing["cpu_time_system"]),
            "cpu_iowait_seconds": seconds(timing["cpu_time_iowait"]),
            "peak_rss_mib": mib(peak.get("memory_rss")),
            "peak_vms_mib": mib(peak.get("memory_vms")),
            "peak_cpu_percent": peak.get("cpu_percent"),
            "peak_threads": peak.get("threads"),
            "avg_rss_mib": mib(average.get("memory_rss")),
            "avg_vms_mib": mib(average.get("memory_vms")),
            "avg_cpu_percent": average.get("cpu_percent"),
            "avg_threads": average.get("threads"),
        }
        process_rows.append(proc)
        row = step_rows.get(step_dir)
        if row is not None:
            row["process_stats_count"] = int(row["process_stats_count"]) + 1
            row["process_stats_files"] = ",".join(
                filter(None, [str(row["process_stats_files"]), filename])
            )
            for col, val in (
                ("peak_rss_mib_max", proc["peak_rss_mib"]),
                ("peak_vms_mib_max", proc["peak_vms_mib"]),
                ("peak_cpu_percent_max", proc["peak_cpu_percent"]),
            ):
                if val is not None:
                    row[col] = (
                        val
                        if row[col] is None
                        else max(float(row[col]), float(val))
                    )

    assert set(step_rows) == numbered_dirs
    assert all(row["state_out_present"] for row in step_rows.values())
    assert sorted(row["step_id"] for row in step_rows.values()) == list(range(1, 79))
    assert len(process_rows) == 55
    assert sum(row["process_stats_count"] > 0 for row in step_rows.values()) == 45
    step_fields = [
        "step_id",
        "step_name",
        "runtime_seconds",
        "state_out_present",
        "process_stats_count",
        "peak_rss_mib_max",
        "peak_vms_mib_max",
        "peak_cpu_percent_max",
        "process_stats_files",
    ]
    with (ROOT / "stage-costs.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=step_fields)
        writer.writeheader()
        writer.writerows(
            sorted(step_rows.values(), key=lambda row: int(row["step_id"]))
        )

    process_fields = list(process_rows[0]) if process_rows else []
    with (ROOT / "process-costs.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=process_fields)
        writer.writeheader()
        writer.writerows(
            sorted(
                process_rows,
                key=lambda row: (int(row["step_id"]), str(row["process_stats_file"])),
            )
        )

    ordered = sorted(step_rows.values(), key=lambda row: int(row["step_id"]))
    summary = {
        "population": "all numbered steps in the single retained spm IHP-SG13G2 run artifact",
        "numbered_steps": len(ordered),
        "direct_step_runtime_records": len(runtime_paths),
        "nested_substep_runtime_records_excluded_from_step_sum": len(runtimes)
        - len(runtime_paths),
        "steps_with_state_out": sum(bool(row["state_out_present"]) for row in ordered),
        "steps_with_runtime_record": sum(
            row["runtime_seconds"] is not None for row in ordered
        ),
        "steps_with_one_or_more_process_stats": sum(
            int(row["process_stats_count"]) > 0 for row in ordered
        ),
        "process_stats_records": len(process_rows),
        "steps_without_process_stats_memory": [
            row["step_id"] for row in ordered if int(row["process_stats_count"]) == 0
        ],
        "sum_of_sequential_step_wall_runtime_seconds": round(
            sum(float(row["runtime_seconds"]) for row in ordered), 3
        ),
        "longest_steps_by_wall_runtime": sorted(
            [
                {
                    "step_id": row["step_id"],
                    "step_name": row["step_name"],
                    "runtime_seconds": row["runtime_seconds"],
                }
                for row in ordered
            ],
            key=lambda row: float(row["runtime_seconds"]),
            reverse=True,
        )[:10],
        "interpretation": "runtime.txt measures the whole LibreLane step wall interval; process_stats.json is subprocess telemetry. These are separate measures and must not be added together. Missing process_stats means subprocess memory was not recorded for that step, not zero memory or a failed step.",
    }
    (ROOT / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {ROOT / 'stage-costs.csv'} ({len(step_rows)} steps)")
    print(
        f"Wrote {ROOT / 'process-costs.csv'} ({len(process_rows)} subprocess records)"
    )
    print(f"Wrote {ROOT / 'summary.json'}")


if __name__ == "__main__":
    main()
