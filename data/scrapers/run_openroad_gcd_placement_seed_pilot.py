#!/usr/bin/env python3
"""Execute a pinned, single-threaded OpenROAD placement-seed pilot.

The retained candidate deliberately stops after detailed placement. The
official ORFS container is linux/amd64-only and reaches placement under Docker
Desktop's ARM emulation on the measurement host, but the full-flow smoke test
fails with an illegal instruction during clock-tree synthesis. This runner
therefore measures only the stage that consumes ``GPL_RANDOM_SEED`` and does
not claim post-route or signoff results.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ORFS = Path(__file__).resolve().parent / ".cache" / "openroad-flow-scripts"
STUDY_DIR = REPO_ROOT / "data" / "studies" / "06-eda-seed-dispersion"
RAW_DIR = STUDY_DIR / "raw-openroad-placement-pilot"
CSV_PATH = STUDY_DIR / "openroad_gcd_placement_seed_pilot.csv"
SUMMARY_PATH = STUDY_DIR / "openroad_gcd_placement_seed_pilot_summary.json"
SMOKE_STDOUT_RECEIPT = RAW_DIR / "openroad_gcd_full_flow_smoke_seed_01.stdout.txt"
SMOKE_METADATA_RECEIPT = RAW_DIR / "openroad_gcd_full_flow_smoke_seed_01.metadata.json"

ORFS_URL = "https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts"
ORFS_COMMIT = "8359fde81991e6118b15b8a93fcde606b577794d"
IMAGE = (
    "openroad/orfs@sha256:"
    "6b279bd4f039c2224e03a94795511a43d69fc9665f4fe33381172cf49d0ce627"
)
IMAGE_DIGEST = "sha256:6b279bd4f039c2224e03a94795511a43d69fc9665f4fe33381172cf49d0ce627"
DESIGN_CONFIG = "./designs/nangate45/gcd/config.mk"
FLOW_TARGET = "place"
CSV_FIELDS = [
    "seed",
    "status",
    "variant",
    "flow_target",
    "gpl_random_seed",
    "grt_seed_fixed",
    "or_seed_fixed",
    "num_cores",
    "docker_returncode",
    "wall_time_seconds",
    "globalplace_instance_area_um2",
    "globalplace_setup_wns_ns",
    "globalplace_setup_tns_ns",
    "globalplace_hold_wns_ns",
    "detailedplace_instance_area_um2",
    "detailedplace_setup_wns_ns",
    "detailedplace_setup_tns_ns",
    "detailedplace_hold_wns_ns",
    "globalplace_flow_errors",
    "detailedplace_flow_errors",
    "globalplace_json_sha256",
    "detailedplace_json_sha256",
    "floorplan_odb_sha256",
    "placement_odb_sha256",
    "stdout_receipt",
    "extraction_timestamp",
]


def run(
    command: list[str],
    *,
    cwd: Path,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def metric(record: dict[str, Any], key: str) -> float | int | None:
    value = record.get(key)
    return value if isinstance(value, (int, float)) else None


def describe(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "n": 0,
            "min": None,
            "q1": None,
            "median": None,
            "q3": None,
            "max": None,
            "range": None,
            "range_pct_of_median": None,
        }
    ordered = sorted(values)
    quartiles = (
        statistics.quantiles(ordered, n=4, method="inclusive")
        if len(ordered) > 1
        else [ordered[0], ordered[0], ordered[0]]
    )
    median = statistics.median(ordered)
    value_range = ordered[-1] - ordered[0]
    return {
        "n": len(ordered),
        "min": ordered[0],
        "q1": quartiles[0],
        "median": median,
        "q3": quartiles[2],
        "max": ordered[-1],
        "range": value_range,
        "range_pct_of_median": 100.0 * value_range / abs(median) if median else None,
    }


def git_commit(checkout: Path) -> str:
    result = run(["git", "rev-parse", "HEAD"], cwd=checkout)
    if result.returncode != 0:
        raise SystemExit(f"Cannot read ORFS commit from {checkout}: {result.stdout}")
    return result.stdout.strip()


def require_clean_tracked_checkout(checkout: Path) -> None:
    result = run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=checkout)
    if result.returncode != 0 or result.stdout.strip():
        raise SystemExit(
            "ORFS checkout has tracked modifications; use a clean checkout for "
            f"the pinned measurement: {checkout}"
        )


def docker_metadata() -> dict[str, str]:
    version = run(
        ["docker", "version", "--format", "{{.Client.Version}}|{{.Server.Version}}"],
        cwd=REPO_ROOT,
    )
    inspect = run(
        [
            "docker",
            "image",
            "inspect",
            IMAGE,
            "--format",
            "{{.Id}}|{{.Architecture}}|{{.Os}}",
        ],
        cwd=REPO_ROOT,
    )
    if version.returncode or inspect.returncode:
        raise SystemExit("Pinned Docker image or running Docker daemon is unavailable")
    client, server = version.stdout.strip().split("|", maxsplit=1)
    image_id, architecture, operating_system = inspect.stdout.strip().split(
        "|", maxsplit=2
    )
    if image_id != IMAGE_DIGEST:
        raise SystemExit(f"Pinned image ID mismatch: {image_id}")
    return {
        "client_version": client,
        "server_version": server,
        "image": IMAGE,
        "image_id": image_id,
        "image_architecture": architecture,
        "image_operating_system": operating_system,
    }


def write_csv(rows: list[dict[str, Any]]) -> None:
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def refresh_retained_artifacts(rows: list[dict[str, Any]], flow: Path) -> None:
    """Copy retained stage metrics byte-for-byte and refresh artifact hashes."""

    for row in rows:
        seed = int(row["seed"])
        variant = str(row["variant"])
        log_dir = flow / "logs" / "nangate45" / "gcd" / variant
        results_dir = flow / "results" / "nangate45" / "gcd" / variant
        gp_path = log_dir / "3_3_place_gp.json"
        dp_path = log_dir / "3_5_place_dp.json"
        gp_raw = RAW_DIR / f"openroad_gcd_placement_seed_{seed:02d}.globalplace.json"
        dp_raw = RAW_DIR / f"openroad_gcd_placement_seed_{seed:02d}.detailedplace.json"
        floorplan_path = results_dir / "2_floorplan.odb"
        placement_path = results_dir / "3_place.odb"

        if gp_path.exists():
            shutil.copyfile(gp_path, gp_raw)
            row["globalplace_json_sha256"] = sha256_file(gp_raw)
        if dp_path.exists():
            shutil.copyfile(dp_path, dp_raw)
            row["detailedplace_json_sha256"] = sha256_file(dp_raw)
        row["floorplan_odb_sha256"] = (
            sha256_file(floorplan_path) if floorplan_path.exists() else ""
        )
        row["placement_odb_sha256"] = (
            sha256_file(placement_path) if placement_path.exists() else ""
        )


def write_summary(
    rows: list[dict[str, Any]],
    *,
    orfs: Path,
    docker: dict[str, str],
    start_timestamp: str,
) -> None:
    successful = [row for row in rows if row["status"] == "pass"]
    floorplan_hashes = {
        str(row["floorplan_odb_sha256"])
        for row in successful
        if row.get("floorplan_odb_sha256")
    }
    if successful and len(floorplan_hashes) != 1:
        raise SystemExit(
            "One-factor attribution requires one identical floorplan input ODB "
            f"hash across successful runs; found {len(floorplan_hashes)}"
        )
    recorded_seeds = sorted(int(row["seed"]) for row in rows)
    metric_columns = {
        "globalplace_instance_area_um2": "globalplace__design__instance__area",
        "globalplace_setup_wns_ns": "globalplace__timing__setup__ws",
        "globalplace_setup_tns_ns": "globalplace__timing__setup__tns",
        "detailedplace_instance_area_um2": "detailedplace__design__instance__area",
        "detailedplace_setup_wns_ns": "detailedplace__timing__setup__ws",
        "detailedplace_setup_tns_ns": "detailedplace__timing__setup__tns",
    }
    distributions = {
        column: describe([float(row[column]) for row in successful])
        for column in metric_columns
    }
    design_source = orfs / "flow" / "designs" / "src" / "gcd" / "gcd.v"
    constraint = orfs / "flow" / "designs" / "nangate45" / "gcd" / "constraint.sdc"
    smoke = (
        read_json(SMOKE_METADATA_RECEIPT)
        if SMOKE_METADATA_RECEIPT.exists()
        else {
            "status": "not retained",
            "consequence": "No post-CTS, routing, GDS, or signoff claim is made",
        }
    )
    summary = {
        "study_status": "executed bounded placement-stage pilot",
        "claim_boundary": (
            f"One ORFS GCD/Nangate45 design, {len(recorded_seeds)} declared global-placement "
            "seeds, one pinned single-threaded linux/amd64 container under "
            "Docker Desktop ARM emulation; placement-stage metrics only"
        ),
        "full_flow_smoke_test": smoke,
        "source": {
            "repository": ORFS_URL,
            "commit": ORFS_COMMIT,
            "design": "gcd",
            "platform": "nangate45",
            "design_config": DESIGN_CONFIG,
            "design_source_sha256": sha256_file(design_source),
            "constraint_sha256": sha256_file(constraint),
        },
        "execution": {
            "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "flow_target": FLOW_TARGET,
            "seeds": recorded_seeds,
            "gpl_random_seed": "varied over the recorded seed list",
            "grt_seed": 1,
            "or_seed": 1,
            "num_cores": 1,
            "host_operating_system": platform.system(),
            "host_kernel_release": platform.release(),
            "host_kernel_version": platform.version(),
            "host_architecture": os.uname().machine,
            "docker": docker,
            "start_timestamp": start_timestamp,
            "end_timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "runs": {
            "attempted": len(rows),
            "successful": len(successful),
            "failed": len(rows) - len(successful),
        },
        "one_factor_input_check": {
            "unique_floorplan_input_hashes": len(floorplan_hashes),
            "floorplan_input_odb_sha256": (
                next(iter(floorplan_hashes)) if floorplan_hashes else None
            ),
        },
        "metric_keys": metric_columns,
        "distributions": distributions,
    }
    SUMMARY_PATH.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--orfs", type=Path, default=DEFAULT_ORFS)
    parser.add_argument("--start-seed", type=int, default=1)
    parser.add_argument("--end-seed", type=int, default=20)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="retain completed rows already present in the candidate CSV",
    )
    parser.add_argument(
        "--full-flow-smoke-only",
        action="store_true",
        help="run one pinned full-flow seed-1 smoke test and retain its expected failure",
    )
    return parser.parse_args()


def run_full_flow_smoke(
    *,
    orfs: Path,
    docker: dict[str, str],
    timeout_seconds: int,
) -> int:
    flow = orfs.resolve() / "flow"
    variant = "arch2-full-flow-smoke-seed-01"
    fixed_make_args = (
        f"DESIGN_CONFIG={DESIGN_CONFIG} "
        f"FLOW_VARIANT={variant} "
        "NUM_CORES=1 GPL_RANDOM_SEED=1 GRT_SEED=1 OR_SEED=1"
    )
    container_script = (
        "source /OpenROAD-flow-scripts/env.sh && "
        "cd /OpenROAD-flow-scripts/flow && "
        f"make {fixed_make_args} clean_all >/dev/null && "
        f"make {fixed_make_args} finish metadata-generate"
    )
    command = [
        "docker",
        "run",
        "--rm",
        "--platform",
        "linux/amd64",
        "-u",
        f"{os.getuid()}:{os.getgid()}",
        "-v",
        f"{flow}:/OpenROAD-flow-scripts/flow",
        IMAGE,
        "bash",
        "-lc",
        container_script,
    ]
    start_timestamp = datetime.now(timezone.utc).isoformat()
    start = time.monotonic()
    try:
        result = run(command, cwd=REPO_ROOT, timeout=timeout_seconds)
        returncode = result.returncode
        output = result.stdout
    except subprocess.TimeoutExpired as exc:
        returncode = 124
        output = (exc.stdout or "") + "\nrunner timeout"
    elapsed = time.monotonic() - start
    SMOKE_STDOUT_RECEIPT.write_text(output, encoding="utf-8")

    placement_odb = flow / "results" / "nangate45" / "gcd" / variant / "3_place.odb"
    failure = (
        "child killed: illegal instruction"
        if "child killed: illegal instruction" in output
        else "unexpected full-flow outcome"
    )
    metadata = {
        "status": "failed after successful placement" if returncode else "passed",
        "failure_stage": "clock-tree synthesis" if "cts.tcl" in output else None,
        "failure": failure if returncode else None,
        "docker_returncode": returncode,
        "wall_time_seconds": round(elapsed, 3),
        "placement_completed": placement_odb.exists(),
        "placement_odb_sha256": (
            sha256_file(placement_odb) if placement_odb.exists() else None
        ),
        "flow_target": "finish metadata-generate",
        "variant": variant,
        "gpl_random_seed": 1,
        "grt_seed": 1,
        "or_seed": 1,
        "num_cores": 1,
        "source": {
            "repository": ORFS_URL,
            "commit": ORFS_COMMIT,
            "design": "gcd",
            "platform": "nangate45",
            "design_config": DESIGN_CONFIG,
            "design_source_sha256": sha256_file(
                flow / "designs" / "src" / "gcd" / "gcd.v"
            ),
            "constraint_sha256": sha256_file(
                flow / "designs" / "nangate45" / "gcd" / "constraint.sdc"
            ),
        },
        "docker": docker,
        "host": {
            "operating_system": platform.system(),
            "kernel_release": platform.release(),
            "kernel_version": platform.version(),
            "architecture": platform.machine(),
        },
        "container_command": container_script,
        "stdout_receipt": SMOKE_STDOUT_RECEIPT.relative_to(REPO_ROOT).as_posix(),
        "stdout_sha256": sha256_file(SMOKE_STDOUT_RECEIPT),
        "start_timestamp": start_timestamp,
        "end_timestamp": datetime.now(timezone.utc).isoformat(),
        "consequence": (
            "No post-CTS, routing, GDS, or signoff claim is made from this pilot"
        ),
    }
    SMOKE_METADATA_RECEIPT.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    expected_failure = (
        returncode != 0
        and metadata["placement_completed"]
        and failure == "child killed: illegal instruction"
    )
    print(f"generated: {SMOKE_STDOUT_RECEIPT}")
    print(f"generated: {SMOKE_METADATA_RECEIPT}")
    return 0 if expected_failure else 1


def main() -> int:
    args = parse_args()
    if shutil.which("docker") is None:
        raise SystemExit("docker is required")
    if git_commit(args.orfs) != ORFS_COMMIT:
        raise SystemExit(f"ORFS checkout must be pinned to {ORFS_COMMIT}: {args.orfs}")
    require_clean_tracked_checkout(args.orfs)
    if args.start_seed < 1 or args.end_seed < args.start_seed:
        raise SystemExit("Require 1 <= start seed <= end seed")
    docker = docker_metadata()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if args.full_flow_smoke_only:
        return run_full_flow_smoke(
            orfs=args.orfs,
            docker=docker,
            timeout_seconds=args.timeout_seconds,
        )
    start_timestamp = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []
    if args.resume and CSV_PATH.exists():
        with CSV_PATH.open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if SUMMARY_PATH.exists():
            previous_summary = read_json(SUMMARY_PATH)
            start_timestamp = previous_summary.get("execution", {}).get(
                "start_timestamp", start_timestamp
            )

    flow = args.orfs.resolve() / "flow"
    for seed in range(args.start_seed, args.end_seed + 1):
        completed = next(
            (
                row
                for row in rows
                if int(row["seed"]) == seed and row["status"] == "pass"
            ),
            None,
        )
        if completed is not None:
            print(f"seed {seed:02d}/{args.end_seed:02d}: retained", flush=True)
            continue
        variant = f"arch2-placement-seed-{seed:02d}"
        fixed_make_args = (
            f"DESIGN_CONFIG={DESIGN_CONFIG} "
            f"FLOW_VARIANT={variant} "
            "NUM_CORES=1 "
            f"GPL_RANDOM_SEED={seed} "
            "GRT_SEED=1 OR_SEED=1"
        )
        container_script = (
            "source /OpenROAD-flow-scripts/env.sh && "
            "cd /OpenROAD-flow-scripts/flow && "
            f"make {fixed_make_args} clean_all >/dev/null && "
            f"make {fixed_make_args} {FLOW_TARGET}"
        )
        command = [
            "docker",
            "run",
            "--rm",
            "--platform",
            "linux/amd64",
            "-u",
            f"{os.getuid()}:{os.getgid()}",
            "-v",
            f"{flow}:/OpenROAD-flow-scripts/flow",
            IMAGE,
            "bash",
            "-lc",
            container_script,
        ]
        print(f"seed {seed:02d}/{args.end_seed:02d}: running", flush=True)
        timestamp = datetime.now(timezone.utc).isoformat()
        start = time.monotonic()
        try:
            result = run(command, cwd=REPO_ROOT, timeout=args.timeout_seconds)
            returncode = result.returncode
            output = result.stdout
        except subprocess.TimeoutExpired as exc:
            returncode = 124
            output = (exc.stdout or "") + "\nrunner timeout"
        elapsed = time.monotonic() - start

        stdout_path = RAW_DIR / f"openroad_gcd_placement_seed_{seed:02d}.stdout.txt"
        stdout_path.write_text(output, encoding="utf-8")
        log_dir = flow / "logs" / "nangate45" / "gcd" / variant
        results_dir = flow / "results" / "nangate45" / "gcd" / variant
        gp_path = log_dir / "3_3_place_gp.json"
        dp_path = log_dir / "3_5_place_dp.json"
        odb_path = results_dir / "3_place.odb"
        gp = read_json(gp_path) if gp_path.exists() else {}
        dp = read_json(dp_path) if dp_path.exists() else {}
        gp_raw = RAW_DIR / f"openroad_gcd_placement_seed_{seed:02d}.globalplace.json"
        dp_raw = RAW_DIR / f"openroad_gcd_placement_seed_{seed:02d}.detailedplace.json"
        if gp:
            shutil.copyfile(gp_path, gp_raw)
        if dp:
            shutil.copyfile(dp_path, dp_raw)
        gp_errors = metric(gp, "globalplace__flow__errors__count")
        dp_errors = metric(dp, "detailedplace__flow__errors__count")
        status = (
            "pass"
            if returncode == 0
            and gp
            and dp
            and odb_path.exists()
            and gp_errors == 0
            and dp_errors == 0
            else "fail"
        )
        row = {
            "seed": seed,
            "status": status,
            "variant": variant,
            "flow_target": FLOW_TARGET,
            "gpl_random_seed": seed,
            "grt_seed_fixed": 1,
            "or_seed_fixed": 1,
            "num_cores": 1,
            "docker_returncode": returncode,
            "wall_time_seconds": round(elapsed, 3),
            "globalplace_instance_area_um2": metric(
                gp, "globalplace__design__instance__area"
            ),
            "globalplace_setup_wns_ns": metric(gp, "globalplace__timing__setup__ws"),
            "globalplace_setup_tns_ns": metric(gp, "globalplace__timing__setup__tns"),
            "globalplace_hold_wns_ns": metric(gp, "globalplace__timing__hold__ws"),
            "detailedplace_instance_area_um2": metric(
                dp, "detailedplace__design__instance__area"
            ),
            "detailedplace_setup_wns_ns": metric(
                dp, "detailedplace__timing__setup__ws"
            ),
            "detailedplace_setup_tns_ns": metric(
                dp, "detailedplace__timing__setup__tns"
            ),
            "detailedplace_hold_wns_ns": metric(dp, "detailedplace__timing__hold__ws"),
            "globalplace_flow_errors": gp_errors,
            "detailedplace_flow_errors": dp_errors,
            "globalplace_json_sha256": sha256_file(gp_raw) if gp else "",
            "detailedplace_json_sha256": sha256_file(dp_raw) if dp else "",
            "floorplan_odb_sha256": "",
            "placement_odb_sha256": sha256_file(odb_path) if odb_path.exists() else "",
            "stdout_receipt": stdout_path.relative_to(REPO_ROOT).as_posix(),
            "extraction_timestamp": timestamp,
        }
        rows = [existing for existing in rows if int(existing["seed"]) != seed]
        rows.append(row)
        rows.sort(key=lambda item: int(item["seed"]))
        refresh_retained_artifacts(rows, flow)
        write_csv(rows)
        write_summary(
            rows,
            orfs=args.orfs,
            docker=docker,
            start_timestamp=start_timestamp,
        )
        print(
            f"seed {seed:02d}/{args.end_seed:02d}: {status} in {elapsed:.1f}s",
            flush=True,
        )

    refresh_retained_artifacts(rows, flow)
    write_csv(rows)
    write_summary(
        rows,
        orfs=args.orfs,
        docker=docker,
        start_timestamp=start_timestamp,
    )
    print(f"generated: {CSV_PATH}")
    print(f"generated: {SUMMARY_PATH}")
    return 0 if all(row["status"] == "pass" for row in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
