#!/usr/bin/env python3
"""Score the matched H100 runs and measure run-to-run spread.

Reads mlperf-h100-runs.csv, the published minutes in
fig-ch09-mlperf-software-dividend.csv, and the retained v3.0 results sheet.
Writes mlperf-h100-spread.csv, mlperf-h100-pairs.csv, and mlperf-h100-hosts.csv,
and refreshes the computed columns of the figure CSV.
Standard library only; the bootstrap seed is fixed, so a rerun repeats exactly.

    python3 analyze_mlperf_h100_runs.py

Scoring follows training_rules.adoc: drop the fastest and slowest run (four of
each for 3D U-Net), count a non-converged run as a slowest run, and average the
rest. The script stops if a rule score fails to reproduce a published time,
after any scaling.json factor, to three decimals.

Aborted-run rule of the plotted intervals: each bootstrap draw resamples converged
runs within a round and holds the number of aborted runs at the count submitted,
so a draw can never lose or gain one. Intervals therefore treat submitted runs as
independent draws and describe spread within one submission pair only. They are
not the uncertainty of the gain:
MLCommons states that even averaged results vary very roughly +/- 2.5 percent for
imaging benchmarks and +/- 5 percent otherwise, and the overlap columns show that
some run sets ran at the same time.

Holding that count fixed spares the three sets that lost a run from ever losing
their result, so a second bootstrap, on its own seed so that the plotted intervals
do not move, resamples all submitted runs. Under training_rules.adoc an aborted run
may count as a slowest run, and a set with more than the rules allow (one, or four
for 3D U-Net) is invalid. An invalid set has no result, so a draw that holds one
has no ratio. no_comparison_draws counts those draws out of DRAWS for each workload
and each pair. They receive no value. The rules use "infinite" only to rank
sliding windows of an M>N submission, and give it no meaning as a time.

The valid_ columns use only draws with a comparison, and so condition on one. The
logged_ columns are not a rule score: they give an aborted run its logged minutes,
although it never reached the target, and so score sets the rules call invalid. No
claim rests on them; they stay as a record of how far that choice moves a result.

depends_on_aborted_runs in the pairs file is yes when the pair has any draw with no
comparison, because a statement over all draws would then need a value that the
rules do not give. The chapter claims no lead for such a pair. It reports what the
published times and the valid runs show, labeled as such. valid_reverse_or_tie_draws
counts the draws with a comparison in which the left ratio is at or below the right.

Run-set columns compare the converged times of the two rounds. sets_overlap says
whether their ranges overlap. Overlap blocks are runs joined by overlapping
start-to-stop spans. A block is a timing statistic and not a launch or session: the
logs carry no launch or machine identity, and separately started runs can overlap.
Runs of eight GPUs that overlap in time imply more than one machine at face value,
so spread within a set can include machine-to-machine spread. The block ratios
divide each v2.1 block's pooled time per unit by the pooled v3.0 value. The step
columns find the largest jump in sorted v2.1 time per unit and repool the runs
below it; they mean something only where that jump is large, as for RNN-T at
9.3 percent, against 2.4 percent or less for the other five.

mlperf-h100-hosts.csv divides the published v2.1 NVIDIA minutes by the published
v3.0 minutes of each 8x H100 SXM submission. Hosts differ, so these ratios are
not replicates, and they keep any scaling inside the published minutes.

Time per unit divides time by the position of the last logged eval, taken as
the convergence point. The logs put this position in an epoch_num field, which
holds an epoch for five workloads and a sample count for BERT, so it is compared
only with itself across rounds. Runs that reach the target between evals share
a position, so epochs to converge are coarse for ResNet-50, Mask R-CNN, and
RetinaNet, whose runs all stop at one position.
"""

import csv
import itertools
import json
import random
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "mlperf-h100-runs.csv"
FIG = HERE / "fig-ch09-mlperf-software-dividend.csv"
SPREAD = HERE / "mlperf-h100-spread.csv"
HOSTS = HERE / "mlperf-h100-hosts.csv"
SHEET_V30 = HERE / "mlperf-h100-sources" / "results-v3.0-sheet.csv"
SHEET_COLUMNS = {"ResNet": "ResNet-50 v1.5", "3D U-Net": "3D U-Net", "RetinaNet": "RetinaNet",
                 "Mask R-CNN": "Mask R-CNN", "RNN-T": "RNN-T", "BERT-large": "BERT"}
PAIRS = HERE / "mlperf-h100-pairs.csv"
SCALING = {("v2.1", "ResNet-50 v1.5"): HERE / "mlperf-h100-sources" / "v2.1-resnet-scaling.json"}

DROP = {"3D U-Net": 4}  # all others drop one run from each end
LIMIT = {"3D U-Net": 4}  # aborted runs a valid result may hold; all others one
DRAWS = 20000
SEED = 20261102
ALL_RUNS_SEED = SEED + 1  # a separate stream leaves the plotted intervals unchanged


def rows_of(path):
    with open(path, encoding="utf-8") as handle:
        return list(csv.DictReader(line for line in handle if not line.startswith("#")))


def score(converged, failed, k):
    """Rule score from converged times plus a count of non-converged runs."""
    ordered = sorted(converged)
    slow = k - failed
    if slow < 0:
        raise ValueError("more non-converged runs than the rules drop")
    return st.mean(ordered[k:len(ordered) - slow] if slow else ordered[k:])


def rule_score(times, work):
    """Rule score of a full run set, where None marks an aborted run. An invalid set has no result."""
    converged = [t for t in times if t is not None]
    failed = len(times) - len(converged)
    if failed > LIMIT.get(work, 1):
        return None
    return score(converged, failed, DROP.get(work, 1))


def comparable(scores):
    """True when every set in a draw has a result, so its ratios exist."""
    return None not in scores


def blocks_of(runs):
    """Groups of runs joined by overlapping start-to-stop spans, in start order."""
    blocks = []
    for run in sorted(runs, key=lambda r: r["start"]):
        if blocks and run["start"] <= max(r["stop"] for r in blocks[-1]):
            blocks[-1].append(run)
        else:
            blocks.append([run])
    return blocks


def most_at_once(runs):
    """Largest number of runs in progress at one moment."""
    return max(sum(r["start"] <= run["start"] < r["stop"] for r in runs) for run in runs)


def pooled_unit(runs):
    """Pooled time per unit of converged runs."""
    done = [r for r in runs if r["time"] is not None]
    return sum(r["time"] for r in done) / sum(r["unit"] for r in done)


def overlap_row(early, late, label=""):
    """Whether two ranges overlap, and how many of each lie inside the other."""
    low, high = max(min(early), min(late)), min(max(early), max(late))
    return {f"sets_overlap{label}": "yes" if low <= high else "no",
            f"from_in_to_range{label}": sum(low <= v <= high for v in early),
            f"to_in_from_range{label}": sum(low <= v <= high for v in late)}


def interval(values):
    ordered = sorted(values)
    return ordered[int(0.025 * len(ordered))], ordered[int(0.975 * len(ordered)) - 1]


def cv_per_unit(slot):
    values = [t / u for t, u in zip(slot["ok"], slot["units"])]
    return 100 * st.stdev(values) / st.mean(values)


def host_rows(fig):
    """One row per v3.0 8x H100 SXM published time, against NVIDIA's v2.1 minutes."""
    with open(SHEET_V30, encoding="utf-8", newline="") as handle:
        sheet = list(csv.reader(handle))
    model = next(row for row in sheet if row[8:10] == ["Model", "ResNet"])
    columns = {SHEET_COLUMNS[name]: i for i, name in enumerate(model) if name in SHEET_COLUMNS}
    if len(columns) != len(SHEET_COLUMNS):
        raise SystemExit("v3.0 sheet header does not name all six workloads")
    earlier = {r["workload"]: float(r["from_time_min"]) for r in fig}
    out, section = [], ""
    for row in sheet[sheet.index(model) + 1:]:
        if row[0] and not row[1]:
            section = row[0]
        if row[1] and row[6].strip() == "8" and "H100-SXM" in row[5]:
            for work, column in columns.items():
                if row[column].strip():
                    minutes = float(row[column])
                    out.append({"workload": work, "result_id": row[0], "submitter": row[1],
                                "system": row[2], "section": section, "accelerator": row[5],
                                "to_time_min": f"{minutes:.3f}",
                                "published_ratio": f"{earlier[work] / minutes:.4f}"})
    return out


def main():
    runs = rows_of(RUNS)
    fig = rows_of(FIG)
    rng = random.Random(SEED)
    all_runs_rng = random.Random(ALL_RUNS_SEED)
    data = {}
    for row in runs:
        key = (row["round"], row["workload"])
        slot = data.setdefault(key, {"ok": [], "units": [], "failed": 0, "starts": [], "runs": []})
        slot["starts"].append(int(row["run_start_ms"]))
        done = row["status"] == "success"
        if done:
            slot["ok"].append(float(row["time_min"]))
            slot["units"].append(float(row["last_eval_position"]))
        else:
            slot["failed"] += 1
        slot["runs"].append({"time": float(row["time_min"]) if done else None,
                             "logged": float(row["time_min"]),
                             "unit": float(row["last_eval_position"]),
                             "start": int(row["run_start_ms"]), "stop": int(row["run_stop_ms"])})

    spread, boot, published, score_boot, logged_boot = [], {}, {}, {}, {}
    for row in fig:
        work = row["workload"]
        early, late = data[("v2.1", work)], data[("v3.0", work)]
        k = DROP.get(work, 1)
        rule = [score(s["ok"], s["failed"], k) for s in (early, late)]
        factors = []
        for version, value, pub in (("v2.1", rule[0], row["from_time_min"]),
                                    ("v3.0", rule[1], row["to_time_min"])):
            path = SCALING.get((version, work))
            factor = json.loads(path.read_text())["scaling_factor"] if path else 1.0
            factors.append(factor)
            if round(value * factor, 3) != float(pub):
                raise SystemExit(f"{version} {work}: rule score {value * factor:.3f} is not published {pub}")
        ratio = rule[0] / rule[1]
        draws, per_unit, units = [], [], []
        for _ in range(DRAWS):
            picks = [rng.choices(range(len(s["ok"])), k=len(s["ok"])) for s in (early, late)]
            a_t = [early["ok"][i] for i in picks[0]]
            b_t = [late["ok"][i] for i in picks[1]]
            a_u = [early["units"][i] for i in picks[0]]
            b_u = [late["units"][i] for i in picks[1]]
            draws.append(score(a_t, early["failed"], k) / score(b_t, late["failed"], k))
            per_unit.append((sum(a_t) / sum(a_u)) / (sum(b_t) / sum(b_u)))
            units.append((sum(a_u) / len(a_u)) / (sum(b_u) / len(b_u)))
        boot[work] = draws
        scores, logged = [], []
        k = DROP.get(work, 1)
        for _ in range(DRAWS):
            sides = [all_runs_rng.choices(s["runs"], k=len(s["runs"])) for s in (early, late)]
            scores.append(tuple(rule_score([r["time"] for r in side], work) for side in sides))
            pair = [st.mean(sorted(r["logged"] for r in side)[k:len(side) - k]) for side in sides]
            logged.append(pair[0] / pair[1])
        score_boot[work], logged_boot[work] = scores, logged
        valid = [a / b for a, b in scores if comparable((a, b))]
        valid_low, valid_high = interval(valid)
        logged_low, logged_high = interval(logged)
        checks = {
            "draws": DRAWS, "no_comparison_draws": DRAWS - len(valid),
            "valid_ratio_low": f"{valid_low:.4f}", "valid_ratio_high": f"{valid_high:.4f}",
            "logged_ratio_low": f"{logged_low:.4f}", "logged_ratio_high": f"{logged_high:.4f}",
            "from_min_min": f"{min(early['ok']):.3f}", "from_max_min": f"{max(early['ok']):.3f}",
            "to_min_min": f"{min(late['ok']):.3f}", "to_max_min": f"{max(late['ok']):.3f}",
            **overlap_row(early["ok"], late["ok"]),
            **overlap_row([t / u for t, u in zip(early["ok"], early["units"])],
                          [t / u for t, u in zip(late["ok"], late["units"])], "_time_per_unit"),
        }
        early_blocks, late_blocks = blocks_of(early["runs"]), blocks_of(late["runs"])
        later_unit = pooled_unit(late["runs"])
        block_ratios = [pooled_unit(b) / later_unit for b in early_blocks]
        values = sorted(t / u for t, u in zip(early["ok"], early["units"]))
        steps = [b / a - 1 for a, b in zip(values, values[1:])]
        cut = steps.index(max(steps)) + 1
        below = sorted(zip(early["ok"], early["units"]), key=lambda p: p[0] / p[1])[:cut]
        later_values = sorted(t / u for t, u in zip(late["ok"], late["units"]))
        checks.update({
            "from_overlap_blocks": len(early_blocks), "to_overlap_blocks": len(late_blocks),
            "from_most_at_once": most_at_once(early["runs"]), "to_most_at_once": most_at_once(late["runs"]),
            "from_block_tpu_ratio_min": f"{min(block_ratios):.4f}",
            "from_block_tpu_ratio_max": f"{max(block_ratios):.4f}",
            "from_tpu_largest_step_pct": f"{100 * max(steps):.2f}",
            "to_tpu_largest_step_pct": f"{100 * max(b / a - 1 for a, b in zip(later_values, later_values[1:])):.2f}",
            "from_runs_above_step": len(values) - cut,
            "time_per_unit_ratio_below_step":
                f"{sum(t for t, _ in below) / sum(u for _, u in below) / later_unit:.4f}",
        })
        published[work] = float(row["from_time_min"]) / float(row["to_time_min"])
        low, high = interval(draws)
        tu_low, tu_high = interval(per_unit)
        cu_low, cu_high = interval(units)
        point_tu = (sum(early["ok"]) / sum(early["units"])) / (sum(late["ok"]) / sum(late["units"]))
        point_cu = st.mean(early["units"]) / st.mean(late["units"])
        spread.append({
            "workload": work,
            "from_runs": len(early["ok"]) + early["failed"],
            "to_runs": len(late["ok"]) + late["failed"],
            "from_nonconverged": early["failed"], "to_nonconverged": late["failed"],
            "from_rule_min": f"{rule[0]:.3f}", "to_rule_min": f"{rule[1]:.3f}",
            "from_scaling": f"{factors[0]:.5f}", "to_scaling": f"{factors[1]:.5f}",
            "published_ratio": f"{published[work]:.4f}", "ratio": f"{ratio:.4f}",
            "ratio_low": f"{low:.4f}", "ratio_high": f"{high:.4f}",
            "p_ratio_at_most_1": f"{sum(d <= 1 for d in draws) / DRAWS:.4f}",
            "from_cv_pct": f"{100 * st.stdev(early['ok']) / st.mean(early['ok']):.2f}",
            "to_cv_pct": f"{100 * st.stdev(late['ok']) / st.mean(late['ok']):.2f}",
            "from_units_cv_pct": f"{100 * st.stdev(early['units']) / st.mean(early['units']):.2f}",
            "to_units_cv_pct": f"{100 * st.stdev(late['units']) / st.mean(late['units']):.2f}",
            "from_time_per_unit_cv_pct": f"{cv_per_unit(early):.2f}",
            "to_time_per_unit_cv_pct": f"{cv_per_unit(late):.2f}",
            "time_per_unit_ratio": f"{point_tu:.4f}",
            "time_per_unit_low": f"{tu_low:.4f}", "time_per_unit_high": f"{tu_high:.4f}",
            "units_ratio": f"{point_cu:.4f}",
            "units_low": f"{cu_low:.4f}", "units_high": f"{cu_high:.4f}",
            "from_start_span_s": f"{(max(early['starts']) - min(early['starts'])) / 1000:.3f}",
            "to_start_span_s": f"{(max(late['starts']) - min(late['starts'])) / 1000:.3f}",
            **checks,
        })

    pairs = []
    for left, right in itertools.combinations([r["workload"] for r in spread], 2):
        gaps = [a - b for a, b in zip(boot[left], boot[right])]
        low, high = interval(gaps)
        paired = [a + b for a, b in zip(score_boot[left], score_boot[right])]
        usable = [p for p in paired if comparable(p)]
        tests = {"valid": [p[0] / p[1] - p[2] / p[3] for p in usable],
                 "logged": [a - b for a, b in zip(logged_boot[left], logged_boot[right])]}
        row = {"left": left, "right": right, "diff_low": f"{low:.4f}", "diff_high": f"{high:.4f}",
               "separated": "yes" if low > 0 or high < 0 else "no"}
        for name, values in tests.items():
            a, b = interval(values)
            row.update({f"{name}_diff_low": f"{a:.4f}", f"{name}_diff_high": f"{b:.4f}",
                        f"{name}_separated": "yes" if a > 0 or b < 0 else "no"})
        row["no_comparison_draws"] = DRAWS - len(usable)
        row["depends_on_aborted_runs"] = "yes" if len(usable) < DRAWS else "no"
        row["valid_reverse_or_tie_draws"] = sum(v <= 0 for v in tests["valid"])
        pairs.append(row)

    for path, rows, origin in ((SPREAD, spread, RUNS.name), (PAIRS, pairs, RUNS.name),
                               (HOSTS, host_rows(fig), f"{SHEET_V30.name} and {FIG.name}")):
        with open(path, "w", newline="", encoding="utf-8") as handle:
            handle.write(f"# Computed by analyze_mlperf_h100_runs.py from {origin}. Do not edit by hand.\n")
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    by_work = {r["workload"]: r for r in spread}
    lines = FIG.read_text(encoding="utf-8").splitlines()
    comments = [l for l in lines if l.startswith("#")]
    added = ["from_rcp_scaling", "from_time_min_unscaled", "ratio", "ratio_low", "ratio_high"]
    fields = [f for f in fig[0] if f not in added] + added
    for row in fig:
        calc = by_work[row["workload"]]
        row.update(from_rcp_scaling=calc["from_scaling"], from_time_min_unscaled=calc["from_rule_min"],
                   ratio=calc["ratio"], ratio_low=calc["ratio_low"], ratio_high=calc["ratio_high"])
    with open(FIG, "w", newline="", encoding="utf-8") as handle:
        handle.write("\n".join(comments) + "\n")
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(fig)
    for row in spread:
        print(row)
    print(sum(p["separated"] == "yes" for p in pairs), "of", len(pairs), "pairs separated with aborted runs held fixed;",
          sum(p["valid_separated"] == "yes" for p in pairs), "among draws with a valid comparison;",
          sum(p["depends_on_aborted_runs"] == "no" for p in pairs), "pairs have no draw without a comparison")


if __name__ == "__main__":
    main()
