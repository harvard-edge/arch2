#!/usr/bin/env python3
"""Recompute every reported number from the declared raw runs and write summary.json.

Stdlib only. For each run and for the pooled sample it computes per-(arm, n)
median and interquartile range, then:
  * crossovers: for each MPS arm, the first n at which its median beats the
    CPU arm of the same panel, and whether it stays ahead at every larger n;
  * resident launch floor: median of all mps_resident samples with n <= 256
    (also reported for mps_bmm and mps_16_launch);
  * sixteen-launch / one-launch cost ratio for n <= 256, per n and summarized;
  * non-monotone points: any (arm, n) where the median is lower than at the
    previous n, and whether that point recurs in every run;
  * dispersion across runs at each crossover size.
Also writes medians.csv (one row per run x arm x n, plus pooled rows).
"""
import csv
import json
import statistics as st
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
CPU_OF = {
    "mps_resident": "cpu_single",
    "mps_copy": "cpu_single",
    "mps_16_launch": "cpu_bmm",
    "mps_bmm": "cpu_bmm",
}
ARMS = ["cpu_single", "mps_resident", "mps_copy", "cpu_bmm", "mps_16_launch", "mps_bmm"]
FLOOR_MAX_N = 256
# The runs provenance.yml declares. Any other raw/run-*.csv, such as an audit rerun
# left in the folder, stays out of the sample and is reported.
DECLARED_RUNS = (1, 2, 3, 4, 5)


def load():
    samples = defaultdict(list)  # (run, arm, n) -> [s]
    hosts = {}
    declared = [RAW / f"run-{k}.csv" for k in DECLARED_RUNS]
    absent = [p.name for p in declared if not p.exists()]
    if absent:
        raise SystemExit(f"declared run file(s) missing: {absent}")
    for path in sorted(set(RAW.glob("run-*.csv")) - set(declared)):
        print(f"ignored undeclared run file: {path.name}")
    for path in declared:
        for row in csv.DictReader(path.open()):
            samples[(int(row["run_id"]), row["arm"], int(row["n"]))].append(
                float(row["seconds"])
            )
        hp = path.with_suffix("").with_suffix(".host.json")
        if hp.exists():
            h = json.loads(hp.read_text())
            hosts[h["run_id"]] = h
    return samples, hosts


def stats(xs):
    q1, q2, q3 = st.quantiles(xs, n=4, method="inclusive")
    return {
        "n_samples": len(xs),
        "median": q2,
        "q1": q1,
        "q3": q3,
        "iqr": q3 - q1,
        "min": min(xs),
        "max": max(xs),
    }


def crossover(series_mps, series_cpu, sizes):
    """First n where mps median < cpu median; whether it stays ahead after."""
    ahead = [series_mps[n] < series_cpu[n] for n in sizes]
    if not any(ahead):
        return {"n": None, "stays_ahead": None, "ahead_at": []}
    first = ahead.index(True)
    return {
        "n": sizes[first],
        "stays_ahead": all(ahead[first:]),
        "ahead_at": [n for n, a in zip(sizes, ahead) if a],
    }


def main():
    samples, hosts = load()
    runs = sorted({k[0] for k in samples})
    sizes = sorted({k[2] for k in samples})
    assert runs and sizes, "no raw data"
    per_run = {
        r: {a: {n: stats(samples[(r, a, n)]) for n in sizes} for a in ARMS}
        for r in runs
    }
    pooled = {
        a: {n: stats([s for r in runs for s in samples[(r, a, n)]]) for n in sizes}
        for a in ARMS
    }
    reps = {len(v) for v in samples.values()}

    rows = []
    for label, table in [(str(r), per_run[r]) for r in runs] + [("pooled", pooled)]:
        for a in ARMS:
            for n in sizes:
                s = table[a][n]
                rows.append(
                    {
                        "run": label,
                        "arm": a,
                        "n": n,
                        **{
                            k: (f"{v:.6e}" if isinstance(v, float) else v)
                            for k, v in s.items()
                        },
                    }
                )
    with (HERE / "medians.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    # Crossovers
    def med(table, a):
        return {n: table[a][n]["median"] for n in sizes}

    cross = {}
    for a, c in CPU_OF.items():
        per = {
            r: crossover(med(per_run[r], a), med(per_run[r], c), sizes) for r in runs
        }
        pool = crossover(med(pooled, a), med(pooled, c), sizes)
        ns = [per[r]["n"] for r in runs]
        cross[a] = {
            "versus": c,
            "pooled": pool,
            "per_run": {str(r): per[r] for r in runs},
            "stable_across_runs": len(set(ns)) == 1
            and all(per[r]["stays_ahead"] for r in runs),
            "per_run_n": ns,
        }

    # Launch floor for n <= 256
    floor = {}
    for a in ["mps_resident", "mps_bmm", "mps_16_launch"]:
        small = [n for n in sizes if n <= FLOOR_MAX_N]
        floor[a] = {
            "sizes": small,
            "pooled": stats(
                [s for r in runs for n in small for s in samples[(r, a, n)]]
            ),
            "per_run": {
                str(r): stats([s for n in small for s in samples[(r, a, n)]])
                for r in runs
            },
        }

    # 16-launch / 1-launch ratio for n <= 256
    small = [n for n in sizes if n <= FLOOR_MAX_N]
    ratio = {"sizes": small, "per_n_pooled": {}, "per_run": {}}
    for n in small:
        ratio["per_n_pooled"][str(n)] = (
            pooled["mps_16_launch"][n]["median"] / pooled["mps_bmm"][n]["median"]
        )
    ratio["pooled_median_of_per_n"] = st.median(ratio["per_n_pooled"].values())
    ratio["pooled_min"], ratio["pooled_max"] = min(ratio["per_n_pooled"].values()), max(
        ratio["per_n_pooled"].values()
    )
    for r in runs:
        vals = {
            str(n): per_run[r]["mps_16_launch"][n]["median"]
            / per_run[r]["mps_bmm"][n]["median"]
            for n in small
        }
        ratio["per_run"][str(r)] = {
            "per_n": vals,
            "median_of_per_n": st.median(vals.values()),
        }

    # Non-monotone points
    nonmono = {"per_run": {}, "pooled": [], "recurring_in_all_runs": []}

    def dips(table, a):
        out = []
        for prev, n in zip(sizes, sizes[1:]):
            if table[a][n]["median"] < table[a][prev]["median"]:
                out.append(
                    {
                        "arm": a,
                        "n": n,
                        "previous_n": prev,
                        "median": table[a][n]["median"],
                        "previous_median": table[a][prev]["median"],
                        "drop_fraction": 1
                        - table[a][n]["median"] / table[a][prev]["median"],
                    }
                )
        return out

    for r in runs:
        nonmono["per_run"][str(r)] = [d for a in ARMS for d in dips(per_run[r], a)]
    nonmono["pooled"] = [d for a in ARMS for d in dips(pooled, a)]
    keys = [set((d["arm"], d["n"]) for d in nonmono["per_run"][str(r)]) for r in runs]
    common = set.intersection(*keys) if keys else set()
    nonmono["recurring_in_all_runs"] = sorted(
        [{"arm": a, "n": n} for a, n in common], key=lambda d: (d["arm"], d["n"])
    )
    nonmono["any_run"] = (
        sorted(
            [
                {
                    "arm": a,
                    "n": n,
                    "runs": [r for r, k in zip(runs, keys) if (a, n) in k],
                }
                for a, n in set.union(*keys)
            ],
            key=lambda d: (d["arm"], d["n"]),
        )
        if keys
        else []
    )

    # Dispersion across runs at crossover sizes
    disp = {}
    for a, c in CPU_OF.items():
        n = cross[a]["pooled"]["n"]
        if n is None:
            continue
        entry = {"n": n}
        for arm in (a, c):
            meds = [per_run[r][arm][n]["median"] for r in runs]
            entry[arm] = {
                "per_run_median": meds,
                "run_to_run_spread_fraction_of_pooled_median": (max(meds) - min(meds))
                / pooled[arm][n]["median"],
                "pooled_median": pooled[arm][n]["median"],
                "pooled_iqr_fraction_of_median": pooled[arm][n]["iqr"]
                / pooled[arm][n]["median"],
            }
        entry["speedup_pooled_median_cpu_over_mps"] = (
            pooled[c][n]["median"] / pooled[a][n]["median"]
        )
        disp[a] = entry

    # Max run-to-run spread anywhere, for the README caveat
    worst = max(
        (
            (
                max(per_run[r][a][n]["median"] for r in runs)
                - min(per_run[r][a][n]["median"] for r in runs)
            )
            / pooled[a][n]["median"],
            a,
            n,
        )
        for a in ARMS
        for n in sizes
    )

    # The boundary states what the receipts recorded, so it cannot outlive a rerun.
    missing = [r for r in runs if r not in hosts]
    if missing:
        raise SystemExit(f"no host receipt for run(s) {missing}")
    h0 = hosts[min(hosts)]
    for key in ("cpu_model", "torch_version", "torch_blas_info"):
        seen = {h.get(key) for h in hosts.values()}
        if len(seen) != 1:
            raise SystemExit(f"receipts disagree on {key}: {sorted(map(str, seen))}")
    summary = {
        "study": "offload-break-even",
        "claim_boundary": f"One {h0['cpu_model']} laptop, FP32 n x n products, "
        f"PyTorch {h0['torch_version']} CPU ({h0['torch_blas_info'].capitalize()} BLAS) versus MPS; "
        "unified memory, so the copy arm measures an in-DRAM copy, not a discrete-link transfer.",
        "host": {
            k: h0.get(k)
            for k in [
                "cpu_model",
                "cpu_perflevel0_cores",
                "cpu_perflevel1_cores",
                "memory_bytes",
                "os",
                "python",
                "torch_version",
                "torch_num_threads",
                "torch_blas_info",
                "mps_available",
            ]
        },
        "runs": {
            str(r): {
                "timestamp_start": hosts.get(r, {}).get("timestamp_start"),
                "elapsed_seconds": hosts.get(r, {}).get("elapsed_seconds"),
                "power_source": (
                    hosts.get(r, {}).get("power_source") or ""
                ).splitlines()[0]
                if hosts.get(r)
                else None,
            }
            for r in runs
        },
        "sizes": sizes,
        "batch": 16,
        "reps_per_arm_per_n": sorted(reps),
        "arms": ARMS,
        "crossovers": cross,
        "launch_floor_n_le_256": floor,
        "sixteen_launch_over_one_launch_ratio_n_le_256": ratio,
        "non_monotone": nonmono,
        "dispersion_at_crossover": disp,
        "worst_run_to_run_spread": {
            "fraction_of_pooled_median": worst[0],
            "arm": worst[1],
            "n": worst[2],
        },
        "medians_table": "medians.csv",
    }
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    print(f"runs={runs} sizes={sizes} reps={sorted(reps)}")
    print(
        "\nCrossovers (first n where MPS median < CPU median; stays ahead; per-run n; stable):"
    )
    for a, c in cross.items():
        print(
            f"  {a:14s} vs {c['versus']:10s} pooled n={c['pooled']['n']} stays={c['pooled']['stays_ahead']} "
            f"per-run={c['per_run_n']} stable={c['stable_across_runs']}"
        )
    print("\nLaunch floor (median of all samples with n<=256):")
    for a, f in floor.items():
        print(
            f"  {a:14s} pooled={f['pooled']['median']:.3e} s  iqr={f['pooled']['iqr']:.2e}  "
            f"per-run={[f'{f['per_run'][str(r)]['median']:.3e}' for r in runs]}"
        )
    print(
        f"\n16-launch / 1-launch ratio, n<=256: pooled median {ratio['pooled_median_of_per_n']:.2f} "
        f"(range {ratio['pooled_min']:.2f} to {ratio['pooled_max']:.2f}); per n: "
        + ", ".join(f"{n}:{v:.2f}" for n, v in ratio["per_n_pooled"].items())
    )
    print(
        "  per-run medians:",
        [f"{ratio['per_run'][str(r)]['median_of_per_n']:.2f}" for r in runs],
    )
    print("\nNon-monotone points (median lower than at previous n):")
    for r in runs:
        print(
            f"  run {r}: "
            + (
                ", ".join(
                    f"{d['arm']}@{d['n']} (-{100*d['drop_fraction']:.1f}%)"
                    for d in nonmono["per_run"][str(r)]
                )
                or "none"
            )
        )
    print(
        "  pooled: "
        + (
            ", ".join(
                f"{d['arm']}@{d['n']} (-{100*d['drop_fraction']:.1f}%)"
                for d in nonmono["pooled"]
            )
            or "none"
        )
    )
    print("  recurring in all runs:", nonmono["recurring_in_all_runs"] or "none")
    print("\nDispersion at pooled crossover sizes:")
    for a, e in disp.items():
        c = CPU_OF[a]
        print(
            f"  {a:14s} n={e['n']}: mps per-run medians {[f'{m:.3e}' for m in e[a]['per_run_median']]} "
            f"spread {100*e[a]['run_to_run_spread_fraction_of_pooled_median']:.1f}% of median, IQR {100*e[a]['pooled_iqr_fraction_of_median']:.1f}%; "
            f"cpu per-run {[f'{m:.3e}' for m in e[c]['per_run_median']]} spread {100*e[c]['run_to_run_spread_fraction_of_pooled_median']:.1f}%; "
            f"cpu/mps = {e['speedup_pooled_median_cpu_over_mps']:.2f}x"
        )
    print(
        f"\nWorst run-to-run spread of a median: {100*worst[0]:.1f}% ({worst[1]} at n={worst[2]})"
    )
    print("\nPooled medians (s):")
    print("  n      " + " ".join(f"{a:>13s}" for a in ARMS))
    for n in sizes:
        print(f"  {n:5d}  " + " ".join(f"{pooled[a][n]['median']:13.3e}" for a in ARMS))
    print(f"\nwrote {HERE / 'summary.json'} and {HERE / 'medians.csv'}")


if __name__ == "__main__":
    main()
