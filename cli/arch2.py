#!/usr/bin/env python3
"""Compatibility facade mapping `cli.arch2` to `cli.book`."""

from __future__ import annotations

import sys
from pathlib import Path


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in (
        here.parents[1],
        *here.parents,
        Path.cwd().resolve(),
        *Path.cwd().resolve().parents,
    ):
        if (candidate / "CITATION.cff").exists() and (candidate / "book").is_dir():
            return candidate
    return here.parents[1]


ROOT = _find_repo_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cli.book as _book

if __name__ == "__main__":
    _book.run_cli()
else:
    sys.modules[__name__] = _book
