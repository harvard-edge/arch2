#!/usr/bin/env python3
"""Record what changed across the two largest steps of the nightly series.

For each step, reads the sibling HTML nightly reports on either side, which record the
tested commit and the failing logs, and the public GitHub comparison of those two commits.
Writes derived/step_commits.json. Commit lists and file lists come from the comparison.
A window names what changed between two reports. It is not a bisection.

Downloaded bytes are untrusted data: nothing here executes or imports them.
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import html
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = "https://ibex.reports.lowrisc.org/opentitan/ibex-regr-report-{}.html"
COMPARE = "https://api.github.com/repos/lowRISC/ibex/compare/{}...{}"
GROUP = "riscv_pmp_full_random_test"
STEPS = [("2024-07-03", "2024-07-04"), ("2025-07-01", "2025-07-02")]
HEADERS = {"User-Agent": "arch2-ibex-nightly-collector/1.0"}


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60) as resp:
        return resp.read()


def read_report(date: str) -> dict:
    url = REPORT.format(dt.date.fromisoformat(date).strftime("%d-%m-%Y"))
    body = fetch(url)
    page = body.decode("utf-8", "replace")
    text = html.unescape(re.sub(r"<[^>]+>", " ", page))
    commits = sorted(set(re.findall(r"\b[0-9a-f]{40}\b", page)))
    if len(commits) != 1:
        raise SystemExit(f"{date}: expected one commit, found {commits}")
    row = re.search(rf"{GROUP}\s+(\d+)\s+(\d+)\s+[\d.]+%", text)
    passing, total = int(row.group(1)), int(row.group(2))
    blocks = re.split(rf"\n(?={GROUP}\.\d+\n-{{5,}})", text)[1:]
    kinds = collections.Counter()
    for block in blocks:
        first = re.search(r"\[E\] \d+: (.*)", block[:3000])
        line = first.group(1) if first else ""
        kinds["cosim_mismatch" if "Cosim mismatch" in line else "other"] += 1
    return {
        "date": date,
        "url": url,
        "sha256": hashlib.sha256(body).hexdigest(),
        "commit": commits[0],
        "group_passing": passing,
        "group_total": total,
        "group_failure_logs": dict(kinds),
    }


def main() -> None:
    windows = []
    for before, after in STEPS:
        first, second = read_report(before), read_report(after)
        url = COMPARE.format(first["commit"], second["commit"])
        body = fetch(url)
        cmp = json.loads(body)
        files = [
            {"file": f["filename"], "added": f["additions"], "removed": f["deletions"]}
            for f in cmp["files"]
        ]
        windows.append(
            {
                "before": first,
                "after": second,
                "compare_url": url,
                "compare_status": cmp["status"],
                "commits": [
                    {"sha": c["sha"], "subject": c["commit"]["message"].splitlines()[0]}
                    for c in cmp["commits"]
                ],
                "files": files,
                "rtl_files": [f["file"] for f in files if f["file"].startswith("rtl/")],
            }
        )
    out = {
        "group": GROUP,
        "fetched_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "windows": windows,
    }
    (ROOT / "derived/step_commits.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
