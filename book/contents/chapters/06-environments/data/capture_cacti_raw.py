#!/usr/bin/env python3
"""Keep the raw CACTI stdout behind cacti-lighthouse-l2.csv and probe the node floor.

run_cacti_lighthouse_l2.py keeps only parsed values. This script reruns the same six
configurations through that script's template and pinned commit, writes each stdout
to cacti-raw/, confirms the parsed fields match the CSV, and records what the build
does at and below 22 nm. CACTI exits 0 on an unsupported node, so the probe records
stdout markers as well as the exit code. Build CACTI as run_cacti_lighthouse_l2.py
describes.

Usage:
    python3 capture_cacti_raw.py --cacti-dir /path/to/built/cacti
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import tempfile
from pathlib import Path

from run_cacti_lighthouse_l2 import (
    CAPACITIES_MIB,
    COMMIT,
    DEVICE_TYPES,
    FIELDS,
    HERE,
    MIB,
    OUT,
    TECHNOLOGY_UM,
    TEMPLATE,
    WAYS,
)

RAW = HERE / "cacti-raw"
PROBE_NODES_UM = ["0.032", "0.022", "0.021", "0.020", "0.016", "0.003"]


def invoke(cacti_dir: Path, capacity_mib: int, device: str, node_um: str):
    cfg = TEMPLATE.read_text().format(
        size_bytes=capacity_mib * MIB,
        associativity=WAYS,
        technology_um=node_um,
        cell_type=device,
        peripheral_type=device,
    )
    with tempfile.NamedTemporaryFile("w", suffix=".cfg", delete=False) as fh:
        fh.write(cfg)
        cfg_path = fh.name
    result = subprocess.run(
        ["./cacti", "-infile", cfg_path], cwd=cacti_dir, capture_output=True, text=True
    )
    Path(cfg_path).unlink()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cacti-dir", type=Path, required=True)
    args = parser.parse_args()
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=args.cacti_dir,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if head != COMMIT:
        raise SystemExit(f"CACTI checkout is at {head}, expected {COMMIT}")
    RAW.mkdir(exist_ok=True)
    with open(OUT, encoding="utf-8") as fh:
        recorded = {
            (r["device_type"], int(r["capacity_mib"])): r
            for r in csv.DictReader(l for l in fh if not l.startswith("#"))
        }
    mismatches = 0
    for device in DEVICE_TYPES:
        for mib in CAPACITIES_MIB:
            result = invoke(args.cacti_dir, mib, device, TECHNOLOGY_UM)
            result.check_returncode()
            (RAW / f"{device}-{mib}mib.stdout.txt").write_text(
                result.stdout, encoding="utf-8"
            )
            for name, pattern in FIELDS.items():
                got = float(re.search(pattern, result.stdout).group(1))
                if got != float(recorded[(device, mib)][name]):
                    mismatches += 1
                    print(f"MISMATCH {device} {mib} {name}: {got}")
    with open(RAW / "node-floor-probe.txt", "w", encoding="utf-8") as fh:
        fh.write(f"# CACTI {COMMIT}, 2 MiB itrs-hp, otherwise the Lighthouse config\n")
        for node in PROBE_NODES_UM:
            result = invoke(args.cacti_dir, 2, "itrs-hp", node)
            solved = "Access time (ns):" in result.stdout
            rejected = "Invalid technology nodes" in result.stdout
            fh.write(
                f"technology_um={node} exit={result.returncode} "
                f"access_time_reported={solved} invalid_node_message={rejected}\n"
            )
    print(f"{mismatches} field mismatches against {OUT.name}")


if __name__ == "__main__":
    main()
