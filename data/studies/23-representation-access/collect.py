#!/usr/bin/env python3
"""Verify retained pinned public archives and extract them to the local cache."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import urllib.request

HERE = Path(__file__).resolve().parent
CACHE = HERE / ".cache" / "repos"


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    manifest = json.loads((HERE / "source_manifest.json").read_text())
    for item in manifest["files"]:
        p = HERE / item["path"]
        if not p.exists() and p.name.endswith(".tar.gz"):
            # The URL is derived from the repository and full commit in the source manifest.
            repo, commit = p.name[:-7].rsplit("__", 1)
            org, name = repo.split("__", 1)
            url = f"https://github.com/{org}/{name}/archive/{commit}.tar.gz"
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_suffix(p.suffix + ".download")
            urllib.request.urlretrieve(url, tmp)
            tmp.replace(p)
        if not p.exists():
            raise SystemExit(f'missing frozen input: {item["path"]}')
        actual = sha256(p)
        if actual != item["sha256"]:
            raise SystemExit(f'input hash mismatch: {item["path"]}: {actual}')
    CACHE.mkdir(parents=True, exist_ok=True)
    for archive in (HERE / "raw").glob("*.tar.gz"):
        parts = archive.name[:-7].split("__")
        repo = parts[1]
        target = CACHE / repo
        if target.exists():
            shutil.rmtree(target)
        with tarfile.open(archive, "r:gz") as tf:
            names = tf.getnames()
            roots = {Path(n).parts[0] for n in names if Path(n).parts}
            if len(roots) != 1 or any(
                Path(n).is_absolute() or ".." in Path(n).parts for n in names
            ):
                raise SystemExit(f"unsafe or unexpected archive layout: {archive.name}")
            staging = CACHE / (repo + ".extracting")
            if staging.exists():
                shutil.rmtree(staging)
            staging.mkdir()
            tf.extractall(staging, filter="data")
            extracted = staging / next(iter(roots))
            extracted.rename(target)
            staging.rmdir()
    print(
        f'verified {len(manifest["files"])} frozen inputs; extracted {len(list((HERE/"raw").glob("*.tar.gz")))} pinned archives'
    )


if __name__ == "__main__":
    main()
