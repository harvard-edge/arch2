#!/usr/bin/env python3
"""Plot explicit erratum additions in four retained document histories."""
import csv
import json
import importlib.metadata
from pathlib import Path
import subprocess
import sys
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))
from book._python.plots import COLORS, apply_style, save_figure_bundle
from evidence_bundle import verify_sources, record_build


def main():
    manifest = verify_sources(HERE)
    verify_sources(HERE.parent / "13-errata-dispositions")
    subprocess.run([sys.executable, str(HERE / "extract_history.py")], check=True)
    manifest = verify_sources(HERE)
    rows = list(csv.DictReader((HERE / "annual_counts.csv").open()))
    for r in rows:
        for k in (
            "year",
            "explicit_added_id_count",
            "distinct_explicit_added_id_count",
            "revision_rows",
        ):
            r[k] = int(r[k])
        assert r["explicit_added_id_count"] == r["distinct_explicit_added_id_count"]
    families = ["Broadwell-EP", "Ice Lake-SP", "Zen 1 (Naples)", "Zen 5 (Turin)"]
    expected = {
        "Broadwell-EP": 46,
        "Ice Lake-SP": 104,
        "Zen 1 (Naples)": 30,
        "Zen 5 (Turin)": 21,
    }
    assert {
        f: sum(r["explicit_added_id_count"] for r in rows if r["family"] == f)
        for f in families
    } == expected
    titles = [
        "(a) Broadwell-EP | retained document: April 2022",
        "(b) Ice Lake-SP | retained document: March 2026",
        "(c) AMD Family 17h 00h–0Fh (Naples-associated) | retained document: August 2023",
        "(d) AMD Family 1Ah 00h–0Fh (Turin-associated) | retained document: July 2025",
    ]
    apply_style()
    fig, axes = plt.subplots(4, 1, figsize=(6.8, 5.8), sharex=True, sharey=True)
    for ax, family, title in zip(axes, families, titles):
        subset = [r for r in rows if r["family"] == family]
        first = min(r["year"] for r in subset)
        last = max(r["year"] for r in subset)
        if first > 2015:
            ax.axvspan(2014.5, first - 0.5, color=COLORS["row"], alpha=0.65, zorder=0)
        if last < 2026:
            ax.axvspan(last + 0.5, 2026.5, color=COLORS["row"], alpha=0.65, zorder=0)
        years = [r["year"] for r in subset]
        counts = [r["explicit_added_id_count"] for r in subset]
        ax.bar(years, counts, width=0.62, color=COLORS["evidence"], zorder=3)
        for year, n in zip(years, counts):
            if n:
                ax.text(year, n + 2, str(n), ha="center", va="bottom", fontsize=6)
        ax.set(
            title=title,
            xlim=(2014.5, 2026.5),
            ylim=(0, 58),
            yticks=[0, 20, 40],
            ylabel="Added entries",
        )
        ax.grid(axis="y", color=COLORS["grid"], lw=0.5)
        ax.grid(axis="x", visible=False)
        ax.spines[["top", "right"]].set_visible(False)
    axes[-1].set_xticks(list(range(2015, 2027)))
    axes[-1].set_xlabel("Document revision year (initial-release counts excluded)")
    fig.legend(
        handles=[
            Patch(facecolor=COLORS["evidence"], label="Identifiers explicitly added"),
            Patch(
                facecolor=COLORS["row"],
                alpha=0.65,
                label="Outside the listed history years",
            ),
        ],
        loc="upper center",
        bbox_to_anchor=(0.54, 0.985),
        ncol=2,
        frameon=False,
    )
    fig.subplots_adjust(left=0.105, right=0.98, top=0.90, bottom=0.085, hspace=0.55)
    save_figure_bundle(fig, HERE / "figure")
    save_figure_bundle(
        fig,
        ROOT
        / "book/contents/chapters/11-ownership/images/fig-ch11-errata-revision-history",
    )
    plt.close(fig)
    (HERE / "summary.json").write_text(
        json.dumps(
            {
                "explicit_additions_by_family": expected,
                "revision_rows": len(
                    list(csv.DictReader((HERE / "revision_rows.csv").open()))
                ),
                "meaning": "Explicit Added identifiers in the retained tables, not discovery dates, annual industry totals, or complete cumulative inventories.",
            },
            indent=2,
        )
        + "\n"
    )
    record_build(
        HERE,
        {
            "source_files_hash_verified": len(manifest["files"]),
            "explicit_additions_checked_against_each_source_history": True,
            "initial_counts_excluded": True,
            "outside_history_years_shaded": True,
        },
        "Four selected revision histories and their explicit identifier additions. Initial inventories are unknown; source gaps and Broadwell BDF92 removal omission prevent full historical reconstruction.",
    )
    receipt = json.loads((HERE / "build_receipt.json").read_text())
    receipt["packages"]["pymupdf"] = importlib.metadata.version("pymupdf")
    (HERE / "build_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
