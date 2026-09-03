#!/usr/bin/env python3
"""Export the provenance notebooks to runnable web pages, and scrub the output.

Two artifacts per notebook:

  html       a static, already-executed page. Fast to open, nothing to install.
  html-wasm  the notebook running in the reader's browser under Pyodide, so the
             numbers are recomputed on their machine from the published receipts.

**Why the scrub exists.** `marimo export` walks up to the project root and copies
sibling files into the export directory. On this repository that pulled `CLAUDE.md`
into the bundle. Publishing that would leak private tooling configuration, so this
script deletes AI-configuration files from every export and then *verifies* they
are gone, exiting non-zero if any survive. Never publish an export produced by
calling `marimo export` directly.

    python3 data/notebooks/export_notebooks.py            # build into www/notebooks/
    python3 data/notebooks/export_notebooks.py --check    # scrub-verify only
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
NOTEBOOKS = REPO / "data" / "notebooks"
OUTPUT = REPO / "www" / "notebooks"

# Anything matching these must never reach a published directory.
FORBIDDEN_NAMES = {
    "claude.md",
    "agents.md",
    "gemini.md",
    "codex.md",
    "copilot-instructions.md",
}
FORBIDDEN_PREFIXES = (".claude", ".codex", ".gemini", ".cursor", ".aider")


def marimo() -> str:
    for candidate in (REPO / ".venv-ast" / "bin" / "marimo", Path("marimo")):
        if candidate.exists() or shutil.which(str(candidate)):
            return str(candidate)
    sys.exit("marimo not found. pip install marimo, or use .venv-ast.")


def scrub(directory: Path) -> list[Path]:
    """Delete AI-configuration files. Returns what was removed."""
    removed = []
    for path in sorted(directory.rglob("*")):
        name = path.name.lower()
        if name in FORBIDDEN_NAMES or name.startswith(FORBIDDEN_PREFIXES):
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            removed.append(path)
    return removed


def verify(directory: Path) -> list[Path]:
    """Anything still present that must not be published."""
    return [
        p
        for p in directory.rglob("*")
        if p.name.lower() in FORBIDDEN_NAMES
        or p.name.lower().startswith(FORBIDDEN_PREFIXES)
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--check",
        action="store_true",
        help="verify existing exports are scrubbed; build nothing",
    )
    args = ap.parse_args()

    books = sorted(p for p in NOTEBOOKS.glob("*.py") if p.name != Path(__file__).name)
    if not books:
        print("no notebooks found")
        return 0

    if args.check:
        leaks = verify(OUTPUT) if OUTPUT.exists() else []
        if leaks:
            print(f"{len(leaks)} FORBIDDEN FILE(S) in {OUTPUT.relative_to(REPO)}:")
            for p in leaks:
                print(f"  - {p.relative_to(REPO)}")
            return 1
        print(f"{OUTPUT.relative_to(REPO)} is clean.")
        return 0

    exe = marimo()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    total_removed = 0

    for nb in books:
        stem = nb.stem
        # 1. static page: already executed, opens instantly
        static = OUTPUT / f"{stem}.html"
        subprocess.run(
            [exe, "export", "html", str(nb), "-o", str(static)],
            check=True,
            capture_output=True,
        )
        # 2. live page: recomputes in the reader's browser
        live = OUTPUT / stem
        if live.exists():
            shutil.rmtree(live)
        subprocess.run(
            [exe, "export", "html-wasm", str(nb), "-o", str(live), "--mode", "run"],
            check=True,
            capture_output=True,
        )

        removed = scrub(live) + scrub(OUTPUT)
        total_removed += len(removed)
        for r in removed:
            print(f"  scrubbed {r.name} from {r.parent.relative_to(REPO)}")
        print(
            f"  built {stem}: {static.relative_to(REPO)} and {live.relative_to(REPO)}/"
        )

    leaks = verify(OUTPUT)
    if leaks:
        print(f"\n{len(leaks)} FORBIDDEN FILE(S) SURVIVED THE SCRUB. Not publishable:")
        for p in leaks:
            print(f"  - {p.relative_to(REPO)}")
        return 1

    print(
        f"\n{len(books)} notebook(s) exported, {total_removed} file(s) scrubbed, 0 leaks."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
