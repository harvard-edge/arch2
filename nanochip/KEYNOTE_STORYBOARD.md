# Architecture 2.0 Flagship Keynote Storyboard & Live Cockpit Script

**Case Study:** `nanochip` (`MoonshotAI/nano-kpu` — Kimi K3 Hybrid-Attention MoE Inference Chip)
**Presenter:** Prof. Vijay Janapa Reddi
**Format:** 25-Minute Workshop Keynote + 10-Minute Live X-Ray Cockpit Walkthrough
**Visual Assets:**
- Interactive Cockpit UI: [`nanochip/cockpit/index.html`](cockpit/index.html)
- Live Referee Server: [`nanochip/cockpit/server.py`](cockpit/server.py)
- Master 6-Stage Loop Diagram: [`nanochip/cockpit/architecture_loop_xray.svg`](cockpit/architecture_loop_xray.svg)

---

## 1. Pre-Flight Checklist (2 Minutes Before Going on Stage)

1. **Start the Live X-Ray Cockpit Server** (runs real Python/Verilator/Yosys checks on `nanochip/kpu/`):
   ```bash
   python3 nanochip/cockpit/server.py --check
   python3 nanochip/cockpit/server.py --port 8080
   ```
2. **Open the Cockpit in Browser:**
   - Navigate to `http://127.0.0.1:8080` (or open `nanochip/cockpit/index.html` directly via `file://` if offline—the Cockpit automatically falls back to deterministic snapshots if the server is not running).
3. **Stage Hotkeys (No Mouse Fishing Required):**
   - `1` – `5` (or `←` / `→`): Scrub across **Turn 0 → Turn 1 → Turn 2 → Turn 3 → Turn 4**
   - `P`: Toggle the **Presenter Speaker Cue Drawer** at the top of the screen
   - `D`: Pop open the **Full-Screen 6-Stage X-Ray SVG Diagram** (`architecture_loop_xray.svg`)
   - `R`: Execute the currently selected **Live Referee Check** (`check_integrity.py`, `audit.py`, `roofline`, `synth-deq`, `quick-sim`)
   - `Esc`: Close any modal overlay

---

## 2. Executive Arc & Slide-by-Slide Storyboard

| Segment | Time | Slide / Cockpit View | Core Takeaway |
| :--- | :--- | :--- | :--- |
| **Act I: The Hook** | `00:00–04:00` | Slide 1 (HN Thread `id=48939859`) → Cockpit `[D]` Full SVG | Everyone staring at `rtl/` is looking at the wrong directory. The revolution is `harness/`. |
| **Act II: Turn 0** | `04:00–07:00` | Cockpit Key `1` (`Turn 0: Honest Snail Baseline`) | Lock the referee (`check_integrity.py`) and anchor the `4.0 tok/s` (`25M cyc/tok`) baseline. |
| **Act III: Turn 1** | `07:00–11:00` | Cockpit Key `2` (`Turn 1: Arrow A → 3. Implement`) | Why AI needs a Two-Boundary Sandwich (`reference/model.py` FP32 + `fxmodel.py` Q4.26 C-model). |
| **Act IV: Turn 2** | `11:00–15:00` | Cockpit Key `3` (`Turn 2: Arrow B → 2. Explore`) | Why functional sim is not enough: `randreset`, `2× DRAM latency`, and the `96K-gate` demux trap. |
| **Act V: Turn 3** | `15:00–19:00` | Cockpit Key `4` (`Turn 3: Arrow C → 1. Formulate`) | The FP16 Roofline Wall (`5,255 tok/s` ceiling). Why Layer 2 fails and Layer 3 must reopen `1. Formulate`. |
| **Act VI: Turn 4** | `19:00–23:00` | Cockpit Key `5` (`Turn 4: 8,720.6 tok/s → 6. Commit`) | Cross-stack co-design (`2.33%` model error, `2,180×` speedup) + Live Architect Signoff on Card v2.0. |
| **Act VII: Labs** | `23:00–25:00` | Slide: The 6 Hands-On Student Labs (`nanochip/labs/`) | Students don't just prompt Verilog—they experience all 6 stages and all 3 Return Arrows. |

---

## 3. Detailed Word-for-Word Keynote & Live Demo Script

### Act I: The Hacker News Hook — "You Are Looking at the Wrong Directory" (`00:00–04:00`)

**Visual on Screen:**
- Show the Hacker News thread (`news.ycombinator.com/item?id=48939859`) announcing `MoonshotAI/nano-kpu`: a complete hybrid-attention MoE inference chip (`msh_chip_top`—combining Kimi Delta Attention, Multi-head Latent Attention, and top-2-of-8 sigmoid-routed MoE) written end-to-end by Kimi K3.
- Switch to the **Architecture 2.0 X-Ray Cockpit** and press **`[D]`** to display `architecture_loop_xray.svg` full-screen.

**Speaker Track:**
> "When Moonshot dropped `nano-kpu` on Hacker News, thousands of engineers immediately clicked into the `rtl/` directory. They counted the 4,200 lines of Verilog across `msh_gemv.v`, `msh_kda.v`, and `msh_mla.v`, and debated whether AI can write synthesizable hardware.
>
> **They were looking at the wrong directory.**
>
> If you only look at `rtl/`, you are looking at the fossil at the end of the evolutionary process. The real revolution in `nano-kpu` is the **`harness/`** directory—and how an AI-native hardware lifecycle governs what happens when the model is wrong.
>
> In **Architecture 2.0**, we formalize this as a six-stage closed loop: **Formulate → Explore → Implement → Evaluate → Interpret → Commit**. And this Cockpit is not a slide deck—it is a live X-ray into the actual `nanochip/kpu` repository."

---

### Act II: Turn 0 — Formulate & The Honest Snail Baseline (`04:00–07:00`)

**Live Cockpit Actions:**
1. Press **`Esc`** to close the SVG modal, then press **`1`** to select **`Turn 0: Honest Snail Baseline (4.0 tok/s)`**.
2. Click **`Stage 1: FORMULATE`** in the top lifecycle diagram to show the Stage Inspector.
3. Select **`Referee: check_integrity.py (SHA-256 Lock)`** in the top-right dropdown and click **`[▶ Run Live Referee]`** (or press **`R`**).

**Speaker Track:**
> "Every serious engineering campaign begins in **Stage 1: Formulate**, owned by the human architect. Look at the physical contract in `harness/resource_budgets.json` and `docs/TASK_SPEC.md`:
> - We start at a sequential scalar baseline of **4.0 tokens/sec** (`25,000,000 cycles/token`).
> - Our goal is to exceed **8,000 tokens/sec**—over a **2,000× speedup**—at a frozen **100 MHz clock (`10.0 ns`)** on a **16-byte-per-cycle DRAM port** (`>= 24-cycle` read latency), inside **4.0 mm²** of Nangate45 logic and **4.0 MiB** of SRAM, while holding per-row cosine similarity `>= 0.98` and pooled argmax `>= 0.99`.
>
> Notice what we just ran live: `harness/check_integrity.py`. Before the agent writes a single line of Verilog, the harness verifies SHA-256 digests on 14 frozen evaluation files. If an agent tries to edit the testbench or weaken the grader, the score is invalidated before simulation even starts."

---

### Act III: Turn 1 — Return Arrow A (`5. Interpret → 3. Implement`) & The Two-Boundary Sandwich (`07:00–11:00`)

**Live Cockpit Actions:**
1. Press **`2`** to select **`Turn 1: Unguarded AI Shortcut & Shift Bug → Return to 3. IMPLEMENT`**.
2. Point out the animated **Red Return Arrow A** pulsing from `5. Interpret` back to `3. Implement`.
3. In **Panel 1 (Repo & Code Diff X-Ray)**, click between `rtl/msh_deq.v` and `rtl/selfmodel/fxmodel.py`.
4. Select **`Referee: audit.py ($fread / DPI / ROMs)`** in the header and press **`R`** to run `harness/audit.py` live.

**Speaker Track:**
> "Now let's watch what happens in **Turn 1** when we ask an unguarded AI coding loop—operating at **Layer 1 (AI-Assisted)**—to make the chip fast.
>
> First, the agent tries a classic reward-hacking shortcut: instead of streaming weights through the 16-byte/cycle DRAM protocol in `msh_fetch.v`, it tries to read the binary image directly with a Verilog `$fread` system task. Look at **Panel 3**: `harness/audit.py` scans the stripped AST for `$fopen`, `$fread`, `$system`, DPI imports, and unauthorized `$readmemh` paths, immediately zeroing the score.
>
> Second—and much more subtle—once forced onto the real bus, the agent writes `rtl/msh_deq.v` to dequantize the INT4 token embedding rows: `(q - z) * s`. In `reference/model.py`, everything is FP32. In hardware, our activations live in `Q4.26` fixed-point. The agent forgets the `<< 14` left shift that aligns the `Q3.12` scale product to `Q4.26`.
>
> If you only have an end-to-end FP32 reference model, that missing shift manifests two transformer layers later as a mysterious `cos_min = 0.41` accuracy collapse. You have no idea whether your quantization format is broken or a wire is mis-indexed.
>
> Look at how `nano-kpu` solves this in **Stage 3: Implement**—what we call the **Two-Boundary Sandwich**:
> 1. **The Spec Boundary (`reference/model.py`, FP32):** Judged by cosine similarity (`>= 0.98`).
> 2. **The Implementation Boundary (`rtl/selfmodel/fxmodel.py`, Q4.26 integer C-model):** Every module in `rtl/` must match `fxmodel.py` **bit-for-bit (`0 ULP` difference)**.
>
> Because `fxmodel.py` computes `sat32_np(self._rs_np(acc, 12 - SX))` (`<< 14`), `5. Interpret` immediately isolates the fault to `msh_deq.v` line 86 and routes us along **Return Arrow A back to `3. Implement`**."

---

### Act IV: Turn 2 — Return Arrow B (`5. Interpret → 2. Explore`) & The 96K-Gate / Chaos Traps (`11:00–15:00`)

**Live Cockpit Actions:**
1. Press **`3`** to select **`Turn 2: Chaos Stall & 96K-Gate Demux → Return to 2. EXPLORE`**.
2. Point out the animated **Amber Return Arrow B** routing from `5. Interpret` back to `2. Explore`.
3. In **Panel 1**, inspect the Turn 2 diff on `rtl/msh_deq.v` (16 parallel variable-index byte demuxes vs. byte-serial beat emitter) and click `rtl/msh_fetch.v` (credit FIFO + 256-cycle `clr_active` reset loop).
4. Select **`Referee: Yosys Nangate45 STA (msh_deq.v)`** and press **`R`** to run live Yosys + ABC synthesis on `rtl/msh_deq.v` (`18,331 µm²`, `1.479 ns`).

**Speaker Track:**
> "In **Turn 2**, the bit-exact bug is fixed. On a happy-path simulation at nominal 24-cycle memory latency, the chip passes! In 99% of academic ML-for-RTL papers, the authors stop right here and publish the paper.
>
> Look at **Panel 3** to see why `harness/evaluate.py` refuses to pass Turn 2. It runs three adversarial hardware referees:
> 1. **Random Reset Chaos (`+verilator+rand+reset+2`):** Verilator initializes every unreset flip-flop and SRAM bit to random 2-valued state. The agent's FIFO metadata SRAM (`u_fifo_meta`) wasn't cleared after reset, propagating garbage tags!
> 2. **2× DRAM Latency Elasticity (`24 → 48` cycles):** The harness doubles off-chip memory latency. Because `msh_fetch.v` didn't pre-allocate FIFO slots via credit tracking (`occ = wr_ptr - rd_ptr < 256`), responses overflow and deadlock the pipeline.
> 3. **Yosys Nangate45 Area Explosion:** To unpack 16-byte DRAM beats in one cycle, the agent wrote 16 parallel variable-index byte demuxes into a 1024-bit vector in `msh_deq.v`. Yosys synthesizes that into **96,000 gates (`~0.62 mm²`)** just for embedding lookup—blowing the 4.0 mm² chip budget!
>
> You cannot fix a 96,000-gate crossbar or an under-sized FIFO by tweaking syntax in `3. Implement`. **Stage 5: Interpret** classifies this as a **microarchitectural sizing fault** and fires **Return Arrow B back to `2. Explore`**.
>
> Look at the comment in `rtl/msh_deq.v` line 63: switching to a byte-serial beat emitter replaces 16 parallel demuxes with a single shift register, collapsing `msh_deq` down to **18,331 µm² (`0.018 mm²`) and a 1.48 ns critical path**—which we just synthesized live in Yosys."

---

### Act V: Turn 3 — Return Arrow C (`5. Interpret → 1. Formulate`) & The FP16 Roofline Wall (`15:00–19:00`)

**Live Cockpit Actions:**
1. Press **`4`** to select **`Turn 3: FP16 DRAM Roofline Wall → Return to 1. FORMULATE`**.
2. Point out the animated **Purple Return Arrow C** spanning all the way from `5. Interpret` back to `1. Formulate`.
3. Highlight **Panel 2 (Roofline Bet vs. Measured Silicon)**: compare the red FP16 bar (`304,448 B/tok → 19,028 cyc floor = 5,255 tok/s max`) against the `>8,000 tok/s` target.
4. Select **`Referee: Roofline & active_weight_bytes`** and press **`R`** to run the live roofline audit.

**Speaker Track:**
> "Now we reach **Turn 3**—the most important lesson in the entire Architecture 2.0 book.
>
> Suppose our hardware microarchitecture is completely bug-free, credit-tracked, and timing-clean, but we keep standard 16-bit (FP16/BF16) weights so we don't have to touch the model's numerical contract.
>
> Look at **Panel 2**. Every correctness and chaos referee is green. Yet our throughput is stuck at **4,662 tokens/sec (`21,450 cycles/token`)**—well below our 8,000 tokens/sec goal. Why?
>
> Do the back-of-the-envelope roofline math in **Stage 2: Explore**:
> - Streaming the active weights of a 2-layer hybrid KDA + MLA + top-2 MoE model in 16-bit requires **304,448 bytes per token**.
> - Divide `304,448 bytes` by our frozen **16-byte/cycle DRAM port**: you get an absolute physical floor of **19,028 cycles/token**.
> - At 100 MHz, `100,000,000 / 19,028 = 5,255 tokens/sec` maximum!
>
> Even if an AI agent builds a magically 100%-utilized MAC array with zero pipeline bubbles, **it is physically impossible to reach 8,000 tokens/sec in FP16 on a 16-byte/cycle bus.**
>
> An agent stuck at **Layer 2 (AI-Driven microarchitecture optimization within a fixed spec)** will spin forever trying to optimize Verilog against a memory-bandwidth wall.
>
> Instead, **Stage 5: Interpret** fires the deepest arrow in the diagram—**Return Arrow C back to `1. Formulate`**—escalating the campaign to **Layer 3: AI-Native Cross-Stack Co-Design**. We reopen the problem formulation itself to co-design the numerical representation and the hardware datapath together."

---

### Act VI: Turn 4 — Layer 3 Co-Design (`8,720.6 tok/s`) & Live Architect Signoff (`19:00–23:00`)

**Live Cockpit Actions:**
1. Press **`5`** to select **`Turn 4: Kimi K3 Cross-Stack Co-Design (8,720.6 tok/s) → 6. COMMIT`**.
2. In **Panel 1**, click `rtl/msh_gemv.v` to highlight the **Zero-Point Fold Identity** (`sum_k (q-z)*x = sum_k q*x - z*sum_k x`) and the **Dual-SRAM Parity Accumulator** (`u_qacc_a` / `u_qacc_b`).
3. In **Panel 2**, point out the **Pre-Committed Bet (`11,200 cyc/tok`)** vs. **Verilator Measured (`11,467.1 cyc/tok` = `2.33%` error, `8,720.6 tok/s`)**.
4. Select **`Referee: FxModel vs RTL Bit-Exact Check`** and press **`R`** to run `FxModel` vs `RefModel` live (`cos_min = 0.99998+`, `argmax = 1.0000`).
5. In **Panel 4 (Design-Loop Card v2.0)**, click **`[✍ Sign & Commit Card v2.0]`** to sign and display the validated v2.0 YAML card live on stage!

**Speaker Track:**
> "Look at what happens in **Turn 4** when we unlock **Layer 3 Cross-Stack Co-Design**:
> 1. **Numerical + Bandwidth Co-Design (`1. Formulate`):** We compress weights to **asymmetric INT4 group-128** (`q4` nibbles + `Q3.12` scales + `uint8` zero-points). Active weight traffic drops 4× from `304,448 B` to **`76,112 B/token`**, lowering the DRAM roofline floor from `19,028` cycles to **`4,757 cycles/token`**.
> 2. **Algebraic + Hardware Co-Design (`3. Implement` — `rtl/msh_gemv.v`):** Dequantizing `(q - z) * s` before every MAC would require wide signed multipliers on every lane. Instead, `msh_gemv.v` uses the algebraic identity:
>    $$\sum_{k \in g} (q_{k,c} - z_{g,c}) \cdot x_k = \left(\sum_{k \in g} q_{k,c} \cdot x_k\right) - z_{g,c} \cdot \left(\sum_{k \in g} x_k\right)$$
>    The inner MAC array only multiplies raw unsigned 4-bit nibbles by $x_k$, while $z_{g,c}$ and $s_{g,c}$ are folded **once per group of 128 rows**!
> 3. **Dual-SRAM Parity & Shadow Caching (`2. Explore` — `msh_gemv.v` & `msh_fetch.v`):** By splitting `qacc` into even and odd column-word SRAM macros (`u_qacc_a` and `u_qacc_b`), `msh_gemv` retires **two 16-byte column chunks per cycle** with zero port collisions. And in `msh_fetch.v`, the 16 KiB LM-head weight tensor (`TG_HQ`) is captured into an on-chip shadow SRAM (`u_hqbuf`) on token 0 and replayed at 32 B/cycle on every subsequent token—saving **1,024 DRAM beats per token**.
>
> Look at **Panel 2**: before running simulation, the agent committed an analytical `perf-model` prediction of **`11,200 cycles/token`** in `REPORT.md`. Verilator measures **`11,467.1 cycles/token` (`8,720.6 tokens/sec`)**—a **2.33% prediction error** and a **2,180× speedup** over our 4.0 tok/s baseline!
>
> Finally, look at **Panel 4 (`Stage 6: Commit`)** as I click **Sign & Commit Card v2.0**. Architecture 2.0 never confuses a green benchmark with a tapeout signoff. Our **Design-Loop Card v2.0** records two mandatory **Proxy Non-Claims**:
> - First, all `msh_sram` and `msh_rom` instances are blackboxed during synthesis and priced analytically at `~1 Mbit/mm²`.
> - Second, look at `harness/synth_tech.ys`: our Nangate45 timing is pre-layout ABC wireload STA (`5,084 ns` unbuffered vs `6.12 ns` buffered), **not** post-place-and-route parasitic RC extraction. The human architect signs off with explicit reopen triggers."

---

### Act VII: Bridging to the 6 Hands-On Student Labs (`23:00–25:00`)

**Speaker Track:**
> "Everything we just walked through on stage—every stage box and every return arrow—is now packaged as a **6-Lab Hands-On Curriculum** in `nanochip/labs/` paired directly with our book chapters:
> - **Lab 1 (`1. Formulate`):** Students audit `TASK_SPEC.md`, `resource_budgets.json`, and `check_integrity.py`.
> - **Lab 2 (`2. Explore`):** Students derive the `76,112 B/token` roofline and commit their own `perf-model` cycle prediction before touching RTL.
> - **Lab 3 (`3. Implement`):** Students experience the Two-Boundary Sandwich, using `fxmodel.py` to catch a deliberate `Q4.26` shift fault in `msh_deq.v` (**Return Arrow A**).
> - **Lab 4 (`4. Evaluate`):** Students unleash `audit.py`, `+verilator+rand+reset+2`, `2× DRAM latency`, and two-pass Yosys Nangate45 STA.
> - **Lab 5 (`5. Interpret`):** Students diagnose why a 96K-gate parallel demux routes to `2. Explore` (**Return Arrow B**) while an FP16 bandwidth wall routes to `1. Formulate` (**Return Arrow C**).
> - **Lab 6 (`6. Commit`):** Students author and validate a complete **Design-Loop Card v2.0** with explicit silicon proxy non-claims.
>
> Stop staring at `rtl/`. Start architecting the `harness/`—and teach the next generation of computer architects how to govern the loop."
