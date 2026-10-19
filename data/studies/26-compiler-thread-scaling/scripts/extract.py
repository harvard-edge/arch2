#!/usr/bin/env python3
"""Extract every 1-, 4-, and 8-thread CPU latency row in pinned IREE report."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPORT = HERE / "source/iree-full-benchmark-result-1559.md"
OUTPUT = HERE / "extracted.csv"
INVENTORY = HERE / "latency_inventory.csv"
GIST_REVISION = "e17830877c662d2e4caec8c68c64a52aaaa4a116"
REPORT_SHA256 = "40d74baeeb139f38e294193dff65d0da736ad8515049dfa29cabb1c062169c58"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_report() -> list[dict[str, str]]:
    text = REPORT.read_text(encoding="utf-8")
    actual_sha = sha256(REPORT)
    if actual_sha != REPORT_SHA256:
        raise ValueError(f"Pinned report hash mismatch: {actual_sha}")
    section = ""
    rows: list[dict[str, str]] = []
    inventory: list[dict[str, str]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.startswith("### "):
            section = line[4:].strip()
        if section not in {"Improved Latencies 🎉", "Similar Latencies"}:
            continue
        if (
            not line.startswith("|")
            or "Average Latency (ms)" in line
            or re.match(r"\|\s*-", line)
        ):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        # Gist Markdown URLs contain literal parentheses after percent-encoded
        # model text, so stop at the final `](URL)` boundary rather than `)`.
        first = re.match(r"\[(.*)\]\((https://.*)\)$", cells[0])
        if not first:
            continue
        name, series_url = first.groups()
        thread = re.search(r"(?<!\w)(1|4|8)-thread", name)
        current = re.match(r"([0-9.]+) \(vs\. ([0-9.]+), ([^)]+)\)", cells[1])
        median = re.match(r"([0-9.]+)", cells[2])
        stdev = re.match(r"([0-9.]+)", cells[3])
        if not (current and median and stdev):
            raise ValueError(
                f"Could not parse latency summary at report line {line_number}"
            )
        normalized_name = name.replace("\\\\", "")
        is_target_device = (
            "GCP-c2-standard-16" in name and "CPU-x86_64-CascadeLake" in normalized_name
        )
        is_target_backend = "with IREE-LLVM-CPU @" in name and "CPU-Sync" not in name
        if "CPU-Sync" in name:
            reason = "Excluded: CPU-Sync is the distinct local-sync driver, not the local-task thread-count sweep."
        elif not thread:
            reason = (
                "Excluded: no explicit 1-, 4-, or 8-thread local-task configuration."
            )
        elif not is_target_device:
            reason = "Excluded: different machine label or CPU architecture from the GCP c2-standard-16 Cascade Lake sweep."
        elif not is_target_backend:
            reason = (
                "Excluded: backend is not the IREE-LLVM-CPU local-task configuration."
            )
        else:
            reason = "Included: explicit 1/4/8-thread local-task row, matching GCP c2-standard-16 Cascade Lake labels, and IREE-LLVM-CPU backend."
        model = name[: thread.start()].strip() if thread else name
        config = name[thread.start() :].split(",", 1)[0] if thread else ""
        precision = re.search(r"\[([^]]+)\]", model)
        framework = re.search(r"\(([^)]+)\)", model)
        record = {
            "source_row_id": f"iree-full-benchmark-result-1559.md:L{line_number}",
            "source_section": section,
            "gist_revision": GIST_REVISION,
            "benchmark_name": name,
            "series_url": series_url,
            "model_and_input": model,
            "precision_and_shape": precision.group(1) if precision else "",
            "framework": framework.group(1) if framework else "",
            "thread_count": thread.group(1) if thread else "",
            "thread_config_tag": config,
            "backend": "IREE-LLVM-CPU (local-task)",
            "machine_label": "GCP-c2-standard-16",
            "architecture_label": "CPU-x86_64-CascadeLake",
            "reported_mean_ms": current.group(1),
            "base_mean_ms": current.group(2),
            "reported_change_vs_base": current.group(3),
            "reported_median_ms": median.group(1),
            "reported_stdev_ms": stdev.group(1),
            "selection_reason": reason,
        }
        inventory.append(
            {
                **record,
                "included_in_thread_scaling_extract": "yes"
                if reason.startswith("Included:")
                else "no",
            }
        )
        if reason.startswith("Included:"):
            rows.append(record)
    fields = list(inventory[0])
    with INVENTORY.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(inventory)
    return rows


def main() -> None:
    if not REPORT.is_file():
        raise FileNotFoundError(REPORT)
    rows = parse_report()
    keys = {(r["model_and_input"], r["thread_count"]) for r in rows}
    if len(rows) != 30 or len(keys) != 30:
        raise ValueError(
            f"Expected 30 unique thread-config rows, found {len(rows)} rows / {len(keys)} keys"
        )
    by_model: dict[str, set[str]] = {}
    for row in rows:
        by_model.setdefault(row["model_and_input"], set()).add(row["thread_count"])
    if len(by_model) != 10 or any(
        threads != {"1", "4", "8"} for threads in by_model.values()
    ):
        raise ValueError("Expected 10 workloads with exactly 1-, 4-, and 8-thread rows")
    fieldnames = list(rows[0])
    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(
        json.dumps(
            {
                "report_sha256": sha256(REPORT),
                "rows": len(rows),
                "workloads": len(by_model),
                "thread_counts_per_workload": [1, 4, 8],
                "output": str(OUTPUT.relative_to(HERE)),
                "output_sha256": sha256(OUTPUT),
                "inventory_rows": sum(1 for _ in INVENTORY.open(encoding="utf-8")) - 1,
                "inventory_sha256": sha256(INVENTORY),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
