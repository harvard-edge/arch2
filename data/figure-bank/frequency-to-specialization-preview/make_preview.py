from pathlib import Path
import sys, csv, json
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter, NullLocator

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "book"))
from _python.plots import apply_style, COLORS

apply_style()
# Frozen CPU points from the Chapter 2 figure at commit 2d0dca23.
snapshot = OUT / "cpu-series.py"
exec(snapshot.read_text())
rows = list(csv.DictReader((OUT / "accelerators.csv").open()))
years = [int(r["year"]) for r in rows]
trans = [float(r["transistors_billion"]) * 1e6 for r in rows]
perf = [float(r["dense_fp16_tflops"]) for r in rows]
fig = plt.figure(figsize=(7.2, 5.9))
ax = fig.add_axes([0.085, 0.50, 0.685, 0.405])
bx = fig.add_axes([0.085, 0.10, 0.685, 0.275])
ax.set_title(
    "(a) Frequency scaling stalls; silicon budgets keep growing",
    loc="left",
    fontsize=8.4,
    pad=26,
    fontweight="bold",
)
ax.set_yscale("log")
ax.set_xlim(1970, 2026)
ax.set_ylim(0.4, 1e10)
ax.axvspan(
    2016,
    2026,
    color=COLORS["designspace_tint"] if "designspace_tint" in COLORS else "#F0ECFA",
    alpha=0.45,
    zorder=0,
)
for x in [2005, 2016]:
    ax.axvline(x, color=COLORS["muted"], lw=0.65, ls=(0, (4, 3)), zorder=1)
for x, lab in [
    (1987, "Device scaling"),
    (2010.4, "Parallelism"),
    (2021, "Specialization"),
]:
    ax.text(
        x, 2.4e9, lab, ha="center", fontsize=6.7, color=COLORS["ink"], fontweight="bold"
    )
for s in series:
    x, y = zip(*s["points"])
    ax.plot(x, y, color=s["color"], lw=1.5, marker="o", ms=2.7)
    lab = (
        s["label"]
        .replace("Transistors\n(thousands)", "CPU transistors\n(thousands)")
        .replace("Single-thread perf", "CPU single-thread")
        .replace("CPU power: 4-year max (W)", "CPU power (W)")
    )
    ax.text(
        1.025,
        s["label_y"],
        lab,
        transform=ax.get_yaxis_transform(),
        va="center",
        fontsize=6.4,
        color=s["color"],
        fontweight="bold",
        linespacing=1.2,
    )
ax.plot(
    years,
    trans,
    color=COLORS["purple"],
    ls=":",
    lw=1.7,
    marker="D",
    ms=3.4,
    mfc="white",
    mew=1.1,
    zorder=5,
)
ax.annotate(
    "GPU transistors\n(thousands)",
    xy=(2025, trans[-1]),
    xytext=(1.025, 6e8),
    textcoords=ax.get_yaxis_transform(),
    color=COLORS["purple"],
    fontsize=6.4,
    fontweight="bold",
    va="center",
    arrowprops=dict(arrowstyle="-", color=COLORS["purple"], lw=0.6),
)
ax.annotate(
    "Blackwell: 208 billion\nacross two logic dies",
    xy=(2024, 2.08e8),
    xytext=(1990, 2.8e8),
    ha="center",
    fontsize=6.1,
    color=COLORS["purple"],
    bbox=dict(facecolor="white", edgecolor="none", pad=2),
    arrowprops=dict(arrowstyle="-", color=COLORS["purple"], lw=0.7),
)
ax.set_xticks([1970, 1980, 1990, 2000, 2010, 2020, 2025])
ax.set_yticks([1, 1e2, 1e4, 1e6, 1e8])
ax.set_ylabel("Log scale; units identified at right", fontsize=6.8)
ax.text(
    0,
    1.035,
    "Solid circles: CPU interval maxima, 1971–2021     Open diamonds: selected NVIDIA GPUs",
    transform=ax.transAxes,
    fontsize=6.2,
    color=COLORS["muted"],
)
bx.set_title(
    "(b) Specialized matrix throughput, at fixed precision",
    loc="left",
    fontsize=8.4,
    pad=22,
    fontweight="bold",
)
bx.set_yscale("log")
bx.set_xlim(2016.4, 2025.6)
bx.set_ylim(80, 4200)
bx.plot(
    years,
    perf,
    color=COLORS["blue"],
    ls=":",
    lw=1.8,
    marker="D",
    ms=4,
    mfc="white",
    mew=1.1,
)
for x, y in zip(years, perf):
    bx.annotate(
        f"{y:,.0f}" if y != 989.5 else "≈990",
        (x, y),
        xytext=(0, 8),
        textcoords="offset points",
        ha="center",
        fontsize=7,
        color=COLORS["blue"],
        fontweight="bold",
    )
bx.set_xticks(years, [f"{r['model']}\n{r['year']}" for r in rows])
bx.set_yticks([100, 300, 1000, 3000])
bx.yaxis.set_major_formatter(ScalarFormatter())
bx.yaxis.set_minor_locator(NullLocator())
bx.set_ylabel("Dense FP16 Tensor TFLOP/s\nper GPU (log scale)", fontsize=6.8)
bx.text(
    0,
    1.035,
    "Published peak specifications • SXM variants • no sparsity multiplier",
    transform=bx.transAxes,
    fontsize=6.2,
    color=COLORS["muted"],
)
bx.text(
    1.025,
    2250,
    "B200 / B300\n2,250 TFLOP/s",
    transform=bx.get_yaxis_transform(),
    fontsize=6.4,
    color=COLORS["blue"],
    fontweight="bold",
    va="center",
)
bx.text(
    1.025,
    500,
    "Separate metric:\nnot CPU SPEC\nor measured\napplication speed",
    transform=bx.get_yaxis_transform(),
    fontsize=6.3,
    color=COLORS["muted"],
    va="center",
    linespacing=1.3,
)
for a in (ax, bx):
    a.grid(axis="y", color=COLORS["grid"], lw=0.5)
    a.tick_params(labelsize=6.5, length=2.5, pad=3)
    for side in ["top", "right"]:
        a.spines[side].set_visible(False)
fig.text(
    0.085,
    0.015,
    "Sources: Karl Rupp microprocessor dataset (CC BY 4.0); NVIDIA architecture papers and product specifications.\nSelected GPU generations, not a market frontier. Years identify product introduction; specifications accessed September 11, 2026.",
    fontsize=5.9,
    color=COLORS["muted"],
)
for suffix in ["svg", "pdf", "png"]:
    path = OUT / f"frequency-to-specialization-preview.{suffix}"
    fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=0.12)
    print(path)
