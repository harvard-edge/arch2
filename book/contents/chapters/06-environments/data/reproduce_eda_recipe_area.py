#!/usr/bin/env python3
"""Re-derive the mapped-area column of fig-eda-runtime-variance-dispersion.csv.

The harness that originally produced the CSV was not retained. This script is a
reconstruction, written 2026-09-29, that reproduces every retained ChipArea_um2 and
SequentialArea_um2 value exactly (125 of 125 rows) from pinned public RTL, the Nangate45 typical
library, and Yosys 0.67+post (git sha1 b8e7da6f40ae8f552c116bf6c359b07c6533e159).

Flow per row (one design, one ABC pass sequence):

    read_verilog <sources>
    synth -flatten -top <TopModule>
    dfflibmap -liberty NangateOpenCellLibrary_typical.lib
    abc -liberty NangateOpenCellLibrary_typical.lib -script +<PassSequence>
    opt_clean
    stat -liberty NangateOpenCellLibrary_typical.lib

Mapped area and sequential area are re-derived. Wall-clock time and peak memory are host
measurements that no retained log records, so they are not part of the dataset.

Usage:
    python3 reproduce_eda_recipe_area.py --cache /tmp/eda-recipe-cache
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import urllib.request
from pathlib import Path

ORFS = "https://raw.githubusercontent.com/The-OpenROAD-Project/OpenROAD-flow-scripts/c63a606f9ccede13df8c82bbe31a8f6c6d323f6b/flow"
SHA256 = "https://raw.githubusercontent.com/secworks/sha256/837c5cc396f001d18f2c765721c585716eb439ae/src/rtl"
PICORV32 = "https://raw.githubusercontent.com/YosysHQ/picorv32/a473fc8fca393771d83b0ffcf0b14db3393339d8"

LIBRARY = f"{ORFS}/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib"
SOURCES = {
    "picorv32": [f"{PICORV32}/picorv32.v"],
    "gcd": [f"{ORFS}/designs/src/gcd/gcd.v"],
    "dynamic_node": [f"{ORFS}/designs/src/dynamic_node/dynamic_node.pickle.v"],
    "aes_cipher_top": [
        f"{ORFS}/designs/src/aes/{name}"
        for name in (
            "aes_cipher_top.v",
            "aes_key_expand_128.v",
            "aes_rcon.v",
            "aes_sbox.v",
            "timescale.v",
        )
    ],
    "sha256_core": [
        f"{SHA256}/{name}"
        for name in ("sha256_core.v", "sha256_k_constants.v", "sha256_w_mem.v")
    ],
}
# timescale.v is an include target for the AES sources, not a compilation unit.
INCLUDE_ONLY = {"timescale.v"}


def fetch(url: str, cache: Path) -> Path:
    target = cache / url.split("/")[-1]
    if not target.exists():
        urllib.request.urlretrieve(url, target)
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--yosys", default="yosys")
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)

    library = fetch(LIBRARY, args.cache)
    csv_path = (
        Path(__file__).resolve().parent / "fig-eda-runtime-variance-dispersion.csv"
    )
    with open(csv_path, encoding="utf-8") as fh:
        rows = list(csv.DictReader(line for line in fh if not line.startswith("#")))

    matched = 0
    for row in rows:
        files = [fetch(url, args.cache) for url in SOURCES[row["DesignName"]]]
        compiled = " ".join(str(f) for f in files if f.name not in INCLUDE_ONLY)
        script = "+" + ";".join(
            step.strip().replace(" ", ",") for step in row["PassSequence"].split(";")
        )
        ys = (
            f"read_verilog -I{args.cache} {compiled}\n"
            f"synth -flatten -top {row['TopModule']}\n"
            f"dfflibmap -liberty {library}\n"
            f"abc -liberty {library} -script {script}\n"
            "opt_clean\n"
            f"stat -liberty {library}\n"
        )
        script_path = args.cache / "run.ys"
        script_path.write_text(ys, encoding="utf-8")
        result = subprocess.run(
            [args.yosys, "-s", str(script_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        areas = re.findall(
            r"Chip area for (?:top )?module '\S+': ([0-9.]+)", result.stdout
        )
        seq = re.findall(r"used for sequential elements: ([0-9.]+)", result.stdout)
        got = float(areas[-1])
        got_seq = float(seq[-1])
        ok = (
            abs(got - float(row["ChipArea_um2"])) < 1e-3
            and abs(got_seq - float(row["SequentialArea_um2"])) < 1e-3
        )
        matched += ok
        print(
            f"{row['DesignName']:>15} recipe {row['SeedIndex']:>3}: "
            f"recorded {row['ChipArea_um2']:>11} re-derived {got:>11.4f} "
            f"{'match' if ok else 'MISMATCH'}"
        )
    print(f"{matched}/{len(rows)} rows re-derived exactly (mapped and sequential area)")


if __name__ == "__main__":
    main()
