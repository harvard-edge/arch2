import matplotlib.pyplot as plt
import csv
from pathlib import Path
import os
import networkx as nx

REPO_ROOT = Path(__file__).resolve().parents[2]
src_dir = REPO_ROOT / "data" / "datasets"
plt.style.use(str(src_dir / "book.mplstyle"))

# Each figure is written to the chapter that includes it. This script previously
# wrote all twelve into an agent CLI scratch directory, so running it appeared to
# succeed while the assets the book ships were never updated.
CHAPTER_DIR = {
    1: "01-moonshot",
    2: "02-pressures",
    3: "03-lifecycle",
    4: "04-representations",
    5: "05-methods",
    6: "06-environments",
    7: "07-feedback",
    8: "08-loop",
    9: "09-patterns",
    10: "10-evaluation",
    11: "11-ownership",
    12: "12-ecosystem",
}


def chapter_png(n):
    d = REPO_ROOT / "book" / "contents" / "chapters" / CHAPTER_DIR[n] / "images"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"plot_ch{n}.png"


def get_rows(fname):
    """Read a dataset, skipping any leading '#' provenance header block."""
    rows = []
    with open(src_dir / fname, "r") as f:
        reader = csv.DictReader(line for line in f if not line.startswith("#"))
        for r in reader:
            rows.append(r)
    return rows


# Ch1: fig-silicon-scaling-plateau (plot_ch1.png)
rows = get_rows("ch1_data.csv")
hw = [r for r in rows if "Silicon" in r["Domain"]]
sw = [r for r in rows if "Software" in r["Domain"]]
plt.figure(figsize=(8, 6))
plt.plot(
    [float(r["Tokens_B"]) for r in sw],
    [float(r["Pass_at_1"]) for r in sw],
    "o-",
    label="Software GenAI",
    color="#2563eb",
    linewidth=2,
    markersize=7,
)
plt.plot(
    [float(r["Tokens_B"]) for r in hw],
    [float(r["Pass_at_1"]) for r in hw],
    "s-",
    label="Silicon GenAI",
    color="#dc2626",
    linewidth=2,
    markersize=7,
)
plt.xscale("log")
plt.xlabel("Deduplicated Training Tokens (Billions, Log)")
plt.ylabel("Pass@1 Accuracy (%)")
plt.ylim(10, 95)
plt.grid(True, alpha=0.25, linestyle="--")
plt.legend(framealpha=0.92, facecolor="white", edgecolor="none")
plt.savefig(chapter_png(1), dpi=300, bbox_inches="tight")
plt.close()

# Ch2: fig-moores-law-breakdown (plot_ch2.png)
rows = get_rows("ch2_data.csv")
nodes = [r["Process_Node"] for r in rows]
capex = [float(r["Foundry_CapEx_Billions"]) for r in rows]
cost_tr = [float(r["Cost_Per_Billion_Transistors_USD"]) for r in rows]

fig, ax1 = plt.subplots(figsize=(10, 6))
ax2 = ax1.twinx()
b1 = ax1.bar(
    nodes, capex, color="#94a3b8", alpha=0.55, width=0.6, label="Foundry CapEx (B$)"
)
l1 = ax2.plot(
    nodes,
    cost_tr,
    "r-o",
    linewidth=2.5,
    markersize=7,
    label="Cost / 1B Transistors ($)",
)
ax1.set_xlabel("Process Node")
ax1.set_ylabel("Foundry CapEx (Billions USD)")
ax2.set_ylabel("Cost per Billion Transistors (USD)")
ax1.set_ylim(0, 32)
ax2.set_ylim(1.8, 7.8)
ax1.grid(True, alpha=0.25, linestyle="--", axis="y")

# Unified legend in open center space
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(
    lines1 + lines2,
    labels1 + labels2,
    loc="upper center",
    bbox_to_anchor=(0.5, 0.95),
    ncol=2,
    framealpha=0.95,
    facecolor="white",
)
plt.savefig(chapter_png(2), dpi=300, bbox_inches="tight")
plt.close()

# Ch3: fig-verification-wall (plot_ch3.png)
from plot_ch3_verification_costs import main as plot_ch3

with plt.rc_context():
    plot_ch3()

# Ch4: fig-topological-explosion (plot_ch4.png)
rows = get_rows("ch4_data.csv")
plt.figure(figsize=(8, 6))
plt.scatter(
    [float(r["Gate_Count_GE"]) for r in rows],
    [float(r["Rents_Exponent"]) for r in rows],
    s=180,
    alpha=0.85,
    c="#7c3aed",
    edgecolors="white",
    linewidths=1.5,
    zorder=4,
)
label_offsets = {
    "PicoRV32": (10, -4),
    "Ibex": (10, -4),
    "CV32E40P": (10, -4),
    "Rocket": (12, -14),
    "Ariane (CVA6)": (12, 6),
    "SonicBOOM": (-85, 4),
    "OpenSPARC T1": (-105, -6),
}
for r in rows:
    core = r["IP_Core"]
    x = float(r["Gate_Count_GE"])
    y = float(r["Rents_Exponent"])
    dx, dy = label_offsets.get(core, (10, -4))
    plt.annotate(
        core,
        (x, y),
        xytext=(dx, dy),
        textcoords="offset points",
        fontsize=9,
        bbox=dict(
            boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.85
        ),
        zorder=5,
    )
plt.xscale("log")
plt.xlabel("Total Gate Count (GE, Log)")
plt.ylabel("Rent's Exponent ($p$, Graph Entropy)")
plt.xlim(6e3, 6e6)
plt.ylim(0.53, 0.78)
plt.grid(True, alpha=0.25, linestyle="--")
plt.savefig(chapter_png(4), dpi=300, bbox_inches="tight")
plt.close()

# Ch5: fig-agentic-sweet-spot (plot_ch5.png)
rows = get_rows("ch5_data.csv")
plt.figure(figsize=(9, 6))

cat_handles = {
    "Sweet Spot": plt.scatter(
        [], [], c="#16a34a", s=120, label="Sweet Spot (High Capability & Speed)"
    ),
    "Balanced": plt.scatter([], [], c="#d97706", s=120, label="Balanced Trade-off"),
    "Bound": plt.scatter(
        [], [], c="#dc2626", s=120, label="Throughput or Capability Bound"
    ),
}

offsets_ch5 = {
    "Claude 3 Opus": (12, -4),
    "OpenAI o1-preview": (12, 4),
    "GPT-4 Turbo": (12, -6),
    "Llama 3.1 405B": (12, -6),
    "Gemini 1.5 Pro": (12, 6),
    "GPT-4o": (12, 4),
    "Claude 3.5 Sonnet": (12, 4),
    "Llama 3.1 70B": (-95, 6),
}

for r in rows:
    color = (
        "#16a34a"
        if "Sweet" in r["category"]
        else "#d97706"
        if "Balanced" in r["category"]
        else "#dc2626"
    )
    x = float(r["tps"])
    y = float(r["swe_bench_score"])
    plt.scatter(x, y, c=color, s=150, edgecolors="white", linewidths=1.2, zorder=4)
    dx, dy = offsets_ch5.get(r["model"], (12, -4))
    plt.annotate(
        r["model"],
        (x, y),
        xytext=(dx, dy),
        textcoords="offset points",
        fontsize=9,
        bbox=dict(
            boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.85
        ),
        zorder=5,
    )

plt.xscale("log")
plt.xlabel("Token Generation Throughput (TPS, Log)")
plt.ylabel("Agentic Coding Score (SWE-bench Verified %)")
plt.xlim(18, 350)
plt.ylim(8, 56)
plt.grid(True, alpha=0.25, linestyle="--")
plt.legend(
    handles=list(cat_handles.values()),
    loc="lower right",
    framealpha=0.95,
    facecolor="white",
    edgecolor="none",
)
plt.savefig(chapter_png(5), dpi=300, bbox_inches="tight")
plt.close()

# Ch6: fig-api-driven-tapeouts (plot_ch6.png)
rows = get_rows("ch6_data.csv")
plt.figure(figsize=(10, 6))
plt.plot(
    [r["Date"] for r in rows],
    [float(r["Cumulative_API_Tapeouts"]) for r in rows],
    "-o",
    color="#c026d3",
    linewidth=2.5,
    markersize=6,
)
plt.xticks(rotation=40, ha="right")
plt.xlabel("Date")
plt.ylabel("Cumulative Programmatic Tapeouts")
plt.ylim(0, 2050)
plt.grid(True, alpha=0.25, linestyle="--")
plt.savefig(chapter_png(6), dpi=300, bbox_inches="tight")
plt.close()

# Ch7: fig-mutation-roi (plot_ch7.png)
rows = get_rows("ch7_data.csv")
plt.figure(figsize=(8, 6))
plt.plot(
    [float(r["Simulation_Compute_Hours"]) for r in rows],
    [float(r["Mutation_Survival_Rate_Pct"]) for r in rows],
    "k-o",
    linewidth=2.2,
    markersize=6,
)
plt.xscale("log")
plt.xlabel("Simulation Compute Hours (Log)")
plt.ylabel("Mutation Survival Rate (%)")
plt.ylim(0, 108)
plt.grid(True, alpha=0.25, linestyle="--")
plt.annotate(
    "Diminishing returns\n(~5% asymptote)",
    xy=(20000, 5.0),
    xytext=(1500, 22),
    arrowprops=dict(arrowstyle="->", color="#dc2626", lw=1.5),
    fontsize=9,
    bbox=dict(
        boxstyle="round,pad=0.3", facecolor="white", edgecolor="#dc2626", alpha=0.9
    ),
)
plt.savefig(chapter_png(7), dpi=300, bbox_inches="tight")
plt.close()

# Ch8: fig-rl-convergence (plot_ch8.png)
rows = get_rows("ch8_data.csv")
hours = [float(r["Training_Hours"]) for r in rows]
plt.figure(figsize=(8, 6))
plt.plot(
    hours,
    [float(r["RL_Agent"]) for r in rows],
    color="#2563eb",
    linewidth=2.8,
    label="RL Agent (AlphaChip proxy)",
)
plt.plot(
    hours,
    [float(r["Simulated_Annealing"]) for r in rows],
    color="#16a34a",
    linestyle="--",
    linewidth=2,
    label="Simulated Annealing",
)
plt.plot(
    hours,
    [float(r["Human_Baseline"]) for r in rows],
    color="#dc2626",
    linestyle=":",
    linewidth=2.2,
    label="Human Expert Baseline",
)
plt.xlabel("Training Hours")
plt.ylabel("Proxy PPA Cost")
plt.ylim(0.76, 1.12)
plt.grid(True, alpha=0.25, linestyle="--")
plt.legend(loc="upper right", framealpha=0.92, facecolor="white", edgecolor="none")
plt.savefig(chapter_png(8), dpi=300, bbox_inches="tight")
plt.close()

# Ch9: fig-interconnect-scaling (plot_ch9.png)
rows = get_rows("ch9_data.csv")
plt.figure(figsize=(9, 6))

offsets_ch9 = {
    "UCIe (Advanced Packaging)": (12, -4),
    "Bunch of Wires": (12, -4),
    "UCIe (Standard 2D)": (12, 4),
    "NVLink C2C": (12, -4),
    "Co-Packaged Optics": (-45, 14),
    "NVLink 5 (Blackwell)": (12, 4),
    "NVLink 4 (Hopper)": (12, -4),
    "PCIe Gen 6": (12, 8),
    "PCIe Gen 5": (12, -6),
    "Pluggable Optics 800G": (12, -12),
}

d2d_h = plt.scatter([], [], c="#2563eb", s=130, label="Die-to-Die (Advanced Packaging)")
pkg_h = plt.scatter([], [], c="#d97706", s=130, label="Package / Scale-up")
brd_h = plt.scatter([], [], c="#16a34a", s=130, label="Board / Optical Network")

for r in rows:
    c = (
        "#2563eb"
        if "Die-to-Die" in r["Type"]
        else "#d97706"
        if "Pkg" in r["Type"]
        else "#16a34a"
    )
    x = float(r["Energy_Efficiency_pJ_bit"])
    y = float(r["Bandwidth_Density_Tbps_mm"])
    plt.scatter(x, y, c=c, s=140, edgecolors="white", linewidths=1.2, zorder=4)
    dx, dy = offsets_ch9.get(r["Interconnect"], (12, 0))
    plt.annotate(
        r["Interconnect"],
        (x, y),
        xytext=(dx, dy),
        textcoords="offset points",
        fontsize=8.5,
        bbox=dict(
            boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.85
        ),
        zorder=5,
    )

plt.xscale("log")
plt.yscale("log")
plt.xlabel("Energy Efficiency (pJ/bit, Log)")
plt.ylabel("Bandwidth Density (Tbps/mm, Log)")
plt.xlim(0.12, 28)
plt.ylim(0.03, 6.5)
plt.grid(True, alpha=0.25, linestyle="--", which="both")
plt.legend(
    handles=[d2d_h, pkg_h, brd_h],
    loc="upper right",
    framealpha=0.95,
    facecolor="white",
    edgecolor="none",
)
plt.savefig(chapter_png(9), dpi=300, bbox_inches="tight")
plt.close()

# Ch10: fig-llm-judge-mfu-collapse (plot_ch10.png)
rows = get_rows("ch10_data.csv")
plt.figure(figsize=(8, 6))
plt.plot(
    [float(r["Parameters_B"]) for r in rows],
    [float(r["MFU_Percent"]) for r in rows],
    color="#0891b2",
    marker="o",
    linewidth=2.5,
    markersize=7,
    zorder=4,
)
plt.xscale("log")
for r in rows:
    x = float(r["Parameters_B"])
    y = float(r["MFU_Percent"])
    plt.annotate(
        r["Model"],
        (x, y),
        xytext=(10, 5),
        textcoords="offset points",
        fontsize=9,
        bbox=dict(
            boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.85
        ),
        zorder=5,
    )
plt.xlabel("Model Parameters (Billions, Log)")
plt.ylabel("Peak Hardware MFU (%)")
plt.xlim(5, 600)
plt.ylim(5, 45)
plt.grid(True, alpha=0.25, linestyle="--")
plt.savefig(chapter_png(10), dpi=300, bbox_inches="tight")
plt.close()

# Ch11: fig-ch11-vuln-shift (plot_ch11.png)
rows = get_rows("ch11_data.csv")
years = [int(r["Year"]) for r in rows]
spec = [float(r["Speculative Execution"]) for r in rows]
side = [float(r["Side Channels"]) for r in rows]
fault = [float(r["Fault Injection"]) for r in rows]
fw = [float(r["Firmware/Management Engine"]) for r in rows]
crypto = [float(r["Crypto/Enclaves"]) for r in rows]

plt.figure(figsize=(10, 6))
plt.stackplot(
    years,
    fw,
    crypto,
    fault,
    side,
    spec,
    labels=[
        "Firmware / ME",
        "Crypto / Enclaves",
        "Fault Injection",
        "Side Channels",
        "Speculative Execution",
    ],
    colors=["#1e3a8a", "#0284c7", "#16a34a", "#f59e0b", "#dc2626"],
    alpha=0.85,
)
plt.axvline(2018, color="#7f1d1d", linestyle="--", linewidth=1.5, alpha=0.7)
plt.text(
    2018.1,
    88,
    "Spectre & Meltdown\n(2018)",
    fontsize=8.5,
    color="#7f1d1d",
    fontweight="bold",
)
plt.xlabel("Year")
plt.ylabel("Number of Reported Hardware CVEs")
plt.xlim(2014, 2024)
plt.ylim(0, 105)
plt.grid(True, alpha=0.25, linestyle="--", axis="y")
plt.legend(loc="upper left", framealpha=0.92, facecolor="white", edgecolor="none")
plt.savefig(chapter_png(11), dpi=300, bbox_inches="tight")
plt.close()

# Ch12: fig-ecosystem-network-graph (plot_ch12.png)
try:
    rows = get_rows("ch12_data.csv")
    G = nx.DiGraph()
    for r in rows:
        G.add_edge(r["Source_Project"], r["Target_Dependency"])
    plt.figure(figsize=(11, 8.5))
    pos = nx.spring_layout(G, k=1.9, iterations=150, seed=42)
    # Custom offset for tightly clustered nodes
    pos["Rocket"] = (pos["Rocket"][0] - 0.08, pos["Rocket"][1] + 0.05)
    pos["BOOM"] = (pos["BOOM"][0] + 0.08, pos["BOOM"][1] + 0.05)
    pos["Chipyard"] = (pos["Chipyard"][0], pos["Chipyard"][1] - 0.08)
    pos["Edalize"] = (pos["Edalize"][0] - 0.08, pos["Edalize"][1] - 0.05)
    pos["OpenLane"] = (pos["OpenLane"][0] + 0.08, pos["OpenLane"][1] + 0.05)

    nx.draw_networkx_nodes(
        G,
        pos,
        node_color="#bae6fd",
        node_size=2200,
        edgecolors="#0284c7",
        linewidths=1.5,
    )
    nx.draw_networkx_edges(
        G, pos, edge_color="#64748b", arrowsize=14, arrowstyle="-|>", node_size=2200
    )
    nx.draw_networkx_labels(
        G, pos, font_size=8.5, font_family="sans-serif", font_weight="bold"
    )
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(chapter_png(12), dpi=300, bbox_inches="tight")
    plt.close()
except Exception as e:
    print(f"Error plotting Ch12: {e}")

print("All 12 plots generated successfully.")
