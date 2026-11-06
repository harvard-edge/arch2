#!/usr/bin/env python3
"""Recount first-seen Tiny Tapeout designs under other design-identity keys.

design_repeats.py counts each module name once. This script asks how far that
estimate moves when another key stands in for design identity. It reads the
shuttle index receipts, which give a module and its repository on every plotted
run except TT01, and writes design-identity-sensitivity.json. TT01 enters at its
full catalog count, as in design_repeats.py, and group containers are left out.

The index and the submission API differ by a row here and there, so the name key
here can differ slightly from the estimate in design-repeats-summary.json.
"""

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSV_PATH = HERE.parent / "fig-shuttle-cost-democratization-submissions.csv"
OUT = HERE / "design-identity-sensitivity.json"
DAY = "2026-11-02"
# Names built from a Wokwi project number, as opposed to chosen by the designer.
WOKWI_NAME = re.compile(r"^tt_um_wokwi_\d+")
OWNER = re.compile(r"github\.com[/:]([^/]+)")


def repository(project: dict) -> str:
    return project["repo"].rstrip("/").removesuffix(".git").lower()


KEYS = {
    "module_name": lambda p: p["macro"],
    "module_name_without_tt_um_prefix": lambda p: p["macro"].removeprefix("tt_um_"),
    "repository": repository,
}


def main() -> None:
    with open(CSV_PATH, encoding="utf-8") as f:
        runs = list(csv.DictReader(line for line in f if not line.startswith("#")))
    runs.sort(key=lambda r: r["CloseDate"])
    projects = {}
    for run in runs:
        slug = run["RunName"].lower()
        path = HERE / f"shuttle_index_{slug}_{DAY}.json"
        if path.exists():
            listed = json.loads(path.read_text(encoding="utf-8"))["projects"]
            projects[slug] = [p for p in listed if p.get("type") != "group"]

    counts = {}
    for name, key in KEYS.items():
        seen = set()
        by_year = Counter()
        for run in runs:
            slug = run["RunName"].lower()
            year = run["CloseDate"][:4]
            if slug not in projects:
                by_year[year] += int(run["SubmittedDesignsCount"])
                continue
            new = {key(p) for p in projects[slug]} - seen
            seen |= new
            by_year[year] += len(new)
        counts[name] = {
            "estimated_distinct_designs": sum(by_year.values()),
            "by_close_year": dict(sorted(by_year.items())),
            "dip_in_2025_and_high_in_2026": by_year["2025"] < by_year["2024"]
            and by_year["2026"] == max(by_year.values()),
        }

    owners = defaultdict(set)
    for listed in projects.values():
        for p in listed:
            match = OWNER.search(repository(p))
            if not match:
                raise SystemExit(f"no GitHub owner in {p['repo']!r}")
            owners[p["macro"]].add(match.group(1))
    base = counts["module_name"]["estimated_distinct_designs"]
    high = counts["repository"]["estimated_distinct_designs"]
    summary = {
        "runs_with_index": len(projects),
        "runs_without_index": [r["RunName"] for r in runs if r["RunName"].lower() not in projects],
        "keys": counts,
        "repository_over_module_name_percent": round(100 * (high / base - 1), 1),
        "module_names_with_more_than_one_owner": sum(len(v) > 1 for v in owners.values()),
        "distinct_generated_wokwi_names": sum(bool(WOKWI_NAME.match(n)) for n in owners),
    }
    OUT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
