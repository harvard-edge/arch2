import os
import csv
import matplotlib.pyplot as plt

plt.style.use("data/source-receipts/book.mplstyle")
plt.rcParams.update(
    {
        "font.size": 12,
        "axes.labelsize": 14,
        "axes.titlesize": 16,
        "legend.fontsize": 12,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
    }
)

OUT_DIR = "data/source-receipts"


def read_csv(path):
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        return list(reader)


def plot_linux_growth():
    data = read_csv(f"{OUT_DIR}/linux_kernel_growth_historical.csv")
    yearly = {}
    for row in data:
        y = int(row["release_year"])
        s = float(row["tar_xz_size_mb"])
        if y not in yearly or s > yearly[y]:
            yearly[y] = s

    years = sorted(yearly.keys())
    sizes = [yearly[y] for y in years]

    plt.figure(figsize=(8, 5))
    plt.plot(years, sizes, marker="o", linewidth=2, color="#2c3e50")
    plt.fill_between(years, sizes, alpha=0.2, color="#34495e")
    plt.title("Linux Kernel Source Complexity (1994-2024)")
    plt.xlabel("Release Year")
    plt.ylabel("Compressed Tarball Size (MB)")
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.savefig(f"{OUT_DIR}/plot_linux_growth.png")
    plt.close()


def plot_mlir_explosion():
    data = read_csv(f"{OUT_DIR}/mlir_dialect_explosion.csv")
    years = [int(row["year"]) for row in data]
    dialects = [int(row["dialect_count"]) for row in data]
    ops = [int(row["total_operations"]) for row in data]

    fig, ax1 = plt.subplots(figsize=(8, 5))

    color1 = "#2980b9"
    ax1.set_xlabel("LLVM Release Year")
    ax1.set_ylabel("Number of MLIR Dialects", color=color1)
    ax1.plot(years, dialects, marker="s", linewidth=2, color=color1)
    ax1.tick_params(axis="y", labelcolor=color1)

    ax2 = ax1.twinx()
    color2 = "#c0392b"
    ax2.set_ylabel("Total Operations Defined", color=color2)
    ax2.plot(years, ops, marker="o", linestyle="--", linewidth=2, color=color2)
    ax2.tick_params(axis="y", labelcolor=color2)

    plt.title("The Compiler IR Explosion: MLIR Dialect Growth")
    plt.grid(False)
    ax1.grid(True, linestyle="--", alpha=0.7)
    plt.savefig(f"{OUT_DIR}/plot_mlir_explosion.png")
    plt.close()


def plot_hdl_trends():
    data = read_csv(f"{OUT_DIR}/github_hdl_language_trends.csv")
    years = [int(r["Year"]) for r in data]

    plt.figure(figsize=(10, 6))
    plt.plot(years, [int(r["Verilog"]) for r in data], label="Verilog", linewidth=2.5)
    plt.plot(
        years,
        [int(r["VHDL"]) for r in data],
        label="VHDL",
        linewidth=2.5,
        linestyle="--",
    )
    plt.plot(
        years,
        [int(r["SystemVerilog"]) for r in data],
        label="SystemVerilog",
        linewidth=2.5,
    )
    plt.plot(
        years,
        [int(r["Chisel"]) for r in data],
        label="Chisel (Agile HDL)",
        linewidth=2.5,
        color="#e74c3c",
    )

    plt.title("Global Open-Source RTL Topology (GitHub Repositories)")
    plt.xlabel("Year")
    plt.ylabel("Cumulative Repositories Created")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.yscale("log")
    plt.savefig(f"{OUT_DIR}/plot_hdl_trends.png")
    plt.close()


def plot_ai_tco_limits():
    data = read_csv(f"{OUT_DIR}/ai_accelerator_power_thermal_trend.csv")

    plt.figure(figsize=(9, 6))
    colors = {
        "Google": "#4285F4",
        "NVIDIA": "#76B900",
        "AMD": "#ED1C24",
        "Cerebras": "#F39C12",
        "Intel": "#0071C5",
    }

    for r in data:
        company = r["Company"]
        if company == "Cerebras":
            continue
        y = float(r["Year"])
        tdp = float(r["TDP_W"])
        trans = float(r["Transistors_B"]) * 10

        plt.scatter(y, tdp, s=trans, c=colors[company], alpha=0.7, edgecolors="k")
        plt.annotate(r["Chip"], (y + 0.1, tdp + 10), fontsize=9)

    # Custom legend
    import matplotlib.patches as mpatches

    handles = [
        mpatches.Patch(color=c, label=k) for k, c in colors.items() if k != "Cerebras"
    ]
    plt.legend(handles=handles, title="Company", loc="upper left")

    plt.title("AI Accelerator Thermal Limits (Bubble Size = Transistors)")
    plt.xlabel("Launch Year")
    plt.ylabel("Thermal Design Power (TDP in Watts)")
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.savefig(f"{OUT_DIR}/plot_ai_tco_limits.png")
    plt.close()


if __name__ == "__main__":
    print("Generating plots...")
    plot_linux_growth()
    plot_mlir_explosion()
    plot_hdl_trends()
    plot_ai_tco_limits()
    print("All plots generated successfully.")
