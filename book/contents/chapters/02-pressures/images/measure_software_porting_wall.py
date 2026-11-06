"""Measure the source-code footprints plotted in fig-ch09-software-porting-wall.

This is the retained measurement harness for the three datasets
  book/contents/chapters/02-pressures/data/fig-ch09-money-plot-software-porting-wall/chapter9-cutlass-porting-wall.csv
  book/contents/chapters/02-pressures/data/fig-ch09-money-plot-software-porting-wall/chapter9-triton-narrow-waist.csv
  book/contents/chapters/02-pressures/data/fig-ch09-money-plot-software-porting-wall/chapter9-vllm-kernel-fragmentation.csv
and of book/contents/chapters/02-pressures/data/fig-ch09-money-plot-software-porting-wall/chapter9-cutlass-v3.6-step-files.csv, which itemizes the CUTLASS
architecture-header step from v3.5.0 to v3.6.0 for the prose in chapter 2.

Tags are a selection, not every release. v3.5.1 is included because it falls between the
two tags of the largest CUTLASS step. Each row records the commit its tag resolved to, since
a tag can move. Clones are not retained; those commits make them refetchable.

For each release tag it makes a shallow clone (git clone --depth 1 --branch TAG) into
CACHE_DIR, lists tracked files with `git ls-files`, and counts newline characters in files
with the extensions below. Release dates come from the tag's commit date (`git log -1
--format=%cs`). A file that cannot be read stops the run. Rerun through the logged wrapper
from the repository root, expecting about 60 to 900 s on a fresh cache:

    python3 data/run_study.py book/contents/chapters/02-pressures/images --expected 60 900 \\
        --reason "..." -- python3 measure_software_porting_wall.py CACHE_DIR

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
           The backend directory buckets include vendored SDK headers, examples, and tests.
           They are path-based counts, not comparable measures of compiler implementation
           or porting effort. The figure therefore plots their combined source-tree total.
  vLLM     attention_loc csrc/attention/
           quant_loc     csrc/quantization/
           moe_loc       csrc/moe/
           other_csrc_loc the rest of csrc/, a residual that spans many directories
           largest_csrc_subdir the csrc/ subdirectory holding the most lines at that tag,
                               with largest_csrc_subdir_lines lines
  Step file distinct_line_forms counts unique lines in a file at v3.6.0 after stripping
            whitespace and replacing every digit run with 0 and every register token
            (%name, %%name, {name}, {{name}}) with R. It is a repetition measure. It does
            not show whether a file was generated.
"""

import collections
import csv
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
DATA = REPO_ROOT / "book/contents/chapters/02-pressures/data/fig-ch09-money-plot-software-porting-wall"
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
            "v3.5.1",
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
    return sum((path / f).read_bytes().count(b"\n") for f in files)


def under(files, *prefixes):
    return [f for f in files if f.startswith(prefixes)]


def date(path: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(path), "log", "-1", "--format=%cs"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def commit(path: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def line_forms(body: bytes) -> int:
    forms = set()
    for line in body.decode("utf-8", "replace").splitlines():
        line = re.sub(r"\{\{?\s*\w+\s*\}?\}", "R", line)
        line = re.sub(r"%%?[A-Za-z_]\w*", "R", line)
        forms.add(re.sub(r"\d+", "0", "".join(line.split())))
    return len(forms)


def step_files(cache: Path, tags=("v3.5.0", "v3.5.1", "v3.6.0")):
    """Lines per architecture header at the tags of the largest CUTLASS step."""
    slug = REPOS["cutlass"][0]
    trees = [checkout(cache, "cutlass", slug, t) for t in tags]
    lines = []
    for p in trees:
        arch = under(tracked(p), "include/cutlass/arch/", "include/cute/arch/")
        lines.append({f: loc(p, [f]) for f in arch})
    rows = []
    for f in sorted(set().union(*lines)):
        counts = [m.get(f, 0) for m in lines]
        if len(set(counts)) == 1:
            continue
        body = (trees[-1] / f).read_bytes() if f in lines[-1] else b""
        rows.append(
            {
                "file": f,
                "lines_v3_5_0": counts[0],
                "lines_v3_5_1": counts[1],
                "lines_v3_6_0": counts[2],
                "change_v3_5_0_to_v3_6_0": counts[2] - counts[0],
                "distinct_line_forms_v3_6_0": line_forms(body),
            }
        )
    return sorted(rows, key=lambda r: -r["change_v3_5_0_to_v3_6_0"])


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
                "commit": commit(p),
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
                "commit": commit(p),
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
        per_dir = collections.Counter()
        for f in csrc:
            parts = f.split("/")
            if len(parts) > 2:
                per_dir[parts[1]] += loc(p, [f])
        largest, largest_lines = per_dir.most_common(1)[0]
        rows["vllm"].append(
            {
                "tag": tag,
                "commit": commit(p),
                "tag_commit_date": date(p),
                "attention_loc": loc(p, att),
                "quant_loc": loc(p, q),
                "moe_loc": loc(p, moe),
                "other_csrc_loc": loc(p, csrc) - loc(p, att) - loc(p, q) - loc(p, moe),
                "largest_csrc_subdir": f"csrc/{largest}",
                "largest_csrc_subdir_lines": largest_lines,
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
    path = DATA / fname
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(HEADER.format(date=today, slug=slug, ext=" ".join(CODE_EXT)))
        if name == "triton":
            fh.write(
                "# Buckets follow directories, not equivalent kinds of engineering work: backend trees include\n"
                "# vendored SDK headers, examples, and tests; pre-v3 NVIDIA lowering is counted in shared_cpp_loc.\n"
                "# The figure sums the four measured buckets rather than comparing shared versus backend code.\n"
            )
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(fname, len(rows), "rows", hashlib.sha256(path.read_bytes()).hexdigest())
    for row in rows:
        if "commit" in row:
            print(" ", row["tag"], row["commit"])


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
    write(
        step_files(cache),
        "cutlass",
        REPOS["cutlass"][0],
        "chapter9-cutlass-v3.6-step-files.csv",
        today,
    )
    print("wrote 4 datasets")
