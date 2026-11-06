#!/usr/bin/env python3
"""Spec 06 reimplementation. Reads only inputs/ next to this file; writes result.json."""
import calendar
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

import fitz

HERE = Path(__file__).resolve().parent
ST = HERE / "inputs/data/studies"
ERRATA = ST / "13-errata-dispositions/raw/errata.csv"
PDFDIR = ST / "13-errata-dispositions/raw/pdf"
LAUNCH = ST / "18-errata-by-year/launch_years.csv"
PAGES = ST / "19-errata-history/source_pages/revision_history_pages.json"

# Document mapping, from the spec.
DOCS = {
    "BroadwellEP.pdf": "Broadwell-EP",
    "IceLakeSP.pdf": "Ice Lake-SP",
    "Zen1Naples.pdf": "Zen 1 (Naples)",
    "Zen5Turin.pdf": "Zen 5 (Turin)",
}
MONTHS = {m: i for i, m in enumerate(calendar.month_name) if m}
DATE = r"(?:%s) \d{4}" % "|".join(MONTHS)
ID = r"(?:[A-Z]{2,4}\d+|#\d+)"
VERB = re.compile(r"\b(Added|Removed|Updated|Modified)\b")
RANGE = re.compile(rf"({ID})\.?\s*(?:to|through|-|–|—)\s*({ID})\.?")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def strip_footer(desc):
    """Cut page furniture that follows the last row of a table."""
    cut = re.search(
        r"(^\d{5}\s+Rev|^Revision Guide for AMD|^\s*Revision History\s*$|^§)",
        desc, re.M)
    return desc[: cut.start()] if cut else desc


def parse_rows(text):
    """Return rows as dicts. Handles the two column orders in these documents."""
    rows = []
    # Date-first order: Date / Revision / Description (Intel Ice Lake, AMD).
    heads = list(re.finditer(rf"^({DATE})\s*\n\s*(\d{{3}}US|\d+\.\d\d)\s*$", text, re.M))
    if heads:
        for i, m in enumerate(heads):
            end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
            rows.append({"date_text": m.group(1), "revision": m.group(2),
                         "description": strip_footer(text[m.end():end])})
        return rows
    # Revision-first order: Revision / Description / Date (Broadwell).
    heads = list(re.finditer(r"^(\d{3})\s*$", text, re.M))
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        lines = [ln.strip() for ln in text[m.end():end].splitlines() if ln.strip()]
        if not re.fullmatch(DATE, lines[-1]):
            raise ValueError(f"row {m.group(1)}: last line is not a date: {lines[-1]!r}")
        rows.append({"date_text": lines[-1], "revision": m.group(1),
                     "description": "\n".join(lines[:-1])})
    return rows


def expand(a, b):
    pa, na = re.fullmatch(r"([A-Z]+|#)(\d+)", a).groups()
    pb, nb = re.fullmatch(r"([A-Z]+|#)(\d+)", b).groups()
    if pa != pb or int(nb) < int(na):
        raise ValueError(f"bad range {a}..{b}")
    return [f"{pa}{n}" for n in range(int(na), int(nb) + 1)]


def added_ids(description, log):
    """IDs named in Added clauses of one row, in order."""
    flat = re.sub(r"\s+", " ", description.replace("•", " ")).strip()
    starts = [m.start() for m in VERB.finditer(flat)]
    out = []
    for i, s in enumerate(starts):
        clause = flat[s: starts[i + 1] if i + 1 < len(starts) else len(flat)]
        verb = VERB.match(clause).group(1)
        log["clauses_" + verb] += 1
        if verb != "Added":
            continue
        clause = clause.split("duplicate of")[0]
        ids = []
        pos = 0
        for m in RANGE.finditer(clause):
            ids += re.findall(ID, clause[pos:m.start()])
            ids += expand(m.group(1), m.group(2))
            pos = m.end()
        ids += re.findall(ID, clause[pos:])
        if not ids:
            log["added_clauses_without_identifier"] += 1
            log["added_clauses_without_identifier_text"].append(clause.strip())
        out += ids
    return out


def row_date(t):
    mon, yr = t.split()
    return int(yr), MONTHS[mon]


def load_history():
    pages = json.loads(PAGES.read_text())
    if set(pages) != set(DOCS):
        raise ValueError(f"unexpected documents {sorted(pages)}")
    log = defaultdict(int)
    log["added_clauses_without_identifier_text"] = []
    hist, checks = {}, {}
    for pdf, doc in DOCS.items():
        p = pages[pdf]
        rows = parse_rows(p["extracted_text"])
        for r in rows:
            r["year"], r["month"] = row_date(r["date_text"])
            r["initial"] = bool(re.search(r"initial\s+(public\s+)?release", r["description"], re.I))
            r["added"] = [] if r["initial"] else added_ids(r["description"], log)
        hist[doc] = rows
        # Check page text against the PDF by two separate extractors.
        pno = p["pdf_page_1based"]
        with fitz.open(PDFDIR / pdf) as d:
            mu = d[pno - 1].get_text()
        lay = subprocess.run(["pdftotext", "-layout", "-f", str(pno), "-l", str(pno),
                              str(PDFDIR / pdf), "-"],
                             capture_output=True, text=True, check=True).stdout
        norm = lambda s: re.sub(r"\s+", "", s)
        tok = lambda s: Counter(re.findall(rf"{ID}|\d{{3}}US|\b\d\.\d\d\b|{DATE}", s))
        layrows = parse_layout_check(lay)
        checks[doc] = {
            "pdf_page_1based": pno,
            "pymupdf_text_equal_after_whitespace": norm(mu) == norm(p["extracted_text"]),
            "pdftotext_token_multiset_equal": tok(lay) == tok(p["extracted_text"]),
            "pdftotext_date_rev_pairs_equal_parsed": layrows == {(r["date_text"], r["revision"]) for r in rows},
        }
    return hist, checks, log


def parse_layout_check(lay):
    """Rows read from pdftotext -layout: revision and date tokens grouped in table order."""
    body = lay.split("Revision History", 1)[1]
    body = re.split(r"^\s*(?:\d+\s+3rd Gen|\d{5}\s+Revision:|\d\s+Intel|§)|Revision History\s+\d", body, maxsplit=1, flags=re.M)[0]
    dates = re.findall(rf"\b{DATE}\b", body)
    revs = re.findall(r"(?<![\d.#A-Z])(\d{3}US|\d{3}|\d\.\d\d)(?![\d.])", body)
    if len(dates) != len(revs):
        raise ValueError(f"layout check: {len(dates)} dates vs {len(revs)} revisions")
    return set(zip(dates, revs))


def corpus(launch):
    with ERRATA.open(newline="") as f:
        rows = list(csv.DictReader(f))
    fams = Counter(r["family"] for r in rows)
    fam_vendor = defaultdict(set)
    for r in rows:
        fam_vendor[r["family"]].add(r["vendor"])
    multi = {k: sorted(v) for k, v in fam_vendor.items() if len(v) != 1}
    if multi:
        raise ValueError(f"family with several vendors {multi}")
    vendor = defaultdict(lambda: {"families": 0, "rows": 0})
    for fam, n in fams.items():
        v = next(iter(fam_vendor[fam]))
        vendor[v]["families"] += 1
        vendor[v]["rows"] += n
    missing = sorted(set(fams) - set(launch))
    years = [int(launch[f]["launch_year"]) for f in fams if f in launch]
    keys = Counter((r["family"], r["erratum_id"]) for r in rows)
    return {
        "rows": len(rows),
        "distinct_family_id": len(keys),
        "families": len(fams),
        "vendor": dict(sorted(vendor.items())),
        "by_family": dict(sorted(fams.items())),
        "launch_year_min": min(years),
        "launch_year_max": max(years),
    }, {
        "families_without_launch_row": missing,
        "launch_rows_not_in_corpus": sorted(set(launch) - set(fams)),
        "duplicate_family_id_keys": {f"{k[0]}|{k[1]}": v for k, v in keys.items() if v > 1},
        "status_values": dict(Counter(r["status"] for r in rows)),
        "blank_erratum_id_rows": sum(1 for r in rows if not r["erratum_id"].strip()),
        "doc_revisions": sorted({(r["family"], r["doc_number"], r["revision"]) for r in rows}),
        "id_set": {f: {r["erratum_id"] for r in rows if r["family"] == f} for f in DOCS.values()},
    }


def reach(launch_date, y, m):
    """Does a row dated month m of year y reach launch + 2 years, at the month's first and last day?"""
    if not launch_date:
        return None, None
    d = date.fromisoformat(launch_date)
    anniv = date(d.year + 2, d.month, d.day)
    return date(y, m, 1) >= anniv, date(y, m, calendar.monthrange(y, m)[1]) >= anniv


def build(hist, launch, corp, keep):
    docs, n_rows, gap = {}, 0, 0
    n_year = n_ds = n_de = 0
    for doc, all_rows in hist.items():
        rows = [r for r in all_rows if keep(r)]
        added = [i for r in rows for i in r["added"]]
        years = sorted({r["year"] for r in rows})
        annual = {}
        for y in years:
            yr = [r for r in rows if r["year"] == y]
            ids = [i for r in yr for i in r["added"]]
            annual[str(y)] = {"rows": len(yr), "added": len(ids), "added_distinct": len(set(ids))}
        with_add = [r for r in rows if r["added"]]
        last = max(with_add, key=lambda r: (r["year"], r["month"]))
        ly = int(launch[doc]["launch_year"])
        ld = launch[doc]["launch_date"]
        by_year = last["year"] - ly >= 2
        ds, de = reach(ld, last["year"], last["month"])
        missing = [y for y in range(years[0], years[-1] + 1) if y not in years]
        docs[doc] = {
            "n_rows": len(rows), "added_total": len(added), "added_distinct": len(set(added)),
            "first_year": years[0], "last_year": years[-1],
            "launch_year": ly, "launch_date": ld,
            "last_addition_year": last["year"],
            "last_addition_row": last["date_text"],
            "continues_two_years_by_year": by_year,
            "continues_two_years_by_date": ds if ds == de else None,
            "by_date_row_at_month_start": ds, "by_date_row_at_month_end": de,
            "years_without_rows": missing, "annual": annual,
        }
        n_rows += len(rows)
        gap += len(missing)
        n_year += by_year
        n_ds += bool(ds)
        n_de += bool(de)
    ice = [r for r in hist["Ice Lake-SP"] if keep(r) and r["year"] == 2026]
    ice_last = max(ice, key=lambda r: r["month"])
    fam17 = [Decimal(r["revision"]) for r in hist["Zen 1 (Naples)"]]
    return {
        "corpus": corp,
        "history": {"n_rows": n_rows, "n_documents": len(docs),
                    "years_without_rows_total": gap, "documents": docs},
        "n_continuing": n_year,
        "n_continuing_by_date_month_start": n_ds,
        "n_continuing_by_date_month_end": n_de,
        "icelake_2026": {"added": sum(len(r["added"]) for r in ice),
                         "through_month": ice_last["date_text"].split()[0],
                         "through_date_text": ice_last["date_text"]},
        "turin_addition_years": sorted({r["year"] for r in hist["Zen 5 (Turin)"] if r["added"] and keep(r)}),
        "family17h_revisions": {
            "listed": len(set(fam17)),
            "span": int((max(fam17) - min(fam17)) / Decimal("0.01")) + 1,
            "lowest": str(min(fam17)), "highest": str(max(fam17))},
    }


def main():
    with LAUNCH.open(newline="") as f:
        launch = {r["family"]: r for r in csv.DictReader(f)}
    for r in launch.values():
        if r["launch_date"] and int(r["launch_date"][:4]) != int(r["launch_year"]):
            raise ValueError(f"launch year/date mismatch {r['family']}")
    hist, checks, log = load_history()
    corp, cdiag = corpus(launch)
    id_set = cdiag.pop("id_set")
    readings = {
        "rows_all_listed": build(hist, launch, corp, lambda r: True),
        "rows_post_initial": build(hist, launch, corp, lambda r: not r["initial"]),
        "rows_with_additions": build(hist, launch, corp, lambda r: bool(r["added"])),
    }
    diag = {
        "pdf_checks": checks,
        "clause_log": dict(log),
        "corpus_diagnostics": cdiag,
        "rows_by_document": {d: [{k: r[k] for k in ("date_text", "revision", "initial")}
                                 | {"added_n": len(r["added"]), "added_first": r["added"][:1], "added_last": r["added"][-1:]}
                                 for r in rows] for d, rows in hist.items()},
        "ids_added_more_than_once": {d: {k: v for k, v in Counter(i for r in rows for i in r["added"]).items() if v > 1}
                                     for d, rows in hist.items()},
        "added_ids_absent_from_errata_csv": {
            d: sorted({i for r in rows for i in r["added"]} - id_set[d]
                      - {x.lstrip("#") for x in id_set[d]}
                      - {"#" + x for x in id_set[d]}) for d, rows in hist.items()},
        "input_sha256": {str(p.relative_to(HERE)): sha(p) for p in
                         [ERRATA, LAUNCH, PAGES] + [PDFDIR / n for n in DOCS]},
    }
    (HERE / "result.json").write_text(json.dumps({"readings": readings, "diagnostics": diag},
                                                 indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
