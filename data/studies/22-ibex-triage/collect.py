#!/usr/bin/env python3
"""Verify or recover the pinned public sources for the Ibex triage packet.

Existing source bytes are never overwritten. Missing downloads are staged in a
temporary directory and installed only after their pinned SHA-256 matches.
The Markdown issue body is derived from the retained API JSON, never scraped
from the rendered GitHub page.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "source_manifest.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def issue_body_from_json(payload: bytes) -> bytes:
    issue = json.loads(payload.decode("utf-8"))
    body = issue.get("body")
    if not isinstance(body, str):
        raise ValueError("Issue API JSON has no string body")
    return (body.rstrip() + "\n").encode("utf-8")


def fetch(url: str) -> bytes:
    result = subprocess.run(
        [
            "curl",
            "--fail",
            "--location",
            "--silent",
            "--show-error",
            "--max-time",
            "90",
            url,
        ],
        check=True,
        capture_output=True,
    )
    return result.stdout


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = manifest.get("files", [])
    if not entries:
        raise SystemExit("Source manifest contains no files")
    paths = [item["path"] for item in entries]
    if len(paths) != len(set(paths)):
        raise SystemExit("Source manifest has duplicate paths")
    # Validate every existing file before any recovery write. A changed file is
    # preserved in place and stops collection instead of being silently reset.
    for item in entries:
        target = HERE / item["path"]
        if target.is_file() and sha256(target.read_bytes()) != item["sha256"]:
            raise SystemExit(f"Refusing to overwrite changed source bytes: {target}")

    for item in entries:
        target = HERE / item["path"]
        if target.is_file() or item.get("derived_from"):
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="ibex-source-recovery-", dir=HERE
        ) as tmp:
            staged = Path(tmp) / target.name
            payload = fetch(item["url"])
            staged.write_bytes(payload)
            if sha256(staged.read_bytes()) != item["sha256"]:
                raise SystemExit(
                    f"Refusing upstream source whose bytes differ from the manifest: {item['url']}"
                )
            os.replace(staged, target)
            print(target.relative_to(HERE))

    # Derive the issue body from the saved JSON. If the JSON itself was missing,
    # the loop above fetched and hash-verified it before this point.
    for item in entries:
        if not item.get("derived_from"):
            continue
        target = HERE / item["path"]
        source = HERE / item["derived_from"]
        if not source.is_file():
            raise SystemExit(
                f"Cannot derive {item['path']}; missing {item['derived_from']}"
            )
        rendered = issue_body_from_json(source.read_bytes())
        if sha256(rendered) != item["sha256"]:
            raise SystemExit(
                f"Issue-body derivation hash does not match the manifest: {item['path']}"
            )
        if target.is_file():
            if target.read_bytes() != rendered:
                raise SystemExit(f"Issue body differs from saved API JSON: {target}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="ibex-body-recovery-", dir=HERE) as tmp:
            staged = Path(tmp) / target.name
            staged.write_bytes(rendered)
            if sha256(staged.read_bytes()) != item["sha256"]:
                raise SystemExit(
                    f"Refusing derived body with unexpected bytes: {target}"
                )
            os.replace(staged, target)
            print(target.relative_to(HERE))

    print(f"Verified or recovered {len(entries)} manifest entries: {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
