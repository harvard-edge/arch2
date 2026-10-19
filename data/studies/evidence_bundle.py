"""Small, shared integrity helpers for mined evidence bundles."""
import datetime
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform

ROOT = Path(__file__).resolve().parents[2]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_sources(here):
    manifest = json.loads((here / "source_manifest.json").read_text())
    for receipt in manifest["files"]:
        assert sha256(here / receipt["path"]) == receipt["sha256"], receipt["path"]
    return manifest


def record_build(here, checks, verification_scope=None):
    files = [
        p
        for p in here.rglob("*")
        if p.is_file()
        and p.name != "build_receipt.json"
        and "__pycache__" not in p.parts
    ]
    record = {
        "built_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "python": platform.python_version(),
        "packages": {
            p: importlib.metadata.version(p)
            for p in ("numpy", "matplotlib", "requests")
        },
        "shared_dependencies": {
            str(p.relative_to(ROOT)): sha256(p)
            for p in (
                ROOT / "book/_python/plots.py",
                ROOT / "book/_styles/arch2.mplstyle",
                Path(__file__),
            )
        },
        "checks": checks,
        "files": {str(p.relative_to(here)): sha256(p) for p in sorted(files)},
        "verification_scope": verification_scope
        or "Local extraction and calculations from retained public records; no GPU benchmark rerun or independent replication.",
    }
    (here / "build_receipt.json").write_text(json.dumps(record, indent=2) + "\n")
    for path in sorted(here.glob("figure.*")):
        print(path.relative_to(ROOT))
