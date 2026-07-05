#!/usr/bin/env python3
"""Generate callout icons in three formats from a single vector source.

SVG is the master. For each callout group defined in
``config/custom-numbered-blocks.yml`` this script draws a clean line-art glyph
(MLSysBook house style: 64x64, ~2.8 stroke, single accent color, fill=none) in
that group's accent color, then derives a PNG and a PDF from the same SVG so the
three formats can never drift.

  HTML / EPUB use the SVG, the LaTeX/PDF build uses the PDF, and the PNG is kept
  as a raster fallback. Accent colors live only in the YAML; edit them there and
  rerun this script.

Usage (from synthesis/):  python3 book/scripts/make_callout_icons.py
"""

import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BOOK = os.path.dirname(HERE)
CONFIG = os.path.join(BOOK, "config", "custom-numbered-blocks.yml")
DST = os.path.join(BOOK, "images", "icons", "callouts")
SW = 2.8  # base stroke width (matches MLSysBook callout icons)


def load_accents(path):
    """Return {group: '#RRGGBB'} from the filter-metadata groups (colors[1])."""
    accents = {}
    try:
        import yaml  # noqa

        data = yaml.safe_load(open(path))
        groups = data["filter-metadata"]["arch2-ext/custom-numbered-blocks"]["groups"]
        for g, v in groups.items():
            cols = v.get("colors") or []
            if len(cols) >= 2:
                accents[g.replace("-", "_")] = "#" + cols[1].lstrip("#")
        return accents
    except Exception:
        pass
    # Regex fallback (no PyYAML): match "group:\n ... colors: [bg, accent]".
    txt = open(path).read()
    for m in re.finditer(
        r'^\s{6}([a-z-]+):\s*\n\s+colors:\s*\["([0-9A-Fa-f]{6})",\s*"([0-9A-Fa-f]{6})"\]',
        txt,
        re.M,
    ):
        g, _bg, ac = m.groups()
        accents[g.replace("-", "_")] = "#" + ac
    return accents


def gear(cx, cy, rI, teeth, c, sw):
    body = (
        '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="%s" stroke-width="%.2f"/>'
        % (cx, cy, rI, c, sw)
    )
    tw, th = 5.4, 5.2
    teeth_svg = ""
    for i in range(teeth):
        ang = (i / teeth) * 360.0
        teeth_svg += (
            '<g transform="rotate(%.2f %.1f %.1f)"><rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="1.4" fill="none" stroke="%s" stroke-width="%.2f" stroke-linejoin="round"/></g>'
            % (ang, cx, cy, cx - tw / 2, cy - rI - th + 1.2, tw, th, c, sw)
        )
    hole = (
        '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="%s" stroke-width="%.2f"/>'
        % (cx, cy, rI * 0.42, c, sw)
    )
    return teeth_svg + body + hole


def glyph(name, c):
    s = SW
    if name == "architect_checkpoint":  # shield + check = governance / authority
        return (
            '<path d="M32 7 L53 15 V31 C53 43 44 52 32 57 C20 52 11 43 11 31 V15 Z" fill="none" stroke="%s" stroke-width="%.2f" stroke-linejoin="round"/>'
            '<path d="M23 31 l6.5 6.5 L42 24" fill="none" stroke="%s" stroke-width="%.2f" stroke-linecap="round" stroke-linejoin="round"/>'
            % (c, s, c, s + 0.4)
        )
    if name == "carry_forward":  # arrow in a circle = carry forward
        return (
            '<circle cx="32" cy="32" r="22" fill="none" stroke="%s" stroke-width="%.2f"/>'
            '<path d="M22 32 H40" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
            '<path d="M34 25 L41 32 L34 39" fill="none" stroke="%s" stroke-width="%.2f" stroke-linecap="round" stroke-linejoin="round"/>'
            % (c, s, c, s, c, s)
        )
    if name == "design_principle":  # classical column = durable principle
        return (
            '<path d="M13 17 H51" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
            '<path d="M17 23 H47" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
            + "".join(
                '<path d="M%d 24 V49" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
                % (x, c, s)
                for x in (21, 28, 36, 43)
            )
            + '<path d="M13 50 H51" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/><path d="M16 55 H48" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
        ) % (c, s, c, s, c, s, c, s)
    if name == "engineer_move":  # cog = an engineering action
        return gear(32, 32, 13.5, 8, c, s)
    if name == "evidence_packet":  # clipboard + check = bundled evidence
        return (
            '<rect x="14" y="13" width="36" height="43" rx="4" fill="none" stroke="%s" stroke-width="%.2f"/>'
            '<rect x="25" y="9" width="14" height="8" rx="2.5" fill="none" stroke="%s" stroke-width="%.2f"/>'
            '<path d="M21 29 H43" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
            '<path d="M21 37 H43" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
            '<path d="M21 45 l4.5 4.5 L34 41" fill="none" stroke="%s" stroke-width="%.2f" stroke-linecap="round" stroke-linejoin="round"/>'
            % (c, s, c, s, c, s, c, s, c, s)
        )
    if name == "failure_mode":  # warning triangle
        return (
            '<path d="M32 11 L54 52 H10 Z" fill="none" stroke="%s" stroke-width="%.2f" stroke-linejoin="round"/>'
            '<path d="M32 26 V40" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
            '<circle cx="32" cy="46" r="2.6" fill="%s"/>' % (c, s, c, s, c)
        )
    if name == "field_note":  # note page with folded corner
        return (
            '<path d="M16 9 H39 L49 19 V55 H16 Z" fill="none" stroke="%s" stroke-width="%.2f" stroke-linejoin="round"/>'
            '<path d="M39 9 V19 H49" fill="none" stroke="%s" stroke-width="%.2f" stroke-linejoin="round"/>'
            '<path d="M22 29 H42" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
            '<path d="M22 37 H42" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
            '<path d="M22 45 H34" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
            % (c, s, c, s, c, s, c, s, c, s)
        )
    if name == "learning_objectives":  # lightbulb = what you will learn
        return (
            '<path d="M21 28 a11 11 0 1 1 22 0 c0 5 -4 7 -5.5 11 h-11 C25 35 21 33 21 28 Z" fill="none" stroke="%s" stroke-width="%.2f" stroke-linejoin="round"/>'
            '<path d="M24.5 44 H39.5" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
            '<path d="M26.5 49 H37.5" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
            '<path d="M29 53.5 H35" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
            '<path d="M32 22 l3 4 l-3 4 l-3 -4 Z" fill="none" stroke="%s" stroke-width="%.2f" stroke-linejoin="round"/>'
            % (c, s, c, s, c, s, c, s, c, s - 0.6)
        )
    if name == "lighthouse":  # lighthouse = recurring worked prompt anchor
        return (
            '<path d="M25 56 H39 L36 21 H28 Z" fill="none" stroke="%s" stroke-width="%.2f" stroke-linejoin="round"/>'
            '<path d="M24 21 H40 L36 12 H28 Z" fill="none" stroke="%s" stroke-width="%.2f" stroke-linejoin="round"/>'
            '<path d="M21 56 H43" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
            '<path d="M29 31 H35" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
            '<path d="M28 43 H36" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
            '<path d="M19 16 H8" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
            '<path d="M45 16 H56" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
            '<path d="M23 11 L15 6" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
            '<path d="M41 11 L49 6" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
            '<circle cx="32" cy="16" r="3.4" fill="none" stroke="%s" stroke-width="%.2f"/>'
            % (c, s, c, s, c, s, c, s, c, s, c, s, c, s, c, s, c, s, c, s - 0.4)
        )
    if name == "crux":  # compass needle in a circle = the chapter's crux
        return (
            '<circle cx="32" cy="32" r="22" fill="none" stroke="%s" stroke-width="%.2f"/>'
            '<path d="M42 22 L35.5 35.5 L22 42 L28.5 28.5 Z" fill="none" stroke="%s" stroke-width="%.2f" stroke-linejoin="round"/>'
            '<path d="M42 22 L35.5 35.5 L28.5 28.5 Z" fill="%s"/>' % (c, s, c, s, c)
        )
    if name == "research_question":  # magnifier + ? = research question
        return (
            '<circle cx="28" cy="28" r="15" fill="none" stroke="%s" stroke-width="%.2f"/>'
            '<path d="M39 39 L51 51" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
            '<path d="M23.5 24 a4.6 4.6 0 1 1 7.3 3.7 c-1.4 1.1 -2.8 1.9 -2.8 4" fill="none" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
            '<circle cx="27.9" cy="35" r="1.9" fill="%s"/>'
            % (c, s, c, s + 0.5, c, s - 0.5, c)
        )
    return None


def svg_doc(body):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" '
        'viewBox="0 0 64 64" fill="none">\n  ' + body + "\n</svg>\n"
    )


def main():
    accents = load_accents(CONFIG)
    if not accents:
        print("ERROR: no accent colors parsed from", CONFIG, file=sys.stderr)
        return 1
    os.makedirs(DST, exist_ok=True)
    made = []
    for name, color in sorted(accents.items()):
        body = glyph(name, color)
        if body is None:
            print("  skip (no glyph defined):", name)
            continue
        base = os.path.join(DST, "icon_callout_%s" % name)
        with open(base + ".svg", "w") as f:
            f.write(svg_doc(body))
        subprocess.run(
            [
                "rsvg-convert",
                "-f",
                "png",
                "-w",
                "512",
                "-h",
                "512",
                base + ".svg",
                "-o",
                base + ".png",
            ],
            check=True,
        )
        subprocess.run(
            ["rsvg-convert", "-f", "pdf", base + ".svg", "-o", base + ".pdf"],
            check=True,
        )
        made.append(name)
    print(
        "generated %d callout icons (svg + png + pdf) in %s"
        % (len(made), os.path.relpath(DST, BOOK))
    )
    for n in made:
        print("  -", n, accents[n])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
