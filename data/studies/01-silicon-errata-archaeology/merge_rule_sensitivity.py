#!/usr/bin/env python3
"""Compare the written merge rule with the merges the study actually applied.

reporting_classes.yml states a rule: a class that fails the audit test is merged
with the class it is most often confused with, when the merged class passes the
same test; otherwise it is dropped. The groupings in that file do not follow the
rule for three of the five failed classes. This script reports both and does not
choose between them.

Inputs:
    audit_sample.csv, errata_classified.csv less excluded_rows.csv (through
    audit_metrics.load_population), reporting_classes.yml

Output:
    merge_rule_sensitivity.json

The written-rule grouping is derived here from the audit labels; no merge and no
outcome is typed in. Shares for every grouping come from audit_metrics.compute,
the path that produces the figure's numbers.

Readings, because the rule leaves two things open:
    outgoing     "confused with" counts the class's own audited rows that the
                 audit assigned to another class. This is the primary reading.
    symmetric    also counts rows of the other class that the audit assigned
                 here. Coherence then ties, so both branches are computed.
    sequential   outgoing confusion recomputed against the groups formed so far,
                 over every order of the failed classes.

Where a count ties, this script computes every branch and chooses none. It adds
no merge rule and no tiebreak. Three sensitivity readings sit beside the above:
    title once        confusion counts each normalized title once, the convention
                      of the study's distinct-title shares. Every tied branch is scored.
    single label      each audited row, relabeled to each other class in turn, with
                      the written rule rederived from the changed labels and every
                      tied branch scored. Point estimates only.
    three labels      the three machine-check rows labeled instruction execution,
                      relabeled to interrupts: the other side of that count.
    class order       rule shares over random orders of the rule classes, for rows
                      matched on the title. Rows matched on the body stay as assigned.
                      Scored unmerged, and for the applied and written-rule groupings.

Numbers here are modeled: they rest on one model's audit labels, and no
independent human relabeling exists.

    python3 merge_rule_sensitivity.py
"""

from __future__ import annotations

import csv
import itertools
import json
import random
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from audit_metrics import HERE, MIN_PRECISION, MIN_WILSON_LOW, SEED, compute, load_population, wilson
from classify_errata import compile_rules

MEMORY_SYSTEM = [
    "Memory controller and DRAM",
    "Coherence and on-die or socket fabric",
    "Caches, TLBs, and load-store ordering",
]
CLASS_ORDERS = 2_000


def slug(name: str) -> str:
    return name.split()[0].strip(",").lower()


def title_key(title: str) -> str:
    """The normalization audit_metrics.compute uses for distinct titles."""
    return re.sub(r"[^a-z0-9]", "", title.lower())


def confusion(rows: list[dict]) -> dict[str, Counter]:
    m: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        m[r["rule_label"]][r["audit_label"]] += 1
    return m


def main() -> int:
    aud = list(csv.DictReader((HERE / "audit_sample.csv").open()))
    pop = load_population()
    applied = yaml.safe_load((HERE / "reporting_classes.yml").read_text())
    Nc = Counter(r["subsystem"] for r in pop)
    classes = sorted(c for c in Nc if c != "Unclassified")

    matrix = confusion(aud)
    titles: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    for r in aud:
        titles[r["rule_label"]][r["audit_label"]].add(title_key(r["title"]))

    def test(members: set[str], sample: list[dict] | None = None) -> dict:
        rows = [r for r in (aud if sample is None else sample) if r["rule_label"] in members]
        k = sum(r["audit_label"] in members for r in rows)
        lo, hi = wilson(k, len(rows))
        return {
            "agree": k,
            "audited": len(rows),
            "precision": k / len(rows),
            "wilson_low": lo,
            "wilson_high": hi,
            "passes": k / len(rows) >= MIN_PRECISION and lo >= MIN_WILSON_LOW,
        }

    def out_count(c: str, o: str) -> int:
        return matrix[c][o]

    def sym_count(c: str, o: str) -> int:
        return matrix[c][o] + matrix[o][c]

    def title_count(c: str, o: str) -> int:
        return len(titles[c][o])

    failed = [c for c in classes if not test({c})["passes"]]
    passed = [c for c in classes if c not in failed]

    def targets(c: str, count) -> list[str]:
        scores = {o: count(c, o) for o in classes if o != c}
        top = max(scores.values())
        return sorted(o for o, v in scores.items() if v == top)

    def grouping(choice: dict[str, str | None], label: str) -> dict:
        """Union the chosen merges. A failed class with no merge is dropped."""
        parent = {c: c for c in classes}

        def find(c: str) -> str:
            while parent[c] != c:
                c = parent[c]
            return c

        for c, t in choice.items():
            if t is not None:
                parent[find(c)] = find(t)
        groups = defaultdict(list)
        for c in classes:
            groups[find(c)].append(c)
        dropped = [c for c, t in choice.items() if t is None]
        for c in dropped:
            if len(groups[find(c)]) == 1:
                del groups[find(c)]
            else:
                dropped = [d for d in dropped if d != c]
        reporting = [
            {"name": " + ".join(sorted(m, key=lambda x: -Nc[x])), "members": sorted(m, key=lambda x: -Nc[x])}
            for m in groups.values()
        ]
        return {
            "label": label,
            "reporting": sorted(reporting, key=lambda R: R["name"]),
            "not_resolved": {
                "name": "Not resolved to a reported class",
                "members": sorted(dropped) + ["Unclassified"],
            },
        }

    def rule_choice(count, pick=None) -> dict[str, str | None]:
        choice: dict[str, str | None] = {}
        for c in failed:
            ts = targets(c, count)
            t = (pick or {}).get(c)
            if t is None:
                if len(ts) > 1:
                    raise SystemExit(f"tie for {c} with no branch named: {ts}")
                t = ts[0]
            choice[c] = t if test({c, t})["passes"] else None
        return choice

    def branches(count, fails: list[str], sample: list[dict]) -> list[dict[str, str | None]]:
        """Every outcome of the written rule when ties are left open."""
        opts = [targets(c, count) for c in fails]
        return [
            {c: (t if test({c, t}, sample)["passes"] else None) for c, t in zip(fails, combo)}
            for combo in itertools.product(*opts)
        ]

    # --- per failed class: the rule against what was done -----------------------
    applied_group = {m: R["name"] for R in applied["reporting"] for m in R["members"]}
    per_failed = {}
    written_choice = rule_choice(out_count)
    for c in failed:
        ts = targets(c, out_count)
        mates = sorted(m for m, g in applied_group.items() if g == applied_group.get(c) and m != c)
        was_dropped = c in applied["not_resolved"]["members"]
        per_failed[c] = {
            "population": Nc[c],
            "alone": test({c}),
            "relabeled_as": {k: v for k, v in matrix[c].most_common() if k != c},
            "most_confused_outgoing": ts,
            "most_confused_symmetric": targets(c, sym_count),
            "merge_with_most_confused": test({c, ts[0]}),
            "written_rule": f"merge with {written_choice[c]}" if written_choice[c] else "drop",
            "applied": "drop" if was_dropped else f"merged with {'; '.join(mates)}",
            "follows_written_rule": (not was_dropped)
            and mates == [written_choice[c]],
            "every_passing_pair": {
                o: test({c, o}) for o in classes if o != c and test({c, o})["passes"]
            },
        }

    # --- groupings --------------------------------------------------------------
    sym_ties = {c: targets(c, sym_count) for c in failed}
    readings = {
        "written_rule": grouping(written_choice, "Written rule, outgoing confusion"),
    }
    for t in sym_ties["Coherence and on-die or socket fabric"]:
        key = "symmetric_coherence_to_" + slug(t)
        readings[key] = grouping(
            rule_choice(sym_count, {"Coherence and on-die or socket fabric": t}),
            f"Written rule, symmetric confusion, coherence tie broken toward {t}",
        )

    # One departure repaired at a time, the rest left as applied.
    def repair(c: str, target: str | None, label: str) -> dict:
        r = {
            "label": label,
            "reporting": [dict(x, members=list(x["members"])) for x in applied["reporting"]],
            "not_resolved": dict(applied["not_resolved"], members=list(applied["not_resolved"]["members"])),
        }
        for R in r["reporting"]:
            if c in R["members"]:
                R["members"].remove(c)
        if c in r["not_resolved"]["members"]:
            r["not_resolved"]["members"].remove(c)
        for R in r["reporting"]:
            if target in R["members"]:
                R["members"].append(c)
        return r

    title_branches = branches(title_count, failed, aud)
    title_ties = {c: targets(c, title_count) for c in failed}
    for choice in title_branches:
        mc = "Machine check and error reporting"
        key = "title_once_machine_to_" + slug(choice[mc] or "dropped")
        readings[key] = grouping(
            choice, f"Written rule, each title counted once, machine check toward {choice[mc]}"
        )

    for c in failed:
        if not per_failed[c]["follows_written_rule"]:
            t = written_choice[c]
            key = "only_" + slug(c)
            readings[key] = repair(c, t, f"As applied, except {c} merged with {t}")

    # --- sequential reading -----------------------------------------------------
    outcomes = Counter()
    tied_orders = 0
    for order in itertools.permutations(failed):
        groups = [{c} for c in classes]
        tied = False
        for c in order:
            mine = next(g for g in groups if c in g)
            scores = []
            for g in groups:
                if g is mine:
                    continue
                n = sum(matrix[a][b] for a in mine for b in g)
                scores.append((n, sorted(g)))
            top = max(s[0] for s in scores)
            best = sorted(s[1] for s in scores if s[0] == top)
            tied = tied or len(best) > 1
            other = next(g for g in groups if sorted(g) == best[0])
            if test(mine | other)["passes"]:
                groups.remove(mine)
                groups.remove(other)
                groups.append(mine | other)
        tied_orders += tied
        outcomes[tuple(sorted(tuple(sorted(g)) for g in groups))] += 1
    written_key = tuple(
        sorted(tuple(sorted(R["members"])) for R in readings["written_rule"]["reporting"])
    )
    # Dropped classes remain singletons in the sequential groups, so compare the
    # written grouping with its dropped classes added as singletons.
    dropped_now = [m for m in readings["written_rule"]["not_resolved"]["members"] if m != "Unclassified"]
    written_key = tuple(sorted(written_key + tuple((d,) for d in dropped_now)))

    # --- score every grouping through one path ----------------------------------
    def summarize(rep: dict, **kw) -> dict:
        out, _ = compute(rep, **kw)
        rows = []
        for name, d in out["shares"].items():
            per = out["per_reporting_class"].get(name, {})
            rows.append(
                {
                    "class": name,
                    "rule_count": d["rule_count"],
                    "rule_share": d["rule_share"],
                    "adjusted_share": d["adjusted_share"],
                    "adjusted_ci95": d["adjusted_ci95"],
                    "distinct_title_share": out["unique_title_shares"][name],
                    "agree": per.get("agree"),
                    "audited": per.get("audited"),
                    "precision_sample": per.get("precision_sample"),
                    "precision_weighted": per.get("precision_weighted"),
                    "wilson_low": per.get("wilson_low"),
                }
            )
        reported = [r for r in rows if r["class"] != rep["not_resolved"]["name"]]
        return {
            "label": rep.get("label", "As applied (reporting_classes.yml)"),
            "not_resolved_members": rep["not_resolved"]["members"],
            "classes": rows,
            "largest_by_rule": max(reported, key=lambda r: r["rule_share"])["class"],
            "largest_by_adjusted": max(reported, key=lambda r: r["adjusted_share"])["class"],
            "largest_rule_share": max(r["rule_share"] for r in reported),
            "largest_adjusted_share": max(r["adjusted_share"] for r in reported),
            "agreement_reporting_weighted": out["agreement_reporting_weighted"],
            "agreement_reporting_weighted_ci95": out["agreement_reporting_weighted_ci95"],
        }

    scored = {"as_applied": summarize(applied)}
    for key, rep in readings.items():
        scored[key] = summarize(rep)

    # The three rows that send machine check to instruction execution, moved to the
    # other side of the count. A changed label set, not a merge choice.
    mc, ix = "Machine check and error reporting", "Instruction execution and exceptions"
    irq = "Interrupts, timers, reset, and system management"
    flipped = [
        dict(r, audit_label=irq) if r["rule_label"] == mc and r["audit_label"] == ix else r
        for r in aud
    ]
    fm = confusion(flipped)
    three = branches(lambda c, o: fm[c][o], [c for c in classes if not test({c}, flipped)["passes"]], flipped)
    for n, choice in enumerate(three):
        key = "three_machine_rows_to_interrupts" + (f"_{n}" if n else "")
        scored[key] = summarize(
            grouping(choice, "Written rule rederived with three machine-check rows relabeled to interrupts"),
            aud=flipped,
        )

    mem_rep = {
        "label": "Memory controllers, coherence fabrics, and caches against everything else",
        "reporting": [{"name": "Memory system", "members": MEMORY_SYSTEM}],
        "not_resolved": {
            "name": "Everything else",
            "members": [c for c in Nc if c not in MEMORY_SYSTEM],
        },
    }
    memory = summarize(mem_rep)["classes"][0]

    # --- single-label changes under the written rule ----------------------------
    base_rule = scored["written_rule"]["largest_rule_share"]
    scope = [i for i, r in enumerate(aud) if r["rule_label"] != "Unclassified"]
    changes = moved = settled = 0
    moved_rows = []
    sweep_rule, sweep_adj, sweep_mem = [], [], []
    sweep_classes_rule, sweep_classes_adj = set(), set()
    fewest_classes = len(classes)

    def fails_in(sample: list[dict]) -> list[str]:
        return [c for c in classes if not test({c}, sample)["passes"]]

    for i in scope:
        for label in classes:
            if label == aud[i]["audit_label"]:
                continue
            changes += 1
            sample = list(aud)
            sample[i] = dict(aud[i], audit_label=label)
            m2 = confusion(sample)
            fails = fails_in(sample)
            tops = set()
            for choice in branches(lambda c, o: m2[c][o], fails, sample):
                s = summarize(grouping(choice, "single label"), aud=sample, pop=pop, replicates=0)
                sweep_rule.append(s["largest_rule_share"])
                sweep_adj.append(s["largest_adjusted_share"])
                sweep_classes_rule.add(s["largest_by_rule"])
                sweep_classes_adj.add(s["largest_by_adjusted"])
                fewest_classes = min(fewest_classes, len(s["classes"]) - 1)
                tops.add(round(s["largest_rule_share"], 12))
            sweep_mem.append(
                summarize(mem_rep, aud=sample, pop=pop, replicates=0)["classes"][0]["adjusted_share"]
            )
            if tops != {round(base_rule, 12)}:
                moved += 1
                settled += round(base_rule, 12) not in tops
                moved_rows.append(
                    {
                        "erratum_id": aud[i]["erratum_id"],
                        "from": aud[i]["audit_label"],
                        "to": label,
                        "largest_rule_shares": sorted(tops),
                    }
                )

    # --- rule-class order --------------------------------------------------------
    rules = compile_rules(HERE / "classification_rules.yml")
    title_rows = [r for r in pop if r["matched_on"] == "title"]
    fixed = Counter(r["subsystem"] for r in pop if r["matched_on"] != "title")
    hits = []
    for r in title_rows:
        hit = [c["name"] for c in rules if any(rx.search(r["title"]) for _, rx in c["patterns"])]
        if not hit or hit[0] != r["subsystem"]:
            raise SystemExit(f"first match disagrees with the label: {r['erratum_id']}")
        hits.append(hit)
    rng = random.Random(SEED)
    names = [c["name"] for c in rules]
    order_top, order_mem = [], []
    order_groupings = {
        "as_applied": {R["name"]: R["members"] for R in applied["reporting"]},
        "written_rule": {R["name"]: R["members"] for R in readings["written_rule"]["reporting"]},
    }
    order_merged = {k: [] for k in order_groupings}
    order_merged_top = {k: set() for k in order_groupings}
    for _ in range(CLASS_ORDERS):
        rank = {n: k for k, n in enumerate(rng.sample(names, len(names)))}
        tally = Counter(fixed)
        for hit in hits:
            tally[min(hit, key=rank.__getitem__)] += 1
        order_top.append(max(v for c, v in tally.items() if c != "Unclassified") / len(pop))
        order_mem.append(sum(tally[c] for c in MEMORY_SYSTEM) / len(pop))
        for key, group in order_groupings.items():
            sizes = {name: sum(tally[m] for m in members) for name, members in group.items()}
            top = max(sizes.values())
            order_merged[key].append(top / len(pop))
            order_merged_top[key].update(name for name, v in sizes.items() if v == top)

    # --- what the readings span --------------------------------------------------
    named = [s for k, s in scored.items()]
    named_rule = [s["largest_rule_share"] for s in named]
    named_adj = [s["largest_adjusted_share"] for s in named]
    named_upper = [
        c["adjusted_ci95"][1]
        for s in named
        for c in s["classes"]
        if not c["class"].startswith("Not resolved")
    ]

    result = {
        "criterion": {
            "min_precision": MIN_PRECISION,
            "min_wilson_low": MIN_WILSON_LOW,
            "text": "A failed class is merged with the class it is most often confused with, when the merged class passes the same test; otherwise it is dropped.",
        },
        "evidence_class": "modeled; audit labels are one model's reading, with no independent human relabeling",
        "failed_classes": failed,
        "passing_classes": passed,
        "per_failed_class": per_failed,
        "departures": sorted(c for c, d in per_failed.items() if not d["follows_written_rule"]),
        "passing_classes_merged_as_applied": sorted(
            c
            for c in passed
            if sum(m in passed for R in applied["reporting"] if c in R["members"] for m in R["members"]) > 1
        ),
        "groupings": scored,
        "memory_system_any_grouping": memory,
        "sequential_reading": {
            "orders": sum(outcomes.values()),
            "distinct_outcomes": len(outcomes),
            "orders_matching_written_rule": outcomes.get(written_key, 0),
            "orders_with_a_tie": tied_orders,
        },
        "symmetric_most_confused": sym_ties,
        "machine_check_target": {
            "rows": {
                k: v
                for k, v in matrix["Machine check and error reporting"].items()
                if k != "Machine check and error reporting"
            },
            "distinct_titles": {
                k: len(v)
                for k, v in titles["Machine check and error reporting"].items()
                if k != "Machine check and error reporting"
            },
        },
        "title_once_most_confused": title_ties,
        "single_label_changes": {
            "scope": "Written rule rederived after changing one audit label; ties branched, not broken; point estimates only",
            "rows": len(scope),
            "changes": changes,
            "changes_moving_largest_rule_share": moved,
            "of_which_with_no_tied_branch_at_the_base_share": settled,
            "moved": moved_rows,
            "largest_rule_share_range": [min(sweep_rule), max(sweep_rule)],
            "largest_adjusted_share_range": [min(sweep_adj), max(sweep_adj)],
            "classes_largest_by_rule": sorted(sweep_classes_rule),
            "classes_largest_by_adjusted": sorted(sweep_classes_adj),
            "memory_system_adjusted_range": [min(sweep_mem), max(sweep_mem)],
            "fewest_reported_classes": fewest_classes,
        },
        "readings_span": {
            "named_groupings": sorted(scored),
            "largest_rule_share_range": [min(named_rule + sweep_rule), max(named_rule + sweep_rule)],
            "largest_adjusted_share_range": [min(named_adj + sweep_adj), max(named_adj + sweep_adj)],
            "classes_largest_by_rule": sorted(
                sweep_classes_rule | {s["largest_by_rule"] for s in named}
            ),
            "classes_largest_by_adjusted": sorted(
                sweep_classes_adj | {s["largest_by_adjusted"] for s in named}
            ),
            "highest_upper_interval_named": max(named_upper),
            "fewest_reported_classes": min(
                [fewest_classes] + [len(s["classes"]) - 1 for s in named]
            ),
        },
        "class_order": {
            "scope": "Rule classes only, no merging; rows matched on the title reassigned, rows matched on the body and Unclassified held",
            "orders": CLASS_ORDERS,
            "seed": SEED,
            "title_matched": len(hits),
            "title_matched_more_than_one_class": sum(len(h) > 1 for h in hits),
            "largest_class_share_range": [min(order_top), max(order_top)],
            "memory_system_rule_share_range": [min(order_mem), max(order_mem)],
            "largest_merged_class": {
                key: {
                    "share_range": [min(v), max(v)],
                    "median_share": statistics.median(v),
                    "classes_largest": sorted(order_merged_top[key]),
                }
                for key, v in order_merged.items()
            },
        },
    }
    (HERE / "merge_rule_sensitivity.json").write_text(json.dumps(result, indent=2) + "\n")

    print("failed classes and the rule")
    for c, d in per_failed.items():
        m = d["merge_with_most_confused"]
        flag = "follows" if d["follows_written_rule"] else "DEPARTS"
        print(
            f"  {flag}  {c}: alone {d['alone']['agree']}/18; most confused {d['most_confused_outgoing']}; "
            f"merge {m['agree']}/{m['audited']} low {m['wilson_low']:.3f} pass={m['passes']}; applied: {d['applied']}"
        )
    print(f"passing classes merged as applied: {result['passing_classes_merged_as_applied']}")
    print(f"sequential: {result['sequential_reading']}")
    for key, s in scored.items():
        print(f"\n{key}: {s['label']}")
        for r in s["classes"]:
            l, h = r["adjusted_ci95"]
            print(
                f"  {100 * r['rule_share']:5.1f} / {100 * r['adjusted_share']:5.1f} "
                f"[{100 * l:.1f}, {100 * h:.1f}] / {100 * r['distinct_title_share']:5.1f}  {r['class']}"
            )
    print(f"\nmachine check target: {result['machine_check_target']}")
    print(f"title-once ties: { {c: t for c, t in title_ties.items() if len(t) > 1} }")
    print(f"single label: {changes} changes, {moved} move the largest rule share")
    print(f"span: {result['readings_span']}")
    print(f"class order: {result['class_order']}")
    l, h = memory["adjusted_ci95"]
    print(
        f"\nmemory system, any grouping: {100 * memory['rule_share']:.1f} / "
        f"{100 * memory['adjusted_share']:.1f} [{100 * l:.1f}, {100 * h:.1f}] / "
        f"{100 * memory['distinct_title_share']:.1f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
