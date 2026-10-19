#!/usr/bin/env python3
"""Check explicit evidence declarations for active manuscript figures.

The figure_evidence map in data/datasets/provenance.yml distinguishes measured,
transcribed, analytical, and conceptual figures. This check verifies inventory,
source-file existence, and bibliography keys. It does not execute generators,
prove that a plot consumes its declared inputs, or certify numerical correctness
or the support a cited source provides. Those require separate source audits.

    python3 data/validate_figure_provenance.py [--verbose]
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CHAPTERS = ROOT / "book" / "contents"
MANIFEST = ROOT / "data" / "datasets" / "provenance.yml"
EVIDENCE_CLASSES = {"measured", "transcribed", "analytical", "conceptual"}


@lru_cache(maxsize=1)
def bibliography_keys() -> set[str]:
    text = (ROOT / "book" / "references" / "references.bib").read_text()
    return set(re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", text))


def cited_sources(caption: str) -> set[str]:
    """Only actual bibliography entries count; @fig/@tbl/@eq are not sources."""
    refs = set(re.findall(r"@([A-Za-z][A-Za-z0-9_:.-]*)", caption))
    return refs & bibliography_keys()


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


@lru_cache(maxsize=1)
def recorded_receipt_paths() -> set[str]:
    records = yaml.safe_load(MANIFEST.read_text()).get("receipts", [])
    return {r["path"] for r in records if isinstance(r, dict) and "path" in r}


def classify(
    label: str, info: dict, evidence: dict | None = None
) -> tuple[str, str, str]:
    """Validate a declaration, never infer evidence class from image format."""
    if evidence is None:
        evidence = (
            yaml.safe_load(MANIFEST.read_text()).get("figure_evidence", {}).get(label)
        )
    where = str(info["qmd"].relative_to(ROOT))
    if not isinstance(evidence, dict):
        return "VIOLATION", "no explicit figure_evidence declaration", where
    kind = evidence.get("evidence_class")
    if kind not in EVIDENCE_CLASSES:
        return "VIOLATION", f"unknown evidence class: {kind!r}", where
    data = evidence.get("data", [])
    keys = evidence.get("citations", [])
    if not isinstance(data, list) or not all(isinstance(p, str) for p in data):
        return "VIOLATION", "data must be a list of repository-relative paths", where
    if not isinstance(keys, list) or not all(isinstance(k, str) for k in keys):
        return "VIOLATION", "citations must be a list of bibliography keys", where
    receipt_paths = recorded_receipt_paths()
    for rel in data:
        path = (ROOT / rel).resolve()
        if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
            return (
                "VIOLATION",
                f"declared input is missing or outside repository: {rel}",
                where,
            )
        if rel not in receipt_paths:
            return (
                "VIOLATION",
                f"declared input is not registered in provenance.yml receipts: {rel}",
                where,
            )
        if rel.startswith("data/studies/"):
            parts = Path(rel).parts
            if len(parts) >= 3:
                study_dir = ROOT / parts[0] / parts[1] / parts[2]
                receipt_file = study_dir / "build_receipt.json"
                if receipt_file.is_file():
                    import hashlib, json

                    receipt_json = json.loads(receipt_file.read_text())
                    rel_in_study = str(path.relative_to(study_dir))
                    expected_sha = receipt_json.get("files", {}).get(rel_in_study)
                    actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
                    if expected_sha and expected_sha != actual_sha:
                        return (
                            "VIOLATION",
                            f"SHA-256 mismatch against {study_dir.name}/build_receipt.json: {rel}",
                            where,
                        )
    unknown = set(keys) - bibliography_keys()
    if unknown:
        return (
            "VIOLATION",
            "unknown bibliography keys: " + ", ".join(sorted(unknown)),
            where,
        )
    source_keys = set(keys) | cited_sources(info.get("caption", ""))
    if kind == "measured" and not data:
        return "VIOLATION", "measured figure requires retained data paths", where
    if kind == "transcribed" and not (data or source_keys):
        return (
            "VIOLATION",
            "transcribed figure requires retained data or bibliographic sources",
            where,
        )
    generator = evidence.get("generator")
    if generator and generator != "inline" and not (ROOT / generator).is_file():
        return "VIOLATION", f"declared generator is missing: {generator}", where
    if not info["cell"]:
        assets = list((info["qmd"].parent / "images").glob(f"{info['stem']}.*"))
        if not any(
            p.suffix.lower() in {".svg", ".pdf", ".png", ".jpg", ".jpeg", ".webp"}
            for p in assets
        ):
            return "VIOLATION", "no figure asset found", where
    detail = (
        f"{len(data)} retained input(s)" if data else "explicit evidence declaration"
    )
    if kind in {"analytical", "conceptual"}:
        detail += "; not empirical observations"
    return f"declared-{kind}", detail, where


def main() -> int:
    manifest = yaml.safe_load(MANIFEST.read_text()).get("figure_evidence", {})
    figs = collect_figures()
    results = [
        (label, *classify(label, info, manifest.get(label, {})))
        for label, info in sorted(figs.items())
    ]
    failures = [r for r in results if r[1] == "VIOLATION"]
    stale = sorted(set(manifest) - set(figs))
    print(f"{len(figs)} active figure declarations\n")
    for kind, count in sorted(Counter(r[1] for r in results).items()):
        print(f"  {kind:24s} {count:3d}")
    if "--verbose" in sys.argv:
        for label, verdict, detail, where in results:
            print(f"  {verdict:24s} {label}: {detail}")
    for label, _, detail, where in failures:
        print(f"  FAIL {label}: {detail} [{where}]")
    for label in stale:
        print(f"  FAIL inactive figure remains in evidence inventory: {label}")
    if failures or stale:
        return 1
    print("\nEvidence declarations and source paths are structurally consistent.")
    print(
        "This does not certify plotted values, generator dataflow, or source support."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
