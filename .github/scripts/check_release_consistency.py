#!/usr/bin/env python3
"""Validate stable and rendered Architecture 2.0 release metadata."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
VERSION_RE = re.compile(r"^v(?P<version>\d+\.\d+\.\d+)$")
RENDERED_VERSION_RE = re.compile(
    r'<span[^>]+id=["\']arch2-release-metadata["\'][^>]*>([^<]+)</span>'
)
RELEASE_LABEL_VERSION_RE = re.compile(
    r"\bRelease\s+(v\d+\.\d+\.\d+(?:\+g[0-9a-f]{7,40})?)\b",
    re.IGNORECASE,
)
VERSION_NEUTRAL_SOURCES = (
    "book/_quarto.yml",
    "book/tex/version.tex",
    "book/tex/springer-header.tex",
    "cli/book.py",
    "book/images/arch2-cover.svg",
    "book/images/arch2-card.svg",
)
TEXT_ARTIFACT_SUFFIXES = {".css", ".html", ".opf", ".svg", ".xhtml", ".xml"}


def git_output(args: list[str]) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise ValueError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout.strip()


def latest_release() -> tuple[str, str]:
    tag = git_output(["describe", "--tags", "--abbrev=0", "--match", "v[0-9]*"])
    if not VERSION_RE.fullmatch(tag):
        raise ValueError(f"latest release tag is malformed: {tag!r}")
    released = git_output(
        ["for-each-ref", f"refs/tags/{tag}", "--format=%(creatordate:short)"]
    )
    try:
        date.fromisoformat(released)
    except ValueError as exc:
        raise ValueError(f"release tag date is malformed: {released!r}") from exc
    return tag, released


def check_cff(path: Path, tag: str, released: str) -> list[str]:
    errors: list[str] = []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return [f"cannot read {path}: {exc}"]
    if not isinstance(data, dict):
        return [f"{path} must contain a YAML mapping"]

    expected_version = tag.removeprefix("v")
    actual_version = str(data.get("version", ""))
    if actual_version != expected_version:
        errors.append(
            f"{path}: version {actual_version!r} does not match {expected_version!r}"
        )

    raw_date = data.get("date-released", "")
    actual_date = raw_date.isoformat() if isinstance(raw_date, date) else str(raw_date)
    if actual_date != released:
        errors.append(
            f"{path}: date-released {actual_date!r} does not match {released!r}"
        )
    return errors


def release_label_versions(text: str) -> set[str]:
    return {match.group(1) for match in RELEASE_LABEL_VERSION_RE.finditer(text)}


def hardcoded_release_label_errors(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for relative in VERSION_NEUTRAL_SOURCES:
        path = root / relative
        if not path.exists():
            continue
        versions = release_label_versions(path.read_text(encoding="utf-8"))
        if versions:
            errors.append(
                f"{path}: fallback release text must be version-neutral, found "
                + ", ".join(sorted(versions))
            )
    return errors


def rendered_html_version(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = RENDERED_VERSION_RE.search(text)
    if not match:
        raise ValueError(f"{path}: release metadata marker is missing")
    return match.group(1).strip()


def rendered_epub_contains(path: Path, expected: str) -> bool:
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if name.endswith((".html", ".xhtml")):
                if expected.encode() in archive.read(name):
                    return True
    return False


def rendered_epub_release_versions(path: Path) -> set[str]:
    versions: set[str] = set()
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if Path(name).suffix.lower() in TEXT_ARTIFACT_SUFFIXES:
                text = archive.read(name).decode("utf-8", errors="replace")
                versions.update(release_label_versions(text))
    return versions


def rendered_pdf_text(path: Path) -> str:
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        raise ValueError("pdftotext is required to validate rendered PDF metadata")
    proc = subprocess.run(
        [pdftotext, str(path), "-"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise ValueError(proc.stderr.strip() or f"cannot extract text from {path}")
    return proc.stdout


def rendered_tree_release_versions(root: Path) -> set[str]:
    versions: set[str] = set()
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in TEXT_ARTIFACT_SUFFIXES:
            text = path.read_text(encoding="utf-8", errors="replace")
            versions.update(release_label_versions(text))
    return versions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cff", type=Path, default=ROOT / "CITATION.cff")
    parser.add_argument("--expected-version")
    parser.add_argument("--rendered-html", type=Path)
    parser.add_argument("--rendered-pdf", type=Path)
    parser.add_argument("--rendered-epub", type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    try:
        tag, released = latest_release()
        errors.extend(check_cff(args.cff, tag, released))
        errors.extend(hardcoded_release_label_errors())
    except ValueError as exc:
        errors.append(str(exc))

    rendered_paths = [args.rendered_html, args.rendered_pdf, args.rendered_epub]
    if any(rendered_paths) and not args.expected_version:
        errors.append("--expected-version is required with rendered artifacts")
    elif args.expected_version:
        try:
            if args.rendered_html:
                actual = rendered_html_version(args.rendered_html)
                if actual != args.expected_version:
                    errors.append(
                        f"{args.rendered_html}: rendered version {actual!r} does not "
                        f"match {args.expected_version!r}"
                    )
                html_versions = rendered_tree_release_versions(
                    args.rendered_html.parent
                )
                unexpected = html_versions - {args.expected_version}
                if unexpected:
                    errors.append(
                        f"{args.rendered_html.parent}: stale rendered release version(s): "
                        + ", ".join(sorted(unexpected))
                    )
            if args.rendered_pdf:
                pdf_text = rendered_pdf_text(args.rendered_pdf)
                if f"Release {args.expected_version}" not in pdf_text:
                    errors.append(
                        f"{args.rendered_pdf}: Release {args.expected_version} is missing"
                    )
                unexpected = release_label_versions(pdf_text) - {args.expected_version}
                if unexpected:
                    errors.append(
                        f"{args.rendered_pdf}: stale rendered release version(s): "
                        + ", ".join(sorted(unexpected))
                    )
            if args.rendered_epub:
                if not rendered_epub_contains(
                    args.rendered_epub, args.expected_version
                ):
                    errors.append(
                        f"{args.rendered_epub}: {args.expected_version} is missing"
                    )
                unexpected = rendered_epub_release_versions(args.rendered_epub) - {
                    args.expected_version
                }
                if unexpected:
                    errors.append(
                        f"{args.rendered_epub}: stale rendered release version(s): "
                        + ", ".join(sorted(unexpected))
                    )
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            errors.append(str(exc))

    if errors:
        print("Release consistency check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        raise SystemExit(1)
    print(f"Release metadata matches {tag} ({released}).")


if __name__ == "__main__":
    main()
