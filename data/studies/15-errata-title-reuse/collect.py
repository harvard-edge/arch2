#!/usr/bin/env python3
"""Reuse the versioned vendor extraction in study 13, retaining its identity."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "13-errata-dispositions"
sys.path.insert(0, str(HERE.parent))
from evidence_bundle import verify_sources


def main():
    verify_sources(SOURCE)
    files = []
    for name in ("derived/errata.csv", "derived/sources.csv", "source_manifest.json"):
        src, dest = SOURCE / name, HERE / "raw" / Path(name).name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            assert (
                dest.read_bytes() == src.read_bytes()
            ), "Source changed; version a new analysis"
        else:
            shutil.copy2(src, dest)
        files.append(
            {
                "path": str(dest.relative_to(HERE)),
                "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
                "origin": "../13-errata-dispositions/" + name,
            }
        )
    path = HERE / "source_manifest.json"
    if not path.exists():
        path.write_text(
            json.dumps(
                {
                    "collected_utc": datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat(),
                    "files": files,
                    "shared_raw_source_package": "../13-errata-dispositions",
                    "policy": "Keep studies 13 and 15 together; the vendor PDF bytes are stored once in study 13.",
                },
                indent=2,
            )
            + "\n"
        )


if __name__ == "__main__":
    main()
