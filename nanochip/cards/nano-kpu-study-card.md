# Design-Loop Card v2.0: `moonshot-kimi-k3-nano-kpu-v2`

**Machine-Readable Contract:** [`nano-kpu-study-card.yaml`](nano-kpu-study-card.yaml)
**Schema Version:** `2.0` ([`card/schemas/design-loop-card.v2.schema.json`](../../card/schemas/design-loop-card.v2.schema.json))
**Validation Command:** `./arch2 validate card nanochip/cards/nano-kpu-study-card.yaml`
**Replay Command:** `python3 nanochip/cards/replay.py verify-all`

---

## 1. Profile Completeness Matrix

| Profile | Status | What It Guarantees in `nanochip` |
| :--- | :--- | :--- |
| **`context`** | `complete` | Explicit objective, frozen physical constraints (`4.0 mm^2`, `4.0 MiB`, `100 MHz`, `16 B/cyc`), non-goals, and deployment assumptions. |
| **`inspectability`** | `complete` | Three-tier representation sandwich (`float32` $\leftrightarrow$ `fxmodel.py` $\leftrightarrow$ `rtl/`), environment blast-radius lock, actor roles, and 48-hour feedback budget. |
| **`replay`** | `complete` | Deterministic `replay.py verify-all` script bound by SHA-256 to `replay-environment.json` and 3 quantitative evidence packets. |
| **`independent_review`** | `complete` | Independent *Architecture 2.0* audit verifying upstream `MoonshotAI/nano-kpu` claims and exposing pre-layout proxy gaps. |
| **`disclosure`** | `complete` | Full open-source Apache-2.0 disclosure of RTL, fixed-point C-model, LUT generators, and public seed `20260706`. |
| **`decision_rights`** | `complete` | Explicit separation of `propose`/`recommend` (`kimi-k3-autonomous-architect`), `execute`/`reject` (`nano-kpu-frozen-harness`), and `waive`/`commit` (`arch2-signoff-architect`). |

---

## 2. Bound Claims and Evidence Summary

| Claim ID | Type | Statement Summary | Measured Outcome | Status |
| :--- | :--- | :--- | :--- | :--- |
| `claim-throughput-2180x` | `architecture_outcome` | Co-designed `msh_chip_top` accelerates decode throughput on `nano` hybrid-attention MoE at `100 MHz`. | **`8,720.58 tok/s`** (`11,467.125 cyc/tok`) vs. `4.0 tok/s` baseline (**`2,180.15x`** speedup; `41.5%` of ideal uncached INT4 pin roofline). | `supported` |
| `claim-sandwich-bit-exact` | `mechanism` | Three-layer Representation Sandwich isolates numeric precision from RTL pipeline implementation bugs. | **`0 ULP`** (100% bit-exact `int32` match) between RTL and `fxmodel.py`; **`cos_min = 1.000000`** (`0.9999999926`) and **`48/48` argmax** vs. `float32`. | `supported` |
| `claim-perf-model-calibration` | `ai_contribution` | Pre-committed analytical `perf-model` accurately predicts full-chip RTL steady-state cycles/token. | **`11,200.0 cyc/tok`** predicted vs. **`11,467.125 cyc/tok`** measured (**`2.33%` relative error**). | `supported` |
| `claim-synthesis-area-timing` | `safety` | Two-pass Yosys/ABC Nangate45 flow closes pre-layout timing and area budgets with zero latches. | **`3.610 mm^2`** total area (`2.707 mm^2` logic + `0.903 mm^2` across 39 macros $\le 4.0\text{ mm}^2$), **`6.166 ns`** delay ($\le 10.0\text{ ns}$), **`0` latches**. | `supported` |

---

## 3. Predeclared Rejection Gates (`gates`)

1. **`gate-frozen-manifest-integrity` (`legality`):** All 35 frozen files in `harness/manifest.json` match SHA-256 $\rightarrow$ **PASSED**.
2. **`gate-static-rtl-audit-and-lint` (`legality`):** Zero hard violations in `audit.py` and Verilator lint `errors == 0`, `warnings == 1 <= 40` $\rightarrow$ **PASSED**.
3. **`gate-functional-cosine-and-argmax` (`functionality`):** Status magic `0x600D_D00D`, $\ge 62,250\text{ B}$ dense read floor, `cos_min >= 0.98`, pooled `argmax >= 0.99` $\rightarrow$ **PASSED**.
4. **`gate-bit-exact-selfmodel` (`evidence`):** `msh_chip_top` RTL matches `rtl/selfmodel/fxmodel.py` bit-exactly across all positions $\rightarrow$ **PASSED**.
5. **`gate-chaos-randreset-and-elasticity` (`reliability`):** Byte-identical output under `+verilator+rand+reset+2` and clean completion at $2\times$ DRAM latency (`48 cyc`, elasticity `1.0457`) $\rightarrow$ **PASSED**.
6. **`gate-nangate45-timing-closure` (`timing`):** Two-pass ABC buffered critical path `6.166 ns <= 10.0 ns` (`100 MHz`) $\rightarrow$ **PASSED**.
7. **`gate-nangate45-area-and-sram-budget` (`area`):** Total area `3.610 mm^2 <= 4.0 mm^2`, SRAM `0.861 MiB <= 4.0 MiB`, `latch_cells == 0` $\rightarrow$ **PASSED**.

---

## 4. Reconstructed Failures & Return Arrows (`failed_or_rejected`)

- **`reject-turn1-shift-and-audit-defect` (`Stage 5 -> Stage 3 Implement`):** 1-bit fixed-point shift mismatch (`<< 13` vs. `<< 14`) or simulation-only `$fread` escape rejected by `selfmodel` diff and `audit.py`.
- **`reject-turn2-non-elastic-stall-and-demux` (`Stage 5 -> Stage 2 Explore`):** Naive 16-way parallel byte demux (+96K gates in `msh_deq`) and rigid non-elastic fetch pipeline rejected; replaced by byte-serial beat emitter (`18,331 um^2`), 256-deep credit FIFO (`1.0457x` elasticity), and dual-parity `qacc` SRAM banking.
- **`reject-turn3-fp16-bandwidth-wall` (`Stage 5 -> Stage 1 Formulate`):** Streaming uncompressed FP16 weights (`304,448 B/tok` $\rightarrow$ `19,028 cyc/tok` floor $\rightarrow$ `5,255 tok/s` ceiling) rejected via conservation of bytes; escalated to INT4 group-128 hardware/numeric co-design (`76,109 B/tok` $\rightarrow$ `4,757 cyc/tok` floor).
- **`reject-unbuffered-wireload-signoff` (`Stage 4 Evaluate`):** Unbuffered ABC wireload STA (`266,515 ps` on `msh_deq`, `5,084 ns` full-chip) rejected as an unbuffered high-fanout artifact; resolved by two-pass `buffer;upsize;dnsize` synthesis (`1,479 ps` on `msh_deq`, `6.166 ns` full-chip).

---

## 5. Signoff Governance & Proxy-to-Purpose Gaps (Chapter 10 & Chapter 11)

Why does the human architect (`arch2-signoff-architect`) authorize **pre-layout architectural commitment** while explicitly **forbidding immediate foundry tapeout**?

1. **Statistical Wireload vs. Extracted Physical Parasitics:** Yosys/ABC uses the `5K_hvratio_1_1` statistical wireload model. Real 1.46M-cell crossbars and 1024-bit wide `qacc` buses require physical floorplanning, global/detailed routing, and SPEF RC extraction in OpenROAD.
2. **Blackboxed Memory Macros (`msh_sram` / `msh_rom`):** All 39 memory macros (9.03 Mbits) are synthesized as blackboxes (`harness/macros/*_bb.v`) priced at a flat `1.0 Mbit/mm^2`. Their internal setup times, clock-to-Q propagation delays, and routing blockages are invisible to pre-layout STA.
3. **Single-Corner Typical STA vs. Multi-Corner PVT Signoff:** Pre-layout timing is measured only at the nominal typical corner (`NangateOpenCellLibrary_typical.lib`) with ideal zero-skew clock distribution. Production silicon signoff requires slow-slow (SS) setup checks, fast-fast (FF) hold checks after clock-tree synthesis (CTS), and IR-drop verification.
