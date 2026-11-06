#!/usr/bin/env python3
"""Compare the removed TotalCellCount and WireCount columns with Yosys stat output.

The columns were removed from fig-eda-runtime-variance-dispersion.csv on 2026-09-29
(commit 542ea2c78). The values survive in git history at the parent of that commit,
so this script reads them from there and reruns the flow of
reproduce_eda_recipe_area.py for each of the 125 retained rows. It prints one line
per row and a summary. It writes no dataset.

Usage (from the repository, with a yosys of the recorded sha1 on PATH):
    python3 recheck_removed_columns.py --cache <dir>
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
from pathlib import Path

from reproduce_eda_recipe_area import INCLUDE_ONLY, LIBRARY, SOURCES, fetch

REV = "542ea2c78^"
CSV = "book/contents/chapters/06-environments/data/fig-eda-runtime-variance-dispersion.csv"


def old_rows() -> list[dict]:
    text = subprocess.run(
        ["git", "show", f"{REV}:{CSV}"],
        cwd=Path(__file__).resolve().parent,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return list(csv.DictReader(l for l in text.splitlines() if not l.startswith("#")))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--yosys", default="yosys")
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    library = fetch(LIBRARY, args.cache)
    rows = [r for r in old_rows() if r["DesignName"] in SOURCES]
    cells_ok = wires_ok = 0
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
        path = args.cache / "run.ys"
        path.write_text(ys, encoding="utf-8")
        out = subprocess.run(
            [args.yosys, "-s", str(path)], capture_output=True, text=True, check=True
        ).stdout
        block = out[out.rindex("Printing statistics") :]
        cells = int(re.search(r"^\s*(\d+)(?:\s+[\d.eE+-]+)?\s+cells\s*$", block, re.M).group(1))
        wires = int(re.search(r"^\s*(\d+)(?:\s+[\d.eE+-]+)?\s+wires\s*$", block, re.M).group(1))
        same_cells = cells == int(row["TotalCellCount"])
        same_wires = wires == int(row["WireCount"])
        cells_ok += same_cells
        wires_ok += same_wires
        print(
            f"{row['DesignName']:>15} recipe {row['SeedIndex']:>3}: "
            f"cells recorded {row['TotalCellCount']:>6} yosys {cells:>6}; "
            f"wires recorded {row['WireCount']:>6} yosys {wires:>6}"
        )
    print(f"{cells_ok}/{len(rows)} cell counts match; {wires_ok}/{len(rows)} wire counts match")


if __name__ == "__main__":
    main()
