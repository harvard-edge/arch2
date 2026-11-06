#!/usr/bin/env python3
"""Run the third ITRS device type for the Lighthouse L2 capacities in chapter 6.

cache.cfg at the pinned CACTI commit lists three ITRS device types for SRAM cells
and peripheral circuits. run_cacti_lighthouse_l2.py covers itrs-hp and itrs-lstp.
This script covers itrs-lop under the same template, node, and cache specification,
keeps each stdout in cacti-raw/, and writes cacti-lighthouse-l2-lop.csv. Its rows
are in a separate file so that the six-row file other records bind stays unchanged.
Build CACTI as run_cacti_lighthouse_l2.py describes.

Usage:
    python3 run_cacti_lighthouse_l2_lop.py --cacti-dir /path/to/built/cacti
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess

from capture_cacti_raw import RAW, invoke
from run_cacti_lighthouse_l2 import (
    CAPACITIES_MIB,
    COMMIT,
    FIELDS,
    HERE,
    MIB,
    TECHNOLOGY_UM,
    WAYS,
)

OUT = HERE / "cacti-lighthouse-l2-lop.csv"
DEVICE = "itrs-lop"
COLUMNS = [
    "device_type",
    "capacity_mib",
    "associativity",
    "sets",
    "technology_nm",
    "area_mm2",
    "height_mm",
    "width_mm",
    "access_time_ns",
    "cycle_time_ns",
    "read_energy_nj",
    "leakage_mw",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cacti-dir", required=True)
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
    rows = []
    for mib in CAPACITIES_MIB:
        result = invoke(args.cacti_dir, mib, DEVICE, TECHNOLOGY_UM)
        result.check_returncode()
        (RAW / f"{DEVICE}-{mib}mib.stdout.txt").write_text(
            result.stdout, encoding="utf-8"
        )
        row = {
            "device_type": DEVICE,
            "capacity_mib": mib,
            "associativity": WAYS,
            "sets": mib * MIB // (64 * WAYS),
            "technology_nm": 22,
        }
        for name, pattern in FIELDS.items():
            row[name] = float(re.search(pattern, result.stdout).group(1))
        row["area_mm2"] = round(row["height_mm"] * row["width_mm"], 4)
        rows.append(row)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        fh.write(
            f"# CACTI 7 ({COMMIT}), config cacti_lighthouse_l2.cfg.in, "
            "written by run_cacti_lighthouse_l2_lop.py\n"
        )
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
