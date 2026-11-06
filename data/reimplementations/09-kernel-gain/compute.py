#!/usr/bin/env python3
"""Spec 09: kernel gain against torch.compile. Run from this folder; writes result.json."""
import json
import os
import re
import statistics

RAW = "inputs/data/studies/10-kernelagent-search/raw"
OCC = "sm__warps_active.avg.pct_of_peak_sustained_active"
DRAM_A = "dram__throughput.avg.pct_of_peak_sustained_elapsed"
DRAM_B = "gpu__dram_throughput.avg.pct_of_peak_sustained_elapsed"
NUM = r"([0-9][0-9,]*\.?[0-9]*)"

dropped = []


def drop(item, why):
    dropped.append({"item": item, "why": why})


def ratio(a, b):
    """Return a/b, or None when either side could not be obtained."""
    if a is None or b is None:
        return None
    return a / b


def load_records():
    """Per-task, per-round timing and profile records from the trace folders."""
    out = {}
    binding = {"rounds": 0, "worker_and_round_match": 0, "mismatches": []}
    for task in sorted(os.listdir(RAW)):
        trace = os.path.join(RAW, task, "optimization_trace")
        if not os.path.isdir(trace):
            continue
        rounds = {}
        for name in os.listdir(trace):
            m = re.fullmatch(r"round_(\d+)", name)
            if m is None:
                drop(f"{task}/{name}", "folder is not round_<r>")
                continue
            r = int(m.group(1))
            d = os.path.join(trace, name)
            paths = {k: os.path.join(d, k) for k in
                     ("benchmark_results.json", "optimized_ncu_metrics.json", "input_ncu_metrics.json")}
            absent = [k for k, p in paths.items() if not os.path.exists(p)]
            if absent:
                drop(f"{task}/round_{r}", f"missing {absent}")
                continue
            with open(paths["benchmark_results.json"]) as f:
                bench = json.load(f)
            with open(paths["optimized_ncu_metrics.json"]) as f:
                opt = json.load(f)
            with open(paths["input_ncu_metrics.json"]) as f:
                inp = json.load(f)
            if len(bench["kernels"]) != 1:
                drop(f"{task}/round_{r}", f"{len(bench['kernels'])} kernel keys in benchmark_results")
                continue
            if len(opt["metrics"]) != 1 or len(inp["metrics"]) != 1:
                drop(f"{task}/round_{r}", "profile file does not hold exactly one kernel key")
                continue
            kernel = next(iter(bench["kernels"].values()))
            rounds[r] = {
                "time_ms": kernel["time_ms"],
                "opt": next(iter(opt["metrics"].values())),
                "inp": next(iter(inp["metrics"].values())),
            }
            pat = r"/w(\d+)/r(\d+)/"
            bm = re.search(pat, kernel["path"])
            om = re.search(pat, opt["metadata"]["kernel_file"])
            binding["rounds"] += 1
            same = (bm is not None and om is not None and bm.groups() == om.groups()
                    and int(bm.group(2)) == r)
            if same:
                binding["worker_and_round_match"] += 1
            else:
                binding["mismatches"].append(f"{task}/round_{r}")
        out[task] = rounds
    return out, binding


def parse_readme():
    """Per-section README values, keyed by the numeric task prefix."""
    with open(os.path.join(RAW, "README.md")) as f:
        text = f.read()
    sections = {}
    parts = re.split(r"^### (\d+)\\_(.*)$", text, flags=re.M)
    for i in range(1, len(parts), 3):
        prefix, body = int(parts[i]), parts[i + 2]
        tc = re.search(r"`torch\.compile`: \*\*" + NUM + r"ms\*\*", body)
        ti = re.search(r"`input kernel`: \*\*" + NUM + r"ms\*\*", body)
        best = re.search(r"Best: round (\d+) — \*\*" + NUM + r"ms\*\* \(" + NUM + r"x vs", body)
        hdr = re.search(r"\| Round \|(.*)\|", body)
        row = re.search(r"\| Best \(ms\) \|(.*)\|", body)
        if not all((tc, ti, best, hdr, row)):
            drop(f"README section {prefix}", "a required field did not parse")
            continue
        rounds = [int(c) for c in hdr.group(1).split("|") if c.strip()]
        cells = [c.strip() for c in row.group(1).split("|") if c.strip()]
        table = {}
        bold_round = None
        for r, c in zip(rounds, cells):
            if c.startswith("**"):
                bold_round = r
            table[r] = float(c.strip("*"))
        ncu = {}
        for label, a, b in re.findall(r"^\| ([A-Z][^|]*\(% peak\)) \| ([0-9.]+)% \| \*{0,2}([0-9.]+)%\*{0,2} \|$",
                                      body, flags=re.M):
            ncu[label] = (float(a), float(b))
        sections[prefix] = {
            "t_tc": float(tc.group(1)),
            "t_in": float(ti.group(1)),
            "t_final": float(best.group(2)),
            "best_round_line": int(best.group(1)),
            "stated_speedup": float(best.group(3)),
            "table": table,
            "table_bold_round": bold_round,
            "ncu": ncu,
        }
    example = {}
    m = re.search(r"Example output:\n```\n(.*?)```", text, flags=re.S)
    if m is None:
        drop("README example output", "block did not parse")
    else:
        for line in re.finditer(r"\] (\d+)_\S+\neager=" + NUM + r"\s+compile=" + NUM + r"\s+input=" + NUM
                                + r"\s+opt=" + NUM, m.group(1)):
            example[int(line.group(1))] = {
                "t_tc": float(line.group(3)), "t_in": float(line.group(4)), "t_final": float(line.group(5))}
    return sections, example


def prompt_starts(task, r):
    """All 'Performance: start → end' pairs in a round's opt_prompt.txt."""
    path = os.path.join(RAW, task, "optimization_trace", f"round_{r}", "opt_prompt.txt")
    if not os.path.exists(path):
        drop(f"{task}/round_{r}/opt_prompt.txt", "missing")
        return []
    with open(path) as f:
        text = f.read()
    return [(float(a), float(b)) for a, b in
            re.findall(r"\*\*Performance\*\*: ([0-9.]+)ms → ([0-9.]+)ms", text)]


def prompt_t_in(task, t_r1):
    """Starting time of the Round 1 worker whose end time equals the retained T_R1 at 4 decimals."""
    pairs = prompt_starts(task, 2)
    hits = [a for a, b in pairs if b == round(t_r1, 4)]
    if len(hits) != 1:
        drop(f"{task}: prompt input time", f"{len(hits)} Round 2 prompt lines end at T_R1")
        return None, pairs
    return hits[0], pairs


def build_task(rounds, tc, ti, final_readme, dram_field, start_key, t_r1=None, t_best=None, r_best=None):
    """All spec fields for one task. Timing overrides are used only by the README-table reading."""
    if t_r1 is None:
        t_r1 = rounds[1]["time_ms"]
        t_best, r_best = None, None
        for r in sorted(rounds):
            t = rounds[r]["time_ms"]
            if t_best is None or t < t_best:  # strict: a tie stays at the earliest round
                t_best, r_best = t, r
    occ_r1 = rounds[1][start_key][OCC]
    occ_best = rounds[r_best]["opt"][OCC]
    return {
        "t_tc": tc, "t_in": ti, "t_r1": t_r1, "t_best": t_best, "r_best": r_best,
        "t_final_readme": final_readme,
        "input_over_tc": ratio(ti, tc),
        "r1_over_tc": ratio(t_r1, tc),
        "search_gain": ratio(t_r1, t_best),
        "lowest_over_r1": ratio(t_best, t_r1),
        "final_speedup_records": ratio(tc, t_best),
        "final_speedup_readme": ratio(tc, final_readme),
        "input_ahead_of_tc": None if ti is None or tc is None else ti < tc,
        "readme_over_records_best": ratio(final_readme, t_best),
        "profile": {
            "occupancy_field": OCC, "dram_field": dram_field,
            "occupancy_r1": occ_r1, "occupancy_best": occ_best,
            "dram_r1": rounds[1][start_key][dram_field], "dram_best": rounds[r_best]["opt"][dram_field],
            "occupancy_falls": occ_best < occ_r1,
        },
    }


def main():
    records, binding = load_records()
    readme, example = parse_readme()
    prefix = {t: int(t.split("_")[0]) for t in records}
    for t, p in prefix.items():
        if p not in readme:
            drop(t, "no README section")

    readings = {k: {"description": d, "tasks": {}} for k, d in {
        "base": "Spec default. T_tc, T_in, T_final_readme from the README task sections; Round 1 profile from "
                "optimized_ncu_metrics.json; DRAM field dram__throughput.",
        "dram_gpu_field": "As base with DRAM field gpu__dram_throughput.",
        "t_in_prompt_round2": "As base with T_in from Round 2 opt_prompt.txt: the start time of the Round 1 worker "
                              "that ended at T_R1. The Round 1 prompt carries no such time.",
        "t_in_prompt_round2_median": "As base with T_in the median of the four worker start times in the Round 2 "
                                     "opt_prompt.txt history.",
        "readme_example_output": "As base with T_tc, T_in, T_final_readme from the README example benchmark output. "
                                 "That block prints only two tasks; the others are null.",
        "profile_start_input_kernel": "As base with the profile start taken from Round 1 input_ncu_metrics.json, "
                                      "the input kernel, not the Round 1 output.",
        "readme_round_table": "As base with T_R1, T_best, r_best from the README running-best table (bold cell), "
                              "so no per-round record enters the times.",
    }.items()}

    diag = {"prompt_round1_performance_lines": {}, "prompt_round2_pairs": {}, "per_round_time_ms": {},
            "readme_running_best_vs_records": {}, "stated_speedup_vs_recomputed": {},
            "dram_field_files_compared": 0, "dram_field_files_differing": 0, "readme_ncu_checks": {},
            "ties_at_best": {}, "readme_over_records": {}}

    for t, rounds in records.items():
        s = readme.get(prefix[t])
        if s is None or 1 not in rounds:
            drop(t, "no README section or no Round 1 record")
            continue
        args = (rounds, s["t_tc"], s["t_in"], s["t_final"])
        readings["base"]["tasks"][t] = build_task(*args, DRAM_A, "opt")
        readings["dram_gpu_field"]["tasks"][t] = build_task(*args, DRAM_B, "opt")
        readings["profile_start_input_kernel"]["tasks"][t] = build_task(*args, DRAM_A, "inp")

        p_in, pairs = prompt_t_in(t, rounds[1]["time_ms"])
        readings["t_in_prompt_round2"]["tasks"][t] = build_task(
            rounds, s["t_tc"], p_in, s["t_final"], DRAM_A, "opt")

        p_med = statistics.median(a for a, _ in pairs) if pairs else None
        readings["t_in_prompt_round2_median"]["tasks"][t] = build_task(
            rounds, s["t_tc"], p_med, s["t_final"], DRAM_A, "opt")

        e = example.get(prefix[t])
        if e is None:
            drop(f"{t}: readme_example_output", "task is elided from the example block")
            readings["readme_example_output"]["tasks"][t] = build_task(rounds, None, None, None, DRAM_A, "opt")
        else:
            readings["readme_example_output"]["tasks"][t] = build_task(
                rounds, e["t_tc"], e["t_in"], e["t_final"], DRAM_A, "opt")

        tbl = s["table"]
        readings["readme_round_table"]["tasks"][t] = build_task(
            *args, DRAM_A, "opt", t_r1=tbl[1], t_best=tbl[s["table_bold_round"]], r_best=s["table_bold_round"])

        # Diagnostics only; nothing below feeds a reading.
        diag["prompt_round1_performance_lines"][t] = len(prompt_starts(t, 1))
        diag["prompt_round2_pairs"][t] = pairs
        times = {r: rounds[r]["time_ms"] for r in sorted(rounds)}
        diag["per_round_time_ms"][t] = times
        best_val = min(times.values())
        diag["ties_at_best"][t] = sum(1 for v in times.values() if v == best_val) - 1
        running, cmp_rows = None, {}
        for r, v in times.items():
            running = v if running is None else min(running, v)
            cmp_rows[r] = {"records_running_best": running, "readme": tbl.get(r),
                           "differs_at_3dp": round(running, 3) != tbl.get(r)}
        diag["readme_running_best_vs_records"][t] = cmp_rows
        diag["stated_speedup_vs_recomputed"][t] = {
            "stated": s["stated_speedup"], "recomputed": s["t_tc"] / s["t_final"],
            "best_line_round": s["best_round_line"], "table_bold_round": s["table_bold_round"]}
        for r in rounds:
            for k in ("opt", "inp"):
                diag["dram_field_files_compared"] += 1
                if rounds[r][k][DRAM_A] != rounds[r][k][DRAM_B]:
                    diag["dram_field_files_differing"] += 1
        diag["readme_over_records"][t] = {
            "round1": tbl[1] / times[1],
            "best": s["t_final"] / best_val,
            "t_in_over_matching_prompt_start": None if p_in is None else s["t_in"] / p_in,
            "t_in_over_median_prompt_start": None if p_med is None else s["t_in"] / p_med}
        checks = {}
        rb = s["table_bold_round"]
        for label, field in (("DRAM throughput (% peak)", DRAM_A), ("Occupancy (% peak)", OCC)):
            if label in s["ncu"]:
                checks[label] = {
                    "readme_input": s["ncu"][label][0], "round1_input_ncu": rounds[1]["inp"][field],
                    "readme_optimized": s["ncu"][label][1], "readme_best_round_optimized_ncu": rounds[rb]["opt"][field],
                    "round1_optimized_ncu": rounds[1]["opt"][field]}
        diag["readme_ncu_checks"][t] = checks

    result = {
        "readings": readings,
        "profile_scope_note": "Spec requires profiles only for matrix-vector, MaxPool 3D, 3D transposed conv; "
                              "all five are written.",
        "profile_binding_by_worker_and_round": binding,
        "dropped": dropped,
        "diagnostics": diag,
    }
    with open("result.json", "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"tasks={len(readings['base']['tasks'])} readings={len(readings)} dropped={len(dropped)}")


if __name__ == "__main__":
    main()
