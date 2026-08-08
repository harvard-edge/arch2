import csv
import sys
from pathlib import Path
import matplotlib.pyplot as plt

# Connect parent repo path to import book._python.plots
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style

apply_style()


def categorize_precision(p):
    p_str = str(p).lower().strip()
    if "fp32" in p_str or "tf32" in p_str:
        return "FP32"
    if "fp16" in p_str or "bf16" in p_str:
        return "FP16/BF16"
    if "int8" in p_str:
        return "INT8"
    if "int4" in p_str or "int2" in p_str or "int1" in p_str or "binary" in p_str:
        return "INT4/Sub-byte"
    return "Other"


def categorize_org(company):
    c_str = str(company).lower()
    if any(
        keyword in c_str for keyword in ["univ", "institute", "mit", "research", "lab"]
    ):
        return "Academic"
    return "Commercial"


def main():
    raw_csv = (
        REPO_ROOT / "data" / "source-receipts" / "sources" / "reuther-laics-2025.csv"
    )
    out_csv = (
        REPO_ROOT
        / "data"
        / "source-receipts"
        / "chapter1-reuther-precision-frontier.csv"
    )
    out_plot = REPO_ROOT / "book" / "images" / "fig-reuther-precision-frontier.svg"

    data_by_prec = {
        "FP32": [],
        "FP16/BF16": [],
        "INT8": [],
        "INT4/Sub-byte": [],
        "Other": [],
    }

    receipt_rows = []

    with open(raw_csv, "r", encoding="utf-8-sig", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                company = row["Company"].strip()
                product = row["Product"].strip()
                perf_raw = float(row["PeakPerformance"])
                power_raw = float(row["Power"])

                if power_raw <= 0 or perf_raw <= 0:
                    continue

                peak_perf = perf_raw / 1e12  # TOPS
                efficiency = peak_perf / power_raw  # TOPS/W
                prec = categorize_precision(row["Precision"])
                tech = row.get("Technology", "")
                org = categorize_org(company)

                receipt_rows.append(
                    [
                        company,
                        product,
                        round(peak_perf, 2),
                        round(power_raw, 2),
                        round(efficiency, 3),
                        prec,
                        tech,
                        org,
                    ]
                )
                data_by_prec[prec].append((peak_perf, efficiency))
            except (ValueError, KeyError, TypeError):
                continue

    # Write CSV receipt
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Company",
                "Product",
                "Peak TOPS",
                "Power (W)",
                "Energy Efficiency (TOPS/W)",
                "Precision mode",
                "Process Node",
                "Organization Type",
            ]
        )
        writer.writerows(receipt_rows)

    print(f"Receipt written to '{out_csv}' ({len(receipt_rows)} chips processed)")

    # Render Plot
    fig, ax = plt.subplots(figsize=(6.4, 3.8))

    color_map = {
        "FP32": COLORS["blue"],
        "FP16/BF16": COLORS["orange"],
        "INT8": COLORS["green"],
        "INT4/Sub-byte": COLORS["purple"],
        "Other": COLORS["muted"],
    }

    for prec in ["FP32", "FP16/BF16", "INT8", "INT4/Sub-byte", "Other"]:
        pts = data_by_prec[prec]
        if not pts:
            continue
        x = [p[0] for p in pts]
        y = [p[1] for p in pts]
        ax.scatter(
            x,
            y,
            s=18,
            color=color_map.get(prec, COLORS["muted"]),
            label=prec,
            alpha=0.75,
            edgecolors="none",
            zorder=3,
        )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Peak Compute (TOPS, log scale)", fontsize=7, color=COLORS["ink"])
    ax.set_ylabel(
        "Energy Efficiency (TOPS/W, log scale)", fontsize=7, color=COLORS["ink"]
    )
    ax.set_title(
        "AI Accelerator Survey: Precision Frontier vs Memory Wall Ceiling",
        fontsize=8,
        fontweight="bold",
        color=COLORS["ink"],
    )

    # Memory wall ceiling line
    ax.axhline(
        y=100, color=COLORS["red"], linestyle="--", linewidth=1.0, alpha=0.7, zorder=4
    )
    ax.text(
        0.01,
        120,
        "Memory Wall Physical Efficiency Ceiling (~100 TOPS/W)",
        fontsize=6.2,
        fontweight="bold",
        color=COLORS["red"],
    )

    ax.tick_params(axis="both", labelsize=6.0, length=2.5, width=0.6)
    ax.grid(True, which="both", color=COLORS["grid"], linewidth=0.5, zorder=0)

    ax.legend(
        title="Precision Mode",
        fontsize=5.8,
        title_fontsize=6.2,
        loc="lower left",
        framealpha=0.9,
        facecolor="white",
        edgecolor=COLORS["grid"],
    )

    plt.tight_layout()
    plt.savefig(out_plot, dpi=300, bbox_inches="tight")
    print(f"Reuther precision frontier plot saved to '{out_plot}'")


if __name__ == "__main__":
    main()
