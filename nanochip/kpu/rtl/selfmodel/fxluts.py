"""LUT definitions shared by the ROM generator and the fixed-point C-model.

Single source of truth for every nonlinearity table used by the chip.
The Verilog ROM files in rtl/roms/*.hex are generated from these exact
functions (scripts/gen_roms.py); the C-model loads the same files.

All tables use LINEAR INTERPOLATION between endpoint values:
  idx  = clip((x >> SHIFT) + OFF, 0, N)      (arithmetic >>, floor)
  frac = x - ((x >> SHIFT) << SHIFT)          # in [0, 2^SHIFT)
  y    = t[idx] + ((d[idx] * frac) >> SHIFT)  # d = t[idx+1] - t[idx]
Tables store N+1 endpoints; d has N+1 entries (last is 0).

Tables (value files *.hex unsigned, delta files *_d.hex signed 16b two's
complement):
  sigmoid  4097 x 23b  sigmoid(x), x int16 Q4.11 (bucket 2^-8), out Q0.22
  alpha    4097 x 23b  exp(-5*sigmoid(x)), same indexing, out Q0.22
  expneg   4097 x 17b  exp(x), x int32 Q8.16 in [-16,0] (bucket 2^-8), out Q0.16
  rsqrt    2049 x 18b  rsqrt(m), m in [2^11, 2^12] (16 sub-steps), out *2^23
  recip    2049 x 20b  1/m,      m in [2^11, 2^12], out 2^30/m
"""

import math

SIG_N = 8192                 # buckets over [-16, 16) at Q4.11
SIG_IDX_SHIFT = 3
EXP_N = 4096                 # buckets over [-16, 0) at Q8.16
EXP_IDX_SHIFT = 8
RSQ_N = 2048                 # buckets over [2^11, 2^12)
SQRT2_Q18 = 370728           # round(sqrt(2) * 2^18)


def _sigmoid_t():
    t = []
    for i in range(SIG_N + 1):
        xm = (i - SIG_N // 2) * (1 << SIG_IDX_SHIFT) / 2048.0
        v = 1.0 / (1.0 + math.exp(-xm))
        t.append(min(2 ** 26 - 1, max(0, int(round(v * 2 ** 26)))))
    return t


def _alpha_t():
    t = []
    for i in range(SIG_N + 1):
        xm = (i - SIG_N // 2) * (1 << SIG_IDX_SHIFT) / 2048.0
        v = math.exp(-5.0 / (1.0 + math.exp(-xm)))
        t.append(min(2 ** 26 - 1, max(0, int(round(v * 2 ** 26)))))
    return t


def _expneg_t():
    t = []
    for i in range(EXP_N + 1):
        xm = (i - EXP_N) * (1 << EXP_IDX_SHIFT) / 65536.0
        t.append(min(2 ** 26, max(0, int(round(math.exp(xm) * 2 ** 26)))))
    return t


def _rsqrt_t():
    t = []
    for i in range(RSQ_N + 1):
        m = 2048 + i
        t.append(int(round(2 ** 32 / math.sqrt(m))))
    return t


def _recip_t():
    t = []
    for i in range(RSQ_N + 1):
        m = 2048 + i
        t.append(min(2 ** 19, int(round(2 ** 30 / m))))
    return t


def _deltas(t):
    return [t[i + 1] - t[i] for i in range(len(t) - 1)] + [0]


TABLES = {
    "sigmoid": (_sigmoid_t, 27),
    "alpha": (_alpha_t, 27),
    "expneg": (_expneg_t, 27),
    "rsqrt": (_rsqrt_t, 33),
    "recip": (_recip_t, 20),
}
DELTA_WIDTH = {"sigmoid": 20, "alpha": 20, "expneg": 20,
               "rsqrt": 16, "recip": 16}


def load_hex(path):
    with open(path) as f:
        return [int(line.strip(), 16) for line in f if line.strip()]


def load_hex_s(path, width=16):
    """Signed two's-complement hex file (given bit width)."""
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            v = int(line, 16)
            out.append(v - (1 << width) if v >= (1 << (width - 1)) else v)
    return out


def topbit(v):
    return v.bit_length() - 1


def _norm20(v):
    """v > 0 -> (m_q in [2^20, 2^21), E9) with v = (m_q/512) * 2^E9."""
    e = topbit(v)
    E = e - 20
    m_q = v >> E if E >= 0 else v << (-E)
    assert 1048576 <= m_q < 2097152, (v, e, E, m_q)
    return m_q, E + 9


def rsqrt_eval_i(t, d, v, sy):
    """Interpolated integer rsqrt: round(1/sqrt(v) * 2^sy), v > 0 int."""
    assert v > 0
    m_q, E9 = _norm20(v)
    idx = (m_q >> 9) - 2048
    frac = m_q & 511
    r = t[idx] + ((d[idx] * frac + 256) >> 9)   # rsqrt(m_q/512) * 2^32
    if E9 % 2 != 0:
        r = (r * SQRT2_Q18 + (1 << 17)) >> 18
        E9 += 1
    sh = sy - 32 - E9 // 2
    if sh >= 0:
        return r << sh
    return (r + (1 << (-sh - 1))) >> (-sh)


def recip_eval_i(t, d, s, sy):
    """Interpolated integer reciprocal: round(2^sy / s), s > 0 int."""
    assert s > 0
    m_q, E9 = _norm20(s)
    idx = (m_q >> 9) - 2048
    frac = m_q & 511
    r = t[idx] + ((d[idx] * frac + 256) >> 9)   # 2^30 / (m_q/512)
    sh = sy - 30 - E9
    if sh >= 0:
        return r << sh
    return (r + (1 << (-sh - 1))) >> (-sh)
