#!/usr/bin/env python3
"""Spec 12: shuttle totals, first-seen names, shipment classes. Writes result.json."""
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "inputs/book/contents/chapters/12-ecosystem/data/tinytapeout-receipts"
CATALOG = RAW / "chips_index_7a575614d5.md"
STATS = RAW / "submission-stats_2026-11-02.json"
CHIP_TT03 = RAW / "chip_page_tt03_2026-11-02.html"
FETCH_LOG = RAW / "index-fetch-log_2026-11-02.json"
INDEX_RE = re.compile(r"shuttle_index_(.+)_2026-11-02\.json$")
# The prose names an August 2026 snapshot; used only to flag rows, never in a total.
SNAPSHOT_MONTH_START = "2026-08-01"


def parse_catalog():
    """Rows of the table under '### Current chips', top to bottom."""
    lines = CATALOG.read_text(encoding="utf-8").splitlines()
    start = lines.index("### Current chips")
    rows, header = [], None
    for line in lines[start + 1:]:
        if line.startswith("###"):
            break
        if not line.startswith("|"):
            if header:
                break
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if set("".join(cells)) <= {"-"}:
            continue
        if len(cells) != len(header):
            raise ValueError(f"cell count {len(cells)} in row: {line}")
        rows.append(dict(zip(header, cells)))
    expected = ["Run", "Launched", "Closed", "Shuttle", "Designs",
                "Chips expected", "Estimated delivery date"]
    if header != expected:
        raise ValueError(f"unexpected header: {header}")
    out = []
    for pos, r in enumerate(rows):
        m = re.fullmatch(r"\[([^\]]+)\]\([^)]*\)", r["Run"])
        run = m.group(1) if m else r["Run"]
        d = r["Designs"].replace("\\*", "").strip()
        out.append({
            "run": run, "slug": run.lower(), "launched": r["Launched"],
            "closed": r["Closed"], "designs_cell": r["Designs"],
            "designs": int(d) if re.fullmatch(r"\d+", d) else None,
            "delivery": r["Estimated delivery date"],
            "chips_expected": r["Chips expected"], "catalog_pos": pos,
        })
    return out


def shipment_class(cell):
    if cell.startswith("Shipped"):
        return "shipped"
    if "test shuttle" in cell:
        return "test"
    return "other"


def parse_tt03_page():
    text = CHIP_TT03.read_text(encoding="utf-8")
    found = re.findall(r"(\d+)\s+projects submitted,\s*(\d+)\s+projects added from", text)
    if len(found) != 1:
        raise ValueError(f"TT03 statistics line matched {len(found)} times")
    return int(found[0][0]), int(found[0][1])


def load_indexes():
    out = {}
    for f in sorted(RAW.glob("shuttle_index_*")):
        out[INDEX_RE.search(f.name).group(1)] = json.loads(f.read_text())["projects"]
    return out


def load_api():
    d = json.loads(STATS.read_text())
    id2slug = {s["id"]: s["slug"] for s in d["shuttles"]}
    rows = defaultdict(list)
    earliest = {}
    for s in d["submissions"]:
        slug = id2slug[s["shuttle_id"]]
        rows[slug].append(s["top_module"])
        t = s["first_submission_time"]
        if slug not in earliest or t < earliest[slug]:
            earliest[slug] = t
    deadlines = {s["slug"]: s["deadline"][:10] for s in d["shuttles"]}
    return set(id2slug.values()), dict(rows), deadlines, earliest


def strip_cross_scheme(name):
    """Same key for tt_um_X and X, and for any two names with one long Wokwi id."""
    m = re.search(r"(\d{15,})", name)
    if m:
        return "wokwi-id:" + m.group(1)
    return name[len("tt_um_"):] if name.startswith("tt_um_") else name


def run_rows(run, cfg, api_slugs, api, idx):
    """Row-level list of names for a run under a reading; None when it has no module data."""
    slug = run["slug"]
    src = cfg.get("source", "api")
    if src == "index":
        if slug not in idx:
            return None
        drop = cfg.get("index_drop_types", {"group"})
        return [p["macro"] for p in idx[slug] if p.get("type") not in drop]
    if slug in api_slugs:
        names = list(api.get(slug, []))
        if cfg.get("api_drop_subtile"):
            sub = {p["macro"] for p in idx.get(slug, []) if p.get("type") == "subtile"}
            names = [n for n in names if n not in sub]
        if cfg.get("api_add_group"):
            names += [p["macro"] for p in idx.get(slug, []) if p.get("type") == "group"]
        return names
    if slug in idx:
        return [p["macro"] for p in idx[slug] if p.get("type") != "group"]
    return None


def order_runs(plotted, cfg, api_earliest):
    key = cfg.get("order", "closed")
    if key == "closed":
        sign = 1 if cfg.get("ties") == "top_down" else -1
        return sorted(plotted, key=lambda r: (r["closed"], sign * r["catalog_pos"]))
    if key == "launched":
        return sorted(plotted, key=lambda r: (r["launched"], -r["catalog_pos"]))
    if key == "launched_ttsky26a_from_api":
        def date(r):
            if r["slug"] == "ttsky26a":
                return api_earliest["ttsky26a"][:10]
            return r["launched"]
        return sorted(plotted, key=lambda r: (date(r), -r["catalog_pos"]))
    raise ValueError(key)


def walk(plotted, cfg, api_slugs, api, idx, earliest):
    """Return first-seen results, exact and case-folded, under one reading."""
    ordered = order_runs(plotted, cfg, earliest)
    run_names = {r["slug"]: run_rows(r, cfg, api_slugs, api, idx) for r in plotted}

    exclude = set()
    org = cfg.get("exclude_organizer")
    if org:
        all_names = {n for v in run_names.values() if v for n in set(v)}
        exclude = {n for n in all_names if re.search(r"factory_test|chip_rom", n)}
        if org == "wide":
            c = Counter(n for v in run_names.values() if v for n in set(v))
            top = max(c.values())
            exclude |= {n for n, k in c.items() if k == top}

    norm = strip_cross_scheme if cfg.get("normalize") == "cross_scheme" else (lambda n: n)
    keyed = {}
    for slug, names in run_names.items():
        keyed[slug] = None if names is None else [norm(n) for n in names if n not in exclude]

    def tally(key_fn):
        seen = set()
        by_year = Counter()
        per_run = {}
        for r in ordered:
            names = keyed[r["slug"]]
            year = r["closed"][:4]
            if names is None:
                if r["slug"] != "tt01":
                    raise ValueError(f"no module data for {r['run']}")
                by_year[year] += r["designs"]
                per_run[r["run"]] = r["designs"]
                continue
            fresh_rows = [n for n in names if key_fn(n) not in seen]
            if cfg.get("count_within_run_repeats"):
                n_new = len(fresh_rows)
            else:
                n_new = len({key_fn(n) for n in fresh_rows})
            seen |= {key_fn(n) for n in names}
            by_year[year] += n_new
            per_run[r["run"]] = n_new
        return by_year, per_run

    exact, per_run = tally(lambda n: n)
    folded, _ = tally(str.casefold)
    tt09 = set(keyed["tt09"])
    ihp = set(keyed["ttihp25a"])
    return {
        "tt09_modules": len(tt09),
        "tt09_on_ttihp25a": len(tt09 & ihp),
        "tt09_on_ttihp25a_case_folded": len({n.casefold() for n in tt09} & {n.casefold() for n in ihp}),
        "new_names_by_year": dict(sorted(exact.items())),
        "new_names_by_year_case_folded": dict(sorted(folded.items())),
        "first_seen_total": sum(exact.values()),
        "first_seen_total_case_folded": sum(folded.values()),
        "order_key_used": cfg.get("order", "closed") + ("_ties_top_down" if cfg.get("ties") == "top_down" else ""),
        "new_names_by_run": per_run,
        "excluded_names": sorted(exclude),
    }


READINGS = {
    "spec_literal": {},
    "order_closed_ties_top_down": {"ties": "top_down"},
    "order_launched_as_listed": {"order": "launched"},
    "order_launched_ttsky26a_from_api": {"order": "launched_ttsky26a_from_api"},
    "source_index_nongroup": {"source": "index"},
    "source_index_no_group_no_subtile": {"source": "index", "index_drop_types": {"group", "subtile"}},
    "source_index_all_rows": {"source": "index", "index_drop_types": set()},
    "source_api_drop_subtile_names": {"api_drop_subtile": True},
    "source_api_add_group_macros": {"api_add_group": True},
    "exclude_organizer_narrow": {"exclude_organizer": "narrow"},
    "exclude_organizer_wide": {"exclude_organizer": "wide"},
    "normalize_cross_scheme": {"normalize": "cross_scheme"},
    "count_within_run_repeats": {"count_within_run_repeats": True},
}


def main():
    rows = parse_catalog()
    plotted = [r for r in rows if r["designs"] is not None]
    dropped_rows = [{"run": r["run"], "designs_cell": r["designs_cell"]}
                    for r in rows if r["designs"] is None]
    api_slugs, api, deadlines, earliest = load_api()
    idx = load_indexes()
    submitted, carried = parse_tt03_page()
    log = json.loads(FETCH_LOG.read_text())

    total = sum(r["designs"] for r in plotted)
    shipment = {c: {"runs": 0, "entries": 0} for c in ("shipped", "test", "other")}
    for r in plotted:
        c = shipment[shipment_class(r["delivery"])]
        c["runs"] += 1
        c["entries"] += r["designs"]
    shipment["shipped"]["pct"] = 100 * shipment["shipped"]["entries"] / total

    entries_by_year = Counter()
    for r in plotted:
        entries_by_year[r["closed"][:4]] += r["designs"]

    plotted_slugs = {r["slug"] for r in plotted}
    index_only = {}
    for slug, projects in sorted(idx.items()):
        if slug in plotted_slugs or not projects:
            continue
        index_only[slug] = sum(1 for p in projects if p.get("type") != "group")

    tt03 = next(r for r in plotted if r["slug"] == "tt03")
    common = {
        "n_runs": len(plotted), "total": total, "mean_per_run": total / len(plotted),
        "tt03": {"catalog_count": tt03["designs"], "carried": carried,
                 "total_with_carryover": total + carried},
        "shipment": shipment,
        "entries_by_year": dict(sorted(entries_by_year.items())),
        "last_close_date": max(r["closed"] for r in plotted),
        "index_only_runs": index_only,
        "ttcad25a_modules": index_only.get("ttcad25a"),
    }

    readings = {}
    for name, cfg in READINGS.items():
        readings[name] = {**common, **walk(plotted, cfg, api_slugs, api, idx, earliest)}

    per_run = []
    for r in plotted:
        s = r["slug"]
        proj = idx.get(s)
        per_run.append({
            "run": r["run"], "designs": r["designs"], "closed": r["closed"],
            "api_deadline": deadlines.get(s), "class": shipment_class(r["delivery"]),
            "api_rows": len(api[s]) if s in api else None,
            "api_unique": len(set(api[s])) if s in api else None,
            "index_rows": len(proj) if proj is not None else None,
            "index_nongroup_rows": sum(p.get("type") != "group" for p in proj) if proj is not None else None,
            "index_nongroup_unique": len({p["macro"] for p in proj if p.get("type") != "group"}) if proj is not None else None,
            "index_type_counts": dict(Counter(str(p.get("type")) for p in proj)) if proj is not None else None,
        })

    stale = [
        {"run": r["run"], "delivery_cell": r["delivery"]} for r in plotted
        if shipment_class(r["delivery"]) == "other"
        and re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["delivery"])
        and r["delivery"] < SNAPSHOT_MONTH_START
    ]
    no_module_data = [r["run"] for r in plotted
                      if r["slug"] not in api_slugs and r["slug"] not in idx]
    tt02m = {p["macro"]: p for p in idx["tt02"]}
    tt02r = {p["repo"] for p in idx["tt02"]}
    logged_ok = {k for k, v in log.items() if v == 200}
    plotted_api_rows = sum(len(api[s]) for s in plotted_slugs if s in api)
    all_api_rows = sum(len(v) for v in api.values())

    diagnostics = {
        "per_run": per_run,
        "catalog_rows_not_plotted": dropped_rows,
        "api_rows_on_non_plotted_runs": {s: len(v) for s, v in sorted(api.items()) if s not in plotted_slugs},
        "api_rows_total": all_api_rows,
        "api_rows_on_plotted_runs": plotted_api_rows,
        "index_group_rows_dropped": {s: sum(p.get("type") == "group" for p in v)
                                     for s, v in idx.items() if any(p.get("type") == "group" for p in v)},
        "within_run_repeat_rows_collapsed_api": {s: len(api[s]) - len(set(api[s]))
                                                  for s in plotted_slugs if s in api and len(api[s]) != len(set(api[s]))},
        "tt09_modules_by_source": {"api_unique": len(set(api["tt09"])),
                                   "index_nongroup_rows": sum(p.get("type") != "group" for p in idx["tt09"])},
        "ttcad25a_by_source": {"api_rows": len(api["ttcad25a"]),
                               "index_nongroup_rows": sum(p.get("type") != "group" for p in idx["ttcad25a"])},
        "tt03_page": {"submitted": submitted, "carried": carried},
        "tt03_index": {
            "rows": len(idx["tt03"]),
            "macros_also_on_tt02": sum(p["macro"] in tt02m for p in idx["tt03"]),
            "macros_not_on_tt02": sum(p["macro"] not in tt02m for p in idx["tt03"]),
            "repos_also_on_tt02": sum(p["repo"] in tt02r for p in idx["tt03"]),
        },
        "rows_with_past_estimate_not_marked_shipped": stale,
        "plotted_runs_without_module_data": no_module_data,
        "closed_vs_api_deadline_differs": [
            {"run": r["run"], "closed": r["closed"], "api_deadline": deadlines[r["slug"]]}
            for r in plotted if r["slug"] in deadlines and r["closed"] != deadlines[r["slug"]]],
        "ttsky26a": {"launched_cell": next(r["launched"] for r in plotted if r["slug"] == "ttsky26a"),
                     "earliest_api_submission": earliest["ttsky26a"]},
        "index_files_vs_log": {
            "logged_200_without_file": sorted(logged_ok - set(idx)),
            "files_not_logged_200": sorted(set(idx) - logged_ok),
            "logged_404": sorted(k for k, v in log.items() if v != 200),
        },
        "catalog_filename_hash_check": "see notes.md; no hash is stated in the spec",
    }

    used = [CATALOG, STATS, CHIP_TT03, FETCH_LOG] + sorted(RAW.glob("shuttle_index_*"))
    result = {
        "readings": readings,
        "diagnostics": diagnostics,
        "inputs_sha256": {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in used},
    }
    (HERE / "result.json").write_text(json.dumps(result, indent=2, sort_keys=False) + "\n")

    print(f"plotted {len(plotted)} total {total} mean {total / len(plotted)}")
    for n, r in readings.items():
        print(f"{n:38s} {r['first_seen_total']:5d} cf {r['first_seen_total_case_folded']:5d} "
              f"tt09 {r['tt09_modules']} on25a {r['tt09_on_ttihp25a']} {r['new_names_by_year']}")


if __name__ == "__main__":
    main()
