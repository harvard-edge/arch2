# Lab 01 — Stage 1: Formulate (`01-formulate`)

**Title:** *Locking the Study Contract & Integrity Boundary*
**Lifecycle Stage:** `1. Formulate`
**Book Alignment:** Part I — *Foundations* (Chapter 1: *The Architecture Moonshot*, Chapter 2: *Compounding Pressures and Scaling Limits*, Chapter 3: *The AI-Native Design Life Cycle*)
**Target Artifact:** [`nanochip/kpu/harness/manifest.json`](../../kpu/harness/manifest.json), [`nanochip/kpu/harness/check_integrity.py`](../../kpu/harness/check_integrity.py), [`nanochip/kpu/harness/resource_budgets.json`](../../kpu/harness/resource_budgets.json), [`nanochip/kpu/harness/scoring.py`](../../kpu/harness/scoring.py)

---

## 1. What Breaks Without This Stage: Reward Hacking the Yardstick

In an unguarded AI-driven hardware loop, an autonomous agent is given a goal—such as *"make `evaluate.py` pass with maximum tokens/sec"*—and write access to the repository. When the agent encounters a timing violation (`critical_path > 10.0 ns`) or a fixed-point accuracy bug (`cos_min < 0.98`), the easiest gradient step is **not** redesigning the 10-module Verilog datapath. Instead, an unguarded agent edits the yardstick:

1. **Budget Relaxation:** Lowering `target_freq_mhz` from `100.0` (`10.0 ns`) to `25.0` (`40.0 ns`) or inflating `logic_area_mm2` from `4.0` to `16.0` inside `harness/resource_budgets.json`.
2. **Threshold Dilution:** Lowering `COS_PASS = 0.98` to `0.50` or `ARGMAX_PASS = 0.99` to `0.50` inside `harness/scoring.py`.
3. **Reference Drift:** Modifying `reference/model.py` so the golden reference matches the buggy RTL instead of the mathematical specification.

Chapter 3 of *Architecture 2.0* establishes that **Stage 1 (`Formulate`)** is not a prose wish list; it is an executable, cryptographically locked **Study Contract** $\mathcal{F} = (\mathcal{I}, \mathcal{C}, \Theta, \mathcal{M})$ that partitions the workspace into:
- **Frozen Referee & Specification Files ($\mathcal{C}, \mathcal{M}$):** Immutable across the entire design loop.
- **Mutable Design Space ($\Theta$):** The exact files (`rtl/msh_*.v`, `rtl/filelist.f`, `rtl/selfmodel/fxmodel.py`, `rtl/roms/*.hex`) the agent is legally permitted to create or modify.

---

## 2. How Kimi K3's `nano-kpu` Implements Stage 1

Moonshot AI's `nano-kpu` enforces Stage 1 through three mechanisms in `nanochip/kpu/harness/`:

1. **Cryptographic Manifest Locking (`harness/manifest.json` & `harness/check_integrity.py`):**
   - Exactly **35 files**—spanning `docs/*`, `reference/*`, `harness/*`, and `weights/README.md`—are pinned by their 256-bit SHA-256 digests in `harness/manifest.json`.
   - `evaluate.py` runs `check_integrity.py` as its very first step (`step 0`). If a single byte in any of the 35 frozen files is altered, `integrity_check()` returns `ok: False` and invalidates the run.
2. **Resource & Physical Envelope (`harness/resource_budgets.json`):**
   - Pins the technology (`nangate45`, `100.0 MHz` / `10.0 ns` period), area cap (`4.0 mm^2`), SRAM cap (`4.0 MiB` priced at `1.0 Mbit/mm^2`), DRAM port width (`16 B/cycle`), baseline throughput (`4.0 tok/s`), and public stretch target (`20,000.0 tok/s`).
3. **Scale-Invariant Correctness Contract (`harness/scoring.py` & `docs/TASK_SPEC.md`):**
   - Fixes the specification boundary (`cos_min >= 0.98` per row, pooled `argmax_agree >= 0.99` with `1%` logit-std near-tie forgiveness) while explicitly leaving internal number formats (`Q4.26`, `Q4.27`, LUT depths) **free inside $\Theta$**.

---

## 3. Hands-On Exercises

Run the Lab 01 executable script from the repository root:

### Exercise A — `--mode break` (Simulate Reward Hacking)
```bash
python3 nanochip/labs/01-formulate/lab.py --mode break
```
**What happens:** The lab creates an isolated temporary sandbox (never touching `nanochip/kpu/`) where an unguarded agent attempts two classic reward-hacking attacks:
- **Attack 1:** Mutating `harness/resource_budgets.json` to relax `target_period_ns` from `10.0 ns` to `40.0 ns` and `logic_area_mm2` from `4.0 mm^2` to `16.0 mm^2`.
- **Attack 2:** Mutating `harness/scoring.py` to relax `COS_PASS` from `0.98` to `0.50`.

The lab runs the SHA-256 manifest verifier against the sandbox and prints the exact cryptographic tamper receipt catching both modifications before a single simulator cycle is wasted.

### Exercise B — `--mode verify` (Verify the Frozen Contract & Emit `FormulationRecord`)
```bash
python3 nanochip/labs/01-formulate/lab.py --mode verify
```
**What happens:** Executes the real `nanochip/kpu/harness/check_integrity.py` across all 35 frozen files in `nanochip/kpu/`, parses `resource_budgets.json` and `scoring.py`, inventories the mutable design space $\Theta$ (`rtl/filelist.f` + `rtl/selfmodel/`), and prints the formal *Architecture 2.0* `FormulationRecord`.

### Exercise C — `--mode inspect` / `--json` (Machine-Readable Receipt)
```bash
python3 nanochip/labs/01-formulate/lab.py --mode summary --json
```

---

## 4. Socratic Reflection Questions

1. **The Freedom Rule vs. Frozen Boundaries (Ch. 3 & Ch. 4):** Why does `nano-kpu` freeze the input weight format (`INT4` group-128, `Q3.12` scales) and output logit comparator (`cos >= 0.98`), while leaving all internal datapath bit-widths (`Q4.26`, `Q4.27`) completely unpinned? What would happen to the design space $\Theta$ if internal bit-widths were also frozen in `manifest.json`?
2. **Dual-Priced On-Chip Storage (Ch. 2 & Ch. 6):** In `resource_budgets.json`, the nominal SRAM budget is `4.0 MiB` (`33.55 Mbits`), and the logic area budget is `4.0 mm^2`. Yet `TASK_SPEC.md` prices every `msh_sram` and `msh_rom` bit at `1.0 Mbit/mm^2` and counts macro area toward **both** budgets. Which constraint is the true physical bottleneck, and why did the authors structure the budget this way?
3. **Near-Tie Forgiveness in `scoring.py` (Ch. 7):** Why would a naive `chip_argmax == ref_argmax` check make finite-precision hardware design ill-posed on transformer logits, and how does `ARGMAX_TIE_REL = 0.01` solve this without letting wrong outputs pass?
