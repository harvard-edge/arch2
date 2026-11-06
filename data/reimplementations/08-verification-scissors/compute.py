#!/usr/bin/env python3
"""Spec 08: verification scissors. Run from this folder; writes result.json.

Arithmetic on the cells is exact (Fraction); only the CAGR root goes through
float. All inputs come from the CSV. Years and spans below come from the spec.
"""
import csv
import hashlib
import json
import re
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSV_PATH = HERE / "inputs/book/contents/chapters/02-pressures/data/fig-verification-demand-scissors/chapter2-wilson-verification-staffing.csv"
OUT_PATH = HERE / "result.json"

COLUMNS = ["year", "design_engineers_mean_peak", "verification_engineers_mean_peak",
           "evidence_type", "source", "caveat"]
WAVE_TYPES = {"printed_data_label", "chart_read_constrained"}
START, END = 2007, 2022
GAP_WAVES = [2014, 2016, 2018, 2020]
SPANS = [(2007, 2014), (2014, 2022), (2007, 2022), (2016, 2018), (2018, 2020), (2014, 2020)]
SERIES = ["design", "verification"]


def load():
    raw = CSV_PATH.read_bytes()
    rows = list(csv.reader(raw.decode("utf-8").splitlines()))
    if rows[0] != COLUMNS:
        sys.exit(f"unexpected header: {rows[0]}")
    waves, cagr_row, ledger = {}, None, []
    for row in rows[1:]:
        if len(row) < len(COLUMNS):
            sys.exit(f"short row, cannot interpret: {row}")
        # Unquoted commas in the trailing caveat text spill into extra fields.
        spilled = len(row) - len(COLUMNS)
        if spilled:
            row = row[:5] + [",".join(row[5:])]
            ledger.append({"row": row[0], "action": "kept",
                           "reason": f"caveat had {spilled} unquoted comma(s); fields rejoined, numeric cells unaffected"})
        rec = dict(zip(COLUMNS, row))
        kind, label = rec["evidence_type"], rec["year"]
        if kind in WAVE_TYPES:
            year = int(label)
            if year in waves:
                sys.exit(f"duplicate wave {year}")
            waves[year] = {"design": Fraction(rec[COLUMNS[1]]),
                           "verification": Fraction(rec[COLUMNS[2]]),
                           "evidence_type": kind, "caveat": rec["caveat"]}
        elif label == f"CAGR {START}-{END}":
            cagr_row = rec
        elif label == "context":
            ledger.append({"row": label, "action": "dropped", "reason": "spec: context row is out of scope"})
        else:
            sys.exit(f"unclassified row: {row}")
    needed = {START, END, *GAP_WAVES, *(y for span in SPANS for y in span)}
    missing = needed - waves.keys()
    if missing or cagr_row is None:
        sys.exit(f"missing inputs: waves {sorted(missing)}, cagr_row present={cagr_row is not None}")
    return waves, cagr_row, ledger, hashlib.sha256(raw).hexdigest(), len(rows) - 1


def percent_cell(text):
    match = re.fullmatch(r"([0-9.]+) percent", text.strip())
    if not match:
        sys.exit(f"CAGR cell is not '<number> percent': {text!r}")
    return float(match.group(1))


def pct(a, b):
    return 100 * (b / a - 1)


def cagr(a, b, years):
    return 100 * (float(b / a) ** (1 / years) - 1)


def difference(iv, id_):
    return iv - id_


def ratio(iv, id_):
    return iv / id_


def build(waves, cagr_design, cagr_verification, distance):
    base = waves[START]
    index, gaps = {}, {}
    for year in sorted(waves):
        w = waves[year]
        id_, iv = w["design"] / base["design"], w["verification"] / base["verification"]
        gaps[year] = distance(iv, id_)
        index[str(year)] = {"design": float(id_), "verification": float(iv),
                            "gap": float(gaps[year]), "evidence_type": w["evidence_type"]}
    gap_min = min(gaps[y] for y in GAP_WAVES)
    gap_max = max(gaps[y] for y in GAP_WAVES)
    years = END - START
    return {
        "index": index,
        "pct_change": {f"{a}_{b}": {s: float(pct(waves[a][s], waves[b][s])) for s in SERIES} for a, b in SPANS},
        "gap_min": float(gap_min),
        "gap_max": float(gap_max),
        "gap_2022": float(gaps[END]),
        "gap_2022_in_range": bool(gap_min <= gaps[END] <= gap_max),
        "cagr_computed": {s: cagr(waves[START][s], waves[END][s], years) for s in SERIES},
        "cagr_stated": {"design": cagr_design, "verification": cagr_verification},
        "share_of_growth_by_2014": {
            s: float((waves[2014][s] - waves[START][s]) / (waves[END][s] - waves[START][s])) for s in SERIES},
    }


def slots(entry, by_2022_from, by_2020_from, waves):
    extra = {}
    if f"{by_2020_from}_2020" not in entry["pct_change"]:
        extra[f"{by_2020_from}_2020"] = {s: float(pct(waves[by_2020_from][s], waves[2020][s])) for s in SERIES}
    entry["pct_change"].update(extra)
    return {"then_by_2022_base": by_2022_from,
            "then_by_2022": entry["pct_change"][f"{by_2022_from}_2022"],
            "rose_fell_by_2020_base": by_2020_from,
            "rose_fell_by_2020": entry["pct_change"][f"{by_2020_from}_2020"]}


def diagnostics(waves, cagr_row, base_entry):
    """Outside the spec's output shape: checks the row caveats make possible."""
    caveats = waves[END]["caveat"]
    design_call = re.search(r"\+(\d+) percent design", caveats)
    verif_call = re.search(r"\+(\d+) percent verification", caveats)
    span_2020 = re.search(r"(\d{4})-(\d{4}) rates stated as ([0-9.]+) percent design and ([0-9.]+) percent verification",
                          cagr_row["caveat"])
    if not (design_call and verif_call and span_2020):
        sys.exit("expected caveat text not found")
    y0, y1 = int(span_2020.group(1)), int(span_2020.group(2))
    return {
        "computed_minus_stated_cagr": {s: base_entry["cagr_computed"][s] - base_entry["cagr_stated"][s] for s in SERIES},
        "callouts_in_2022_caveat_pct": {"design": float(design_call.group(1)), "verification": float(verif_call.group(1))},
        "computed_minus_callout_pct": {
            "design": base_entry["pct_change"]["2007_2022"]["design"] - float(design_call.group(1)),
            "verification": base_entry["pct_change"]["2007_2022"]["verification"] - float(verif_call.group(1))},
        "cagr_2007_2020": {
            "computed": {s: cagr(waves[y0][s], waves[y1][s], y1 - y0) for s in SERIES},
            "stated_in_caveat": {"design": float(span_2020.group(3)), "verification": float(span_2020.group(4))}},
    }


def main():
    waves, cagr_row, ledger, digest, n_rows = load()
    stated_d = percent_cell(cagr_row[COLUMNS[1]])
    stated_v = percent_cell(cagr_row[COLUMNS[2]])

    defs = [
        ("R1_diff_then2014_rose2018_cagrAsNamed", difference, 2014, 2018, False,
         "Distance = Iv-Id; 'then by 2022' from 2014; 'by 2020' from 2018; CAGR cells design, verification by column name"),
        ("R2_ratio_distance", ratio, 2014, 2018, False,
         "As R1 but distance = Iv/Id, so gap, gap_min, gap_max, gap_2022 are ratios"),
        ("R3_then_by_2022_from_2007", difference, 2007, 2018, False,
         "As R1 but 'then by 2022' from 2007"),
        ("R4_rose_by_2020_from_2016", difference, 2014, 2016, False,
         "As R1 but 'by 2020' from 2016, the wave before the fall (spec treats 2018 as implied, not stated)"),
        ("R5_cagr_columns_swapped", difference, 2014, 2018, True,
         "As R1 but CAGR cells read the other way round (column meaning is inferred)"),
    ]
    readings = {}
    for name, distance, by22, by20, swap, text in defs:
        entry = build(waves, stated_v if swap else stated_d, stated_d if swap else stated_v, distance)
        entry["claim_slots"] = slots(entry, by22, by20, waves)
        readings[name] = {"description": text, "result": entry}

    baseline = readings[defs[0][0]]["result"]
    result = {
        "input_sha256": digest,
        "rows": {"total": n_rows, "waves": len(waves), "cagr": 1,
                 "dropped": sum(1 for item in ledger if item["action"] == "dropped")},
        "row_ledger": ledger,
        "readings": readings,
        "diagnostics_outside_spec_shape": diagnostics(waves, cagr_row, baseline),
    }
    OUT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: baseline[k] for k in baseline if k != "index"}, indent=1))
    print(json.dumps(result["diagnostics_outside_spec_shape"], indent=1))
    r2 = readings["R2_ratio_distance"]["result"]
    print("ratio", r2["gap_min"], r2["gap_max"], r2["gap_2022"], r2["gap_2022_in_range"])


if __name__ == "__main__":
    main()
