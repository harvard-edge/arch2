#!/usr/bin/env python3
"""Verify frozen inputs; recover missing files only if their hashes still match."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((HERE / "source_manifest.json").read_text())
    urls = {
        x["local_copy"]: x["url"] for x in manifest["sources"] if x.get("local_copy")
    }
    for row in manifest["files"]:
        path = HERE / row["path"]
        if not path.exists():
            url = urls[row["path"]]
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="arch2-evidence-") as temporary:
                candidate = Path(temporary) / "download"
                if url.endswith("/zip"):
                    with candidate.open("wb") as output:
                        subprocess.run(["gh", "api", url], stdout=output, check=True)
                else:
                    subprocess.run(
                        ["curl", "-fLsS", "--retry", "2", url, "-o", str(candidate)],
                        check=True,
                    )
                if digest(candidate) != row["sha256"]:
                    raise ValueError(
                        f"Source changed; frozen file was not replaced: {row['path']}"
                    )
                path.write_bytes(candidate.read_bytes())
                print(f"Recovered {path}")
        if digest(path) != row["sha256"]:
            raise ValueError(f"Frozen source hash mismatch: {row['path']}")
    print(f"Verified {len(manifest['files'])} frozen inputs; no snapshot refresh.")


if __name__ == "__main__":
    main()
