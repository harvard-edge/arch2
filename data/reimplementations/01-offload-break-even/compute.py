#!/usr/bin/env python3
"""Offload break-even crossovers, spec 01. Run from this folder: python3 compute.py"""
import csv
import hashlib
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "inputs/data/studies/27-offload-break-even/raw"
SUPERSEDED = RAW / "superseded-shared-wait"

PAIRS = {  # pair: (GPU arm, host arm), from the spec's Definitions
    "resident": ("mps_resident", "cpu_single"),
    "copy": ("mps_copy", "cpu_single"),
    "sixteen_await": ("mps_16_launch", "cpu_bmm"),
    "one_launch": ("mps_bmm", "cpu_bmm"),
}
SPEC_CUTOFF = 256  # stated in the spec's launch-ratio definition
COLUMNS = ["run_id", "n", "panel", "arm", "arm_order", "rep", "seconds"]


def run_files(directory):
    """All run-<k>.csv directly in directory, in numeric k order."""
    found = []
    for path in directory.glob("run-*.csv"):
        match = re.fullmatch(r"run-(\d+)\.csv", path.name)
        if match is None:
            raise ValueError(f"unexpected file name {path}")
        found.append((int(match.group(1)), path))
    return sorted(found)


def load(directory, drops):
    """Rows of one directory as {run_id: {(arm, n): [seconds]}}. Refuses malformed files."""
    runs = {}
    for k, path in run_files(directory):
        cells = defaultdict(list)
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != COLUMNS:
                raise ValueError(f"{path}: columns {reader.fieldnames}")
            for row in reader:
                if int(row["run_id"]) != k:
                    raise ValueError(f"{path}: run_id {row['run_id']} in run-{k}.csv")
                seconds = float(row["seconds"])
                if not seconds > 0:  # also catches NaN
                    drops.append({"file": str(path.relative_to(HERE)), "row": row,
                                  "why": "seconds not a positive number"})
                    continue
                cells[(row["arm"], int(row["n"]))].append(seconds)
        runs[k] = dict(cells)
    return runs


def grid_of(cells_by_run):
    """The size grid, required to be the same for every arm of every run."""
    grids = {frozenset(n for (_, n) in cells) for cells in cells_by_run.values()}
    if len(grids) != 1:
        raise ValueError(f"runs disagree on the size grid: {grids}")
    grid = sorted(next(iter(grids)))
    for run, cells in cells_by_run.items():
        for gpu, host in PAIRS.values():
            for arm in (gpu, host):
                missing = [n for n in grid if (arm, n) not in cells]
                if missing:
                    raise ValueError(f"run {run} arm {arm} has no rows at {missing}")
    return grid


def medians_of(cells):
    return {key: statistics.median(values) for key, values in cells.items()}


def crossover(medians, pair, grid, ties):
    """first_ahead_n, sustained_from_n and the ascending ahead list on one table of medians."""
    gpu, host = PAIRS[pair]
    ahead = []
    for n in grid:
        if medians[(gpu, n)] == medians[(host, n)]:
            ties.append({"pair": pair, "n": n})
        if medians[(gpu, n)] < medians[(host, n)]:
            ahead.append(n)
    first = ahead[0] if ahead else None
    sustained = None
    for n in reversed(grid):
        if n not in ahead:
            break
        sustained = n
    return {"first_ahead_n": first, "sustained_from_n": sustained, "ahead_ns": ahead}


def present(values):
    return [v for v in values if v is not None]


def span(values):
    kept = present(values)
    return (min(kept), max(kept)) if kept else (None, None)


def steps(grid, low, high):
    if low is None or high is None:
        return None
    return grid.index(high) - grid.index(low)


def launch_ratio(medians, n):
    return medians[("mps_16_launch", n)] / medians[("mps_bmm", n)]


def launch_fields(per_run_medians, pooled_medians, grid, pooled_cutoff, lohi_cutoff):
    pooled_ns = [n for n in grid if n <= pooled_cutoff]
    lohi_ns = [n for n in grid if n <= lohi_cutoff]
    ratios = [(launch_ratio(medians, n), run, n)
              for run, medians in sorted(per_run_medians.items()) for n in lohi_ns]
    low = min(ratios)
    high = max(ratios)
    return {
        "launch_ratio_pooled": statistics.median(
            launch_ratio(pooled_medians, n) for n in pooled_ns),
        "launch_ratio_lo": low[0],
        "launch_ratio_hi": high[0],
        "launch_ratio_detail": {
            "pooled_ns": pooled_ns,
            "lohi_ns": lohi_ns,
            "lo_at": {"run_id": low[1], "n": low[2]},
            "hi_at": {"run_id": high[1], "n": high[2]},
            "pooled_ratio_by_n": {str(n): launch_ratio(pooled_medians, n) for n in lohi_ns},
            "per_run_lo_hi": {
                str(run): [min(launch_ratio(medians, n) for n in lohi_ns),
                           max(launch_ratio(medians, n) for n in lohi_ns)]
                for run, medians in sorted(per_run_medians.items())},
        },
    }


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    drops = []
    current = load(RAW, drops)
    superseded = load(SUPERSEDED, drops)
    grid = grid_of(current)
    superseded_grid = grid_of(superseded)

    per_run = {run: medians_of(cells) for run, cells in current.items()}
    pooled_rows = defaultdict(list)
    for cells in current.values():
        for key, values in cells.items():
            pooled_rows[key].extend(values)
    pooled = medians_of(pooled_rows)

    ties = []
    pairs = {}
    for pair in PAIRS:
        table = {}
        for run, medians in sorted(per_run.items()):
            table[run] = crossover(medians, pair, grid, ties)
        first = [row["first_ahead_n"] for row in table.values()]
        sustained = [row["sustained_from_n"] for row in table.values()]
        first_min, first_max = span(first)
        sustained_min, sustained_max = span(sustained)
        whole = crossover(pooled, pair, grid, ties)
        pairs[pair] = {
            "per_run": {str(run): {key: row[key] for key in
                                   ("first_ahead_n", "sustained_from_n", "ahead_ns")}
                        for run, row in table.items()},
            "first_ahead_min": first_min,
            "first_ahead_max": first_max,
            "sustained_from_min": sustained_min,
            "sustained_from_max": sustained_max,
            "pooled_first_ahead_n": whole["first_ahead_n"],
            "pooled_sustained_from_n": whole["sustained_from_n"],
            "pooled_ahead_ns": whole["ahead_ns"],
            # all() on null-free runs only: a run with no crossover cannot make the pair stable.
            "stable": (None not in first and len(set(first)) == 1
                       and all(a == b for a, b in zip(first, sustained))),
            "first_ahead_grid_steps": steps(grid, first_min, first_max),
            "sustained_from_grid_steps": steps(grid, sustained_min, sustained_max),
            "runs_with_null_first_ahead": first.count(None),
            "runs_with_null_sustained_from": sustained.count(None),
        }

    earlier = {}
    earlier_ties = []
    for run, cells in sorted(superseded.items()):
        medians = medians_of(cells)
        results = {pair: crossover(medians, pair, superseded_grid, earlier_ties)
                   for pair in PAIRS}
        earlier[str(run)] = {
            "pairs": {pair: {"first_ahead_n": row["first_ahead_n"],
                             "sustained_from_n": row["sustained_from_n"]}
                      for pair, row in results.items()},
            "copy_ahead_ns": results["copy"]["ahead_ns"],
        }

    base = {"n_current_runs": len(current), "pairs": pairs, "superseded": earlier}
    below, above = (grid[grid.index(SPEC_CUTOFF) + d] for d in (-1, 1))
    readings = {
        "spec_n_le_256": ("Spec as written: median and lo/hi both on n <= 256.",
                          SPEC_CUTOFF, SPEC_CUTOFF),
        "lohi_all_grid": ("Median on n <= 256; lo/hi on every grid n, since the prose "
                          "'individual sizes within a run' states no restriction.",
                          SPEC_CUTOFF, grid[-1]),
        f"small_n_le_{below}": ("'Small sizes' taken one grid step below the provenance "
                                "cutoff, for median and lo/hi.", below, below),
        f"small_n_le_{above}": ("'Small sizes' taken one grid step above the provenance "
                                "cutoff, for median and lo/hi.", above, above),
    }
    result = {
        "readings": {
            name: {"reading": text, **base,
                   **launch_fields(per_run, pooled, grid, pooled_cutoff, lohi_cutoff)}
            for name, (text, pooled_cutoff, lohi_cutoff) in readings.items()
        },
        "checks": {
            "grid": grid,
            "rows_per_current_run": {str(r): sum(map(len, c.values())) for r, c in current.items()},
            "rows_per_superseded_run": {str(r): sum(map(len, c.values()))
                                        for r, c in superseded.items()},
            "rows_per_pooled_cell": sorted({len(v) for v in pooled_rows.values()}),
            "dropped_rows": len(drops),
            "drops": drops,
            "exact_ties_current": ties,
            "exact_ties_superseded": earlier_ties,
            "input_sha256": {
                str(path.relative_to(HERE)): sha256(path)
                for directory in (RAW, SUPERSEDED) for _, path in run_files(directory)},
        },
    }
    (HERE / "result.json").write_text(json.dumps(result, indent=1) + "\n")


if __name__ == "__main__":
    main()
