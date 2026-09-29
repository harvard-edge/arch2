#!/usr/bin/env python3
"""Run CACTI 7 for the three Lighthouse L2 capacities screened in chapter 6.

Written 2026-09-29 to replace hand-typed screening returns in the chapter 6
walkthrough with model output. It writes cacti-lighthouse-l2.csv next to this
file.

Tool, pinned:
    https://github.com/HewlettPackard/cacti
    commit 1ffd8dfb10303d306ecd8d215320aea07651e878 (CACTI 7.0)

Build (the unmodified source does not compile with current clang):
    git clone https://github.com/HewlettPackard/cacti && cd cacti
    git checkout 1ffd8dfb10303d306ecd8d215320aea07651e878
    # nuca.cc repeats a default argument that nuca.h already declares; drop it.
    sed -i.bak 's|DeviceType \\*dt = &(g_tp.peri_global)|DeviceType *dt|' nuca.cc
    mkdir -p obj_opt
    make -f cacti.mk TAG=opt CXX=clang++ CC=clang \\
        OPT="-O2 -Wno-reserved-user-defined-literal -DNTHREADS=8"

The patch removes a redundant default argument and changes no model code.
Verified on arm64 macOS with Apple clang; on x86 Linux with g++ the stock
`make` target may build without it.

Declared construction rule (the chapter says the study must supply one):
    64-byte lines, 16-way set associative (2,048 / 3,072 / 4,096 sets for
    2 / 3 / 4 MiB; CACTI requires power-of-two associativity), one bank, one
    read-write port, ECC on, 360 K, the design objective of the stock
    cache.cfg (ED^2), and 22 nm, the smallest node CACTI 7 characterizes.
Device type is run both ways, because the study has not bound it: ITRS
high-performance (itrs-hp) and ITRS low-standby-power (itrs-lstp) for both
the cell array and the peripheral circuits.

These choices are the author's, stated so the runs can be repeated. They are
one legal organization per capacity, not an optimized design.

Usage:
    python3 run_cacti_lighthouse_l2.py --cacti-dir /path/to/built/cacti
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "cacti_lighthouse_l2.cfg.in"
OUT = HERE / "cacti-lighthouse-l2.csv"
COMMIT = "1ffd8dfb10303d306ecd8d215320aea07651e878"

MIB = 1024 * 1024
CAPACITIES_MIB = [2, 3, 4]
WAYS = 16
TECHNOLOGY_UM = "0.022"
DEVICE_TYPES = ["itrs-hp", "itrs-lstp"]

FIELDS = {
    "access_time_ns": r"Access time \(ns\):\s*([0-9.eE+-]+)",
    "cycle_time_ns": r"Cycle time \(ns\):\s*([0-9.eE+-]+)",
    "read_energy_nj": r"Total dynamic read energy per access \(nJ\):\s*([0-9.eE+-]+)",
    "leakage_mw": r"Total leakage power of a bank \(mW\):\s*([0-9.eE+-]+)",
    "height_mm": r"Cache height x width \(mm\):\s*([0-9.eE+-]+)\s*x",
    "width_mm": r"Cache height x width \(mm\):\s*[0-9.eE+-]+\s*x\s*([0-9.eE+-]+)",
}


def run_one(cacti_dir: Path, capacity_mib: int, device: str) -> dict:
    ways = WAYS
    cfg = TEMPLATE.read_text().format(
        size_bytes=capacity_mib * MIB,
        associativity=ways,
        technology_um=TECHNOLOGY_UM,
        cell_type=device,
        peripheral_type=device,
    )
    with tempfile.NamedTemporaryFile("w", suffix=".cfg", delete=False) as fh:
        fh.write(cfg)
        cfg_path = fh.name
    # CACTI resolves tech_params/ relative to its working directory.
    out = subprocess.run(
        ["./cacti", "-infile", cfg_path],
        cwd=cacti_dir,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    Path(cfg_path).unlink()
    row = {
        "capacity_mib": capacity_mib,
        "associativity": ways,
        "sets": capacity_mib * MIB // (64 * ways),
        "device_type": device,
    }
    for name, pattern in FIELDS.items():
        match = re.search(pattern, out)
        if match is None:
            raise RuntimeError(f"{capacity_mib} MiB: CACTI output lacks {name}")
        row[name] = float(match.group(1))
    row["area_mm2"] = round(row["height_mm"] * row["width_mm"], 4)
    return row


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
    rows = [
        run_one(args.cacti_dir, mib, device)
        for device in DEVICE_TYPES
        for mib in CAPACITIES_MIB
    ]
    columns = [
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
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        fh.write(
            f"# CACTI 7 ({COMMIT}), config cacti_lighthouse_l2.cfg.in, "
            "written by run_cacti_lighthouse_l2.py\n"
        )
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            row["technology_nm"] = 22
            writer.writerow({k: row[k] for k in columns})
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
