"""Small, shared integrity helpers for mined evidence bundles."""
import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform

ROOT = Path(__file__).resolve().parents[2]

# What each verify_sources call in this process checked, by folder. record_build
# reads this, so a receipt cannot report more verification than took place.
_verifications = {}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_sources(here, allow_missing_gitignored=False):
    manifest = json.loads((here / "source_manifest.json").read_text())
    verified = 0
    missing = []
    for receipt in manifest["files"]:
        target = here / receipt["path"]
        if not target.exists() and allow_missing_gitignored:
            missing.append(receipt["path"])
            continue
        assert target.exists(), f"missing source file: {receipt['path']}"
        assert sha256(target) == receipt["sha256"], receipt["path"]
        verified += 1
    manifest["verified_count"] = verified
    manifest["missing_sources"] = missing
    _verifications[Path(here).resolve()] = {
        "declared": len(manifest["files"]),
        "hash_verified": verified,
        "missing": missing,
    }
    if missing:
        print(f"{here.name}: {len(missing)} declared source(s) absent, not hash-checked:")
        for path in missing:
            print(f"  {path}")
    return manifest


def record_build(here, checks, verification_scope=None):
    receipt_path = here / "build_receipt.json"
    # Older callers pass len(manifest["files"]), the declared count. Reports what was
    # hashed instead, because those callers' reproduce.py files are bound by audits.
    own = _verifications.get(Path(here).resolve())
    if own and isinstance(checks, dict) and "source_files_hash_verified" in checks:
        checks = {**checks, "source_files_hash_verified": own["hash_verified"]}
    files = [
        p
        for p in here.rglob("*")
        if p.is_file()
        and p.name != "build_receipt.json"
        and p.name != "runs.jsonl"
        and "runs" not in p.relative_to(here).parts
        and "__pycache__" not in p.parts
        and "visual_qa" not in p.parts
        and "source_visual_qa" not in p.parts
    ]
    file_hashes = {}
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
        "source_verification": {
            os.path.relpath(folder, ROOT): result
            for folder, result in sorted(_verifications.items())
        },
        "files": dict(sorted(file_hashes.items())),
        "verification_scope": verification_scope
        or "Local extraction and calculations from retained public records; no GPU benchmark rerun or independent replication.",
    }
    receipt_path.write_text(json.dumps(record, indent=2) + "\n")
    for path in sorted(here.glob("figure.*")):
        print(path.relative_to(ROOT))
