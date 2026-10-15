# Lab 03 — Stage 3: Implement (`03-implement`)

**Title:** *The Multi-Fidelity Representation Sandwich (`float32` $\rightarrow$ `fxmodel.py` $\rightarrow$ `rtl/`)*
**Lifecycle Stage:** `3. Implement`
**Book Alignment:** Part II — *Loop Mechanics* (Chapter 4: *Data, Knowledge, and Representation*, Chapter 7: *Verification, Feedback, and Learning*)
**Target Artifact:** [`nanochip/kpu/reference/model.py`](../../kpu/reference/model.py), [`nanochip/kpu/rtl/selfmodel/fxmodel.py`](../../kpu/rtl/selfmodel/fxmodel.py), [`nanochip/kpu/rtl/msh_deq.v`](../../kpu/rtl/msh_deq.v), [`nanochip/kpu/rtl/msh_gemv.v`](../../kpu/rtl/msh_gemv.v), [`nanochip/kpu/reference/selftest.py`](../../kpu/reference/selftest.py), [`nanochip/kpu/harness/selfcheck.py`](../../kpu/harness/selfcheck.py)

---

## 1. What Breaks Without This Stage: Representation Collapse

Suppose an autonomous agent translates a 2-layer hybrid-attention MoE model (`reference/model.py` in `float32`) directly into 10,000 lines of Verilog (`rtl/msh_*.v`). After 20 minutes of compilation and simulation, the final output logits fail with `cos_min = 0.61` and `argmax_agree = 0.25`.

**Where is the bug?**
- Did the Q-format choice for the KDA recurrent state $S_t = \text{diag}(\alpha_t) S_{t-1} + \beta_t k_t (v_t - k_t S_{t-1})^T$ overflow 32 bits?
- Did the piece-wise linear LUT for $\text{rsqrt}(x)$ lack enough buckets for tiny KDA readout variances?
- Or did the Verilog state machine in `msh_gemv.v` drop the last beat of an AXI-like stream or misalign the zero-point subtraction?

When you jump directly from `float32` to Verilog RTL, **numeric approximation errors** and **hardware implementation bugs** are hopelessly entangled. Because `float32` and fixed-point arithmetic naturally diverge by small rounding amounts on every multiply-accumulate, you cannot use bit-exact (`==`) comparison against `float32`. Yet cosine similarity at the end of a 2-layer recurrent network is far too coarse to localize a 1-bit shift bug inside an RTL submodule!

---

## 2. How Kimi K3's `nano-kpu` Implements Stage 3: The Representation Sandwich

As documented in `docs/TASK_SPEC.md` (Deliverable 5) and `rtl/selfmodel/fxmodel.py`, Kimi K3 solves this by inserting a **bit-exact Python integer twin (`fxmodel.py`)** between the `float32` specification and the Verilog RTL:

```text
  [ reference/model.py ]          <-- Spec Boundary: Cosine >= 0.98, Argmax >= 0.99
     (Normative float32)              (Absorbs Q-format & LUT approximation choices)
             |
             v
  [ rtl/selfmodel/fxmodel.py ]    <-- Implementation Boundary: 100% Bit-Exact (0 ULP)
     (Exact int32/int64 Q4.26)        (Localizes any RTL shift/rounding/FSM bug on Row 0)
             |
             v
  [ rtl/msh_*.v (10 modules) ]
     (Synthesizable Verilog-2005)
```

### Key Mathematical Identities Shared Bit-for-Bit Between `fxmodel.py` and `rtl/`

1. **Embedding Dequantization (`fxmodel.py::emb_row` $\leftrightarrow$ `rtl/msh_deq.v`):**
   - Each byte holds two 4-bit nibbles `lo_j` and `hi_j`. With group scale `s` (`Q3.12`) and zero-point `z` (`uint4`):
     $$y[2j] = \text{sat32}\big((q_{2j} - z_{\lfloor 2j/g \rfloor}) \cdot s_{\lfloor 2j/g \rfloor} \ll 14\big) \quad \in \text{Q4.26}$$
2. **Zero-Point Folded INT4 GEMV (`fxmodel.py::gemv_acc` $\leftrightarrow$ `rtl/msh_gemv.v`):**
   - Instead of subtracting $z_{g,c}$ inside every MAC cell, `msh_gemv.v` accumulates raw unsigned nibbles $q_{k,c} \cdot x_k$ and folds the zero-point once per group:
     $$\sum_{k \in g} (q_{k,c} - z_{g,c}) x_k = \left(\sum_{k \in g} q_{k,c} x_k\right) - z_{g,c} \left(\sum_{k \in g} x_k\right)$$
3. **80-Bit Exact Sum-of-Squares RMSNorm (`fxmodel.py::_sumsq` $\leftrightarrow$ `rtl/msh_vec.v`):**
   - Splits `int32` $x = \text{hi} \cdot 2^{16} + \text{lo}$ so $\sum x_i^2$ up to $2^{71}$ is accumulated with zero precision loss before shifting into the `rsqrt` LUT domain.

---

## 3. Hands-On Exercises

### Exercise A — `--mode break` (Inject Shift & Zero-Point Bugs Across the Implementation Boundary)
```bash
python3 nanochip/labs/03-implement/lab.py --mode break
```
**What happens:** Simulates two subtle RTL datapath bugs against the golden fixed-point twin (`fxmodel.py`):
- **Bug 1 (`msh_deq` 1-bit shift error `<< 13` vs. `<< 14`):** Note that a uniform $2\times$ scale error on an isolated vector has `cosine == 1.000000` (because cosine is scale-invariant!), so a naive unit cosine check on `msh_deq` would **miss it completely**, only for it to corrupt the non-linear `RMSNorm(\epsilon)` and `KDA` recurrences downstream! The bit-exact implementation boundary (`fxmodel.py == rtl`) catches `msh_deq` at **Token 0, Element 0** in `< 5 ms`.
- **Bug 2 (`msh_gemv` missing zero-point fold `- z * sum(x)`):** Shows how omitting the `- z * xsum` term in the group fold destroys logit cosine (`cos_min` drops from `1.000000` to `< 0.05`) and is immediately pinpointed at Row 0 by `do_selfmodel()`.

### Exercise B — `--mode verify` (Run `selftest.py`, `selfcheck.py`, and Full Representation Sandwich Check)
```bash
python3 nanochip/labs/03-implement/lab.py --mode verify
```
**What happens:** Executes `nanochip/kpu/reference/selftest.py` and `nanochip/kpu/harness/selfcheck.py`, then runs `FxModel` on the public `nano` image (`seq_len=48`) and compares it against the `float32` golden (`cos_min = 0.9999999926`, `48/48` argmax hits) and verifies 0-ULP bit-exactness.

---

## 4. Socratic Reflection Questions

1. **Why Cosine Alone Fails at Submodule Boundaries (Ch. 4 & Ch. 7):** Since cosine similarity is scale-invariant ($\cos(c \cdot \mathbf{y}, \mathbf{y}) = 1$ for any $c > 0$), why does a 1-bit left-shift bug (`<< 13` instead of `<< 14`) in `msh_deq.v` pass a cosine check on the embedding output, yet cause catastrophic divergence in Layer 0's KDA recurrence? How does the bit-exact `fxmodel.py` boundary eliminate this blind spot?
2. **Hardware Cost of the Zero-Point Fold Identity (Ch. 4):** In `msh_gemv.v`, why does Kimi K3 compute $\sum q_k x_k - z \sum x_k$ at the end of a 128-element group instead of subtracting $q_k - z$ before each multiplier? What is the bit-width and gate-count difference across 16 parallel columns?
3. **80-Bit Sum-of-Squares in `msh_vec.v` (Ch. 4):** Why did Kimi K3 use an exact 80-bit accumulator (`hi*2^16 + lo` split in `fxmodel.py::_sumsq`) for `RMSNorm` and `L2Norm` instead of shifting `x` right before squaring? Hint: inspect the comment in `fxmodel.py` line 279 about KDA readout signal magnitudes.
