#!/usr/bin/env python3
"""Prepare generated and chapter-local figures before Quarto renders."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

BOOK_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BOOK_DIR.parent
IMAGE_REF_RE = re.compile(
    r"images/(?P<name>[^)\s.]+?)(?:\.(?P<ext>pdf|svg|png))?(?=[)\s])"
)


def image_ref_stems(text: str) -> list[str]:
    return sorted({match.group("name") for match in IMAGE_REF_RE.finditer(text)})


def is_stale(source: Path, target: Path) -> bool:
    return not target.exists() or source.stat().st_mtime > target.stat().st_mtime


def audit_svg_text_fit(svg: Path) -> None:
    subprocess.run(
        [str(REPO_ROOT / "arch2"), "validate", "svg", str(svg)],
        check=True,
    )


def prepare_local_images() -> None:
    missing: list[str] = []
    for qmd in sorted(
        [
            *BOOK_DIR.glob("chapters/*/index.qmd"),
            *BOOK_DIR.glob("appendices/*/index.qmd"),
        ]
    ):
        chapter_dir = qmd.parent
        image_dir = chapter_dir / "images"
        image_dir.mkdir(parents=True, exist_ok=True)
        refs = image_ref_stems(qmd.read_text(encoding="utf-8"))
        referenced = {f"{ref}{suffix}" for ref in refs for suffix in (".pdf", ".svg")}
        for existing in [*image_dir.glob("*.pdf"), *image_dir.glob("*.svg")]:
            if existing.name not in referenced:
                existing.unlink()

        for ref in refs:
            svg = image_dir / f"{ref}.svg"
            pdf = image_dir / f"{ref}.pdf"

            if not svg.exists():
                missing.append(f"{qmd.relative_to(BOOK_DIR)} -> images/{ref}.svg")
                continue

            if not pdf.exists() or is_stale(svg, pdf):
                audit_svg_text_fit(svg)
                subprocess.run(
                    ["rsvg-convert", "-f", "pdf", "-o", str(pdf), str(svg)],
                    check=True,
                )

    if missing:
        print("Missing local figure SVGs:", file=sys.stderr)
        for item in missing:
            print(f"  {item}", file=sys.stderr)
        raise SystemExit(1)


def run_book_integrity_checks() -> None:
    subprocess.run(
        [str(REPO_ROOT / "arch2"), "validate", "refs"],
        check=True,
    )


def main() -> None:
    prepare_local_images()
    run_book_integrity_checks()


if __name__ == "__main__":
    main()
