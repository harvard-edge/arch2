#!/usr/bin/env python3
"""Regenerate the committed figure receipts from the raw upstream sources.

The six quantitative "money plot" figures each read a trimmed receipt CSV in this
directory. Those receipts are derived from the raw upstream files in ``sources/``.
Run this script to rebuild every receipt after refreshing a raw source::

    python3 data/source-receipts/regenerate.py

To refresh a source first, re-fetch it (URLs below) into ``sources/`` under the
same filename, then re-run this script and rebuild the book.

Sources:
- epoch-notable-models.csv   epoch.ai/data/notable_ai_models.csv
- epoch-benchmarks.csv       epoch.ai/data/benchmarks.csv
- epoch-ml-hardware.csv      epoch.ai/data/ml_hardware.csv
- reuther-laics-2025.csv     github.com/areuther/ai-accelerators (peak_accelerators_ieee_hpec_2025.csv)
- metr-time-horizon.yaml     metr.org/assets/benchmark_results_1_1.yaml

Requires: pyyaml (only for the METR receipt).
"""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "sources"


def _num(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _write(name, header, rows):
    with open(HERE / name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  wrote {name} ({len(rows)} rows)")


def training_compute():  # ch2
    out = []
    with open(SRC / "epoch-notable-models.csv", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        if len(row) <= 41:
            continue
        model = row[0].strip().replace("\n", " ")
        date, comp, front = row[2].strip(), row[7].strip(), row[41].strip()
        if _num(comp) and date and _num(comp) > 0:
            out.append(
                [
                    model,
                    date,
                    comp,
                    "1" if front.lower() in ("true", "yes", "1") else "0",
                ]
            )
    _write(
        "chapter2-training-compute.csv",
        ["model", "publication_date", "training_compute_flop", "frontier"],
        out,
    )


def accelerator_landscape():  # ch1
    out = []
    with open(SRC / "reuther-laics-2025.csv", encoding="utf-8-sig") as f:
        reader = csv.DictReader(l for l in f if not l.startswith("#"))
        reader.fieldnames = [fn.strip().lstrip("﻿") for fn in reader.fieldnames]
        for d in reader:
            d = {
                k.strip(): (v.strip() if isinstance(v, str) else v)
                for k, v in d.items()
            }
            if _num(d.get("PeakPerformance")) and _num(d.get("Power")):
                out.append(
                    [
                        d.get("Label", ""),
                        d.get("PeakPerformance"),
                        d.get("Power"),
                        d.get("FormFactor", ""),
                        d.get("IorT", ""),
                    ]
                )
    _write(
        "chapter1-accelerator-landscape.csv",
        [
            "label",
            "peak_performance_ops_per_s",
            "power_w",
            "form_factor",
            "inference_or_training",
        ],
        out,
    )


def swebench():  # ch1
    out = []
    for row in csv.DictReader(open(SRC / "epoch-benchmarks.csv", encoding="utf-8-sig")):
        if row["task"] != "SWE-Bench verified":
            continue
        score = _num(row["Best score (across scorers)"])
        date = row["Version release date"].strip()
        if score is not None and date:
            out.append([row.get("Model") or row.get("model"), date, score])
    out.sort(key=lambda x: x[1])
    _write(
        "chapter1-swebench-verified.csv",
        ["model", "release_date", "resolved_fraction"],
        out,
    )


def hardware_efficiency():  # ch10
    out = []
    for row in csv.DictReader(
        open(SRC / "epoch-ml-hardware.csv", encoding="utf-8-sig")
    ):
        eff = _num(row.get("Energy efficiency"))
        date = row.get("Release date", "").strip()
        if eff and eff > 0 and date:
            out.append(
                [row.get("Hardware name", ""), date, row.get("Energy efficiency")]
            )
    _write(
        "chapter10-hardware-efficiency.csv",
        ["hardware_name", "release_date", "energy_efficiency_bitops_per_w"],
        out,
    )


def task_horizon():  # ch11
    import yaml

    data = yaml.safe_load(open(SRC / "metr-time-horizon.yaml"))
    out = []
    for key, val in data["results"].items():
        try:
            rd = val["release_date"]
            rd = rd.isoformat() if hasattr(rd, "isoformat") else str(rd)
            out.append([key, rd, val["metrics"]["p50_horizon_length"]["estimate"]])
        except (KeyError, TypeError):
            pass
    out.sort(key=lambda x: x[1])
    _write(
        "chapter11-task-horizon.csv",
        ["model", "release_date", "p50_horizon_minutes"],
        out,
    )


def simulator_tax():  # ch5 (synthesized from primary sources; no raw file)
    rows = [
        ["Native silicon", "~3 GHz core", 1, "definitional baseline (~3 GHz, IPC ~1)"],
        [
            "Functional / ISA sim",
            "QEMU / Spike / gem5-Atomic",
            30,
            "tens-hundreds MIPS; ZSim IPC=1 up to 90 MIPS (Sanchez & Kozyrakis 2013)",
        ],
        [
            "Cycle-approximate",
            "ZSim / Sniper",
            1000,
            "ZSim/Sniper detailed OOO ~1-4 MIPS/core; ZSim reports ~1000x faster than detailed cycle-accurate simulators, so this rung sits well above cycle-accurate (Sanchez & Kozyrakis 2013; Carlson et al. 2011)",
        ],
        [
            "Cycle-accurate",
            "gem5 O3 / Flexus",
            15000,
            "~200 KIPS gem5/Flexus/MARSS class (Sanchez & Kozyrakis 2013)",
        ],
        [
            "RTL simulation",
            "Verilator",
            30000,
            "~10-292 kHz effective core clock (Chipyard; GSIM 2025)",
        ],
        ["FPGA emulation", "FireSim", 20, "150+ MHz per node (Karandikar et al. 2018)"],
    ]
    _write(
        "chapter5-simulator-tax.csv",
        ["rung", "example", "slowdown_vs_silicon", "source_note"],
        rows,
    )


def mitigation_overhead():  # ch7 (compiled from Canella et al. 2019 Table 11; no raw file)
    rows = [
        [
            "KPTI page-table isolation",
            "Meltdown",
            0,
            5,
            "~0% compute-bound to ~5% at 75k syscalls/s (Gregg 2018); KAISER 0-2.6% (Canella 2019 Tbl.11)",
        ],
        [
            "SSBD microcode",
            "Spectre-v4",
            2,
            8,
            "SYSmark 2018 / SPEC integer (Intel, in Canella 2019 Tbl.11)",
        ],
        [
            "Retpoline software",
            "Spectre-v2",
            5,
            10,
            "real-world servers (Carruth/Google, in Canella 2019 Tbl.11)",
        ],
        [
            "All default mitigations (Intel)",
            "combined",
            7,
            16,
            "mixed suite Linux 4.19-5.0 (Phoronix 2018-2019); AMD ~3-4%",
        ],
        [
            "IBRS microcode",
            "Spectre-v2",
            20,
            30,
            "syscall-heavy Sysbench (Turner/Google, in Canella 2019 Tbl.11)",
        ],
        [
            "STIBP cross-thread",
            "Spectre-v2",
            30,
            50,
            "Rodinia OpenMP / DaCapo (Larabel, in Canella 2019 Tbl.11)",
        ],
    ]
    _write(
        "chapter7-mitigation-overhead.csv",
        ["mitigation", "threat", "low_pct", "high_pct", "source_note"],
        rows,
    )


if __name__ == "__main__":
    print("Regenerating figure receipts from sources/ ...")
    training_compute()
    accelerator_landscape()
    swebench()
    hardware_efficiency()
    task_horizon()
    simulator_tax()
    mitigation_overhead()
    print("Done. Rebuild with: python3 cli/arch2.py build --html")
