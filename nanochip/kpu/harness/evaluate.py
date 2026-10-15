"""Nano-only evaluation orchestrator. Runs the quantitative pipeline:

  integrity -> audit -> lint -> verilate -> nano teacher-forced
  simulation (parallel), cosine-similarity comparison vs the float32
  reference -> yosys netlist generation + area/timing
  -> pure measurement report (no benchmark scoring: the legacy C/P/E/A/F
  composite, the primary gates and TOTAL have been removed)

Usage:
  python3 harness/evaluate.py                 # nano, both workloads
  python3 harness/evaluate.py --quick         # nano short run, no synth
  python3 harness/evaluate.py --seeds-file F  # alternate seed set (grading)
  python3 harness/evaluate.py --jobs N        # parallel simulations (default 4)

Seeds file (JSON): {"seed": int, "group_size": 64|128 (default 128),
"seq_stretch": float (default 1.0)}. The hidden grading set may vary
group_size and stretch the sequence lengths (bounded by max_seq) — designs
must self-configure from the image header, not from the public constants.

Memory timing per run (see harness/tb/tb_main.cpp): long runs (index 0)
use latency jitter only (--lat-jitter=12), preserving sustained bandwidth
for the cycles/beats-per-token measurements; short runs (index 1) are
stress runs with larger jitter and ~5% request back-pressure
(--lat-jitter=24 --stall-permille=50). Timing seeds are derived
deterministically from (seed, config, prompt).

Outputs build/score.json (strictly six sections: workloads, correctness,
throughput, timing, area, sram) and a human-readable summary on stdout.
This file is part of the frozen harness. Do not modify.
"""

import argparse
import collections
import dataclasses
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

from reference.config import CONFIGS, DEFAULT_LADDER          # noqa: E402
from reference.gen_weights import (gen_weights, gen_tokens,   # noqa: E402
                                   active_weight_bytes, floor_weight_bytes)
from reference.prng import fnv1a64                            # noqa: E402
from harness import scoring                                   # noqa: E402
from harness.memmap import build_image, parse_result, DONE_WORD  # noqa: E402
from harness.gen_golden import golden                          # noqa: E402
from harness.check_integrity import check as integrity_check   # noqa: E402
from harness.audit import check as audit_check                 # noqa: E402

BUILD = os.path.join(ROOT, "build")
TOP = "msh_chip_top"
BUDGETS_JSON = os.path.join(HERE, "resource_budgets.json")
MEM_PORT_BYTES = 16

# on-chip storage must go through the harness-provided SRAM macro: the
# behavioral model is linked into simulations, the blackbox stub into the
# synthesis flows; macro instances are priced from their parameters.
MACRO_SIM = os.path.join(HERE, "macros", "msh_sram.v")
MACRO_BB = os.path.join(HERE, "macros", "msh_sram_bb.v")
MACRO_ROM_SIM = os.path.join(HERE, "macros", "msh_rom.v")
MACRO_ROM_BB = os.path.join(HERE, "macros", "msh_rom_bb.v")
# harness-injected storage macros: writable SRAM + read-only ROM (constant
# LUTs). Instances of either are credited as macro storage (priced from
# DEPTH/WIDTH), NOT as design $mem_v2 (see macros_only gate).
MACRO_TYPES = {"msh_sram", "msh_rom"}
MACRO_AREA_UM2_PER_MBIT = 1.0e6   # ~1 Mbit/mm2 at N45 incl. periphery

# memory-timing profiles: (lat_jitter, stall_permille)
TIMING_LONG = (12, 0)     # bandwidth-preserving; used for the throughput runs
TIMING_SHORT = (24, 50)   # stress: jitter + ~5% request back-pressure
LAT_BASE = 24             # normative minimum read latency (memmap.MEM_LATENCY_MIN)
LAT_BASE_HI = 48          # elasticity sweep: doubled base latency


def load_budgets() -> dict:
    with open(BUDGETS_JSON) as f:
        return json.load(f)


def resource_budget_for_config(budgets: dict, cfg_name: str):
    """Return (logic_area_mm2, onchip_sram_mib) for a config.

    `logic_area_mm2` / `onchip_sram_mib` remain as full/default fallbacks for
    older budget files; `budget_ladder` holds the normative nano budget.
    """
    resources = budgets.get("resources", {}) or {}
    ladder = resources.get("budget_ladder", {}) or {}
    cfg_budget = ladder.get(cfg_name, {}) or {}
    area = cfg_budget.get("logic_area_mm2", resources.get("logic_area_mm2", 0.0))
    sram = cfg_budget.get("onchip_sram_mib", resources.get("onchip_sram_mib", 0.0))
    return float(area or 0.0), float(sram or 0.0)


# yosys prints one "Using template $extern:wrap:..." / 'Running "alumacc" on
# wrapper ...' line per cell INSTANCE (measured: 1,040,247 lines / 719 MB of
# stdout on a 2.19M-cell design), and its loop checker emits one "Warning:
# Detected loop ..." line per suspect net on $lut netlists with undef inputs
# (measured: 9,508,281 lines / 718 MB on the same design family). Stream yosys
# output through this filter so neither the log file nor the returned text
# can OOM the evaluator.
YOSYS_SPAM_RE = re.compile(
    r"Using template \$extern:wrap|Running \"alumacc\" on wrapper"
    r"|Warning: Detected loop")
RUN_OUT_CAP_BYTES = 64 * 1024 * 1024


class _BoundedOut:
    """Head+tail text accumulator: never retains more than cap bytes."""

    def __init__(self, cap=RUN_OUT_CAP_BYTES):
        self.cap = cap
        self.head, self.head_len = [], 0
        self.tail, self.tail_len = collections.deque(), 0
        self.total = 0

    def add(self, line):
        self.total += len(line)
        if self.head_len < self.cap // 2:
            self.head.append(line)
            self.head_len += len(line)
        else:
            self.tail.append(line)
            self.tail_len += len(line)
            while self.tail_len > self.cap // 2:
                self.tail_len -= len(self.tail.popleft())

    def text(self):
        elided = self.total - self.head_len - self.tail_len
        if elided <= 0:
            return "".join(self.head) + "".join(self.tail)
        return ("".join(self.head)
                + f"[evaluate.py: {elided} bytes of output elided "
                  f"(head+tail kept)]\n"
                + "".join(self.tail))


def _drain_stdout(pipe, logf, acc):
    try:
        for line in pipe:
            if YOSYS_SPAM_RE.search(line):
                continue
            if logf:
                logf.write(line)
            acc.add(line)
    finally:
        if logf:
            logf.close()


def _run_streaming(cmd, timeout, cwd, log_name, t0):
    """yosys path: stream stdout through the spam filter into the log file
    and a bounded head+tail buffer. PIPE-capturing unbounded yosys stdout
    OOM-killed the evaluator on a 2.19M-cell design (719 MB captured)."""
    logf = None
    if log_name:
        os.makedirs(BUILD, exist_ok=True)
        logf = open(os.path.join(BUILD, log_name), "w")
        logf.write(f"$ {' '.join(cmd)}\n")
    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True,
                         errors="replace")
    acc = _BoundedOut()
    th = threading.Thread(target=_drain_stdout,
                          args=(p.stdout, logf, acc), daemon=True)
    th.start()
    th.join(timeout)
    if th.is_alive():
        p.kill()
        th.join()
        code, tmo = -1, True
    else:
        code, tmo = p.wait(), False
    p.wait()
    return code, acc.text(), tmo, time.time() - t0


def run(cmd, timeout=None, cwd=ROOT, log_name=None):
    t0 = time.time()
    if os.path.basename(str(cmd[0])) == "yosys":
        return _run_streaming(cmd, timeout, cwd, log_name, t0)
    try:
        p = subprocess.run(cmd, cwd=cwd, timeout=timeout,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True)
        out, code, tmo = p.stdout, p.returncode, False
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode(errors="replace") \
            if isinstance(e.stdout, bytes) else (e.stdout or "")
        code, tmo = -1, True
    if log_name:
        os.makedirs(BUILD, exist_ok=True)
        with open(os.path.join(BUILD, log_name), "w") as f:
            f.write(f"$ {' '.join(cmd)}\n{out}")
    return code, out, tmo, time.time() - t0


def rtl_files():
    files = []
    with open(os.path.join(ROOT, "rtl", "filelist.f")) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith(("#", "//")):
                files.append(line)
    return files


def effective_config(cfg_name: str, variant: dict):
    """Apply seeds-file variant knobs (group_size, seq_stretch) to a config;
    the result is what images, goldens, and rooflines are computed from."""
    c = CONFIGS[cfg_name]
    g = int(variant.get("group_size", c.group_size))
    stretch = float(variant.get("seq_stretch", 1.0))
    lens = tuple(max(8, min(c.max_seq, int(round(s * stretch))))
                 for s in c.seq_lens)
    return dataclasses.replace(c, group_size=g, seq_lens=lens)


def do_lint():
    cmd = ["verilator", "--lint-only", "-Wall", "-Wno-fatal", "--top-module",
           TOP, MACRO_SIM, MACRO_ROM_SIM, "-f", "rtl/filelist.f"]
    code, out, _, _ = run(cmd, timeout=300, log_name="lint.log")
    warnings = len(re.findall(r"%Warning", out))
    errors = len(re.findall(r"%Error(?!.*due to)", out))
    gate_ok = code == 0 and scoring.lint_ok(errors, warnings)
    return {"ok": code == 0 and errors == 0, "warnings": warnings,
            "errors": errors, "gate_ok": bool(gate_ok),
            "max_warnings": scoring.LINT_MAX_WARN}


def build_sim(sources, tag, threads=0):
    objdir = os.path.join(BUILD, f"verilator_{tag}")
    shutil.rmtree(objdir, ignore_errors=True)
    cmd = ["verilator", "--cc", "--exe", "--build", "-j", "8", "-O2",
           "-Wno-fatal", "--top-module", TOP,
           "--x-initial", "unique"]
    if threads:
        cmd += ["--threads", str(threads)]
    cmd += ["--Mdir", objdir, "-o", "tb",
            os.path.join(HERE, "tb", "tb_main.cpp")] + sources
    code, out, _, dt = run(cmd, timeout=1800, log_name=f"build_{tag}.log")
    binp = os.path.join(objdir, "tb")
    ok = code == 0 and os.path.exists(binp)
    return {"ok": ok, "bin": binp if ok else None, "secs": round(dt, 1),
            "log_tail": out[-2000:] if not ok else ""}


def timing_seed(seed: int, cfg_name: str, prompt_idx: int) -> int:
    return (fnv1a64(f"timing/{seed}/{cfg_name}/{prompt_idx}")
            & 0x7FFFFFFFFFFFFFFF) or 1


def prepare_run(cfg_name, seed, prompt_idx, variant):
    """Build (and cache) the image and golden for one run. Serial: heavy
    numpy work; sims themselves run in parallel afterwards."""
    c = effective_config(cfg_name, variant)
    key = f"{cfg_name}_{seed}_{prompt_idx}_g{c.group_size}_s{c.seq_lens[prompt_idx]}"
    img_path = os.path.join(BUILD, f"img_{key}.bin")
    lay_path = img_path + ".layout.json"
    if not (os.path.exists(img_path) and os.path.exists(lay_path)):
        w = gen_weights(c, seed)
        r = build_image(c, w, gen_tokens(c, seed, prompt_idx))
        with open(img_path, "wb") as f:
            f.write(r["image"])
        json.dump(r["layout"], open(lay_path, "w"))
    g = golden(cfg_name, seed, prompt_idx, cfg=c)
    return {"cfg": c, "key": key, "img": img_path,
            "layout": json.load(open(lay_path)), "golden": g,
            "active_bytes": active_weight_bytes(c),
            "floor_bytes": floor_weight_bytes(c)}


def sim_one(binp, cfg_name, seed, prompt_idx, prep, tag="rtl", wall_mult=1,
            lat_base=LAT_BASE, plusargs=()):
    """Run one simulation and compare against the golden (cosine)."""
    c = prep["cfg"]
    layout = prep["layout"]
    res_path = os.path.join(BUILD, f"res_{tag}_{prep['key']}.bin")
    out_base = layout["out_logits_addr"]
    out_len = layout["out_status_addr"] + 16 - out_base
    jit, stall = TIMING_LONG if prompt_idx == 0 else TIMING_SHORT
    code, out, wall_tmo, dt = run(
        [binp, f"--image={prep['img']}", f"--result={res_path}",
         f"--out-base={out_base}", f"--out-len={out_len}",
         f"--timeout={c.timeout_cycles}",
         f"--lat-base={lat_base}",
         f"--lat-jitter={jit}", f"--stall-permille={stall}",
         f"--timing-seed={timing_seed(seed, cfg_name, prompt_idx)}"]
        + list(plusargs),
        timeout=c.wall_secs * wall_mult,
        log_name=f"sim_{tag}_{cfg_name}_{prompt_idx}.log")
    m = re.search(r"RESULT (\{.*\})", out)
    stats = json.loads(m.group(1)) if m else {}
    g = prep["golden"]
    # the dense tensors (everything except the data-dependent routed
    # experts and embedding rows) participate in every position's forward
    # pass, so a clean run must read at least floor_bytes from memory.
    # Fewer read beats than that is a protocol violation (the run cannot
    # PASS), not a bandwidth win.
    weight_stream_ok = stats.get("read_beats", 0) * MEM_PORT_BYTES >= prep["floor_bytes"]
    no_timeout = not stats.get("timeout", True) and not wall_tmo
    r = {"prompt": prompt_idx, "seq_len": layout["seq_len"],
         "sim_secs": round(dt, 1),
         "lat_base": lat_base, "lat_jitter": jit, "stall_permille": stall,
         "wall_timeout": wall_tmo, "cycle_timeout": stats.get("timeout", True),
         "cycles": stats.get("cycles", 0),
         "read_beats": stats.get("read_beats", 0),
         "write_beats": stats.get("write_beats", 0),
         "addr_errors": stats.get("addr_errors", 0),
         "roofline_cycles": layout["seq_len"] * (
             (prep["active_bytes"] + MEM_PORT_BYTES - 1) // MEM_PORT_BYTES),
         "weight_stream_ok": bool(weight_stream_ok)}
    if not os.path.exists(res_path):
        r.update(cos_min=0.0, cos_mean=0.0, row_score=0.0, argmax_agree=0.0,
                 argmax_hits=0, n_rows=0,
                 run_score=0.0, status_magic_ok=False, protocol_ok=False,
                 run_ok=False, status_ok=False)
        return r
    parsed = parse_result(c, layout, open(res_path, "rb").read())
    met = scoring.run_metrics(parsed["logits"], parsed["argmax"],
                              g["logits"], g["argmax"])
    status_magic_ok = parsed["status"] == DONE_WORD
    protocol_ok = status_magic_ok and no_timeout and r["addr_errors"] == 0
    run_ok = protocol_ok and weight_stream_ok
    r.update(**{k: (round(v, 6) if isinstance(v, float) else v)
                for k, v in met.items()},
             status_magic_ok=bool(status_magic_ok),
             protocol_ok=bool(protocol_ok),
             run_ok=bool(run_ok),
             # Backward-compatible alias for analysis scripts. Scoring gates on
             # run_ok; status_magic_ok is the literal status-word check.
             status_ok=bool(status_magic_ok))
    return r


def roofline_cycles(cfg_eff):
    return cfg_eff.seq_lens[0] * (
        (active_weight_bytes(cfg_eff) + MEM_PORT_BYTES - 1) // MEM_PORT_BYTES
    )


def _param_int(v):
    """yosys `dump` parameter value -> int. dump prints plain integers in
    decimal (`parameter signed \\DEPTH 65536`); values too wide for a native
    int print as sized binary (`32'b0101`)."""
    if v is None:
        return 0
    if isinstance(v, int):
        return v
    v = str(v).strip()
    m = re.match(r"^\d+'[bB]([01]+)$", v)
    if m:
        return int(m.group(1), 2)
    try:
        return int(v, 0)
    except ValueError:
        return 0


def _parse_macro_dump(path):
    """Parse yosys `dump t:msh_sram t:msh_rom` output into
    [(cell_type, {param_name: value_text}), ...]."""
    cells, ctype, params = [], None, {}
    with open(path) as f:
        for line in f:
            m = re.match(r"\s*cell \\(\S+) \\(\S+)", line)
            if m:
                if ctype is not None:
                    cells.append((ctype, params))
                ctype, params = m.group(1), {}
                continue
            m = re.match(r"\s+parameter (?:signed )?\\(\S+) (.*\S)\s*$", line)
            if m and ctype is not None:
                params[m.group(1)] = m.group(2)
    if ctype is not None:
        cells.append((ctype, params))
    return cells


def do_synth():
    files = " ".join([MACRO_BB, MACRO_ROM_BB] + rtl_files())
    script = open(os.path.join(HERE, "synth_area.ys")).read()
    mpath = os.path.join(BUILD, "macros_dump.txt")
    script = script.replace("{FILES}", files).replace("{MACROS}", mpath)
    spath = os.path.join(BUILD, "synth_area_gen.ys")
    open(spath, "w").write(script)
    code, out, tmo, dt = run(["yosys", "-s", spath], timeout=3600,
                             log_name="synth_area.log")
    res = {"ok": code == 0 and not tmo, "secs": round(dt, 1), "cells": {},
           "mem_bits": 0, "inferred_mem_bits": 0, "macro_bits": 0,
           "macro_count": 0, "macro_area_um2": 0.0,
           "ne": 0.0, "levels": 0, "levels_rtl": 0,
           "latch_cells": 0,
           "modules": {"count": 0, "max_share": 0.0, "cells_by_module": {}}}
    if not res["ok"]:
        res["log_tail"] = out[-2000:]
        return res
    # cells + memory bits from the JSON stat blob (text stat misses
    # $mem_v2 bit counts). Blob 0 is the pre-flatten stat: per-module cell
    # counts feed the module-structure metrics (R3 evidence).
    blobs = re.findall(r"^\{$.*?^\}$", out, re.M | re.S)
    parsed_json = False
    for bi, blob in enumerate(blobs):
        try:
            stat = json.loads(blob)
            top = stat.get("modules", {}).get("\\" + TOP, {})
            res["inferred_mem_bits"] = max(
                res["inferred_mem_bits"], int(top.get("num_memory_bits", 0)))
            if bi == 0:                       # pre-flatten: module structure
                mods = {name.lstrip("\\"): int(m.get("num_cells", 0))
                        for name, m in stat.get("modules", {}).items()}
                total = sum(mods.values())
                res["modules"] = {
                    "count": len(mods),
                    "max_share": round(max(mods.values()) / total, 4)
                    if total else 0.0,
                    "cells_by_module": dict(sorted(
                        mods.items(), key=lambda kv: -kv[1])[:40]),
                }
            if bi == len(blobs) - 1:          # cells from the final netlist
                for cell, cnt in top.get("num_cells_by_type", {}).items():
                    if cell.startswith("$"):
                        res["cells"][cell] = res["cells"].get(cell, 0) \
                            + int(cnt)
            parsed_json = True
        except (ValueError, KeyError):
            continue
    if not parsed_json:
        for mm in re.finditer(r"^\s+(\d+)\s+(\$_[A-Z0-9_]+_|\$\w+)\s*$",
                              out, re.M):
            res["cells"][mm.group(2)] = res["cells"].get(mm.group(2), 0) \
                + int(mm.group(1))
        mb = re.search(r"Number of memory bits:\s+(\d+)", out)
        if mb:
            res["inferred_mem_bits"] = int(mb.group(1))
    # on-chip SRAM = msh_sram/msh_rom macro instances, priced from their
    # parameters (targeted yosys `dump` — a few KB vs the old 672 MB
    # full-netlist write_json on a 2.19M-cell design); any inferred $mem_v2
    # left in the netlist is reported as inferred_mem_bits, not credited
    # storage.
    if os.path.exists(mpath):
        try:
            for ctype, pr in _parse_macro_dump(mpath):
                if ctype not in MACRO_TYPES:
                    continue
                d, w = _param_int(pr.get("DEPTH")), _param_int(pr.get("WIDTH"))
                if d and w:
                    res["macro_count"] += 1
                    res["macro_bits"] += d * w
            res["macro_area_um2"] = round(
                res["macro_bits"] / (1024.0 * 1024.0)
                * MACRO_AREA_UM2_PER_MBIT, 0)
            res["mem_bits"] = res["macro_bits"]
        except (ValueError, KeyError) as e:
            res["macro_parse_error"] = str(e)
    # single ltp report on the final mapped netlist (the pre-abc
    # informational ltp was dropped for cost on ~2M-cell designs; the
    # levels_rtl it produced is informational only and reads as 0)
    lvs = re.findall(r"Longest topological path.*\(length=(\d+)\)", out)
    if lvs:
        res["levels"] = int(lvs[-1])
        res["levels_rtl"] = int(lvs[0]) if len(lvs) > 1 else 0
    res["ne"] = round(scoring.ne_from_cells(res["cells"], res["mem_bits"]), 1)
    res["latch_cells"] = scoring.latch_cells(res["cells"])
    return res


def do_tech(budgets):
    """Technology-anchored logic area/timing.

    The bundled academic Nangate45 liberty gives a stable, deterministic
    pre-layout proxy for standard-cell area and critical path. This is not
    signoff STA; it feeds the area/timing measurements and the
    critical-path -> scored-clock ladder used for the tokens/s report.
    """
    tech = budgets.get("tech", {})
    lib_rel = tech.get("liberty", "harness/lib/NangateOpenCellLibrary_typical.lib")
    lib = lib_rel if os.path.isabs(lib_rel) else os.path.join(ROOT, lib_rel)
    if not os.path.exists(lib):
        return {"ok": False, "why": f"liberty missing: {lib}"}
    files = " ".join([MACRO_BB, MACRO_ROM_BB] + rtl_files())
    script = open(os.path.join(HERE, "synth_tech.ys")).read()
    script = script.replace("{FILES}", files).replace("{LIB}", lib)
    spath = os.path.join(BUILD, "synth_tech_gen.ys")
    open(spath, "w").write(script)
    code, out, tmo, dt = run(["yosys", "-s", spath], timeout=3600,
                             log_name="synth_tech.log")
    res = {"ok": code == 0 and not tmo, "secs": round(dt, 1),
           "lib": tech.get("name", "nangate45"),
           "liberty": os.path.relpath(lib, ROOT)}
    if not res["ok"]:
        res["log_tail"] = out[-2000:]
        return res
    m = re.search(r"Delay\s*=\s*([0-9.]+)\s*ps", out)
    if m:
        delay_ns = float(m.group(1)) / 1000.0
        res["critical_path_ns"] = delay_ns
        res["critical_path_ns_rounded"] = round(delay_ns, 3)
        res["fmax_mhz_est"] = round(1000.0 / delay_ns, 1) if delay_ns else 0.0
    a = re.findall(r"Chip area for (?:top )?module '\\" + TOP + r"':\s*([0-9.]+)",
                   out)
    if a:
        res["logic_area_um2"] = round(float(a[-1]), 0)
        res["logic_area_mm2"] = round(float(a[-1]) / 1e6, 6)
    return res


def compute_throughput(res, budgets) -> dict:
    """Decode-throughput measurement (no gating, no score).

    cycles/token of the config's long run, converted to tokens/s at the
    target clock and at the scored clock picked from the critical-path ->
    frequency ladder. Reported as measured; nothing is zeroed out.
    """
    primary_cfg = budgets.get("primary", {})
    final_cfg = primary_cfg.get("final_config", "nano")
    proxy_cfg = primary_cfg.get("proxy_config", "nano")
    configs = res.get("configs", {})
    if final_cfg in configs:
        cfg_name = final_cfg
    elif proxy_cfg in configs:
        cfg_name = proxy_cfg
    else:
        # Ad-hoc and quick runs may evaluate only one prompt. Report the
        # simulated config so inner loops still show cycles/token.
        present = [name for name in CONFIGS if name in configs]
        cfg_name = present[-1] if present else proxy_cfg
    cfg = configs.get(cfg_name)
    run_idx = int(primary_cfg.get("run_index", 0))
    run = None
    if cfg and len(cfg.get("runs", [])) > run_idx:
        run = cfg["runs"][run_idx]

    tech = res.get("tech", {}) or {}
    target_freq_mhz = float(budgets.get("tech", {}).get("target_freq_mhz", 500.0))
    target_period_ns = float(budgets.get("tech", {}).get(
        "target_period_ns", 1000.0 / target_freq_mhz if target_freq_mhz else 0.0))
    # Fixed target clock from budgets (100 MHz / 10 ns). If the budgets
    # file carries an optional freq_ladder ([max_period_ns, freq_mhz]
    # rungs), the measured critical path picks the scored clock from it;
    # otherwise the scored clock equals the target clock. Runs without a
    # valid critical path fall back to the target clock.
    freq_ladder = sorted(
        ((float(p), float(f)) for p, f in
         (budgets.get("tech", {}).get("freq_ladder") or [])),
        key=lambda rung: rung[0])

    seq_len = int((run or {}).get("seq_len", 0) or 0)
    cycles = int((run or {}).get("cycles", 0) or 0)
    read_beats = int((run or {}).get("read_beats", 0) or 0)
    write_beats = int((run or {}).get("write_beats", 0) or 0)
    cycles_per_token = (cycles / seq_len) if seq_len and cycles else 0.0
    bytes_per_token = (float(MEM_PORT_BYTES) * (read_beats + write_beats) / seq_len) \
        if seq_len else 0.0

    critical_path_ns = float(tech.get("critical_path_ns", 0.0) or 0.0)
    if freq_ladder:
        rung = next((f for p, f in freq_ladder
                     if 0 < critical_path_ns <= p), None)
        scored_freq_mhz = rung if rung is not None else freq_ladder[-1][1]
    else:
        scored_freq_mhz = target_freq_mhz
    tokens_per_sec_scored = (scored_freq_mhz * 1e6 / cycles_per_token) \
        if cycles_per_token > 0 else 0.0
    tokens_per_sec_target = (target_freq_mhz * 1e6 / cycles_per_token) \
        if cycles_per_token > 0 else 0.0

    return {
        "config": cfg_name,
        "run_index": run_idx,
        "seq_len": seq_len,
        "cycles": cycles,
        "cycles_per_token": round(cycles_per_token, 3),
        "read_beats": read_beats,
        "write_beats": write_beats,
        "dram_bytes_per_token": round(bytes_per_token, 3),
        "critical_path_ns": critical_path_ns,
        "target_freq_mhz": target_freq_mhz,
        "target_period_ns": target_period_ns,
        "scored_freq_mhz": scored_freq_mhz,
        "tokens_per_sec_scored_clock": round(tokens_per_sec_scored, 6),
        "tokens_per_sec_target_clock": round(tokens_per_sec_target, 6),
    }


def score_report(res) -> dict:
    """Trim the in-memory result to the on-disk score.json schema: exactly
    six top-level sections (workloads / correctness / throughput / timing /
    area / sram). Everything else (integrity, audit, lint, randreset,
    latency sweep, netlist, selfmodel, perf_model, cell histograms,
    budgets) is reported on stdout only. Sections whose inputs were not
    produced (synthesis skipped or failed) are present with value null.
    """
    t = res.get("throughput", {}) or {}
    meta = res.get("meta", {}) or {}
    cfg = (res.get("configs", {}) or {}).get(t.get("config")) or {}

    runs = []
    for r in cfg.get("runs", []) or []:
        runs.append({
            "index": r.get("prompt"),
            "seq_len": r.get("seq_len", 0),
            "cycles": r.get("cycles", 0),
            "cos_min": r.get("cos_min", 0.0),
            "argmax_agree": r.get("argmax_agree", 0.0),
            "run_ok": bool(r.get("run_ok", r.get("status_ok"))),
            "read_beats": r.get("read_beats", 0),
            "write_beats": r.get("write_beats", 0),
            "roofline_cycles": r.get("roofline_cycles", 0),
        })
    workloads = {
        "seed": meta.get("seed"),
        "group_size": meta.get("group_size"),
        "seq_stretch": meta.get("seq_stretch"),
        "seq_lens": list(cfg.get("seq_lens", []) or []),
        "runs": runs,
    }
    correctness = {
        "pass": bool(cfg.get("pass", False)),
        "argmax_pooled": cfg.get("argmax_pooled", 0.0),
    }
    throughput = {
        "cycles_per_token": t.get("cycles_per_token", 0.0),
        "scored_clock_mhz": t.get("scored_freq_mhz", 0.0),
        "target_clock_mhz": t.get("target_freq_mhz", 0.0),
        "tokens_per_sec_scored": t.get("tokens_per_sec_scored_clock", 0.0),
        "tokens_per_sec_target": t.get("tokens_per_sec_target_clock", 0.0),
    }

    tech = res.get("tech", {}) or {}
    synth = res.get("synth", {}) or {}
    have_tech = bool(tech.get("ok"))
    have_synth = bool(synth.get("ok"))
    timing = None
    if have_tech or have_synth:
        timing = {
            "critical_path_ns": tech.get("critical_path_ns")
            if have_tech else None,
            "levels": synth.get("levels") if have_synth else None,
        }
    area = None
    if have_tech or have_synth:
        logic = tech.get("logic_area_mm2") if have_tech else None
        macro = round(float(synth.get("macro_area_um2", 0.0) or 0.0) / 1e6, 6) \
            if have_synth else None
        area = {
            "logic_area_mm2": logic,
            "macro_area_mm2": macro,
            "total_area_mm2": round(logic + macro, 6)
            if logic is not None and macro is not None else None,
            "ne": synth.get("ne") if have_synth else None,
            "latch_cells": synth.get("latch_cells") if have_synth else None,
        }
    sram = None
    if have_synth:
        bits = int(synth.get("macro_bits", 0) or 0)
        sram = {"macro_bits": bits,
                "macro_mib": round(bits / 8.0 / (1024.0 * 1024.0), 6)}

    return {
        "workloads": workloads,
        "correctness": correctness,
        "throughput": throughput,
        "timing": timing,
        "area": area,
        "sram": sram,
    }


def do_netlist():
    """Generate a synthesized Verilog netlist as a hardware-realism artifact.

    The netlist is not re-simulated in the nano harness; correctness is
    established by RTL simulation, while synthesis, area, SRAM, and timing
    are reported as measurements alongside it.
    """
    files = " ".join([MACRO_BB, MACRO_ROM_BB] + rtl_files())
    netlist = os.path.join(BUILD, "netlist_synth.v")
    script = open(os.path.join(HERE, "synth_netlist.ys")).read()
    script = script.replace("{FILES}", files).replace("{NETLIST}", netlist)
    spath = os.path.join(BUILD, "synth_netlist_gen.ys")
    open(spath, "w").write(script)
    code, out, tmo, dt = run(["yosys", "-s", spath], timeout=3600,
                             log_name="synth_netlist.log")
    ok = code == 0 and not tmo and os.path.exists(netlist)
    res = {"ok": bool(ok), "secs": round(dt, 1),
           "path": os.path.relpath(netlist, ROOT)}
    if not ok:
        res["why"] = "synthesis failed" if code != 0 else "netlist missing"
        res["log_tail"] = out[-2000:]
    return res


def do_randreset(binp, seed, variant, cfg_names=("nano",)):
    """Reset robustness: re-run the nano short run with every
    flop initialized to a pseudo-random value instead of zero
    (+verilator+rand+reset+2). A design with a coherent reset strategy is
    unaffected; one that silently relies on zero-initialized state (a
    simulation artifact real silicon does not provide) diverges. Output
    regions are compared byte-for-byte against the normal RTL runs and the
    match flag is reported as a measurement."""
    detail = {}
    match = True
    for cfg_name in cfg_names:
        prep = prepare_run(cfg_name, seed, 1, variant)
        rrs = (fnv1a64(f"randreset/{seed}/{cfg_name}") % 2147483645) + 1
        r = sim_one(binp, cfg_name, seed, 1, prep, tag="rr",
                    plusargs=("+verilator+rand+reset+2",
                              f"+verilator+seed+{rrs}"))
        detail[cfg_name] = r
        rtl_res = os.path.join(BUILD, f"res_rtl_{prep['key']}.bin")
        rr_res = os.path.join(BUILD, f"res_rr_{prep['key']}.bin")
        if not (os.path.exists(rtl_res) and os.path.exists(rr_res)):
            match = False
            detail[cfg_name]["why"] = "missing result dump"
            continue
        same = open(rtl_res, "rb").read() == open(rr_res, "rb").read()
        detail[cfg_name]["byte_identical"] = bool(same)
        match = match and same
    return {"ok": True, "match": bool(match), "detail": detail}


def do_latency_sweep(binp, seed, variant, base_runs):
    """Latency elasticity: re-run the nano short run with the
    base read latency doubled (48 instead of 24 cycles; jitter and
    back-pressure unchanged). elasticity = cycles(48) / cycles(24). A
    design that keeps enough requests in flight is barely affected
    (ratio near 1.0); one that serializes on each read degrades toward
    2.0. Reported for the R2 realism judgment, not scored."""
    detail = {}
    for cfg_name in ("nano",):
        base = base_runs.get(cfg_name)
        if not base or not base.get("cycles"):
            continue
        prep = prepare_run(cfg_name, seed, 1, variant)
        r = sim_one(binp, cfg_name, seed, 1, prep, tag="hilat",
                    lat_base=LAT_BASE_HI)
        detail[cfg_name] = {
            "cycles_base": base["cycles"], "cycles_hilat": r["cycles"],
            "elasticity": round(r["cycles"] / base["cycles"], 4)
            if r["cycles"] else 0.0,
            "status_magic_ok": r.get("status_magic_ok", r["status_ok"]),
            "protocol_ok": r.get("protocol_ok"),
            "weight_stream_ok": r.get("weight_stream_ok"),
            "run_ok": r.get("run_ok", r["status_ok"]),
            "status_ok": r["status_ok"], "cos_min": r["cos_min"],
        }
    return detail


def do_selfmodel(jobs):
    """Optional bit-exact self-reference model (industry C-model
    discipline): if the submission ships rtl/selfmodel/run.sh, run it as
    `bash run.sh <image.bin> <out.bin>` for every simulated nano workload,
    and compare its int32 logits (little-endian, row-major
    [seq_len, vocab], no padding) bit-exactly against the chip's. Reported
    in score.json as R4 evidence; not scored. The script runs in a scratch
    directory on a copy of the image, with a wall-clock budget."""
    script = os.path.join(ROOT, "rtl", "selfmodel", "run.sh")
    if not os.path.exists(script):
        return {"present": False}
    runs = {}
    all_match = True
    for cfg_name, k, prep in jobs:
        c = prep["cfg"]
        rtl_res = os.path.join(BUILD, f"res_rtl_{prep['key']}.bin")
        entry = {"match": False}
        tmpd = tempfile.mkdtemp(prefix="selfmodel-")
        try:
            img_copy = os.path.join(tmpd, "img.bin")
            shutil.copy(prep["img"], img_copy)
            out_path = os.path.join(tmpd, "out.bin")
            code, _, tmo, dt = run(["bash", script, img_copy, out_path],
                                   timeout=c.wall_secs, cwd=tmpd,
                                   log_name=f"selfmodel_{cfg_name}_{k}.log")
            entry["secs"] = round(dt, 1)
            if code != 0 or tmo:
                entry["why"] = "script failed" if not tmo else "timeout"
            elif not os.path.exists(rtl_res):
                entry["why"] = "no RTL result to compare against"
            elif not os.path.exists(out_path):
                entry["why"] = "script produced no out.bin"
            else:
                chip = parse_result(c, prep["layout"],
                                    open(rtl_res, "rb").read())["logits"]
                raw = np.frombuffer(open(out_path, "rb").read(), dtype="<i4")
                if raw.size != chip.shape[0] * chip.shape[1]:
                    entry["why"] = (f"size mismatch: got {raw.size} int32s, "
                                    f"expected {chip.shape[0] * chip.shape[1]}")
                else:
                    model = raw.reshape(chip.shape).astype(np.int64)
                    entry["match"] = bool(np.array_equal(model, chip))
                    if not entry["match"]:
                        bad = np.argwhere((model != chip).any(axis=1))
                        entry["why"] = (f"first differing row: "
                                        f"{int(bad[0][0]) if len(bad) else -1}")
        finally:
            shutil.rmtree(tmpd, ignore_errors=True)
        runs[f"{cfg_name}/{k}"] = entry
        all_match = all_match and entry["match"]
    return {"present": True, "all_match": bool(all_match), "runs": runs}


def parse_perf_model(cfg_results):
    """Predicted-vs-measured performance model: REPORT.md may carry a
    fenced ```json perf-model``` block with
    {"cycles_per_token": {"<config>": <number>, ...}} — the design's own
    analytical prediction of steady-state cycles per token on the long
    (bandwidth-preserving) run. Compared against measured cycles/seq_len
    per config and reported for the judge (architecture-understanding
    evidence, R2/R3); not scored."""
    rp = os.path.join(ROOT, "REPORT.md")
    if not os.path.exists(rp):
        return {"present": False}
    m = re.search(r"```[^\n]*perf-model[^\n]*\n(.*?)```",
                  open(rp, encoding="utf-8", errors="replace").read(), re.S)
    if not m:
        return {"present": False}
    try:
        pred = json.loads(m.group(1)).get("cycles_per_token", {})
    except ValueError as e:
        return {"present": True, "error": f"unparseable perf-model block: {e}"}
    per_cfg = {}
    for name, r in cfg_results.items():
        run0 = next((x for x in r.get("runs", []) if x.get("prompt") == 0),
                    None)
        if not run0 or not run0.get("cycles") or not run0.get("seq_len"):
            continue
        meas = run0["cycles"] / run0["seq_len"]
        p = pred.get(name)
        per_cfg[name] = {"measured_cpt": round(meas, 1)}
        if isinstance(p, (int, float)) and p > 0:
            per_cfg[name].update(predicted_cpt=float(p),
                                 rel_err=round(abs(p - meas) / meas, 4))
    return {"present": True, "per_config": per_cfg}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", default=None,
                    help="comma list; nano-only task default is nano")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--seeds-file", default=None)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--skip-synth", action="store_true")
    ap.add_argument("--jobs", type=int, default=4,
                    help="parallel simulations (default 4)")
    ap.add_argument("--out", default=os.path.join(BUILD, "score.json"))
    a = ap.parse_args()

    os.makedirs(BUILD, exist_ok=True)
    variant = {}
    seed = a.seed
    if a.seeds_file:
        variant = json.load(open(a.seeds_file))
        seed = variant["seed"]
    if seed is None:
        variant = json.load(open(os.path.join(HERE, "seeds_public.json")))
        seed = variant["seed"]

    if a.configs:
        ladder = a.configs.split(",")
    elif a.quick:
        ladder = ["nano"]
    else:
        ladder = list(DEFAULT_LADDER)
    # runs per config: index 0 = long sequence, 1 = short. quick = short only
    run_idx = [1] if a.quick else [0, 1]

    budgets = load_budgets()
    res = {"meta": {"seed": seed, "configs": ladder, "quick": a.quick,
                    "group_size": int(variant.get("group_size", 128)),
                    "seq_stretch": float(variant.get("seq_stretch", 1.0)),
                    "time": time.strftime("%Y-%m-%d %H:%M:%S")},
           "budgets": budgets,
           "integrity": integrity_check()}
    print(f"[integrity] {'OK' if res['integrity']['ok'] else 'MODIFIED: ' + str(res['integrity']['modified'])}")

    res["audit"] = audit_check()
    print(f"[audit] ok={res['audit']['ok']}"
          + (f" HARD={res['audit']['hard']}" if res['audit']['hard'] else "")
          + (f" flags={len(res['audit']['soft'])}" if res['audit']['soft'] else ""))

    res["lint"] = do_lint()
    print(f"[lint] errors={res['lint']['errors']} "
          f"warnings={res['lint']['warnings']} "
          f"gate_ok={res['lint']['gate_ok']} "
          f"(<= {res['lint']['max_warnings']} warnings required)")

    b = build_sim(rtl_files() + [MACRO_SIM, MACRO_ROM_SIM], "rtl")
    res["build"] = b
    print(f"[build] ok={b['ok']} ({b['secs']}s)")

    cfg_results = {}
    jobs = []
    res["randreset"] = {"skipped": True, "match": True}
    res["latency_sweep"] = {}
    if b["ok"]:
        # prepare images + goldens serially (heavy numpy, shared cache) ...
        for cfg in ladder:
            for k in run_idx:
                print(f"[prep] {cfg} run {k} ...", flush=True)
                jobs.append((cfg, k, prepare_run(cfg, seed, k, variant)))
        # ... then simulate in parallel
        results = {}
        with ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
            futs = {ex.submit(sim_one, b["bin"], cfg, seed, k, prep): (cfg, k)
                    for (cfg, k, prep) in jobs}
            for fut in futs:
                cfg, k = futs[fut]
                p = fut.result()
                results[(cfg, k)] = p
                print(f"[sim] {cfg} run {k} (seq_len={p['seq_len']}): "
                      f"cos_min={p['cos_min']:.4f} "
                      f"argmax={p['argmax_agree']:.3f} "
                      f"cycles={p['cycles']} "
                      f"run_ok={p.get('run_ok', p.get('status_ok'))} "
                      f"(status={p.get('status_magic_ok', p.get('status_ok'))} "
                      f"weights={p.get('weight_stream_ok')})", flush=True)
        for cfg in ladder:
            runs = [results[(cfg, k)] for k in run_idx]
            ceff = effective_config(cfg, variant)
            cfg_results[cfg] = {
                "runs": runs,
                "seq_lens": list(ceff.seq_lens),
                "pass": scoring.config_pass(runs),
                "argmax_pooled": round(scoring.pooled_argmax(runs), 6),
                "cycles": runs[0]["cycles"],       # long run
                "roofline_cycles": roofline_cycles(ceff),
            }
            print(f"[cfg] {cfg}: pass={cfg_results[cfg]['pass']} "
                  f"argmax_pooled={cfg_results[cfg]['argmax_pooled']:.4f}")
        if not a.quick:
            rr_cfgs = tuple(c for c in ("nano",) if c in ladder)
            if rr_cfgs:
                res["randreset"] = do_randreset(b["bin"], seed, variant,
                                                rr_cfgs)
                print(f"[randreset] match={res['randreset']['match']} "
                      f"({' + '.join(rr_cfgs)}, random initial state)")
            res["latency_sweep"] = do_latency_sweep(
                b["bin"], seed, variant,
                {c: results.get((c, 1)) for c in ("nano",)})
            for c, d in res["latency_sweep"].items():
                print(f"[latency] {c}: elasticity={d['elasticity']} "
                      f"(cycles {d['cycles_base']} -> {d['cycles_hilat']} "
                      f"at 2x base latency)")
    res["configs"] = cfg_results
    res["meta"]["seq_lens"] = {c: cfg_results[c]["seq_lens"]
                               for c in cfg_results}

    if a.skip_synth or a.quick:
        res["synth"] = {"ok": False, "skipped": True, "ne": 0, "levels": 0}
        res["tech"] = {"ok": False, "skipped": True}
        res["netlist"] = {"ok": False, "skipped": True}
    else:
        res["synth"] = do_synth()
        print(f"[synth] ok={res['synth']['ok']} NE={res['synth'].get('ne')} "
              f"levels={res['synth'].get('levels')} "
              f"(rtl-level {res['synth'].get('levels_rtl')}) "
              f"latch_cells={res['synth'].get('latch_cells')} "
              f"modules={res['synth'].get('modules', {}).get('count')}")
        res["tech"] = do_tech(budgets)
        if res["tech"].get("ok"):
            print(f"[tech] {res['tech'].get('lib')}: "
                  f"logic_area={res['tech'].get('logic_area_um2', 0) / 1e6:.3f}mm2 "
                  f"critical_path={res['tech'].get('critical_path_ns')}ns "
                  f"fmax~{res['tech'].get('fmax_mhz_est')}MHz "
                  f"(pre-layout estimate)")
        res["netlist"] = do_netlist()
        print(f"[netlist] ok={res['netlist']['ok']} "
              f"path={res['netlist'].get('path')}")

    # agent-shell hook runs LAST among the checks: every metric above is
    # already held in memory, so the script cannot influence them.
    res["selfmodel"] = {"present": False, "skipped": True} if a.quick \
        else do_selfmodel(jobs)
    if res["selfmodel"].get("present"):
        print(f"[selfmodel] all_match={res['selfmodel'].get('all_match')}")
    res["perf_model"] = parse_perf_model(cfg_results)
    if res["perf_model"].get("present"):
        print(f"[perf-model] {json.dumps(res['perf_model'].get('per_config', res['perf_model']))}")

    res["throughput"] = compute_throughput(res, budgets)
    t = res["throughput"]
    print(f"[throughput] config={t['config']} "
          f"cycles/token={t['cycles_per_token']} "
          f"tokens/s={t['tokens_per_sec_scored_clock']} "
          f"@ {t['scored_freq_mhz']}MHz scored "
          f"({t['tokens_per_sec_target_clock']} @ {t['target_freq_mhz']}MHz target)")
    # score.json is strictly the six-section measurement report; the full
    # res dict stays in memory for the stdout summary below.
    json.dump(score_report(res), open(a.out, "w"), indent=2)

    synth, tech = res["synth"], res["tech"]
    area_budget, sram_budget_mib = resource_budget_for_config(budgets,
                                                              t["config"])
    print("\n=========== MEASUREMENT REPORT ===========")
    print(f" seed={res['meta']['seed']} group_size={res['meta']['group_size']} "
          f"seq_stretch={res['meta']['seq_stretch']} quick={res['meta']['quick']}")
    print(f" integrity   : "
          f"{'OK' if res['integrity']['ok'] else 'FAIL ' + str(res['integrity']['modified'])}")
    print(f" audit       : {'OK' if res['audit']['ok'] else 'FAIL'}")
    print(f" lint        : errors={res['lint']['errors']} "
          f"warnings={res['lint']['warnings']} "
          f"gate_ok={res['lint']['gate_ok']} "
          f"(informational, <= {res['lint']['max_warnings']} warnings)")
    for name, cr in cfg_results.items():
        print(f" [{name}] correctness pass={cr['pass']} "
              f"argmax_pooled={cr['argmax_pooled']:.4f} "
              f"seq_lens={cr['seq_lens']}")
        for r in cr["runs"]:
            print(f"   run {r['prompt']}: seq_len={r['seq_len']} cycles={r['cycles']} "
                  f"cos_min={r['cos_min']:.4f} argmax_agree={r['argmax_agree']:.3f} "
                  f"run_ok={r.get('run_ok', r.get('status_ok'))}")
            print(f"          read_beats={r['read_beats']} "
                  f"write_beats={r['write_beats']} "
                  f"roofline_cycles={r.get('roofline_cycles', 0)}")
    if tech.get("ok"):
        print(f" timing      : critical_path={tech.get('critical_path_ns')}ns "
              f"levels={synth.get('levels', 0)} "
              f"(scored clock {t['scored_freq_mhz']}MHz, "
              f"target {t['target_freq_mhz']}MHz)")
    elif tech.get("skipped"):
        print(" timing      : skipped (no synth)")
    else:
        print(" timing      : synth/tech FAILED")
    if synth.get("ok") or tech.get("ok"):
        logic_mm2 = float(tech.get("logic_area_mm2", 0.0) or 0.0)
        macro_mm2 = float(synth.get("macro_area_um2", 0.0) or 0.0) / 1e6
        sram_mib = float(synth.get("mem_bits", 0) or 0) / 8.0 / (1024.0 * 1024.0)
        print(f" area        : logic={logic_mm2:.6f}mm2 "
              f"+ macros={macro_mm2:.6f}mm2 "
              f"= {logic_mm2 + macro_mm2:.6f}mm2 (budget {area_budget}mm2) "
              f"NE={synth.get('ne', 0)} latch_cells={synth.get('latch_cells', 0)}")
        print(f" SRAM        : {synth.get('mem_bits', 0)} macro bits "
              f"= {sram_mib:.6f} MiB (budget {sram_budget_mib} MiB)")
    elif synth.get("skipped"):
        print(" area/SRAM   : skipped (no synth)")
    else:
        print(" area/SRAM   : synth FAILED")
    print(f" cycles/token: {t['cycles_per_token']} "
          f"({t['config']} run {t['run_index']}, seq_len={t['seq_len']})")
    print(f" tokens/s    : {t['tokens_per_sec_scored_clock']:.4f} "
          f"@ scored {t['scored_freq_mhz']}MHz | "
          f"{t['tokens_per_sec_target_clock']:.4f} "
          f"@ target {t['target_freq_mhz']}MHz")
    if not res["randreset"].get("skipped"):
        print(f" rand-reset  : match={res['randreset'].get('match')}")
    print(f" -> {a.out}")
    # CI contract: nonzero exit unless the run is clean end to end.
    # Always required: frozen files intact, audit clean, lint gate, and
    # every config's correctness verdict PASS. randreset and a shipped
    # selfmodel gate whenever they actually ran. The synthesis trio
    # (synth/tech/netlist) is required only when synthesis was requested
    # (i.e. not --quick/--skip-synth).
    ok = bool(res["integrity"].get("ok")) \
        and bool(res.get("audit", {}).get("ok", True)) \
        and bool(res.get("lint", {}).get("gate_ok", True))
    cfgs = res.get("configs", {}) or {}
    ok = ok and bool(cfgs) \
        and all(bool(c.get("pass", False)) for c in cfgs.values())
    rr = res.get("randreset", {}) or {}
    if rr and not rr.get("skipped"):
        ok = ok and bool(rr.get("match", False))
    sm = res.get("selfmodel", {}) or {}
    if sm.get("present"):
        ok = ok and bool(sm.get("all_match", False))
    if not (a.skip_synth or a.quick):
        ok = ok and bool(res.get("synth", {}).get("ok")) \
            and bool(res.get("tech", {}).get("ok")) \
            and bool(res.get("netlist", {}).get("ok"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
