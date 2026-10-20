#!/usr/bin/env python3
"""Render nested time boundaries and measured step costs from one retained job."""
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))
from book._python.plots import COLORS, FONT_SIZES, apply_style, save_figure_bundle
from evidence_bundle import record_build, verify_sources


def duration(row):
    return (
        datetime.fromisoformat(row["completed_at"])
        - datetime.fromisoformat(row["started_at"])
    ).total_seconds()


def main():
    manifest = verify_sources(HERE, allow_missing_gitignored=True)
    archive = (
        HERE / "raw/librelane-spm-ihp-sg13g2-run-37749124131-artifact-11539925672.zip"
    )
    if archive.exists():
        subprocess.run(
            [sys.executable, str(HERE / "extract_stage_costs.py")], check=True
        )
    rows = list(csv.DictReader((HERE / "stage-costs.csv").open()))
    for row in rows:
        row["runtime_seconds"] = float(row["runtime_seconds"])
        row["step_id"] = int(row["step_id"])
    assert sorted(r["step_id"] for r in rows) == list(range(1, 79))
    total = sum(r["runtime_seconds"] for r in rows)
    job = json.loads((HERE / "raw/design-job.json").read_text())
    run = json.loads((HERE / "raw/workflow-run.json").read_text())
    assert job["run_id"] == run["id"] == 37749124131
    assert (
        job["head_sha"] == run["head_sha"] == "36aa197408e1b6508fc4862b7758d21ec8853048"
    )
    assert job["conclusion"] == "success"
    actions = [s for s in job["steps"] if s["name"] == "Run Test"]
    assert len(actions) == 1 and actions[0]["conclusion"] == "success"
    test_seconds, job_seconds = duration(actions[0]), duration(job)
    assert total <= test_seconds <= job_seconds
    ranked = sorted(rows, key=lambda r: (-r["runtime_seconds"], r["step_id"]))
    top, other = ranked[:6], ranked[6:]
    labels = {
        "openroad-detailedrouting": "Detailed routing (OpenROAD)",
        "magic-writelef": "LEF generation (Magic)",
        "magic-streamout": "Layout streamout (Magic)",
        "klayout-drc": "Design-rule checks (KLayout)",
        "magic-drc": "Design-rule checks (Magic)",
        "openroad-cts": "Clock-tree synthesis (OpenROAD)",
    }
    display = [
        {
            "label": labels[r["step_name"]],
            "step_ids": str(r["step_id"]),
            "seconds": r["runtime_seconds"],
        }
        for r in top
    ]
    display.append(
        {
            "label": f"Other {len(other)} steps (combined)",
            "step_ids": ";".join(str(r["step_id"]) for r in other),
            "seconds": sum(r["runtime_seconds"] for r in other),
        }
    )
    with (HERE / "plot_rows.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(display[0]))
        w.writeheader()
        w.writerows(display)
    boundaries = {
        "sum_step_intervals_seconds": round(total, 3),
        "run_test_action_seconds": test_seconds,
        "complete_design_job_seconds": job_seconds,
        "semantics": "Nested intervals, not additive cost components. API timestamps have one-second resolution.",
    }
    (HERE / "time_boundaries.json").write_text(json.dumps(boundaries, indent=2) + "\n")

    apply_style()
    fig, (ax, scope) = plt.subplots(
        2, 1, figsize=(6.8, 4.7), gridspec_kw={"height_ratios": [2, 1.1]}
    )
    y = list(range(len(display)))
    ax.barh(
        y,
        [r["seconds"] for r in display],
        height=0.62,
        color=[COLORS["evidence"]] * 6 + [COLORS["row"]],
        edgecolor=COLORS["evidence_ink"],
        linewidth=0.4,
    )
    ax.set(
        yticks=y,
        yticklabels=[r["label"] for r in display],
        xlim=(0, 31),
        ylim=(len(display) - 0.3, -0.7),
        xlabel="Recorded step time (seconds)",
    )
    for i, r in enumerate(display):
        ax.text(
            r["seconds"] + 0.45,
            i,
            f'{r["seconds"]:.2f}',
            va="center",
            fontsize=FONT_SIZES["annotation"],
        )
    ax.set_title(f"(a) All 78 step intervals: {total:.1f} seconds", loc="left", pad=9)
    scope_labels = [
        "Sum of 78 step intervals",
        "Run Test action",
        "Complete design CI job",
    ]
    scope_values = [total, test_seconds, job_seconds]
    scope.barh(
        range(3),
        scope_values,
        height=0.55,
        color=[COLORS["evidence"], COLORS["purple"], COLORS["amber"]],
    )
    scope.set(
        yticks=range(3),
        yticklabels=scope_labels,
        ylim=(2.65, -0.65),
        xlim=(0, 335),
        xlabel="Elapsed seconds at each accounting boundary",
    )
    for i, value in enumerate(scope_values):
        scope.text(
            value + 4, i, f"{value:.1f}", va="center", fontsize=FONT_SIZES["annotation"]
        )
    scope.set_title(
        "(b) The enclosing job also includes setup and other CI work", loc="left", pad=9
    )
    for axis in (ax, scope):
        axis.grid(axis="x", color=COLORS["grid"], linewidth=0.5)
        axis.grid(axis="y", visible=False)
        axis.spines[["top", "right", "left"]].set_visible(False)
        axis.tick_params(axis="y", length=0, pad=5, labelsize=FONT_SIZES["tick"])
    fig.subplots_adjust(left=0.335, right=0.94, top=0.91, bottom=0.11, hspace=0.68)
    save_figure_bundle(fig, HERE / "figure")
    save_figure_bundle(
        fig,
        ROOT
        / "book/contents/chapters/06-environments/images/fig-ch06-implementation-stage-costs",
    )
    plt.close(fig)
    files = sorted(
        p
        for p in HERE.rglob("*")
        if p.is_file()
        and p.name not in {"sha256-manifest.txt", "build_receipt.json"}
        and "__pycache__" not in p.parts
    )
    (HERE / "sha256-manifest.txt").write_text(
        "".join(
            f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(HERE)}\n"
            for p in files
        )
    )
    record_build(
        HERE,
        {
            "source_files_hash_verified": len(manifest["files"]),
            "all_78_numbered_steps_plotted_or_grouped": True,
            "raw_job_and_run_identities_match": True,
            "nested_duration_order": boundaries,
        },
        "Source-byte verification and offline extraction of one selected public CI artifact. No tool rerun, industry cost estimate, causal intervention, or AI comparison.",
    )
    print(json.dumps(boundaries, indent=2))


if __name__ == "__main__":
    main()
