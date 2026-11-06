#!/usr/bin/env python3
"""Break the first-seen module-name count down by run and test its year bins.

Reads the receipts in this folder and the chapter CSV, applies the same rule as
design_repeats.py (submission API names, shuttle index for TT02 and TT03, TT01 at
its full catalog count, runs taken in closing-date order), and writes
new-name-readings.json. Module names are a proxy for design identity, so these
are estimates. The script fails if its yearly counts differ from
design-repeats-summary.json, and it also counts the older user_module_<id> names
that design_identity_sensitivity.py leaves out of its Wokwi count. Whether those
names are Wokwi-generated is an assumption. A year shifted by n months runs from
month n + 1 of one calendar year to month n of the next.
"""

import csv
import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSV_PATH = HERE.parent / "fig-shuttle-cost-democratization-submissions.csv"
OUT = HERE / "new-name-readings.json"
DAY = "2026-11-02"
SHIFTS = range(0, 7)


def plotted_rows() -> list:
    lines = [ln for ln in CSV_PATH.read_text(encoding="utf-8").splitlines() if not ln.startswith("#")]
    return sorted(csv.DictReader(lines), key=lambda r: r["CloseDate"])


def run_modules() -> dict:
    stats = json.loads((HERE / f"submission-stats_{DAY}.json").read_text(encoding="utf-8"))
    slug = {s["id"]: s["slug"] for s in stats["shuttles"]}
    modules = {}
    for sub in stats["submissions"]:
        modules.setdefault(slug[sub["shuttle_id"]], set()).add(sub["top_module"])
    for run in ("tt02", "tt03"):
        index = json.loads((HERE / f"shuttle_index_{run}_{DAY}.json").read_text(encoding="utf-8"))
        modules[run] = {p["macro"] for p in index["projects"]}
    return modules


def shifted_year(close_date: str, months: int) -> str:
    year, month = int(close_date[:4]), int(close_date[5:7])
    return str(year if month > months else year - 1)


def main() -> None:
    rows, modules = plotted_rows(), run_modules()
    seen = set()
    per_run = []
    for row in rows:
        name = row["RunName"].lower()
        if name in modules:
            new = len(modules[name] - seen)
            seen |= modules[name]
        else:
            new = int(row["SubmittedDesignsCount"])
        per_run.append({"run": row["RunName"], "closed": row["CloseDate"],
                        "entries": int(row["SubmittedDesignsCount"]), "new_names": new})

    by_year = Counter()
    for item in per_run:
        by_year[item["closed"][:4]] += item["new_names"]
    summary = json.loads((HERE / "design-repeats-summary.json").read_text(encoding="utf-8"))
    if dict(by_year) != summary["repeats"]["first_seen_by_close_year"]:
        raise SystemExit("yearly counts differ from design-repeats-summary.json")

    shifted = {}
    for months in SHIFTS:
        bins = Counter()
        for item in per_run:
            bins[shifted_year(item["closed"], months)] += item["new_names"]
        shifted[str(months)] = dict(sorted(bins.items()))

    every_name = set().union(*modules.values())
    plotted = [modules[r["RunName"].lower()] for r in rows if r["RunName"].lower() in modules]
    names = set().union(*plotted)
    wokwi = {n for n in names if re.match(r"^tt_um_wokwi_\d+", n)}
    older = {n for n in names if re.match(r"^user_module_\d+", n)}

    ihp = next(i for i in per_run if i["run"] == "TTIHP25a")
    OUT.write_text(json.dumps({
        "generated_on": DAY,
        "per_run": per_run,
        "ttihp25a": ihp,
        "by_close_year": dict(sorted(by_year.items())),
        "by_year_shifted_months": shifted,
        "wokwi_names_on_plotted_runs": len(wokwi),
        "older_user_module_names_on_plotted_runs": len(older),
        "all_runs_names_including_unplotted": len(every_name),
    }, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
