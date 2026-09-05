#!/usr/bin/env python3
"""Validate skip-link and main-landmark structure in rendered custom pages."""

from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path


class LandmarkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.main_ids: list[str | None] = []
        self.main_depth = 0
        self.nested_main = False
        self.skip_targets: list[str | None] = []
        self.accessibility_initializers = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "main":
            if self.main_depth:
                self.nested_main = True
            self.main_depth += 1
            self.main_ids.append(attributes.get("id"))
        if tag == "a" and "site-skip-link" in (attributes.get("class") or "").split():
            self.skip_targets.append(attributes.get("href"))
        if tag == "script" and attributes.get("data-arch2-accessibility") == "true":
            self.accessibility_initializers += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "main":
            self.main_depth -= 1


def findings(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if 'http-equiv="refresh"' in text.lower():
        return []
    parser = LandmarkParser()
    parser.feed(text)
    problems: list[str] = []
    if parser.main_ids != ["main-content"]:
        problems.append(
            f"expected one main#main-content landmark, found {parser.main_ids}"
        )
    if parser.nested_main:
        problems.append("main landmarks are nested")
    if parser.main_depth != 0:
        problems.append("main landmark tags are unbalanced")
    if parser.skip_targets != ["#main-content"]:
        problems.append(
            f"expected one skip link to #main-content, found {parser.skip_targets}"
        )
    if parser.accessibility_initializers != 1:
        problems.append(
            "expected one shared accessibility initializer, found "
            f"{parser.accessibility_initializers}"
        )
    return problems


def main(arguments: list[str]) -> int:
    paths = [Path(argument) for argument in arguments]
    if not paths:
        print("usage: check_site_accessibility.py RENDERED_HTML ...", file=sys.stderr)
        return 2

    failed = False
    for path in paths:
        if not path.is_file():
            print(f"{path}: rendered HTML file does not exist", file=sys.stderr)
            failed = True
            continue
        for problem in findings(path):
            print(f"{path}: {problem}", file=sys.stderr)
            failed = True
    if failed:
        return 1
    print(f"Rendered landmark contract passed for {len(paths)} page(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
