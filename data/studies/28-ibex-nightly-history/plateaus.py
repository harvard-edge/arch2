#!/usr/bin/env python3
"""Split the nightly series at its three largest level shifts and summarize each plateau.

A shift is the largest absolute difference between the 14-report means on either side of
a report, with chosen shifts at least 60 days apart. Writes derived/plateaus.csv.
"""
import csv
import datetime as dt
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
nightly = list(csv.DictReader((HERE / "derived/nightly.csv").open(encoding="utf-8")))
cells = list(csv.DictReader((HERE / "derived/group_night.csv").open(encoding="utf-8")))
dates = [r["date"] for r in nightly]
ys = [float(r["pass_pct"]) for r in nightly]
failing = {d: set() for d in dates}
for c in cells:
    if c["nonpass"] == "True":
        failing[c["date"]].add(c["test_name"])
jumps = sorted(
    (
        (abs(st.mean(ys[i : i + 14]) - st.mean(ys[i - 14 : i])), i)
        for i in range(14, len(ys) - 14)
    ),
    reverse=True,
)
picked = []
for _, i in jumps:
    d = dt.date.fromisoformat(dates[i])
    if all(abs((d - dt.date.fromisoformat(dates[j])).days) > 60 for j in picked):
        picked.append(i)
    if len(picked) == 3:
        break
bounds = [0] + sorted(picked) + [len(dates)]
with (HERE / "derived/plateaus.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(
        [
            "first_date",
            "last_date",
            "reports",
            "pass_pct_median",
            "pass_pct_sd",
            "failing_groups_median",
            "distinct_failing_groups",
            "mean_groups_changed_between_reports",
        ]
    )
    for a, b in zip(bounds, bounds[1:]):
        ds = dates[a:b]
        y = ys[a:b]
        change = [len(failing[p] ^ failing[q]) for p, q in zip(ds, ds[1:])]
        w.writerow(
            [
                ds[0],
                ds[-1],
                len(ds),
                f"{st.median(y):.2f}",
                f"{st.pstdev(y):.2f}",
                st.median(len(failing[d]) for d in ds),
                len(set().union(*(failing[d] for d in ds))),
                f"{st.mean(change):.2f}",
            ]
        )
