import matplotlib.pyplot as plt
import numpy as np
import sys
import os

# Include book/_python path for styling
sys.path.append(os.path.abspath("book/_python"))
from plots import apply_style, COLORS, add_note_box

apply_style()

fig, ax = plt.subplots(figsize=(8, 5))

# Analytical Model Parameters:
# T_total = N * (t_gen + s * t_eval)
# N: Candidate Proposal Volume (10^0 to 10^5)
# s: Early Screening Selectivity (fraction of candidates surviving to full verification, 0.001 to 1.0)
# Budget limit: B_time = 1000 GPU-hours
# t_gen = 0.01 GPU-hours (Fast LLM generation)
# t_eval = 5.0 GPU-hours (Full physical/RTL simulation & signoff)

N = np.logspace(0, 5, 200)
selectivity_levels = [1.0, 0.1, 0.01, 0.001]
line_styles = ["-", "--", "-.", ":"]
colors_list = [
    COLORS["constraints"],
    COLORS["methods"],
    COLORS["workload"],
    COLORS["evidence"],
]

B_time = 1000.0  # Time budget in GPU-hours
t_gen = 0.01
t_eval = 5.0

for s, style, col in zip(selectivity_levels, line_styles, colors_list):
    cost = N * (t_gen + s * t_eval)
    label = f"s = {s*100:g}% survival ({'Unfiltered' if s==1.0 else f'{int(1/s):d}x screening filter'})"
    ax.plot(N, cost, label=label, color=col, linestyle=style, linewidth=2.2)

# Plot Budget Ceiling
ax.axhline(
    B_time,
    color="black",
    linestyle="--",
    linewidth=1.5,
    label="Project Execution Time Budget ($B_{time}$)",
)

# Highlight Feasible Operating Sub-Region
ax.fill_between(
    N,
    0.1,
    B_time,
    where=(N * (t_gen + 0.001 * t_eval) <= B_time),
    color=COLORS["evidence"],
    alpha=0.08,
    label="Architect's Feasible Region (s <= 0.1%)",
)


ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlim(1, 100000)
ax.set_ylim(0.1, 1000000)

ax.set_xlabel("Candidate Proposal Volume ($N$)", fontsize=11, fontweight="bold")
ax.set_ylabel(
    "Total Verification Compute Demand (GPU-Hours)", fontsize=11, fontweight="bold"
)
ax.set_title(
    "First-Order Analytical Model: The Architect's Feasible Execution Sub-Region",
    fontsize=12,
    fontweight="bold",
    pad=12,
)

ax.grid(True, which="both", linestyle=":", alpha=0.4)
ax.legend(loc="upper left", frameon=True, fontsize=8.5)

# Add explanatory note box using figure coordinates
add_note_box(
    fig,
    "Analytical Formulation:\n"
    "T_total = N * (t_gen + s * t_eval) <= B_time\n"
    "As candidate generation rate increases by 1000x,\n"
    "early rejection-bound screening (s <= 0.1%) is required\n"
    "to remain inside the feasible execution window.",
    xywh=(0.52, 0.18, 0.40, 0.22),
    fontsize=6.5,
)


plt.tight_layout()
os.makedirs("scratch", exist_ok=True)
plot_path = "scratch/architect_feasible_subregion.png"
plt.savefig(plot_path, dpi=300)
plt.close(fig)

print(f"Plot saved successfully to {plot_path}")
