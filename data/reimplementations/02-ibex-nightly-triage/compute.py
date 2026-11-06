#!/usr/bin/env python3
"""Spec 02: Ibex nightly plateaus and triage. Run from this folder: python3 -I compute.py"""
import collections
import concurrent.futures as cf
import csv
import datetime as dt
import hashlib
import http.client
import json
import math
import re
import ssl
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

HERE = Path.cwd()
STUDIES = HERE / "inputs/data/studies"
MANIFEST = STUDIES / "28-ibex-nightly-history/manifest.csv"
SNAPSHOT = STUDIES / "16-regression-records/raw/ibex-opentitan-latest-report.json"
TRIAGE_DIR = STUDIES / "22-ibex-triage/source"
FETCHED = HERE / "fetched"

FAMILIES = {
    "riscv_assorted_traps_interrupts_debug_test",
    "riscv_pmp_basic_test",
    "riscv_pmp_out_of_bounds_test",
    "riscv_pmp_full_random_test",
}

# Method parameters, fixed before the series was looked at.
MIN_SEG = 14
K_RANGE = range(3, 13)
K_MAX_BIC = 20
THRESHOLDS_PP = (1.0, 2.0)
THRESH_WINDOW = 7
STEADY_MIN_REPORTS = 30
STEADY_SD_LIMIT = 0.5
DIRECT_SD_LIMITS = (0.25, 0.5)
DIRECT_WINDOWS = (90, 180)
CA_FILE = "/etc/ssl/cert.pem"  # this Python build ships no CA bundle; sha256 is the integrity check
TLS = ssl.create_default_context(cafile=CA_FILE)
FETCH_ERRORS = (urllib.error.URLError, TimeoutError, http.client.HTTPException, ConnectionError)


def fetch_row(row):
    """Return (key, path or None, failure or None). Cached copies are re-hashed."""
    path = FETCHED / row["key"].replace("/", "_")
    want = row["sha256"]
    if path.exists():
        if hashlib.sha256(path.read_bytes()).hexdigest() == want:
            return row["key"], path, None
        path.unlink()
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(row["url"], headers={"User-Agent": "spec02-reimpl"})
            with urllib.request.urlopen(req, timeout=60, context=TLS) as resp:
                body = resp.read()
        except FETCH_ERRORS as exc:
            last = f"fetch failed: {type(exc).__name__}: {exc}"
            time.sleep(1 + attempt)
            continue
        got = hashlib.sha256(body).hexdigest()
        if got != want:
            return row["key"], None, f"sha256 mismatch: got {got}, want {want}"
        path.write_bytes(body)
        return row["key"], path, None
    return row["key"], None, last


def parse_report(path, drops):
    """Parse one report. Rows that do not fit the shape are dropped and counted."""
    doc = json.loads(path.read_text())
    res = doc["results"]
    rows = []
    for item in res["unmapped_tests"]:
        name, p, t = item.get("name"), item.get("passing_runs"), item.get("total_runs")
        if not isinstance(name, str) or not isinstance(p, int) or not isinstance(t, int):
            drops["row_bad_type"] += 1
            continue
        if p > t or p < 0:
            drops["row_pass_outside_range"] += 1
            continue
        rows.append((name, p, t))
    return {"rows": rows, "testpoints": len(res.get("testpoints") or [])}


def summarize(rep):
    names = [r[0] for r in rep["rows"]]
    passing = sum(r[1] for r in rep["rows"])
    total = sum(r[2] for r in rep["rows"])
    nonpass = collections.Counter()
    for name, p, t in rep["rows"]:
        nonpass[name] += t - p
    return {
        "passing": passing,
        "total": total,
        "rate": 100.0 * passing / total if total else None,
        "failing": {r[0] for r in rep["rows"] if r[1] < r[2]},
        "failing_rows": sum(1 for r in rep["rows"] if r[1] < r[2]),
        "zero_groups": sum(1 for r in rep["rows"] if r[2] == 0),
        "n_groups": len(rep["rows"]),
        "dup_names": len(names) - len(set(names)),
        "nonpass": nonpass,
        "testpoints": rep["testpoints"],
    }


# ---- segmentation ----

def dp_segments(x, kmax, min_seg):
    """Optimal L2 partition. Returns {k: (rss, boundaries)}; boundaries are segment start indices."""
    n = len(x)
    p1 = np.concatenate(([0.0], np.cumsum(x)))
    p2 = np.concatenate(([0.0], np.cumsum(x * x)))

    def cost_to(j):  # cost of x[i:j] for every i in 0..j-1
        i = np.arange(j)
        ln = j - i
        return (p2[j] - p2[i]) - (p1[j] - p1[i]) ** 2 / ln

    D = np.full((kmax + 1, n + 1), np.inf)
    back = np.zeros((kmax + 1, n + 1), dtype=int)
    D[0, 0] = 0.0
    for k in range(1, kmax + 1):
        for j in range(k * min_seg, n + 1):
            lo = (k - 1) * min_seg
            hi = j - min_seg
            if hi < lo:
                continue
            c = D[k - 1, lo:hi + 1] + cost_to(j)[lo:hi + 1]
            m = int(np.argmin(c))
            D[k, j], back[k, j] = c[m], lo + m
    out = {}
    for k in range(1, kmax + 1):
        if not math.isfinite(D[k, n]):
            continue
        bounds, j = [], n
        for kk in range(k, 0, -1):
            j = int(back[kk, j])
            bounds.append(j)
        out[k] = (float(D[k, n]), sorted(bounds))
    return out


def bic_k(segs, n):
    score = {k: n * math.log(max(rss, 1e-12) / n) + (2 * k - 1) * math.log(n) for k, (rss, _) in segs.items()}
    return min(score, key=score.get)


def threshold_segments(x, t, w, min_seg):
    """Step where |median(next w) - median(previous w)| >= t; strongest first, min_seg apart."""
    n = len(x)
    stat = {i: abs(float(np.median(x[i:i + w])) - float(np.median(x[i - w:i]))) for i in range(w, n - w + 1)}
    chosen = []
    for i in sorted(stat, key=lambda i: (-stat[i], i)):
        if stat[i] < t:
            break
        if i < min_seg or n - i < min_seg:
            continue
        if all(abs(i - c) >= min_seg for c in chosen):
            chosen.append(i)
    return [0] + sorted(chosen)


def rolling_median(x, w):
    h = w // 2
    return np.array([np.median(x[max(0, i - h):i + h + 1]) for i in range(len(x))])


# ---- statistics ----

def churn_stats(nights, a, b):
    all_d, gap1 = [], []
    for i in range(a, b - 1):
        d = len(nights[i]["failing"] ^ nights[i + 1]["failing"])
        all_d.append(d)
        if (nights[i + 1]["day"] - nights[i]["day"]).days == 1:
            gap1.append(d)
    return all_d, gap1


def interval(nights, a, b):
    """Statistics over reports a..b-1."""
    r = [n["rate"] for n in nights[a:b]]
    fails = [len(n["failing"]) for n in nights[a:b]]
    churn, gap1 = churn_stats(nights, a, b)
    return {
        "start": nights[a]["date"],
        "end": nights[b - 1]["date"],
        "n_reports": b - a,
        "mean_pct": statistics.fmean(r),
        "sd_pct_sample": statistics.stdev(r) if len(r) > 1 else None,
        "sd_pct_population": statistics.pstdev(r),
        "median_failing": statistics.median(fails),
        "distinct_failing": len(set().union(*(n["failing"] for n in nights[a:b]))),
        "churn_mean": statistics.fmean(churn) if churn else None,
        "churn_median": statistics.median(churn) if churn else None,
        "churn_mean_gap1day_only": statistics.fmean(gap1) if gap1 else None,
        "churn_median_gap1day_only": statistics.median(gap1) if gap1 else None,
        "churn_pairs": len(churn),
        "churn_pairs_gap1day": len(gap1),
    }


def mean_nonpass(nights, a, b):
    out = collections.Counter()
    for n in nights[a:b]:
        for g, v in n["nonpass"].items():
            out[g] += v
    return {g: v / (b - a) for g, v in out.items()}


def attribute(before, after):
    """Group with the largest nonpassing change in the direction of the total change."""
    groups = set(before) | set(after)
    delta = {g: after.get(g, 0) - before.get(g, 0) for g in groups}
    total = sum(delta.values())
    if total == 0:
        return None, None, 0
    sign = 1 if total > 0 else -1
    top = max(sorted(groups), key=lambda g: sign * delta[g])
    return top, delta[top] / total, total


def step_record(nights, l_a, l_b, r_a, r_b):
    """Step between report ranges. Share is delta(group nonpass) / delta(all nonpass)."""
    left = statistics.fmean(n["rate"] for n in nights[l_a:l_b])
    right = statistics.fmean(n["rate"] for n in nights[r_a:r_b])
    top, share, total = attribute(mean_nonpass(nights, l_a, l_b), mean_nonpass(nights, r_a, r_b))
    top2, share2, total2 = attribute(mean_nonpass(nights, l_b - 1, l_b), mean_nonpass(nights, r_a, r_a + 1))
    return {
        "date": nights[r_a]["date"],
        "delta_pct": right - left,
        "top_group": top,
        "top_group_share": share,
        "delta_nonpassing_all": total,
        "top_group_adjacent_reports": top2,
        "top_group_share_adjacent_reports": share2,
        "delta_nonpassing_all_adjacent_reports": total2,
    }


def night_to_night_steps(nights, count=2):
    idx = sorted(range(1, len(nights)), key=lambda i: -abs(nights[i]["rate"] - nights[i - 1]["rate"]))
    return [step_record(nights, i - 1, i, i, i + 1) for i in idx[:count]]


def boundary_steps(nights, bounds, count=2):
    edges = bounds + [len(nights)]
    recs = [step_record(nights, edges[i - 1], edges[i], edges[i], edges[i + 1]) for i in range(1, len(bounds))]
    return sorted(recs, key=lambda r: -abs(r["delta_pct"]))[:count]


def direct_longest(x, limit):
    """Longest contiguous window with sample SD <= limit; ties go to lower SD, then earlier."""
    n = len(x)
    p1 = np.concatenate(([0.0], np.cumsum(x)))
    p2 = np.concatenate(([0.0], np.cumsum(x * x)))
    best = None
    for ln in range(n, 1, -1):
        a = np.arange(0, n - ln + 1)
        var = np.maximum(((p2[a + ln] - p2[a]) - (p1[a + ln] - p1[a]) ** 2 / ln) / (ln - 1), 0)
        ok = np.where(var <= limit * limit)[0]
        if len(ok):
            s = ok[np.argmin(var[ok])]
            best = (int(s), int(s + ln))
            break
    return best


def direct_lowest(x, ln):
    n = len(x)
    if n < ln:
        return None
    p1 = np.concatenate(([0.0], np.cumsum(x)))
    p2 = np.concatenate(([0.0], np.cumsum(x * x)))
    a = np.arange(0, n - ln + 1)
    var = ((p2[a + ln] - p2[a]) - (p1[a + ln] - p1[a]) ** 2 / ln) / (ln - 1)
    s = int(np.argmin(var))
    return s, s + ln


# ---- logs ----

CASE_RE = re.compile(r"^(\S+?)\.(\d+):\s+(\S.*?)\s*$")
SUMMARY_RE = re.compile(r"^([\d.]+)% PASS (\d+) PASSED, (\d+) FAILED\s*$")


def parse_log(path):
    """Case rows are test.seed: status. Lines in the failure-details section never carry that form."""
    cases, other_status, summary = [], collections.Counter(), None
    for line in path.read_text(errors="replace").splitlines():
        m = SUMMARY_RE.match(line)
        if m and summary is None:
            summary = {"pct": float(m[1]), "passed": int(m[2]), "failed": int(m[3])}
            continue
        m = CASE_RE.match(line)
        if not m:
            continue
        status = m[3]
        if status == "PASS":
            cases.append((m[1], m[2], False))
        elif status in ("FAILED", "FAILED {T}"):
            cases.append((m[1], m[2], True))
        else:
            other_status[status[:40]] += 1
    failed = [c for c in cases if c[2]]
    ids = [(c[0], c[1]) for c in cases]
    return {
        "total": len(cases),
        "failed": len(failed),
        "passed": len(cases) - len(failed),
        "families_failed": sum(1 for c in failed if c[0] in FAMILIES),
        "other_tests_failed": sum(1 for c in failed if c[0] not in FAMILIES),
        "summary": summary,
        "reconciles": summary is not None and summary["passed"] == len(cases) - len(failed) and summary["failed"] == len(failed),
        "duplicate_case_ids": len(ids) - len(set(ids)),
        "failed_ids": sorted((c[0], c[1]) for c in failed),
        "all_ids": sorted(ids),
        "unrecognized_status_rows": dict(other_status),
    }


NUMBERED_RE = re.compile(r"^(\d+)\.\s")
BULLET_RE = re.compile(r"^\s*-\s+(\S+)\.(\d+)\s+-\s+Signature\s+(\d+)\s*$")
RTL_PHRASE = "Possible RTL bug"


def parse_issue(body):
    """Split the body at '# ' headings into regressions. Each has numbered explanations and bullet rows."""
    regressions, cur, section, current_k = [], None, None, None
    other_bullets = 0
    for line in body.splitlines():
        if line.startswith("# "):
            cur, section, current_k = None, None, None
            if "Regression" in line:
                cur = {"title": line[2:].strip(), "explanations": {}, "rows": []}
                regressions.append(cur)
            continue
        if cur is None:
            continue
        if line.startswith("## "):
            section = "failures" if line[3:].strip().lower() == "failures" else "explanations"
            current_k = None
            continue
        if section == "explanations":
            m = NUMBERED_RE.match(line)
            if m:
                current_k = int(m[1])
                cur["explanations"][current_k] = line
            elif current_k is not None:
                cur["explanations"][current_k] += "\n" + line
        elif section == "failures":
            m = BULLET_RE.match(line)
            if m:
                cur["rows"].append((m[1], m[2], int(m[3])))
            elif line.lstrip().startswith("- "):
                other_bullets += 1
    return regressions, other_bullets


def map_run(rows, explanations, failed_ids, all_ids):
    """Count mapped cases. A row outside the failed set is counted and kept out of mapped."""
    ok = [r for r in rows if (r[0], r[1]) in failed_ids]
    unique = {(r[0], r[1]) for r in ok}
    rtl = {(r[0], r[1]) for r in ok if RTL_PHRASE in explanations.get(r[2], "")}
    return {
        "bullet_rows": len(rows),
        "mapped": len(unique),
        "duplicate_rows": len(ok) - len(unique),
        "rows_not_failed_in_log": [f"{r[0]}.{r[1]}" for r in rows if (r[0], r[1]) not in failed_ids],
        "rows_absent_from_log": [f"{r[0]}.{r[1]}" for r in rows if (r[0], r[1]) not in all_ids],
        "rows_unknown_signature": [f"{r[0]}.{r[1]}" for r in rows if r[2] not in explanations],
        "rtl": len(rtl),
        "rtl_cases": sorted(f"{a}.{b}" for a, b in rtl),
        "by_signature": dict(sorted(collections.Counter(r[2] for r in ok).items())),
        "n_signatures_explained": len(explanations),
        "mapped_outside_families": len({(r[0], r[1]) for r in ok if r[0] not in FAMILIES}),
        "mapped_inside_families": len({(r[0], r[1]) for r in ok if r[0] in FAMILIES}),
    }


def main():
    t0 = time.time()
    not_computed = []
    drops = collections.Counter()
    FETCHED.mkdir(exist_ok=True)

    # single report
    snap = summarize(parse_report(SNAPSHOT, drops))
    single = {
        "passing_runs": snap["passing"], "total_runs": snap["total"], "pass_pct": snap["rate"],
        "failing_groups": snap["failing_rows"], "total_groups": snap["n_groups"],
        "zero_run_groups": snap["zero_groups"], "duplicate_group_names": snap["dup_names"],
        "nonempty_testpoints": snap["testpoints"],
    }

    # triage: only what the available inputs support
    log1 = TRIAGE_DIR / "regr-first.log"
    log2 = TRIAGE_DIR / "regr-second.log"
    issue = TRIAGE_DIR / "issue-2187.json"
    r1 = parse_log(log1) if log1.exists() else None
    r2 = parse_log(log2) if log2.exists() else None
    triage = {k: None for k in (
        "run1_failed run1_total run2_failed run2_total failed_pooled mapped mapped_run1 mapped_run2 "
        "rtl_mapped non_rtl_mapped unmapped coverage_pct non_rtl_per_rtl families_failed_run1 "
        "families_failed_run2 other_tests_failed_run2 unmapped_run2").split()}
    if r1:
        triage.update(run1_failed=r1["failed"], run1_total=r1["total"], families_failed_run1=r1["families_failed"])
    else:
        not_computed.append({"part": "triage.run1", "reason": f"input missing: {log1.relative_to(HERE)}"})
    if r2:
        triage.update(run2_failed=r2["failed"], run2_total=r2["total"], families_failed_run2=r2["families_failed"],
                      other_tests_failed_run2=r2["other_tests_failed"])
    else:
        not_computed.append({"part": "triage: run2_failed, run2_total, failed_pooled, families_failed_run2, other_tests_failed_run2",
                             "reason": f"input missing: {log2.relative_to(HERE)}"})
    if r1 and r2:
        triage["failed_pooled"] = r1["failed"] + r2["failed"]
    triage_detail = None
    triage_readings = None
    if not issue.exists():
        not_computed.append({"part": "triage mapping", "reason": f"input missing: {issue.relative_to(HERE)}"})
    elif r1 and r2:
        regs, other_bullets = parse_issue(json.loads(issue.read_text())["body"])
        drops["issue_bullet_not_a_mapping_row"] += other_bullets
        if len(regs) != 2:
            raise ValueError(f"expected 2 regressions in the issue body, found {len(regs)}")
        m1 = map_run(regs[0]["rows"], regs[0]["explanations"], set(r1["failed_ids"]), set(r1["all_ids"]))
        m2 = map_run(regs[1]["rows"], regs[1]["explanations"], set(r2["failed_ids"]), set(r2["all_ids"]))
        for m in (m1, m2):
            drops["mapping_row_not_failed_in_log"] += len(m["rows_not_failed_in_log"])
            drops["mapping_row_duplicate"] += m["duplicate_rows"]
        mapped = m1["mapped"] + m2["mapped"]
        rtl = m1["rtl"] + m2["rtl"]
        pooled = r1["failed"] + r2["failed"]
        triage.update(
            mapped=mapped, mapped_run1=m1["mapped"], mapped_run2=m2["mapped"], rtl_mapped=rtl,
            non_rtl_mapped=mapped - rtl, unmapped=pooled - mapped, coverage_pct=100.0 * mapped / pooled,
            non_rtl_per_rtl=(mapped - rtl) / rtl if rtl else None, unmapped_run2=r2["failed"] - m2["mapped"])
        triage_detail = {
            "run1": m1, "run2": m2,
            "unmapped_run1": r1["failed"] - m1["mapped"],
            "unmapped_run1_inside_families": r1["families_failed"] - m1["mapped_inside_families"],
            "unmapped_run1_outside_families": r1["other_tests_failed"] - m1["mapped_outside_families"],
            "unmapped_run2_inside_families": r2["families_failed"] - m2["mapped_inside_families"],
            "unmapped_run2_outside_families": r2["other_tests_failed"] - m2["mapped_outside_families"],
        }
        triage_readings = [
            {"reading": "compared_all_failures_outside_families", "compared_second_run_failures": r2["other_tests_failed"]},
            {"reading": "compared_unmapped_second_run_failures_only", "compared_second_run_failures": r2["failed"] - m2["mapped"]},
        ]

    # archive: fetch all, stop this part on any failure
    rows = list(csv.DictReader(MANIFEST.open(newline="")))
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        fetched = list(ex.map(fetch_row, rows))
    failures = [{"key": k, "reason": why} for k, _, why in fetched if why]
    paths = {k: p for k, p, why in fetched if not why}
    base = {
        "single_report": single,
        "triage": triage,
    }
    out = {
        "spec": "02-ibex-nightly-triage",
        "not_computed": not_computed,
        "fetch": {"rows": len(rows), "ok": len(paths), "failed": len(failures), "failures": failures[:50]},
        "log_checks": {
            name: {k: v for k, v in r.items() if k not in ("failed_ids", "all_ids")}
            for name, r in (("regr-first.log", r1), ("regr-second.log", r2)) if r
        },
        "triage_detail": triage_detail,
        "triage_readings": triage_readings,
        "triage_input_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (log1, log2, issue) if p.exists()
        },
        "parameters": {
            "min_segment_reports": MIN_SEG, "k_range": [K_RANGE[0], K_RANGE[-1]], "bic_k_max": K_MAX_BIC,
            "threshold_pp": THRESHOLDS_PP, "threshold_window_reports": THRESH_WINDOW,
            "steady_min_reports": STEADY_MIN_REPORTS, "steady_sd_limit_pp": STEADY_SD_LIMIT,
            "direct_sd_limits_pp": DIRECT_SD_LIMITS, "direct_windows_reports": DIRECT_WINDOWS,
        },
    }
    if failures:
        not_computed.append({"part": "archive, plateaus, steps", "reason": f"{len(failures)} of {len(rows)} fetches failed or mismatched"})
        out["readings"] = [dict(base, reading="no_archive", archive=None, segmentation_method=None, plateaus=None,
                                steadiest_start=None, steadiest_end=None, largest_steps=None)]
    else:
        out.update(archive_part(rows, paths, drops, base, snap))
    out["dropped"] = dict(drops)
    out["elapsed_s"] = time.time() - t0
    (HERE / "result.json").write_text(json.dumps(out, indent=1, sort_keys=False) + "\n")
    print(f"readings={len(out['readings'])} fetch_ok={len(paths)}/{len(rows)} drops={dict(drops)} elapsed={out['elapsed_s']:.1f}s")


def archive_part(rows, paths, drops, base, snap):
    by_date = collections.defaultdict(list)
    for r in rows:
        by_date[r["date"]].append(r)
    nights = []
    date_name_mismatch = 0
    objects_with_testpoints = 0
    objects_zero_groups = 0
    for r in rows:
        rep = parse_report(paths[r["key"]], drops)
        objects_with_testpoints += rep["testpoints"] > 0
        objects_zero_groups += any(x[2] == 0 for x in rep["rows"])
    for date in sorted(by_date):
        group = by_date[date]
        keep = [r for r in group if not r["key"].startswith("/")]
        if len(group) > 1:
            drops["object_same_date_leading_slash"] += len(group) - len(keep)
        if len(keep) != 1:
            raise ValueError(f"{date}: {len(keep)} rows after slash rule")
        r = keep[0]
        m = re.search(r"-(\d\d)-(\d\d)-(\d{4})\.json$", r["key"])
        if not m or f"{m[3]}-{m[2]}-{m[1]}" != date:
            date_name_mismatch += 1
        s = summarize(parse_report(paths[r["key"]], drops))
        s.update(date=date, day=dt.date.fromisoformat(date), key=r["key"], sha=r["sha256"])
        if s["rate"] is None:
            drops["night_zero_total_runs"] += 1
        nights.append(s)
    all_nights = nights
    series = [n for n in nights if n["rate"] is not None]
    x = np.array([n["rate"] for n in series])
    n = len(series)

    snap_bytes_sha = hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest()
    snap_match = [r["date"] for r in rows if r["sha256"] == snap_bytes_sha]

    archive = {
        "n_objects": len(rows), "n_nights": len(all_nights),
        "first_date": all_nights[0]["date"], "last_date": all_nights[-1]["date"],
        "nights_with_testpoints": sum(1 for s in all_nights if s["testpoints"] > 0),
        "groups_zero_runs_nights": sum(1 for s in all_nights if s["zero_groups"] > 0),
        "group_nights_zero_runs": sum(s["zero_groups"] for s in all_nights),
        "objects_with_testpoints": int(objects_with_testpoints),
        "objects_with_zero_run_groups": int(objects_zero_groups),
        "nights_with_duplicate_group_names": sum(1 for s in all_nights if s["dup_names"]),
        "nights_zero_total_runs": len(all_nights) - n,
        "key_date_mismatches": date_name_mismatch,
        "snapshot_sha256_matches_manifest_dates": snap_match,
    }

    n2n = night_to_night_steps(series)
    readings = []
    full_stats = interval(series, 0, n)

    segmentations = []
    med = rolling_median(x, 7)
    for label, sig in (("raw", x), ("med7", med)):
        segs = dp_segments(sig, K_MAX_BIC, MIN_SEG)
        for k in K_RANGE:
            segmentations.append((f"dp_l2_{label}_k{k}", f"optimal L2 partition of {label} nightly pass rate, k={k}, min {MIN_SEG} reports", segs[k][1]))
        kb = bic_k(segs, n)
        segmentations.append((f"dp_l2_{label}_bic", f"optimal L2 partition of {label} rate, k={kb} chosen by BIC over 1..{K_MAX_BIC}, min {MIN_SEG} reports", segs[kb][1]))
    for t in THRESHOLDS_PP:
        segmentations.append((f"step_t{t:g}pp", f"boundary where |median(next {THRESH_WINDOW})-median(previous {THRESH_WINDOW})| >= {t:g} pp, strongest first, min {MIN_SEG} reports apart",
                              threshold_segments(x, t, THRESH_WINDOW, MIN_SEG)))

    for name, desc, bounds in segmentations:
        edges = bounds + [n]
        plateaus = [interval(series, edges[i], edges[i + 1]) for i in range(len(bounds))]
        steps = boundary_steps(series, bounds)
        for score, pick in (("lowest_sd_ge30", lambda: pick_lowest(plateaus)), ("longest_sd_le0.5", lambda: pick_longest(plateaus))):
            best = pick()
            readings.append(dict(
                base, reading=f"{name}__{score}", archive=archive,
                segmentation_method=f"{desc}; steadiest = {score}", plateaus=plateaus,
                steadiest_start=best["start"] if best else None, steadiest_end=best["end"] if best else None,
                steadiest_stats=best, largest_steps=steps))

    direct = []
    for lim in DIRECT_SD_LIMITS:
        direct.append((f"direct_longest_sd_le{lim:g}", f"longest contiguous window of reports with sample SD <= {lim:g} pp, no segmentation", direct_longest(x, lim)))
    for ln in DIRECT_WINDOWS:
        direct.append((f"direct_lowest_sd_{ln}reports", f"lowest sample SD over all windows of {ln} reports, no segmentation", direct_lowest(x, ln)))
    for name, desc, win in direct:
        st = interval(series, *win) if win else None
        readings.append(dict(
            base, reading=name, archive=archive, segmentation_method=desc, plateaus=[st] if st else [],
            steadiest_start=st["start"] if st else None, steadiest_end=st["end"] if st else None,
            steadiest_stats=st, largest_steps=n2n))
    return {"readings": readings, "largest_steps_night_to_night": n2n, "full_series_stats": full_stats}


def pick_lowest(plateaus):
    c = [p for p in plateaus if p["n_reports"] >= STEADY_MIN_REPORTS]
    return min(c, key=lambda p: (p["sd_pct_sample"], p["start"])) if c else None


def pick_longest(plateaus):
    c = [p for p in plateaus if p["sd_pct_sample"] is not None and p["sd_pct_sample"] <= STEADY_SD_LIMIT]
    return max(c, key=lambda p: (p["n_reports"], -p["sd_pct_sample"])) if c else None


if __name__ == "__main__":
    main()
