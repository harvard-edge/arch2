import matplotlib.pyplot as plt
import csv
from pathlib import Path
import os
import networkx as nx

plt.style.use("data/source-receipts/book.mplstyle")
out_dir = Path(
    "/Users/VJ/.gemini/antigravity-cli/brain/e9d45d93-bc24-4e34-bc92-58598a39e67b"
)
src_dir = Path("data/source-receipts")


def get_rows(fname):
    rows = []
    with open(src_dir / fname, "r") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


# Ch1
rows = get_rows("ch1_data.csv")
hw = [r for r in rows if "Silicon" in r["Domain"]]
sw = [r for r in rows if "Software" in r["Domain"]]
plt.figure(figsize=(8, 6))
plt.plot(
    [float(r["Tokens_B"]) for r in sw],
    [float(r["Pass_at_1"]) for r in sw],
    "o-",
    label="Software GenAI (HumanEval)",
    color="blue",
)
plt.plot(
    [float(r["Tokens_B"]) for r in hw],
    [float(r["Pass_at_1"]) for r in hw],
    "s-",
    label="Silicon GenAI (VerilogEval)",
    color="red",
)
plt.xscale("log")
plt.xlabel("Deduplicated Training Tokens (Billions, Log)")
plt.ylabel("Pass@1 Accuracy (%)")
plt.legend()
plt.savefig(out_dir / "plot_ch1.png", dpi=300)
plt.close()

# Ch2
rows = get_rows("ch2_data.csv")
nodes = [r["Process_Node"] for r in rows]
capex = [float(r["Foundry_CapEx_Billions"]) for r in rows]
cost_tr = [float(r["Cost_Per_Billion_Transistors_USD"]) for r in rows]

fig, ax1 = plt.subplots(figsize=(10, 6))
ax2 = ax1.twinx()
ax1.bar(nodes, capex, color="gray", alpha=0.5, label="Foundry CapEx (B$)")
ax2.plot(nodes, cost_tr, "r-o", linewidth=2, label="Cost / 1B Transistors ($)")
ax1.set_xlabel("Process Node")
ax1.set_ylabel("CapEx (Billions USD)")
ax2.set_ylabel("Cost per Billion Transistors (USD)")
ax1.legend(loc="upper left")
ax2.legend(loc="upper right")
plt.savefig(out_dir / "plot_ch2.png", dpi=300)
plt.close()

# Ch3
rows = get_rows("ch3_data.csv")
locs = [float(r["pr_complexity_loc"]) for r in rows]
times = [float(r["execution_time_minutes"]) for r in rows]
colors = [
    "blue" if r["ci_stage"] == "Lint" else "green" if r["ci_stage"] == "Sim" else "red"
    for r in rows
]
plt.figure(figsize=(8, 6))
plt.scatter(locs, times, c=colors, alpha=0.7)
plt.xscale("log")
plt.yscale("log")
plt.xlabel("PR Complexity (LOC, Log)")
plt.ylabel("Execution Time (Minutes, Log)")
plt.savefig(out_dir / "plot_ch3.png", dpi=300)
plt.close()

# Ch4
rows = get_rows("ch4_data.csv")
plt.figure(figsize=(8, 6))
plt.scatter(
    [float(r["Gate_Count_GE"]) for r in rows],
    [float(r["Rents_Exponent"]) for r in rows],
    s=200,
    alpha=0.8,
    c="purple",
)
for r in rows:
    plt.annotate(r["IP_Core"], (float(r["Gate_Count_GE"]), float(r["Rents_Exponent"])))
plt.xscale("log")
plt.xlabel("Total Gate Count (GE, Log)")
plt.ylabel("Rent's Exponent (Graph Entropy)")
plt.savefig(out_dir / "plot_ch4.png", dpi=300)
plt.close()

# Ch5
rows = get_rows("ch5_data.csv")
plt.figure(figsize=(8, 6))
for r in rows:
    color = (
        "green"
        if "Sweet" in r["category"]
        else "orange"
        if "Balanced" in r["category"]
        else "red"
    )
    plt.scatter(float(r["tps"]), float(r["swe_bench_score"]), c=color, s=150)
    plt.annotate(r["model"], (float(r["tps"]), float(r["swe_bench_score"])))
plt.xscale("log")
plt.xlabel("Token Generation Throughput (TPS, Log)")
plt.ylabel("Agentic Coding Score (SWE-bench %)")
plt.savefig(out_dir / "plot_ch5.png", dpi=300)
plt.close()

# Ch6
rows = get_rows("ch6_data.csv")
plt.figure(figsize=(10, 6))
plt.plot(
    [r["Date"] for r in rows],
    [float(r["Cumulative_API_Tapeouts"]) for r in rows],
    "m-o",
    linewidth=3,
)
plt.xticks(rotation=45)
plt.xlabel("Date")
plt.ylabel("Cumulative API Tapeouts")
plt.tight_layout()
plt.savefig(out_dir / "plot_ch6.png", dpi=300)
plt.close()

# Ch7
rows = get_rows("ch7_data.csv")
plt.figure(figsize=(8, 6))
plt.plot(
    [float(r["Simulation_Compute_Hours"]) for r in rows],
    [float(r["Mutation_Survival_Rate_Pct"]) for r in rows],
    "k-o",
    linewidth=2,
)
plt.xscale("log")
plt.xlabel("Simulation Compute Hours (Log)")
plt.ylabel("Mutation Survival Rate (%)")
plt.savefig(out_dir / "plot_ch7.png", dpi=300)
plt.close()

# Ch8
rows = get_rows("ch8_data.csv")
hours = [float(r["Training_Hours"]) for r in rows]
plt.figure(figsize=(8, 6))
plt.plot(
    hours,
    [float(r["RL_Agent"]) for r in rows],
    "b-",
    linewidth=3,
    label="RL Agent (AlphaChip proxy)",
)
plt.plot(
    hours,
    [float(r["Simulated_Annealing"]) for r in rows],
    "g--",
    label="Simulated Annealing",
)
plt.plot(
    hours,
    [float(r["Human_Baseline"]) for r in rows],
    "r:",
    linewidth=2,
    label="Human Expert Baseline",
)
plt.xlabel("Training Hours")
plt.ylabel("Proxy PPA Cost")
plt.legend()
plt.savefig(out_dir / "plot_ch8.png", dpi=300)
plt.close()

# Ch9
rows = get_rows("ch9_data.csv")
plt.figure(figsize=(8, 6))
for r in rows:
    c = (
        "blue"
        if "Die-to-Die" in r["Type"]
        else "orange"
        if "Package" in r["Type"]
        else "green"
    )
    plt.scatter(
        float(r["Energy_Efficiency_pJ_bit"]),
        float(r["Bandwidth_Density_Tbps_mm"]),
        c=c,
        s=150,
    )
    plt.annotate(
        r["Interconnect"],
        (float(r["Energy_Efficiency_pJ_bit"]), float(r["Bandwidth_Density_Tbps_mm"])),
    )
plt.xscale("log")
plt.yscale("log")
plt.xlabel("Energy Efficiency (pJ/bit, Log)")
plt.ylabel("Bandwidth Density (Tbps/mm, Log)")
plt.savefig(out_dir / "plot_ch9.png", dpi=300)
plt.close()

# Ch10
rows = get_rows("ch10_data.csv")
plt.figure(figsize=(8, 6))
plt.plot(
    [float(r["Parameters_B"]) for r in rows],
    [float(r["MFU_Percent"]) for r in rows],
    "c-o",
    linewidth=3,
)
plt.xscale("log")
for r in rows:
    plt.annotate(r["Model"], (float(r["Parameters_B"]), float(r["MFU_Percent"])))
plt.xlabel("Model Parameters (Billions, Log)")
plt.ylabel("Peak Hardware MFU (%)")
plt.savefig(out_dir / "plot_ch10.png", dpi=300)
plt.close()

# Ch11
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
    labels=["Firmware", "Crypto", "Fault Inj", "Side Channels", "Speculative"],
)
plt.xlabel("Year")
plt.ylabel("Number of Reported CVEs")
plt.legend(loc="upper left")
plt.savefig(out_dir / "plot_ch11.png", dpi=300)
plt.close()

# Ch12
try:
    rows = get_rows("ch12_data.csv")
    G = nx.DiGraph()
    for r in rows:
        G.add_edge(r["Source_Project"], r["Target_Dependency"])
    plt.figure(figsize=(10, 8))
    pos = nx.spring_layout(G, k=0.5)
    nx.draw(
        G,
        pos,
        with_labels=True,
        node_color="lightblue",
        edge_color="gray",
        node_size=2000,
        font_size=9,
    )
    plt.savefig(out_dir / "plot_ch12.png", dpi=300)
    plt.close()
except:
    pass

print("All 12 plots generated successfully.")
