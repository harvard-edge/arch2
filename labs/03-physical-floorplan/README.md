# Micro-Loop C: Physical Design, Macro Placement, and Routing Congestion

## Conceptual Focus

This micro-loop answers the central question: **Are we doing AI-native architecture here, or are we just doing AI-assisted or AI-driven optimization?**

Focusing on floorplanning and macro placement for an on-chip accelerator tile ($1000 \times 1000\ \mu\text{m}$ die area), this exercise compares three operational paradigms:

1. **AI-Assisted Architecture (Level 1):**
   * **Mechanism:** A generative model drafts initial floorplan macro coordinates and boundary constraints without physical context.
   * **Limitation:** The resulting placement exhibits high half-perimeter wire length (HPWL: $12,400\ \mu\text{m}$) and severe routing congestion ($94.2\%$), producing 18 design rule check (DRC) violations. Human intervention is required to diagnose routability failures.

2. **AI-Driven Optimization (Level 2):**
   * **Mechanism:** An automated macro placer (for example, reinforcement learning or simulated annealing) searches $(x, y)$ coordinates to minimize HPWL within fixed macro pin layouts.
   * **Limitation:** The optimizer successfully reduces HPWL to $7,820\ \mu\text{m}$ (a $36.9\%$ wirelength reduction), but creates an acute routing bottleneck: inward-facing pin arrays create a congested channel that exceeds detailed routing capacity ($91.8\%$ peak congestion, 12 DRC violations). The single-layer geometric optimizer cannot resolve this because it cannot alter pin interfaces or macro banking.

3. **AI-Native System Design (Level 3):**
   * **Mechanism:** The closed loop ingests detailed routing congestion heatmaps and DRC feedback from physical EDA tools.
   * **Cross-layer Adaptation:** Upon diagnosing channel overflow, the loop reframes the design: it re-orients macro pin directions (applying orientation flipping) and repartitions the monolithic memory into interleaved banks with dedicated routing tracks.
   * **Outcome:** Peak congestion drops to $64.5\%$ and DRC violations reach zero, achieving DRC-clean physical placement signoff.

---

## Directory Contents

* `contract.yaml`: Machine-readable contract specifying die boundaries, pin rules, and congestion thresholds.
* `run.py`: Standalone Python runner simulating wirelength, congestion heatmaps, and DRC evaluations across all three modes.
* `results.json`: Generated execution records.

---

## How to Run

From this directory, run:

```bash
python3 run.py
```
