#!/usr/bin/env python3
"""Extract per-run records for the matched H100 MLPerf Training submissions.

Fetches every result log for the six matched workloads from the MLCommons
results repositories at pinned commits, checks each file against the git blob
SHA recorded in the pinned tree, and writes one row per submitted run to
mlperf-h100-runs.csv. Non-converged runs are kept. The raw logs total about
21 MB and are not retained here; the commit and blob SHA in each row make them
refetchable. Copies of the two mutable results sheets and of the scaling and
system records are retained under mlperf-h100-sources/.

    python3 collect_mlperf_h100_runs.py [--cache DIR]

Requires gh (for the pinned trees) and curl. Standard library otherwise.
"""

import argparse
import csv
import hashlib
import json
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "mlperf-h100-runs.csv"
SOURCES = HERE / "mlperf-h100-sources"

ROUNDS = {
    "v2.1": ("training_results_v2.1", "158189d4cbfbee366c10da1f0f086c85d8f15b5f"),
    "v3.0": ("training_results_v3.0", "63e326c400f5d8bb8c6070a9ab08332d4931152e"),
}
# Directory names are the submission's own. Repository names map to the
# workloads as labeled in fig-ch09-mlperf-software-dividend.csv.
WORKLOADS = {
    "bert": ("BERT", 10),
    "rnnt": ("RNN-T", 10),
    "resnet": ("ResNet-50 v1.5", 5),
    "unet3d": ("3D U-Net", 40),
    "maskrcnn": ("Mask R-CNN", 5),
    "ssd": ("RetinaNet", 5),
}
SYSTEM = {
    ("v2.1", w): "dgxh100_preview" for w in WORKLOADS
} | {
    ("v3.0", w): "dgxh100_ngc23.04_mxnet" if w in ("resnet", "unet3d")
    else "dgxh100_ngc23.04_pytorch"
    for w in WORKLOADS
}
RESULT_ID = {
    ("v2.1", w): "2.1-2091" for w in WORKLOADS
} | {
    ("v3.0", w): "3.0-2062" if w in ("resnet", "unet3d") else "3.0-2064"
    for w in WORKLOADS
}
MLLOG = re.compile(r":::MLLOG (\{.*\})\s*$")
FIELDS = [
    "round", "result_id", "workload", "system", "file", "repo", "commit",
    "git_blob_sha", "log_sha256", "log_bytes", "run_start_ms", "run_stop_ms",
    "time_min", "status", "eval_count", "last_eval_value", "last_eval_position",
    "position_key", "global_batch_size", "submission_platform",
]


def gh_json(path):
    out = subprocess.run(["gh", "api", path], capture_output=True, text=True,
                         check=True, stdin=subprocess.DEVNULL).stdout
    return json.loads(out)


def directory_blobs(repo, commit, directory):
    """Walk to one directory at the pinned commit; a recursive root tree truncates."""
    sha = commit
    for part in directory.split("/"):
        tree = gh_json(f"repos/mlcommons/{repo}/git/trees/{sha}")
        sha = next(e["sha"] for e in tree["tree"] if e["path"] == part)
    tree = gh_json(f"repos/mlcommons/{repo}/git/trees/{sha}")
    if tree.get("truncated"):
        raise RuntimeError(f"truncated tree: {repo}/{directory}")
    return {e["path"]: e["sha"] for e in tree["tree"] if e["type"] == "blob"}


def fetch(repo, commit, path, blob, target):
    if not target.exists():
        url = f"https://raw.githubusercontent.com/mlcommons/{repo}/{commit}/{path}"
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["curl", "-sSf", "--retry", "5", "-m", "280", "-o", str(target), url],
                       check=True, stdin=subprocess.DEVNULL)
    data = target.read_bytes()
    actual = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
    if actual != blob:
        target.unlink()
        raise RuntimeError(f"blob mismatch: {path}")
    return data


def parse(data):
    start = stop = status = None
    last = None
    evals = 0
    meta = {}
    for line in data.decode("utf-8", "replace").splitlines():
        match = MLLOG.search(line)
        if not match:
            continue
        try:
            event = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        key = event.get("key")
        if key == "run_start" and start is None:
            start = event["time_ms"]
        elif key == "run_stop":
            stop = event["time_ms"]
            status = event.get("metadata", {}).get("status")
        elif key == "eval_accuracy":
            evals += 1
            last = event
        elif key in ("global_batch_size", "submission_platform"):
            meta[key] = event["value"]
    position = position_key = ""
    if last:
        md = last.get("metadata", {})
        for name in ("epoch_num", "train_samples", "epoch_count"):
            if name in md:
                position, position_key = md[name], name
                break
    return {
        "run_start_ms": start, "run_stop_ms": stop,
        "time_min": f"{(stop - start) / 60000:.6f}",
        "status": status, "eval_count": evals,
        "last_eval_value": last["value"] if last else "",
        "last_eval_position": position, "position_key": position_key,
        "global_batch_size": meta.get("global_batch_size", ""),
        "submission_platform": meta.get("submission_platform", ""),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=Path(tempfile.mkdtemp()))
    args = parser.parse_args()
    jobs = []
    for version, (repo, commit) in ROUNDS.items():
        for work, (label, count) in WORKLOADS.items():
            system = SYSTEM[(version, work)]
            blobs = directory_blobs(repo, commit, f"NVIDIA/results/{system}/{work}")
            names = sorted(n for n in blobs if n.startswith("result_"))
            if len(names) != count:
                raise RuntimeError(f"{version} {work}: {len(names)} logs, expected {count}")
            extra = sorted(set(blobs) - set(names))
            for name in extra:  # scaling.json is the only other file expected
                path = f"NVIDIA/results/{system}/{work}/{name}"
                data = fetch(repo, commit, path, blobs[name],
                             args.cache / version / work / name)
                SOURCES.mkdir(exist_ok=True)
                (SOURCES / f"{version}-{work}-{name}").write_bytes(data)
            for name in names:
                jobs.append((version, repo, commit, work, label, system, name, blobs[name]))

    def run(job):
        version, repo, commit, work, label, system, name, blob = job
        path = f"NVIDIA/results/{system}/{work}/{name}"
        data = fetch(repo, commit, path, blob, args.cache / version / work / name)
        return {
            "round": version, "result_id": RESULT_ID[(version, work)],
            "workload": label, "system": system, "file": f"{work}/{name}",
            "repo": repo, "commit": commit, "git_blob_sha": blob,
            "log_sha256": hashlib.sha256(data).hexdigest(), "log_bytes": len(data),
        } | parse(data)

    with ThreadPoolExecutor(6) as pool:
        rows = list(pool.map(run, jobs))
    with open(OUT, "w", newline="", encoding="utf-8") as handle:
        handle.write("# One row per submitted run, extracted from raw MLLOG result files by collect_mlperf_h100_runs.py.\n")
        handle.write("# time_min is run_stop minus run_start. Status 'aborted' or any non-success value marks a non-converged run.\n")
        handle.write("# last_eval_position is the position of the final logged eval, in the unit named by position_key.\n")
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {OUT} ({len(rows)} runs)")


if __name__ == "__main__":
    main()
