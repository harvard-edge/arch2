#!/usr/bin/env python3
"""Version a fresh vendor snapshot and report every departure from study 01."""
import concurrent.futures
import csv
import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ORIGINAL = ROOT / "data/studies/01-silicon-errata-archaeology"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    (HERE / "raw/pdf").mkdir(parents=True, exist_ok=True)
    for name in ("sources.csv", "families.csv", "errata.csv"):
        dest = HERE / "raw" / name
        if not dest.exists():
            shutil.copy2(ORIGINAL / name, dest)
    parser = HERE / "raw/mine_cpu_errata.py"
    if not parser.exists():
        shutil.copy2(ROOT / "data/scrapers/mine_cpu_errata.py", parser)
    sources = list(
        csv.DictReader(
            l for l in (HERE / "raw/sources.csv").open() if not l.startswith("#")
        )
    )
    collected = datetime.datetime.now(datetime.timezone.utc).isoformat()
    prior_path = HERE / "source_manifest.json"
    pinned = (
        {r["path"]: r["sha256"] for r in json.loads(prior_path.read_text())["files"]}
        if prior_path.exists()
        else {}
    )

    def fetch(row):
        dest = HERE / "raw/pdf" / (re.sub(r"[^A-Za-z0-9]", "", row["family"]) + ".pdf")
        if not dest.exists():
            subprocess.run(
                [
                    "curl",
                    "-fsSL",
                    "--retry",
                    "2",
                    "--max-time",
                    "90",
                    "-A",
                    "Mozilla/5.0",
                    row["url"],
                    "-o",
                    str(dest),
                ],
                check=True,
            )
        assert dest.read_bytes().startswith(b"%PDF"), dest
        if pinned:
            assert digest(dest) == pinned[str(dest.relative_to(HERE))], dest
        matches = digest(dest) == row["sha256"]
        print(
            "MATCH" if matches else "CHANGED SINCE STUDY 01", row["family"], flush=True
        )
        return {
            "path": str(dest.relative_to(HERE)),
            "sha256": digest(dest),
            "url": row["url"],
            "family": row["family"],
            "document_number": row["doc_number"],
            "prior_revision": row["revision"],
            "prior_document_date": row["doc_date"],
            "prior_sha256": row["sha256"],
            "matches_study_01": matches,
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        files = list(pool.map(fetch, sources))
    for path in sorted((HERE / "raw").glob("*")):
        if path.is_file():
            files.append(
                {
                    "path": str(path.relative_to(HERE)),
                    "sha256": digest(path),
                    "origin": "Local study 01 input or extraction script at base commit 055b7c66162128223dd397b4223c9ad686fb617d",
                }
            )
    manifest = {
        "collected_utc": collected,
        "files": files,
        "policy": "This is a new snapshot; each departure from study 01 is recorded. Later runs verify this manifest and never overwrite source bytes.",
        "redistribution": "Vendor PDFs retained locally for audit; no redistribution license inferred.",
    }
    if not prior_path.exists():
        prior_path.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
