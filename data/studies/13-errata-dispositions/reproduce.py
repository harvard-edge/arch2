#!/usr/bin/env python3
"""Re-extract vendor records and plot their reported fix dispositions."""
import collections
import csv
import json
from pathlib import Path
import subprocess
import sys
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))
from book._python.plots import COLORS, apply_style, save_figure_bundle
from evidence_bundle import verify_sources, record_build


def main():
    manifest = verify_sources(HERE, allow_missing_gitignored=True)
    subprocess.run([sys.executable, str(HERE / "extract.py")], check=True)
    rows = list(csv.DictReader((HERE / "derived/errata.csv").open()))
    assert len({(r["family"], r["erratum_id"]) for r in rows}) == len(rows)
    statuses = ["No Fix", "Plan Fix", "Fixed"]
    assert set(r["status"] for r in rows) == set(statuses)
    families = sorted({(r["vendor"], r["family"]) for r in rows})
    counts = []
    for vendor, family in families:
        c = collections.Counter(r["status"] for r in rows if r["family"] == family)
        counts.append(
            {
                "vendor": vendor,
                "family": family,
                "total": sum(c.values()),
                **{s: c[s] for s in statuses},
            }
        )
    with (HERE / "dispositions.csv").open("w") as f:
        writer = csv.DictWriter(f, fieldnames=list(counts[0]))
        writer.writeheader()
        writer.writerows(counts)
    totals = collections.Counter(r["status"] for r in rows)
    summary = {
        "entries": len(rows),
        "families": len(families),
        "status_counts": dict(totals),
        "no_fix_fraction": totals["No Fix"] / len(rows),
        "unit": "Published family/erratum entries, with least-resolved disposition across steppings",
    }
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    apply_style()
    fig, ax = plt.subplots(figsize=(6.8, 4.25))
    colors = [COLORS["constraints"], COLORS["methods"], COLORS["evidence"]]
    labels = ["No planned fix", "Planned fix", "Fixed"]
    left = [0.0] * len(counts)
    for status, color, label, hatch in zip(
        statuses, colors, labels, [None, "////", "..."]
    ):
        values = [c[status] / c["total"] for c in counts]
        ax.barh(
            range(len(counts)),
            values,
            left=left,
            color=color,
            label=label,
            height=0.64,
            hatch=hatch,
            edgecolor="white",
            linewidth=0.25,
        )
        left = [a + b for a, b in zip(left, values)]
    for i, row in enumerate(counts):
        ax.text(1.02, i, str(row["total"]), va="center", ha="left", fontsize=5.8)
    ax.text(1.02, -1.1, "Entries", fontsize=5.8, ha="left")
    ax.set(
        yticks=range(len(counts)),
        yticklabels=[f"{c['vendor']}  {c['family']}" for c in counts],
        ylim=(len(counts) - 0.45, -1.65),
        xlim=(0, 1.12),
        xlabel="Share of published erratum entries in each document",
    )
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1])
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    ax.grid(axis="x", color=COLORS["grid"], lw=0.4)
    ax.grid(axis="y", visible=False)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.legend(loc="upper center", bbox_to_anchor=(0.47, 1.11), ncol=3, frameon=False)
    fig.text(
        0.5,
        0.985,
        "Vendor fix dispositions in 19 processor-family documents",
        ha="center",
        va="top",
        fontsize=7.2,
    )
    fig.text(
        0.27,
        0.015,
        "Snapshots dated 2020–2026. No planned fix does not mean no workaround.",
        fontsize=5.8,
        color=COLORS["muted"],
    )
    fig.subplots_adjust(left=0.27, right=0.97, top=0.87, bottom=0.12)
    save_figure_bundle(fig, HERE / "figure")
    plt.close(fig)
    record_build(
        HERE,
        {
            "source_files_hash_verified": len(manifest["files"]),
            "vendor_PDFs": 19,
            "extraction_completeness_passed": True,
            "unique_family_id_pairs": len(rows),
        },
        "PDF identities, parser completeness checks, snapshot comparison, and arithmetic verified. Body fields and subsystem labels are not validated; no independent semantic audit of all entries.",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
