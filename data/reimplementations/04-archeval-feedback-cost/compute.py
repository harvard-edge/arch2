#!/usr/bin/env python3
"""Spec 04: ArchEval feedback-cost comparison. Reads inputs/ only, writes result.json."""
import csv
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "inputs" / "data" / "datasets"
SETTINGS_CSV = DATA / "chapter10-archeval-settings.csv"
L3_CSV = DATA / "chapter10-archeval-l3-per-challenge.csv"

SETTINGS = ("L1", "L2", "L3")
HF = "hf"
BASELINE = 1.00
CELL_HALF_UNIT = 0.005  # cells are printed to two decimals
HALF_PCT = 50.0
ASTRA = "ASTRA-sim"

READINGS = {
    "printed_1_00_is_win": {
        "text": "Spec definition. Printed 1.00 is a win and is not below baseline.",
        "tie_win": True, "tie_below": False},
    "printed_1_00_is_tie": {
        "text": "Sensitivity. Printed 1.00 is neither a win nor below baseline.",
        "tie_win": False, "tie_below": False},
    "printed_1_00_is_below": {
        "text": "Sensitivity. Printed 1.00 is treated as a value that rounded up: "
                "not a win, and counted below baseline.",
        "tie_win": False, "tie_below": True},
}


def load(path):
    with path.open(newline="", encoding="utf-8") as f:
        lines = f.readlines()
    comments = sum(1 for l in lines if l.startswith("#"))
    rows = list(csv.DictReader(l for l in lines if not l.startswith("#")))
    for r in rows:
        if None in r or None in r.values():
            raise ValueError(f"{path.name}: malformed row {r}")
    return rows, comments


def parse_perf(text):
    """Return None for hf, a float for a number. Anything else stops the run."""
    if text == HF:
        return None
    return float(text)


def geomean(values):
    return math.exp(sum(math.log(v) for v in values) / len(values))


def is_win(v, reading):
    if v is None:
        return False
    if v == BASELINE:
        return reading["tie_win"]
    return v > BASELINE


def is_below(v, reading):
    if v is None:
        return False
    if v == BASELINE:
        return reading["tie_below"]
    return v < BASELINE


def main():
    settings_rows, settings_comments = load(SETTINGS_CSV)
    l3_rows, l3_comments = load(L3_CSV)

    agents = list(dict.fromkeys(r["agent"] for r in settings_rows))
    by_key = Counter((r["agent"], r["setting"]) for r in settings_rows)
    expected = {(a, s) for a in agents for s in SETTINGS}
    if set(by_key) != expected or set(by_key.values()) != {1}:
        raise ValueError("settings file is not one row per agent and setting")
    settings = {(r["agent"], r["setting"]): r for r in settings_rows}

    if {r["agent"] for r in l3_rows} != set(agents):
        raise ValueError("agent names differ between the two files")
    pairs = Counter((r["challenge_id"], r["agent"]) for r in l3_rows)
    challenges = list(dict.fromkeys(r["challenge_id"] for r in l3_rows))
    if set(pairs) != {(c, a) for c in challenges for a in agents} or set(pairs.values()) != {1}:
        raise ValueError("per-challenge file is not one row per challenge and agent")
    sim_of = {}
    for r in l3_rows:
        if sim_of.setdefault(r["challenge_id"], r["simulator"]) != r["simulator"]:
            raise ValueError(f"mixed simulator for {r['challenge_id']}")

    for r in l3_rows:
        r["v"] = parse_perf(r["norm_perf"])

    n_challenges = len(challenges)
    astra_ids = {c for c in challenges if sim_of[c] == ASTRA}
    keep_ids = [c for c in challenges if c not in astra_ids]
    n_remaining = len(keep_ids)

    def rows_for(agent, ids=None):
        return [r for r in l3_rows if r["agent"] == agent and (ids is None or r["challenge_id"] in ids)]

    def num(rows):
        return [r["v"] for r in rows if r["v"] is not None]

    under = {s: [a for a in agents if float(settings[(a, s)]["win_rate_pct"]) < HALF_PCT]
             for s in ("L2", "L3")}

    readings_out = {}
    for name, reading in READINGS.items():
        agents_out, checks = {}, {}
        for a in agents:
            mtok = {s: float(settings[(a, s)]["mean_mtok"]) for s in SETTINGS}
            win_pct = {s: float(settings[(a, s)]["win_rate_pct"]) for s in SETTINGS}
            printed = settings[(a, "L3")]
            all_rows, keep_rows = rows_for(a), rows_for(a, set(keep_ids))
            wins = sum(is_win(r["v"], reading) for r in all_rows)
            wins_keep = sum(is_win(r["v"], reading) for r in keep_rows)
            wins_pct = 100.0 * wins / n_challenges
            gm = geomean(num(all_rows))
            gm_keep = geomean(num(keep_rows))
            gm_printed = float(printed["geomean_norm_perf"])
            med_printed = float(printed["median_norm_perf"])
            agents_out[a] = {
                "mtok": mtok,
                "l3_lt_l2": mtok["L3"] < mtok["L2"],
                "l3_gt_l1": mtok["L3"] > mtok["L1"],
                "ratio_l3_l2": mtok["L3"] / mtok["L2"],
                "ratio_l3_l1": mtok["L3"] / mtok["L1"],
                "win_rate_pct": win_pct,
                "wins_l3": wins,
                "wins_l3_pct": wins_pct,
                "geomean_l3_printed": gm_printed,
                "geomean_l3_computed": gm,
                "median_l3_printed": med_printed,
                "geomean_no_astra": gm_keep,
                "wins_no_astra": wins_keep,
            }
            med = statistics.median(num(all_rows))
            checks[a] = {
                "wins_l3_pct_minus_printed": wins_pct - win_pct["L3"],
                "geomean_computed_minus_printed": gm - gm_printed,
                "median_l3_computed": med,
                "median_computed_minus_printed": med - med_printed,
                "geomean_low_if_every_cell_rounded_up": geomean([v - CELL_HALF_UNIT for v in num(all_rows)]),
                "geomean_high_if_every_cell_rounded_down": geomean([v + CELL_HALF_UNIT for v in num(all_rows)]),
                "n_numeric": len(num(all_rows)),
                "n_hf": len(all_rows) - len(num(all_rows)),
                "n_numeric_no_astra": len(num(keep_rows)),
                "n_printed_1_00": sum(r["v"] == BASELINE for r in all_rows),
                "n_printed_1_00_no_astra": sum(r["v"] == BASELINE for r in keep_rows),
                "wins_no_astra_pct": 100.0 * wins_keep / n_remaining,
                "under_half_no_astra": 100.0 * wins_keep / n_remaining < HALF_PCT,
            }
        values = [r["v"] for r in l3_rows if r["v"] is not None]
        readings_out[name] = {
            "reading": reading["text"],
            "agents": agents_out,
            "under_half": {
                "L2": under["L2"], "L3": under["L3"],
                "crossed_l2_to_l3": [a for a in under["L3"] if a not in under["L2"]],
            },
            "agents_l3_lower_than_l2": sum(v["l3_lt_l2"] for v in agents_out.values()),
            "agents_l3_higher_than_l1": sum(v["l3_gt_l1"] for v in agents_out.values()),
            "panel_b": {
                "n_challenges": n_challenges,
                "n_runs": len(l3_rows),
                "n_results": len(values),
                "n_hf": len(l3_rows) - len(values),
                "n_below": sum(is_below(r["v"], reading) for r in l3_rows),
                "min": min(values),
                "max": max(values),
            },
            "astra": {"dropped_challenges": len(astra_ids), "remaining_challenges": n_remaining},
            "checks": {
                "per_agent": checks,
                "under_half_l3_from_wins": [a for a in agents
                                            if agents_out[a]["wins_l3_pct"] < HALF_PCT],
                "agents_under_half_no_astra": sum(c["under_half_no_astra"] for c in checks.values()),
            },
        }

    hf_rows = sum(r["v"] is None for r in l3_rows)
    astra_rows = sum(r["simulator"] == ASTRA for r in l3_rows)
    astra_hf = sum(r["simulator"] == ASTRA and r["v"] is None for r in l3_rows)
    out = {
        "spec": "04-archeval-feedback-cost",
        "readings": readings_out,
        "drops": {
            "comment_lines_skipped": {"settings": settings_comments, "per_challenge": l3_comments},
            "hf_rows_excluded_from_numeric_aggregates": hf_rows,
            "astra_rows_excluded_from_no_astra_subset": astra_rows,
            "astra_rows_that_are_hf": astra_hf,
            "rows_failing_to_parse": 0,
        },
        "input_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in (SETTINGS_CSV, L3_CSV)},
    }
    (HERE / "result.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
