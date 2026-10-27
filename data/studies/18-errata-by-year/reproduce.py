#!/usr/bin/env python3
"""Plot retained erratum-entry counts against reference-family introduction year."""
import collections
import csv
import json
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SHARED = HERE.parent / "13-errata-dispositions"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))
from book._python.plots import COLORS, apply_style, save_figure_bundle
from evidence_bundle import verify_sources, record_build


def read_csv(path):
    return list(
        csv.DictReader(
            line for line in path.read_text().splitlines() if not line.startswith("#")
        )
    )


def main():
    manifest = verify_sources(HERE, allow_missing_gitignored=True)
    verify_sources(SHARED, allow_missing_gitignored=True)
    errata = read_csv(SHARED / "derived/errata.csv")
    sources = read_csv(SHARED / "derived/sources.csv")
    launches = read_csv(HERE / "launch_years.csv")
    assert len(launches) == len({r["family"] for r in launches}) == 19
    launch_map = {r["family"]: r for r in launches}
    assert (
        set(launch_map)
        == {r["family"] for r in sources}
        == {r["family"] for r in errata}
    )
    counts = collections.Counter(r["family"] for r in errata)
    statuses = collections.Counter((r["family"], r["status"]) for r in errata)
    rows = []
    for source in sources:
        family = source["family"]
        launch = launch_map[family]
        assert counts[family] == int(source["extracted_count"])
        rows.append(
            {
                "family": family,
                "vendor": source["vendor"],
                "segment": source["segment"],
                "launch_year": int(launch["launch_year"]),
                "erratum_entries": counts[family],
                "no_fix": statuses[family, "No Fix"],
                "plan_fix": statuses[family, "Plan Fix"],
                "fixed": statuses[family, "Fixed"],
                "document_date": source["doc_date"],
                "document_revision": source["revision"],
                "document_number": source["doc_number"],
                "errata_source_url": source["url"],
                "errata_source_sha256": source["sha256"],
                "launch_source_url": launch["source_url"],
                "date_scope": launch["scope_note"],
            }
        )
    rows.sort(key=lambda r: (r["vendor"], r["segment"], r["launch_year"], r["family"]))
    with (HERE / "family_year_counts.csv").open("w") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    apply_style()
    fig, axes = plt.subplots(3, 1, figsize=(6.8, 5.9), sharex=True, sharey=True)
    groups = [
        ("Intel", "Client", "(a) Intel client-family documents"),
        ("Intel", "Server", "(b) Intel server-family documents"),
        ("AMD", "Server", "(c) AMD server-associated family guides"),
    ]
    offsets = {
        "Coffee Lake": (0, 10),
        "Ice Lake (client)": (0, 13),
        "Tiger Lake": (-5, -16),
        "Rocket Lake": (0, 10),
        "Alder Lake": (-4, 14),
        "Raptor Lake": (0, -17),
        "Meteor Lake": (-5, 33),
        "Lunar Lake": (-3, -13),
        "Arrow Lake": (-3, 17),
        "Broadwell-EP": (6, 10),
        "Skylake-SP": (0, 14),
        "Cascade Lake": (0, -17),
        "Ice Lake-SP": (0, 12),
        "Sapphire Rapids": (0, 12),
        "Emerald Rapids": (0, -18),
    }
    short = {
        "Ice Lake (client)": "Ice Lake",
        "Zen 1 (Naples)": "Naples",
        "Zen 2 (Rome)": "Rome",
        "Zen 4 (Genoa)": "Genoa",
        "Zen 5 (Turin)": "Turin",
    }
    for ax, (vendor, segment, title) in zip(axes, groups):
        subset = [r for r in rows if r["vendor"] == vendor and r["segment"] == segment]
        ax.scatter(
            [r["launch_year"] for r in subset],
            [r["erratum_entries"] for r in subset],
            s=24,
            color=COLORS["designspace"],
            edgecolor="white",
            linewidth=0.5,
            zorder=4,
        )
        for r in subset:
            offset = offsets.get(r["family"], (0, 12))
            ax.annotate(
                f'{short.get(r["family"],r["family"])} ({r["erratum_entries"]})',
                (r["launch_year"], r["erratum_entries"]),
                xytext=offset,
                textcoords="offset points",
                ha="center",
                va="center",
                fontsize=5.8,
                bbox=dict(boxstyle="round,pad=.12", fc="white", ec="none", alpha=0.95),
                arrowprops=dict(
                    arrowstyle="-", color=COLORS["muted"], lw=0.4, shrinkA=1, shrinkB=3
                ),
                zorder=5,
            )
        ax.set(
            title=title,
            xlim=(2015.4, 2024.7),
            ylim=(0, 230),
            yticks=[0, 50, 100, 150, 200],
        )
        ax.set_ylabel("Listed erratum entries")
        ax.grid(axis="y", color=COLORS["grid"], linewidth=0.5)
        ax.grid(axis="x", visible=False)
        ax.spines[["top", "right"]].set_visible(False)
    axes[-1].set_xticks(list(range(2016, 2025)))
    axes[-1].set_xlabel("Reference product-family introduction year")
    fig.suptitle(
        "Published errata by processor-family introduction year", fontsize=8.5, y=0.985
    )
    fig.text(
        0.5,
        0.95,
        "19 retained documents, revised 2020–2026 | Counts include fixed entries; removed entries are excluded",
        ha="center",
        fontsize=6,
        color=COLORS["muted"],
    )
    fig.subplots_adjust(left=0.105, right=0.97, top=0.88, bottom=0.08, hspace=0.40)
    save_figure_bundle(fig, HERE / "figure")
    plt.close(fig)
    summary = {
        "families": len(rows),
        "entries": sum(counts.values()),
        "launch_year_range": [
            min(r["launch_year"] for r in rows),
            max(r["launch_year"] for r in rows),
        ],
        "interpretation": "Cross-sectional counts in retained documents located by reference-family introduction year; not annual discoveries or a quality trend.",
    }
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    record_build(
        HERE,
        {
            "source_files_hash_verified": len(manifest["files"]),
            "shared_vendor_sources_hash_verified": True,
            "all_19_families_join_exactly_once": True,
            "counts_reconcile_with_source_metadata": True,
        },
        "Retained errata-count arithmetic, launch-date source mapping, and rendered figures. Document scope and observation windows differ; no inference about defect rates or vendor quality.",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
