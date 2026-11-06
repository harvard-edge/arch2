#!/usr/bin/env python3
"""Spec 03: CVDP category gap. Run from this folder; writes result.json.

Computes every output from the CSV. Arithmetic is exact (Decimal/Fraction) so a
half-way check is not disturbed by binary floats. Readings are the cross product
of the three ambiguity axes listed in AXES.
"""
import csv
import hashlib
import itertools
import json
import re
import shutil
import subprocess
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP
from fractions import Fraction
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSV_PATH = HERE / "inputs/book/contents/chapters/10-evaluation/data/fig-ch10-cvdp-category-gap/chapter10-cvdp-category-pass1.csv"
PDF_PATH = HERE / "src/paper.pdf"
HTML_PATH = HERE / "src/paper.html"
OUT = HERE / "result.json"
SPEC_TO_RTL, CHECKER = "cid03", "cid13"
OVERALL = "overall"
TOL_OVERALL = Fraction(1, 10)

AXES = {
    "rounding": {"half_up": ROUND_HALF_UP, "half_even": ROUND_HALF_EVEN},
    "median": ("midpoint", "low", "high"),
    "aggregate": ("printed", "recomputed"),
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load():
    """Return data rows, comment-line count, and blank-line count."""
    lines = CSV_PATH.read_text(encoding="utf-8").splitlines()
    comments = sum(1 for x in lines if x.startswith("#"))
    blanks = sum(1 for x in lines if not x.strip())
    kept = [x for x in lines if x.strip() and not x.startswith("#")]
    rows = []
    for r in csv.DictReader(kept):
        rows.append({
            "cid": r["category_id"], "name": r["category_name"],
            "group": r["category_group"], "model": r["model"],
            "pct": Decimal(r["pass_at_1_pct"]), "n": int(r["n_problems"]),
        })
    return rows, comments, blanks


def validate(rows):
    keys = [(r["cid"], r["model"]) for r in rows]
    if len(keys) != len(set(keys)):
        raise SystemExit("duplicate (category, model) rows")
    models = list(dict.fromkeys(r["model"] for r in rows))
    cids = list(dict.fromkeys(r["cid"] for r in rows))
    missing = [(c, m) for c in cids for m in models if (c, m) not in set(keys)]
    if missing:
        raise SystemExit(f"missing cells: {missing}")
    for c in cids:
        if len({r["n"] for r in rows if r["cid"] == c}) != 1:
            raise SystemExit(f"n_problems varies within {c}")
    return models, cids


def median(values, kind):
    s = sorted(values)
    k = len(s)
    if k % 2:
        return s[k // 2]
    lo, hi = s[k // 2 - 1], s[k // 2]
    return {"midpoint": (lo + hi) / 2, "low": lo, "high": hi}[kind]


def to_int(value, mode):
    return int(Decimal(value).quantize(Decimal(1), rounding=mode))


def frac_dec(fr):
    return Decimal(fr.numerator) / Decimal(fr.denominator)


def recompute(rows, models):
    """Sum of n times percent over sum of n, per model, exact."""
    out = {}
    for m in models:
        cat = [r for r in rows if r["model"] == m and r["cid"] != OVERALL]
        out[m] = sum(Fraction(r["pct"]) * r["n"] for r in cat) / sum(r["n"] for r in cat)
    return out


def lowest(stat_by_cat):
    low = min(stat_by_cat.values())
    return " | ".join(sorted(c for c, v in stat_by_cat.items() if v == low))


def reading(rows, models, rounding, median_kind, aggregate):
    mode = AXES["rounding"][rounding]
    cat_rows = [r for r in rows if r["cid"] != OVERALL]
    cids = list(dict.fromkeys(r["cid"] for r in cat_rows))
    printed = {r["model"]: r["pct"] for r in rows if r["cid"] == OVERALL}
    recomputed = recompute(rows, models)
    agg = printed if aggregate == "printed" else {m: frac_dec(v) for m, v in recomputed.items()}
    top = max(agg.values())
    best = [m for m in models if agg[m] == top]

    cats, mins, maxs, meds = {}, {}, {}, {}
    for c in cids:
        sel = [r for r in cat_rows if r["cid"] == c]
        vals = [r["pct"] for r in sel]
        mins[c], maxs[c], meds[c] = min(vals), max(vals), median(vals, median_kind)
        by_model = {r["model"]: r["pct"] for r in sel}
        cats[c] = {
            "name": sel[0]["name"], "n_problems": sel[0]["n"],
            "min_pct": float(mins[c]), "max_pct": float(maxs[c]),
            "median_pct": float(meds[c]), "spread_pp": float(maxs[c] - mins[c]),
            "best_model_pct": float(by_model[best[0]]),
        }
        if len(best) > 1:
            cats[c]["best_model_pct_all"] = {m: float(by_model[m]) for m in best}

    return {
        "n_models": len(models),
        "categories": cats,
        "spec_to_rtl_range_pct": [float(mins[SPEC_TO_RTL]), float(maxs[SPEC_TO_RTL])],
        "checker_range_pct": [float(mins[CHECKER]), float(maxs[CHECKER])],
        "spec_to_rtl_range_int": [to_int(mins[SPEC_TO_RTL], mode), to_int(maxs[SPEC_TO_RTL], mode)],
        "checker_range_int": [to_int(mins[CHECKER], mode), to_int(maxs[CHECKER], mode)],
        "gap": {
            "gap_max_pp": float(maxs[SPEC_TO_RTL] - maxs[CHECKER]),
            "gap_min_pp": float(mins[SPEC_TO_RTL] - mins[CHECKER]),
            "disjoint": bool(maxs[CHECKER] < mins[SPEC_TO_RTL]),
        },
        "lowest_category": {"by_max": lowest(maxs), "by_median": lowest(meds), "by_min": lowest(mins)},
        "best_aggregate_model": best,
        "overall_max_pct": round(float(top), 6),
        "overall_max_int": to_int(top, mode),
        "overall_check": {
            m: {"printed": float(printed[m]), "recomputed": round(float(recomputed[m]), 6)}
            for m in models
        },
    }


def half_cells(rows):
    """Range endpoints and overall maxima whose rounding would hit an exact .5."""
    frac = Decimal("0.5")
    return [
        {"category_id": r["cid"], "model": r["model"], "pct": float(r["pct"])}
        for r in rows
        if r["cid"] in (SPEC_TO_RTL, CHECKER, OVERALL) and r["pct"] % 1 == frac
    ]


def overall_flags(rows, models):
    printed = {r["model"]: r["pct"] for r in rows if r["cid"] == OVERALL}
    rec = recompute(rows, models)
    out = {}
    for m in models:
        diff = rec[m] - Fraction(printed[m])
        out[m] = {"recomputed_minus_printed": round(float(diff), 6), "over_0p1": abs(diff) > TOL_OVERALL}
    return out


class Tables(HTMLParser):
    """Collect each outer table in the arXiv HTML as rows of cell text."""

    def __init__(self):
        super().__init__()
        self.tables, self.cur, self.row, self.cell = [], None, None, None

    def handle_starttag(self, tag, attrs):
        if tag == "table" and self.cur is None and self.cell is None:
            self.cur = []
        elif tag == "tr" and self.cur is not None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.cur.append(self.row)
            self.row = None
        elif tag == "table" and self.cur is not None and self.cell is None:
            self.tables.append(self.cur)
            self.cur = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def html_table2(path):
    p = Tables()
    p.feed(path.read_text(encoding="utf-8"))
    t2 = [t for t in p.tables if t[0][:3] == ["Model", "Overall", "cid02"]]
    t1 = [t for t in p.tables if len(t) > 1 and t[1][:2] == ["ID", "Category Description"]]
    t3 = [t for t in p.tables if t[0][:3] == ["Model", "Overall", "cid03"]]
    if len(t2) != 1 or len(t1) != 1 or len(t3) != 1:
        raise SystemExit(f"HTML tables not uniquely found: {len(t1)}, {len(t2)}, {len(t3)}")
    grid = [(r[0], [c.rstrip("%") for c in r[1:]]) for r in t2[0][1:]]
    counts = {r[0]: (r[1], int(r[2])) for r in t1[0] if re.fullmatch(r"cid\d\d", r[0])}
    agentic_overall = [Decimal(r[1].rstrip("%")) for r in t3[0][1:]]
    return t2[0][0][1:], grid, counts, agentic_overall


def pdf_table2(path):
    text = subprocess.run(["pdftotext", "-layout", str(path), "-"], check=True,
                          capture_output=True, text=True).stdout
    lines = text.splitlines()
    head = [i for i, x in enumerate(lines) if re.match(r"\s*Model\s+Overall\s+cid02", x)]
    if len(head) != 1:
        raise SystemExit(f"PDF Table 2 header found {len(head)} times")
    columns = lines[head[0]].split()[1:]
    grid = []
    for line in lines[head[0] + 1:]:
        if line.strip().startswith("Table 2:"):
            break
        cells = re.findall(r"(\d+\.\d+)%", line)
        grid.append((re.split(r"\s+\d+\.\d+%", line.strip())[0].strip(), cells))
    counts = {}
    for line in lines:
        m = re.match(r"\s*(cid\d\d) (.+?)\s+(\d+)\s+(\d+)\s+(?:–|\d+\.\d+/)", line)
        if m:
            counts[m.group(1)] = (" ".join(m.group(2).split()), int(m.group(3)))
    return columns, grid, counts


def compare(label, columns, grid, counts, rows, models):
    """Cell-by-cell comparison; rows align by order, labels are reported."""
    cell = {(r["cid"], r["model"]): r["pct"] for r in rows}
    diffs, checked, label_notes = [], 0, []
    if len(grid) != len(models):
        diffs.append({"problem": f"{label} has {len(grid)} model rows, CSV has {len(models)}"})
    for (name, cells), model in zip(grid, models):
        if name != model:
            label_notes.append({"source_label": name, "csv_model": model})
        if len(cells) != len(columns):
            diffs.append({"problem": f"{label} row {name}: {len(cells)} cells"})
        for col, value in zip(columns, cells):
            cid = "overall" if col == "Overall" else col
            checked += 1
            if Decimal(value) != cell[(cid, model)]:
                diffs.append({"model": model, "category_id": cid, "source": value,
                              "csv": str(cell[(cid, model)])})
    n_csv = {r["cid"]: (r["name"], r["n"]) for r in rows if r["cid"] != OVERALL}
    count_diffs = []
    for cid, (name, n) in n_csv.items():
        if cid not in counts:
            count_diffs.append({"category_id": cid, "problem": "not found in source"})
        elif counts[cid] != (name, n):
            count_diffs.append({"category_id": cid, "source": counts[cid], "csv": (name, n)})
    return {"cells_checked": checked, "cell_differences": diffs,
            "table1_rows_checked": len(n_csv), "table1_differences": count_diffs,
            "model_label_mismatches": label_notes}


def source_comparison(rows, models):
    out = {}
    if HTML_PATH.exists():
        columns, grid, counts, agentic = html_table2(HTML_PATH)
        out["html"] = {"sha256": sha256(HTML_PATH), **compare("HTML", columns, grid, counts, rows, models)}
        out["agentic_overall_max_pct_table3"] = float(max(agentic))
    else:
        out["html"] = {"status": "not fetched"}
    if not PDF_PATH.exists():
        out["pdf"] = {"status": "not fetched"}
    elif shutil.which("pdftotext") is None:
        out["pdf"] = {"status": "pdftotext not installed"}
    else:
        columns, grid, counts = pdf_table2(PDF_PATH)
        out["pdf"] = {"sha256": sha256(PDF_PATH), **compare("PDF", columns, grid, counts, rows, models)}
    return out


def main():
    rows, comments, blanks = load()
    models, cids = validate(rows)
    results = {}
    for rnd, med, agg in itertools.product(AXES["rounding"], AXES["median"], AXES["aggregate"]):
        results[f"round_{rnd}__median_{med}__aggregate_{agg}"] = reading(rows, models, rnd, med, agg)

    first = next(iter(results.values()))
    varying = sorted({k for r in results.values() for k in r if r[k] != first[k]})
    n_sum = sum({r["cid"]: r["n"] for r in rows if r["cid"] != OVERALL}.values())
    n_overall = {r["n"] for r in rows if r["cid"] == OVERALL}
    output = {
        "readings": results,
        "meta": {
            "input_sha256": sha256(CSV_PATH),
            "rows_read": len(rows),
            "models": models,
            "category_rows_used": sum(r["cid"] != OVERALL for r in rows),
            "overall_rows_held_apart": sum(r["cid"] == OVERALL for r in rows),
            "comment_lines_skipped": comments,
            "blank_lines_skipped": blanks,
            "rows_dropped": 0,
            "sum_category_n": n_sum,
            "overall_row_n": sorted(n_overall),
            "exact_half_cells": half_cells(rows),
            "category_cells_that_are_whole_numbers": sum(
                r["pct"] % 1 == 0 for r in rows if r["cid"] != OVERALL),
            "top_level_keys_that_vary_across_readings": varying,
        },
        "overall_check_flags": overall_flags(rows, models),
        "source_comparison": source_comparison(rows, models),
    }
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT.name}: {len(results)} readings")


if __name__ == "__main__":
    main()
