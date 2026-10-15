# Grounded Workbench Labs Moved to `nanochip/`

The ***Architecture 2.0*** hands-on laboratory curriculum now lives in [`../nanochip/`](../nanochip/README.md), centered on the complete 6-stage AI-native design loop of **Moonshot AI's `nano-kpu`** (`msh_chip_top`, designed by Kimi K3):

- **Flagship Guide:** [`../nanochip/README.md`](../nanochip/README.md)
- **Attribution & Provenance:** [`../nanochip/CREDIT.md`](../nanochip/CREDIT.md)
- **Design-Loop Card v2.0:** [`../nanochip/cards/nano-kpu-study-card.yaml`](../nanochip/cards/nano-kpu-study-card.yaml)

## The 6 Progressive Lifecycle Labs

1. **Lab 01 — Stage 1 (`Formulate`):** [`../nanochip/labs/01-formulate/`](../nanochip/labs/01-formulate/README.md) — *Locking the Study Contract & Integrity Boundary*
2. **Lab 02 — Stage 2 (`Explore`):** [`../nanochip/labs/02-explore/`](../nanochip/labs/02-explore/README.md) — *Roofline Betting & Candidate Generation*
3. **Lab 03 — Stage 3 (`Implement`):** [`../nanochip/labs/03-implement/`](../nanochip/labs/03-implement/README.md) — *The Multi-Fidelity Representation Sandwich (`float32` $\rightarrow$ `fxmodel.py` $\rightarrow$ `rtl/`)*
4. **Lab 04 — Stage 4 (`Evaluate`):** [`../nanochip/labs/04-evaluate/`](../nanochip/labs/04-evaluate/README.md) — *Adversarial Referees, Chaos Testing & Silicon Synthesis*
5. **Lab 05 — Stage 5 (`Interpret`):** [`../nanochip/labs/05-interpret/`](../nanochip/labs/05-interpret/README.md) — *Causal Credit Assignment & The Three Return Arrows*
6. **Lab 06 — Stage 6 (`Commit`):** [`../nanochip/labs/06-commit/`](../nanochip/labs/06-commit/README.md) — *Signoff Governance, Proxy Gaps & The Design-Loop Card v2.0*

## Quickstart

```bash
./arch2 lab list
./arch2 lab run all
# or directly:
python3 nanochip/labs/run_all.py
```
