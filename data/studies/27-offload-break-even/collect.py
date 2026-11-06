#!/usr/bin/env python3
"""Measure where accelerator offload breaks even against an optimized host.

One invocation is one run (fresh process). Runs in one session share its host state. It times FP32 n x n
matrix products on the host CPU (vendor BLAS through torch.matmul / torch.bmm)
and on the Apple GPU through the PyTorch MPS backend, and writes every timed
repetition to raw/run-<id>.csv plus a host-state record raw/run-<id>.host.json.

Panel (a), one n x n product, three arms:
  cpu_single      torch.matmul on the host; synchronous.
  mps_resident    operands already on the MPS device; kernel only, then
                  torch.mps.synchronize().
  mps_copy        A.to('mps'), B.to('mps'), matmul, C.cpu(); synchronized.
Panel (b), sixteen independent n x n products, three arms:
  cpu_bmm         torch.bmm on the host over a (16, n, n) batch.
  mps_16_launch   sixteen separate torch.matmul launches on resident operands,
                  waiting for each with torch.mps.synchronize() before the next.
  mps_bmm         one torch.bmm launch on resident operands, synchronized.

For each n the six arms run in a random order (recorded), each arm is warmed
up, then timed R times with time.perf_counter(). Output allocation is inside
the timed region for every arm, as it is for an ordinary caller.
"""
import argparse
import csv
import datetime as dt
import json
import platform
import random
import re
import subprocess
import sys
import time
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
SIZES = [16, 24, 32, 48, 64, 96, 128, 192, 256, 384, 512, 768, 1024, 1536, 2048, 3072]
BATCH = 16
ARMS = {
    "a": ["cpu_single", "mps_resident", "mps_copy"],
    "b": ["cpu_bmm", "mps_16_launch", "mps_bmm"],
}


def sh(cmd):
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=20
        ).stdout.strip()
    except Exception as exc:  # noqa: BLE001
        return f"unavailable: {exc}"


def host_state(args):
    cfg = torch.__config__.show()
    blas = re.search(r"BLAS_INFO=(\w+)", cfg)
    return {
        "run_id": args.run_id,
        "timestamp_start": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "cpu_model": sh(["sysctl", "-n", "machdep.cpu.brand_string"]),
        "cpu_logical": sh(["sysctl", "-n", "hw.ncpu"]),
        "cpu_perflevel0_cores": sh(["sysctl", "-n", "hw.perflevel0.physicalcpu"]),
        "cpu_perflevel1_cores": sh(["sysctl", "-n", "hw.perflevel1.physicalcpu"]),
        "memory_bytes": sh(["sysctl", "-n", "hw.memsize"]),
        "os": f"{platform.system()} {platform.mac_ver()[0]} (Darwin {platform.release()})",
        "python": sys.version.split()[0],
        "torch_version": torch.__version__,
        "torch_num_threads": torch.get_num_threads(),
        "torch_blas_info": blas.group(1) if blas else "unknown",
        "torch_config_show": cfg,
        "torch_parallel_info": torch.__config__.parallel_info(),
        "mps_available": torch.backends.mps.is_available(),
        "power_source": sh(["pmset", "-g", "batt"]),
        "thermal": sh(["pmset", "-g", "therm"]),
        "sizes": args.sizes,
        "batch": BATCH,
        "reps": args.reps,
        "warmup": args.warmup,
        "seed": args.seed,
        "command": " ".join(sys.argv),
    }


def timed(fn, reps, warmup):
    for _ in range(warmup):
        fn()
    out = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        out.append(time.perf_counter() - t0)
    return out


def make_arms(n, dev):
    a = torch.randn(n, n)
    b = torch.randn(n, n)
    a16 = torch.randn(BATCH, n, n)
    b16 = torch.randn(BATCH, n, n)
    ad, bd = a.to(dev), b.to(dev)
    a16d, b16d = a16.to(dev), b16.to(dev)
    torch.mps.synchronize()

    def cpu_single():
        return torch.matmul(a, b)

    def mps_resident():
        c = torch.matmul(ad, bd)
        torch.mps.synchronize()
        return c

    def mps_copy():
        c = torch.matmul(a.to(dev), b.to(dev)).cpu()
        torch.mps.synchronize()
        return c

    def cpu_bmm():
        return torch.bmm(a16, b16)

    def mps_16_launch():
        cs = []
        for i in range(BATCH):
            cs.append(torch.matmul(a16d[i], b16d[i]))
            torch.mps.synchronize()
        return cs

    def mps_bmm():
        c = torch.bmm(a16d, b16d)
        torch.mps.synchronize()
        return c

    return {
        "cpu_single": ("a", cpu_single),
        "mps_resident": ("a", mps_resident),
        "mps_copy": ("a", mps_copy),
        "cpu_bmm": ("b", cpu_bmm),
        "mps_16_launch": ("b", mps_16_launch),
        "mps_bmm": ("b", mps_bmm),
    }


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--run-id", type=int, required=True)
    p.add_argument("--reps", type=int, default=31)
    p.add_argument("--warmup", type=int, default=5)
    p.add_argument("--seed", type=int, default=None, help="default: 1000 + run_id")
    p.add_argument("--sizes", type=int, nargs="+", default=SIZES)
    p.add_argument("--out", type=Path, default=HERE / "raw")
    args = p.parse_args()
    if args.seed is None:
        args.seed = 1000 + args.run_id
    if not torch.backends.mps.is_available():
        sys.exit("MPS backend not available")
    torch.manual_seed(args.seed)
    rng = random.Random(args.seed)
    dev = torch.device("mps")
    args.out.mkdir(parents=True, exist_ok=True)
    state = host_state(args)

    rows = []
    t_start = time.perf_counter()
    for n in args.sizes:
        arms = make_arms(n, dev)
        order = list(arms)
        rng.shuffle(order)
        for pos, name in enumerate(order):
            panel, fn = arms[name]
            samples = timed(fn, args.reps, args.warmup)
            for rep, s in enumerate(samples):
                rows.append(
                    {
                        "run_id": args.run_id,
                        "n": n,
                        "panel": panel,
                        "arm": name,
                        "arm_order": pos,
                        "rep": rep,
                        "seconds": f"{s:.9e}",
                    }
                )
            med = sorted(samples)[len(samples) // 2]
            print(
                f"run {args.run_id} n={n:5d} {name:14s} order={pos} median={med:.3e} s",
                flush=True,
            )
        del arms
        torch.mps.empty_cache()
    state["elapsed_seconds"] = round(time.perf_counter() - t_start, 2)
    state["timestamp_end"] = (
        dt.datetime.now().astimezone().isoformat(timespec="seconds")
    )

    csv_path = args.out / f"run-{args.run_id}.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (args.out / f"run-{args.run_id}.host.json").write_text(
        json.dumps(state, indent=2) + "\n"
    )
    print(f"wrote {csv_path} ({len(rows)} rows) in {state['elapsed_seconds']} s")


if __name__ == "__main__":
    main()
