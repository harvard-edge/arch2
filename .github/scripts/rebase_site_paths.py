#!/usr/bin/env python3
"""Rebase an assembled site under a URL base path (for subpath previews).

The production site is served from a domain root (``arch2.mlsysbook.ai/``) and
its pages therefore use root-absolute references such as ``/book/index.html`` and
``/images/arch2-card.png``. A GitHub project-pages preview is served from a
subpath instead (``harvard-edge.github.io/<repo>/``), so every root-absolute
reference has to be prefixed with that base path or it resolves against the
wrong root and 404s.

This rewrites the references in place. The files keep their locations inside the
assembled tree; only the link text changes, because on the live server the base
path maps back onto the deployed repository root.

Usage:
    rebase_site_paths.py SITE_DIR BASE_PATH

``BASE_PATH`` is a leading-slash, no-trailing-slash prefix such as ``/arch2-dev``.
An empty base path is a no-op, so the same step can run unconditionally for the
root deployment.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# HTML attributes whose value is a single URL that must be rebased when it is
# root-absolute. ``data-arch2-href`` is the hub navbar's deferred href, copied
# onto ``href`` at runtime, so it must move in lockstep.
SINGLE_URL_ATTRS = ("href", "src", "poster", "data-arch2-href")

HTML_SUFFIXES = {".html", ".htm"}
CSS_SUFFIXES = {".css"}
MANIFEST_SUFFIXES = {".webmanifest"}


def _needs_prefix(value: str, base: str) -> bool:
    """A root-absolute local path that is not already under the base path."""
    if not value.startswith("/") or value.startswith("//"):
        return False
    if value == base or value.startswith(base + "/"):
        return False
    return True


def _rebase_single_attrs(text: str, base: str) -> tuple[str, int]:
    count = 0
    attr_group = "|".join(re.escape(attr) for attr in SINGLE_URL_ATTRS)
    pattern = re.compile(
        rf"(?P<attr>\b(?:{attr_group}))(?P<eq>\s*=\s*)(?P<q>[\"'])(?P<val>[^\"']*)(?P=q)"
    )

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        value = match.group("val")
        if not _needs_prefix(value, base):
            return match.group(0)
        count += 1
        return (
            f"{match.group('attr')}{match.group('eq')}{match.group('q')}"
            f"{base}{value}{match.group('q')}"
        )

    return pattern.sub(repl, text), count


def _rebase_srcset(text: str, base: str) -> tuple[str, int]:
    count = 0
    pattern = re.compile(r"(srcset\s*=\s*)([\"'])(.*?)\2", re.IGNORECASE | re.DOTALL)

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        candidates = []
        for candidate in match.group(3).split(","):
            parts = candidate.strip().split(None, 1)
            if not parts:
                continue
            url = parts[0]
            descriptor = f" {parts[1]}" if len(parts) > 1 else ""
            if _needs_prefix(url, base):
                url = f"{base}{url}"
                count += 1
            candidates.append(f"{url}{descriptor}")
        return (
            f"{match.group(1)}{match.group(2)}{', '.join(candidates)}{match.group(2)}"
        )

    return pattern.sub(repl, text), count


def _rebase_css_urls(text: str, base: str) -> tuple[str, int]:
    count = 0
    pattern = re.compile(r"url\(\s*(['\"]?)(?P<val>[^)'\"]*)\1\s*\)")

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        value = match.group("val")
        if not _needs_prefix(value, base):
            return match.group(0)
        count += 1
        quote = match.group(1)
        return f"url({quote}{base}{value}{quote})"

    return pattern.sub(repl, text), count


def _rebase_manifest(text: str, base: str) -> tuple[str, int]:
    count = 0
    pattern = re.compile(r"\"(?P<val>/[^\"]*)\"")

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        value = match.group("val")
        if not _needs_prefix(value, base):
            return match.group(0)
        count += 1
        return f'"{base}{value}"'

    return pattern.sub(repl, text), count


def rebase_file(path: Path, base: str) -> int:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    total = 0
    if suffix in HTML_SUFFIXES:
        text, changed = _rebase_single_attrs(text, base)
        total += changed
        text, changed = _rebase_srcset(text, base)
        total += changed
        text, changed = _rebase_css_urls(text, base)
        total += changed
    elif suffix in CSS_SUFFIXES:
        text, changed = _rebase_css_urls(text, base)
        total += changed
    elif suffix in MANIFEST_SUFFIXES:
        text, changed = _rebase_manifest(text, base)
        total += changed
    if total:
        path.write_text(text, encoding="utf-8")
    return total


def normalize_base(raw: str) -> str:
    base = raw.strip().rstrip("/")
    if not base:
        return ""
    if not base.startswith("/"):
        base = "/" + base
    return base


def main(arguments: list[str]) -> int:
    if len(arguments) != 2:
        print("usage: rebase_site_paths.py SITE_DIR BASE_PATH", file=sys.stderr)
        return 2
    site_dir = Path(arguments[0])
    if not site_dir.is_dir():
        print(f"{site_dir}: site directory does not exist", file=sys.stderr)
        return 2
    base = normalize_base(arguments[1])
    if not base:
        print("Empty base path; leaving the site at the domain root (no-op).")
        return 0

    suffixes = HTML_SUFFIXES | CSS_SUFFIXES | MANIFEST_SUFFIXES
    files = 0
    rewrites = 0
    for path in sorted(site_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in suffixes:
            changed = rebase_file(path, base)
            if changed:
                files += 1
                rewrites += changed
    print(f"Rebased {rewrites} reference(s) under {base!r} across {files} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
