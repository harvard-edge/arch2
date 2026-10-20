"""Fresh, bounded RTL simulation of one dequantizer block, not a KPU evaluation.

The independent Python oracle uses integer arithmetic on constructed teaching
inputs. The C++ driver executes the snapshotted RTL with Verilator and compares
its output words with those supplied oracle values. No learning or GDS claim is
made. The frozen KPU harness is neither imported nor modified.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import signal
import subprocess
import time
from typing import Any


VECTOR_SEED = 20261017
BENCH = Path(__file__).with_name("assets") / "dequant_tb.cpp"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def constructed_vectors() -> list[dict[str, Any]]:
    """Valid block inputs; scalar oracle is independent of RTL implementation.

    Covers both nibbles, negative/zero/positive int16 scales, saturation and
    nearby values, one/two quantization groups, and selected row sizes up to 256.
    These are teaching fixtures, not sampled model weights or workload traces.
    """
    rng = random.Random(VECTOR_SEED)
    rows = []
    for index, (d, group) in enumerate([(4, 4), (64, 64), (128, 128),
                                       (128, 64), (256, 128)] * 3):
        ng = d // group
        if index < 5:
            scales = [32767, -32768][:ng]
            zeros = [0, 15][:ng]
            q = [0, 15, 8, 7] * (d // 4)
        elif index < 10:
            scales = [16384, 13107][:ng]
            zeros = [8, 5][:ng]
            q = [0, 15, 8, 7, 10, 1, 14, 5] * (d // 8) if d >= 8 else [0, 15, 8, 7]
        else:
            scales = [rng.choice([0, -1, 1, -16384, 16383, 16384, 32767, -32768])
                      for _ in range(ng)]
            zeros = [rng.randrange(16) for _ in range(ng)]
            q = [rng.randrange(16) for _ in range(d)]
        expected = []
        for lane, nibble in enumerate(q):
            g = lane // group
            product = (nibble - zeros[g]) * scales[g] * (2 ** 14)
            signed = max(-(2 ** 31), min(2 ** 31 - 1, product))
            expected.append(signed & 0xFFFFFFFF)
        rows.append({"d": d, "group": group, "buffer": index % 16,
                     "schedule": index % 4, "scales": scales, "zeros": zeros,
                     "q": q, "expected_u32": expected})
    return rows


def _run(command: list[str], cwd: Path, log: Path, timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    with log.open("w") as output:
        try:
            process = subprocess.Popen(command, cwd=cwd, stdout=output,
                                       stderr=subprocess.STDOUT, start_new_session=True)
        except OSError as exc:
            output.write(str(exc) + "\n")
            return {"command": command, "returncode": None, "timed_out": False,
                    "elapsed_s": time.perf_counter() - started, "log": str(log),
                    "error": str(exc)}
        timed_out = False
        try:
            process.wait(timeout=max(0.001, timeout))
        except subprocess.TimeoutExpired:
            timed_out = True
            # Terminate compiler children as well as the Verilator driver.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
    return {"command": command, "returncode": process.returncode,
            "timed_out": timed_out, "elapsed_s": time.perf_counter() - started,
            "log": str(log)}


def run_probe(candidate_path: Path, output_dir: Path, timeout_s: float = 120,
              *, bench_path: Path | None = None) -> dict[str, Any]:
    """Snapshot one candidate and execute a fresh build and actual RTL test.

    ``output_dir`` must be absent or empty; no earlier result is reused.
    ``timeout_s`` bounds the combined version/build/simulation subprocess time.
    An unavailable compiler, timeout, failed build, or failed check cannot pass.
    """
    candidate_path, output_dir = Path(candidate_path).resolve(), Path(output_dir).resolve()
    if not candidate_path.is_file():
        raise FileNotFoundError(candidate_path)
    if not math.isfinite(timeout_s) or timeout_s <= 0:
        raise ValueError("timeout_s must be finite and positive")
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise ValueError(f"probe output directory must be empty: {output_dir}")
    started = time.perf_counter()
    started_utc = datetime.now(timezone.utc).isoformat()
    deadline = started + timeout_s
    source = output_dir / "candidate.v"
    bench = output_dir / "dequant_tb.cpp"
    shutil.copyfile(candidate_path, source)
    shutil.copyfile(bench_path or BENCH, bench)
    rows = constructed_vectors()
    vector_json = output_dir / "vectors.json"
    vector_json.write_text(json.dumps({"origin": "constructed teaching inputs",
                                      "seed": VECTOR_SEED, "rows": rows}, indent=2) + "\n")
    vector_text = output_dir / "vectors.txt"
    with vector_text.open("w") as output:
        output.write(f"{len(rows)}\n")
        for row in rows:
            output.write(" ".join(str(row[k]) for k in ("d", "group", "buffer", "schedule")) + "\n")
            for field in ("scales", "zeros", "q", "expected_u32"):
                output.write(" ".join(map(str, row[field])) + "\n")
    receipt: dict[str, Any] = {
        "schema_version": 1, "mode": "fresh", "scope": "single msh_deq RTL block simulation",
        "evidence_type": "fresh_rtl_simulation", "ok": False, "status": "unavailable",
        "source_origin": str(candidate_path), "output_dir": str(output_dir),
        "candidate_sha256": _sha256(source), "bench_sha256": _sha256(bench),
        "probe_sha256": _sha256(Path(__file__)),
        "started_at_utc": started_utc,
        "vectors_sha256": _sha256(vector_json), "vector_text_sha256": _sha256(vector_text),
        "vector_provenance": {"origin": "constructed teaching inputs", "seed": VECTOR_SEED,
                              "rows": len(rows), "expected_lanes": sum(r["d"] for r in rows),
                              "oracle": "clamp_int32((q-z)*signed_int16_scale*16384)"},
        "limits": ["Not complete KPU workload correctness", "Not a physical implementation",
                   "Constructed finite vectors do not establish exhaustive equivalence",
                   "Y write port has no ready input; only input-stream backpressure is exercised"],
        "timeout_s": timeout_s, "peak_memory_bytes": None,
        "peak_memory_note": "Not measured by this probe",
    }
    compiler = shutil.which("verilator")
    if compiler:
        version = _run([compiler, "--version"], output_dir, output_dir / "version.log",
                       min(5, max(0.001, deadline - time.perf_counter())))
        receipt["version_probe"] = version
        receipt["tool_version"] = (output_dir / "version.log").read_text().strip()
        receipt["status"] = "timeout" if version["timed_out"] else "tool_failed"
        if version["returncode"] == 0 and not version["timed_out"]:
            command = [compiler, "--cc", "--exe", "--build", "-j", "2", "-O1",
                       "-Wno-fatal", "--top-module", "msh_deq", "--Mdir",
                       str(output_dir / "obj"), "-o", "dequant_probe", str(source), str(bench)]
            build = _run(command, output_dir, output_dir / "build.log",
                         max(0.001, deadline - time.perf_counter()))
            receipt["build"] = build
            receipt["status"] = "timeout" if build["timed_out"] else "build_failed"
            binary = output_dir / "obj" / "dequant_probe"
            if build["returncode"] == 0 and not build["timed_out"] and binary.is_file():
                simulation = _run([str(binary), str(vector_text)], output_dir,
                                  output_dir / "simulation.log",
                                  max(0.001, deadline - time.perf_counter()))
                receipt["simulation"] = simulation
                receipt["binary_sha256"] = _sha256(binary)
                for line in (output_dir / "simulation.log").read_text().splitlines():
                    if line.startswith("PROBE_JSON "):
                        try:
                            receipt["checks"] = json.loads(line[len("PROBE_JSON "):])
                        except json.JSONDecodeError:
                            receipt["parse_error"] = "malformed simulator summary"
                checks = receipt.get("checks", {})
                receipt["ok"] = bool(simulation["returncode"] == 0
                                     and not simulation["timed_out"] and checks.get("ok") is True
                                     and checks.get("rows_completed") == len(rows)
                                     and checks.get("lanes_checked") == sum(r["d"] for r in rows)
                                     and checks.get("stream_stall_cycles", 0) > 0
                                     and checks.get("producer_bubble_cycles", 0) > 0)
                receipt["status"] = (
                    "passed" if receipt["ok"] else
                    "timeout" if simulation["timed_out"] else
                    "simulation_failed" if simulation["returncode"] not in (0, 1) or not checks else
                    "check_failed"
                )
    else:
        receipt["error"] = "verilator not found on PATH; no installation attempted"
    receipt["total_elapsed_s"] = time.perf_counter() - started
    receipt["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    receipt["generated_files"] = sorted(str(p) for p in output_dir.rglob("*") if p.is_file())
    receipt["generated_files"].append(str(output_dir / "receipt.json"))
    (output_dir / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()
    result = run_probe(args.candidate, args.output, args.timeout)
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
