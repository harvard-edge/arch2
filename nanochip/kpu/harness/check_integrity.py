"""Frozen-file integrity check. Verifies SHA-256 of every file listed in
harness/manifest.json. evaluate.py refuses to produce a valid score when any
frozen file was modified. (Final grading additionally re-runs the evaluation
from a pristine checkout — see grading notes — so tampering with this check
or the manifest cannot improve the graded result.)"""

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
MANIFEST = os.path.join(HERE, "manifest.json")


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check() -> dict:
    if not os.path.exists(MANIFEST):
        return {"ok": False, "modified": ["harness/manifest.json (missing)"]}
    man = json.load(open(MANIFEST))
    bad = []
    for rel, digest in man["files"].items():
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            bad.append(rel + " (deleted)")
        elif sha256(p) != digest:
            bad.append(rel)
    return {"ok": not bad, "modified": bad}


if __name__ == "__main__":
    r = check()
    print(json.dumps(r, indent=2))
    sys.exit(0 if r["ok"] else 1)
