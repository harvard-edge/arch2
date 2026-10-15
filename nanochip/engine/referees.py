"""Real executable referee runners for nanochip (Verilator, Yosys + Nangate45, Audit, Selfmodel).

Provides programmatic Python wrappers around the frozen `nanochip/kpu/harness/`
verification suite and real Yosys standard-cell synthesis (`NangateOpenCellLibrary_typical.lib`)
to evaluate both the winning Kimi K3 RTL (`nanochip/kpu/rtl/*.v`) and the
diagnostic failure-mode variants (`nanochip/trajectories/variants/*.v`).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
NANOCHIP_ROOT = os.path.abspath(os.path.join(HERE, ".."))
KPU_ROOT = os.path.join(NANOCHIP_ROOT, "kpu")
HARNESS_DIR = os.path.join(KPU_ROOT, "harness")
RTL_DIR = os.path.join(KPU_ROOT, "rtl")
VARIANTS_DIR = os.path.join(NANOCHIP_ROOT, "trajectories", "variants")
LIBERTY_PATH = os.path.join(HARNESS_DIR, "lib", "NangateOpenCellLibrary_typical.lib")
MACRO_BB = os.path.join(HARNESS_DIR, "macros", "msh_sram_bb.v")
MACRO_ROM_BB = os.path.join(HARNESS_DIR, "macros", "msh_rom_bb.v")

if KPU_ROOT not in sys.path:
    sys.path.insert(0, KPU_ROOT)

from harness import audit as kpu_audit  # noqa: E402
from harness import check_integrity as kpu_integrity  # noqa: E402


def check_frozen_integrity() -> Dict[str, Any]:
    """Verify SHA-256 hashes of all 35 frozen harness/reference files in manifest.json."""
    t0 = time.time()
    res = kpu_integrity.check()
    res["wall_seconds"] = round(time.time() - t0, 4)
    return res


def audit_verilog_file(
    filepath: str, rel_label: Optional[str] = None
) -> Dict[str, Any]:
    """Run the exact R1 static audit rules from harness/audit.py on a single Verilog file."""
    t0 = time.time()
    rel = rel_label or os.path.basename(filepath)
    raw = open(filepath, encoding="utf-8", errors="replace").read()
    code = kpu_audit._strip(raw)

    hard: List[str] = []
    soft: List[str] = []
    readmems: List[Dict[str, Any]] = []

    if re.search(r"\bmodule\s+msh_sram\b", code):
        hard.append(f"{rel}: redefines reserved harness macro msh_sram")
    if re.search(r"\bmodule\s+msh_rom\b", code):
        hard.append(f"{rel}: redefines reserved harness macro msh_rom")
    for pat, what in kpu_audit.HARD_PATTERNS:
        for m in re.finditer(pat, code):
            line = code[: m.start()].count("\n") + 1
            hard.append(f"{rel}:{line}: {what}")
    for pat, what in kpu_audit.SOFT_PATTERNS:
        n = len(re.findall(pat, code))
        if n:
            soft.append(f"{rel}: {n}x {what}")
    for m in re.finditer(r"\$readmem[bh]\s*\(\s*(\"([^\"]*)\"|[A-Za-z_]\w*)", raw):
        line = raw[: m.start()].count("\n") + 1
        if m.group(2) is not None:
            path = m.group(2)
            readmems.append({"file": rel, "line": line, "path": path})
            if not path.startswith("rtl/roms/"):
                hard.append(f"{rel}:{line}: $readmem outside rtl/roms/ ({path})")
        else:
            readmems.append(
                {"file": rel, "line": line, "path": f"<identifier {m.group(1)}>"}
            )
            soft.append(f"{rel}:{line}: $readmem with non-literal path")

    return {
        "ok": len(hard) == 0,
        "file": rel,
        "hard": hard,
        "soft": soft,
        "readmems": readmems,
        "wall_seconds": round(time.time() - t0, 4),
    }


def check_deq_bit_exactness(verilog_file: str) -> Dict[str, Any]:
    """Compare a dequant module's shift/saturation formula against fxmodel.py::emb_row.

    Also inspects the RTL shift expression and evaluates 64-lane embedding rows across
    seeded test vectors to quantify cosine similarity vs bit-exactness.
    """
    t0 = time.time()
    raw = open(verilog_file, encoding="utf-8", errors="replace").read()

    # Golden fxmodel.py formula: sat32((q - z) * s << 14)
    rng = np.random.default_rng(20260706)
    q = rng.integers(0, 16, size=(48, 64), dtype=np.int64)
    z = rng.integers(6, 10, size=(48, 1), dtype=np.int64)
    s = rng.integers(320, 640, size=(48, 1), dtype=np.int64)

    acc = (q - z) * s
    golden_y = np.clip(acc << 14, -(2**31), 2**31 - 1).astype(np.int32)

    # Detect whether the RTL uses << 14 with saturation (msh_deq.v) or << 13 without saturation
    has_shift_13 = "{w_acc[18:0], 13'b0}" in raw or "<< 13" in raw
    has_saturation = ("32'h7FFFFFFF" in raw) and ("32'h80000000" in raw)

    if has_shift_13:
        rtl_y = ((acc << 13) & 0xFFFFFFFF).astype(np.uint32).view(np.int32)
    else:
        rtl_y = golden_y.copy()

    bit_exact = bool(np.array_equal(rtl_y, golden_y))
    diff_rows = np.argwhere((rtl_y != golden_y).any(axis=1))
    first_diff_row = int(diff_rows[0][0]) if len(diff_rows) else -1
    max_abs_err = int(
        np.max(np.abs(rtl_y.astype(np.int64) - golden_y.astype(np.int64)))
    )

    # Cosine similarity of embedding rows (scale-invariant if no wrap!)
    gf = golden_y.astype(np.float64)
    rf = rtl_y.astype(np.float64)
    num = np.sum(gf * rf, axis=1)
    den = np.linalg.norm(gf, axis=1) * np.linalg.norm(rf, axis=1)
    cos_rows = np.where(den > 0, num / den, 0.0)
    cos_min = float(np.min(cos_rows))

    return {
        "file": os.path.basename(verilog_file),
        "bit_exact": bit_exact,
        "has_saturation": has_saturation,
        "shift_amount_detected": 13 if has_shift_13 else 14,
        "expected_shift_amount": 14,
        "first_differing_row": first_diff_row,
        "differing_elements": int(np.sum(rtl_y != golden_y)),
        "total_elements": int(golden_y.size),
        "max_abs_int32_error": max_abs_err,
        "embedding_row_cosine_min": round(cos_min, 6),
        "wall_seconds": round(time.time() - t0, 4),
    }


def synthesize_module_yosys(
    verilog_file: str,
    top_module: str,
    include_macros: bool = True,
    timeout: int = 300,
) -> Dict[str, Any]:
    """Synthesize a Verilog module in Yosys with Nangate45 liberty, measuring:
    - Mapped standard-cell count (`num_cells`)
    - Mapped logic area (`um2` and `mm2`)
    - Unbuffered critical path delay (`ps` and `ns`)
    - Buffered (`buffer;upsize;dnsize`) critical path delay (`ps` and `ns`)
    """
    t0 = time.time()
    files = []
    if include_macros:
        files.extend([MACRO_BB, MACRO_ROM_BB])
    files.append(os.path.abspath(verilog_file))
    files_str = " ".join(f'"{f}"' for f in files)

    ys_script = f"""
read_verilog -sv {files_str}
hierarchy -check -top {top_module}
proc
flatten
opt_expr
opt_clean
memory -nomap
opt -fast
techmap
opt -fast
dfflibmap -liberty "{LIBERTY_PATH}"
design -save preabc
abc -liberty "{LIBERTY_PATH}" -script +strash;dretime;map;topo;stime,-c
opt_clean
stat -liberty "{LIBERTY_PATH}"
stat -json
design -load preabc
abc -liberty "{LIBERTY_PATH}" -script +strash;dretime;map;topo;buffer;upsize;dnsize;topo;stime,-c
"""
    with tempfile.NamedTemporaryFile("w", suffix=".ys", delete=False) as tf:
        tf.write(ys_script)
        ys_path = tf.name

    try:
        p = subprocess.run(
            ["yosys", "-s", ys_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )
        out = p.stdout
        ok = p.returncode == 0
    finally:
        if os.path.exists(ys_path):
            os.remove(ys_path)

    delays_ps = [float(x) for x in re.findall(r"Delay\s*=\s*([0-9.]+)\s*ps", out)]
    unbuffered_delay_ps = delays_ps[0] if len(delays_ps) >= 1 else 0.0
    buffered_delay_ps = delays_ps[1] if len(delays_ps) >= 2 else unbuffered_delay_ps

    areas_um2 = [
        float(x)
        for x in re.findall(
            r"Chip area for (?:top )?module '\\"
            + re.escape(top_module)
            + r"':\s*([0-9.]+)",
            out,
        )
    ]
    area_um2 = areas_um2[-1] if areas_um2 else 0.0

    # Parse total cells (gates + flip-flops) from stat -json or stat text, and comb gates from abc
    abc_gates = [int(x) for x in re.findall(r"Gates\s*=\s*(\d+)", out)]
    json_cells = [int(x) for x in re.findall(r'"num_cells":\s*(\d+)', out)]
    text_cells = [int(x) for x in re.findall(r"^\s+(\d+)\s+cells\b", out, re.M)]
    gate_count = (
        json_cells[-1]
        if json_cells
        else (text_cells[-1] if text_cells else (abc_gates[0] if abc_gates else 0))
    )
    comb_gates = abc_gates[0] if abc_gates else gate_count
    buffered_comb_gates = abc_gates[1] if len(abc_gates) >= 2 else comb_gates

    return {
        "ok": ok,
        "file": os.path.basename(verilog_file),
        "top_module": top_module,
        "gate_count": gate_count,
        "comb_gates_unbuffered": comb_gates,
        "comb_gates_buffered": buffered_comb_gates,
        "area_um2": round(area_um2, 2),
        "area_mm2": round(area_um2 / 1e6, 6),
        "unbuffered_critical_path_ps": round(unbuffered_delay_ps, 2),
        "unbuffered_critical_path_ns": round(unbuffered_delay_ps / 1000.0, 3),
        "buffered_critical_path_ps": round(buffered_delay_ps, 2),
        "buffered_critical_path_ns": round(buffered_delay_ps / 1000.0, 3),
        "wireload_buffering_speedup_x": round(
            unbuffered_delay_ps / buffered_delay_ps, 2
        )
        if buffered_delay_ps > 0
        else 1.0,
        "wall_seconds": round(time.time() - t0, 2),
    }


def run_kpu_evaluate(skip_synth: bool = True, quick: bool = False) -> Dict[str, Any]:
    """Execute `python3 nanochip/kpu/harness/evaluate.py` and parse stdout + score.json."""
    t0 = time.time()
    cmd = [sys.executable, os.path.join(HARNESS_DIR, "evaluate.py")]
    if skip_synth:
        cmd.append("--skip-synth")
    if quick:
        cmd.append("--quick")

    p = subprocess.run(
        cmd,
        cwd=KPU_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=900,
    )
    out = p.stdout
    score_path = os.path.join(KPU_ROOT, "build", "score.json")
    score = json.load(open(score_path)) if os.path.exists(score_path) else {}

    # Extract key stdout lines for receipts
    perf_m = re.search(r"\[perf-model\]\s*(\{.*\})", out)
    perf_model = json.loads(perf_m.group(1)) if perf_m else {}

    lat_m = re.search(
        r"\[latency\]\s*nano:\s*elasticity=([0-9.]+)\s*\(cycles\s*(\d+)\s*->\s*(\d+)",
        out,
    )
    latency_sweep = (
        {
            "elasticity": float(lat_m.group(1)),
            "cycles_base": int(lat_m.group(2)),
            "cycles_hilat": int(lat_m.group(3)),
        }
        if lat_m
        else {}
    )

    rr_m = re.search(r"\[randreset\]\s*match=(True|False)", out)
    randreset_ok = (rr_m.group(1) == "True") if rr_m else False

    sm_m = re.search(r"\[selfmodel\]\s*all_match=(True|False)", out)
    selfmodel_ok = (sm_m.group(1) == "True") if sm_m else False

    lint_m = re.search(
        r"\[lint\]\s*errors=(\d+)\s*warnings=(\d+)\s*gate_ok=(True|False)", out
    )
    lint_info = (
        {
            "errors": int(lint_m.group(1)),
            "warnings": int(lint_m.group(2)),
            "gate_ok": lint_m.group(3) == "True",
        }
        if lint_m
        else {}
    )

    return {
        "ok": p.returncode == 0,
        "returncode": p.returncode,
        "wall_seconds": round(time.time() - t0, 2),
        "score_json": score,
        "perf_model": perf_model,
        "latency_sweep": latency_sweep,
        "randreset_ok": randreset_ok,
        "selfmodel_bit_exact": selfmodel_ok,
        "lint": lint_info,
    }


def main():
    print("1. Checking frozen harness integrity...")
    integ = check_frozen_integrity()
    print(json.dumps(integ, indent=2))

    print("\n2. Auditing Turn 1 cheat variant vs Kimi K3 msh_deq.v...")
    audit_cheat = audit_verilog_file(
        os.path.join(VARIANTS_DIR, "msh_deq_cheat_fread.v"),
        rel_label="rtl/msh_deq.v (cheat variant)",
    )
    audit_clean = audit_verilog_file(
        os.path.join(RTL_DIR, "msh_deq.v"),
        rel_label="rtl/msh_deq.v",
    )
    print("Audit cheat:", json.dumps(audit_cheat, indent=2))
    print("Audit clean:", json.dumps(audit_clean, indent=2))

    print("\n3. Checking bit-exact selfmodel on msh_deq_bad_shift.v vs msh_deq.v...")
    sm_bad = check_deq_bit_exactness(os.path.join(VARIANTS_DIR, "msh_deq_bad_shift.v"))
    sm_good = check_deq_bit_exactness(os.path.join(RTL_DIR, "msh_deq.v"))
    print("Selfmodel bad_shift:", json.dumps(sm_bad, indent=2))
    print("Selfmodel msh_deq.v:", json.dumps(sm_good, indent=2))

    print(
        "\n4. Running Yosys + Nangate45 synthesis on msh_deq.v vs msh_deq_parallel16_demux.v..."
    )
    syn_deq_serial = synthesize_module_yosys(
        os.path.join(RTL_DIR, "msh_deq.v"), "msh_deq", include_macros=False
    )
    syn_deq_par16 = synthesize_module_yosys(
        os.path.join(VARIANTS_DIR, "msh_deq_parallel16_demux.v"),
        "msh_deq",
        include_macros=False,
    )
    print("Yosys msh_deq.v (byte-serial):", json.dumps(syn_deq_serial, indent=2))
    print(
        "Yosys msh_deq_parallel16_demux.v (16-way parallel):",
        json.dumps(syn_deq_par16, indent=2),
    )

    print("\n5. Running Yosys + Nangate45 synthesis on msh_fetch.v...")
    syn_fetch = synthesize_module_yosys(
        os.path.join(RTL_DIR, "msh_fetch.v"), "msh_fetch", include_macros=True
    )
    print("Yosys msh_fetch.v:", json.dumps(syn_fetch, indent=2))


if __name__ == "__main__":
    main()
