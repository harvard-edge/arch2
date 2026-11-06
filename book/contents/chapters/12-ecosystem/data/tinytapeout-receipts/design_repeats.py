#!/usr/bin/env python3
"""Check the Tiny Tapeout CSV against pinned sources and measure repeated designs.

Reads only the receipts in this folder and the chapter CSV, then writes
design-repeats-summary.json. Pass --fetch to download every receipt again first,
or --fetch-missing to download only absent ones. Live endpoints change, so a
refetch can change the results.

Module names come from the submission API where it has the run and from the
public shuttle index for TT02 and TT03, which the API omits. TT01 is absent from
both (the index returns 404, recorded in index-fetch-log_2026-11-02.json), so it
enters the estimate at its full catalog count. A module name is a proxy for a
design: a shared name does not prove identical RTL and a few repeats are
organizer macros, so the distinct counts are estimates.
"""

import csv
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSV_PATH = HERE.parent / "fig-shuttle-cost-democratization-submissions.csv"
OUT = HERE / "design-repeats-summary.json"
PIN = "7a575614d5396e8f9b279fcfc97142bffb291e14"
FAQ_DOC = "12KPutDPBst7FF0ncB1qyxErDYeATmXoQLGjRq38dfjU"
DAY = "2026-11-02"
RECEIPTS = {
    "chips_index_7a575614d5.md": "https://raw.githubusercontent.com/TinyTapeout/"
    f"tinytapeout_www/{PIN}/content/chips/_index.md",
    f"submission-stats_{DAY}.json": "https://app.tinytapeout.com/api/shuttles/submission-stats",
    f"shuttle_index_tt09_{DAY}.json": "https://index.tinytapeout.com/tt09.json",
    f"shuttle_index_ttihp25a_{DAY}.json": "https://index.tinytapeout.com/ttihp25a.json",
    f"efabless-faq_{DAY}.txt": f"https://docs.google.com/document/d/{FAQ_DOC}/export?format=txt",
}
# Index slugs tried. The index host publishes no list of runs, so the runs outside
# the catalog table are the closed ones named by the API or the FAQ or found by
# trying a name; this list can be incomplete.
OFF_TABLE_SLUGS = ["tt03p5", "ttcad25a", "ttgf0p1", "ttihp0p1", "ttihp0p3"]
CANCELLED_SLUGS = ["tt10"]
CHIP_PAGES = ["tt01", "tt03", "ttihp25a"]
for _slug in CHIP_PAGES:
    RECEIPTS[f"chip_page_{_slug}_{DAY}.html"] = f"https://tinytapeout.com/chips/{_slug}/"
FETCH_LOG = HERE / f"index-fetch-log_{DAY}.json"
COMPARED = {
    "LaunchDate": "launched",
    "CloseDate": "closed",
    "ShuttleHarness": "shuttle",
    "SubmittedDesignsCount": "designs",
    "DeliveryStatus": "delivery",
}


def index_file(slug: str) -> Path:
    return HERE / f"shuttle_index_{slug}_{DAY}.json"


def fetch_url(url: str) -> tuple:
    """Fetch through curl; the hosts refuse or stall Python's default client."""
    with tempfile.NamedTemporaryFile() as body:
        done = subprocess.run(
            ["curl", "-sL", "-m", "60", "-o", body.name, "-w", "%{http_code}", url],
            capture_output=True, text=True, check=True,
        )
        return int(done.stdout), Path(body.name).read_bytes()


def fetch(slugs: list, only_missing: bool) -> None:
    for name, url in RECEIPTS.items():
        if not (only_missing and (HERE / name).exists()):
            status, body = fetch_url(url)
            if status != 200:
                raise SystemExit(f"{url}: HTTP {status}")
            (HERE / name).write_bytes(body)
    log = {}
    for slug in slugs:
        url = f"https://index.tinytapeout.com/{slug}.json"
        if only_missing and index_file(slug).exists():
            log[slug] = 200
            continue
        status, body = fetch_url(url)
        log[slug] = status
        if status == 200:
            index_file(slug).write_bytes(body)
    FETCH_LOG.write_text(json.dumps(log, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def catalog_rows() -> dict:
    """Parse the Current chips table of the pinned site source."""
    rows = {}
    text = (HERE / "chips_index_7a575614d5.md").read_text(encoding="utf-8")
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 7:
            continue
        name = re.sub(r"^\[([^\]]+)\].*$", r"\1", cells[0])
        if not name.startswith("TT"):
            continue
        rows[name] = {
            "launched": cells[1],
            "closed": cells[2],
            "shuttle": cells[3],
            "designs": cells[4],
            "delivery": cells[6],
        }
    return rows


def compare_catalog(csv_rows: list) -> dict:
    catalog = catalog_rows()
    differences = []
    for row in csv_rows:
        source = catalog[row["RunName"]]
        for field, key in COMPARED.items():
            if row[field] != source[key]:
                differences.append(
                    {"run": row["RunName"], "field": field, "csv": row[field], "source": source[key]}
                )
    return {
        "source_commit": PIN,
        "rows_compared": len(csv_rows),
        "fields_compared": len(csv_rows) * len(COMPARED),
        "differences": differences,
    }


def load_index(slug: str) -> dict:
    return json.loads(index_file(slug).read_text(encoding="utf-8"))


def index_modules(slug: str) -> set:
    """Distinct module names on a run, without group containers."""
    projects = load_index(slug)["projects"]
    return {p["macro"] for p in projects if p.get("type") != "group"}


def chip_page_rows(slug: str) -> int:
    """Count data rows in the project table of a retained chip page."""
    html = (HERE / f"chip_page_{slug}_{DAY}.html").read_text(encoding="utf-8")
    return html.count("<tr") - 1


def tt03_counts() -> dict:
    """Read the TT03 chip page statement that explains the catalog's asterisk."""
    html = (HERE / f"chip_page_tt03_{DAY}.html").read_text(encoding="utf-8")
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    match = re.search(r"(\d+) projects submitted, (\d+) projects added from TT02", text)
    if match is None:
        raise SystemExit("TT03 chip page statement not found")
    tt02 = index_modules("tt02")
    tt03 = index_modules("tt03")
    return {
        "projects_submitted": int(match.group(1)),
        "projects_added_from_tt02": int(match.group(2)),
        "chip_page_table_rows": chip_page_rows("tt03"),
        "index_modules": len(tt03),
        "index_modules_also_on_tt02": len(tt02 & tt03),
    }


def compare_all_indexes(csv_rows: list, log: dict) -> dict:
    differs = {}
    missing = []
    for row in csv_rows:
        slug = row["RunName"].lower()
        if log.get(slug) != 200:
            missing.append({"run": row["RunName"], "index_http_status": log.get(slug)})
            continue
        count = len(index_modules(slug))
        if count != int(row["SubmittedDesignsCount"]):
            differs[row["RunName"]] = {"catalog": int(row["SubmittedDesignsCount"]), "index": count}
    off_table = {s: len(index_modules(s)) for s in OFF_TABLE_SLUGS if log.get(s) == 200}
    return {
        "index_differs_from_catalog": differs,
        "plotted_runs_without_index": missing,
        "cancelled_runs_index_status": {s: log.get(s) for s in CANCELLED_SLUGS},
        "indexed_runs_outside_catalog_table": off_table,
        "indexed_runs_outside_catalog_table_count": len(off_table),
        "ttihp25a_chip_page_table_rows": chip_page_rows("ttihp25a"),
    }


def compare_indexes() -> dict:
    tt09 = load_index("tt09")
    ihp = load_index("ttihp25a")
    tt09_by_macro = {p["macro"]: p for p in tt09["projects"]}
    ihp_by_macro = {p["macro"]: p for p in ihp["projects"]}
    shared = set(tt09_by_macro) & set(ihp_by_macro)
    groups = {p["macro"] for p in ihp["projects"] if p.get("type") == "group"}
    types = Counter(str(p.get("type")) for p in ihp["projects"])
    return {
        "tt09_modules": len(tt09_by_macro),
        "tt09_modules_on_ttihp25a": len(shared),
        "same_repository": sum(tt09_by_macro[m]["repo"] == ihp_by_macro[m]["repo"] for m in shared),
        "same_commit": sum(tt09_by_macro[m]["commit"] == ihp_by_macro[m]["commit"] for m in shared),
        "ttihp25a_index_rows": len(ihp["projects"]),
        "ttihp25a_distinct_modules": len(ihp_by_macro),
        "ttihp25a_group_containers": len(groups),
        "ttihp25a_distinct_modules_without_groups": len(set(ihp_by_macro) - groups),
        "ttihp25a_type_counts": dict(sorted(types.items())),
    }


def repeats(csv_rows: list) -> dict:
    stats = json.loads((HERE / f"submission-stats_{DAY}.json").read_text(encoding="utf-8"))
    slug = {s["id"]: s["slug"] for s in stats["shuttles"]}
    modules = {}
    rows_per_run = Counter()
    for sub in stats["submissions"]:
        name = slug[sub["shuttle_id"]]
        modules.setdefault(name, set()).add(sub["top_module"])
        rows_per_run[name] += 1

    for run in ("tt02", "tt03"):
        modules[run] = index_modules(run)
        rows_per_run[run] = len(modules[run])

    ordered = sorted(csv_rows, key=lambda r: r["CloseDate"])
    covered = [r for r in ordered if r["RunName"].lower() in modules]
    uncovered = [r for r in ordered if r["RunName"].lower() not in modules]

    def first_seen(extra: tuple) -> dict:
        seen = set()
        by_year = Counter()
        for row in uncovered:
            by_year[row["CloseDate"][:4]] += int(row["SubmittedDesignsCount"])
        sequence = [(r["CloseDate"], r["RunName"].lower()) for r in covered] + list(extra)
        for closed, name in sorted(sequence):
            new = modules[name] - seen
            seen |= modules[name]
            by_year[closed[:4]] += len(new)
        return {"distinct_modules": len(seen), "by_close_year": dict(sorted(by_year.items()))}

    raw_by_year = Counter()
    for row in ordered:
        raw_by_year[row["CloseDate"][:4]] += int(row["SubmittedDesignsCount"])
    plotted = first_seen(())
    with_cad = first_seen((("2025-06-10", "ttcad25a"),))
    uncovered_designs = sum(int(r["SubmittedDesignsCount"]) for r in uncovered)
    module_rows = sum(rows_per_run[r["RunName"].lower()] for r in covered)
    zero_tile = sum(
        s["tile_count"] == 0 and slug[s["shuttle_id"]] == "ttihp25a" for s in stats["submissions"]
    )
    return {
        "runs_with_module_data": len(covered),
        "runs_without_module_data": [r["RunName"] for r in uncovered],
        "designs_on_runs_without_module_data": uncovered_designs,
        "module_data_source": "submission API; shuttle index for TT02 and TT03",
        "module_rows_on_plotted_runs": module_rows,
        "distinct_modules_on_plotted_runs": plotted["distinct_modules"],
        "repeat_rows_percent": round(100 * (1 - plotted["distinct_modules"] / module_rows), 1),
        "estimated_distinct_designs": plotted["distinct_modules"] + uncovered_designs,
        "raw_by_close_year": dict(sorted(raw_by_year.items())),
        "first_seen_by_close_year": plotted["by_close_year"],
        "last_close_date": ordered[-1]["CloseDate"],
        "first_seen_by_close_year_with_ttcad25a": with_cad["by_close_year"],
        "ttcad25a_api_rows": rows_per_run["ttcad25a"],
        "ttihp25a_api_rows_with_tile_count_zero": zero_tile,
        "api_differs_from_catalog": {
            r["RunName"]: {
                "catalog": int(r["SubmittedDesignsCount"]),
                "api": rows_per_run[r["RunName"].lower()],
            }
            for r in covered
            if r["RunName"] not in ("TT02", "TT03")
            and rows_per_run[r["RunName"].lower()] != int(r["SubmittedDesignsCount"])
        },
    }


def main() -> None:
    with open(CSV_PATH, encoding="utf-8") as f:
        csv_rows = list(csv.DictReader(line for line in f if not line.startswith("#")))
    slugs = [r["RunName"].lower() for r in csv_rows] + CANCELLED_SLUGS + OFF_TABLE_SLUGS
    if "--fetch" in sys.argv[1:] or "--fetch-missing" in sys.argv[1:]:
        fetch(slugs, "--fetch" not in sys.argv[1:])
    log = json.loads(FETCH_LOG.read_text(encoding="utf-8"))
    indexes = sorted(HERE.glob(f"shuttle_index_*_{DAY}.json"))
    summary = {
        "generated_on": str(date.today()),
        "receipts_sha256": {
            n: hashlib.sha256((HERE / n).read_bytes()).hexdigest()
            for n in sorted({*RECEIPTS, *(i.name for i in indexes), FETCH_LOG.name})
        },
        "catalog_check": compare_catalog(csv_rows),
        "tt03_counts": tt03_counts(),
        "index_comparison": compare_indexes(),
        "index_coverage": compare_all_indexes(csv_rows, log),
        "repeats": repeats(csv_rows),
    }
    OUT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in summary if k != "receipts_sha256"}, indent=2))


if __name__ == "__main__":
    main()
