# rtl/roms/

Optional location for ROM initialization files (`$readmem*` targets).
Rules (machine-checked by `harness/audit.py`, rule R1.4):

* this task ships **no frozen numeric artifacts** (there is no RoPE), so
  every file here is one of YOUR nonlinearity LUTs (silu/sigmoid/exp/...
  at whatever resolution you chose) and requires a **disclosed,
  reproducible generator** (`scripts/gen_roms.py` + a note in
  REPORT.md);
* opaque tables that encode evaluation answers are hardcoding — automatic
  fail. `$readmem` from anywhere outside this directory: automatic fail.
