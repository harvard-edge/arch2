# Micro-Loop C: Physical Design, Macro Placement, and Routing Congestion

## 1. Conceptual Focus

This micro-loop answers the foundational question of AI in computer architecture: **Are we doing AI-native architecture here, or are we just doing AI-assisted or AI-driven optimization?**

Using a physics-grounded **Rectangular Uniform Density (RUDY)** routing wire congestion model calibrated to modern physical design signoff rules, this exercise shows why optimizing geometric proxies like wirelength leads to unroutable silicon, and how AI-native systems resolve routing bottlenecks through multi-objective physical co-adaptation.

---

## 2. Workload & Technology Constraints

* **Die Canvas:** $1000 \times 1000\ \mu\text{m}$ single-die silicon tile.
* **Blocks:** Central standard-cell compute core ($300 \times 300\ \mu\text{m}$) and 4 memory SRAM macros ($200 \times 400\ \mu\text{m}$).
* **Metal Pitch & Capacity:** Metal 3/4 track pitch of $0.40\ \mu\text{m}$ ($100\text{ tracks}$ per $40\ \mu\text{m}$ grid cell).
* **Physical Blockages:** Memory macros block $80\%$ of routing tracks across all internal metal layers.
* **Signoff Criteria:** Peak routing track density $\le 85.0\%$ and zero Design Rule Check (DRC) routing shorts ($\text{DRC} = 0$).

---

## 3. Paradigm Comparison

### Level 1: AI-Assisted Architecture (Open-Loop Coordinate Drafting)
* **Mechanism:** A generative model drafts macro $(x,y)$ bounding boxes and orientation coordinates based on textual prompting.
* **Limitation:** The placement is uncoordinated and asymmetric. Total wirelength is high ($\text{HPWL} = 12,400\ \mu\text{m}$), and wire density peaks at $94.2\%$, causing 18 design rule check (DRC) shorts where wires overlap without available routing tracks.

### Level 2: AI-Driven Optimization (Single-Objective Wirelength Minimization)
* **Mechanism:** An automated macro placement algorithm (simulated annealing, analytical placement, or reinforcement learning) searches coordinate space to minimize Half-Perimeter Wirelength (HPWL).
* **Limitation:** The optimizer successfully reduces HPWL to $7,820\ \mu\text{m}$ (a $36.9\%$ wirelength reduction) by clustering the 4 memory macros tightly against the compute core. However, packing the macros inward directs all pin escape corridors into the same narrow central avenues, causing severe track overflow ($91.8\%$ peak congestion, well past the $85\%$ physical DRC cliff). The optimizer cannot fix this because it cannot alter pin interfaces or widen macro corridors.

### Level 3: AI-Native System Design (Closed-Loop Multi-Objective Co-Adaptation)
* **Mechanism:** The closed-loop agent ingests the 2D RUDY routing congestion heatmap from the physical signoff engine.
* **Cross-Layer Action:** Recognizing that pin escape density is causing routing shorts, the agent executes two coordinated physical adaptations:
  1. **Pin Re-Orientation:** Rotates macro orientations outward so memory pin arrays break out directly into peripheral routing channels.
  2. **Dedicated Channel Allocation:** Enforces guaranteed $110\ \mu\text{m}$ routing avenues between macros and the core.
* **Signoff Outcome:** Although HPWL increases slightly to $8,240\ \mu\text{m}$ (a necessary trade-off), peak congestion drops to $64.5\%$ and DRC shorts drop to zero ($0$ violations), achieving DRC-clean tapeout signoff.

---

## 4. Anti-Reward-Hacking Guarantee

| Aspect | Description |
| :--- | :--- |
| **Naive / Hacked Proxy Metric** | Half-Perimeter Wirelength (HPWL) minimization. Commonly used in academic placers because it is differentiable and fast to compute. |
| **Hidden Physical Failure** | Extreme routing congestion hotspots and DRC pin shorts: tightly packed macros leave zero routing tracks for actual metal wires, rendering the chip unmanufacturable. |
| **Grounded Signoff Gate** | **Detailed 2D RUDY Track Saturation & DRC Audit:** Every $40 \times 40\ \mu\text{m}$ bin is evaluated against local metal layer track capacity. Any bin exceeding $85\%$ track demand triggers hard DRC short rejections. |
| **Toolchain Provenance** | Modeled after standard commercial global routers using Rectangular Uniform Density with macro blockage derating and pin escape modeling. |

---

## 5. Execution & Verification

### Running inside Docker (Recommended)
```bash
./arch2 docker lab 03
```

### Running on Host Python
```bash
python3 labs/03-physical-floorplan/run.py
```

### Artifacts Generated
* `results.json`: Floorplan coordinates, HPWL, peak/average congestion percentages, and DRC violation counts.
* `results.png`: 2D floorplan layout maps and routing congestion heatmaps for all three paradigms.
