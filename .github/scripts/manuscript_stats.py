#!/usr/bin/env python3
"""Compute manuscript statistics for the landing page.

The site is static, so the numbers are measured at build time and baked into
the rendered HTML rather than fetched by the browser. That keeps them exact,
keeps the page working with no external requests, and refreshes them on every
publish.

Emits `key=value` lines on stdout for build_site.sh to turn into Quarto
metadata. Every value is a string so a missing measurement degrades to an
empty strip rather than a broken render.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHAPTERS = ROOT / "book" / "chapters"
BIB = ROOT / "book" / "references" / "references.bib"

# Strip the constructs that are not prose the reader reads: fenced code,
# inline code, YAML front matter, div fences, and Quarto attribute blocks.
FENCE = re.compile(r"^(```|:::)", re.MULTILINE)
INLINE_CODE = re.compile(r"`[^`]*`")
FRONT_MATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
ATTRS = re.compile(r"\{[^{}\n]*\}")


def _prose(text: str) -> str:
    text = FRONT_MATTER.sub("", text)
    kept, in_fence = [], False
    for line in text.splitlines():
        if FENCE.match(line):
            # A ::: fence opens and closes callouts; only ``` blocks hide prose.
            if line.startswith("```"):
                in_fence = not in_fence
            continue
        if not in_fence:
            kept.append(line)
    body = "\n".join(kept)
    return ATTRS.sub(" ", INLINE_CODE.sub(" ", body))


def _chapter_files() -> list[Path]:
    return sorted(p for p in CHAPTERS.glob("*/*.qmd") if p.parent.name[:2].isdigit())


def _words(paths: list[Path]) -> int:
    return sum(len(_prose(p.read_text(encoding="utf-8")).split()) for p in paths)


def _figures(paths: list[Path]) -> int:
    """Count labelled figures, which is what a reader actually navigates by."""
    seen: set[str] = set()
    for path in paths:
        seen.update(
            re.findall(r"#(fig-[A-Za-z0-9._-]+)", path.read_text(encoding="utf-8"))
        )
    return len(seen)


def _references() -> int:
    if not BIB.exists():
        return 0
    return len(re.findall(r"^@\w+\s*\{", BIB.read_text(encoding="utf-8"), re.MULTILINE))


def _last_updated() -> str:
    try:
        stamp = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=format:%B %-d, %Y"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return ""
    return stamp


def main() -> int:
    chapters = _chapter_files()
    if not chapters:
        print("manuscript_stats: no chapter files found", file=sys.stderr)
        return 1

    stats = {
        "arch2-stat-chapters": str(len(chapters)),
        "arch2-stat-words": f"{_words(chapters):,}",
        "arch2-stat-figures": str(_figures(chapters)),
        "arch2-stat-references": str(_references()),
        "arch2-stat-updated": _last_updated(),
    }
    for key, value in stats.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
