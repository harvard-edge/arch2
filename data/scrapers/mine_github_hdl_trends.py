#!/usr/bin/env python3
"""
Hand-typed stand-in for HDL repository counts. NOT MINED DATA.
==============================================================

Despite this file's name, nothing it writes was read from GitHub. The table
below is hand-typed, its origin is unrecorded, and no value has been checked
against a source. Even years are the typed values. Each odd year is the
previous even year scaled up by 15 percent, a formula chosen by hand. The
retained CSV matches this table and formula in all 75 cells, so no API query
contributed to it. The earlier API code could not run, because a constant
forced this table, and it recorded a failed query as zero repositories. It has
been removed so that the script cannot be mistaken for a miner.

The output feeds no book figure and no book number. Its only reader is
data/datasets/plot_new_mining_datasets.py. Evidence class: constructed.

Outputs:
data/datasets/github_hdl_language_trends.csv
"""

import csv
import os

HEADER = """\
# CONSTRUCTED STAND-IN. NOT MINED DATA. Nothing here was read from GitHub.
# Even years are hand-typed values of unrecorded origin, unchecked against any source.
# Odd years are the previous even year scaled up by 15 percent, a formula chosen by hand.
# Written by data/scrapers/mine_github_hdl_trends.py. Feeds no book figure or number.
"""

LANGUAGES = ["Verilog", "VHDL", "SystemVerilog", "Chisel", "Tcl"]
START_YEAR = 2010
END_YEAR = 2024

# Hand-typed anchor values. Their origin is unrecorded and none has been checked.
STAND_IN_ANCHORS = {
    2010: {"Verilog": 450, "VHDL": 320, "SystemVerilog": 45, "Chisel": 0, "Tcl": 210},
    2012: {
        "Verilog": 1200,
        "VHDL": 850,
        "SystemVerilog": 120,
        "Chisel": 15,
        "Tcl": 450,
    },
    2014: {
        "Verilog": 2500,
        "VHDL": 1600,
        "SystemVerilog": 350,
        "Chisel": 60,
        "Tcl": 890,
    },
    2016: {
        "Verilog": 4800,
        "VHDL": 3100,
        "SystemVerilog": 850,
        "Chisel": 180,
        "Tcl": 1500,
    },
    2018: {
        "Verilog": 8500,
        "VHDL": 5200,
        "SystemVerilog": 1900,
        "Chisel": 450,
        "Tcl": 2800,
    },
    2020: {
        "Verilog": 14200,
        "VHDL": 7800,
        "SystemVerilog": 3600,
        "Chisel": 950,
        "Tcl": 4200,
    },
    2022: {
        "Verilog": 21500,
        "VHDL": 10500,
        "SystemVerilog": 6500,
        "Chisel": 1850,
        "Tcl": 6100,
    },
    2024: {
        "Verilog": 32000,
        "VHDL": 13200,
        "SystemVerilog": 11500,
        "Chisel": 3200,
        "Tcl": 8500,
    },
}


def write_stand_in():
    print("Writing the hand-typed HDL stand-in table (not mined)...")
    results = []

    for year in range(START_YEAR, END_YEAR + 1):
        row = {"Year": year}
        closest_year = min(STAND_IN_ANCHORS, key=lambda k: abs(k - year))
        for lang in LANGUAGES:
            base_val = STAND_IN_ANCHORS[closest_year][lang]
            # Fills odd years with a hand-chosen formula. These are not observations.
            row[lang] = int(base_val * (1.0 + 0.15 * (year - closest_year)))
        results.append(row)

    os.makedirs("data/datasets", exist_ok=True)
    out_file = "data/datasets/github_hdl_language_trends.csv"

    with open(out_file, "w", newline="") as f:
        f.write(HEADER)
        writer = csv.DictWriter(f, fieldnames=["Year"] + LANGUAGES)
        writer.writeheader()
        writer.writerows(results)

    print(f"Saved the stand-in table to {out_file}")


if __name__ == "__main__":
    write_stand_in()
