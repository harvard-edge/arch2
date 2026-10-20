#!/usr/bin/env python3
"""Benchmark kernels in each problem folder.

For each problem, benchmarks PyTorch eager, torch.compile, input kernel,
and optimized kernel. Uses torch._inductor.runtime.benchmarking for consistent
measurements, reporting the mean runtime over 100 repetitions (with >1s warmup).

Usage:
  python benchmark.py                    # all problems
  python benchmark.py 43_Max_Pooling_3D  # single problem
  python benchmark.py --json out.json    # save results
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
import json
import math
import sys
from pathlib import Path
from typing import Any, Callable

import torch
import triton.testing as tt

# Make sure GPUs are fully warmed up before running benchmarks
WARMUP_ITERS = 500
BENCHMARK_ITERS = 100


def _import(path: Path):
    name = f"mod_{hashlib.md5(str(path).encode()).hexdigest()}"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _bench(fn: Callable) -> float:
    """Mean runtime in ms (100 reps, 500 warmup)."""
    return tt.do_bench(fn, warmup=WARMUP_ITERS, rep=BENCHMARK_ITERS, return_mode="mean")


def _extract_params(model: torch.nn.Module) -> dict[str, Any]:
    """Extract weight/bias/stride/padding/etc. from model layers."""
    params: dict[str, Any] = {}
    for _, m in model.named_modules():
        for attr in ("weight", "bias"):
            val = getattr(m, attr, None)
            if val is not None and isinstance(val, (torch.Tensor, torch.nn.Parameter)):
                params.setdefault(attr, val)
        for attr in (
            "kernel_size",
            "stride",
            "padding",
            "dilation",
            "output_padding",
            "groups",
            "eps",
        ):
            val = getattr(m, attr, None)
            if val is not None:
                params.setdefault(
                    attr, val[0] if isinstance(val, (tuple, list)) else val
                )
    return params


def _bind_kernel(kernel_path: Path, model: torch.nn.Module) -> Callable:
    """Load kernel_function, binding model params where the signature expects them."""
    kfn = getattr(_import(kernel_path), "kernel_function")
    sig = inspect.signature(kfn)
    param_names = list(sig.parameters.keys())
    model_params = _extract_params(model)

    model_param_keys = {
        "weight",
        "bias",
        "kernel_size",
        "stride",
        "padding",
        "dilation",
        "output_padding",
        "groups",
        "eps",
    }

    # Check if signature uses *args/**kwargs (e.g. kernel_function(x, *args, **kwargs))
    has_var = any(
        p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        for p in sig.parameters.values()
    )

    if not has_var and not model_param_keys.intersection(param_names):
        return kfn

    if has_var and model_params:
        # Signature uses *args — pass model params as kwargs
        def bound_var(*args):
            return kfn(*args, **model_params)

        return bound_var

    def bound(*args):
        kwargs = {}
        pos = 0
        for name in param_names:
            if name in model_params:
                kwargs[name] = model_params[name]
            elif pos < len(args):
                kwargs[name] = args[pos]
                pos += 1
        return kfn(**kwargs)

    return bound


def _prepare(problem_dir: Path):
    """Load problem.py → (model, inputs)."""
    mod = _import(problem_dir / "problem.py")
    init_inputs = getattr(mod, "get_init_inputs", lambda: [])()
    if not isinstance(init_inputs, (tuple, list)):
        init_inputs = [init_inputs]

    model = mod.Model(*init_inputs).cuda().eval()
    has_params = any(p.numel() > 0 for p in model.parameters())

    inputs = mod.get_inputs()
    if not isinstance(inputs, (tuple, list)):
        inputs = (inputs,)

    dtype = torch.bfloat16
    if has_params:
        model = model.to(dtype)
    inputs = tuple(
        (
            inp.cuda().to(dtype)
            if isinstance(inp, torch.Tensor) and inp.is_floating_point()
            else inp.cuda() if isinstance(inp, torch.Tensor) else inp
        )
        for inp in inputs
    )
    return model, inputs


def benchmark_one(problem_dir: Path) -> dict[str, Any]:
    name = problem_dir.name
    result: dict[str, Any] = {"problem": name}

    try:
        model, inputs = _prepare(problem_dir)
    except Exception as e:
        print(f"  SKIP {name}: {e}")
        return {
            **result,
            "eager_ms": None,
            "compile_ms": None,
            "input_kernel_ms": None,
            "optimized_ms": None,
        }

    # Eager
    try:
        with torch.inference_mode():
            model(*inputs)
        result["eager_ms"] = _bench(lambda: model(*inputs))
    except Exception as e:
        print(f"  {name} eager: {e}")
        result["eager_ms"] = None

    # torch.compile
    try:
        compiled = torch.compile(model)
        with torch.inference_mode():
            compiled(*inputs)
        result["compile_ms"] = _bench(lambda: compiled(*inputs))
    except Exception as e:
        print(f"  {name} compile: {e}")
        result["compile_ms"] = None

    # Input kernel / Optimized kernel
    for key, filename in [
        ("input_kernel_ms", "input_kernel.py"),
        ("optimized_ms", "optimized_kernel_beam_search.py"),
    ]:
        path = problem_dir / filename
        if not path.exists():
            result[key] = None
            continue
        try:
            kfn = _bind_kernel(path, model)
            with torch.inference_mode():
                kfn(*inputs)
            result[key] = _bench(lambda: kfn(*inputs))
        except Exception as e:
            print(f"  {name} {filename}: {e}")
            result[key] = None

    return result


def _fmt(v: float | None) -> str:
    return f"{v:.3f}" if v is not None else "N/A"


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark KernelAgent artifacts")
    parser.add_argument("problem_dirs", nargs="*")
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    if args.problem_dirs:
        dirs = [base / d for d in args.problem_dirs]
    else:
        dirs = sorted(
            (d for d in base.iterdir() if d.is_dir() and (d / "problem.py").exists()),
            key=lambda d: (
                (
                    int(d.name.split("_")[0])
                    if d.name.split("_")[0].isdigit()
                    else float("inf")
                ),
                d.name,
            ),
        )

    print(f"Benchmarking {len(dirs)} problems on {torch.cuda.get_device_name()}\n")

    results = []
    for i, d in enumerate(dirs):
        print(f"[{i + 1}/{len(dirs)}] {d.name}")
        r = benchmark_one(d)
        results.append(r)
        speedup = (
            f"{r['compile_ms'] / r['optimized_ms']:.2f}x"
            if r.get("compile_ms") and r.get("optimized_ms")
            else ""
        )
        print(
            f"  eager={_fmt(r['eager_ms'])}  compile={_fmt(r['compile_ms'])}  "
            f"input={_fmt(r['input_kernel_ms'])}  opt={_fmt(r['optimized_ms'])}  {speedup}\n"
        )

    # Summary table
    print("=" * 80)
    for r in results:
        speedup = (
            f"{r['compile_ms'] / r['optimized_ms']:.2f}x"
            if r.get("compile_ms") and r.get("optimized_ms")
            else ""
        )
        print(f"  {r['problem']:<60} {_fmt(r['optimized_ms']):>8}  {speedup:>6}")

    if args.json:
        with open(args.json, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nSaved to {args.json}")


if __name__ == "__main__":
    main()
