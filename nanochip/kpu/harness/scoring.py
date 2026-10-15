"""Correctness judgement and synthesis-measurement helpers (no scoring).

This module contains NO benchmark scoring: the legacy C/P/E/A/F composite,
the primary gates and TOTAL have been removed. evaluate.py uses it for two
things only:

* Functional-correctness metric and PASS rule, teacher-forced on nano:
  for every emitted logits row p, cos_p = <chip_p, ref_p> / (|chip_p| *
  |ref_p|) computed in float64 (0 if either row is all-zero). Cosine is
  scale-invariant, so the chip may emit int32 logits in any per-row
  fixed-point scale it likes. Argmax agreement uses near-tie forgiveness
  (see ARGMAX_TIE_REL): the chip's pick counts as agreeing when its
  REFERENCE logit is within 1% of the row's logit std of the reference
  max — reference top-2 margins can be arbitrarily small, so exact-argmax
  matching would be ill-posed for any finite-precision implementation;
  forgiven picks are still forced to be reference-near-optimal, so wrong
  outputs never benefit.
      PASS per config: every run clean (status word, no timeout, no
      memory protocol errors) with min-row cos >= COS_PASS, AND argmax
      agreement >= ARGMAX_PASS over the positions of BOTH runs POOLED
      (pooling reduces small-sample noise at the pass bar).
* Synthesis measurement helpers: NAND2-equivalent (NE) cell accounting
  from the yosys flow (AND/NAND/OR/NOR=1, XOR/XNOR/MUX=2.5, NOT=0.5,
  DFF*=6, ANDNOT/ORNOT=1.5, memory bit=0.25), latch detection in the
  final netlist, and the lint warning threshold.

run_metrics additionally exposes the row_score/prec_score/run_score
fields consumed by harness/selfcheck.py's metric-discrimination check;
they are per-run diagnostics, not a benchmark score.
"""

import numpy as np


def clamp01(x):
    return max(0.0, min(1.0, x))


COS_PASS = 0.98
COS_RAMP_LO = 0.80
PREC_FULL = 2e-5        # 1-cos at which the precision term saturates
                        # (3 decades above the 0.02 of the pass bar);
                        # reachable: an int16 rendering of exact logits
                        # measures 1-cos ~ 1e-10, reference float32/BLAS
                        # wobble sits many decades lower still
ARGMAX_PASS = 0.99          # evaluated on positions pooled across both runs
ARGMAX_TIE_REL = 0.01   # near-tie forgiveness: chip's pick counts as agreeing
                        # if its REFERENCE logit is within 1% of the row's
                        # logit std of the reference max. Reference top-2
                        # margins can be arbitrarily small, so exact-argmax
                        # matching would be ill-posed for any finite-precision
                        # implementation; forgiven picks are still forced to
                        # be reference-near-optimal, so wrong outputs never
                        # benefit.
LINT_MAX_WARN = 40

CELL_NE = {"$_AND_": 1.0, "$_NAND_": 1.0, "$_OR_": 1.0, "$_NOR_": 1.0,
           "$_XOR_": 2.5, "$_XNOR_": 2.5, "$_MUX_": 2.5, "$_NMUX_": 2.5,
           "$_NOT_": 0.5, "$_BUF_": 0.0,
           "$_ANDNOT_": 1.5, "$_ORNOT_": 1.5,
           "$_AOI3_": 2.0, "$_OAI3_": 2.0, "$_AOI4_": 2.5, "$_OAI4_": 2.5}
DFF_NE = 6.0
MEMBIT_NE = 0.25


def row_cosines(chip_logits: np.ndarray, ref_logits: np.ndarray) -> np.ndarray:
    """Per-row cosine similarity, float64; all-zero rows give 0."""
    a = chip_logits.astype(np.float64)
    b = ref_logits.astype(np.float64)
    na = np.linalg.norm(a, axis=-1)
    nb = np.linalg.norm(b, axis=-1)
    dot = (a * b).sum(axis=-1)
    denom = na * nb
    return np.where(denom > 0, dot / np.maximum(denom, 1e-30), 0.0)


def run_metrics(chip_logits, chip_argmax, ref_logits, ref_argmax) -> dict:
    cos = row_cosines(chip_logits, ref_logits)
    base = np.clip((cos - COS_RAMP_LO) / (COS_PASS - COS_RAMP_LO), 0.0, 1.0)
    # precision above the bar: log-scaled in (1 - cos), 0 below the bar
    err = np.maximum(1.0 - cos, 1e-12)
    prec = np.where(cos >= COS_PASS,
                    np.clip(np.log10((1.0 - COS_PASS) / err) / 3.0, 0.0, 1.0),
                    0.0)
    ref = np.asarray(ref_logits, np.float64)
    ca = np.clip(np.asarray(chip_argmax, np.int64), 0, ref.shape[1] - 1)
    picked = ref[np.arange(ref.shape[0]), ca]
    tol = ARGMAX_TIE_REL * ref.std(axis=-1)
    agree_rows = picked >= ref.max(axis=-1) - tol
    agree = float(agree_rows.mean()) if len(cos) else 0.0
    n = len(cos)
    return {"cos_min": float(cos.min()) if n else 0.0,
            "cos_mean": float(cos.mean()) if n else 0.0,
            "row_score": float(base.mean()) if n else 0.0,
            "prec_score": float(prec.mean()) if n else 0.0,
            "argmax_agree": agree,
            "argmax_hits": int(agree_rows.sum()),
            "n_rows": int(n),
            "run_score": 0.55 * float(base.mean() if n else 0.0)
                         + 0.15 * float(prec.mean() if n else 0.0)
                         + 0.30 * agree}


def pooled_argmax(runs) -> float:
    """Argmax agreement over the positions of all runs pooled."""
    hits = sum(r.get("argmax_hits", 0) for r in runs)
    n = sum(r.get("n_rows", 0) for r in runs)
    return hits / n if n else 0.0


def config_pass(runs) -> bool:
    """PASS: every run clean with min-row cos >= COS_PASS; argmax agreement
    >= ARGMAX_PASS over the pooled positions of both runs."""
    if not runs:
        return False
    for r in runs:
        if not r.get("run_ok", r.get("status_ok")) \
                or r.get("cos_min", 0.0) < COS_PASS:
            return False
    return pooled_argmax(runs) >= ARGMAX_PASS


def ne_from_cells(cells: dict, mem_bits: int) -> float:
    ne = 0.0
    for cell, cnt in cells.items():
        if cell.startswith(("$_DFF", "$_SDFF", "$_ADFF", "$_DLATCH", "$_SR")):
            ne += DFF_NE * cnt
        else:
            ne += CELL_NE.get(cell, 1.0) * cnt
    return ne + MEMBIT_NE * mem_bits


LATCH_PREFIXES = ("$_DLATCH", "$_ALATCH", "$_SR",
                  "$dlatch", "$adlatch", "$dlatchsr", "$sr")


def latch_cells(cells: dict) -> int:
    """Count level-sensitive storage in the final netlist. Inferred latches
    in a single-clock synchronous design are an RTL bug (unintended
    combinational feedback / incomplete assignment), and industry flows
    treat them as zero-tolerance; the count is reported as a measurement."""
    return sum(cnt for cell, cnt in cells.items()
               if cell.startswith(LATCH_PREFIXES))


def lint_ok(errors: int, warnings: int) -> bool:
    return errors == 0 and warnings <= LINT_MAX_WARN
