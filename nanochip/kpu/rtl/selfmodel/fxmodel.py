"""Fixed-point C-model of the Moonshot hybrid chip (normative for the RTL).

Reads a memory image (harness/memmap.py format), computes per-position
int32 logits with EXACT integer arithmetic — every op here is mirrored
bit-exactly by the Verilog RTL. Correctness vs the float32 reference is
judged by cosine; the RTL must match THIS model exactly.

Number formats (v2 — see REPORT.md for rationale):
  X    general activations (residual stream, normed vectors, GEMV I/O)
       int32, Q4.26  (sx = 26, range +/-32)
  ACT  SwiGLU intermediate                     int32, Q5.26
  QK   L2-normalized KDA q/k                   int32, Q2.26
  S    KDA state                               int32, Q4.27 (saturating)
  O    KDA pre-onorm readout                   int32, Q2.26
  weights  (q-z) int8 [-15,15], scales int16 Q3.12  -> GEMV acc int64
  sigmoid/beta/gates Q0.22, alpha Q0.22, softmax exp Q0.16
  probs divided via reciprocal LUT at 2^30
  logits out: int32 = sat32((acc + 2^9) >> 10)

GEMV (fused dequant, exact integer):
  acc[c] = sum_g s[g,c] * sum_{k in group g} (q[k,c] - z[g,c]) * x[k]
  y[c]   = sat32((acc + 2^(R-1)) >> R)     R = sx + 12 - sy
"""

import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

from reference.config import ModelConfig, RMS_EPS, L2_EPS, ROUTER_SCALE  # noqa: E402
from reference.gen_weights import tensor_list                            # noqa: E402
from rtl.selfmodel import fxluts                                          # noqa: E402

# ---------------------------------------------------------------- constants

SX = 26                      # general activation scale (Q4.26)
SA = 26                      # swiglu act scale (Q5.26, range bit extra)
SQK = 26                     # L2-normed q/k scale (Q2.26)
SS = 27                      # KDA state scale (Q4.27)
SO = 26                      # KDA readout scale (Q2.26)
SIG = 26                     # sigmoid-family output scale (Q0.26)
ALPHA = 26                   # alpha output scale (Q0.26)
EXP = 26                     # softmax exp output scale (Q0.26)
R_HEAD = 10                  # logits = acc >> R_HEAD
I32MIN, I32MAX = -2 ** 31, 2 ** 31 - 1
I64MIN, I64MAX = -2 ** 63, 2 ** 63 - 1

ROUTER_Q26 = int(round(ROUTER_SCALE * 2 ** SIG))     # 2.828 at Q0.26


def sat32(v):
    return I32MIN if v < I32MIN else (I32MAX if v > I32MAX else int(v))


def rshift(v, r):
    """Arithmetic right shift with round-half-up (add 2^(r-1)); r<0 shifts left."""
    if r <= 0:
        return v << (-r)
    return (v + (1 << (r - 1))) >> r


def inv_sqrt_q16(d):
    return int(round(2 ** 16 / np.sqrt(d)))


def sat32_np(v):
    return np.clip(v, I32MIN, I32MAX).astype(np.int32)


# ---------------------------------------------------------------- the model

class FxModel:
    def __init__(self, image: bytes, rom_dir=None, dump=None):
        self.img = image
        self.dump = dump                    # optional dict for intermediates
        rom_dir = rom_dir or os.path.join(ROOT, "rtl", "roms")
        L = lambda nm: np.asarray(fxluts.load_hex(
            os.path.join(rom_dir, nm + ".hex")), np.int64)
        Ld = lambda nm: np.asarray(fxluts.load_hex_s(
            os.path.join(rom_dir, nm + "_d.hex"),
            fxluts.DELTA_WIDTH[nm]), np.int64)
        self.lut_sig, self.lut_sig_d = L("sigmoid"), Ld("sigmoid")
        self.lut_alpha, self.lut_alpha_d = L("alpha"), Ld("alpha")
        self.lut_exp, self.lut_exp_d = L("expneg"), Ld("expneg")
        self.lut_rsq, self.lut_rsq_d = L("rsqrt"), Ld("rsqrt")
        self.lut_rec, self.lut_rec_d = L("recip"), Ld("recip")
        self._parse_header()
        self._load_tensors()
        self.reset()

    # -- image parsing (mirrors memmap.build_image) --

    def _parse_header(self):
        w = struct.unpack_from("<64I", self.img, 0)
        assert w[0] == 0x4B444143, hex(w[0])
        (self.n_layers, self.d_model, self.n_heads, self.mla_dk, self.mla_dr,
         self.mla_dv, self.mla_dc, self.kda_heads, self.kda_dim,
         self.conv_kernel, self.n_experts, self.top_k, self.n_shared,
         self.d_ff, self.attn_res_block, self.vocab, self.max_seq,
         self.seq_len, self.group_size) = w[2:21]
        self.lt_bitmap = w[21]
        self.n_tensors = w[22]
        (self.desc_addr, self.tokens_addr, self.logits_addr, self.argmax_addr,
         self.status_addr, self.scratch_addr, self.scratch_bytes, self.stride,
         self.n_positions) = w[23:32]
        self.layer_types = ["F" if (self.lt_bitmap >> i) & 1 else "L"
                            for i in range(self.n_layers)]
        self.cfg = ModelConfig(
            name="img", d_model=self.d_model, n_layers=self.n_layers,
            layer_pattern="".join(self.layer_types),
            n_heads=self.n_heads, mla_dk=self.mla_dk, mla_dr=self.mla_dr,
            mla_dv=self.mla_dv, mla_dc=self.mla_dc,
            kda_heads=self.kda_heads, kda_dim=self.kda_dim,
            conv_kernel=self.conv_kernel, n_experts=self.n_experts,
            top_k=self.top_k, n_shared=self.n_shared, d_ff=self.d_ff,
            attn_res_block=self.attn_res_block, vocab=self.vocab,
            max_seq=self.max_seq, group_size=self.group_size,
            seq_lens=(self.seq_len,), timeout_cycles=0)
        self.P = self.kda_heads * self.kda_dim
        self.dqk = self.mla_dk + self.mla_dr
        self.c_att = inv_sqrt_q16(self.dqk)
        self.c_dh = inv_sqrt_q16(self.kda_dim)
        self.inv_d24 = {}                   # d -> round(2^24/d) for variance
        for d in (self.d_model, self.kda_dim, self.dqk, self.mla_dv,
                  self.mla_dc, self.d_ff, self.n_experts, self.P):
            self.inv_d24[d] = int(round(2 ** 24 / d))

    def _load_tensors(self):
        """Walk the descriptor table in canonical tensor_list order; build
        qz int16 [K,N] (= q - z) + s int16 [ng,N] per matmul, raw int16 for
        params."""
        names = [nm for nm, _, _ in tensor_list(self.cfg)]
        shapes = {nm: sh for nm, sh, _ in tensor_list(self.cfg)}
        assert len(names) == self.n_tensors, (len(names), self.n_tensors)
        self.qz, self.scl, self.param = {}, {}, {}
        self._k_of = {}
        self.emb_q = self.emb_s = self.emb_z = None
        for i, nm in enumerate(names):
            _, addr, nbytes, aux = struct.unpack_from(
                "<IIII", self.img, self.desc_addr + 16 * i)
            data = self.img[addr:addr + nbytes]
            if nm == "emb.q":
                self.emb_q = np.frombuffer(data, np.uint8).reshape(
                    self.vocab, self.d_model // 2)
            elif nm == "emb.s":
                ng = (self.d_model + min(self.group_size, self.d_model) - 1) \
                    // min(self.group_size, self.d_model)
                self.emb_s = np.frombuffer(data, "<i2").reshape(
                    self.vocab, ng).astype(np.int64)
            elif nm == "emb.z":
                self.emb_z = np.frombuffer(data, np.uint8).reshape(
                    self.vocab, -1).astype(np.int64)
            elif nm.endswith(".q"):
                k, n = 2 * shapes[nm][0], shapes[nm][1]
                self._k_of[nm[:-2]] = k
                pk = np.frombuffer(data, np.uint8).reshape(k // 2, n)
                q = np.empty((k, n), np.int8)
                q[0::2] = (pk & 0x0F).astype(np.int8)
                q[1::2] = (pk >> 4).astype(np.int8)
                self.qz[nm[:-2]] = q.astype(np.int16)
            elif nm.endswith(".s"):
                k, n = self._k_of[nm[:-2]], shapes[nm][1]
                ng = (k + min(self.group_size, k) - 1) // min(self.group_size, k)
                self.scl[nm[:-2]] = np.frombuffer(data, "<i2").reshape(
                    ng, n).astype(np.int64)
            elif nm.endswith(".z"):
                k, n = self._k_of[nm[:-2]], shapes[nm][1]
                ng = (k + min(self.group_size, k) - 1) // min(self.group_size, k)
                z = np.frombuffer(data, np.uint8).reshape(ng, n).astype(np.int16)
                gsz = min(self.group_size, k)
                gi = np.arange(k) // gsz
                self.qz[nm[:-2]] = (self.qz[nm[:-2]] - z[gi]).astype(np.int16)
            else:
                self.param[nm] = np.frombuffer(data, "<i2").reshape(
                    shapes[nm]).astype(np.int64)

    # -- state --

    def reset(self):
        self.pos = 0
        self.kda_S = {}                     # li -> int64 [H, dh, dh] (Q4.27)
        self.conv_hist = {}                 # li -> int32 [3, K-1, P] (Q4.26)
        self.kv_k, self.kv_v = {}, {}       # li -> int32 [T, H, *] (Q4.26)
        for li, t in enumerate(self.layer_types):
            if t == "F":
                self.kv_k[li] = np.zeros(
                    (self.max_seq, self.n_heads, self.dqk), np.int32)
                self.kv_v[li] = np.zeros(
                    (self.max_seq, self.n_heads, self.mla_dv), np.int32)
            else:
                self.kda_S[li] = np.zeros(
                    (self.kda_heads, self.kda_dim, self.kda_dim), np.int64)
                self.conv_hist[li] = np.zeros(
                    (3, self.conv_kernel - 1, self.P), np.int32)

    # -- primitive ops (all exact integer) --

    def _rs_np(self, v, r):
        return (v + (1 << (r - 1))) >> r if r > 0 else v << (-r)

    def gemv_acc(self, nm, x):
        """acc int64 [N] = sum_g s[g] * (x @ qz_g). Exact: all intermediate
        integers < 2^53 so float64 BLAS is bit-exact."""
        qz, s = self.qz[nm], self.scl[nm]
        k, n = qz.shape
        gsz = min(self.group_size, k)
        xf = x.astype(np.float64)
        acc = np.zeros(n, np.float64)
        for g0 in range(0, k, gsz):
            acc += s[g0 // gsz] * (
                xf[g0:g0 + gsz] @ qz[g0:g0 + gsz].astype(np.float64))
        assert np.all(np.abs(acc) < 2 ** 53), nm
        return acc.astype(np.int64)

    def gemv(self, nm, x, sx=SX, sy=SX):
        """int32 [N] at scale 2^sy from int32 x at scale 2^sx."""
        acc = self.gemv_acc(nm, x)
        return sat32_np(self._rs_np(acc, sx + 12 - sy))

    # LUT lookups with linear interpolation (mirror RTL exactly).
    # Bucket width 2^-8 float (2^(sx-8) codes); the interpolation fraction
    # uses ALL sub-bucket bits: y = t[i] + (d[i]*frac) >> (sx-8).
    def _lut_interp(self, x_int, sx, n_buckets, offset, t, d):
        sh = sx - 8
        b = x_int >> sh
        idx = np.clip(b + offset, 0, n_buckets)
        frac = x_int - (b << sh)
        return t[idx] + (((d[idx] * frac) + (1 << (sh - 1))) >> sh)

    def sig(self, x, sx=26):
        """sigmoid of x at scale 2^sx -> Q0.22 (interpolated)."""
        x = np.asarray(x, np.int64)
        return self._lut_interp(x, sx, fxluts.SIG_N, fxluts.SIG_N // 2,
                                self.lut_sig, self.lut_sig_d)

    def alpha_of(self, x, sx=26):
        x = np.asarray(x, np.int64)
        return self._lut_interp(x, sx, fxluts.SIG_N, fxluts.SIG_N // 2,
                                self.lut_alpha, self.lut_alpha_d)

    def exp_of(self, x, sx=26):
        """exp of x<=0 at scale 2^sx -> Q0.18 (interpolated)."""
        x = np.asarray(x, np.int64)
        return self._lut_interp(x, sx, fxluts.EXP_N, fxluts.EXP_N,
                                self.lut_exp, self.lut_exp_d)

    def rsqrt(self, v, domain_frac):
        """v: positive int at scale 2^domain_frac. Returns r = rsqrt(v_float)
        at Q24 (int)."""
        r = fxluts.rsqrt_eval_i(self.lut_rsq, self.lut_rsq_d, int(v),
                                24 + domain_frac // 2)
        return r

    def recip(self, s):
        """s: positive int (any scale). Returns round(2^46 / s)."""
        return fxluts.recip_eval_i(self.lut_rec, self.lut_rec_d, int(s), 46)

    @staticmethod
    def _sumsq(x):
        """Exact sum of squares for int32-range values (results up to 2^71).
        Split x = hi*2^16 + lo (lo >= 0) so every partial sum fits int64;
        combine as Python ints."""
        x = np.asarray(x, np.int64)
        hi = x >> 16
        lo = x - (hi << 16)
        return ((int((hi * hi).sum()) << 32)
                + (int((hi * lo).sum()) << 17)
                + int((lo * lo).sum()))

    def rmsnorm(self, x, w_off):
        """x int32 array at scale 2^26, w_off int16 Q2.13. Returns int32 at
        2^26: y = x * rsqrt(mean(x^2)+eps) * (1+w). Variance from the EXACT
        sum of squares (80-bit accumulator in RTL) shifted to the 2^32
        domain — precise even for tiny signals (KDA readout)."""
        x = np.asarray(x, np.int64)
        d = x.shape[-1]
        ss = self._sumsq(x)                                 # exact, scale 2^52
        v = self._rs_np(ss * self.inv_d24[d], 44)           # mean(x^2) @2^32
        eps = int(round(RMS_EPS * 2 ** 32))                 # 42950
        r = fxluts.rsqrt_eval_i(self.lut_rsq, self.lut_rsq_d,
                                int(v) + eps, 24 + 16)      # true rsqrt @Q24
        g = 8192 + np.asarray(w_off, np.int64)              # Q2.13
        rg = (r * g + (1 << 12)) >> 13                      # Q24
        y = ((self._rs_np(x, 4) * rg) + (1 << 19)) >> 20     # back to 2^26
        return sat32_np(y)

    def l2norm(self, x):
        """x int32 Q4.26 [dh] -> int32 Q2.26. y = x / sqrt(sum(x^2) + eps):
        the norm divides by the SUM of squares, not the mean."""
        x = np.asarray(x, np.int64)
        ss = self._sumsq(x)
        v = self._rs_np(ss, 20)                             # sum(x^2) @2^32
        ss = int(v) + int(round(L2_EPS * 2 ** 32))
        r = fxluts.rsqrt_eval_i(self.lut_rsq, self.lut_rsq_d, ss, 24 + 16)
        y = ((self._rs_np(x, 4) * r) + (1 << 19)) >> 20      # -> Q2.26
        return sat32_np(y)

    def silu(self, x):
        """silu of int32 Q4.26 -> int32 Q4.26."""
        x = np.asarray(x, np.int64)
        sig = self.sig(x, 26)
        return sat32_np(self._rs_np(x * sig, SIG))

    def softmax_mix(self, logits_q37, cands):
        """logits int64 Q8.37 [M]; cands list of int32 Q4.26 arrays.
        out = sum p_i * cand_i (raw), p = softmax(logits), int32 Q4.26."""
        lg = np.asarray(logits_q37, np.int64)
        mx = int(lg.max())
        ei = np.clip(self._rs_np(lg - mx, 11), -(1 << 30), 0)   # -> Q8.26
        e = self.exp_of(ei, 26)                                 # Q0.26
        se = int(e.sum())
        rec = self.recip(se)                                    # 2^46/se
        out = np.zeros_like(np.asarray(cands[0], np.int64))
        for i, cd in enumerate(cands):
            out += np.asarray(cd, np.int64) * int(e[i])         # Q4.26*Q0.26
        y = ((self._rs_np(out, 24) * rec) + (1 << 21)) >> 22  # scales cancel
        if self.dump is not None:
            p = e.astype(np.float64) * rec / 2 ** 30
            self.dump.setdefault("softmax_p", []).append(p.copy())
        return sat32_np(y)

    # -- residual mixing --

    def res_mix(self, prefix, blocks, name):
        cands = list(blocks) + [prefix]
        nw = self.param[f"{name}.norm.w"]
        pw = self.param[f"{name}.proj"]
        logits = []
        for v in cands:
            vn = self.rmsnorm(v, nw)
            dot = (vn.astype(np.int64) * pw).sum()      # Q(4+4).(26+11)=Q8.37
            logits.append(dot)                          # int64, no clipping
        return self.softmax_mix(np.array(logits, np.int64), cands)

    # -- MoE --

    def swiglu(self, h, pref):
        g = self.gemv(pref + "g", h)
        u = self.gemv(pref + "u", h)
        sg = self.silu(g)                                   # Q4.26
        act = sat32_np(self._rs_np(sg * u.astype(np.int64), 26))  # -> Q5.26
        return self.gemv(pref + "d", act, SA)

    def moe(self, li, h):
        p = f"L{li}.moe."
        rin = self.gemv(p + "router", h)                    # Q4.26 [E]
        scores = self.sig(rin, 26)                          # Q0.22 [E]
        bias = self.param[p + "bias"]                       # Q4.11 [E]
        m = scores + (bias << (SIG - 11))                   # aligned Q0.22
        order = []
        mm = m.copy()
        for _ in range(self.top_k):
            j = int(np.argmax(mm))                          # lowest-index tie
            order.append(j)
            mm[j] = -2 ** 62
        ssel = scores[order]
        ssum = int(ssel.sum())
        wsel = [sat32((int(s) * ROUTER_Q26 + ssum // 2) // ssum)
                for s in ssel]
        if self.dump is not None:
            self.dump.setdefault("moe_sel", []).append(
                np.array([order, [w / 2 ** SIG for w in wsel]]))
        out = self.swiglu(h, p + "shared.").astype(np.int64)
        for j, w in zip(order, wsel):
            e = self.swiglu(h, p + f"e{j}.")
            out += self._rs_np(int(w) * e.astype(np.int64), SIG)
        return sat32_np(out)

    # -- KDA --

    def conv(self, li, stream, x):
        """x int32 Q4.26 [P]; causal depthwise conv kernel 4 then SiLU."""
        w = self.param[f"L{li}.kda.{'qkv'[stream]}conv"]     # [P, 4] Q4.11
        hist = self.conv_hist[li][stream]                    # [K-1, P] int32
        win = np.concatenate([hist, x[None, :]], axis=0).astype(np.int64)
        y = (win * w.T).sum(0)                               # Q8.37 [P]
        sig = self.sig(y, 37)
        out = sat32_np(self._rs_np(self._rs_np(y, 16) * sig,
                                   11 + SIG - 16))           # -> Q4.26
        self.conv_hist[li][stream] = np.concatenate(
            [hist[1:], x[None, :]], axis=0)
        return out

    def kda(self, li, h):
        H, dh = self.kda_heads, self.kda_dim
        p = f"L{li}.kda."
        q = self.conv(li, 0, self.gemv(p + "q", h))
        k = self.conv(li, 1, self.gemv(p + "k", h))
        v = self.conv(li, 2, self.gemv(p + "v", h))
        beta = self.sig(self.gemv(p + "b", h), 26)           # Q0.22 [H]
        f1 = self.gemv(p + "f1", h)
        f = self.gemv(p + "f2", f1).reshape(H, dh).astype(np.int64)
        dtb = self.param[p + "dtb"].reshape(H, dh)           # Q4.11
        A = self.param[p + "A"]                              # u Q8.8 [H]
        arg = self._rs_np(A[:, None] * (f + (dtb << (SX - 11))),
                          8)                                   # -> Q4.26
        alpha = self.alpha_of(arg, 26)                       # Q0.22 [H, dh]
        g1 = self.gemv(p + "g1", h)
        z = self.sig(self.gemv(p + "g2", g1), 26).reshape(H, dh)
        S = self.kda_S[li]                                   # [H, dh, dh] Q4.27
        outs = []
        for hd in range(H):
            qh = self.l2norm(q[hd * dh:(hd + 1) * dh]).astype(np.int64)  # Q2.26
            kh = self.l2norm(k[hd * dh:(hd + 1) * dh]).astype(np.int64)
            vh = v[hd * dh:(hd + 1) * dh].astype(np.int64)   # Q4.26
            Sd = self._rs_np(S[hd] * alpha[hd][:, None], ALPHA)  # Q4.27
            Sd4 = self._rs_np(Sd, 4)                         # headroom for sums
            kS = (kh[:, None] * Sd4).sum(0)                  # Q(2+4).(26+23)=Q6.49
            u = (vh << (SS - SX)) - self._rs_np(kS, 22)      # -> Q4.27
            bk = self._rs_np(int(beta[hd]) * kh, 24)         # Q0.22*Q2.26 -> Q2.28
            upd = self._rs_np(bk[:, None] * u[None, :], 28)  # -> Q4.27
            S[hd] = np.clip(Sd + upd, I32MIN, I32MAX)
            S4 = self._rs_np(S[hd], 4)                     # updated state
            o = self._rs_np((qh[:, None] * S4).sum(0), 23)  # Q6.49 -> Q6.26
            o = self._rs_np(o * self.c_dh, 16)              # 1/sqrt(dh)
            on = self.rmsnorm(sat32_np(o),
                              self.param[p + "onorm.w"])     # Q2.26 -> Q4.26?
            # NOTE: onorm reads Q2.26 but rmsnorm is scale-generic (x>>16/x>>4)
            outs.append(sat32_np(self._rs_np(
                on.astype(np.int64) * z[hd], SIG)))          # gate -> Q4.26
        core = np.concatenate(outs)
        if self.dump is not None:
            self.dump.setdefault("kda_core", []).append(
                core.astype(np.float64) / 2 ** SX)
        return self.gemv(p + "o", core)

    # -- MLA --

    def mla(self, li, h):
        c = self
        p = f"L{li}.mla."
        lat = self.rmsnorm(self.gemv(p + "wc", h),
                           self.param[p + "knorm.w"])
        qc = self.gemv(p + "wq_c", h).reshape(c.n_heads, c.mla_dk)
        qr = self.gemv(p + "wq_r", h).reshape(c.n_heads, c.mla_dr)
        kc = self.gemv(p + "wk_c", lat).reshape(c.n_heads, c.mla_dk)
        kr = self.gemv(p + "wk_r", h)                        # [dr]
        vv = self.gemv(p + "wv", lat).reshape(c.n_heads, c.mla_dv)
        q = np.concatenate([qc, qr], axis=-1)                # [H, dqk] Q4.26
        kk = np.concatenate(
            [kc, np.broadcast_to(kr, (c.n_heads, c.mla_dr))], axis=-1)
        c.kv_k[li][c.pos] = kk
        c.kv_v[li][c.pos] = vv
        T = c.pos + 1
        K = c.kv_k[li][:T].astype(np.int64)                  # [T, H, dqk]
        V = c.kv_v[li][:T].astype(np.int64)                  # [T, H, dv]
        outs = []
        for hd in range(c.n_heads):
            att = (self._rs_np(K[:, hd], 4)
                   * self._rs_np(q[hd].astype(np.int64), 4)
                   ).sum(-1)                                   # Q8.44 [T]
            att = self._rs_np(att, 18)                           # -> Q8.26
            att = self._rs_np(att * self.c_att, 16)              # scaled Q8.26
            mx = int(att.max())
            ei = np.clip(att - mx, -(1 << 30), 0)
            e = self.exp_of(ei, 26)                              # Q0.26 [T]
            se = int(e.sum())
            rec = self.recip(se)
            acc = (self._rs_np(e, 4)[:, None] * V[:, hd]).sum(0)  # [dv]
            outs.append(sat32_np((self._rs_np(acc, 28) * rec
                                  + (1 << 13)) >> 14))
        ctx = np.concatenate(outs)
        if self.dump is not None:
            self.dump.setdefault("mla_ctx", []).append(
                ctx.astype(np.float64) / 2 ** SX)
        return self.gemv(p + "o", ctx)

    # -- one token --

    def emb_row(self, token):
        q = np.empty(self.d_model, np.int16)
        row = self.emb_q[token].astype(np.int16)
        q[0::2] = row & 0x0F
        q[1::2] = row >> 4
        gsz = min(self.group_size, self.d_model)
        gi = np.arange(self.d_model) // gsz
        acc = (q - self.emb_z[token][gi]).astype(np.int64) \
            * self.emb_s[token][gi]                          # (q-z)*s, sx=0
        return sat32_np(self._rs_np(acc, 12 - SX))           # << 14 -> Q4.26

    def step(self, token):
        x = self.emb_row(token)
        blocks = []
        for li, t in enumerate(self.layer_types):
            boundary = li % self.attn_res_block == 0
            prefix = x
            if boundary:
                blocks.append(x)
            mix_in = blocks[:-1] if boundary else blocks
            if mix_in:
                x = self.res_mix(x, mix_in, f"L{li}.res_attn")
            h1 = self.rmsnorm(x, self.param[f"L{li}.norm1.w"])
            a = (self.mla if t == "F" else self.kda)(li, h1)
            prefix = a if boundary else sat32_np(
                prefix.astype(np.int64) + a)
            x = self.res_mix(prefix, blocks, f"L{li}.res_mlp")
            h2 = self.rmsnorm(x, self.param[f"L{li}.norm2.w"])
            m = self.moe(li, h2)
            x = sat32_np(prefix.astype(np.int64) + m)
            if self.dump is not None:
                self.dump.setdefault("layer_out", []).append(
                    x.astype(np.float64) / 2 ** SX)
        x = self.res_mix(x, blocks, "res_out")
        hn = self.rmsnorm(x, self.param["final_norm.w"])
        acc = self.gemv_acc("head", hn)
        logits = sat32_np(self._rs_np(acc, R_HEAD))
        self.pos += 1
        return logits

    def run(self):
        toks = np.frombuffer(
            self.img[self.tokens_addr:self.tokens_addr + 4 * self.seq_len],
            "<u4").astype(np.int64)
        logits = np.zeros((self.seq_len, self.vocab), np.int32)
        argmax = np.zeros(self.seq_len, np.int64)
        for p, t in enumerate(toks):
            row = self.step(int(t))
            logits[p] = row
            argmax[p] = int(np.argmax(row))                  # lowest-index tie
        return logits, argmax


def main():
    img_path, out_path = sys.argv[1], sys.argv[2]
    with open(img_path, "rb") as f:
        img = f.read()
    m = FxModel(img)
    logits, _ = m.run()
    logits.astype("<i4").tofile(out_path)


if __name__ == "__main__":
    main()
