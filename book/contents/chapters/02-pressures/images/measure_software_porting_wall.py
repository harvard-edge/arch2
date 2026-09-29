"""Measure the source-code footprints plotted in fig-ch09-software-porting-wall.

This is the retained measurement harness for the three datasets
  data/datasets/chapter9-cutlass-porting-wall.csv
  data/datasets/chapter9-triton-narrow-waist.csv
  data/datasets/chapter9-vllm-kernel-fragmentation.csv

For each release tag it makes a shallow clone (git clone --depth 1 --branch TAG) into
CACHE_DIR, lists tracked files with `git ls-files`, and counts newline characters in files
with the extensions below. Release dates come from the tag's commit date (`git log -1
--format=%cs`). Rerun with:

    python3 measure_software_porting_wall.py [CACHE_DIR]

Bucket definitions (paths are relative to the repository root; a file counts once):
  CUTLASS  arch_loc    include/cutlass/arch/ + include/cute/arch/
           warp_tb_loc include/cutlass/gemm/warp/ + include/cutlass/gemm/threadblock/
           shared_loc  the rest of include/
           inline_ptx  occurrences of the literal "asm volatile" in include/
  Triton   nvidia_backend_loc third_party/nvidia/
           amd_backend_loc    third_party/amd/
           python_loc         python/ (excluding the two backend trees)
           shared_cpp_loc     include/ + lib/ (C++, TableGen; the shared compiler)
           Before v3.0 the NVIDIA-specific lowering lived inside lib/ and is counted as shared.
  vLLM     attention_loc csrc/attention/
           quant_loc     csrc/quantization/
           moe_loc       csrc/moe/
           other_csrc_loc the rest of csrc/
"""

import csv
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
DATA = REPO_ROOT / "data" / "datasets"
CODE_EXT = (".h", ".hpp", ".cuh", ".cu", ".cpp", ".cc", ".c", ".inl", ".py", ".td")

REPOS = {
    "cutlass": (
        "NVIDIA/cutlass",
        [
            "v2.0.0",
            "v2.5.0",
            "v2.10.0",
            "v3.0.0",
            "v3.5.0",
            "v3.6.0",
            "v4.0.0",
            "v4.7.0",
        ],
    ),
    "triton": (
        "triton-lang/triton",
        ["v1.0", "v2.0.0", "v2.1.0", "v3.0.0", "v3.2.0", "v3.5.0", "v3.7.0"],
    ),
    "vllm": (
        "vllm-project/vllm",
        [
            "v0.1.0",
            "v0.2.0",
            "v0.3.0",
            "v0.4.0",
            "v0.6.0",
            "v0.15.0",
            "v0.20.0",
            "v0.27.0",
        ],
    ),
}


def checkout(cache: Path, name: str, slug: str, tag: str) -> Path:
    path = cache / f"{name}-{tag}"
    if not (path / ".git").exists():
        subprocess.run(
            [
                "git",
                "-c",
                "advice.detachedHead=false",
                "clone",
                "-q",
                "--depth",
                "1",
                "--branch",
                tag,
                f"https://github.com/{slug}.git",
                str(path),
            ],
            check=True,
        )
    return path


def tracked(path: Path) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(path), "ls-files"], capture_output=True, text=True, check=True
    ).stdout
    return [f for f in out.splitlines() if f.endswith(CODE_EXT)]


def loc(path: Path, files) -> int:
    total = 0
    for f in files:
        try:
            total += (path / f).read_bytes().count(b"\n")
        except OSError:
            pass
    return total


def under(files, *prefixes):
    return [f for f in files if f.startswith(prefixes)]


def date(path: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(path), "log", "-1", "--format=%cs"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def measure(cache: Path):
    rows = {}
    slug, tags = REPOS["cutlass"]
    rows["cutlass"] = []
    for tag in tags:
        p = checkout(cache, "cutlass", slug, tag)
        fs = tracked(p)
        inc = under(fs, "include/")
        arch = under(inc, "include/cutlass/arch/", "include/cute/arch/")
        wt = under(
            inc, "include/cutlass/gemm/warp/", "include/cutlass/gemm/threadblock/"
        )
        asm = sum((p / f).read_bytes().count(b"asm volatile") for f in inc)
        rows["cutlass"].append(
            {
                "tag": tag,
                "tag_commit_date": date(p),
                "arch_loc": loc(p, arch),
                "warp_tb_loc": loc(p, wt),
                "shared_loc": loc(p, inc) - loc(p, arch) - loc(p, wt),
                "inline_ptx_asm_volatile": asm,
            }
        )
    slug, tags = REPOS["triton"]
    rows["triton"] = []
    for tag in tags:
        p = checkout(cache, "triton", slug, tag)
        fs = tracked(p)
        nv = under(fs, "third_party/nvidia/")
        amd = under(fs, "third_party/amd/")
        py = [f for f in under(fs, "python/") if f not in set(nv) | set(amd)]
        shared = under(fs, "include/", "lib/")
        rows["triton"].append(
            {
                "tag": tag,
                "tag_commit_date": date(p),
                "shared_cpp_loc": loc(p, shared),
                "nvidia_backend_loc": loc(p, nv),
                "amd_backend_loc": loc(p, amd),
                "python_loc": loc(p, py),
            }
        )
    slug, tags = REPOS["vllm"]
    rows["vllm"] = []
    for tag in tags:
        p = checkout(cache, "vllm", slug, tag)
        fs = tracked(p)
        csrc = under(fs, "csrc/")
        att, q, moe = (
            under(csrc, "csrc/attention/"),
            under(csrc, "csrc/quantization/"),
            under(csrc, "csrc/moe/"),
        )
        rows["vllm"].append(
            {
                "tag": tag,
                "tag_commit_date": date(p),
                "attention_loc": loc(p, att),
                "quant_loc": loc(p, q),
                "moe_loc": loc(p, moe),
                "other_csrc_loc": loc(p, csrc) - loc(p, att) - loc(p, q) - loc(p, moe),
            }
        )
    return rows


HEADER = (
    "# Measured {date} by book/contents/chapters/02-pressures/images/measure_software_porting_wall.py\n"
    "# (shallow clone of each tag of github.com/{slug}; newline counts of tracked files with extensions\n"
    "# {ext}; bucket definitions are in the script docstring). Line counts describe implementation\n"
    "# footprint, not maintenance effort. tag_commit_date is the commit date of the tagged commit.\n"
)


def write(rows, name, slug, fname, today):
    with open(DATA / fname, "w", encoding="utf-8", newline="") as fh:
        fh.write(HEADER.format(date=today, slug=slug, ext=" ".join(CODE_EXT)))
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    import datetime

    cache = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path(os.environ.get("TMPDIR", "/tmp")) / "porting-wall-repos"
    )
    cache.mkdir(parents=True, exist_ok=True)
    rows = measure(cache)
    today = datetime.date.today().isoformat()
    write(
        rows["cutlass"],
        "cutlass",
        REPOS["cutlass"][0],
        "chapter9-cutlass-porting-wall.csv",
        today,
    )
    write(
        rows["triton"],
        "triton",
        REPOS["triton"][0],
        "chapter9-triton-narrow-waist.csv",
        today,
    )
    write(
        rows["vllm"],
        "vllm",
        REPOS["vllm"][0],
        "chapter9-vllm-kernel-fragmentation.csv",
        today,
    )
    print("wrote 3 datasets")
