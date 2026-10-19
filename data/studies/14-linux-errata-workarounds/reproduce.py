#!/usr/bin/env python3
"""Count explicitly prompted erratum configuration options in pinned Kconfig files."""
import csv
import datetime
import json
from pathlib import Path
import re
import sys
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))
from book._python.plots import COLORS, apply_style, save_figure_bundle
from evidence_bundle import verify_sources, record_build


def write_csv(name, rows):
    with (HERE / name).open("w") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def extract(text):
    blocks = list(
        re.finditer(
            r"^config (\w+)\n(.*?)(?=^(?:config |menuconfig |endmenu|menu |choice|endchoice)|\Z)",
            text,
            re.M | re.S,
        )
    )
    assert len(blocks) == len(re.findall(r"^config ", text, re.M))
    result = []
    for b in blocks:
        name, body = b.groups()
        if not re.search(r"(?:^|_)ERRAT(?:UM|A)(?:_|$)", name):
            continue
        prompt = re.search(r'^\s*bool\s+"([^"]+)"', body, re.M)
        result.append(
            {
                "symbol": name,
                "source_line": text.count("\n", 0, b.start()) + 1,
                "included": bool(prompt),
                "prompt": prompt.group(1) if prompt else "",
                "reason": "Named erratum option with a bool prompt"
                if prompt
                else "No bool prompt; tool capability helper",
            }
        )
    assert len({r["symbol"] for r in result}) == len(result)
    return result


def main():
    manifest = verify_sources(HERE)
    pins = json.loads((HERE / "pins.json").read_text())
    entries, series, original, previous = [], [], None, set()
    for pin in pins:
        path = f"raw/{pin['tag']}/arch/arm64/Kconfig"
        found = extract((HERE / path).read_text())
        names = {r["symbol"] for r in found if r["included"]}
        if original is None:
            original = names
        series.append(
            {
                "tag": pin["tag"],
                "date": pin["date"][:10],
                "commit": pin["commit"],
                "options": len(names),
                "present_in_v4_4": len(names & original),
                "other_options": len(names - original),
                "added_since_previous_snapshot": ";".join(sorted(names - previous))
                if previous
                else "",
                "absent_since_previous_snapshot": ";".join(sorted(previous - names)),
            }
        )
        entries.extend(
            {**pin, **r, "path": path, "present_in_v4_4": r["symbol"] in original}
            for r in found
        )
        previous = names
    assert (
        len(series) == 10 and series[0]["options"] == 10 and series[-1]["options"] == 52
    )
    write_csv("options.csv", entries)
    write_csv("release_counts.csv", series)
    # Keep the documentation as a separate source, including discrepancies.
    registry = []
    docpath = "raw/v6.12/Documentation/arch/arm64/silicon-errata.rst"
    for lineno, line in enumerate((HERE / docpath).read_text().splitlines(), 1):
        if not line.startswith("|"):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) != 4 or cols[0] == "Implementor":
            continue
        if not cols[0]:
            assert registry
            for key, value in zip(
                ("implementor", "component", "erratum_ids", "config"), cols
            ):
                registry[-1][key] += value
        else:
            registry.append(
                dict(
                    zip(("implementor", "component", "erratum_ids", "config"), cols),
                    source_line=lineno,
                )
            )
    assert len(registry) == 115 and all(r["config"] for r in registry)
    write_csv("registry.csv", registry)
    registry_names = {r["config"] for r in registry if r["config"] != "N/A"}
    summary = {
        "release_snapshots": len(series),
        "first": series[0],
        "last": series[-1],
        "original_options_present_in_every_sampled_release": all(
            s["present_in_v4_4"] == 10 for s in series
        ),
        "years_between_endpoints": (
            datetime.date.fromisoformat(series[-1]["date"])
            - datetime.date.fromisoformat(series[0]["date"])
        ).days
        / 365.2425,
        "registry_only_names": sorted(registry_names - previous),
        "counted_Kconfig_names_absent_from_registry": sorted(previous - registry_names),
    }
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    apply_style()
    fig, ax = plt.subplots(figsize=(6.8, 2.8))
    x = range(len(series))
    ax.bar(
        x,
        [s["present_in_v4_4"] for s in series],
        color=COLORS["evidence"],
        label="Options already present in v4.4",
        width=0.65,
    )
    ax.bar(
        x,
        [s["other_options"] for s in series],
        bottom=[s["present_in_v4_4"] for s in series],
        color=COLORS["designspace"],
        label="Other options present in that release",
        width=0.65,
    )
    for i, s in enumerate(series):
        ax.text(i, s["options"] + 1.2, str(s["options"]), ha="center", fontsize=6)
    ax.set(
        xticks=list(x),
        xticklabels=[s["tag"] + "\n" + s["date"][:4] for s in series],
        ylim=(0, 60),
        yticks=[0, 10, 20, 30, 40, 50, 60],
        ylabel="Selectable erratum workaround options",
        xlabel="Selected Linux releases (equally spaced snapshots)",
    )
    ax.grid(axis="y", color=COLORS["grid"], lw=0.5)
    ax.grid(axis="x", visible=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper left", frameon=False)
    fig.subplots_adjust(left=0.11, right=0.985, top=0.93, bottom=0.20)
    save_figure_bundle(fig, HERE / "figure")
    save_figure_bundle(
        fig,
        ROOT
        / "book/contents/chapters/09-patterns/images/fig-ch09-linux-arm64-errata-workarounds",
    )
    plt.close(fig)
    record_build(
        HERE,
        {
            "source_files_hash_verified": len(manifest["files"]),
            "release_snapshots": 10,
            "all_config_blocks_parsed": True,
            "excluded_helpers_retained": True,
            "registry_disagreements_retained_separately": True,
        },
        "Static extraction from pinned Linux source and arithmetic; no kernel build, hardware execution, performance measurement, or independent semantic audit.",
    )
    print({k: v for k, v in summary.items() if k not in ("first", "last")})


if __name__ == "__main__":
    main()
