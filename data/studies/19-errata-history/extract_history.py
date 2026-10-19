#!/usr/bin/env python3
"""Extract and audit explicit erratum-ID changes in four frozen revision histories.

Run from the repository root. Source PDFs and the manifest are read-only inputs
from study 13; all outputs are confined to study 19.
"""
from __future__ import annotations
import csv, hashlib, json, re
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data/studies/19-errata-history"
SOURCE = ROOT / "data/studies/13-errata-dispositions"
MANIFEST_PATH = SOURCE / "source_manifest.json"
FAMILY_CONFIG = {
    "BroadwellEP.pdf": {
        "family": "Broadwell-EP",
        "page": 4,
        "prefix": "BDF",
        "coverage": "May 2015–April 2022 (publisher-stated; first date ambiguous)",
    },
    "IceLakeSP.pdf": {
        "family": "Ice Lake-SP",
        "page": 4,
        "prefix": "ICX",
        "coverage": "July 2021–March 2026 (revision-history rows)",
    },
    "Zen1Naples.pdf": {
        "family": "Zen 1 (Naples)",
        "page": 5,
        "prefix": "#",
        "coverage": "June 2018–August 2023 (listed rows; version-number gaps)",
    },
    "Zen5Turin.pdf": {
        "family": "Zen 5 (Turin)",
        "page": 4,
        "prefix": "#",
        "coverage": "January–July 2025 (revision-history rows)",
    },
}
EXPECTED_ROW_COUNTS = {
    "BroadwellEP.pdf": 8,
    "IceLakeSP.pdf": 24,
    "Zen1Naples.pdf": 4,
    "Zen5Turin.pdf": 4,
}
MONTHS = {
    m: i
    for i, m in enumerate(
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
        1,
    )
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def date_parts(s):
    m = re.fullmatch(r"([A-Z][a-z]+) (\d{4})", s)
    if not m or m.group(1) not in MONTHS:
        raise ValueError(f"bad date {s!r}")
    return int(m.group(2)), MONTHS[m.group(1)]


def id_token(prefix, n):
    return f"{prefix}{int(n)}" if prefix != "#" else str(int(n))


def identifiers_in_clause(clause, prefix):
    """Parse explicit IDs and explicit inclusive ranges within one action clause."""
    # Replace known inclusive range spellings with their expanded IDs first.
    ranges = []
    pat = re.compile(
        r"(?P<a>(?:BDF|ICX)\d+|#\s*\d+)\.?\s*(?:-|to|through)\s*(?P<b>(?:BDF|ICX)\d+|#\s*\d+)\.?",
        re.I,
    )

    def expand(m):
        def parts(s):
            q = re.search(r"\d+", s)
            return int(q.group()), s.lstrip().startswith("#")

        a, ah = parts(m.group("a"))
        b, bh = parts(m.group("b"))
        if ah != bh or (
            not ah
            and re.sub(r"\d+", "", m.group("a")).upper()
            != re.sub(r"\d+", "", m.group("b")).upper()
        ):
            return m.group(0)
        if b < a:
            raise ValueError(f"descending range: {m.group(0)}")
        prefix0 = "#" if ah else re.sub(r"\d+", "", m.group("a")).upper()
        vals = [id_token(prefix0, x) for x in range(a, b + 1)]
        ranges.extend(vals)
        return " ".join(vals)

    replaced = pat.sub(expand, clause)
    toks = []
    for m in re.finditer(r"\bBDF\s*\d+\b|\bICX\s*\d+\b|#\s*\d+", replaced, re.I):
        token = m.group(0)
        p = "#" if token.lstrip().startswith("#") else re.sub(r"\d+", "", token).upper()
        n = int(re.search(r"\d+", token).group())
        if (prefix == "#" and p == "#") or (prefix != "#" and p == prefix):
            toks.append(id_token(prefix, n))
    return list(dict.fromkeys(toks))


def parse_actions(description, prefix):
    # Source cells use bullets, semicolons, and line wrapping inconsistently.
    # Segment at each explicit action verb so wrapped text remains attached
    # while update/removal IDs cannot leak into the preceding Added clause.
    adds = []
    removes = []
    updates = []
    flags = []
    marks = list(re.finditer(r"(?i)\b(Added|Removed|Updated|Modified)\b", description))
    for i, m in enumerate(marks):
        verb = m.group(1).lower()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(description)
        body = description[m.end() : end]
        # In "Removed X. duplicate of Y", Y is a cross-reference to the
        # surviving duplicate, not a second removal.
        id_body = body.split("duplicate of", 1)[0] if verb == "removed" else body
        ids = identifiers_in_clause(id_body, prefix)
        if verb == "added":
            adds.extend(ids)
        elif verb == "removed":
            removes.extend(ids)
        else:
            updates.extend(ids)
    return (
        list(dict.fromkeys(adds)),
        list(dict.fromkeys(removes)),
        list(dict.fromkeys(updates)),
    )


def audit_ranges(description, prefix):
    pattern = re.compile(
        r"(?P<a>(?:BDF|ICX)\d+|#\s*\d+)\.?\s*(?:-|to|through)\s*(?P<b>(?:BDF|ICX)\d+|#\s*\d+)\.?",
        re.I,
    )
    rows = []
    for m in pattern.finditer(description):
        a, b = m.group("a"), m.group("b")
        pa = "#" if a.lstrip().startswith("#") else re.sub(r"\d+", "", a).upper()
        pb = "#" if b.lstrip().startswith("#") else re.sub(r"\d+", "", b).upper()
        na, nb = int(re.search(r"\d+", a).group()), int(re.search(r"\d+", b).group())
        if pa != pb or pa != prefix or nb < na:
            raise ValueError(f"invalid range expression {m.group(0)!r}")
        ids = [id_token(prefix, n) for n in range(na, nb + 1)]
        rows.append(
            {
                "range_expression": m.group(0),
                "first_id": id_token(prefix, na),
                "last_id": id_token(prefix, nb),
                "expanded_id_count": len(ids),
                "endpoint_span_count": nb - na + 1,
                "expansion_matches_endpoints": len(ids) == nb - na + 1,
                "expanded_ids": ids,
            }
        )
    return rows


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def main():
    manifest = json.loads(MANIFEST_PATH.read_text())
    byname = {Path(x["path"]).name: x for x in manifest["files"]}
    source_meta = []
    history_rows = []
    raw_pages = {}
    for fname, cfg in FAMILY_CONFIG.items():
        entry = byname[fname]
        pdf = SOURCE / entry["path"]
        actual = sha256(pdf)
        if actual != entry["sha256"]:
            raise SystemExit(
                f"SHA-256 mismatch for {pdf}: {actual} != {entry['sha256']}"
            )
        doc = fitz.open(pdf)
        page_no = cfg["page"]
        page = doc[page_no - 1]
        page_text = page.get_text(sort=False)
        raw_pages[fname] = {"pdf_page_1based": page_no, "extracted_text": page_text}
        source_meta.append(
            {
                "file": fname,
                "family": cfg["family"],
                "sha256": actual,
                "manifest_sha256": entry["sha256"],
                "url": entry["url"],
                "document_number": entry["document_number"],
                "prior_revision": entry["prior_revision"],
                "revision_history_pdf_page": page_no,
                "page_count": len(doc),
                "coverage_label": cfg["coverage"],
            }
        )
        found = page.find_tables()
        if len(found.tables) != 1:
            raise SystemExit(
                f"Expected one revision-history table on {fname} p.{page_no}; found {len(found.tables)}"
            )
        matrix = found.tables[0].extract()
        headers = [norm(x).lower() for x in matrix[0]]
        if not {"date", "revision", "description"}.issubset(set(headers)):
            raise SystemExit(
                f"Unexpected revision-history table headers on {fname}: {headers}"
            )
        if len(matrix) - 1 != EXPECTED_ROW_COUNTS[fname]:
            raise SystemExit(
                f"Unexpected visible history row count for {fname}: {len(matrix)-1}; expected {EXPECTED_ROW_COUNTS[fname]}"
            )
        source_meta[-1]["visible_revision_history_row_count"] = len(matrix) - 1
        ci = {h: i for i, h in enumerate(headers)}
        for cells in matrix[1:]:
            if not all(cells[ci[h]] for h in ("date", "revision", "description")):
                raise SystemExit(
                    f"Incomplete table row on {fname} p.{page_no}: {cells}"
                )
            date = norm(cells[ci["date"]])
            revision = norm(cells[ci["revision"]])
            description = (cells[ci["description"]] or "").replace("\xa0", " ").strip()
            year, month = date_parts(date)
            added, removed, updated = parse_actions(description, cfg["prefix"])
            history_rows.append(
                {
                    "pdf_file": fname,
                    "family": cfg["family"],
                    "date": date,
                    "year": year,
                    "month": month,
                    "revision": revision,
                    "description": description,
                    "raw_row_text": " | ".join(str(x or "").strip() for x in cells),
                    "pdf_page_1based": page_no,
                    "page_locator": f"{fname}, PDF p. {page_no}",
                    "explicit_added_ids": added,
                    "explicit_removed_ids": removed,
                    "explicit_updated_or_modified_ids": updated,
                    "range_expansions": audit_ranges(description, cfg["prefix"]),
                    "initial_release_row": bool(
                        re.search(r"(?i)initial (public )?release", description)
                    ),
                }
            )
    # Source snapshot and raw page text
    standard_files = []
    for meta in source_meta:
        standard_files.append(
            {
                "path": f"../13-errata-dispositions/raw/pdf/{meta['file']}",
                "sha256": meta["sha256"],
                "url": meta["url"],
                "family": meta["family"],
                "document_number": meta["document_number"],
            }
        )
    source_notes = [
        {
            "family": "Broadwell-EP",
            "note": "Revision 003 explicitly says Added BDF86–BDF99, including BDF92; the final errata table omits BDF92 and the erratum detail on PDF p.33 labels it Removed due to inapplicability. The revision-history table has no dated removal row for BDF92, so a complete dated change replay cannot reconcile.",
        },
        {
            "family": "Broadwell-EP",
            "note": "Revision 001 dates Initial Release to May 2015. The retained Intel product announcement in study 18 dates E5-2600 v4 introduction to March 2016. Initial Release may refer to this document rather than silicon; it is not used as a product launch date.",
        },
        {
            "family": "Ice Lake-SP",
            "note": "The pinned PDF has 24 visible revision-history rows from 003US (July 2021) through 026US (March 2026). PDF p.5 begins Preface; no earlier revision rows or initial-release date occur elsewhere in this snapshot. The 003US additions are explicit; any earlier baseline remains unknown.",
        },
        {
            "family": "Zen 1 (Naples)",
            "note": "The printed table lists revisions 1.12, 1.16, 1.17, and 1.21. Revision-number gaps are retained as publisher-table gaps; no missing dates or counts are imputed.",
        },
        {
            "family": "All",
            "note": "Revision-history additions/removals are dated document disclosures. They are not defect discovery dates, silicon escape dates, defect rates, or a complete lifecycle inventory. No initial-release baseline is included in annual addition counts.",
        },
    ]
    for rel in ["source_manifest.json", "raw/errata.csv"]:
        standard_files.append(
            {
                "path": f"../13-errata-dispositions/{rel}",
                "sha256": sha256(SOURCE / rel),
                "role": "Shared frozen source metadata",
            }
        )
    (OUT / "source_manifest.json").write_text(
        json.dumps(
            {
                "study": "Explicit erratum additions and removals in retained revision-history tables",
                "study13_manifest_path": "data/studies/13-errata-dispositions/source_manifest.json",
                "study13_manifest_sha256": sha256(MANIFEST_PATH),
                "files": standard_files,
                "source_files": source_meta,
                "source_notes": source_notes,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    (OUT / "source_pages" / "revision_history_pages.json").write_text(
        json.dumps(raw_pages, indent=2, ensure_ascii=False) + "\n"
    )
    (OUT / "history_rows.json").write_text(
        json.dumps(history_rows, indent=2, ensure_ascii=False) + "\n"
    )
    # Full revision rows: IDs are JSON strings in CSV cells for easy audit.
    rr = []
    for r in history_rows:
        rr.append(
            {
                **r,
                "explicit_added_ids": json.dumps(r["explicit_added_ids"]),
                "explicit_removed_ids": json.dumps(r["explicit_removed_ids"]),
                "explicit_updated_or_modified_ids": json.dumps(
                    r["explicit_updated_or_modified_ids"]
                ),
            }
        )
    write_csv(OUT / "revision_rows.csv", rr, list(rr[0].keys()))
    events = []
    for r in history_rows:
        for typ, key in [
            ("added", "explicit_added_ids"),
            ("removed", "explicit_removed_ids"),
            ("updated_or_modified", "explicit_updated_or_modified_ids"),
        ]:
            for ident in r[key]:
                events.append(
                    {
                        "family": r["family"],
                        "pdf_file": r["pdf_file"],
                        "date": r["date"],
                        "year": r["year"],
                        "revision": r["revision"],
                        "event_type": typ,
                        "erratum_id": ident,
                        "description": r["description"],
                        "page_locator": r["page_locator"],
                    }
                )
    write_csv(OUT / "identifier_events.csv", events, list(events[0].keys()))
    range_rows = []
    for r in history_rows:
        for ran in r["range_expansions"]:
            range_rows.append(
                {
                    "family": r["family"],
                    "pdf_file": r["pdf_file"],
                    "date": r["date"],
                    "revision": r["revision"],
                    "page_locator": r["page_locator"],
                    "description": r["description"],
                    **{
                        k: (json.dumps(v) if isinstance(v, list) else v)
                        for k, v in ran.items()
                    },
                }
            )
    write_csv(OUT / "range_expansions.csv", range_rows, list(range_rows[0].keys()))
    # Annual counts: count unique IDs explicitly called Added in the history rows.
    years = {}
    for r in history_rows:
        y = (r["family"], r["year"])
        q = years.setdefault(
            y,
            {
                "family": r["family"],
                "year": r["year"],
                "revision_rows": 0,
                "rows_with_explicit_addition": 0,
                "explicit_added_id_count": 0,
                "distinct_explicit_added_ids": set(),
                "explicit_removed_id_count": 0,
                "explicit_updated_or_modified_id_count": 0,
                "initial_release_rows": 0,
            },
        )
        q["revision_rows"] += 1
        q["initial_release_rows"] += int(r["initial_release_row"])
        q["rows_with_explicit_addition"] += bool(r["explicit_added_ids"])
        q["explicit_added_id_count"] += len(r["explicit_added_ids"])
        q["distinct_explicit_added_ids"].update(r["explicit_added_ids"])
        q["explicit_removed_id_count"] += len(r["explicit_removed_ids"])
        q["explicit_updated_or_modified_id_count"] += len(
            r["explicit_updated_or_modified_ids"]
        )
    annual = []
    for fam in sorted({x["family"] for x in history_rows}):
        famyears = [y for f, y in years if f == fam]
        for yr in range(min(famyears), max(famyears) + 1):
            q = years.get(
                (fam, yr),
                {
                    "family": fam,
                    "year": yr,
                    "revision_rows": 0,
                    "rows_with_explicit_addition": 0,
                    "explicit_added_id_count": 0,
                    "distinct_explicit_added_ids": set(),
                    "explicit_removed_id_count": 0,
                    "explicit_updated_or_modified_id_count": 0,
                    "initial_release_rows": 0,
                },
            )
            annual.append(
                {
                    "family": fam,
                    "year": yr,
                    "revision_rows": q["revision_rows"],
                    "calendar_year_has_no_revision_rows": q["revision_rows"] == 0,
                    "rows_with_explicit_addition": int(
                        q["rows_with_explicit_addition"]
                    ),
                    "explicit_added_id_count": q["explicit_added_id_count"],
                    "distinct_explicit_added_id_count": len(
                        q["distinct_explicit_added_ids"]
                    ),
                    "explicit_removed_id_count": q["explicit_removed_id_count"],
                    "explicit_updated_or_modified_id_count": q[
                        "explicit_updated_or_modified_id_count"
                    ],
                    "initial_release_rows": q["initial_release_rows"],
                    "zero_added_ids_in_year_with_revision_rows": q["revision_rows"] > 0
                    and q["explicit_added_id_count"] == 0,
                }
            )
    write_csv(OUT / "annual_counts.csv", annual, list(annual[0].keys()))
    # Final identifier reconciliation against the frozen study-13 extraction.
    final_rows = list(
        csv.DictReader(open(SOURCE / "raw/errata.csv", newline="", encoding="utf-8"))
    )
    family_pdf = {cfg["family"]: fname for fname, cfg in FAMILY_CONFIG.items()}
    reconciliations = []
    for fam, fname in family_pdf.items():
        prefix = FAMILY_CONFIG[fname]["prefix"]
        final = {x["erratum_id"] for x in final_rows if x["family"] == fam}
        hist = [r for r in history_rows if r["family"] == fam]
        # Rows in PDF are newest first; reverse to walk forward from an inferred residual baseline.
        ordered = sorted(
            hist,
            key=lambda r: (
                r["year"],
                r["month"],
                int(re.search(r"\d+", r["revision"]).group()),
            ),
        )
        state = set(final)
        reversal_errors = []
        for r in reversed(ordered):
            for x in r["explicit_added_ids"]:
                if x not in state:
                    reversal_errors.append(
                        f"reverse-add missing final-state ID {x} at rev {r['revision']}"
                    )
                state.discard(x)
            for x in r["explicit_removed_ids"]:
                state.add(x)
        baseline = state
        replay = set(baseline)
        replay_errors = []
        for r in ordered:
            for x in r["explicit_added_ids"]:
                if x in replay:
                    replay_errors.append(
                        f"added ID already present {x} at rev {r['revision']}"
                    )
                replay.add(x)
            for x in r["explicit_removed_ids"]:
                if x not in replay:
                    replay_errors.append(
                        f"removed ID absent {x} at rev {r['revision']}"
                    )
                replay.discard(x)
        missing = sorted(final - replay)
        extra = sorted(replay - final)
        duplicates = [
            k
            for k, v in Counter(
                x["erratum_id"] for x in final_rows if x["family"] == fam
            ).items()
            if v > 1
        ]
        note = (
            "BDF92 is explicitly in the 2018 Added BDF86–BDF99 range, absent from the frozen final errata list, and labeled Removed due to inapplicability in the final PDF erratum details (PDF p.33); the revision-history table supplies no dated removal row."
            if fam == "Broadwell-EP"
            else None
        )
        reconciliations.append(
            {
                "family": fam,
                "pdf_file": fname,
                "final_id_count": len(final),
                "final_ids": sorted(final),
                "final_duplicate_ids_in_study13_extract": duplicates,
                "explicit_added_event_count": sum(
                    len(r["explicit_added_ids"]) for r in hist
                ),
                "explicit_removed_event_count": sum(
                    len(r["explicit_removed_ids"]) for r in hist
                ),
                "inferred_residual_baseline_id_count": len(baseline),
                "inferred_residual_baseline_ids": sorted(baseline),
                "replay_final_id_count": len(replay),
                "replay_matches_frozen_final_list": not missing
                and not extra
                and not reversal_errors
                and not replay_errors,
                "missing_from_replay": missing,
                "extra_in_replay": extra,
                "reverse_replay_errors": reversal_errors,
                "forward_replay_errors": replay_errors,
                "reconciliation_note": note,
                "assumption": "The revision table's explicitly labeled Added and Removed events are treated as exhaustive, ordered changes to a stable identifier set for the listed rows; unmentioned IDs are assigned to an inferred residual prehistory baseline solely for set reconciliation. This baseline is not observed, not dated, and is excluded from annual additions.",
            }
        )
    (OUT / "final_id_reconciliation.json").write_text(
        json.dumps(reconciliations, indent=2, ensure_ascii=False) + "\n"
    )
    # Render only source revision-history pages for visual QA; no analytic chart is produced.
    for fname, cfg in FAMILY_CONFIG.items():
        d = fitz.open(SOURCE / "raw/pdf" / fname)
        pix = d[cfg["page"] - 1].get_pixmap(matrix=fitz.Matrix(1.8, 1.8), alpha=False)
        pix.save(OUT / "source_visual_qa" / f"{Path(fname).stem}-p{cfg['page']}.png")
    print(
        f"Wrote {len(history_rows)} revision rows; {len(events)} identifier events; {len(annual)} annual rows"
    )
    print(
        "Outputs: "
        + ", ".join(
            str(p.relative_to(ROOT)) for p in sorted(OUT.rglob("*")) if p.is_file()
        )
    )
    for r in reconciliations:
        print(
            r["family"],
            "final",
            r["final_id_count"],
            "residual baseline",
            r["inferred_residual_baseline_id_count"],
            "reconciled",
            r["replay_matches_frozen_final_list"],
            "errors",
            len(r["reverse_replay_errors"]) + len(r["forward_replay_errors"]),
        )


if __name__ == "__main__":
    main()
