#!/usr/bin/env python3
"""Extract matched MLPerf run logs and plot the effect of the latency contract."""
import csv
import json
from pathlib import Path
import re
import sys
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))
from book._python.plots import COLORS, FONT_SIZES, apply_style, save_figure_bundle
from evidence_bundle import verify_sources, record_build
from collect import select_pairs


def number(text, key):
    matches = re.findall(r"^" + re.escape(key) + r"\s*:\s*([\d.]+)", text, re.M)
    assert matches and len(set(matches)) == 1, (key, matches)
    return float(matches[0])


def main():
    manifest = verify_sources(HERE, allow_missing_gitignored=True)
    raw_summary = HERE / "raw/summary_results.json"
    if raw_summary.exists():
        pairs, unpaired = select_pairs(json.loads(raw_summary.read_text()))
        assert pairs == json.loads((HERE / "selected_pairs.json").read_text())
        assert unpaired == manifest["unpaired_systems"]
    else:
        pairs = json.loads((HERE / "selected_pairs.json").read_text())
    rows = []
    for pair in pairs:
        data = {}
        for condition, model in [
            ("standard", "llama2-70b-99"),
            ("interactive", "llama2-70b-interactive-99"),
        ]:
            r = pair[model]
            source = (
                "raw/" + r["Location"] + "/performance/run_1/mlperf_log_summary.txt"
            )
            text = (HERE / source).read_text()
            assert re.search(r"Result is\s*:\s*VALID\s*$", text, re.M)
            assert "Performance constraints satisfied : Yes" in text
            throughput = number(text, "Completed tokens per second")
            assert abs(throughput - r["Performance_Result"]) <= max(
                0.006, throughput * 5e-6
            ), (source, throughput, r["Performance_Result"])
            data[condition + "_tokens_per_s"] = throughput
            data[condition + "_ttft_ms"] = number(text, "ttft_latency (ns)") / 1e6
            data[condition + "_tpot_ms"] = number(text, "tpot_latency (ns)") / 1e6
            data[condition + "_source"] = source
            data[condition + "_published_tokens_per_s"] = r["Performance_Result"]
        standard = pair["llama2-70b-99"]
        accelerator = standard["Accelerator"]
        family = next(
            x
            for x in ("H100-SXM", "H200-NVL", "H200-SXM", "B200-SXM")
            if x in accelerator
        )
        system = json.loads(
            (
                HERE
                / f"raw/closed/{standard['Submitter']}/systems/{standard['Platform']}.json"
            ).read_text()
        )
        assert int(system["accelerators_per_node"]) == 8
        data.update(
            {
                "submitter": standard["Submitter"],
                "platform": standard["Platform"],
                "system_id": standard["ID"],
                "accelerator": accelerator,
                "family": family,
                "precision": standard["weight_data_types"],
                "software": standard["Software"],
                "interactive_fraction": data["interactive_tokens_per_s"]
                / data["standard_tokens_per_s"],
            }
        )
        assert (
            data["standard_ttft_ms"],
            data["standard_tpot_ms"],
            data["interactive_ttft_ms"],
            data["interactive_tpot_ms"],
        ) == (2000, 200, 450, 40)
        rows.append(data)
    assert len(rows) == 19
    with (HERE / "paired_throughput.csv").open("w") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    ratios = [r["interactive_fraction"] for r in rows]
    summary = {
        "pairs": len(rows),
        "raw_logs": 2 * len(rows),
        "minimum_interactive_fraction": min(ratios),
        "median_interactive_fraction": float(np.median(ratios)),
        "maximum_interactive_fraction": max(ratios),
        "latency_contract_ms": {k: rows[0][k] for k in rows[0] if k.endswith("_ms")},
    }
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    apply_style()
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(6.8, 2.65),
        gridspec_kw={"width_ratios": [1, 1.7], "wspace": 0.65},
    )
    ax = axes[0]
    for i, field in enumerate(("ttft", "tpot")):
        values = [rows[0][f"{c}_{field}_ms"] for c in ("standard", "interactive")]
        ax.barh(
            i - 0.15,
            values[0],
            height=0.26,
            color=COLORS["workload"],
            label="Standard" if i == 0 else None,
        )
        ax.barh(
            i + 0.15,
            values[1],
            height=0.26,
            color=COLORS["constraints"],
            hatch="///",
            label="Interactive" if i == 0 else None,
        )
        for y, v in zip((i - 0.15, i + 0.15), values):
            ax.text(v + 30, y, f"{v:g}", va="center", fontsize=5.8)
    ax.set(
        yticks=[0, 1],
        yticklabels=["First token", "Per output\ntoken"],
        xlim=(0, 2450),
        ylim=(1.6, -0.6),
        xlabel="Latency target (ms)",
        title="(a) A stricter latency requirement",
    )
    ax.set_xticks([0, 1000, 2000])
    ax.legend(loc="lower center", bbox_to_anchor=(0.4, -0.46), ncol=2, frameon=False)
    ax = axes[1]
    labels = []
    for i, family in enumerate(("H100-SXM", "H200-NVL", "H200-SXM", "B200-SXM")):
        values = sorted(
            r["interactive_fraction"] for r in rows if r["family"] == family
        )
        offsets = np.linspace(-0.22, 0.22, len(values)) if len(values) > 1 else [0]
        ax.scatter(
            values,
            i + np.array(offsets),
            s=16,
            color=COLORS["workload"],
            edgecolor="white",
            linewidth=0.4,
            label="Paired submission" if i == 0 else None,
            zorder=3,
        )
        ax.scatter(
            [np.median(values)],
            [i],
            marker="|",
            s=110,
            color=COLORS["ink"],
            linewidth=1.2,
            zorder=4,
            label="Group median" if i == 0 else None,
        )
        labels.append(f"{family.replace('-', ' ')} (n={len(values)})")
    ax.axvline(1, color=COLORS["muted"], lw=0.8, ls="--")
    ax.set(
        xlim=(0, 1.08),
        ylim=(3.6, -0.6),
        yticks=range(4),
        yticklabels=labels,
        xlabel="Interactive / standard throughput",
        title="(b) Throughput under that requirement",
    )
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1])
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.46), ncol=2, frameon=False)
    for ax in axes:
        ax.grid(axis="x", color=COLORS["grid"], lw=0.5)
        ax.grid(axis="y", visible=False)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
    fig.subplots_adjust(left=0.095, right=0.99, top=0.86, bottom=0.29)
    save_figure_bundle(fig, HERE / "figure")
    save_figure_bundle(
        fig,
        ROOT
        / "book/contents/chapters/09-patterns/images/fig-ch09-mlperf-latency-contract",
    )
    plt.close(fig)
    record_build(
        HERE,
        {
            "source_files_hash_verified": len(manifest["files"]),
            "run_logs_valid": 38,
            "published_summary_agrees_with_logs_to_published_precision": True,
            "matching_latency_contracts": True,
            "systems_with_eight_accelerators": 19,
        },
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
