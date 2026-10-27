#!/usr/bin/env python3
"""Measure recurring text, without assuming identical hardware root causes."""
import collections
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))
from book._python.plots import COLORS, apply_style, save_figure_bundle
from evidence_bundle import verify_sources, record_build


def key(title):
    return " ".join(unicodedata.normalize("NFKC", title).casefold().split())


def group(rows, normalize):
    groups = collections.defaultdict(list)
    for r in rows:
        groups[normalize(r["title"])].append(r)
    return groups


def main():
    manifest = verify_sources(HERE, allow_missing_gitignored=True)
    shared = HERE.parent / "13-errata-dispositions"
    verify_sources(shared, allow_missing_gitignored=True)
    assert (HERE / "raw/source_manifest.json").read_bytes() == (
        shared / "source_manifest.json"
    ).read_bytes()
    assert (HERE / "raw/errata.csv").read_bytes() == (
        shared / "derived/errata.csv"
    ).read_bytes()
    rows = list(csv.DictReader((HERE / "raw/errata.csv").open()))
    groups = group(rows, key)
    summary = {
        "entries": len(rows),
        "families": len({r["family"] for r in rows}),
        "distinct_normalized_titles": len(groups),
        "normalization": "Unicode NFKC, case folding, whitespace collapsing; punctuation and numbers retained",
        "groups_appearing_in_multiple_families": sum(
            len({r["family"] for r in g}) > 1 for g in groups.values()
        ),
        "entries_with_title_shared_across_families": sum(
            len(g) for g in groups.values() if len({r["family"] for r in g}) > 1
        ),
    }
    summary["shared_entry_fraction"] = summary[
        "entries_with_title_shared_across_families"
    ] / len(rows)
    summary["normalization_sensitivity"] = {}
    for label, normalize in [
        ("literal", lambda t: t),
        ("case_space", key),
        ("alphanumeric_only", lambda t: re.sub("[^a-z0-9]", "", t.lower())),
    ]:
        g = group(rows, normalize)
        summary["normalization_sensitivity"][label] = {
            "distinct_titles": len(g),
            "entries_with_title_shared_across_families": sum(
                len(v) for v in g.values() if len({r["family"] for r in v}) > 1
            ),
        }
    with (HERE / "title_groups.csv").open("w") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "group_sha256",
                "normalized_title",
                "entries",
                "families",
                "family_names",
                "entry_ids",
            ],
        )
        w.writeheader()
        for k, g in sorted(groups.items()):
            w.writerow(
                {
                    "group_sha256": hashlib.sha256(k.encode()).hexdigest(),
                    "normalized_title": k,
                    "entries": len(g),
                    "families": len({r["family"] for r in g}),
                    "family_names": ";".join(sorted({r["family"] for r in g})),
                    "entry_ids": ";".join(
                        r["family"] + ":" + r["erratum_id"] for r in g
                    ),
                }
            )
    counts = collections.Counter(len({r["family"] for r in g}) for g in groups.values())
    assert sum(counts.values()) == len(groups)
    with (HERE / "title_multiplicity.csv").open("w") as f:
        w = csv.writer(f)
        w.writerow(["processor_families", "distinct_titles"])
        w.writerows(sorted(counts.items()))
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    apply_style()
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(6.8, 2.8),
        gridspec_kw={"width_ratios": [1, 1.45], "wspace": 0.47},
    )
    ax = axes[0]
    shared_entries = summary["entries_with_title_shared_across_families"]
    values = [len(rows) - shared_entries, shared_entries]
    ax.bar([0, 1], values, color=[COLORS["muted"], COLORS["designspace"]], width=0.6)
    for i, v in enumerate(values):
        ax.text(i, v + 30, f"{v:,}", ha="center", fontsize=6)
    ax.set(
        xticks=[0, 1],
        xticklabels=[
            "Title confined to\none family",
            "Title shared across\nmultiple families",
        ],
        ylabel="Published erratum entries",
        ylim=(0, 1250),
        title="(a) Repeated wording in the corpus",
    )
    ax = axes[1]
    xs = list(range(1, max(counts) + 1))
    values = [counts[n] for n in xs]
    ax.bar(
        xs,
        values,
        width=0.7,
        color=[COLORS["muted"]] + [COLORS["designspace"]] * (len(xs) - 1),
    )
    for n, v in zip(xs, values):
        ax.text(n, v * 1.12, str(v), ha="center", fontsize=5.8)
    ax.set(
        xticks=xs,
        xlabel="Processor families sharing a normalized title",
        ylabel="Distinct titles (log scale)",
        yscale="log",
        ylim=(0.7, 1400),
        yticks=[1, 10, 100, 1000],
        title="(b) Most recurrence spans a few families",
    )
    ax.set_yticklabels(["1", "10", "100", "1,000"])
    ax.minorticks_off()
    for ax in axes:
        ax.grid(axis="y", color=COLORS["grid"], lw=0.5)
        ax.grid(axis="x", visible=False)
        ax.spines[["top", "right"]].set_visible(False)
    fig.text(
        0.1,
        0.015,
        "Case and whitespace normalized; punctuation retained. Matching titles do not establish a shared root cause.",
        fontsize=5.8,
        color=COLORS["muted"],
    )
    fig.subplots_adjust(left=0.1, right=0.985, top=0.86, bottom=0.24)
    save_figure_bundle(fig, HERE / "figure")
    plt.close(fig)
    record_build(
        HERE,
        {
            "source_files_hash_verified": len(manifest["files"]),
            "shared_vendor_package_hash_verified": True,
            "normalization_sensitivity_computed": True,
            "title_groups_partition_all_entries": True,
        },
        "Text recurrence and arithmetic on verified extracted titles. Matching titles do not establish identical defects, root causes, independent samples, or model training contamination.",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
