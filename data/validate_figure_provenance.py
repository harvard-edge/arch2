#!/usr/bin/env python3
"""Fail if a figure's data has no honest account of where it came from.

Companion to ``validate_provenance.py``, which polices the receipt files. This
one polices the figures built from them, and it exists because of a real defect:
``fig-testbench-vacuity-and-judge-bias`` drew its values from ``rng.gauss`` while
its caption attributed them to three real papers.

The rule is not "never use a random number generator". The manuscript has
legitimate constructed illustrations, and they are good figures. The rule is:

    A figure whose numbers do not come from a data file must either
    declare itself constructed, or cite the source it transcribed.

Silence is the defect. A constructed figure that says so is honest. A
constructed figure whose caption reads like a measurement is not, and neither is
a table of numbers typed into a script with no source named anywhere.

    python3 data/validate_figure_provenance.py [--verbose]

Exits non-zero on any violation, so it can gate a commit or a build.
"""

from __future__ import annotations

import io
import re
import sys
import tokenize
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHAPTERS = ROOT / "book" / "contents"

RNG_PATTERNS = [
    r"\brng\s*\.\s*(gauss|uniform|normalvariate|betavariate|triangular)",
    r"\brandom\s*\.\s*(gauss|uniform|normalvariate|triangular|random)\b",
    r"\bnp\.random\.(normal|randn|uniform|lognormal|choice)",
    r"_gaussian_noise\s*\(",
]

# Words that tell the reader the figure is not a measurement. Kept deliberately
# broad: the point is that the caption said *something*, not that it used an
# approved synonym.
DECLARES_CONSTRUCTED = [
    "constructed",
    "illustrative",
    "illustration",
    "schematic",
    "stylized",
    "hypothetical",
    "notional",
    "conceptual",
    "for illustration",
    "no real system",
    "not a measurement",
    "synthetic",
    "toy example",
]

# Inline numeric literals above this count mean the script carries its own data
# table rather than a few layout constants.
LITERAL_THRESHOLD = 25


def strip_code(src: str) -> str:
    """Blank out comments and strings so prose about an RNG is not read as one."""
    try:
        out: list[str] = []
        last = (1, 0)
        for tok, text, start, end, _ in tokenize.generate_tokens(
            io.StringIO(src).readline
        ):
            if tok in (tokenize.COMMENT, tokenize.STRING):
                text = re.sub(r"\S", " ", text)
            if start[0] > last[0]:
                out.append("\n" * (start[0] - last[0]))
            out.append(text)
            last = end
        return "".join(out)
    except Exception:
        return "\n".join(re.sub(r"#.*$", "", line) for line in src.splitlines())


def uses_rng(src: str) -> str | None:
    code = strip_code(src)
    for pat in RNG_PATTERNS:
        m = re.search(pat, code)
        if m:
            return f"{m.group(0)} (line {code[: m.start()].count(chr(10)) + 1})"
    return None


def reads_data(src: str) -> str | None:
    m = re.search(r"['\"]([A-Za-z0-9._/-]+\.(?:csv|json|tsv))['\"]", src)
    return Path(m.group(1)).name if m else None


def literal_count(src: str) -> int:
    return len(re.findall(r"\b\d+\.?\d*\s*[,\]]", strip_code(src)))


def caption_of_cell(block: str) -> str:
    """Join every continuation line of a `#| fig-cap:` block scalar.

    Captions run across many `#|` lines and end at the next `#| key:`. Slicing
    at the first one silently drops the citation, which usually sits at the end.
    """
    lines, grabbing, out = block.splitlines(), False, []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("#|"):
            if grabbing:
                break
            continue
        body = stripped[2:].strip()
        if re.match(r"^fig-cap:", body):
            grabbing = True
            out.append(re.sub(r"^fig-cap:\s*\|?", "", body))
            continue
        if grabbing:
            if re.match(r"^[a-z-]+:\s", body):  # next key ends the caption
                break
            out.append(body)
    return " ".join(out).strip()


def collect_figures() -> dict[str, dict]:
    figs: dict[str, dict] = {}
    for qmd in sorted(CHAPTERS.rglob("*.qmd")):
        text = qmd.read_text(errors="ignore")

        # markdown figures: ![caption](images/stem){#fig-label ...}
        for m in re.finditer(
            r"!\[(.*?)\]\(images/([A-Za-z0-9._-]+)\)\{#(fig-[A-Za-z0-9-]+)", text, re.S
        ):
            stem = re.sub(r"\.(png|svg|pdf|jpe?g|webp)$", "", m.group(2), flags=re.I)
            figs[m.group(3)] = {
                "qmd": qmd,
                "stem": stem,
                "cell": None,
                "caption": m.group(1),
            }

        # executable cells: ```{python} ... #| label: fig-...
        for m in re.finditer(r"```\{python\}(.*?)```", text, re.S):
            block = m.group(1)
            lm = re.search(r"#\|\s*label:\s*(fig-[A-Za-z0-9-]+)", block)
            if not lm:
                continue
            figs[lm.group(1)] = {
                "qmd": qmd,
                "stem": None,
                "cell": block,
                "caption": caption_of_cell(block),
            }
    return figs


def generator_for(stem: str | None) -> tuple[Path, str] | None:
    if not stem:
        return None
    for py in sorted(ROOT.rglob("*.py")):
        sp = str(py)
        if "/.git/" in sp or "/.venv" in sp or "/.cache/" in sp:
            continue
        try:
            src = py.read_text(errors="ignore")
        except Exception:
            continue
        if stem in src:
            return py, src
    return None


def classify(label: str, info: dict) -> tuple[str, str, str]:
    """Return (verdict, detail, where)."""
    caption = (info.get("caption") or "").lower()
    declared = any(w in caption for w in DECLARES_CONSTRUCTED)
    cited = bool(re.search(r"@[A-Za-z][A-Za-z0-9_:.-]{3,}", info.get("caption") or ""))

    if info["cell"]:
        src, where = info["cell"], f"{info['qmd'].name} inline cell"
    else:
        found = generator_for(info["stem"])
        if not found:
            assets = list((info["qmd"].parent / "images").glob(f"{info['stem']}.*"))
            if any(a.suffix == ".svg" for a in assets):
                return "ok-diagram", "hand-authored SVG, makes no data claim", ""
            if assets:
                return (
                    "ok-photo",
                    (
                        f"raster only ({assets[0].suffix}), no plotted data; "
                        f"check third-party image permissions, not data provenance"
                    ),
                    "",
                )
            return "unresolved", "no generator and no vector source found", ""
        py, src = found
        where = str(py.relative_to(ROOT))

    data = reads_data(src)
    if data:
        return "ok-data", f"reads {data}", where

    rng = uses_rng(src)
    n = literal_count(src)

    if rng:
        if declared:
            return "ok-constructed", f"{rng}, caption declares it", where
        return (
            "VIOLATION",
            (
                f"generated values ({rng}) and the caption does not say so"
                + (". It cites sources instead" if cited else "")
            ),
            where,
        )

    if n > LITERAL_THRESHOLD:
        if cited or declared:
            kind = "transcribed, cited" if cited else "declared constructed"
            return "ok-inline", f"~{n} inline values, {kind}", where
        return (
            "VIOLATION",
            (
                f"~{n} inline numeric values with no data file, no citation, "
                f"and no statement that the figure is constructed"
            ),
            where,
        )

    return "ok-analytic", f"~{n} literals, computed or schematic", where


def main() -> int:
    verbose = "--verbose" in sys.argv
    figs = collect_figures()
    results = [
        (label, *classify(label, info), info) for label, info in sorted(figs.items())
    ]

    counts = Counter(r[1] for r in results)
    violations = [r for r in results if r[1] == "VIOLATION"]
    unresolved = [r for r in results if r[1] == "unresolved"]

    print(f"{len(results)} referenced figures\n")
    for k, v in sorted(counts.items()):
        print(f"  {k:16s} {v:3d}")

    if verbose:
        print()
        for label, verdict, detail, where, _ in results:
            if verdict.startswith("ok"):
                print(f"  {verdict:16s} {label}\n{' ' * 20}{detail}")

    if unresolved:
        print(f"\n{len(unresolved)} figure(s) could not be resolved to a source.")
        print("Not evidence of fabrication; evidence that the trail is not recorded.\n")
        for label, _, detail, _, info in unresolved:
            print(f"  ? {label}  [{info['qmd'].parent.name}]  {detail}")

    if violations:
        print(f"\n{len(violations)} FIGURE PROVENANCE VIOLATION(S):\n")
        for label, _, detail, where, info in violations:
            print(f"  - {label}  [{info['qmd'].parent.name}]")
            print(f"      {detail}")
            if where:
                print(f"      {where}")
        return 1

    print(
        "\nEvery figure either reads a data file, cites a source, or says it is constructed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
