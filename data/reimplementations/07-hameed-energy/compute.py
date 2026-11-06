#!/usr/bin/env python3
"""Spec 07: Hameed energy decomposition. Run from this folder; writes result.json."""
import collections
import csv
import hashlib
import json
import math
import os
import re
import subprocess
import unicodedata
import urllib.error
import urllib.request
from fractions import Fraction

STAGED = "inputs/book/contents/chapters/02-pressures/data/fig-ch02-specialization-energy/chapter2-hameed-staged-energy.csv"
BREAKDOWN = "inputs/book/contents/chapters/02-pressures/data/fig-ch02-specialization-energy/chapter2-hameed-component-breakdown.csv"
PDF = "pdf/source.pdf"
STAGES = ["plus_SIMD_VLIW", "plus_op_fusion", "plus_magic", "ASIC"]
COMPONENTS = ["IF", "Pipeline", "D-cache", "Control", "RegFile", "FU"]
SUBSTAGES = ["IME", "FME", "IP", "CABAC"]
STAGED_COLS = 8
BREAKDOWN_COLS = 9
TOL_CHART = Fraction(5, 100)
TOL_ASIC = Fraction(5, 100)


def load(path, ncols):
    """Return (rows, header comment lines, counters). Malformed rows are counted, not kept."""
    comments, body = [], []
    with open(path, newline="", encoding="utf-8") as fh:
        for line in fh:
            (comments if line.startswith("#") else body).append(line)
    reader = csv.reader(body)
    header = next(reader)
    if len(header) != ncols:
        raise SystemExit(f"{path}: header has {len(header)} columns, expected {ncols}")
    rows, malformed, blank = [], 0, 0
    for rec in reader:
        if not rec:
            blank += 1
        elif len(rec) != ncols:
            malformed += 1
        else:
            rows.append(dict(zip(header, rec)))
    counts = {"comment_lines": len(comments), "data_rows": len(rows),
              "dropped_malformed": malformed, "dropped_blank": blank}
    return rows, comments, counts


def one(rows, **where):
    hits = [r for r in rows if all(r[k] == v for k, v in where.items())]
    if len(hits) != 1:
        raise SystemExit(f"expected exactly one row for {where}, found {len(hits)}")
    return hits[0]


def val(row):
    return Fraction(row["value"])


def half_up_1dp(x):
    return Fraction(math.floor(x * 10 + Fraction(1, 2)), 10)


def f(x):
    return float(x)


def rel(a, b):
    """|a-b| / b as a float."""
    return float(abs(a - b) / b)


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def components_block(by_comp, denom, rank_style):
    shares = {c: by_comp[c] / denom * 100 for c in COMPONENTS}
    distinct = sorted(set(shares.values()), reverse=True)
    out = {}
    for c in COMPONENTS:
        if rank_style == "competition":
            rank = 1 + sum(1 for o in COMPONENTS if shares[o] > shares[c])
        else:
            rank = 1 + distinct.index(shares[c])
        out[c] = {"mJ": f(by_comp[c]), "share_pct": f(shares[c]),
                  "share_pct_1dp": f(half_up_1dp(shares[c])), "rank": rank}
    return out, shares


def fetch_pdf(url, want_sha):
    """Return a record of the source check inputs; never substitutes anything."""
    if not os.path.exists(PDF):
        os.makedirs("pdf", exist_ok=True)
        try:
            urllib.request.urlretrieve(url, PDF)
        except (urllib.error.URLError, OSError) as exc:
            return {"available": False, "reason": f"fetch failed: {exc}"}
    got = sha256(PDF)
    if got != want_sha:
        return {"available": False, "reason": f"sha256 mismatch: got {got}, want {want_sha}"}
    return {"available": True, "sha256": got}


def pdf_text(layout):
    cmd = ["pdftotext"] + (["-layout"] if layout else []) + [PDF, "-"]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    return unicodedata.normalize("NFKC", out)


def compare_source(staged, breakdown):
    """Compare every Table 1/2/3 and quoted-text transcribed cell with the PDF text."""
    text = pdf_text(layout=True)
    flat = " ".join(pdf_text(layout=False).split())

    t3_cols = {"IF": "IF", "D-$": "D-cache", "Pip": "Pipeline", "Ctl": "Control",
               "RF": "RegFile", "FU": "FU", "Total": "Total"}
    head = re.search(r"\bIF\s+D-\$\s+Pip\s+Ctl\s+RF\s+FU\s+Total\b", text)
    if head is None:
        raise SystemExit("Table 3 header not found in PDF text")
    order = [t3_cols[t] for t in head.group(0).split()]
    t3 = {}
    for m in re.finditer(r"^\s*(IME|FME|Intra|CABAC|Total)((?:\s+\d+){7})\b", text, re.M):
        name = "IP" if m.group(1) == "Intra" else m.group(1)
        t3[name] = dict(zip(order, (Fraction(x) for x in m.group(2).split())))
    t2 = {}
    pat2 = r"^\s*(IME|FME|Intra|CABAC)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s+([\d.]+)x\s+(\d+)x"
    for m in re.finditer(pat2, text, re.M):
        name = "IP" if m.group(1) == "Intra" else m.group(1)
        t2[name] = {"fps": Fraction(m.group(3)), "mJ": Fraction(m.group(5)),
                    "perf_gap": Fraction(m.group(6)), "energy_gap": Fraction(m.group(7))}
    t1 = re.search(r"\bASIC\s+(\d+)\s+(\d+)\s+(\d+)\s*$", text, re.M)
    if len(t3) != 5 or len(t2) != 4 or t1 is None:
        raise SystemExit(f"table parse incomplete: t3={len(t3)} t2={len(t2)} t1={t1}")

    compared, diffs, not_compared = 0, [], collections.Counter()

    def check(label, csv_value, pdf_value, slack=Fraction(0)):
        nonlocal compared
        compared += 1
        if abs(csv_value - pdf_value) > slack:
            diffs.append({"cell": label, "csv": f(csv_value), "pdf": f(pdf_value)})

    for r in breakdown:
        if r["source_table_or_figure"] == "Table 3" and r["evidence_class"] == "transcribed":
            check(f"breakdown {r['h264_substage']}/{r['component']}", val(r),
                  t3[r["h264_substage"]][r["component"]])
    for r in staged:
        if r["evidence_class"] != "transcribed":
            continue
        src, sub, metric = r["source_table_or_figure"], r["h264_substage_or_total"], r["metric"]
        lab = f"staged {r['optimization_stage']}/{sub}/{metric} [{src}]"
        if src == "Table 2":
            pdf_v = t2[sub]["mJ"] if metric == "energy_mJ_per_frame" else t2[sub]["fps"]
            check(lab, val(r), pdf_v)
        elif src == "Table 2 perf gap":
            check(lab, val(r), t2[sub]["perf_gap"])
        elif src == "Table 2 energy gap (1/gap)":
            check(lab, val(r), 1 / t2[sub]["energy_gap"], Fraction(5, 10**7))
        elif src == "Table 3 total":
            check(lab, val(r), t3["Total"]["Total"])
        elif src == "Table 1":
            pdf_v = Fraction(t1.group(3)) if metric == "energy_mJ_per_frame" else Fraction(t1.group(1))
            check(lab, val(r), pdf_v)
        else:
            quote = re.search(r"'(.+)'", src)
            if quote is None:
                not_compared[src] += 1
                continue
            compared += 1
            q = quote.group(1)
            num = re.search(r"([\d.]+)x", q)
            if q not in flat:
                diffs.append({"cell": lab, "problem": "quoted text not found in PDF"})
            elif Fraction(num.group(1)) != val(r):
                diffs.append({"cell": lab, "csv": f(val(r)), "pdf_quote": q})
    return {"cells_compared": compared, "differences": diffs,
            "not_compared_rows_by_source": dict(not_compared)}


def main():
    staged, staged_head, staged_counts = load(STAGED, STAGED_COLS)
    breakdown, break_head, break_counts = load(BREAKDOWN, BREAKDOWN_COLS)
    head_text = "".join(staged_head)

    # Panel (a)
    total = {"h264_substage_or_total": "Total", "metric": "energy_efficiency_ratio_vs_base"}
    transcribed = {s: val(one(staged, optimization_stage=s, evidence_class="transcribed", **total))
                   for s in STAGES}
    chart = {s: val(one(staged, optimization_stage=s, evidence_class="chart-read", **total))
             for s in STAGES}
    factors, chart_checks, prev = {}, {}, Fraction(1)  # base is 1 by definition in the spec
    for s in STAGES:
        ratio = transcribed[s] / chart[s]
        factors[s] = {"transcribed": f(transcribed[s]), "chart_read": f(chart[s]),
                      "transcribed_over_chart_read": f(ratio),
                      "step_factor": f(transcribed[s] / prev)}
        prev = transcribed[s]
        chart_checks[s] = {"rel_diff_vs_chart_read": rel(transcribed[s], chart[s]),
                           "rel_diff_vs_transcribed": rel(chart[s], transcribed[s]),
                           "within_5pct_vs_chart_read": bool(abs(ratio - 1) <= TOL_CHART),
                           "within_5pct_vs_transcribed": bool(abs(chart[s] - transcribed[s]) / transcribed[s] <= TOL_CHART)}

    # Energy check
    base_mJ = val(one(staged, optimization_stage="base_RISC_CMP", h264_substage_or_total="Total",
                      metric="energy_mJ_per_frame", evidence_class="transcribed",
                      source_table_or_figure="Table 3 total"))
    asic_mJ = val(one(staged, optimization_stage="ASIC", h264_substage_or_total="Total",
                      metric="energy_mJ_per_frame", evidence_class="transcribed",
                      source_table_or_figure="Table 1"))
    base_over_asic = base_mJ / asic_mJ
    energy_check = {"base_mJ": f(base_mJ), "asic_mJ": f(asic_mJ), "base_over_asic": f(base_over_asic)}
    vs_factor = {"asic_factor": f(transcribed["ASIC"]),
                 "rel_diff_vs_asic_factor": rel(base_over_asic, transcribed["ASIC"]),
                 "rel_diff_vs_base_over_asic": rel(transcribed["ASIC"], base_over_asic),
                 "within_5pct_vs_asic_factor": bool(abs(base_over_asic - transcribed["ASIC"]) / transcribed["ASIC"] <= TOL_ASIC),
                 "within_5pct_vs_base_over_asic": bool(abs(base_over_asic - transcribed["ASIC"]) / base_over_asic <= TOL_ASIC)}

    # Diagnostic, outside the spec's definitions: ASIC energy implied by Table 2 gaps.
    implied = Fraction(0)
    table2_sum = Fraction(0)
    for sub in SUBSTAGES:
        e = val(one(staged, optimization_stage="base_RISC_CMP", h264_substage_or_total=sub,
                    metric="energy_mJ_per_frame", evidence_class="transcribed"))
        gap_ratio = val(one(staged, optimization_stage="ASIC", h264_substage_or_total=sub,
                            metric="energy_efficiency_ratio_vs_base", evidence_class="transcribed"))
        table2_sum += e
        implied += e * gap_ratio
    diagnostic = {"note": "not a spec metric; sums base substage mJ (Table 2) times 1/energy gap (Table 2 rows)",
                  "implied_asic_mJ_from_table2_gaps": f(implied),
                  "table3_total_over_implied_asic": f(base_mJ / implied),
                  "table2_sum_over_implied_asic": f(table2_sum / implied)}

    # Panel (b)
    sel = {"optimization_stage": "base_RISC_CMP", "metric": "energy_mJ_per_frame",
           "evidence_class": "transcribed"}
    by_comp = {c: val(one(breakdown, h264_substage="Total", component=c, **sel)) for c in COMPONENTS}
    total_mJ = val(one(breakdown, h264_substage="Total", component="Total", **sel))
    components_sum = sum(by_comp.values())
    substage_t3 = sum(val(one(breakdown, h264_substage=s, component="Total", **sel)) for s in SUBSTAGES)
    substage_t2 = table2_sum

    comp_total, shares = components_block(by_comp, total_mJ, "competition")
    ties = []
    for i, a in enumerate(COMPONENTS):
        for b in COMPONENTS[i + 1:]:
            if shares[a] == shares[b]:
                ties.append([a, b])

    def reading(desc, denom=total_mJ, style="competition", substage=substage_t3):
        comps, _ = components_block(by_comp, denom, style)
        return {"description": desc, "factors": factors, "energy_check": energy_check,
                "components": comps, "total_mJ": f(total_mJ),
                "components_sum_mJ": f(components_sum), "substage_sum_mJ": f(substage)}

    readings = {
        "R0_total_denominator_competition_rank_table3_substages": reading(
            "Denominator is the Total row (the spec's agreement test); ties share a rank and the next rank is skipped; substage sum from breakdown Table 3 rows."),
        "R1_components_sum_denominator": reading(
            "As R0, but share denominator is the sum of the six components.", denom=components_sum),
        "R2_dense_rank": reading(
            "As R0, but ties share a rank and the next rank is not skipped.", style="dense"),
        "R3_table2_substages": reading(
            "As R0, but substage_sum_mJ sums the Table 2 per-substage energies in the staged file (CABAC 39, not 32).",
            substage=substage_t2),
    }

    # Printed factors in the file header, compared with the computed steps.
    fusion = re.search(r"fusion \+([\d.]+)x energy", head_text)
    magic = re.search(r"magic \+([\d.]+)x energy", head_text)
    within = re.search(r"within ([\d.]+)x of ASIC", head_text)
    if not (fusion and magic and within):
        raise SystemExit("printed step factors not found in staged header")
    printed = {"plus_op_fusion": Fraction(fusion.group(1)), "plus_magic": Fraction(magic.group(1)),
               "ASIC": Fraction(within.group(1))}
    step_vs_printed = {s: {"step_factor": factors[s]["step_factor"], "printed": f(p),
                           "step_over_printed": factors[s]["step_factor"] / f(p)}
                       for s, p in printed.items()}

    # Source comparison
    url = re.search(r"# PDF: (\S+)\s+sha256 ([0-9a-f]{64})", head_text)
    source = fetch_pdf(url.group(1), url.group(2))
    if source["available"]:
        source.update(compare_source(staged, breakdown))

    result = {
        "spec": "07-hameed-energy",
        "readings": readings,
        "checks": {
            "chart_read_tolerance": chart_checks,
            "base_over_asic_vs_asic_factor": vs_factor,
            "components_sum_equals_total": components_sum == total_mJ,
            "substage_sum_equals_total_table3": substage_t3 == total_mJ,
            "substage_sum_equals_total_table2": substage_t2 == total_mJ,
            "ties": ties,
            "step_vs_printed": step_vs_printed,
            "asic_efficiency_diagnostic": diagnostic,
        },
        "source_pdf": source,
        "input_counts": {"staged": staged_counts, "breakdown": break_counts},
        "input_sha256": {STAGED: sha256(STAGED), BREAKDOWN: sha256(BREAKDOWN)},
    }
    with open("result.json", "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
        fh.write("\n")
    print(json.dumps({k: result[k] for k in ("checks", "source_pdf", "input_counts")}, indent=1))
    for name, r in readings.items():
        print(name, r["total_mJ"], r["components_sum_mJ"], r["substage_sum_mJ"],
              {c: (v["share_pct_1dp"], v["rank"]) for c, v in r["components"].items()})
    print(json.dumps(factors, indent=1), energy_check)


if __name__ == "__main__":
    main()
