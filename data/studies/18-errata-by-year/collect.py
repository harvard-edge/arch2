#!/usr/bin/env python3
"""Verify frozen inputs; recover missing public sources only by exact hash."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent


def main():
    manifest = json.loads((HERE / "source_manifest.json").read_text())
    for entry in manifest["files"]:
        path = (HERE / entry["path"]).resolve()
        if path.exists():
            assert (
                hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
            ), path
            continue
        if not entry.get("url") or not path.is_relative_to(HERE):
            raise SystemExit(
                f"Missing retained metadata/shared input: {path}; restore the original package."
            )
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / "response"
            subprocess.run(
                [
                    "curl",
                    "--fail",
                    "--silent",
                    "--show-error",
                    "--location",
                    "--max-time",
                    "60",
                    entry["url"],
                    "--output",
                    str(candidate),
                ],
                check=True,
            )
            if hashlib.sha256(candidate.read_bytes()).hexdigest() != entry["sha256"]:
                raise SystemExit(
                    f'Upstream bytes changed; refusing to replace frozen source: {entry["url"]}'
                )
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(candidate.read_bytes())
    print(f'Verified {len(manifest["files"])} frozen source/metadata files.')


if __name__ == "__main__":
    main()
