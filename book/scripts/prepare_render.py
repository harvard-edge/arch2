#!/usr/bin/env python3
"""Prepare generated and chapter-local figures before Quarto renders."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

# rsvg-convert stamps a creation date into every PDF it writes, so converting the
# same SVG twice produces different bytes. The render's generated-asset check then
# reports the tracked derivative as dirty and fails the publish, which is why a
# release could not get past the drift gate. Pinning SOURCE_DATE_EPOCH makes the
# output byte-identical, so a derivative changes only when its SVG actually does.
# The value is arbitrary and fixed on purpose: it is metadata no reader sees, and
# anything derived from the clock or from HEAD would reintroduce the drift.
SOURCE_DATE_EPOCH = "1700000000"


def deterministic_env() -> dict[str, str]:
    return {**os.environ, "SOURCE_DATE_EPOCH": SOURCE_DATE_EPOCH}


BOOK_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BOOK_DIR.parent
IMAGE_REF_RE = re.compile(
    r"images/(?P<name>[^)\s.]+?)(?:\.(?P<ext>pdf|svg|png))?(?=[)\s])"
)


def image_ref_stems(text: str) -> list[str]:
    return sorted({match.group("name") for match in IMAGE_REF_RE.finditer(text)})


def _git_path(repo_root: Path, path: Path) -> str | None:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return None


def _git_dirty(repo_root: Path, path: Path) -> bool | None:
    relative = _git_path(repo_root, path)
    if relative is None:
        return None
    proc = subprocess.run(
        [
            "git",
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            "--",
            relative,
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    return bool(proc.stdout.strip())


def _git_tracked(repo_root: Path, path: Path) -> bool | None:
    relative = _git_path(repo_root, path)
    if relative is None:
        return None
    proc = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return True
    if proc.returncode == 1:
        return False
    return None


def _git_last_change(repo_root: Path, path: Path) -> str | None:
    relative = _git_path(repo_root, path)
    if relative is None:
        return None
    proc = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", relative],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _git_is_ancestor(repo_root: Path, ancestor: str, descendant: str) -> bool | None:
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return True
    if proc.returncode == 1:
        return False
    return None


def is_stale(source: Path, target: Path, *, repo_root: Path = REPO_ROOT) -> bool:
    """Return whether a derived asset needs regeneration.

    Git checkout mtimes depend on checkout order, so committed pairs use their
    last-changing revisions. Files being actively edited retain the convenient
    mtime behavior used during figure authoring.
    """
    if not target.exists():
        return True

    source_tracked = _git_tracked(repo_root, source)
    target_tracked = _git_tracked(repo_root, target)
    if source_tracked is True and target_tracked is False:
        return True

    source_dirty = _git_dirty(repo_root, source)
    target_dirty = _git_dirty(repo_root, target)
    if source_dirty is not None and target_dirty is not None:
        if source_dirty:
            if not target_dirty:
                return True
            return source.stat().st_mtime > target.stat().st_mtime
        if target_dirty:
            return False

        source_change = _git_last_change(repo_root, source)
        target_change = _git_last_change(repo_root, target)
        if source_change and target_change:
            synchronized = _git_is_ancestor(repo_root, source_change, target_change)
            if synchronized is not None:
                return not synchronized

    return source.stat().st_mtime > target.stat().st_mtime


def audit_svg_text_fit(svg: Path) -> None:
    return


def chapter_sources() -> dict[Path, list[Path]]:
    """Map each chapter and appendix directory to the QMD files it owns.

    Matched on any ``*.qmd`` rather than on ``index.qmd``, because chapter files
    are named after their directory. A directory's ``images/`` is private to it,
    so refs are unioned across the directory before anything is pruned.
    """
    groups: dict[Path, list[Path]] = {}
    for qmd in sorted(
        [
            *BOOK_DIR.glob("contents/chapters/*/*.qmd"),
            *BOOK_DIR.glob("contents/backmatter/*/*.qmd"),
        ]
    ):
        groups.setdefault(qmd.parent, []).append(qmd)
    return groups


def convert_refs(refs: list[str], image_dir: Path, source: Path) -> list[str]:
    """Render each referenced SVG to PDF, returning refs that have no source."""
    missing: list[str] = []
    for ref in refs:
        svg = image_dir / f"{ref}.svg"
        pdf = image_dir / f"{ref}.pdf"
        png = image_dir / f"{ref}.png"

        if png.exists():
            continue

        if not svg.exists():
            missing.append(
                f"{source.relative_to(BOOK_DIR)} -> {image_dir.name}/{ref}.svg"
            )
            continue

        if not pdf.exists() or is_stale(svg, pdf):
            audit_svg_text_fit(svg)
            subprocess.run(
                ["rsvg-convert", "-f", "pdf", "-o", str(pdf), str(svg)],
                check=True,
                env=deterministic_env(),
            )
    return missing


def prepare_local_images() -> None:
    groups = chapter_sources()
    if not groups:
        print(
            "No chapter or appendix QMD files found under "
            f"{BOOK_DIR}/contents/chapters and {BOOK_DIR}/contents/backmatter. "
            "Figure preparation "
            "would silently do nothing and the PDF would build against stale "
            "art, so this is treated as a build failure.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    missing: list[str] = []
    for chapter_dir, qmds in groups.items():
        image_dir = chapter_dir / "images"
        image_dir.mkdir(parents=True, exist_ok=True)
        refs = sorted(
            {
                ref
                for qmd in qmds
                for ref in image_ref_stems(qmd.read_text(encoding="utf-8"))
            }
        )
        referenced = {f"{ref}{suffix}" for ref in refs for suffix in (".pdf", ".svg")}
        for existing in [*image_dir.glob("*.pdf"), *image_dir.glob("*.svg")]:
            if existing.name not in referenced:
                existing.unlink()
        missing += convert_refs(refs, image_dir, qmds[0])

    # Front matter draws on book/images/, which also holds site art such as the
    # cover and favicons that no QMD references. Convert it, never prune it.
    # Root index.qmd includes the preface; front matter pages live under contents/.
    frontmatter_dir = BOOK_DIR / "contents" / "frontmatter"
    front_matter_sources = [
        path
        for path in (
            BOOK_DIR / "index.qmd",
            *sorted(frontmatter_dir.glob("*.qmd")),
        )
        if path.exists()
    ]
    front_refs: set[str] = set()
    for source in front_matter_sources:
        front_refs.update(image_ref_stems(source.read_text(encoding="utf-8")))
    if front_refs:
        missing += convert_refs(
            sorted(front_refs),
            BOOK_DIR / "images",
            front_matter_sources[0],
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
