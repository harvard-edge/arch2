#!/usr/bin/env python3
"""Inject a "development preview" banner into every page of an assembled site.

This runs only in the dev-preview pipeline against the already-assembled
``_site`` tree, so the production build is never touched. The banner makes the
build identity obvious on every page: which branch and commit it came from, when
it was built, and a link back to the stable site.

All identity values are passed in by the caller (nothing hardcoded) via
environment variables:

    ARCH2_PREVIEW_REF         branch name, e.g. dev
    ARCH2_PREVIEW_SHORT_SHA   short commit sha, e.g. a93123ec
    ARCH2_PREVIEW_COMMIT_URL  link to the commit (optional; sha is plain text if unset)
    ARCH2_PREVIEW_BUILD_TIME  human build timestamp, e.g. 2026-08-09 13:44 UTC
    ARCH2_PREVIEW_STABLE_URL  link to the production site, e.g. https://arch2.mlsysbook.ai/

Usage:
    inject_preview_banner.py SITE_DIR
"""

from __future__ import annotations

import html
import os
import re
import sys
from pathlib import Path

MARKER = "data-arch2-preview-banner"
BODY_OPEN_RE = re.compile(r"(<body\b[^>]*>)", re.IGNORECASE)
HTML_SUFFIXES = {".html", ".htm"}

# Self-contained inline styles so the banner renders identically across the
# three sub-projects (www, book, tools) regardless of their own stylesheets.
BANNER_STYLE = (
    "margin:0;padding:.55rem 1rem;"
    "background:#fdf6e3;border-bottom:1px solid #f0d999;"
    "border-left:5px solid #b30000;"
    "font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;"
    "font-size:.9rem;line-height:1.4;color:#5c4600;text-align:center;"
)
SHA_STYLE = (
    "font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;"
    "background:#efe3ff;color:#5a2ca0;padding:.05rem .4rem;border-radius:4px;"
    "text-decoration:none;"
)
STABLE_STYLE = "color:#b30000;font-style:italic;font-weight:600;text-decoration:none;"


def build_banner() -> str:
    ref = html.escape(os.environ.get("ARCH2_PREVIEW_REF", "dev"))
    short_sha = html.escape(os.environ.get("ARCH2_PREVIEW_SHORT_SHA", "unknown"))
    commit_url = os.environ.get("ARCH2_PREVIEW_COMMIT_URL", "").strip()
    build_time = html.escape(os.environ.get("ARCH2_PREVIEW_BUILD_TIME", "").strip())
    stable_url = os.environ.get("ARCH2_PREVIEW_STABLE_URL", "").strip()

    if commit_url:
        sha_html = (
            f'<a href="{html.escape(commit_url, quote=True)}" '
            f'style="{SHA_STYLE}">{ref}@{short_sha}</a>'
        )
    else:
        sha_html = f'<code style="{SHA_STYLE}">{ref}@{short_sha}</code>'

    parts = [
        '<span aria-hidden="true">⚠️ 🚧</span> ',
        "<strong>DEVELOPMENT PREVIEW</strong> — Built from ",
        sha_html,
    ]
    if build_time:
        parts.append(f" • <time>{build_time}</time>")
    if stable_url:
        parts.append(
            f' • <a href="{html.escape(stable_url, quote=True)}" '
            f'style="{STABLE_STYLE}">Stable version →</a>'
        )

    inner = "".join(parts)
    return (
        f'<div {MARKER} role="note" aria-label="Development preview banner" '
        f'style="{BANNER_STYLE}">{inner}</div>'
    )


def inject(path: Path, banner: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return False
    new_text, count = BODY_OPEN_RE.subn(
        lambda m: f"{m.group(1)}{banner}", text, count=1
    )
    if count == 0:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def main(arguments: list[str]) -> int:
    if len(arguments) != 1:
        print("usage: inject_preview_banner.py SITE_DIR", file=sys.stderr)
        return 2
    site_dir = Path(arguments[0])
    if not site_dir.is_dir():
        print(f"{site_dir}: site directory does not exist", file=sys.stderr)
        return 2

    banner = build_banner()
    injected = 0
    for path in sorted(site_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in HTML_SUFFIXES:
            if inject(path, banner):
                injected += 1
    print(f"Injected preview banner into {injected} page(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
