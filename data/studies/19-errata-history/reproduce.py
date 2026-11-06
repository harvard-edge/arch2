#!/usr/bin/env python3
"""Plot explicit erratum additions in four retained document histories."""
from collections import Counter
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
from book._python.plots import COLORS, FONT_SIZES, apply_style, save_figure_bundle
from evidence_bundle import verify_sources, record_build


def main():
    manifest = verify_sources(HERE, allow_missing_gitignored=True)
    pdf_dir = HERE.parent / "13-errata-dispositions/raw/pdf"
    extraction_ran = pdf_dir.exists() and any(pdf_dir.glob("*.pdf"))
    if extraction_ran:
        verify_sources(
            HERE.parent / "13-errata-dispositions", allow_missing_gitignored=True
        )
        (HERE / "source_visual_qa").mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, str(HERE / "extract_history.py")], check=True)
        manifest = verify_sources(HERE, allow_missing_gitignored=True)
    else:
        print(
            "Source PDFs absent: extraction skipped, committed CSVs plotted as is. "
            "build_receipt.json records this run as unchecked against the sources."
        )
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
    additions_by_family = {
        f: sum(r["explicit_added_id_count"] for r in rows if r["family"] == f)
        for f in families
    }
    # Annual counts must equal the per-identifier records in every family and
    # year, so an edit that preserves a family's total still halts the build.
    events = list(csv.DictReader((HERE / "identifier_events.csv").open()))
    event_counts = Counter(
        (e["family"], int(e["year"])) for e in events if e["event_type"] == "added"
    )
    annual_counts = Counter(
        {
            (r["family"], r["year"]): r["explicit_added_id_count"]
            for r in rows
            if r["explicit_added_id_count"]
        }
    )
    assert event_counts == annual_counts
    revision_rows = list(csv.DictReader((HERE / "revision_rows.csv").open()))
    initial_rows = [r for r in revision_rows if r["initial_release_row"] == "True"]
    initial_counts_excluded = all(
        not json.loads(r["explicit_added_ids"]) for r in initial_rows
    )
    shaded_years = {}
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
        shaded_years[family] = set()
        if first > 2015:
            shaded_years[family] |= set(range(2015, first))
            ax.axvspan(2014.5, first - 0.5, color=COLORS["row"], alpha=0.65, zorder=0)
        if last < 2026:
            shaded_years[family] |= set(range(last + 1, 2027))
            ax.axvspan(last + 0.5, 2026.5, color=COLORS["row"], alpha=0.65, zorder=0)
        years = [r["year"] for r in subset]
        counts = [r["explicit_added_id_count"] for r in subset]
        ax.bar(years, counts, width=0.62, color=COLORS["evidence"], zorder=3)
        for year, n in zip(years, counts):
            if n:
                ax.text(
                    year,
                    n + 2,
                    str(n),
                    ha="center",
                    va="bottom",
                    fontsize=FONT_SIZES["annotation"],
                )
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
                "explicit_additions_by_family": additions_by_family,
                "revision_rows": len(revision_rows),
                "meaning": "Explicit Added identifiers in the retained tables, not discovery dates, annual industry totals, or complete cumulative inventories.",
            },
            indent=2,
        )
        + "\n"
    )
    record_build(
        HERE,
        {
            "source_files_declared": len(manifest["files"]),
            "source_files_hash_verified": manifest["verified_count"],
            "source_extraction_ran": extraction_ran,
            "annual_counts_match_identifier_events": event_counts == annual_counts,
            "initial_counts_excluded": initial_counts_excluded,
            "outside_history_years_shaded": all(
                shaded_years[f]
                == set(range(2015, 2027))
                - set(
                    range(
                        min(int(r["year"]) for r in revision_rows if r["family"] == f),
                        max(int(r["year"]) for r in revision_rows if r["family"] == f)
                        + 1,
                    )
                )
                for f in families
            ),
        },
        "Four selected revision histories and their explicit identifier additions. Initial inventories are unknown; source gaps and Broadwell BDF92 removal omission prevent full historical reconstruction.",
    )
    if extraction_ran:
        receipt = json.loads((HERE / "build_receipt.json").read_text())
        receipt["packages"]["pymupdf"] = importlib.metadata.version("pymupdf")
        (HERE / "build_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
