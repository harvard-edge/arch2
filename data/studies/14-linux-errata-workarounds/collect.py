#!/usr/bin/env python3
"""Retain historical Linux arm64 workaround source at ten pinned release commits."""
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import requests

HERE = Path(__file__).resolve().parent
TAGS = [
    "v4.4",
    "v4.9",
    "v4.14",
    "v4.19",
    "v5.4",
    "v5.10",
    "v5.15",
    "v6.1",
    "v6.6",
    "v6.12",
]
REPO = "torvalds/linux"


def get(url):
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    return r


def main():
    HERE.joinpath("raw").mkdir(parents=True, exist_ok=True)
    pins_path = HERE / "pins.json"
    if pins_path.exists():
        pins = json.loads(pins_path.read_text())
    else:

        def resolve(tag):
            response = get(f"https://api.github.com/repos/{REPO}/commits/{tag}")
            payload = response.json()
            (HERE / "raw" / f"{tag}-commit.json").write_bytes(response.content)
            return {
                "tag": tag,
                "commit": payload["sha"],
                "date": payload["commit"]["committer"]["date"],
            }

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            pins = list(pool.map(resolve, TAGS))
        pins_path.write_text(json.dumps(pins, indent=2) + "\n")

    def download(pin):
        records = []
        paths = ["arch/arm64/Kconfig", "arch/arm64/kernel/cpu_errata.c", "COPYING"]
        if pin["tag"] == "v6.12":
            paths += [
                "Documentation/arch/arm64/silicon-errata.rst",
                "LICENSES/preferred/GPL-2.0",
            ]
        for path in paths:
            url = f"https://raw.githubusercontent.com/{REPO}/{pin['commit']}/{path}"
            dest = HERE / "raw" / pin["tag"] / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                dest.write_bytes(get(url).content)
            records.append(
                {
                    "path": str(dest.relative_to(HERE)),
                    "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
                    "url": url,
                    "commit": pin["commit"],
                    "tag": pin["tag"],
                }
            )
        print("RETAINED", pin["tag"], pin["commit"], flush=True)
        return records

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        files = [r for records in pool.map(download, pins) for r in records]
    for path in [pins_path, *sorted((HERE / "raw").glob("*-commit.json"))]:
        files.append(
            {
                "path": str(path.relative_to(HERE)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "origin": "Release commit resolution through GitHub API",
            }
        )
    manifest = {
        "collected_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "repository": REPO,
        "selection": "Ten predeclared releases, v4.4 through v6.12. Historical source comparison, not a current-release inventory.",
        "files": files,
    }
    prior_path = HERE / "source_manifest.json"
    if prior_path.exists():
        prior = json.loads(prior_path.read_text())
        assert {x["path"]: x["sha256"] for x in prior["files"]} == {
            x["path"]: x["sha256"] for x in files
        }
    else:
        prior_path.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
