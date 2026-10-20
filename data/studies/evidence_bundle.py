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


def verify_sources(here, allow_missing_gitignored=False):
    manifest = json.loads((here / "source_manifest.json").read_text())
    verified = 0
    for receipt in manifest["files"]:
        target = here / receipt["path"]
        if not target.exists() and allow_missing_gitignored:
            continue
        assert target.exists(), f"missing source file: {receipt['path']}"
        assert sha256(target) == receipt["sha256"], receipt["path"]
        verified += 1
    manifest["verified_count"] = verified
    return manifest


def record_build(here, checks, verification_scope=None):
    prev_files = {}
    receipt_path = here / "build_receipt.json"
    if receipt_path.exists():
        try:
            prev_files = json.loads(receipt_path.read_text()).get("files", {})
        except Exception:
            prev_files = {}
    files = [
        p
        for p in here.rglob("*")
        if p.is_file()
        and p.name != "build_receipt.json"
        and "__pycache__" not in p.parts
        and "visual_qa" not in p.parts
        and "source_visual_qa" not in p.parts
    ]
    file_hashes = dict(prev_files)
    # Remove any stale visual_qa entries from previous receipts
    for k in list(file_hashes):
        if "visual_qa/" in k or "source_visual_qa/" in k:
            del file_hashes[k]
    for p in sorted(files):
        file_hashes[str(p.relative_to(here))] = sha256(p)
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
        "files": dict(sorted(file_hashes.items())),
        "verification_scope": verification_scope
        or "Local extraction and calculations from retained public records; no GPU benchmark rerun or independent replication.",
    }
    receipt_path.write_text(json.dumps(record, indent=2) + "\n")
    for path in sorted(here.glob("figure.*")):
        print(path.relative_to(ROOT))
