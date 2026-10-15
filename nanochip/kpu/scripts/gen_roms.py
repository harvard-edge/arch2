#!/usr/bin/env python3
"""Regenerate the nonlinearity LUT ROM files in rtl/roms/.

Usage:
    python3 scripts/gen_roms.py [OUTDIR]        # default: <repo>/rtl/roms

Numeric source: rtl/selfmodel/fxluts.py is the single source of truth for
the endpoint tables (the fixed-point C model uses the same tables), so
this script only serializes them into the three on-disk variants:

  <name>.hex      endpoint table t[0..N], unsigned, one lowercase
                  zero-padded hex value per line, ceil(bits/4) digits
                  (bits: sigmoid/alpha/expneg 27, rsqrt 33, recip 20);
                  consumed by the C model.
  <name>_d.hex    delta table d[i] = t[i+1] - t[i] for i in [0, N) plus a
                  trailing 0 (N+1 entries), signed two's complement in
                  DELTA_WIDTH bits (20 for sigmoid/alpha/expneg, 16 for
                  rsqrt/recip); consumed by the C model.
  <name>_msh.hex  endpoint table with the last row duplicated
                  (t[0..N] + [t[N]] -> N+2 entries), zero-padded to the
                  RTL container width (32b sigmoid/alpha/expneg, 40b
                  rsqrt, 24b recip); consumed via $readmemh by the
                  msh_rom instances in rtl/msh_vec.v / rtl/msh_mla.v,
                  which read t[idx] and t[idx+1] with idx clipped to
                  [0, N] and form the delta on the fly, so the duplicated
                  top row makes the top bucket's delta 0.

Table math (see rtl/selfmodel/fxluts.py for the exact code):
  sigmoid  8193 endpoints: round(sigmoid(x) * 2^26), x = (i-4096)*8/2048
  alpha    8193 endpoints: round(exp(-5*sigmoid(x)) * 2^26), same grid
  expneg   4097 endpoints: round(exp(x) * 2^26), x = (i-4096)*256/65536
  rsqrt    2049 endpoints: round(2^32 / sqrt(2048+i))
  recip    2049 endpoints: round(2^30 / (2048+i)), clamped to 2^19

Standard library only. The output is byte-for-byte identical to the
committed rtl/roms/*.hex; scripts/check_roms.sh verifies that via sha256.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "rtl", "selfmodel"))

import fxluts  # noqa: E402  (single source of truth for the table math)

# Container widths of the msh_rom instances in rtl/msh_vec.v / rtl/msh_mla.v
# (e.g. msh_rom #(.DEPTH(8194), .WIDTH(32)) for sigmoid/alpha).
MSH_BITS = {"sigmoid": 32, "alpha": 32, "expneg": 32, "rsqrt": 40, "recip": 24}


def _write(path, values, bits):
    digits = (bits + 3) // 4
    with open(path, "w", newline="\n") as f:
        for v in values:
            f.write(f"{v:0{digits}x}\n")


def main():
    outdir = (sys.argv[1] if len(sys.argv) > 1
              else os.path.join(REPO_ROOT, "rtl", "roms"))
    os.makedirs(outdir, exist_ok=True)
    n = 0
    for name, (build, bits) in fxluts.TABLES.items():
        t = build()
        dbits = fxluts.DELTA_WIDTH[name]
        dmask = (1 << dbits) - 1
        _write(os.path.join(outdir, name + ".hex"), t, bits)
        _write(os.path.join(outdir, name + "_d.hex"),
               [v & dmask for v in fxluts._deltas(t)], dbits)
        _write(os.path.join(outdir, name + "_msh.hex"), t + [t[-1]],
               MSH_BITS[name])
        n += 3
    print(f"gen_roms: wrote {n} files to {outdir}")


if __name__ == "__main__":
    main()
