#!/usr/bin/env python3
"""Spec 10: H100 matched workloads. Run from this folder. Stdlib only; needs gh for the log refetch."""
import base64, concurrent.futures, csv, hashlib, json, math, os, random, statistics, subprocess, sys, time

DATA = "inputs/book/contents/chapters/09-patterns/data"
RUNS_CSV = f"{DATA}/mlperf-h100-runs.csv"
SHEETS = {"v2.1": f"{DATA}/mlperf-h100-sources/results-v2.1-sheet.csv",
          "v3.0": f"{DATA}/mlperf-h100-sources/results-v3.0-sheet.csv"}
SCALING = f"{DATA}/mlperf-h100-sources/v2.1-resnet-scaling.json"
PROVENANCE = f"{DATA}/provenance.yml"
LOG_DIR = "logs"
ORG = "mlcommons"  # from the source URLs in provenance.yml

# Workload label in the runs table -> task column name in both sheets.
COLUMN = {"ResNet-50 v1.5": "Image classification",
          "3D U-Net": "Image segmentation (medical)",
          "RetinaNet": "Object detection, light-weight",
          "Mask R-CNN": "Object detection, heavy-weight",
          "RNN-T": "Speech recognition",
          "BERT": "NLP"}
RESULT_ID = {"v2.1": {w: "2.1-2091" for w in COLUMN},
             "v3.0": {"BERT": "3.0-2064", "RNN-T": "3.0-2064", "Mask R-CNN": "3.0-2064",
                      "RetinaNet": "3.0-2064", "ResNet-50 v1.5": "3.0-2062", "3D U-Net": "3.0-2062"}}
WORKLOADS = list(COLUMN)
RESNET = "ResNet-50 v1.5"
UNET = "3D U-Net"


def provenance_scalar(key):
    """Read draws and seed from the provenance environment sentence, not from a literal here."""
    text = open(PROVENANCE).read()
    line = next(l for l in text.splitlines() if l.startswith("environment:"))
    words = line.replace(",", " ").split()
    if key == "seed":
        return int(words[words.index("seed") + 1])
    if key == "draws":
        return int(words[words.index("draws") - 1])
    raise ValueError(key)


def load_table():
    with open(RUNS_CSV, newline="") as f:
        return list(csv.DictReader(l for l in f if not l.startswith("#")))


def load_published():
    out = {}
    for rnd, path in SHEETS.items():
        rows = list(csv.reader(open(path, newline="")))
        head = rows[1]
        col = {w: head.index(name) for w, name in COLUMN.items()}
        out[rnd] = {}
        for w in WORKLOADS:
            hit = [r for r in rows if r and r[0] == RESULT_ID[rnd][w]]
            if len(hit) != 1:
                raise SystemExit(f"{rnd} {w}: {len(hit)} sheet rows for {RESULT_ID[rnd][w]}")
            out[rnd][w] = hit[0][col[w]].strip()
    return out


def fetch_one(row):
    """Return (bytes or None, failure string or None). Verifies the git blob SHA and the log sha256."""
    sha, want256 = row["git_blob_sha"], row["log_sha256"]
    path = os.path.join(LOG_DIR, want256 + ".txt")
    if os.path.exists(path):
        data = open(path, "rb").read()
    else:
        p = subprocess.run(["gh", "api", f"repos/{ORG}/{row['repo']}/git/blobs/{sha}"],
                           capture_output=True)
        if p.returncode != 0:
            return None, f"gh rc={p.returncode}: {p.stderr.decode(errors='replace')[:200]}"
        blob = json.loads(p.stdout)
        data = base64.b64decode(blob["content"])
    blobsha = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
    if blobsha != sha:
        return None, f"git blob sha mismatch: got {blobsha}"
    got256 = hashlib.sha256(data).hexdigest()
    if got256 != want256:
        return None, f"log sha256 mismatch: got {got256}"
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(data)
    return data, None


def parse_log(data, position_key):
    """Extract run_start, run_stop, status, and eval events from one MLLOG file."""
    starts, stops, evals, bad, malformed_eval_position = [], [], [], 0, 0
    for line in data.decode("utf-8", errors="replace").splitlines():
        at = line.find(":::MLLOG ")
        if at < 0:
            continue
        try:
            e = json.loads(line[at + len(":::MLLOG "):])
        except json.JSONDecodeError:
            bad += 1
            continue
        key = e.get("key")
        if key == "run_start":
            starts.append(e["time_ms"])
        elif key == "run_stop":
            stops.append((e["time_ms"], e["metadata"].get("status")))
        elif key == "eval_accuracy":
            if position_key in e["metadata"]:
                evals.append((e["value"], e["metadata"][position_key]))
            else:
                malformed_eval_position += 1
    return {"starts": starts, "stops": stops, "evals": evals, "malformed_lines": bad,
            "evals_without_position": malformed_eval_position}


def eval_value_pair(value, table_text):
    """Scalars compare as numbers. A dict value (Mask R-CNN) compares as its Python repr, as the table prints it."""
    if isinstance(value, dict):
        return str(value), table_text
    return float(value), float(table_text)


def refetch(rows):
    """Refetch and re-extract every run. Returns (runs or None, report)."""
    os.makedirs(LOG_DIR, exist_ok=True)
    report = {"attempted": len(rows), "fetched_and_hash_verified": 0, "failures": [],
              "multi_event_runs": [], "malformed_mllog_lines": 0, "evals_without_position": 0,
              "field_mismatches": []}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        fetched = list(ex.map(fetch_one, rows))
    runs = []
    for row, (data, fail) in zip(rows, fetched):
        if fail:
            report["failures"].append({"file": f"{row['round']}/{row['system']}/{row['file']}", "reason": fail})
            continue
        report["fetched_and_hash_verified"] += 1
        p = parse_log(data, row["position_key"])
        report["malformed_mllog_lines"] += p["malformed_lines"]
        report["evals_without_position"] += p["evals_without_position"]
        ident = f"{row['round']}/{row['system']}/{row['file']}"
        if len(p["starts"]) != 1 or len(p["stops"]) != 1:
            report["multi_event_runs"].append({"file": ident, "run_start": len(p["starts"]), "run_stop": len(p["stops"])})
        if not p["starts"] or not p["stops"] or not p["evals"]:
            report["failures"].append({"file": ident, "reason": "missing run_start, run_stop, or evals"})
            continue
        start, (stop, status) = p["starts"][0], p["stops"][-1]
        t = (stop - start) / 60000.0
        last_value, last_pos = p["evals"][-1]
        fields = {"run_start_ms": (start, int(row["run_start_ms"])),
                  "run_stop_ms": (stop, int(row["run_stop_ms"])),
                  "time_min": (round(t, 6), float(row["time_min"])),
                  "status": (status, row["status"]),
                  "eval_count": (len(p["evals"]), int(row["eval_count"])),
                  "last_eval_position": (float(last_pos), float(row["last_eval_position"])),
                  "last_eval_value": eval_value_pair(last_value, row["last_eval_value"]),
                  "log_bytes": (len(data), int(row["log_bytes"]))}
        for name, (mine, theirs) in fields.items():
            if mine != theirs:
                report["field_mismatches"].append({"file": ident, "field": name, "refetched": mine, "table": theirs})
        runs.append({"round": row["round"], "workload": row["workload"], "result_id": row["result_id"],
                     "time": t, "ok": status == "success", "pos": float(last_pos)})
    return (runs if not report["failures"] else None), report


def table_runs(rows):
    return [{"round": r["round"], "workload": r["workload"], "result_id": r["result_id"],
             "time": float(r["time_min"]), "ok": r["status"] == "success",
             "pos": float(r["last_eval_position"])} for r in rows]


def rule(items, k):
    """Non-success ranks slower than every success. Returns (mean of kept, kept includes a non-success)."""
    s = sorted(items, key=lambda r: (not r["ok"], r["time"]))
    kept = s[k:len(s) - k] if k else s
    if not kept:
        raise ValueError(f"no runs left after dropping {k} from each end of {len(s)}")
    return sum(r["time"] for r in kept) / len(kept), any(not r["ok"] for r in kept)


def rule_kept(items, k):
    s = sorted(items, key=lambda r: (not r["ok"], r["time"]))
    return s[k:len(s) - k] if k else s


def fit_k(items, published, factor):
    """All k tried; a k matches when the score prints as the sheet prints it (3 decimals here)."""
    decimals = len(published.split(".")[1])
    tried, matches = [], []
    for k in range((len(items) - 1) // 2 + 1):
        v, aborted_kept = rule(items, k)
        scaled = v * factor
        printed = f"{scaled:.{decimals}f}"
        hit = printed == published
        tried.append({"k": k, "score": v, "scaled": scaled, "printed": printed, "match": hit,
                      "aborted_retained": aborted_kept})
        if hit:
            matches.append(k)
    return matches, tried


# Draw families. Each returns the pair of resamples for one draw, or None when the draw is unusable.
def draw_independent(a, b, rng, ka, kb):
    return rng.choices(a, k=len(a)), rng.choices(b, k=len(b))


def draw_paired(a, b, rng, ka, kb):
    idx = rng.choices(range(len(a)), k=len(a))
    return [a[i] for i in idx], [b[i] for i in idx]


def draw_pooled(a, b, rng, ka, kb):
    pool = [(0, r) for r in a] + [(1, r) for r in b]
    picked = rng.choices(pool, k=len(pool))
    x = [r for side, r in picked if side == 0]
    y = [r for side, r in picked if side == 1]
    if len(x) <= 2 * ka or len(y) <= 2 * kb:
        return None
    return x, y


FAMILIES = {"independent": draw_independent, "paired_index": draw_paired, "pooled_rounds": draw_pooled}
ABORTED = ("retain_time", "dnf_infinite", "exclude_draw")
K_POLICIES = {"k_tie_smallest": min, "k_tie_largest": max}


def collect(a, b, stat_a, stat_b, family, rng, draws, ka, kb):
    """Return (list of (num, den, flag_num, flag_den), unusable draw count)."""
    fn, out, unusable = FAMILIES[family], [], 0
    for _ in range(draws):
        pair = fn(a, b, rng, ka, kb)
        if pair is None:
            unusable += 1
            continue
        n, fn_flag = stat_a(pair[0])
        d, fd_flag = stat_b(pair[1])
        out.append((n, d, fn_flag, fd_flag))
    return out, unusable


def ratios(samples, aborted):
    """Apply an aborted reading to the draws. Returns (ratios, excluded count)."""
    out, excluded = [], 0
    for n, d, fn_flag, fd_flag in samples:
        if aborted == "retain_time" or not (fn_flag or fd_flag):
            out.append(n / d)
        elif aborted == "exclude_draw":
            excluded += 1
        elif fn_flag and fd_flag:
            excluded += 1  # infinity over infinity has no value
        elif fn_flag:
            out.append(math.inf)
        else:
            out.append(0.0)
    return sorted(out), excluded


def q_linear(s, p):
    h = (len(s) - 1) * p
    lo, hi = math.floor(h), math.ceil(h)
    if lo == hi:
        return s[lo]
    if s[lo] == s[hi]:
        return s[lo]
    return s[lo] + (s[hi] - s[lo]) * (h - lo)


def q_rank(s, p):
    """Lower order statistic at index floor(N*p), clipped."""
    return s[min(int(len(s) * p), len(s) - 1)]


def acceleration(a, b, stat_a, stat_b):
    """Two-sample jackknife acceleration of the ratio, leaving one run out of one round at a time."""
    va, vb = stat_a(a)[0], stat_b(b)[0]
    infl = []
    for side, items, stat in ((0, a, stat_a), (1, b, stat_b)):
        vals = []
        for i in range(len(items)):
            rest = items[:i] + items[i + 1:]
            try:
                v = stat(rest)[0]
            except ValueError:  # leave-one-out leaves no run after the drops (k=2 of 5)
                return None
            vals.append(v / vb if side == 0 else va / v)
        m = sum(vals) / len(vals)
        infl += [(len(vals) - 1) * (m - v) for v in vals]
    den = sum(x * x for x in infl) ** 1.5
    return sum(x ** 3 for x in infl) / (6 * den) if den else 0.0


def bca(sorted_r, theta, accel):
    """BCa percentile endpoints; ties at theta count half. Returns (low, high, note)."""
    if accel is None:
        return None, None, "jackknife acceleration undefined: a leave-one-out sample has no run left after the drops"
    nd = statistics.NormalDist()
    below = sum(1 for r in sorted_r if r < theta)
    ties = sum(1 for r in sorted_r if r == theta)
    frac = (below + 0.5 * ties) / len(sorted_r)
    if frac <= 0 or frac >= 1:
        return None, None, f"bias fraction {frac} is outside (0,1)"
    z0 = nd.inv_cdf(frac)
    ends = []
    for p in (0.025, 0.975):
        z = nd.inv_cdf(p)
        adj = nd.cdf(z0 + (z0 + z) / (1 - accel * (z0 + z)))
        ends.append(q_linear(sorted_r, adj))
    return ends[0], ends[1], None


def num(x):
    if x is None or math.isfinite(x):
        return x
    return "inf" if x > 0 else "-inf"


def interval(method, sorted_r, theta, accel):
    if method == "percentile_linear":
        return q_linear(sorted_r, 0.025), q_linear(sorted_r, 0.975), None
    if method == "percentile_lower_rank":
        return q_rank(sorted_r, 0.025), q_rank(sorted_r, 0.975), None
    if method == "bca":
        return bca(sorted_r, theta, accel)
    raise ValueError(method)


def includes(lo, hi):
    if lo is None or hi is None:
        return None
    return lo <= 1 <= hi


# Time-per-epoch aggregates over converged runs. Each returns (value, False).
def tpe_stats(k):
    def tpe(r):
        return r["time"] / r["pos"]

    def by_time(items):
        return sorted(items, key=lambda r: r["time"])[k:len(items) - k]

    def rule_on_tpe(items):
        s = sorted(items, key=tpe)[k:len(items) - k]
        return sum(tpe(r) for r in s) / len(s), False

    def mean_tpe_of_time_kept(items):
        s = by_time(items)
        return sum(tpe(r) for r in s) / len(s), False

    def mean_tpe_all(items):
        return sum(tpe(r) for r in items) / len(items), False

    def ratio_of_means_all(items):
        return sum(r["time"] for r in items) / sum(r["pos"] for r in items), False

    def ratio_of_means_time_kept(items):
        s = by_time(items)
        return sum(r["time"] for r in s) / sum(r["pos"] for r in s), False

    return {"rule_score_on_time_per_epoch": rule_on_tpe,
            "mean_time_per_epoch_of_runs_kept_by_time_rule": mean_tpe_of_time_kept,
            "mean_time_per_epoch_all_converged": mean_tpe_all,
            "mean_time_over_mean_epochs_all_converged": ratio_of_means_all,
            "mean_time_over_mean_epochs_runs_kept_by_time_rule": ratio_of_means_time_kept}


def main():
    t0 = time.time()
    rows = load_table()
    published = load_published()
    factor = json.load(open(SCALING))["scaling_factor"]
    seed, draws = provenance_scalar("seed"), provenance_scalar("draws")
    runs, refetch_report = refetch(rows)
    source = "refetched_logs" if runs is not None else "table_mlperf-h100-runs.csv"
    table = table_runs(rows)
    if runs is None:
        runs = table
    dropped = [{"file": x["file"], "why": x["reason"]} for x in refetch_report["failures"]]

    groups = {w: {rnd: [r for r in runs if r["workload"] == w and r["round"] == rnd
                        and r["result_id"] == RESULT_ID[rnd][w]] for rnd in ("v2.1", "v3.0")} for w in WORKLOADS}
    unused = len(runs) - sum(len(g) for w in WORKLOADS for g in groups[w].values())

    # Fit k. A k tie at printed precision is outside the spec's stop rule, so each tie policy is a reading.
    fits, stopped = {}, {}
    matches = {}
    for w in WORKLOADS:
        ks, fit_detail = {}, {}
        for rnd in ("v2.1", "v3.0"):
            f = factor if (w == RESNET and rnd == "v2.1") else 1.0
            ks[rnd], fit_detail[rnd] = fit_k(groups[w][rnd], published[rnd][w], f)
        fits[w] = fit_detail
        if not ks["v2.1"] or not ks["v3.0"]:
            stopped[w] = {"matching_k": ks}
        else:
            matches[w] = ks
    k_ties = {w: ks for w, ks in matches.items() if len(ks["v2.1"]) > 1 or len(ks["v3.0"]) > 1}

    bases, table_checks = {}, {}
    for policy, pick in K_POLICIES.items():
        base, table_check = {}, {}
        for w, ks in matches.items():
            kv21, kv30 = pick(ks["v2.1"]), pick(ks["v3.0"])
            s21, s30 = rule(groups[w]["v2.1"], kv21)[0], rule(groups[w]["v3.0"], kv30)[0]
            base[w] = {"k": kv21 if kv21 == kv30 else {"v2.1": kv21, "v3.0": kv30}, "k21": kv21, "k30": kv30,
                       "n_v21": len(groups[w]["v2.1"]), "n_v30": len(groups[w]["v3.0"]),
                       "score_v21": s21, "published_v21": float(published["v2.1"][w]),
                       "score_v30": s30, "published_v30": float(published["v3.0"][w]),
                       "ratio": s21 / s30}
            tg = {rnd: [r for r in table if r["workload"] == w and r["round"] == rnd] for rnd in ("v2.1", "v3.0")}
            table_check[w] = rule(tg["v2.1"], kv21)[0] / rule(tg["v3.0"], kv30)[0]
        bases[policy], table_checks[policy] = base, table_check

    def stats(base, wk):
        return ((lambda items: rule(items, base[wk]["k21"])), (lambda items: rule(items, base[wk]["k30"])))

    # Draws for each policy and family, on one stream per family, in workload order.
    samples, unusable, accels = {}, {}, {}
    for policy, base in bases.items():
        for family in FAMILIES:
            rng = random.Random(seed)
            for w in base:
                sa, sb = stats(base, w)
                got, u = collect(groups[w]["v2.1"], groups[w]["v3.0"], sa, sb, family, rng, draws,
                                 base[w]["k21"], base[w]["k30"])
                samples[(policy, family, w)], unusable[(policy, family, w)] = got, u
        accels[policy] = {w: acceleration(groups[w]["v2.1"], groups[w]["v3.0"], *stats(base, w)) for w in base}

    # Time per epoch on converged runs.
    tpe_samples, tpe_unusable, tpe_point, tpe_accel, tpe_excluded = {}, {}, {}, {}, None
    unet_k = matches[UNET]["v2.1"][0] if UNET in matches and matches[UNET]["v2.1"] == matches[UNET]["v3.0"] and len(matches[UNET]["v2.1"]) == 1 else None
    if unet_k is not None:
        k = unet_k
        a = [r for r in groups[UNET]["v2.1"] if r["ok"]]
        b = [r for r in groups[UNET]["v3.0"] if r["ok"]]
        tpe_excluded = {"v2.1": len(groups[UNET]["v2.1"]) - len(a), "v3.0": len(groups[UNET]["v3.0"]) - len(b)}
        for name, stat in tpe_stats(k).items():
            tpe_point[name] = stat(a)[0] / stat(b)[0]
            tpe_accel[name] = acceleration(a, b, stat, stat)
            for family in FAMILIES:
                rng = random.Random(seed)
                s, u = collect(a, b, stat, stat, family, rng, draws, k, k)
                tpe_samples[(family, name)], tpe_unusable[(family, name)] = s, u

    # Assemble the readings: interval method crossed with the handling of a retained non-success run.
    methods = {"percentile_linear_independent": ("independent", "percentile_linear"),
               "percentile_lower_rank_independent": ("independent", "percentile_lower_rank"),
               "bca_independent": ("independent", "bca"),
               "percentile_linear_joint_paired_index": ("paired_index", "percentile_linear"),
               "percentile_linear_joint_pooled_rounds": ("pooled_rounds", "percentile_linear")}
    readings = {}
    for policy, base in bases.items():
        for mname, (family, quant) in methods.items():
            for ab in ABORTED:
                workloads, counts = {}, {}
                for w in base:
                    r, excl = ratios(samples[(policy, family, w)], ab)
                    lo, hi, note = interval(quant, r, base[w]["ratio"], accels[policy][w])
                    entry = {x: base[w][x] for x in ("k", "n_v21", "n_v30", "score_v21", "published_v21",
                                                     "score_v30", "published_v30", "ratio")}
                    entry.update(ci_low=num(lo), ci_high=num(hi), includes_no_gain=includes(lo, hi))
                    if note:
                        entry["ci_note"] = note
                    workloads[w] = entry
                    counts[w] = {"draws_used": len(r), "excluded_by_aborted_reading": excl,
                                 "unusable_draw_too_few_runs": unusable[(policy, family, w)]}
                rn = base.get(RESNET)
                floor_w = min(base, key=lambda w: base[w]["ratio"])
                ceil_w = max(base, key=lambda w: base[w]["ratio"])
                tpe = []
                for name in tpe_point:
                    r, _ = ratios(tpe_samples[(family, name)], "retain_time")
                    lo, hi, note = interval(quant, r, tpe_point[name], tpe_accel[name])
                    item = {"aggregate": name, "ratio": tpe_point[name], "ci_low": num(lo), "ci_high": num(hi)}
                    if note:
                        item["ci_note"] = note
                    tpe.append(item)
                readings[f"{policy}__{mname}__{ab}"] = {
                    "workloads": workloads,
                    "resnet": {"scaling_factor": factor, "ratio_unscaled": rn["ratio"] if rn else None,
                               "ratio_published": (rn["published_v21"] / rn["published_v30"]) if rn else None},
                    "floor": {"workload": floor_w, "ratio": base[floor_w]["ratio"]},
                    "ceiling": {"workload": ceil_w, "ratio": base[ceil_w]["ratio"]},
                    "unet_time_per_epoch": tpe,
                    "bootstrap": {"draws": draws, "seed": seed,
                                  "rng": f"Python {sys.version.split()[0]} random.Random (MT19937), one stream per draw family",
                                  "method": f"{family} resampling; {quant}; non-success retained in a draw: {ab}; k tie: {policy}"},
                    "draw_counts": counts}

    # Monte Carlo sensitivity: reseed at each workload rather than sharing one stream.
    mc = {}
    for policy, base in bases.items():
        mc[policy] = {}
        for w in base:
            rng = random.Random(seed)
            sa, sb = stats(base, w)
            got, _ = collect(groups[w]["v2.1"], groups[w]["v3.0"], sa, sb, "independent", rng, draws,
                             base[w]["k21"], base[w]["k30"])
            r, _ = ratios(got, "retain_time")
            mc[policy][w] = {"ci_low": q_linear(r, 0.025), "ci_high": q_linear(r, 0.975)}

    result = {
        "readings": readings,
        "time_source": source,
        "refetch": refetch_report,
        "stopped_workloads": stopped,
        "k_fit": fits,
        "k_ties": k_ties,
        "ratio_from_table_times": table_checks,
        "reseed_each_workload_percentile_linear_independent_retain_time": mc,
        "time_per_epoch_nonconverged_excluded": tpe_excluded,
        "dropped_runs": dropped,
        "runs_outside_named_submissions": unused,
        "elapsed_s": round(time.time() - t0, 1)}
    with open("result.json", "w") as f:
        json.dump(result, f, indent=1, allow_nan=False)
    print(json.dumps({"source": source, "stopped": stopped, "fetched": refetch_report["fetched_and_hash_verified"],
                      "fail": len(refetch_report["failures"]), "mismatch": len(refetch_report["field_mismatches"]),
                      "readings": len(readings), "elapsed_s": result["elapsed_s"]}))


if __name__ == "__main__":
    main()
